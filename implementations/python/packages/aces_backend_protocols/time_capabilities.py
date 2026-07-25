"""Portable shared-time backend capability declarations."""

from __future__ import annotations

from dataclasses import dataclass, field

from aces_contracts.manifest_authority import validate_backend_supported_contract_versions

TIME_CAPABILITY_REQUIRED_CONTRACTS = frozenset(
    {
        "time-model-v1",
        "time-runtime-state-v1",
        "realized-time-model-v1",
        "runtime-snapshot-v1",
        "experiment-run-v1",
    }
)
_TIME_DOMAIN_KINDS = frozenset({"wall_clock", "monotonic", "simulated", "logical", "external"})
_TIME_AUTHORITY_KINDS = frozenset({"runtime", "backend", "system", "external"})
_TIME_ADVANCEMENT_MODES = frozenset({"real_time", "dilated", "stepped", "event_driven", "externally_paced"})
_TIME_SYNCHRONIZATION_MODES = frozenset({"none", "authority", "barrier", "conservative"})
_TIME_MAPPING_KINDS = frozenset({"identity", "affine_rational"})
_TIME_CONSTRAINT_KINDS = frozenset({"precedence", "duration", "window", "deadline", "cadence"})
_TIME_RESET_BEHAVIORS = frozenset({"unsupported", "new_segment_zero", "new_segment_preserve_value"})
_TIME_REPLAY_BEHAVIORS = frozenset({"unsupported", "restart_from_anchor", "restore_recorded_advances"})


def _validate_unique_non_empty_strings(label: str, values: frozenset[str]) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{label} must not contain empty strings")


def _validate_time_terms(label: str, values: frozenset[str], allowed: frozenset[str]) -> None:
    _validate_unique_non_empty_strings(label, values)
    unknown = sorted(values - allowed)
    if unknown:
        raise ValueError(f"{label} contains unknown values: {', '.join(unknown)}")


@dataclass(frozen=True)
class TimeCapabilities:
    """Backend support for the portable shared-time contract family."""

    name: str
    supported_contract_versions: frozenset[str] = frozenset()
    supported_domain_kinds: frozenset[str] = frozenset()
    supported_authority_kinds: frozenset[str] = frozenset()
    supported_advancement_modes: frozenset[str] = frozenset()
    supported_synchronization_modes: frozenset[str] = frozenset()
    supported_mapping_kinds: frozenset[str] = frozenset()
    supported_constraint_kinds: frozenset[str] = frozenset()
    supported_reset_behaviors: frozenset[str] = frozenset()
    supported_replay_behaviors: frozenset[str] = frozenset()
    max_time_domains: int | None = None
    max_clocks: int | None = None
    supports_pause: bool = False
    supports_jump: bool = False
    supports_exact_rational_mappings: bool = False
    supports_append_only_history: bool = False
    supports_run_provenance: bool = False
    supports_coordinated_participant_reset: bool = False
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("TimeCapabilities.name must be non-empty")
        if self.supported_contract_versions != TIME_CAPABILITY_REQUIRED_CONTRACTS:
            raise ValueError("TimeCapabilities.supported_contract_versions must contain the complete time family")
        validate_backend_supported_contract_versions(self.supported_contract_versions)
        _validate_time_terms(
            "TimeCapabilities.supported_domain_kinds",
            self.supported_domain_kinds,
            _TIME_DOMAIN_KINDS,
        )
        _validate_time_terms(
            "TimeCapabilities.supported_authority_kinds",
            self.supported_authority_kinds,
            _TIME_AUTHORITY_KINDS,
        )
        _validate_time_terms(
            "TimeCapabilities.supported_advancement_modes",
            self.supported_advancement_modes,
            _TIME_ADVANCEMENT_MODES,
        )
        _validate_time_terms(
            "TimeCapabilities.supported_synchronization_modes",
            self.supported_synchronization_modes,
            _TIME_SYNCHRONIZATION_MODES,
        )
        _validate_time_terms(
            "TimeCapabilities.supported_mapping_kinds",
            self.supported_mapping_kinds,
            _TIME_MAPPING_KINDS,
        )
        _validate_time_terms(
            "TimeCapabilities.supported_constraint_kinds",
            self.supported_constraint_kinds,
            _TIME_CONSTRAINT_KINDS,
        )
        _validate_time_terms(
            "TimeCapabilities.supported_reset_behaviors",
            self.supported_reset_behaviors,
            _TIME_RESET_BEHAVIORS,
        )
        _validate_time_terms(
            "TimeCapabilities.supported_replay_behaviors",
            self.supported_replay_behaviors,
            _TIME_REPLAY_BEHAVIORS,
        )
        for label, value in (("max_time_domains", self.max_time_domains), ("max_clocks", self.max_clocks)):
            if value is not None and value < 1:
                raise ValueError(f"TimeCapabilities.{label} must be positive when provided")
        required_non_empty = (
            ("supported_domain_kinds", self.supported_domain_kinds),
            ("supported_authority_kinds", self.supported_authority_kinds),
            ("supported_advancement_modes", self.supported_advancement_modes),
            ("supported_synchronization_modes", self.supported_synchronization_modes),
            ("supported_reset_behaviors", self.supported_reset_behaviors),
            ("supported_replay_behaviors", self.supported_replay_behaviors),
        )
        for label, values in required_non_empty:
            if not values:
                raise ValueError(f"TimeCapabilities.{label} must not be empty")
        if self.supported_mapping_kinds and not self.supports_exact_rational_mappings:
            raise ValueError("TimeCapabilities mapping support requires exact rational mappings")
