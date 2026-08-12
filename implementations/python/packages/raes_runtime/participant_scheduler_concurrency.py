"""Bounded concurrent native execution and serialized participant commits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from raes_contracts.contracts import ParticipantAutonomousExecutionStateModel
from raes_contracts.contracts.participant_execution import ParticipantExecutionServiceStateModel
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_binding import ParticipantActionAdmissionRequest, ParticipantActionApplyResult
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from raes_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime

from .participant_action_validation import autonomous_action_result_violation

if TYPE_CHECKING:
    from .participant_scheduler_types import SchedulerRunState, _DueActionContext


def _changed_mapping(
    base: dict[str, object],
    incoming: dict[str, object],
) -> dict[str, object]:
    return {key: value for key, value in incoming.items() if base.get(key) != value}


def _merge_mapping_revision_checked(
    *,
    base: dict[str, object],
    current: dict[str, object],
    incoming: dict[str, object],
    field_name: str,
) -> dict[str, object]:
    merged = dict(current)
    for key, value in _changed_mapping(base, incoming).items():
        current_value = current.get(key)
        base_value = base.get(key)
        if current_value != base_value and current_value != value:
            raise ValueError(f"concurrent participant commit conflict in {field_name}[{key!r}]")
        merged[key] = value
    return merged


def _merge_concurrent_action_snapshot(
    base: RuntimeSnapshot,
    current: RuntimeSnapshot,
    incoming: RuntimeSnapshot,
) -> RuntimeSnapshot:
    """Merge one native result without replacing a newer whole snapshot."""

    entries = _merge_mapping_revision_checked(
        base=dict(base.entries),
        current=dict(current.entries),
        incoming=dict(incoming.entries),
        field_name="entries",
    )
    mapping_fields = (
        "participant_episode_results",
        "participant_episode_history",
        "participant_behavior_history",
        "participant_control_history",
        "shared_state_records",
        "shared_state_history",
        "joint_action_records",
        "time_management_contexts",
    )
    updates: dict[str, object] = {}
    for field_name in mapping_fields:
        updates[field_name] = _merge_mapping_revision_checked(
            base=dict(getattr(base, field_name)),
            current=dict(getattr(current, field_name)),
            incoming=dict(getattr(incoming, field_name)),
            field_name=field_name,
        )
    metadata = dict(current.metadata)
    metadata.update(incoming.metadata)
    updates["metadata"] = metadata
    return current.with_entries(entries, **updates)


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


def _reserve_concurrent_actions(
    run: SchedulerRunState,
    contexts: tuple[_DueActionContext, ...],
) -> None:
    states = dict(run.working.participant_autonomous_execution_states)
    for context in contexts:
        state = ParticipantAutonomousExecutionStateModel.model_validate(states[context.key])
        states[context.key] = state.model_copy(
            update={
                "attempted_actions": state.attempted_actions + 1,
                "in_flight": state.in_flight + 1,
            }
        ).model_dump(mode="json")
    services = dict(run.working.participant_execution_services)
    for policy_address in {context.policy.address for context in contexts}:
        payload = services.get(policy_address)
        if payload is None:
            continue
        service = ParticipantExecutionServiceStateModel.model_validate(payload)
        count = sum(1 for context in contexts if context.policy.address == policy_address)
        services[policy_address] = service.model_copy(
            update={
                "reserved": 0,
                "in_flight": count,
                "quiescent": False,
            }
        ).model_dump(mode="json")
    run.working = run.working.with_entries(
        dict(run.working.entries),
        participant_autonomous_execution_states=states,
        participant_execution_services=services,
    )


def _release_concurrent_reservations(
    run: SchedulerRunState,
    contexts: tuple[_DueActionContext, ...],
    policy_address: str,
) -> None:
    """Undo ``_reserve_concurrent_actions`` when the batch never produced results.

    Reservations are taken before the backend batch call, and only
    ``_commit_concurrent_result`` clears a participant's ``in_flight``. Abandoning
    the batch without releasing them would leave participants permanently
    in-flight and the service non-quiescent, so no later occurrence can be
    admitted for them.

    The reservation is reverted rather than settled as a failed action. Without
    per-action results there is no basis for the rest of a failed-action
    transition (``next_tick``, ``next_action_index``, lifecycle), and recording a
    failure while leaving those untouched would let the same occurrence be
    serviced again at the same tick. Reverting restores the pre-batch state
    exactly, so the returned failure snapshot reports the diagnostic without
    inventing a half-applied occurrence.
    """

    states = dict(run.working.participant_autonomous_execution_states)
    for context in contexts:
        payload = states.get(context.key)
        if payload is None:
            continue
        state = ParticipantAutonomousExecutionStateModel.model_validate(payload)
        # Exactly the one reservation this batch added is withdrawn. Clearing the
        # aggregate instead would erase in-flight work a previous batch is still
        # accounting for, since `_due_contexts` does not require `in_flight == 0`.
        states[context.key] = state.model_copy(
            update={
                "in_flight": state.in_flight - 1,
                "attempted_actions": state.attempted_actions - 1,
            }
        ).model_dump(mode="json")
    run.working = run.working.with_entries(
        dict(run.working.entries),
        participant_autonomous_execution_states=states,
    )
    _finish_concurrent_service_state(run, policy_address)


def _finish_concurrent_service_state(
    run: SchedulerRunState,
    policy_address: str,
) -> None:
    services = dict(run.working.participant_execution_services)
    payload = services.get(policy_address)
    if payload is None:
        return
    service = ParticipantExecutionServiceStateModel.model_validate(payload)
    services[policy_address] = service.model_copy(update={"reserved": 0, "in_flight": 0, "quiescent": True}).model_dump(
        mode="json"
    )
    run.working = run.working.with_entries(
        dict(run.working.entries),
        participant_execution_services=services,
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


def _set_concurrent_failure(run: SchedulerRunState, diagnostic: Diagnostic) -> None:
    run.diagnostics.append(diagnostic)
    run.failure = ApplyResult(
        success=False,
        snapshot=run.working,
        diagnostics=run.diagnostics,
        changed_addresses=list(dict.fromkeys(run.changed)),
    )


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


def _commit_concurrent_result(
    context: _DueActionContext,
    state: ParticipantAutonomousExecutionStateModel,
    request: ParticipantActionAdmissionRequest,
    result: ParticipantActionApplyResult,
    base: RuntimeSnapshot,
    run: SchedulerRunState,
) -> None:
    from .participant_scheduler_operations import _next_action_state

    stale_completion = participant_generation_commit_diagnostic(request, run.working)
    if stale_completion is not None:
        _set_concurrent_failure(run, stale_completion)
        return
    try:
        run.working = _merge_concurrent_action_snapshot(base, run.working, result.snapshot)
    except ValueError as exc:
        _set_concurrent_failure(
            run,
            Diagnostic(
                code="runtime.participant-concurrent-commit-conflict",
                domain="participant",
                address=context.key,
                message=str(exc),
            ),
        )
        return
    protocol_violation = autonomous_action_result_violation(
        request,
        result,
        episode_id=state.episode_id,
        predecessor=base,
    )
    if protocol_violation is not None:
        _set_concurrent_failure(
            run,
            Diagnostic(
                code="runtime.participant-autonomous-action-protocol-invalid",
                domain="participant",
                address=context.participant_address,
                message=protocol_violation,
            ),
        )
        return
    action_result = result.action_result
    action_succeeded = bool(result.success and action_result is not None and action_result.status == "succeeded")
    next_state = _next_action_state(
        context,
        state,
        request,
        action_succeeded=action_succeeded,
        protocol_failure=False,
    ).model_copy(update={"in_flight": 0})
    scheduler_states = dict(run.working.participant_autonomous_execution_states)
    scheduler_states[context.key] = next_state.model_dump(mode="json")
    run.working = run.working.with_entries(
        dict(run.working.entries),
        participant_autonomous_execution_states=scheduler_states,
    )
    run.diagnostics.extend(result.diagnostics)
    run.changed.extend([*result.changed_addresses, context.key])
    if not action_succeeded and context.policy.failure_policy == "stop":
        run.failure = ApplyResult(
            success=False,
            snapshot=run.working,
            diagnostics=run.diagnostics,
            changed_addresses=list(dict.fromkeys(run.changed)),
        )


def _finish_due_policy(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    current_tick: int,
    cadence_ticks: int,
    run: SchedulerRunState,
) -> None:
    from .participant_scheduler_operations import participant_due_context, run_participant_due

    if run.failure is not None:
        return
    if run_policy_due_concurrently(policy, time_model, participant_runtime, current_tick, cadence_ticks, run):
        return
    for participant_address in policy.participant_addresses:
        run_participant_due(
            participant_due_context(
                policy,
                time_model,
                participant_runtime,
                participant_address,
                current_tick,
                cadence_ticks,
            ),
            run,
        )
        if run.failure is not None:
            break


@dataclass(frozen=True)
class _ConcurrentBatch:
    policy: ParticipantAutonomousExecutionRuntime
    time_model: CompiledTimeModel
    participant_runtime: object
    current_tick: int
    cadence_ticks: int
    run: SchedulerRunState
    contexts: list[_DueActionContext]
    states: list[ParticipantAutonomousExecutionStateModel]


def _execute_concurrent_batch(batch: _ConcurrentBatch) -> None:
    batch_method = getattr(batch.participant_runtime, "admit_actions_concurrently", None)
    if not callable(batch_method):
        _unsupported_concurrency_failure(batch.policy, batch.run)
        return
    selected_contexts = tuple(batch.contexts[: batch.policy.max_in_flight])
    selected_states = batch.states[: batch.policy.max_in_flight]
    from .participant_scheduler_operations import _bound_action_request

    requests = tuple(
        _bound_action_request(context, batch.run.working, state)
        for context, state in zip(selected_contexts, selected_states, strict=True)
    )
    _reserve_concurrent_actions(batch.run, selected_contexts)
    base = batch.run.working
    # The batch method is backend-supplied. A raising or miscounting backend is a
    # conformance failure to report, not an exception to leak through the
    # scheduler, and either way the reservations taken above must be released.
    try:
        results = batch_method(requests, base, len(requests))
        result_count = len(results)
    except Exception as exc:  # noqa: BLE001 - backend trust boundary
        _release_concurrent_reservations(batch.run, selected_contexts, batch.policy.address)
        _set_concurrent_failure(
            batch.run,
            Diagnostic(
                code="runtime.participant-concurrent-batch-failed",
                domain="participant",
                address=batch.policy.address,
                # Only the exception type crosses the boundary, matching
                # `_backend_call_failed`: backend messages can carry host paths,
                # credentials, or participant data that must not enter a
                # portable diagnostic.
                message=(f"Backend concurrent participant batch did not complete ({type(exc).__name__})."),
            ),
        )
        return
    if result_count != len(requests):
        _release_concurrent_reservations(batch.run, selected_contexts, batch.policy.address)
        _set_concurrent_failure(
            batch.run,
            Diagnostic(
                code="runtime.participant-concurrent-result-count-invalid",
                domain="participant",
                address=batch.policy.address,
                message=(
                    f"Backend returned {result_count} concurrent participant results for {len(requests)} requests."
                ),
            ),
        )
        return
    for context, state, request, result in zip(selected_contexts, selected_states, requests, results, strict=True):
        _commit_concurrent_result(context, state, request, result, base, batch.run)
        if batch.run.failure is not None:
            break
    _finish_concurrent_service_state(batch.run, batch.policy.address)
    _finish_due_policy(
        batch.policy,
        batch.time_model,
        batch.participant_runtime,
        batch.current_tick,
        batch.cadence_ticks,
        batch.run,
    )


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
    contexts, states = _due_contexts(policy, time_model, participant_runtime, current_tick, cadence_ticks, run)
    enough_due_work = len(contexts) >= 2 and policy.max_in_flight >= 2
    if run.failure is None and not enough_due_work:
        return False
    if run.failure is None:
        _execute_concurrent_batch(
            _ConcurrentBatch(
                policy=policy,
                time_model=time_model,
                participant_runtime=participant_runtime,
                current_tick=current_tick,
                cadence_ticks=cadence_ticks,
                run=run,
                contexts=contexts,
                states=states,
            )
        )
    return run.failure is not None or enough_due_work
