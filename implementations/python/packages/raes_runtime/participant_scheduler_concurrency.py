"""Bounded concurrent native execution and serialized participant commits."""

from __future__ import annotations

from asyncio import CancelledError
from copy import deepcopy
from dataclasses import dataclass
from itertools import islice
from typing import TYPE_CHECKING, cast

from raes_contracts.addressing import require_compiled_address
from raes_contracts.contracts import ParticipantAutonomousExecutionStateModel
from raes_contracts.contracts.participant_execution import ParticipantExecutionServiceStateModel
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_binding import ParticipantActionAdmissionRequest, ParticipantActionApplyResult
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from raes_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime

from .participant_action_validation import autonomous_action_result_violation
from .participant_scheduler_concurrent_settlement import (
    _fail_concurrent_batch_before_dispatch,
    _set_concurrent_failure,
    _settle_concurrent_service_state,
    _settle_failed_concurrent_occurrence,
    _settle_indeterminate_concurrent_batch,
)
from .participant_scheduler_concurrent_state import (
    _available_concurrent_capacity,
    _freeze_concurrent_results,
    _materialize_concurrent_snapshot,
    _reserve_concurrent_actions,
    _stage_concurrent_action_snapshot,
    _with_concurrent_scheduler_updates,
)

if TYPE_CHECKING:
    from .participant_scheduler_types import SchedulerRunState, _DueActionContext


def participant_generation_commit_diagnostic(
    request: ParticipantActionAdmissionRequest,
    authoritative: RuntimeSnapshot,
) -> Diagnostic | None:
    """Fence native completion against the serialized commit owner's state."""

    scope = request.execution_scope_ref
    if scope is None:
        return None
    payload = authoritative.participant_execution_services.get(scope)
    expected = request.execution_generation
    if payload is not None:
        service = ParticipantExecutionServiceStateModel.model_validate(payload)
        if service.generation == expected and service.observed_generation == expected:
            return None
    return Diagnostic(
        code="runtime.participant-execution-stale-completion",
        domain="participant",
        address=request.participant_address,
        message=(
            "Participant action completion was rejected because the authoritative serialized commit generation changed."
        ),
    )


def _due_contexts(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    current_tick: int,
    cadence_ticks: int,
    run: SchedulerRunState,
) -> tuple[list[_DueActionContext], list[ParticipantAutonomousExecutionStateModel]]:
    from .participant_scheduler_time import cadence_missed_result
    from .participant_scheduler_types import _DueActionContext

    contexts: list[_DueActionContext] = []
    states: list[ParticipantAutonomousExecutionStateModel] = []
    for participant_address in policy.participant_addresses:
        key = f"{policy.address}.state.{participant_address}"
        state = ParticipantAutonomousExecutionStateModel.model_validate(
            run.working.participant_autonomous_execution_states[key]
        )
        if state.lifecycle_state == "running" and state.next_tick < current_tick:
            run.failure = cadence_missed_result(run.working, key, current_tick, state)
            break
        due = (
            state.lifecycle_state == "running"
            and state.next_tick == current_tick
            and state.attempted_actions < policy.max_action_attempts
            and state.in_flight == 0
        )
        if due:
            contexts.append(
                _DueActionContext(
                    policy=policy,
                    time_model=time_model,
                    participant_runtime=participant_runtime,
                    participant_address=participant_address,
                    key=key,
                    current_tick=current_tick,
                    cadence_ticks=cadence_ticks,
                )
            )
            states.append(state)
    return contexts, states


def _unsupported_concurrency_failure(policy: ParticipantAutonomousExecutionRuntime, run: SchedulerRunState) -> None:
    run.failure = ApplyResult(
        success=False,
        snapshot=run.working,
        diagnostics=[
            Diagnostic(
                code="runtime.participant-concurrency-unsupported",
                domain="participant",
                address=policy.address,
                message="Backend declared bounded participant concurrency without an executable batch method.",
            )
        ],
    )


def _concurrent_result_protocol_invalid(
    request: ParticipantActionAdmissionRequest,
    result: object,
    *,
    episode_id: str,
    predecessor: RuntimeSnapshot,
) -> bool:
    """Validate one backend result without copying backend-controlled detail."""

    try:
        if not isinstance(result, ParticipantActionApplyResult):
            return True
        if not isinstance(result.snapshot, RuntimeSnapshot) or type(result.success) is not bool:
            return True
        if type(result.diagnostics) is not list or any(
            not isinstance(diagnostic, Diagnostic) for diagnostic in result.diagnostics
        ):
            return True
        if type(result.changed_addresses) is not list:
            return True
        for address in result.changed_addresses:
            require_compiled_address(address, field_name="changed address")
        if len(result.changed_addresses) != len(set(result.changed_addresses)):
            return True
        return (
            autonomous_action_result_violation(
                request,
                result,
                episode_id=episode_id,
                predecessor=predecessor,
            )
            is not None
        )
    except (Exception, CancelledError):  # NOSONAR - a malformed backend envelope must fail closed
        return True


def _commit_concurrent_result(
    context: _DueActionContext,
    state: ParticipantAutonomousExecutionStateModel,
    request: ParticipantActionAdmissionRequest,
    result: object,
    protocol_invalid: bool,
    base: RuntimeSnapshot,
    run: SchedulerRunState,
) -> bool:
    from .participant_scheduler_operations import _next_action_state

    stale_completion = participant_generation_commit_diagnostic(request, run.working)
    if stale_completion is not None:
        return _settle_failed_concurrent_occurrence(
            context,
            state,
            request,
            run,
            diagnostic=stale_completion,
        )
    if protocol_invalid:
        return _settle_failed_concurrent_occurrence(
            context,
            state,
            request,
            run,
            diagnostic=Diagnostic(
                code="runtime.participant-autonomous-action-protocol-invalid",
                domain="participant",
                address=context.participant_address,
                message=(
                    "Backend returned a concurrent participant result that did not satisfy "
                    "the bound terminal-result protocol."
                ),
            ),
        )
    typed_result = cast(ParticipantActionApplyResult, result)
    try:
        run.working = _stage_concurrent_action_snapshot(base, run.working, typed_result.snapshot)
    except (Exception, CancelledError):  # NOSONAR - backend snapshot merge is a trust boundary
        return _settle_failed_concurrent_occurrence(
            context,
            state,
            request,
            run,
            diagnostic=Diagnostic(
                code="runtime.participant-concurrent-commit-conflict",
                domain="participant",
                address=context.key,
                message="Backend concurrent participant state could not be merged at the serialized commit boundary.",
            ),
        )
    action_result = typed_result.action_result
    action_succeeded = bool(typed_result.success and action_result is not None and action_result.status == "succeeded")
    next_state = _next_action_state(
        context,
        state,
        request,
        action_succeeded=action_succeeded,
        protocol_failure=False,
    ).model_copy(update={"in_flight": state.in_flight})
    scheduler_states = dict(run.working.participant_autonomous_execution_states)
    scheduler_states[context.key] = next_state.model_dump(mode="json")
    run.working = _with_concurrent_scheduler_updates(
        run.working,
        states=scheduler_states,
    )
    run.diagnostics.extend(typed_result.diagnostics)
    run.changed.extend([*typed_result.changed_addresses, context.key])
    return not action_succeeded and context.policy.failure_policy == "stop"


@dataclass(frozen=True)
class _ConcurrentBatch:
    policy: ParticipantAutonomousExecutionRuntime
    time_model: CompiledTimeModel
    participant_runtime: object
    current_tick: int
    cadence_ticks: int
    run: SchedulerRunState
    contexts: tuple[_DueActionContext, ...]
    states: tuple[ParticipantAutonomousExecutionStateModel, ...]
    pre_batch: RuntimeSnapshot | None = None
    materialize: bool = True


def _execute_concurrent_batch(batch: _ConcurrentBatch) -> None:
    batch_method = getattr(batch.participant_runtime, "admit_actions_concurrently", None)
    if not callable(batch_method):
        _unsupported_concurrency_failure(batch.policy, batch.run)
        return
    from .participant_scheduler_operations import _bound_action_request

    # RuntimeSnapshot owns mutable nested mappings. Keep both the scheduler's
    # pre-dispatch rollback point and the binding predecessor isolated. Once the
    # backend dispatch boundary is entered, rollback is no longer truthful:
    # missing results are indeterminate native work and must become non-retryable.
    try:
        provided_pre_batch = getattr(batch, "pre_batch", None)
        pre_batch = provided_pre_batch if provided_pre_batch is not None else deepcopy(batch.run.working)
        binding_snapshot = deepcopy(pre_batch)
    except (Exception, CancelledError):  # NOSONAR - local snapshot isolation must fail closed
        _fail_concurrent_batch_before_dispatch(
            batch.run,
            batch.run.working,
            policy_address=batch.policy.address,
            code="runtime.participant-concurrent-snapshot-isolation-failed",
            message="Concurrent participant snapshot isolation did not complete before dispatch.",
        )
        return
    try:
        requests = tuple(
            _bound_action_request(context, binding_snapshot, state)
            for context, state in zip(batch.contexts, batch.states, strict=True)
        )
    except (Exception, CancelledError):  # NOSONAR - backend binding is a trust boundary
        _fail_concurrent_batch_before_dispatch(
            batch.run,
            pre_batch,
            policy_address=batch.policy.address,
            code="runtime.participant-concurrent-binding-failed",
            message="Backend concurrent participant request binding did not complete.",
        )
        return
    batch.run.working = pre_batch
    try:
        _reserve_concurrent_actions(batch.run, batch.contexts)
    except (Exception, CancelledError):  # NOSONAR - capacity/readback drift fails before dispatch
        _fail_concurrent_batch_before_dispatch(
            batch.run,
            pre_batch,
            policy_address=batch.policy.address,
            code="runtime.participant-concurrent-reservation-failed",
            message="Concurrent participant reservations could not be admitted within service capacity.",
        )
        return
    base = batch.run.working
    try:
        dispatch_snapshot = deepcopy(base)
    except (Exception, CancelledError):  # NOSONAR - no backend action has been submitted yet
        _fail_concurrent_batch_before_dispatch(
            batch.run,
            pre_batch,
            policy_address=batch.policy.address,
            code="runtime.participant-concurrent-snapshot-isolation-failed",
            message="Concurrent participant dispatch isolation did not complete before dispatch.",
        )
        return
    # The batch method is backend-supplied. Once called, every submitted request
    # is potentially side-effecting. A raised/cancelled call or an unpairable
    # result collection must settle those action ids instead of restoring them.
    try:
        raw_results = batch_method(requests, dispatch_snapshot, len(requests))
        # Consume at most one result beyond the declared count. This freezes a
        # mutable/generator response and cannot hang on an unbounded iterable.
        results = tuple(islice(iter(raw_results), len(requests) + 1))
    except (Exception, CancelledError):  # NOSONAR - dispatched work is now indeterminate
        _settle_indeterminate_concurrent_batch(
            batch.run,
            policy_address=batch.policy.address,
            contexts=batch.contexts,
            states=batch.states,
            requests=requests,
            pre_batch=pre_batch,
            code="runtime.participant-concurrent-batch-failed",
            message="Backend concurrent participant batch became indeterminate after dispatch.",
        )
        return
    result_count = len(results)
    if result_count != len(requests):
        _settle_indeterminate_concurrent_batch(
            batch.run,
            policy_address=batch.policy.address,
            contexts=batch.contexts,
            states=batch.states,
            requests=requests,
            pre_batch=pre_batch,
            code="runtime.participant-concurrent-result-count-invalid",
            message=(
                "Backend concurrent participant result count did not match submitted work; "
                "the dispatched actions are indeterminate."
            ),
        )
        return
    try:
        frozen_results, freeze_invalid = _freeze_concurrent_results(results, deepcopy)
    except CancelledError:  # cancellation after dispatch makes the whole batch indeterminate
        _settle_indeterminate_concurrent_batch(
            batch.run,
            policy_address=batch.policy.address,
            contexts=batch.contexts,
            states=batch.states,
            requests=requests,
            pre_batch=pre_batch,
            code="runtime.participant-concurrent-batch-cancelled",
            message="Concurrent participant result isolation was cancelled after dispatch.",
        )
        return
    protocol_invalid = tuple(
        invalid
        or _concurrent_result_protocol_invalid(
            request,
            result,
            episode_id=state.episode_id,
            predecessor=base,
        )
        for state, request, result, invalid in zip(
            batch.states,
            requests,
            frozen_results,
            freeze_invalid,
            strict=True,
        )
    )
    batch_failed = False
    for context, state, request, result, invalid in zip(
        batch.contexts,
        batch.states,
        requests,
        frozen_results,
        protocol_invalid,
        strict=True,
    ):
        # Every peer was already dispatched. Settle every peer before honoring
        # stop semantics so valid native outcomes are never silently dropped.
        batch_failed = (
            _commit_concurrent_result(
                context,
                state,
                request,
                result,
                invalid,
                base,
                batch.run,
            )
            or batch_failed
        )
    service_settled = _settle_concurrent_service_state(
        batch.run,
        policy_address=batch.policy.address,
        completed_count=len(requests),
        pre_batch=pre_batch,
    )
    if getattr(batch, "materialize", True) or batch_failed or batch.run.failure is not None:
        try:
            batch.run.working = _materialize_concurrent_snapshot(batch.run.working)
        except (Exception, CancelledError):  # NOSONAR - the commit boundary must fail closed
            _set_concurrent_failure(
                batch.run,
                Diagnostic(
                    code="runtime.participant-concurrent-commit-invalid",
                    domain="participant",
                    address=batch.policy.address,
                    message="Concurrent participant batch state failed final invariant validation.",
                ),
            )
            return
    if batch_failed and service_settled:
        _set_concurrent_failure(batch.run)


def run_policy_due_concurrently(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    current_tick: int,
    cadence_ticks: int,
    run: SchedulerRunState,
) -> bool:
    """Execute one due v1 occurrence per participant with bounded overlap."""

    if policy.profile != "participant-autonomous-execution/v1":
        return False
    contexts, _states = _due_contexts(policy, time_model, participant_runtime, current_tick, cadence_ticks, run)
    enough_due_work = len(contexts) >= 2 and policy.max_in_flight >= 2
    if run.failure is None and not enough_due_work:
        return False
    if run.failure is not None:
        return True
    try:
        run.working = deepcopy(run.working)
    except (Exception, CancelledError):  # NOSONAR - no native action has been submitted
        _set_concurrent_failure(
            run,
            Diagnostic(
                code="runtime.participant-concurrent-snapshot-isolation-failed",
                domain="participant",
                address=policy.address,
                message="Concurrent participant snapshot isolation did not complete before dispatch.",
            ),
        )
        return True
    offset = 0
    while len(contexts) - offset >= 2 and run.failure is None:
        available = _available_concurrent_capacity(policy, run)
        if available == 0:
            _set_concurrent_failure(
                run,
                Diagnostic(
                    code="runtime.participant-execution-capacity-blocked",
                    domain="participant",
                    address=policy.address,
                    message="Due participant work could not progress because execution-service capacity is exhausted.",
                ),
            )
            return True
        if available < 2:
            break
        batch_size = min(available, len(contexts) - offset)
        selected_contexts = tuple(contexts[offset : offset + batch_size])
        selected_states = tuple(
            ParticipantAutonomousExecutionStateModel.model_validate(
                run.working.participant_autonomous_execution_states[context.key]
            )
            for context in selected_contexts
        )
        _execute_concurrent_batch(
            _ConcurrentBatch(
                policy=policy,
                time_model=time_model,
                participant_runtime=participant_runtime,
                current_tick=current_tick,
                cadence_ticks=cadence_ticks,
                run=run,
                contexts=selected_contexts,
                states=selected_states,
                pre_batch=run.working,
                materialize=False,
            )
        )
        offset += batch_size

    if run.failure is None:
        run.working = _materialize_concurrent_snapshot(run.working)
        from .participant_scheduler_operations import run_participant_due

        for context in contexts[offset:]:
            run_participant_due(context, run)
            if run.failure is not None:
                break
    return True
