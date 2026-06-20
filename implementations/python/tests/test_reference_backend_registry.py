"""RUN-314: registry/target shape + descriptor tests."""

from __future__ import annotations

from aces_reference_backend import (
    REFERENCE_BACKEND_NAME,
    create_reference_backend_components,
    create_reference_backend_manifest,
    create_reference_backend_target,
    register_reference_backend,
)
from aces_reference_backend.drivers.inprocess import InProcessDriver
from aces_reference_backend.provisioner import ReferenceProvisioner

from aces.core.runtime.registry import BackendRegistry, RuntimeTarget


def test_create_target_passes_shape_validation():
    target = create_reference_backend_target()

    assert isinstance(target, RuntimeTarget)
    assert target.name == REFERENCE_BACKEND_NAME
    assert target.orchestrator is not None
    assert target.evaluator is not None
    assert target.participant_runtime is not None


def test_register_and_create_via_registry():
    registry = BackendRegistry()
    register_reference_backend(registry)

    assert registry.is_registered(REFERENCE_BACKEND_NAME)
    target = registry.create(REFERENCE_BACKEND_NAME)

    assert target.name == REFERENCE_BACKEND_NAME
    assert target.manifest.name == REFERENCE_BACKEND_NAME


def test_driver_config_flows_through_to_components():
    driver = InProcessDriver()
    manifest = create_reference_backend_manifest()
    components = create_reference_backend_components(manifest=manifest, driver=driver)

    assert isinstance(components.provisioner, ReferenceProvisioner)
    assert components.provisioner._driver is driver


def test_registry_create_threads_driver_config():
    registry = BackendRegistry()
    register_reference_backend(registry)
    driver = InProcessDriver()

    target = registry.create(REFERENCE_BACKEND_NAME, driver=driver)

    assert target.provisioner._driver is driver


def test_manifest_factory_is_single_source_of_truth():
    registry = BackendRegistry()
    register_reference_backend(registry)

    manifest = registry.manifest(REFERENCE_BACKEND_NAME)

    assert manifest.name == REFERENCE_BACKEND_NAME
    assert manifest.has_participant_runtime
