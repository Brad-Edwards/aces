"""Time-indexed anchor lookups over participant-behavior history events."""

from collections.abc import Iterable, Mapping
from typing import Any

from aces_contracts.participant_behavior import ParticipantBehaviorHistoryEventType

from .history_event import ParticipantBehaviorHistoryEvent


def _participant_behavior_history_anchor_indexes(
    events: Iterable[ParticipantBehaviorHistoryEvent],
) -> tuple[dict[str, int], dict[str, int], dict[tuple[str, str | None], int]]:
    action_attempts: dict[str, int] = {}
    state_transitions: dict[str, int] = {}
    observations: dict[tuple[str, str | None], int] = {}
    for index, event in enumerate(events):
        if event.event_type == ParticipantBehaviorHistoryEventType.ACTION_ATTEMPTED:
            action_attempts.setdefault(event.action_instance_id, index)
        elif event.event_type == ParticipantBehaviorHistoryEventType.STATE_TRANSITION_RECORDED:
            state_transitions.setdefault(event.action_instance_id, index)
        elif event.event_type == ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            observations.setdefault((event.action_instance_id, event.observation_boundary_address), index)
    return action_attempts, state_transitions, observations


def _participant_behavior_transition_anchor_index_by_event_type(
    *,
    event_type: str,
    action_instance_id: str,
    boundary_address: str,
    action_attempts: Mapping[str, int],
    state_transitions: Mapping[str, int],
    observations: Mapping[tuple[str, str | None], int],
) -> int | None:
    if event_type == "action_attempted":
        return action_attempts.get(action_instance_id)
    if event_type == "state_transition_recorded":
        return state_transitions.get(action_instance_id)
    return observations.get((action_instance_id, boundary_address)) if event_type == "observation_emitted" else None


def _participant_behavior_transition_anchor_index(
    *,
    transition: Mapping[str, Any],
    boundary_address: str,
    action_attempts: Mapping[str, int],
    state_transitions: Mapping[str, int],
    observations: Mapping[tuple[str, str | None], int],
) -> int | None:
    event_type = str(transition.get("history_event_type", ""))
    if event_type == "episode_close":
        return None
    action_instance_id = transition.get("action_instance_id")
    if not isinstance(action_instance_id, str) or not action_instance_id:
        return None
    return _participant_behavior_transition_anchor_index_by_event_type(
        event_type=event_type,
        action_instance_id=action_instance_id,
        boundary_address=boundary_address,
        action_attempts=action_attempts,
        state_transitions=state_transitions,
        observations=observations,
    )
