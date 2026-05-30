"""Security-monitoring manager runtime inventory models."""

from enum import Enum
from typing import Any

from pydantic import Field, ValidationInfo, field_validator, model_validator

from ._base import SDLModel, is_variable_ref, parse_int_or_var
from .runtime_filesystem import RuntimeSensitivityClassification
from .runtime_security_monitoring_definitions import (
    RuntimeSecurityMonitoringDetectionDefinition,
    RuntimeSecurityMonitoringDetectionDefinitionKind,
    RuntimeSecurityMonitoringDetectionEngine,
    RuntimeSecurityMonitoringFieldPredicate,
    RuntimeSecurityMonitoringFieldPredicateOperator,
)
from .runtime_values import (
    absolute_path_or_var,
    coerce_string_list,
    name_indicates_secret,
    parse_optional_bool_or_var,
    parse_runtime_enum_or_var,
    require_symbol,
)

__all__ = [
    "RuntimeSecurityMonitoringAgent",
    "RuntimeSecurityMonitoringAgentGroup",
    "RuntimeSecurityMonitoringAgentStatus",
    "RuntimeSecurityMonitoringComponent",
    "RuntimeSecurityMonitoringComponentKind",
    "RuntimeSecurityMonitoringComponentStatus",
    "RuntimeSecurityMonitoringContentFormat",
    "RuntimeSecurityMonitoringContentKind",
    "RuntimeSecurityMonitoringContentSet",
    "RuntimeSecurityMonitoringDetectionDefinition",
    "RuntimeSecurityMonitoringDetectionDefinitionKind",
    "RuntimeSecurityMonitoringDetectionEngine",
    "RuntimeSecurityMonitoringFieldPredicate",
    "RuntimeSecurityMonitoringFieldPredicateOperator",
    "RuntimeSecurityMonitoringImplementation",
    "RuntimeSecurityMonitoringListener",
    "RuntimeSecurityMonitoringListenerRole",
    "RuntimeSecurityMonitoringManager",
    "RuntimeSecurityMonitoringManagerKind",
    "RuntimeSecurityMonitoringSetting",
    "RuntimeSecurityMonitoringSettingProvenance",
]

_REDACTED_SENSITIVITIES = frozenset(
    {RuntimeSensitivityClassification.REDACTED, RuntimeSensitivityClassification.OPERATOR_SECRET}
)


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


def _require_non_empty(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _normalize_enum(value: Any, enum_cls: type[Enum], *, field_name: str) -> Any:
    return parse_runtime_enum_or_var(value, enum_cls, field_name=field_name)


def _coerce_refs(value: Any) -> list[str]:
    return coerce_string_list(value)


def _absolute_refs(values: list[str], *, field_name: str) -> list[str]:
    return [absolute_path_or_var(item, field_name=field_name) for item in values]


class RuntimeSecurityMonitoringListener(SDLModel):
    """A manager listener bound to a same-node transport service."""

    listener_id: str
    service: str = ""
    role: RuntimeSecurityMonitoringListenerRole | str = RuntimeSecurityMonitoringListenerRole.OTHER
    protocol: str = ""
    auth_required: bool | str | None = None
    tls_enabled: bool | str | None = None
    description: str = ""

    @field_validator("listener_id")
    @classmethod
    def validate_listener_id(cls, v: str) -> str:
        return require_symbol(v, field_name="listener_id")

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(
        cls,
        v: RuntimeSecurityMonitoringListenerRole | str,
    ) -> RuntimeSecurityMonitoringListenerRole | str:
        return _normalize_enum(v, RuntimeSecurityMonitoringListenerRole, field_name="role")

    @field_validator("auth_required", "tls_enabled", mode="before")
    @classmethod
    def parse_optional_bool(cls, v: Any, info: ValidationInfo) -> bool | str | None:
        return parse_optional_bool_or_var(v, field_name=info.field_name)


class RuntimeSecurityMonitoringComponent(SDLModel):
    """A manager daemon, module, or internal component."""

    component_id: str
    kind: RuntimeSecurityMonitoringComponentKind | str = RuntimeSecurityMonitoringComponentKind.OTHER
    name: str
    status: RuntimeSecurityMonitoringComponentStatus | str = RuntimeSecurityMonitoringComponentStatus.UNKNOWN
    enabled: bool | str | None = None
    process_ref: str = ""
    description: str = ""

    @field_validator("component_id")
    @classmethod
    def validate_component_id(cls, v: str) -> str:
        return require_symbol(v, field_name="component_id")

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(
        cls,
        v: RuntimeSecurityMonitoringComponentKind | str,
    ) -> RuntimeSecurityMonitoringComponentKind | str:
        return _normalize_enum(v, RuntimeSecurityMonitoringComponentKind, field_name="kind")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(
        cls,
        v: RuntimeSecurityMonitoringComponentStatus | str,
    ) -> RuntimeSecurityMonitoringComponentStatus | str:
        return _normalize_enum(v, RuntimeSecurityMonitoringComponentStatus, field_name="status")

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_enabled(cls, v: Any) -> bool | str | None:
        return parse_optional_bool_or_var(v, field_name="enabled")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _require_non_empty(v, field_name="component name")


class RuntimeSecurityMonitoringAgent(SDLModel):
    """An agent or sensor enrolled with the manager."""

    agent_id: str
    name: str
    status: RuntimeSecurityMonitoringAgentStatus | str = RuntimeSecurityMonitoringAgentStatus.UNKNOWN
    address: str = ""
    version: str = ""
    os: str = ""
    node_ref: str = ""
    group_refs: list[str] = Field(default_factory=list)
    description: str = ""

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        return require_symbol(v, field_name="agent_id")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(
        cls,
        v: RuntimeSecurityMonitoringAgentStatus | str,
    ) -> RuntimeSecurityMonitoringAgentStatus | str:
        return _normalize_enum(v, RuntimeSecurityMonitoringAgentStatus, field_name="status")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _require_non_empty(v, field_name="agent name")

    @field_validator("group_refs", mode="before")
    @classmethod
    def coerce_group_refs(cls, v: Any) -> list[str]:
        return _coerce_refs(v)


class RuntimeSecurityMonitoringAgentGroup(SDLModel):
    """A manager-side enrolled-agent group."""

    group_id: str
    name: str = ""
    member_refs: list[str] = Field(default_factory=list)
    configuration_file_refs: list[str] = Field(default_factory=list)
    description: str = ""

    @field_validator("group_id")
    @classmethod
    def validate_group_id(cls, v: str) -> str:
        return require_symbol(v, field_name="group_id")

    @field_validator("member_refs", "configuration_file_refs", mode="before")
    @classmethod
    def coerce_lists(cls, v: Any) -> list[str]:
        return _coerce_refs(v)

    @field_validator("configuration_file_refs")
    @classmethod
    def validate_configuration_file_refs(cls, v: list[str]) -> list[str]:
        return _absolute_refs(v, field_name="configuration_file_refs")


class RuntimeSecurityMonitoringContentSet(SDLModel):
    """A manager-owned rule, decoder, policy, list, or query corpus."""

    content_id: str
    kind: RuntimeSecurityMonitoringContentKind | str = RuntimeSecurityMonitoringContentKind.OTHER
    format: RuntimeSecurityMonitoringContentFormat | str = RuntimeSecurityMonitoringContentFormat.UNKNOWN
    name: str = ""
    file_count: int | str | None = None
    file_refs: list[str] = Field(default_factory=list)
    loaded: bool | str | None = None
    description: str = ""

    @field_validator("content_id")
    @classmethod
    def validate_content_id(cls, v: str) -> str:
        return require_symbol(v, field_name="content_id")

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(
        cls,
        v: RuntimeSecurityMonitoringContentKind | str,
    ) -> RuntimeSecurityMonitoringContentKind | str:
        return _normalize_enum(v, RuntimeSecurityMonitoringContentKind, field_name="kind")

    @field_validator("format", mode="before")
    @classmethod
    def normalize_format(
        cls,
        v: RuntimeSecurityMonitoringContentFormat | str,
    ) -> RuntimeSecurityMonitoringContentFormat | str:
        return _normalize_enum(v, RuntimeSecurityMonitoringContentFormat, field_name="format")

    @field_validator("file_count", mode="before")
    @classmethod
    def parse_file_count(cls, v: Any) -> int | str | None:
        return parse_int_or_var(v, minimum=0, field_name="file_count") if v is not None else v

    @field_validator("file_refs", mode="before")
    @classmethod
    def coerce_file_refs(cls, v: Any) -> list[str]:
        return _coerce_refs(v)

    @field_validator("file_refs")
    @classmethod
    def validate_file_refs(cls, v: list[str]) -> list[str]:
        return _absolute_refs(v, field_name="file_refs")

    @field_validator("loaded", mode="before")
    @classmethod
    def parse_loaded(cls, v: Any) -> bool | str | None:
        return parse_optional_bool_or_var(v, field_name="loaded")


class RuntimeSecurityMonitoringSetting(SDLModel):
    """A bounded manager setting with sensitivity classification."""

    setting_id: str
    component_ref: str = ""
    name: str
    value: str = ""
    value_classification: RuntimeSensitivityClassification | str = RuntimeSensitivityClassification.UNKNOWN
    provenance: RuntimeSecurityMonitoringSettingProvenance | str = RuntimeSecurityMonitoringSettingProvenance.UNKNOWN
    source_path: str = ""
    description: str = ""

    @field_validator("setting_id")
    @classmethod
    def validate_setting_id(cls, v: str) -> str:
        return require_symbol(v, field_name="setting_id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _require_non_empty(v, field_name="setting name")

    @field_validator("value_classification", mode="before")
    @classmethod
    def normalize_value_classification(
        cls,
        v: RuntimeSensitivityClassification | str,
    ) -> RuntimeSensitivityClassification | str:
        return _normalize_enum(v, RuntimeSensitivityClassification, field_name="value_classification")

    @field_validator("provenance", mode="before")
    @classmethod
    def normalize_provenance(
        cls,
        v: RuntimeSecurityMonitoringSettingProvenance | str,
    ) -> RuntimeSecurityMonitoringSettingProvenance | str:
        return _normalize_enum(v, RuntimeSecurityMonitoringSettingProvenance, field_name="provenance")

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, v: str) -> str:
        return absolute_path_or_var(v, field_name="source_path") if v else v

    @model_validator(mode="after")
    def validate_redacted_value(self) -> "RuntimeSecurityMonitoringSetting":
        if name_indicates_secret(self.name):
            self._enforce_secret_name_redaction()
        elif self.value and self.value_classification in _REDACTED_SENSITIVITIES:
            raise ValueError(
                f"security-monitoring setting '{self.name}' classified "
                f"'{self.value_classification}' must omit its raw value"
            )
        return self

    def _enforce_secret_name_redaction(self) -> None:
        if self.value:
            raise ValueError(
                f"security-monitoring setting '{self.name}' carries a secret-bearing name and must omit its raw value"
            )
        if is_variable_ref(self.value_classification):
            return
        if self.value_classification not in _REDACTED_SENSITIVITIES:
            raise ValueError(
                f"security-monitoring setting '{self.name}' carries a secret-bearing name; "
                f"value_classification must be 'redacted' or 'operator_secret'"
            )


class RuntimeSecurityMonitoringManager(SDLModel):
    """Node-scoped runtime inventory for a SIEM/security-monitoring manager."""

    security_monitoring_manager_id: str
    service: str = ""
    implementation: RuntimeSecurityMonitoringImplementation | str = RuntimeSecurityMonitoringImplementation.UNKNOWN
    manager_kind: RuntimeSecurityMonitoringManagerKind | str = RuntimeSecurityMonitoringManagerKind.UNKNOWN
    version: str = ""
    revision: str = ""
    name: str = ""
    configuration_file_refs: list[str] = Field(default_factory=list)
    log_file_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    listeners: list[RuntimeSecurityMonitoringListener] = Field(default_factory=list)
    components: list[RuntimeSecurityMonitoringComponent] = Field(default_factory=list)
    agents: list[RuntimeSecurityMonitoringAgent] = Field(default_factory=list)
    agent_groups: list[RuntimeSecurityMonitoringAgentGroup] = Field(default_factory=list)
    content_sets: list[RuntimeSecurityMonitoringContentSet] = Field(default_factory=list)
    detection_definitions: list[RuntimeSecurityMonitoringDetectionDefinition] = Field(default_factory=list)
    settings: list[RuntimeSecurityMonitoringSetting] = Field(default_factory=list)
    description: str = ""

    @field_validator("security_monitoring_manager_id")
    @classmethod
    def validate_security_monitoring_manager_id(cls, v: str) -> str:
        return require_symbol(v, field_name="security_monitoring_manager_id")

    @field_validator("implementation", mode="before")
    @classmethod
    def normalize_implementation(
        cls,
        v: RuntimeSecurityMonitoringImplementation | str,
    ) -> RuntimeSecurityMonitoringImplementation | str:
        return _normalize_enum(v, RuntimeSecurityMonitoringImplementation, field_name="implementation")

    @field_validator("manager_kind", mode="before")
    @classmethod
    def normalize_manager_kind(
        cls,
        v: RuntimeSecurityMonitoringManagerKind | str,
    ) -> RuntimeSecurityMonitoringManagerKind | str:
        return _normalize_enum(v, RuntimeSecurityMonitoringManagerKind, field_name="manager_kind")

    @field_validator("configuration_file_refs", "log_file_refs", "evidence_refs", mode="before")
    @classmethod
    def coerce_file_refs(cls, v: Any) -> list[str]:
        return _coerce_refs(v)

    @field_validator("configuration_file_refs", "log_file_refs", "evidence_refs")
    @classmethod
    def validate_file_refs(cls, v: list[str], info: ValidationInfo) -> list[str]:
        return _absolute_refs(v, field_name=info.field_name)

    @model_validator(mode="after")
    def validate_manager(self) -> "RuntimeSecurityMonitoringManager":
        _reject_duplicate_local_ref_ids(self)
        return self


def _reject_duplicate_local_ref_ids(manager: RuntimeSecurityMonitoringManager) -> None:
    entries: list[tuple[str, str]] = [("security_monitoring_manager_id", manager.security_monitoring_manager_id)]
    for label, collection_name in (
        ("listener_id", "listeners"),
        ("component_id", "components"),
        ("agent_id", "agents"),
        ("group_id", "agent_groups"),
        ("content_id", "content_sets"),
        ("definition_id", "detection_definitions"),
        ("setting_id", "settings"),
    ):
        entries.extend((label, getattr(item, label)) for item in getattr(manager, collection_name))

    seen: dict[str, str] = {}
    for label, value in entries:
        prior = seen.get(value)
        if prior is not None:
            raise ValueError(
                f"Duplicate runtime security-monitoring stable id '{value}' in manager "
                f"'{manager.security_monitoring_manager_id}' across {prior} and {label}"
            )
        seen[value] = label
