"""Typed deterministic semantic addresses for authored historical objects."""

from __future__ import annotations

from typing import Annotated, Literal

from aces_sdl.identifiers import PortableIdentifier, require_qualified_identifier
from pydantic import AfterValidator, Field, model_validator

from .base import ContractModel, NonEmptyString
from .validators import _validate_unique_string_values

HISTORICAL_SEMANTIC_ADDRESS_PROFILE = "aces-historical-semantic-address/v1"
HISTORICAL_BASELINE_DIGEST_PROFILE = "aces-historical-baseline-digest/v1"
HistoricalSemanticAddressValue = Annotated[str, Field(pattern=r"^hsa1:[a-f0-9]{64}$")]
HistoricalBaselineDigestValue = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]


def _qualified_identifier(value: str) -> str:
    return require_qualified_identifier(value, field_name="historical semantic address coordinate")


QualifiedIdentifier = Annotated[str, AfterValidator(_qualified_identifier)]


class HistoricalSemanticAddressContextModel(ContractModel):
    """Closed v1 semantic coordinate, excluding provider and runtime identity."""

    address_profile: Literal["aces-historical-semantic-address/v1"]
    range_instance_id: QualifiedIdentifier
    deployment_tenant_id: QualifiedIdentifier
    reset_generation_id: QualifiedIdentifier
    baseline_id: QualifiedIdentifier
    baseline_version: NonEmptyString
    object_id: PortableIdentifier


class HistoricalSemanticAddressModel(ContractModel):
    """Derived domain-separated address plus its complete typed material."""

    profile: Literal["aces-historical-semantic-address/v1"]
    context: HistoricalSemanticAddressContextModel
    algorithm: Literal["sha256"]
    value: HistoricalSemanticAddressValue

    @model_validator(mode="after")
    def _profile_agrees_with_context(self) -> HistoricalSemanticAddressModel:
        if self.profile != self.context.address_profile:
            raise ValueError("historical semantic address profile must match context.address_profile")
        return self


class HistoricalBaselineDigestModel(ContractModel):
    """Domain-separated identity of one complete admitted historical baseline."""

    profile: Literal["aces-historical-baseline-digest/v1"]
    baseline_id: QualifiedIdentifier
    baseline_version: NonEmptyString
    algorithm: Literal["sha256"]
    value: HistoricalBaselineDigestValue


HistoricalMaterializationInterfaceProfile = Literal[
    "native-message/v1",
    "native-case/v1",
    "native-alert/v1",
    "native-ticket/v1",
    "native-dashboard/v1",
    "native-file/v1",
    "native-record/v1",
]
HistoricalMaterializationObjectKind = Literal[
    "message",
    "case",
    "alert",
    "ticket",
    "dashboard",
    "file",
    "record",
]


class HistoricalStateCapabilitiesModel(ContractModel):
    """Exact provider-neutral historical materialization support."""

    supported_interface_profiles: list[HistoricalMaterializationInterfaceProfile] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    supported_object_kinds: list[HistoricalMaterializationObjectKind] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )

    @model_validator(mode="after")
    def _validate_unique_capabilities(self) -> HistoricalStateCapabilitiesModel:
        _validate_unique_string_values("supported_interface_profiles", self.supported_interface_profiles)
        _validate_unique_string_values("supported_object_kinds", self.supported_object_kinds)
        expected_kinds = {
            profile.removeprefix("native-").removesuffix("/v1") for profile in self.supported_interface_profiles
        }
        if set(self.supported_object_kinds) != expected_kinds:
            raise ValueError(
                "historical-state interface profiles and object kinds must declare the same exact support pairs"
            )
        return self


__all__ = [
    "HISTORICAL_BASELINE_DIGEST_PROFILE",
    "HISTORICAL_SEMANTIC_ADDRESS_PROFILE",
    "HistoricalBaselineDigestModel",
    "HistoricalBaselineDigestValue",
    "HistoricalSemanticAddressContextModel",
    "HistoricalSemanticAddressModel",
    "HistoricalSemanticAddressValue",
    "HistoricalStateCapabilitiesModel",
]
