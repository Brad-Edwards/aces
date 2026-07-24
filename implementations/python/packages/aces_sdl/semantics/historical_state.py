"""Pure finite-graph analysis for authored historical state."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from ..propositions import AssertionRole, PropositionBasis
from ._domain_topology_types import resolve_section_ref
from ._historical_state_identity import actor_issues, baseline_tenancy_issues, identifier_issues, object_issues
from ._historical_state_lifecycle import (
    event_reference_issues,
    global_historical_relationship_issues,
    relationship_issues,
)
from ._historical_state_lifecycle_state import event_lifecycle_issues
from ._historical_state_materialization import (
    MaterializationContext,
    materialization_issues,
)
from ._historical_state_types import HistoricalStateIssue, enum_value, issue, resolve_local_ref
from ._historical_state_types import historical_object_ref as _historical_object_ref

HistoricalStateIssue.__module__ = __name__


@dataclass(frozen=True)
class HistoricalStateAnalysisContext:
    """Declarations and variable-resolution policy used by historical-state analysis."""

    historical_baselines: Mapping[str, object]
    entities: Mapping[str, object]
    agents: Mapping[str, object]
    accounts: Mapping[str, object]
    nodes: Mapping[str, object]
    content: Mapping[str, object]
    propositions: Mapping[str, object]
    assertions: Mapping[str, object]
    observation_boundaries: Mapping[str, object]
    deployment_tenants: Mapping[str, object]
    deployment_cells: Mapping[str, object]
    relationships: Mapping[str, object]
    is_unresolved: Callable[[object], bool]


def historical_object_ref(baseline_name: str, object_id: str) -> str:
    """Return the canonical declaration address of a baseline-local object."""

    return _historical_object_ref(baseline_name, object_id)


@dataclass(frozen=True)
class _ReadbackContext:
    baseline_name: str
    baseline: object
    propositions: Mapping[str, object]
    assertions: Mapping[str, object]
    observation_boundaries: Mapping[str, object]
    is_unresolved: Callable[[object], bool]

    @property
    def objects(self) -> Mapping[str, object]:
        return getattr(self.baseline, "objects", {})


def _boundary_visibility_issues(
    context: _ReadbackContext,
    readback_id: str,
    boundary_name: str | None,
    expected_subject: str | None,
) -> list[HistoricalStateIssue]:
    if boundary_name is None or expected_subject is None:
        return []
    observable_refs = getattr(
        context.observation_boundaries[boundary_name],
        "observable_refs",
        (),
    )
    if any(context.is_unresolved(ref) for ref in observable_refs) or expected_subject in observable_refs:
        return []
    return [
        issue(
            "historical-state.readback.boundary-visibility",
            f"Historical baseline '{context.baseline_name}' readback '{readback_id}' object must be "
            "participant-visible through its observation boundary",
        )
    ]


def _readback_subject_issues(
    context: _ReadbackContext,
    readback_id: str,
    readback: object,
) -> tuple[list[HistoricalStateIssue], str | None]:
    issues: list[HistoricalStateIssue] = []
    object_ref = getattr(readback, "object_ref", "")
    object_id = resolve_local_ref(
        object_ref,
        baseline_name=context.baseline_name,
        collection_name="objects",
        declarations=context.objects,
    )
    if object_id is None and not context.is_unresolved(object_ref):
        issues.append(
            issue(
                "historical-state.readback.object-unbound",
                f"Historical baseline '{context.baseline_name}' readback '{readback_id}' object_ref does not resolve",
            )
        )
    boundary_ref = getattr(readback, "observation_boundary_ref", "")
    boundary_name = (
        None
        if context.is_unresolved(boundary_ref)
        else resolve_section_ref(
            boundary_ref,
            "observation_boundaries",
            context.observation_boundaries,
        )
    )
    if not context.is_unresolved(boundary_ref) and boundary_name is None:
        issues.append(
            issue(
                "historical-state.readback.boundary-unbound",
                f"Historical baseline '{context.baseline_name}' readback '{readback_id}' observation boundary "
                "does not resolve",
            )
        )
    expected_subject = historical_object_ref(context.baseline_name, object_id) if object_id is not None else None
    issues.extend(_boundary_visibility_issues(context, readback_id, boundary_name, expected_subject))
    return issues, expected_subject


def _resolve_readback_assertion(
    context: _ReadbackContext,
    readback_id: str,
    assertion_ref: object,
) -> tuple[HistoricalStateIssue | None, object | None]:
    if context.is_unresolved(assertion_ref):
        return None, None
    assertion_name = resolve_section_ref(assertion_ref, "assertions", context.assertions)
    if assertion_name is None:
        return (
            issue(
                "historical-state.readback.assertion-unbound",
                f"Historical baseline '{context.baseline_name}' readback '{readback_id}' assertion_ref "
                "does not resolve",
            ),
            None,
        )
    return None, context.assertions[assertion_name]


def _assertion_matches_readback(
    proposition: object | None,
    proposition_basis: object,
    proposition_subjects: Iterable[object],
    role: str,
    expected_subject: str,
) -> bool:
    return (
        proposition is not None
        and enum_value(proposition_basis) == PropositionBasis.OBSERVED_STATE.value
        and expected_subject in set(proposition_subjects)
        and role in {AssertionRole.INVARIANT.value, AssertionRole.POSTCONDITION.value}
    )


def _assertion_mismatch_issue(
    context: _ReadbackContext,
    readback_id: str,
    assertion: object,
    expected_subject: str | None,
) -> HistoricalStateIssue | None:
    mismatch = None
    proposition_ref = getattr(assertion, "proposition", "")
    if not context.is_unresolved(proposition_ref) and expected_subject is not None:
        proposition_name = resolve_section_ref(
            proposition_ref,
            "propositions",
            context.propositions,
        )
        proposition = context.propositions.get(proposition_name) if proposition_name is not None else None
        role = enum_value(getattr(assertion, "role", ""))
        proposition_basis = getattr(proposition, "basis", "") if proposition is not None else ""
        proposition_subjects = getattr(proposition, "subjects", ()) if proposition is not None else ()
        proposition_values = (proposition_basis, role, *proposition_subjects)
        if not any(context.is_unresolved(value) for value in proposition_values) and not _assertion_matches_readback(
            proposition,
            proposition_basis,
            proposition_subjects,
            role,
            expected_subject,
        ):
            mismatch = issue(
                "historical-state.readback.assertion-mismatch",
                f"Historical baseline '{context.baseline_name}' readback '{readback_id}' assertion must be an "
                "observed-state invariant or postcondition over its exact semantic object",
            )
    return mismatch


def _readback_assertion_issues(
    context: _ReadbackContext,
    readback_id: str,
    readback: object,
    expected_subject: str | None,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for assertion_ref in getattr(readback, "assertion_refs", ()):
        resolution_issue, assertion = _resolve_readback_assertion(context, readback_id, assertion_ref)
        if resolution_issue is not None:
            issues.append(resolution_issue)
        if assertion is not None:
            mismatch_issue = _assertion_mismatch_issue(context, readback_id, assertion, expected_subject)
            if mismatch_issue is not None:
                issues.append(mismatch_issue)
    return issues


def readback_issues(
    baseline_name: str,
    baseline: object,
    *,
    propositions: Mapping[str, object],
    assertions: Mapping[str, object],
    observation_boundaries: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    context = _ReadbackContext(
        baseline_name=baseline_name,
        baseline=baseline,
        propositions=propositions,
        assertions=assertions,
        observation_boundaries=observation_boundaries,
        is_unresolved=is_unresolved,
    )
    for readback_id, readback in getattr(baseline, "readback_requirements", {}).items():
        subject_issues, expected_subject = _readback_subject_issues(context, readback_id, readback)
        issues.extend(subject_issues)
        issues.extend(_readback_assertion_issues(context, readback_id, readback, expected_subject))
    return issues


def _baseline_issues(
    context: HistoricalStateAnalysisContext,
    baseline_name: str,
    baseline: object,
) -> tuple[list[HistoricalStateIssue], set[str]]:
    issues = identifier_issues(baseline_name, baseline, context.is_unresolved)
    issues.extend(
        actor_issues(
            baseline_name,
            baseline,
            entities=context.entities,
            agents=context.agents,
            accounts=context.accounts,
            nodes=context.nodes,
            is_unresolved=context.is_unresolved,
        )
    )
    issues.extend(
        object_issues(
            baseline_name,
            baseline,
            content=context.content,
            nodes=context.nodes,
            deployment_cells=context.deployment_cells,
            is_unresolved=context.is_unresolved,
        )
    )
    relationship_diagnostics, owned_relationships = relationship_issues(
        baseline_name,
        baseline,
        relationships=context.relationships,
        is_unresolved=context.is_unresolved,
    )
    issues.extend(relationship_diagnostics)
    event_issues, _predecessors, _causes = event_reference_issues(
        baseline_name,
        baseline,
        relationships=context.relationships,
        is_unresolved=context.is_unresolved,
    )
    issues.extend(event_issues)
    issues.extend(
        event_lifecycle_issues(
            baseline_name,
            baseline,
            relationships=context.relationships,
            owned_relationships=owned_relationships,
            is_unresolved=context.is_unresolved,
        )
    )
    tenancy_issues, tenancy = baseline_tenancy_issues(
        baseline_name,
        baseline,
        deployment_tenants=context.deployment_tenants,
        deployment_cells=context.deployment_cells,
        relationships=context.relationships,
        is_unresolved=context.is_unresolved,
    )
    issues.extend(tenancy_issues)
    issues.extend(
        materialization_issues(
            MaterializationContext(
                baseline_name=baseline_name,
                baseline=baseline,
                nodes=context.nodes,
                deployment_tenants=context.deployment_tenants,
                deployment_cells=context.deployment_cells,
                relationships=context.relationships,
                is_unresolved=context.is_unresolved,
            ),
            tenancy=tenancy,
        )
    )
    issues.extend(
        readback_issues(
            baseline_name,
            baseline,
            propositions=context.propositions,
            assertions=context.assertions,
            observation_boundaries=context.observation_boundaries,
            is_unresolved=context.is_unresolved,
        )
    )
    return issues, owned_relationships


def analyze_historical_state(
    context: HistoricalStateAnalysisContext | None = None,
    **declarations: object,
) -> tuple[HistoricalStateIssue, ...]:
    """Analyze all historical baselines and return deterministic collected issues."""

    if context is None:
        context = HistoricalStateAnalysisContext(**declarations)
    elif declarations:
        unexpected = next(iter(declarations))
        raise TypeError(f"analyze_historical_state() got an unexpected keyword argument '{unexpected}'")
    issues: list[HistoricalStateIssue] = []
    relationship_ownership: defaultdict[str, list[str]] = defaultdict(list)
    relationship_ownership_incomplete = False
    for baseline_name, baseline in context.historical_baselines.items():
        relationship_ownership_incomplete = relationship_ownership_incomplete or any(
            context.is_unresolved(ref) for ref in getattr(baseline, "relationship_refs", ())
        )
        baseline_issues, owned_relationships = _baseline_issues(context, baseline_name, baseline)
        issues.extend(baseline_issues)
        for relationship_name in owned_relationships:
            relationship_ownership[relationship_name].append(baseline_name)
    issues.extend(
        global_historical_relationship_issues(
            context.relationships,
            relationship_ownership,
            context.is_unresolved,
            ownership_incomplete=relationship_ownership_incomplete,
        )
    )
    return tuple(issues)


__all__ = [
    "HistoricalStateIssue",
    "HistoricalStateAnalysisContext",
    "analyze_historical_state",
    "historical_object_ref",
]
