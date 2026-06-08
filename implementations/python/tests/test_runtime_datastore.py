"""Runtime datastore-service (SCN-010 §5.1) SDL surface tests.

Covers the OPEN ``data_model`` discriminator spine, the typed cluster / node /
partition / persistence / transport-security / setting children, secret-bearing
setting redaction, duplicate-id rejection, and — the core correctness feature —
the ``require_profile_for_data_model`` guard (positive for each model plus each
REQUIRE / REJECT negative).
"""

from __future__ import annotations

import pytest
from aces_sdl.runtime_datastore import (
    RuntimeDatastoreCluster,
    RuntimeDatastoreDataModel,
    RuntimeDatastoreEngine,
    RuntimeDatastoreEnginePlugin,
    RuntimeDatastoreNode,
    RuntimeDatastoreNodeEndpoint,
    RuntimeDatastorePartitionKind,
    RuntimeDatastorePersistence,
    RuntimeDatastoreService,
    RuntimeDatastoreSetting,
    RuntimeDatastoreTransportSecurity,
)
from aces_sdl.runtime_datastore_vocab import (
    RuntimeDatastoreEvictionPolicy,
    RuntimeDatastoreNodeEndpointRole,
    RuntimeDatastoreNodeRole,
    RuntimeDatastoreReplicationStrategy,
    RuntimeDatastoreSettingProvenance,
    RuntimeDatastoreSettingScope,
    RuntimeDatastoreTransportSecurityMode,
)
from pydantic import ValidationError


def _search_index_service(**overrides) -> dict:
    service = {
        "datastore_service_id": "wazuh-indexer",
        "service": "indexer-listener",
        "engine": "opensearch",
        "data_model": "search_index",
        "protocol": "opensearch-transport",
        "version": "2.19.1.0",
        "name": "wazuh-cluster",
        "cluster": {
            "cluster_id": "wazuh-cluster",
            "name": "wazuh",
            "health": "green",
            "discovery_mode": "single-node",
        },
        "nodes": [
            {
                "node_id": "indexer-1",
                "name": "wazuh.indexer",
                "roles": ["cluster_manager", "data", "ingest"],
                "is_coordinator": True,
                "engine_version": "2.19.1",
                "build_hash": "dae2bfc93896178873b43cdf4781f183c72b238f",
                "build_type": "rpm",
                "heap_init_bytes": "1 GiB",
                "heap_max_bytes": "1 GiB",
                "memory_locked": True,
                "endpoints": [
                    {
                        "endpoint_id": "http",
                        "role": "client",
                        "protocol": "https",
                        "address": "172.20.0.12",
                        "port": 9200,
                    },
                    {
                        "endpoint_id": "transport",
                        "role": "peer",
                        "protocol": "transport",
                        "address": "172.20.0.12",
                        "port": 9300,
                    },
                ],
                "plugins": [
                    {"plugin_id": "opensearch-security", "name": "opensearch-security", "version": "2.19.1.0"},
                    {"plugin_id": "opensearch-alerting", "name": "opensearch-alerting", "version": "2.19.1.0"},
                ],
            }
        ],
        "partitions": [
            {
                "partition_id": "wazuh-alerts",
                "kind": "index",
                "name": "wazuh-alerts-4.x-2026.05.30",
                "shard_count": 3,
                "replica_count": 0,
                "health": "green",
            }
        ],
        "templates": ["wazuh-template"],
        "aliases": ["wazuh-alerts"],
        "mappings": ["index.mapping.total_fields.limit=10000"],
        "lifecycle_policies": ["wazuh-ism"],
        "ingest_pipelines": ["geoip"],
        "transport_security": {
            "transport_security_id": "indexer-tls",
            "mode": "mutual_tls",
            "node_verification": True,
        },
        "settings": [
            {
                "setting_id": "cluster-name",
                "scope": "cluster",
                "provenance": "configuration_file",
                "name": "cluster.name",
                "value": "wazuh-cluster",
            }
        ],
        "authorization_ref": "wazuh-indexer-rbac",
    }
    service.update(overrides)
    return service


def _wide_column_service(**overrides) -> dict:
    service = {
        "datastore_service_id": "thehive-cassandra",
        "engine": "cassandra",
        "data_model": "wide_column",
        "version": "4.1",
        "cluster": {
            "cluster_id": "thehive-ring",
            "partitioner": "Murmur3Partitioner",
            "native_protocol_version": "5",
        },
        "nodes": [
            {"node_id": "cass-1", "roles": ["seed", "coordinator"], "is_coordinator": True},
        ],
        "partitions": [
            {
                "partition_id": "thehive-ks",
                "kind": "keyspace",
                "name": "thehive",
                "replication_strategy": "network_topology_strategy",
                "replication_factor": 1,
                "per_dc_factor_map": {"dc1": 1},
                "durable_writes": True,
            }
        ],
        "authorization_ref": "cassandra-rbac",
    }
    service.update(overrides)
    return service


def _key_value_service(**overrides) -> dict:
    service = {
        "datastore_service_id": "misp-redis",
        "engine": "redis",
        "data_model": "key_value",
        "version": "7.2",
        "partitions": [
            {"partition_id": "db0", "kind": "logical_db", "name": "0", "datatype_census": {"string": 42, "hash": 7}},
        ],
        "persistence": {
            "persistence_id": "redis-persistence",
            "rdb_save_points": ["3600 1", "300 100", "60 10000"],
            "aof": False,
            "eviction": "noeviction",
            "maxmemory": "0",
        },
        "pubsub_channels": ["misp:channel"],
        "queues_streams": ["resque:queue"],
        "authorization_ref": "redis-acl",
    }
    service.update(overrides)
    return service


# --------------------------------------------------------------------------- #
# Construction / typed-child coercion                                         #
# --------------------------------------------------------------------------- #


def test_search_index_service_typed_children() -> None:
    svc = RuntimeDatastoreService(**_search_index_service())

    assert svc.datastore_service_id == "wazuh-indexer"
    assert svc.engine is RuntimeDatastoreEngine.OPENSEARCH
    assert svc.data_model is RuntimeDatastoreDataModel.SEARCH_INDEX
    assert isinstance(svc.cluster, RuntimeDatastoreCluster)
    node = svc.nodes[0]
    assert node.roles[0] is RuntimeDatastoreNodeRole.CLUSTER_MANAGER
    assert node.engine_version == "2.19.1"
    assert node.build_hash == "dae2bfc93896178873b43cdf4781f183c72b238f"
    assert node.build_type == "rpm"
    assert node.heap_init_bytes == 1_073_741_824
    assert node.heap_max_bytes == 1_073_741_824
    assert node.memory_locked is True
    assert [e.role for e in node.endpoints] == [
        RuntimeDatastoreNodeEndpointRole.CLIENT,
        RuntimeDatastoreNodeEndpointRole.PEER,
    ]
    assert node.endpoints[0].port == 9200
    assert node.endpoints[1].port == 9300
    assert node.plugins[0].name == "opensearch-security"
    assert node.plugins[0].version == "2.19.1.0"
    assert svc.partitions[0].kind is RuntimeDatastorePartitionKind.INDEX
    assert svc.partitions[0].shard_count == 3
    assert isinstance(svc.transport_security, RuntimeDatastoreTransportSecurity)
    assert svc.transport_security.mode is RuntimeDatastoreTransportSecurityMode.MUTUAL_TLS
    assert svc.settings[0].scope is RuntimeDatastoreSettingScope.CLUSTER
    assert svc.settings[0].provenance is RuntimeDatastoreSettingProvenance.CONFIGURATION_FILE
    assert svc.authorization_ref == "wazuh-indexer-rbac"


def test_wide_column_service_typed_children() -> None:
    svc = RuntimeDatastoreService(**_wide_column_service())

    partition = svc.partitions[0]
    assert partition.kind is RuntimeDatastorePartitionKind.KEYSPACE
    assert partition.replication_strategy is RuntimeDatastoreReplicationStrategy.NETWORK_TOPOLOGY_STRATEGY
    assert partition.replication_factor == 1
    assert partition.per_dc_factor_map == {"dc1": 1}
    assert partition.durable_writes is True


def test_key_value_service_typed_children() -> None:
    svc = RuntimeDatastoreService(**_key_value_service())

    assert isinstance(svc.persistence, RuntimeDatastorePersistence)
    assert svc.persistence.eviction is RuntimeDatastoreEvictionPolicy.NOEVICTION
    assert svc.persistence.aof is False
    assert svc.partitions[0].datatype_census == {"string": 42, "hash": 7}


def test_kebab_case_enum_inputs_normalize() -> None:
    svc = RuntimeDatastoreService(
        **_search_index_service(
            engine="OpenSearch",
            nodes=[{"node_id": "n1", "roles": ["cluster-manager", "data"]}],
        )
    )
    assert svc.engine is RuntimeDatastoreEngine.OPENSEARCH
    assert svc.nodes[0].roles[0] is RuntimeDatastoreNodeRole.CLUSTER_MANAGER


def test_relational_and_open_tail_impose_no_profile() -> None:
    # relational, unknown, other are permissive — a near-empty instance validates.
    for model in ("relational", "unknown", "other"):
        svc = RuntimeDatastoreService(datastore_service_id=f"ds-{model}", data_model=model)
        assert svc.data_model.value == model


def test_variable_ref_data_model_is_exempt_from_guard() -> None:
    svc = RuntimeDatastoreService(datastore_service_id="ds-var", data_model="${DATA_MODEL}")
    assert svc.data_model == "${DATA_MODEL}"


# --------------------------------------------------------------------------- #
# Duplicate-id and secret-redaction guards                                    #
# --------------------------------------------------------------------------- #


def test_rejects_duplicate_stable_ids_across_children() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime datastore stable id 'dup'"):
        RuntimeDatastoreService(
            **_search_index_service(
                nodes=[{"node_id": "dup", "roles": ["data"]}],
                partitions=[
                    {"partition_id": "dup", "kind": "index", "shard_count": 1, "replica_count": 0},
                ],
            )
        )


def test_rejects_duplicate_string_list_entries() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime datastore templates"):
        RuntimeDatastoreService(**_search_index_service(templates=["a", "a"]))


def test_secret_named_setting_may_carry_scenario_value() -> None:
    setting = RuntimeDatastoreSetting(setting_id="admin-pw", name="admin_password", value="hunter2")

    assert setting.value == "hunter2"


def test_secret_named_setting_with_redacted_class_is_valid() -> None:
    setting = RuntimeDatastoreSetting(
        setting_id="admin-pw",
        name="admin_password",
        classification="redacted",
    )
    assert setting.value == ""


def test_redacted_class_must_omit_raw_value() -> None:
    with pytest.raises(ValidationError, match="must omit its raw value"):
        RuntimeDatastoreSetting(setting_id="s1", name="cluster.name", classification="redacted", value="x")


def test_node_rejects_duplicate_roles() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime datastore roles"):
        RuntimeDatastoreNode(node_id="n1", roles=["data", "data"])


# --------------------------------------------------------------------------- #
# require_profile_for_data_model — search_index                               #
# --------------------------------------------------------------------------- #


def test_search_index_requires_index_partition() -> None:
    with pytest.raises(ValidationError, match="requires at least one partition with kind 'index'"):
        RuntimeDatastoreService(**_search_index_service(partitions=[]))


def test_search_index_requires_shard_replica_geometry() -> None:
    with pytest.raises(ValidationError, match="must carry shard_count and replica_count geometry"):
        RuntimeDatastoreService(
            **_search_index_service(partitions=[{"partition_id": "idx", "kind": "index", "shard_count": 3}])
        )


# --------------------------------------------------------------------------- #
# require_profile_for_data_model — key_value                                   #
# --------------------------------------------------------------------------- #


def test_key_value_requires_persistence() -> None:
    with pytest.raises(ValidationError, match="data_model 'key_value' requires a persistence profile"):
        RuntimeDatastoreService(**_key_value_service(persistence=None))


def test_key_value_rejects_relational_partitions() -> None:
    with pytest.raises(ValidationError, match="must not carry .*partitions"):
        RuntimeDatastoreService(
            **_key_value_service(
                partitions=[{"partition_id": "ks", "kind": "keyspace", "name": "x"}],
            )
        )


# --------------------------------------------------------------------------- #
# require_profile_for_data_model — wide_column                                 #
# --------------------------------------------------------------------------- #


def test_wide_column_requires_keyspace_partition() -> None:
    with pytest.raises(ValidationError, match="requires at least one partition with kind 'keyspace'"):
        RuntimeDatastoreService(**_wide_column_service(partitions=[]))


def test_wide_column_requires_replication_strategy_and_factor() -> None:
    with pytest.raises(ValidationError, match="must carry replication_strategy and replication_factor"):
        RuntimeDatastoreService(
            **_wide_column_service(
                partitions=[{"partition_id": "ks", "kind": "keyspace", "name": "thehive"}],
            )
        )


def test_wide_column_rejects_keyspace_missing_factor() -> None:
    with pytest.raises(ValidationError, match="must carry replication_strategy and replication_factor"):
        RuntimeDatastoreService(
            **_wide_column_service(
                partitions=[
                    {
                        "partition_id": "ks",
                        "kind": "keyspace",
                        "replication_strategy": "simple_strategy",
                    }
                ],
            )
        )


# --------------------------------------------------------------------------- #
# DSL-141 — node engine provenance, heap posture, plugins, endpoints          #
# --------------------------------------------------------------------------- #


def test_node_provenance_defaults_are_empty() -> None:
    node = RuntimeDatastoreNode(node_id="n1")
    assert node.engine_version == ""
    assert node.build_hash == ""
    assert node.build_type == ""
    assert node.heap_init_bytes is None
    assert node.heap_max_bytes is None
    assert node.memory_locked is None
    assert node.endpoints == []
    assert node.plugins == []


def test_node_heap_bytes_accept_human_int_and_var() -> None:
    node = RuntimeDatastoreNode(node_id="n1", heap_init_bytes="512 MiB", heap_max_bytes=1_073_741_824)
    assert node.heap_init_bytes == 536_870_912
    assert node.heap_max_bytes == 1_073_741_824

    var_node = RuntimeDatastoreNode(node_id="n2", heap_max_bytes="${HEAP}")
    assert var_node.heap_max_bytes == "${HEAP}"


def test_node_rejects_heap_init_above_max() -> None:
    with pytest.raises(ValidationError, match="heap_init_bytes.*heap_max_bytes"):
        RuntimeDatastoreNode(node_id="n1", heap_init_bytes="2 GiB", heap_max_bytes="1 GiB")


def test_node_heap_ordering_exempt_for_variable_bounds() -> None:
    node = RuntimeDatastoreNode(node_id="n1", heap_init_bytes="${INIT}", heap_max_bytes=1024)
    assert node.heap_init_bytes == "${INIT}"


def test_node_memory_locked_parses_bool_and_var() -> None:
    assert RuntimeDatastoreNode(node_id="n1", memory_locked="true").memory_locked is True
    assert RuntimeDatastoreNode(node_id="n2", memory_locked="${MLOCK}").memory_locked == "${MLOCK}"


def test_engine_plugin_retains_per_plugin_version() -> None:
    plugin = RuntimeDatastoreEnginePlugin(
        plugin_id="opensearch-security", name="opensearch-security", version="2.19.1.0"
    )
    assert plugin.plugin_id == "opensearch-security"
    assert plugin.version == "2.19.1.0"


def test_engine_plugin_id_must_be_stable_symbol() -> None:
    with pytest.raises(ValidationError, match="plugin_id"):
        RuntimeDatastoreEnginePlugin(plugin_id="${PLUGIN}", name="x")
    with pytest.raises(ValidationError, match="plugin_id"):
        RuntimeDatastoreEnginePlugin(plugin_id="", name="x")


def test_node_endpoint_typed_fields() -> None:
    endpoint = RuntimeDatastoreNodeEndpoint(
        endpoint_id="http", role="client", protocol="https", address="172.20.0.12", port=9200
    )
    assert endpoint.role is RuntimeDatastoreNodeEndpointRole.CLIENT
    assert endpoint.address == "172.20.0.12"
    assert endpoint.port == 9200


def test_endpoint_role_normalizes_hyphen_alias_and_open_sentinels() -> None:
    assert RuntimeDatastoreNodeEndpointRole.UNKNOWN.value == "unknown"
    assert RuntimeDatastoreNodeEndpointRole.OTHER.value == "other"
    endpoint = RuntimeDatastoreNodeEndpoint(endpoint_id="e1", role="PEER")
    assert endpoint.role is RuntimeDatastoreNodeEndpointRole.PEER


def test_endpoint_role_rejects_unrecognized_value() -> None:
    # An unrecognized (non-var) role must raise with the closed-set error
    # envelope, never silently pass through as an arbitrary string.
    with pytest.raises(ValidationError, match="role must be one of: client, peer, unknown, other"):
        RuntimeDatastoreNodeEndpoint(endpoint_id="e1", role="gossip")


def test_endpoint_id_must_be_stable_symbol() -> None:
    with pytest.raises(ValidationError, match="endpoint_id"):
        RuntimeDatastoreNodeEndpoint(endpoint_id="${E}")


def test_endpoint_port_range_enforced() -> None:
    # Both bounds: above the 65535 ceiling and below the minimum of 1.
    with pytest.raises(ValidationError, match="port"):
        RuntimeDatastoreNodeEndpoint(endpoint_id="e1", port=70000)
    with pytest.raises(ValidationError, match="port"):
        RuntimeDatastoreNodeEndpoint(endpoint_id="e1", port=0)


def test_node_rejects_duplicate_plugin_ids() -> None:
    with pytest.raises(ValidationError, match="plugin"):
        RuntimeDatastoreNode(
            node_id="n1",
            plugins=[{"plugin_id": "dup", "name": "a"}, {"plugin_id": "dup", "name": "b"}],
        )


def test_node_rejects_duplicate_endpoint_ids() -> None:
    with pytest.raises(ValidationError, match="endpoint"):
        RuntimeDatastoreNode(
            node_id="n1",
            endpoints=[{"endpoint_id": "dup"}, {"endpoint_id": "dup"}],
        )


def test_service_wide_id_namespace_includes_plugin_and_endpoint_ids() -> None:
    # A plugin id colliding with the node id is a service-wide stable-id clash.
    with pytest.raises(ValidationError, match="Duplicate runtime datastore stable id 'indexer-1'"):
        RuntimeDatastoreService(
            **_search_index_service(
                nodes=[
                    {
                        "node_id": "indexer-1",
                        "roles": ["data"],
                        "plugins": [{"plugin_id": "indexer-1", "name": "x"}],
                    }
                ]
            )
        )


def test_endpoint_id_collision_with_partition_is_service_wide() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime datastore stable id 'wazuh-alerts'"):
        RuntimeDatastoreService(
            **_search_index_service(
                nodes=[
                    {
                        "node_id": "indexer-1",
                        "roles": ["data"],
                        "endpoints": [{"endpoint_id": "wazuh-alerts"}],
                    }
                ]
            )
        )


def test_same_plugin_id_on_two_nodes_is_rejected_service_wide() -> None:
    # The service-wide namespace spans ALL nodes: the same plugin_id appearing
    # on two distinct nodes is a collision the per-node check cannot catch. A
    # service-scoped check that only deduped within each node would pass this.
    with pytest.raises(ValidationError, match="Duplicate runtime datastore stable id 'opensearch-security'"):
        RuntimeDatastoreService(
            **_search_index_service(
                nodes=[
                    {
                        "node_id": "indexer-1",
                        "roles": ["cluster_manager", "data"],
                        "plugins": [{"plugin_id": "opensearch-security", "name": "x"}],
                    },
                    {
                        "node_id": "indexer-2",
                        "roles": ["data"],
                        "plugins": [{"plugin_id": "opensearch-security", "name": "y"}],
                    },
                ]
            )
        )


def test_same_endpoint_id_on_two_nodes_is_rejected_service_wide() -> None:
    # Same cross-node obligation for endpoint ids: the same endpoint_id on two
    # distinct nodes collides in the service-wide stable-id namespace.
    with pytest.raises(ValidationError, match="Duplicate runtime datastore stable id 'transport'"):
        RuntimeDatastoreService(
            **_search_index_service(
                nodes=[
                    {
                        "node_id": "indexer-1",
                        "roles": ["cluster_manager", "data"],
                        "endpoints": [{"endpoint_id": "transport", "role": "peer"}],
                    },
                    {
                        "node_id": "indexer-2",
                        "roles": ["data"],
                        "endpoints": [{"endpoint_id": "transport", "role": "peer"}],
                    },
                ]
            )
        )


def test_removed_node_address_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="address"):
        RuntimeDatastoreNode(node_id="n1", address="172.20.0.12")


def test_removed_service_engine_plugins_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="engine_plugins"):
        RuntimeDatastoreService(**_search_index_service(engine_plugins=["opensearch-security"]))
