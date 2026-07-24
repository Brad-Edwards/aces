"""Reference coordinator for the shared ACES time lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from aces_contracts.runtime_state import RuntimeSnapshot
from aces_processor.models.time_model import (
    CompiledClock,
    CompiledTimeDomainMapping,
    CompiledTimeModel,
    CompiledTimeProgressionPolicy,
)


class ClockLifecycleState(str, Enum):
    """Observable lifecycle state of one runtime clock."""

    RUNNING = "running"
    PAUSED = "paused"


class ClockTransitionKind(str, Enum):
    """Append-only clock transition kinds."""

    INITIALIZE = "initialize"
    ADVANCE = "advance"
    PAUSE = "pause"
    RESUME = "resume"
    JUMP = "jump"
    RESET = "reset"
    REPLAY = "replay"


@dataclass(frozen=True)
class ClockReading:
    """One exact superdense runtime clock reading."""

    clock_address: str
    segment: int
    tick: int
    microstep: int = 0


def _policy_by_clock(time_model: CompiledTimeModel) -> dict[str, CompiledTimeProgressionPolicy]:
    policies: dict[str, CompiledTimeProgressionPolicy] = {}
    for policy in time_model.progression_policies:
        if policy.clock_address in policies:
            raise ValueError("a clock may have at most one compiled progression policy")
        policies[policy.clock_address] = policy
    return policies


def _clock_by_address(time_model: CompiledTimeModel) -> dict[str, CompiledClock]:
    return {clock.address: clock for clock in time_model.clocks}


def _transition(
    *,
    sequence: int,
    kind: ClockTransitionKind,
    segment: int,
    tick: int,
    microstep: int,
    previous_segment: int | None,
    previous_tick: int | None,
    previous_microstep: int | None,
) -> dict[str, object]:
    return {
        "sequence": sequence,
        "kind": kind.value,
        "segment": segment,
        "tick": tick,
        "microstep": microstep,
        "previous_segment": previous_segment,
        "previous_tick": previous_tick,
        "previous_microstep": previous_microstep,
    }


class TimeCoordinator:
    """Pure reference implementation of declared clock control semantics."""

    def __init__(self, time_model: CompiledTimeModel) -> None:
        self._time_model = time_model
        self._clocks = _clock_by_address(time_model)
        self._policies = _policy_by_clock(time_model)

    def initialize(self, snapshot: RuntimeSnapshot | None = None) -> RuntimeSnapshot:
        """Create exact initial clock state without replacing existing state."""

        current = snapshot or RuntimeSnapshot()
        contexts = dict(current.time_management_contexts)
        for clock_address, clock in self._clocks.items():
            if clock_address in contexts:
                raise ValueError(f"clock '{clock_address}' is already initialized")
            policy = self._policies.get(clock_address)
            contexts[clock_address] = {
                "schema_version": "aces-time-context/v1",
                "clock_address": clock_address,
                "time_domain_address": clock.time_domain_address,
                "progression_policy_address": policy.address if policy else None,
                "authority_kind": clock.authority_kind,
                "authority_ref": clock.authority_ref,
                "segment": 0,
                "tick": 0,
                "microstep": 0,
                "state": ClockLifecycleState.RUNNING.value,
                "sequence": 0,
                "history": [
                    _transition(
                        sequence=0,
                        kind=ClockTransitionKind.INITIALIZE,
                        segment=0,
                        tick=0,
                        microstep=0,
                        previous_segment=None,
                        previous_tick=None,
                        previous_microstep=None,
                    )
                ],
            }
        return current.with_entries(current.entries, time_management_contexts=contexts)

    def reading(self, snapshot: RuntimeSnapshot, clock_address: str) -> ClockReading:
        context = self._context(snapshot, clock_address)
        return ClockReading(
            clock_address=clock_address,
            segment=int(context["segment"]),
            tick=int(context["tick"]),
            microstep=int(context["microstep"]),
        )

    def advance(
        self,
        snapshot: RuntimeSnapshot,
        clock_address: str,
        *,
        ticks: int,
        microstep: int = 0,
    ) -> RuntimeSnapshot:
        if ticks < 0 or microstep < 0:
            raise ValueError("clock advance must be non-negative")
        context = self._context(snapshot, clock_address)
        if context["state"] != ClockLifecycleState.RUNNING.value:
            raise ValueError("a paused clock cannot advance")
        policy = self._policies.get(clock_address)
        if policy is None:
            raise ValueError("clock advancement requires a compiled progression policy")
        if policy.advancement_mode == "stepped" and ticks != policy.step_ticks:
            raise ValueError("stepped clock advances must equal the declared step_ticks")
        previous = self.reading(snapshot, clock_address)
        next_tick = previous.tick + ticks
        next_microstep = microstep if ticks else previous.microstep + microstep
        if ticks == 0 and microstep == 0:
            raise ValueError("clock advance must change tick or microstep")
        return self._replace_context(
            snapshot,
            clock_address,
            context,
            kind=ClockTransitionKind.ADVANCE,
            segment=previous.segment,
            tick=next_tick,
            microstep=next_microstep,
            state=ClockLifecycleState.RUNNING,
        )

    def pause(self, snapshot: RuntimeSnapshot, clock_address: str) -> RuntimeSnapshot:
        clock = self._clock(clock_address)
        if not clock.supports_pause:
            raise ValueError("clock does not support pause")
        context = self._context(snapshot, clock_address)
        if context["state"] != ClockLifecycleState.RUNNING.value:
            raise ValueError("only a running clock may be paused")
        reading = self.reading(snapshot, clock_address)
        return self._replace_context(
            snapshot,
            clock_address,
            context,
            kind=ClockTransitionKind.PAUSE,
            segment=reading.segment,
            tick=reading.tick,
            microstep=reading.microstep,
            state=ClockLifecycleState.PAUSED,
        )

    def resume(self, snapshot: RuntimeSnapshot, clock_address: str) -> RuntimeSnapshot:
        context = self._context(snapshot, clock_address)
        if context["state"] != ClockLifecycleState.PAUSED.value:
            raise ValueError("only a paused clock may be resumed")
        reading = self.reading(snapshot, clock_address)
        return self._replace_context(
            snapshot,
            clock_address,
            context,
            kind=ClockTransitionKind.RESUME,
            segment=reading.segment,
            tick=reading.tick,
            microstep=reading.microstep,
            state=ClockLifecycleState.RUNNING,
        )

    def jump(
        self,
        snapshot: RuntimeSnapshot,
        clock_address: str,
        *,
        tick: int,
        microstep: int = 0,
    ) -> RuntimeSnapshot:
        clock = self._clock(clock_address)
        if not clock.supports_jump:
            raise ValueError("clock does not support jumps")
        context = self._context(snapshot, clock_address)
        reading = self.reading(snapshot, clock_address)
        return self._replace_context(
            snapshot,
            clock_address,
            context,
            kind=ClockTransitionKind.JUMP,
            segment=reading.segment + 1,
            tick=tick,
            microstep=microstep,
            state=ClockLifecycleState(str(context["state"])),
        )

    def reset(
        self,
        snapshot: RuntimeSnapshot,
        clock_address: str,
        *,
        replay: bool = False,
    ) -> RuntimeSnapshot:
        clock = self._clock(clock_address)
        if not clock.supports_reset:
            raise ValueError("clock does not support reset")
        policy = self._policies.get(clock_address)
        if policy is None:
            raise ValueError("clock reset requires a compiled progression policy")
        behavior = policy.replay_behavior if replay else policy.reset_behavior
        if behavior == "unsupported":
            raise ValueError("clock policy does not support the requested lifecycle operation")
        context = self._context(snapshot, clock_address)
        reading = self.reading(snapshot, clock_address)
        preserve = behavior == "new_segment_preserve_value"
        return self._replace_context(
            snapshot,
            clock_address,
            context,
            kind=ClockTransitionKind.REPLAY if replay else ClockTransitionKind.RESET,
            segment=reading.segment + 1,
            tick=reading.tick if preserve else 0,
            microstep=reading.microstep if preserve else 0,
            state=ClockLifecycleState.RUNNING,
        )

    def convert_tick(
        self,
        mapping_address: str,
        tick: int,
    ) -> Fraction:
        mapping = self._mapping(mapping_address)
        return Fraction(tick * mapping.scale_numerator, mapping.scale_denominator) + mapping.offset_ticks

    def _clock(self, address: str) -> CompiledClock:
        try:
            return self._clocks[address]
        except KeyError as exc:
            raise KeyError(f"unknown compiled clock '{address}'") from exc

    def _mapping(self, address: str) -> CompiledTimeDomainMapping:
        for mapping in self._time_model.mappings:
            if mapping.address == address:
                return mapping
        raise KeyError(f"unknown compiled time-domain mapping '{address}'")

    def _context(self, snapshot: RuntimeSnapshot, clock_address: str) -> dict[str, object]:
        self._clock(clock_address)
        try:
            context = snapshot.time_management_contexts[clock_address]
        except KeyError as exc:
            raise KeyError(f"clock '{clock_address}' is not initialized") from exc
        if context.get("clock_address") != clock_address:
            raise ValueError("runtime time context key disagrees with clock_address")
        return dict(context)

    def _replace_context(
        self,
        snapshot: RuntimeSnapshot,
        clock_address: str,
        context: dict[str, object],
        *,
        kind: ClockTransitionKind,
        segment: int,
        tick: int,
        microstep: int,
        state: ClockLifecycleState,
    ) -> RuntimeSnapshot:
        previous = self.reading(snapshot, clock_address)
        sequence = int(context["sequence"]) + 1
        history = [*list(context.get("history", []))]
        history.append(
            _transition(
                sequence=sequence,
                kind=kind,
                segment=segment,
                tick=tick,
                microstep=microstep,
                previous_segment=previous.segment,
                previous_tick=previous.tick,
                previous_microstep=previous.microstep,
            )
        )
        context.update(
            {
                "segment": segment,
                "tick": tick,
                "microstep": microstep,
                "state": state.value,
                "sequence": sequence,
                "history": history,
            }
        )
        contexts = dict(snapshot.time_management_contexts)
        contexts[clock_address] = context
        return snapshot.with_entries(snapshot.entries, time_management_contexts=contexts)


__all__ = [
    "ClockLifecycleState",
    "ClockReading",
    "ClockTransitionKind",
    "TimeCoordinator",
]
