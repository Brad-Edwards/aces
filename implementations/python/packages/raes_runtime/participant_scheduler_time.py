"""Shared-time helpers for autonomous participant scheduling."""

from raes_contracts.runtime_state import RuntimeSnapshot
from raes_processor.models import CompiledTimeModel, ParticipantAutonomousExecutionRuntime


def clock_coordinate(snapshot: RuntimeSnapshot, clock_address: str) -> tuple[int, int]:
    """Read one shared clock coordinate or fail closed."""

    if snapshot.time_model_state is None:
        raise ValueError("autonomous participant execution requires typed shared-time state")
    clock = snapshot.time_model_state.clocks.get(clock_address)
    if clock is None:
        raise ValueError(f"autonomous participant clock {clock_address!r} has no runtime state")
    return clock.coordinate.segment, clock.coordinate.tick


def participant_time_domain(
    policy: ParticipantAutonomousExecutionRuntime,
    time_model: CompiledTimeModel,
) -> str:
    clock = next(item for item in time_model.clocks if item.address == policy.clock_address)
    domain = next(item for item in time_model.domains if item.address == clock.time_domain_address)
    return {
        "wall_clock": "wall_clock_time",
        "simulated": "simulation_time",
        "logical": "scenario_time",
        "monotonic": "scenario_time",
        "external": "backend_time",
    }[domain.kind]


__all__ = ["clock_coordinate", "participant_time_domain"]
