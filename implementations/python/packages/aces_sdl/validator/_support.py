"""Shared module-level helpers for the SemanticValidator package."""

from collections import defaultdict, deque
from dataclasses import dataclass, field

from ..orchestration import WorkflowStep

# Common ref-path prefix used by qualified runtime/service refs (e.g.
# ``nodes.vm.services.http``, ``nodes.vm.runtime.applications.webapp``).
_NODES_PREFIX = "nodes."


@dataclass
class _WorkflowBuildState:
    """Per-workflow graph-build accumulators threaded through edge collection."""

    graph: dict[str, list[str]]
    predicate_step_refs: dict[str, list[str]] = field(default_factory=dict)
    join_targets: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


@dataclass
class _CompensationState:
    """Cross-workflow call- and compensation-graph accumulators."""

    call_graph: dict[str, set[str]]
    compensation_graph: dict[str, set[str]]
    compensation_targets: set[str] = field(default_factory=set)
    workflows_with_compensation: set[str] = field(default_factory=set)


@dataclass
class _AvailableStateContext:
    """State threaded through the predicate available-step-state recursion."""

    workflow_steps: dict[str, WorkflowStep]
    graph: dict[str, list[str]]
    predecessors: dict[str, set[str]]
    start: str
    join_targets: dict[str, list[str]]
    available_memo: dict[str, set[str]] = field(default_factory=dict)
    branch_memo: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    visiting: set[str] = field(default_factory=set)


def _topological_sort(graph: dict[str, list[str]]) -> list[str] | None:
    """Return topological order or None if a cycle exists."""
    in_degree: dict[str, int] = defaultdict(int)
    for node in graph:
        in_degree.setdefault(node, 0)
    for deps in graph.values():
        for dep in deps:
            in_degree[dep] += 1

    queue = deque(n for n, d in in_degree.items() if d == 0)
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for dep in graph.get(node, []):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    return order if len(order) == len(in_degree) else None
