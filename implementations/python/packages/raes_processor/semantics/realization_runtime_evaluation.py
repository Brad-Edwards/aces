"""Runtime evaluation for registered SEM-218 realization concerns."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance
from raes.runtime_resource_limits import (
    process_resource_limit_capability_admits,
    process_resource_limit_identity_digest,
)
from raes_backend_protocols.capabilities import BackendManifest
from raes_contracts.apparatus import (
    DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND,
    ProcessResourceLimitCapability,
    RealizationSupportDeclaration,
)
from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import ChangeAction, ProvisionOp
from raes_contracts.runtime_state import (
    RealizationObservationDisclosure,
    RealizationProvenanceEntry,
    RuntimeSnapshot,
)
from raes_contracts.vocabulary import (
    RealizationSupportMode,
    observation_strength_satisfies,
    verification_scope_satisfies,
)

from .realization_concerns import CONCERN_PAYLOAD_PATH, project_realization_concern
from .realization_process_limits import bound_process_resource_limit_capabilities
from .realization_snapshot_sanitization import invalid_observation_diagnostic

if TYPE_CHECKING:
    from .realization import CompiledRealizationRequirement

_BACKEND_CONTRACT_INVALID = "runtime.backend-contract-invalid"
_MISSING_CONCERN_VALUE = object()


def evaluate_registered_realization(
    requirement: CompiledRealizationRequirement,
    declared_ops: dict[str, ProvisionOp],
    returned_snapshot: RuntimeSnapshot,
    *,
    manifest: BackendManifest | None = None,
) -> tuple[Diagnostic | None, RealizationProvenanceEntry | None]:
    """Gate one compiled requirement against its realized value."""

    path = CONCERN_PAYLOAD_PATH.get(requirement.requirement_kind)
    op = declared_ops.get(requirement.address)
    if requirement.explicitness is None or path is None or op is None or op.action is ChangeAction.DELETE:
        return None, None
    snapshot_entry = returned_snapshot.entries.get(requirement.address)
    realized_value = (
        _concern_value(snapshot_entry.payload, path) if snapshot_entry is not None else _MISSING_CONCERN_VALUE
    )
    if requirement.explicitness is ExplicitnessClass.OPEN:
        return _evaluate_open_realization(requirement, realized_value, returned_snapshot, manifest)
    return _evaluate_declared_realization(
        requirement,
        _concern_value(op.payload, path),
        realized_value,
        returned_snapshot,
        manifest,
    )


def _evaluate_open_realization(
    requirement: CompiledRealizationRequirement,
    realized_value: object,
    returned_snapshot: RuntimeSnapshot,
    manifest: BackendManifest | None,
) -> tuple[Diagnostic | None, RealizationProvenanceEntry | None]:
    diagnostic: Diagnostic | None = None
    provenance: RealizationProvenanceEntry | None = None
    if realized_value is not _MISSING_CONCERN_VALUE:
        diagnostic, projection = _observed_projection(requirement, realized_value)
        if diagnostic is None:
            diagnostic = _corroboration_diagnostic(requirement, returned_snapshot, manifest)
        if diagnostic is None:
            diagnostic = _process_limit_apparatus_diagnostic(requirement, projection, manifest)
        if diagnostic is None:
            provenance = _realization_provenance_entry(requirement, False)
    return diagnostic, provenance


def _evaluate_declared_realization(
    requirement: CompiledRealizationRequirement,
    declared_value: object,
    realized_value: object,
    returned_snapshot: RuntimeSnapshot,
    manifest: BackendManifest | None,
) -> tuple[Diagnostic | None, RealizationProvenanceEntry | None]:
    if declared_value is _MISSING_CONCERN_VALUE:
        return None, None
    corroboration_diagnostic = _corroboration_diagnostic(requirement, returned_snapshot, manifest)
    if corroboration_diagnostic is not None:
        result = (corroboration_diagnostic, None)
    else:
        try:
            declared_projection = project_realization_concern(
                requirement.requirement_kind,
                declared_value,
            )
        except (TypeError, ValueError):
            declared_projection = _MISSING_CONCERN_VALUE
        diagnostic, realized_projection = _observed_projection(requirement, realized_value)
        if diagnostic is not None:
            result = (diagnostic, None)
        else:
            process_limit_diagnostic, honoured = _process_limit_realization_result(
                requirement,
                declared_projection,
                realized_projection,
                manifest,
            )
            if process_limit_diagnostic is not None:
                result = (process_limit_diagnostic, None)
            else:
                if honoured is None:
                    honoured = realized_projection == declared_projection
                if requirement.explicitness is ExplicitnessClass.EXACT and not honoured:
                    result = (_silent_approximation_diagnostic(requirement), None)
                elif realized_value is not _MISSING_CONCERN_VALUE:
                    result = (None, _realization_provenance_entry(requirement, honoured))
                else:
                    result = (None, None)
    return result


def _corroboration_diagnostic(
    requirement: CompiledRealizationRequirement,
    returned_snapshot: RuntimeSnapshot,
    manifest: BackendManifest | None,
) -> Diagnostic | None:
    """Reject exact inventory equality that lacks its declared observation basis."""

    required_scope = requirement.verification_scope
    requires_process_limit_evidence = requirement.requirement_kind == "process-resource-limits"
    if (requirement.explicitness is not ExplicitnessClass.EXACT and not requires_process_limit_evidence) or (
        required_scope is None and requirement.required_observation_strength is None
    ):
        return None
    observation = _matching_observation(requirement, returned_snapshot)
    if (
        observation is not None
        and (required_scope is None or verification_scope_satisfies(observation.verification_scope, required_scope))
        and (
            requirement.required_observation_strength is None
            or observation_strength_satisfies(
                observation.observation_strength,
                requirement.required_observation_strength,
            )
        )
        and _manifest_corroborates(requirement, observation, manifest)
    ):
        return None
    return Diagnostic(
        code=_BACKEND_CONTRACT_INVALID,
        domain=requirement.domain,
        address=requirement.address,
        message=(
            f"Backend returned no valid effective corroboration for "
            f"'{requirement.requirement_kind}' requirement at '{requirement.field_path}'; "
            "matching inventory values alone do not establish realization (SEM-218 I2)."
        ),
        severity=Severity.ERROR,
    )


def _matching_observation(
    requirement: CompiledRealizationRequirement,
    returned_snapshot: RuntimeSnapshot,
) -> RealizationObservationDisclosure | None:
    return next(
        (
            entry
            for entry in returned_snapshot.realization_observations
            if (
                entry.address,
                entry.field_path,
                entry.domain,
                entry.requirement_kind,
            )
            == (
                requirement.address,
                requirement.field_path,
                requirement.domain,
                requirement.requirement_kind,
            )
        ),
        None,
    )


def _manifest_corroborates(
    requirement: CompiledRealizationRequirement,
    observation: RealizationObservationDisclosure,
    manifest: BackendManifest | None,
) -> bool:
    if manifest is None:
        return False
    return any(
        (capability := declaration.observation_capabilities.get(requirement.requirement_kind)) is not None
        and _observation_posture_supported(requirement, declaration)
        and verification_scope_satisfies(capability.verification_scope, observation.verification_scope)
        and observation_strength_satisfies(capability.observation_strength, observation.observation_strength)
        for declaration in manifest.realization_support
        if declaration.domain == requirement.domain
    )


def _observation_posture_supported(
    requirement: CompiledRealizationRequirement,
    declaration: RealizationSupportDeclaration,
) -> bool:
    if requirement.requirement_kind != "process-resource-limits":
        supported = DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND in declaration.supported_exact_requirement_kinds
    elif requirement.explicitness is ExplicitnessClass.OPEN:
        supported = declaration.support_mode is RealizationSupportMode.OPEN_REALIZATION
    elif requirement.explicitness is ExplicitnessClass.CONSTRAINED:
        supported = requirement.requirement_kind in declaration.supported_constraint_kinds
    else:
        supported = DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND in declaration.supported_exact_requirement_kinds
    return supported


def _process_limit_declaration_supported(
    requirement: CompiledRealizationRequirement,
    declaration: RealizationSupportDeclaration,
) -> bool:
    capability = declaration.observation_capabilities.get(requirement.requirement_kind)
    return (
        _observation_posture_supported(requirement, declaration)
        and capability is not None
        and (
            requirement.verification_scope is None
            or verification_scope_satisfies(capability.verification_scope, requirement.verification_scope)
        )
        and (
            requirement.required_observation_strength is None
            or observation_strength_satisfies(
                capability.observation_strength,
                requirement.required_observation_strength,
            )
        )
    )


def _process_limit_realization_result(
    requirement: CompiledRealizationRequirement,
    declared_projection: object,
    realized_projection: object,
    manifest: BackendManifest | None,
) -> tuple[Diagnostic | None, bool | None]:
    if requirement.requirement_kind != "process-resource-limits":
        result = (None, None)
    else:
        apparatus = _process_limit_apparatus_diagnostic(requirement, realized_projection, manifest)
        if apparatus is not None:
            result = (apparatus, None)
        elif requirement.explicitness is not ExplicitnessClass.CONSTRAINED:
            result = (None, declared_projection == realized_projection)
        else:
            result = _constrained_process_limit_realization_result(
                requirement,
                declared_projection,
                realized_projection,
            )
    return result


def _process_limit_projection_maps(
    requirement: CompiledRealizationRequirement,
    declared_projection: object,
    realized_projection: object,
) -> tuple[Diagnostic | None, dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    diagnostic: Diagnostic | None = None
    declared: dict[str, dict[str, object]] = {}
    realized: dict[str, dict[str, object]] = {}
    if not isinstance(declared_projection, list) or not isinstance(realized_projection, list):
        diagnostic = _silent_approximation_diagnostic(requirement)
    else:
        try:
            declared = {
                process_resource_limit_identity_digest(item): cast(dict[str, object], item)
                for item in declared_projection
            }
            realized = {
                process_resource_limit_identity_digest(item): cast(dict[str, object], item)
                for item in realized_projection
            }
        except (TypeError, ValueError):
            diagnostic = invalid_observation_diagnostic(requirement)
        if diagnostic is None and declared.keys() != realized.keys():
            diagnostic = _silent_approximation_diagnostic(requirement)
    return diagnostic, declared, realized


def _constrained_process_limit_values_admitted(
    requirement: CompiledRealizationRequirement,
    declared: dict[str, dict[str, object]],
    realized: dict[str, dict[str, object]],
) -> tuple[bool, bool]:
    constraints = {
        (constraint.identity_digest, constraint.leaf): constraint.allowed_values
        for constraint in requirement.value_constraints
    }
    admitted = True
    exact = True
    for identity, expected in declared.items():
        actual = realized[identity]
        for leaf in ("soft", "hard"):
            expected_value = expected[leaf]
            actual_value = actual[leaf]
            allowed = constraints.get((identity, leaf))
            leaf_admitted = actual_value == expected_value if allowed is None else _strict_member(actual_value, allowed)
            admitted = admitted and leaf_admitted
            exact = exact and actual_value == expected_value
    return admitted, exact


def _constrained_process_limit_realization_result(
    requirement: CompiledRealizationRequirement,
    declared_projection: object,
    realized_projection: object,
) -> tuple[Diagnostic | None, bool | None]:
    diagnostic, declared, realized = _process_limit_projection_maps(
        requirement,
        declared_projection,
        realized_projection,
    )
    exact: bool | None = None
    if diagnostic is None:
        admitted, exact = _constrained_process_limit_values_admitted(requirement, declared, realized)
        if not admitted:
            diagnostic = _silent_approximation_diagnostic(requirement)
            exact = None
    return diagnostic, exact


def _strict_member(value: object, domain: tuple[object, ...]) -> bool:
    return any(type(value) is type(candidate) and value == candidate for candidate in domain)


def _bound_process_limit_capabilities(
    requirement: CompiledRealizationRequirement,
    manifest: BackendManifest,
) -> tuple[ProcessResourceLimitCapability, ...]:
    return tuple(
        capability
        for declaration in manifest.realization_support
        if declaration.domain == requirement.domain and _process_limit_declaration_supported(requirement, declaration)
        for capability in bound_process_resource_limit_capabilities(declaration, manifest.realization_envelope)
    )


def _process_limit_projection_admitted(
    realized_projection: list[object],
    capabilities: tuple[ProcessResourceLimitCapability, ...],
) -> bool:
    try:
        admitted = all(
            any(process_resource_limit_capability_admits(capability, item) for capability in capabilities)
            for item in realized_projection
        )
    except (TypeError, ValueError):
        admitted = False
    return admitted


def _process_limit_apparatus_diagnostic(
    requirement: CompiledRealizationRequirement,
    realized_projection: object,
    manifest: BackendManifest | None,
) -> Diagnostic | None:
    if requirement.requirement_kind != "process-resource-limits" or realized_projection is _MISSING_CONCERN_VALUE:
        diagnostic = None
    elif not isinstance(realized_projection, list) or manifest is None:
        diagnostic = _silent_approximation_diagnostic(requirement)
    else:
        capabilities = _bound_process_limit_capabilities(requirement, manifest)
        admitted = _process_limit_projection_admitted(realized_projection, capabilities)
        diagnostic = None if admitted else _silent_approximation_diagnostic(requirement)
    return diagnostic


def _observed_projection(
    requirement: CompiledRealizationRequirement,
    realized_value: object,
) -> tuple[Diagnostic | None, object]:
    if realized_value is _MISSING_CONCERN_VALUE:
        return None, _MISSING_CONCERN_VALUE
    try:
        projection = project_realization_concern(
            requirement.requirement_kind,
            realized_value,
            observed=True,
        )
    except (TypeError, ValueError):
        return invalid_observation_diagnostic(requirement), _MISSING_CONCERN_VALUE
    return None, projection


def _realization_provenance_entry(
    requirement: CompiledRealizationRequirement,
    honoured: bool,
) -> RealizationProvenanceEntry:
    return RealizationProvenanceEntry(
        address=requirement.address,
        field_path=requirement.field_path,
        domain=requirement.domain,
        requirement_kind=requirement.requirement_kind,
        explicitness=requirement.explicitness,
        provenance=(requirement.provenance if honoured else ExplicitnessProvenance.BACKEND_REALIZED),
        governing_scope=requirement.governing_scope,
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
            f"or differs); silent approximation or omission of an exact declaration is forbidden "
            f"(SEM-218 I2)."
        ),
        severity=Severity.ERROR,
    )


def _concern_value(payload: dict[str, object], path: tuple[str, ...]) -> object:
    current: object = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return _MISSING_CONCERN_VALUE
        current = current[key]
    return current


__all__ = ["evaluate_registered_realization"]
