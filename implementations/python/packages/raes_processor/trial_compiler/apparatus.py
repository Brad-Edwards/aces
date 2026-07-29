"""Digest-bound apparatus admission for deterministic trial compilation."""

from __future__ import annotations

from collections.abc import Iterable

from raes_contracts.canonical import canonical_json_digest
from raes_contracts.contracts import (
    BackendManifestV2Model,
    ExperimentManifestReferenceModel,
    ParticipantImplementationManifestModel,
    ProcessorManifestV2Model,
)
from raes_contracts.experiment_bindings import (
    ApparatusManifest,
    ApparatusManifestKey,
    ParticipantManifestKey,
)

from .models import CompilationFailure, TrialCompilationRequest

_CAPABILITY_CONTRACT_ALIASES = {
    "evaluation-results": "evaluation-result-envelope-v1",
    "workflow-results": "workflow-result-envelope-v1",
}


def _fail(code: str, address: str, message: str) -> CompilationFailure:
    return CompilationFailure(code, address, message)


def _reference_key(reference: ExperimentManifestReferenceModel) -> ApparatusManifestKey:
    subject = reference.subject_ref
    if (
        subject is None
        or subject.ref_kind not in {"processor", "backend"}
        or subject.ref_version is None
        or reference.ref_version is None
    ):
        raise _fail(
            "apparatus-manifest-reference-invalid",
            "/apparatus/manifest_refs",
            "selected apparatus manifest references require an exact processor or backend subject identity",
        )
    return (
        subject.ref_kind,
        subject.ref_id,
        subject.ref_version,
        reference.ref_version,
    )


def _manifest_kind(manifest: ApparatusManifest) -> str:
    return "processor" if isinstance(manifest, ProcessorManifestV2Model) else "backend"


def _validate_reference_payload(
    reference: ExperimentManifestReferenceModel,
    manifest: ApparatusManifest,
) -> None:
    subject = reference.subject_ref
    manifest_kind = _manifest_kind(manifest)
    if (
        subject is None
        or subject.ref_kind != manifest_kind
        or reference.ref_id != manifest.identity.name
        or reference.ref_version != manifest.schema_version
        or subject.ref_id != manifest.identity.name
        or subject.ref_version != manifest.identity.version
    ):
        raise _fail(
            "apparatus-manifest-identity-mismatch",
            "/apparatus/manifest_refs",
            "selected apparatus manifest identity does not match its concrete payload",
        )
    digest = canonical_json_digest(manifest.model_dump(mode="json"))
    if reference.ref_digest != digest:
        raise _fail(
            "apparatus-manifest-digest-mismatch",
            "/apparatus/manifest_refs",
            "selected apparatus manifest digest does not match its concrete payload",
        )


def _manifest_capability_ids(manifest: ApparatusManifest) -> set[str]:
    contracts = set(manifest.supported_contract_versions)
    capabilities = set(contracts)
    if isinstance(manifest, ProcessorManifestV2Model):
        capabilities.update(manifest.capabilities.supported_sdl_versions)
        capabilities.update(
            feature.value if hasattr(feature, "value") else str(feature)
            for feature in manifest.capabilities.supported_features
        )
    else:
        capabilities.update(
            capability
            for capability, required_contract in _CAPABILITY_CONTRACT_ALIASES.items()
            if required_contract in contracts
        )
    return capabilities


def _identity_allowed(
    manifest: ApparatusManifest,
    allowed_refs: Iterable[object],
) -> bool:
    manifest_kind = _manifest_kind(manifest)
    return any(
        getattr(reference, "ref_kind", None) == manifest_kind
        and getattr(reference, "ref_id", None) == manifest.identity.name
        and getattr(reference, "ref_version", None) == manifest.identity.version
        for reference in allowed_refs
    )


def _reference_satisfies_requirement(
    selected: ExperimentManifestReferenceModel,
    required: ExperimentManifestReferenceModel,
) -> bool:
    for field_name in ("ref_kind", "ref_id", "ref_version", "ref_digest"):
        required_value = getattr(required, field_name)
        if required_value is not None and getattr(selected, field_name) != required_value:
            return False
    required_subject = required.subject_ref
    selected_subject = selected.subject_ref
    if required_subject is None:
        return True
    if selected_subject is None:
        return False
    return all(
        getattr(required_subject, field_name) is None
        or getattr(selected_subject, field_name) == getattr(required_subject, field_name)
        for field_name in ("ref_kind", "ref_id", "ref_version")
    )


def validate_selected_apparatus(
    request: TrialCompilationRequest,
) -> dict[ApparatusManifestKey, ApparatusManifest]:
    """Resolve and validate every sealed apparatus reference against concrete content."""

    selected: dict[ApparatusManifestKey, ApparatusManifest] = {}
    references_by_key: dict[ApparatusManifestKey, ExperimentManifestReferenceModel] = {}
    for reference in request.apparatus.manifest_refs:
        key = _reference_key(reference)
        if key in selected:
            raise _fail(
                "apparatus-manifest-duplicate",
                "/apparatus/manifest_refs",
                "selected apparatus contains duplicate concrete manifest identities",
            )
        manifest = request.apparatus_manifests.get(key)
        if manifest is None:
            raise _fail(
                "apparatus-manifest-payload-missing",
                "/apparatus/manifest_refs",
                "selected apparatus manifest reference has no exact concrete payload",
            )
        _validate_reference_payload(reference, manifest)
        selected[key] = manifest
        references_by_key[key] = reference

    backends = [manifest for manifest in selected.values() if isinstance(manifest, BackendManifestV2Model)]
    if not backends or any(
        manifest.realization_envelope != request.realization_envelope.identity for manifest in backends
    ):
        raise _fail(
            "apparatus-envelope-unsupported",
            "/apparatus/realization_envelope",
            "selected backend manifests do not bind the admitted realization envelope",
        )

    available_capabilities = set().union(*(_manifest_capability_ids(manifest) for manifest in selected.values()))
    declared_capabilities = set(request.apparatus.capability_refs)
    if not declared_capabilities.issubset(available_capabilities):
        raise _fail(
            "apparatus-capability-unproven",
            "/apparatus/capability_refs",
            "selected apparatus capability claims are not proven by concrete manifests",
        )

    intent = request.experiment.apparatus_intent
    if intent is None:
        return selected
    if not set(intent.required_capabilities).issubset(declared_capabilities):
        raise _fail(
            "apparatus-capability-missing",
            "/apparatus/capability_refs",
            "selected apparatus does not satisfy every required capability",
        )

    for manifest_kind, allowed_refs in (
        ("processor", intent.allowed_processor_refs),
        ("backend", intent.allowed_backend_refs),
    ):
        matching_kind = [manifest for manifest in selected.values() if _manifest_kind(manifest) == manifest_kind]
        if allowed_refs and (
            not matching_kind or any(not _identity_allowed(manifest, allowed_refs) for manifest in matching_kind)
        ):
            raise _fail(
                "apparatus-identity-not-allowed",
                "/apparatus/manifest_refs",
                "selected apparatus identity is outside its admitted kind-specific allowlist",
            )

    selected_references = tuple(references_by_key.values())
    if any(
        not any(_reference_satisfies_requirement(selected_ref, required) for selected_ref in selected_references)
        for required in intent.required_manifest_refs
    ):
        raise _fail(
            "apparatus-manifest-missing",
            "/apparatus/manifest_refs",
            "selected apparatus does not include every exact required manifest",
        )
    return selected


def validate_selected_participant_manifests(
    request: TrialCompilationRequest,
) -> dict[ParticipantManifestKey, ParticipantImplementationManifestModel]:
    """Resolve every participant admission authority from its sealed digest reference."""

    selected: dict[ParticipantManifestKey, ParticipantImplementationManifestModel] = {}
    for reference in request.apparatus.participant_manifest_refs:
        key = (
            reference.participant_address,
            reference.implementation_name,
            reference.implementation_version,
            reference.manifest_version,
        )
        manifest = request.participant_manifests.get(key)
        if manifest is None:
            raise _fail(
                "participant-manifest-payload-missing",
                "/apparatus/participant_manifest_refs",
                "selected participant manifest reference has no exact concrete payload",
            )
        if (
            manifest.identity.name != reference.implementation_name
            or manifest.identity.version != reference.implementation_version
            or manifest.schema_version != reference.manifest_version
        ):
            raise _fail(
                "participant-manifest-identity-mismatch",
                "/apparatus/participant_manifest_refs",
                "selected participant manifest identity does not match its concrete payload",
            )
        if canonical_json_digest(manifest.model_dump(mode="json")) != reference.manifest_digest:
            raise _fail(
                "participant-manifest-digest-mismatch",
                "/apparatus/participant_manifest_refs",
                "selected participant manifest digest does not match its concrete payload",
            )
        selected[key] = manifest
    return selected


__all__ = ["validate_selected_apparatus", "validate_selected_participant_manifests"]
