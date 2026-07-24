"""Identity and corpus checks for authored historical state."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ..entities import flatten_entities
from ..historical_state import (
    HISTORICAL_ADDRESS_PROFILE,
    HISTORICAL_TIME_PROFILE,
    HistoricalActorAuthority,
    HistoricalContentSensitivity,
)
from ..relationships import RelationshipType
from ._domain_topology_types import resolve_section_ref
from ._historical_state_types import (
    QUALIFIED_IDENTIFIER_RE,
    SEMANTIC_VERSION_RE,
    HistoricalStateIssue,
    enum_value,
    issue,
    resolve_local_ref,
    service_owner,
    unsafe_text_reason,
)


def identifier_issues(
    baseline_name: str,
    baseline: object,
    is_unresolved: Callable[[object], bool],
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    if getattr(baseline, "address_profile", "") != HISTORICAL_ADDRESS_PROFILE:
        issues.append(
            issue(
                "historical-state.address.profile",
                f"Historical baseline '{baseline_name}' must use address_profile '{HISTORICAL_ADDRESS_PROFILE}'",
            )
        )
    if getattr(baseline, "history_time_profile", "") != HISTORICAL_TIME_PROFILE:
        issues.append(
            issue(
                "historical-state.time.profile",
                f"Historical baseline '{baseline_name}' must use history_time_profile '{HISTORICAL_TIME_PROFILE}'",
            )
        )
    version = getattr(baseline, "version", "")
    if not is_unresolved(version) and SEMANTIC_VERSION_RE.fullmatch(str(version)) is None:
        issues.append(
            issue(
                "historical-state.baseline.version",
                f"Historical baseline '{baseline_name}' version must be an explicit semantic version",
            )
        )
    for field_name in ("range_instance_id", "reset_generation_id"):
        value = getattr(baseline, field_name, "")
        if not is_unresolved(value) and QUALIFIED_IDENTIFIER_RE.fullmatch(str(value)) is None:
            issues.append(
                issue(
                    "historical-state.address.coordinate",
                    f"Historical baseline '{baseline_name}' {field_name} must be a portable qualified identifier",
                )
            )
    return issues


def actor_issues(
    baseline_name: str,
    baseline: object,
    *,
    entities: Mapping[str, object],
    agents: Mapping[str, object],
    accounts: Mapping[str, object],
    nodes: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    actor_targets = {
        HistoricalActorAuthority.ENTITY.value: ("entity", flatten_entities(dict(entities))),
        HistoricalActorAuthority.AGENT.value: ("agent", agents),
        HistoricalActorAuthority.ACCOUNT.value: ("account", accounts),
    }
    for actor_id, actor in getattr(baseline, "actors", {}).items():
        authority = enum_value(getattr(actor, "authority", ""))
        authority_ref = getattr(actor, "authority_ref", "")
        if is_unresolved(authority_ref):
            continue
        if authority == HistoricalActorAuthority.SERVICE.value:
            resolved = service_owner(authority_ref, nodes) is not None
            target_label = "named VM service"
        else:
            target_label, declarations = actor_targets.get(authority, ("declared authority", {}))
            section = {
                HistoricalActorAuthority.ENTITY.value: "entities",
                HistoricalActorAuthority.AGENT.value: "agents",
                HistoricalActorAuthority.ACCOUNT.value: "accounts",
            }.get(authority, "")
            resolved = bool(section and resolve_section_ref(authority_ref, section, declarations) is not None)
        if not resolved:
            issues.append(
                issue(
                    "historical-state.actor.authority-unbound",
                    f"Historical baseline '{baseline_name}' actor '{actor_id}' authority_ref does not resolve "
                    f"to a {target_label}",
                )
            )
    return issues


@dataclass(frozen=True)
class _TenancyContext:
    baseline_name: str
    deployment_tenants: Mapping[str, object]
    deployment_cells: Mapping[str, object]
    relationships: Mapping[str, object]
    is_unresolved: Callable[[object], bool]


def _cell_tenancy_issues(
    context: _TenancyContext,
    tenant_name: str | None,
    cell_name: str | None,
) -> list[HistoricalStateIssue]:
    if tenant_name is None or cell_name is None:
        return []
    cell_tenant_ref = getattr(context.deployment_cells[cell_name], "tenant_ref", "")
    cell_tenant_name = (
        None
        if context.is_unresolved(cell_tenant_ref)
        else resolve_section_ref(cell_tenant_ref, "deployment_tenants", context.deployment_tenants)
    )
    if context.is_unresolved(cell_tenant_ref) or cell_tenant_name == tenant_name:
        return []
    return [
        issue(
            "historical-state.cell.tenant-mismatch",
            f"Historical baseline '{context.baseline_name}' deployment cell and tenant must agree",
        )
    ]


def _reset_owner_issues(
    context: _TenancyContext,
    tenant_ref: object,
    tenant_name: str | None,
    reset_ref: object,
    reset_name: str | None,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    if reset_name is None:
        if not context.is_unresolved(reset_ref):
            issues.append(
                issue(
                    "historical-state.reset.unbound",
                    f"Historical baseline '{context.baseline_name}' reset_owner_relationship_ref does not resolve",
                )
            )
    else:
        relationship = context.relationships[reset_name]
        detail = getattr(relationship, "shared_service", None)
        relationship_type = getattr(relationship, "type", "")
        source_ref = getattr(relationship, "source", "")
        reset_owner = getattr(detail, "reset_generation_owner", "") if detail is not None else ""
        source_name = resolve_section_ref(
            source_ref,
            "deployment_tenants",
            context.deployment_tenants,
        )
        ownership_values = (tenant_ref, relationship_type, source_ref, reset_owner)
        ownership_mismatch = (
            enum_value(relationship_type) != RelationshipType.USES_SHARED_SERVICE.value
            or detail is None
            or source_name != tenant_name
            or enum_value(reset_owner) == "none"
        )
        if not any(context.is_unresolved(value) for value in ownership_values) and ownership_mismatch:
            issues.append(
                issue(
                    "historical-state.reset.owner-mismatch",
                    f"Historical baseline '{context.baseline_name}' reset owner must be an agreeing ADR-087 "
                    "shared-service binding",
                )
            )
    return issues


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
    context = _TenancyContext(
        baseline_name=baseline_name,
        deployment_tenants=deployment_tenants,
        deployment_cells=deployment_cells,
        relationships=relationships,
        is_unresolved=is_unresolved,
    )
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
    issues.extend(
        _cell_tenancy_issues(
            context,
            tenant_name,
            cell_name,
        )
    )
    issues.extend(
        _reset_owner_issues(
            context,
            tenant_ref,
            tenant_name,
            reset_ref,
            reset_name,
        )
    )
    return issues, (tenant_name, cell_name, reset_name)


@dataclass(frozen=True)
class _ObjectAnalysisContext:
    baseline_name: str
    baseline: object
    content: Mapping[str, object]
    nodes: Mapping[str, object]
    deployment_cells: Mapping[str, object]
    is_unresolved: Callable[[object], bool]


def _object_identity_issues(
    context: _ObjectAnalysisContext,
    object_id: str,
    historical_object: object,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    writer_ref = getattr(historical_object, "writer_actor_ref", "")
    if (
        not context.is_unresolved(writer_ref)
        and resolve_local_ref(
            writer_ref,
            baseline_name=context.baseline_name,
            collection_name="actors",
            declarations=getattr(context.baseline, "actors", {}),
        )
        is None
    ):
        issues.append(
            issue(
                "historical-state.object.writer-unbound",
                f"Historical baseline '{context.baseline_name}' object '{object_id}' writer_actor_ref does not "
                "resolve to a baseline actor",
            )
        )
    for field_name in ("title", "summary"):
        value = getattr(historical_object, field_name, "")
        if isinstance(value, str) and unsafe_text_reason(value) is not None:
            issues.append(
                issue(
                    "historical-state.corpus.unsafe-metadata",
                    f"Historical baseline '{context.baseline_name}' object '{object_id}' {field_name} contains "
                    "unsafe corpus material",
                )
            )
    return issues


def _content_tenancy_issues(
    context: _ObjectAnalysisContext,
    object_id: str,
    content_value: object,
) -> tuple[list[HistoricalStateIssue], str | None]:
    content_target_ref = getattr(content_value, "target", "")
    target_node = (
        None
        if context.is_unresolved(content_target_ref)
        else resolve_section_ref(content_target_ref, "nodes", context.nodes)
    )
    cell_ref = getattr(context.baseline, "deployment_cell_ref", "")
    cell_name = (
        None
        if context.is_unresolved(cell_ref)
        else resolve_section_ref(cell_ref, "deployment_cells", context.deployment_cells)
    )
    issues: list[HistoricalStateIssue] = []
    if target_node is not None and cell_name is not None:
        cell_nodes, cell_nodes_incomplete = _resolved_cell_nodes(context, cell_name)
        if not cell_nodes_incomplete and target_node not in cell_nodes:
            issues.append(
                issue(
                    "historical-state.object.content-tenant-mismatch",
                    f"Historical baseline '{context.baseline_name}' object '{object_id}' content target must "
                    "belong to the baseline deployment cell",
                )
            )
    return issues, target_node


def _resolved_cell_nodes(
    context: _ObjectAnalysisContext,
    cell_name: str,
) -> tuple[set[str], bool]:
    cell_node_refs = getattr(context.deployment_cells[cell_name], "node_refs", ())
    resolved = {
        node_name
        for node_ref in cell_node_refs
        if not context.is_unresolved(node_ref)
        and (node_name := resolve_section_ref(node_ref, "nodes", context.nodes)) is not None
    }
    return resolved, any(context.is_unresolved(node_ref) for node_ref in cell_node_refs)


def _content_materialization_issues(
    context: _ObjectAnalysisContext,
    object_id: str,
    target_node: str | None,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    for binding_id, binding in getattr(context.baseline, "materialization_bindings", {}).items():
        object_refs = getattr(binding, "object_refs", ())
        resolved_objects = {
            resolved
            for object_ref in object_refs
            if not context.is_unresolved(object_ref)
            and (
                resolved := resolve_local_ref(
                    object_ref,
                    baseline_name=context.baseline_name,
                    collection_name="objects",
                    declarations=getattr(context.baseline, "objects", {}),
                )
            )
            is not None
        }
        if object_id not in resolved_objects:
            continue
        target_service_ref = getattr(binding, "target_service_ref", "")
        materialization_node = (
            None if context.is_unresolved(target_service_ref) else service_owner(target_service_ref, context.nodes)
        )
        if target_node is not None and materialization_node is not None and target_node != materialization_node:
            issues.append(
                issue(
                    "historical-state.object.content-target-mismatch",
                    f"Historical baseline '{context.baseline_name}' object '{object_id}' content target must "
                    f"agree with materialization binding '{binding_id}' target",
                )
            )
    return issues


def _content_policy_issues(
    context: _ObjectAnalysisContext,
    object_id: str,
    historical_object: object,
    content_value: object,
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    content_sensitive = getattr(content_value, "sensitive", False)
    object_sensitivity = getattr(historical_object, "sensitivity", "")
    if (
        not context.is_unresolved(content_sensitive)
        and not context.is_unresolved(object_sensitivity)
        and content_sensitive is True
        and enum_value(object_sensitivity) != HistoricalContentSensitivity.RESTRICTED.value
    ):
        issues.append(
            issue(
                "historical-state.object.content-sensitivity-downgrade",
                f"Historical baseline '{context.baseline_name}' object '{object_id}' must not downgrade "
                "sensitive content",
            )
        )
    if getattr(content_value, "text", None) is not None:
        issues.append(
            issue(
                "historical-state.corpus.inline-body",
                f"Historical baseline '{context.baseline_name}' object '{object_id}' must not reference inline "
                "historical corpus bodies",
            )
        )
    metadata = [
        getattr(content_value, "description", ""),
        *(getattr(item, "description", "") for item in getattr(content_value, "items", ())),
    ]
    if any(isinstance(value, str) and unsafe_text_reason(value) is not None for value in metadata):
        issues.append(
            issue(
                "historical-state.corpus.unsafe-content",
                f"Historical baseline '{context.baseline_name}' object '{object_id}' references unsafe "
                "content metadata",
            )
        )
    return issues


def object_issues(
    baseline_name: str,
    baseline: object,
    *,
    content: Mapping[str, object],
    nodes: Mapping[str, object],
    deployment_cells: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[HistoricalStateIssue]:
    issues: list[HistoricalStateIssue] = []
    context = _ObjectAnalysisContext(
        baseline_name=baseline_name,
        baseline=baseline,
        content=content,
        nodes=nodes,
        deployment_cells=deployment_cells,
        is_unresolved=is_unresolved,
    )
    for object_id, historical_object in getattr(baseline, "objects", {}).items():
        issues.extend(_object_identity_issues(context, object_id, historical_object))
        content_ref = getattr(historical_object, "content_ref", "")
        if not content_ref or is_unresolved(content_ref):
            continue
        content_name = resolve_section_ref(content_ref, "content", content)
        if content_name is None:
            issues.append(
                issue(
                    "historical-state.object.content-unbound",
                    f"Historical baseline '{baseline_name}' object '{object_id}' content_ref does not resolve",
                )
            )
            continue
        content_value = content[content_name]
        tenancy_issues, target_node = _content_tenancy_issues(context, object_id, content_value)
        issues.extend(tenancy_issues)
        issues.extend(_content_materialization_issues(context, object_id, target_node))
        issues.extend(_content_policy_issues(context, object_id, historical_object, content_value))
    return issues
