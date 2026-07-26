"""Cross-backend invariant ledger for the cross-backend evidence corpus (issue #600).

Computes the inspectable comparison between two backend-run descriptors (libvirt +
APTL) over the same authored scenario. The ledger has four sections, matching the
issue #600 acceptance criteria:

* ``preserved_invariants`` -- facts held identical across both backends (authored
  scenario digest, compiled RAES address sets, recorded evidence surfaces), each
  annotated with the per-backend basis (verified-in-artifact vs external-summarized)
  so an external summary is never presented as an independently verified fact;
* ``realization_differences`` -- where the two realizations legitimately differ
  (substrate, participant proof, defensive evidence, evidence provenance, mode);
* ``unsupported_or_degraded_surfaces`` -- per-backend capability gaps / degradations;
* ``evidence_limitations`` -- the union of both runs' limitations.

The ledger is derived interpretation over portable descriptor fields; it is not a
leaderboard, score table, or equivalence proof, and it invents no facts beyond what
the descriptors carry.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from raes_operations._cross_backend_corpus_backend_runs import ACCEPTED_EVIDENCE_SURFACES

_ADDRESS_CLASSES: tuple[str, ...] = (
    "participant_behaviors",
    "action_contracts",
    "observation_boundaries",
    "objectives",
    "networks",
    "node_deployments",
)


def _basis(run: Mapping[str, Any]) -> str:
    """Return the per-backend evidence basis label for an invariant row."""
    provenance = str(run.get("evidence_provenance", "unknown"))
    return "verified-in-artifact" if provenance == "generated-in-repo" else provenance


def _scenario_digest_invariant(libvirt: Mapping[str, Any], aptl: Mapping[str, Any]) -> dict[str, Any]:
    libvirt_digest = str((libvirt.get("scenario") or {}).get("content_sha256", ""))
    aptl_digest = str((aptl.get("scenario") or {}).get("content_sha256", ""))
    return {
        "invariant": "authored_scenario_digest",
        "value": libvirt_digest,
        "status": "preserved" if libvirt_digest and libvirt_digest == aptl_digest else "divergent",
        "per_backend": {
            libvirt["backend_id"]: {"value": libvirt_digest, "basis": _basis(libvirt)},
            aptl["backend_id"]: {"value": aptl_digest, "basis": _basis(aptl)},
        },
    }


def _address_invariants(libvirt: Mapping[str, Any], aptl: Mapping[str, Any]) -> list[dict[str, Any]]:
    libvirt_sets = libvirt.get("compiled_address_sets") or {}
    aptl_sets = aptl.get("compiled_address_sets") or {}
    rows: list[dict[str, Any]] = []
    for cls in _ADDRESS_CLASSES:
        libvirt_addrs = sorted(str(a) for a in (libvirt_sets.get(cls) or []))
        aptl_addrs = sorted(str(a) for a in (aptl_sets.get(cls) or []))
        rows.append(
            {
                "invariant": f"compiled_addresses:{cls}",
                "value": libvirt_addrs,
                "status": "preserved" if libvirt_addrs == aptl_addrs else "divergent",
                "per_backend": {
                    libvirt["backend_id"]: {"basis": _basis(libvirt)},
                    aptl["backend_id"]: {"basis": _basis(aptl)},
                },
            }
        )
    return rows


def _surface_invariants(libvirt: Mapping[str, Any], aptl: Mapping[str, Any]) -> list[dict[str, Any]]:
    libvirt_cov = libvirt.get("evidence_surface_coverage") or {}
    aptl_cov = aptl.get("evidence_surface_coverage") or {}
    rows: list[dict[str, Any]] = []
    for surface in ACCEPTED_EVIDENCE_SURFACES:
        libvirt_note = str(libvirt_cov.get(surface, "absent"))
        aptl_note = str(aptl_cov.get(surface, "absent"))
        both_present = libvirt_note != "absent" and aptl_note != "absent"
        rows.append(
            {
                "invariant": f"evidence_surface:{surface}",
                "status": "preserved" if both_present else "partial",
                "per_backend": {
                    libvirt["backend_id"]: {"coverage": libvirt_note, "basis": _basis(libvirt)},
                    aptl["backend_id"]: {"coverage": aptl_note, "basis": _basis(aptl)},
                },
            }
        )
    return rows


def _preserved_invariants(libvirt: Mapping[str, Any], aptl: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        _scenario_digest_invariant(libvirt, aptl),
        *_address_invariants(libvirt, aptl),
        *_surface_invariants(libvirt, aptl),
    ]


def _realization_differences(libvirt: Mapping[str, Any], aptl: Mapping[str, Any]) -> list[dict[str, Any]]:
    libvirt_chars = libvirt.get("realization_characteristics") or {}
    aptl_chars = aptl.get("realization_characteristics") or {}
    dimensions = ("substrate", "participant_proof", "defensive_evidence")
    rows = [
        {
            "dimension": dim,
            libvirt["backend_id"]: str(libvirt_chars.get(dim, "unknown")),
            aptl["backend_id"]: str(aptl_chars.get(dim, "unknown")),
        }
        for dim in dimensions
    ]
    rows.append(
        {
            "dimension": "evidence_provenance",
            libvirt["backend_id"]: str(libvirt.get("evidence_provenance", "unknown")),
            aptl["backend_id"]: str(aptl.get("evidence_provenance", "unknown")),
        }
    )
    rows.append(
        {
            "dimension": "evidence_source_mode",
            libvirt["backend_id"]: str(libvirt.get("evidence_source_mode", "unknown")),
            aptl["backend_id"]: str(aptl.get("evidence_source_mode", "unknown")),
        }
    )
    return rows


def _degraded_surfaces(libvirt: Mapping[str, Any], aptl: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"backend_id": run["backend_id"], "surfaces": list(run.get("unsupported_or_degraded_surfaces", []) or [])}
        for run in (libvirt, aptl)
    ]


def _dedupe(items: Sequence[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


def _evidence_limitations(libvirt: Mapping[str, Any], aptl: Mapping[str, Any]) -> list[str]:
    return _dedupe([*(libvirt.get("limitations") or []), *(aptl.get("limitations") or [])])


def build_invariant_ledger(libvirt: Mapping[str, Any], aptl: Mapping[str, Any]) -> dict[str, Any]:
    """Compute the four-section cross-backend invariant ledger from two backend runs."""
    return {
        "preserved_invariants": _preserved_invariants(libvirt, aptl),
        "realization_differences": _realization_differences(libvirt, aptl),
        "unsupported_or_degraded_surfaces": _degraded_surfaces(libvirt, aptl),
        "evidence_limitations": _evidence_limitations(libvirt, aptl),
    }
