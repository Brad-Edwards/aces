"""Issue #601: libvirt provisioning backend manifest surface."""

from __future__ import annotations

from raes_backend_libvirt import create_libvirt_manifest
from raes_backend_protocols.manifest import backend_manifest_payload
from raes_conformance.conformance import BackendCapabilityProfile, profile_for_manifest
from raes_contracts.contracts import BackendManifestV2Model


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
            "realization-envelope-v1",
            "operation-receipt-v1",
            "operation-status-v1",
            "provisioning-plan-v1",
            "runtime-snapshot-v1",
        }
    )


def test_libvirt_manifest_supports_vm_domains_and_switch_networks():
    manifest = create_libvirt_manifest()

    assert manifest.provisioner.supported_node_types == frozenset({"switch", "vm"})


def test_libvirt_manifest_narrows_unproven_content_and_account_realization():
    """ASR-519: only terms with a concrete generic-driver mechanism are claimed."""
    provisioner = create_libvirt_manifest().provisioner

    assert provisioner.supported_os_families == frozenset({"linux"})
    assert provisioner.supported_content_types == frozenset({"file"})
    assert provisioner.supported_account_features == frozenset({"groups", "shell", "home", "disabled", "auth_method"})
    assert provisioner.supports_accounts is True
    assert provisioner.supports_acls is True
