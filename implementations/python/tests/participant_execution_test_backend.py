"""Native in-memory execution controller used by backend contract tests."""

from __future__ import annotations

import threading
import time

from raes_contracts.contracts import ParticipantAutonomousExecutionStateModel
from raes_contracts.contracts.participant_execution import (
    ParticipantExecutionControlRequestModel,
    ParticipantExecutionServiceStateModel,
)
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot


class NativeParticipantExecutionController:
    """Backend-owned lifecycle implementation with observed native state."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._active = 0
        self._accepting = True
        self._resources_allocated = True

    def begin_action(self) -> None:
        with self._condition:
            if not self._accepting:
                raise RuntimeError("native participant execution is not accepting work")
            self._active += 1

    def finish_action(self) -> None:
        with self._condition:
            self._active -= 1
            self._condition.notify_all()

    @staticmethod
    def _failure(
        request: ParticipantExecutionControlRequestModel,
        snapshot: RuntimeSnapshot,
        code: str,
    ) -> ApplyResult:
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                Diagnostic(
                    code=code,
                    domain="participant",
                    address=request.execution_scope_ref,
                    message="Native participant execution control failed.",
                )
            ],
        )

    def _drain(
        self,
        request: ParticipantExecutionControlRequestModel,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult | None:
        if request.action != "drain":
            return None
        assert request.timeout_seconds is not None
        deadline = time.monotonic() + request.timeout_seconds
        with self._condition:
            self._accepting = False
            while self._active:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not self._condition.wait(timeout=remaining):
                    return self._failure(
                        request,
                        snapshot,
                        "runtime.participant-execution-drain-timeout",
                    )
        return None

    @staticmethod
    def _scheduler_updates(
        snapshot: RuntimeSnapshot,
        state: ParticipantExecutionServiceStateModel,
        lifecycle: str,
        *,
        reset: bool,
    ) -> dict[str, dict[str, object]]:
        scheduler_states = dict(snapshot.participant_autonomous_execution_states)
        for ref in state.scheduler_state_refs:
            payload = scheduler_states.get(ref)
            if payload is None:
                continue
            scheduler_state = ParticipantAutonomousExecutionStateModel.model_validate(payload)
            updates: dict[str, object] = {"lifecycle_state": lifecycle}
            if reset:
                updates.update(
                    attempted_actions=0,
                    succeeded_actions=0,
                    failed_actions=0,
                    in_flight=0,
                )
            scheduler_states[ref] = scheduler_state.model_copy(update=updates).model_dump(mode="json")
        return scheduler_states

    def control(
        self,
        request: ParticipantExecutionControlRequestModel,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult:
        payload = snapshot.participant_execution_services.get(request.execution_scope_ref)
        if payload is None:
            return self._failure(
                request,
                snapshot,
                "runtime.participant-execution-not-found",
            )
        state = ParticipantExecutionServiceStateModel.model_validate(payload)
        if state.generation != request.expected_generation:
            return self._failure(
                request,
                snapshot,
                "runtime.participant-execution-stale-generation",
            )
        drain_failure = self._drain(request, snapshot)
        if drain_failure is not None:
            return drain_failure
        transition = self._transition(request, state)
        if transition is None:
            return self._failure(
                request,
                snapshot,
                "runtime.participant-execution-transition-invalid",
            )
        lifecycle, readiness, accepting, generation = transition
        with self._condition:
            self._accepting = accepting
            if request.action == "start":
                self._resources_allocated = True
            if request.action == "teardown":
                self._resources_allocated = False
            active = self._active
        evidence_ref = f"evidence:{request.execution_scope_ref}:backend-native-{request.action}:generation-{generation}"
        next_state = state.model_copy(
            update={
                "desired_lifecycle": lifecycle,
                "observed_lifecycle": lifecycle,
                "generation": generation,
                "observed_generation": generation,
                "readiness": readiness,
                "accepting_new_work": accepting,
                "draining": False,
                "quiescent": active == 0,
                "reserved": 0,
                "in_flight": active,
                "resources_released": not self._resources_allocated,
                "last_transition_ref": (
                    f"operation:{request.execution_scope_ref}:backend-native-{request.action}:generation-{generation}"
                ),
                "evidence_refs": tuple(dict.fromkeys([*state.evidence_refs, evidence_ref])),
            }
        )
        services = dict(snapshot.participant_execution_services)
        services[request.execution_scope_ref] = next_state.model_dump(mode="json")
        scheduler_lifecycle = "paused" if lifecycle == "paused" else "running"
        scheduler_states = self._scheduler_updates(
            snapshot,
            state,
            scheduler_lifecycle,
            reset=request.action == "reset",
        )
        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(
                dict(snapshot.entries),
                participant_execution_services=services,
                participant_autonomous_execution_states=scheduler_states,
            ),
            changed_addresses=[
                request.execution_scope_ref,
                *[ref for ref in state.scheduler_state_refs if ref in scheduler_states],
            ],
        )

    @staticmethod
    def _transition(
        request: ParticipantExecutionControlRequestModel,
        state: ParticipantExecutionServiceStateModel,
    ) -> tuple[str, str, bool, int] | None:
        action = request.action
        lifecycle = state.observed_lifecycle
        if action == "start" and lifecycle == "stopped":
            return "running", "ready", True, state.generation
        if action == "pause" and lifecycle == "running":
            return "paused", "not_ready", False, state.generation
        if action == "resume" and lifecycle == "paused":
            return "running", "ready", True, state.generation
        if action == "drain" and lifecycle in {"running", "paused", "quiescent"}:
            return "quiescent", "not_ready", False, state.generation
        if action == "reset" and lifecycle == "quiescent":
            return "running", "ready", True, state.generation + 1
        if action == "teardown" and lifecycle == "quiescent":
            return "terminated", "not_ready", False, state.generation
        return None


__all__ = ["NativeParticipantExecutionController"]
