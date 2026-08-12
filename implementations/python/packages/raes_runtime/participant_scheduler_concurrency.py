"""Bounded concurrent native execution and serialized participant commits."""

from __future__ import annotations

from asyncio import CancelledError
from copy import deepcopy
from typing import TYPE_CHECKING

from raes_contracts.contracts import ParticipantAutonomousExecutionStateModel
from raes_contracts.diagnostics import Diagnostic
from raes_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime

from .participant_scheduler_concurrent_dispatch import (
    _CONCURRENT_SNAPSHOT_ISOLATION_FAILED,
    _ConcurrentBatch,
    _execute_concurrent_batch,
)
from .participant_scheduler_concurrent_settlement import _set_concurrent_failure
from .participant_scheduler_concurrent_state import (
    _available_concurrent_capacity,
    _materialize_concurrent_snapshot,
)

if TYPE_CHECKING:
    from .participant_scheduler_types import SchedulerRunState, _DueActionContext


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


def _isolate_concurrent_policy_snapshot(
    policy: ParticipantAutonomousExecutionRuntime,
    run: SchedulerRunState,
) -> bool:
    isolated = True
    try:
        run.working = deepcopy(run.working)
    except (Exception, CancelledError):  # NOSONAR - no native action has been submitted
        _set_concurrent_failure(
            run,
            Diagnostic(
                code=_CONCURRENT_SNAPSHOT_ISOLATION_FAILED,
                domain="participant",
                address=policy.address,
                message="Concurrent participant snapshot isolation did not complete before dispatch.",
            ),
        )
        isolated = False
    return isolated


def _execute_capacity_bounded_batches(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    current_tick: int,
    cadence_ticks: int,
    run: SchedulerRunState,
    contexts: list[_DueActionContext],
) -> int:
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
            break
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
    return offset


def _execute_concurrent_due_contexts(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    current_tick: int,
    cadence_ticks: int,
    run: SchedulerRunState,
    contexts: list[_DueActionContext],
) -> None:
    if not _isolate_concurrent_policy_snapshot(policy, run):
        return
    offset = _execute_capacity_bounded_batches(
        policy,
        time_model,
        participant_runtime,
        current_tick,
        cadence_ticks,
        run,
        contexts,
    )

    if run.failure is None:
        run.working = _materialize_concurrent_snapshot(run.working)
        from .participant_scheduler_operations import run_participant_due

        for context in contexts[offset:]:
            run_participant_due(context, run)
            if run.failure is not None:
                break


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
    handled = run.failure is not None or (len(contexts) >= 2 and policy.max_in_flight >= 2)
    if handled and run.failure is None:
        _execute_concurrent_due_contexts(
            policy,
            time_model,
            participant_runtime,
            current_tick,
            cadence_ticks,
            run,
            contexts,
        )
    return handled
