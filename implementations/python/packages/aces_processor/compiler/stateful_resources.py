"""Compilation of generated artifacts and persistent volumes."""

from typing import Any

from aces_sdl.scenario import InstantiatedScenario

from ..models import GeneratedArtifactRuntime, PersistentVolumeRuntime
from .addresses import (
    _generated_artifact_address,
    _node_address,
    _persistent_volume_address,
    _section_ref_name,
)
from .support import _dump


def _stateful_dependency_address(
    scenario: InstantiatedScenario,
    reference: str,
) -> str:
    if reference.startswith("generated_artifacts."):
        name = reference.removeprefix("generated_artifacts.")
        if name in scenario.generated_artifacts:
            return _generated_artifact_address(name)
    if reference.startswith("persistent_volumes."):
        name = reference.removeprefix("persistent_volumes.")
        if name in scenario.persistent_volumes:
            return _persistent_volume_address(name)
    in_artifacts = reference in scenario.generated_artifacts
    in_volumes = reference in scenario.persistent_volumes
    if in_artifacts != in_volumes:
        return _generated_artifact_address(reference) if in_artifacts else _persistent_volume_address(reference)
    raise ValueError("validated stateful dependency reference must resolve unambiguously")


def _stateful_spec(
    scenario: InstantiatedScenario,
    resource: object,
) -> dict[str, Any]:
    spec = _dump(resource)
    consumers: list[dict[str, Any]] = []
    for raw_consumer in spec.get("consumers", []):
        consumer = dict(raw_consumer)
        node_name = _section_ref_name(
            str(consumer.get("node", "")),
            "nodes",
            scenario.nodes,
        )
        consumer["node"] = node_name
        consumer["target_address"] = _node_address(node_name)
        consumers.append(consumer)
    spec["consumers"] = consumers
    return spec


def _compile_generated_artifacts(
    scenario: InstantiatedScenario,
) -> dict[str, GeneratedArtifactRuntime]:
    resources: dict[str, GeneratedArtifactRuntime] = {}
    for name, artifact in scenario.generated_artifacts.items():
        address = _generated_artifact_address(name)
        resources[address] = GeneratedArtifactRuntime(
            address=address,
            name=name,
            spec=_stateful_spec(scenario, artifact),
            ordering_dependencies=tuple(
                _stateful_dependency_address(scenario, ref) for ref in artifact.ordering_dependencies
            ),
            refresh_dependencies=tuple(
                _stateful_dependency_address(scenario, ref) for ref in artifact.refresh_dependencies
            ),
        )
    return resources


def _compile_persistent_volumes(
    scenario: InstantiatedScenario,
) -> dict[str, PersistentVolumeRuntime]:
    resources: dict[str, PersistentVolumeRuntime] = {}
    for name, volume in scenario.persistent_volumes.items():
        address = _persistent_volume_address(name)
        resources[address] = PersistentVolumeRuntime(
            address=address,
            name=name,
            spec=_stateful_spec(scenario, volume),
            ordering_dependencies=tuple(
                _stateful_dependency_address(scenario, ref) for ref in volume.ordering_dependencies
            ),
            refresh_dependencies=tuple(
                _stateful_dependency_address(scenario, ref) for ref in volume.refresh_dependencies
            ),
        )
    return resources
