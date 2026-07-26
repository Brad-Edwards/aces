"""Trusted lifecycle and behavior anchors for decision-surface projection."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from raes_contracts.contracts import (
    ParticipantDecisionSurfaceBehaviorAnchorModel,
    ParticipantDecisionSurfaceEpisodeReadinessAnchorModel,
    ParticipantDecisionSurfaceModel,
    ParticipantDecisionSurfaceProjectionAnchorModel,
)
from raes_contracts.participant_behavior import ParticipantBehaviorHistoryEventType
from raes_contracts.participant_episode import (
    ParticipantEpisodeExecutionState,
    ParticipantEpisodeHistoryEvent,
    ParticipantEpisodeHistoryEventType,
    ParticipantEpisodeStatus,
    iter_participant_episode_snapshot_violations,
)
from raes_contracts.runtime_state import RuntimeSnapshot

from .behavior_history_violations import iter_participant_behavior_history_violations
from .history_event import ParticipantBehaviorHistoryEvent
from .runtime_model import RuntimeModel

if TYPE_CHECKING:
    from .decision_surface import ParticipantDecisionSurfaceProjectionInput


def _stable_projection_event_ref(event_domain: str, payload: Mapping[str, object]) -> str:
    try:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("projection anchor events must have canonically serializable payloads") from exc
    return f"participant-{event_domain}-event:sha256:{hashlib.sha256(canonical).hexdigest()}"


def _participant_episode_snapshot_context(
    runtime_snapshot: RuntimeSnapshot,
    participant_address: str,
) -> tuple[ParticipantEpisodeExecutionState, tuple[ParticipantEpisodeHistoryEvent, ...]]:
    if not isinstance(runtime_snapshot, RuntimeSnapshot):
        raise TypeError("runtime_snapshot must be a current trusted RuntimeSnapshot")
    state_payload = runtime_snapshot.participant_episode_results.get(participant_address)
    history_payloads = runtime_snapshot.participant_episode_history.get(participant_address)
    if state_payload is None or history_payloads is None:
        raise ValueError("projection anchor participant does not have current RUN-311 state and history")
    violations = tuple(
        iter_participant_episode_snapshot_violations(
            {participant_address: state_payload},
            {participant_address: history_payloads},
        )
    )
    if violations:
        raise ValueError(f"projection anchor RUN-311 snapshot is invalid: {violations[0][1]}")
    state = ParticipantEpisodeExecutionState.from_payload(state_payload)
    history = tuple(ParticipantEpisodeHistoryEvent.from_payload(payload) for payload in history_payloads)
    if not history or history[0].event_type != ParticipantEpisodeHistoryEventType.EPISODE_INITIALIZED:
        raise ValueError(
            "projection anchors require the complete participant lifecycle history from episode_initialized"
        )
    return state, history


def _current_episode_behavior_events(
    runtime_snapshot: RuntimeSnapshot,
    *,
    participant_address: str,
    episode_id: str,
) -> tuple[ParticipantBehaviorHistoryEvent, ...]:
    payloads = runtime_snapshot.participant_behavior_history.get(participant_address, [])
    events = tuple(ParticipantBehaviorHistoryEvent.from_payload(payload) for payload in payloads)
    return tuple(event for event in events if event.episode_id == episode_id)


def resolve_participant_episode_readiness_anchor(
    runtime_snapshot: RuntimeSnapshot,
    *,
    participant_address: str,
    decision_surface_order: int,
    evidence_refs: Sequence[str],
    provenance_refs: Sequence[str],
) -> ParticipantDecisionSurfaceEpisodeReadinessAnchorModel:
    """Resolve the current RUN-311 ``episode_running`` event as a trusted anchor."""

    if decision_surface_order != 0:
        raise ValueError("episode-readiness projection is always decision_surface_order zero")
    state, history = _participant_episode_snapshot_context(runtime_snapshot, participant_address)
    head = history[-1]
    if (
        state.status != ParticipantEpisodeStatus.RUNNING
        or head.event_type != ParticipantEpisodeHistoryEventType.EPISODE_RUNNING
    ):
        raise ValueError("episode-readiness projection requires the current lifecycle head to be episode_running")
    if head.participant_address != state.participant_address or head.episode_id != state.episode_id:
        raise ValueError("episode-readiness projection state and lifecycle head must identify the same episode")
    if _current_episode_behavior_events(
        runtime_snapshot,
        participant_address=participant_address,
        episode_id=state.episode_id,
    ):
        raise ValueError("episode-readiness projection requires empty current-episode behavior history")
    event_ref = _stable_projection_event_ref("episode", head.to_payload())
    return ParticipantDecisionSurfaceEpisodeReadinessAnchorModel(
        anchor_kind="episode_readiness",
        participant_address=state.participant_address,
        episode_id=state.episode_id,
        decision_surface_order=decision_surface_order,
        event_ref=event_ref,
        anchor_order=len(history) - 1,
        event_type=head.event_type.value,
        episode_sequence_number=state.sequence_number,
        evidence_refs=list(evidence_refs),
        provenance_refs=list(dict.fromkeys((*provenance_refs, event_ref))),
    )


def _resolved_behavior_decision_surface_order(
    events: Sequence[ParticipantBehaviorHistoryEvent],
    behavior_history_order: int,
) -> int:
    event = events[behavior_history_order]
    if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
        raise ValueError("behavior decision surfaces must be anchored by a terminal observation_emitted event")
    return sum(
        candidate.event_type == ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED
        for candidate in events[: behavior_history_order + 1]
    )


def resolve_participant_behavior_projection_anchor(
    runtime_snapshot: RuntimeSnapshot,
    *,
    runtime_model: RuntimeModel,
    participant_address: str,
    episode_id: str,
    decision_surface_order: int,
    behavior_history_order: int,
    evidence_refs: Sequence[str],
    provenance_refs: Sequence[str],
) -> ParticipantDecisionSurfaceBehaviorAnchorModel:
    """Resolve one exact event in the current participant/episode behavior prefix."""

    state, episode_history = _participant_episode_snapshot_context(runtime_snapshot, participant_address)
    if state.status != ParticipantEpisodeStatus.RUNNING or state.episode_id != episode_id:
        raise ValueError("behavior projection anchor must identify the current running participant episode")
    events = _current_episode_behavior_events(
        runtime_snapshot,
        participant_address=participant_address,
        episode_id=episode_id,
    )
    if behavior_history_order < 0 or behavior_history_order >= len(events):
        raise ValueError("behavior_history_order must identify an event in the current episode behavior history")
    if behavior_history_order != len(events) - 1:
        raise ValueError("behavior projection anchor must identify the exact current behavior-history prefix head")
    payloads = [event.to_payload() for event in events]
    violations = tuple(
        iter_participant_behavior_history_violations(
            payloads,
            action_contracts=runtime_model.action_contracts,
            observation_boundaries=runtime_model.observation_boundaries,
            participant_episode_history=[event.to_payload() for event in episode_history],
            expected_participant_address=participant_address,
        )
    )
    if violations:
        raise ValueError(f"projection anchor behavior history is invalid: {violations[0][1]}")
    event = events[behavior_history_order]
    resolved_decision_surface_order = _resolved_behavior_decision_surface_order(events, behavior_history_order)
    if decision_surface_order != resolved_decision_surface_order:
        raise ValueError(
            "decision_surface_order must equal the number of completed observation_emitted events in the episode"
        )
    event_ref = _stable_projection_event_ref("behavior", event.to_payload())
    return ParticipantDecisionSurfaceBehaviorAnchorModel(
        anchor_kind="behavior_event",
        participant_address=participant_address,
        episode_id=episode_id,
        decision_surface_order=decision_surface_order,
        event_ref=event_ref,
        anchor_order=behavior_history_order,
        event_type=event.event_type.value,
        action_instance_id=event.action_instance_id,
        history_prefix_length=len(events),
        evidence_refs=list(evidence_refs),
        provenance_refs=list(dict.fromkeys((*provenance_refs, event_ref))),
    )


def _validate_projection_anchor_refs(
    anchor: ParticipantDecisionSurfaceProjectionAnchorModel,
    projection: ParticipantDecisionSurfaceProjectionInput,
) -> None:
    mismatched = [
        name
        for name, anchor_value, projection_value in (
            ("participant_address", anchor.participant_address, projection.participant_address),
            ("episode_id", anchor.episode_id, projection.episode_id),
            ("decision_surface_order", anchor.decision_surface_order, projection.observation_order),
        )
        if anchor_value != projection_value
    ]
    if mismatched:
        raise ValueError("projection anchor disagrees with projection input on: " + ", ".join(mismatched))
    if not set(anchor.evidence_refs).issubset(projection.evidence_refs):
        raise ValueError("projection anchor evidence_refs must be carried by projection evidence_refs")
    if not set(anchor.provenance_refs).issubset(projection.provenance_refs):
        raise ValueError("projection anchor provenance_refs must be carried by projection provenance_refs")


def _validate_resolved_projection_anchor(
    runtime_model: RuntimeModel,
    runtime_snapshot: RuntimeSnapshot,
    history_events: Sequence[ParticipantBehaviorHistoryEvent],
    projection: ParticipantDecisionSurfaceProjectionInput,
) -> int:
    anchor = projection.projection_anchor
    if anchor is None:
        raise ValueError("projection_anchor is required for trusted anchor validation")
    _validate_projection_anchor_refs(anchor, projection)
    if isinstance(anchor, ParticipantDecisionSurfaceEpisodeReadinessAnchorModel):
        resolved = resolve_participant_episode_readiness_anchor(
            runtime_snapshot,
            participant_address=anchor.participant_address,
            decision_surface_order=anchor.decision_surface_order,
            evidence_refs=anchor.evidence_refs,
            provenance_refs=anchor.provenance_refs,
        )
        if resolved != anchor:
            raise ValueError("episode-readiness projection anchor does not match the current trusted RuntimeSnapshot")
        if history_events:
            raise ValueError("episode-readiness projection requires empty current-episode behavior history")
        return 0
    resolved = resolve_participant_behavior_projection_anchor(
        runtime_snapshot,
        runtime_model=runtime_model,
        participant_address=anchor.participant_address,
        episode_id=anchor.episode_id,
        decision_surface_order=anchor.decision_surface_order,
        behavior_history_order=anchor.anchor_order,
        evidence_refs=anchor.evidence_refs,
        provenance_refs=anchor.provenance_refs,
    )
    if resolved != anchor:
        raise ValueError("behavior projection anchor does not match the current trusted RuntimeSnapshot")
    current_prefix = _current_episode_behavior_events(
        runtime_snapshot,
        participant_address=anchor.participant_address,
        episode_id=anchor.episode_id,
    )
    if tuple(history_events) != current_prefix:
        raise ValueError("behavior projection requires the exact current behavior-history prefix")
    return anchor.anchor_order


def validate_participant_decision_surface_projection_anchor(
    runtime_snapshot: RuntimeSnapshot,
    surface: ParticipantDecisionSurfaceModel,
) -> None:
    """Reject an anchored surface that is no longer current at admission."""

    anchor = surface.projection_anchor
    if anchor is None:
        return
    if isinstance(anchor, ParticipantDecisionSurfaceEpisodeReadinessAnchorModel):
        resolved = resolve_participant_episode_readiness_anchor(
            runtime_snapshot,
            participant_address=anchor.participant_address,
            decision_surface_order=anchor.decision_surface_order,
            evidence_refs=anchor.evidence_refs,
            provenance_refs=anchor.provenance_refs,
        )
    else:
        state, _ = _participant_episode_snapshot_context(runtime_snapshot, anchor.participant_address)
        if state.status != ParticipantEpisodeStatus.RUNNING or state.episode_id != anchor.episode_id:
            raise ValueError("behavior projection anchor is outside the current running episode")
        events = _current_episode_behavior_events(
            runtime_snapshot,
            participant_address=anchor.participant_address,
            episode_id=anchor.episode_id,
        )
        if anchor.anchor_order != len(events) - 1:
            raise ValueError("behavior projection anchor is not the current behavior-history prefix head")
        event = events[anchor.anchor_order]
        resolved_decision_surface_order = _resolved_behavior_decision_surface_order(events, anchor.anchor_order)
        if anchor.decision_surface_order != resolved_decision_surface_order:
            raise ValueError("behavior projection anchor has a stale or forged decision_surface_order")
        resolved = ParticipantDecisionSurfaceBehaviorAnchorModel(
            anchor_kind="behavior_event",
            participant_address=anchor.participant_address,
            episode_id=anchor.episode_id,
            decision_surface_order=anchor.decision_surface_order,
            event_ref=_stable_projection_event_ref("behavior", event.to_payload()),
            anchor_order=anchor.anchor_order,
            event_type=event.event_type.value,
            action_instance_id=event.action_instance_id,
            history_prefix_length=len(events),
            evidence_refs=anchor.evidence_refs,
            provenance_refs=anchor.provenance_refs,
        )
    if resolved != anchor:
        raise ValueError("participant decision surface projection anchor is stale or does not resolve")
