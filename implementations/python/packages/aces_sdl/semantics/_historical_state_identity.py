"""Identity and corpus checks for authored historical state."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from ..entities import flatten_entities
from ..historical_state import (
    HISTORICAL_ADDRESS_PROFILE,
    HISTORICAL_TIME_PROFILE,
    HistoricalActorAuthority,
    HistoricalContentSensitivity,
)
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
    actors = getattr(baseline, "actors", {})
    for object_id, historical_object in getattr(baseline, "objects", {}).items():
        writer_ref = getattr(historical_object, "writer_actor_ref", "")
        if (
            not is_unresolved(writer_ref)
            and resolve_local_ref(
                writer_ref,
                baseline_name=baseline_name,
                collection_name="actors",
                declarations=actors,
            )
            is None
        ):
            issues.append(
                issue(
                    "historical-state.object.writer-unbound",
                    f"Historical baseline '{baseline_name}' object '{object_id}' writer_actor_ref does not "
                    "resolve to a baseline actor",
                )
            )
        for field_name in ("title", "summary"):
            value = getattr(historical_object, field_name, "")
            if isinstance(value, str) and unsafe_text_reason(value) is not None:
                issues.append(
                    issue(
                        "historical-state.corpus.unsafe-metadata",
                        f"Historical baseline '{baseline_name}' object '{object_id}' {field_name} contains "
                        "unsafe corpus material",
                    )
                )
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
        content_target_ref = getattr(content_value, "target", "")
        target_node = (
            None if is_unresolved(content_target_ref) else resolve_section_ref(content_target_ref, "nodes", nodes)
        )
        cell_ref = getattr(baseline, "deployment_cell_ref", "")
        cell_name = (
            None if is_unresolved(cell_ref) else resolve_section_ref(cell_ref, "deployment_cells", deployment_cells)
        )
        if target_node is not None and cell_name is not None:
            cell_node_refs = getattr(deployment_cells[cell_name], "node_refs", ())
            cell_nodes = {
                node_name
                for node_ref in cell_node_refs
                if not is_unresolved(node_ref)
                and (node_name := resolve_section_ref(node_ref, "nodes", nodes)) is not None
            }
            if not any(is_unresolved(node_ref) for node_ref in cell_node_refs) and target_node not in cell_nodes:
                issues.append(
                    issue(
                        "historical-state.object.content-tenant-mismatch",
                        f"Historical baseline '{baseline_name}' object '{object_id}' content target must "
                        "belong to the baseline deployment cell",
                    )
                )
        for binding_id, binding in getattr(baseline, "materialization_bindings", {}).items():
            object_refs = getattr(binding, "object_refs", ())
            resolved_objects = {
                resolved
                for object_ref in object_refs
                if not is_unresolved(object_ref)
                and (
                    resolved := resolve_local_ref(
                        object_ref,
                        baseline_name=baseline_name,
                        collection_name="objects",
                        declarations=getattr(baseline, "objects", {}),
                    )
                )
                is not None
            }
            if object_id not in resolved_objects:
                continue
            target_service_ref = getattr(binding, "target_service_ref", "")
            materialization_node = (
                None if is_unresolved(target_service_ref) else service_owner(target_service_ref, nodes)
            )
            if target_node is not None and materialization_node is not None and target_node != materialization_node:
                issues.append(
                    issue(
                        "historical-state.object.content-target-mismatch",
                        f"Historical baseline '{baseline_name}' object '{object_id}' content target must "
                        f"agree with materialization binding '{binding_id}' target",
                    )
                )
        content_sensitive = getattr(content_value, "sensitive", False)
        object_sensitivity = getattr(historical_object, "sensitivity", "")
        if (
            not is_unresolved(content_sensitive)
            and not is_unresolved(object_sensitivity)
            and content_sensitive is True
            and enum_value(object_sensitivity) != HistoricalContentSensitivity.RESTRICTED.value
        ):
            issues.append(
                issue(
                    "historical-state.object.content-sensitivity-downgrade",
                    f"Historical baseline '{baseline_name}' object '{object_id}' must not downgrade sensitive content",
                )
            )
        if getattr(content_value, "text", None) is not None:
            issues.append(
                issue(
                    "historical-state.corpus.inline-body",
                    f"Historical baseline '{baseline_name}' object '{object_id}' must not reference inline "
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
                    f"Historical baseline '{baseline_name}' object '{object_id}' references unsafe content metadata",
                )
            )
    return issues
