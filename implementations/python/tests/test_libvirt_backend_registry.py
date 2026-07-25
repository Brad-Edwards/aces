"""Issue #601: libvirt backend target and registry construction."""

from __future__ import annotations

from raes_backend_libvirt import (
    LIBVIRT_BACKEND_NAME,
    LibvirtProvisioner,
    create_libvirt_components,
    create_libvirt_manifest,
    create_libvirt_target,
    register_libvirt_backend,
)

from raes_runtime.registry import BackendRegistry, RuntimeTarget


class _NoopDriver:
    driver_mode = "generic"

    def realize(self, *, networks, domains):
        from raes_backend_libvirt.driver import DriverResult

        return DriverResult()

    def destroy(self, *, networks, domains):
        from raes_backend_libvirt.driver import DriverResult

        return DriverResult()

    def realized_addresses(self):
        return frozenset()


def test_create_target_passes_runtime_shape_validation():
    target = create_libvirt_target(driver=_NoopDriver())

    assert isinstance(target, RuntimeTarget)
    assert target.name == LIBVIRT_BACKEND_NAME
    assert isinstance(target.provisioner, LibvirtProvisioner)
    assert target.orchestrator is None
    assert target.evaluator is None
    assert target.participant_runtime is None


def test_register_and_create_via_registry_threads_driver_config():
    registry = BackendRegistry()
    register_libvirt_backend(registry)
    driver = _NoopDriver()

    target = registry.create(LIBVIRT_BACKEND_NAME, driver=driver)

    assert target.name == LIBVIRT_BACKEND_NAME
    assert target.manifest.name == LIBVIRT_BACKEND_NAME
    assert target.provisioner._driver is driver


def test_components_factory_accepts_and_ignores_extra_config_for_manifest_shape():
    manifest = create_libvirt_manifest(uri="qemu:///session")

    components = create_libvirt_components(manifest=manifest, driver=_NoopDriver(), uri="qemu:///session")

    assert isinstance(components.provisioner, LibvirtProvisioner)
    assert components.orchestrator is None
    assert components.evaluator is None
    assert components.participant_runtime is None
