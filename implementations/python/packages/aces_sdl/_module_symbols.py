"""Symbol-index helpers for SDL module composition.

Builds the per-section rename maps and the cross-section ``named`` alias
table that ``composition._namespace_payload`` uses to rewrite SDL
references when an imported module is mounted under a namespace.

Lives next to ``composition.py`` (not inside it) to keep that file under
the repo-policy line cap, mirroring ``_module_provenance.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .entities import flatten_entities
from .scenario import ModuleDescriptor, Scenario

# Canonical list of scenario top-level sections that hold user-defined
# hashmap keys. Re-exported as both the public ``HASHMAP_SECTIONS`` name
# (consumed by ``composition.py``) and the private ``_HASHMAP_SECTIONS``
# alias used within this module.
HASHMAP_SECTIONS = (
    "nodes",
    "infrastructure",
    "features",
    "conditions",
    "vulnerabilities",
    "metrics",
    "evaluations",
    "tlos",
    "goals",
    "entities",
    "injects",
    "events",
    "scripts",
    "stories",
    "content",
    "accounts",
    "relationships",
    "agents",
    "objectives",
    "workflows",
)
_HASHMAP_SECTIONS = HASHMAP_SECTIONS


def _prefix(namespace: str, name: str) -> str:
    return f"{namespace}.{name}" if namespace else name


def _private_prefix(namespace: str, name: str) -> str:
    return _prefix(namespace, f"__private.{name}")


def explicit_exports(
    scenario: Scenario,
    descriptor: ModuleDescriptor,
) -> dict[str, set[str]]:
    if scenario.module is None:
        return {
            section: set(getattr(scenario, section).keys())
            for section in _HASHMAP_SECTIONS
            if getattr(scenario, section)
        } | {"entities": set(flatten_entities(scenario.entities))}
    return {section: set(names) for section, names in descriptor.exports.items()} | {
        "entities": set(descriptor.exports.get("entities", []))
    }


def _section_rename_map(
    section: Mapping[str, Any],
    *,
    namespace: str,
    exported_names: set[str],
) -> dict[str, str]:
    return {
        name: (_prefix(namespace, name) if name in exported_names else _private_prefix(namespace, name))
        for name in section
    }


def _qualified_section_aliases(section_name: str, rename_map: Mapping[str, str]) -> dict[str, str]:
    """Section-qualified aliases (e.g. ``nodes.vm`` -> ``nodes.shared.vm``)."""
    return {f"{section_name}.{bare}": f"{section_name}.{prefixed}" for bare, prefixed in rename_map.items()}


def _nested_node_service_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    """Qualified service refs ``nodes.<vm>.services.<svc>``.

    The node's bare name in the second segment must be rewritten so a
    qualified service ref survives namespacing.
    """
    aliases: dict[str, str] = {}
    for node_name, node in scenario.nodes.items():
        prefixed_node = node_rename_map.get(node_name, node_name)
        if prefixed_node == node_name:
            continue
        for service in getattr(node, "services", []):
            if not getattr(service, "name", ""):
                continue
            bare_ref = f"nodes.{node_name}.services.{service.name}"
            prefixed_ref = f"nodes.{prefixed_node}.services.{service.name}"
            aliases[bare_ref] = prefixed_ref
    return aliases


def _nested_node_application_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    """Qualified runtime-application refs ``nodes.<vm>.runtime.applications.<app>``.

    The node segment must be rewritten so a qualified application ref used as a
    relationship endpoint survives namespacing.
    """
    aliases: dict[str, str] = {}
    for node_name, node in scenario.nodes.items():
        prefixed_node = node_rename_map.get(node_name, node_name)
        if prefixed_node == node_name:
            continue
        runtime = getattr(node, "runtime", None)
        if runtime is None:
            continue
        for application in getattr(runtime, "applications", []):
            app_id = getattr(application, "application_id", "")
            if not app_id:
                continue
            bare_ref = f"nodes.{node_name}.runtime.applications.{app_id}"
            aliases[bare_ref] = f"nodes.{prefixed_node}.runtime.applications.{app_id}"
    return aliases


def _database_service_aliases(
    *,
    node_name: str,
    prefixed_node: str,
    dbsvc: Any,
) -> dict[str, str]:
    """Aliases for one database service: the service ref and each contained database."""
    svc_id = getattr(dbsvc, "database_service_id", "")
    if not svc_id:
        return {}
    bare_base = f"nodes.{node_name}.runtime.database_services.{svc_id}"
    prefixed_base = f"nodes.{prefixed_node}.runtime.database_services.{svc_id}"
    aliases: dict[str, str] = {bare_base: prefixed_base}
    for database in getattr(dbsvc, "databases", []):
        db_id = getattr(database, "database_id", "")
        if db_id:
            aliases[f"{bare_base}.databases.{db_id}"] = f"{prefixed_base}.databases.{db_id}"
    return aliases


def _nested_node_database_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    """Qualified database refs ``nodes.<vm>.runtime.database_services.<id>[...]``.

    Covers the database-service ref and the ``.databases.<id>`` ref so an
    application-to-database relationship endpoint survives namespacing
    (ADR-029 §2).
    """
    aliases: dict[str, str] = {}
    for node_name, node in scenario.nodes.items():
        prefixed_node = node_rename_map.get(node_name, node_name)
        if prefixed_node == node_name:
            continue
        runtime = getattr(node, "runtime", None)
        if runtime is None:
            continue
        for dbsvc in getattr(runtime, "database_services", []):
            aliases.update(
                _database_service_aliases(
                    node_name=node_name,
                    prefixed_node=prefixed_node,
                    dbsvc=dbsvc,
                )
            )
    return aliases


def _identity_authority_collection_aliases(
    *,
    bare_base: str,
    prefixed_base: str,
    collection: list[Any],
    collection_name: str,
    id_field: str,
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for item in collection:
        item_id = getattr(item, id_field, "")
        if item_id:
            aliases[f"{bare_base}.{collection_name}.{item_id}"] = f"{prefixed_base}.{collection_name}.{item_id}"
    return aliases


def _identity_authority_aliases(
    *,
    node_name: str,
    prefixed_node: str,
    authority: Any,
) -> dict[str, str]:
    """Aliases for one identity authority and its stable child records."""
    authority_id = getattr(authority, "authority_id", "")
    if not authority_id:
        return {}
    bare_base = f"nodes.{node_name}.runtime.identity_authorities.{authority_id}"
    prefixed_base = f"nodes.{prefixed_node}.runtime.identity_authorities.{authority_id}"
    aliases: dict[str, str] = {bare_base: prefixed_base}
    aliases.update(
        _identity_authority_collection_aliases(
            bare_base=bare_base,
            prefixed_base=prefixed_base,
            collection=getattr(authority, "services", []),
            collection_name="services",
            id_field="service_id",
        )
    )
    aliases.update(
        _identity_authority_collection_aliases(
            bare_base=bare_base,
            prefixed_base=prefixed_base,
            collection=getattr(authority, "subjects", []),
            collection_name="subjects",
            id_field="subject_id",
        )
    )
    aliases.update(
        _identity_authority_collection_aliases(
            bare_base=bare_base,
            prefixed_base=prefixed_base,
            collection=getattr(authority, "policies", []),
            collection_name="policies",
            id_field="policy_id",
        )
    )
    aliases.update(
        _identity_authority_collection_aliases(
            bare_base=bare_base,
            prefixed_base=prefixed_base,
            collection=getattr(authority, "relationships", []),
            collection_name="relationships",
            id_field="relationship_id",
        )
    )
    return aliases


def _nested_node_identity_authority_aliases(
    scenario: Scenario,
    node_rename_map: Mapping[str, str],
) -> dict[str, str]:
    """Qualified identity authority refs ``nodes.<vm>.runtime.identity_authorities.<id>[...]``."""
    aliases: dict[str, str] = {}
    for node_name, node in scenario.nodes.items():
        prefixed_node = node_rename_map.get(node_name, node_name)
        if prefixed_node == node_name:
            continue
        runtime = getattr(node, "runtime", None)
        if runtime is None:
            continue
        for authority in getattr(runtime, "identity_authorities", []):
            aliases.update(
                _identity_authority_aliases(
                    node_name=node_name,
                    prefixed_node=prefixed_node,
                    authority=authority,
                )
            )
    return aliases


def _nested_content_item_aliases(
    scenario: Scenario,
    content_rename_map: Mapping[str, str],
) -> dict[str, str]:
    """Qualified content-item refs ``content.<section>.items.<item>``."""
    aliases: dict[str, str] = {}
    for content_name, content in scenario.content.items():
        prefixed_content = content_rename_map.get(content_name, content_name)
        if prefixed_content == content_name:
            continue
        for item in getattr(content, "items", []):
            if not getattr(item, "name", ""):
                continue
            bare_ref = f"content.{content_name}.items.{item.name}"
            prefixed_ref = f"content.{prefixed_content}.items.{item.name}"
            aliases[bare_ref] = prefixed_ref
    return aliases


def symbol_index(
    scenario: Scenario,
    *,
    namespace: str,
    descriptor: ModuleDescriptor,
) -> dict[str, dict[str, str] | set[str]]:
    entities = set(flatten_entities(scenario.entities))
    exported = explicit_exports(scenario, descriptor)
    named: dict[str, str] = {}
    section_maps: dict[str, dict[str, str]] = {}
    for section_name in _HASHMAP_SECTIONS:
        section = getattr(scenario, section_name, {})
        if not isinstance(section, Mapping):
            continue
        section_map = _section_rename_map(
            section,
            namespace=namespace,
            exported_names=exported.get(section_name, set()),
        )
        section_maps[section_name] = section_map
        named.update(section_map)
        named.update(_qualified_section_aliases(section_name, section_map))

    entity_map = _section_rename_map(
        {name: None for name in entities},
        namespace=namespace,
        exported_names=exported.get("entities", set()),
    )
    named.update(entity_map)
    named.update(_qualified_section_aliases("entities", entity_map))

    named.update(_nested_node_service_aliases(scenario, section_maps.get("nodes", {})))
    named.update(_nested_node_application_aliases(scenario, section_maps.get("nodes", {})))
    named.update(_nested_node_database_aliases(scenario, section_maps.get("nodes", {})))
    named.update(_nested_node_identity_authority_aliases(scenario, section_maps.get("nodes", {})))
    named.update(_nested_content_item_aliases(scenario, section_maps.get("content", {})))

    return {
        "nodes": section_maps.get("nodes", {}),
        "infrastructure": section_maps.get("infrastructure", {}),
        "features": section_maps.get("features", {}),
        "conditions": section_maps.get("conditions", {}),
        "vulnerabilities": section_maps.get("vulnerabilities", {}),
        "metrics": section_maps.get("metrics", {}),
        "evaluations": section_maps.get("evaluations", {}),
        "tlos": section_maps.get("tlos", {}),
        "goals": section_maps.get("goals", {}),
        "entities": entity_map,
        "injects": section_maps.get("injects", {}),
        "events": section_maps.get("events", {}),
        "scripts": section_maps.get("scripts", {}),
        "stories": section_maps.get("stories", {}),
        "content": section_maps.get("content", {}),
        "accounts": section_maps.get("accounts", {}),
        "relationships": section_maps.get("relationships", {}),
        "agents": section_maps.get("agents", {}),
        "objectives": section_maps.get("objectives", {}),
        "workflows": section_maps.get("workflows", {}),
        "named": named,
    }


__all__ = ["HASHMAP_SECTIONS", "explicit_exports", "symbol_index"]
