"""Runtime evaluation for registered SEM-218 realization concerns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance
from raes_backend_protocols.capabilities import BackendManifest
from raes_contracts.apparatus import DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND
from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import ChangeAction, ProvisionOp
from raes_contracts.runtime_state import RealizationProvenanceEntry, RuntimeSnapshot
from raes_contracts.vocabulary import verification_scope_satisfies

from .realization_concerns import CONCERN_PAYLOAD_PATH, project_realization_concern
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
        return _evaluate_open_realization(requirement, realized_value)
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
) -> tuple[Diagnostic | None, RealizationProvenanceEntry | None]:
    if realized_value is _MISSING_CONCERN_VALUE:
        return None, None
    diagnostic, _projection = _observed_projection(requirement, realized_value)
    if diagnostic is not None:
        return diagnostic, None
    return None, _realization_provenance_entry(requirement, False)


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
        return corroboration_diagnostic, None
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
    if requirement.explicitness is not ExplicitnessClass.EXACT or required_scope is None:
        return None
    observation = next(
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
    capability_matches = False
    if manifest is not None and observation is not None:
        capability_matches = any(
            (capability := declaration.observation_capabilities.get(requirement.requirement_kind)) is not None
            and DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND in declaration.supported_exact_requirement_kinds
            and verification_scope_satisfies(capability.verification_scope, observation.verification_scope)
            and capability.observation_strength is observation.observation_strength
            for declaration in manifest.realization_support
            if declaration.domain == requirement.domain
        )
    if (
        observation is None
        or not verification_scope_satisfies(observation.verification_scope, required_scope)
        or not capability_matches
    ):
        return Diagnostic(
            code=_BACKEND_CONTRACT_INVALID,
            domain=requirement.domain,
            address=requirement.address,
            message=(
                f"Backend returned no valid '{required_scope.value}' corroboration for exact "
                f"'{requirement.requirement_kind}' requirement at '{requirement.field_path}'; "
                "matching inventory values alone do not establish realization (SEM-218 I2)."
            ),
            severity=Severity.ERROR,
        )
    return None


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
