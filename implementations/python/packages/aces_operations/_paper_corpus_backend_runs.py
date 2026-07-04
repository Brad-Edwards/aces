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


def _mapping(value: object) -> Mapping[str, Any]:
    """Return ``value`` when it is a mapping, else an empty mapping (safe navigation)."""
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> list[Any]:
    """Return ``value`` as a list when it is a list/tuple, else an empty list."""
    return list(value) if isinstance(value, list | tuple) else []


def _backend_identity(artifact: Mapping[str, Any]) -> dict[str, str]:
    """Extract the libvirt backend id + version from the artifact (no raw manifest internals)."""
    provenance = _mapping(_mapping(artifact.get("backend")).get("realization_provenance"))
    name = str(provenance.get("backend") or "libvirt-qemu")
    version = "unknown"
    for disclosure in _sequence(artifact.get("realized_form_disclosures")):
        ref = _mapping(disclosure.get("realized_by_ref") if isinstance(disclosure, Mapping) else None)
        if ref.get("ref_kind") == "backend" and ref.get("ref_version"):
            version = str(ref["ref_version"])
            break
    return {"name": name, "version": version}


def _libvirt_surface_coverage(artifact: Mapping[str, Any]) -> dict[str, str]:
    """Map each accepted evidence surface to a bounded coverage note for the libvirt run."""
    defensive_source = str(_mapping(artifact.get("defensive_evidence")).get("evidence_source", "unknown"))
    topology_basis = str(_mapping(artifact.get("realized_topology")).get("basis", "unknown"))
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
    backend = _mapping(artifact.get("backend"))
    compiled = _mapping(artifact.get("compiled_artifact"))
    topology = _mapping(artifact.get("realized_topology"))
    proof = _mapping(artifact.get("participant_action_proof"))
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
        "capability_profile": _mapping(backend.get("capability_profile")),
        "scenario": _mapping(artifact.get("scenario")),
        "compiled_address_sets": _mapping(compiled.get("compiled_address_sets")),
        "compiled_model_fingerprint": str(compiled.get("compiled_model_fingerprint", "")),
        "topology": {
            "basis": str(topology.get("basis", "unknown")),
            "network_attachment_matrix": _mapping(topology.get("network_attachment_matrix")),
        },
        "realization_characteristics": {
            "substrate": "native libvirt/QEMU VM and network appliances",
            "participant_proof": str(proof.get("runtime", "unknown")),
            "defensive_evidence": str(_mapping(artifact.get("defensive_evidence")).get("evidence_source", "unknown")),
        },
        "evidence_surface_coverage": _libvirt_surface_coverage(artifact),
        "unsupported_or_degraded_surfaces": list(_sequence(topology.get("unrealized_capabilities"))),
        "limitations": list(_sequence(artifact.get("limitations"))),
        "non_claims": list(_sequence(artifact.get("non_claims"))),
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


def _apply_export_scenario(
    descriptor: dict[str, Any], scenario: Mapping[str, Any], export: Mapping[str, Any]
) -> list[str]:
    """Record the export's own scenario digest (honest preserved/divergent); diagnose a mismatch."""
    export_scenario = export.get("scenario")
    export_digest = export_scenario.get("content_sha256") if isinstance(export_scenario, Mapping) else None
    if not export_digest:
        return []
    descriptor["scenario"] = {**descriptor["scenario"], "content_sha256": str(export_digest)}
    authored_digest = scenario.get("content_sha256")
    if str(export_digest) == str(authored_digest):
        return []
    return [
        f"APTL export scenario digest {str(export_digest)!r} does not match the authored scenario digest "
        f"{str(authored_digest)!r}"
    ]


def _apply_export_addresses(
    descriptor: dict[str, Any], address_sets: Mapping[str, Any], export: Mapping[str, Any]
) -> list[str]:
    """Record the export's own compiled address sets; a per-class mismatch fails the descriptor."""
    export_addresses = export.get("compiled_address_sets")
    if not isinstance(export_addresses, Mapping):
        return []
    aces_sets = {cls: sorted(str(a) for a in _sequence(values)) for cls, values in address_sets.items()}
    export_sets = {cls: sorted(str(a) for a in _sequence(export_addresses.get(cls))) for cls in aces_sets}
    descriptor["compiled_address_sets"] = export_sets
    return [
        f"APTL export compiled_address_sets[{cls}] differs from the compiled ACES address set"
        for cls in aces_sets
        if export_sets[cls] != aces_sets[cls]
    ]


def _apply_export_scalars(descriptor: dict[str, Any], export: Mapping[str, Any]) -> None:
    """Copy the remaining allowlisted portable scalars/lists from the export."""
    mode = export.get("evidence_source_mode")
    if isinstance(mode, str) and mode:
        descriptor["evidence_source_mode"] = mode
    limitations = export.get("limitations")
    if isinstance(limitations, Sequence) and not isinstance(limitations, str | bytes):
        descriptor["limitations"] = [str(item) for item in limitations] + descriptor["limitations"]


def _aptl_from_export(
    scenario: Mapping[str, Any], address_sets: Mapping[str, Any], export: Mapping[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Build the APTL descriptor from an operator-supplied export's allowlisted portable fields.

    Only ``_APTL_PORTABLE_KEYS`` are read; everything else (including any
    backend-private field) is ignored. The authored scenario identity/addresses come
    from the export when it supplies them, so a divergent export honestly fails
    rather than silently inheriting the ACES-side values.
    """
    descriptor = _aptl_summary_descriptor(scenario, address_sets)
    descriptor["evidence_provenance"] = "external-artifact-summarized"
    diagnostics = [
        *_apply_export_scenario(descriptor, scenario, export),
        *_apply_export_addresses(descriptor, address_sets, export),
    ]
    _apply_export_scalars(descriptor, export)
    return descriptor, diagnostics


def _read_export(path: Path) -> tuple[Mapping[str, Any] | None, str | None]:
    """Read and JSON-parse an APTL export; return ``(mapping_or_None, error_or_None)``."""
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"could not read APTL evidence export {path.name}: {exc}"
    if not isinstance(parsed, Mapping):
        return None, "APTL evidence export is not a JSON object; using documented-shape summary"
    return parsed, None


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
    export, read_error = _read_export(aptl_evidence_path)
    if export is None:
        return _aptl_summary_descriptor(scenario, address_sets), ([read_error] if read_error else [])
    return _aptl_from_export(scenario, address_sets, export)
