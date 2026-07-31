"""Atomic SDL declaration rename and identity transport."""

from __future__ import annotations

from copy import deepcopy

from pydantic import ValidationError
from raes_contracts.contracts import (
    ArtifactTransformationIdentityMapModel,
    ArtifactTransformationKind,
    ArtifactTransformationPreservationModel,
    ArtifactTransformationReportModel,
    ArtifactTransformationStatus,
    ExternalConceptBindingDocumentModel,
    PreservationOutcome,
    TransformationCheckOutcome,
)

from ._declarations import build_declaration_index
from ._errors import SDLParseError, SDLValidationError
from ._identifiers import QualifiedName
from ._module_symbols import FORWARDING_AGENTS_SECTION, symbol_index
from ._transformation_support import (
    IDENTITY_TRANSPORT_PROFILE,
    RENAME_PROFILE,
    SDL_CONTRACT_PROFILE,
    check,
    default_policy_digest,
    refused_rename,
    rename_derivation_digest,
    top_level_declaration,
)
from ._transformation_types import (
    RenameSDLDeclarationRequest,
    SDLAuthoringArtifact,
    SDLTransformationResult,
)
from .canonical import canonical_sdl_bytes, canonical_sdl_digest
from .composition import _rewrite_payload_with_symbols
from .external_concept_subjects import external_concept_subjects
from .scenario import ExpandedScenario, ModuleDescriptor, Scenario
from .validator import SemanticValidator


def _new_qualified_key(*, section: str, old_key: str, new_local_name: str) -> str:
    old_name = QualifiedName.parse(old_key)
    if section == "nodes" and len(new_local_name) > 35:
        raise ValueError("node identifiers must remain within the 35-character local limit")
    return QualifiedName((*old_name.parts[:-1], new_local_name)).render()


def _identity_symbols(
    scenario: SDLAuthoringArtifact,
) -> dict[str, dict[str, str] | set[str]]:
    symbols = symbol_index(
        scenario,
        namespace="",
        descriptor=ModuleDescriptor(id="raes/transformation", version="1"),
        restrict_to_descriptor=False,
    )
    symbols[FORWARDING_AGENTS_SECTION] = {
        agent.forwarding_agent_id: agent.forwarding_agent_id for agent in scenario.forwarding_agents
    }
    return symbols


def _rename_symbols(
    scenario: SDLAuthoringArtifact,
    *,
    section: str,
    old_key: str,
    new_key: str,
) -> dict[str, dict[str, str] | set[str]]:
    symbols = _identity_symbols(scenario)
    section_symbols = symbols[section]
    named_symbols = symbols["named"]
    if not isinstance(section_symbols, dict) or not isinstance(named_symbols, dict):
        raise TypeError("SDL symbol index returned an invalid mapping shape")

    section_symbols[old_key] = new_key
    old_address = f"{section}.{old_key}"
    new_address = f"{section}.{new_key}"
    rewritten_named: dict[str, str] = {}
    for alias, target in named_symbols.items():
        if target == old_key:
            rewritten_named[alias] = new_key
        elif target == old_address:
            rewritten_named[alias] = new_address
        elif target.startswith(f"{old_address}."):
            rewritten_named[alias] = f"{new_address}{target.removeprefix(old_address)}"
        else:
            rewritten_named[alias] = target
    rewritten_named[old_key] = new_key
    rewritten_named[old_address] = new_address
    symbols["named"] = rewritten_named
    return symbols


def _rewrite_module_exports(
    payload: dict[str, object],
    *,
    section: str,
    old_key: str,
    new_key: str,
) -> None:
    module = payload.get("module")
    if not isinstance(module, dict):
        return
    exports = module.get("exports")
    if not isinstance(exports, dict):
        return
    exported_names = exports.get(section)
    if isinstance(exported_names, list):
        exports[section] = [new_key if name == old_key else name for name in exported_names]


def _preserve_explicit_shape(template: object, rewritten: object) -> object:
    """Remove helper-populated defaults while retaining rewritten map keys."""

    if isinstance(template, dict) and isinstance(rewritten, dict):
        result: dict[object, object] = {}
        matched_template: set[object] = set()
        matched_rewritten: set[object] = set()
        for key in template:
            if key not in rewritten:
                continue
            result[key] = _preserve_explicit_shape(template[key], rewritten[key])
            matched_template.add(key)
            matched_rewritten.add(key)
        template_only = [key for key in template if key not in matched_template]
        rewritten_only = [key for key in rewritten if key not in matched_rewritten]
        if len(template_only) > len(rewritten_only):
            raise ValueError("reference rewrite changed the explicit payload shape")
        for template_key, rewritten_key in zip(template_only, rewritten_only, strict=False):
            result[rewritten_key] = _preserve_explicit_shape(
                template[template_key],
                rewritten[rewritten_key],
            )
        return result
    if isinstance(template, list) and isinstance(rewritten, list):
        if len(template) != len(rewritten):
            raise ValueError("reference rewrite changed an explicit list shape")
        return [
            _preserve_explicit_shape(template_item, rewritten_item)
            for template_item, rewritten_item in zip(template, rewritten, strict=True)
        ]
    if isinstance(template, tuple) and isinstance(rewritten, tuple):
        if len(template) != len(rewritten):
            raise ValueError("reference rewrite changed an explicit tuple shape")
        return tuple(
            _preserve_explicit_shape(template_item, rewritten_item)
            for template_item, rewritten_item in zip(template, rewritten, strict=True)
        )
    return rewritten


def _rewritten_candidate(
    source: SDLAuthoringArtifact,
    *,
    section: str,
    old_key: str,
    new_key: str,
) -> SDLAuthoringArtifact:
    payload = source.model_dump(mode="python", by_alias=True, exclude_unset=True)
    explicit_shape = deepcopy(payload)
    rewritten = _rewrite_payload_with_symbols(
        payload,
        symbols=_rename_symbols(source, section=section, old_key=old_key, new_key=new_key),
    )
    _rewrite_module_exports(rewritten, section=section, old_key=old_key, new_key=new_key)
    rewritten = _preserve_explicit_shape(explicit_shape, rewritten)
    if not isinstance(rewritten, dict):
        raise TypeError("SDL reference rewrite returned a non-object payload")
    candidate = type(source).model_validate(rewritten)
    validator = SemanticValidator(candidate)
    validator.validate()
    candidate._set_advisories(validator.warnings)
    candidate._set_source_diagnostics(list(source.source_diagnostics))
    candidate._set_semantic_validated(True)
    return candidate


def _retarget_binding_documents(
    documents: tuple[ExternalConceptBindingDocumentModel, ...],
    *,
    source: SDLAuthoringArtifact,
    target: SDLAuthoringArtifact,
    source_digest: str,
    target_digest: str,
    before: str,
    after: str,
) -> tuple[ExternalConceptBindingDocumentModel, ...]:
    source_subjects = {subject.canonical_ref: subject for subject in external_concept_subjects(source)}
    target_subjects = {subject.canonical_ref: subject for subject in external_concept_subjects(target)}
    transformed: list[ExternalConceptBindingDocumentModel] = []
    for document in documents:
        payload = document.model_dump(mode="json")
        bindings = payload.get("bindings")
        if not isinstance(bindings, dict):
            raise ValueError("external concept binding document has an invalid binding map")
        for binding in bindings.values():
            if not isinstance(binding, dict) or not isinstance(binding.get("subject"), dict):
                raise ValueError("external concept binding document has an invalid subject")
            subject = binding["subject"]
            canonical_ref = str(subject.get("canonical_ref", ""))
            source_subject = source_subjects.get(canonical_ref)
            same_source_coordinate = source_subject is not None and (
                source_subject.subject_kind == subject.get("subject_kind")
                and source_subject.owning_contract_id == subject.get("owning_contract_id")
                and source_subject.lifecycle_phase.value == subject.get("lifecycle_phase")
            )
            supplied_digest = str(subject.get("artifact_digest", ""))
            if same_source_coordinate and supplied_digest.casefold() != source_digest.casefold():
                raise ValueError("external concept subject is stale for the source artifact")
            if supplied_digest.casefold() != source_digest.casefold():
                continue
            if not same_source_coordinate or source_subject is None:
                raise ValueError("external concept subject does not resolve in the source artifact")
            rewritten_ref = after if canonical_ref == before else canonical_ref
            target_subject = target_subjects.get(rewritten_ref)
            if target_subject is None or target_subject.subject_kind != source_subject.subject_kind:
                raise ValueError("external concept subject does not resolve in the target artifact")
            subject["canonical_ref"] = rewritten_ref
            subject["artifact_digest"] = target_digest
        transformed.append(ExternalConceptBindingDocumentModel.model_validate(payload))
    return tuple(transformed)


def rename_sdl_declaration(
    source: SDLAuthoringArtifact,
    request: RenameSDLDeclarationRequest,
    *,
    binding_documents: tuple[ExternalConceptBindingDocumentModel, ...] = (),
) -> SDLTransformationResult:
    """Atomically rename one exact top-level SDL declaration and its references."""

    if not isinstance(source, (Scenario, ExpandedScenario)) or not source.semantic_validated:
        raise SDLParseError("SDL transformation requires a semantically admitted authoring scenario")
    source_digest = canonical_sdl_digest(source)
    index = build_declaration_index(source)
    resolved = top_level_declaration(source, index, request.target_address)
    if resolved is None:
        return refused_rename(
            source_digest=source_digest,
            request=request,
            diagnostic_code="artifact-transformation.target-not-exact",
            message="The request target is not an exact supported declaration address.",
        )
    declaration, section, old_key = resolved
    try:
        new_key = _new_qualified_key(section=section, old_key=old_key, new_local_name=request.new_local_name)
    except ValueError:
        return refused_rename(
            source_digest=source_digest,
            request=request,
            diagnostic_code="artifact-transformation.target-unsupported",
            message="The requested replacement is outside the declaration's supported identity boundary.",
            passed_checks=("source-admitted", "target-exact"),
            affected_identities=(request.target_address,),
        )
    new_address = f"{section}.{new_key}"
    collision = index.declaration_for(new_address)
    if collision is not None and collision.address != declaration.address:
        return refused_rename(
            source_digest=source_digest,
            request=request,
            diagnostic_code="artifact-transformation.identity-collision",
            message="The requested replacement collides with an existing canonical declaration.",
            passed_checks=("source-admitted", "target-exact", "target-supported"),
            affected_identities=(request.target_address,),
        )

    try:
        target = _rewritten_candidate(source, section=section, old_key=old_key, new_key=new_key)
    except (SDLValidationError, ValidationError, TypeError, ValueError):
        return refused_rename(
            source_digest=source_digest,
            request=request,
            diagnostic_code="artifact-transformation.target-invalid",
            message="The complete transformed candidate failed structural or semantic admission.",
            passed_checks=("source-admitted", "target-exact", "target-injective", "target-supported"),
            affected_identities=(request.target_address,),
        )
    target_digest = canonical_sdl_digest(target)
    try:
        transformed_bindings = _retarget_binding_documents(
            binding_documents,
            source=source,
            target=target,
            source_digest=source_digest.value,
            target_digest=target_digest.value,
            before=request.target_address,
            after=new_address,
        )
    except (ValidationError, ValueError):
        return refused_rename(
            source_digest=source_digest,
            request=request,
            diagnostic_code="artifact-transformation.linked-artifact-stale",
            message="A supplied linked artifact does not resolve against the exact source and target identities.",
            passed_checks=("source-admitted", "target-exact", "target-injective", "target-supported"),
            affected_identities=(request.target_address,),
        )

    try:
        round_trip = _rewritten_candidate(target, section=section, old_key=new_key, new_key=old_key)
        round_trip_digest = canonical_sdl_digest(round_trip)
    except (SDLValidationError, ValidationError, TypeError, ValueError):
        round_trip_digest = None
    target_index = build_declaration_index(target)
    target_declaration = target_index.declaration_for(new_address)
    preservation_verified = (
        round_trip_digest is not None
        and canonical_sdl_bytes(round_trip) == canonical_sdl_bytes(source)
        and target_declaration is not None
        and target_declaration.kind == declaration.kind
        and target_index.declaration_for(request.target_address) is None
        and len(target_index.declarations) == len(index.declarations)
    )
    if not preservation_verified:
        return refused_rename(
            source_digest=source_digest,
            request=request,
            diagnostic_code="artifact-transformation.preservation-failed",
            message="The transformed candidate did not satisfy the identity-transport round-trip relation.",
            passed_checks=(
                "linked-artifacts-current",
                "source-admitted",
                "target-admitted",
                "target-exact",
                "target-injective",
                "target-supported",
            ),
            affected_identities=(request.target_address,),
        )

    policy_digest = default_policy_digest()
    report = ArtifactTransformationReportModel(
        operation_profile=RENAME_PROFILE,
        status=ArtifactTransformationStatus.SUCCESS,
        artifact_kind=ArtifactTransformationKind.SDL_AUTHORING,
        source_profile=SDL_CONTRACT_PROFILE,
        target_profile=SDL_CONTRACT_PROFILE,
        canonicalization_profile=source_digest.profile,
        source_digest=source_digest.value,
        target_digest=target_digest.value,
        policy_digest=policy_digest,
        derivation_digest=rename_derivation_digest(
            source_digest=source_digest.value,
            policy_digest=policy_digest,
            request=request,
        ),
        preconditions=tuple(
            check(name, TransformationCheckOutcome.PASSED)
            for name in (
                "linked-artifacts-current",
                "source-admitted",
                "target-exact",
                "target-injective",
                "target-supported",
            )
        ),
        postconditions=tuple(
            check(name, TransformationCheckOutcome.PASSED)
            for name in (
                "identity-map-bijective",
                "linked-artifacts-retargeted",
                "round-trip-canonical-identity",
                "target-admitted",
            )
        ),
        affected_identities=(request.target_address,),
        identity_map=(
            ArtifactTransformationIdentityMapModel(
                declaration_kind=declaration.kind,
                before=request.target_address,
                after=new_address,
            ),
        ),
        preservation=ArtifactTransformationPreservationModel(
            profile=IDENTITY_TRANSPORT_PROFILE,
            outcome=PreservationOutcome.VERIFIED,
            evidence_digests=tuple(sorted({source_digest.value, target_digest.value})),
            limitations=("Finite structural and semantic verification does not establish behavioral equivalence.",),
        ),
    )
    return SDLTransformationResult(output=target, binding_documents=transformed_bindings, report=report)


__all__ = ["rename_sdl_declaration"]
