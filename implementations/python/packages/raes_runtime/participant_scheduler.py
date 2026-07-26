"""Shared-clock scheduler for autonomous ordinary participants."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict

from raes_contracts.contracts import ParticipantAutonomousExecutionStateModel
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_episode import (
    ParticipantEpisodeInitializeRequest,
    ParticipantEpisodeResetRequest,
)
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from raes_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime

from .participant_activity import (
    ParticipantActivityRandomControl,
    activity_control_for,
    draw_activity_integer,
    next_activity_timing,
)
from .participant_scheduler_operations import (
    SchedulerRunState,
    run_participant_due,
)
from .participant_scheduler_time import clock_coordinate


def _state_key(policy_address: str, participant_address: str) -> str:
    return f"{policy_address}.state.{participant_address}"


def _policy_digest(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
) -> str:
    clock = next(item for item in time_model.clocks if item.address == policy.clock_address)
    progression = next(
        item for item in time_model.progression_policies if item.address == policy.progression_policy_address
    )
    domain = next(item for item in time_model.domains if item.address == clock.time_domain_address)
    constraints = sorted(
        (asdict(item) for item in time_model.constraints if item.address in policy.temporal_constraint_addresses),
        key=lambda item: str(item["address"]),
    )
    payload = {
        "address": policy.address,
        "participant_addresses": policy.participant_addresses,
        "participant_implementation_ref": policy.participant_implementation_ref,
        "clock_address": policy.clock_address,
        "progression_policy_address": policy.progression_policy_address,
        "temporal_constraint_addresses": policy.temporal_constraint_addresses,
        "action_contract_addresses": policy.action_contract_addresses,
        "target_addresses": policy.target_addresses,
        "observation_boundary_address": policy.observation_boundary_address,
        "selection_strategy": policy.selection_strategy,
        "max_action_attempts": policy.max_action_attempts,
        "max_in_flight": policy.max_in_flight,
        "failure_policy": policy.failure_policy,
        "evaluation_authority_mode": policy.evaluation_authority_mode,
        "objective_refs": policy.objective_refs,
        "proof_producer_refs": policy.proof_producer_refs,
        "score_authority_refs": policy.score_authority_refs,
        "receipt_authority_refs": policy.receipt_authority_refs,
        "resolved_clock": asdict(clock),
        "resolved_time_domain": asdict(domain),
        "resolved_progression_policy": asdict(progression),
        "resolved_temporal_constraints": constraints,
    }
    if policy.profile == "participant-autonomous-execution/v2":
        payload.update(
            {
                "profile": policy.profile,
                "work_window_addresses": policy.work_window_addresses,
                "pause_window_addresses": policy.pause_window_addresses,
                "stochastic_control_ref": policy.stochastic_control_ref,
                "timing_minimum_ticks": policy.timing_minimum_ticks,
                "timing_maximum_ticks": policy.timing_maximum_ticks,
                "outside_window_disposition": policy.outside_window_disposition,
                "empty_eligible_disposition": policy.empty_eligible_disposition,
                "action_candidate_ids": policy.action_candidate_ids,
                "action_candidate_weights": policy.action_candidate_weights,
                "action_candidate_dependencies": policy.action_candidate_dependencies,
                "action_candidate_retry_failure_classes": (policy.action_candidate_retry_failure_classes),
                "action_candidate_max_retries": policy.action_candidate_max_retries,
                "action_candidate_cooldown_ticks": policy.action_candidate_cooldown_ticks,
                "max_occurrences": policy.max_occurrences,
                "max_burst_size": policy.max_burst_size,
            }
        )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _clock_tick(snapshot: RuntimeSnapshot, clock_address: str) -> int:
    if snapshot.time_model_state is None:
        raise ValueError("autonomous participant execution requires typed shared-time state")
    clock = snapshot.time_model_state.clocks.get(clock_address)
    if clock is None:
        raise ValueError(f"autonomous participant clock {clock_address!r} has no runtime state")
    return clock.coordinate.tick


def _cadence(policy: ParticipantAutonomousExecutionRuntime, time_model: CompiledTimeModel) -> tuple[int, int]:
    selected = [
        constraint
        for constraint in time_model.constraints
        if constraint.address in policy.temporal_constraint_addresses and constraint.kind == "cadence"
    ]
    if len(selected) != 1 or selected[0].cadence_ticks is None:
        raise ValueError("autonomous participant execution requires exactly one cadence constraint")
    constraint = selected[0]
    return constraint.start_tick or 0, constraint.cadence_ticks


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
            cadence_ticks = (
                _cadence(policy, time_model)[1] if policy.profile == "participant-autonomous-execution/v1" else 0
            )
            current_tick = _clock_tick(run.working, policy.clock_address)
            for participant_address in policy.participant_addresses:
                run_participant_due(
                    policy,
                    time_model,
                    participant_runtime,
                    participant_address,
                    current_tick,
                    cadence_ticks,
                    run,
                    resolved_activity_controls,
                )
                if run.failure is not None:
                    return run.result()
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
            if activity_control is None:
                first_tick, cadence_ticks = _cadence(policy, time_model)
                next_tick = first_tick
                timing_disposition = "cadence"
                if next_tick < current_tick:
                    next_tick += ((current_tick - next_tick + cadence_ticks - 1) // cadence_ticks) * cadence_ticks
            for participant_address in policy.participant_addresses:
                result_changed: list[str] = []
                if reset_participants:
                    result = participant_runtime.reset(
                        ParticipantEpisodeResetRequest(
                            participant_address=participant_address,
                            episode_id=f"{participant_address}-autonomous-{segment}",
                            reason=f"shared clock reset to segment {segment}",
                        ),
                        working,
                    )
                    if not result.success:
                        return result
                    working = result.snapshot
                    result_changed.extend(result.changed_addresses)
                key = _state_key(policy.address, participant_address)
                state = ParticipantAutonomousExecutionStateModel.model_validate(
                    working.participant_autonomous_execution_states[key]
                )
                if activity_control is not None:
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
                    selected_tick = timing.tick
                    timing_disposition = timing.disposition
                    next_tick = selected_tick if selected_tick is not None else current_tick
                states = dict(working.participant_autonomous_execution_states)
                states[key] = state.model_copy(
                    update={
                        "episode_id": working.participant_episode_results[participant_address]["episode_id"],
                        "lifecycle_state": "running",
                        "time_segment": segment,
                        "next_tick": next_tick,
                        "next_action_index": 0,
                        "attempted_actions": 0,
                        "succeeded_actions": 0,
                        "failed_actions": 0,
                        "in_flight": 0,
                        "last_action_instance_id": None,
                        "occurrence_ordinal": 0,
                        "current_retry": 0,
                        "burst_position": 0,
                        "last_candidate_id": None,
                        "completed_candidate_ids": [],
                        "candidate_cooldown_until": {},
                        "burst_size": burst_size if activity_control is not None else 1,
                        "next_timing_disposition": timing_disposition,
                    }
                ).model_dump(mode="json")
                working = working.with_entries(
                    dict(working.entries),
                    participant_autonomous_execution_states=states,
                )
                changed.extend([*result_changed, key])
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
        states = dict(snapshot.participant_autonomous_execution_states)
        changed: list[str] = []
        for key, payload in list(states.items()):
            state = ParticipantAutonomousExecutionStateModel.model_validate(payload)
            if state.clock_address == clock_address and state.lifecycle_state not in {"completed", "failed"}:
                states[key] = state.model_copy(update={"lifecycle_state": lifecycle_state}).model_dump(mode="json")
                changed.append(key)
        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(
                dict(snapshot.entries),
                participant_autonomous_execution_states=states,
            ),
            changed_addresses=changed,
        )


__all__ = ["ParticipantScheduler"]
