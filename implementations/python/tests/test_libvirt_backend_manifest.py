"""Issue #601: libvirt provisioning backend manifest surface."""

from __future__ import annotations

from aces_backend_libvirt import create_libvirt_manifest
from aces_backend_protocols.manifest import backend_manifest_payload
from aces_contracts.contracts import BackendManifestV2Model

from aces.core.runtime.conformance import BackendCapabilityProfile, profile_for_manifest


def test_libvirt_manifest_renders_as_provisioning_only_manifest_v2():
    manifest = create_libvirt_manifest()

    payload = backend_manifest_payload(manifest)
    model = BackendManifestV2Model.model_validate(payload)

    assert model.identity.name == "libvirt-qemu"
    assert manifest.provisioner.name == "libvirt-provisioner"
    assert manifest.orchestrator is None
    assert manifest.evaluator is None
    assert manifest.participant_runtime is None
    assert manifest.observation is None
    assert profile_for_manifest(manifest) == BackendCapabilityProfile.PROVISIONING_ONLY


def test_libvirt_manifest_declares_only_provisioning_contract_surface():
    manifest = create_libvirt_manifest()

    assert manifest.supported_contract_versions == frozenset(
        {
            "backend-manifest-v2",
            "operation-receipt-v1",
            "operation-status-v1",
            "provisioning-plan-v1",
            "runtime-snapshot-v1",
        }
    )
