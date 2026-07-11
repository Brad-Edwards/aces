"""Configuration-bound libvirt realization-envelope selection (ASR-519)."""

from __future__ import annotations

from dataclasses import replace
from textwrap import dedent

import pytest
from aces_backend_libvirt.manifest import create_libvirt_manifest
from aces_backend_libvirt.provisioner import LibvirtProvisioner
from aces_backend_libvirt.target import create_libvirt_components, create_libvirt_target
from aces_backend_libvirt.techvault_native import TechVaultNativeLibvirtDriver
from aces_backend_protocols.manifest import backend_manifest_payload
from aces_contracts.realization_envelope import BackendRealizationEnvelopeModel, realization_envelope_digest
from aces_processor.reference import run_reference_processor
from aces_sdl.parser import parse_sdl
from libvirt_conformance_fixtures import RecordingLibvirtDriver


def test_default_libvirt_manifest_selects_generic_envelope():
    manifest = create_libvirt_manifest()

    assert manifest.realization_envelope is not None
    assert manifest.realization_envelope.id == "libvirt-qemu.generic.v1"
    assert manifest.realization_envelope.configuration.mode == "generic"
    assert "realization-envelope-v1" in manifest.supported_contract_versions
    assert backend_manifest_payload(manifest)["realization_envelope"] == (
        manifest.realization_envelope.identity.model_dump(mode="json")
    )


def test_operational_config_does_not_change_generic_material_identity():
    default = create_libvirt_manifest().realization_envelope
    configured = create_libvirt_manifest(connection_uri="qemu:///session", name_prefix="example").realization_envelope

    assert default is not None and configured is not None
    assert default.identity == configured.identity


def test_injected_driver_requires_explicit_mode():
    class DriverWithoutMode:
        pass

    with pytest.raises(ValueError, match="driver_mode is required"):
        create_libvirt_target(driver=DriverWithoutMode())


def test_injected_generic_driver_selects_generic_envelope():
    target = create_libvirt_target(driver=RecordingLibvirtDriver(), driver_mode="generic")

    assert target.manifest.realization_envelope is not None
    assert target.manifest.realization_envelope.configuration.mode == "generic"


def test_techvault_driver_selects_narrow_appliance_envelope(tmp_path):
    driver = TechVaultNativeLibvirtDriver(state_dir=tmp_path)
    target = create_libvirt_target(driver=driver, driver_mode="techvault-appliance")
    envelope = target.manifest.realization_envelope

    assert envelope is not None
    assert envelope.id == "libvirt-qemu.techvault-appliance.v1"
    assert envelope.configuration.mode == "techvault-appliance"
    assert target.manifest.provisioner.supported_os_families == {"linux"}
    assert not target.manifest.provisioner.supported_content_types
    assert not target.manifest.provisioner.supports_accounts
    assert not target.manifest.provisioner.supports_acls


def test_driver_and_declared_mode_must_match(tmp_path):
    driver = TechVaultNativeLibvirtDriver(state_dir=tmp_path)

    with pytest.raises(ValueError, match="does not match driver_mode"):
        create_libvirt_target(driver=driver, driver_mode="generic")


def test_direct_provisioner_construction_binds_techvault_driver_mode(tmp_path):
    driver = TechVaultNativeLibvirtDriver(state_dir=tmp_path)
    generic = create_libvirt_manifest(driver_mode="generic")

    with pytest.raises(ValueError, match="capabilities do not match driver mode"):
        LibvirtProvisioner(
            driver,
            provisioner_capabilities=generic.provisioner,
            realization_envelope=generic.realization_envelope.identity,
        )


def test_unknown_libvirt_configuration_fails_closed():
    with pytest.raises(ValueError, match="unknown libvirt target configuration"):
        create_libvirt_target(unrecognized=True)


def test_manifest_broader_than_selected_envelope_fails_before_driver_io():
    manifest = create_libvirt_manifest(driver_mode="generic")
    broader_provisioner = replace(
        manifest.provisioner,
        supported_content_types=manifest.provisioner.supported_content_types | {"dataset"},
    )
    broader_manifest = replace(
        manifest,
        capabilities=replace(manifest.capabilities, provisioner=broader_provisioner),
    )
    driver = RecordingLibvirtDriver()

    with pytest.raises(ValueError, match="capabilities do not match realization envelope"):
        create_libvirt_components(
            manifest=broader_manifest,
            driver=driver,
            driver_mode="generic",
        )

    assert not driver.recorded_ops


def _scenario():
    return parse_sdl(
        dedent(
            """
            name: envelope-test
            nodes:
              vm:
                type: vm
                os: linux
                resources: {ram: 1 gib, cpu: 1}
            """
        )
    )


def test_planner_carries_selected_envelope_identity_to_provisioning_plan():
    manifest = create_libvirt_manifest()

    result = run_reference_processor(_scenario(), manifest)

    assert result.execution_plan.provisioning.realization_envelope == manifest.realization_envelope.identity


def test_planner_uses_shared_membership_relation_for_selected_envelope():
    manifest = create_libvirt_manifest()
    payload = manifest.realization_envelope.model_dump(mode="json")
    payload["expression"]["domains"] = {"name": {"kind": "exact", "value": "different-scenario"}}
    payload["expression"]["bindings"] = [{"path": "name", "scope": "scenario", "posture": "exact", "domain": "name"}]
    payload["digest"] = realization_envelope_digest(payload)
    restricted = BackendRealizationEnvelopeModel.model_validate(payload)

    result = run_reference_processor(_scenario(), replace(manifest, realization_envelope=restricted))

    assert "realization-envelope.membership.domain-mismatch" in {diag.code for diag in result.diagnostics}
