"""Shared planner semantic tests."""

from __future__ import annotations

import itertools
from types import SimpleNamespace

from hypothesis import given, settings
from hypothesis import strategies as st
from raes_processor.semantics.planner import (
    DependencyKind,
    canonical_resource_identity,
    dependency_cycles,
    dependency_edges,
    dependency_graph,
    refresh_impacted_nodes,
    resource_delete_order,
    resource_topological_order,
    topological_dependency_order,
)


def _resource(
    *,
    ordering: tuple[str, ...] = (),
    refresh: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        ordering_dependencies=ordering,
        refresh_dependencies=refresh,
    )


@st.composite
def _dag_resources(draw):
    size = draw(st.integers(min_value=1, max_value=6))
    nodes = [f"resource.{index}" for index in range(size)]
    resources: dict[str, SimpleNamespace] = {}
    for index, node in enumerate(nodes):
        available = nodes[:index]
        if available:
            ordering = tuple(
                draw(
                    st.lists(
                        st.sampled_from(available),
                        unique=True,
                        max_size=len(available),
                    )
                )
            )
            refresh = tuple(
                draw(
                    st.lists(
                        st.sampled_from(available),
                        unique=True,
                        max_size=len(available),
                    )
                )
            )
        else:
            ordering = ()
            refresh = ()
        resources[node] = _resource(ordering=ordering, refresh=refresh)
    return resources


@st.composite
def _dag_resources_with_change_sets(draw):
    resources = draw(_dag_resources())
    nodes = list(resources)
    subset_a = set(draw(st.lists(st.sampled_from(nodes), unique=True, max_size=len(nodes)))) if nodes else set()
    remaining = [node for node in nodes if node not in subset_a]
    subset_b = subset_a | (
        set(
            draw(
                st.lists(
                    st.sampled_from(remaining),
                    unique=True,
                    max_size=len(remaining),
                )
            )
        )
        if remaining
        else set()
    )
    return resources, subset_a, subset_b


def _dependency_graphs() -> st.SearchStrategy[dict[str, tuple[str, ...]]]:
    """Small graphs that freely admit self-loops and multi-node cycles."""

    def _build(size: int, choices: list[list[int]]) -> dict[str, tuple[str, ...]]:
        nodes = [f"nodes.host-{index}" for index in range(size)]
        return {
            node: tuple(nodes[target % size] for target in targets)
            for node, targets in zip(nodes, choices, strict=True)
        }

    # Deliberately larger and denser than the DAG strategies above: the explicit
    # frame stack has to resume a partially consumed iterator, so the graphs that
    # matter are the ones where a node still has unvisited dependencies left when
    # a descent happens and some of those are already on the stack.
    return st.integers(min_value=1, max_value=18).flatmap(
        lambda size: st.lists(
            st.lists(st.integers(min_value=0, max_value=17), max_size=6),
            min_size=size,
            max_size=size,
        ).map(lambda choices: _build(size, choices))
    )


def _exhaustive_dependency_graphs(size: int):
    """Enumerate every simple directed graph of one fixed small size."""

    nodes = tuple(f"nodes.host-{index}" for index in range(size))
    possible_edges = tuple(itertools.product(nodes, repeat=2))
    for mask in range(1 << len(possible_edges)):
        yield {
            node: tuple(
                target
                for edge_index, (source, target) in enumerate(possible_edges)
                if source == node and mask & (1 << edge_index)
            )
            for node in nodes
        }


def _reference_dependency_cycles(
    dependencies_by_node: dict[str, tuple[str, ...]],
) -> list[tuple[str, ...]]:
    """Recursive Tarjan reference for differential comparison.

    Kept deliberately naive: it mirrors the textbook recursion the production
    walk replaced, so any behavioural drift in the explicit-stack version shows
    up as a mismatch rather than as a silently different plan order.
    """

    graph = dependency_graph(dependencies_by_node)
    if not graph:
        return []
    counter = itertools.count()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cycles: list[tuple[str, ...]] = []

    def strongconnect(node: str) -> None:
        indices[node] = lowlinks[node] = next(counter)
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

    for node in sorted(graph, key=canonical_resource_identity):
        if node not in indices:
            strongconnect(node)
    return sorted(cycles, key=lambda cycle: tuple(canonical_resource_identity(node) for node in cycle))


class TestPlannerSemantics:
    def test_dependency_edges_preserve_kinds(self):
        resources = {
            "evaluation.metric.uptime": _resource(
                ordering=("evaluation.condition.vm.health",),
                refresh=("orchestration.workflow.flow",),
            ),
            "evaluation.condition.vm.health": _resource(),
            "orchestration.workflow.flow": _resource(),
        }

        ordering_edges = dependency_edges(resources, kind=DependencyKind.ORDERING)
        refresh_edges = dependency_edges(resources, kind=DependencyKind.REFRESH)

        assert ordering_edges[0].kind == DependencyKind.ORDERING
        assert ordering_edges[0].target == "evaluation.condition.vm.health"
        assert refresh_edges[0].kind == DependencyKind.REFRESH
        assert refresh_edges[0].target == "orchestration.workflow.flow"

    def test_refresh_impacted_nodes_propagate_transitively(self):
        resources = {
            "evaluation.condition.vm.health": _resource(),
            "evaluation.metric.uptime": _resource(refresh=("evaluation.condition.vm.health",)),
            "evaluation.goal.pass": _resource(refresh=("evaluation.metric.uptime",)),
        }

        assert refresh_impacted_nodes(
            resources,
            {"evaluation.condition.vm.health"},
        ) == (
            "evaluation.metric.uptime",
            "evaluation.goal.pass",
        )

    @given(_dag_resources())
    def test_topological_order_respects_dependencies(self, resources):
        order = resource_topological_order(resources)
        positions = {address: index for index, address in enumerate(order)}

        for address, resource in resources.items():
            for dependency in resource.ordering_dependencies:
                assert positions[dependency] < positions[address]

        assert resource_delete_order(resources) == list(reversed(order))

    @given(_dag_resources_with_change_sets())
    def test_refresh_propagation_is_monotonic(self, payload):
        resources, subset_a, subset_b = payload

        impacted_a = subset_a | set(refresh_impacted_nodes(resources, subset_a))
        impacted_b = subset_b | set(refresh_impacted_nodes(resources, subset_b))

        assert impacted_a <= impacted_b


class TestDependencyCycleScale:
    """Cycle detection must survive dependency chains longer than the recursion limit."""

    _DEEP = 5000

    def _chain(self, size: int) -> dict[str, tuple[str, ...]]:
        graph: dict[str, tuple[str, ...]] = {
            f"nodes.host-{index:05d}": (f"nodes.host-{index + 1:05d}",) for index in range(size)
        }
        graph[f"nodes.host-{size:05d}"] = ()
        return graph

    def test_deep_acyclic_chain_reports_no_cycles(self):
        assert dependency_cycles(self._chain(self._DEEP)) == []

    def test_deep_cycle_is_still_detected(self):
        size = 3000
        graph = {f"nodes.host-{index:05d}": (f"nodes.host-{(index + 1) % size:05d}",) for index in range(size)}

        cycles = dependency_cycles(graph)

        assert len(cycles) == 1
        assert len(cycles[0]) == size

    def test_deep_chain_topological_order_is_complete(self):
        graph = self._chain(self._DEEP)

        assert len(topological_dependency_order(graph)) == len(graph)

    def test_unknown_dependency_references_do_not_become_graph_nodes(self):
        graph = {
            "nodes.host-a": ("nodes.host-missing",),
            "nodes.host-b": ("nodes.host-a",),
        }

        assert dependency_cycles(graph) == []

    def test_cycle_order_is_independent_of_mapping_and_edge_insertion_order(self):
        forward = {
            "nodes.host-a": ("nodes.host-b",),
            "nodes.host-b": ("nodes.host-a",),
            "nodes.host-c": ("nodes.host-c",),
            "nodes.host-d": (),
        }
        reversed_input = {
            node: tuple(reversed(dependencies)) for node, dependencies in reversed(tuple(forward.items()))
        }

        expected = [("nodes.host-a", "nodes.host-b"), ("nodes.host-c",)]
        assert dependency_cycles(forward) == expected
        assert dependency_cycles(reversed_input) == expected

    def test_cycle_detection_matches_oracle_for_every_graph_up_to_three_nodes(self):
        for size in range(1, 4):
            for graph in _exhaustive_dependency_graphs(size):
                assert dependency_cycles(graph) == _reference_dependency_cycles(graph)

    @settings(max_examples=400)
    @given(_dependency_graphs())
    def test_cycle_detection_matches_a_reference_walk(self, graph):
        """Guards the explicit-stack walk against the recursive semantics it replaced."""

        assert dependency_cycles(graph) == _reference_dependency_cycles(graph)
