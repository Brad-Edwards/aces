"""Pure deployment-cell, carrier-placement, and shared-service analysis."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ..deployment_tenancy import (
    EndpointPersona,
    StateOwner,
    TenantIsolationMode,
    WorkloadAuthenticationMode,
)
from ..nodes import NodeType
from ..relationships import RelationshipType
from ._domain_topology_types import resolve_section_ref


@dataclass(frozen=True)
class DeploymentTenancyIssue:
    code: str
    message: str


def _issue(code: str, message: str) -> DeploymentTenancyIssue:
    return DeploymentTenancyIssue(code=code, message=message)


def _enum_value(value: object) -> str:
    return getattr(value, "value", str(value))


def _service_owner(service_ref: object, nodes: Mapping[str, object]) -> str | None:
    if not isinstance(service_ref, str):
        return None
    for node_name, node in nodes.items():
        for service in getattr(node, "services", ()):
            name = getattr(service, "name", "")
            if name and service_ref == f"nodes.{node_name}.services.{name}":
                return node_name
    return None


@dataclass
class _CellIndex:
    node_cell: dict[str, str]
    cell_tenant: dict[str, str]
    tenant_nodes: defaultdict[str, set[str]]
    issues: list[DeploymentTenancyIssue]


def _build_cell_index(
    deployment_tenants: Mapping[str, object],
    deployment_cells: Mapping[str, object],
    nodes: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> _CellIndex:
    index = _CellIndex({}, {}, defaultdict(set), [])
    for cell_name, cell in deployment_cells.items():
        tenant_ref = getattr(cell, "tenant_ref", "")
        tenant_name = None
        if not is_unresolved(tenant_ref):
            tenant_name = resolve_section_ref(tenant_ref, "deployment_tenants", deployment_tenants)
            if tenant_name is None:
                index.issues.append(
                    _issue(
                        "deployment-tenancy.cell.tenant-unbound",
                        f"Deployment cell '{cell_name}' tenant_ref '{tenant_ref}' does not resolve "
                        "to a deployment tenant",
                    )
                )
            else:
                index.cell_tenant[cell_name] = tenant_name
        for node_ref in getattr(cell, "node_refs", ()):
            if is_unresolved(node_ref):
                continue
            node_name = resolve_section_ref(node_ref, "nodes", nodes)
            if node_name is None:
                index.issues.append(
                    _issue(
                        "deployment-tenancy.cell.node-unbound",
                        f"Deployment cell '{cell_name}' node_ref '{node_ref}' does not resolve to a node",
                    )
                )
                continue
            previous = index.node_cell.get(node_name)
            if previous is not None and previous != cell_name:
                index.issues.append(
                    _issue(
                        "deployment-tenancy.cell.node-multiple",
                        f"Node '{node_name}' belongs to multiple deployment cells: {previous}, {cell_name}",
                    )
                )
            else:
                index.node_cell[node_name] = cell_name
                if tenant_name is not None:
                    index.tenant_nodes[tenant_name].add(node_name)
    if deployment_cells:
        for node_name, node in nodes.items():
            if getattr(node, "type", None) == NodeType.VM and node_name not in index.node_cell:
                index.issues.append(
                    _issue(
                        "deployment-tenancy.cell.node-missing",
                        f"VM node '{node_name}' must belong to exactly one deployment cell",
                    )
                )
    return index


_DETAIL_FIELDS = {
    RelationshipType.PLACED_ON_CARRIER.value: "carrier_placement",
    RelationshipType.USES_SHARED_SERVICE.value: "shared_service",
}


def _relationship_detail_issues(
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[DeploymentTenancyIssue]:
    issues: list[DeploymentTenancyIssue] = []
    detail_fields = tuple(_DETAIL_FIELDS.values())
    for name, relationship in relationships.items():
        type_value = getattr(relationship, "type", "")
        if is_unresolved(type_value):
            continue
        type_name = _enum_value(type_value)
        expected = _DETAIL_FIELDS.get(type_name)
        populated = [field_name for field_name in detail_fields if getattr(relationship, field_name, None) is not None]
        if expected is not None and expected not in populated:
            issues.append(
                _issue(
                    "deployment-tenancy.relationship.detail-required",
                    f"Relationship '{name}' type '{type_name}' requires {expected} detail",
                )
            )
        for field_name in populated:
            if field_name != expected:
                issues.append(
                    _issue(
                        "deployment-tenancy.relationship.detail-mismatch",
                        f"Relationship '{name}' carries {field_name} detail with type '{type_name}'",
                    )
                )
    return issues


def _placement_issues(
    nodes: Mapping[str, object],
    relationships: Mapping[str, object],
    cell_index: _CellIndex,
    is_unresolved: Callable[[object], bool],
) -> list[DeploymentTenancyIssue]:
    issues: list[DeploymentTenancyIssue] = []
    carrier_by_source: dict[str, str] = {}
    edge_name_by_source: dict[str, str] = {}
    for name, relationship in relationships.items():
        if _enum_value(getattr(relationship, "type", "")) != RelationshipType.PLACED_ON_CARRIER.value:
            continue
        if getattr(relationship, "carrier_placement", None) is None:
            continue
        source_ref = getattr(relationship, "source", "")
        target_ref = getattr(relationship, "target", "")
        if any(is_unresolved(value) for value in (source_ref, target_ref)):
            continue
        source = resolve_section_ref(source_ref, "nodes", nodes)
        target = resolve_section_ref(target_ref, "nodes", nodes)
        if (
            source is None
            or target is None
            or getattr(nodes.get(source), "type", None) != NodeType.VM
            or getattr(nodes.get(target), "type", None) != NodeType.VM
        ):
            issues.append(
                _issue(
                    "deployment-tenancy.placement.endpoint-invalid",
                    f"Relationship '{name}' carrier placement endpoints must resolve to VM nodes",
                )
            )
            continue
        if source == target:
            issues.append(
                _issue(
                    "deployment-tenancy.placement.self",
                    f"Relationship '{name}' cannot place a node on itself",
                )
            )
        previous = carrier_by_source.get(source)
        if previous is not None and previous != target:
            issues.append(
                _issue(
                    "deployment-tenancy.placement.multiple-carriers",
                    f"Node '{source}' has multiple carrier placements",
                )
            )
        carrier_by_source[source] = target
        edge_name_by_source[source] = name
        persona = _enum_value(getattr(nodes[target], "endpoint_persona", ""))
        if persona != EndpointPersona.CARRIER.value:
            issues.append(
                _issue(
                    "deployment-tenancy.placement.target-not-carrier",
                    f"Relationship '{name}' target '{target}' must have endpoint persona 'carrier'",
                )
            )
        source_cell = cell_index.node_cell.get(source)
        target_cell = cell_index.node_cell.get(target)
        if source_cell is not None and target_cell is not None and source_cell != target_cell:
            issues.append(
                _issue(
                    "deployment-tenancy.placement.cross-cell",
                    f"Relationship '{name}' carrier placement crosses different deployment cells",
                )
            )

    for start in carrier_by_source:
        seen: set[str] = set()
        current = start
        while current in carrier_by_source:
            if current in seen:
                issues.append(
                    _issue(
                        "deployment-tenancy.placement.cycle",
                        f"Relationship '{edge_name_by_source[start]}' participates in a carrier placement cycle",
                    )
                )
                break
            seen.add(current)
            current = carrier_by_source[current]
    for source, target in carrier_by_source.items():
        if target in carrier_by_source:
            issues.append(
                _issue(
                    "deployment-tenancy.placement.nested",
                    f"Relationship '{edge_name_by_source[source]}' cannot place a node on another placed node",
                )
            )
    return issues


def _state_consumer_nodes(volume: object) -> set[str]:
    return {getattr(consumer, "node", "") for consumer in getattr(volume, "consumers", ())}


def _shared_service_issues(
    deployment_tenants: Mapping[str, object],
    nodes: Mapping[str, object],
    persistent_volumes: Mapping[str, object],
    relationships: Mapping[str, object],
    cell_index: _CellIndex,
    is_unresolved: Callable[[object], bool],
) -> list[DeploymentTenancyIssue]:
    issues: list[DeploymentTenancyIssue] = []
    state_owners: dict[str, tuple[str, str]] = {}
    for name, relationship in relationships.items():
        if _enum_value(getattr(relationship, "type", "")) != RelationshipType.USES_SHARED_SERVICE.value:
            continue
        detail = getattr(relationship, "shared_service", None)
        if detail is None:
            continue
        source_ref = getattr(relationship, "source", "")
        target_ref = getattr(relationship, "target", "")
        if any(is_unresolved(value) for value in (source_ref, target_ref)):
            continue
        tenant_name = resolve_section_ref(source_ref, "deployment_tenants", deployment_tenants)
        service_node = _service_owner(target_ref, nodes)
        if tenant_name is None or service_node is None:
            issues.append(
                _issue(
                    "deployment-tenancy.shared-service.endpoint-invalid",
                    f"Relationship '{name}' must connect a deployment tenant to a named VM service",
                )
            )
            continue
        service_cell = cell_index.node_cell.get(service_node)
        service_tenant = cell_index.cell_tenant.get(service_cell, "") if service_cell is not None else ""
        isolation = _enum_value(getattr(detail, "tenant_isolation", ""))
        authentication = _enum_value(getattr(detail, "workload_authentication", ""))
        state_owner = _enum_value(getattr(detail, "mutable_state_owner", ""))
        reset_owner = _enum_value(getattr(detail, "reset_generation_owner", ""))
        state_refs = tuple(getattr(detail, "mutable_state_refs", ()))

        if tenant_name != service_tenant and (
            isolation not in {TenantIsolationMode.STATELESS.value, TenantIsolationMode.TENANT_PARTITIONED.value}
            or authentication != WorkloadAuthenticationMode.TENANT_SCOPED_WORKLOAD_IDENTITY.value
        ):
            issues.append(
                _issue(
                    "deployment-tenancy.shared-service.cross-tenant-unsafe",
                    f"Relationship '{name}' {isolation or 'cross-tenant'} isolation requires "
                    "tenant-scoped workload authentication",
                )
            )
        if isolation == TenantIsolationMode.STATELESS.value and state_owner == StateOwner.SHARED_SERVICE.value:
            issues.append(
                _issue(
                    "deployment-tenancy.shared-service.stateless-service-state",
                    f"Relationship '{name}' stateless isolation forbids shared-service-owned mutable state",
                )
            )
        if isolation == TenantIsolationMode.TENANT_PARTITIONED.value and (
            not state_refs
            or state_owner != StateOwner.SHARED_SERVICE.value
            or reset_owner != StateOwner.SHARED_SERVICE.value
        ):
            issues.append(
                _issue(
                    "deployment-tenancy.shared-service.partitioned-state-required",
                    f"Relationship '{name}' tenant_partitioned isolation requires shared-service-owned "
                    "state and reset generation",
                )
            )
        if state_refs and state_owner == StateOwner.NONE.value:
            issues.append(
                _issue(
                    "deployment-tenancy.shared-service.state-owner-missing",
                    f"Relationship '{name}' mutable_state_refs require a non-none owner",
                )
            )
        if not state_refs and state_owner != StateOwner.NONE.value:
            issues.append(
                _issue(
                    "deployment-tenancy.shared-service.state-refs-missing",
                    f"Relationship '{name}' mutable state owner requires mutable_state_refs",
                )
            )
        if state_owner != StateOwner.NONE.value and reset_owner != state_owner:
            issues.append(
                _issue(
                    "deployment-tenancy.shared-service.reset-owner-mismatch",
                    f"Relationship '{name}' reset_generation_owner must equal mutable state owner",
                )
            )
        if state_owner == StateOwner.NONE.value and reset_owner != StateOwner.NONE.value:
            issues.append(
                _issue(
                    "deployment-tenancy.shared-service.reset-owner-without-state",
                    f"Relationship '{name}' reset_generation_owner must be none without mutable state",
                )
            )
        for state_ref in state_refs:
            if is_unresolved(state_ref):
                continue
            state_name = resolve_section_ref(state_ref, "persistent_volumes", persistent_volumes)
            if state_name is None:
                issues.append(
                    _issue(
                        "deployment-tenancy.shared-service.state-unbound",
                        f"Relationship '{name}' mutable_state_ref '{state_ref}' does not resolve "
                        "to a persistent volume",
                    )
                )
                continue
            owner_key = (tenant_name, state_owner)
            previous = state_owners.setdefault(state_name, owner_key)
            if previous != owner_key:
                issues.append(
                    _issue(
                        "deployment-tenancy.shared-service.state-owner-conflict",
                        f"Persistent volume '{state_name}' has conflicting shared-service owners",
                    )
                )
            consumers = _state_consumer_nodes(persistent_volumes[state_name])
            if state_owner == StateOwner.CONSUMER_TENANT.value:
                allowed = cell_index.tenant_nodes.get(tenant_name, set())
                if not consumers or not consumers.issubset(allowed):
                    issues.append(
                        _issue(
                            "deployment-tenancy.shared-service.consumer-state-mismatch",
                            f"Relationship '{name}' consumer-owned state must be consumed only by its tenant",
                        )
                    )
            elif state_owner == StateOwner.SHARED_SERVICE.value and service_node not in consumers:
                issues.append(
                    _issue(
                        "deployment-tenancy.shared-service.service-state-mismatch",
                        f"Relationship '{name}' shared-service-owned state must be consumed by the service node",
                    )
                )
    return issues


def _cross_cell_service_consumption_issues(
    deployment_tenants: Mapping[str, object],
    nodes: Mapping[str, object],
    relationships: Mapping[str, object],
    cell_index: _CellIndex,
    is_unresolved: Callable[[object], bool],
) -> list[DeploymentTenancyIssue]:
    if not cell_index.node_cell:
        return []

    permitted: set[tuple[str, str]] = set()
    for relationship in relationships.values():
        if _enum_value(getattr(relationship, "type", "")) != RelationshipType.USES_SHARED_SERVICE.value:
            continue
        source_ref = getattr(relationship, "source", "")
        target_ref = getattr(relationship, "target", "")
        if any(is_unresolved(value) for value in (source_ref, target_ref)):
            continue
        tenant_name = resolve_section_ref(source_ref, "deployment_tenants", deployment_tenants)
        if tenant_name is not None and _service_owner(target_ref, nodes) is not None:
            permitted.add((tenant_name, target_ref))

    issues: list[DeploymentTenancyIssue] = []
    for name, relationship in relationships.items():
        if _enum_value(getattr(relationship, "type", "")) == RelationshipType.USES_SHARED_SERVICE.value:
            continue
        source_ref = getattr(relationship, "source", "")
        target_ref = getattr(relationship, "target", "")
        if any(is_unresolved(value) for value in (source_ref, target_ref)):
            continue

        source_node = resolve_section_ref(source_ref, "nodes", nodes) or _service_owner(source_ref, nodes)
        target_node = _service_owner(target_ref, nodes)
        if source_node is None or target_node is None:
            continue
        source_cell = cell_index.node_cell.get(source_node)
        target_cell = cell_index.node_cell.get(target_node)
        if source_cell is None or target_cell is None or source_cell == target_cell:
            continue
        source_tenant = cell_index.cell_tenant.get(source_cell)
        if source_tenant is None or (source_tenant, target_ref) in permitted:
            continue
        issues.append(
            _issue(
                "deployment-tenancy.shared-service.binding-required",
                f"Relationship '{name}' cross-cell service consumption requires an explicit "
                "shared-service binding for the consumer tenant and target service",
            )
        )
    return issues


def analyze_deployment_tenancy(
    *,
    deployment_tenants: Mapping[str, object],
    deployment_cells: Mapping[str, object],
    nodes: Mapping[str, object],
    persistent_volumes: Mapping[str, object],
    relationships: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[DeploymentTenancyIssue, ...]:
    """Validate portable tenancy and placement intent."""

    cell_index = _build_cell_index(deployment_tenants, deployment_cells, nodes, is_unresolved)
    issues = list(cell_index.issues)
    issues.extend(_relationship_detail_issues(relationships, is_unresolved))
    issues.extend(_placement_issues(nodes, relationships, cell_index, is_unresolved))
    issues.extend(
        _shared_service_issues(
            deployment_tenants,
            nodes,
            persistent_volumes,
            relationships,
            cell_index,
            is_unresolved,
        )
    )
    issues.extend(
        _cross_cell_service_consumption_issues(
            deployment_tenants,
            nodes,
            relationships,
            cell_index,
            is_unresolved,
        )
    )
    return tuple(issues)


__all__ = ["DeploymentTenancyIssue", "analyze_deployment_tenancy"]
