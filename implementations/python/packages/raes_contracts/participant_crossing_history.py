"""Runtime-snapshot invariants for append-only API-423 crossing history."""

from __future__ import annotations

from collections.abc import Iterator

from raes_contracts.contracts import ParticipantCrossingOccurrenceModel


def iter_participant_crossing_history_snapshot_violations(
    history: object,
) -> Iterator[tuple[str, str]]:
    """Yield closed-shape and participant-key violations."""

    if not isinstance(history, dict):
        yield ("runtime.participant-crossing-history", "participant crossing history must be a mapping")
        return
    for participant_address, events in history.items():
        address = f"runtime.participant-crossing-history.{participant_address}"
        if not isinstance(participant_address, str) or not participant_address:
            yield (address, "participant crossing history map keys must be non-empty strings")
            continue
        if not isinstance(events, list):
            yield (address, "participant crossing history values must be event lists")
            continue
        event_ids: set[str] = set()
        for event in events:
            try:
                parsed = ParticipantCrossingOccurrenceModel.model_validate(event)
            except (TypeError, ValueError):
                yield (address, "participant crossing history must contain closed API-423 occurrences")
                continue
            if parsed.participant_address != participant_address:
                yield (
                    address,
                    "participant crossing history map key must equal the embedded participant address",
                )
            if parsed.event_id in event_ids:
                yield (address, "participant crossing history event identities must be unique")
            event_ids.add(parsed.event_id)


def iter_participant_crossing_history_transition_violations(
    previous: object,
    current: object,
) -> Iterator[tuple[str, str]]:
    """Yield violations when a crossing stream does not retain its exact prefix."""

    if not isinstance(previous, dict) or not isinstance(current, dict):
        yield ("runtime.participant-crossing-history", "participant crossing history must remain append-only")
        return
    for participant_address, previous_events in previous.items():
        current_events = current.get(participant_address)
        if (
            not isinstance(previous_events, list)
            or not isinstance(current_events, list)
            or len(current_events) < len(previous_events)
            or current_events[: len(previous_events)] != previous_events
        ):
            yield (
                f"runtime.participant-crossing-history.{participant_address}",
                "participant crossing history must remain append-only and preserve its exact prefix",
            )


__all__ = (
    "iter_participant_crossing_history_snapshot_violations",
    "iter_participant_crossing_history_transition_violations",
)
