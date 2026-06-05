"""Cluster, node, partition, persistence, and setting child models for the
``runtime.datastore_services`` family (SCN-010 §5.1).

Split out of ``runtime_datastore.py`` so no single source file exceeds the
ADR-015 600-line cap. These typed children compose into
:class:`~aces_sdl.runtime_datastore.RuntimeDatastoreService`; the top spine and
its ``require_profile_for_data_model`` guard live in ``runtime_datastore.py``.

Every typed child carries a ``<child_noun>_id`` validated by ``require_symbol``.
Settings whose name signals secret content omit their raw value and classify
``redacted`` / ``operator_secret`` via the shared ``name_indicates_secret``
helper, exactly as the relational ``DatabaseSetting`` does.
"""

from enum import Enum

from pydantic import Field, ValidationInfo, field_validator, model_validator

from ._base import SDLModel, is_variable_ref, parse_int_or_var
from .runtime_datastore_vocab import (
    RuntimeDatastoreEvictionPolicy,
    RuntimeDatastoreNodeRole,
    RuntimeDatastorePartitionKind,
    RuntimeDatastoreReplicationStrategy,
    RuntimeDatastoreSettingProvenance,
    RuntimeDatastoreSettingScope,
    RuntimeDatastoreTransportSecurityMode,
)
from .runtime_filesystem import RuntimeSensitivityClassification
from .runtime_values import (
    coerce_string_list,
    name_indicates_secret,
    parse_optional_bool_or_var,
    parse_runtime_enum_or_var,
    require_symbol,
)

__all__ = [
    "RuntimeDatastoreCluster",
    "RuntimeDatastoreNode",
    "RuntimeDatastorePartition",
    "RuntimeDatastorePersistence",
    "RuntimeDatastoreSetting",
    "RuntimeDatastoreTransportSecurity",
]

# Sensitivity classes whose raw value must never be recorded.
_REDACTED_SENSITIVITIES = frozenset(
    {RuntimeSensitivityClassification.REDACTED, RuntimeSensitivityClassification.OPERATOR_SECRET}
)


def _normalize_enum(value: object, enum_cls: type[Enum], *, field_name: str) -> object:
    return parse_runtime_enum_or_var(value, enum_cls, field_name=field_name)


def _coerce_refs(value: object) -> object:
    return coerce_string_list(value)


def _reject_duplicate_values(values: list[object], *, field_name: str, owner: str) -> None:
    seen: set[object] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate runtime datastore {field_name} entry on '{owner}'")
        seen.add(value)


def _require_object_name(value: str, *, field_name: str) -> str:
    """Validate an observed object name: non-empty, ``${var}`` allowed."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _setting_name_is_concrete_secret(name: object) -> bool:
    """Return whether ``name`` is a concrete (non-``${var}``) secret-bearing label."""
    return isinstance(name, str) and not is_variable_ref(name) and name_indicates_secret(name)


class RuntimeDatastoreNode(SDLModel):
    """An observed node participating in a datastore cluster."""

    node_id: str
    name: str = ""
    roles: list[RuntimeDatastoreNodeRole | str] = Field(default_factory=list)
    is_coordinator: bool | str | None = None
    address: str = ""
    description: str = ""

    @field_validator("node_id")
    @classmethod
    def validate_node_id(cls, v: str) -> str:
        return require_symbol(v, field_name="node_id")

    @field_validator("roles", mode="before")
    @classmethod
    def normalize_roles(cls, v: object) -> object:
        values = _coerce_refs(v)
        if isinstance(values, list):
            return [_normalize_enum(item, RuntimeDatastoreNodeRole, field_name="roles") for item in values]
        return values

    @field_validator("is_coordinator", mode="before")
    @classmethod
    def parse_is_coordinator(cls, v: object) -> bool | str | None:
        return parse_optional_bool_or_var(v, field_name="is_coordinator")

    @model_validator(mode="after")
    def validate_node(self) -> "RuntimeDatastoreNode":
        _reject_duplicate_values(self.roles, field_name="roles", owner=self.node_id)
        return self


class RuntimeDatastoreCluster(SDLModel):
    """The single observed cluster posture of a datastore service.

    Captures the cluster-identity facts a search/wide-column cluster exposes:
    health, discovery mode, partitioner, and native protocol version.
    """

    cluster_id: str
    name: str = ""
    health: str = ""
    discovery_mode: str = ""
    partitioner: str = ""
    native_protocol_version: str = ""
    description: str = ""

    @field_validator("cluster_id")
    @classmethod
    def validate_cluster_id(cls, v: str) -> str:
        return require_symbol(v, field_name="cluster_id")


class RuntimeDatastorePartition(SDLModel):
    """An observed partition primitive (index / keyspace / logical_db / family).

    Carries the geometry that differentiates one datastore data model from
    another: shard/replica counts for a search index, replication strategy +
    factor + per-DC factor map for a wide-column keyspace, and a datatype census
    for a key-value logical database.
    """

    partition_id: str
    kind: RuntimeDatastorePartitionKind | str = RuntimeDatastorePartitionKind.UNKNOWN
    name: str = ""
    shard_count: int | str | None = None
    replica_count: int | str | None = None
    replication_strategy: RuntimeDatastoreReplicationStrategy | str = RuntimeDatastoreReplicationStrategy.UNKNOWN
    replication_factor: int | str | None = None
    per_dc_factor_map: dict[str, int | str] = Field(default_factory=dict)
    durable_writes: bool | str | None = None
    datatype_census: dict[str, int | str] = Field(default_factory=dict)
    health: str = ""
    description: str = ""

    @field_validator("partition_id")
    @classmethod
    def validate_partition_id(cls, v: str) -> str:
        return require_symbol(v, field_name="partition_id")

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, v: RuntimeDatastorePartitionKind | str) -> object:
        return _normalize_enum(v, RuntimeDatastorePartitionKind, field_name="kind")

    @field_validator("replication_strategy", mode="before")
    @classmethod
    def normalize_replication_strategy(cls, v: RuntimeDatastoreReplicationStrategy | str) -> object:
        return _normalize_enum(v, RuntimeDatastoreReplicationStrategy, field_name="replication_strategy")

    @field_validator("shard_count", "replica_count", "replication_factor", mode="before")
    @classmethod
    def parse_counts(cls, v: object, info: ValidationInfo) -> int | str | None:
        return parse_int_or_var(v, minimum=0, field_name=info.field_name) if v is not None else v

    @field_validator("durable_writes", mode="before")
    @classmethod
    def parse_durable_writes(cls, v: object) -> bool | str | None:
        return parse_optional_bool_or_var(v, field_name="durable_writes")

    @field_validator("per_dc_factor_map", "datatype_census", mode="before")
    @classmethod
    def parse_int_maps(cls, v: object, info: ValidationInfo) -> object:
        if not isinstance(v, dict):
            return v
        return {key: parse_int_or_var(value, minimum=0, field_name=info.field_name) for key, value in v.items()}


class RuntimeDatastorePersistence(SDLModel):
    """The single observed persistence posture of a key-value datastore.

    Captures Redis-style persistence: RDB save points, AOF on/off, the eviction
    policy, and the maxmemory ceiling. Its presence is the defining profile a
    ``key_value`` data model must carry.
    """

    persistence_id: str
    rdb_save_points: list[str] = Field(default_factory=list)
    aof: bool | str | None = None
    eviction: RuntimeDatastoreEvictionPolicy | str = RuntimeDatastoreEvictionPolicy.UNKNOWN
    maxmemory: str = ""
    description: str = ""

    @field_validator("persistence_id")
    @classmethod
    def validate_persistence_id(cls, v: str) -> str:
        return require_symbol(v, field_name="persistence_id")

    @field_validator("rdb_save_points", mode="before")
    @classmethod
    def coerce_save_points(cls, v: object) -> object:
        return _coerce_refs(v)

    @field_validator("aof", mode="before")
    @classmethod
    def parse_aof(cls, v: object) -> bool | str | None:
        return parse_optional_bool_or_var(v, field_name="aof")

    @field_validator("eviction", mode="before")
    @classmethod
    def normalize_eviction(cls, v: RuntimeDatastoreEvictionPolicy | str) -> object:
        return _normalize_enum(v, RuntimeDatastoreEvictionPolicy, field_name="eviction")


class RuntimeDatastoreTransportSecurity(SDLModel):
    """The single observed transport-security posture of a datastore service.

    Records the intra-cluster transport TLS mode and whether client/node
    certificate verification is enforced — the observable ``xpack.security`` /
    ``SKIPSSL_VERIFY`` posture, never the certificate material itself.
    """

    transport_security_id: str
    mode: RuntimeDatastoreTransportSecurityMode | str = RuntimeDatastoreTransportSecurityMode.NONE
    client_verification: bool | str | None = None
    node_verification: bool | str | None = None
    description: str = ""

    @field_validator("transport_security_id")
    @classmethod
    def validate_transport_security_id(cls, v: str) -> str:
        return require_symbol(v, field_name="transport_security_id")

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, v: RuntimeDatastoreTransportSecurityMode | str) -> object:
        return _normalize_enum(v, RuntimeDatastoreTransportSecurityMode, field_name="mode")

    @field_validator("client_verification", "node_verification", mode="before")
    @classmethod
    def parse_verifications(cls, v: object) -> bool | str | None:
        return parse_optional_bool_or_var(v, field_name="verification")


class RuntimeDatastoreSetting(SDLModel):
    """An observed datastore runtime setting with scope, provenance, and class.

    Settings that may carry credentials, hashes, or operator-only values must
    omit their raw ``value`` and classify it as ``redacted`` / ``operator_secret``
    — enforced via the shared ``name_indicates_secret`` helper even when the
    submitter left ``classification`` at its default.
    """

    setting_id: str
    scope: RuntimeDatastoreSettingScope | str = RuntimeDatastoreSettingScope.ENGINE
    provenance: RuntimeDatastoreSettingProvenance | str = RuntimeDatastoreSettingProvenance.UNKNOWN
    classification: RuntimeSensitivityClassification | str = RuntimeSensitivityClassification.UNKNOWN
    name: str = ""
    value: str = ""
    description: str = ""

    @field_validator("setting_id")
    @classmethod
    def validate_setting_id(cls, v: str) -> str:
        return require_symbol(v, field_name="setting_id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _require_object_name(v, field_name="setting name") if v else v

    @field_validator("scope", mode="before")
    @classmethod
    def normalize_scope(cls, v: RuntimeDatastoreSettingScope | str) -> object:
        return _normalize_enum(v, RuntimeDatastoreSettingScope, field_name="scope")

    @field_validator("provenance", mode="before")
    @classmethod
    def normalize_provenance(cls, v: RuntimeDatastoreSettingProvenance | str) -> object:
        return _normalize_enum(v, RuntimeDatastoreSettingProvenance, field_name="provenance")

    @field_validator("classification", mode="before")
    @classmethod
    def normalize_classification(cls, v: RuntimeSensitivityClassification | str) -> object:
        return _normalize_enum(v, RuntimeSensitivityClassification, field_name="classification")

    @model_validator(mode="after")
    def validate_setting(self) -> "RuntimeDatastoreSetting":
        if _setting_name_is_concrete_secret(self.name):
            self._enforce_secret_name_redaction()
        elif self.value and self.classification in _REDACTED_SENSITIVITIES:
            raise ValueError(
                f"datastore setting '{self.setting_id}' classified '{self.classification}' must omit its raw value"
            )
        return self

    def _enforce_secret_name_redaction(self) -> None:
        if self.value:
            raise ValueError(
                f"datastore setting '{self.setting_id}' carries a secret-bearing name and must omit its raw value "
                f"(classification must be 'redacted' or 'operator_secret')"
            )
        if not is_variable_ref(self.classification) and self.classification not in _REDACTED_SENSITIVITIES:
            raise ValueError(
                f"datastore setting '{self.setting_id}' carries a secret-bearing name; "
                f"classification must be 'redacted' or 'operator_secret'"
            )
