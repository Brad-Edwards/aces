"""Observed runtime configuration models for SDL nodes."""

from collections.abc import Iterable
from enum import Enum

from pydantic import Field, ValidationInfo, field_validator, model_validator

from . import runtime_app_authorization as _runtime_app_authorization
from . import runtime_application as _runtime_application
from . import runtime_database as _runtime_database
from . import runtime_datastore as _runtime_datastore
from . import runtime_directory_identity as _runtime_directory_identity
from . import runtime_dns as _runtime_dns
from . import runtime_file_service as _runtime_file_service
from . import runtime_forwarding_agent as _runtime_forwarding_agent
from . import runtime_listeners as _runtime_listeners
from . import runtime_mail_service as _runtime_mail_service
from . import runtime_network_detection as _runtime_network_detection
from . import runtime_network_sensor as _runtime_network_sensor
from . import runtime_orchestration as _runtime_orchestration
from . import runtime_platform_application as _runtime_platform_application
from . import runtime_scheduled_job as _runtime_scheduled_job
from . import runtime_security_monitoring as _runtime_security_monitoring
from . import runtime_ssh_server as _runtime_ssh_server
from ._base import (
    SDLModel,
    parse_float_or_var,
    parse_int_or_var,
)
from ._runtime_service_families import install_runtime_service_family_exports
from .runtime_capabilities import (
    RuntimeCapabilityOverrideScope,
    RuntimeCapabilityPolicy,
    RuntimeProcessCapabilityOverride,
    RuntimeProcessIdentity,
    RuntimeProcessRole,
)
from .runtime_container import (
    RuntimeContainerConfiguration,
    RuntimeDeviceMapping,
    RuntimeExtraHost,
    RuntimeHealthcheckLog,
    RuntimeHealthObservation,
    RuntimeHealthStatus,
    RuntimeInitProcess,
    RuntimeNamespaceConfiguration,
)
from .runtime_filesystem import (
    RuntimeFilesystemEntry,
    RuntimeFilesystemEntryType,
    RuntimeFilesystemPresence,
    RuntimeFilesystemStability,
    RuntimeMountPropagation,
    RuntimeSensitivityClassification,
)
from .runtime_identity import (
    RuntimeIdentityProvenance,
    RuntimeLocalGroup,
    RuntimeLocalIdentityInventory,
    RuntimeLocalUser,
    RuntimeSudoPrincipalKind,
    RuntimeSudoRule,
)
from .runtime_mounts import (
    RuntimeControlInterface,
    RuntimeControlInterfaceAccess,
    RuntimeControlInterfaceKind,
    RuntimeMount,
    RuntimeMountSourceKind,
)
from .runtime_network import (
    RuntimeNetworkBackendDetail,
    RuntimeNetworkDriver,
    RuntimeNetworkEndpoint,
    RuntimeNetworkIdStability,
    RuntimeNetworkRealization,
    RuntimePublishedPort,
)
from .runtime_service_units import (
    ServiceManagerKind,
    ServiceManagerUnit,
    ServiceUnitActiveState,
    ServiceUnitEnabledState,
    ServiceUnitExecStart,
    ServiceUnitExecStartKind,
    ServiceUnitKind,
    ServiceUnitLoadState,
    ServiceUnitResult,
)
from .runtime_software import (
    RuntimeSoftwareComponent,
    RuntimeSoftwareComponentHash,
    RuntimeSoftwareComponentProvenance,
    RuntimeSoftwareComponentType,
)
from .runtime_values import absolute_path_or_var as _abs_path_or_var
from .runtime_values import parse_ram
from .runtime_values import parse_runtime_enum_or_var as _parse_runtime_enum_or_var

_RUNTIME_SERVICE_FAMILY_EXPORTS = install_runtime_service_family_exports(globals())
__all__ = [
    *_RUNTIME_SERVICE_FAMILY_EXPORTS,
    "RuntimeCapabilityOverrideScope",
    "RuntimeCapabilityPolicy",
    "RuntimeConfiguration",
    "RuntimeContainerConfiguration",
    "RuntimeControlInterface",
    "RuntimeControlInterfaceAccess",
    "RuntimeControlInterfaceKind",
    "RuntimeDependencyManifest",
    "RuntimeDeviceMapping",
    "RuntimeEnvironmentValueClassification",
    "RuntimeEnvironmentVariable",
    "RuntimeEnvironmentVariableProvenance",
    "RuntimeExtraHost",
    "RuntimeFilesystemEntry",
    "RuntimeFilesystemEntryType",
    "RuntimeFilesystemPresence",
    "RuntimeFilesystemStability",
    "RuntimeHealthObservation",
    "RuntimeHealthStatus",
    "RuntimeHealthcheckLog",
    "RuntimeIdentityProvenance",
    "RuntimeInitProcess",
    "RuntimeLocalGroup",
    "RuntimeLocalIdentityInventory",
    "RuntimeLocalUser",
    "RuntimeMount",
    "RuntimeMountPropagation",
    "RuntimeMountSourceKind",
    "RuntimeNamespaceConfiguration",
    "RuntimeNetworkBackendDetail",
    "RuntimeNetworkDriver",
    "RuntimeNetworkEndpoint",
    "RuntimeNetworkIdStability",
    "RuntimeNetworkRealization",
    "RuntimeOperationalPolicy",
    "RuntimePackage",
    "RuntimePackageVulnerabilityFinding",
    "RuntimePackageVulnerabilitySeverity",
    "RuntimeProcessCapabilityOverride",
    "RuntimeProcessIdentity",
    "RuntimeProcessRole",
    "RuntimePublishedPort",
    "RuntimeResourceLimits",
    "RuntimeRestartPolicy",
    "RuntimeSensitivityClassification",
    "RuntimeSoftwareComponent",
    "RuntimeSoftwareComponentHash",
    "RuntimeSoftwareComponentProvenance",
    "RuntimeSoftwareComponentType",
    "RuntimeSudoPrincipalKind",
    "RuntimeSudoRule",
    "ServiceManagerKind",
    "ServiceManagerUnit",
    "ServiceUnitActiveState",
    "ServiceUnitEnabledState",
    "ServiceUnitExecStart",
    "ServiceUnitExecStartKind",
    "ServiceUnitKind",
    "ServiceUnitLoadState",
    "ServiceUnitResult",
    "parse_ram",
]


class RuntimePackageVulnerabilitySeverity(str, Enum):
    """Scanner-derived package finding severity."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuntimeEnvironmentValueClassification(str, Enum):
    """Sensitivity classification for an observed runtime environment value."""

    PLAIN = "plain"
    REDACTED = "redacted"
    SECRET_FIXTURE = "secret_fixture"  # noqa: S105
    UNKNOWN = "unknown"


class RuntimeEnvironmentVariableProvenance(str, Enum):
    """Origin class for an observed runtime environment variable."""

    COMPOSE = "compose"
    IMAGE = "image"
    OPERATOR = "operator"
    CONTAINER = "container"
    RUNTIME = "runtime"
    OTHER = "other"
    UNKNOWN = "unknown"


class RuntimeRestartPolicy(str, Enum):
    """Portable restart policy classification observed at runtime."""

    NO = "no"
    ALWAYS = "always"
    ON_FAILURE = "on_failure"
    UNLESS_STOPPED = "unless_stopped"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeEnvironmentVariable(SDLModel):
    """Observed runtime environment variable with provenance and sensitivity."""

    name: str
    value: str = ""
    value_classification: RuntimeEnvironmentValueClassification | str = RuntimeEnvironmentValueClassification.UNKNOWN
    provenance: RuntimeEnvironmentVariableProvenance | str = RuntimeEnvironmentVariableProvenance.UNKNOWN
    source: str = ""
    description: str = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("environment variable name must be a non-empty string")
        if "=" in v:
            raise ValueError("environment variable name must not contain '='")
        return v

    @field_validator("value_classification", mode="before")
    @classmethod
    def normalize_value_classification(
        cls,
        v: RuntimeEnvironmentValueClassification | str,
    ) -> RuntimeEnvironmentValueClassification | str:
        return _parse_runtime_enum_or_var(
            v,
            RuntimeEnvironmentValueClassification,
            field_name="value_classification",
        )

    @field_validator("provenance", mode="before")
    @classmethod
    def normalize_provenance(
        cls,
        v: RuntimeEnvironmentVariableProvenance | str,
    ) -> RuntimeEnvironmentVariableProvenance | str:
        return _parse_runtime_enum_or_var(v, RuntimeEnvironmentVariableProvenance, field_name="provenance")

    @model_validator(mode="after")
    def validate_redacted_value(self) -> "RuntimeEnvironmentVariable":
        if self.value_classification == RuntimeEnvironmentValueClassification.REDACTED and self.value:
            raise ValueError("redacted runtime environment variables must omit value")
        return self


class RuntimeResourceLimits(SDLModel):
    """Observed runtime/cgroup resource limits for a node."""

    memory: int | str | None = None
    memory_swap: int | str | None = None
    cpu: float | str | None = None
    pids: int | str | None = None
    open_files: int | str | None = None
    description: str = ""

    @field_validator("memory", "memory_swap", mode="before")
    @classmethod
    def parse_memory_limit(cls, v: int | str | None) -> int | str | None:
        return parse_ram(v) if v is not None else v

    @field_validator("cpu", mode="before")
    @classmethod
    def parse_cpu_limit(cls, v: float | str | None) -> float | str | None:
        return parse_float_or_var(v, minimum=0, field_name="cpu") if v is not None else v

    @field_validator("pids", "open_files", mode="before")
    @classmethod
    def parse_count_limit(cls, v: int | str | None, info: ValidationInfo) -> int | str | None:
        return parse_int_or_var(v, minimum=1, field_name=info.field_name) if v is not None else v


class RuntimeOperationalPolicy(SDLModel):
    """Observed restart and resource-limit policy for a runtime node."""

    restart: RuntimeRestartPolicy | str = RuntimeRestartPolicy.UNKNOWN
    resource_limits: RuntimeResourceLimits | None = None
    description: str = ""

    @field_validator("restart", mode="before")
    @classmethod
    def normalize_restart(cls, v: RuntimeRestartPolicy | str | bool) -> RuntimeRestartPolicy | str:
        if v is False:
            return RuntimeRestartPolicy.NO
        return _parse_runtime_enum_or_var(v, RuntimeRestartPolicy, field_name="restart")


class RuntimePackage(SDLModel):
    """A package observed in a runtime image or node."""

    manager: str
    name: str
    version: str
    architecture: str = ""
    source: str = ""
    purl: str = ""


class RuntimeDependencyManifest(SDLModel):
    """A dependency manifest visible in the realized runtime artifact."""

    ecosystem: str
    path: str
    format: str = ""
    name: str = ""
    version: str = ""

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        return _abs_path_or_var(v, field_name="path")


class RuntimePackageVulnerabilityFinding(SDLModel):
    """A scanner-derived CVE/advisory finding for an observed package."""

    id: str
    package_name: str
    installed_version: str
    severity: RuntimePackageVulnerabilitySeverity | str = RuntimePackageVulnerabilitySeverity.UNKNOWN
    scanner: str
    image_digest: str
    scan_time: str
    fixed_version: str = ""
    advisory_url: str = ""
    scanner_version: str = ""
    scanner_database: str = ""

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(
        cls,
        v: RuntimePackageVulnerabilitySeverity | str,
    ) -> RuntimePackageVulnerabilitySeverity | str:
        return _parse_runtime_enum_or_var(v, RuntimePackageVulnerabilitySeverity, field_name="severity")


def _reject_duplicate_keys(items: Iterable[object], *, attr: str, label: str) -> None:
    """Raise on the first repeated non-empty key read from ``attr``."""
    seen: set[object] = set()
    for item in items:
        key = getattr(item, attr)
        if key is None or key == "":
            continue
        if key in seen:
            raise ValueError(f"Duplicate runtime {label} '{key}'")
        seen.add(key)


class RuntimeConfiguration(SDLModel):
    """Observed runtime configuration facts attached to a VM node."""

    mounts: list[RuntimeMount] = Field(default_factory=list)
    filesystem_inventory: list[RuntimeFilesystemEntry] = Field(default_factory=list)
    local_control_interfaces: list[RuntimeControlInterface] = Field(default_factory=list)
    process: RuntimeProcessIdentity | None = None
    processes: list[RuntimeProcessIdentity] = Field(default_factory=list)
    environment: list[RuntimeEnvironmentVariable] = Field(default_factory=list)
    linux_capabilities: RuntimeCapabilityPolicy | None = None
    operational_policy: RuntimeOperationalPolicy | None = None
    container: RuntimeContainerConfiguration | None = None
    health: RuntimeHealthObservation | None = None
    local_identity: RuntimeLocalIdentityInventory | None = None
    identity_authorities: list[_runtime_directory_identity.RuntimeIdentityAuthority] = Field(default_factory=list)
    file_services: list[_runtime_file_service.RuntimeFileService] = Field(default_factory=list)
    mail_services: list[_runtime_mail_service.RuntimeMailService] = Field(default_factory=list)
    network: RuntimeNetworkRealization | None = None
    service_listeners: list[_runtime_listeners.RuntimeServiceListener] = Field(default_factory=list)
    applications: list[_runtime_application.RuntimeApplicationSurface] = Field(default_factory=list)
    database_services: list[_runtime_database.RuntimeDatabaseService] = Field(default_factory=list)
    dns_services: list[_runtime_dns.RuntimeDnsService] = Field(default_factory=list)
    network_sensors: list[_runtime_network_sensor.RuntimeNetworkSensor] = Field(default_factory=list)
    network_detection_engines: list[_runtime_network_detection.RuntimeNetworkDetectionEngine] = Field(
        default_factory=list
    )
    security_monitoring_managers: list[_runtime_security_monitoring.RuntimeSecurityMonitoringManager] = Field(
        default_factory=list
    )
    ssh_servers: list[_runtime_ssh_server.RuntimeSshServer] = Field(default_factory=list)
    datastore_services: list[_runtime_datastore.RuntimeDatastoreService] = Field(default_factory=list)
    platform_applications: list[_runtime_platform_application.RuntimePlatformApplication] = Field(default_factory=list)
    forwarding_agents: list[_runtime_forwarding_agent.RuntimeForwardingAgent] = Field(default_factory=list)
    orchestration_authorities: list[_runtime_orchestration.RuntimeOrchestrationAuthority] = Field(default_factory=list)
    app_authorizations: list[_runtime_app_authorization.RuntimeAppAuthorization] = Field(default_factory=list)
    scheduled_jobs: list[_runtime_scheduled_job.RuntimeScheduledJob] = Field(default_factory=list)
    service_manager_units: list[ServiceManagerUnit] = Field(default_factory=list)
    packages: list[RuntimePackage] = Field(default_factory=list)
    software_components: list[RuntimeSoftwareComponent] = Field(default_factory=list)
    dependency_manifests: list[RuntimeDependencyManifest] = Field(default_factory=list)
    package_vulnerabilities: list[RuntimePackageVulnerabilityFinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_runtime_entries(self) -> "RuntimeConfiguration":
        _reject_duplicate_keys(self.environment, attr="name", label="environment variable")
        _reject_duplicate_keys(self.mounts, attr="target", label="mount target")
        _reject_duplicate_keys(
            self.local_control_interfaces,
            attr="control_interface_id",
            label="control_interface_id",
        )
        _reject_duplicate_keys(self.filesystem_inventory, attr="path", label="filesystem path")
        _reject_duplicate_keys(self.processes, attr="name", label="process name")
        _reject_duplicate_keys(self.processes, attr="pid", label="process pid")
        _reject_duplicate_keys(self.service_listeners, attr="listener_id", label="service_listener listener_id")
        _reject_duplicate_keys(self.applications, attr="application_id", label="application_id")
        _reject_duplicate_keys(self.database_services, attr="database_service_id", label="database_service_id")
        _reject_duplicate_keys(self.dns_services, attr="dns_service_id", label="dns_service_id")
        _reject_duplicate_keys(self.network_sensors, attr="sensor_id", label="network sensor")
        _reject_duplicate_keys(self.network_detection_engines, attr="engine_id", label="network detection engine")
        _reject_duplicate_keys(self.security_monitoring_managers, attr="manager_id", label="security manager")
        _reject_duplicate_keys(self.ssh_servers, attr="server_id", label="ssh_server server_id")
        _reject_duplicate_keys(
            self.datastore_services,
            attr="datastore_service_id",
            label="datastore_service_id",
        )
        _reject_duplicate_keys(
            self.platform_applications,
            attr="platform_application_id",
            label="platform_application_id",
        )
        _reject_duplicate_keys(
            self.forwarding_agents,
            attr="forwarding_agent_id",
            label="forwarding_agent_id",
        )
        _reject_duplicate_keys(
            self.orchestration_authorities,
            attr="orchestration_authority_id",
            label="orchestration_authority_id",
        )
        _reject_duplicate_keys(
            self.app_authorizations,
            attr="app_authorization_id",
            label="app_authorization_id",
        )
        _reject_duplicate_keys(self.scheduled_jobs, attr="scheduled_job_id", label="scheduled_job_id")
        _reject_duplicate_keys(
            self.service_manager_units,
            attr="unit_id",
            label="service_manager_unit unit_id",
        )
        _reject_duplicate_keys(
            self.service_manager_units,
            attr="unit_name",
            label="service_manager_unit unit_name",
        )
        _reject_duplicate_keys(self.identity_authorities, attr="authority_id", label="identity authority")
        _reject_duplicate_keys(self.file_services, attr="service_id", label="file_service service_id")
        _reject_duplicate_keys(self.mail_services, attr="service_id", label="mail_service service_id")
        _reject_duplicate_keys(self.software_components, attr="component_id", label="software component")
        return self
