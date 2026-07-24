"""Pure deterministic dependency-graph algorithms shared across layers."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Mapping

SortKey = Callable[[str], object]


def _lexical_identity(value: str) -> object:
    return (value,)


def dependency_graph(
    dependencies_by_node: Mapping[str, Iterable[str]],
) -> dict[str, tuple[str, ...]]:
    """Normalize a dependency graph to only include known nodes."""

    known_nodes = set(dependencies_by_node)
    return {
        node: tuple(dependency for dependency in dependencies if dependency in known_nodes)
        for node, dependencies in dependencies_by_node.items()
    }


def dependency_cycles(
    dependencies_by_node: Mapping[str, Iterable[str]],
    *,
    sort_key: SortKey = _lexical_identity,
) -> list[tuple[str, ...]]:
    """Return strongly connected components that represent dependency cycles."""

    graph = dependency_graph(dependencies_by_node)
    if not graph:
        return []

    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cycles: list[tuple[str, ...]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for dependency in graph[node]:
            if dependency not in indices:
                strongconnect(dependency)
                lowlinks[node] = min(lowlinks[node], lowlinks[dependency])
            elif dependency in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[dependency])

        if lowlinks[node] != indices[node]:
            return

        component: list[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break

        component = sorted(component)
        if len(component) > 1 or component[0] in graph[component[0]]:
            cycles.append(tuple(component))

    for node in sorted(graph, key=sort_key):
        if node not in indices:
            strongconnect(node)

    return sorted(cycles, key=lambda cycle: tuple(sort_key(node) for node in cycle))


def topological_dependency_order(
    dependencies_by_node: Mapping[str, Iterable[str]],
    *,
    sort_key: SortKey = _lexical_identity,
) -> list[str]:
    """Return a stable topological order, appending residual nodes on cycles."""

    graph = dependency_graph(dependencies_by_node)
    dependents: dict[str, list[str]] = {node: [] for node in graph}
    indegree: dict[str, int] = {node: 0 for node in graph}

    for node, dependencies in graph.items():
        for dependency in dependencies:
            dependents[dependency].append(node)
            indegree[node] += 1

    queue = deque(sorted((node for node, degree in indegree.items() if degree == 0), key=sort_key))
    order: list[str] = []

    while queue:
        current = queue.popleft()
        order.append(current)
        for dependent in sorted(dependents[current], key=sort_key):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                queue.append(dependent)

    if len(order) != len(graph):
        order.extend(sorted((node for node in graph if node not in order), key=sort_key))

    return order


def reverse_delete_order(
    dependencies_by_node: Mapping[str, Iterable[str]],
    *,
    sort_key: SortKey = _lexical_identity,
) -> list[str]:
    """Return reverse topological order for delete/teardown semantics."""

    return list(reversed(topological_dependency_order(dependencies_by_node, sort_key=sort_key)))


__all__ = [
    "dependency_cycles",
    "dependency_graph",
    "reverse_delete_order",
    "topological_dependency_order",
]
