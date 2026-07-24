"""Native materialization checks for authored historical state."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from ..relationships import RelationshipType
from ._domain_topology_types import resolve_section_ref
from ._historical_state_types import (
    INTERFACE_OBJECT_KIND,
    HistoricalStateIssue,
    enum_value,
    has_cycle,
    issue,
    resolve_local_ref,
    service_owner,
)


@dataclass(frozen=True)
class MaterializationContext:
    baseline_name: str
    baseline: object
    nodes: Mapping[str, object]
    deployment_tenants: Mapping[str, object]
    deployment_cells: Mapping[str, object]
    relationships: Mapping[str, object]
    is_unresolved: Callable[[object], bool]

    @property
    def objects(self) -> Mapping[str, object]:
        return getattr(self.baseline, "objects", {})

    @property
    def bindings(self) -> Mapping[str, object]:
        return getattr(self.baseline, "materialization_bindings", {})

    @property
    def readbacks(self) -> Mapping[str, object]:
        return getattr(self.baseline, "readback_requirements", {})


@dataclass
class _MaterializationState:
    object_bindings: defaultdict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    dependency_graph: dict[str, set[str]] = field(default_factory=dict)
    object_binding_authority_incomplete: bool = False


def _tenancy_is_unresolved(
    value: object,
    is_unresolved: Callable[[object], bool],
) -> bool:
    return any(
        is_unresolved(getattr(value, field_name, ""))
        for field_name in (
            "deployment_tenant_ref",
            "deployment_cell_ref",
        )
    )


def _binding_target_issues(
    context: MaterializationContext,
    binding_id: str,
    binding: object,
) -> list[HistoricalStateIssue]:
    target_ref = getattr(binding, "target_service_ref", "")
    target_resolves = context.is_unresolved(target_ref) or service_owner(target_ref, context.nodes) is not None
    if target_resolves:
        return []
    return [
        issue(
            "historical-state.materialization.target-unbound",
            f"Historical baseline '{context.baseline_name}' materialization binding '{binding_id}' target "
            "must resolve to a named VM service",
        )
    ]


def _binding_reset_target_issues(
    context: MaterializationContext,
    binding_id: str,
    binding: object,
) -> list[HistoricalStateIssue]:
    reset_ref = getattr(binding, "reset_owner_relationship_ref", "")
    if context.is_unresolved(reset_ref):
        return []
    reset_name = resolve_section_ref(reset_ref, "relationships", context.relationships)
    if reset_name is None:
        return [
            issue(
                "historical-state.materialization.reset-owner-unbound",
                f"Historical baseline '{context.baseline_name}' materialization binding '{binding_id}' "
                "reset-owner relationship does not resolve",
            )
        ]
    relationship = context.relationships[reset_name]
    detail = getattr(relationship, "shared_service", None)
    target_ref = getattr(binding, "target_service_ref", "")
    tenant_ref = getattr(binding, "deployment_tenant_ref", "")
    source_ref = getattr(relationship, "source", "")
    reset_target = getattr(relationship, "target", "")
    relationship_type = getattr(relationship, "type", "")
    reset_owner = getattr(detail, "reset_generation_owner", "") if detail is not None else ""
    tenant_name = resolve_section_ref(tenant_ref, "deployment_tenants", context.deployment_tenants)
    source_name = resolve_section_ref(source_ref, "deployment_tenants", context.deployment_tenants)
    ownership_values = (tenant_ref, source_ref, reset_target, relationship_type, reset_owner, target_ref)
    mismatch = (
        enum_value(relationship_type) != RelationshipType.USES_SHARED_SERVICE.value
        or detail is None
        or source_name != tenant_name
        or enum_value(reset_owner) == "none"
        or reset_target != target_ref
    )
    if not any(context.is_unresolved(value) for value in ownership_values) and mismatch:
        return [
            issue(
                "historical-state.materialization.reset-owner-mismatch",
                f"Historical baseline '{context.baseline_name}' materialization binding '{binding_id}' "
                "reset-owner relationship must bind its tenant to its exact target service",
            )
        ]
    return []


def _binding_tenancy_issues(
    context: MaterializationContext,
    binding_id: str,
    binding: object,
    tenancy: tuple[str | None, str | None, str | None],
) -> list[HistoricalStateIssue]:
    binding_tenancy = (
        resolve_section_ref(
            getattr(binding, "deployment_tenant_ref", ""),
            "deployment_tenants",
            context.deployment_tenants,
        ),
        resolve_section_ref(
            getattr(binding, "deployment_cell_ref", ""),
            "deployment_cells",
            context.deployment_cells,
        ),
    )
    if (
        not _tenancy_is_unresolved(context.baseline, context.is_unresolved)
        and not _tenancy_is_unresolved(binding, context.is_unresolved)
        and all(value is not None for value in tenancy[:2])
        and binding_tenancy != tenancy[:2]
    ):
        return [
            issue(
                "historical-state.materialization.ownership-mismatch",
                f"Historical baseline '{context.baseline_name}' materialization binding '{binding_id}' tenant, "
                "and cell must agree with the baseline",
            )
        ]
    return []


def _binding_ownership_issues(
    context: MaterializationContext,
    binding_id: str,
    binding: object,
    tenancy: tuple[str | None, str | None, str | None],
) -> list[HistoricalStateIssue]:
    return [
        *_binding_target_issues(context, binding_id, binding),
        *_binding_tenancy_issues(context, binding_id, binding, tenancy),
        *_binding_reset_target_issues(context, binding_id, binding),
    ]


def _binding_object_issues(
    context: MaterializationContext,
    state: _MaterializationState,
    binding_id: str,
    binding: object,
) -> tuple[list[HistoricalStateIssue], bool]:
    issues: list[HistoricalStateIssue] = []
    interface_value = getattr(binding, "interface_profile", "")
    expected_kind = INTERFACE_OBJECT_KIND.get(enum_value(interface_value))
    binding_object_refs = getattr(binding, "object_refs", ())
    binding_objects_unresolved = any(context.is_unresolved(ref) for ref in binding_object_refs)
    state.object_binding_authority_incomplete = state.object_binding_authority_incomplete or binding_objects_unresolved
    for object_ref in binding_object_refs:
        if context.is_unresolved(object_ref):
            continue
        object_id = resolve_local_ref(
            object_ref,
            baseline_name=context.baseline_name,
            collection_name="objects",
            declarations=context.objects,
        )
        if object_id is None:
            issues.append(
                issue(
                    "historical-state.materialization.object-unbound",
                    f"Historical baseline '{context.baseline_name}' materialization binding '{binding_id}' "
                    "object_ref does not resolve",
                )
            )
            continue
        state.object_bindings[object_id].append(binding_id)
        object_kind = enum_value(getattr(context.objects[object_id], "kind", ""))
        if not context.is_unresolved(interface_value) and object_kind != expected_kind:
            issues.append(
                issue(
                    "historical-state.materialization.interface-mismatch",
                    f"Historical baseline '{context.baseline_name}' materialization binding '{binding_id}' "
                    f"interface does not support object '{object_id}' kind",
                )
            )
    return issues, binding_objects_unresolved


def _binding_dependency_issues(
    context: MaterializationContext,
    state: _MaterializationState,
    binding_id: str,
    binding: object,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for dependency_ref in getattr(binding, "ordering_dependencies", ()):
        if context.is_unresolved(dependency_ref):
            continue
        dependency_id = resolve_local_ref(
            dependency_ref,
            baseline_name=context.baseline_name,
            collection_name="materialization_bindings",
            declarations=context.bindings,
        )
        if dependency_id is None:
            issues.append(
                issue(
                    "historical-state.materialization.dependency-unbound",
                    f"Historical baseline '{context.baseline_name}' materialization binding '{binding_id}' "
                    "ordering dependency does not resolve",
                )
            )
        else:
            state.dependency_graph[binding_id].add(dependency_id)
    return issues


def _binding_readback_object(
    context: MaterializationContext,
    binding_id: str,
    readback_ref: object,
) -> tuple[list[HistoricalStateIssue], str | None, bool]:
    readback_id = resolve_local_ref(
        readback_ref,
        baseline_name=context.baseline_name,
        collection_name="readback_requirements",
        declarations=context.readbacks,
    )
    if readback_id is None:
        return (
            [
                issue(
                    "historical-state.materialization.readback-unbound",
                    f"Historical baseline '{context.baseline_name}' materialization binding '{binding_id}' "
                    "readback requirement does not resolve",
                )
            ],
            None,
            False,
        )
    readback_object_ref = getattr(context.readbacks[readback_id], "object_ref", "")
    if context.is_unresolved(readback_object_ref):
        return [], None, True
    return (
        [],
        resolve_local_ref(
            readback_object_ref,
            baseline_name=context.baseline_name,
            collection_name="objects",
            declarations=context.objects,
        ),
        False,
    )


def _resolved_binding_object_ids(
    context: MaterializationContext,
    binding: object,
) -> set[str]:
    return {
        object_id
        for ref in getattr(binding, "object_refs", ())
        if (
            object_id := resolve_local_ref(
                ref,
                baseline_name=context.baseline_name,
                collection_name="objects",
                declarations=context.objects,
            )
        )
        is not None
    }


def _binding_readback_issues(
    context: MaterializationContext,
    binding_id: str,
    binding: object,
    binding_objects_unresolved: bool,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    bound_readback_objects: set[str] = set()
    binding_readback_refs = getattr(binding, "readback_requirement_refs", ())
    readback_coverage_incomplete = any(context.is_unresolved(ref) for ref in binding_readback_refs)
    for readback_ref in binding_readback_refs:
        if context.is_unresolved(readback_ref):
            continue
        readback_issues, readback_object, object_ref_unresolved = _binding_readback_object(
            context,
            binding_id,
            readback_ref,
        )
        issues.extend(readback_issues)
        readback_coverage_incomplete = readback_coverage_incomplete or object_ref_unresolved
        if readback_object is not None:
            bound_readback_objects.add(readback_object)
    bound_object_ids = _resolved_binding_object_ids(context, binding)
    if (
        not binding_objects_unresolved
        and not readback_coverage_incomplete
        and not bound_object_ids.issubset(bound_readback_objects)
    ):
        issues.append(
            issue(
                "historical-state.materialization.readback-coverage",
                f"Historical baseline '{context.baseline_name}' materialization binding '{binding_id}' requires "
                "participant readback for every bound object",
            )
        )
    return issues


def _materialization_summary_issues(
    context: MaterializationContext,
    state: _MaterializationState,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    if has_cycle(state.dependency_graph):
        issues.append(
            issue(
                "historical-state.materialization.dependency-cycle",
                f"Historical baseline '{context.baseline_name}' materialization dependency graph contains a cycle",
            )
        )
    if not state.object_binding_authority_incomplete:
        for object_id in context.objects:
            if len(state.object_bindings.get(object_id, [])) != 1:
                issues.append(
                    issue(
                        "historical-state.materialization.object-authority",
                        f"Historical baseline '{context.baseline_name}' object '{object_id}' must have exactly one "
                        "materialization binding",
                    )
                )
    return issues


def materialization_issues(
    context: MaterializationContext,
    tenancy: tuple[str | None, str | None, str | None],
) -> list[HistoricalStateIssue]:
    state = _MaterializationState(
        dependency_graph={binding_id: set() for binding_id in context.bindings},
    )
    issues: list[HistoricalStateIssue] = []
    for binding_id, binding in context.bindings.items():
        issues.extend(_binding_ownership_issues(context, binding_id, binding, tenancy))
        object_issues, binding_objects_unresolved = _binding_object_issues(context, state, binding_id, binding)
        issues.extend(object_issues)
        issues.extend(_binding_dependency_issues(context, state, binding_id, binding))
        issues.extend(
            _binding_readback_issues(
                context,
                binding_id,
                binding,
                binding_objects_unresolved,
            )
        )
    issues.extend(_materialization_summary_issues(context, state))
    return issues
