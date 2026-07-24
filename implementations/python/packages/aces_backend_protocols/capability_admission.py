"""Admission checks that bind backend capabilities to portable contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    gaps.extend(
        _unsupported_time_terms(
            "domain kinds",
            {domain.kind for domain in declaration.domains.values()},
            capability.supported_domain_kinds,
        )
    )
    gaps.extend(
        _unsupported_time_terms(
            "authority kinds",
            {clock.authority_kind for clock in declaration.clocks.values()},
            capability.supported_authority_kinds,
        )
    )
    gaps.extend(
        _unsupported_time_terms(
            "advancement modes",
            {policy.advancement_mode for policy in declaration.progression_policies.values()},
            capability.supported_advancement_modes,
        )
    )
    gaps.extend(
        _unsupported_time_terms(
            "synchronization modes",
            {policy.synchronization_mode for policy in declaration.progression_policies.values()},
            capability.supported_synchronization_modes,
        )
    )
    gaps.extend(
        _unsupported_time_terms(
            "mapping kinds",
            {mapping.mapping_kind for mapping in declaration.mappings.values()},
            capability.supported_mapping_kinds,
        )
    )
    gaps.extend(
        _unsupported_time_terms(
            "constraint kinds",
            {constraint.kind for constraint in declaration.temporal_constraints.values()},
            capability.supported_constraint_kinds,
        )
    )
    gaps.extend(
        _unsupported_time_terms(
            "reset behaviors",
            {policy.reset_behavior for policy in declaration.progression_policies.values()},
            capability.supported_reset_behaviors,
        )
    )
    gaps.extend(
        _unsupported_time_terms(
            "replay behaviors",
            {policy.replay_behavior for policy in declaration.progression_policies.values()},
            capability.supported_replay_behaviors,
        )
    )
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
