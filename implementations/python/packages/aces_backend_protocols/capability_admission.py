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
