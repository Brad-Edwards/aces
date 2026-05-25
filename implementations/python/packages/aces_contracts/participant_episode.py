"""Shared participant episode runtime contracts."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aces_contracts.versions import PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION


class ParticipantEpisodeStatus(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    TERMINATED = "terminated"


class ParticipantEpisodeTerminalReason(str, Enum):
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    TRUNCATED = "truncated"
    INTERRUPTED = "interrupted"


class ParticipantEpisodeControlAction(str, Enum):
    INITIALIZE = "initialize"
    RESET = "reset"
    RESTART = "restart"


class ParticipantEpisodeHistoryEventType(str, Enum):
    EPISODE_INITIALIZED = "episode_initialized"
    EPISODE_RUNNING = "episode_running"
    EPISODE_COMPLETED = "episode_completed"
    EPISODE_TIMED_OUT = "episode_timed_out"
    EPISODE_TRUNCATED = "episode_truncated"
    EPISODE_INTERRUPTED = "episode_interrupted"
    EPISODE_RESET = "episode_reset"
    EPISODE_RESTARTED = "episode_restarted"


_PARTICIPANT_EPISODE_TERMINAL_EVENTS: dict[
    ParticipantEpisodeHistoryEventType,
    ParticipantEpisodeTerminalReason,
] = {
    ParticipantEpisodeHistoryEventType.EPISODE_COMPLETED: ParticipantEpisodeTerminalReason.COMPLETED,
    ParticipantEpisodeHistoryEventType.EPISODE_TIMED_OUT: ParticipantEpisodeTerminalReason.TIMED_OUT,
    ParticipantEpisodeHistoryEventType.EPISODE_TRUNCATED: ParticipantEpisodeTerminalReason.TRUNCATED,
    ParticipantEpisodeHistoryEventType.EPISODE_INTERRUPTED: ParticipantEpisodeTerminalReason.INTERRUPTED,
}


_PARTICIPANT_EPISODE_CONTROL_EVENTS: dict[
    ParticipantEpisodeHistoryEventType,
    ParticipantEpisodeControlAction,
] = {
    ParticipantEpisodeHistoryEventType.EPISODE_INITIALIZED: ParticipantEpisodeControlAction.INITIALIZE,
    ParticipantEpisodeHistoryEventType.EPISODE_RESET: ParticipantEpisodeControlAction.RESET,
    ParticipantEpisodeHistoryEventType.EPISODE_RESTARTED: ParticipantEpisodeControlAction.RESTART,
}

PARTICIPANT_EPISODE_TERMINAL_EVENTS = _PARTICIPANT_EPISODE_TERMINAL_EVENTS
PARTICIPANT_EPISODE_CONTROL_EVENTS = _PARTICIPANT_EPISODE_CONTROL_EVENTS


@dataclass(frozen=True)
class ParticipantEpisodeInitializeRequest:
    """Portable request for initializing the first episode of a participant."""

    participant_address: str
    episode_id: str | None = None


@dataclass(frozen=True)
class ParticipantEpisodeResetRequest:
    """Portable request for resetting a non-terminal participant episode."""

    participant_address: str
    episode_id: str | None = None
    reason: str = "reset by operator"


@dataclass(frozen=True)
class ParticipantEpisodeRestartRequest:
    """Portable request for restarting a terminated participant episode."""

    participant_address: str
    episode_id: str | None = None
    reason: str = "restarted by operator"


@dataclass(frozen=True)
class ParticipantEpisodeTerminateRequest:
    """Portable request for driving the current episode to ``TERMINATED``."""

    participant_address: str
    terminal_reason: ParticipantEpisodeTerminalReason = ParticipantEpisodeTerminalReason.INTERRUPTED
    detail: str = "terminated by operator"


@dataclass(frozen=True)
class ParticipantEpisodeExecutionState:
    """Internal normalized participant-episode execution state envelope."""

    state_schema_version: str = PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION
    participant_address: str = ""
    episode_id: str = ""
    sequence_number: int = 0
    status: ParticipantEpisodeStatus = ParticipantEpisodeStatus.INITIALIZING
    terminal_reason: ParticipantEpisodeTerminalReason | None = None
    initialized_at: str = ""
    updated_at: str = ""
    terminated_at: str | None = None
    last_control_action: ParticipantEpisodeControlAction = ParticipantEpisodeControlAction.INITIALIZE
    previous_episode_id: str | None = None

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> ParticipantEpisodeExecutionState:
        if not isinstance(payload, Mapping):
            raise TypeError("participant episode payload must be a mapping")
        missing_keys = [
            key
            for key in (
                "state_schema_version",
                "participant_address",
                "episode_id",
                "sequence_number",
                "status",
                "initialized_at",
                "updated_at",
                "last_control_action",
            )
            if key not in payload
        ]
        if missing_keys:
            raise ValueError("participant episode payload is missing required fields: " + ", ".join(missing_keys))
        sequence_number_raw = payload.get("sequence_number")
        if isinstance(sequence_number_raw, bool) or not isinstance(sequence_number_raw, int):
            raise TypeError("participant episode sequence_number must be an int")
        status_raw = payload.get("status")
        terminal_reason_raw = payload.get("terminal_reason")
        last_control_action_raw = payload.get("last_control_action")
        return cls(
            state_schema_version=str(payload.get("state_schema_version")),
            participant_address=str(payload.get("participant_address")),
            episode_id=str(payload.get("episode_id")),
            sequence_number=sequence_number_raw,
            status=(
                status_raw
                if isinstance(status_raw, ParticipantEpisodeStatus)
                else ParticipantEpisodeStatus(str(status_raw))
            ),
            terminal_reason=(
                terminal_reason_raw
                if isinstance(terminal_reason_raw, ParticipantEpisodeTerminalReason)
                else (
                    ParticipantEpisodeTerminalReason(str(terminal_reason_raw))
                    if terminal_reason_raw is not None
                    else None
                )
            ),
            initialized_at=str(payload.get("initialized_at")),
            updated_at=str(payload.get("updated_at")),
            terminated_at=(str(payload["terminated_at"]) if payload.get("terminated_at") is not None else None),
            last_control_action=(
                last_control_action_raw
                if isinstance(last_control_action_raw, ParticipantEpisodeControlAction)
                else ParticipantEpisodeControlAction(str(last_control_action_raw))
            ),
            previous_episode_id=(
                str(payload["previous_episode_id"]) if payload.get("previous_episode_id") is not None else None
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "state_schema_version": self.state_schema_version,
            "participant_address": self.participant_address,
            "episode_id": self.episode_id,
            "sequence_number": self.sequence_number,
            "status": self.status.value,
            "terminal_reason": self.terminal_reason.value if self.terminal_reason is not None else None,
            "initialized_at": self.initialized_at,
            "updated_at": self.updated_at,
            "terminated_at": self.terminated_at,
            "last_control_action": self.last_control_action.value,
            "previous_episode_id": self.previous_episode_id,
        }

    def __post_init__(self) -> None:
        if not isinstance(self.state_schema_version, str) or not self.state_schema_version:
            raise TypeError("participant episode state_schema_version must be a non-empty string")
        if not isinstance(self.participant_address, str) or not self.participant_address:
            raise TypeError("participant_address must be a non-empty string")
        if not isinstance(self.episode_id, str) or not self.episode_id:
            raise TypeError("episode_id must be a non-empty string")
        if isinstance(self.sequence_number, bool) or not isinstance(self.sequence_number, int):
            raise TypeError("sequence_number must be an int")
        if self.sequence_number < 0:
            raise ValueError("sequence_number must be >= 0")
        if not isinstance(self.status, ParticipantEpisodeStatus):
            raise TypeError("status must be a ParticipantEpisodeStatus")
        if self.terminal_reason is not None and not isinstance(self.terminal_reason, ParticipantEpisodeTerminalReason):
            raise TypeError("terminal_reason must be a ParticipantEpisodeTerminalReason or None")
        if not isinstance(self.initialized_at, str) or not self.initialized_at:
            raise TypeError("initialized_at must be a non-empty string")
        if not isinstance(self.updated_at, str) or not self.updated_at:
            raise TypeError("updated_at must be a non-empty string")
        if self.terminated_at is not None and (not isinstance(self.terminated_at, str) or not self.terminated_at):
            raise TypeError("terminated_at must be a non-empty string or None")
        if not isinstance(self.last_control_action, ParticipantEpisodeControlAction):
            raise TypeError("last_control_action must be a ParticipantEpisodeControlAction")
        if self.previous_episode_id is not None and (
            not isinstance(self.previous_episode_id, str) or not self.previous_episode_id
        ):
            raise TypeError("previous_episode_id must be a non-empty string or None")
        if self.status in {ParticipantEpisodeStatus.INITIALIZING, ParticipantEpisodeStatus.RUNNING}:
            if self.terminal_reason is not None:
                raise ValueError("non-terminal participant episodes may not report a terminal_reason")
            if self.terminated_at is not None:
                raise ValueError("non-terminal participant episodes may not report a terminated_at timestamp")
        if self.status == ParticipantEpisodeStatus.TERMINATED:
            if self.terminal_reason is None:
                raise ValueError("terminated participant episodes must report a terminal_reason")
            if self.terminated_at is None:
                raise ValueError("terminated participant episodes must report a terminated_at timestamp")
        if self.sequence_number == 0:
            if self.last_control_action != ParticipantEpisodeControlAction.INITIALIZE:
                raise ValueError(
                    "the first participant episode (sequence_number=0) must use the INITIALIZE control action"
                )
            if self.previous_episode_id is not None:
                raise ValueError(
                    "the first participant episode (sequence_number=0) must not link to a previous episode"
                )
        else:
            if self.last_control_action == ParticipantEpisodeControlAction.INITIALIZE:
                raise ValueError(
                    "subsequent participant episodes (sequence_number>0) must use RESET or RESTART, not INITIALIZE"
                )
            if self.previous_episode_id is None:
                raise ValueError(
                    "subsequent participant episodes (sequence_number>0) must link to a previous_episode_id"
                )
            if self.previous_episode_id == self.episode_id:
                raise ValueError("previous_episode_id must differ from episode_id; reset/restart create a new instance")


@dataclass(frozen=True)
class ParticipantEpisodeHistoryEvent:
    """Internal normalized participant-episode history event."""

    event_type: ParticipantEpisodeHistoryEventType
    timestamp: str
    participant_address: str
    episode_id: str
    sequence_number: int
    terminal_reason: ParticipantEpisodeTerminalReason | None = None
    control_action: ParticipantEpisodeControlAction | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> ParticipantEpisodeHistoryEvent:
        if not isinstance(payload, Mapping):
            raise TypeError("participant episode history event must be a mapping")
        missing_keys = [
            key
            for key in (
                "event_type",
                "timestamp",
                "participant_address",
                "episode_id",
                "sequence_number",
            )
            if key not in payload
        ]
        if missing_keys:
            raise ValueError("participant episode history event is missing required fields: " + ", ".join(missing_keys))
        sequence_number_raw = payload.get("sequence_number")
        if isinstance(sequence_number_raw, bool) or not isinstance(sequence_number_raw, int):
            raise TypeError("participant episode history sequence_number must be an int")
        terminal_reason_raw = payload.get("terminal_reason")
        control_action_raw = payload.get("control_action")
        return cls(
            event_type=(
                payload["event_type"]
                if isinstance(payload["event_type"], ParticipantEpisodeHistoryEventType)
                else ParticipantEpisodeHistoryEventType(str(payload["event_type"]))
            ),
            timestamp=str(payload["timestamp"]),
            participant_address=str(payload["participant_address"]),
            episode_id=str(payload["episode_id"]),
            sequence_number=sequence_number_raw,
            terminal_reason=(
                terminal_reason_raw
                if isinstance(terminal_reason_raw, ParticipantEpisodeTerminalReason)
                else (
                    ParticipantEpisodeTerminalReason(str(terminal_reason_raw))
                    if terminal_reason_raw is not None
                    else None
                )
            ),
            control_action=(
                control_action_raw
                if isinstance(control_action_raw, ParticipantEpisodeControlAction)
                else (
                    ParticipantEpisodeControlAction(str(control_action_raw)) if control_action_raw is not None else None
                )
            ),
            details=dict(payload.get("details", {})) if isinstance(payload.get("details", {}), Mapping) else {},
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "participant_address": self.participant_address,
            "episode_id": self.episode_id,
            "sequence_number": self.sequence_number,
            "terminal_reason": self.terminal_reason.value if self.terminal_reason is not None else None,
            "control_action": self.control_action.value if self.control_action is not None else None,
            "details": dict(self.details),
        }

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, ParticipantEpisodeHistoryEventType):
            raise TypeError("event_type must be a ParticipantEpisodeHistoryEventType")
        if not isinstance(self.timestamp, str) or not self.timestamp:
            raise TypeError("timestamp must be a non-empty string")
        if not isinstance(self.participant_address, str) or not self.participant_address:
            raise TypeError("participant_address must be a non-empty string")
        if not isinstance(self.episode_id, str) or not self.episode_id:
            raise TypeError("episode_id must be a non-empty string")
        if isinstance(self.sequence_number, bool) or not isinstance(self.sequence_number, int):
            raise TypeError("sequence_number must be an int")
        if self.sequence_number < 0:
            raise ValueError("sequence_number must be >= 0")
        if self.terminal_reason is not None and not isinstance(self.terminal_reason, ParticipantEpisodeTerminalReason):
            raise TypeError("terminal_reason must be a ParticipantEpisodeTerminalReason or None")
        if self.control_action is not None and not isinstance(self.control_action, ParticipantEpisodeControlAction):
            raise TypeError("control_action must be a ParticipantEpisodeControlAction or None")
        if not isinstance(self.details, dict):
            raise TypeError("details must be a dict")
        expected_terminal_reason = _PARTICIPANT_EPISODE_TERMINAL_EVENTS.get(self.event_type)
        if expected_terminal_reason is not None:
            if self.terminal_reason != expected_terminal_reason:
                raise ValueError(
                    f"{self.event_type.value} history events must report terminal_reason "
                    f"{expected_terminal_reason.value}"
                )
        elif self.terminal_reason is not None:
            raise ValueError(f"{self.event_type.value} history events may not report a terminal_reason")
        expected_control_action = _PARTICIPANT_EPISODE_CONTROL_EVENTS.get(self.event_type)
        if expected_control_action is not None:
            if self.control_action != expected_control_action:
                raise ValueError(
                    f"{self.event_type.value} history events must report control_action {expected_control_action.value}"
                )
        elif self.control_action is not None:
            raise ValueError(f"{self.event_type.value} history events may not report a control_action")
        if self.event_type == ParticipantEpisodeHistoryEventType.EPISODE_INITIALIZED and self.sequence_number != 0:
            raise ValueError(
                "episode_initialized history events must report sequence_number=0; "
                "later episodes arrive via episode_reset or episode_restarted"
            )
        if (
            self.event_type
            in {
                ParticipantEpisodeHistoryEventType.EPISODE_RESET,
                ParticipantEpisodeHistoryEventType.EPISODE_RESTARTED,
            }
            and self.sequence_number == 0
        ):
            raise ValueError(
                f"{self.event_type.value} history events must report sequence_number>0; "
                "the first episode uses episode_initialized"
            )


def iter_participant_episode_snapshot_violations(
    participant_episode_results: Any,
    participant_episode_history: Any,
) -> Iterator[tuple[str, str]]:
    """Yield every participant-episode invariant violation in a snapshot."""

    results_key = "runtime.snapshot.participant-episode-results"
    history_key = "runtime.snapshot.participant-episode-history"

    if not isinstance(participant_episode_results, Mapping):
        yield (results_key, "participant_episode_results must be a mapping")
    else:
        for outer_key, result in participant_episode_results.items():
            if not isinstance(outer_key, str) or not outer_key:
                yield (results_key, "participant episode result keys must be non-empty strings")
                continue
            if not isinstance(result, Mapping):
                yield (outer_key, "participant episode result must be a mapping")
                continue
            try:
                normalized_result = ParticipantEpisodeExecutionState.from_payload(result)
            except (TypeError, ValueError) as exc:
                yield (outer_key, f"participant episode result is invalid: {exc}")
                continue
            if normalized_result.participant_address != outer_key:
                yield (
                    outer_key,
                    (
                        f"participant episode result outer key {outer_key!r} does not match "
                        f"inner participant_address {normalized_result.participant_address!r}"
                    ),
                )

    if not isinstance(participant_episode_history, Mapping):
        yield (history_key, "participant_episode_history must be a mapping")
        return

    for outer_key, history in participant_episode_history.items():
        if not isinstance(outer_key, str) or not outer_key:
            yield (history_key, "participant episode history keys must be non-empty strings")
            continue
        if not isinstance(history, list):
            yield (outer_key, "participant episode history must be a list of events")
            continue
        normalized_events: list[ParticipantEpisodeHistoryEvent] = []
        per_entry_violations = False
        for index, event in enumerate(history):
            locator = f"{outer_key}[{index}]"
            if not isinstance(event, Mapping):
                yield (locator, "participant episode history event must be a mapping")
                per_entry_violations = True
                continue
            try:
                normalized_event = ParticipantEpisodeHistoryEvent.from_payload(event)
            except (TypeError, ValueError) as exc:
                yield (locator, f"participant episode history event is invalid: {exc}")
                per_entry_violations = True
                continue
            if normalized_event.participant_address != outer_key:
                yield (
                    locator,
                    (
                        f"participant episode history event outer key {outer_key!r} does not match "
                        f"inner participant_address {normalized_event.participant_address!r}"
                    ),
                )
                per_entry_violations = True
                continue
            normalized_events.append(normalized_event)

        if per_entry_violations:
            continue

        last_sequence = -1
        sequence_to_episode: dict[int, str] = {}
        for index, event in enumerate(normalized_events):
            locator = f"{outer_key}[{index}]"
            if event.sequence_number < last_sequence:
                yield (
                    locator,
                    (
                        f"participant episode history sequence_number went backward "
                        f"({last_sequence} -> {event.sequence_number})"
                    ),
                )
                continue
            if (
                event.sequence_number > last_sequence
                and last_sequence != -1
                and event.event_type
                not in {
                    ParticipantEpisodeHistoryEventType.EPISODE_RESET,
                    ParticipantEpisodeHistoryEventType.EPISODE_RESTARTED,
                }
            ):
                yield (
                    locator,
                    (
                        f"participant episode transition to sequence_number "
                        f"{event.sequence_number} must arrive via episode_reset or "
                        f"episode_restarted; saw {event.event_type.value}"
                    ),
                )
            expected_episode_id = sequence_to_episode.get(event.sequence_number)
            if expected_episode_id is not None and expected_episode_id != event.episode_id:
                yield (
                    locator,
                    (
                        f"participant episode history episode_id changed within "
                        f"sequence_number {event.sequence_number}: "
                        f"{expected_episode_id!r} -> {event.episode_id!r}"
                    ),
                )
            sequence_to_episode[event.sequence_number] = event.episode_id
            last_sequence = event.sequence_number

    if isinstance(participant_episode_results, Mapping) and isinstance(participant_episode_history, Mapping):
        for outer_key, result in participant_episode_results.items():
            if not isinstance(outer_key, str) or not outer_key:
                continue
            if not isinstance(result, Mapping):
                continue
            history = participant_episode_history.get(outer_key)
            if not isinstance(history, list) or not history:
                continue
            try:
                normalized_result = ParticipantEpisodeExecutionState.from_payload(result)
            except (TypeError, ValueError):
                continue
            last_event: ParticipantEpisodeHistoryEvent | None = None
            for event in history:
                if not isinstance(event, Mapping):
                    continue
                try:
                    candidate = ParticipantEpisodeHistoryEvent.from_payload(event)
                except (TypeError, ValueError):
                    continue
                if candidate.participant_address != outer_key:
                    continue
                last_event = candidate
            if last_event is None:
                continue
            if (
                last_event.episode_id != normalized_result.episode_id
                or last_event.sequence_number != normalized_result.sequence_number
            ):
                yield (
                    outer_key,
                    (
                        f"participant episode result (episode_id="
                        f"{normalized_result.episode_id!r}, sequence_number="
                        f"{normalized_result.sequence_number}) does not match head of "
                        f"history chain (episode_id={last_event.episode_id!r}, "
                        f"sequence_number={last_event.sequence_number})"
                    ),
                )
                continue
            if normalized_result.status == ParticipantEpisodeStatus.TERMINATED:
                if last_event.event_type not in _PARTICIPANT_EPISODE_TERMINAL_EVENTS:
                    yield (
                        outer_key,
                        (
                            f"participant episode result status is 'terminated' but head "
                            f"history event is {last_event.event_type.value!r}, not a "
                            f"terminal event"
                        ),
                    )
                elif normalized_result.terminal_reason != last_event.terminal_reason:
                    expected = (
                        normalized_result.terminal_reason.value
                        if normalized_result.terminal_reason is not None
                        else None
                    )
                    got = last_event.terminal_reason.value if last_event.terminal_reason is not None else None
                    yield (
                        outer_key,
                        (
                            f"participant episode result terminal_reason {expected!r} does "
                            f"not match head history terminal_reason {got!r}"
                        ),
                    )
            elif normalized_result.status in (
                ParticipantEpisodeStatus.INITIALIZING,
                ParticipantEpisodeStatus.RUNNING,
            ):
                if last_event.event_type in _PARTICIPANT_EPISODE_TERMINAL_EVENTS:
                    yield (
                        outer_key,
                        (
                            f"participant episode result status is "
                            f"{normalized_result.status.value!r} but head history event is "
                            f"terminal ({last_event.event_type.value!r})"
                        ),
                    )


__all__ = (
    "ParticipantEpisodeControlAction",
    "PARTICIPANT_EPISODE_CONTROL_EVENTS",
    "PARTICIPANT_EPISODE_TERMINAL_EVENTS",
    "ParticipantEpisodeExecutionState",
    "ParticipantEpisodeHistoryEvent",
    "ParticipantEpisodeHistoryEventType",
    "ParticipantEpisodeInitializeRequest",
    "ParticipantEpisodeResetRequest",
    "ParticipantEpisodeRestartRequest",
    "ParticipantEpisodeStatus",
    "ParticipantEpisodeTerminalReason",
    "ParticipantEpisodeTerminateRequest",
    "iter_participant_episode_snapshot_violations",
)
