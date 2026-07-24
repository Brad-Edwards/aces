"""Pure finite-graph analysis for authored historical state."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping

from ._historical_state_identity import actor_issues, identifier_issues, object_issues
from ._historical_state_lifecycle import (
    event_lifecycle_issues,
    event_reference_issues,
    global_historical_relationship_issues,
    relationship_issues,
)
from ._historical_state_materialization import (
    baseline_tenancy_issues,
    materialization_issues,
    readback_issues,
)
from ._historical_state_types import HistoricalStateIssue
from ._historical_state_types import historical_object_ref as _historical_object_ref

HistoricalStateIssue.__module__ = __name__


def historical_object_ref(baseline_name: str, object_id: str) -> str:
    """Return the canonical declaration address of a baseline-local object."""

    return _historical_object_ref(baseline_name, object_id)


def analyze_historical_state(
    *,
    historical_baselines: Mapping[str, object],
    entities: Mapping[str, object],
    agents: Mapping[str, object],
    accounts: Mapping[str, object],
    nodes: Mapping[str, object],
    content: Mapping[str, object],
    propositions: Mapping[str, object],
    assertions: Mapping[str, object],
    observation_boundaries: Mapping[str, object],
    deployment_tenants: Mapping[str, object],
    deployment_cells: Mapping[str, object],
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[HistoricalStateIssue, ...]:
    """Analyze all historical baselines and return deterministic collected issues."""

    issues: list[HistoricalStateIssue] = []
    relationship_ownership: defaultdict[str, list[str]] = defaultdict(list)
    relationship_ownership_incomplete = False
    for baseline_name, baseline in historical_baselines.items():
        relationship_ownership_incomplete = relationship_ownership_incomplete or any(
            is_unresolved(ref) for ref in getattr(baseline, "relationship_refs", ())
        )
        issues.extend(identifier_issues(baseline_name, baseline, is_unresolved))
        issues.extend(
            actor_issues(
                baseline_name,
                baseline,
                entities=entities,
                agents=agents,
                accounts=accounts,
                nodes=nodes,
                is_unresolved=is_unresolved,
            )
        )
        issues.extend(
            object_issues(
                baseline_name,
                baseline,
                content=content,
                nodes=nodes,
                deployment_cells=deployment_cells,
                is_unresolved=is_unresolved,
            )
        )
        baseline_relationship_issues, owned_relationships = relationship_issues(
            baseline_name,
            baseline,
            relationships=relationships,
            is_unresolved=is_unresolved,
        )
        issues.extend(baseline_relationship_issues)
        for relationship_name in owned_relationships:
            relationship_ownership[relationship_name].append(baseline_name)
        event_issues, _predecessors, _causes = event_reference_issues(
            baseline_name,
            baseline,
            relationships=relationships,
            is_unresolved=is_unresolved,
        )
        issues.extend(event_issues)
        issues.extend(
            event_lifecycle_issues(
                baseline_name,
                baseline,
                relationships=relationships,
                owned_relationships=owned_relationships,
                is_unresolved=is_unresolved,
            )
        )
        tenancy_issues, tenancy = baseline_tenancy_issues(
            baseline_name,
            baseline,
            deployment_tenants=deployment_tenants,
            deployment_cells=deployment_cells,
            relationships=relationships,
            is_unresolved=is_unresolved,
        )
        issues.extend(tenancy_issues)
        issues.extend(
            materialization_issues(
                baseline_name,
                baseline,
                nodes=nodes,
                deployment_tenants=deployment_tenants,
                deployment_cells=deployment_cells,
                relationships=relationships,
                tenancy=tenancy,
                is_unresolved=is_unresolved,
            )
        )
        issues.extend(
            readback_issues(
                baseline_name,
                baseline,
                propositions=propositions,
                assertions=assertions,
                observation_boundaries=observation_boundaries,
                is_unresolved=is_unresolved,
            )
        )
    issues.extend(
        global_historical_relationship_issues(
            relationships,
            relationship_ownership,
            is_unresolved,
            ownership_incomplete=relationship_ownership_incomplete,
        )
    )
    return tuple(issues)


__all__ = [
    "HistoricalStateIssue",
    "analyze_historical_state",
    "historical_object_ref",
]
