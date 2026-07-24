"""Admission checks that bind backend capabilities to portable contracts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol

from .capabilities import (
    OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS,
    PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS,
    PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_ROLE_SCOPE,
)

if TYPE_CHECKING:
    from aces_contracts.contracts.time_model import TimeModelDeclarationModel
    from aces_contracts.contracts.trial_cleanup import TrialCleanupPlanModel

    from .backend_manifest import BackendManifest


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


def participant_autonomous_execution_capability_gaps(
    manifest: BackendManifest,
    policies: Iterable[AutonomousExecutionPolicy],
    time_model: object | None = None,
) -> tuple[str, ...]:
    """Return fail-closed backend gaps for compiled autonomous participants."""

    policies = tuple(policies)
    if not policies:
        return ()
    capability = manifest.participant_runtime
    if capability is None or not capability.supports_autonomous_execution:
        return ("backend does not declare autonomous participant execution",)
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
    unsupported_strategies = sorted(
        {policy.selection_strategy for policy in policies} - capability.supported_autonomous_selection_strategies
    )
    if unsupported_strategies:
        gaps.append("unsupported autonomous selection strategies: " + ", ".join(unsupported_strategies))
    required_actions = {address for policy in policies for address in policy.action_contract_addresses}
    unsupported_actions = sorted(required_actions - capability.supported_autonomous_action_contracts)
    if unsupported_actions:
        gaps.append("unsupported autonomous action contracts: " + ", ".join(unsupported_actions))
    required_boundaries = {policy.observation_boundary_address for policy in policies}
    unsupported_boundaries = sorted(required_boundaries - capability.supported_autonomous_observation_boundaries)
    if unsupported_boundaries:
        gaps.append("unsupported autonomous observation boundaries: " + ", ".join(unsupported_boundaries))
    required_targets = {address for policy in policies for address in policy.target_addresses}
    unsupported_targets = sorted(required_targets - capability.supported_autonomous_target_addresses)
    if unsupported_targets:
        gaps.append("unsupported autonomous target addresses: " + ", ".join(unsupported_targets))
    if time_model is not None:
        progression_by_address = {
            progression.address: progression for progression in getattr(time_model, "progression_policies", ())
        }
        requires_coordinated_reset = any(
            progression_by_address[policy.progression_policy_address].reset_behavior != "unsupported"
            or progression_by_address[policy.progression_policy_address].replay_behavior != "unsupported"
            for policy in policies
            if policy.progression_policy_address in progression_by_address
        )
        time_capability = manifest.time
        if requires_coordinated_reset and (
            time_capability is None or not time_capability.supports_coordinated_participant_reset
        ):
            gaps.append("autonomous clock reset requires coordinated participant reset support")
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
    if capability.max_time_domains is not None and len(declaration.domains) > capability.max_time_domains:
        gaps.append(
            f"time model requires {len(declaration.domains)} domains; backend limit is {capability.max_time_domains}"
        )
    if capability.max_clocks is not None and len(declaration.clocks) > capability.max_clocks:
        gaps.append(f"time model requires {len(declaration.clocks)} clocks; backend limit is {capability.max_clocks}")
    if any(clock.supports_pause for clock in declaration.clocks.values()) and not capability.supports_pause:
        gaps.append("time model requires pause control")
    if any(clock.supports_jump for clock in declaration.clocks.values()) and not capability.supports_jump:
        gaps.append("time model requires jump control")
    if declaration.mappings and not capability.supports_exact_rational_mappings:
        gaps.append("time model requires exact rational mappings")
    if not capability.supports_append_only_history:
        gaps.append("time model requires append-only clock transition history")
    if not capability.supports_run_provenance:
        gaps.append("time model requires realized run provenance")
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
