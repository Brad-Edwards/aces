"""Tests for the backend-manifest-v2 -> BackendManifest reverse adapter (issue #609).

The adapter is the inverse of ``backend_manifest_v2_model``: it reconstructs the
internal typed :class:`BackendManifest` (running its own capability validators)
from a validated ``BackendManifestV2Model`` so the plan-inspection CLI can plan
against an externally supplied manifest. Realization-envelope-bearing manifests
fail closed because a v2 payload carries only the envelope identity, not the full
digest-checked declaration the planner needs.
"""

from __future__ import annotations

import pytest
from raes_backend_protocols.manifest import (
    backend_manifest_from_v2_model,
    backend_manifest_v2_model,
)
from raes_backend_stubs.manifest import create_stub_manifest
from raes_contracts.contracts import BackendManifestV2Model


def test_round_trips_the_full_stub_manifest() -> None:
    original = create_stub_manifest()
    v2_model = backend_manifest_v2_model(original)

    reconstructed = backend_manifest_from_v2_model(v2_model)

    assert reconstructed == original


@pytest.mark.parametrize(
    ("with_participant_runtime", "with_observation"),
    [(False, True), (True, False), (False, False)],
)
def test_round_trips_reduced_capability_stub_manifests(with_participant_runtime: bool, with_observation: bool) -> None:
    original = create_stub_manifest(
        with_participant_runtime=with_participant_runtime,
        with_observation=with_observation,
    )

    reconstructed = backend_manifest_from_v2_model(backend_manifest_v2_model(original))

    assert reconstructed == original
    assert (reconstructed.participant_runtime is not None) == with_participant_runtime
    assert (reconstructed.observation is not None) == with_observation


def test_round_trip_reconstructs_via_serialized_payload() -> None:
    """A payload that survives JSON serialization + revalidation still round-trips."""

    original = create_stub_manifest()
    payload = backend_manifest_v2_model(original).model_dump(mode="json")

    revalidated = BackendManifestV2Model.model_validate(payload)
    reconstructed = backend_manifest_from_v2_model(revalidated)

    assert reconstructed == original


def test_envelope_bearing_manifest_fails_closed() -> None:
    stub_payload = backend_manifest_v2_model(create_stub_manifest()).model_dump(mode="json")
    stub_payload["supported_contract_versions"].append("realization-envelope-v1")
    stub_payload["realization_envelope"] = {
        "contract_id": "realization-envelope-v1",
        "envelope_id": "example-envelope",
        "schema_version": "realization-envelope/v1",
        "digest": "sha256:" + "0" * 64,
        "configuration_digest": "sha256:" + "1" * 64,
    }
    envelope_model = BackendManifestV2Model.model_validate(stub_payload)

    with pytest.raises(ValueError, match="realization envelope"):
        backend_manifest_from_v2_model(envelope_model)
