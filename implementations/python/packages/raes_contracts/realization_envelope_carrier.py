"""Published configuration-bound backend realization-envelope carrier."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from raes_contracts.contracts import ContractModel, NonEmptyString, RealizationEnvelopeIdentityModel
from raes_contracts.realization_envelope import RealizationEnvelopeModel

DigestString = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]


class ObservationStrength(str, Enum):
    """Strongest evidence a backend configuration emits for one concern."""

    NONE = "none"
    DRIVER_REPORTED = "driver-reported"
    DAEMON_OBSERVED = "daemon-observed"
    GUEST_OBSERVED = "guest-observed"


class ConcernDisposition(str, Enum):
    """How the selected realizer treats a governed concern."""

    REALIZED = "realized"
    TRANSFORMED = "transformed"
    DESCRIPTOR_ONLY = "descriptor-only"
    UNSUPPORTED = "unsupported"


class RealizationConcern(str, Enum):
    """Closed concern taxonomy shared by backend envelope artifacts."""

    TOPOLOGY = "topology"
    ARCHITECTURE = "architecture"
    IMAGE = "image"
    RESOURCE_ALLOCATION = "resource-allocation"
    NETWORK = "network"
    CONTENT_PLACEMENT = "content-placement"
    ACCOUNT_PLACEMENT = "account-placement"
    FEATURE_BINDING = "feature-binding"
    SERVICE = "service"
    ACL = "acl"


class TransformationKind(str, Enum):
    """Portable disclosure of a material realization transformation."""

    BOUNDED_NORMALIZATION = "bounded-normalization"
    DEFAULT_SUBSTITUTION = "default-substitution"
    DESCRIPTOR_SUBSTITUTION = "descriptor-substitution"
    IMAGE_SUBSTITUTION = "image-substitution"
    SERVICE_SYNTHESIS = "service-synthesis"


class IntegerBoundsModel(ContractModel):
    """Closed positive integer interval used by realizer resource claims."""

    minimum: int = Field(ge=1)
    maximum: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validate_bounds(self) -> IntegerBoundsModel:
        if self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("maximum must not be less than minimum")
        return self


class RealizerConfigurationModel(ContractModel):
    """Secret-free material configuration identity for one realizer mode."""

    mode: NonEmptyString
    configuration_digest: DigestString
    architecture: NonEmptyString
    image_policy: NonEmptyString
    network_policy: NonEmptyString
    supported_node_types: list[NonEmptyString] = Field(min_length=1)
    supported_os_families: list[NonEmptyString] = Field(min_length=1)
    supported_content_types: list[NonEmptyString] = Field(default_factory=list)
    supported_account_features: list[NonEmptyString] = Field(default_factory=list)
    supported_domain_profiles: list[NonEmptyString] = Field(default_factory=list)
    supports_acls: bool = False
    memory_mib: IntegerBoundsModel
    vcpus: IntegerBoundsModel

    @model_validator(mode="after")
    def _validate_unique_terms(self) -> RealizerConfigurationModel:
        for field_name in (
            "supported_node_types",
            "supported_os_families",
            "supported_content_types",
            "supported_account_features",
            "supported_domain_profiles",
        ):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler.resolve_ref_schema(handler(core_schema))
        properties = json_schema.get("properties", {})
        for field_name in (
            "supported_node_types",
            "supported_os_families",
            "supported_content_types",
            "supported_account_features",
            "supported_domain_profiles",
        ):
            properties[field_name]["uniqueItems"] = True
        return json_schema


class RealizationConcernDisclosureModel(ContractModel):
    """Typed support, transformation, and observation claim for one concern."""

    concern: RealizationConcern
    disposition: ConcernDisposition
    observation_strength: ObservationStrength
    mechanism: NonEmptyString | None = None
    transformations: list[TransformationKind] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_disposition(self) -> RealizationConcernDisclosureModel:
        if len(self.transformations) != len(set(self.transformations)):
            raise ValueError("transformations must not contain duplicates")
        if self.disposition is ConcernDisposition.TRANSFORMED and not self.transformations:
            raise ValueError("transformed disposition requires transformations")
        if self.disposition is not ConcernDisposition.TRANSFORMED and self.transformations:
            raise ValueError("transformations require transformed disposition")
        if self.disposition is ConcernDisposition.UNSUPPORTED:
            if self.observation_strength is not ObservationStrength.NONE or self.mechanism is not None:
                raise ValueError("unsupported disposition cannot claim observation or mechanism")
        elif self.observation_strength is ObservationStrength.NONE or self.mechanism is None:
            raise ValueError("supported dispositions require observation and mechanism")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler.resolve_ref_schema(handler(core_schema))
        json_schema["properties"]["transformations"]["uniqueItems"] = True
        json_schema.setdefault("allOf", []).extend(
            [
                {
                    "if": {"properties": {"disposition": {"const": "transformed"}}},
                    "then": {"properties": {"transformations": {"minItems": 1}}},
                    "else": {"properties": {"transformations": {"maxItems": 0}}},
                },
                {
                    "if": {"properties": {"disposition": {"const": "unsupported"}}},
                    "then": {
                        "properties": {
                            "observation_strength": {"const": "none"},
                            "mechanism": {"type": "null"},
                        }
                    },
                    "else": {
                        "properties": {
                            "observation_strength": {"not": {"const": "none"}},
                            "mechanism": {"type": "string", "minLength": 1},
                        }
                    },
                },
            ]
        )
        return json_schema


def realizer_configuration_digest(payload: Mapping[str, Any] | RealizerConfigurationModel) -> str:
    """Digest the closed, secret-free material configuration projection."""

    material = payload.model_dump(mode="json") if isinstance(payload, RealizerConfigurationModel) else dict(payload)
    material.pop("configuration_digest", None)
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def realization_envelope_digest(payload: Mapping[str, Any] | ContractModel) -> str:
    """Return the canonical digest of a published envelope, excluding its self-digest."""

    if isinstance(payload, BackendRealizationEnvelopeModel):
        material = payload.model_dump(mode="json")
    elif isinstance(payload, Mapping) and {"id", "expression", "configuration", "concerns"} <= payload.keys():
        material = {
            "schema_version": payload.get("schema_version", "realization-envelope/v1"),
            "contract_id": payload.get("contract_id", "realization-envelope-v1"),
            "id": payload["id"],
            "expression": RealizationEnvelopeModel.model_validate(payload["expression"]).model_dump(mode="json"),
            "configuration": RealizerConfigurationModel.model_validate(payload["configuration"]).model_dump(
                mode="json"
            ),
            "concerns": [
                RealizationConcernDisclosureModel.model_validate(claim).model_dump(mode="json")
                for claim in payload["concerns"]
            ],
        }
    else:
        material = payload.model_dump(mode="json") if isinstance(payload, ContractModel) else dict(payload)
    material.pop("digest", None)
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


class BackendRealizationEnvelopeModel(ContractModel):
    """Published backend carrier: shared set expression plus truthful realization claims."""

    schema_version: Literal["realization-envelope/v1"] = "realization-envelope/v1"
    contract_id: Literal["realization-envelope-v1"] = "realization-envelope-v1"
    id: NonEmptyString
    expression: RealizationEnvelopeModel
    configuration: RealizerConfigurationModel
    concerns: list[RealizationConcernDisclosureModel] = Field(min_length=1)
    digest: DigestString

    @model_validator(mode="after")
    def _validate_carrier(self) -> BackendRealizationEnvelopeModel:
        concern_values = [claim.concern for claim in self.concerns]
        if len(concern_values) != len(set(concern_values)):
            raise ValueError("concerns must not contain duplicate concern values")
        missing_concerns = set(RealizationConcern) - set(concern_values)
        if missing_concerns:
            missing = ", ".join(sorted(concern.value for concern in missing_concerns))
            raise ValueError(f"concerns must disclose every governed concern; missing: {missing}")
        if self.configuration.configuration_digest != realizer_configuration_digest(self.configuration):
            raise ValueError("realizer configuration digest does not match canonical content")
        expected = realization_envelope_digest(self)
        if self.digest != expected:
            raise ValueError("realization envelope digest does not match canonical content")
        return self

    @property
    def identity(self) -> RealizationEnvelopeIdentityModel:
        return RealizationEnvelopeIdentityModel(
            contract_id=self.contract_id,
            envelope_id=self.id,
            schema_version=self.schema_version,
            digest=self.digest,
            configuration_digest=self.configuration.configuration_digest,
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler.resolve_ref_schema(handler(core_schema))
        concerns = json_schema["properties"]["concerns"]
        concern_count = len(RealizationConcern)
        concerns["minItems"] = concern_count
        concerns["maxItems"] = concern_count
        concerns["allOf"] = [
            {
                "contains": {
                    "type": "object",
                    "required": ["concern"],
                    "properties": {"concern": {"const": concern.value}},
                },
                "minContains": 1,
                "maxContains": 1,
            }
            for concern in RealizationConcern
        ]
        json_schema["x-raes-invariants"] = [
            {
                "id": "realization-envelope-canonical-semantics-valid",
                "description": (
                    "Configuration bounds, expression references, canonical configuration and envelope digests, "
                    "and all cross-field realization disclosure semantics must validate together."
                ),
                "level": "error",
                "validator": "raes_contracts.realization_envelope.validate_backend_realization_envelope",
                "inputs": [{"contract_id": "realization-envelope-v1", "instance_path": "#"}],
            }
        ]
        return json_schema


def validate_backend_realization_envelope(payload: Mapping[str, Any]) -> BackendRealizationEnvelopeModel:
    """Apply the semantic-invariant validator named by the published schema."""

    return BackendRealizationEnvelopeModel.model_validate(payload)


__all__ = [
    "BackendRealizationEnvelopeModel",
    "ConcernDisposition",
    "IntegerBoundsModel",
    "ObservationStrength",
    "RealizationConcern",
    "RealizationConcernDisclosureModel",
    "RealizerConfigurationModel",
    "TransformationKind",
    "realization_envelope_digest",
    "realizer_configuration_digest",
    "validate_backend_realization_envelope",
]
