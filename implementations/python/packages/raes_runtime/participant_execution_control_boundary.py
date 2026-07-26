"""Validation boundary for backend-owned participant execution control."""

from __future__ import annotations

from collections.abc import Callable

from raes_contracts.contracts.participant_execution import (
    ParticipantExecutionControlRequestModel,
    ParticipantExecutionServiceStateModel,
)
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot

from .backend_calls import _call_backend_apply


def _failure(
    snapshot: RuntimeSnapshot,
    request: ParticipantExecutionControlRequestModel,
    code: str,
    message: str,
) -> ApplyResult:
    return ApplyResult(
        success=False,
        snapshot=snapshot,
        diagnostics=[
            Diagnostic(
                code=code,
                domain="participant",
                address=request.execution_scope_ref,
                message=message,
            )
        ],
    )


def _precondition(
    request: ParticipantExecutionControlRequestModel,
    snapshot: RuntimeSnapshot,
) -> ApplyResult | None:
    payload = snapshot.participant_execution_services.get(request.execution_scope_ref)
    if payload is None:
        return _failure(
            snapshot,
            request,
            "runtime.participant-execution-not-found",
            "Participant execution scope is not configured.",
        )
    state = ParticipantExecutionServiceStateModel.model_validate(payload)
    if state.generation != request.expected_generation:
        return _failure(
            snapshot,
            request,
            "runtime.participant-execution-stale-generation",
            "Participant execution request generation does not match current state.",
        )
    return None


def _expected_observation(
    request: ParticipantExecutionControlRequestModel,
) -> tuple[str, str, bool]:
    if request.action in {"start", "resume", "reset"}:
        return "running", "ready", True
    if request.action == "pause":
        return "paused", "not_ready", False
    if request.action == "drain":
        return "quiescent", "not_ready", False
    return "terminated", "not_ready", False


def _validate_observed_result(
    request: ParticipantExecutionControlRequestModel,
    predecessor: RuntimeSnapshot,
    result: ApplyResult,
) -> ApplyResult:
    if not result.success:
        return result
    payload = result.snapshot.participant_execution_services.get(request.execution_scope_ref)
    if payload is None:
        return _failure(
            predecessor,
            request,
            "runtime.participant-execution-readback-missing",
            "Backend control succeeded without publishing execution-service readback.",
        )
    before = ParticipantExecutionServiceStateModel.model_validate(
        predecessor.participant_execution_services[request.execution_scope_ref]
    )
    observed = ParticipantExecutionServiceStateModel.model_validate(payload)
    lifecycle, readiness, accepting = _expected_observation(request)
    expected_generation = request.expected_generation + (1 if request.action == "reset" else 0)
    invalid = (
        observed.observed_lifecycle != lifecycle
        or observed.desired_lifecycle != lifecycle
        or observed.readiness != readiness
        or observed.accepting_new_work is not accepting
        or observed.generation != expected_generation
        or observed.observed_generation != expected_generation
        or not observed.last_transition_ref
        or observed.last_transition_ref == before.last_transition_ref
        or not set(observed.evidence_refs).difference(before.evidence_refs)
    )
    if request.action == "drain":
        invalid = invalid or bool(
            observed.reserved or observed.in_flight or observed.draining or not observed.quiescent
        )
    if request.action == "teardown":
        invalid = invalid or not observed.resources_released
    if invalid:
        return _failure(
            predecessor,
            request,
            "runtime.participant-execution-readback-invalid",
            "Backend control result did not prove the requested observed lifecycle transition.",
        )
    return result


def backend_execution_control_method(
    backend_method: Callable[..., object],
) -> Callable[[ParticipantExecutionControlRequestModel, RuntimeSnapshot], ApplyResult]:
    """Wrap native control with generation preflight and observed-result checks."""

    def apply(
        request: ParticipantExecutionControlRequestModel,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult:
        failure = _precondition(request, snapshot)
        if failure is not None:
            return failure
        result = _call_backend_apply(
            backend_method,
            request,
            snapshot,
            address=f"runtime.participant-execution.{request.execution_scope_ref}.{request.action}",
            snapshot=snapshot,
        )
        return _validate_observed_result(request, snapshot, result)

    return apply


__all__ = ["backend_execution_control_method"]
