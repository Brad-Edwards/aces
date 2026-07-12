"""Outcome-interpretation validation and the public participant-behavior violation iterators."""

from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from aces_contracts.participant_behavior import ParticipantBehaviorHistoryEventType, ParticipantObservationStatus

from .behavior_anchor_checks import (
    _contract_sem215_source_bindings,
    _contract_sem215_target_bindings,
    _outcome_source_layer_requires_provenance,
    _participant_behavior_action_result_ref_authorization_violations_for_events,
    _participant_behavior_address_violations,
    _participant_behavior_detail_shape_violations_for_events,
    _participant_behavior_observation_visibility_violations,
    _participant_behavior_temporal_contract_violations,
    _participant_behavior_transition_anchor_violations,
)
from .behavior_grounding_checks import _participant_behavior_outcome_event_grounding_violations
from .behavior_resources import (
    _PARTICIPANT_TERMINAL_OBSERVATION_STATUSES,
    ParticipantObservationBoundaryRuntime,
    ParticipantOutcomeInterpretationRuleRuntime,
)
from .history_event import ParticipantBehaviorHistoryEvent
from .outcome import ParticipantOutcomeInterpretationRecord
from .resources import (
    _PARTICIPANT_BEHAVIOR_HISTORY_KEY,
    ParticipantActionContractRuntime,
    _as_string_set,
    _contract_uses_sem211_action_results,
    validate_participant_action_result_contract,
)


def validate_participant_outcome_interpretation_record(
    record: ParticipantOutcomeInterpretationRecord,
    rule: ParticipantOutcomeInterpretationRuleRuntime,
) -> list[str]:
    """Return SEM-215 rule-conformance violations for a runtime interpretation."""

    violations: list[str] = []
    declared_sources = _contract_sem215_source_bindings(rule)
    declared_targets = _contract_sem215_target_bindings(rule)
    reported_sources: set[tuple[str, str]] = set()
    for source in record.source_bindings:
        source_key = (source.source_id, source.source_layer.value)
        reported_sources.add(source_key)
        if source_key not in declared_sources:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"is not declared by {rule.address}"
            )
            continue
        declared_refs = declared_sources[source_key]
        if source.ref != declared_refs["ref"]:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"ref {source.ref!r} does not match declared ref {declared_refs['ref']!r}"
            )
        for ref in sorted(set(source.evidence_refs) - declared_refs["evidence_refs"]):
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"reports undeclared evidence_ref {ref!r}"
            )
        for ref in sorted(set(source.provenance_refs) - declared_refs["provenance_refs"]):
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"reports undeclared provenance_ref {ref!r}"
            )
        for ref in sorted(declared_refs["provenance_refs"] - set(source.provenance_refs)):
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"omits declared provenance_ref {ref!r}"
            )
    for source_id, source_layer in sorted(declared_sources):
        if not _outcome_source_layer_requires_provenance(source_layer):
            continue
        if (source_id, source_layer) not in reported_sources:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source_id!r} "
                f"with provenance-required layer {source_layer!r} is not reported"
            )
    for target in record.target_bindings:
        target_key = (target.target_id, target.target_layer.value)
        if target_key not in declared_targets:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                f"is not declared by {rule.address}"
            )
            continue
        declared_refs = declared_targets[target_key]
        if target.ref != declared_refs["ref"]:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                f"ref {target.ref!r} does not match declared ref {declared_refs['ref']!r}"
            )
        if target.governance_ref != declared_refs["governance_ref"]:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                f"governance_ref {target.governance_ref!r} does not match declared governance_ref "
                f"{declared_refs['governance_ref']!r}"
            )
        for ref in sorted(set(target.evidence_refs) - declared_refs["evidence_refs"]):
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                f"reports undeclared evidence_ref {ref!r}"
            )
        if declared_refs["limitations"] and not set(target.limitations) <= declared_refs["limitations"]:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                "reports limitations outside the declared rule"
            )
    declared_rule_evidence_refs = _as_string_set(rule.spec.get("evidence_refs", ()))
    for ref in sorted(set(record.evidence_refs) - declared_rule_evidence_refs):
        violations.append(
            f"outcome interpretation {record.interpretation_id!r} reports undeclared evidence_ref {ref!r}"
        )
    return violations


def _participant_behavior_outcome_interpretation_rule_violations(
    events: Iterable[ParticipantBehaviorHistoryEvent],
    *,
    outcome_interpretation_rules: Mapping[str, ParticipantOutcomeInterpretationRuleRuntime],
) -> Iterator[tuple[str, str]]:
    for index, event in enumerate(events):
        if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            continue
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        for record in event.outcome_interpretations:
            rule = outcome_interpretation_rules.get(record.rule_address)
            if rule is None:
                yield (
                    locator,
                    (
                        f"outcome interpretation {record.interpretation_id!r} references unknown "
                        f"rule_address {record.rule_address!r}"
                    ),
                )
                continue
            for violation in validate_participant_outcome_interpretation_record(record, rule):
                yield (locator, violation)


def _participant_behavior_action_result_contract_violations(
    events: Iterable[ParticipantBehaviorHistoryEvent],
    *,
    action_contracts: Mapping[str, ParticipantActionContractRuntime],
) -> Iterator[tuple[str, str]]:
    for index, event in enumerate(events):
        if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            continue
        if event.observation_status not in _PARTICIPANT_TERMINAL_OBSERVATION_STATUSES:
            continue
        action_contract_address = event.action_contract_address or ""
        contract = action_contracts.get(action_contract_address)
        if contract is None or not _contract_uses_sem211_action_results(contract):
            continue
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        if event.action_result is None:
            yield (
                locator,
                f"terminal observation must carry SEM-211 action_result for {action_contract_address}",
            )
            continue
        for violation in validate_participant_action_result_contract(event.action_result, contract):
            yield (locator, violation)


def _normalize_participant_behavior_events(
    participant_behavior_history: list[Any],
    *,
    action_contract_addresses: set[str] | frozenset[str] | None,
    observation_boundary_addresses: set[str] | frozenset[str] | None,
    expected_participant_address: str | None = None,
) -> tuple[list[ParticipantBehaviorHistoryEvent], list[tuple[str, str]]]:
    normalized_events: list[ParticipantBehaviorHistoryEvent] = []
    violations: list[tuple[str, str]] = []
    for index, event in enumerate(participant_behavior_history):
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        if not isinstance(event, Mapping):
            violations.append((locator, "participant behavior history event must be a mapping"))
            continue
        try:
            normalized = ParticipantBehaviorHistoryEvent.from_payload(event)
        except (TypeError, ValueError) as exc:
            violations.append((locator, f"participant behavior history event is invalid: {exc}"))
            continue
        if expected_participant_address is not None and normalized.participant_address != expected_participant_address:
            violations.append(
                (
                    locator,
                    (
                        f"participant behavior history event outer key {expected_participant_address!r} "
                        f"does not match inner participant_address {normalized.participant_address!r}"
                    ),
                )
            )
            continue
        violations.extend(
            _participant_behavior_address_violations(
                normalized,
                locator=locator,
                action_contract_addresses=action_contract_addresses,
                observation_boundary_addresses=observation_boundary_addresses,
            )
        )
        normalized_events.append(normalized)
    return normalized_events, violations


def _participant_behavior_events_by_action_instance(
    events: list[ParticipantBehaviorHistoryEvent],
) -> dict[str, list[ParticipantBehaviorHistoryEvent]]:
    events_by_action_instance: dict[str, list[ParticipantBehaviorHistoryEvent]] = {}
    for event in events:
        events_by_action_instance.setdefault(event.action_instance_id, []).append(event)
    return events_by_action_instance


def _participant_behavior_action_instance_violation(
    action_instance_id: str,
    events: list[ParticipantBehaviorHistoryEvent],
) -> tuple[str, str] | None:
    attempts = [event for event in events if event.event_type == ParticipantBehaviorHistoryEventType.ACTION_ATTEMPTED]
    observations = [
        event
        for event in events
        if event.event_type == ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED
        and event.observation_status in _PARTICIPANT_TERMINAL_OBSERVATION_STATUSES
    ]
    transitions = [
        event for event in events if event.event_type == ParticipantBehaviorHistoryEventType.STATE_TRANSITION_RECORDED
    ]

    if len(attempts) > 1:
        return (action_instance_id, "participant action instance may only have one action_attempted event")
    if len(attempts) == 0:
        return (action_instance_id, "participant behavior events require a matching action_attempted event")
    if len(observations) != 1:
        return (
            action_instance_id,
            "participant action instance requires exactly one terminal observation or orphaned-action observation",
        )
    observation = observations[0]
    if observation.observation_status == ParticipantObservationStatus.ORPHANED_ACTION:
        return None
    if len(transitions) != 1:
        return (action_instance_id, "participant action instance requires exactly one state transition")
    if observation.post_state_digest != transitions[0].post_state_digest:
        return (
            action_instance_id,
            "terminal observation post_state_digest must match the state transition post_state_digest",
        )
    return None


def _participant_behavior_action_instance_violations(
    events: list[ParticipantBehaviorHistoryEvent],
) -> Iterator[tuple[str, str]]:
    for action_instance_id, grouped_events in _participant_behavior_events_by_action_instance(events).items():
        violation = _participant_behavior_action_instance_violation(action_instance_id, grouped_events)
        if violation is not None:
            yield violation


def _participant_behavior_joint_action_order_violations(
    events: Iterable[ParticipantBehaviorHistoryEvent],
) -> Iterator[tuple[str, str]]:
    attempts_by_joint_set: dict[str, list[ParticipantBehaviorHistoryEvent]] = {}
    for event in events:
        if (
            event.event_type == ParticipantBehaviorHistoryEventType.ACTION_ATTEMPTED
            and event.joint_action_set_id is not None
        ):
            attempts_by_joint_set.setdefault(event.joint_action_set_id, []).append(event)

    for joint_action_set_id, attempts in sorted(attempts_by_joint_set.items()):
        attempts_by_order: dict[int, list[ParticipantBehaviorHistoryEvent]] = {}
        for event in attempts:
            if event.realized_order is None:
                continue
            attempts_by_order.setdefault(event.realized_order, []).append(event)
        for realized_order, duplicate_attempts in sorted(attempts_by_order.items()):
            if len(duplicate_attempts) <= 1:
                continue
            instances = ", ".join(
                sorted(f"{event.participant_address}/{event.action_instance_id}" for event in duplicate_attempts)
            )
            yield (
                f"joint-action-set.{joint_action_set_id}",
                (
                    f"joint action set realized_order {realized_order} is assigned to "
                    f"multiple action_attempted events: {instances}"
                ),
            )


def iter_participant_behavior_history_violations(
    participant_behavior_history: Any,
    *,
    action_contract_addresses: set[str] | frozenset[str] | None = None,
    action_contracts: Mapping[str, ParticipantActionContractRuntime] | None = None,
    outcome_interpretation_rules: Mapping[str, ParticipantOutcomeInterpretationRuleRuntime] | None = None,
    observation_boundary_addresses: set[str] | frozenset[str] | None = None,
    observation_boundaries: Mapping[str, ParticipantObservationBoundaryRuntime] | None = None,
    participant_episode_history: Any = None,
    expected_participant_address: str | None = None,
) -> Iterator[tuple[str, str]]:
    """Yield every SEM-208 behavior-history invariant violation.

    The helper checks that each action instance has one terminal observation
    paired with the state transition digest it reports. When compiled address
    sets are provided, it also rejects references outside those sets. When
    compiled observation boundaries are provided, SEM-210 observation details
    and SEM-211 action-result references are checked against the time-indexed
    participant view relation.
    """

    if not isinstance(participant_behavior_history, list):
        yield (_PARTICIPANT_BEHAVIOR_HISTORY_KEY, "participant behavior history must be a list of events")
        return
    if action_contracts is not None and action_contract_addresses is None:
        action_contract_addresses = frozenset(action_contracts.keys())
    if observation_boundaries is not None and observation_boundary_addresses is None:
        observation_boundary_addresses = frozenset(observation_boundaries.keys())

    normalized_events, entry_violations = _normalize_participant_behavior_events(
        participant_behavior_history,
        action_contract_addresses=action_contract_addresses,
        observation_boundary_addresses=observation_boundary_addresses,
        expected_participant_address=expected_participant_address,
    )
    if entry_violations:
        yield from entry_violations
        return

    yield from _participant_behavior_detail_shape_violations_for_events(normalized_events)
    yield from _participant_behavior_action_instance_violations(normalized_events)
    yield from _participant_behavior_joint_action_order_violations(normalized_events)
    yield from _participant_behavior_outcome_event_grounding_violations(
        normalized_events,
        participant_episode_history=participant_episode_history,
    )
    if action_contracts is not None:
        yield from _participant_behavior_action_result_contract_violations(
            normalized_events,
            action_contracts=action_contracts,
        )
        yield from _participant_behavior_temporal_contract_violations(
            normalized_events,
            action_contracts=action_contracts,
        )
    if outcome_interpretation_rules is not None:
        yield from _participant_behavior_outcome_interpretation_rule_violations(
            normalized_events,
            outcome_interpretation_rules=outcome_interpretation_rules,
        )
    if observation_boundaries is not None:
        yield from _participant_behavior_transition_anchor_violations(
            normalized_events,
            observation_boundaries=observation_boundaries,
            participant_episode_history=participant_episode_history,
        )
        yield from _participant_behavior_observation_visibility_violations(
            normalized_events,
            observation_boundaries=observation_boundaries,
        )
        yield from _participant_behavior_action_result_ref_authorization_violations_for_events(
            normalized_events,
            observation_boundaries=observation_boundaries,
        )


def iter_participant_behavior_joint_action_violations(
    participant_behavior_history_by_participant: Any,
) -> Iterator[tuple[str, str]]:
    """Yield SEM-209 joint-action ordering violations across participant histories."""

    if not isinstance(participant_behavior_history_by_participant, Mapping):
        yield (_PARTICIPANT_BEHAVIOR_HISTORY_KEY, "participant behavior histories must be a mapping")
        return

    normalized_events: list[ParticipantBehaviorHistoryEvent] = []
    for history in participant_behavior_history_by_participant.values():
        if not isinstance(history, list):
            continue
        participant_events, entry_violations = _normalize_participant_behavior_events(
            history,
            action_contract_addresses=None,
            observation_boundary_addresses=None,
        )
        if entry_violations:
            continue
        normalized_events.extend(participant_events)

    yield from _participant_behavior_joint_action_order_violations(normalized_events)
