"""Admission checks that bind backend capabilities to portable contracts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol

from raes_contracts.vocabulary import ParticipantFeatureSupportLevel

from .capabilities import (
    OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS,
    PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS,
    PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_POLICY_FEATURES,
    PARTICIPANT_RUNTIME_ROLE_SCOPE,
    ParticipantFeatureSupport,
)

if TYPE_CHECKING:
    from raes_contracts.contracts.time_model import TimeModelDeclarationModel
    from raes_contracts.contracts.trial_cleanup import TrialCleanupPlanModel

    from .backend_manifest import BackendManifest
    from .capabilities import ParticipantRuntimeCapabilities, TimeCapabilities


class AutonomousExecutionPolicy(Protocol):
    participant_addresses: tuple[str, ...]
    action_contract_addresses: tuple[str, ...]
    target_addresses: tuple[str, ...]
    observation_boundary_address: str
    max_action_attempts: int
    max_in_flight: int
    selection_strategy: str


def participant_runtime_capability_contract_gaps(manifest: BackendManifest) -> tuple[str, ...]:
    """Return missing contract surfaces for declared standard API-405 claims."""

    participant_runtime = manifest.participant_runtime
    if participant_runtime is None:
        return ()

    declared_terms = {
        PARTICIPANT_RUNTIME_ROLE_SCOPE: participant_runtime.supported_participant_roles,
        PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE: participant_runtime.supported_behavior_features,
        PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE: participant_runtime.supported_interaction_features,
    }
    gaps: list[str] = []
    for scope, terms in declared_terms.items():
        required_by_term = PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[scope]
        for term in sorted(terms):
            required_contracts = required_by_term.get(term)
            if required_contracts is None:
                continue
            missing = sorted(required_contracts - manifest.supported_contract_versions)
            if missing:
                gaps.append(f"{scope}.{term} missing required contracts: {', '.join(missing)}")
    return tuple(gaps)


_PARTICIPANT_FEATURE_SUPPORT_RANK = {
    ParticipantFeatureSupportLevel.UNSUPPORTED: 0,
    ParticipantFeatureSupportLevel.DISCLOSED_WEAK: 1,
    ParticipantFeatureSupportLevel.BOUNDED: 2,
    ParticipantFeatureSupportLevel.EXACT: 3,
}


def _participant_feature_required_contracts(feature: str) -> frozenset[str]:
    for scope in (
        PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
        PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
    ):
        contracts = PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[scope].get(feature)
        if contracts is not None:
            return contracts
    return frozenset()


def _validate_downgrade_authorization(
    feature: str,
    allowed_downgrade_level: ParticipantFeatureSupportLevel | None,
    downgrade_policy_ref: str | None,
    downgrade_provenance_ref: str | None,
) -> None:
    if allowed_downgrade_level is not None and (not downgrade_policy_ref or not downgrade_provenance_ref):
        raise ValueError(
            f"participant feature '{feature}' requires explicit downgrade authorization "
            "with policy and provenance references"
        )


def _participant_feature_declaration(
    manifest: BackendManifest,
    feature: str,
) -> ParticipantFeatureSupport | None:
    capability = manifest.participant_runtime
    if capability is None:
        raise ValueError(f"participant feature '{feature}' requires participant runtime capabilities")

    supported_features = capability.supported_behavior_features | capability.supported_interaction_features
    declaration = next((entry for entry in capability.feature_support if entry.feature == feature), None)
    if declaration is None:
        if feature in supported_features and feature not in PARTICIPANT_RUNTIME_POLICY_FEATURES:
            return None
        raise ValueError(f"participant feature '{feature}' has no explicit support declaration")
    if declaration.support_level == ParticipantFeatureSupportLevel.UNSUPPORTED:
        raise ValueError(f"participant feature '{feature}' is explicitly unsupported")
    return declaration


def _validate_participant_feature_evidence(
    manifest: BackendManifest,
    feature: str,
    declaration: ParticipantFeatureSupport,
) -> None:
    missing_contracts = sorted(_participant_feature_required_contracts(feature) - manifest.supported_contract_versions)
    if missing_contracts:
        raise ValueError(
            f"participant feature '{feature}' is missing required contracts: {', '.join(missing_contracts)}"
        )
    if not declaration.evidence_refs and feature in PARTICIPANT_RUNTIME_POLICY_FEATURES:
        raise ValueError(f"participant feature '{feature}' has no conformance evidence")


def _validate_participant_feature_strength(
    feature: str,
    declaration: ParticipantFeatureSupport,
    required_level: ParticipantFeatureSupportLevel,
    allowed_downgrade_level: ParticipantFeatureSupportLevel | None,
) -> None:
    declared_rank = _PARTICIPANT_FEATURE_SUPPORT_RANK[declaration.support_level]
    required_rank = _PARTICIPANT_FEATURE_SUPPORT_RANK[required_level]
    if declared_rank >= required_rank:
        return
    if allowed_downgrade_level is None:
        raise ValueError(
            f"participant feature '{feature}' requires {required_level.value} support; "
            f"backend declares {declaration.support_level.value}"
        )
    if declaration.support_level != allowed_downgrade_level:
        raise ValueError(
            f"participant feature '{feature}' authorized downgrade is "
            f"{allowed_downgrade_level.value}; backend declares {declaration.support_level.value}"
        )


def resolve_participant_feature_support(
    manifest: BackendManifest,
    feature: str,
    *,
    required_level: ParticipantFeatureSupportLevel = ParticipantFeatureSupportLevel.EXACT,
    allowed_downgrade_level: ParticipantFeatureSupportLevel | None = None,
    downgrade_policy_ref: str | None = None,
    downgrade_provenance_ref: str | None = None,
) -> ParticipantFeatureSupport | None:
    """Resolve one required participant feature without inventing support.

    Historical API-405 behavior and interaction requirements remain
    presence-based when no API-407 strength entry exists. Participant-policy
    features added by issue #801 always require an explicit strength entry.
    An accepted downgrade returns that manifest entry unchanged, so callers
    cannot retain the stronger requested claim.
    """

    _validate_downgrade_authorization(
        feature,
        allowed_downgrade_level,
        downgrade_policy_ref,
        downgrade_provenance_ref,
    )
    declaration = _participant_feature_declaration(manifest, feature)
    if declaration is None:
        return None
    _validate_participant_feature_evidence(manifest, feature, declaration)
    _validate_participant_feature_strength(
        feature,
        declaration,
        required_level,
        allowed_downgrade_level,
    )
    return declaration


def participant_feature_support_gaps(
    manifest: BackendManifest,
    features: Iterable[str],
    *,
    required_level: ParticipantFeatureSupportLevel = ParticipantFeatureSupportLevel.EXACT,
) -> tuple[str, ...]:
    """Return fail-closed gaps for required participant semantic features."""

    gaps: list[str] = []
    for feature in sorted(set(features)):
        try:
            resolve_participant_feature_support(
                manifest,
                feature,
                required_level=required_level,
            )
        except ValueError as exc:
            gaps.append(str(exc))
    return tuple(gaps)


def _autonomous_limit_gaps(
    capability: ParticipantRuntimeCapabilities,
    policies: tuple[AutonomousExecutionPolicy, ...],
) -> list[str]:
    gaps: list[str] = []
    participant_count = len({participant for policy in policies for participant in policy.participant_addresses})
    limits = (
        ("participants", participant_count, capability.max_autonomous_participants),
        (
            "action attempts",
            max(policy.max_action_attempts for policy in policies),
            capability.max_autonomous_action_attempts,
        ),
        (
            "in-flight actions",
            max(policy.max_in_flight for policy in policies),
            capability.max_autonomous_in_flight,
        ),
    )
    for label, required, supported in limits:
        if supported is None or required > supported:
            gaps.append(f"autonomous {label} require {required}, backend limit is {supported}")
    return gaps


def _unsupported_autonomous_value_gaps(
    capability: ParticipantRuntimeCapabilities,
    policies: tuple[AutonomousExecutionPolicy, ...],
) -> list[str]:
    requirements = (
        (
            "selection strategies",
            {policy.selection_strategy for policy in policies},
            capability.supported_autonomous_selection_strategies,
        ),
        (
            "action contracts",
            {address for policy in policies for address in policy.action_contract_addresses},
            capability.supported_autonomous_action_contracts,
        ),
        (
            "observation boundaries",
            {policy.observation_boundary_address for policy in policies},
            capability.supported_autonomous_observation_boundaries,
        ),
        (
            "target addresses",
            {address for policy in policies for address in policy.target_addresses},
            capability.supported_autonomous_target_addresses,
        ),
    )
    return [
        f"unsupported autonomous {label}: {', '.join(unsupported)}"
        for label, required, supported in requirements
        if (unsupported := sorted(required - supported))
    ]


def _requires_coordinated_reset(
    policies: tuple[AutonomousExecutionPolicy, ...],
    time_model: object,
) -> bool:
    progression_by_address = {
        progression.address: progression for progression in getattr(time_model, "progression_policies", ())
    }
    return any(
        progression_by_address[policy.progression_policy_address].reset_behavior != "unsupported"
        or progression_by_address[policy.progression_policy_address].replay_behavior != "unsupported"
        for policy in policies
        if policy.progression_policy_address in progression_by_address
    )


def _autonomous_reset_gaps(
    manifest: BackendManifest,
    policies: tuple[AutonomousExecutionPolicy, ...],
    time_model: object | None,
) -> list[str]:
    if time_model is None or not _requires_coordinated_reset(policies, time_model):
        return []
    time_capability = manifest.time
    if time_capability is not None and time_capability.supports_coordinated_participant_reset:
        return []
    return ["autonomous clock reset requires coordinated participant reset support"]


def participant_autonomous_execution_capability_gaps(
    manifest: BackendManifest,
    policies: Iterable[AutonomousExecutionPolicy],
    time_model: object | None = None,
) -> tuple[str, ...]:
    """Return fail-closed backend gaps for compiled autonomous participants."""

    normalized_policies = tuple(policies)
    gaps: list[str] = []
    capability = manifest.participant_runtime
    if normalized_policies and (capability is None or not capability.supports_autonomous_execution):
        gaps.append("backend does not declare autonomous participant execution")
    elif normalized_policies and capability is not None:
        gaps.extend(_autonomous_limit_gaps(capability, normalized_policies))
        gaps.extend(_unsupported_autonomous_value_gaps(capability, normalized_policies))
        gaps.extend(_autonomous_reset_gaps(manifest, normalized_policies, time_model))
    return tuple(gaps)


def observation_capability_contract_gaps(manifest: BackendManifest) -> tuple[str, ...]:
    """Return missing contract surfaces for declared EXP-715 observation claims."""

    observation = manifest.observation
    if observation is None:
        return ()

    required_contracts = set(observation.supported_evidence_contracts) | set(OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS)
    missing = sorted(required_contracts - manifest.supported_contract_versions)
    gaps: list[str] = []
    if missing:
        gaps.append(f"capabilities.observation missing required contracts: {', '.join(missing)}")
    return tuple(gaps)


def time_capability_contract_gaps(manifest: BackendManifest) -> tuple[str, ...]:
    """Return missing contract surfaces for a declared API-421 capability."""

    from .capabilities import TIME_CAPABILITY_REQUIRED_CONTRACTS

    if manifest.time is None:
        return ()
    missing = sorted(TIME_CAPABILITY_REQUIRED_CONTRACTS - manifest.supported_contract_versions)
    return () if not missing else (f"capabilities.time missing required contracts: {', '.join(missing)}",)


def _unsupported_time_terms(
    label: str,
    required: set[str],
    supported: frozenset[str],
) -> list[str]:
    missing = sorted(required - supported)
    return [] if not missing else [f"unsupported time {label}: {', '.join(missing)}"]


def _time_capacity_gaps(
    capability: TimeCapabilities,
    declaration: TimeModelDeclarationModel,
) -> list[str]:
    gaps: list[str] = []
    if capability.max_time_domains is not None and len(declaration.domains) > capability.max_time_domains:
        gaps.append(
            f"time model requires {len(declaration.domains)} domains; backend limit is {capability.max_time_domains}"
        )
    if capability.max_clocks is not None and len(declaration.clocks) > capability.max_clocks:
        gaps.append(f"time model requires {len(declaration.clocks)} clocks; backend limit is {capability.max_clocks}")
    return gaps


def _time_control_gaps(
    capability: TimeCapabilities,
    declaration: TimeModelDeclarationModel,
) -> list[str]:
    requirements = (
        (
            any(clock.supports_pause for clock in declaration.clocks.values()),
            capability.supports_pause,
            "pause control",
        ),
        (any(clock.supports_jump for clock in declaration.clocks.values()), capability.supports_jump, "jump control"),
        (bool(declaration.mappings), capability.supports_exact_rational_mappings, "exact rational mappings"),
        (True, capability.supports_append_only_history, "append-only clock transition history"),
        (True, capability.supports_run_provenance, "realized run provenance"),
    )
    return [f"time model requires {label}" for required, supported, label in requirements if required and not supported]


def time_model_capability_gaps(
    manifest: BackendManifest,
    declaration: TimeModelDeclarationModel,
) -> tuple[str, ...]:
    """Return fail-closed admission gaps for one portable time declaration."""

    capability = manifest.time
    if capability is None:
        return ("backend does not declare time capabilities",)

    gaps: list[str] = [*time_capability_contract_gaps(manifest)]
    term_sources = (
        ("domain kinds", declaration.domains.values(), "kind", capability.supported_domain_kinds),
        ("authority kinds", declaration.clocks.values(), "authority_kind", capability.supported_authority_kinds),
        (
            "advancement modes",
            declaration.progression_policies.values(),
            "advancement_mode",
            capability.supported_advancement_modes,
        ),
        (
            "synchronization modes",
            declaration.progression_policies.values(),
            "synchronization_mode",
            capability.supported_synchronization_modes,
        ),
        ("mapping kinds", declaration.mappings.values(), "mapping_kind", capability.supported_mapping_kinds),
        (
            "constraint kinds",
            declaration.temporal_constraints.values(),
            "kind",
            capability.supported_constraint_kinds,
        ),
        (
            "reset behaviors",
            declaration.progression_policies.values(),
            "reset_behavior",
            capability.supported_reset_behaviors,
        ),
        (
            "replay behaviors",
            declaration.progression_policies.values(),
            "replay_behavior",
            capability.supported_replay_behaviors,
        ),
    )
    for label, values, attribute, supported in term_sources:
        gaps.extend(_unsupported_time_terms(label, {getattr(value, attribute) for value in values}, supported))
    gaps.extend(_time_capacity_gaps(capability, declaration))
    gaps.extend(_time_control_gaps(capability, declaration))
    return tuple(gaps)


def require_time_model_capability(
    manifest: BackendManifest,
    declaration: TimeModelDeclarationModel,
) -> None:
    """Fail admission when a backend cannot honor the portable time model."""

    gaps = time_model_capability_gaps(manifest, declaration)
    if gaps:
        raise ValueError("; ".join(gaps))


def _required_cleanup_actions(plan: TrialCleanupPlanModel) -> set[str]:
    return {
        obligation.action_kind
        for obligation in plan.cleanup_obligations.values()
        if obligation.requirement == "required"
    }


def _required_cleanup_probe_methods(plan: TrialCleanupPlanModel) -> set[str]:
    probe_refs = set(plan.clean_state.verification_probe_refs)
    probe_refs.update(
        probe_ref
        for obligation in plan.cleanup_obligations.values()
        if obligation.requirement == "required"
        for probe_ref in obligation.verification_probe_refs
    )
    return {probe_ref.partition(":")[0] for probe_ref in probe_refs}


def _require_supported_cleanup_values(label: str, required: set[str], supported: frozenset[str]) -> None:
    unsupported = sorted(required - supported)
    if unsupported:
        raise ValueError(f"unsupported cleanup {label}: {', '.join(unsupported)}")


def require_cleanup_plan_capability(manifest: BackendManifest, plan: TrialCleanupPlanModel) -> None:
    """Fail admission when a backend cannot satisfy a portable cleanup plan."""

    cleanup = manifest.cleanup
    if cleanup is None:
        raise ValueError("backend does not declare cleanup capabilities")

    _require_supported_cleanup_values("action kinds", _required_cleanup_actions(plan), cleanup.supported_action_kinds)
    _require_supported_cleanup_values(
        "verification methods", _required_cleanup_probe_methods(plan), cleanup.supported_verification_methods
    )

    if plan.clean_state.mode == "declared-reusable" and not cleanup.supports_reusable_state:
        raise ValueError("backend does not support declared reusable state")
    required_cleanup = any(obligation.requirement == "required" for obligation in plan.cleanup_obligations.values())
    if required_cleanup and not cleanup.supports_residual_state_disclosure:
        raise ValueError("required cleanup needs backend residual-state disclosure")
