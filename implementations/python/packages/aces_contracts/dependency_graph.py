"""Pure deterministic dependency-graph algorithms shared across layers."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

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


@dataclass
class _TarjanState:
    graph: dict[str, tuple[str, ...]]
    index: int = 0
    indices: dict[str, int] = field(default_factory=dict)
    lowlinks: dict[str, int] = field(default_factory=dict)
    stack: list[str] = field(default_factory=list)
    on_stack: set[str] = field(default_factory=set)
    cycles: list[tuple[str, ...]] = field(default_factory=list)

    def connect(self, node: str) -> None:
        self.indices[node] = self.index
        self.lowlinks[node] = self.index
        self.index += 1
        self.stack.append(node)
        self.on_stack.add(node)
        for dependency in self.graph[node]:
            self._visit_dependency(node, dependency)
        if self.lowlinks[node] == self.indices[node]:
            self._record_component(node)

    def _visit_dependency(self, node: str, dependency: str) -> None:
        if dependency not in self.indices:
            self.connect(dependency)
            self.lowlinks[node] = min(self.lowlinks[node], self.lowlinks[dependency])
        elif dependency in self.on_stack:
            self.lowlinks[node] = min(self.lowlinks[node], self.indices[dependency])

    def _record_component(self, root: str) -> None:
        component: list[str] = []
        while self.stack:
            member = self.stack.pop()
            self.on_stack.remove(member)
            component.append(member)
            if member == root:
                break
        component.sort()
        if len(component) > 1 or component[0] in self.graph[component[0]]:
            self.cycles.append(tuple(component))


def dependency_cycles(
    dependencies_by_node: Mapping[str, Iterable[str]],
    *,
    sort_key: SortKey = _lexical_identity,
) -> list[tuple[str, ...]]:
    """Return strongly connected components that represent dependency cycles."""

    graph = dependency_graph(dependencies_by_node)
    if not graph:
        return []

    state = _TarjanState(graph)
    for node in sorted(graph, key=sort_key):
        if node not in state.indices:
            state.connect(node)

    return sorted(state.cycles, key=lambda cycle: tuple(sort_key(node) for node in cycle))


def topological_dependency_order(
    dependencies_by_node: Mapping[str, Iterable[str]],
    *,
    sort_key: SortKey = _lexical_identity,
) -> list[str]:
    """Return a stable topological order, appending residual nodes on cycles."""

    graph = dependency_graph(dependencies_by_node)
    dependents: dict[str, list[str]] = {node: [] for node in graph}
    indegree: dict[str, int] = dict.fromkeys(graph, 0)

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
