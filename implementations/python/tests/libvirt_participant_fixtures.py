"""Shared fixtures for the libvirt participant-runtime tests and proof driver.

Both ``test_libvirt_participant_runtime.py`` (the acceptance-criteria tests) and
``libvirt_participant_proof.py`` (the end-to-end proof driver) need the same
deterministic participant-implementation manifest, selection, action-result, and
a no-op libvirt driver. They live here so the two consumers share one definition
rather than carrying parallel copies.
"""

from __future__ import annotations

from collections.abc import Mapping

from aces_contracts.contracts import (
    ParticipantActionResultModel,
    ParticipantImplementationManifestModel,
    ParticipantImplementationSelectionModel,
)

# Deterministic participant implementation identity + provenance refs. These are
# structural-proof placeholders (synthetic digests): no live agent is installed.
AGENT_IDENTITY = {"name": "libvirt-deterministic-agent", "version": "1.0.0"}
MANIFEST_REF = "contracts/fixtures/participant-implementation-manifest/libvirt-deterministic.json"
MANIFEST_DIGEST = "sha256:" + "1" * 64
POLICY_ID = "libvirt-paper-agent-policy"
POLICY_VERSION = "1.0.0"
POLICY_DIGEST = "sha256:" + "3" * 64

# Refs the participant must never observe: evaluator internals, the internal DB,
# Wazuh, and the policy gate. The exposure policy withholds them.
WITHHELD_REFS = (
    "content.evaluator-notes",
    "nodes.customer-db.services.postgres",
    "nodes.wazuh-manager",
    "nodes.wazuh-indexer",
    "nodes.participant-policy-gate",
)


class NullLibvirtDriver:
    """No-op libvirt driver for structural tests that never call realize()."""

    def realize(self, *, networks, domains):
        from aces_backend_libvirt.driver import DriverResult

        return DriverResult()

    def destroy(self, *, networks, domains):
        from aces_backend_libvirt.driver import DriverResult

        return DriverResult()

    def realized_addresses(self):
        return frozenset()


def build_implementation_manifest() -> ParticipantImplementationManifestModel:
    """Return the deterministic participant-implementation manifest."""
    return ParticipantImplementationManifestModel.model_validate(
        {
            "schema_version": "participant-implementation-manifest/v1",
            "identity": AGENT_IDENTITY,
            "implementation_kind": "agent",
            "supported_contract_versions": [
                "participant-implementation-manifest-v1",
                "participant-implementation-provenance-v1",
                "participant-episode-state-envelope-v1",
                "participant-episode-history-event-stream-v1",
                "participant-behavior-history-event-stream-v1",
            ],
            "compatibility": {
                "participant_runtimes": ["libvirt-qemu"],
                "processors": ["aces-reference-processor"],
                "backends": ["libvirt-qemu"],
            },
            "concept_bindings": [
                {"scope": "implementation_kind", "family": "apparatus-declarations"},
                {"scope": "capabilities.supported_participant_contracts", "family": "apparatus-declarations"},
                {"scope": "capabilities.supported_decision_surface_modes", "family": "apparatus-declarations"},
                {"scope": "capabilities.tool_affordance_expectations", "family": "tools-and-artifacts"},
                {"scope": "capabilities.exposure_policy_kinds", "family": "provenance-and-evidence"},
            ],
            "constraints": {
                "max_parallel_episodes": "1",
                "simulation_disclosure": "deterministic-simulation: no live libvirt domain execution",
            },
            "capabilities": {
                "supported_participant_contracts": [
                    "participant-episode-state-envelope-v1",
                    "participant-episode-history-event-stream-v1",
                    "participant-behavior-history-event-stream-v1",
                ],
                "supported_decision_surface_modes": ["policy-directed"],
                "tool_affordance_expectations": ["http-api"],
                "exposure_policy_kinds": ["task-statement", "observation-stream"],
            },
        }
    )


def build_implementation_selection(
    participant_address: str,
    withheld_refs: tuple[str, ...] = WITHHELD_REFS,
) -> ParticipantImplementationSelectionModel:
    """Return the deterministic participant-implementation selection."""
    return ParticipantImplementationSelectionModel.model_validate(
        {
            "participant_address": participant_address,
            "implementation_identity": AGENT_IDENTITY,
            "manifest_ref": MANIFEST_REF,
            "manifest_digest": MANIFEST_DIGEST,
            "selected_decision_surface_mode": "policy-directed",
            "participant_contract_versions": [
                "participant-episode-state-envelope-v1",
                "participant-behavior-history-event-stream-v1",
            ],
            "exposure_policy": {
                "policy_id": POLICY_ID,
                "policy_version": POLICY_VERSION,
                "policy_digest": POLICY_DIGEST,
                "exposure_policy_kinds": ["task-statement", "observation-stream"],
                "disclosed_refs": [],
                "withheld_refs": list(withheld_refs),
                "tool_affordance_refs": [],
                "visibility_scope_refs": [],
            },
        }
    )


def build_action_result(
    *,
    participant_address: str,
    episode_id: str,
    action_instance_id: str,
    action_contract_address: str,
    contract_spec: Mapping[str, object],
) -> ParticipantActionResultModel:
    """Build a deterministic succeeded action_result for a compiled action contract.

    Reports every declared precondition (with empty support/evidence refs) to
    satisfy the SEM-211 completeness requirement, and only ``no_effect`` effects
    (which need no target/evidence refs), so the result never introduces a
    hidden-ref or boundary-evidence violation.
    """
    preconditions = []
    for pc in contract_spec.get("preconditions", ()):
        if not isinstance(pc, Mapping) or not pc.get("precondition_id") or not pc.get("precondition_class"):
            continue
        preconditions.append(
            {
                "precondition_id": str(pc["precondition_id"]),
                "precondition_class": str(pc["precondition_class"]),
                "status": "satisfied",
                "participant_address": participant_address,
                "episode_id": episode_id,
                "action_contract_address": action_contract_address,
                "observation_point": f"{action_instance_id}:pc-{pc['precondition_id']}",
                "support_refs": [],
                "evidence_refs": [],
            }
        )

    effects = []
    for eff in contract_spec.get("effects", ()):
        if not isinstance(eff, Mapping) or not eff.get("effect_id") or not eff.get("effect_class"):
            continue
        if str(eff["effect_class"]) == "no_effect":
            effects.append(
                {
                    "effect_id": str(eff["effect_id"]),
                    "effect_class": "no_effect",
                    "description": str(eff.get("description", "No domain effect in deterministic proof.")),
                }
            )

    return ParticipantActionResultModel.model_validate(
        {
            "status": "succeeded",
            "participant_address": participant_address,
            "episode_id": episode_id,
            "action_instance_id": action_instance_id,
            "action_contract_address": action_contract_address,
            "observation_point": f"{action_instance_id}:terminal-observation",
            "preconditions": preconditions,
            "effects": effects,
            "observations": [f"{action_instance_id}:terminal-observation"],
            "evidence_refs": [],
        }
    )
