"""Portable execution-service behavior shared by participant runtimes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from raes_contracts.contracts.participant_execution import (
    ParticipantExecutionServiceStateModel,
)
from raes_contracts.participant_binding import (
    ParticipantActionAdmissionRequest,
    ParticipantActionApplyResult,
)
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot

from .participant_action_commit import reject_participant_action_outcome
from .participant_execution_service import participant_execution_state


class ParticipantExecutionRuntimeMixin:
    """Generation fencing, lifecycle readback, and bounded native dispatch."""

    def execution_state(
        self,
        execution_scope_ref: str,
        snapshot: RuntimeSnapshot,
    ) -> ParticipantExecutionServiceStateModel:
        """Return typed health/readiness and lifecycle readback."""

        return participant_execution_state(execution_scope_ref, snapshot)

    @staticmethod
    def _execution_generation_failure(
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
        *,
        completion: bool,
        predecessor: RuntimeSnapshot | None = None,
    ) -> ParticipantActionApplyResult | None:
        scope = request.execution_scope_ref
        if scope is None:
            return None
        payload = snapshot.participant_execution_services.get(scope)
        expected = request.execution_generation
        reason = None
        if payload is None:
            reason = "execution-service state is missing"
        else:
            state = ParticipantExecutionServiceStateModel.model_validate(payload)
            if state.generation != expected or state.observed_generation != expected:
                reason = "execution generation changed"
            elif not completion and (
                state.observed_lifecycle != "running" or not state.accepting_new_work or state.readiness != "ready"
            ):
                reason = "execution service is not accepting work"
        if reason is None:
            return None
        phase = "completion" if completion else "work"
        original = predecessor or snapshot
        return reject_participant_action_outcome(
            original,
            ApplyResult(success=False, snapshot=snapshot),
            request.participant_address,
            f"runtime.participant-execution-stale-{phase}",
            (f"Participant action {phase} was rejected because its generation-bound {reason}."),
        )

    def admit_actions_concurrently(
        self,
        requests: tuple[ParticipantActionAdmissionRequest, ...],
        snapshot: RuntimeSnapshot,
        max_workers: int,
    ) -> tuple[ParticipantActionApplyResult, ...]:
        """Execute independent native actions with a finite worker bound.

        Each call receives the same immutable predecessor. The scheduler owns
        revision-checked serialized merge and scheduler-state commit.
        """

        if max_workers < 2:
            raise ValueError("concurrent participant execution requires at least two workers")
        if len(requests) > max_workers:
            raise ValueError("participant action batch exceeds its worker bound")
        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="raes-participant",
        ) as executor:
            futures = [executor.submit(self.admit_action, request, snapshot) for request in requests]
            return tuple(future.result() for future in futures)
