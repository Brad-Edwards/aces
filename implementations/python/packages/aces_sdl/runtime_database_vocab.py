"""Closed-world vocabularies for ``runtime.database_services`` (ADR-029).

Holds the enums and the engine-to-protocol mapping that the database-service
model and its validators consume. Lives next to ``runtime_database.py`` to keep
that file under the repo-policy 600-line source-file cap (ADR-015), the same
``_module_*`` pattern composition.py uses.
"""

from enum import Enum

__all__ = [
    "DatabaseAuthMethod",
    "DatabaseEngine",
    "DatabaseObjectOrigin",
    "DatabaseObjectType",
    "DatabaseProtocol",
    "DatabaseRoleType",
    "DatabaseSettingProvenance",
    "ENGINE_TO_PROTOCOLS",
]


class DatabaseEngine(str, Enum):
    """The database engine of an observed database service."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    MSSQL = "mssql"
    ORACLE = "oracle"
    REDIS = "redis"
    OTHER = "other"
    UNKNOWN = "unknown"


class DatabaseProtocol(str, Enum):
    """The wire protocol an observed database service speaks.

    Kept distinct from :class:`DatabaseEngine`: a MariaDB engine speaks the
    ``mysql`` protocol, and PostgreSQL must never be ``other`` (ADR-029 §3).
    """

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    TDS = "tds"
    MONGODB = "mongodb"
    REDIS = "redis"
    OTHER = "other"
    UNKNOWN = "unknown"


class DatabaseObjectOrigin(str, Enum):
    """Whether a database object was scenario-authored or engine-supplied.

    Keeps engine built-ins (``postgres``, ``template0``, ``template1``,
    ``information_schema``) and system roles from looking scenario-authored.
    """

    SCENARIO = "scenario"
    BUILT_IN = "built_in"
    SYSTEM = "system"
    UNKNOWN = "unknown"
    OTHER = "other"


class DatabaseRoleType(str, Enum):
    """Portable classification of a database-local role."""

    LOGIN = "login"
    GROUP = "group"
    APPLICATION = "application"
    SERVICE = "service"
    ADMIN = "admin"
    SYSTEM = "system"
    OTHER = "other"
    UNKNOWN = "unknown"


class DatabaseSettingProvenance(str, Enum):
    """Where an observed database runtime setting value came from."""

    INTROSPECTION = "introspection"
    CONFIGURATION_FILE = "configuration_file"
    IMAGE_DEFAULT = "image_default"
    OPERATOR_OVERRIDE = "operator_override"
    RUNTIME_DEFAULT = "runtime_default"
    UNKNOWN = "unknown"
    OTHER = "other"


class DatabaseObjectType(str, Enum):
    """The kind of database object a grant applies to."""

    DATABASE = "database"
    SCHEMA = "schema"
    TABLE = "table"


class DatabaseAuthMethod(str, Enum):
    """How a client authenticates to a database on an access relationship."""

    PASSWORD = "password"  # noqa: S105
    MD5 = "md5"
    SCRAM_SHA_256 = "scram_sha_256"
    CERT = "cert"
    TRUST = "trust"
    PEER = "peer"
    IDENT = "ident"
    GSSAPI = "gssapi"
    SSPI = "sspi"
    LDAP = "ldap"
    RADIUS = "radius"
    OTHER = "other"
    UNKNOWN = "unknown"


# Engines that speak a well-known wire protocol. A scenario authored with one
# of these engines must declare the matching protocol — ADR-029 §3 disallows
# PostgreSQL being modelled as ``protocol: other``, and the same rule applies
# to the other engines that have one canonical wire protocol. Engines without
# an entry here (``sqlite`` is file-based; ``oracle`` / ``other`` are left
# unconstrained for now) skip the cross-field check.
ENGINE_TO_PROTOCOLS: dict[DatabaseEngine, frozenset[DatabaseProtocol]] = {
    DatabaseEngine.POSTGRESQL: frozenset({DatabaseProtocol.POSTGRESQL}),
    DatabaseEngine.MYSQL: frozenset({DatabaseProtocol.MYSQL}),
    DatabaseEngine.MARIADB: frozenset({DatabaseProtocol.MYSQL}),
    DatabaseEngine.MSSQL: frozenset({DatabaseProtocol.TDS}),
    DatabaseEngine.MONGODB: frozenset({DatabaseProtocol.MONGODB}),
    DatabaseEngine.REDIS: frozenset({DatabaseProtocol.REDIS}),
}
