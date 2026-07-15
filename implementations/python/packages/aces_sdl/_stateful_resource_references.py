"""Cross-section reference validation for stateful realization resources."""

from collections.abc import Mapping

from .nodes import Node
from .stateful_resources import GeneratedArtifact, PersistentVolume


def _validate_consumer_references(
    *, owner: str, resource: GeneratedArtifact | PersistentVolume, node_refs: set[str]
) -> None:
    for consumer in resource.consumers:
        if consumer.node not in node_refs:
            raise ValueError(f"{owner} consumer node reference {consumer.node!r} is missing")


def _validate_dependency_references(
    *,
    owner: str,
    resource: GeneratedArtifact | PersistentVolume,
    stateful_refs: set[str],
) -> None:
    for dependency in (*resource.ordering_dependencies, *resource.refresh_dependencies):
        if dependency not in stateful_refs:
            raise ValueError(f"{owner} dependency reference {dependency!r} is missing")


def validate_stateful_resource_references(
    *,
    nodes: Mapping[str, Node],
    generated_artifacts: Mapping[str, GeneratedArtifact],
    persistent_volumes: Mapping[str, PersistentVolume],
) -> None:
    """Reject incomplete stateful graphs before compilation or dispatch."""

    node_refs = set(nodes) | {f"nodes.{name}" for name in nodes}
    stateful_refs = (
        set(generated_artifacts)
        | {f"generated_artifacts.{name}" for name in generated_artifacts}
        | set(persistent_volumes)
        | {f"persistent_volumes.{name}" for name in persistent_volumes}
    )
    for section, resources in (
        ("generated_artifacts", generated_artifacts),
        ("persistent_volumes", persistent_volumes),
    ):
        for name, resource in resources.items():
            owner = f"{section}.{name}"
            _validate_consumer_references(owner=owner, resource=resource, node_refs=node_refs)
            _validate_dependency_references(owner=owner, resource=resource, stateful_refs=stateful_refs)
