"""Backend-run descriptor builders for the paper demonstration corpus (issue #600).

A backend-run descriptor is the portable, bounded projection of one backend's
realization of the authored paper scenario. Two descriptors -- one libvirt, one
APTL -- are the ``backend_runs`` of the cross-backend invariant ledger.

Only stable ACES-side facts cross into a descriptor: the authored scenario
identity/digest, the compiled ACES address sets, backend id + capability profile,
topology basis + network-attachment matrix, per-surface evidence coverage, and
disclosed limitations. Backend-private semantics (libvirt domain UUIDs/XML, QEMU
command lines, host paths; APTL container ids, Compose service names, Docker
inspect payloads, upstream Wazuh rule bodies) never enter a descriptor -- see the
issue #600 preflight redaction gate.

The libvirt descriptor is extracted from the real ``aces.libvirt.paper-evidence-run/v1``
artifact (issue #615) and marked ``generated-in-repo``. The APTL descriptor is a
bounded summary of the publicly documented APTL realization
(``examples/scenarios/paper-agent-loop.README.md`` + Brad-Edwards/aptl#558) marked
``external-summarized``; when an operator supplies a real APTL evidence export, the
same descriptor is built from that file's allowlisted portable fields and marked
``external-artifact-summarized``. ACES never imports APTL-private schemas.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

# The evidence surfaces issue #600's acceptance criteria require each backend run
# to record or link. Each descriptor maps every surface to a bounded coverage note.
ACCEPTED_EVIDENCE_SURFACES: tuple[str, ...] = (
    "scenario_source_hash",
    "processor_artifact_identity",
    "backend_manifest_capability_profile",
    "runtime_snapshots",
    "realized_topology_matrix",
    "participant_implementation_provenance",
    "participant_episode_history",
    "participant_behavior_history",
    "participant_terminal_observation",
    "evaluator_wazuh_evidence",
    "outcome_interpretation_evidence",
)

_APTL_EVIDENCE_ISSUE = "Brad-Edwards/aptl#558"
_APTL_EVIDENCE_URL = "https://github.com/Brad-Edwards/aptl/issues/558"

# Allowlisted portable keys copied from an operator-supplied APTL evidence export.
# Anything else in the file is ignored, so APTL-private semantics cannot leak in.
_APTL_PORTABLE_KEYS: tuple[str, ...] = (
    "scenario",
    "compiled_address_sets",
    "evidence_source_mode",
    "limitations",
    "non_claims",
)


def _get(payload: Mapping[str, Any], *path: str, default: Any = None) -> Any:
    """Safely read a nested value from a mapping tree, returning ``default`` on any miss."""
    node: Any = payload
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return default
        node = node[key]
    return node


def _backend_identity(artifact: Mapping[str, Any]) -> dict[str, str]:
    """Extract the libvirt backend id + version from the artifact (no raw manifest internals)."""
    name = str(_get(artifact, "backend", "realization_provenance", "backend", default="libvirt-qemu"))
    version = "unknown"
    for disclosure in _get(artifact, "realized_form_disclosures", default=[]) or []:
        ref = disclosure.get("realized_by_ref", {}) if isinstance(disclosure, Mapping) else {}
        if isinstance(ref, Mapping) and ref.get("ref_kind") == "backend" and ref.get("ref_version"):
            version = str(ref["ref_version"])
            break
    return {"name": name, "version": version}


def _libvirt_surface_coverage(artifact: Mapping[str, Any]) -> dict[str, str]:
    """Map each accepted evidence surface to a bounded coverage note for the libvirt run."""
    defensive_source = str(_get(artifact, "defensive_evidence", "evidence_source", default="unknown"))
    topology_basis = str(_get(artifact, "realized_topology", "basis", default="unknown"))
    return {
        "scenario_source_hash": "recorded",
        "processor_artifact_identity": "recorded",
        "backend_manifest_capability_profile": "recorded",
        "runtime_snapshots": "recorded (participant lifecycle snapshot)",
        "realized_topology_matrix": f"recorded ({topology_basis})",
        "participant_implementation_provenance": "recorded",
        "participant_episode_history": "recorded",
        "participant_behavior_history": "recorded",
        "participant_terminal_observation": "recorded (behavior-history-equivalent)",
        "evaluator_wazuh_evidence": f"recorded (evaluator-only; {defensive_source})",
        "outcome_interpretation_evidence": "recorded",
    }


def build_libvirt_backend_run(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Build the libvirt backend-run descriptor from its paper-evidence artifact.

    Copies only portable, timestamp-free fields so the descriptor (and therefore the
    corpus) is byte-stable across runs; the full timestamped evidence stays in the
    regenerable ``aces.libvirt.paper-evidence-run/v1`` artifact.
    """
    return {
        "backend_id": "libvirt-reference",
        "realization": "aces-libvirt-reference-backend",
        "evidence_source_mode": str(artifact.get("evidence_source_mode", "deterministic")),
        "evidence_provenance": "generated-in-repo",
        "evidence_locator": {
            "kind": "regenerable-artifact",
            "schema": str(artifact.get("schema", "")),
            "command": "aces libvirt paper validate-evidence",
        },
        "backend_manifest": _backend_identity(artifact),
        "capability_profile": _get(artifact, "backend", "capability_profile", default={}),
        "scenario": _get(artifact, "scenario", default={}),
        "compiled_address_sets": _get(artifact, "compiled_artifact", "compiled_address_sets", default={}),
        "compiled_model_fingerprint": _get(artifact, "compiled_artifact", "compiled_model_fingerprint", default=""),
        "topology": {
            "basis": str(_get(artifact, "realized_topology", "basis", default="unknown")),
            "network_attachment_matrix": _get(artifact, "realized_topology", "network_attachment_matrix", default={}),
        },
        "realization_characteristics": {
            "substrate": "native libvirt/QEMU VM and network appliances",
            "participant_proof": str(_get(artifact, "participant_action_proof", "runtime", default="unknown")),
            "defensive_evidence": str(_get(artifact, "defensive_evidence", "evidence_source", default="unknown")),
        },
        "evidence_surface_coverage": _libvirt_surface_coverage(artifact),
        "unsupported_or_degraded_surfaces": list(
            _get(artifact, "realized_topology", "unrealized_capabilities", default=[]) or []
        ),
        "limitations": list(artifact.get("limitations", []) or []),
        "non_claims": list(artifact.get("non_claims", []) or []),
    }


def _aptl_summary_descriptor(scenario: Mapping[str, Any], address_sets: Mapping[str, Any]) -> dict[str, Any]:
    """Build the APTL descriptor from the publicly documented APTL realization shape."""
    return {
        "backend_id": "aptl-docker",
        "realization": "aptl-emulation-backend",
        "evidence_source_mode": "docker-live",
        "evidence_provenance": "external-summarized",
        "evidence_locator": {"kind": "external-issue", "ref": _APTL_EVIDENCE_ISSUE, "url": _APTL_EVIDENCE_URL},
        "backend_manifest": {"name": "aptl-docker", "version": "external"},
        "capability_profile": {},
        "scenario": dict(scenario),
        "compiled_address_sets": dict(address_sets),
        "compiled_model_fingerprint": "",
        "topology": {"basis": "external-summarized", "network_attachment_matrix": {}},
        "realization_characteristics": {
            "substrate": "Docker/Compose containers",
            "participant_proof": "live participant runtime",
            "defensive_evidence": "upstream Wazuh live detection telemetry",
        },
        "evidence_surface_coverage": {
            surface: f"external-summarized ({_APTL_EVIDENCE_ISSUE})" for surface in ACCEPTED_EVIDENCE_SURFACES
        },
        "unsupported_or_degraded_surfaces": [
            "In-repo record is a bounded summary of the APTL realization; per-surface evidence lives in "
            f"{_APTL_EVIDENCE_ISSUE}."
        ],
        "limitations": [
            "APTL evidence is summarized and linked, not re-executed in this repository or embedded here.",
            "The authored scenario identity is the ACES-side authored digest both backends consume; byte-level "
            f"confirmation against the APTL export ({_APTL_EVIDENCE_ISSUE}) is external to this repository.",
            "No APTL-private container ids, Compose service names, Docker inspect payloads, or raw Wazuh rule "
            "bodies are recorded as portable semantics.",
        ],
        "non_claims": [
            "No Wazuh detection-quality claim.",
            "No model-defense robustness claim.",
            "No byte-equivalence or application-internals equivalence claim between APTL containers and libvirt "
            "appliances.",
            "No full semantic-equivalence claim beyond this invariant ledger.",
        ],
    }


def _aptl_from_export(
    scenario: Mapping[str, Any], address_sets: Mapping[str, Any], export: Mapping[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Build the APTL descriptor from an operator-supplied export's allowlisted portable fields.

    Only ``_APTL_PORTABLE_KEYS`` are read; everything else (including any
    backend-private field) is ignored. The authored scenario identity/addresses
    remain the ACES-side values -- the export cannot redefine the authored scenario.
    """
    descriptor = _aptl_summary_descriptor(scenario, address_sets)
    descriptor["evidence_provenance"] = "external-artifact-summarized"
    diagnostics: list[str] = []
    export_scenario = export.get("scenario") if isinstance(export, Mapping) else None
    if isinstance(export_scenario, Mapping):
        export_digest = export_scenario.get("content_sha256")
        authored_digest = scenario.get("content_sha256")
        if export_digest:
            # Record the export's own authored-scenario digest so the ledger honestly
            # shows preserved vs divergent rather than assuming the authored value.
            descriptor["scenario"] = {**descriptor["scenario"], "content_sha256": str(export_digest)}
        if export_digest and export_digest != authored_digest:
            diagnostics.append(
                f"APTL export scenario digest {export_digest!r} does not match the authored scenario digest "
                f"{authored_digest!r}"
            )
    export_addresses = export.get("compiled_address_sets") if isinstance(export, Mapping) else None
    if isinstance(export_addresses, Mapping):
        # Record the export's OWN compiled address sets so the ledger honestly shows
        # preserved vs divergent rather than assuming the authored ACES addresses; a
        # per-class mismatch fails the descriptor (the pairing is not the same
        # compiled scenario).
        aces_sets = {cls: sorted(str(a) for a in (values or [])) for cls, values in address_sets.items()}
        export_sets = {cls: sorted(str(a) for a in (export_addresses.get(cls) or [])) for cls in aces_sets}
        descriptor["compiled_address_sets"] = export_sets
        diagnostics.extend(
            f"APTL export compiled_address_sets[{cls}] differs from the compiled ACES address set"
            for cls in aces_sets
            if export_sets[cls] != aces_sets[cls]
        )
    export_mode = export.get("evidence_source_mode") if isinstance(export, Mapping) else None
    if isinstance(export_mode, str) and export_mode:
        descriptor["evidence_source_mode"] = export_mode
    export_limitations = export.get("limitations") if isinstance(export, Mapping) else None
    if isinstance(export_limitations, Sequence) and not isinstance(export_limitations, str | bytes):
        descriptor["limitations"] = [str(item) for item in export_limitations] + descriptor["limitations"]
    return descriptor, diagnostics


def build_aptl_backend_run(
    scenario: Mapping[str, Any],
    address_sets: Mapping[str, Any],
    aptl_evidence_path: Path | None,
) -> tuple[dict[str, Any], list[str]]:
    """Build the APTL backend-run descriptor.

    Returns ``(descriptor, diagnostics)``. Without an export path the descriptor is
    the documented-shape summary + link; with one it is the export's allowlisted
    portable projection. A read/parse failure falls back to the summary and records
    a diagnostic rather than raising.
    """
    if aptl_evidence_path is None:
        return _aptl_summary_descriptor(scenario, address_sets), []
    try:
        export = json.loads(aptl_evidence_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return (
            _aptl_summary_descriptor(scenario, address_sets),
            [f"could not read APTL evidence export {aptl_evidence_path.name}: {exc}"],
        )
    if not isinstance(export, Mapping):
        return (
            _aptl_summary_descriptor(scenario, address_sets),
            ["APTL evidence export is not a JSON object; using documented-shape summary"],
        )
    return _aptl_from_export(scenario, address_sets, export)
