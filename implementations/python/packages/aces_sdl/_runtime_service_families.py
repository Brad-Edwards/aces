"""Canonical runtime service-family registry for SDL facades and refs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass

from ._runtime_service_family_registry import (
    RUNTIME_SERVICE_FAMILIES,
    RuntimeReferenceChild,
    RuntimeServiceFamily,
)


@dataclass(frozen=True)
class RuntimeFamilyReference:
    """One exact qualified address in a node runtime inventory."""

    address: str
    node_name: str
    family: RuntimeServiceFamily
    item: object
    owning_item: object
    collection_path: tuple[str, ...] = ()


def runtime_service_family_export_names() -> tuple[str, ...]:
    """Return the public model symbols exported by all registered families."""

    names: list[str] = []
    owners: dict[str, str] = {}
    duplicate_names: list[str] = []
    for family in RUNTIME_SERVICE_FAMILIES:
        for name in family.public_symbols:
            if name in owners:
                duplicate_names.append(f"{name} ({owners[name]}, {family.key})")
                continue
            owners[name] = family.key
            names.append(name)
    if duplicate_names:
        raise RuntimeError("Runtime service family export names must be unique: " + ", ".join(duplicate_names))
    return tuple(names)


def runtime_service_family_exports() -> dict[str, object]:
    """Return the public model symbols exported by all registered families."""

    runtime_service_family_export_names()
    exports: dict[str, object] = {}
    for family in RUNTIME_SERVICE_FAMILIES:
        for name in family.public_symbols:
            exports[name] = getattr(family.module, name)
    return exports


def install_runtime_service_family_exports(namespace: MutableMapping[str, object]) -> tuple[str, ...]:
    """Install family symbols into a facade module namespace."""

    exports = runtime_service_family_exports()
    names = runtime_service_family_export_names()
    for name in names:
        namespace[name] = exports[name]
    return names


def collect_qualified_runtime_family_refs(
    scenario: object,
    *,
    family_keys: Iterable[str] | None = None,
) -> set[str]:
    """Return targetable qualified refs for all registered runtime families."""

    return {reference.address for reference in iter_runtime_family_references(scenario, family_keys=family_keys)}


def iter_runtime_family_references(
    scenario: object,
    *,
    family_keys: Iterable[str] | None = None,
) -> Iterable[RuntimeFamilyReference]:
    """Yield registered runtime declarations without decoding rendered addresses."""

    selected = _selected_family_keys(family_keys)
    for node_name, _prefixed_node, runtime in _runtime_instances(scenario, {}):
        for family in _families(selected):
            for item in getattr(runtime, family.collection_name, []):
                item_id = getattr(item, family.id_field, "")
                if not item_id:
                    continue
                base = f"nodes.{node_name}.runtime.{family.collection_name}.{item_id}"
                yield RuntimeFamilyReference(
                    address=base,
                    node_name=node_name,
                    family=family,
                    item=item,
                    owning_item=item,
                )
                yield from _iter_child_references(
                    item,
                    base=base,
                    node_name=node_name,
                    family=family,
                    owning_item=item,
                    collection_path=(),
                    child_specs=family.child_refs,
                )


def _iter_child_references(
    item: object,
    *,
    base: str,
    node_name: str,
    family: RuntimeServiceFamily,
    owning_item: object,
    collection_path: tuple[str, ...],
    child_specs: tuple[RuntimeReferenceChild, ...],
) -> Iterable[RuntimeFamilyReference]:
    for child_spec in child_specs:
        for child in getattr(item, child_spec.collection_name, []):
            child_id = getattr(child, child_spec.id_field, "")
            if not child_id:
                continue
            child_base = f"{base}.{child_spec.collection_name}.{child_id}"
            yield RuntimeFamilyReference(
                address=child_base,
                node_name=node_name,
                family=family,
                item=child,
                owning_item=owning_item,
                collection_path=(*collection_path, child_spec.collection_name),
            )
            yield from _iter_child_references(
                child,
                base=child_base,
                node_name=node_name,
                family=family,
                owning_item=owning_item,
                collection_path=(*collection_path, child_spec.collection_name),
                child_specs=child_spec.children,
            )


def nested_node_runtime_family_aliases(
    scenario: object,
    node_rename_map: Mapping[str, str],
    *,
    family_keys: Iterable[str] | None = None,
) -> dict[str, str]:
    """Return nested-node aliases for registered runtime family refs."""

    aliases: dict[str, str] = {}
    selected = _selected_family_keys(family_keys)
    for node_name, prefixed_node, runtime in _runtime_instances(scenario, node_rename_map):
        if prefixed_node == node_name:
            continue
        for family in _families(selected):
            aliases.update(
                _runtime_family_aliases(
                    node_name=node_name,
                    prefixed_node=prefixed_node,
                    runtime=runtime,
                    family=family,
                )
            )
    return aliases


def _selected_family_keys(family_keys: Iterable[str] | None) -> set[str] | None:
    if family_keys is None:
        return None
    return set(family_keys)


def _families(selected: set[str] | None) -> Iterable[RuntimeServiceFamily]:
    for family in RUNTIME_SERVICE_FAMILIES:
        if selected is None or family.key in selected or family.collection_name in selected:
            yield family


def _runtime_instances(
    scenario: object,
    node_rename_map: Mapping[str, str],
) -> Iterable[tuple[str, str, object]]:
    nodes = getattr(scenario, "nodes", {})
    if not isinstance(nodes, Mapping):
        return
    for node_name, node in nodes.items():
        if not isinstance(node_name, str):
            continue
        prefixed_node = node_rename_map.get(node_name, node_name)
        runtime = getattr(node, "runtime", None)
        if runtime is not None:
            yield node_name, prefixed_node, runtime


def _runtime_family_refs(*, node_name: str, runtime: object, family: RuntimeServiceFamily) -> set[str]:
    refs: set[str] = set()
    for item in getattr(runtime, family.collection_name, []):
        item_id = getattr(item, family.id_field, "")
        if not item_id:
            continue
        base = f"nodes.{node_name}.runtime.{family.collection_name}.{item_id}"
        refs.add(base)
        refs.update(_child_refs(item, base, family.child_refs))
    return refs


def _child_refs(item: object, base: str, child_specs: tuple[RuntimeReferenceChild, ...]) -> set[str]:
    refs: set[str] = set()
    for child_spec in child_specs:
        for child in getattr(item, child_spec.collection_name, []):
            child_id = getattr(child, child_spec.id_field, "")
            if not child_id:
                continue
            child_base = f"{base}.{child_spec.collection_name}.{child_id}"
            refs.add(child_base)
            refs.update(_child_refs(child, child_base, child_spec.children))
    return refs


def _runtime_family_aliases(
    *,
    node_name: str,
    prefixed_node: str,
    runtime: object,
    family: RuntimeServiceFamily,
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for item in getattr(runtime, family.collection_name, []):
        item_id = getattr(item, family.id_field, "")
        if not item_id:
            continue
        bare_base = f"nodes.{node_name}.runtime.{family.collection_name}.{item_id}"
        prefixed_base = f"nodes.{prefixed_node}.runtime.{family.collection_name}.{item_id}"
        aliases[bare_base] = prefixed_base
        aliases.update(_child_aliases(item, bare_base, prefixed_base, family.child_refs))
    return aliases


def _child_aliases(
    item: object,
    bare_base: str,
    prefixed_base: str,
    child_specs: tuple[RuntimeReferenceChild, ...],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for child_spec in child_specs:
        for child in getattr(item, child_spec.collection_name, []):
            child_id = getattr(child, child_spec.id_field, "")
            if not child_id:
                continue
            bare_child = f"{bare_base}.{child_spec.collection_name}.{child_id}"
            prefixed_child = f"{prefixed_base}.{child_spec.collection_name}.{child_id}"
            aliases[bare_child] = prefixed_child
            aliases.update(_child_aliases(child, bare_child, prefixed_child, child_spec.children))
    return aliases


__all__ = [
    "RUNTIME_SERVICE_FAMILIES",
    "RuntimeFamilyReference",
    "RuntimeReferenceChild",
    "RuntimeServiceFamily",
    "collect_qualified_runtime_family_refs",
    "install_runtime_service_family_exports",
    "iter_runtime_family_references",
    "nested_node_runtime_family_aliases",
    "runtime_service_family_export_names",
    "runtime_service_family_exports",
]
