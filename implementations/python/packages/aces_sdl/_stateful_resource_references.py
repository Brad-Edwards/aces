"""Semantic validation for stateful realization resource references."""

from collections.abc import Mapping

from .nodes import Node, OSFamily
from .stateful_resources import GeneratedArtifact, PersistentVolume


def _node_name(reference: str, nodes: Mapping[str, Node]) -> str | None:
    name = reference.removeprefix("nodes.") if reference.startswith("nodes.") else reference
    return name if name in nodes else None


def _dependency_candidates(
    reference: str,
    *,
    generated_artifacts: Mapping[str, GeneratedArtifact],
    persistent_volumes: Mapping[str, PersistentVolume],
) -> list[str]:
    if reference.startswith("generated_artifacts."):
        name = reference.removeprefix("generated_artifacts.")
        return [reference] if name in generated_artifacts else []
    if reference.startswith("persistent_volumes."):
        name = reference.removeprefix("persistent_volumes.")
        return [reference] if name in persistent_volumes else []

    candidates: list[str] = []
    if reference in generated_artifacts:
        candidates.append(f"generated_artifacts.{reference}")
    if reference in persistent_volumes:
        candidates.append(f"persistent_volumes.{reference}")
    return candidates


def _consumer_reference_errors(
    *,
    owner: str,
    resource: GeneratedArtifact | PersistentVolume,
    nodes: Mapping[str, Node],
    occupied_destinations: dict[tuple[str, str], str],
) -> list[str]:
    errors: list[str] = []
    for consumer in resource.consumers:
        node_name = _node_name(consumer.node, nodes)
        if node_name is None:
            errors.append(f"{owner} consumer node reference {consumer.node!r} is missing")
            continue
        node = nodes[node_name]
        if node.os is OSFamily.WINDOWS or node.os == OSFamily.WINDOWS.value:
            errors.append(f"{owner} uses a POSIX mount_destination for Windows consumer node {node_name!r}")
        destination = (node_name, consumer.mount_destination)
        previous = occupied_destinations.get(destination)
        if previous is None:
            occupied_destinations[destination] = owner
        else:
            errors.append(
                f"{owner} mount_destination {consumer.mount_destination!r} on node {node_name!r} "
                f"is already consumed by {previous}"
            )
    return errors


def _dependency_reference_errors(
    *,
    owner: str,
    resource: GeneratedArtifact | PersistentVolume,
    generated_artifacts: Mapping[str, GeneratedArtifact],
    persistent_volumes: Mapping[str, PersistentVolume],
) -> list[str]:
    errors: list[str] = []
    for dependency in (*resource.ordering_dependencies, *resource.refresh_dependencies):
        candidates = _dependency_candidates(
            dependency,
            generated_artifacts=generated_artifacts,
            persistent_volumes=persistent_volumes,
        )
        if not candidates:
            errors.append(f"{owner} dependency reference {dependency!r} is missing")
        elif len(candidates) > 1:
            choices = ", ".join(candidates)
            errors.append(f"{owner} dependency reference {dependency!r} is ambiguous; use one of: {choices}")
    return errors


def stateful_resource_reference_errors(
    *,
    nodes: Mapping[str, Node],
    generated_artifacts: Mapping[str, GeneratedArtifact],
    persistent_volumes: Mapping[str, PersistentVolume],
) -> list[str]:
    """Return bounded semantic errors before compilation or dispatch."""

    errors: list[str] = []
    occupied_destinations: dict[tuple[str, str], str] = {}
    for section, resources in (
        ("generated_artifacts", generated_artifacts),
        ("persistent_volumes", persistent_volumes),
    ):
        for name, resource in resources.items():
            owner = f"{section}.{name}"
            errors.extend(
                _consumer_reference_errors(
                    owner=owner,
                    resource=resource,
                    nodes=nodes,
                    occupied_destinations=occupied_destinations,
                )
            )
            errors.extend(
                _dependency_reference_errors(
                    owner=owner,
                    resource=resource,
                    generated_artifacts=generated_artifacts,
                    persistent_volumes=persistent_volumes,
                )
            )
    return errors


__all__ = ["stateful_resource_reference_errors"]
