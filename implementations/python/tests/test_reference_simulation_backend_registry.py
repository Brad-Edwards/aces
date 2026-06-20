"""RUN-315: registry/target shape + simulator config flow."""

from __future__ import annotations

from aces_reference_simulation_backend import (
    REFERENCE_SIMULATION_BACKEND_NAME,
    InProcessSimulationEngine,
    ReferenceSimulationProvisioner,
    create_reference_simulation_backend_components,
    create_reference_simulation_backend_manifest,
    create_reference_simulation_backend_target,
    register_reference_simulation_backend,
)

from aces.core.runtime.registry import BackendRegistry, RuntimeTarget


def test_create_target_passes_shape_validation():
    target = create_reference_simulation_backend_target()

    assert isinstance(target, RuntimeTarget)
    assert target.name == REFERENCE_SIMULATION_BACKEND_NAME
    assert target.orchestrator is not None
    assert target.evaluator is not None
    assert target.participant_runtime is not None


def test_register_and_create_via_registry():
    registry = BackendRegistry()
    register_reference_simulation_backend(registry)

    assert registry.is_registered(REFERENCE_SIMULATION_BACKEND_NAME)
    target = registry.create(REFERENCE_SIMULATION_BACKEND_NAME)

    assert target.name == REFERENCE_SIMULATION_BACKEND_NAME
    assert target.manifest.name == REFERENCE_SIMULATION_BACKEND_NAME


def test_engine_config_flows_through_to_components():
    engine = InProcessSimulationEngine()
    manifest = create_reference_simulation_backend_manifest()
    components = create_reference_simulation_backend_components(manifest=manifest, engine=engine)

    assert isinstance(components.provisioner, ReferenceSimulationProvisioner)
    assert components.provisioner._engine is engine


def test_registry_create_threads_engine_config():
    registry = BackendRegistry()
    register_reference_simulation_backend(registry)
    engine = InProcessSimulationEngine()

    target = registry.create(REFERENCE_SIMULATION_BACKEND_NAME, engine=engine)

    assert target.provisioner._engine is engine


def test_manifest_factory_is_single_source_of_truth():
    registry = BackendRegistry()
    register_reference_simulation_backend(registry)

    manifest = registry.manifest(REFERENCE_SIMULATION_BACKEND_NAME, engine=object())

    assert manifest.name == REFERENCE_SIMULATION_BACKEND_NAME
    assert manifest.has_participant_runtime
