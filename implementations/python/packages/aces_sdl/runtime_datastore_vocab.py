"""Closed-world vocabularies for ``runtime.datastore_services`` (SCN-010 §5.1).

Holds the enums consumed by the datastore-service spine, its partition/cluster/
persistence child models, and the ``require_profile_for_data_model`` guard. Lives
next to ``runtime_datastore.py`` so no single source file exceeds the ADR-015
600-line cap, mirroring the ``runtime_database_vocab`` split.

Enum-sentinel discipline (DSL-139): OPEN taxonomy carries both ``unknown`` and
``other``; CLOSED structural/standard-fixed vocab carries neither.
"""

from enum import Enum

__all__ = [
    "RuntimeDatastoreDataModel",
    "RuntimeDatastoreEngine",
    "RuntimeDatastoreEvictionPolicy",
    "RuntimeDatastoreNodeEndpointRole",
    "RuntimeDatastoreNodeRole",
    "RuntimeDatastorePartitionKind",
    "RuntimeDatastoreReplicationStrategy",
    "RuntimeDatastoreSettingProvenance",
    "RuntimeDatastoreSettingScope",
    "RuntimeDatastoreTransportSecurityMode",
]


class RuntimeDatastoreEngine(str, Enum):
    """Observed product family for a datastore service.

    OPEN taxonomy: real-world datastore engines are unbounded, so both
    ``unknown`` and ``other`` are carried.
    """

    OPENSEARCH = "opensearch"
    ELASTICSEARCH = "elasticsearch"
    CASSANDRA = "cassandra"
    SCYLLADB = "scylladb"
    REDIS = "redis"
    VALKEY = "valkey"
    MEMCACHED = "memcached"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeDatastoreDataModel(str, Enum):
    """The logical data model of a datastore — the spine discriminator.

    OPEN taxonomy (per the SCN-010 adversarial verdict): carries both
    ``unknown`` and ``other`` so an unrecognized model is permissive rather than
    forcing a shallow relational encoding. ``document`` is intentionally absent —
    no observed container realizes it (forbidden-completion discipline).
    """

    SEARCH_INDEX = "search_index"
    WIDE_COLUMN = "wide_column"
    KEY_VALUE = "key_value"
    RELATIONAL = "relational"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeDatastorePartitionKind(str, Enum):
    """The kind of a datastore partition/namespace primitive.

    OPEN taxonomy: carries both ``unknown`` and ``other``. An ``index`` is the
    search-cluster primary object, a ``keyspace`` the wide-column one, a
    ``logical_db`` a numbered key-value database, and a ``column_family`` a
    wide-column table.
    """

    INDEX = "index"
    KEYSPACE = "keyspace"
    LOGICAL_DB = "logical_db"
    COLUMN_FAMILY = "column_family"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeDatastoreNodeRole(str, Enum):
    """A role a cluster node fulfils.

    OPEN taxonomy: carries both ``unknown`` and ``other``. Covers OpenSearch
    ``cluster_manager``/``data``/``ingest``/``ml`` roles and Cassandra
    ``coordinator``/``seed`` roles uniformly.
    """

    CLUSTER_MANAGER = "cluster_manager"
    DATA = "data"
    INGEST = "ingest"
    COORDINATING = "coordinating"
    ML = "ml"
    SEED = "seed"
    COORDINATOR = "coordinator"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeDatastoreNodeEndpointRole(str, Enum):
    """The role a datastore node's published listener fulfils.

    OPEN taxonomy: carries both ``unknown`` and ``other``. ``client`` is the
    participant/application-facing listener (OpenSearch ``http``, Cassandra
    native/CQL, Redis client); ``peer`` is the inter-node/cluster listener
    (OpenSearch ``transport``, Cassandra internode, Redis cluster-bus).
    Engine-native listener names are intentionally not modelled — the datastore
    spine stays product-neutral (ADR-048, ADR-058).
    """

    CLIENT = "client"
    PEER = "peer"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeDatastoreEvictionPolicy(str, Enum):
    """A key-value eviction policy.

    OPEN taxonomy: carries both ``unknown`` and ``other``. Covers Redis
    ``maxmemory-policy`` values.
    """

    NOEVICTION = "noeviction"
    ALLKEYS_LRU = "allkeys_lru"
    ALLKEYS_LFU = "allkeys_lfu"
    ALLKEYS_RANDOM = "allkeys_random"
    VOLATILE_LRU = "volatile_lru"
    VOLATILE_LFU = "volatile_lfu"
    VOLATILE_RANDOM = "volatile_random"
    VOLATILE_TTL = "volatile_ttl"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeDatastoreReplicationStrategy(str, Enum):
    """A wide-column replication strategy — the spine discriminator's geometry.

    OPEN taxonomy (per the SCN-010 verdict): carries both ``unknown`` and
    ``other``. Covers Cassandra ``SimpleStrategy``/``NetworkTopologyStrategy``.
    """

    SIMPLE_STRATEGY = "simple_strategy"
    NETWORK_TOPOLOGY_STRATEGY = "network_topology_strategy"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeDatastoreTransportSecurityMode(str, Enum):
    """The transport-security posture of a datastore service.

    CLOSED structural vocab: the observable TLS posture is a fixed three-way
    distinction (none / one-way TLS / mutual TLS), so no ``unknown`` / ``other``.
    A ``${var}`` placeholder remains expressible at the field level.
    """

    NONE = "none"
    TLS = "tls"
    MUTUAL_TLS = "mutual_tls"


class RuntimeDatastoreSettingScope(str, Enum):
    """The scope a datastore runtime setting applies at.

    CLOSED structural vocab: the scope lattice (cluster / node / partition /
    engine) is fixed by the spine's own topology, so no ``unknown`` / ``other``.
    """

    CLUSTER = "cluster"
    NODE = "node"
    PARTITION = "partition"
    ENGINE = "engine"


class RuntimeDatastoreSettingProvenance(str, Enum):
    """Where an observed datastore runtime setting value came from.

    OPEN taxonomy: provenance sources are extensible, so both ``unknown`` and
    ``other`` are carried (mirrors ``DatabaseSettingProvenance``).
    """

    INTROSPECTION = "introspection"
    CONFIGURATION_FILE = "configuration_file"
    IMAGE_DEFAULT = "image_default"
    OPERATOR_OVERRIDE = "operator_override"
    RUNTIME_DEFAULT = "runtime_default"
    UNKNOWN = "unknown"
    OTHER = "other"
