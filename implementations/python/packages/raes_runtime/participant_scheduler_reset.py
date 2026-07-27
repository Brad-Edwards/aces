"""Clock-boundary reset operations for autonomous participant scheduling."""

from __future__ import annotations

from dataclasses import dataclass

from raes_contracts.contracts import ParticipantAutonomousExecutionStateModel
from raes_contracts.participant_episode import ParticipantEpisodeResetRequest
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from raes_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime

from .participant_activity import (
    ParticipantActivityDrawContext,
    ParticipantActivityRandomControl,
    draw_activity_integer,
    next_activity_timing,
)
from .participant_scheduler_time import cadence


@dataclass(frozen=True)
class ClockResetContext:
    policy: ParticipantAutonomousExecutionRuntime
    time_model: CompiledTimeModel
    participant_runtime: object
    segment: int
    current_tick: int
    reset_participants: bool
    activity_control: ParticipantActivityRandomControl | None
    next_tick: int
    timing_disposition: str


def clock_reset_context(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
    participant_runtime: object,
    segment: int,
    current_tick: int,
    reset_participants: bool,
    activity_control: ParticipantActivityRandomControl | None,
) -> ClockResetContext:
    next_tick = current_tick
    if activity_control is None:
        next_tick, cadence_ticks = cadence(policy, time_model)
        if next_tick < current_tick:
            next_tick += ((current_tick - next_tick + cadence_ticks - 1) // cadence_ticks) * cadence_ticks
    return ClockResetContext(
        policy=policy,
        time_model=time_model,
        participant_runtime=participant_runtime,
        segment=segment,
        current_tick=current_tick,
        reset_participants=reset_participants,
        activity_control=activity_control,
        next_tick=next_tick,
        timing_disposition="cadence",
    )


def reset_scheduler_participant(
    context: ClockResetContext,
    snapshot: RuntimeSnapshot,
    participant_address: str,
) -> ApplyResult:
    working = snapshot
    changed: list[str] = []
    if context.reset_participants:
        reset = context.participant_runtime.reset(
            ParticipantEpisodeResetRequest(
                participant_address=participant_address,
                episode_id=f"{participant_address}-autonomous-{context.segment}",
                reason=f"shared clock reset to segment {context.segment}",
            ),
            working,
        )
        if not reset.success:
            return reset
        working = reset.snapshot
        changed.extend(reset.changed_addresses)
    key = f"{context.policy.address}.state.{participant_address}"
    state = ParticipantAutonomousExecutionStateModel.model_validate(
        working.participant_autonomous_execution_states[key]
    )
    next_tick = context.next_tick
    timing_disposition = context.timing_disposition
    burst_size = 1
    if context.activity_control is not None:
        burst_size = draw_activity_integer(
            ParticipantActivityDrawContext(
                policy=context.policy,
                participant_address=participant_address,
                time_segment=context.segment,
                occurrence_ordinal=0,
                control=context.activity_control,
            ),
            local_coordinate=2,
            minimum=1,
            maximum=context.policy.max_burst_size,
        )
        timing = next_activity_timing(
            policy=context.policy,
            time_model=context.time_model,
            participant_address=participant_address,
            time_segment=context.segment,
            occurrence_ordinal=0,
            current_tick=context.current_tick,
            control=context.activity_control,
        )
        next_tick = timing.tick if timing.tick is not None else context.current_tick
        timing_disposition = timing.disposition
    states = dict(working.participant_autonomous_execution_states)
    states[key] = state.model_copy(
        update={
            "episode_id": working.participant_episode_results[participant_address]["episode_id"],
            "lifecycle_state": "running",
            "time_segment": context.segment,
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
            "burst_size": burst_size,
            "next_timing_disposition": timing_disposition,
        }
    ).model_dump(mode="json")
    working = working.with_entries(
        dict(working.entries),
        participant_autonomous_execution_states=states,
    )
    changed.append(key)
    return ApplyResult(success=True, snapshot=working, changed_addresses=changed)
