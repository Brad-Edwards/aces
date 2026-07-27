"""Single-participant operations used by the autonomous scheduler."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from raes_contracts.contracts import (
    ParticipantAutonomousExecutionStateModel,
    ParticipantTemporalRuntimeContextModel,
)
from raes_contracts.contracts.participant_execution import ParticipantExecutionServiceStateModel
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_binding import ParticipantActionAdmissionRequest
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from raes_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime

from .participant_action_validation import autonomous_action_result_violation
from .participant_activity import (
    ParticipantActivityRandomControl,
    activity_control_for,
    draw_activity_integer,
    next_activity_timing,
    select_activity_candidate,
)
from .participant_activity_support import (
    activity_attempt_id,
    activity_eligible_indices,
    annotate_activity_history,
    persist_activity_state,
)
from .participant_scheduler_concurrency import participant_generation_commit_diagnostic, run_policy_due_concurrently
from .participant_scheduler_resources import (
    commit_activity_resources,
    measurement_requirements,
    reserve_activity_resources,
)
from .participant_scheduler_time import cadence_missed_result, clock_coordinate, participant_time_domain
from .participant_scheduler_types import SchedulerRunState, _DueActionContext


def _bound_action_request(
    context: _DueActionContext,
    working: RuntimeSnapshot,
    state: ParticipantAutonomousExecutionStateModel,
) -> ParticipantActionAdmissionRequest:
    policy = context.policy
    action_address = policy.action_contract_addresses[state.next_action_index % len(policy.action_contract_addresses)]
    if policy.profile in {
        "participant-autonomous-execution/v2",
        "participant-autonomous-execution/v3",
    }:
        action_instance_id = activity_attempt_id(
            policy_address=policy.address,
            participant_address=context.participant_address,
            episode_id=state.episode_id,
            time_segment=state.time_segment,
            occurrence_ordinal=state.occurrence_ordinal,
            retry_ordinal=state.current_retry,
        )
    else:
        action_instance_id = f"{policy.address}:{context.participant_address}:{state.attempted_actions}"
    segment, _ = clock_coordinate(working, policy.clock_address)
    temporal_contexts = tuple(
        ParticipantTemporalRuntimeContextModel(
            temporal_contract_id=constraint_address,
            time_domain=participant_time_domain(policy, context.time_model),
            clock_authority=policy.clock_address,
            event_points=["submit", "start", "end", "observed"],
            observation_point=f"{policy.clock_address}@segment={segment},tick={context.current_tick}",
            reset_boundary=f"{policy.clock_address}:segment={segment}",
        )
        for constraint_address in policy.temporal_constraint_addresses
    )
    request = context.participant_runtime.bind_autonomous_action(
        context.participant_address,
        action_address,
        policy.observation_boundary_address,
        policy.participant_implementation_ref,
        action_instance_id,
        temporal_contexts,
        working,
    )
    if request.implementation_selection.manifest_ref != policy.participant_implementation_ref:
        raise ValueError("participant implementation selection does not match the autonomous execution policy")
    matching_bindings = tuple(
        binding for binding in policy.execution_bindings if binding.action_contract_address == action_address
    )
    if len(matching_bindings) != 1:
        raise ValueError("autonomous participant action must resolve exactly one execution binding")
    service_payload = working.participant_execution_services.get(policy.address)
    if service_payload is None:
        raise ValueError("autonomous participant action requires execution-service state")
    service = ParticipantExecutionServiceStateModel.model_validate(service_payload)
    return cast(
        ParticipantActionAdmissionRequest,
        replace(
            request,
            participant_address=context.participant_address,
            action_contract_address=action_address,
            observation_boundary_address=policy.observation_boundary_address,
            action_instance_id=action_instance_id,
            temporal_contexts=temporal_contexts,
            action_result=None,
            post_state_digest=None,
            requires_terminal_outcome=True,
            target_addresses=matching_bindings[0].target_addresses,
            execution_scope_ref=policy.address,
            execution_generation=service.generation,
            resource_measurement_requirements=measurement_requirements(policy),
        ),
    )


def _record_protocol_result(
    run: SchedulerRunState,
    context: _DueActionContext,
    predecessor: RuntimeSnapshot,
    result: object,
    protocol_violation: str | None,
) -> bool:
    if isinstance(result, ApplyResult):
        run.diagnostics.extend(result.diagnostics)
    if protocol_violation is None:
        run.working = result.snapshot
        return False
    run.diagnostics.append(
        Diagnostic(
            code="runtime.participant-autonomous-action-protocol-invalid",
            domain="participant",
            address=context.participant_address,
            message=protocol_violation,
        )
    )
    run.working = predecessor
    return True


def _next_action_state(
    context: _DueActionContext,
    state: ParticipantAutonomousExecutionStateModel,
    request: ParticipantActionAdmissionRequest,
    *,
    action_succeeded: bool,
    protocol_failure: bool,
) -> ParticipantAutonomousExecutionStateModel:
    policy = context.policy
    attempted = state.attempted_actions + 1
    lifecycle = state.lifecycle_state
    if protocol_failure or (not action_succeeded and policy.failure_policy == "stop"):
        lifecycle = "failed"
    elif attempted >= policy.max_action_attempts:
        lifecycle = "completed"
    return state.model_copy(
        update={
            "lifecycle_state": lifecycle,
            "next_tick": state.next_tick + context.cadence_ticks,
            "next_action_index": (state.next_action_index + 1) % len(policy.action_contract_addresses),
            "attempted_actions": attempted,
            "succeeded_actions": state.succeeded_actions + (1 if action_succeeded else 0),
            "failed_actions": state.failed_actions + (0 if action_succeeded else 1),
            "last_action_instance_id": request.action_instance_id,
        }
    )


def _run_one_due_action(
    context: _DueActionContext,
    state: ParticipantAutonomousExecutionStateModel,
    run: SchedulerRunState,
) -> ParticipantAutonomousExecutionStateModel:
    request = _bound_action_request(context, run.working, state)
    predecessor = run.working
    result = context.participant_runtime.admit_action(request, predecessor)
    stale_completion = participant_generation_commit_diagnostic(request, run.working)
    if stale_completion is not None:
        run.diagnostics.append(stale_completion)
        run.failure = ApplyResult(
            success=False,
            snapshot=run.working,
            diagnostics=run.diagnostics,
            changed_addresses=list(dict.fromkeys(run.changed)),
        )
        return state
    protocol_violation = autonomous_action_result_violation(
        request,
        result,
        episode_id=state.episode_id,
        predecessor=predecessor,
    )
    protocol_failure = _record_protocol_result(run, context, predecessor, result, protocol_violation)
    action_succeeded = bool(
        not protocol_failure
        and result.success
        and result.action_result is not None
        and result.action_result.status == "succeeded"
    )
    next_state = _next_action_state(
        context,
        state,
        request,
        action_succeeded=action_succeeded,
        protocol_failure=protocol_failure,
    )
    states = dict(run.working.participant_autonomous_execution_states)
    states[context.key] = next_state.model_dump(mode="json")
    run.working = run.working.with_entries(
        dict(run.working.entries),
        participant_autonomous_execution_states=states,
    )
    if not protocol_failure:
        run.changed.extend(result.changed_addresses)
    run.changed.append(context.key)
    action_failed_and_stops = not action_succeeded and context.policy.failure_policy == "stop"
    if protocol_failure or action_failed_and_stops:
        run.failure = ApplyResult(
            success=False,
            snapshot=run.working,
            diagnostics=run.diagnostics,
            changed_addresses=list(dict.fromkeys(run.changed)),
        )
    return next_state


def _next_activity_occurrence_state(
    context: _DueActionContext,
    state: ParticipantAutonomousExecutionStateModel,
    request: ParticipantActionAdmissionRequest,
    *,
    action_succeeded: bool,
    failure_class: str | None,
    protocol_failure: bool,
) -> ParticipantAutonomousExecutionStateModel:
    policy = context.policy
    control = context.activity_control
    if control is None:
        raise ValueError("participant activity execution requires a random control")
    index = state.next_action_index
    candidate_id = policy.action_candidate_ids[index]
    attempted = state.attempted_actions + 1
    failed = state.failed_actions + (0 if action_succeeded else 1)
    retryable = (
        not protocol_failure
        and not action_succeeded
        and failure_class in policy.action_candidate_retry_failure_classes[index]
        and state.current_retry < policy.action_candidate_max_retries[index]
        and attempted < policy.max_action_attempts
    )
    if retryable:
        return state.model_copy(
            update={
                "next_tick": context.current_tick,
                "attempted_actions": attempted,
                "failed_actions": failed,
                "current_retry": state.current_retry + 1,
                "last_candidate_id": candidate_id,
                "last_action_instance_id": request.action_instance_id,
            }
        )

    completed = list(state.completed_candidate_ids)
    if action_succeeded and candidate_id not in completed:
        completed.append(candidate_id)
    cooldowns = dict(state.candidate_cooldown_until)
    cooldowns[candidate_id] = context.current_tick + policy.action_candidate_cooldown_ticks[index]
    occurrence = state.occurrence_ordinal + 1
    lifecycle = state.lifecycle_state
    if protocol_failure or (not action_succeeded and policy.failure_policy == "stop"):
        lifecycle = "failed"
    elif occurrence >= policy.max_occurrences or attempted >= policy.max_action_attempts:
        lifecycle = "completed"

    burst_position = state.burst_position
    burst_size = state.burst_size
    next_tick = context.current_tick
    if lifecycle == "running":
        if burst_position + 1 < burst_size:
            burst_position += 1
        else:
            burst_position = 0
            burst_size = draw_activity_integer(
                policy=policy,
                participant_address=context.participant_address,
                time_segment=state.time_segment,
                occurrence_ordinal=occurrence,
                control=control,
                local_coordinate=2,
                minimum=1,
                maximum=policy.max_burst_size,
            )
            timing = next_activity_timing(
                policy=policy,
                time_model=context.time_model,
                participant_address=context.participant_address,
                time_segment=state.time_segment,
                occurrence_ordinal=occurrence,
                current_tick=context.current_tick,
                control=control,
            )
            selected_tick = timing.tick
            if selected_tick is None:
                lifecycle = "completed"
            else:
                next_tick = selected_tick
    return state.model_copy(
        update={
            "lifecycle_state": lifecycle,
            "next_tick": next_tick,
            "attempted_actions": attempted,
            "succeeded_actions": state.succeeded_actions + (1 if action_succeeded else 0),
            "failed_actions": failed,
            "occurrence_ordinal": occurrence,
            "current_retry": 0,
            "burst_position": burst_position,
            "burst_size": burst_size,
            "last_candidate_id": candidate_id,
            "completed_candidate_ids": completed,
            "candidate_cooldown_until": cooldowns,
            "last_action_instance_id": request.action_instance_id,
            "next_timing_disposition": (
                timing.disposition if lifecycle == "running" and burst_position == 0 else state.next_timing_disposition
            ),
        }
    )


def _run_one_activity_action(
    context: _DueActionContext,
    state: ParticipantAutonomousExecutionStateModel,
    run: SchedulerRunState,
) -> ParticipantAutonomousExecutionStateModel:
    request = _bound_action_request(context, run.working, state)
    if not reserve_activity_resources(context, request, run):
        return state
    predecessor = run.working
    result = context.participant_runtime.admit_action(request, predecessor)
    protocol_violation = autonomous_action_result_violation(
        request,
        result,
        episode_id=state.episode_id,
        predecessor=predecessor,
    )
    protocol_failure = _record_protocol_result(run, context, predecessor, result, protocol_violation)
    if not commit_activity_resources(
        context,
        request,
        result,
        protocol_failure=protocol_failure,
        run=run,
    ):
        return state
    action_result = getattr(result, "action_result", None)
    status = getattr(getattr(action_result, "status", None), "value", getattr(action_result, "status", None))
    action_succeeded = bool(not protocol_failure and result.success and status == "succeeded")
    failure_value = getattr(
        getattr(action_result, "failure_class", None),
        "value",
        getattr(action_result, "failure_class", None),
    )
    if not protocol_failure:
        annotate_activity_history(
            run,
            context,
            state,
            request,
            str(status or "unknown"),
        )
    next_state = _next_activity_occurrence_state(
        context,
        state,
        request,
        action_succeeded=action_succeeded,
        failure_class=str(failure_value) if failure_value is not None else None,
        protocol_failure=protocol_failure,
    )
    persist_activity_state(run, context.key, next_state)
    if not protocol_failure:
        run.changed.extend(result.changed_addresses)
    if next_state.lifecycle_state == "failed":
        run.failure = ApplyResult(
            success=False,
            snapshot=run.working,
            diagnostics=run.diagnostics,
            changed_addresses=list(dict.fromkeys(run.changed)),
        )
    return next_state


def _run_participant_activity_due(
    context: _DueActionContext,
    state: ParticipantAutonomousExecutionStateModel,
    run: SchedulerRunState,
) -> None:
    while (
        state.lifecycle_state == "running"
        and state.next_tick == context.current_tick
        and state.attempted_actions < context.policy.max_action_attempts
        and run.failure is None
    ):
        eligible = activity_eligible_indices(context.policy, state, context.current_tick)
        control = context.activity_control
        if control is None:
            raise ValueError("participant activity execution requires a random control")
        selected = (
            state.next_action_index
            if state.current_retry
            else select_activity_candidate(
                policy=context.policy,
                participant_address=context.participant_address,
                time_segment=state.time_segment,
                occurrence_ordinal=state.occurrence_ordinal,
                control=control,
                eligible_indices=eligible,
            )
        )
        if selected is None:
            lifecycle = "completed" if context.policy.empty_eligible_disposition == "complete" else "running"
            selected_tick = (
                None
                if lifecycle == "completed"
                else next_activity_timing(
                    policy=context.policy,
                    time_model=context.time_model,
                    participant_address=context.participant_address,
                    time_segment=state.time_segment,
                    occurrence_ordinal=state.occurrence_ordinal,
                    current_tick=context.current_tick,
                    control=control,
                ).tick
            )
            if selected_tick is None:
                lifecycle = "completed"
            state = state.model_copy(
                update={
                    "lifecycle_state": lifecycle,
                    "next_tick": selected_tick if selected_tick is not None else context.current_tick,
                }
            )
            persist_activity_state(run, context.key, state)
            return
        state = state.model_copy(update={"next_action_index": selected})
        state = _run_one_activity_action(context, state, run)


def run_participant_due(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    participant_address: str,
    current_tick: int,
    cadence_ticks: int,
    run: SchedulerRunState,
    activity_controls: dict[str, ParticipantActivityRandomControl] | None = None,
) -> None:
    """Run one participant at the current governed cadence boundary."""

    key = f"{policy.address}.state.{participant_address}"
    state = ParticipantAutonomousExecutionStateModel.model_validate(
        run.working.participant_autonomous_execution_states[key]
    )
    if state.lifecycle_state == "running" and state.next_tick < current_tick:
        run.failure = cadence_missed_result(run.working, key, current_tick, state)
        return
    action_context = _DueActionContext(
        policy=policy,
        time_model=time_model,
        participant_runtime=participant_runtime,
        participant_address=participant_address,
        key=key,
        current_tick=current_tick,
        cadence_ticks=cadence_ticks,
        activity_control=activity_control_for(policy, activity_controls or {}),
    )
    if policy.profile in {
        "participant-autonomous-execution/v2",
        "participant-autonomous-execution/v3",
    }:
        _run_participant_activity_due(action_context, state, run)
        return
    action_is_due = (
        state.lifecycle_state == "running"
        and state.next_tick == current_tick
        and state.attempted_actions < policy.max_action_attempts
    )
    while action_is_due and run.failure is None:
        state = _run_one_due_action(action_context, state, run)
        action_is_due = (
            state.lifecycle_state == "running"
            and state.next_tick == current_tick
            and state.attempted_actions < policy.max_action_attempts
        )


__all__ = [
    "SchedulerRunState",
    "run_participant_due",
    "run_policy_due_concurrently",
]
