"""Participant-behavior outcome-grounding and anchor-index violation checks."""

from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from aces_contracts.participant_behavior import ParticipantBehaviorHistoryEventType
from aces_contracts.participant_episode import ParticipantEpisodeHistoryEvent
from aces_sdl.participant_outcome_semantics import OutcomeInterpretationSourceLayer

from .behavior_ref_checks import (
    _participant_behavior_attribution_candidate_ref_violations,
    _participant_behavior_attribution_evidence_ref_violations,
)
from .behavior_resources import ParticipantObservationBoundaryRuntime
from .history_event import ParticipantBehaviorHistoryEvent
from .outcome import ParticipantOutcomeInterpretationRecord, ParticipantOutcomeSourceRecord
from .resources import _PARTICIPANT_BEHAVIOR_HISTORY_KEY, _PARTICIPANT_EPISODE_TERMINAL_EVENTS


def _participant_behavior_attribution_ref_authorization_violations(
    *,
    event: ParticipantBehaviorHistoryEvent,
    locator: str,
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for edge in event.attribution_edges:
        violations.extend(
            _participant_behavior_attribution_evidence_ref_violations(
                locator=locator,
                edge=edge,
                refs=edge.evidence_refs,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
        violations.extend(
            _participant_behavior_attribution_candidate_ref_violations(
                locator=locator,
                edge=edge,
                candidate=edge.cause_candidate,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
        violations.extend(
            _participant_behavior_attribution_candidate_ref_violations(
                locator=locator,
                edge=edge,
                candidate=edge.effect_candidate,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
    return violations


def _participant_behavior_outcome_evidence_ref_violations(
    *,
    locator: str,
    record: ParticipantOutcomeInterpretationRecord,
    refs: tuple[str, ...],
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for ref in refs:
        disposition = relation.get(ref)
        if disposition is None and ref in boundary.hidden_refs:
            disposition = "hidden"
        if ref in boundary.evidence_refs or disposition == "evidence_only":
            continue
        suffix = f": disposition {disposition!r}" if disposition is not None else ""
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} evidence_ref {ref!r} "
                    f"is not authorized evidence at effective_order {effective_order}{suffix}"
                ),
            )
        )
    return violations


def _participant_behavior_outcome_provenance_ref_violations(
    *,
    locator: str,
    record: ParticipantOutcomeInterpretationRecord,
    refs: tuple[str, ...],
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for ref in refs:
        disposition = relation.get(ref)
        if disposition is None and ref in boundary.hidden_refs:
            disposition = "hidden"
        if ref in boundary.evidence_refs or disposition in {"evidence_only", "disclosed", "observable", "discovered"}:
            continue
        if ref not in boundary.hidden_refs and disposition not in {"hidden", "concealed", "deceptive"}:
            continue
        suffix = f": disposition {disposition!r}" if disposition is not None else ""
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} provenance_ref {ref!r} "
                    f"exposes a hidden participant-boundary ref at effective_order {effective_order}{suffix}"
                ),
            )
        )
    return violations


def _participant_behavior_outcome_ref_authorization_violations(
    *,
    event: ParticipantBehaviorHistoryEvent,
    locator: str,
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for record in event.outcome_interpretations:
        violations.extend(
            _participant_behavior_outcome_evidence_ref_violations(
                locator=locator,
                record=record,
                refs=record.evidence_refs,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
        for source in record.source_bindings:
            violations.extend(
                _participant_behavior_outcome_evidence_ref_violations(
                    locator=locator,
                    record=record,
                    refs=source.evidence_refs,
                    boundary=boundary,
                    relation=relation,
                    effective_order=effective_order,
                )
            )
            violations.extend(
                _participant_behavior_outcome_provenance_ref_violations(
                    locator=locator,
                    record=record,
                    refs=source.provenance_refs,
                    boundary=boundary,
                    relation=relation,
                    effective_order=effective_order,
                )
            )
        for target in record.target_bindings:
            violations.extend(
                _participant_behavior_outcome_evidence_ref_violations(
                    locator=locator,
                    record=record,
                    refs=target.evidence_refs,
                    boundary=boundary,
                    relation=relation,
                    effective_order=effective_order,
                )
            )
    return violations


def _participant_behavior_event_evidence_refs(event: ParticipantBehaviorHistoryEvent) -> set[str]:
    evidence_refs: set[str] = set()
    detail_refs = event.details.get("evidence_refs")
    if not isinstance(detail_refs, (str, bytes, Mapping)) and isinstance(detail_refs, Iterable):
        evidence_refs.update(str(ref) for ref in detail_refs if isinstance(ref, str) and ref)
    if event.action_result is not None:
        evidence_refs.update(event.action_result.evidence_refs)
        for precondition in event.action_result.preconditions:
            evidence_refs.update(precondition.evidence_refs)
        for effect in event.action_result.effects:
            evidence_refs.update(effect.evidence_refs)
    for edge in event.attribution_edges:
        evidence_refs.update(edge.evidence_refs)
    return evidence_refs


def _participant_episode_terminal_statuses(
    participant_episode_history: Any,
) -> dict[tuple[str, str], set[str]]:
    terminal_statuses: dict[tuple[str, str], set[str]] = {}
    if isinstance(participant_episode_history, Mapping):
        histories = participant_episode_history.values()
    elif isinstance(participant_episode_history, list):
        histories = (participant_episode_history,)
    else:
        histories = ()
    for history in histories:
        if isinstance(history, (str, bytes, Mapping)) or not isinstance(history, Iterable):
            continue
        for event in history:
            if not isinstance(event, Mapping):
                continue
            try:
                normalized = ParticipantEpisodeHistoryEvent.from_payload(event)
            except (TypeError, ValueError):
                continue
            terminal_reason = _PARTICIPANT_EPISODE_TERMINAL_EVENTS.get(normalized.event_type)
            if terminal_reason is None:
                continue
            key = (normalized.participant_address, normalized.episode_id)
            terminal_statuses.setdefault(key, set()).add(terminal_reason.value)
    return terminal_statuses


def _participant_behavior_outcome_evidence_grounding_violations(
    *,
    locator: str,
    record: ParticipantOutcomeInterpretationRecord,
    owner_label: str,
    refs: tuple[str, ...],
    grounded_evidence_refs: set[str],
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    owner = f" {owner_label}" if owner_label else ""
    for ref in refs:
        if ref in grounded_evidence_refs:
            continue
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r}{owner} evidence_ref {ref!r} "
                    "is not grounded in event evidence"
                ),
            )
        )
    return violations


def _participant_behavior_outcome_action_source_grounding_violations(
    *,
    locator: str,
    event: ParticipantBehaviorHistoryEvent,
    record: ParticipantOutcomeInterpretationRecord,
    source: ParticipantOutcomeSourceRecord,
) -> list[tuple[str, str]]:
    if source.source_layer != OutcomeInterpretationSourceLayer.PARTICIPANT_ACTION_OUTCOME:
        return []
    if event.action_result is None:
        return [
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                    "uses participant_action_outcome without an action_result"
                ),
            )
        ]
    violations: list[tuple[str, str]] = []
    if source.ref != event.action_result.action_contract_address:
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                    f"ref {source.ref!r} does not match action_result action_contract_address "
                    f"{event.action_result.action_contract_address!r}"
                ),
            )
        )
    expected_status = event.action_result.status.value
    if source.observed_value != expected_status:
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                    f"observed_value {source.observed_value!r} does not match action_result status "
                    f"{expected_status!r}"
                ),
            )
        )
    return violations


def _participant_behavior_outcome_episode_status_grounding_violations(
    *,
    locator: str,
    record: ParticipantOutcomeInterpretationRecord,
    source: ParticipantOutcomeSourceRecord,
    terminal_statuses: Mapping[tuple[str, str], set[str]],
) -> list[tuple[str, str]]:
    if source.source_layer != OutcomeInterpretationSourceLayer.PARTICIPANT_EPISODE_STATUS:
        return []
    key = (record.participant_address, record.episode_id)
    statuses = terminal_statuses.get(key, set())
    if not statuses:
        return [
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                    "participant_episode_status is not grounded by a terminal participant_episode_history event"
                ),
            )
        ]
    if source.observed_value in statuses:
        return []
    expected = ", ".join(repr(status) for status in sorted(statuses))
    return [
        (
            locator,
            (
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"observed_value {source.observed_value!r} does not match participant_episode_history terminal status "
                f"{expected}"
            ),
        )
    ]


def _participant_behavior_outcome_source_grounding_violations(
    *,
    locator: str,
    event: ParticipantBehaviorHistoryEvent,
    record: ParticipantOutcomeInterpretationRecord,
    source: ParticipantOutcomeSourceRecord,
    grounded_evidence_refs: set[str],
    terminal_statuses: Mapping[tuple[str, str], set[str]],
) -> list[tuple[str, str]]:
    violations = _participant_behavior_outcome_action_source_grounding_violations(
        locator=locator,
        event=event,
        record=record,
        source=source,
    )
    violations.extend(
        _participant_behavior_outcome_episode_status_grounding_violations(
            locator=locator,
            record=record,
            source=source,
            terminal_statuses=terminal_statuses,
        )
    )
    if (
        source.source_layer == OutcomeInterpretationSourceLayer.EVIDENCE_CLAIM
        and source.ref not in grounded_evidence_refs
    ):
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} evidence_claim source "
                    f"{source.source_id!r} ref {source.ref!r} is not grounded in event evidence"
                ),
            )
        )
    violations.extend(
        _participant_behavior_outcome_evidence_grounding_violations(
            locator=locator,
            record=record,
            owner_label=f"source {source.source_id!r}",
            refs=source.evidence_refs,
            grounded_evidence_refs=grounded_evidence_refs,
        )
    )
    return violations


def _participant_behavior_outcome_event_grounding_violations(
    events: Iterable[ParticipantBehaviorHistoryEvent],
    *,
    participant_episode_history: Any = None,
) -> Iterator[tuple[str, str]]:
    terminal_statuses = _participant_episode_terminal_statuses(participant_episode_history)
    for index, event in enumerate(events):
        if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            continue
        if not event.outcome_interpretations:
            continue
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        grounded_evidence_refs = _participant_behavior_event_evidence_refs(event)
        for record in event.outcome_interpretations:
            yield from _participant_behavior_outcome_evidence_grounding_violations(
                locator=locator,
                record=record,
                owner_label="",
                refs=record.evidence_refs,
                grounded_evidence_refs=grounded_evidence_refs,
            )
            for source in record.source_bindings:
                yield from _participant_behavior_outcome_source_grounding_violations(
                    locator=locator,
                    event=event,
                    record=record,
                    source=source,
                    grounded_evidence_refs=grounded_evidence_refs,
                    terminal_statuses=terminal_statuses,
                )
            for target in record.target_bindings:
                yield from _participant_behavior_outcome_evidence_grounding_violations(
                    locator=locator,
                    record=record,
                    owner_label=f"target {target.target_id!r}",
                    refs=target.evidence_refs,
                    grounded_evidence_refs=grounded_evidence_refs,
                )


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
    if event_type == "action_attempted":
        return action_attempts.get(action_instance_id)
    if event_type == "state_transition_recorded":
        return state_transitions.get(action_instance_id)
    if event_type == "observation_emitted":
        return observations.get((action_instance_id, boundary_address))
    return None
