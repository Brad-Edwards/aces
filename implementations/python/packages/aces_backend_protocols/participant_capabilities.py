"""Participant-runtime capability declarations and evidence requirements."""

from dataclasses import dataclass, field

from aces_contracts.addressing import require_compiled_address
from aces_contracts.controlled_vocabularies import validate_controlled_vocabulary_scope_values
from aces_contracts.vocabulary import ParticipantFeatureSupportLevel

PARTICIPANT_RUNTIME_ROLE_SCOPE = "capabilities.participant_runtime.supported_participant_roles"
PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE = "capabilities.participant_runtime.supported_behavior_features"
PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE = "capabilities.participant_runtime.supported_interaction_features"

_PARTICIPANT_EPISODE_CONTRACTS = frozenset(
    {
        "participant-episode-state-envelope-v1",
        "participant-episode-history-event-stream-v1",
        "runtime-snapshot-v1",
    }
)
_PARTICIPANT_BEHAVIOR_CONTRACTS = frozenset(
    {
        "participant-behavior-history-event-stream-v1",
        "runtime-snapshot-v1",
    }
)
_PARTICIPANT_INTERACTION_CONTRACTS = frozenset(
    {
        "participant-behavior-history-event-stream-v1",
        "participant-shared-state-record-v1",
        "participant-joint-action-record-v1",
        "participant-time-management-context-v1",
        "runtime-snapshot-v1",
    }
)

PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS = {
    PARTICIPANT_RUNTIME_ROLE_SCOPE: {
        "blue": _PARTICIPANT_EPISODE_CONTRACTS,
        "green": _PARTICIPANT_EPISODE_CONTRACTS,
        "red": _PARTICIPANT_EPISODE_CONTRACTS,
        "white": _PARTICIPANT_EPISODE_CONTRACTS,
    },
    PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE: {
        "action_contracts": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "autonomous_execution": _PARTICIPANT_INTERACTION_CONTRACTS,
        "attribution_support": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "behavior_history": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "effects": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "failure_classes": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "observation_boundaries": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "outcome_interpretation": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "preconditions": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "state_transitions": _PARTICIPANT_BEHAVIOR_CONTRACTS,
        "temporal_contracts": _PARTICIPANT_BEHAVIOR_CONTRACTS,
    },
    PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE: {
        "contention": _PARTICIPANT_INTERACTION_CONTRACTS,
        "coordination": _PARTICIPANT_INTERACTION_CONTRACTS,
        "interference": _PARTICIPANT_INTERACTION_CONTRACTS,
        "shared_state_change": _PARTICIPANT_INTERACTION_CONTRACTS,
    },
}


def _validate_unique_non_empty_strings(field_name: str, values: tuple[str, ...]) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{field_name} must not contain empty strings")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicate values")


def _validate_participant_feature_support_term(feature: str) -> None:
    errors: list[str] = []
    for scope in (PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE, PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE):
        try:
            validate_controlled_vocabulary_scope_values(scope, (feature,))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        return
    raise ValueError(
        "ParticipantFeatureSupport.feature must be a governed participant behavior or interaction feature "
        f"term, or match the governed extension pattern; got {feature!r}; "
        f"validation details: {'; '.join(errors)}"
    )


@dataclass(frozen=True)
class ParticipantFeatureSupport:
    """API-407 per-feature participant runtime support declaration."""

    feature: str
    support_level: ParticipantFeatureSupportLevel | str
    constraint_refs: tuple[str, ...] = ()
    disclosure_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.feature.strip():
            raise ValueError("ParticipantFeatureSupport.feature must be non-empty")
        _validate_participant_feature_support_term(self.feature)
        try:
            support_level = (
                self.support_level
                if isinstance(self.support_level, ParticipantFeatureSupportLevel)
                else ParticipantFeatureSupportLevel(str(self.support_level))
            )
        except ValueError as exc:
            raise ValueError("ParticipantFeatureSupport.support_level must be a valid support level") from exc
        constraint_refs = tuple(self.constraint_refs)
        disclosure_refs = tuple(self.disclosure_refs)
        _validate_unique_non_empty_strings("ParticipantFeatureSupport.constraint_refs", constraint_refs)
        _validate_unique_non_empty_strings("ParticipantFeatureSupport.disclosure_refs", disclosure_refs)
        if support_level != ParticipantFeatureSupportLevel.EXACT and not disclosure_refs:
            raise ValueError(
                "ParticipantFeatureSupport disclosure_refs must be non-empty when support_level is below exact"
            )
        object.__setattr__(self, "support_level", support_level)
        object.__setattr__(self, "constraint_refs", constraint_refs)
        object.__setattr__(self, "disclosure_refs", disclosure_refs)


@dataclass(frozen=True)
class ParticipantRuntimeCapabilities:
    """Backend participant lifecycle, behavior, and execution support."""

    name: str
    supported_participant_roles: frozenset[str] = frozenset()
    supported_behavior_features: frozenset[str] = frozenset()
    supported_interaction_features: frozenset[str] = frozenset()
    feature_support: tuple[ParticipantFeatureSupport, ...] = ()
    supports_autonomous_execution: bool = False
    supported_autonomous_selection_strategies: frozenset[str] = frozenset()
    supported_autonomous_action_contracts: frozenset[str] = frozenset()
    supported_autonomous_observation_boundaries: frozenset[str] = frozenset()
    supported_autonomous_target_addresses: frozenset[str] = frozenset()
    max_autonomous_participants: int | None = None
    max_autonomous_action_attempts: int | None = None
    max_autonomous_in_flight: int | None = None
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ParticipantRuntimeCapabilities.name must be non-empty")
        self._validate_required_vocabularies()
        feature_support = self._normalize_feature_support()
        self._validate_feature_support(feature_support)
        self._validate_autonomous_execution()
        object.__setattr__(self, "feature_support", feature_support)

    def _validate_required_vocabularies(self) -> None:
        for field_name, values in (
            ("supported_participant_roles", self.supported_participant_roles),
            ("supported_behavior_features", self.supported_behavior_features),
            ("supported_interaction_features", self.supported_interaction_features),
        ):
            if not values:
                raise ValueError(f"ParticipantRuntimeCapabilities.{field_name} must not be empty")
            if any(not value.strip() for value in values):
                raise ValueError(f"ParticipantRuntimeCapabilities.{field_name} must not contain empty strings")
        validate_controlled_vocabulary_scope_values(
            PARTICIPANT_RUNTIME_ROLE_SCOPE,
            self.supported_participant_roles,
        )
        validate_controlled_vocabulary_scope_values(
            PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
            self.supported_behavior_features,
        )
        validate_controlled_vocabulary_scope_values(
            PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
            self.supported_interaction_features,
        )

    def _normalize_feature_support(self) -> tuple[ParticipantFeatureSupport, ...]:
        return tuple(
            entry if isinstance(entry, ParticipantFeatureSupport) else ParticipantFeatureSupport(**entry)
            for entry in self.feature_support
        )

    def _validate_feature_support(self, feature_support: tuple[ParticipantFeatureSupport, ...]) -> None:
        feature_names = tuple(entry.feature for entry in feature_support)
        _validate_unique_non_empty_strings("ParticipantRuntimeCapabilities.feature_support", feature_names)
        supported_features = self.supported_behavior_features | self.supported_interaction_features
        for entry in feature_support:
            if (
                entry.support_level == ParticipantFeatureSupportLevel.UNSUPPORTED
                and entry.feature in supported_features
            ):
                raise ValueError(
                    "ParticipantRuntimeCapabilities.feature_support cannot declare a supported feature unsupported"
                )

    def _validate_autonomous_execution(self) -> None:
        declares_autonomous = "autonomous_execution" in self.supported_behavior_features
        if declares_autonomous != self.supports_autonomous_execution:
            raise ValueError("ParticipantRuntimeCapabilities autonomous_execution feature and support flag must agree")
        if self.supports_autonomous_execution:
            self._validate_enabled_autonomous_execution()
        elif self._has_autonomous_configuration():
            raise ValueError("autonomous execution limits require autonomous execution support")

    def _validate_enabled_autonomous_execution(self) -> None:
        if not self.supported_autonomous_selection_strategies:
            raise ValueError("autonomous execution requires supported selection strategies")
        unknown_strategies = sorted(self.supported_autonomous_selection_strategies - {"ordered_cycle"})
        if unknown_strategies:
            raise ValueError("unsupported autonomous selection strategies: " + ", ".join(unknown_strategies))
        if not self.supported_autonomous_action_contracts:
            raise ValueError("autonomous execution requires exact supported action contracts")
        if not self.supported_autonomous_observation_boundaries:
            raise ValueError("autonomous execution requires exact supported observation boundaries")
        self._validate_autonomous_addresses()
        for label, value in self._autonomous_limits():
            if value is None or value < 1:
                raise ValueError(f"autonomous execution requires positive {label}")

    def _validate_autonomous_addresses(self) -> None:
        for field_name, addresses in (
            ("supported_autonomous_action_contracts", self.supported_autonomous_action_contracts),
            ("supported_autonomous_observation_boundaries", self.supported_autonomous_observation_boundaries),
            ("supported_autonomous_target_addresses", self.supported_autonomous_target_addresses),
        ):
            for address in addresses:
                require_compiled_address(address, field_name=field_name)

    def _autonomous_limits(self) -> tuple[tuple[str, int | None], ...]:
        return (
            ("max_autonomous_participants", self.max_autonomous_participants),
            ("max_autonomous_action_attempts", self.max_autonomous_action_attempts),
            ("max_autonomous_in_flight", self.max_autonomous_in_flight),
        )

    def _has_autonomous_configuration(self) -> bool:
        return bool(
            self.supported_autonomous_selection_strategies
            or self.supported_autonomous_action_contracts
            or self.supported_autonomous_observation_boundaries
            or self.supported_autonomous_target_addresses
            or any(value is not None for _, value in self._autonomous_limits())
        )


__all__ = [
    "PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE",
    "PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS",
    "PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE",
    "PARTICIPANT_RUNTIME_ROLE_SCOPE",
    "ParticipantFeatureSupport",
    "ParticipantRuntimeCapabilities",
]
