"""Neutral participant implementation binding DTOs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .contracts import (
    ParticipantActionResultModel,
    ParticipantBehaviorHistoryEventModel,
    ParticipantImplementationManifestModel,
    ParticipantImplementationSelectionModel,
    ParticipantObservationDetailsModel,
)
from .participant_behavior import (
    ParticipantAdmissionDisposition,
    ParticipantBehaviorHistoryEventType,
    ParticipantObservationStatus,
    ParticipantPhaseRealization,
    ParticipantRuntimeLifecyclePhase,
)

_ACTION_CONTRACT_PREFIX = "participant.action-contract."
_OBSERVATION_BOUNDARY_PREFIX = "participant.observation-boundary."


@dataclass(frozen=True)
class ParticipantActionAdmissionRequest:
    """Backend-neutral request to admit one compiled participant action."""

    participant_address: str
    action_contract_address: str
    observation_boundary_address: str
    action_instance_id: str
    implementation_manifest: ParticipantImplementationManifestModel
    implementation_selection: ParticipantImplementationSelectionModel
    evidence_refs: tuple[str, ...] = ()
    visible_refs: tuple[str, ...] = ()
    disclosed_refs: tuple[str, ...] = ()
    observation_boundary_evidence_refs: tuple[str, ...] = ()
    action_result: ParticipantActionResultModel | None = None
    state_transition_kind: str = "participant_action_admitted"
    post_state_digest: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.participant_address, "participant_address")
        _require_prefixed(
            self.action_contract_address,
            _ACTION_CONTRACT_PREFIX,
            "action_contract_address",
        )
        _require_prefixed(
            self.observation_boundary_address,
            _OBSERVATION_BOUNDARY_PREFIX,
            "observation_boundary_address",
        )
        _require_non_empty(self.action_instance_id, "action_instance_id")
        _require_non_empty(self.state_transition_kind, "state_transition_kind")
        if self.post_state_digest is not None:
            _require_non_empty(self.post_state_digest, "post_state_digest")
        if not isinstance(self.implementation_manifest, ParticipantImplementationManifestModel):
            raise TypeError("implementation_manifest must be a ParticipantImplementationManifestModel")
        if not isinstance(self.implementation_selection, ParticipantImplementationSelectionModel):
            raise TypeError("implementation_selection must be a ParticipantImplementationSelectionModel")
        if self.action_result is not None and not isinstance(self.action_result, ParticipantActionResultModel):
            raise TypeError("action_result must be a ParticipantActionResultModel or None")
        object.__setattr__(self, "evidence_refs", _string_tuple(self.evidence_refs, "evidence_refs"))
        object.__setattr__(self, "visible_refs", _string_tuple(self.visible_refs, "visible_refs"))
        object.__setattr__(self, "disclosed_refs", _string_tuple(self.disclosed_refs, "disclosed_refs"))
        object.__setattr__(
            self,
            "observation_boundary_evidence_refs",
            _string_tuple(self.observation_boundary_evidence_refs, "observation_boundary_evidence_refs"),
        )
        violations = participant_action_admission_request_violations(self)
        if violations:
            raise ValueError(violations[0])


def participant_implementation_actor_provenance(selection: ParticipantImplementationSelectionModel) -> str:
    """Return the portable actor provenance ref for a selected implementation."""

    identity = selection.implementation_identity
    return f"participant-implementation:{identity.name}@{identity.version}"


def participant_action_admission_request_violations(
    request: ParticipantActionAdmissionRequest,
) -> tuple[str, ...]:
    """Return manifest/selection compatibility violations for a binding request."""

    return (
        *_implementation_selection_violations(request),
        *_exposure_policy_violations(request),
        *_action_result_violations(request),
    )


def _implementation_selection_violations(request: ParticipantActionAdmissionRequest) -> tuple[str, ...]:
    violations: list[str] = []
    manifest = request.implementation_manifest
    selection = request.implementation_selection
    if selection.participant_address != request.participant_address:
        violations.append(
            "implementation selection participant_address must match the compiled participant behavior address"
        )
    if manifest.identity.model_dump(mode="json") != selection.implementation_identity.model_dump(mode="json"):
        violations.append("implementation selection identity must match the participant implementation manifest")
    unsupported_contracts = sorted(
        set(selection.participant_contract_versions) - set(manifest.capabilities.supported_participant_contracts)
    )
    if unsupported_contracts:
        violations.append(
            "implementation selection declares participant contracts unsupported by the manifest: "
            + ", ".join(unsupported_contracts)
        )
    if selection.selected_decision_surface_mode not in manifest.capabilities.supported_decision_surface_modes:
        violations.append("selected decision-surface mode is not supported by the participant implementation manifest")
    unsupported_policies = sorted(
        set(selection.exposure_policy.exposure_policy_kinds) - set(manifest.capabilities.exposure_policy_kinds)
    )
    if unsupported_policies:
        violations.append(
            "implementation exposure policy uses kinds unsupported by the manifest: " + ", ".join(unsupported_policies)
        )
    return tuple(violations)


def _exposure_policy_violations(request: ParticipantActionAdmissionRequest) -> tuple[str, ...]:
    violations: list[str] = []
    policy = request.implementation_selection.exposure_policy
    action_result_evidence_refs = _action_result_evidence_refs(request.action_result)
    observation_evidence_refs = set(request.evidence_refs) | action_result_evidence_refs
    emitted_refs = set(request.visible_refs) | set(request.disclosed_refs) | observation_evidence_refs
    withheld_refs = sorted(emitted_refs & set(policy.withheld_refs))
    if withheld_refs:
        violations.append(
            "participant binding refs must not include exposure policy withheld_refs: " + ", ".join(withheld_refs)
        )
    visible_allowed_refs = set(policy.disclosed_refs) | set(policy.visibility_scope_refs)
    unauthorized_visible_refs = sorted(set(request.visible_refs) - visible_allowed_refs)
    if unauthorized_visible_refs:
        violations.append(
            "visible_refs must be declared by exposure policy disclosed_refs or visibility_scope_refs: "
            + ", ".join(unauthorized_visible_refs)
        )
    unauthorized_disclosed_refs = sorted(set(request.disclosed_refs) - set(policy.disclosed_refs))
    if unauthorized_disclosed_refs:
        violations.append(
            "disclosed_refs must be declared by exposure policy disclosed_refs: "
            + ", ".join(unauthorized_disclosed_refs)
        )
    unauthorized_evidence_refs = sorted(observation_evidence_refs - set(request.observation_boundary_evidence_refs))
    if unauthorized_evidence_refs:
        violations.append(
            "evidence_refs must be declared by the compiled observation boundary: "
            + ", ".join(unauthorized_evidence_refs)
        )
    return tuple(violations)


def _action_result_violations(request: ParticipantActionAdmissionRequest) -> tuple[str, ...]:
    violations: list[str] = []
    action_result = request.action_result
    if action_result is None:
        return ()
    if action_result.participant_address != request.participant_address:
        violations.append("action_result participant_address must match the binding participant_address")
    if action_result.action_instance_id != request.action_instance_id:
        violations.append("action_result action_instance_id must match the binding action_instance_id")
    if action_result.action_contract_address != request.action_contract_address:
        violations.append("action_result action_contract_address must match the binding action_contract_address")
    return tuple(violations)


def _action_result_evidence_refs(action_result: ParticipantActionResultModel | None) -> set[str]:
    if action_result is None:
        return set()
    evidence_refs = set(action_result.evidence_refs)
    for precondition in action_result.preconditions:
        evidence_refs.update(precondition.evidence_refs)
    for effect in action_result.effects:
        evidence_refs.update(effect.evidence_refs)
    return evidence_refs


def participant_action_binding_events(
    request: ParticipantActionAdmissionRequest,
    *,
    episode_id: str,
    timestamp: str,
    post_state_digest: str,
) -> tuple[ParticipantBehaviorHistoryEventModel, ...]:
    """Build the portable behavior-history events for an admitted action."""

    actor_provenance = participant_implementation_actor_provenance(request.implementation_selection)
    return (
        ParticipantBehaviorHistoryEventModel(
            event_type=ParticipantBehaviorHistoryEventType.ACTION_ATTEMPTED,
            timestamp=timestamp,
            participant_address=request.participant_address,
            episode_id=episode_id,
            action_instance_id=request.action_instance_id,
            action_contract_address=request.action_contract_address,
            actor_provenance=actor_provenance,
            lifecycle_phase=ParticipantRuntimeLifecyclePhase.SELECTION_OR_ADMISSION,
            phase_realization=ParticipantPhaseRealization.RUNTIME_MEDIATED,
            admission_disposition=ParticipantAdmissionDisposition.ADMITTED,
        ),
        ParticipantBehaviorHistoryEventModel(
            event_type=ParticipantBehaviorHistoryEventType.STATE_TRANSITION_RECORDED,
            timestamp=timestamp,
            participant_address=request.participant_address,
            episode_id=episode_id,
            action_instance_id=request.action_instance_id,
            action_contract_address=request.action_contract_address,
            lifecycle_phase=ParticipantRuntimeLifecyclePhase.STATE_UPDATE_COMMIT,
            phase_realization=ParticipantPhaseRealization.RUNTIME_MEDIATED,
            state_transition_kind=request.state_transition_kind,
            post_state_digest=post_state_digest,
        ),
        ParticipantBehaviorHistoryEventModel(
            event_type=ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED,
            timestamp=timestamp,
            participant_address=request.participant_address,
            episode_id=episode_id,
            action_instance_id=request.action_instance_id,
            action_contract_address=request.action_contract_address,
            observation_boundary_address=request.observation_boundary_address,
            observation_status=ParticipantObservationStatus.TERMINAL,
            lifecycle_phase=ParticipantRuntimeLifecyclePhase.OBSERVATION_EMISSION,
            phase_realization=ParticipantPhaseRealization.RUNTIME_MEDIATED,
            post_state_digest=post_state_digest,
            action_result=request.action_result,
            details=ParticipantObservationDetailsModel(
                visible_refs=list(request.visible_refs),
                disclosed_refs=list(request.disclosed_refs),
                evidence_refs=list(request.evidence_refs),
            ),
        ),
    )


def participant_behavior_event_payload(event: ParticipantBehaviorHistoryEventModel) -> dict[str, object]:
    """Serialize a behavior event without empty optional/default fields."""

    return event.model_dump(mode="json", exclude_none=True, exclude_defaults=True)


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{field_name} must be a non-empty string")


def _require_prefixed(value: str, prefix: str, field_name: str) -> None:
    _require_non_empty(value, field_name)
    if not value.startswith(prefix):
        raise ValueError(f"{field_name} must be a compiled {prefix.removesuffix('.')} address")


def _string_tuple(value: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise TypeError(f"{field_name} must be an iterable of strings")
    values = tuple(value)
    if any(not isinstance(item, str) or not item for item in values):
        raise TypeError(f"{field_name} entries must be non-empty strings")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} entries must be unique")
    return values


__all__ = (
    "ParticipantActionAdmissionRequest",
    "participant_action_admission_request_violations",
    "participant_action_binding_events",
    "participant_behavior_event_payload",
    "participant_implementation_actor_provenance",
)
