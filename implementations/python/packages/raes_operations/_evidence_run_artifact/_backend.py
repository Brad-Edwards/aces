"""Backend-manifest and realized-form section builders for the evidence artifact."""

from __future__ import annotations

from typing import Any

from raes_backend_protocols.capabilities import (
    observation_capability_contract_gaps,
    participant_runtime_capability_contract_gaps,
)
from raes_backend_protocols.manifest import backend_manifest_payload
from raes_contracts.contracts import (
    ExperimentRealizedFormDisclosureModel,
)

from raes_operations._evidence_run_types import (
    BackendManifest,
)

_LIBVIRT_BACKEND_NAME = "libvirt-qemu"


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
