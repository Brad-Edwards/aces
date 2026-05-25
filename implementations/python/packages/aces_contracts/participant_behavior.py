"""Shared participant behavior runtime contract enums."""

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


__all__ = (
    "ParticipantActionPreconditionStatus",
    "ParticipantActionResultStatus",
    "ParticipantBehaviorHistoryEventType",
    "ParticipantObservationStatus",
)
