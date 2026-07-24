"""Runtime-manager control for autonomous ordinary participants."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from aces_contracts.contracts import ParticipantAutonomousExecutionStateModel
from aces_contracts.diagnostics import Diagnostic
from aces_contracts.participant_episode import ParticipantEpisodeResetRequest
from aces_contracts.runtime_state import ApplyResult

from .diagnostics import _has_error_diagnostic
from .participant_clock_driver import ParticipantClockDriver
from .participant_scheduler import ParticipantScheduler

if TYPE_CHECKING:
    from aces_processor.models import ExecutionPlan

    from .manager import _RuntimeApplyState


class RuntimeParticipantExecutionMixin:
    """Autonomous participant portion of the runtime manager."""

    def _participant_driver_apply_precondition(self) -> ApplyResult | None:
        if self._stop_participant_clock_driver():
            return None
        return ApplyResult(
            success=False,
            snapshot=self._snapshot,
            diagnostics=[
                Diagnostic(
                    code="runtime.participant-clock-driver-stop-timeout",
                    domain="participant",
                    address="runtime.apply",
                    message="Apply did not start because the participant clock driver is still active.",
                )
            ],
        )

    def _finalize_participant_driver_apply(self, state: _RuntimeApplyState) -> None:
        self._snapshot = state.working_snapshot
        driver_started = self._start_participant_clock_driver()
        if not driver_started:
            state.diagnostics.append(
                Diagnostic(
                    code="runtime.participant-clock-driver-stop-timeout",
                    domain="participant",
                    address="runtime.apply",
                    message="Apply completed but the prior participant clock driver remained active.",
                )
            )
        state.failure = ApplyResult(
            success=driver_started and not _has_error_diagnostic(state.diagnostics),
            snapshot=self._snapshot,
            diagnostics=state.diagnostics,
            changed_addresses=list(dict.fromkeys(state.changed_addresses)),
        )

    def _apply_participant_execution_phase(
        self,
        execution_plan: ExecutionPlan,
        state: _RuntimeApplyState,
    ) -> None:
        policies = tuple(
            spec.autonomous_execution
            for spec in execution_plan.model.behavior_specifications.values()
            if spec.autonomous_execution is not None
        )
        self._participant_execution_policies = policies
        self._participant_execution_time_model = execution_plan.model.time_model
        if not policies:
            return
        if self._target.participant_runtime is None:
            self._fail_apply_state(state)
            return
        result = self._participant_scheduler.initialize(
            policies,
            execution_plan.model.time_model,
            self._target.participant_runtime,
            state.working_snapshot,
        )
        self._record_phase_result(state, result)
        if not result.success:
            self._fail_apply_state(state)

    def _start_participant_execution_phase(
        self,
        execution_plan: ExecutionPlan,
        state: _RuntimeApplyState,
    ) -> bool:
        if not self._participant_execution_policies:
            return True
        due = self._participant_scheduler.run_due(
            self._participant_execution_policies,
            execution_plan.model.time_model,
            self._target.participant_runtime,
            state.working_snapshot,
        )
        self._record_phase_result(state, due)
        return due.success

    def run_due_participant_actions(self) -> ApplyResult:
        with self._participant_execution_lock:
            if self._target.participant_runtime is None:
                raise ValueError("runtime manager has no participant runtime")
            result = self._participant_scheduler.run_due(
                self._participant_execution_policies,
                self._participant_execution_time_model,
                self._target.participant_runtime,
                self._snapshot,
            )
            self._snapshot = result.snapshot
            return result

    def _start_participant_clock_driver(self) -> bool:
        if not self._stop_participant_clock_driver():
            return False
        if not self._participant_execution_policies or self._participant_execution_time_model is None:
            return True
        self._participant_clock_driver = ParticipantClockDriver(
            self._participant_execution_policies,
            self._participant_execution_time_model,
            snapshot=lambda: self._snapshot,
            advance=lambda clock_address, ticks: self.advance_time(clock_address, ticks=ticks),
            service_due=self.run_due_participant_actions,
            lock=self._participant_execution_lock,
        )
        self._participant_clock_driver.start()
        return True

    def _stop_participant_clock_driver(self) -> bool:
        if self._participant_clock_driver is not None:
            if not self._participant_clock_driver.stop():
                return False
        self._participant_clock_driver = None
        return True

    def participant_clock_driver_status(self) -> dict[str, object]:
        driver = self._participant_clock_driver
        failure = driver.failure if driver is not None else None
        return {
            "active": bool(driver is not None and driver.active),
            "failure": ([diagnostic.message for diagnostic in failure.diagnostics] if failure is not None else None),
        }

    def _sync_participant_execution_clock(
        self,
        method_name: str,
        clock_address: str,
    ) -> ApplyResult | None:
        if method_name == "reset":
            if self._target.participant_runtime is None or self._participant_execution_time_model is None:
                return None
            result = self._participant_scheduler.reset_clock(
                self._participant_execution_policies,
                self._participant_execution_time_model,
                self._target.participant_runtime,
                self._snapshot,
                clock_address,
                reset_participants=False,
            )
            self._snapshot = result.snapshot
            return result
        lifecycle = {"pause": "paused", "resume": "running"}.get(method_name)
        lifecycle_result = None
        if lifecycle is not None:
            lifecycle_result = self._participant_scheduler.set_clock_lifecycle(
                self._snapshot,
                clock_address,
                lifecycle,
            )
            self._snapshot = lifecycle_result.snapshot
        if method_name not in {"advance", "jump", "resume"}:
            return lifecycle_result
        due_result = self.run_due_participant_actions()
        if lifecycle_result is None:
            return due_result
        return ApplyResult(
            success=due_result.success,
            snapshot=due_result.snapshot,
            diagnostics=[*lifecycle_result.diagnostics, *due_result.diagnostics],
            changed_addresses=list(dict.fromkeys([*lifecycle_result.changed_addresses, *due_result.changed_addresses])),
        )

    def _participant_execution_clock_reset_requests(
        self,
        clock_address: str,
    ) -> tuple[ParticipantEpisodeResetRequest, ...]:
        if self._snapshot.time_model_state is None:
            return ()
        clock = self._snapshot.time_model_state.clocks.get(clock_address)
        if clock is None:
            return ()
        segment = clock.coordinate.segment + 1
        participant_addresses = {
            participant_address
            for policy in self._participant_execution_policies
            if policy.clock_address == clock_address
            for participant_address in policy.participant_addresses
        }
        return tuple(
            ParticipantEpisodeResetRequest(
                participant_address=participant_address,
                episode_id=f"{participant_address}-autonomous-{segment}",
                reason=f"shared clock reset to segment {segment}",
            )
            for participant_address in sorted(participant_addresses)
        )

    def _participant_execution_clock_preflight(
        self,
        method_name: str,
        args: tuple[object, ...],
    ) -> ApplyResult | None:
        if method_name not in {"advance", "jump"} or self._snapshot.time_model_state is None:
            return None
        clock_address = str(args[0])
        clock = self._snapshot.time_model_state.clocks.get(clock_address)
        if clock is None:
            return None
        current_tick = clock.coordinate.tick
        resulting_tick = current_tick + int(args[1]) if method_name == "advance" else int(args[1])
        if resulting_tick <= current_tick:
            return None
        for state_address, payload in self._snapshot.participant_autonomous_execution_states.items():
            state = ParticipantAutonomousExecutionStateModel.model_validate(payload)
            if state.clock_address != clock_address or state.lifecycle_state != "running":
                continue
            if state.next_tick < current_tick or current_tick < state.next_tick < resulting_tick:
                return ApplyResult(
                    success=False,
                    snapshot=self._snapshot,
                    diagnostics=[
                        Diagnostic(
                            code="runtime.participant-autonomous-cadence-skipped",
                            domain="participant",
                            address=state_address,
                            message=(
                                f"Clock transition to tick {resulting_tick} would skip governed participant "
                                f"cadence tick {state.next_tick}; advance to the cadence boundary first."
                            ),
                        )
                    ],
                )
        return None

    def _initialize_participant_scheduler(self) -> None:
        self._participant_execution_lock = threading.RLock()
        self._participant_scheduler = ParticipantScheduler()
        self._participant_execution_policies = ()
        self._participant_execution_time_model = None
        self._participant_clock_driver = None


__all__ = ["RuntimeParticipantExecutionMixin"]
