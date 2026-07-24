"""Relationship and lifecycle checks for authored historical state."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ..relationships import RelationshipType
from ._domain_topology_types import resolve_section_ref
from ._historical_state_types import (
    HistoricalStateIssue,
    enum_value,
    has_cycle,
    historical_object_ref,
    issue,
    resolve_local_ref,
)


def _resolved_owned_relationships(
    baseline: object,
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[set[str], bool]:
    relationship_refs = getattr(baseline, "relationship_refs", ())
    owned: set[str] = set()
    for relationship_ref in relationship_refs:
        if is_unresolved(relationship_ref):
            continue
        resolved = resolve_section_ref(relationship_ref, "relationships", relationships)
        if resolved is not None:
            owned.add(resolved)
    return owned, any(is_unresolved(ref) for ref in relationship_refs)


@dataclass(frozen=True)
class _EventReferenceContext:
    baseline_name: str
    actors: Mapping[str, object]
    objects: Mapping[str, object]
    events: Mapping[str, object]
    relationships: Mapping[str, object]
    owned_relationships: set[str]
    ownership_incomplete: bool
    orders: Mapping[str, int]
    is_unresolved: Callable[[object], bool]


def _event_actor_issues(
    context: _EventReferenceContext,
    event_id: str,
    event: object,
) -> list[HistoricalStateIssue]:
    actor_ref = getattr(event, "actor_ref", "")
    if context.is_unresolved(actor_ref) or (
        resolve_local_ref(
            actor_ref,
            baseline_name=context.baseline_name,
            collection_name="actors",
            declarations=context.actors,
        )
        is not None
    ):
        return []
    return [
        issue(
            "historical-state.event.actor-unbound",
            f"Historical baseline '{context.baseline_name}' event '{event_id}' actor_ref does not resolve",
        )
    ]


def _event_object_reference_issues(
    context: _EventReferenceContext,
    event_id: str,
    event: object,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for object_ref in getattr(event, "object_refs", ()):
        if (
            not context.is_unresolved(object_ref)
            and resolve_local_ref(
                object_ref,
                baseline_name=context.baseline_name,
                collection_name="objects",
                declarations=context.objects,
            )
            is None
        ):
            issues.append(
                issue(
                    "historical-state.event.object-unbound",
                    f"Historical baseline '{context.baseline_name}' event '{event_id}' object_ref does not resolve",
                )
            )
    return issues


def _event_graph_reference_issues(
    context: _EventReferenceContext,
    event_id: str,
    event: object,
    *,
    field_name: str,
    graph: dict[str, set[str]],
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for event_ref in getattr(event, field_name, ()):
        if context.is_unresolved(event_ref):
            continue
        resolved = resolve_local_ref(
            event_ref,
            baseline_name=context.baseline_name,
            collection_name="events",
            declarations=context.events,
        )
        if resolved is None:
            issues.append(
                issue(
                    "historical-state.event.reference-unbound",
                    f"Historical baseline '{context.baseline_name}' event '{event_id}' {field_name} does not resolve",
                )
            )
            continue
        graph[event_id].add(resolved)
        if context.orders.get(resolved, -1) >= context.orders[event_id]:
            issues.append(
                issue(
                    "historical-state.event.order-conflict",
                    f"Historical baseline '{context.baseline_name}' event '{event_id}' {field_name} must precede it",
                )
            )
    return issues


def _event_relationship_reference_issues(
    context: _EventReferenceContext,
    event_id: str,
    event: object,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for relationship_ref in getattr(event, "relationship_refs", ()):
        if context.is_unresolved(relationship_ref):
            continue
        resolved = resolve_section_ref(relationship_ref, "relationships", context.relationships)
        if resolved is None or (resolved not in context.owned_relationships and not context.ownership_incomplete):
            issues.append(
                issue(
                    "historical-state.event.relationship-unbound",
                    f"Historical baseline '{context.baseline_name}' event '{event_id}' relationship_ref is not "
                    "owned by the baseline",
                )
            )
    return issues


def _event_cycle_issues(
    baseline_name: str,
    predecessor_graph: Mapping[str, set[str]],
    cause_graph: Mapping[str, set[str]],
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    if has_cycle(predecessor_graph):
        issues.append(
            issue(
                "historical-state.event.predecessor-cycle",
                f"Historical baseline '{baseline_name}' predecessor graph contains a cycle",
            )
        )
    if has_cycle(cause_graph):
        issues.append(
            issue(
                "historical-state.event.causal-cycle",
                f"Historical baseline '{baseline_name}' causal graph contains a cycle",
            )
        )
    return issues


def event_reference_issues(
    baseline_name: str,
    baseline: object,
    *,
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[list[HistoricalStateIssue], dict[str, set[str]], dict[str, set[str]]]:
    issues: list[HistoricalStateIssue] = []
    events = getattr(baseline, "events", {})
    objects = getattr(baseline, "objects", {})
    actors = getattr(baseline, "actors", {})
    owned_relationships, ownership_incomplete = _resolved_owned_relationships(
        baseline,
        relationships,
        is_unresolved,
    )
    predecessor_graph: dict[str, set[str]] = {event_id: set() for event_id in events}
    cause_graph: dict[str, set[str]] = {event_id: set() for event_id in events}
    orders = {event_id: getattr(event, "order", -1) for event_id, event in events.items()}
    context = _EventReferenceContext(
        baseline_name=baseline_name,
        actors=actors,
        objects=objects,
        events=events,
        relationships=relationships,
        owned_relationships=owned_relationships,
        ownership_incomplete=ownership_incomplete,
        orders=orders,
        is_unresolved=is_unresolved,
    )
    duplicate_orders = sorted(order for order, count in Counter(orders.values()).items() if count > 1)
    if duplicate_orders:
        issues.append(
            issue(
                "historical-state.event.order-duplicate",
                f"Historical baseline '{baseline_name}' event order coordinates must be unique",
            )
        )
    for event_id, event in events.items():
        issues.extend(_event_actor_issues(context, event_id, event))
        issues.extend(_event_object_reference_issues(context, event_id, event))
        for field_name, graph in (("predecessor_refs", predecessor_graph), ("cause_refs", cause_graph)):
            issues.extend(
                _event_graph_reference_issues(
                    context,
                    event_id,
                    event,
                    field_name=field_name,
                    graph=graph,
                )
            )
        issues.extend(_event_relationship_reference_issues(context, event_id, event))
    issues.extend(_event_cycle_issues(baseline_name, predecessor_graph, cause_graph))
    return issues, predecessor_graph, cause_graph


def relationship_object_ids(
    baseline_name: str,
    relationship: object,
    objects: Mapping[str, object],
) -> set[str]:
    resolved: set[str] = set()
    for endpoint in (getattr(relationship, "source", ""), getattr(relationship, "target", "")):
        for object_id in objects:
            if endpoint == historical_object_ref(baseline_name, object_id):
                resolved.add(object_id)
                break
    return resolved


def relationship_issues(
    baseline_name: str,
    baseline: object,
    *,
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[list[HistoricalStateIssue], set[str]]:
    issues: list[HistoricalStateIssue] = []
    objects = getattr(baseline, "objects", {})
    owned: set[str] = set()
    for relationship_ref in getattr(baseline, "relationship_refs", ()):
        if is_unresolved(relationship_ref):
            continue
        relationship_name = resolve_section_ref(relationship_ref, "relationships", relationships)
        if relationship_name is None:
            issues.append(
                issue(
                    "historical-state.relationship.unbound",
                    f"Historical baseline '{baseline_name}' relationship_ref '{relationship_ref}' does not resolve",
                )
            )
            continue
        owned.add(relationship_name)
        relationship = relationships[relationship_name]
        type_name = enum_value(getattr(relationship, "type", ""))
        detail = getattr(relationship, "historical_object_link", None)
        if type_name != RelationshipType.HISTORICAL_OBJECT_LINK.value or detail is None:
            issues.append(
                issue(
                    "historical-state.relationship.type",
                    f"Historical baseline '{baseline_name}' relationship '{relationship_name}' must use "
                    "historical_object_link typed detail",
                )
            )
            continue
        if getattr(relationship, "properties", {}):
            issues.append(
                issue(
                    "historical-state.relationship.properties",
                    f"Historical relationship '{relationship_name}' must not carry free-form properties",
                )
            )
        endpoints = (
            getattr(relationship, "source", ""),
            getattr(relationship, "target", ""),
        )
        object_ids = relationship_object_ids(baseline_name, relationship, objects)
        if not any(is_unresolved(endpoint) for endpoint in endpoints) and len(object_ids) != 2:
            issues.append(
                issue(
                    "historical-state.relationship.endpoint",
                    f"Historical relationship '{relationship_name}' endpoints must be distinct objects in "
                    f"baseline '{baseline_name}'",
                )
            )
    return issues, owned


def global_historical_relationship_issues(
    relationships: Mapping[str, object],
    ownership: Mapping[str, list[str]],
    is_unresolved: Callable[[object], bool],
    *,
    ownership_incomplete: bool = False,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for relationship_name, relationship in relationships.items():
        type_value = getattr(relationship, "type", "")
        if is_unresolved(type_value):
            continue
        is_historical = enum_value(type_value) == RelationshipType.HISTORICAL_OBJECT_LINK.value
        detail = getattr(relationship, "historical_object_link", None)
        if is_historical and detail is None:
            issues.append(
                issue(
                    "historical-state.relationship.detail-required",
                    f"Relationship '{relationship_name}' type 'historical_object_link' requires typed detail",
                )
            )
        if not is_historical and detail is not None:
            issues.append(
                issue(
                    "historical-state.relationship.detail-mismatch",
                    f"Relationship '{relationship_name}' carries historical_object_link detail with "
                    f"type '{enum_value(type_value)}'",
                )
            )
        if is_historical and not ownership_incomplete and len(ownership.get(relationship_name, ())) != 1:
            issues.append(
                issue(
                    "historical-state.relationship.owner-count",
                    f"Historical relationship '{relationship_name}' must be owned by exactly one baseline",
                )
            )
    return issues
