"""Deterministic bounded impact-path traversal for semantic comparison."""

from __future__ import annotations

from collections import deque

from raes_contracts.semantic_comparison import (
    ComparisonReason,
    DependencyChangeModel,
    IdentityRelation,
    ImpactPathModel,
    ImpactPathStepModel,
    RelationStatus,
    SemanticChangeModel,
    SemanticComparisonRequestModel,
)


def impact_paths(
    request: SemanticComparisonRequestModel,
    changes: tuple[SemanticChangeModel, ...],
    dependencies: tuple[DependencyChangeModel, ...],
    reasons: set[ComparisonReason],
) -> tuple[ImpactPathModel, ...]:
    adjacency = _impact_adjacency(dependencies)
    sources = _impact_sources(changes)
    paths: list[ImpactPathModel] = []
    for source in sources:
        exhausted = _append_source_paths(request, source, adjacency, paths, reasons)
        if exhausted:
            break
    return tuple(sorted(paths, key=_path_key))


def _impact_adjacency(
    dependencies: tuple[DependencyChangeModel, ...],
) -> dict[str, list[ImpactPathStepModel]]:
    adjacency: dict[str, list[ImpactPathStepModel]] = {}
    for dependency in dependencies:
        state = dependency.after if dependency.after is not None else dependency.before
        side = "after" if dependency.after is not None else "before"
        if state is None:
            continue
        step = ImpactPathStepModel(
            dependent_identity=dependency.dependent_identity,
            dependency_identity=state.dependency_identity,
            rule_id=dependency.rule_id,
            evidence_side=side,
        )
        adjacency.setdefault(state.dependency_identity, []).append(step)
    return adjacency


def _impact_sources(changes: tuple[SemanticChangeModel, ...]) -> list[str]:
    return sorted(
        change.identity
        for change in changes
        if change.identity_relation != IdentityRelation.SAME
        or change.semantic_relation == RelationStatus.CHANGED
        or change.structural_relation == RelationStatus.CHANGED
    )


def _append_source_paths(
    request: SemanticComparisonRequestModel,
    source: str,
    adjacency: dict[str, list[ImpactPathStepModel]],
    paths: list[ImpactPathModel],
    reasons: set[ComparisonReason],
) -> bool:
    queue: deque[tuple[str, tuple[ImpactPathStepModel, ...]]] = deque([(source, ())])
    visited = {source}
    exhausted = False
    while queue and not exhausted:
        current, steps = queue.popleft()
        for step in _bounded_outgoing(request, current, steps, adjacency, reasons):
            exhausted = _append_path_step(request, source, step, steps, queue, visited, paths, reasons)
            if exhausted:
                break
    return exhausted


def _bounded_outgoing(
    request: SemanticComparisonRequestModel,
    current: str,
    steps: tuple[ImpactPathStepModel, ...],
    adjacency: dict[str, list[ImpactPathStepModel]],
    reasons: set[ComparisonReason],
) -> list[ImpactPathStepModel]:
    outgoing = sorted(adjacency.get(current, ()), key=lambda item: (item.dependent_identity, item.rule_id))
    if outgoing and len(steps) >= request.limits.max_path_depth:
        reasons.add(ComparisonReason.IMPACT_PATH_DEPTH_EXHAUSTED)
        outgoing = []
    return outgoing


def _append_path_step(
    request: SemanticComparisonRequestModel,
    source: str,
    step: ImpactPathStepModel,
    steps: tuple[ImpactPathStepModel, ...],
    queue: deque[tuple[str, tuple[ImpactPathStepModel, ...]]],
    visited: set[str],
    paths: list[ImpactPathModel],
    reasons: set[ComparisonReason],
) -> bool:
    next_steps = (*steps, step)
    paths.append(
        ImpactPathModel(
            source_identity=source,
            affected_identity=step.dependent_identity,
            steps=next_steps,
        )
    )
    exhausted = len(paths) >= request.limits.max_paths
    if exhausted:
        reasons.add(ComparisonReason.IMPACT_PATH_BOUND_EXHAUSTED)
    elif step.dependent_identity not in visited:
        visited.add(step.dependent_identity)
        queue.append((step.dependent_identity, next_steps))
    return exhausted


def _path_key(path: ImpactPathModel) -> tuple[str, str, tuple[tuple[str, str, str], ...]]:
    return (
        path.source_identity,
        path.affected_identity,
        tuple((step.dependency_identity, step.dependent_identity, step.rule_id) for step in path.steps),
    )


__all__: list[str] = []
