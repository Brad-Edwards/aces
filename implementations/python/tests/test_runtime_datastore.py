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
    RuntimeDatastoreNode,
    RuntimeDatastorePartitionKind,
    RuntimeDatastorePersistence,
    RuntimeDatastoreService,
    RuntimeDatastoreSetting,
    RuntimeDatastoreTransportSecurity,
)
from aces_sdl.runtime_datastore_vocab import (
    RuntimeDatastoreEvictionPolicy,
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
        "engine_plugins": ["opensearch-security", "opensearch-alerting"],
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
    assert svc.nodes[0].roles[0] is RuntimeDatastoreNodeRole.CLUSTER_MANAGER
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
    with pytest.raises(ValidationError, match="Duplicate runtime datastore engine_plugins"):
        RuntimeDatastoreService(**_search_index_service(engine_plugins=["a", "a"]))


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
