"""Runtime datastore-service (SCN-010 §5.1) SDL surface tests.

Covers the OPEN ``data_model`` discriminator spine, the typed cluster / node /
partition / persistence / transport-security / setting children, secret-bearing
setting redaction, duplicate-id rejection, and — the core correctness feature —
the ``require_profile_for_data_model`` guard (positive for each model plus each
REQUIRE / REJECT negative).
"""

from __future__ import annotations

import json

import pytest
from aces_sdl._runtime_service_families import collect_qualified_runtime_family_refs
from aces_sdl.runtime_datastore import (
    RuntimeDatastoreCluster,
    RuntimeDatastoreDataModel,
    RuntimeDatastoreEngine,
    RuntimeDatastoreMapping,
    RuntimeDatastoreNode,
    RuntimeDatastorePartitionKind,
    RuntimeDatastorePersistence,
    RuntimeDatastoreService,
    RuntimeDatastoreSetting,
    RuntimeDatastoreTemplate,
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
from paths import REPO_ROOT
from pydantic import ValidationError

from aces.core.sdl.scenario import Scenario

_PUBLISHED_SDL_SCHEMA_NAMES = ("instantiated-scenario-v1", "sdl-authoring-input-v1")
_DATASTORE_MAPPING_SCHEMA_FIELDS = {
    "date_detection",
    "description",
    "dynamic_policy",
    "dynamic_template_count",
    "evidence_refs",
    "field_type_census",
    "leaf_field_count",
    "mapping_id",
    "name",
    "partition_ref",
    "schema_digest",
    "top_level_field_count",
}
_DATASTORE_TEMPLATE_SCHEMA_FIELDS = {
    "description",
    "evidence_refs",
    "index_patterns",
    "mapping_ref",
    "name",
    "settings_summary",
    "template_digest",
    "template_id",
}


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
        "templates": [
            {
                "template_id": "wazuh-template",
                "name": "wazuh",
                "index_patterns": ["wazuh-alerts-4.x-*", "wazuh-archives-4.x-*"],
                "settings_summary": {
                    "index.number_of_shards": "3",
                    "index.number_of_replicas": "0",
                    "index.refresh_interval": "5s",
                },
                "mapping_ref": "wazuh-alerts-mapping",
                "template_digest": "sha256:wazuh-template",
                "evidence_refs": ["docs/aces/inventory/wazuh.indexer/evidence/wazuh-indexer-templates.json.gz"],
            }
        ],
        "aliases": ["wazuh-alerts"],
        "mappings": [
            {
                "mapping_id": "wazuh-alerts-mapping",
                "partition_ref": "wazuh-alerts",
                "name": "wazuh-alerts-4.x-*",
                "top_level_field_count": 25,
                "leaf_field_count": 670,
                "field_type_census": {"keyword": 220, "date": 9, "ip": 12, "object": 70},
                "dynamic_policy": "true",
                "dynamic_template_count": 5,
                "date_detection": True,
                "schema_digest": "sha256:wazuh-alerts-mapping",
                "evidence_refs": ["docs/aces/inventory/wazuh.indexer/evidence/wazuh-indexer-family-mappings.json.gz"],
            }
        ],
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
    assert isinstance(svc.mappings[0], RuntimeDatastoreMapping)
    assert svc.mappings[0].top_level_field_count == 25
    assert svc.mappings[0].leaf_field_count == 670
    assert svc.mappings[0].partition_ref == "wazuh-alerts"
    assert svc.mappings[0].field_type_census["keyword"] == 220
    assert svc.mappings[0].dynamic_policy == "true"
    assert svc.mappings[0].dynamic_template_count == 5
    assert svc.mappings[0].date_detection is True
    assert svc.mappings[0].schema_digest == "sha256:wazuh-alerts-mapping"
    assert svc.mappings[0].evidence_refs == [
        "docs/aces/inventory/wazuh.indexer/evidence/wazuh-indexer-family-mappings.json.gz"
    ]
    assert isinstance(svc.templates[0], RuntimeDatastoreTemplate)
    assert svc.templates[0].index_patterns == ["wazuh-alerts-4.x-*", "wazuh-archives-4.x-*"]
    assert svc.templates[0].settings_summary == {
        "index.number_of_shards": "3",
        "index.number_of_replicas": "0",
        "index.refresh_interval": "5s",
    }
    assert svc.templates[0].mapping_ref == "wazuh-alerts-mapping"
    assert svc.templates[0].template_digest == "sha256:wazuh-template"
    assert svc.templates[0].evidence_refs == [
        "docs/aces/inventory/wazuh.indexer/evidence/wazuh-indexer-templates.json.gz"
    ]
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


def test_legacy_string_template_mapping_inputs_coerce_to_typed_manifests() -> None:
    svc = RuntimeDatastoreService(
        **_search_index_service(
            templates=["legacy-template"],
            mappings=["legacy-mapping"],
        )
    )

    assert svc.templates[0].template_id == "legacy-template"
    assert svc.templates[0].name == "legacy-template"
    assert svc.mappings[0].mapping_id == "legacy-mapping"
    assert svc.mappings[0].name == "legacy-mapping"

    single = RuntimeDatastoreService(
        **_search_index_service(
            templates="single-template",
            mappings="single-mapping",
        )
    )
    assert single.templates[0].template_id == "single-template"
    assert single.mappings[0].mapping_id == "single-mapping"


def test_relational_and_open_tail_impose_no_profile() -> None:
    # relational, unknown, other are permissive — a near-empty instance validates.
    for model in ("relational", "unknown", "other"):
        svc = RuntimeDatastoreService(datastore_service_id=f"ds-{model}", data_model=model)
        assert svc.data_model.value == model


def test_variable_ref_data_model_is_exempt_from_guard() -> None:
    svc = RuntimeDatastoreService(datastore_service_id="ds-var", data_model="${DATA_MODEL}")
    assert svc.data_model == "${DATA_MODEL}"


def test_variable_refs_for_mapping_and_template_links_are_exempt_from_resolution_guard() -> None:
    svc = RuntimeDatastoreService(
        **_search_index_service(
            mappings=[
                {
                    "mapping_id": "deferred-mapping",
                    "partition_ref": "${PARTITION_ID}",
                    "top_level_field_count": 1,
                    "leaf_field_count": 1,
                }
            ],
            templates=[
                {
                    "template_id": "deferred-template",
                    "mapping_ref": "${MAPPING_ID}",
                    "index_patterns": ["wazuh-*"],
                }
            ],
        )
    )

    assert svc.mappings[0].partition_ref == "${PARTITION_ID}"
    assert svc.templates[0].mapping_ref == "${MAPPING_ID}"


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


def test_rejects_duplicate_mapping_and_template_ids() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime datastore stable id 'dup'"):
        RuntimeDatastoreService(
            **_search_index_service(
                mappings=[
                    {"mapping_id": "dup", "partition_ref": "wazuh-alerts"},
                    {"mapping_id": "dup", "partition_ref": "wazuh-alerts"},
                ],
            )
        )

    with pytest.raises(ValidationError, match="Duplicate runtime datastore stable id 'dup'"):
        RuntimeDatastoreService(
            **_search_index_service(
                templates=[
                    {"template_id": "dup", "mapping_ref": "wazuh-alerts-mapping"},
                    {"template_id": "dup", "mapping_ref": "wazuh-alerts-mapping"},
                ],
            )
        )


def test_mapping_and_template_reject_duplicate_local_lists() -> None:
    with pytest.raises(ValidationError, match="Duplicate runtime datastore evidence_refs"):
        RuntimeDatastoreMapping(mapping_id="mapping", evidence_refs=["e1", "e1"])

    with pytest.raises(ValidationError, match="Duplicate runtime datastore index_patterns"):
        RuntimeDatastoreTemplate(template_id="template", index_patterns=["wazuh-*", "wazuh-*"])


def test_mapping_and_template_ids_reject_variable_placeholders() -> None:
    with pytest.raises(ValidationError, match="mapping_id must be a stable identifier"):
        RuntimeDatastoreMapping(mapping_id="${MAPPING_ID}")

    with pytest.raises(ValidationError, match="template_id must be a stable identifier"):
        RuntimeDatastoreTemplate(template_id="${TEMPLATE_ID}")


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


def test_search_index_requires_mapping_manifest() -> None:
    with pytest.raises(ValidationError, match="requires at least one structured mapping manifest"):
        RuntimeDatastoreService(**_search_index_service(mappings=[]))


def test_mapping_partition_ref_must_resolve() -> None:
    with pytest.raises(ValidationError, match="mapping 'orphan' partition_ref 'missing-index' does not resolve"):
        RuntimeDatastoreService(
            **_search_index_service(
                mappings=[{"mapping_id": "orphan", "partition_ref": "missing-index"}],
            )
        )


def test_template_mapping_ref_must_resolve() -> None:
    with pytest.raises(
        ValidationError, match="template 'orphan-template' mapping_ref 'missing-mapping' does not resolve"
    ):
        RuntimeDatastoreService(
            **_search_index_service(
                templates=[{"template_id": "orphan-template", "mapping_ref": "missing-mapping"}],
            )
        )


def test_mapping_and_template_refs_are_targetable() -> None:
    scenario = Scenario(
        name="datastore-refs",
        nodes={
            "indexer": {
                "type": "vm",
                "runtime": {"datastore_services": [_search_index_service()]},
            }
        },
    )

    refs = collect_qualified_runtime_family_refs(scenario, family_keys={"datastore-services"})

    assert "nodes.indexer.runtime.datastore_services.wazuh-indexer.mappings.wazuh-alerts-mapping" in refs
    assert "nodes.indexer.runtime.datastore_services.wazuh-indexer.templates.wazuh-template" in refs


def test_published_sdl_schemas_include_mapping_and_template_manifests() -> None:
    for schema_name in _PUBLISHED_SDL_SCHEMA_NAMES:
        schema_path = REPO_ROOT / "contracts" / "schemas" / "sdl" / f"{schema_name}.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        defs = schema["$defs"]
        service_properties = defs["RuntimeDatastoreService"]["properties"]

        assert service_properties["mappings"]["items"]["$ref"] == "#/$defs/RuntimeDatastoreMapping"
        assert service_properties["templates"]["items"]["$ref"] == "#/$defs/RuntimeDatastoreTemplate"

        mapping_schema = defs["RuntimeDatastoreMapping"]
        assert mapping_schema["additionalProperties"] is False
        assert set(mapping_schema["properties"]) == _DATASTORE_MAPPING_SCHEMA_FIELDS
        assert mapping_schema["required"] == ["mapping_id"]
        assert mapping_schema["properties"]["field_type_census"]["additionalProperties"]["anyOf"] == [
            {"type": "integer"},
            {"type": "string"},
        ]
        assert mapping_schema["properties"]["date_detection"]["anyOf"] == [
            {"type": "boolean"},
            {"type": "string"},
            {"type": "null"},
        ]

        template_schema = defs["RuntimeDatastoreTemplate"]
        assert template_schema["additionalProperties"] is False
        assert set(template_schema["properties"]) == _DATASTORE_TEMPLATE_SCHEMA_FIELDS
        assert template_schema["required"] == ["template_id"]
        assert template_schema["properties"]["settings_summary"]["additionalProperties"]["anyOf"] == [
            {"type": "string"},
            {"type": "integer"},
            {"type": "boolean"},
        ]


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
