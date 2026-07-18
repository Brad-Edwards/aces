"""Provisioner/orchestrator/evaluator capability and realization-support contracts."""

from __future__ import annotations

from pydantic import Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from ..vocabulary import RealizationSupportMode, WorkflowFeature, WorkflowStatePredicateFeature
from .base import ContractModel, NonEmptyString
from .validators import _validate_controlled_vocabulary_terms


class ProvisionerCapabilitiesModel(ContractModel):
    name: NonEmptyString
    supported_node_types: list[NonEmptyString] = Field(min_length=1)
    supported_os_families: list[NonEmptyString] = Field(min_length=1)
    supported_content_types: list[NonEmptyString] = Field(default_factory=list)
    supported_account_features: list[NonEmptyString] = Field(default_factory=list)
    supported_domain_profiles: list[NonEmptyString] = Field(default_factory=list)
    max_total_nodes: int | None = Field(default=None, gt=0)
    supports_acls: bool = False
    supports_accounts: bool = False
    supports_generated_artifacts: bool = False
    supports_persistent_volumes: bool = False
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_account_support(self) -> ProvisionerCapabilitiesModel:
        _validate_controlled_vocabulary_terms(
            "capabilities.provisioner.supported_node_types",
            self.supported_node_types,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.provisioner.supported_os_families",
            self.supported_os_families,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.provisioner.supported_content_types",
            self.supported_content_types,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.provisioner.supported_account_features",
            self.supported_account_features,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.provisioner.supported_domain_profiles",
            self.supported_domain_profiles,
        )
        if self.supports_accounts and not self.supported_account_features:
            raise ValueError("provisioners that support accounts must declare supported_account_features")
        if not self.supports_accounts and self.supported_account_features:
            raise ValueError("supported_account_features require supports_accounts=true")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.setdefault("allOf", []).extend(
            [
                {
                    "if": {
                        "properties": {"supports_accounts": {"const": True}},
                        "required": ["supports_accounts"],
                    },
                    "then": {
                        "required": ["supported_account_features"],
                        "properties": {"supported_account_features": {"minItems": 1}},
                    },
                },
                {
                    "if": {
                        "properties": {"supports_accounts": {"const": False}},
                        "required": ["supports_accounts"],
                    },
                    "then": {
                        "properties": {"supported_account_features": {"maxItems": 0}},
                    },
                },
            ]
        )
        return json_schema


class OrchestratorCapabilitiesModel(ContractModel):
    name: NonEmptyString
    supported_sections: list[NonEmptyString] = Field(min_length=1)
    supports_workflows: bool = False
    supports_assertion_refs: bool = True
    supports_inject_bindings: bool = True
    supported_workflow_features: list[WorkflowFeature] = Field(default_factory=list)
    supported_workflow_state_predicates: list[WorkflowStatePredicateFeature] = Field(default_factory=list)
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_workflow_support(self) -> OrchestratorCapabilitiesModel:
        _validate_controlled_vocabulary_terms(
            "capabilities.orchestrator.supported_sections",
            self.supported_sections,
        )
        if self.supports_workflows:
            if "workflows" not in self.supported_sections:
                raise ValueError("orchestrators that support workflows must include 'workflows' in supported_sections")
            if not self.supported_workflow_features:
                raise ValueError("orchestrators that support workflows must declare supported_workflow_features")
        else:
            if "workflows" in self.supported_sections:
                raise ValueError("'workflows' in supported_sections requires supports_workflows=true")
            if self.supported_workflow_features:
                raise ValueError("supported_workflow_features require supports_workflows=true")
            if self.supported_workflow_state_predicates:
                raise ValueError("supported_workflow_state_predicates require supports_workflows=true")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.setdefault("allOf", []).extend(
            [
                {
                    "if": {
                        "properties": {"supports_workflows": {"const": True}},
                        "required": ["supports_workflows"],
                    },
                    "then": {
                        "required": ["supported_workflow_features", "supported_sections"],
                        "properties": {
                            "supported_workflow_features": {"minItems": 1},
                            "supported_sections": {"contains": {"const": "workflows"}},
                        },
                    },
                },
                {
                    "if": {
                        "properties": {"supports_workflows": {"const": False}},
                        "required": ["supports_workflows"],
                    },
                    "then": {
                        "properties": {
                            "supported_workflow_features": {"maxItems": 0},
                            "supported_workflow_state_predicates": {"maxItems": 0},
                            "supported_sections": {"not": {"contains": {"const": "workflows"}}},
                        },
                    },
                },
            ]
        )
        return json_schema


class EvaluatorCapabilitiesModel(ContractModel):
    name: NonEmptyString
    supported_sections: list[NonEmptyString] = Field(min_length=1)
    supports_scoring: bool = True
    supports_objectives: bool = True
    supported_predicate_families: list[NonEmptyString] = Field(default_factory=list)
    supported_quantifiers: list[NonEmptyString] = Field(default_factory=list)
    supported_truth_outcomes: list[NonEmptyString] = Field(default_factory=list)
    supported_evidence_channels: list[NonEmptyString] = Field(default_factory=list)
    supported_time_domains: list[NonEmptyString] = Field(default_factory=list)
    preserves_binding_provenance: bool = False
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_evaluator_support(self) -> EvaluatorCapabilitiesModel:
        _validate_controlled_vocabulary_terms(
            "capabilities.evaluator.supported_sections",
            self.supported_sections,
        )
        if not self.supports_scoring and not self.supports_objectives:
            raise ValueError("evaluators must support scoring, objectives, or both")
        for field_name in (
            "supported_predicate_families",
            "supported_quantifiers",
            "supported_truth_outcomes",
            "supported_evidence_channels",
            "supported_time_domains",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"evaluator {field_name} must be unique")
        proposition_sections = {"propositions", "assertions"}
        if proposition_sections.intersection(self.supported_sections):
            if not proposition_sections.issubset(self.supported_sections):
                raise ValueError("evaluator proposition support requires propositions and assertions")
            if set(self.supported_truth_outcomes) != {"true", "false", "unknown", "unsupported"}:
                raise ValueError("evaluator proposition support requires all portable truth outcomes")
            if not all(
                (
                    self.supported_predicate_families,
                    self.supported_quantifiers,
                    self.supported_evidence_channels,
                    self.supported_time_domains,
                )
            ):
                raise ValueError("evaluator proposition support requires typed capability dimensions")
            if not self.preserves_binding_provenance:
                raise ValueError("evaluator proposition support requires binding provenance")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.setdefault("allOf", []).append(
            {
                "not": {
                    "allOf": [
                        {
                            "properties": {"supports_scoring": {"const": False}},
                            "required": ["supports_scoring"],
                        },
                        {
                            "properties": {"supports_objectives": {"const": False}},
                            "required": ["supports_objectives"],
                        },
                    ]
                }
            }
        )
        return json_schema


class ApparatusIdentityModel(ContractModel):
    name: NonEmptyString
    version: NonEmptyString


class BackendCompatibilityModel(ContractModel):
    processors: list[NonEmptyString] = Field(min_length=1)


class ProcessorCompatibilityModel(ContractModel):
    backends: list[NonEmptyString] = Field(min_length=1)


class RealizationSupportDeclarationModel(ContractModel):
    domain: NonEmptyString
    support_mode: RealizationSupportMode
    supported_constraint_kinds: list[NonEmptyString] = Field(default_factory=list)
    supported_exact_requirement_kinds: list[NonEmptyString] = Field(default_factory=list)
    disclosure_kinds: list[NonEmptyString] = Field(min_length=1)
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_realization_support(self) -> RealizationSupportDeclarationModel:
        if not self.supported_constraint_kinds and not self.supported_exact_requirement_kinds:
            raise ValueError(
                "realization_support declarations must declare supported_constraint_kinds "
                "or supported_exact_requirement_kinds"
            )
        if self.support_mode == RealizationSupportMode.EXACT_ONLY and self.supported_constraint_kinds:
            raise ValueError("exact-only realization support must not declare supported_constraint_kinds")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.setdefault("allOf", []).extend(
            [
                {
                    "anyOf": [
                        {
                            "required": ["supported_constraint_kinds"],
                            "properties": {"supported_constraint_kinds": {"minItems": 1}},
                        },
                        {
                            "required": ["supported_exact_requirement_kinds"],
                            "properties": {"supported_exact_requirement_kinds": {"minItems": 1}},
                        },
                    ]
                },
                {
                    "if": {
                        "properties": {"support_mode": {"const": RealizationSupportMode.EXACT_ONLY.value}},
                        "required": ["support_mode"],
                    },
                    "then": {
                        "required": ["supported_exact_requirement_kinds"],
                        "properties": {
                            "supported_exact_requirement_kinds": {"minItems": 1},
                            "supported_constraint_kinds": {"maxItems": 0},
                        },
                    },
                },
            ]
        )
        return json_schema
