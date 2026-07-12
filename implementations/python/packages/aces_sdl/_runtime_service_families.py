"""Canonical runtime service-family registry for SDL facades and refs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from types import ModuleType

from . import runtime_app_authorization as _runtime_app_authorization
from . import runtime_application as _runtime_application
from . import runtime_database as _runtime_database
from . import runtime_datastore as _runtime_datastore
from . import runtime_directory_identity as _runtime_directory_identity
from . import runtime_dns as _runtime_dns
from . import runtime_file_service as _runtime_file_service
from . import runtime_forwarding_agent as _runtime_forwarding_agent
from . import runtime_listeners as _runtime_listeners
from . import runtime_mail_service as _runtime_mail_service
from . import runtime_network_detection as _runtime_network_detection
from . import runtime_network_sensor as _runtime_network_sensor
from . import runtime_orchestration as _runtime_orchestration
from . import runtime_platform_application as _runtime_platform_application
from . import runtime_scheduled_job as _runtime_scheduled_job
from . import runtime_security_monitoring as _runtime_security_monitoring
from . import runtime_ssh_server as _runtime_ssh_server


@dataclass(frozen=True)
class RuntimeReferenceChild:
    """A stable child collection that can be addressed below a runtime family."""

    collection_name: str
    id_field: str
    children: tuple[RuntimeReferenceChild, ...] = ()


@dataclass(frozen=True)
class RuntimeServiceFamily:
    """Static registration metadata for one node-scoped runtime family."""

    key: str
    module: ModuleType
    collection_name: str
    id_field: str
    child_refs: tuple[RuntimeReferenceChild, ...] = ()

    @property
    def public_symbols(self) -> tuple[str, ...]:
        return tuple(getattr(self.module, "__all__", ()))


@dataclass(frozen=True)
class RuntimeFamilyReference:
    """One exact qualified address in a node runtime inventory."""

    address: str
    node_name: str
    family: RuntimeServiceFamily
    item: object
    owning_item: object
    collection_path: tuple[str, ...] = ()


RUNTIME_SERVICE_FAMILIES: tuple[RuntimeServiceFamily, ...] = (
    RuntimeServiceFamily(
        key="service-listeners",
        module=_runtime_listeners,
        collection_name="service_listeners",
        id_field="service_listener_id",
    ),
    RuntimeServiceFamily(
        key="applications",
        module=_runtime_application,
        collection_name="applications",
        id_field="application_id",
    ),
    RuntimeServiceFamily(
        key="database-services",
        module=_runtime_database,
        collection_name="database_services",
        id_field="database_service_id",
        child_refs=(RuntimeReferenceChild("databases", "database_id"),),
    ),
    RuntimeServiceFamily(
        key="dns-services",
        module=_runtime_dns,
        collection_name="dns_services",
        id_field="dns_service_id",
        child_refs=(
            RuntimeReferenceChild(
                "zones",
                "zone_id",
                children=(RuntimeReferenceChild("rrsets", "rrset_id"),),
            ),
        ),
    ),
    RuntimeServiceFamily(
        key="identity-authorities",
        module=_runtime_directory_identity,
        collection_name="identity_authorities",
        id_field="identity_authority_id",
        child_refs=(
            RuntimeReferenceChild("services", "service_id"),
            RuntimeReferenceChild("subjects", "subject_id"),
            RuntimeReferenceChild("policies", "policy_id"),
            RuntimeReferenceChild("relationships", "relationship_id"),
        ),
    ),
    RuntimeServiceFamily(
        key="file-services",
        module=_runtime_file_service,
        collection_name="file_services",
        id_field="file_service_id",
        child_refs=(
            RuntimeReferenceChild("shares", "share_id"),
            RuntimeReferenceChild("principals", "principal_id"),
            RuntimeReferenceChild("access_rules", "rule_id"),
            RuntimeReferenceChild("access_observations", "observation_id"),
        ),
    ),
    RuntimeServiceFamily(
        key="mail-services",
        module=_runtime_mail_service,
        collection_name="mail_services",
        id_field="mail_service_id",
        child_refs=(
            RuntimeReferenceChild("components", "component_id"),
            RuntimeReferenceChild("listeners", "listener_id"),
            RuntimeReferenceChild("domains", "domain_id"),
            RuntimeReferenceChild("mailbox_stores", "store_id"),
            RuntimeReferenceChild("mailboxes", "mailbox_id"),
            RuntimeReferenceChild("aliases", "alias_id"),
            RuntimeReferenceChild("routing_rules", "rule_id"),
            RuntimeReferenceChild("queues", "queue_id"),
            RuntimeReferenceChild("settings", "setting_id"),
        ),
    ),
    RuntimeServiceFamily(
        key="network-sensors",
        module=_runtime_network_sensor,
        collection_name="network_sensors",
        id_field="network_sensor_id",
    ),
    RuntimeServiceFamily(
        key="network-detection-engines",
        module=_runtime_network_detection,
        collection_name="network_detection_engines",
        id_field="network_detection_engine_id",
        child_refs=(
            RuntimeReferenceChild("rule_sources", "source_id"),
            RuntimeReferenceChild("network_sets", "set_id"),
            RuntimeReferenceChild("output_streams", "stream_id"),
            RuntimeReferenceChild("control_channels", "channel_id"),
        ),
    ),
    RuntimeServiceFamily(
        key="security-monitoring-managers",
        module=_runtime_security_monitoring,
        collection_name="security_monitoring_managers",
        id_field="security_monitoring_manager_id",
        child_refs=(
            RuntimeReferenceChild("listeners", "listener_id"),
            RuntimeReferenceChild("components", "component_id"),
            RuntimeReferenceChild("agents", "agent_id"),
            RuntimeReferenceChild("agent_groups", "group_id"),
            RuntimeReferenceChild("content_sets", "content_id"),
            RuntimeReferenceChild("detection_definitions", "definition_id"),
            RuntimeReferenceChild("settings", "setting_id"),
        ),
    ),
    RuntimeServiceFamily(
        key="ssh-servers",
        module=_runtime_ssh_server,
        collection_name="ssh_servers",
        id_field="ssh_server_id",
        child_refs=(RuntimeReferenceChild("match_rules", "match_id"),),
    ),
    RuntimeServiceFamily(
        key="app-authorizations",
        module=_runtime_app_authorization,
        collection_name="app_authorizations",
        id_field="app_authorization_id",
        child_refs=(
            RuntimeReferenceChild("principals", "principal_id"),
            RuntimeReferenceChild("roles", "role_id"),
            RuntimeReferenceChild("permission_grants", "grant_id"),
            RuntimeReferenceChild("role_mappings", "mapping_id"),
            RuntimeReferenceChild("tenants", "tenant_id"),
        ),
    ),
    RuntimeServiceFamily(
        key="scheduled-jobs",
        module=_runtime_scheduled_job,
        collection_name="scheduled_jobs",
        id_field="scheduled_job_id",
    ),
    RuntimeServiceFamily(
        key="datastore-services",
        module=_runtime_datastore,
        collection_name="datastore_services",
        id_field="datastore_service_id",
        child_refs=(
            RuntimeReferenceChild(
                "nodes",
                "node_id",
                children=(
                    RuntimeReferenceChild("plugins", "plugin_id"),
                    RuntimeReferenceChild("endpoints", "endpoint_id"),
                ),
            ),
            RuntimeReferenceChild("partitions", "partition_id"),
            RuntimeReferenceChild("templates", "template_id"),
            RuntimeReferenceChild("mappings", "mapping_id"),
            RuntimeReferenceChild("settings", "setting_id"),
        ),
    ),
    RuntimeServiceFamily(
        key="platform-applications",
        module=_runtime_platform_application,
        collection_name="platform_applications",
        id_field="platform_application_id",
        child_refs=(
            RuntimeReferenceChild("organizations", "organization_id"),
            RuntimeReferenceChild("tenants", "tenant_id"),
            RuntimeReferenceChild("content_objects", "content_object_id"),
            RuntimeReferenceChild("markings", "marking_id"),
            RuntimeReferenceChild("upstream_bindings", "binding_id"),
            RuntimeReferenceChild("connectors", "connector_id"),
            RuntimeReferenceChild("settings", "setting_id"),
        ),
    ),
    RuntimeServiceFamily(
        key="forwarding-agents",
        module=_runtime_forwarding_agent,
        collection_name="forwarding_agents",
        id_field="forwarding_agent_id",
        child_refs=(
            RuntimeReferenceChild("sources", "source_id"),
            RuntimeReferenceChild("transforms", "transform_id"),
            RuntimeReferenceChild("ship_targets", "target_id"),
            RuntimeReferenceChild("reload_channels", "reload_channel_id"),
            RuntimeReferenceChild("settings", "setting_id"),
        ),
    ),
    RuntimeServiceFamily(
        key="orchestration-authorities",
        module=_runtime_orchestration,
        collection_name="orchestration_authorities",
        id_field="orchestration_authority_id",
        child_refs=(
            RuntimeReferenceChild("spawn_templates", "template_id"),
            RuntimeReferenceChild("realized_children", "workload_id"),
        ),
    ),
)


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
