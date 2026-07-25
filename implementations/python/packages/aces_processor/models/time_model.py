"""Compiled shared time-model declarations."""

from dataclasses import dataclass

from aces_contracts.addressing import require_compiled_address


@dataclass(frozen=True)
class CompiledTimeDomain:
    address: str
    kind: str
    tick_period_numerator: int
    tick_period_denominator: int
    epoch: str
    visibility: str
    description: str

    def __post_init__(self) -> None:
        require_compiled_address(self.address)


@dataclass(frozen=True)
class CompiledClock:
    address: str
    time_domain_address: str
    authority_kind: str
    authority_ref: str
    monotonicity: str
    supports_pause: bool
    supports_reset: bool
    supports_jump: bool
    description: str

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        require_compiled_address(self.time_domain_address, field_name="time domain address")


@dataclass(frozen=True)
class CompiledTimeDomainMapping:
    address: str
    source_domain_address: str
    target_domain_address: str
    mapping_kind: str
    scale_numerator: int
    scale_denominator: int
    offset_ticks: int
    description: str

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        require_compiled_address(self.source_domain_address, field_name="source domain address")
        require_compiled_address(self.target_domain_address, field_name="target domain address")


@dataclass(frozen=True)
class CompiledTimeProgressionPolicy:
    address: str
    clock_address: str
    advancement_mode: str
    pacing_numerator: int
    pacing_denominator: int
    synchronization_mode: str
    step_ticks: int | None
    drift_bound_ticks: int | None
    reset_behavior: str
    replay_behavior: str
    description: str

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        require_compiled_address(self.clock_address, field_name="clock address")


@dataclass(frozen=True)
class CompiledTemporalConstraint:
    address: str
    kind: str
    clock_address: str
    subject_addresses: tuple[str, ...]
    start_tick: int | None
    start_microstep: int | None
    end_tick: int | None
    end_microstep: int | None
    duration_ticks: int | None
    cadence_ticks: int | None
    description: str

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        require_compiled_address(self.clock_address, field_name="clock address")
        for subject in self.subject_addresses:
            require_compiled_address(subject, field_name="temporal subject address")


@dataclass(frozen=True)
class CompiledTimeModel:
    domains: tuple[CompiledTimeDomain, ...] = ()
    clocks: tuple[CompiledClock, ...] = ()
    mappings: tuple[CompiledTimeDomainMapping, ...] = ()
    progression_policies: tuple[CompiledTimeProgressionPolicy, ...] = ()
    constraints: tuple[CompiledTemporalConstraint, ...] = ()

    def __post_init__(self) -> None:
        addresses = [
            item.address
            for collection in (
                self.domains,
                self.clocks,
                self.mappings,
                self.progression_policies,
                self.constraints,
            )
            for item in collection
        ]
        if len(addresses) != len(set(addresses)):
            raise ValueError("compiled time-model addresses must be unique")


__all__ = [
    "CompiledClock",
    "CompiledTemporalConstraint",
    "CompiledTimeDomain",
    "CompiledTimeDomainMapping",
    "CompiledTimeModel",
    "CompiledTimeProgressionPolicy",
]
