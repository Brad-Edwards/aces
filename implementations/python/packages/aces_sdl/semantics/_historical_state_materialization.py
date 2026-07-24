"""Tenancy, materialization, and readback checks for historical state."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping

from ..propositions import AssertionRole, PropositionBasis
from ..relationships import RelationshipType
from ._domain_topology_types import resolve_section_ref
from ._historical_state_types import (
    INTERFACE_OBJECT_KIND,
    HistoricalStateIssue,
    enum_value,
    has_cycle,
    historical_object_ref,
    issue,
    resolve_local_ref,
    service_owner,
)


def baseline_tenancy_issues(
    baseline_name: str,
    baseline: object,
    *,
    deployment_tenants: Mapping[str, object],
    deployment_cells: Mapping[str, object],
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[list[HistoricalStateIssue], tuple[str | None, str | None, str | None]]:
    issues: list[HistoricalStateIssue] = []
    tenant_ref = getattr(baseline, "deployment_tenant_ref", "")
    cell_ref = getattr(baseline, "deployment_cell_ref", "")
    reset_ref = getattr(baseline, "reset_owner_relationship_ref", "")
    tenant_name = (
        None if is_unresolved(tenant_ref) else resolve_section_ref(tenant_ref, "deployment_tenants", deployment_tenants)
    )
    cell_name = None if is_unresolved(cell_ref) else resolve_section_ref(cell_ref, "deployment_cells", deployment_cells)
    reset_name = None if is_unresolved(reset_ref) else resolve_section_ref(reset_ref, "relationships", relationships)
    if tenant_name is None and not is_unresolved(tenant_ref):
        issues.append(
            issue(
                "historical-state.tenant.unbound",
                f"Historical baseline '{baseline_name}' deployment_tenant_ref does not resolve",
            )
        )
    if cell_name is None and not is_unresolved(cell_ref):
        issues.append(
            issue(
                "historical-state.cell.unbound",
                f"Historical baseline '{baseline_name}' deployment_cell_ref does not resolve",
            )
        )
    if tenant_name is not None and cell_name is not None:
        cell_tenant_ref = getattr(deployment_cells[cell_name], "tenant_ref", "")
        cell_tenant_name = (
            None
            if is_unresolved(cell_tenant_ref)
            else resolve_section_ref(cell_tenant_ref, "deployment_tenants", deployment_tenants)
        )
        if not is_unresolved(cell_tenant_ref) and cell_tenant_name != tenant_name:
            issues.append(
                issue(
                    "historical-state.cell.tenant-mismatch",
                    f"Historical baseline '{baseline_name}' deployment cell and tenant must agree",
                )
            )
    if reset_name is None and not is_unresolved(reset_ref):
        issues.append(
            issue(
                "historical-state.reset.unbound",
                f"Historical baseline '{baseline_name}' reset_owner_relationship_ref does not resolve",
            )
        )
    elif reset_name is not None:
        relationship = relationships[reset_name]
        detail = getattr(relationship, "shared_service", None)
        relationship_type = getattr(relationship, "type", "")
        source_ref = getattr(relationship, "source", "")
        reset_owner = getattr(detail, "reset_generation_owner", "") if detail is not None else ""
        source_name = resolve_section_ref(
            source_ref,
            "deployment_tenants",
            deployment_tenants,
        )
        if not any(is_unresolved(value) for value in (tenant_ref, relationship_type, source_ref, reset_owner)) and (
            enum_value(relationship_type) != RelationshipType.USES_SHARED_SERVICE.value
            or detail is None
            or source_name != tenant_name
            or enum_value(reset_owner) == "none"
        ):
            issues.append(
                issue(
                    "historical-state.reset.owner-mismatch",
                    f"Historical baseline '{baseline_name}' reset owner must be an agreeing ADR-087 "
                    "shared-service binding",
                )
            )
    return issues, (tenant_name, cell_name, reset_name)


def materialization_issues(
    baseline_name: str,
    baseline: object,
    *,
    nodes: Mapping[str, object],
    deployment_tenants: Mapping[str, object],
    deployment_cells: Mapping[str, object],
    relationships: Mapping[str, object],
    tenancy: tuple[str | None, str | None, str | None],
    is_unresolved: Callable[[object], bool],
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    objects = getattr(baseline, "objects", {})
    bindings = getattr(baseline, "materialization_bindings", {})
    readbacks = getattr(baseline, "readback_requirements", {})
    tenant_name, cell_name, reset_name = tenancy
    object_bindings: defaultdict[str, list[str]] = defaultdict(list)
    object_binding_authority_incomplete = False
    dependency_graph: dict[str, set[str]] = {binding_id: set() for binding_id in bindings}
    baseline_ownership_unresolved = any(
        is_unresolved(getattr(baseline, field_name, ""))
        for field_name in (
            "deployment_tenant_ref",
            "deployment_cell_ref",
            "reset_owner_relationship_ref",
        )
    )
    for binding_id, binding in bindings.items():
        target_ref = getattr(binding, "target_service_ref", "")
        target_resolves = is_unresolved(target_ref) or service_owner(target_ref, nodes) is not None
        if not target_resolves:
            issues.append(
                issue(
                    "historical-state.materialization.target-unbound",
                    f"Historical baseline '{baseline_name}' materialization binding '{binding_id}' target "
                    "must resolve to a named VM service",
                )
            )
        binding_tenant = resolve_section_ref(
            getattr(binding, "deployment_tenant_ref", ""),
            "deployment_tenants",
            deployment_tenants,
        )
        binding_cell = resolve_section_ref(
            getattr(binding, "deployment_cell_ref", ""),
            "deployment_cells",
            deployment_cells,
        )
        binding_reset = resolve_section_ref(
            getattr(binding, "reset_owner_relationship_ref", ""),
            "relationships",
            relationships,
        )
        binding_ownership_unresolved = any(
            is_unresolved(getattr(binding, field_name, ""))
            for field_name in (
                "deployment_tenant_ref",
                "deployment_cell_ref",
                "reset_owner_relationship_ref",
            )
        )
        if (
            not baseline_ownership_unresolved
            and not binding_ownership_unresolved
            and all(value is not None for value in tenancy)
            and (binding_tenant, binding_cell, binding_reset) != tenancy
        ):
            issues.append(
                issue(
                    "historical-state.materialization.ownership-mismatch",
                    f"Historical baseline '{baseline_name}' materialization binding '{binding_id}' tenant, "
                    "cell, and reset owner must agree with the baseline",
                )
            )
        if reset_name is not None and target_resolves and not is_unresolved(target_ref):
            reset_target = getattr(relationships[reset_name], "target", "")
            if not is_unresolved(reset_target) and reset_target != target_ref:
                issues.append(
                    issue(
                        "historical-state.materialization.reset-target-mismatch",
                        f"Historical baseline '{baseline_name}' materialization binding '{binding_id}' target "
                        "must agree with its reset-owner relationship",
                    )
                )
        interface = enum_value(getattr(binding, "interface_profile", ""))
        expected_kind = INTERFACE_OBJECT_KIND.get(interface)
        binding_object_refs = getattr(binding, "object_refs", ())
        binding_objects_unresolved = any(is_unresolved(object_ref) for object_ref in binding_object_refs)
        object_binding_authority_incomplete = object_binding_authority_incomplete or binding_objects_unresolved
        for object_ref in binding_object_refs:
            if is_unresolved(object_ref):
                continue
            object_id = resolve_local_ref(
                object_ref,
                baseline_name=baseline_name,
                collection_name="objects",
                declarations=objects,
            )
            if object_id is None:
                issues.append(
                    issue(
                        "historical-state.materialization.object-unbound",
                        f"Historical baseline '{baseline_name}' materialization binding '{binding_id}' "
                        "object_ref does not resolve",
                    )
                )
                continue
            object_bindings[object_id].append(binding_id)
            object_kind = enum_value(getattr(objects[object_id], "kind", ""))
            if not is_unresolved(getattr(binding, "interface_profile", "")) and object_kind != expected_kind:
                issues.append(
                    issue(
                        "historical-state.materialization.interface-mismatch",
                        f"Historical baseline '{baseline_name}' materialization binding '{binding_id}' interface "
                        f"does not support object '{object_id}' kind",
                    )
                )
        for dependency_ref in getattr(binding, "ordering_dependencies", ()):
            if is_unresolved(dependency_ref):
                continue
            dependency_id = resolve_local_ref(
                dependency_ref,
                baseline_name=baseline_name,
                collection_name="materialization_bindings",
                declarations=bindings,
            )
            if dependency_id is None:
                issues.append(
                    issue(
                        "historical-state.materialization.dependency-unbound",
                        f"Historical baseline '{baseline_name}' materialization binding '{binding_id}' "
                        "ordering dependency does not resolve",
                    )
                )
            else:
                dependency_graph[binding_id].add(dependency_id)
        bound_readback_objects: set[str] = set()
        binding_readback_refs = getattr(binding, "readback_requirement_refs", ())
        readback_coverage_incomplete = any(is_unresolved(readback_ref) for readback_ref in binding_readback_refs)
        for readback_ref in binding_readback_refs:
            if is_unresolved(readback_ref):
                continue
            readback_id = resolve_local_ref(
                readback_ref,
                baseline_name=baseline_name,
                collection_name="readback_requirements",
                declarations=readbacks,
            )
            if readback_id is None:
                issues.append(
                    issue(
                        "historical-state.materialization.readback-unbound",
                        f"Historical baseline '{baseline_name}' materialization binding '{binding_id}' "
                        "readback requirement does not resolve",
                    )
                )
                continue
            readback_object_ref = getattr(readbacks[readback_id], "object_ref", "")
            if is_unresolved(readback_object_ref):
                readback_coverage_incomplete = True
                continue
            readback_object = resolve_local_ref(
                readback_object_ref,
                baseline_name=baseline_name,
                collection_name="objects",
                declarations=objects,
            )
            if readback_object is not None:
                bound_readback_objects.add(readback_object)
        bound_object_ids = {
            object_id
            for ref in binding_object_refs
            if (
                object_id := resolve_local_ref(
                    ref,
                    baseline_name=baseline_name,
                    collection_name="objects",
                    declarations=objects,
                )
            )
            is not None
        }
        if (
            not binding_objects_unresolved
            and not readback_coverage_incomplete
            and not bound_object_ids.issubset(bound_readback_objects)
        ):
            issues.append(
                issue(
                    "historical-state.materialization.readback-coverage",
                    f"Historical baseline '{baseline_name}' materialization binding '{binding_id}' requires "
                    "participant readback for every bound object",
                )
            )
    if has_cycle(dependency_graph):
        issues.append(
            issue(
                "historical-state.materialization.dependency-cycle",
                f"Historical baseline '{baseline_name}' materialization dependency graph contains a cycle",
            )
        )
    if not object_binding_authority_incomplete:
        for object_id in objects:
            owners = object_bindings.get(object_id, [])
            if len(owners) != 1:
                issues.append(
                    issue(
                        "historical-state.materialization.object-authority",
                        f"Historical baseline '{baseline_name}' object '{object_id}' must have exactly one "
                        "materialization binding",
                    )
                )
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
    objects = getattr(baseline, "objects", {})
    for readback_id, readback in getattr(baseline, "readback_requirements", {}).items():
        object_id = resolve_local_ref(
            getattr(readback, "object_ref", ""),
            baseline_name=baseline_name,
            collection_name="objects",
            declarations=objects,
        )
        if object_id is None and not is_unresolved(getattr(readback, "object_ref", "")):
            issues.append(
                issue(
                    "historical-state.readback.object-unbound",
                    f"Historical baseline '{baseline_name}' readback '{readback_id}' object_ref does not resolve",
                )
            )
        boundary_ref = getattr(readback, "observation_boundary_ref", "")
        boundary_name = (
            None
            if is_unresolved(boundary_ref)
            else resolve_section_ref(
                boundary_ref,
                "observation_boundaries",
                observation_boundaries,
            )
        )
        if not is_unresolved(boundary_ref) and boundary_name is None:
            issues.append(
                issue(
                    "historical-state.readback.boundary-unbound",
                    f"Historical baseline '{baseline_name}' readback '{readback_id}' observation boundary "
                    "does not resolve",
                )
            )
        expected_subject = historical_object_ref(baseline_name, object_id) if object_id is not None else None
        if boundary_name is not None and expected_subject is not None:
            observable_refs = getattr(
                observation_boundaries[boundary_name],
                "observable_refs",
                (),
            )
            if not any(is_unresolved(ref) for ref in observable_refs) and expected_subject not in observable_refs:
                issues.append(
                    issue(
                        "historical-state.readback.boundary-visibility",
                        f"Historical baseline '{baseline_name}' readback '{readback_id}' object must be "
                        "participant-visible through its observation boundary",
                    )
                )
        for assertion_ref in getattr(readback, "assertion_refs", ()):
            if is_unresolved(assertion_ref):
                continue
            assertion_name = resolve_section_ref(assertion_ref, "assertions", assertions)
            if assertion_name is None:
                issues.append(
                    issue(
                        "historical-state.readback.assertion-unbound",
                        f"Historical baseline '{baseline_name}' readback '{readback_id}' assertion_ref "
                        "does not resolve",
                    )
                )
                continue
            assertion = assertions[assertion_name]
            proposition_ref = getattr(assertion, "proposition", "")
            if is_unresolved(proposition_ref) or expected_subject is None:
                continue
            proposition_name = resolve_section_ref(
                proposition_ref,
                "propositions",
                propositions,
            )
            proposition = propositions.get(proposition_name) if proposition_name is not None else None
            role = enum_value(getattr(assertion, "role", ""))
            proposition_basis = getattr(proposition, "basis", "") if proposition is not None else ""
            proposition_subjects = getattr(proposition, "subjects", ()) if proposition is not None else ()
            if any(is_unresolved(value) for value in (proposition_basis, role, *proposition_subjects)):
                continue
            if (
                proposition is None
                or enum_value(proposition_basis) != PropositionBasis.OBSERVED_STATE.value
                or expected_subject not in set(proposition_subjects)
                or role not in {AssertionRole.INVARIANT.value, AssertionRole.POSTCONDITION.value}
            ):
                issues.append(
                    issue(
                        "historical-state.readback.assertion-mismatch",
                        f"Historical baseline '{baseline_name}' readback '{readback_id}' assertion must be an "
                        "observed-state invariant or postcondition over its exact semantic object",
                    )
                )
    return issues
