"""Forwarding / intel-sync agent runtime inventory family (SCN-010 §5.5).

A single node-scoped family, :class:`RuntimeForwardingAgent`, typing the
agent-side ``(source, transform, ship-target, buffer)`` shipping state that
``runtime.security_monitoring_managers`` (the *manager* half) and
``runtime.network_detection_engines`` (the *consumer* of generated content)
provably cannot shape. It covers both the log-shipping sidecars
(``agent_kind = log_forwarder``) and the intel-sync co-process
(``agent_kind = content_sync``) — the same ``source -> transform -> target``
shape in the intel-to-content direction — so the second never forks a third
family.

The OPEN ``agent_kind`` discriminator selects the family member; the
``require_profile_for_agent_kind`` after-validator makes each member's defining
profile executable so an under-populated instance FAILS validation rather than
silently shallow-encoding a defining shipping fact. A ``${var}`` discriminator
is exempt (nothing concrete is asserted); the ``unknown`` / ``other`` tail is
permissive.

This is observed runtime state attached to ``Node.runtime``. Secret-bearing
settings and ship-target enrollment identities never carry raw values; they
classify ``redacted`` / ``operator_secret`` via the shared
``name_indicates_secret`` helper and the closed enrollment lattice.
"""

from enum import Enum

from pydantic import Field, ValidationInfo, field_validator, model_validator

from ._base import SDLModel, is_variable_ref, parse_int_or_var
from .runtime_forwarding_agent_vocab import (
    RuntimeForwardingAgentImplementation,
    RuntimeForwardingAgentKind,
    RuntimeForwardingBufferCrypto,
    RuntimeForwardingEnrollmentClassification,
    RuntimeForwardingParseFormat,
    RuntimeForwardingProtocol,
    RuntimeForwardingReloadChannelKind,
    RuntimeForwardingSettingClassification,
    RuntimeForwardingSettingProvenance,
    RuntimeForwardingSourceKind,
    RuntimeForwardingTransformKind,
)
from .runtime_values import (
    name_indicates_secret,
    parse_runtime_enum_or_var,
    require_symbol,
)

__all__ = [
    "RuntimeForwardingAgent",
    "RuntimeForwardingAgentImplementation",
    "RuntimeForwardingAgentKind",
    "RuntimeForwardingBufferCrypto",
    "RuntimeForwardingBufferPolicy",
    "RuntimeForwardingEnrollmentClassification",
    "RuntimeForwardingParseFormat",
    "RuntimeForwardingProtocol",
    "RuntimeForwardingReloadChannel",
    "RuntimeForwardingReloadChannelKind",
    "RuntimeForwardingSetting",
    "RuntimeForwardingSettingClassification",
    "RuntimeForwardingSettingProvenance",
    "RuntimeForwardingShipTarget",
    "RuntimeForwardingSource",
    "RuntimeForwardingSourceKind",
    "RuntimeForwardingTransform",
    "RuntimeForwardingTransformKind",
]

# Enrollment classifications that mark a present (but unrecorded) credential.
_PRESENT_ENROLLMENT_CLASSIFICATIONS = frozenset(
    {
        RuntimeForwardingEnrollmentClassification.REDACTED,
        RuntimeForwardingEnrollmentClassification.OPERATOR_SECRET,
    }
)
# Setting classifications whose raw value must never be recorded.
_REDACTED_SETTING_CLASSIFICATIONS = frozenset(
    {
        RuntimeForwardingSettingClassification.REDACTED,
        RuntimeForwardingSettingClassification.OPERATOR_SECRET,
    }
)


def _normalize_enum(value: object, enum_cls: type[Enum], *, field_name: str) -> object:
    return parse_runtime_enum_or_var(value, enum_cls, field_name=field_name)


def _setting_name_is_concrete_secret(name: object) -> bool:
    """Return whether ``name`` is a concrete (non-``${var}``) secret-bearing label."""
    return isinstance(name, str) and not is_variable_ref(name) and name_indicates_secret(name)


class RuntimeForwardingSource(SDLModel):
    """An observed forwarder input source (tailed path, API pull, or queue)."""

    source_id: str
    kind: RuntimeForwardingSourceKind | str = RuntimeForwardingSourceKind.UNKNOWN
    location: str = ""
    parse_format: RuntimeForwardingParseFormat | str = RuntimeForwardingParseFormat.UNKNOWN
    selector: str = ""
    description: str = ""

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, v: str) -> str:
        return require_symbol(v, field_name="source_id")

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, v: RuntimeForwardingSourceKind | str) -> object:
        return _normalize_enum(v, RuntimeForwardingSourceKind, field_name="kind")

    @field_validator("parse_format", mode="before")
    @classmethod
    def normalize_parse_format(cls, v: RuntimeForwardingParseFormat | str) -> object:
        return _normalize_enum(v, RuntimeForwardingParseFormat, field_name="parse_format")


class RuntimeForwardingTransform(SDLModel):
    """An observed transform applied between a source and a ship target."""

    transform_id: str
    kind: RuntimeForwardingTransformKind | str = RuntimeForwardingTransformKind.UNKNOWN
    sid_namespace: str = ""
    description: str = ""

    @field_validator("transform_id")
    @classmethod
    def validate_transform_id(cls, v: str) -> str:
        return require_symbol(v, field_name="transform_id")

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, v: RuntimeForwardingTransformKind | str) -> object:
        return _normalize_enum(v, RuntimeForwardingTransformKind, field_name="kind")


class RuntimeForwardingShipTarget(SDLModel):
    """An observed downstream ship target (event ingest and/or enrollment).

    ``ingestion_port`` is the event-ingest endpoint (e.g. ``wazuh.manager:1514``);
    ``enrollment_port`` is the enrollment endpoint (e.g. ``:1515``). The
    enrollment identity itself is never recorded — only the closed
    ``enrollment_identity_classification`` lattice (``none`` / ``redacted`` /
    ``operator_secret``).
    """

    target_id: str
    target_node_ref: str = ""
    target_service_ref: str = ""
    ingestion_port: int | str | None = None
    enrollment_port: int | str | None = None
    protocol: RuntimeForwardingProtocol | str = RuntimeForwardingProtocol.UNKNOWN
    enrollment_identity_classification: RuntimeForwardingEnrollmentClassification | str = (
        RuntimeForwardingEnrollmentClassification.NONE
    )
    description: str = ""

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, v: str) -> str:
        return require_symbol(v, field_name="target_id")

    @field_validator("ingestion_port", "enrollment_port", mode="before")
    @classmethod
    def parse_ports(cls, v: object, info: ValidationInfo) -> int | str | None:
        return parse_int_or_var(v, minimum=0, maximum=65535, field_name=info.field_name) if v is not None else v

    @field_validator("protocol", mode="before")
    @classmethod
    def normalize_protocol(cls, v: RuntimeForwardingProtocol | str) -> object:
        return _normalize_enum(v, RuntimeForwardingProtocol, field_name="protocol")

    @field_validator("enrollment_identity_classification", mode="before")
    @classmethod
    def normalize_enrollment_classification(cls, v: RuntimeForwardingEnrollmentClassification | str) -> object:
        return _normalize_enum(
            v, RuntimeForwardingEnrollmentClassification, field_name="enrollment_identity_classification"
        )

    def has_ingestion_endpoint(self) -> bool:
        """Return whether this target carries a concrete event-ingest endpoint."""
        return self.ingestion_port is not None

    def has_enrollment_endpoint(self) -> bool:
        """Return whether this target carries an enrollment endpoint or identity."""
        if self.enrollment_port is not None:
            return True
        classification = self.enrollment_identity_classification
        return (
            isinstance(classification, RuntimeForwardingEnrollmentClassification)
            and classification in _PRESENT_ENROLLMENT_CLASSIFICATIONS
        )


class RuntimeForwardingBufferPolicy(SDLModel):
    """The single observed buffer / back-pressure posture of a forwarder.

    Captures the ``client_buffer`` shape: queue capacity, events-per-second
    ceiling, at-rest/in-transit crypto, and reconnect interval. Its presence is
    the defining profile a ``log_forwarder`` must carry.
    """

    buffer_policy_id: str
    queue_capacity: int | str | None = None
    eps: int | str | None = None
    crypto: RuntimeForwardingBufferCrypto | str = RuntimeForwardingBufferCrypto.UNKNOWN
    reconnect_seconds: int | str | None = None
    description: str = ""

    @field_validator("buffer_policy_id")
    @classmethod
    def validate_buffer_policy_id(cls, v: str) -> str:
        return require_symbol(v, field_name="buffer_policy_id")

    @field_validator("queue_capacity", "eps", "reconnect_seconds", mode="before")
    @classmethod
    def parse_counts(cls, v: object, info: ValidationInfo) -> int | str | None:
        return parse_int_or_var(v, minimum=0, field_name=info.field_name) if v is not None else v

    @field_validator("crypto", mode="before")
    @classmethod
    def normalize_crypto(cls, v: RuntimeForwardingBufferCrypto | str) -> object:
        return _normalize_enum(v, RuntimeForwardingBufferCrypto, field_name="crypto")


class RuntimeForwardingReloadChannel(SDLModel):
    """An observed downstream reload channel a content-sync agent drives.

    References the downstream consumer's control channel (e.g. the Suricata
    rule-reload socket) rather than inventing a parallel socket model; the
    inter-node trust edge is carried by ``RelationshipForwardingEdge``.
    """

    reload_channel_id: str
    target_ref: str = ""
    kind: RuntimeForwardingReloadChannelKind | str = RuntimeForwardingReloadChannelKind.UNKNOWN
    description: str = ""

    @field_validator("reload_channel_id")
    @classmethod
    def validate_reload_channel_id(cls, v: str) -> str:
        return require_symbol(v, field_name="reload_channel_id")

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, v: RuntimeForwardingReloadChannelKind | str) -> object:
        return _normalize_enum(v, RuntimeForwardingReloadChannelKind, field_name="kind")


class RuntimeForwardingSetting(SDLModel):
    """An observed forwarding-agent runtime setting with provenance and class.

    Settings that may carry credentials or operator-only values must omit their
    raw ``value`` and classify it ``redacted`` / ``operator_secret`` — enforced
    via the shared ``name_indicates_secret`` helper even when the submitter left
    ``classification`` at its default.
    """

    setting_id: str
    name: str = ""
    value: str = ""
    provenance: RuntimeForwardingSettingProvenance | str = RuntimeForwardingSettingProvenance.UNKNOWN
    classification: RuntimeForwardingSettingClassification | str = RuntimeForwardingSettingClassification.PLAIN
    description: str = ""

    @field_validator("setting_id")
    @classmethod
    def validate_setting_id(cls, v: str) -> str:
        return require_symbol(v, field_name="setting_id")

    @field_validator("provenance", mode="before")
    @classmethod
    def normalize_provenance(cls, v: RuntimeForwardingSettingProvenance | str) -> object:
        return _normalize_enum(v, RuntimeForwardingSettingProvenance, field_name="provenance")

    @field_validator("classification", mode="before")
    @classmethod
    def normalize_classification(cls, v: RuntimeForwardingSettingClassification | str) -> object:
        return _normalize_enum(v, RuntimeForwardingSettingClassification, field_name="classification")

    @model_validator(mode="after")
    def validate_setting(self) -> "RuntimeForwardingSetting":
        if _setting_name_is_concrete_secret(self.name):
            self._enforce_secret_name_redaction()
        elif self.value and self.classification in _REDACTED_SETTING_CLASSIFICATIONS:
            raise ValueError(
                f"forwarding setting '{self.setting_id}' classified '{self.classification}' must omit its raw value"
            )
        return self

    def _enforce_secret_name_redaction(self) -> None:
        if self.value:
            raise ValueError(
                f"forwarding setting '{self.setting_id}' carries a secret-bearing name and must omit its raw value "
                f"(classification must be 'redacted' or 'operator_secret')"
            )
        if not is_variable_ref(self.classification) and self.classification not in _REDACTED_SETTING_CLASSIFICATIONS:
            raise ValueError(
                f"forwarding setting '{self.setting_id}' carries a secret-bearing name; "
                f"classification must be 'redacted' or 'operator_secret'"
            )


class RuntimeForwardingAgent(SDLModel):
    """Node-scoped runtime inventory for a forwarding / intel-sync agent.

    The single forwarder spine. The ``agent_kind`` discriminator selects the
    required profile the ``require_profile_for_agent_kind`` guard enforces.
    Cadence composes a ``runtime.scheduled_jobs`` entry; the inter-node trust
    edge composes a ``RelationshipForwardingEdge`` — neither is re-typed here.
    """

    forwarding_agent_id: str
    implementation: RuntimeForwardingAgentImplementation | str = RuntimeForwardingAgentImplementation.UNKNOWN
    agent_kind: RuntimeForwardingAgentKind | str = RuntimeForwardingAgentKind.UNKNOWN
    version: str = ""
    name: str = ""
    sources: list[RuntimeForwardingSource] = Field(default_factory=list)
    transforms: list[RuntimeForwardingTransform] = Field(default_factory=list)
    ship_targets: list[RuntimeForwardingShipTarget] = Field(default_factory=list)
    buffer_policy: RuntimeForwardingBufferPolicy | None = None
    reload_channels: list[RuntimeForwardingReloadChannel] = Field(default_factory=list)
    settings: list[RuntimeForwardingSetting] = Field(default_factory=list)
    description: str = ""

    @field_validator("forwarding_agent_id")
    @classmethod
    def validate_forwarding_agent_id(cls, v: str) -> str:
        return require_symbol(v, field_name="forwarding_agent_id")

    @field_validator("implementation", mode="before")
    @classmethod
    def normalize_implementation(cls, v: RuntimeForwardingAgentImplementation | str) -> object:
        return _normalize_enum(v, RuntimeForwardingAgentImplementation, field_name="implementation")

    @field_validator("agent_kind", mode="before")
    @classmethod
    def normalize_agent_kind(cls, v: RuntimeForwardingAgentKind | str) -> object:
        return _normalize_enum(v, RuntimeForwardingAgentKind, field_name="agent_kind")

    @model_validator(mode="after")
    def validate_forwarding_agent(self) -> "RuntimeForwardingAgent":
        self._reject_duplicate_local_ref_ids()
        self.require_profile_for_agent_kind()
        return self

    # ------------------------------------------------------------------ #
    # Local stable-id uniqueness
    # ------------------------------------------------------------------ #

    def _reject_duplicate_local_ref_ids(self) -> None:
        entries: list[tuple[str, str]] = [("forwarding_agent_id", self.forwarding_agent_id)]
        if self.buffer_policy is not None:
            entries.append(("buffer_policy_id", self.buffer_policy.buffer_policy_id))
        for label, collection_name in (
            ("source_id", "sources"),
            ("transform_id", "transforms"),
            ("target_id", "ship_targets"),
            ("reload_channel_id", "reload_channels"),
            ("setting_id", "settings"),
        ):
            entries.extend((label, getattr(item, label)) for item in getattr(self, collection_name))

        seen: dict[str, str] = {}
        for label, value in entries:
            prior = seen.get(value)
            if prior is not None:
                raise ValueError(
                    f"Duplicate runtime forwarding agent stable id '{value}' in agent "
                    f"'{self.forwarding_agent_id}' across {prior} and {label}"
                )
            seen[value] = label

    # ------------------------------------------------------------------ #
    # Required-profile guard
    # ------------------------------------------------------------------ #

    def require_profile_for_agent_kind(self) -> None:
        """Fail validation when a concrete ``agent_kind`` lacks its profile.

        A ``${var}`` placeholder discriminator is exempt (nothing concrete is
        asserted); the OPEN ``unknown`` / ``other`` sentinels impose no profile
        (permissive tail). ``log_forwarder`` and ``content_sync`` each REQUIRE
        (and REJECT) specific child state per SCN-010 §5.5.
        """
        kind = self.agent_kind
        if is_variable_ref(kind) or not isinstance(kind, RuntimeForwardingAgentKind):
            return
        if kind is RuntimeForwardingAgentKind.LOG_FORWARDER:
            self._require_log_forwarder_profile()
        elif kind is RuntimeForwardingAgentKind.CONTENT_SYNC:
            self._require_content_sync_profile()
        # UNKNOWN / OTHER impose no profile by the enum-sentinel discipline.

    def _profile_error(self, requirement: str) -> ValueError:
        return ValueError(
            f"forwarding agent '{self.forwarding_agent_id}' agent_kind '{self.agent_kind.value}' requires {requirement}"
        )

    def _has_transform_kind(self, kind: RuntimeForwardingTransformKind) -> bool:
        return any(t.kind is kind for t in self.transforms)

    def _has_source_kind(self, kind: RuntimeForwardingSourceKind) -> bool:
        return any(s.kind is kind for s in self.sources)

    def _require_log_forwarder_profile(self) -> None:
        # REQUIRES a buffer_policy AND >=1 ship_target with an ingestion endpoint.
        if self.buffer_policy is None:
            raise self._profile_error("a buffer_policy")
        if not any(target.has_ingestion_endpoint() for target in self.ship_targets):
            raise self._profile_error(">=1 ship_target carrying an ingestion endpoint")
        # REJECTS any ioc_to_rule transform — that is the content_sync shape.
        if self._has_transform_kind(RuntimeForwardingTransformKind.IOC_TO_RULE):
            raise ValueError(
                f"forwarding agent '{self.forwarding_agent_id}' agent_kind 'log_forwarder' must not carry "
                f"a transform of kind 'ioc_to_rule'"
            )

    def _require_content_sync_profile(self) -> None:
        # REQUIRES >=1 api_pull source AND >=1 ioc_to_rule transform AND >=1 reload_channel.
        if not self._has_source_kind(RuntimeForwardingSourceKind.API_PULL):
            raise self._profile_error(">=1 source of kind 'api_pull'")
        if not self._has_transform_kind(RuntimeForwardingTransformKind.IOC_TO_RULE):
            raise self._profile_error(">=1 transform of kind 'ioc_to_rule'")
        if not self.reload_channels:
            raise self._profile_error(">=1 reload_channel")
        # REJECTS a buffer_policy and any ship_target enrollment endpoint.
        if self.buffer_policy is not None:
            raise ValueError(
                f"forwarding agent '{self.forwarding_agent_id}' agent_kind 'content_sync' must not carry "
                f"a buffer_policy"
            )
        offending = next((t for t in self.ship_targets if t.has_enrollment_endpoint()), None)
        if offending is not None:
            raise ValueError(
                f"forwarding agent '{self.forwarding_agent_id}' agent_kind 'content_sync' must not carry "
                f"a ship_target enrollment endpoint (ship_target '{offending.target_id}')"
            )
