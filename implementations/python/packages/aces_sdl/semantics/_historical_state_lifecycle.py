"""Relationship and lifecycle checks for authored historical state."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping

from ..historical_state import HistoricalEventOperation
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
    owned_relationships: set[str] = set()
    ownership_incomplete = any(
        is_unresolved(relationship_ref) for relationship_ref in getattr(baseline, "relationship_refs", ())
    )
    for relationship_ref in getattr(baseline, "relationship_refs", ()):
        if is_unresolved(relationship_ref):
            continue
        resolved = resolve_section_ref(relationship_ref, "relationships", relationships)
        if resolved is not None:
            owned_relationships.add(resolved)
    predecessor_graph: dict[str, set[str]] = {event_id: set() for event_id in events}
    cause_graph: dict[str, set[str]] = {event_id: set() for event_id in events}
    orders = {event_id: getattr(event, "order", -1) for event_id, event in events.items()}
    duplicate_orders = sorted(order for order, count in Counter(orders.values()).items() if count > 1)
    if duplicate_orders:
        issues.append(
            issue(
                "historical-state.event.order-duplicate",
                f"Historical baseline '{baseline_name}' event order coordinates must be unique",
            )
        )
    for event_id, event in events.items():
        actor_ref = getattr(event, "actor_ref", "")
        if (
            not is_unresolved(actor_ref)
            and resolve_local_ref(
                actor_ref,
                baseline_name=baseline_name,
                collection_name="actors",
                declarations=actors,
            )
            is None
        ):
            issues.append(
                issue(
                    "historical-state.event.actor-unbound",
                    f"Historical baseline '{baseline_name}' event '{event_id}' actor_ref does not resolve",
                )
            )
        for object_ref in getattr(event, "object_refs", ()):
            if (
                not is_unresolved(object_ref)
                and resolve_local_ref(
                    object_ref,
                    baseline_name=baseline_name,
                    collection_name="objects",
                    declarations=objects,
                )
                is None
            ):
                issues.append(
                    issue(
                        "historical-state.event.object-unbound",
                        f"Historical baseline '{baseline_name}' event '{event_id}' object_ref does not resolve",
                    )
                )
        for field_name, graph in (("predecessor_refs", predecessor_graph), ("cause_refs", cause_graph)):
            for event_ref in getattr(event, field_name, ()):
                if is_unresolved(event_ref):
                    continue
                resolved = resolve_local_ref(
                    event_ref,
                    baseline_name=baseline_name,
                    collection_name="events",
                    declarations=events,
                )
                if resolved is None:
                    issues.append(
                        issue(
                            "historical-state.event.reference-unbound",
                            f"Historical baseline '{baseline_name}' event '{event_id}' {field_name} does not resolve",
                        )
                    )
                    continue
                graph[event_id].add(resolved)
                if orders.get(resolved, -1) >= orders[event_id]:
                    issues.append(
                        issue(
                            "historical-state.event.order-conflict",
                            f"Historical baseline '{baseline_name}' event '{event_id}' {field_name} must precede it",
                        )
                    )
        for relationship_ref in getattr(event, "relationship_refs", ()):
            if is_unresolved(relationship_ref):
                continue
            resolved = resolve_section_ref(relationship_ref, "relationships", relationships)
            if resolved is None or (resolved not in owned_relationships and not ownership_incomplete):
                issues.append(
                    issue(
                        "historical-state.event.relationship-unbound",
                        f"Historical baseline '{baseline_name}' event '{event_id}' relationship_ref is not "
                        "owned by the baseline",
                    )
                )
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


def event_lifecycle_issues(
    baseline_name: str,
    baseline: object,
    *,
    relationships: Mapping[str, object],
    owned_relationships: set[str],
    is_unresolved: Callable[[object], bool],
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    objects = getattr(baseline, "objects", {})
    events = getattr(baseline, "events", {})
    actors = getattr(baseline, "actors", {})
    create_counts: Counter[str] = Counter()
    alive: set[str] = set()
    linked: set[str] = set()
    object_state_uncertain = False
    relationship_state_uncertain = any(is_unresolved(ref) for ref in getattr(baseline, "relationship_refs", ()))
    for event_id, event in sorted(events.items(), key=lambda item: (getattr(item[1], "order", -1), item[0])):
        operation = enum_value(getattr(event, "operation", ""))
        actor_id = resolve_local_ref(
            getattr(event, "actor_ref", ""),
            baseline_name=baseline_name,
            collection_name="actors",
            declarations=actors,
        )
        event_object_refs = getattr(event, "object_refs", ())
        event_objects_unresolved = any(is_unresolved(ref) for ref in event_object_refs)
        object_ids = [
            resolved
            for ref in event_object_refs
            if (
                resolved := resolve_local_ref(
                    ref,
                    baseline_name=baseline_name,
                    collection_name="objects",
                    declarations=objects,
                )
            )
            is not None
        ]
        for object_id in object_ids:
            writer_id = resolve_local_ref(
                getattr(objects[object_id], "writer_actor_ref", ""),
                baseline_name=baseline_name,
                collection_name="actors",
                declarations=actors,
            )
            if actor_id is not None and writer_id is not None and actor_id != writer_id:
                issues.append(
                    issue(
                        "historical-state.object.writer-conflict",
                        f"Historical baseline '{baseline_name}' event '{event_id}' conflicts with object "
                        f"'{object_id}' single writer",
                    )
                )
        if (
            not object_state_uncertain
            and not event_objects_unresolved
            and operation == HistoricalEventOperation.CREATE.value
        ):
            for object_id in object_ids:
                create_counts[object_id] += 1
                if object_id in alive:
                    issues.append(
                        issue(
                            "historical-state.object.duplicate-create",
                            f"Historical baseline '{baseline_name}' object '{object_id}' is created more than once",
                        )
                    )
                alive.add(object_id)
        elif (
            not object_state_uncertain
            and not event_objects_unresolved
            and operation
            in {
                HistoricalEventOperation.UPDATE.value,
                HistoricalEventOperation.DELETE.value,
                HistoricalEventOperation.LINK.value,
                HistoricalEventOperation.UNLINK.value,
            }
        ):
            for object_id in object_ids:
                if object_id not in alive:
                    issues.append(
                        issue(
                            "historical-state.object.use-before-create",
                            f"Historical baseline '{baseline_name}' event '{event_id}' uses object '{object_id}' "
                            "before creation or after deletion",
                        )
                    )
            if operation == HistoricalEventOperation.DELETE.value:
                alive.difference_update(object_ids)
        elif (
            not object_state_uncertain
            and not event_objects_unresolved
            and operation == HistoricalEventOperation.RESTORE.value
        ):
            for object_id in object_ids:
                if object_id in alive or create_counts[object_id] == 0:
                    issues.append(
                        issue(
                            "historical-state.object.invalid-restore",
                            f"Historical baseline '{baseline_name}' event '{event_id}' restores object "
                            f"'{object_id}' without a prior deletion",
                        )
                    )
                alive.add(object_id)
        if operation in {HistoricalEventOperation.LINK.value, HistoricalEventOperation.UNLINK.value}:
            event_relationship_refs = getattr(event, "relationship_refs", ())
            event_relationships_unresolved = any(is_unresolved(ref) for ref in event_relationship_refs)
            for relationship_ref in event_relationship_refs:
                if is_unresolved(relationship_ref):
                    continue
                relationship_name = resolve_section_ref(relationship_ref, "relationships", relationships)
                if relationship_name is None or relationship_name not in owned_relationships:
                    continue
                relationship = relationships[relationship_name]
                endpoints_unresolved = any(
                    is_unresolved(getattr(relationship, field_name, "")) for field_name in ("source", "target")
                )
                endpoint_ids = relationship_object_ids(
                    baseline_name,
                    relationship,
                    objects,
                )
                if not event_objects_unresolved and not endpoints_unresolved and set(object_ids) != endpoint_ids:
                    issues.append(
                        issue(
                            "historical-state.relationship.event-endpoints",
                            f"Historical baseline '{baseline_name}' event '{event_id}' object_refs must match "
                            f"relationship '{relationship_name}' endpoints",
                        )
                    )
                if relationship_state_uncertain or event_relationships_unresolved:
                    continue
                if operation == HistoricalEventOperation.LINK.value:
                    if relationship_name in linked:
                        issues.append(
                            issue(
                                "historical-state.relationship.duplicate-link",
                                f"Historical relationship '{relationship_name}' is linked more than once",
                            )
                        )
                    linked.add(relationship_name)
                elif relationship_name not in linked:
                    issues.append(
                        issue(
                            "historical-state.relationship.unlink-before-link",
                            f"Historical relationship '{relationship_name}' is unlinked before linkage",
                        )
                    )
                else:
                    linked.remove(relationship_name)
            relationship_state_uncertain = relationship_state_uncertain or event_relationships_unresolved
        object_state_uncertain = object_state_uncertain or event_objects_unresolved
    if not object_state_uncertain:
        for object_id in objects:
            if create_counts[object_id] != 1:
                issues.append(
                    issue(
                        "historical-state.object.create-count",
                        f"Historical baseline '{baseline_name}' object '{object_id}' must have exactly one create event",
                    )
                )
    if not relationship_state_uncertain:
        for relationship_name in owned_relationships:
            link_count = sum(
                1
                for event in events.values()
                if enum_value(getattr(event, "operation", "")) == HistoricalEventOperation.LINK.value
                and resolve_section_ref(relationship_name, "relationships", relationships)
                in {
                    resolve_section_ref(ref, "relationships", relationships)
                    for ref in getattr(event, "relationship_refs", ())
                    if not is_unresolved(ref)
                }
            )
            if link_count != 1:
                issues.append(
                    issue(
                        "historical-state.relationship.link-count",
                        f"Historical relationship '{relationship_name}' must have exactly one link event",
                    )
                )
    return issues


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
