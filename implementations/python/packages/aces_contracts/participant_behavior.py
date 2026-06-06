"""Shared participant behavior runtime contracts."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from enum import Enum


class ParticipantBehaviorHistoryEventType(str, Enum):
    """Portable history event kinds for participant behavior semantics."""

    ACTION_ATTEMPTED = "action_attempted"
    STATE_TRANSITION_RECORDED = "state_transition_recorded"
    OBSERVATION_EMITTED = "observation_emitted"


class ParticipantObservationStatus(str, Enum):
    """Terminal interpretation of a participant observation event."""

    TERMINAL = "terminal"
    ORPHANED_ACTION = "orphaned_action"


class ParticipantActionPreconditionStatus(str, Enum):
    """Runtime resolution state for one SEM-211 action precondition."""

    SATISFIED = "satisfied"
    UNSATISFIED = "unsatisfied"
    UNRESOLVED = "unresolved"


class ParticipantActionResultStatus(str, Enum):
    """Portable local status for a SEM-211 participant action attempt."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHHELD = "withheld"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    UNKNOWN = "unknown"


class ParticipantRuntimeLifecyclePhase(str, Enum):
    """RUN-306 observable participant runtime lifecycle phases."""

    INTENT_OR_PROPOSAL = "intent_or_proposal"
    SELECTION_OR_ADMISSION = "selection_or_admission"
    EXECUTION_ATTEMPT = "execution_attempt"
    OBSERVATION_EMISSION = "observation_emission"
    STATE_UPDATE_COMMIT = "state_update_commit"


class ParticipantPhaseRealization(str, Enum):
    """RUN-306 realization modes for an observable lifecycle phase."""

    OBSERVED = "observed"
    RUNTIME_MEDIATED = "runtime_mediated"
    EXTERNALLY_SUPPLIED = "externally_supplied"
    OPAQUE = "opaque"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    UNSUPPORTED = "unsupported"


class ParticipantAdmissionDisposition(str, Enum):
    """RUN-306 selection/admission disposition values."""

    ADMITTED = "admitted"
    REJECTED = "rejected"
    WITHHELD = "withheld"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class ParticipantLifecycleOperationState(str, Enum):
    """RUN-306 operation states for execution-attempt records."""

    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


_PARTICIPANT_BEHAVIOR_HISTORY_KEY = "runtime.snapshot.participant-behavior-history"
_PARTICIPANT_RUNTIME_METADATA_KEY = "runtime.snapshot.metadata"
_RESERVED_RUNTIME_STATE_KEYS = frozenset(
    {
        "participant_episode_results",
        "participant_episode_history",
        "participant_behavior_history",
    }
)
_REQUIRED_BEHAVIOR_EVENT_FIELDS = (
    "event_type",
    "timestamp",
    "participant_address",
    "episode_id",
    "action_instance_id",
)
_OPTIONAL_NON_EMPTY_STRING_FIELDS = (
    "action_contract_address",
    "observation_boundary_address",
    "actor_provenance",
    "state_transition_kind",
    "post_state_digest",
    "joint_action_set_id",
    "interaction_ref",
    "operation_ref",
)


def iter_participant_behavior_snapshot_violations(
    participant_behavior_history: object,
    *,
    participant_episode_results: object = None,
    participant_episode_history: object = None,
    metadata: object = None,
) -> Iterator[tuple[str, str]]:
    """Yield RUN-305 participant behavior-history snapshot violations.

    This is the runtime-boundary integrity check for portable behavior history.
    SEM-specific action, visibility, temporal, attribution, and outcome semantics
    remain in the richer participant-semantics validators. This helper only
    checks that behavior history is carried as a first-class snapshot stream and
    is internally addressable enough for evidential claims not to be weakened by
    malformed map keys, missing identities, unknown event kinds, or metadata
    smuggling.
    """

    yield from _iter_reserved_metadata_key_violations(metadata)
    if not isinstance(participant_behavior_history, Mapping):
        yield (_PARTICIPANT_BEHAVIOR_HISTORY_KEY, "participant_behavior_history must be a mapping")
        return

    known_episode_ids = _participant_episode_ids_by_participant(
        participant_episode_results,
        participant_episode_history,
    )
    for outer_key, history in participant_behavior_history.items():
        if not isinstance(outer_key, str) or not outer_key:
            yield (_PARTICIPANT_BEHAVIOR_HISTORY_KEY, "participant behavior history keys must be non-empty strings")
            continue
        if not isinstance(history, list):
            yield (outer_key, "participant behavior history must be a list of events")
            continue
        for index, event in enumerate(history):
            locator = f"{outer_key}[{index}]"
            if not isinstance(event, Mapping):
                yield (locator, "participant behavior history event must be a mapping")
                continue
            yield from _iter_behavior_event_shape_violations(locator, outer_key, event)
            yield from _iter_behavior_event_episode_reference_violations(locator, outer_key, event, known_episode_ids)
            yield from _iter_behavior_event_detail_smuggling_violations(locator, event)


def iter_participant_runtime_history_transition_violations(
    previous_participant_episode_history: object,
    next_participant_episode_history: object,
    previous_participant_behavior_history: object,
    next_participant_behavior_history: object,
) -> Iterator[tuple[str, str]]:
    """Yield RUN-305/RUN-311 history rewrite violations across an apply."""

    yield from _iter_append_only_history_violations(
        "participant_episode_history",
        "runtime.snapshot.participant-episode-history",
        previous_participant_episode_history,
        next_participant_episode_history,
    )
    yield from _iter_append_only_history_violations(
        "participant_behavior_history",
        _PARTICIPANT_BEHAVIOR_HISTORY_KEY,
        previous_participant_behavior_history,
        next_participant_behavior_history,
    )


def _iter_reserved_metadata_key_violations(metadata: object) -> Iterator[tuple[str, str]]:
    if metadata is None:
        return
    if not isinstance(metadata, Mapping):
        yield (_PARTICIPANT_RUNTIME_METADATA_KEY, "RuntimeSnapshot.metadata must be a mapping")
        return
    for key in sorted(_RESERVED_RUNTIME_STATE_KEYS.intersection(str(item) for item in metadata)):
        yield (
            f"{_PARTICIPANT_RUNTIME_METADATA_KEY}.{key}",
            (
                f"RuntimeSnapshot.metadata must not contain {key!r}; "
                "participant runtime state/history must use first-class snapshot fields"
            ),
        )


def _iter_append_only_history_violations(
    field_name: str,
    address_prefix: str,
    previous_history: object,
    next_history: object,
) -> Iterator[tuple[str, str]]:
    if not isinstance(previous_history, Mapping) or not isinstance(next_history, Mapping):
        return
    for participant_address, previous_events in previous_history.items():
        if not isinstance(participant_address, str) or not participant_address or not isinstance(previous_events, list):
            continue
        next_events = next_history.get(participant_address)
        participant_locator = f"{address_prefix}.{participant_address}"
        if not isinstance(next_events, list):
            yield (
                participant_locator,
                f"{field_name} must be append-only; participant {participant_address!r} history was removed",
            )
            continue
        if len(next_events) < len(previous_events):
            yield (
                participant_locator,
                (
                    f"{field_name} must be append-only; participant {participant_address!r} history shrank "
                    f"from {len(previous_events)} to {len(next_events)} events"
                ),
            )
            continue
        for index, previous_event in enumerate(previous_events):
            if next_events[index] != previous_event:
                yield (
                    f"{participant_locator}[{index}]",
                    f"{field_name} must be append-only; existing event at index {index} changed",
                )


def _iter_behavior_event_shape_violations(
    locator: str,
    outer_key: str,
    event: Mapping[object, object],
) -> Iterator[tuple[str, str]]:
    missing = [field for field in _REQUIRED_BEHAVIOR_EVENT_FIELDS if field not in event]
    if missing:
        yield (locator, "participant behavior history event is missing required fields: " + ", ".join(missing))
        return

    for field in _REQUIRED_BEHAVIOR_EVENT_FIELDS:
        value = event[field]
        if not isinstance(value, str) or not value:
            yield (locator, f"participant behavior history event field {field} must be a non-empty string")
            return

    event_type = event["event_type"]
    if event_type not in {kind.value for kind in ParticipantBehaviorHistoryEventType}:
        yield (locator, f"participant behavior history event_type {event_type!r} is not supported")

    participant_address = event["participant_address"]
    if participant_address != outer_key:
        yield (
            locator,
            (
                f"participant behavior history event outer key {outer_key!r} "
                f"does not match inner participant_address {participant_address!r}"
            ),
        )

    observation_status = event.get("observation_status")
    if observation_status is not None and observation_status not in {
        status.value for status in ParticipantObservationStatus
    }:
        yield (locator, f"participant behavior observation_status {observation_status!r} is not supported")

    for field in _OPTIONAL_NON_EMPTY_STRING_FIELDS:
        value = event.get(field)
        if value is not None and (not isinstance(value, str) or not value):
            yield (locator, f"participant behavior history event field {field} must be a non-empty string or None")

    realized_order = event.get("realized_order")
    if realized_order is not None and (
        isinstance(realized_order, bool) or not isinstance(realized_order, int) or realized_order < 0
    ):
        yield (locator, "participant behavior realized_order must be a non-negative integer or None")

    shared_state_refs = event.get("shared_state_refs", [])
    if not isinstance(shared_state_refs, list):
        yield (locator, "participant behavior shared_state_refs must be a list")
    elif any(not isinstance(ref, str) or not ref for ref in shared_state_refs):
        yield (locator, "participant behavior shared_state_refs entries must be non-empty strings")
    elif len(set(shared_state_refs)) != len(shared_state_refs):
        yield (locator, "participant behavior shared_state_refs entries must be unique")

    details = event.get("details", {})
    if not isinstance(details, Mapping):
        yield (locator, "participant behavior details must be a mapping")

    yield from _iter_behavior_event_lifecycle_violations(locator, event_type, event)


def _enum_values(enum_type: type[Enum]) -> set[str]:
    return {item.value for item in enum_type}


def _iter_optional_enum_violations(
    locator: str,
    event: Mapping[object, object],
    field: str,
    enum_type: type[Enum],
) -> Iterator[tuple[str, str]]:
    value = event.get(field)
    if value is not None and value not in _enum_values(enum_type):
        yield (locator, f"participant behavior {field} {value!r} is not supported")


def _iter_behavior_event_lifecycle_violations(
    locator: str,
    event_type: object,
    event: Mapping[object, object],
) -> Iterator[tuple[str, str]]:
    lifecycle_phase = event.get("lifecycle_phase")
    phase_realization = event.get("phase_realization")
    admission_disposition = event.get("admission_disposition")
    operation_ref = event.get("operation_ref")
    operation_state = event.get("operation_state")

    for field, enum_type in (
        ("lifecycle_phase", ParticipantRuntimeLifecyclePhase),
        ("phase_realization", ParticipantPhaseRealization),
        ("admission_disposition", ParticipantAdmissionDisposition),
        ("operation_state", ParticipantLifecycleOperationState),
    ):
        yield from _iter_optional_enum_violations(locator, event, field, enum_type)

    if lifecycle_phase is None:
        lifecycle_fields = (phase_realization, admission_disposition, operation_ref, operation_state)
        if any(value is not None for value in lifecycle_fields):
            yield (locator, "participant behavior lifecycle fields require lifecycle_phase")
        return
    if lifecycle_phase not in _enum_values(ParticipantRuntimeLifecyclePhase):
        return
    if phase_realization is None:
        yield (locator, "lifecycle_phase requires phase_realization")
    elif phase_realization not in _enum_values(ParticipantPhaseRealization):
        return

    if lifecycle_phase == ParticipantRuntimeLifecyclePhase.SELECTION_OR_ADMISSION.value:
        if admission_disposition is None:
            yield (locator, "selection_or_admission lifecycle_phase requires admission_disposition")
    elif admission_disposition is not None:
        yield (locator, "admission_disposition requires lifecycle_phase selection_or_admission")

    if operation_state is not None and lifecycle_phase != ParticipantRuntimeLifecyclePhase.EXECUTION_ATTEMPT.value:
        yield (locator, "operation_state requires lifecycle_phase execution_attempt")
    if operation_ref is not None and lifecycle_phase != ParticipantRuntimeLifecyclePhase.EXECUTION_ATTEMPT.value:
        yield (locator, "operation_ref requires lifecycle_phase execution_attempt")

    if event_type == ParticipantBehaviorHistoryEventType.ACTION_ATTEMPTED.value:
        allowed = {
            ParticipantRuntimeLifecyclePhase.INTENT_OR_PROPOSAL.value,
            ParticipantRuntimeLifecyclePhase.SELECTION_OR_ADMISSION.value,
            ParticipantRuntimeLifecyclePhase.EXECUTION_ATTEMPT.value,
        }
        if lifecycle_phase not in allowed:
            yield (
                locator,
                (
                    "action_attempted lifecycle_phase must be one of intent_or_proposal, "
                    "selection_or_admission, execution_attempt"
                ),
            )
    elif event_type == ParticipantBehaviorHistoryEventType.STATE_TRANSITION_RECORDED.value:
        if lifecycle_phase != ParticipantRuntimeLifecyclePhase.STATE_UPDATE_COMMIT.value:
            yield (locator, "state_transition_recorded lifecycle_phase must be state_update_commit")
    elif event_type == ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED.value:
        if lifecycle_phase != ParticipantRuntimeLifecyclePhase.OBSERVATION_EMISSION.value:
            yield (locator, "observation_emitted lifecycle_phase must be observation_emission")


def _iter_behavior_event_episode_reference_violations(
    locator: str,
    outer_key: str,
    event: Mapping[object, object],
    known_episode_ids: Mapping[str, set[str]],
) -> Iterator[tuple[str, str]]:
    participant_episode_ids = known_episode_ids.get(outer_key)
    episode_id = event.get("episode_id")
    if (
        participant_episode_ids
        and isinstance(episode_id, str)
        and episode_id
        and episode_id not in participant_episode_ids
    ):
        yield (
            locator,
            (
                f"participant behavior history event references episode_id {episode_id!r} "
                f"that is not present in participant episode state/history for {outer_key!r}"
            ),
        )


def _iter_behavior_event_detail_smuggling_violations(
    locator: str,
    event: Mapping[object, object],
) -> Iterator[tuple[str, str]]:
    details = event.get("details", {})
    if not isinstance(details, Mapping):
        return
    for key in sorted(_RESERVED_RUNTIME_STATE_KEYS.intersection(str(item) for item in details)):
        yield (
            f"{locator}.details.{key}",
            (
                f"participant behavior history details must not contain {key!r}; "
                "participant runtime state/history must use first-class snapshot fields"
            ),
        )


def _participant_episode_ids_by_participant(
    participant_episode_results: object,
    participant_episode_history: object,
) -> dict[str, set[str]]:
    episode_ids: dict[str, set[str]] = {}
    _collect_episode_result_ids(episode_ids, participant_episode_results)
    _collect_episode_history_ids(episode_ids, participant_episode_history)
    return episode_ids


def _collect_episode_result_ids(
    episode_ids: dict[str, set[str]],
    participant_episode_results: object,
) -> None:
    if not isinstance(participant_episode_results, Mapping):
        return
    for outer_key, result in participant_episode_results.items():
        if not isinstance(outer_key, str) or not outer_key or not isinstance(result, Mapping):
            continue
        participant_address = result.get("participant_address", outer_key)
        episode_id = result.get("episode_id")
        if participant_address == outer_key and isinstance(episode_id, str) and episode_id:
            episode_ids.setdefault(outer_key, set()).add(episode_id)


def _collect_episode_history_ids(
    episode_ids: dict[str, set[str]],
    participant_episode_history: object,
) -> None:
    if not isinstance(participant_episode_history, Mapping):
        return
    for outer_key, history in participant_episode_history.items():
        if not isinstance(outer_key, str) or not outer_key or not isinstance(history, list):
            continue
        for event in history:
            if not isinstance(event, Mapping):
                continue
            participant_address = event.get("participant_address", outer_key)
            episode_id = event.get("episode_id")
            if participant_address == outer_key and isinstance(episode_id, str) and episode_id:
                episode_ids.setdefault(outer_key, set()).add(episode_id)


__all__ = (
    "ParticipantAdmissionDisposition",
    "ParticipantActionPreconditionStatus",
    "ParticipantActionResultStatus",
    "ParticipantBehaviorHistoryEventType",
    "ParticipantLifecycleOperationState",
    "ParticipantObservationStatus",
    "ParticipantPhaseRealization",
    "ParticipantRuntimeLifecyclePhase",
    "iter_participant_behavior_snapshot_violations",
    "iter_participant_runtime_history_transition_violations",
)
