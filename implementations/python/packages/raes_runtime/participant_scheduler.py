"""Shared-clock scheduler for autonomous ordinary participants."""

from __future__ import annotations

from collections.abc import Iterable

from raes_contracts.contracts import (
    ParticipantAutonomousExecutionStateModel,
)
from raes_contracts.contracts.participant_execution import ParticipantExecutionServiceStateModel
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_episode import (
    ParticipantEpisodeInitializeRequest,
)
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from raes_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime

from .participant_activity import (
    ParticipantActivityRandomControl,
    activity_control_for,
    draw_activity_integer,
    next_activity_timing,
)
from .participant_execution_scheduler_state import (
    execution_service_state,
    reset_execution_service,
    set_execution_clock_lifecycle,
)
from .participant_scheduler_operations import (
    SchedulerRunState,
    run_participant_due,
    run_policy_due_concurrently,
)
from .participant_scheduler_policy import _policy_digest
from .participant_scheduler_reset import clock_reset_context, reset_scheduler_participant
from .participant_scheduler_time import cadence as _cadence
from .participant_scheduler_time import clock_coordinate


def _state_key(policy_address: str, participant_address: str) -> str:
    return f"{policy_address}.state.{participant_address}"


def _clock_tick(snapshot: RuntimeSnapshot, clock_address: str) -> int:
    if snapshot.time_model_state is None:
        raise ValueError("autonomous participant execution requires typed shared-time state")
    clock = snapshot.time_model_state.clocks.get(clock_address)
    if clock is None:
        raise ValueError(f"autonomous participant clock {clock_address!r} has no runtime state")
    return clock.coordinate.tick


def _state_identity(state: ParticipantAutonomousExecutionStateModel) -> tuple[object, ...]:
    return (
        state.policy_address,
        state.policy_digest,
        state.participant_address,
        state.episode_id,
        state.participant_implementation_ref,
        state.clock_address,
        state.time_segment,
        state.profile,
        state.random_control_id,
        state.random_profile_id,
        state.random_namespace,
    )


def _initialize_participant(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    snapshot: RuntimeSnapshot,
    participant_address: str,
    activity_controls: dict[str, ParticipantActivityRandomControl],
) -> ApplyResult:
    working = snapshot
    changed: list[str] = []
    if participant_address not in working.participant_episode_results:
        result = participant_runtime.initialize(
            ParticipantEpisodeInitializeRequest(
                participant_address=participant_address,
                episode_id=f"{participant_address}-autonomous-0",
            ),
            working,
        )
        if not result.success:
            return result
        working = result.snapshot
        changed.extend(result.changed_addresses)
    key = _state_key(policy.address, participant_address)
    segment, _ = clock_coordinate(working, policy.clock_address)
    activity_control = activity_control_for(policy, activity_controls)
    if policy.profile == "participant-autonomous-execution/v2" and activity_control is None:
        return ApplyResult(
            success=False,
            snapshot=working,
            diagnostics=[
                Diagnostic(
                    code="runtime.participant-activity-control-unbound",
                    domain="participant",
                    address=policy.address,
                    message=(
                        f"Participant activity policy requires admitted stochastic control "
                        f"{policy.stochastic_control_ref!r}."
                    ),
                )
            ],
        )
    if activity_control is None:
        first_tick, _ = _cadence(policy, time_model)
        burst_size = 1
        timing_disposition = "cadence"
    else:
        current_tick = _clock_tick(working, policy.clock_address)
        burst_size = draw_activity_integer(
            policy=policy,
            participant_address=participant_address,
            time_segment=segment,
            occurrence_ordinal=0,
            control=activity_control,
            local_coordinate=2,
            minimum=1,
            maximum=policy.max_burst_size,
        )
        timing = next_activity_timing(
            policy=policy,
            time_model=time_model,
            participant_address=participant_address,
            time_segment=segment,
            occurrence_ordinal=0,
            current_tick=current_tick,
            control=activity_control,
        )
        first_tick = timing.tick
        timing_disposition = timing.disposition
    expected = ParticipantAutonomousExecutionStateModel(
        policy_address=policy.address,
        policy_digest=_policy_digest(policy, time_model),
        participant_address=participant_address,
        episode_id=working.participant_episode_results[participant_address]["episode_id"],
        participant_implementation_ref=policy.participant_implementation_ref,
        clock_address=policy.clock_address,
        time_segment=segment,
        lifecycle_state="running" if first_tick is not None else "completed",
        next_tick=first_tick if first_tick is not None else _clock_tick(working, policy.clock_address),
        next_action_index=0,
        attempted_actions=0,
        succeeded_actions=0,
        failed_actions=0,
        profile=policy.profile,
        random_control_id=activity_control.control_id if activity_control is not None else None,
        random_profile_id=activity_control.profile_id if activity_control is not None else None,
        random_namespace=activity_control.namespace if activity_control is not None else None,
        burst_size=burst_size,
        next_timing_disposition=timing_disposition,
    )
    states = dict(working.participant_autonomous_execution_states)
    if key in states and _state_identity(ParticipantAutonomousExecutionStateModel.model_validate(states[key])) != (
        _state_identity(expected)
    ):
        return ApplyResult(
            success=False,
            snapshot=working,
            diagnostics=[
                Diagnostic(
                    code="runtime.participant-autonomous-state-conflict",
                    domain="participant",
                    address=policy.address,
                    message="Existing autonomous participant state does not match the compiled policy.",
                )
            ],
        )
    if key not in states:
        states[key] = expected.model_dump(mode="json")
        working = working.with_entries(
            dict(working.entries),
            participant_autonomous_execution_states=states,
        )
        changed.append(key)
    return ApplyResult(success=True, snapshot=working, changed_addresses=changed)


def _missing_execution_service_result(
    policy: ParticipantAutonomousExecutionRuntime,
    run: SchedulerRunState,
) -> ApplyResult:
    return ApplyResult(
        success=False,
        snapshot=run.working,
        diagnostics=[
            Diagnostic(
                code="runtime.participant-execution-state-missing",
                domain="participant",
                address=policy.address,
                message="Autonomous participant execution requires typed execution-service state.",
            )
        ],
    )


def _execution_service_accepts_work(service: ParticipantExecutionServiceStateModel) -> bool:
    return service.observed_lifecycle == "running" and service.accepting_new_work and service.readiness == "ready"


def _run_serial_due(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    current_tick: int,
    cadence_ticks: int,
    activity_controls: dict[str, ParticipantActivityRandomControl],
    run: SchedulerRunState,
) -> None:
    for participant_address in policy.participant_addresses:
        run_participant_due(
            policy,
            time_model,
            participant_runtime,
            participant_address,
            current_tick,
            cadence_ticks,
            run,
            activity_controls,
        )
        if run.failure is not None:
            break


def _run_due_policy(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    activity_controls: dict[str, ParticipantActivityRandomControl],
    run: SchedulerRunState,
) -> None:
    service_payload = run.working.participant_execution_services.get(policy.address)
    if service_payload is None:
        run.failure = _missing_execution_service_result(policy, run)
        return
    service = ParticipantExecutionServiceStateModel.model_validate(service_payload)
    if not _execution_service_accepts_work(service):
        return
    cadence_ticks = _cadence(policy, time_model)[1] if policy.profile == "participant-autonomous-execution/v1" else 0
    current_tick = _clock_tick(run.working, policy.clock_address)
    if not run_policy_due_concurrently(policy, time_model, participant_runtime, current_tick, cadence_ticks, run):
        _run_serial_due(policy, time_model, participant_runtime, current_tick, cadence_ticks, activity_controls, run)


class ParticipantScheduler:
    """Deterministically selects due actions and delegates native execution."""

    @staticmethod
    def initialize(
        policies: Iterable[ParticipantAutonomousExecutionRuntime],
        time_model: CompiledTimeModel,
        participant_runtime: object,
        snapshot: RuntimeSnapshot,
        activity_controls: dict[str, ParticipantActivityRandomControl] | None = None,
    ) -> ApplyResult:
        working = snapshot
        resolved_activity_controls = activity_controls or {}
        changed: list[str] = []
        for policy in policies:
            for participant_address in policy.participant_addresses:
                result = _initialize_participant(
                    policy,
                    time_model,
                    participant_runtime,
                    working,
                    participant_address,
                    resolved_activity_controls,
                )
                if not result.success:
                    return result
                working = result.snapshot
                changed.extend(result.changed_addresses)
            services = dict(working.participant_execution_services)
            expected_service = execution_service_state(
                policy,
                time_model,
                policy_digest=_policy_digest(policy, time_model),
            )
            existing_service = services.get(policy.address)
            if existing_service is not None:
                existing = ParticipantExecutionServiceStateModel.model_validate(existing_service)
                if (
                    existing.policy_digest != expected_service.policy_digest
                    or existing.binding_digest != expected_service.binding_digest
                    or existing.time_declaration_digest != expected_service.time_declaration_digest
                ):
                    return ApplyResult(
                        success=False,
                        snapshot=working,
                        diagnostics=[
                            Diagnostic(
                                code="runtime.participant-execution-state-conflict",
                                domain="participant",
                                address=policy.address,
                                message=(
                                    "Existing participant execution service state "
                                    "does not match the admitted policy, bindings, "
                                    "or shared-time declaration."
                                ),
                            )
                        ],
                    )
            else:
                services[policy.address] = expected_service.model_dump(mode="json")
                working = working.with_entries(
                    dict(working.entries),
                    participant_execution_services=services,
                )
                changed.append(policy.address)
        return ApplyResult(
            success=True,
            snapshot=working,
            changed_addresses=list(dict.fromkeys(changed)),
        )

    @staticmethod
    def run_due(
        policies: Iterable[ParticipantAutonomousExecutionRuntime],
        time_model: CompiledTimeModel,
        participant_runtime: object,
        snapshot: RuntimeSnapshot,
        activity_controls: dict[str, ParticipantActivityRandomControl] | None = None,
    ) -> ApplyResult:
        run = SchedulerRunState(working=snapshot, diagnostics=[], changed=[])
        resolved_activity_controls = activity_controls or {}
        for policy in policies:
            _run_due_policy(policy, time_model, participant_runtime, resolved_activity_controls, run)
            if run.failure is not None:
                break
        return run.result()

    @staticmethod
    def reset_clock(
        policies: Iterable[ParticipantAutonomousExecutionRuntime],
        time_model: CompiledTimeModel,
        participant_runtime: object,
        snapshot: RuntimeSnapshot,
        clock_address: str,
        *,
        reset_participants: bool = True,
        activity_controls: dict[str, ParticipantActivityRandomControl] | None = None,
    ) -> ApplyResult:
        """Reset bound episodes and scheduler counters at a shared-clock segment boundary."""

        working = snapshot
        resolved_activity_controls = activity_controls or {}
        changed: list[str] = []
        segment, _ = clock_coordinate(snapshot, clock_address)
        for policy in policies:
            if policy.clock_address != clock_address:
                continue
            current_tick = _clock_tick(snapshot, clock_address)
            activity_control = activity_control_for(policy, resolved_activity_controls)
            context = clock_reset_context(
                policy,
                time_model,
                participant_runtime,
                segment,
                current_tick,
                reset_participants,
                activity_control,
            )
            for participant_address in policy.participant_addresses:
                result = reset_scheduler_participant(context, working, participant_address)
                if not result.success:
                    return result
                working = result.snapshot
                changed.extend(result.changed_addresses)
            working, service_changed = reset_execution_service(
                working,
                policy.address,
            )
            if service_changed:
                changed.append(policy.address)
        return ApplyResult(
            success=True,
            snapshot=working,
            changed_addresses=list(dict.fromkeys(changed)),
        )

    @staticmethod
    def set_clock_lifecycle(
        snapshot: RuntimeSnapshot,
        clock_address: str,
        lifecycle_state: str,
    ) -> ApplyResult:
        return set_execution_clock_lifecycle(
            snapshot,
            clock_address,
            lifecycle_state,
        )


__all__ = ["ParticipantScheduler"]
