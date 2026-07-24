"""Cross-contract capability claim checks kept out of the model module."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .backend_manifest import BackendManifest


def _missing_contract_gap(label: str, required: set[str], supported: frozenset[str]) -> tuple[str, ...]:
    missing = sorted(required - supported)
    return tuple([f"{label} missing required contracts: {', '.join(missing)}"] if missing else [])


def participant_runtime_capability_contract_gaps(manifest: BackendManifest) -> tuple[str, ...]:
    from .capabilities import PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS

    participant_runtime = manifest.participant_runtime
    if participant_runtime is None:
        return ()
    from .capabilities import (
        PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
        PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
        PARTICIPANT_RUNTIME_ROLE_SCOPE,
    )

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
    from .capabilities import OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS

    observation = manifest.observation
    if observation is None:
        return ()
    required = set(observation.supported_evidence_contracts) | set(OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS)
    return _missing_contract_gap("capabilities.observation", required, manifest.supported_contract_versions)


def live_activity_capability_contract_gaps(manifest: BackendManifest) -> tuple[str, ...]:
    if manifest.live_activity is None:
        return ()
    required = {"live-activity-profile-v1", "live-activity-occurrence-v1"}
    return _missing_contract_gap("capabilities.live_activity", required, manifest.supported_contract_versions)


__all__ = [
    "live_activity_capability_contract_gaps",
    "observation_capability_contract_gaps",
    "participant_runtime_capability_contract_gaps",
]
