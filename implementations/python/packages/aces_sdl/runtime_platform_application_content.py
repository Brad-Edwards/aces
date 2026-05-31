"""Typed child models for the platform-applications runtime family.

These are the bounded, typed sub-collections held by
:class:`~aces_sdl.runtime_platform_application.RuntimePlatformApplication`:
content objects (bounded parsed manifests — never raw bodies), releasability
markings, organizations, tenants, outbound upstream bindings, connectors, the
optional execution policy, and provenance-bearing settings.
"""

from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from ._base import SDLModel, is_variable_ref, parse_int_or_var
from .runtime_platform_application_vocab import (
    RuntimePlatformApplicationConnectorKind,
    RuntimePlatformApplicationContentObjectKind,
    RuntimePlatformApplicationMarkingScheme,
    RuntimePlatformApplicationSettingClassification,
    RuntimePlatformApplicationSettingProvenance,
    RuntimePlatformApplicationUpstreamBindingRole,
)
from .runtime_values import (
    coerce_string_list,
    name_indicates_secret,
    parse_optional_bool_or_var,
    parse_runtime_enum_or_var,
    require_symbol,
)

__all__ = [
    "RuntimePlatformApplicationConnector",
    "RuntimePlatformApplicationContentObject",
    "RuntimePlatformApplicationExecutionPolicy",
    "RuntimePlatformApplicationMarking",
    "RuntimePlatformApplicationOrganization",
    "RuntimePlatformApplicationSetting",
    "RuntimePlatformApplicationTenant",
    "RuntimePlatformApplicationUpstreamBinding",
]

_OMIT_RAW_CLASSIFICATIONS: frozenset[RuntimePlatformApplicationSettingClassification] = frozenset(
    {
        RuntimePlatformApplicationSettingClassification.REDACTED,
        RuntimePlatformApplicationSettingClassification.OPERATOR_SECRET,
    }
)


def _normalize_enum(value: object, enum_cls: type[Enum], *, field_name: str) -> object:
    return parse_runtime_enum_or_var(value, enum_cls, field_name=field_name)


def _coerce_refs(value: object) -> object:
    return coerce_string_list(value)


def _reject_duplicate_values(values: list[object], *, field_name: str, owner: str) -> None:
    seen: set[object] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate runtime platform application {field_name} entry on '{owner}'")
        seen.add(value)


class RuntimePlatformApplicationOrganization(SDLModel):
    """An organization/owner tenant known to the platform application."""

    organization_id: str
    name: str = ""
    description: str = ""

    @field_validator("organization_id")
    @classmethod
    def validate_organization_id(cls, v: str) -> str:
        return require_symbol(v, field_name="organization_id")


class RuntimePlatformApplicationTenant(SDLModel):
    """A tenant/namespace scope within the platform application."""

    tenant_id: str
    name: str = ""
    description: str = ""

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        return require_symbol(v, field_name="tenant_id")


class RuntimePlatformApplicationContentObject(SDLModel):
    """A typed platform content object as a bounded parsed manifest entry.

    The object carries a typed ``kind``, bounded typed ``attributes``, typed
    ``references`` (to other ``content_object_id`` values), ``marking_refs``,
    and ``evidence_refs`` — structurally **never** a raw object body.
    """

    content_object_id: str
    kind: RuntimePlatformApplicationContentObjectKind | str = RuntimePlatformApplicationContentObjectKind.UNKNOWN
    name: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)
    references: list[str] = Field(default_factory=list)
    marking_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    description: str = ""

    @field_validator("content_object_id")
    @classmethod
    def validate_content_object_id(cls, v: str) -> str:
        return require_symbol(v, field_name="content_object_id")

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, v: RuntimePlatformApplicationContentObjectKind | str) -> object:
        return _normalize_enum(v, RuntimePlatformApplicationContentObjectKind, field_name="kind")

    @field_validator("references", "marking_refs", "evidence_refs", mode="before")
    @classmethod
    def coerce_ref_lists(cls, v: object) -> object:
        return _coerce_refs(v)

    @model_validator(mode="after")
    def validate_content_object(self) -> "RuntimePlatformApplicationContentObject":
        _reject_duplicate_values(self.references, field_name="references", owner=self.content_object_id)
        _reject_duplicate_values(self.marking_refs, field_name="marking_refs", owner=self.content_object_id)
        _reject_duplicate_values(self.evidence_refs, field_name="evidence_refs", owner=self.content_object_id)
        return self


class RuntimePlatformApplicationMarking(SDLModel):
    """A releasability marking (TLP/PAP/distribution) defined by the platform."""

    marking_id: str
    scheme: RuntimePlatformApplicationMarkingScheme | str = RuntimePlatformApplicationMarkingScheme.TLP
    level: str = ""
    value: str = ""
    description: str = ""

    @field_validator("marking_id")
    @classmethod
    def validate_marking_id(cls, v: str) -> str:
        return require_symbol(v, field_name="marking_id")

    @field_validator("scheme", mode="before")
    @classmethod
    def normalize_scheme(cls, v: RuntimePlatformApplicationMarkingScheme | str) -> object:
        return _normalize_enum(v, RuntimePlatformApplicationMarkingScheme, field_name="scheme")


class RuntimePlatformApplicationUpstreamBinding(SDLModel):
    """An outbound binding to an upstream node/service (data source, backend)."""

    binding_id: str
    role: RuntimePlatformApplicationUpstreamBindingRole | str = RuntimePlatformApplicationUpstreamBindingRole.UNKNOWN
    target_node_ref: str = ""
    target_service_ref: str = ""
    description: str = ""

    @field_validator("binding_id")
    @classmethod
    def validate_binding_id(cls, v: str) -> str:
        return require_symbol(v, field_name="binding_id")

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v: RuntimePlatformApplicationUpstreamBindingRole | str) -> object:
        return _normalize_enum(v, RuntimePlatformApplicationUpstreamBindingRole, field_name="role")


class RuntimePlatformApplicationConnector(SDLModel):
    """A connector/integration wired into the platform.

    A connector never carries a raw credential value; its credential posture is
    recorded purely via :attr:`credential_classification`.
    """

    connector_id: str
    kind: RuntimePlatformApplicationConnectorKind | str = RuntimePlatformApplicationConnectorKind.UNKNOWN
    name: str = ""
    enabled: bool | str | None = None
    credential_classification: RuntimePlatformApplicationSettingClassification | str = (
        RuntimePlatformApplicationSettingClassification.PLAIN
    )
    description: str = ""

    @field_validator("connector_id")
    @classmethod
    def validate_connector_id(cls, v: str) -> str:
        return require_symbol(v, field_name="connector_id")

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, v: RuntimePlatformApplicationConnectorKind | str) -> object:
        return _normalize_enum(v, RuntimePlatformApplicationConnectorKind, field_name="kind")

    @field_validator("credential_classification", mode="before")
    @classmethod
    def normalize_credential_classification(
        cls,
        v: RuntimePlatformApplicationSettingClassification | str,
    ) -> object:
        return _normalize_enum(
            v,
            RuntimePlatformApplicationSettingClassification,
            field_name="credential_classification",
        )

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_enabled(cls, v: object) -> bool | str | None:
        return parse_optional_bool_or_var(v, field_name="enabled")

    @model_validator(mode="after")
    def validate_connector(self) -> "RuntimePlatformApplicationConnector":
        self._enforce_secret_name_redaction()
        return self

    def _enforce_secret_name_redaction(self) -> None:
        """A secret-bearing connector name must carry a redaction classification."""
        if not self.name or is_variable_ref(self.name) or not name_indicates_secret(self.name):
            return
        if is_variable_ref(self.credential_classification):
            return
        if self.credential_classification not in _OMIT_RAW_CLASSIFICATIONS:
            raise ValueError(
                f"connector '{self.connector_id}' carries a secret-bearing name; "
                f"credential_classification must be 'redacted' or 'operator_secret'"
            )


class RuntimePlatformApplicationExecutionPolicy(SDLModel):
    """The platform's job/analyzer execution model (rate limits, runner)."""

    policy_id: str = ""
    runner: str = ""
    max_concurrent_jobs: int | str | None = None
    job_timeout: str = ""
    rate_limit: str = ""
    description: str = ""

    @field_validator("policy_id")
    @classmethod
    def validate_policy_id(cls, v: str) -> str:
        return require_symbol(v, field_name="policy_id") if v else v

    @field_validator("max_concurrent_jobs", mode="before")
    @classmethod
    def parse_max_concurrent_jobs(cls, v: object) -> object:
        return parse_int_or_var(v, minimum=0, field_name="max_concurrent_jobs") if v is not None else v


class RuntimePlatformApplicationSetting(SDLModel):
    """An observed platform setting with provenance and sensitivity.

    Settings whose name signals secret content must omit their raw ``value``
    and classify it as ``redacted`` / ``operator_secret``.
    """

    setting_id: str
    name: str = ""
    value: str = ""
    provenance: RuntimePlatformApplicationSettingProvenance | str = RuntimePlatformApplicationSettingProvenance.UNKNOWN
    classification: RuntimePlatformApplicationSettingClassification | str = (
        RuntimePlatformApplicationSettingClassification.PLAIN
    )
    redaction: str = ""
    description: str = ""

    @field_validator("setting_id")
    @classmethod
    def validate_setting_id(cls, v: str) -> str:
        return require_symbol(v, field_name="setting_id")

    @field_validator("provenance", mode="before")
    @classmethod
    def normalize_provenance(cls, v: RuntimePlatformApplicationSettingProvenance | str) -> object:
        return _normalize_enum(v, RuntimePlatformApplicationSettingProvenance, field_name="provenance")

    @field_validator("classification", mode="before")
    @classmethod
    def normalize_classification(cls, v: RuntimePlatformApplicationSettingClassification | str) -> object:
        return _normalize_enum(v, RuntimePlatformApplicationSettingClassification, field_name="classification")

    @model_validator(mode="after")
    def validate_setting(self) -> "RuntimePlatformApplicationSetting":
        if self._name_is_concrete_secret():
            self._enforce_secret_name_redaction()
        elif self.value and self.classification in _OMIT_RAW_CLASSIFICATIONS:
            raise ValueError(
                f"platform setting '{self.name}' classified '{self.classification}' must omit its raw value"
            )
        return self

    def _name_is_concrete_secret(self) -> bool:
        return bool(self.name) and not is_variable_ref(self.name) and name_indicates_secret(self.name)

    def _enforce_secret_name_redaction(self) -> None:
        if self.value:
            raise ValueError(
                f"platform setting '{self.name}' carries a secret-bearing name and must omit its raw value "
                f"(classification must be 'redacted' or 'operator_secret')"
            )
        if not is_variable_ref(self.classification) and self.classification not in _OMIT_RAW_CLASSIFICATIONS:
            raise ValueError(
                f"platform setting '{self.name}' carries a secret-bearing name; "
                f"classification must be 'redacted' or 'operator_secret'"
            )
