"""Bounded concurrent native execution and serialized participant commits."""

from __future__ import annotations

from asyncio import CancelledError
from copy import deepcopy
from typing import TYPE_CHECKING

from raes_contracts.contracts import ParticipantAutonomousExecutionStateModel
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_binding import ParticipantActionAdmissionRequest
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
    from raes_processor.models import ParticipantExecutionBindingRuntime

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


def _execution_binding_for_state(
    context: _DueActionContext,
    state: ParticipantAutonomousExecutionStateModel,
) -> ParticipantExecutionBindingRuntime | None:
    policy = context.policy
    action_address = policy.action_contract_addresses[state.next_action_index % len(policy.action_contract_addresses)]
    bindings = tuple(
        binding
        for binding in getattr(policy, "execution_bindings", ())
        if binding.action_contract_address == action_address
    )
    if not bindings:
        # Unit-level scheduler doubles created before semantic binding metadata
        # existed represent an action with no declared interaction footprint.
        return None
    if len(bindings) != 1:
        raise ValueError("concurrent participant action must resolve exactly one execution binding")
    return bindings[0]


def _bindings_semantically_conflict(
    left: ParticipantExecutionBindingRuntime | None,
    right: ParticipantExecutionBindingRuntime | None,
) -> bool:
    if left is None or right is None:
        return False
    left_related = set(left.related_action_contract_addresses)
    right_related = set(right.related_action_contract_addresses)
    if right.action_contract_address in left_related or left.action_contract_address in right_related:
        related_commutes = right.action_contract_address in set(
            left.commutative_related_action_contract_addresses
        ) and left.action_contract_address in set(right.commutative_related_action_contract_addresses)
        left_related_rules = dict(left.related_action_merge_rules)
        right_related_rules = dict(right.related_action_merge_rules)
        related_rule_matches = left_related_rules.get(
            right.action_contract_address
        ) is not None and left_related_rules.get(right.action_contract_address) == right_related_rules.get(
            left.action_contract_address
        )
        if not related_commutes and not related_rule_matches:
            return True
    shared_overlap = set(left.shared_state_refs) & set(right.shared_state_refs)
    commutative_overlap = set(left.commutative_shared_state_refs) & set(right.commutative_shared_state_refs)
    left_shared_rules = dict(left.shared_state_merge_rules)
    right_shared_rules = dict(right.shared_state_merge_rules)
    authorized_rule_refs = {
        ref
        for ref in shared_overlap
        if left_shared_rules.get(ref) is not None and left_shared_rules.get(ref) == right_shared_rules.get(ref)
    }
    return bool(shared_overlap - commutative_overlap - authorized_rule_refs)


def _semantically_independent_prefix_size(
    contexts: list[_DueActionContext],
    states: list[ParticipantAutonomousExecutionStateModel],
    *,
    offset: int,
    limit: int,
) -> int:
    """Return the largest deterministic prefix with no declared interaction conflict.

    Conflicting actions remain on the serialized path unless their authored
    interaction footprints declare commutativity or the same governed merge
    rule.
    """

    selected_bindings: list[ParticipantExecutionBindingRuntime | None] = []
    for context, state in zip(
        contexts[offset : offset + limit],
        states[offset : offset + limit],
        strict=True,
    ):
        candidate = _execution_binding_for_state(context, state)
        if any(_bindings_semantically_conflict(candidate, prior) for prior in selected_bindings):
            break
        selected_bindings.append(candidate)
    return len(selected_bindings)


def _bind_concurrent_policy_requests(
    policy: ParticipantAutonomousExecutionRuntime,
    run: SchedulerRunState,
    contexts: list[_DueActionContext],
    states: list[ParticipantAutonomousExecutionStateModel],
) -> list[ParticipantActionAdmissionRequest] | None:
    """Bind the same-tick due set once against one isolated predecessor."""

    from .participant_scheduler_operations import _bound_action_request

    pre_policy = run.working
    try:
        binding_snapshot = deepcopy(pre_policy)
        requests = [
            _bound_action_request(context, binding_snapshot, state)
            for context, state in zip(contexts, states, strict=True)
        ]
        if binding_snapshot != pre_policy:
            raise ValueError("participant request binding mutated its predecessor")
        return requests
    except (Exception, CancelledError):  # NOSONAR - no native action has been submitted
        run.working = pre_policy
        _set_concurrent_failure(
            run,
            Diagnostic(
                code="runtime.participant-concurrent-binding-failed",
                domain="participant",
                address=policy.address,
                message="Backend concurrent participant request binding did not complete.",
            ),
        )
        return None


def _execute_capacity_bounded_batches(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    current_tick: int,
    cadence_ticks: int,
    run: SchedulerRunState,
    contexts: list[_DueActionContext],
    due_states: list[ParticipantAutonomousExecutionStateModel],
    requests: list[ParticipantActionAdmissionRequest],
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
        batch_size = _semantically_independent_prefix_size(
            contexts,
            due_states,
            offset=offset,
            limit=min(available, len(contexts) - offset),
        )
        if batch_size < 2:
            break
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
                requests=tuple(requests[offset : offset + batch_size]),
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
    due_states: list[ParticipantAutonomousExecutionStateModel],
) -> None:
    if not _isolate_concurrent_policy_snapshot(policy, run):
        return
    requests = _bind_concurrent_policy_requests(policy, run, contexts, due_states)
    if requests is None:
        return
    offset = _execute_capacity_bounded_batches(
        policy,
        time_model,
        participant_runtime,
        current_tick,
        cadence_ticks,
        run,
        contexts,
        due_states,
        requests,
    )

    if run.failure is None:
        try:
            run.working = _materialize_concurrent_snapshot(run.working)
        except (Exception, CancelledError):  # NOSONAR - normalize the deferred batch boundary
            _set_concurrent_failure(
                run,
                Diagnostic(
                    code="runtime.participant-concurrent-commit-invalid",
                    domain="participant",
                    address=policy.address,
                    message="Concurrent participant batch state failed final invariant validation.",
                ),
            )
            return
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
    contexts, states = _due_contexts(policy, time_model, participant_runtime, current_tick, cadence_ticks, run)
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
            states,
        )
    return handled
