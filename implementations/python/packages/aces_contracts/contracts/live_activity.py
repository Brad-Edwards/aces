"""Deterministic live-activity compiled and occurrence identity contracts."""

from __future__ import annotations

import math
from typing import Annotated, Literal

from aces_sdl.identifiers import PortableIdentifier
from pydantic import Field, model_validator

from .base import ContractModel, NonEmptyString, NonNegativeInteger, PositiveInteger
from .historical_state import HistoricalBaselineDigestModel, QualifiedIdentifier
from .random_stream import GovernedEntropyRefModel, PublicSeedModel, RootEntropyModel
from .validators import _validate_unique_string_values

LIVE_ACTIVITY_PROFILE_DIGEST_PROFILE = "aces-live-activity-profile-digest/v1"
LIVE_ACTIVITY_OCCURRENCE_PROFILE = "aces-live-activity-occurrence/v1"
LiveActivityDigestValue = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
LiveActivityOccurrenceValue = Annotated[str, Field(pattern=r"^lao1:[a-f0-9]{64}$")]
LiveActivityContractProfile = Literal["aces-live-activity/v1"]
LiveActivityScheduleProfile = Literal["finite-logical-schedule/v1"]
LiveActivityReadbackProfile = Literal["evidence-readback/v1"]
LiveActivityLifecycleProfile = Literal["range-lifecycle/v1"]
LiveActivityResourceDimension = Literal["operations", "bytes", "connections", "cpu_milliseconds"]
LiveActivityDependencyKind = Literal["ordering", "refresh"]
LiveActivityOperationProfile = Annotated[
    str,
    Field(pattern=r"^protocol-operation/v1:[a-z_]+:[a-z_]+$"),
]
_LIVE_ACTIVITY_PROTOCOLS = frozenset({"http_api", "smtp", "imap", "ldap", "database", "file_service"})
_LIVE_ACTIVITY_OPERATIONS = frozenset(
    {"create", "read", "update", "delete", "send", "receive", "query", "list", "authenticate"}
)


class ActivityProfileDigestModel(ContractModel):
    profile: Literal["aces-live-activity-profile-digest/v1"]
    activity_profile_id: QualifiedIdentifier
    activity_profile_version: NonEmptyString
    historical_baseline_digest: LiveActivityDigestValue
    algorithm: Literal["sha256"]
    value: LiveActivityDigestValue


ActivityPublicSeedIdentityModel = PublicSeedModel
ActivityGovernedEntropyIdentityModel = GovernedEntropyRefModel
ActivityEntropyIdentityModel = RootEntropyModel


class CompiledActivityActionModel(ContractModel):
    action_id: QualifiedIdentifier
    template_id: QualifiedIdentifier
    execution_context_id: QualifiedIdentifier
    target_service_id: QualifiedIdentifier
    operation_profile: NonEmptyString
    schedule_profile: NonEmptyString
    schedule_anchor_seconds: NonNegativeInteger
    schedule_interval_seconds: PositiveInteger
    max_occurrences: PositiveInteger
    max_retry_attempts: PositiveInteger
    random_stream_profile: NonEmptyString
    transform_profile: NonEmptyString
    address_profile: NonEmptyString
    readback_profile: NonEmptyString
    lifecycle_profile: NonEmptyString
    ordering_dependencies: list[PortableIdentifier] = Field(default_factory=list)
    refresh_dependencies: list[PortableIdentifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_dependencies(self) -> CompiledActivityActionModel:
        for field_name in ("ordering_dependencies", "refresh_dependencies"):
            values = getattr(self, field_name)
            _validate_unique_string_values(field_name, values)
        return self


class ActivityRationalQuantityModel(ContractModel):
    numerator: NonNegativeInteger
    denominator: PositiveInteger

    @model_validator(mode="after")
    def _lowest_terms(self) -> ActivityRationalQuantityModel:
        if math.gcd(self.numerator, self.denominator) != 1:
            raise ValueError("activity rational quantities must be in lowest terms")
        return self


class CompiledActivityBudgetEnvelopeModel(ContractModel):
    dimension: Literal["operations", "bytes", "connections", "cpu_milliseconds"]
    unit: Literal["operation", "byte", "connection", "cpu_millisecond"]
    window_seconds: PositiveInteger
    action_demands: dict[PortableIdentifier, ActivityRationalQuantityModel] = Field(min_length=1)
    range_capacity: ActivityRationalQuantityModel
    fleet_capacity: ActivityRationalQuantityModel
    participant_reservation: ActivityRationalQuantityModel


class CompiledActivityProfileModel(ContractModel):
    contract_profile: Literal["aces-live-activity/v1"]
    activity_profile_id: QualifiedIdentifier
    activity_profile_version: NonEmptyString
    activity_digest: ActivityProfileDigestModel
    baseline_digest: HistoricalBaselineDigestModel
    deployment_tenant_id: QualifiedIdentifier
    range_instance_id: QualifiedIdentifier
    reset_generation_id: QualifiedIdentifier
    entropy_identity: ActivityEntropyIdentityModel
    actions: dict[PortableIdentifier, CompiledActivityActionModel] = Field(min_length=1)
    budget_envelopes: list[CompiledActivityBudgetEnvelopeModel] = Field(min_length=1)
    dependency_order: list[PortableIdentifier] = Field(min_length=1)
    reverse_teardown_order: list[PortableIdentifier] = Field(min_length=1)
    required_operation_profiles: list[NonEmptyString] = Field(min_length=1)
    required_schedule_profiles: list[NonEmptyString] = Field(min_length=1)
    required_readback_profiles: list[NonEmptyString] = Field(min_length=1)
    required_lifecycle_profiles: list[NonEmptyString] = Field(min_length=1)
    required_resource_dimensions: list[NonEmptyString] = Field(min_length=1)
    required_dependency_kinds: list[NonEmptyString] = Field(default_factory=list)
    requires_bounded_retry: Literal[True] = True
    requires_generation_lifecycle: Literal[True] = True
    requires_participant_reservation: Literal[True] = True
    requires_readback_provenance: Literal[True] = True

    @model_validator(mode="after")
    def _validate_compiled_identity(self) -> CompiledActivityProfileModel:
        if self.activity_digest.activity_profile_id != self.activity_profile_id:
            raise ValueError("compiled activity profile id must match its digest carrier")
        if self.activity_digest.historical_baseline_digest != self.baseline_digest.value:
            raise ValueError("compiled activity profile digest must reuse the exact historical baseline digest")
        if set(self.actions) != set(self.dependency_order):
            raise ValueError("compiled activity dependency order must cover every action exactly")
        if self.reverse_teardown_order != list(reversed(self.dependency_order)):
            raise ValueError("compiled activity reverse teardown order must reverse dependency order")
        dimensions = [budget.dimension for budget in self.budget_envelopes]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("compiled activity budget dimensions must be unique")
        if sorted(dimensions) != sorted(self.required_resource_dimensions):
            raise ValueError("compiled activity budget dimensions must match required resource dimensions")
        return self


class ActivityOccurrenceContextModel(ContractModel):
    occurrence_profile: Literal["aces-live-activity-occurrence/v1"]
    deployment_tenant_id: QualifiedIdentifier
    range_instance_id: QualifiedIdentifier
    reset_generation_id: QualifiedIdentifier
    activity_profile_id: QualifiedIdentifier
    activity_digest: LiveActivityDigestValue
    historical_baseline_digest: LiveActivityDigestValue
    logical_time_seconds: NonNegativeInteger
    occurrence_ordinal: NonNegativeInteger
    action_id: QualifiedIdentifier
    template_id: QualifiedIdentifier
    execution_context_id: QualifiedIdentifier
    target_service_id: QualifiedIdentifier
    entropy_identity: ActivityEntropyIdentityModel
    random_stream_profile: NonEmptyString
    schedule_profile: NonEmptyString
    transform_profile: NonEmptyString
    address_profile: NonEmptyString


class ActivityOccurrenceIdentityModel(ContractModel):
    profile: Literal["aces-live-activity-occurrence/v1"]
    context: ActivityOccurrenceContextModel
    algorithm: Literal["sha256"]
    value: LiveActivityOccurrenceValue

    @model_validator(mode="after")
    def _profile_agreement(self) -> ActivityOccurrenceIdentityModel:
        if self.profile != self.context.occurrence_profile:
            raise ValueError("activity occurrence profile must match its context")
        return self


class LiveActivityCapabilitiesModel(ContractModel):
    supported_contract_profiles: list[LiveActivityContractProfile] = Field(default_factory=list, max_length=1)
    supported_operation_profiles: list[LiveActivityOperationProfile] = Field(default_factory=list, max_length=64)
    supported_schedule_profiles: list[LiveActivityScheduleProfile] = Field(default_factory=list, max_length=1)
    supported_readback_profiles: list[LiveActivityReadbackProfile] = Field(default_factory=list, max_length=1)
    supported_lifecycle_profiles: list[LiveActivityLifecycleProfile] = Field(default_factory=list, max_length=1)
    supported_resource_dimensions: list[LiveActivityResourceDimension] = Field(default_factory=list, max_length=4)
    supported_dependency_kinds: list[LiveActivityDependencyKind] = Field(default_factory=list, max_length=2)
    supports_bounded_retry: bool = False
    supports_generation_lifecycle: bool = False
    supports_participant_reservation: bool = False
    supports_readback_provenance: bool = False

    @model_validator(mode="after")
    def _unique_capability_terms(self) -> LiveActivityCapabilitiesModel:
        for field_name in (
            "supported_contract_profiles",
            "supported_operation_profiles",
            "supported_schedule_profiles",
            "supported_readback_profiles",
            "supported_lifecycle_profiles",
            "supported_resource_dimensions",
            "supported_dependency_kinds",
        ):
            _validate_unique_string_values(field_name, getattr(self, field_name))
        for profile in self.supported_operation_profiles:
            _prefix, protocol, operation = profile.split(":")
            if protocol not in _LIVE_ACTIVITY_PROTOCOLS or operation not in _LIVE_ACTIVITY_OPERATIONS:
                raise ValueError(f"unsupported governed live activity operation profile {profile!r}")
        return self


__all__ = [
    "LIVE_ACTIVITY_OCCURRENCE_PROFILE",
    "LIVE_ACTIVITY_PROFILE_DIGEST_PROFILE",
    "ActivityEntropyIdentityModel",
    "ActivityGovernedEntropyIdentityModel",
    "ActivityOccurrenceContextModel",
    "ActivityOccurrenceIdentityModel",
    "ActivityProfileDigestModel",
    "ActivityPublicSeedIdentityModel",
    "ActivityRationalQuantityModel",
    "CompiledActivityActionModel",
    "CompiledActivityBudgetEnvelopeModel",
    "CompiledActivityProfileModel",
    "LiveActivityDigestValue",
    "LiveActivityOccurrenceValue",
    "LiveActivityCapabilitiesModel",
]
