"""Portable artifact admission and runtime satisfaction semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from raes.artifact_requirements import ArtifactMechanismProfile, ArtifactRequirement
from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance
from raes_backend_protocols.capabilities import BackendManifest
from raes_contracts.artifact_requirements import (
    ArtifactAvailabilityContext,
    ArtifactRequirementAvailability,
    ArtifactSatisfactionDisclosureModel,
)
from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import ChangeAction, ProvisionOp
from raes_contracts.runtime_state import RealizationProvenanceEntry, RuntimeSnapshot
from raes_contracts.vocabulary import RealizationSupportMode

if TYPE_CHECKING:
    from .realization import CompiledRealizationRequirement

_BACKEND_CONTRACT_INVALID = "runtime.backend-contract-invalid"


def artifact_requirement_diagnostics(
    requirements: tuple[CompiledRealizationRequirement, ...],
    manifest: BackendManifest,
    *,
    availability: ArtifactAvailabilityContext | None = None,
) -> list[Diagnostic]:
    """Validate portable artifact demand against facts and backend routes."""

    facts = availability or ArtifactAvailabilityContext()
    diagnostics: list[Diagnostic] = []

    for compiled in requirements:
        requirement = compiled.artifact_requirement
        if requirement is None:
            continue
        scoped_facts = facts.for_address(compiled.address)
        available_digests = set(scoped_facts.available_artifact_digests)
        available_candidates = set(scoped_facts.available_candidate_ids)
        verified_locked_inputs = set(scoped_facts.verified_locked_input_ids)
        satisfied_constraints = set(scoped_facts.satisfied_constraint_ids)
        declarations = [
            declaration for declaration in manifest.realization_support if declaration.domain == compiled.domain
        ]

        if requirement.explicitness is ExplicitnessClass.OPEN and not any(
            declaration.support_mode is RealizationSupportMode.OPEN_REALIZATION for declaration in declarations
        ):
            diagnostics.append(
                _artifact_diagnostic(
                    compiled,
                    "artifact.unsupported-open-realization",
                    "Backend declares no open artifact realization support.",
                )
            )

        if (
            requirement.explicitness is ExplicitnessClass.EXACT
            and requirement.exact_artifact is not None
            and requirement.exact_artifact.digest not in available_digests
        ):
            diagnostics.append(
                _artifact_diagnostic(
                    compiled,
                    "artifact.unavailable-exact-artifact",
                    "The required immutable artifact is not available.",
                )
            )

        for constraint in requirement.constraints:
            if constraint.constraint_id not in satisfied_constraints:
                diagnostics.append(
                    _artifact_diagnostic(
                        compiled,
                        "artifact.unsatisfied-constraint",
                        f"Artifact constraint '{constraint.constraint_id}' is not satisfied.",
                    )
                )

        for locked_input in requirement.locked_inputs:
            if locked_input.input_id not in verified_locked_inputs:
                diagnostics.append(
                    _artifact_diagnostic(
                        compiled,
                        "artifact.missing-locked-input",
                        f"Locked artifact input '{locked_input.input_id}' is not verified.",
                    )
                )

        if requirement.candidates and not any(
            candidate.candidate_id in available_candidates for candidate in requirement.candidates
        ):
            diagnostics.append(
                _artifact_diagnostic(
                    compiled,
                    "artifact.unavailable-candidate",
                    "No declared artifact candidate is available.",
                )
            )

        if requirement.materialization_specifications and not any(
            specification.digest in scoped_facts.available_materialization_specification_digests
            for specification in requirement.materialization_specifications
        ):
            diagnostics.append(
                _artifact_diagnostic(
                    compiled,
                    "artifact.unavailable-materialization-specification",
                    "No declared digest-bound materialization specification is available.",
                )
            )

        supported_routes = {
            (
                _artifact_mechanism_key(capability.mechanism),
                route.acquisition,
                route.timing,
            )
            for declaration in declarations
            for capability in declaration.artifact_mechanisms
            if compiled.requirement_kind in capability.supported_requirement_kinds
            for route in capability.supported_routes
        }
        if not any(
            (
                _artifact_mechanism_key(route.mechanism),
                route.acquisition,
                route.timing,
            )
            in supported_routes
            for route in requirement.permitted_routes
        ):
            diagnostics.append(
                _artifact_diagnostic(
                    compiled,
                    "artifact.unsupported-backend-mechanism",
                    "Backend declares no supported artifact mechanism and acquisition/timing route.",
                )
            )
    return diagnostics


def evaluate_artifact_realization(
    requirement: CompiledRealizationRequirement,
    declared_ops: dict[str, ProvisionOp],
    returned_snapshot: RuntimeSnapshot,
    *,
    manifest: BackendManifest | None,
    availability: ArtifactAvailabilityContext | None,
) -> tuple[Diagnostic | None, RealizationProvenanceEntry | None]:
    """Validate one returned artifact satisfaction before snapshot admission."""

    contract = requirement.artifact_requirement
    op = declared_ops.get(requirement.address)
    if contract is None or op is None or op.action is ChangeAction.DELETE:
        return None, None
    snapshot_entry = returned_snapshot.entries.get(requirement.address)
    payload = snapshot_entry.payload.get("artifact_satisfaction") if snapshot_entry is not None else None
    try:
        satisfaction = ArtifactSatisfactionDisclosureModel.model_validate(payload)
    except (TypeError, ValueError):
        return _silent_approximation_diagnostic(requirement), None

    facts = (availability or ArtifactAvailabilityContext()).for_address(requirement.address)
    permitted_routes = {
        (
            _artifact_mechanism_key(route.mechanism),
            route.acquisition,
            route.timing,
        )
        for route in contract.permitted_routes
    }
    candidate_ids = {candidate.candidate_id for candidate in contract.candidates}
    candidates = {candidate.candidate_id: candidate for candidate in contract.candidates}
    specifications = {
        specification.specification_id: specification for specification in contract.materialization_specifications
    }
    selected_candidate = candidates.get(satisfaction.candidate_id) if satisfaction.candidate_id is not None else None
    selected_specification = (
        specifications.get(satisfaction.materialization_specification_id)
        if satisfaction.materialization_specification_id is not None
        else None
    )
    selected_mechanism = _artifact_mechanism_key(satisfaction.mechanism)
    matching_specifications = {
        specification.specification_id
        for specification in contract.materialization_specifications
        if _artifact_mechanism_key(specification.profile) == selected_mechanism
    }
    locked_input_ids = {locked_input.input_id for locked_input in contract.locked_inputs}
    required_locked_input_ids = (
        set(selected_specification.locked_input_ids) if selected_specification is not None else locked_input_ids
    )
    constraint_ids = {constraint.constraint_id for constraint in contract.constraints}
    invalid = (
        manifest is None
        or satisfaction.backend != manifest.identity
        or not _backend_route_supported(requirement, satisfaction, manifest)
        or satisfaction.requirement_id != contract.requirement_id
        or (
            selected_mechanism,
            satisfaction.acquisition,
            satisfaction.timing,
        )
        not in permitted_routes
        or (contract.exact_artifact is not None and satisfaction.artifact != contract.exact_artifact)
        or (
            contract.exact_artifact is not None
            and contract.exact_artifact.digest not in facts.available_artifact_digests
        )
        or (satisfaction.candidate_id is not None and selected_candidate is None)
        or (bool(candidate_ids) and satisfaction.candidate_id is None)
        or (not candidate_ids and satisfaction.candidate_id is not None)
        or (
            selected_candidate is not None
            and (
                satisfaction.artifact != selected_candidate.artifact
                or selected_candidate.candidate_id not in facts.available_candidate_ids
            )
        )
        or (satisfaction.materialization_specification_id is not None and selected_specification is None)
        or (
            selected_specification is not None
            and _artifact_mechanism_key(selected_specification.profile) != selected_mechanism
        )
        or (selected_specification is None and satisfaction.materialization_specification_digest is not None)
        or (
            selected_specification is not None
            and satisfaction.materialization_specification_digest != selected_specification.digest
        )
        or (
            selected_specification is not None
            and selected_specification.digest not in facts.available_materialization_specification_digests
        )
        or (bool(matching_specifications) and satisfaction.materialization_specification_id is None)
        or set(satisfaction.locked_input_ids) != required_locked_input_ids
        or not required_locked_input_ids.issubset(facts.verified_locked_input_ids)
        or set(satisfaction.satisfied_constraint_ids) != constraint_ids
        or not constraint_ids.issubset(facts.satisfied_constraint_ids)
        or not _trust_claims_verified(contract, satisfaction, facts)
    )
    if invalid:
        return _silent_approximation_diagnostic(requirement), None
    honoured = contract.explicitness is ExplicitnessClass.EXACT and contract.exact_artifact == satisfaction.artifact
    return None, RealizationProvenanceEntry(
        address=requirement.address,
        field_path=requirement.field_path,
        domain=requirement.domain,
        requirement_kind=requirement.requirement_kind,
        explicitness=requirement.explicitness,
        provenance=(requirement.provenance if honoured else ExplicitnessProvenance.BACKEND_REALIZED),
        governing_scope=requirement.governing_scope,
        artifact_satisfaction=satisfaction,
    )


def _artifact_diagnostic(
    requirement: CompiledRealizationRequirement,
    code: str,
    reason: str,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        domain=requirement.domain,
        address=requirement.address,
        message=(
            f"{reason} Requirement '{requirement.requirement_kind}' at '{requirement.field_path}' cannot be admitted."
        ),
        severity=Severity.ERROR,
    )


def _artifact_mechanism_key(
    mechanism: ArtifactMechanismProfile,
) -> tuple[str, str, str, str]:
    return (
        mechanism.mechanism,
        mechanism.profile,
        mechanism.version,
        mechanism.digest,
    )


def _backend_route_supported(
    requirement: CompiledRealizationRequirement,
    satisfaction: ArtifactSatisfactionDisclosureModel,
    manifest: BackendManifest,
) -> bool:
    selected = (
        _artifact_mechanism_key(satisfaction.mechanism),
        satisfaction.acquisition,
        satisfaction.timing,
    )
    return any(
        selected
        == (
            _artifact_mechanism_key(capability.mechanism),
            route.acquisition,
            route.timing,
        )
        for declaration in manifest.realization_support
        if declaration.domain == requirement.domain
        for capability in declaration.artifact_mechanisms
        if requirement.requirement_kind in capability.supported_requirement_kinds
        for route in capability.supported_routes
    )


def _trust_claims_verified(
    contract: ArtifactRequirement,
    satisfaction: ArtifactSatisfactionDisclosureModel,
    facts: ArtifactRequirementAvailability,
) -> bool:
    required_admission_refs = {
        *contract.trust_policy_refs,
        *(locked_input.trust_policy_ref for locked_input in contract.locked_inputs),
    }
    required_evidence_refs = {
        *contract.associated_artifact_manifest_refs,
        *(locked_input.associated_artifact_manifest_ref for locked_input in contract.locked_inputs),
    }
    disclosed_integrity = set(satisfaction.integrity_refs)
    disclosed_authenticity = set(satisfaction.authenticity_refs)
    disclosed_admission = set(satisfaction.admission_refs)
    disclosed_provenance = set(satisfaction.provenance_refs)
    disclosed_evidence = set(satisfaction.evidence_refs)
    return (
        satisfaction.artifact.digest in disclosed_integrity
        and disclosed_integrity.issubset(facts.verified_integrity_refs)
        and disclosed_authenticity.issubset(facts.verified_authenticity_refs)
        and required_admission_refs.issubset(disclosed_admission)
        and disclosed_admission.issubset(facts.verified_admission_refs)
        and disclosed_provenance.issubset(facts.verified_provenance_refs)
        and required_evidence_refs.issubset(disclosed_evidence)
        and disclosed_evidence.issubset(facts.verified_evidence_refs)
    )


def _silent_approximation_diagnostic(
    requirement: CompiledRealizationRequirement,
) -> Diagnostic:
    return Diagnostic(
        code=_BACKEND_CONTRACT_INVALID,
        domain=requirement.domain,
        address=requirement.address,
        message=(
            f"Backend did not realize the exact '{requirement.requirement_kind}' requirement at "
            f"'{requirement.field_path}' as the author declared it (the realized value is absent "
            "or differs); silent approximation or omission of an exact declaration is forbidden "
            "(SEM-218 I2)."
        ),
        severity=Severity.ERROR,
    )


__all__ = [
    "artifact_requirement_diagnostics",
    "evaluate_artifact_realization",
]
