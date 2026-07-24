"""Autonomous participant scheduler-state snapshot invariants."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping

from aces_contracts.addressing import require_compiled_address
from aces_contracts.contracts.participant_runtime import ParticipantAutonomousExecutionStateModel

_SNAPSHOT_FIELD = "runtime.snapshot.participant-autonomous-execution-states"
_SHA256_DIGEST = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)


def iter_participant_autonomous_state_snapshot_violations(
    states: object,
) -> Iterator[tuple[str, str]]:
    """Yield structural and accounting violations for scheduler readback."""

    if not isinstance(states, Mapping):
        yield (_SNAPSHOT_FIELD, "participant_autonomous_execution_states must be a mapping")
        return

    for map_key, raw_state in states.items():
        if not isinstance(map_key, str) or not map_key:
            yield (_SNAPSHOT_FIELD, "autonomous participant state keys must be non-empty strings")
            continue
        locator = f"{_SNAPSHOT_FIELD}.{map_key}"
        if not isinstance(raw_state, Mapping):
            yield (locator, "autonomous participant state must be a mapping")
            continue

        try:
            state = ParticipantAutonomousExecutionStateModel.model_validate(raw_state)
        except ValueError as exc:
            yield (locator, f"autonomous participant state is invalid: {exc}")
            continue

        expected_key = f"{state.policy_address}.state.{state.participant_address}"
        if map_key != expected_key:
            yield (
                locator,
                "autonomous participant state map key must equal the embedded policy and participant address",
            )
        if _SHA256_DIGEST.fullmatch(state.policy_digest) is None:
            yield (
                f"{locator}.policy_digest",
                "autonomous participant policy_digest must be a canonical sha256 digest",
            )

        for field_name, address in (
            ("policy_address", state.policy_address),
            ("participant_address", state.participant_address),
            ("participant_implementation_ref", state.participant_implementation_ref),
            ("clock_address", state.clock_address),
        ):
            try:
                require_compiled_address(address, field_name=field_name)
            except ValueError as exc:
                yield (f"{locator}.{field_name}", str(exc))

        accounted_actions = state.succeeded_actions + state.failed_actions + state.in_flight
        if accounted_actions != state.attempted_actions:
            yield (
                locator,
                ("autonomous participant attempted_actions must equal succeeded_actions + failed_actions + in_flight"),
            )
        if state.lifecycle_state in {"completed", "failed"} and state.in_flight:
            yield (
                locator,
                "terminal autonomous participant state cannot retain in-flight actions",
            )


def require_participant_autonomous_state_snapshot(states: object) -> None:
    """Raise when autonomous scheduler readback violates snapshot invariants."""

    violation = next(iter_participant_autonomous_state_snapshot_violations(states), None)
    if violation is not None:
        address, message = violation
        raise ValueError(f"{address}: {message}")


def iter_participant_autonomous_runtime_snapshot_violations(
    snapshot: object,
) -> Iterator[tuple[str, str]]:
    """Yield cross-surface scheduler, clock, and episode violations."""

    states = getattr(snapshot, "participant_autonomous_execution_states", None)
    yield from iter_participant_autonomous_state_snapshot_violations(states)
    if not isinstance(states, Mapping) or not states:
        return

    time_state = getattr(snapshot, "time_model_state", None)
    clocks = getattr(time_state, "clocks", {}) if time_state is not None else {}
    episodes = getattr(snapshot, "participant_episode_results", {})
    for map_key, raw_state in states.items():
        if not isinstance(map_key, str) or not isinstance(raw_state, Mapping):
            continue
        try:
            state = ParticipantAutonomousExecutionStateModel.model_validate(raw_state)
        except ValueError:
            continue
        locator = f"{_SNAPSHOT_FIELD}.{map_key}"
        clock = clocks.get(state.clock_address) if isinstance(clocks, Mapping) else None
        if clock is None:
            yield (f"{locator}.clock_address", "autonomous participant state requires matching shared-time state")
        else:
            coordinate = getattr(clock, "coordinate", None)
            if coordinate is None or state.time_segment != getattr(coordinate, "segment", None):
                yield (
                    f"{locator}.time_segment",
                    "autonomous participant time_segment must match the bound shared clock segment",
                )
            clock_state = getattr(clock, "state", None)
            if (
                state.lifecycle_state not in {"completed", "failed"}
                and clock_state in {"running", "paused"}
                and state.lifecycle_state != clock_state
            ):
                yield (
                    f"{locator}.lifecycle_state",
                    "autonomous participant lifecycle must match the bound shared clock lifecycle",
                )

        episode = episodes.get(state.participant_address) if isinstance(episodes, Mapping) else None
        if not isinstance(episode, Mapping):
            yield (
                f"{locator}.episode_id",
                "autonomous participant state requires matching participant episode state",
            )
            continue
        if episode.get("episode_id") != state.episode_id:
            yield (
                f"{locator}.episode_id",
                "autonomous participant episode_id must match the live participant episode",
            )
        if episode.get("participant_address") != state.participant_address:
            yield (
                f"{locator}.participant_address",
                "autonomous participant state must match the embedded episode participant",
            )
        if episode.get("status") == "terminated":
            yield (
                f"{locator}.episode_id",
                "autonomous participant state cannot reference a terminated episode",
            )


def require_participant_autonomous_runtime_snapshot(snapshot: object) -> None:
    """Raise when durable autonomous state contradicts clock or episode state."""

    violation = next(iter_participant_autonomous_runtime_snapshot_violations(snapshot), None)
    if violation is not None:
        address, message = violation
        raise ValueError(f"{address}: {message}")


__all__ = (
    "iter_participant_autonomous_state_snapshot_violations",
    "iter_participant_autonomous_runtime_snapshot_violations",
    "require_participant_autonomous_runtime_snapshot",
    "require_participant_autonomous_state_snapshot",
)
