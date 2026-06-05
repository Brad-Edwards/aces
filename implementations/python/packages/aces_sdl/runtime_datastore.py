"""Observed datastore logical-state runtime inventory models for SDL nodes.

This family (SCN-010 §5.1) types the participant-observable logical state of a
node's *non-relational* (and, via the open discriminator, relational) datastore
service: a single spine, :class:`RuntimeDatastoreService`, differentiated by an
OPEN ``data_model`` discriminator (``search_index`` / ``wide_column`` /
``key_value`` / ``relational`` / ``unknown`` / ``other``). It covers the
OpenSearch/Elasticsearch search clusters, the Cassandra wide-column store, and
the Redis key-value store that ``runtime.database_services`` (irreducibly
relational) cannot shape.

The spine is guarded by a ``require_profile_for_data_model`` after-validator so
an under-populated instance FAILS validation — the abstraction provably cannot
silently shallow-encode a defining datastore fact (a search cluster with no
shard/replica geometry, a wide-column store with no replication factor, a
key-value store with no persistence posture).

This is observed runtime state attached to ``Node.runtime``. ``service``
references the owning same-node transport listener; it never mutates that
surface. Application-internal RBAC is delegated to ``runtime.app_authorization``
via ``authorization_ref`` (a string ``app_authorization_id`` resolved by the
semantic validator) — this surface carries no embedded principal/role/grant.
"""

from enum import Enum

from pydantic import Field, field_validator, model_validator

from ._base import SDLModel, is_variable_ref
from .runtime_datastore_partitions import (
    RuntimeDatastoreCluster,
    RuntimeDatastoreNode,
    RuntimeDatastorePartition,
    RuntimeDatastorePersistence,
    RuntimeDatastoreSetting,
    RuntimeDatastoreTransportSecurity,
)
from .runtime_datastore_vocab import (
    RuntimeDatastoreDataModel,
    RuntimeDatastoreEngine,
    RuntimeDatastoreEvictionPolicy,
    RuntimeDatastoreNodeRole,
    RuntimeDatastorePartitionKind,
    RuntimeDatastoreReplicationStrategy,
    RuntimeDatastoreSettingProvenance,
    RuntimeDatastoreSettingScope,
    RuntimeDatastoreTransportSecurityMode,
)
from .runtime_values import (
    coerce_string_list,
    parse_runtime_enum_or_var,
    require_symbol,
)

__all__ = [
    "RuntimeDatastoreCluster",
    "RuntimeDatastoreDataModel",
    "RuntimeDatastoreEngine",
    "RuntimeDatastoreEvictionPolicy",
    "RuntimeDatastoreNode",
    "RuntimeDatastoreNodeRole",
    "RuntimeDatastorePartition",
    "RuntimeDatastorePartitionKind",
    "RuntimeDatastorePersistence",
    "RuntimeDatastoreReplicationStrategy",
    "RuntimeDatastoreService",
    "RuntimeDatastoreSetting",
    "RuntimeDatastoreSettingProvenance",
    "RuntimeDatastoreSettingScope",
    "RuntimeDatastoreTransportSecurity",
    "RuntimeDatastoreTransportSecurityMode",
]


def _normalize_enum(value: object, enum_cls: type[Enum], *, field_name: str) -> object:
    return parse_runtime_enum_or_var(value, enum_cls, field_name=field_name)


def _coerce_refs(value: object) -> object:
    return coerce_string_list(value)


class RuntimeDatastoreService(SDLModel):
    """An observed datastore service hosted by a transport service on a node.

    The single non-relational datastore spine. ``service`` references the owning
    same-node ``Node.services[].name`` (bare name or the qualified
    ``nodes.<node>.services.<name>`` form). The ``data_model`` discriminator
    selects the required profile the ``require_profile_for_data_model`` guard
    enforces.
    """

    datastore_service_id: str
    service: str = ""
    engine: RuntimeDatastoreEngine | str = RuntimeDatastoreEngine.UNKNOWN
    data_model: RuntimeDatastoreDataModel | str = RuntimeDatastoreDataModel.UNKNOWN
    protocol: str = ""
    version: str = ""
    name: str = ""
    cluster: RuntimeDatastoreCluster | None = None
    nodes: list[RuntimeDatastoreNode] = Field(default_factory=list)
    partitions: list[RuntimeDatastorePartition] = Field(default_factory=list)
    templates: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    mappings: list[str] = Field(default_factory=list)
    lifecycle_policies: list[str] = Field(default_factory=list)
    ingest_pipelines: list[str] = Field(default_factory=list)
    persistence: RuntimeDatastorePersistence | None = None
    pubsub_channels: list[str] = Field(default_factory=list)
    queues_streams: list[str] = Field(default_factory=list)
    engine_plugins: list[str] = Field(default_factory=list)
    transport_security: RuntimeDatastoreTransportSecurity | None = None
    backup_targets: list[str] = Field(default_factory=list)
    settings: list[RuntimeDatastoreSetting] = Field(default_factory=list)
    authorization_ref: str = ""
    description: str = ""

    @field_validator("datastore_service_id")
    @classmethod
    def validate_datastore_service_id(cls, v: str) -> str:
        return require_symbol(v, field_name="datastore_service_id")

    @field_validator("engine", mode="before")
    @classmethod
    def normalize_engine(cls, v: RuntimeDatastoreEngine | str) -> object:
        return _normalize_enum(v, RuntimeDatastoreEngine, field_name="engine")

    @field_validator("data_model", mode="before")
    @classmethod
    def normalize_data_model(cls, v: RuntimeDatastoreDataModel | str) -> object:
        return _normalize_enum(v, RuntimeDatastoreDataModel, field_name="data_model")

    @field_validator(
        "templates",
        "aliases",
        "mappings",
        "lifecycle_policies",
        "ingest_pipelines",
        "pubsub_channels",
        "queues_streams",
        "engine_plugins",
        "backup_targets",
        mode="before",
    )
    @classmethod
    def coerce_string_lists(cls, v: object) -> object:
        return _coerce_refs(v)

    @model_validator(mode="after")
    def validate_datastore_service(self) -> "RuntimeDatastoreService":
        self._reject_duplicate_string_lists()
        _reject_duplicate_local_ref_ids(self)
        self.require_profile_for_data_model()
        return self

    def _reject_duplicate_string_lists(self) -> None:
        for field_name in (
            "templates",
            "aliases",
            "mappings",
            "lifecycle_policies",
            "ingest_pipelines",
            "pubsub_channels",
            "queues_streams",
            "engine_plugins",
            "backup_targets",
        ):
            _reject_duplicate_values(getattr(self, field_name), field_name=field_name, owner=self.datastore_service_id)

    def require_profile_for_data_model(self) -> None:
        """Fail validation when the declared ``data_model`` lacks its profile.

        A ``${var}`` placeholder discriminator is exempt (nothing concrete is
        asserted); the OPEN ``unknown`` / ``other`` sentinels impose no profile
        (permissive tail). Each concrete structural data model REQUIRES (and in
        some cases REJECTS) specific child state per SCN-010 §5.1.
        """
        model = self.data_model
        if is_variable_ref(model) or not isinstance(model, RuntimeDatastoreDataModel):
            return
        if model is RuntimeDatastoreDataModel.SEARCH_INDEX:
            self._require_search_index_profile()
        elif model is RuntimeDatastoreDataModel.KEY_VALUE:
            self._require_key_value_profile()
        elif model is RuntimeDatastoreDataModel.WIDE_COLUMN:
            self._require_wide_column_profile()
        # RELATIONAL / UNKNOWN / OTHER impose no profile here: a relational store
        # belongs to ``runtime.database_services`` (the named confirmation-fold),
        # and the open tail is permissive by the enum-sentinel discipline.

    def _index_partitions(self) -> list[RuntimeDatastorePartition]:
        return [p for p in self.partitions if p.kind is RuntimeDatastorePartitionKind.INDEX]

    def _keyspace_partitions(self) -> list[RuntimeDatastorePartition]:
        return [p for p in self.partitions if p.kind is RuntimeDatastorePartitionKind.KEYSPACE]

    def _require_search_index_profile(self) -> None:
        index_partitions = self._index_partitions()
        if not index_partitions:
            raise ValueError(
                f"datastore service '{self.datastore_service_id}' data_model 'search_index' "
                f"requires at least one partition with kind 'index'"
            )
        for partition in index_partitions:
            if partition.shard_count is None or partition.replica_count is None:
                raise ValueError(
                    f"datastore service '{self.datastore_service_id}' search_index partition "
                    f"'{partition.partition_id}' must carry shard_count and replica_count geometry"
                )

    def _require_key_value_profile(self) -> None:
        if self.persistence is None:
            raise ValueError(
                f"datastore service '{self.datastore_service_id}' data_model 'key_value' requires a persistence profile"
            )
        # A key-value store must not carry the relational object tree — that is
        # the shallow encoding the guard exists to forbid (Redis-as-relational).
        relational_partitions = [
            p
            for p in self.partitions
            if p.kind in (RuntimeDatastorePartitionKind.KEYSPACE, RuntimeDatastorePartitionKind.COLUMN_FAMILY)
        ]
        if relational_partitions:
            offending = relational_partitions[0]
            raise ValueError(
                f"datastore service '{self.datastore_service_id}' data_model 'key_value' must not carry "
                f"relational/wide-column partitions (partition '{offending.partition_id}')"
            )

    def _require_wide_column_profile(self) -> None:
        keyspaces = self._keyspace_partitions()
        if not keyspaces:
            raise ValueError(
                f"datastore service '{self.datastore_service_id}' data_model 'wide_column' "
                f"requires at least one partition with kind 'keyspace'"
            )
        for partition in keyspaces:
            if not self._has_concrete_replication(partition) or partition.replication_factor is None:
                raise ValueError(
                    f"datastore service '{self.datastore_service_id}' wide_column keyspace "
                    f"'{partition.partition_id}' must carry replication_strategy and replication_factor"
                )

    @staticmethod
    def _has_concrete_replication(partition: RuntimeDatastorePartition) -> bool:
        """Return whether a keyspace declares a non-``unknown`` replication strategy.

        A ``${var}`` placeholder strategy is treated as concrete-deferred (the
        author asserted a strategy, resolved at instantiation); only the OPEN
        ``unknown`` sentinel counts as an absent profile.
        """
        strategy = partition.replication_strategy
        if is_variable_ref(strategy):
            return True
        if isinstance(strategy, RuntimeDatastoreReplicationStrategy):
            return strategy is not RuntimeDatastoreReplicationStrategy.UNKNOWN
        return False


def _reject_duplicate_values(values: list[object], *, field_name: str, owner: str) -> None:
    seen: set[object] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate runtime datastore {field_name} entry on '{owner}'")
        seen.add(value)


def _reject_duplicate_local_ref_ids(service: RuntimeDatastoreService) -> None:
    entries: list[tuple[str, str]] = [("datastore_service_id", service.datastore_service_id)]
    if service.cluster is not None:
        entries.append(("cluster_id", service.cluster.cluster_id))
    if service.persistence is not None:
        entries.append(("persistence_id", service.persistence.persistence_id))
    if service.transport_security is not None:
        entries.append(("transport_security_id", service.transport_security.transport_security_id))
    for label, collection_name in (
        ("node_id", "nodes"),
        ("partition_id", "partitions"),
        ("setting_id", "settings"),
    ):
        entries.extend((label, getattr(item, label)) for item in getattr(service, collection_name))

    seen: dict[str, str] = {}
    for label, value in entries:
        prior = seen.get(value)
        if prior is not None:
            raise ValueError(
                f"Duplicate runtime datastore stable id '{value}' in service "
                f"'{service.datastore_service_id}' across {prior} and {label}"
            )
        seen[value] = label
