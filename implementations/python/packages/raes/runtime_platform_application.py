"""Platform-application runtime inventory family (RuntimePlatformApplication).

A single discriminated spine for the SCN-010 platform-application cluster
(analytics dashboard, threat-intelligence platform, case management, analyzer
engine, SOAR). The ``platform_kind`` discriminator selects the family member;
the ``require_profile_for_platform_kind`` after-validator makes each member's
defining content/binding profile executable so an under-populated instance
fails validation rather than silently shallow-encoding a defining fact.

The app's internal RBAC store is delegated to ``app_authorization`` via the
string ``authorization_ref`` (resolved by the semantic validator) and is never
re-typed here. Content objects are bounded parsed manifests — typed kind +
bounded attributes + typed references — never raw object bodies.
"""

from pydantic import Field, field_validator, model_validator

from ._base import SDLModel, is_variable_ref
from .runtime_platform_application_content import (
    RuntimePlatformApplicationConnector,
    RuntimePlatformApplicationContentObject,
    RuntimePlatformApplicationExecutionPolicy,
    RuntimePlatformApplicationMarking,
    RuntimePlatformApplicationOrganization,
    RuntimePlatformApplicationSetting,
    RuntimePlatformApplicationTenant,
    RuntimePlatformApplicationUpstreamBinding,
)
from .runtime_platform_application_vocab import (
    RelationshipServiceIntegrationDirection,
    RelationshipServiceIntegrationKind,
    RuntimePlatformApplicationConnectorKind,
    RuntimePlatformApplicationContentObjectKind,
    RuntimePlatformApplicationKind,
    RuntimePlatformApplicationMarkingScheme,
    RuntimePlatformApplicationSettingClassification,
    RuntimePlatformApplicationSettingProvenance,
    RuntimePlatformApplicationUpstreamBindingRole,
)
from .runtime_values import parse_optional_bool_or_var, parse_runtime_enum_or_var, require_symbol

__all__ = [
    "RelationshipServiceIntegration",
    "RelationshipServiceIntegrationDirection",
    "RelationshipServiceIntegrationKind",
    "RuntimePlatformApplication",
    "RuntimePlatformApplicationConnector",
    "RuntimePlatformApplicationConnectorKind",
    "RuntimePlatformApplicationContentObject",
    "RuntimePlatformApplicationContentObjectKind",
    "RuntimePlatformApplicationExecutionPolicy",
    "RuntimePlatformApplicationKind",
    "RuntimePlatformApplicationMarking",
    "RuntimePlatformApplicationMarkingScheme",
    "RuntimePlatformApplicationOrganization",
    "RuntimePlatformApplicationSetting",
    "RuntimePlatformApplicationSettingClassification",
    "RuntimePlatformApplicationSettingProvenance",
    "RuntimePlatformApplicationTenant",
    "RuntimePlatformApplicationUpstreamBinding",
    "RuntimePlatformApplicationUpstreamBindingRole",
]

_Kind = RuntimePlatformApplicationKind
_ContentKind = RuntimePlatformApplicationContentObjectKind
_BindingRole = RuntimePlatformApplicationUpstreamBindingRole

# Saved-object kinds that satisfy the analytics_dashboard content requirement.
_DASHBOARD_SAVED_OBJECT_KINDS: frozenset[RuntimePlatformApplicationContentObjectKind] = frozenset(
    {
        _ContentKind.INDEX_PATTERN,
        _ContentKind.VISUALIZATION,
        _ContentKind.DASHBOARD,
        _ContentKind.SEARCH,
    }
)

# Upstream-binding roles that satisfy the analytics_dashboard backing requirement.
_DASHBOARD_BACKING_ROLES: frozenset[RuntimePlatformApplicationUpstreamBindingRole] = frozenset(
    {_BindingRole.INDEX_BACKEND, _BindingRole.DATA_SOURCE}
)


class RuntimePlatformApplication(SDLModel):
    """Node-scoped runtime inventory for a security platform application.

    ``service`` references the owning same-node ``Node.services[].name``. The
    inventory is observation metadata above transport; it never duplicates the
    inbound HTTP route surface (``runtime.applications``) or mutates
    ``Node.services``. ``authorization_ref`` is the ``app_authorization_id`` of
    the platform's internal RBAC store (resolved by the semantic validator).
    """

    platform_application_id: str
    service: str = ""
    platform_kind: RuntimePlatformApplicationKind | str = RuntimePlatformApplicationKind.UNKNOWN
    product: str = ""
    version: str = ""
    name: str = ""
    organizations: list[RuntimePlatformApplicationOrganization] = Field(default_factory=list)
    tenants: list[RuntimePlatformApplicationTenant] = Field(default_factory=list)
    content_objects: list[RuntimePlatformApplicationContentObject] = Field(default_factory=list)
    markings: list[RuntimePlatformApplicationMarking] = Field(default_factory=list)
    upstream_bindings: list[RuntimePlatformApplicationUpstreamBinding] = Field(default_factory=list)
    connectors: list[RuntimePlatformApplicationConnector] = Field(default_factory=list)
    execution_policy: RuntimePlatformApplicationExecutionPolicy | None = None
    settings: list[RuntimePlatformApplicationSetting] = Field(default_factory=list)
    authorization_ref: str = ""
    description: str = ""

    @field_validator("platform_application_id")
    @classmethod
    def validate_platform_application_id(cls, v: str) -> str:
        return require_symbol(v, field_name="platform_application_id")

    @field_validator("platform_kind", mode="before")
    @classmethod
    def normalize_platform_kind(cls, v: RuntimePlatformApplicationKind | str) -> object:
        return parse_runtime_enum_or_var(v, RuntimePlatformApplicationKind, field_name="platform_kind")

    @model_validator(mode="after")
    def validate_platform_application(self) -> "RuntimePlatformApplication":
        self._reject_duplicate_local_ref_ids()
        self.require_profile_for_platform_kind()
        return self

    # ------------------------------------------------------------------ #
    # Local stable-id uniqueness
    # ------------------------------------------------------------------ #

    def _reject_duplicate_local_ref_ids(self) -> None:
        entries: list[tuple[str, str]] = [("platform_application_id", self.platform_application_id)]
        for label, collection_name in (
            ("organization_id", "organizations"),
            ("tenant_id", "tenants"),
            ("content_object_id", "content_objects"),
            ("marking_id", "markings"),
            ("binding_id", "upstream_bindings"),
            ("connector_id", "connectors"),
            ("setting_id", "settings"),
        ):
            entries.extend((label, getattr(item, label)) for item in getattr(self, collection_name))

        seen: dict[str, str] = {}
        for label, value in entries:
            prior = seen.get(value)
            if prior is not None:
                raise ValueError(
                    f"Duplicate runtime platform application stable id '{value}' in application "
                    f"'{self.platform_application_id}' across {prior} and {label}"
                )
            seen[value] = label

    # ------------------------------------------------------------------ #
    # Required-profile guard
    # ------------------------------------------------------------------ #

    def require_profile_for_platform_kind(self) -> None:
        """Fail validation when a concrete platform_kind lacks its profile.

        A ``${var}`` placeholder discriminator is exempt (nothing concrete is
        asserted); ``unknown`` / ``other`` are permissive. Each concrete member
        requires the defining content/binding profile so the abstraction cannot
        silently shallow-encode a defining fact.
        """
        kind = self.platform_kind
        if is_variable_ref(kind) or not isinstance(kind, RuntimePlatformApplicationKind):
            return
        profile = _PROFILE_DISPATCH.get(kind)
        if profile is None:
            return
        profile(self)

    def _content_kinds(self) -> set[object]:
        return {obj.kind for obj in self.content_objects}

    def _has_content_kind(self, kind: RuntimePlatformApplicationContentObjectKind) -> bool:
        return any(obj.kind == kind for obj in self.content_objects)

    def _require_content_kind(self, kind: RuntimePlatformApplicationContentObjectKind) -> None:
        if not self._has_content_kind(kind):
            raise self._profile_error(f">=1 content_object with kind '{kind.value}'")

    def _profile_error(self, requirement: str) -> ValueError:
        return ValueError(
            f"platform application '{self.platform_application_id}' platform_kind "
            f"'{self.platform_kind.value}' requires {requirement}"
        )

    def _require_threat_intel_profile(self) -> None:
        for kind in (
            _ContentKind.TAXONOMY,
            _ContentKind.GALAXY_CLUSTER,
            _ContentKind.WARNINGLIST,
            _ContentKind.FEED,
            _ContentKind.SHARING_GROUP,
        ):
            self._require_content_kind(kind)

    def _require_soar_profile(self) -> None:
        self._require_content_kind(_ContentKind.WORKFLOW)

    def _require_analyzer_engine_profile(self) -> None:
        if not (self._has_content_kind(_ContentKind.ANALYZER) or self._has_content_kind(_ContentKind.RESPONDER)):
            raise self._profile_error(">=1 analyzer or responder content_object")
        if self.execution_policy is None:
            raise self._profile_error("an execution_policy")

    def _require_case_management_profile(self) -> None:
        self._require_content_kind(_ContentKind.CASE_TEMPLATE)
        self._require_content_kind(_ContentKind.CUSTOM_FIELD)

    def _require_analytics_dashboard_profile(self) -> None:
        saved_objects = [obj for obj in self.content_objects if obj.kind in _DASHBOARD_SAVED_OBJECT_KINDS]
        if not saved_objects:
            kinds = ", ".join(sorted(k.value for k in _DASHBOARD_SAVED_OBJECT_KINDS))
            raise self._profile_error(f">=1 saved-object content_object (one of: {kinds})")
        if not any(obj.references for obj in saved_objects):
            raise self._profile_error(">=1 saved-object content_object that carries references")
        if not any(
            isinstance(b.role, RuntimePlatformApplicationUpstreamBindingRole) and b.role in _DASHBOARD_BACKING_ROLES
            for b in self.upstream_bindings
        ):
            roles = ", ".join(sorted(r.value for r in _DASHBOARD_BACKING_ROLES))
            raise self._profile_error(f">=1 upstream_binding with role one of: {roles}")


_PROFILE_DISPATCH = {
    _Kind.THREAT_INTEL: RuntimePlatformApplication._require_threat_intel_profile,
    _Kind.SOAR: RuntimePlatformApplication._require_soar_profile,
    _Kind.ANALYZER_ENGINE: RuntimePlatformApplication._require_analyzer_engine_profile,
    _Kind.CASE_MANAGEMENT: RuntimePlatformApplication._require_case_management_profile,
    _Kind.ANALYTICS_DASHBOARD: RuntimePlatformApplication._require_analytics_dashboard_profile,
}


class RelationshipServiceIntegration(SDLModel):
    """Typed service-integration detail carried by a top-level relationship edge.

    When a consumer application integrates with a platform engine (analyzer,
    responder, webhook, notification, or enrichment), the relationship's
    endpoints resolve to the two platform applications and this block keeps the
    ``integration_kind``, ``auth_principal_ref`` (an ``app_authorization``
    ``principal_id`` in the target), and ``direction`` structurally validated
    rather than recorded as prose. ``consumer_ref``/``engine_ref`` are the
    ``platform_application_id`` symbols of the two endpoints; a ``${var}``
    placeholder is permitted in those refs.
    """

    consumer_ref: str = ""
    engine_ref: str = ""
    integration_kind: RelationshipServiceIntegrationKind | str = RelationshipServiceIntegrationKind.UNKNOWN
    auth_principal_ref: str = ""
    enabled: bool | str | None = None
    direction: RelationshipServiceIntegrationDirection | str = RelationshipServiceIntegrationDirection.BIDIRECTIONAL
    description: str = ""

    @field_validator("integration_kind", mode="before")
    @classmethod
    def normalize_integration_kind(
        cls, v: RelationshipServiceIntegrationKind | str
    ) -> RelationshipServiceIntegrationKind | str:
        return parse_runtime_enum_or_var(v, RelationshipServiceIntegrationKind, field_name="integration_kind")

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(
        cls, v: RelationshipServiceIntegrationDirection | str
    ) -> RelationshipServiceIntegrationDirection | str:
        return parse_runtime_enum_or_var(v, RelationshipServiceIntegrationDirection, field_name="direction")

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_enabled(cls, v: bool | str | None) -> bool | str | None:
        return parse_optional_bool_or_var(v, field_name="enabled")
