"""Object and relationship state-machine checks for authored historical state."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from ..historical_state import HistoricalEventOperation
from ._domain_topology_types import resolve_section_ref
from ._historical_state_types import (
    HistoricalStateIssue,
    enum_value,
    historical_object_ref,
    issue,
    resolve_local_ref,
)


@dataclass(frozen=True)
class _LifecycleContext:
    baseline_name: str
    objects: Mapping[str, object]
    events: Mapping[str, object]
    actors: Mapping[str, object]
    relationships: Mapping[str, object]
    owned_relationships: set[str]
    is_unresolved: Callable[[object], bool]


@dataclass
class _LifecycleState:
    create_counts: Counter[str] = field(default_factory=Counter)
    alive: set[str] = field(default_factory=set)
    linked: set[str] = field(default_factory=set)
    object_state_uncertain: bool = False
    relationship_state_uncertain: bool = False


@dataclass(frozen=True)
class _LifecycleEvent:
    event_id: str
    operation: str
    object_ids: tuple[str, ...]
    objects_unresolved: bool
    relationships_unresolved: bool


def _resolved_event_actor(context: _LifecycleContext, event: object) -> str | None:
    return resolve_local_ref(
        getattr(event, "actor_ref", ""),
        baseline_name=context.baseline_name,
        collection_name="actors",
        declarations=context.actors,
    )


def _resolved_event_objects(context: _LifecycleContext, event: object) -> tuple[str, ...]:
    return tuple(
        resolved
        for ref in getattr(event, "object_refs", ())
        if (
            resolved := resolve_local_ref(
                ref,
                baseline_name=context.baseline_name,
                collection_name="objects",
                declarations=context.objects,
            )
        )
        is not None
    )


def _writer_conflict_issues(
    context: _LifecycleContext,
    lifecycle_event: _LifecycleEvent,
    actor_id: str | None,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for object_id in lifecycle_event.object_ids:
        writer_id = resolve_local_ref(
            getattr(context.objects[object_id], "writer_actor_ref", ""),
            baseline_name=context.baseline_name,
            collection_name="actors",
            declarations=context.actors,
        )
        if actor_id is not None and writer_id is not None and actor_id != writer_id:
            issues.append(
                issue(
                    "historical-state.object.writer-conflict",
                    f"Historical baseline '{context.baseline_name}' event '{lifecycle_event.event_id}' conflicts "
                    f"with object '{object_id}' single writer",
                )
            )
    return issues


def _create_object_issues(
    context: _LifecycleContext,
    state: _LifecycleState,
    lifecycle_event: _LifecycleEvent,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for object_id in lifecycle_event.object_ids:
        state.create_counts[object_id] += 1
        if object_id in state.alive:
            issues.append(
                issue(
                    "historical-state.object.duplicate-create",
                    f"Historical baseline '{context.baseline_name}' object '{object_id}' is created more than once",
                )
            )
        state.alive.add(object_id)
    return issues


def _use_object_issues(
    context: _LifecycleContext,
    state: _LifecycleState,
    lifecycle_event: _LifecycleEvent,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for object_id in lifecycle_event.object_ids:
        if object_id not in state.alive:
            issues.append(
                issue(
                    "historical-state.object.use-before-create",
                    f"Historical baseline '{context.baseline_name}' event '{lifecycle_event.event_id}' uses object "
                    f"'{object_id}' before creation or after deletion",
                )
            )
    if lifecycle_event.operation == HistoricalEventOperation.DELETE.value:
        state.alive.difference_update(lifecycle_event.object_ids)
    return issues


def _restore_object_issues(
    context: _LifecycleContext,
    state: _LifecycleState,
    lifecycle_event: _LifecycleEvent,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for object_id in lifecycle_event.object_ids:
        if object_id in state.alive or state.create_counts[object_id] == 0:
            issues.append(
                issue(
                    "historical-state.object.invalid-restore",
                    f"Historical baseline '{context.baseline_name}' event '{lifecycle_event.event_id}' restores "
                    f"object '{object_id}' without a prior deletion",
                )
            )
        state.alive.add(object_id)
    return issues


def _object_lifecycle_issues(
    context: _LifecycleContext,
    state: _LifecycleState,
    lifecycle_event: _LifecycleEvent,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    if not state.object_state_uncertain and not lifecycle_event.objects_unresolved:
        if lifecycle_event.operation == HistoricalEventOperation.CREATE.value:
            issues = _create_object_issues(context, state, lifecycle_event)
        elif lifecycle_event.operation in {
            HistoricalEventOperation.UPDATE.value,
            HistoricalEventOperation.DELETE.value,
            HistoricalEventOperation.LINK.value,
            HistoricalEventOperation.UNLINK.value,
        }:
            issues = _use_object_issues(context, state, lifecycle_event)
        elif lifecycle_event.operation == HistoricalEventOperation.RESTORE.value:
            issues = _restore_object_issues(context, state, lifecycle_event)
    return issues


def _relationship_object_ids(
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


def _relationship_event_issues(
    context: _LifecycleContext,
    state: _LifecycleState,
    lifecycle_event: _LifecycleEvent,
    relationship_name: str,
    relationship: object,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    endpoints_unresolved = any(
        context.is_unresolved(getattr(relationship, field_name, "")) for field_name in ("source", "target")
    )
    endpoint_ids = _relationship_object_ids(
        context.baseline_name,
        relationship,
        context.objects,
    )
    if (
        not lifecycle_event.objects_unresolved
        and not endpoints_unresolved
        and set(lifecycle_event.object_ids) != endpoint_ids
    ):
        issues.append(
            issue(
                "historical-state.relationship.event-endpoints",
                f"Historical baseline '{context.baseline_name}' event '{lifecycle_event.event_id}' object_refs "
                f"must match relationship '{relationship_name}' endpoints",
            )
        )
    if state.relationship_state_uncertain or lifecycle_event.relationships_unresolved:
        return issues
    if lifecycle_event.operation == HistoricalEventOperation.LINK.value:
        if relationship_name in state.linked:
            issues.append(
                issue(
                    "historical-state.relationship.duplicate-link",
                    f"Historical relationship '{relationship_name}' is linked more than once",
                )
            )
        state.linked.add(relationship_name)
    elif relationship_name not in state.linked:
        issues.append(
            issue(
                "historical-state.relationship.unlink-before-link",
                f"Historical relationship '{relationship_name}' is unlinked before linkage",
            )
        )
    else:
        state.linked.remove(relationship_name)
    return issues


def _relationship_lifecycle_issues(
    context: _LifecycleContext,
    state: _LifecycleState,
    lifecycle_event: _LifecycleEvent,
    event: object,
) -> list[HistoricalStateIssue]:
    if lifecycle_event.operation not in {
        HistoricalEventOperation.LINK.value,
        HistoricalEventOperation.UNLINK.value,
    }:
        return []
    issues: list[HistoricalStateIssue] = []
    for relationship_ref in getattr(event, "relationship_refs", ()):
        if context.is_unresolved(relationship_ref):
            continue
        relationship_name = resolve_section_ref(relationship_ref, "relationships", context.relationships)
        if relationship_name is None or relationship_name not in context.owned_relationships:
            continue
        issues.extend(
            _relationship_event_issues(
                context,
                state,
                lifecycle_event,
                relationship_name,
                context.relationships[relationship_name],
            )
        )
    state.relationship_state_uncertain = state.relationship_state_uncertain or lifecycle_event.relationships_unresolved
    return issues


def _create_count_issues(
    context: _LifecycleContext,
    state: _LifecycleState,
) -> list[HistoricalStateIssue]:
    if state.object_state_uncertain:
        return []
    return [
        issue(
            "historical-state.object.create-count",
            f"Historical baseline '{context.baseline_name}' object '{object_id}' must have exactly one create event",
        )
        for object_id in context.objects
        if state.create_counts[object_id] != 1
    ]


def _link_count_issues(
    context: _LifecycleContext,
    state: _LifecycleState,
) -> list[HistoricalStateIssue]:
    if state.relationship_state_uncertain:
        return []
    issues: list[HistoricalStateIssue] = []
    for relationship_name in context.owned_relationships:
        link_count = sum(
            1
            for event in context.events.values()
            if enum_value(getattr(event, "operation", "")) == HistoricalEventOperation.LINK.value
            and resolve_section_ref(relationship_name, "relationships", context.relationships)
            in {
                resolve_section_ref(ref, "relationships", context.relationships)
                for ref in getattr(event, "relationship_refs", ())
                if not context.is_unresolved(ref)
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
    context = _LifecycleContext(
        baseline_name=baseline_name,
        objects=objects,
        events=events,
        actors=actors,
        relationships=relationships,
        owned_relationships=owned_relationships,
        is_unresolved=is_unresolved,
    )
    state = _LifecycleState(
        relationship_state_uncertain=any(is_unresolved(ref) for ref in getattr(baseline, "relationship_refs", ()))
    )
    for event_id, event in sorted(events.items(), key=lambda item: (getattr(item[1], "order", -1), item[0])):
        operation = enum_value(getattr(event, "operation", ""))
        event_object_refs = getattr(event, "object_refs", ())
        lifecycle_event = _LifecycleEvent(
            event_id=event_id,
            operation=operation,
            object_ids=_resolved_event_objects(context, event),
            objects_unresolved=any(is_unresolved(ref) for ref in event_object_refs),
            relationships_unresolved=any(is_unresolved(ref) for ref in getattr(event, "relationship_refs", ())),
        )
        issues.extend(_writer_conflict_issues(context, lifecycle_event, _resolved_event_actor(context, event)))
        issues.extend(_object_lifecycle_issues(context, state, lifecycle_event))
        issues.extend(_relationship_lifecycle_issues(context, state, lifecycle_event, event))
        state.object_state_uncertain = state.object_state_uncertain or lifecycle_event.objects_unresolved
    issues.extend(_create_count_issues(context, state))
    issues.extend(_link_count_issues(context, state))
    return issues
