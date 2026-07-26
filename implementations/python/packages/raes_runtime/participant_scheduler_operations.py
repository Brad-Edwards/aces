"""Single-participant operations used by the autonomous scheduler."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import cast

from raes_contracts.contracts import (
    ParticipantAutonomousExecutionStateModel,
    ParticipantTemporalRuntimeContextModel,
)
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_binding import ParticipantActionAdmissionRequest
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from raes_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime

from .participant_action_validation import autonomous_action_result_violation


def clock_coordinate(snapshot: RuntimeSnapshot, clock_address: str) -> tuple[int, int]:
    """Read one shared clock coordinate or fail closed."""

    if snapshot.time_model_state is None:
        raise ValueError("autonomous participant execution requires typed shared-time state")
    clock = snapshot.time_model_state.clocks.get(clock_address)
    if clock is None:
        raise ValueError(f"autonomous participant clock {clock_address!r} has no runtime state")
    return clock.coordinate.segment, clock.coordinate.tick


def _time_domain(policy: ParticipantAutonomousExecutionRuntime, time_model: CompiledTimeModel) -> str:
    clock = next(item for item in time_model.clocks if item.address == policy.clock_address)
    domain = next(item for item in time_model.domains if item.address == clock.time_domain_address)
    return {
        "wall_clock": "wall_clock_time",
        "simulated": "simulation_time",
        "logical": "scenario_time",
        "monotonic": "scenario_time",
        "external": "backend_time",
    }[domain.kind]


@dataclass
class SchedulerRunState:
    """Mutable aggregate for one deterministic scheduler pass."""

    working: RuntimeSnapshot
    diagnostics: list[Diagnostic]
    changed: list[str]
    failure: ApplyResult | None = None

    def result(self) -> ApplyResult:
        return self.failure or ApplyResult(
            success=True,
            snapshot=self.working,
            diagnostics=self.diagnostics,
            changed_addresses=list(dict.fromkeys(self.changed)),
        )


@dataclass(frozen=True)
class _DueActionContext:
    policy: ParticipantAutonomousExecutionRuntime
    time_model: CompiledTimeModel
    participant_runtime: object
    participant_address: str
    key: str
    current_tick: int
    cadence_ticks: int


def _cadence_missed_result(
    working: RuntimeSnapshot,
    key: str,
    current_tick: int,
    state: ParticipantAutonomousExecutionStateModel,
) -> ApplyResult:
    return ApplyResult(
        success=False,
        snapshot=working,
        diagnostics=[
            Diagnostic(
                code="runtime.participant-autonomous-cadence-missed",
                domain="participant",
                address=key,
                message=(
                    f"Shared clock is at tick {current_tick}, after the next governed "
                    f"participant cadence tick {state.next_tick}."
                ),
            )
        ],
    )


def _bound_action_request(
    context: _DueActionContext,
    working: RuntimeSnapshot,
    state: ParticipantAutonomousExecutionStateModel,
) -> ParticipantActionAdmissionRequest:
    policy = context.policy
    action_address = policy.action_contract_addresses[state.next_action_index % len(policy.action_contract_addresses)]
    action_instance_id = f"{policy.address}:{context.participant_address}:{state.attempted_actions}"
    segment, _ = clock_coordinate(working, policy.clock_address)
    temporal_contexts = tuple(
        ParticipantTemporalRuntimeContextModel(
            temporal_contract_id=constraint_address,
            time_domain=_time_domain(policy, context.time_model),
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


def run_participant_due(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    participant_address: str,
    current_tick: int,
    cadence_ticks: int,
    run: SchedulerRunState,
) -> None:
    """Run one participant at the current governed cadence boundary."""

    key = f"{policy.address}.state.{participant_address}"
    state = ParticipantAutonomousExecutionStateModel.model_validate(
        run.working.participant_autonomous_execution_states[key]
    )
    if state.lifecycle_state == "running" and state.next_tick < current_tick:
        run.failure = _cadence_missed_result(run.working, key, current_tick, state)
        return
    action_context = _DueActionContext(
        policy=policy,
        time_model=time_model,
        participant_runtime=participant_runtime,
        participant_address=participant_address,
        key=key,
        current_tick=current_tick,
        cadence_ticks=cadence_ticks,
    )
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


__all__ = ["SchedulerRunState", "clock_coordinate", "run_participant_due"]
