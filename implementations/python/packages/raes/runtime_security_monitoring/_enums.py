"""Portable enum taxonomies for security-monitoring manager runtime inventory."""

from enum import Enum


class RuntimeSecurityMonitoringImplementation(str, Enum):
    """Product family for an observed security-monitoring manager."""

    WAZUH = "wazuh"
    OSSEC = "ossec"
    ELASTIC_SECURITY = "elastic_security"
    SPLUNK_ENTERPRISE_SECURITY = "splunk_enterprise_security"
    SECURITY_ONION = "security_onion"
    MICROSOFT_SENTINEL = "microsoft_sentinel"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeSecurityMonitoringManagerKind(str, Enum):
    """Portable manager role/family."""

    SIEM = "siem"
    XDR = "xdr"
    HIDS = "hids"
    NDR = "ndr"
    LOG_MANAGEMENT = "log_management"
    DETECTION_ENGINE = "detection_engine"
    SECURITY_MONITORING = "security_monitoring"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeSecurityMonitoringListenerRole(str, Enum):
    """Logical role of a manager transport listener."""

    AGENT_EVENT_INGESTION = "agent_event_ingestion"
    AGENT_ENROLLMENT = "agent_enrollment"
    SYSLOG_INGESTION = "syslog_ingestion"
    API = "api"
    ALERT_FORWARDING = "alert_forwarding"
    INDEXER_FORWARDING = "indexer_forwarding"
    DASHBOARD = "dashboard"
    OTHER = "other"
    UNKNOWN = "unknown"


class RuntimeSecurityMonitoringComponentKind(str, Enum):
    """Portable component/module kind inside a security-monitoring manager."""

    ANALYSIS_ENGINE = "analysis_engine"
    AGENT_INGESTION = "agent_ingestion"
    AGENT_ENROLLMENT = "agent_enrollment"
    MODULE_SUPERVISOR = "module_supervisor"
    LOG_COLLECTION = "log_collection"
    ALERTING = "alerting"
    API = "api"
    CLUSTER = "cluster"
    INDEXER_FORWARDER = "indexer_forwarder"
    VULNERABILITY_DETECTION = "vulnerability_detection"
    FILE_INTEGRITY_MONITORING = "file_integrity_monitoring"
    ROOTKIT_DETECTION = "rootkit_detection"
    SCA = "sca"
    ACTIVE_RESPONSE = "active_response"
    INTEGRATION = "integration"
    DATABASE = "database"
    OTHER = "other"
    UNKNOWN = "unknown"


class RuntimeSecurityMonitoringComponentStatus(str, Enum):
    """Observed component/module status."""

    RUNNING = "running"
    STOPPED = "stopped"
    DISABLED = "disabled"
    ENABLED = "enabled"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeSecurityMonitoringAgentStatus(str, Enum):
    """Observed enrolled-agent status."""

    AVAILABLE = "available"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    NEVER_CONNECTED = "never_connected"
    PENDING = "pending"
    REMOVED = "removed"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeSecurityMonitoringContentKind(str, Enum):
    """Kind of manager-owned detection or monitoring content."""

    RULE_CORPUS = "rule_corpus"
    DECODER_CORPUS = "decoder_corpus"
    CORRELATION_RULES = "correlation_rules"
    SCA_POLICIES = "sca_policies"
    ACTIVE_RESPONSE = "active_response"
    CDB_LIST = "cdb_list"
    THREAT_INTEL = "threat_intel"
    DASHBOARD = "dashboard"
    OTHER = "other"
    UNKNOWN = "unknown"


class RuntimeSecurityMonitoringContentFormat(str, Enum):
    """Portable format family for manager-owned content."""

    WAZUH_RULE_XML = "wazuh_rule_xml"
    WAZUH_DECODER_XML = "wazuh_decoder_xml"
    SIGMA = "sigma"
    YARA = "yara"
    STIX = "stix"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    QUERY = "query"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeSecurityMonitoringSettingProvenance(str, Enum):
    """Where an observed manager setting came from."""

    INTROSPECTION = "introspection"
    CONFIGURATION_FILE = "configuration_file"
    API = "api"
    IMAGE_DEFAULT = "image_default"
    OPERATOR_OVERRIDE = "operator_override"
    RUNTIME_DEFAULT = "runtime_default"
    UNKNOWN = "unknown"
    OTHER = "other"
