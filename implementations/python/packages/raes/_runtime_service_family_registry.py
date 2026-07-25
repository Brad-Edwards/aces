"""Static registry of node-scoped runtime service families.

This module holds the pure registration data — the :class:`RuntimeServiceFamily`
and :class:`RuntimeReferenceChild` dataclasses plus the canonical
``RUNTIME_SERVICE_FAMILIES`` table.  The traversal/alias logic that consumes the
registry lives in :mod:`raes._runtime_service_families`, which re-exports
these names so existing import paths remain stable.
"""

from __future__ import annotations

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


__all__ = [
    "RUNTIME_SERVICE_FAMILIES",
    "RuntimeReferenceChild",
    "RuntimeServiceFamily",
]
