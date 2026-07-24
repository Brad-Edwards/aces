"""Concept-binding, capability-v2, and processor-manifest contracts."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from ..addressing import require_compiled_address
from ..manifest_authority import (
    PROCESSOR_SUPPORTED_CONTRACT_IDS,
    PROCESSOR_SUPPORTED_SDL_VERSION_IDS,
    validate_backend_supported_contract_versions,
    validate_processor_supported_contract_versions,
    validate_processor_supported_sdl_versions,
)
from ..versions import PROCESSOR_MANIFEST_V2_SCHEMA_VERSION
from ..vocabulary import ConceptFamilyId, ParticipantFeatureSupportLevel, ProcessorFeature
from .base import _PROCESSOR_CONCEPT_BINDING_SCOPES, ContractModel, NonEmptyString
from .capabilities import (
    ApparatusIdentityModel,
    EvaluatorCapabilitiesModel,
    OrchestratorCapabilitiesModel,
    ProcessorCompatibilityModel,
    ProvisionerCapabilitiesModel,
)
from .trial_cleanup import CleanupActionKind
from .validators import (
    _validate_canonical_concept_bindings,
    _validate_controlled_vocabulary_terms,
    _validate_unique_string_values,
)


class ConceptBindingEntryModel(ContractModel):
    """Binds a vocabulary surface in an artifact to a canonical concept family."""

    scope: NonEmptyString = Field(
        ...,
        pattern=r"^[a-z_][a-z0-9_.]*[a-z0-9_]$",
    )
    family: ConceptFamilyId


class ProcessorCapabilitiesV2Model(ContractModel):
    supported_sdl_versions: list[NonEmptyString] = Field(min_length=1)
    supported_features: list[ProcessorFeature] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_declared_authority(self) -> ProcessorCapabilitiesV2Model:
        validate_processor_supported_sdl_versions(self.supported_sdl_versions)
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["properties"]["supported_sdl_versions"]["items"]["enum"] = list(PROCESSOR_SUPPORTED_SDL_VERSION_IDS)
        return json_schema


_PARTICIPANT_FEATURE_SUPPORT_VOCABULARY_IDS = (
    "participant-runtime-behavior-features",
    "participant-runtime-interaction-features",
)


def _validate_participant_feature_support_term(feature: str) -> None:
    from ..controlled_vocabularies import load_controlled_vocabulary_catalog

    catalog = load_controlled_vocabulary_catalog()
    for vocabulary_id in _PARTICIPANT_FEATURE_SUPPORT_VOCABULARY_IDS:
        definition = catalog.vocabularies[vocabulary_id]
        if feature in definition.terms:
            return
        if definition.extension_pattern is not None and re.fullmatch(definition.extension_pattern, feature):
            return
    joined = ", ".join(_PARTICIPANT_FEATURE_SUPPORT_VOCABULARY_IDS)
    raise ValueError(
        f"feature_support feature '{feature}' is not a governed term of {joined} "
        "and does not match the governed extension pattern"
    )


class ParticipantFeatureSupportModel(ContractModel):
    """API-407 per-feature participant runtime support declaration."""

    feature: NonEmptyString
    support_level: ParticipantFeatureSupportLevel
    constraint_refs: list[NonEmptyString] = Field(default_factory=list)
    disclosure_refs: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_feature_support_declaration(self) -> ParticipantFeatureSupportModel:
        _validate_participant_feature_support_term(self.feature)
        _validate_unique_string_values("constraint_refs", self.constraint_refs)
        _validate_unique_string_values("disclosure_refs", self.disclosure_refs)
        if self.support_level != ParticipantFeatureSupportLevel.EXACT and not self.disclosure_refs:
            raise ValueError(
                f"feature_support entry '{self.feature}' declares support_level "
                f"'{self.support_level.value}' below 'exact' and must carry at least one disclosure_refs entry"
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
        below_exact = [
            level.value for level in ParticipantFeatureSupportLevel if level != ParticipantFeatureSupportLevel.EXACT
        ]
        json_schema.setdefault("allOf", []).append(
            {
                "if": {
                    "properties": {"support_level": {"enum": below_exact}},
                    "required": ["support_level"],
                },
                "then": {
                    "required": ["disclosure_refs"],
                    "properties": {"disclosure_refs": {"minItems": 1}},
                },
            }
        )
        return json_schema


class ParticipantRuntimeCapabilitiesModel(ContractModel):
    """Participant-episode lifecycle capability block (RUN-311).

    A backend that declares this block advertises that it implements
    the full participant episode control surface on the
    ``ParticipantRuntime`` protocol: ``initialize`` / ``reset`` /
    ``restart`` / ``terminate`` plus ``status`` / ``results`` /
    ``history``. Consumers of the manifest can infer the
    ``FULL_REMOTE_CONTROL_PLANE`` conformance profile from this block.

    API-405 support dimensions live here because they are backend apparatus
    claims: which participant roles, behavior features, and interaction
    features this participant runtime can actually realize.
    """

    name: NonEmptyString
    supported_participant_roles: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    supported_behavior_features: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    supported_interaction_features: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    feature_support: list[ParticipantFeatureSupportModel] = Field(default_factory=list)
    supports_autonomous_execution: bool = False
    supported_autonomous_selection_strategies: list[Literal["ordered_cycle"]] = Field(
        default_factory=list,
        json_schema_extra={"uniqueItems": True},
    )
    supported_autonomous_action_contracts: list[NonEmptyString] = Field(
        default_factory=list,
        json_schema_extra={"uniqueItems": True},
    )
    supported_autonomous_observation_boundaries: list[NonEmptyString] = Field(
        default_factory=list,
        json_schema_extra={"uniqueItems": True},
    )
    supported_autonomous_target_addresses: list[NonEmptyString] = Field(
        default_factory=list,
        json_schema_extra={"uniqueItems": True},
    )
    max_autonomous_participants: int | None = Field(default=None, ge=1)
    max_autonomous_action_attempts: int | None = Field(default=None, ge=1)
    max_autonomous_in_flight: int | None = Field(default=None, ge=1)
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_api_405_declarations(self) -> ParticipantRuntimeCapabilitiesModel:
        _validate_unique_string_values("supported_participant_roles", self.supported_participant_roles)
        _validate_unique_string_values("supported_behavior_features", self.supported_behavior_features)
        _validate_unique_string_values("supported_interaction_features", self.supported_interaction_features)
        _validate_controlled_vocabulary_terms(
            "capabilities.participant_runtime.supported_participant_roles",
            self.supported_participant_roles,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.participant_runtime.supported_behavior_features",
            self.supported_behavior_features,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.participant_runtime.supported_interaction_features",
            self.supported_interaction_features,
        )
        return self

    @model_validator(mode="after")
    def _validate_api_407_feature_support(self) -> ParticipantRuntimeCapabilitiesModel:
        _validate_unique_string_values("feature_support", [entry.feature for entry in self.feature_support])
        supported_features = set(self.supported_behavior_features) | set(self.supported_interaction_features)
        for entry in self.feature_support:
            declared_unsupported = entry.support_level == ParticipantFeatureSupportLevel.UNSUPPORTED
            if declared_unsupported and entry.feature in supported_features:
                raise ValueError(
                    f"feature_support entry '{entry.feature}' declares support_level 'unsupported' but the "
                    "feature is declared in supported_behavior_features or supported_interaction_features"
                )
        declares_autonomous = "autonomous_execution" in self.supported_behavior_features
        if declares_autonomous != self.supports_autonomous_execution:
            raise ValueError("autonomous_execution feature and support flag must agree")
        limits = (
            self.max_autonomous_participants,
            self.max_autonomous_action_attempts,
            self.max_autonomous_in_flight,
        )
        if self.supports_autonomous_execution and (
            not self.supported_autonomous_selection_strategies
            or not self.supported_autonomous_action_contracts
            or not self.supported_autonomous_observation_boundaries
            or any(value is None for value in limits)
        ):
            raise ValueError(
                "autonomous execution requires selection strategies, exact action and observation support, "
                "and finite limits"
            )
        if not self.supports_autonomous_execution and (
            self.supported_autonomous_selection_strategies
            or self.supported_autonomous_action_contracts
            or self.supported_autonomous_observation_boundaries
            or self.supported_autonomous_target_addresses
            or any(value is not None for value in limits)
        ):
            raise ValueError("autonomous execution limits require autonomous execution support")
        for field_name in (
            "supported_autonomous_action_contracts",
            "supported_autonomous_observation_boundaries",
            "supported_autonomous_target_addresses",
        ):
            values = getattr(self, field_name)
            _validate_unique_string_values(field_name, values)
            for address in values:
                try:
                    require_compiled_address(address, field_name=field_name)
                except (TypeError, ValueError) as exc:
                    raise ValueError(str(exc)) from exc
        return self


class ObservationCapabilitiesModel(ContractModel):
    """EXP-715 backend observation and evidence-collection capability declaration."""

    name: NonEmptyString
    supported_capture_kinds: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_channel_kinds: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_evidence_contracts: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_media_types: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_sealing_modes: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supports_redaction: bool = False
    supports_loss_disclosure: bool = False
    supports_chain_of_custody: bool = False
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_observation_capability(self) -> ObservationCapabilitiesModel:
        _validate_unique_string_values("supported_capture_kinds", self.supported_capture_kinds)
        _validate_unique_string_values("supported_channel_kinds", self.supported_channel_kinds)
        _validate_unique_string_values("supported_evidence_contracts", self.supported_evidence_contracts)
        _validate_unique_string_values("supported_media_types", self.supported_media_types)
        _validate_unique_string_values("supported_sealing_modes", self.supported_sealing_modes)
        _validate_controlled_vocabulary_terms(
            "capabilities.observation.supported_capture_kinds",
            self.supported_capture_kinds,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.observation.supported_channel_kinds",
            self.supported_channel_kinds,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.observation.supported_sealing_modes",
            self.supported_sealing_modes,
        )
        validate_backend_supported_contract_versions(self.supported_evidence_contracts)
        for contract_id in self.supported_evidence_contracts:
            if not contract_id.startswith("experiment-"):
                raise ValueError("observation supported_evidence_contracts must be experiment contract ids")
        return self


class CleanupCapabilitiesModel(ContractModel):
    """Backend support for the portable SCE-007 cleanup contract family."""

    name: NonEmptyString
    supported_contract_versions: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_action_kinds: list[CleanupActionKind] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_verification_methods: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supports_reusable_state: bool = False
    supports_residual_state_disclosure: bool = False

    @model_validator(mode="after")
    def _validate_cleanup_capability(self) -> CleanupCapabilitiesModel:
        _validate_unique_string_values("cleanup supported_contract_versions", self.supported_contract_versions)
        _validate_unique_string_values("cleanup supported_action_kinds", self.supported_action_kinds)
        _validate_unique_string_values("cleanup supported_verification_methods", self.supported_verification_methods)
        required = {"trial-cleanup-plan-v1", "trial-cleanup-receipt-v1"}
        if set(self.supported_contract_versions) != required:
            raise ValueError(
                "cleanup capabilities require contract versions trial-cleanup-plan-v1 and trial-cleanup-receipt-v1"
            )
        validate_backend_supported_contract_versions(self.supported_contract_versions)
        if self.supports_reusable_state and not self.supports_residual_state_disclosure:
            raise ValueError("reusable-state support requires residual-state disclosure")
        return self


_TIME_CAPABILITY_REQUIRED_CONTRACTS = {
    "time-model-v1",
    "time-runtime-state-v1",
    "realized-time-model-v1",
    "runtime-snapshot-v1",
    "experiment-run-v1",
}
_TIME_CAPABILITY_TERMS = {
    "supported_domain_kinds": {"wall_clock", "monotonic", "simulated", "logical", "external"},
    "supported_authority_kinds": {"runtime", "backend", "system", "external"},
    "supported_advancement_modes": {
        "real_time",
        "dilated",
        "stepped",
        "event_driven",
        "externally_paced",
    },
    "supported_synchronization_modes": {"none", "authority", "barrier", "conservative"},
    "supported_mapping_kinds": {"identity", "affine_rational"},
    "supported_constraint_kinds": {"precedence", "duration", "window", "deadline", "cadence"},
    "supported_reset_behaviors": {"unsupported", "new_segment_zero", "new_segment_preserve_value"},
    "supported_replay_behaviors": {"unsupported", "restart_from_anchor", "restore_recorded_advances"},
}


class TimeCapabilitiesModel(ContractModel):
    """Backend support for the API-421 portable shared-time contract family."""

    name: NonEmptyString
    supported_contract_versions: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_domain_kinds: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_authority_kinds: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_advancement_modes: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_synchronization_modes: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_mapping_kinds: list[NonEmptyString] = Field(default_factory=list, json_schema_extra={"uniqueItems": True})
    supported_constraint_kinds: list[NonEmptyString] = Field(
        default_factory=list, json_schema_extra={"uniqueItems": True}
    )
    supported_reset_behaviors: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    supported_replay_behaviors: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    max_time_domains: int | None = Field(default=None, ge=1)
    max_clocks: int | None = Field(default=None, ge=1)
    supports_pause: bool = False
    supports_jump: bool = False
    supports_exact_rational_mappings: bool = False
    supports_append_only_history: bool = False
    supports_run_provenance: bool = False
    supports_coordinated_participant_reset: bool = False
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_time_capability(self) -> TimeCapabilitiesModel:
        if set(self.supported_contract_versions) != _TIME_CAPABILITY_REQUIRED_CONTRACTS:
            raise ValueError("time capabilities require the complete time contract family")
        validate_backend_supported_contract_versions(self.supported_contract_versions)
        for field_name, allowed in _TIME_CAPABILITY_TERMS.items():
            values = getattr(self, field_name)
            _validate_unique_string_values(f"time {field_name}", values)
            unknown = sorted(set(values) - allowed)
            if unknown:
                raise ValueError(f"time {field_name} contains unknown values: {', '.join(unknown)}")
        if self.supported_mapping_kinds and not self.supports_exact_rational_mappings:
            raise ValueError("time mapping support requires exact rational mappings")
        return self


class BackendCapabilitiesV2Model(ContractModel):
    provisioner: ProvisionerCapabilitiesModel
    orchestrator: OrchestratorCapabilitiesModel | None = None
    evaluator: EvaluatorCapabilitiesModel | None = None
    participant_runtime: ParticipantRuntimeCapabilitiesModel | None = None
    observation: ObservationCapabilitiesModel | None = None
    cleanup: CleanupCapabilitiesModel | None = None
    time: TimeCapabilitiesModel | None = None


class ProcessorManifestV2Model(ContractModel):
    schema_version: Literal[PROCESSOR_MANIFEST_V2_SCHEMA_VERSION] = PROCESSOR_MANIFEST_V2_SCHEMA_VERSION
    identity: ApparatusIdentityModel
    supported_contract_versions: list[NonEmptyString] = Field(min_length=1)
    compatibility: ProcessorCompatibilityModel
    concept_bindings: list[ConceptBindingEntryModel] = Field(min_length=1)
    constraints: dict[str, str] = Field(default_factory=dict)
    capabilities: ProcessorCapabilitiesV2Model

    @model_validator(mode="after")
    def _validate_unique_binding_scopes(self) -> ProcessorManifestV2Model:
        validate_processor_supported_contract_versions(self.supported_contract_versions)
        scopes = [binding.scope for binding in self.concept_bindings]
        if len(scopes) != len(set(scopes)):
            raise ValueError("concept_bindings must not contain duplicate scopes")
        _validate_canonical_concept_bindings(self, allowed_scopes=_PROCESSOR_CONCEPT_BINDING_SCOPES)
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
            PROCESSOR_SUPPORTED_CONTRACT_IDS
        )
        return json_schema
