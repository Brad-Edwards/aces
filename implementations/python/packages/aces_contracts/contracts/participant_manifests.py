"""Backend-manifest and participant-implementation manifest contracts."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from ..manifest_authority import (
    BACKEND_SUPPORTED_CONTRACT_IDS,
    PARTICIPANT_IMPLEMENTATION_SUPPORTED_CONTRACT_IDS,
    validate_backend_supported_contract_versions,
    validate_participant_implementation_supported_contract_versions,
    validate_participant_supported_contract_versions,
)
from ..versions import (
    BACKEND_MANIFEST_V2_SCHEMA_VERSION,
    PARTICIPANT_IMPLEMENTATION_MANIFEST_V1_SCHEMA_VERSION,
    PARTICIPANT_IMPLEMENTATION_PROVENANCE_V1_SCHEMA_VERSION,
)
from .base import (
    _BACKEND_CONCEPT_BINDING_SCOPES,
    _PARTICIPANT_IMPLEMENTATION_CONCEPT_BINDING_SCOPES,
    ContractModel,
    NonEmptyString,
)
from .capabilities import (
    ApparatusIdentityModel,
    BackendCompatibilityModel,
    RealizationSupportDeclarationModel,
)
from .manifests import BackendCapabilitiesV2Model, ConceptBindingEntryModel
from .realization_plans import RealizationEnvelopeIdentityModel
from .validators import (
    _validate_canonical_concept_bindings,
    _validate_controlled_vocabulary_terms,
    _validate_unique_string_values,
)


class BackendManifestV2Model(ContractModel):
    schema_version: Literal[BACKEND_MANIFEST_V2_SCHEMA_VERSION] = BACKEND_MANIFEST_V2_SCHEMA_VERSION
    identity: ApparatusIdentityModel
    supported_contract_versions: list[NonEmptyString] = Field(min_length=1)
    compatibility: BackendCompatibilityModel
    realization_support: list[RealizationSupportDeclarationModel] = Field(min_length=1)
    realization_envelope: RealizationEnvelopeIdentityModel | None = None
    concept_bindings: list[ConceptBindingEntryModel] = Field(min_length=1)
    constraints: dict[str, str] = Field(default_factory=dict)
    capabilities: BackendCapabilitiesV2Model

    @model_validator(mode="after")
    def _validate_unique_binding_scopes(self) -> BackendManifestV2Model:
        validate_backend_supported_contract_versions(self.supported_contract_versions)
        envelope_contract_declared = "realization-envelope-v1" in self.supported_contract_versions
        if self.realization_envelope is not None and not envelope_contract_declared:
            raise ValueError("realization_envelope requires realization-envelope-v1 support")
        if envelope_contract_declared and self.realization_envelope is None:
            raise ValueError("realization-envelope-v1 support requires realization_envelope identity")
        scopes = [binding.scope for binding in self.concept_bindings]
        if len(scopes) != len(set(scopes)):
            raise ValueError("concept_bindings must not contain duplicate scopes")
        _validate_canonical_concept_bindings(self, allowed_scopes=_BACKEND_CONCEPT_BINDING_SCOPES)
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["properties"]["supported_contract_versions"]["items"]["enum"] = list(BACKEND_SUPPORTED_CONTRACT_IDS)
        json_schema.setdefault("allOf", []).extend(
            [
                {
                    "if": {
                        "properties": {"realization_envelope": {"not": {"type": "null"}}},
                        "required": ["realization_envelope"],
                    },
                    "then": {
                        "properties": {
                            "supported_contract_versions": {"contains": {"const": "realization-envelope-v1"}}
                        }
                    },
                },
                {
                    "if": {
                        "properties": {
                            "supported_contract_versions": {"contains": {"const": "realization-envelope-v1"}}
                        },
                        "required": ["supported_contract_versions"],
                    },
                    "then": {
                        "properties": {"realization_envelope": {"not": {"type": "null"}}},
                        "required": ["realization_envelope"],
                    },
                },
            ]
        )
        return json_schema


class ParticipantImplementationCompatibilityModel(ContractModel):
    participant_runtimes: list[NonEmptyString] = Field(default_factory=list)
    processors: list[NonEmptyString] = Field(default_factory=list)
    backends: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_non_empty_compatibility(self) -> ParticipantImplementationCompatibilityModel:
        _validate_unique_string_values("participant_runtimes", self.participant_runtimes)
        _validate_unique_string_values("processors", self.processors)
        _validate_unique_string_values("backends", self.backends)
        if not (self.participant_runtimes or self.processors or self.backends):
            raise ValueError(
                "compatibility must declare at least one participant runtime, processor, or backend surface"
            )
        return self


class ParticipantImplementationCapabilitiesModel(ContractModel):
    supported_participant_contracts: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    supported_decision_surface_modes: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    tool_affordance_expectations: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    exposure_policy_kinds: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )

    @model_validator(mode="after")
    def _validate_participant_implementation_capabilities(self) -> ParticipantImplementationCapabilitiesModel:
        _validate_unique_string_values("supported_participant_contracts", self.supported_participant_contracts)
        _validate_unique_string_values("supported_decision_surface_modes", self.supported_decision_surface_modes)
        _validate_unique_string_values("tool_affordance_expectations", self.tool_affordance_expectations)
        _validate_unique_string_values("exposure_policy_kinds", self.exposure_policy_kinds)
        validate_participant_supported_contract_versions(self.supported_participant_contracts)
        _validate_controlled_vocabulary_terms(
            "capabilities.supported_participant_contracts",
            self.supported_participant_contracts,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.supported_decision_surface_modes",
            self.supported_decision_surface_modes,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.tool_affordance_expectations",
            self.tool_affordance_expectations,
        )
        _validate_controlled_vocabulary_terms("capabilities.exposure_policy_kinds", self.exposure_policy_kinds)
        return self


class ParticipantImplementationManifestModel(ContractModel):
    schema_version: Literal[PARTICIPANT_IMPLEMENTATION_MANIFEST_V1_SCHEMA_VERSION] = (
        PARTICIPANT_IMPLEMENTATION_MANIFEST_V1_SCHEMA_VERSION
    )
    identity: ApparatusIdentityModel
    implementation_kind: NonEmptyString
    supported_contract_versions: list[NonEmptyString] = Field(min_length=1)
    compatibility: ParticipantImplementationCompatibilityModel
    concept_bindings: list[ConceptBindingEntryModel] = Field(min_length=1)
    constraints: dict[str, str] = Field(default_factory=dict)
    capabilities: ParticipantImplementationCapabilitiesModel

    @model_validator(mode="after")
    def _validate_participant_implementation_manifest(self) -> ParticipantImplementationManifestModel:
        validate_participant_implementation_supported_contract_versions(self.supported_contract_versions)
        _validate_unique_string_values("supported_contract_versions", self.supported_contract_versions)
        _validate_controlled_vocabulary_terms("implementation_kind", [self.implementation_kind])
        unsupported = sorted(
            set(self.capabilities.supported_participant_contracts) - set(self.supported_contract_versions)
        )
        if unsupported:
            joined = ", ".join(unsupported)
            raise ValueError(
                "supported_participant_contracts must be declared in supported_contract_versions: " + joined
            )
        scopes = [binding.scope for binding in self.concept_bindings]
        if len(scopes) != len(set(scopes)):
            raise ValueError("concept_bindings must not contain duplicate scopes")
        _validate_canonical_concept_bindings(
            self,
            allowed_scopes=_PARTICIPANT_IMPLEMENTATION_CONCEPT_BINDING_SCOPES,
        )
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["properties"]["supported_contract_versions"]["items"]["enum"] = list(
            PARTICIPANT_IMPLEMENTATION_SUPPORTED_CONTRACT_IDS
        )
        return json_schema


DigestString = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]


class ParticipantExposurePolicyModel(ContractModel):
    policy_id: NonEmptyString
    policy_version: NonEmptyString | None = None
    policy_digest: DigestString | None = None
    exposure_policy_kinds: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    disclosed_refs: list[NonEmptyString] = Field(default_factory=list)
    withheld_refs: list[NonEmptyString] = Field(default_factory=list)
    tool_affordance_refs: list[NonEmptyString] = Field(default_factory=list)
    visibility_scope_refs: list[NonEmptyString] = Field(default_factory=list)
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_exposure_policy(self) -> ParticipantExposurePolicyModel:
        _validate_unique_string_values("exposure_policy_kinds", self.exposure_policy_kinds)
        _validate_unique_string_values("disclosed_refs", self.disclosed_refs)
        _validate_unique_string_values("withheld_refs", self.withheld_refs)
        _validate_unique_string_values("tool_affordance_refs", self.tool_affordance_refs)
        _validate_unique_string_values("visibility_scope_refs", self.visibility_scope_refs)
        _validate_controlled_vocabulary_terms("capabilities.exposure_policy_kinds", self.exposure_policy_kinds)
        if not (self.disclosed_refs or self.withheld_refs or self.tool_affordance_refs or self.visibility_scope_refs):
            raise ValueError(
                "exposure policy must declare disclosed_refs, withheld_refs, "
                "tool_affordance_refs, or visibility_scope_refs"
            )
        return self


class ParticipantImplementationSelectionModel(ContractModel):
    participant_address: NonEmptyString
    implementation_identity: ApparatusIdentityModel
    manifest_ref: NonEmptyString
    manifest_digest: DigestString
    configuration_ref: NonEmptyString | None = None
    configuration_digest: DigestString | None = None
    selected_decision_surface_mode: NonEmptyString
    participant_contract_versions: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    exposure_policy: ParticipantExposurePolicyModel

    @model_validator(mode="after")
    def _validate_participant_implementation_selection(self) -> ParticipantImplementationSelectionModel:
        _validate_unique_string_values("participant_contract_versions", self.participant_contract_versions)
        validate_participant_supported_contract_versions(self.participant_contract_versions)
        _validate_controlled_vocabulary_terms(
            "capabilities.supported_decision_surface_modes",
            [self.selected_decision_surface_mode],
        )
        return self


class ParticipantImplementationProvenanceModel(ContractModel):
    schema_version: Literal[PARTICIPANT_IMPLEMENTATION_PROVENANCE_V1_SCHEMA_VERSION] = (
        PARTICIPANT_IMPLEMENTATION_PROVENANCE_V1_SCHEMA_VERSION
    )
    run_id: NonEmptyString
    participant_implementations: list[ParticipantImplementationSelectionModel] = Field(min_length=1)
    processor_manifest_ref: NonEmptyString | None = None
    backend_manifest_ref: NonEmptyString | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_unique_participant_addresses(self) -> ParticipantImplementationProvenanceModel:
        addresses = [selection.participant_address for selection in self.participant_implementations]
        _validate_unique_string_values("participant_address", addresses)
        return self
