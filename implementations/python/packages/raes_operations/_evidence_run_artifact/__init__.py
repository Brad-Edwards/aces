"""Artifact assembly for the libvirt scenario-evidence producer.

Builds the ``raes.libvirt.scenario-evidence-run/v1`` payload from the compiled runtime
model, the backend manifest, the participant-proof result, and (optionally) the
native substrate snapshot. Section builders only read duck-typed runtime-layer
objects and copy allowlisted, bounded fields, so no raw libvirt/backend internals
reach the artifact. The backend section embeds the canonical ``BackendManifestV2``
payload rendered by the pure ``raes_backend_protocols`` manifest/capability helpers
(ADR-036 allows ``raes_operations`` those two side-effect-free renderers) so the
evidence carries the same backend contract the rest of the stack uses, not a
hand-rolled summary. Split from ``libvirt_evidence_run`` to keep each module under
the ADR-015 source-size cap.
"""

from __future__ import annotations

from typing import Any

from raes_operations._evidence_run_types import (
    EvidenceArtifactInputs,
)

from ._backend import _backend_section, _realized_form_disclosures
from ._evidence import (
    _boundary_hidden_refs,
    _defensive_evidence_section,
    _evaluator_outcome_section,
    _limitations,
    _negative_boundary_section,
    _redaction_provenance,
)
from ._participant import _participant_proof_section, _terminal_observation_section
from ._topology import (
    _compiled_artifact_section,
    _invariant_ledger_refs,
    _realization_facts_section,
    _scenario_section,
    _topology_section,
)

EVIDENCE_RUN_SCHEMA = "raes.libvirt.scenario-evidence-run/v1"

# The four scenario non-claims (issue #615). Carried verbatim in the artifact.
_NON_CLAIMS = (
    "No Wazuh detection-quality claim.",
    "No model-defense robustness claim.",
    "No byte-equivalence or application-internals equivalence claim between libvirt appliances and APTL containers.",
    "No full semantic-equivalence claim beyond the invariant ledger in OpenRAE/rae#600.",
)


def assemble_artifact(inputs: EvidenceArtifactInputs) -> dict[str, Any]:
    """Assemble the full scenario-evidence artifact payload."""
    scenario_path = inputs.scenario_path
    run_id = inputs.run_id
    recorded_at = inputs.recorded_at
    mode = inputs.mode
    model = inputs.model
    manifest = inputs.manifest
    proof = inputs.proof
    native_snapshot = inputs.native_snapshot
    native_cleanup_verified = inputs.native_cleanup_verified
    unrealized_capabilities = inputs.unrealized_capabilities

    substrate_realized = native_snapshot is not None
    scenario_section = _scenario_section(scenario_path, model)
    boundary_refs = _boundary_hidden_refs(model)

    return {
        "schema": EVIDENCE_RUN_SCHEMA,
        "run_id": run_id,
        "recorded_at": recorded_at,
        "evidence_source_mode": mode,
        "scenario": scenario_section,
        "compiled_artifact": _compiled_artifact_section(model),
        "backend": _backend_section(manifest, mode, substrate_realized, native_cleanup_verified),
        "realization_facts": _realization_facts_section(
            model, native_snapshot, native_cleanup_verified, inputs.guest_observed
        ),
        "realized_topology": _topology_section(model, native_snapshot, unrealized_capabilities),
        "participant_action_proof": _participant_proof_section(proof),
        "terminal_observation": _terminal_observation_section(proof["snapshot"]),
        "defensive_evidence": _defensive_evidence_section(native_snapshot, model, recorded_at),
        "negative_boundary_checks": _negative_boundary_section(boundary_refs),
        "evaluator_outcome": _evaluator_outcome_section(proof["lifecycle_clean"], recorded_at),
        "realized_form_disclosures": _realized_form_disclosures(manifest, substrate_realized),
        "limitations": _limitations(mode, unrealized_capabilities),
        "non_claims": list(_NON_CLAIMS),
        "redaction_provenance": _redaction_provenance(),
        "invariant_ledger_refs": _invariant_ledger_refs(model, scenario_section),
    }
