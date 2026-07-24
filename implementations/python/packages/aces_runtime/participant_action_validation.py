"""Fail-closed validation for autonomous participant action commits."""

from dataclasses import replace

from aces_contracts.contracts import ParticipantBehaviorHistoryEventModel
from aces_contracts.participant_binding import (
    ParticipantActionApplyResult,
    participant_action_admission_request_violations,
    participant_implementation_actor_provenance,
)
from aces_contracts.runtime_state import RuntimeSnapshot

_TERMINAL_ACTION_STATUSES = frozenset({"succeeded", "failed", "partial_success", "rejected", "withheld"})


def autonomous_action_result_violation(
    request: object,
    result: object,
    *,
    episode_id: str,
    predecessor: RuntimeSnapshot,
) -> str | None:
    """Return why a native result cannot be committed, or ``None``."""

    if not isinstance(result, ParticipantActionApplyResult):
        return "participant runtime did not return ParticipantActionApplyResult"
    action_result = result.action_result
    if action_result is None:
        return "participant runtime did not return a typed action outcome"
    if action_result.status not in _TERMINAL_ACTION_STATUSES:
        return "participant runtime returned a non-terminal action outcome"
    if action_result.episode_id != episode_id:
        return "participant runtime action outcome does not match the live episode"
    try:
        bound_request = replace(request, action_result=action_result)
    except (TypeError, ValueError) as exc:
        return f"participant runtime action outcome contradicts its binding: {exc}"
    violations = participant_action_admission_request_violations(bound_request)
    if violations:
        return f"participant runtime action outcome contradicts its binding: {violations[0]}"
    prior_history = predecessor.participant_behavior_history.get(bound_request.participant_address, ())
    history = result.snapshot.participant_behavior_history.get(bound_request.participant_address, ())
    if len(history) < len(prior_history) or list(history[: len(prior_history)]) != list(prior_history):
        return "participant runtime rewrote predecessor behavior history"
    appended_payloads = history[len(prior_history) :]
    appended: list[ParticipantBehaviorHistoryEventModel] = []
    for event in appended_payloads:
        try:
            appended.append(ParticipantBehaviorHistoryEventModel.model_validate(event))
        except (TypeError, ValueError) as exc:
            return f"participant runtime appended an invalid behavior history event: {exc}"
    expected_types = (
        "action_attempted",
        "state_transition_recorded",
        "observation_emitted",
    )
    if tuple(event.event_type for event in appended) != expected_types:
        return "participant runtime did not append the required ordered action history"
    expected_actor = participant_implementation_actor_provenance(bound_request.implementation_selection)
    for event in appended:
        if (
            event.participant_address != bound_request.participant_address
            or event.episode_id != episode_id
            or event.action_instance_id != bound_request.action_instance_id
            or event.action_contract_address != bound_request.action_contract_address
            or event.temporal_contexts != list(bound_request.temporal_contexts)
        ):
            return "participant runtime appended behavior history outside the bound action context"
    if appended[0].actor_provenance != expected_actor:
        return "participant runtime action history contradicts selected implementation provenance"
    observation = appended[-1]
    if (
        observation.observation_boundary_address != bound_request.observation_boundary_address
        or observation.observation_status != "terminal"
        or observation.action_result != action_result
    ):
        return "participant runtime did not commit the bound terminal observation to behavior history"
    return None
