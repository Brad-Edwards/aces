"""Dependency, budget, and evidence policy checks for live activity."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from fractions import Fraction

from aces_contracts.dependency_graph import dependency_cycles

from ..observability_plane_semantics import collect_scenario_native_observability_refs
from ._live_activity_types import LiveActivityIssue, activity_issue
from .domain_topology import resolve_section_ref


def dependency_issues(profile_name: str, profile: object) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    actions = getattr(profile, "actions", {})
    graph: dict[str, set[str]] = {name: set() for name in actions}
    seen: set[tuple[str, str, str]] = set()
    for dependency in getattr(profile, "dependencies", ()):
        source = dependency.action_ref
        target = dependency.depends_on_ref
        kind = dependency.kind.value
        key = (source, target, kind)
        if key in seen:
            issues.append(
                activity_issue(
                    "live-activity.dependency-duplicate",
                    f"Activity profile '{profile_name}' has a duplicate action dependency",
                )
            )
        seen.add(key)
        if source not in actions or target not in actions:
            issues.append(
                activity_issue(
                    "live-activity.dependency-unresolved",
                    f"Activity profile '{profile_name}' action dependency does not resolve",
                )
            )
            continue
        if source == target:
            issues.append(
                activity_issue(
                    "live-activity.dependency-self",
                    f"Activity action '{profile_name}.{source}' cannot depend on itself",
                )
            )
        graph[source].add(target)
    for cycle in dependency_cycles(graph):
        issues.append(
            activity_issue(
                "live-activity.dependency-cycle",
                f"Activity profile '{profile_name}' dependency cycle: {', '.join(cycle)}",
            )
        )
    return issues


def _rational(value: object) -> Fraction:
    return Fraction(value.numerator, value.denominator)  # type: ignore[attr-defined]


def budget_issues(profile_name: str, profile: object) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    actions = set(getattr(profile, "actions", {}))
    seen_dimensions: set[str] = set()
    expected_unit = {
        "operations": "operation",
        "bytes": "byte",
        "connections": "connection",
        "cpu_milliseconds": "cpu_millisecond",
    }
    for budget in getattr(profile, "budgets", ()):
        dimension = budget.dimension.value
        if dimension in seen_dimensions:
            issues.append(
                activity_issue(
                    "live-activity.budget-duplicate",
                    f"Activity profile '{profile_name}' repeats budget dimension '{dimension}'",
                )
            )
        seen_dimensions.add(dimension)
        if budget.unit.value != expected_unit[dimension]:
            issues.append(
                activity_issue(
                    "live-activity.budget-unit-mismatch",
                    f"Activity profile '{profile_name}' budget dimension and unit disagree",
                )
            )
        if set(budget.action_demands) != actions:
            issues.append(
                activity_issue(
                    "live-activity.budget-action-coverage",
                    f"Activity profile '{profile_name}' budget must cover every action exactly",
                )
            )
        reservation = _rational(budget.participant_reservation)
        range_capacity = _rational(budget.range_capacity)
        fleet_capacity = _rational(budget.fleet_capacity)
        if reservation > range_capacity:
            issues.append(
                activity_issue(
                    "live-activity.participant-reservation-exceeded",
                    f"Activity profile '{profile_name}' participant reservation exceeds range capacity",
                )
            )
        if range_capacity > fleet_capacity:
            issues.append(
                activity_issue(
                    "live-activity.range-capacity-exceeded",
                    f"Activity profile '{profile_name}' range capacity exceeds fleet capacity",
                )
            )
        available = range_capacity - reservation
        demands = [_rational(demand) for demand in budget.action_demands.values()]
        if any(demand <= 0 or demand > available for demand in demands):
            issues.append(
                activity_issue(
                    "live-activity.action-demand-exceeded",
                    f"Activity profile '{profile_name}' action demand exceeds participant-reserved range allowance",
                )
            )
        if sum(demands, start=Fraction()) > available:
            issues.append(
                activity_issue(
                    "live-activity.aggregate-demand-exceeded",
                    f"Activity profile '{profile_name}' aggregate action demand exceeds "
                    "participant-reserved range allowance",
                )
            )
    return issues


def evidence_issues(
    profile_name: str,
    profile: object,
    *,
    scenario: object,
    evidence_requirements: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[LiveActivityIssue]:
    issues: list[LiveActivityIssue] = []
    observability = collect_scenario_native_observability_refs(scenario)
    for policy_name in ("readback", "telemetry"):
        policy = getattr(profile, policy_name)
        for ref in getattr(policy, "observability_refs", ()):
            if not is_unresolved(ref) and ref not in observability:
                issues.append(
                    activity_issue(
                        f"live-activity.{policy_name}-observability-unresolved",
                        f"Activity profile '{profile_name}' {policy_name} reference is not scenario-native observability",
                    )
                )
        for ref in getattr(policy, "evidence_requirement_refs", ()):
            if (
                not is_unresolved(ref)
                and resolve_section_ref(ref, "evidence_requirements", evidence_requirements) is None
            ):
                issues.append(
                    activity_issue(
                        f"live-activity.{policy_name}-evidence-unresolved",
                        f"Activity profile '{profile_name}' {policy_name} evidence requirement does not resolve",
                    )
                )
    return issues


__all__ = ["budget_issues", "dependency_issues", "evidence_issues"]
