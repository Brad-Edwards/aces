"""RUN-315: reference simulation backend manifest tests."""

from __future__ import annotations

from aces_backend_protocols.manifest import backend_manifest_payload
from aces_contracts.contracts import BackendManifestV2Model
from aces_reference_simulation_backend import (
    REFERENCE_SIMULATION_BACKEND_NAME,
    create_reference_simulation_backend_manifest,
)

from aces.core.runtime.conformance import BackendCapabilityProfile, profile_for_manifest


def test_manifest_renders_as_valid_backend_manifest_v2():
    manifest = create_reference_simulation_backend_manifest()

    payload = backend_manifest_payload(manifest)
    model = BackendManifestV2Model.model_validate(payload)

    assert model.identity.name == REFERENCE_SIMULATION_BACKEND_NAME
    assert model.identity.name == "reference-simulation"
    assert model.capabilities.provisioner.name == "reference-simulation-provisioner"
    assert payload["constraints"]["simulation_engine"] == "in-process-discrete"


def test_manifest_infers_full_remote_control_plane_profile():
    manifest = create_reference_simulation_backend_manifest()

    assert profile_for_manifest(manifest) == BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE


def test_manifest_declares_standard_runtime_components():
    manifest = create_reference_simulation_backend_manifest()

    assert manifest.has_orchestrator
    assert manifest.has_evaluator
    assert manifest.has_participant_runtime


def test_manifest_accepts_and_ignores_simulator_config_kwargs():
    manifest = create_reference_simulation_backend_manifest(engine=object(), seed=123, clock_policy="fixed")

    assert manifest.name == REFERENCE_SIMULATION_BACKEND_NAME
    assert manifest.constraints["clock"] == "simulation_tick"


def test_manifest_declares_only_evidence_backed_contract_ids():
    from aces_backend_stubs.stubs import create_stub_manifest

    manifest = create_reference_simulation_backend_manifest()

    assert manifest.supported_contract_versions == create_stub_manifest().supported_contract_versions
