"""Wall-paced clock driver for autonomous participant execution."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from fractions import Fraction

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from aces_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime


@dataclass(frozen=True)
class _ClockRate:
    clock_address: str
    seconds_per_tick: Fraction


def _automatic_clock_rates(
    policies: Iterable[ParticipantAutonomousExecutionRuntime],
    time_model: CompiledTimeModel,
) -> tuple[_ClockRate, ...]:
    policy_clocks = {policy.clock_address for policy in policies}
    clocks = {clock.address: clock for clock in time_model.clocks}
    domains = {domain.address: domain for domain in time_model.domains}
    rates: list[_ClockRate] = []
    for progression in time_model.progression_policies:
        if progression.clock_address not in policy_clocks:
            continue
        if progression.advancement_mode not in {"real_time", "dilated"}:
            continue
        if clocks[progression.clock_address].authority_kind != "runtime":
            continue
        domain = domains[clocks[progression.clock_address].time_domain_address]
        tick_period = Fraction(domain.tick_period_numerator, domain.tick_period_denominator)
        pacing = Fraction(progression.pacing_numerator, progression.pacing_denominator)
        rates.append(
            _ClockRate(
                clock_address=progression.clock_address,
                seconds_per_tick=tick_period / pacing,
            )
        )
    return tuple(rates)


class ParticipantClockDriver:
    """Advance wall-paced shared clocks to each governed participant cadence."""

    def __init__(
        self,
        policies: Iterable[ParticipantAutonomousExecutionRuntime],
        time_model: CompiledTimeModel,
        *,
        snapshot: Callable[[], RuntimeSnapshot],
        advance: Callable[[str, int], ApplyResult],
        service_due: Callable[[], ApplyResult],
        lock: threading.RLock,
    ) -> None:
        self._rates = _automatic_clock_rates(policies, time_model)
        self._snapshot = snapshot
        self._advance = advance
        self._service_due = service_due
        self._lock = lock
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._failure: ApplyResult | None = None
        self._deadlines: dict[tuple[str, int, int, int], float] = {}

    @property
    def active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def failure(self) -> ApplyResult | None:
        return self._failure

    def start(self) -> None:
        if not self._rates or self.active:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="aces-participant-clock-driver",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout: float = 2.0) -> bool:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        if thread is not None and thread.is_alive():
            return False
        self._thread = None
        self._deadlines.clear()
        return True

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                transition = self._next_transition()
                if transition is None:
                    self._stop.wait(0.05)
                    continue
                _clock_address, _ticks, delay = transition
                if delay > 0:
                    if self._stop.wait(delay):
                        return
                    # Lifecycle controls may have changed the clock during the wait.
                    continue
                with self._lock:
                    current = self._next_transition()
                    if current is None:
                        continue
                    clock_address, ticks, current_delay = current
                    if current_delay > 0:
                        continue
                    result = self._service_due() if ticks == 0 else self._advance(clock_address, ticks)
                if not result.success:
                    self._failure = result
                    return
        except Exception as exc:  # noqa: BLE001 - failure must remain observable
            self._failure = ApplyResult(
                success=False,
                snapshot=self._snapshot(),
                diagnostics=[
                    Diagnostic(
                        code="runtime.participant-clock-driver-failed",
                        domain="participant",
                        address="runtime.participant-clock-driver",
                        message=f"Participant clock driver terminated unexpectedly: {exc}",
                    )
                ],
            )

    def _next_transition(self) -> tuple[str, int, float] | None:
        with self._lock:
            snapshot = self._snapshot()
            if snapshot.time_model_state is None:
                return None
            candidates: list[tuple[float, str, int]] = []
            now = time.monotonic()
            active_keys: set[tuple[str, int, int, int]] = set()
            for rate in self._rates:
                clock = snapshot.time_model_state.clocks.get(rate.clock_address)
                if clock is None or clock.state != "running":
                    continue
                next_ticks = []
                for payload in snapshot.participant_autonomous_execution_states.values():
                    if (
                        payload.get("clock_address") == rate.clock_address
                        and payload.get("lifecycle_state") == "running"
                    ):
                        next_ticks.append(int(payload["next_tick"]))
                if not next_ticks:
                    continue
                next_tick = min(next_ticks)
                current_tick = clock.coordinate.tick
                if next_tick <= current_tick:
                    return rate.clock_address, 0, 0.0
                key = (rate.clock_address, clock.coordinate.segment, current_tick, next_tick)
                active_keys.add(key)
                deadline = self._deadlines.setdefault(
                    key,
                    now + float(rate.seconds_per_tick * (next_tick - current_tick)),
                )
                candidates.append((max(0.0, deadline - now), rate.clock_address, next_tick - current_tick))
            self._deadlines = {key: value for key, value in self._deadlines.items() if key in active_keys}
            if not candidates:
                return None
            delay, clock_address, ticks = min(candidates)
            return clock_address, ticks, delay


__all__ = ["ParticipantClockDriver"]
