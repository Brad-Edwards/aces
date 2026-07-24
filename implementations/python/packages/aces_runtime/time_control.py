"""Runtime-manager shared-time initialization, control, and readback."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aces_contracts.contracts.time_model import TimeRuntimeStateModel, validate_time_runtime_state
from aces_contracts.runtime_state import ApplyResult
from aces_processor.compiler.time_model import time_model_contract_model

from .backend_calls import _call_backend_apply
from .diagnostics import _failure_diagnostic, _has_error_diagnostic

if TYPE_CHECKING:
    from aces_processor.models import ExecutionPlan

    from .manager import _RuntimeApplyState

_APPLY_TIME_ADDRESS = "runtime.apply.time"


class RuntimeTimeControlMixin:
    """Shared-time portion of the runtime manager."""

    def _apply_time_phase(
        self,
        execution_plan: ExecutionPlan,
        state: _RuntimeApplyState,
    ) -> None:
        declaration = time_model_contract_model(execution_plan.model.time_model)
        if declaration is None:
            return
        if self._target.time_runtime is None:
            state.diagnostics.append(
                _failure_diagnostic(
                    "runtime.apply-missing-time-runtime",
                    _APPLY_TIME_ADDRESS,
                    "Execution plan requires shared-time control, but the target does not provide it.",
                )
            )
            self._fail_apply_state(state)
            return
        result = _call_backend_apply(
            self._target.time_runtime.initialize,
            declaration,
            state.working_snapshot,
            address=_APPLY_TIME_ADDRESS,
            snapshot=state.working_snapshot,
        )
        self._record_phase_result(state, result)
        if result.success:
            try:
                if result.snapshot.time_model_state is None:
                    raise ValueError("time runtime did not publish typed state")
                validate_time_runtime_state(declaration, result.snapshot.time_model_state)
            except ValueError as exc:
                state.diagnostics.append(
                    _failure_diagnostic(
                        "runtime.time-readback-invalid",
                        _APPLY_TIME_ADDRESS,
                        str(exc),
                    )
                )
                self._fail_apply_state(state)
            else:
                self._time_declaration = declaration
            return
        if not _has_error_diagnostic(result.diagnostics):
            state.diagnostics.append(
                _failure_diagnostic(
                    "runtime.apply-phase-failed",
                    _APPLY_TIME_ADDRESS,
                    "Shared-time runtime failed to initialize.",
                )
            )
        self._fail_apply_state(state)

    def read_time_state(self) -> TimeRuntimeStateModel:
        """Read and validate target-provided shared-time state."""

        if self._target.time_runtime is None or self._time_declaration is None:
            raise ValueError("runtime manager has no initialized shared-time model")
        state = self._target.time_runtime.state(self._snapshot)
        validate_time_runtime_state(self._time_declaration, state)
        if state != self._snapshot.time_model_state:
            raise ValueError("time runtime readback disagrees with the runtime snapshot")
        return state

    def advance_time(self, clock_address: str, *, ticks: int, microstep: int = 0) -> ApplyResult:
        return self._apply_time_control("advance", clock_address, ticks, microstep)

    def pause_time(self, clock_address: str) -> ApplyResult:
        return self._apply_time_control("pause", clock_address)

    def resume_time(self, clock_address: str) -> ApplyResult:
        return self._apply_time_control("resume", clock_address)

    def jump_time(self, clock_address: str, *, tick: int, microstep: int = 0) -> ApplyResult:
        return self._apply_time_control("jump", clock_address, tick, microstep)

    def reset_time(self, clock_address: str, *, replay: bool = False) -> ApplyResult:
        return self._apply_time_control("reset", clock_address, replay)

    def _apply_time_control(self, method_name: str, *args: object) -> ApplyResult:
        if self._target.time_runtime is None or self._time_declaration is None:
            raise ValueError("runtime manager has no initialized shared-time model")
        method = getattr(self._target.time_runtime, method_name)
        result = _call_backend_apply(
            method,
            *args,
            self._snapshot,
            address=f"runtime.time.{method_name}",
            snapshot=self._snapshot,
        )
        if not result.success:
            return result
        if result.snapshot.time_model_state is None:
            return ApplyResult(
                success=False,
                snapshot=self._snapshot,
                diagnostics=[
                    _failure_diagnostic(
                        "runtime.time-readback-invalid",
                        f"runtime.time.{method_name}",
                        "time runtime removed typed state",
                    )
                ],
            )
        try:
            validate_time_runtime_state(self._time_declaration, result.snapshot.time_model_state)
        except ValueError as exc:
            return ApplyResult(
                success=False,
                snapshot=self._snapshot,
                diagnostics=[
                    _failure_diagnostic(
                        "runtime.time-readback-invalid",
                        f"runtime.time.{method_name}",
                        str(exc),
                    )
                ],
            )
        self._snapshot = result.snapshot
        return result
