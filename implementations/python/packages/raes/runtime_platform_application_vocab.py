"""Closed and open enumerations for the platform-applications runtime family.

These vocabularies back :mod:`runtime_platform_application` and its child
content models. Per the DSL-139 enum-sentinel rule, OPEN taxonomies carry both
``unknown`` and ``other`` while CLOSED structural/standard-fixed vocabularies
carry neither.
"""

from enum import Enum

__all__ = [
    "RelationshipServiceIntegrationDirection",
    "RelationshipServiceIntegrationKind",
    "RuntimePlatformApplicationCapabilityKind",
    "RuntimePlatformApplicationConnectorKind",
    "RuntimePlatformApplicationContentObjectKind",
    "RuntimePlatformApplicationKind",
    "RuntimePlatformApplicationMarkingScheme",
    "RuntimePlatformApplicationSettingClassification",
    "RuntimePlatformApplicationSettingProvenance",
    "RuntimePlatformApplicationUpstreamBindingRole",
]


class RelationshipServiceIntegrationKind(str, Enum):
    """Open taxonomy of how a consumer integrates with a platform engine.

    Open taxonomy: carries both ``unknown`` and ``other``.
    """

    ANALYZER = "analyzer"
    RESPONDER = "responder"
    WEBHOOK = "webhook"
    NOTIFICATION = "notification"
    ENRICHMENT = "enrichment"
    UNKNOWN = "unknown"
    OTHER = "other"


class RelationshipServiceIntegrationDirection(str, Enum):
    """Closed structural vocabulary for an integration edge's data direction.

    Closed structural vocabulary: carries neither ``unknown`` nor ``other``.
    """

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class RuntimePlatformApplicationKind(str, Enum):
    """Legacy open category for a platform-application product family.

    This category is retained for compatibility. It does not assert
    configuration completeness or imply application capabilities. New
    documents should use composable ``capabilities`` instead. Open taxonomy:
    carries both ``unknown`` and ``other``.
    """

    ANALYTICS_DASHBOARD = "analytics_dashboard"
    THREAT_INTEL = "threat_intel"
    CASE_MANAGEMENT = "case_management"
    ANALYZER_ENGINE = "analyzer_engine"
    SOAR = "soar"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimePlatformApplicationCapabilityKind(str, Enum):
    """Open taxonomy of provider-neutral application capabilities.

    A capability describes a functional role exposed by an application. It
    does not imply a product identity, configuration profile, content
    inventory, policy, or execution guarantee. Open taxonomy: carries both
    ``unknown`` and ``other``.
    """

    THREAT_INTELLIGENCE_MANAGEMENT = "threat_intelligence_management"
    INTELLIGENCE_EXCHANGE = "intelligence_exchange"
    CASE_MANAGEMENT = "case_management"
    ANALYSIS_EXECUTION = "analysis_execution"
    WORKFLOW_AUTOMATION = "workflow_automation"
    ANALYTICS_PRESENTATION = "analytics_presentation"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimePlatformApplicationContentObjectKind(str, Enum):
    """Legacy open taxonomy of typed platform content objects.

    A content object is a bounded parsed manifest entry (typed kind + bounded
    attributes + typed references) — never a raw object body. The collection is
    retained for compatibility and does not define an application's
    capabilities. Open taxonomy: carries both ``unknown`` and ``other``.
    """

    INDEX_PATTERN = "index_pattern"
    VISUALIZATION = "visualization"
    DASHBOARD = "dashboard"
    SEARCH = "search"
    FEED = "feed"
    TAXONOMY = "taxonomy"
    GALAXY_CLUSTER = "galaxy_cluster"
    WARNINGLIST = "warninglist"
    OBJECT_TEMPLATE = "object_template"
    SHARING_GROUP = "sharing_group"
    CASE_TEMPLATE = "case_template"
    CUSTOM_FIELD = "custom_field"
    ANALYZER = "analyzer"
    RESPONDER = "responder"
    WORKFLOW = "workflow"
    APP = "app"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimePlatformApplicationMarkingScheme(str, Enum):
    """Closed releasability-marking scheme vocabulary.

    Standard-fixed (FIRST TLP 2.0 / PAP / MISP distribution lattice), so per
    the enum-sentinel rule it carries neither ``unknown`` nor ``other``.
    """

    TLP = "tlp"
    PAP = "pap"
    DISTRIBUTION = "distribution"


class RuntimePlatformApplicationUpstreamBindingRole(str, Enum):
    """Open taxonomy for the role an outbound upstream binding plays.

    Open taxonomy: carries both ``unknown`` and ``other``.
    """

    DATA_SOURCE = "data_source"
    BACKEND_API = "backend_api"
    SYNC_PEER = "sync_peer"
    INDEX_BACKEND = "index_backend"
    CQL_BACKEND = "cql_backend"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimePlatformApplicationConnectorKind(str, Enum):
    """Open taxonomy of platform connector/integration kinds.

    Open taxonomy: carries both ``unknown`` and ``other``.
    """

    ANALYZER_ENGINE = "analyzer_engine"
    RESPONDER = "responder"
    WEBHOOK = "webhook"
    NOTIFICATION = "notification"
    SYNC = "sync"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimePlatformApplicationSettingProvenance(str, Enum):
    """Open taxonomy of where an observed platform setting originated.

    Open taxonomy: carries both ``unknown`` and ``other``.
    """

    DEFAULT = "default"
    ENVIRONMENT = "environment"
    CONFIG_FILE = "config_file"
    DATABASE = "database"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimePlatformApplicationSettingClassification(str, Enum):
    """Closed sensitivity classification for a platform setting value.

    Closed structural redaction vocabulary: carries neither ``unknown`` nor
    ``other`` (an unclassified value is ``plain``).
    """

    PLAIN = "plain"
    REDACTED = "redacted"
    OPERATOR_SECRET = "operator_secret"  # noqa: S105
