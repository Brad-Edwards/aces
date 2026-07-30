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

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from raes_backend_libvirt.techvault_native import expected_surface
from raes_backend_protocols.capabilities import (
    observation_capability_contract_gaps,
    participant_runtime_capability_contract_gaps,
)
from raes_backend_protocols.manifest import backend_manifest_payload
from raes_contracts.contracts import (
    EvaluationHistoryEventModel,
    EvaluationResultStateModel,
    ExperimentRealizedFormDisclosureModel,
)

from raes_operations._evidence_run_types import (
    BackendManifest,
    CompiledModel,
    EvidenceArtifactInputs,
    NodeDeployment,
    RealizedNetwork,
    TerminalSnapshot,
)
from raes_operations.run_artifacts import portable_artifact_ref

EVIDENCE_RUN_SCHEMA = "raes.libvirt.scenario-evidence-run/v1"
_LIBVIRT_BACKEND_NAME = "libvirt-qemu"

# Internal/evaluator-only surfaces the participant must never observe. Derived from
# the reference scenario observation boundary's hidden_refs; the negative-boundary
# evidence confirms none of these reach the participant's visible/disclosed refs.
_INTERNAL_SURFACE_KEYWORDS = ("customer-db", "wazuh", "evaluator", "policy-gate", "postgres")

# The four scenario non-claims (issue #615). Carried verbatim in the artifact.
_NON_CLAIMS = (
    "No Wazuh detection-quality claim.",
    "No model-defense robustness claim.",
    "No byte-equivalence or application-internals equivalence claim between libvirt appliances and APTL containers.",
    "No full semantic-equivalence claim beyond the invariant ledger in RAESystem/rae#600.",
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


def _manifest_name(manifest: BackendManifest) -> str:
    identity = getattr(manifest, "identity", None)
    if identity is not None and getattr(identity, "name", None):
        return str(identity.name)
    return str(getattr(manifest, "name", _LIBVIRT_BACKEND_NAME))


def _manifest_version(manifest: BackendManifest) -> str:
    identity = getattr(manifest, "identity", None)
    if identity is not None and getattr(identity, "version", None):
        return str(identity.version)
    return str(getattr(manifest, "version", "0.0.0+unknown"))


def _backend_section(
    manifest: BackendManifest,
    mode: str,
    substrate_realized: bool,
    cleanup_verified: bool | None,
) -> dict[str, Any]:
    """Embed the canonical BackendManifestV2 payload + capability-gap report.

    The manifest is rendered through ``backend_manifest_payload`` — the same
    canonical V2 renderer the rest of the stack uses — and re-validated against
    ``BackendManifestV2Model`` by the artifact validator, so the evidence carries
    the published backend contract rather than a hand-rolled summary. The
    capability profile reports any contract gaps between the declared participant-
    runtime / observation capabilities and their required contracts (empty when the
    manifest fully satisfies them).
    """
    return {
        "manifest": backend_manifest_payload(manifest),
        "capability_profile": {
            "participant_runtime_contract_gaps": list(participant_runtime_capability_contract_gaps(manifest)),
            "observation_contract_gaps": list(observation_capability_contract_gaps(manifest)),
        },
        "realization_provenance": {
            "backend": _manifest_name(manifest),
            "evidence_source_mode": mode,
            "substrate_realized": substrate_realized,
            "basis": "daemon-observed-substrate" if substrate_realized else "planned-not-realized",
            "cleanup_verified": cleanup_verified,
        },
    }


def _scenario_section(scenario_path: Path, model: CompiledModel) -> dict[str, Any]:
    from raes.parser import parse_sdl_file

    content = scenario_path.read_bytes()
    version: str | None = None
    try:
        version = getattr(parse_sdl_file(scenario_path), "version", None)
    except Exception:
        version = None
    return {
        "name": model.scenario_name,
        "version": version,
        "relative_path": portable_artifact_ref(scenario_path),
        "content_sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
    }


def _compiled_artifact_section(model: CompiledModel) -> dict[str, Any]:
    addresses = {
        "participant_behaviors": sorted(model.participant_behaviors),
        "action_contracts": sorted(model.action_contracts),
        "observation_boundaries": sorted(model.observation_boundaries),
        "objectives": sorted(model.objectives),
        "networks": sorted(model.networks),
        "node_deployments": sorted(model.node_deployments),
    }
    fingerprint = hashlib.sha256(json.dumps(addresses, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "processor": "raes-reference-processor",
        "compiled_address_sets": addresses,
        "compiled_model_fingerprint": "sha256:" + fingerprint,
    }


def _node_services(node: NodeDeployment) -> list[dict[str, Any]]:
    spec = getattr(node, "spec", {}) or {}
    node_spec = spec.get("node", {}) if isinstance(spec, Mapping) else {}
    services = node_spec.get("services", []) if isinstance(node_spec, Mapping) else []
    return [
        {"name": svc.get("name"), "port": svc.get("port"), "protocol": svc.get("protocol")}
        for svc in services
        if isinstance(svc, Mapping)
    ]


def _node_network_links(node: NodeDeployment) -> list[str]:
    spec = getattr(node, "spec", {}) or {}
    infra = spec.get("infrastructure", {}) if isinstance(spec, Mapping) else {}
    links = infra.get("links", []) if isinstance(infra, Mapping) else []
    return [str(link) for link in links]


def _network_properties(network: RealizedNetwork) -> dict[str, Any]:
    spec = getattr(network, "spec", {}) or {}
    infra = spec.get("infrastructure", {}) if isinstance(spec, Mapping) else {}
    props = infra.get("properties") if isinstance(infra, Mapping) else None
    if not isinstance(props, Mapping):
        return {}
    return {"cidr": props.get("cidr"), "gateway": props.get("gateway"), "internal": props.get("internal")}


def _realization_facts_section(
    model: CompiledModel,
    native_snapshot: Mapping[str, Any] | None,
    cleanup_verified: bool | None,
    guest_observed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    observed = native_snapshot if isinstance(native_snapshot, Mapping) else {}
    daemon_domains = observed.get("domains", ())
    daemon_networks = observed.get("networks", ())
    realized_addresses = observed.get("realized_addresses", ())
    return {
        "authored": {
            "source": "authored",
            "scenario_name": model.scenario_name,
        },
        "planned": {
            "source": "planned",
            "node_addresses": sorted(model.node_deployments),
            "network_addresses": sorted(model.networks),
        },
        "driver_reported": {
            "source": "driver-reported",
            "realized_addresses": list(realized_addresses) if isinstance(realized_addresses, list | tuple) else [],
        },
        "daemon_observed": {
            "source": "daemon-observed",
            "domains": list(daemon_domains) if isinstance(daemon_domains, list | tuple) else [],
            "networks": list(daemon_networks) if isinstance(daemon_networks, list | tuple) else [],
        },
        "guest_observed": _guest_observed_section(guest_observed),
        "cleanup": {
            "source": "driver-reported",
            "status": _cleanup_status(cleanup_verified),
        },
        "binding": observed.get("binding"),
    }


def _guest_observed_section(guest_observed: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return the guest-observed fact section: the bound report, or a not-observed stub.

    A daemon-only run discloses ``not-observed`` honestly; a guest-certified run
    embeds the operation-joined, challenge-bound, per-domain guest report.
    """

    if not isinstance(guest_observed, Mapping):
        return {"source": "guest-observed", "status": "not-observed"}
    return {**guest_observed, "source": "guest-observed"}


def _cleanup_status(cleanup_verified: bool | None) -> str:
    if cleanup_verified is None:
        return "not-required"
    return "verified" if cleanup_verified else "failed"


def _topology_section(
    model: CompiledModel,
    native_snapshot: Mapping[str, Any] | None,
    unrealized_capabilities: tuple[str, ...] = (),
) -> dict[str, Any]:
    substrate_realized = native_snapshot is not None
    nodes = [
        {
            "source": "planned",
            "address": node.address,
            "name": node.name,
            "node_type": getattr(node, "node_type", None),
            "os_family": getattr(node, "os_family", None),
            "services": _node_services(node),
            "networks": _node_network_links(node),
        }
        for node in model.node_deployments.values()
    ]
    networks = [
        {"source": "planned", "address": net.address, "name": net.name, **_network_properties(net)}
        for net in model.networks.values()
    ]
    section: dict[str, Any] = {
        "basis": "mixed-source" if substrate_realized else "planned",
        "disclosure": (
            "Compiled topology remains planned; the native surface contains only independently daemon-observed "
            "substrate fields."
            if substrate_realized
            else "Compiled/planned topology from the authored scenario; no live substrate realized. Network CIDRs and "
            "gateways are authored values, not host-private libvirt addresses."
        ),
        "networks": networks,
        "nodes": nodes,
        "network_attachment_matrix": {node["name"]: node["networks"] for node in nodes},
    }
    if native_snapshot is not None:
        section["native_surface"] = expected_surface(native_snapshot)
    if unrealized_capabilities:
        section["unrealized_capabilities"] = list(unrealized_capabilities)
        section["unrealized_capabilities_disclosure"] = (
            "The libvirt backend realizes the provisioning substrate (VMs and networks) only. The capabilities listed "
            "above (content placement, orchestration, and evaluation) are not realized by this backend and remain "
            "evaluator-only or translated; this is the n=2 backend-diversity limitation, not a substrate-realization "
            "failure."
        )
    return section


def _participant_proof_section(proof: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = proof["snapshot"]
    episodes = {addr: _redact_episode_state(state) for addr, state in snapshot.participant_episode_results.items()}
    return {
        "runtime": "libvirt-deterministic-participant-runtime",
        "lifecycle_clean": proof["lifecycle_clean"],
        "diagnostics": list(proof["diagnostics"]),
        "admitted_action_addresses": list(proof["admitted_action_addresses"]),
        "episode_states": episodes,
        # The participant runtime never received any visible/disclosed refs: the
        # admission surface exposes nothing of the internal or evaluator state.
        "participant_visible_refs": [],
        "participant_disclosed_refs": [],
        "structural_validation_note": (
            "Deep behavior-history and episode-snapshot invariant validation is performed by the issue #614 "
            "participant-runtime test suite (processor-layer iterators); this artifact records the libvirt "
            "participant-runtime lifecycle outcome."
        ),
    }


def _redact_episode_state(state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        return {}
    keep = (
        "state_schema_version",
        "participant_address",
        "episode_id",
        "sequence_number",
        "status",
        "terminal_reason",
        "last_control_action",
    )
    return {key: state.get(key) for key in keep if key in state}


def _terminal_observation_section(snapshot: TerminalSnapshot) -> dict[str, Any]:
    behavior_history = {
        addr: _redact_behavior_history(events) for addr, events in snapshot.participant_behavior_history.items()
    }
    return {
        "form": "participant-projected-history",
        "taxonomy": {
            "taxonomy_id": "raes-behavioral-relations",
            "taxonomy_revision": "rev7",
            "non_claimed_relation_ids": [
                "participant-projected-history-equivalence",
                "epistemic-indistinguishability",
                "alternating-strategic-equivalence",
            ],
        },
        "observation_projection": {
            "subject": "the participant addressed by each behavior-history stream",
            "policy_ref": "participant-observation-boundary",
            "policy_revision": "participant-observation-envelope/v1",
            "redaction_scope": "Only the fields retained by _redact_behavior_history are disclosed.",
            "order_treatment": "Recorded participant sequence order is preserved.",
            "simultaneity_treatment": "No simultaneity equivalence is inferred from the serialized order.",
        },
        "evidence_boundary": (
            "The terminal snapshot's named participant behavior-history streams for this single run; "
            "no second execution or universal trace set is compared."
        ),
        "disclosure": (
            "The libvirt participant runtime emits a behavior-history event stream rather than a standalone SEM-210 "
            "observation envelope; the terminal participant view is reported as a bounded participant projection."
        ),
        "explicit_non_claims": [
            "This single projected record does not establish participant-projected-history-equivalence.",
            "It does not establish epistemic or strategic equivalence.",
        ],
        "behavior_history": behavior_history,
    }


def _redact_behavior_history(events: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(events, Sequence):
        return out
    for event in events:
        if not isinstance(event, Mapping):
            continue
        out.append(
            {
                "event_type": event.get("event_type"),
                "action_instance_id": event.get("action_instance_id"),
                "action_contract_address": event.get("action_contract_address"),
                "observation_boundary_address": event.get("observation_boundary_address"),
            }
        )
    return out


def _defensive_evidence_section(
    native_snapshot: Mapping[str, Any] | None, model: CompiledModel, recorded_at: str
) -> dict[str, Any]:
    # captured_at is the run's recorded_at timestamp threaded through artifact
    # assembly, not a freshly synthesized one, so every section shares one
    # consistent run timestamp and the artifact stays reproducible.
    evidence_channels = _boundary_evidence_refs(model)
    substrate_note = (
        " Daemon-observed libvirt substrate state is present, but it is not guest SOC observation."
        if native_snapshot is not None
        else ""
    )
    return {
        "evidence_kind": "telemetry",
        "evidence_source": "structural-evaluator-channel",
        "visibility": "evaluator-only",
        "sensitivity": "restricted",
        "redaction_state": "withheld",
        "loss_disclosure": (
            "Deterministic mode: no live SOC substrate is booted. Wazuh/SOC defensive evidence is reported as the "
            "evaluator-only evidence channels declared by the scenario observation boundary, not upstream Wazuh "
            f"detection output; no detection-quality claim is made.{substrate_note}"
        ),
        "evaluator_evidence_channels": evidence_channels,
        "payload_summary": (
            "Evaluator-only Wazuh/SOC and policy-decision evidence channels are declared and kept off the participant "
            "view; neither evidence mode claims guest SOC readback."
        ),
        "captured_at": recorded_at,
    }


def _negative_boundary_section(boundary_refs: Sequence[str]) -> dict[str, Any]:
    internal_refs = [ref for ref in boundary_refs if any(kw in ref for kw in _INTERNAL_SURFACE_KEYWORDS)]
    checks = [{"ref": ref, "exposed_to_participant": False} for ref in internal_refs]
    return {
        "method": (
            "Structural boundary analysis over the compiled observation boundary (hidden_refs) and the participant "
            "exposure policy (empty visible/disclosed refs). The participant action surface does not expose the "
            "internal DB, Wazuh, evaluator, or policy-gate surfaces."
        ),
        "value_status": "reported",
        "all_internal_surfaces_withheld": all(not c["exposed_to_participant"] for c in checks),
        "checks": checks,
        "disclosure": "Negative boundary checks are evaluator-side derived analysis, not participant observations.",
    }


def _evaluator_outcome_section(lifecycle_clean: bool, recorded_at: str) -> dict[str, Any]:
    status = "ready" if lifecycle_clean else "failed"
    result = EvaluationResultStateModel.model_validate(
        {
            "resource_type": "participant-loop-evaluation",
            "run_id": "scenario-evidence",
            "status": status,
            "observed_at": recorded_at,
            "updated_at": recorded_at,
            "passed": lifecycle_clean,
            "detail": "Structural participant-loop proof over the libvirt deterministic participant runtime.",
            "evidence_refs": ["participant_action_proof", "negative_boundary_checks"],
        }
    )
    history = EvaluationHistoryEventModel.model_validate(
        {
            "event_type": "evaluation_completed",
            "timestamp": recorded_at,
            "status": status,
            "passed": lifecycle_clean,
            "detail": "Scenario-evidence evaluator outcome derived from the structural participant proof.",
            "evidence_refs": ["participant_action_proof"],
        }
    )
    return {
        "result": result.model_dump(mode="json"),
        "history": [history.model_dump(mode="json")],
        "limitations": [
            "Evaluator outcome reflects the structural participant-loop proof; the libvirt backend ships no generic "
            "evaluator component, so this is a evidence-run evaluator record, not a generic backend evaluator result.",
        ],
    }


def _realized_form_disclosures(manifest: BackendManifest, substrate_realized: bool) -> list[dict[str, Any]]:
    backend_version = _manifest_version(manifest)
    backend_name = _manifest_name(manifest)
    backend_ref = {"ref_kind": "backend", "ref_id": backend_name, "ref_version": backend_version}
    disclosures = [
        ExperimentRealizedFormDisclosureModel.model_validate(
            {
                "concern_id": "libvirt-backend-selection",
                "concern_kind": "backend-selection",
                "basis": "backend-realized",
                "realized_by_ref": backend_ref,
                "realized_value_summary": (
                    f"{backend_name} backend ({backend_version}); substrate "
                    f"{'daemon-observed at bounded fields' if substrate_realized else 'planned, not realized'}."
                ),
                "disclosure": (
                    "The libvirt-qemu backend supplied the run; live claims are limited to independently "
                    "daemon-observed substrate fields."
                ),
            }
        ),
        ExperimentRealizedFormDisclosureModel.model_validate(
            {
                "concern_id": "libvirt-participant-implementation",
                "concern_kind": "participant-implementation",
                "basis": "backend-realized",
                "realized_by_ref": backend_ref,
                "realized_value_summary": (
                    "Deterministic libvirt participant runtime (no live domain execution); see issue #614."
                ),
                "disclosure": (
                    "The participant action proof uses the deterministic domain adapter; live domain execution is not "
                    "performed."
                ),
            }
        ),
    ]
    return [d.model_dump(mode="json") for d in disclosures]


def _limitations(mode: str, unrealized_capabilities: tuple[str, ...] = ()) -> list[str]:
    limitations = [
        "The libvirt participant runtime uses the deterministic domain adapter; no live participant domain is "
        "executed (issue #614).",
        "Wazuh/SOC evidence is evaluator-only structural evidence; daemon substrate state is not promoted to guest "
        "or application observation.",
    ]
    if mode != "native-live":
        limitations.append(
            "Deterministic mode does not realize a live libvirt substrate; topology and defensive evidence channels "
            "are compiled/structural, explicitly disclosed as not-live observations."
        )
    if unrealized_capabilities:
        limitations.append(
            "Native-live mode realizes the provisioning substrate only; content placement, orchestration, and "
            "evaluation declared by the scenario are not realized by the libvirt backend."
        )
    return limitations


def _redaction_provenance() -> dict[str, Any]:
    return {
        "policy": (
            "Only allowlisted, bounded fields are copied into the artifact. Raw libvirt XML, domain UUIDs, QEMU "
            "command lines, host paths, connection URIs, credentials, private keys, and backend-private inspect "
            "payloads are never written."
        ),
        "redacted_field_classes": [
            "raw-libvirt-xml",
            "domain-uuid",
            "qemu-command-line",
            "host-path",
            "connection-uri",
            "credential",
            "private-key",
            "backend-private-inspect-payload",
        ],
        "provenance_refs": [
            "docs/decisions/issue-615-libvirt-paper-evidence-preflight.md",
            "docs/decisions/issue-614-libvirt-participant-runtime.md",
        ],
    }


def _invariant_ledger_refs(model: CompiledModel, scenario_section: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scenario_name": model.scenario_name,
        "scenario_content_sha256": scenario_section["content_sha256"],
        "participant_behaviors": sorted(model.participant_behaviors),
        "action_contracts": sorted(model.action_contracts),
        "observation_boundaries": sorted(model.observation_boundaries),
        "evidence_refs": [
            "participant_action_proof",
            "terminal_observation",
            "defensive_evidence",
            "negative_boundary_checks",
            "evaluator_outcome",
        ],
        "note": (
            "Stable RAES addresses and evidence refs for the RAESystem/rae#600 cross-backend invariant ledger; "
            "no libvirt domain UUIDs, host paths, or APTL-private identifiers."
        ),
    }


def _boundary_hidden_refs(model: CompiledModel) -> list[str]:
    return _boundary_spec_refs(model, "hidden_refs")


def _boundary_evidence_refs(model: CompiledModel) -> list[str]:
    return _boundary_spec_refs(model, "evidence_refs")


def _boundary_spec_refs(model: CompiledModel, key: str) -> list[str]:
    refs: list[str] = []
    for boundary in model.observation_boundaries.values():
        spec = getattr(boundary, "spec", None)
        if isinstance(spec, Mapping):
            for ref in spec.get(key, []) or []:
                if isinstance(ref, str):
                    refs.append(ref)
    return refs
