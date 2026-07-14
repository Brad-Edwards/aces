"""Versioned behavioral-relation authority and claim-binding validation."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .contracts import (
    BehavioralClaimBindingModel,
    BehavioralRelationId,
    BehavioralTaxonomyRevision,
    ContractModel,
    NonEmptyString,
)
from .corpus import CONCEPT_AUTHORITY, corpus_family_root
from .versions import BEHAVIORAL_RELATIONS_SCHEMA_VERSION


class ImmutablePublicationLocatorModel(ContractModel):
    kind: Literal["doi", "isbn"]
    value: NonEmptyString


class BehavioralBibliographySourceModel(ContractModel):
    source_id: BehavioralRelationId
    title: NonEmptyString
    authors: list[NonEmptyString] = Field(min_length=1)
    publication_year: int = Field(ge=1900, le=2100)
    publication_venue: NonEmptyString
    edition_or_version: NonEmptyString
    immutable_locator: ImmutablePublicationLocatorModel


class TransitionSignatureModel(ContractModel):
    applicability: Literal["applicable", "not-applicable"]
    labels: NonEmptyString
    transition_relation: NonEmptyString
    observable_actions: NonEmptyString
    hidden_actions: NonEmptyString
    stuttering_actions: NonEmptyString
    not_applicable_rationale: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_applicability(self) -> TransitionSignatureModel:
        if self.applicability == "not-applicable" and self.not_applicable_rationale is None:
            raise ValueError("not-applicable transition signatures require a rationale")
        if self.applicability == "applicable" and self.not_applicable_rationale is not None:
            raise ValueError("applicable transition signatures must not carry a not-applicable rationale")
        return self


class ObservationProjectionModel(ContractModel):
    applicability: Literal["required", "parameterized", "identity", "not-applicable"]
    subject: NonEmptyString
    policy_ref: NonEmptyString
    policy_revision: NonEmptyString
    redaction_scope: NonEmptyString
    order_treatment: NonEmptyString
    simultaneity_treatment: NonEmptyString


class RelationQuantificationModel(ContractModel):
    states: NonEmptyString
    traces: NonEmptyString
    schedulers: NonEmptyString
    strategies: NonEmptyString
    environments: NonEmptyString
    observations: NonEmptyString


class RelationDimensionTreatmentModel(ContractModel):
    status: Literal["supported", "parameterized", "abstracted", "outside-scope"]
    treatment: NonEmptyString


class RelationDimensionsModel(ContractModel):
    nondeterminism: RelationDimensionTreatmentModel
    concurrency: RelationDimensionTreatmentModel
    probability: RelationDimensionTreatmentModel
    time: RelationDimensionTreatmentModel
    partial_order: RelationDimensionTreatmentModel


class RelationPreservationModel(ContractModel):
    property: NonEmptyString
    proof_obligation: NonEmptyString


class RelationAssuranceModel(ContractModel):
    definition_status: Literal["defined", "future"]
    implementation_status: Literal["implemented", "partial", "not-implemented", "not-applicable"]
    test_status: Literal["tested", "bounded", "not-tested", "not-applicable"]
    proof_status: Literal["proved", "model-checked", "deliberately-unproved", "future", "not-applicable"]
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)


class BehavioralRelationDefinitionModel(ContractModel):
    relation_id: BehavioralRelationId
    display_name: NonEmptyString
    relation_class: Literal["predicate", "set-relation", "behavioral", "epistemic", "strategic", "empirical"]
    definition: NonEmptyString
    left_carrier: NonEmptyString
    right_carrier: NonEmptyString
    initial_states: NonEmptyString
    transition_signature: TransitionSignatureModel
    observation_projection: ObservationProjectionModel
    projection_required: bool
    direction: Literal["unary", "left-to-right", "right-to-left", "symmetric"]
    quantification: RelationQuantificationModel
    dimensions: RelationDimensionsModel
    preservation: RelationPreservationModel
    bounded_evidence: list[NonEmptyString] = Field(min_length=1)
    explicit_non_claims: list[NonEmptyString] = Field(min_length=1)
    incompatible_claim_surfaces: list[NonEmptyString] = Field(min_length=1)
    assurance: RelationAssuranceModel
    source_refs: list[BehavioralRelationId] = Field(min_length=1)


class BehavioralClaimSurfaceModel(ContractModel):
    surface_id: BehavioralRelationId
    intended_relation_ids: list[BehavioralRelationId] = Field(min_length=1)
    evidence_boundary: NonEmptyString
    prohibited_relation_ids: list[BehavioralRelationId] = Field(min_length=1)
    explicit_non_claims: list[NonEmptyString] = Field(min_length=1)


class ExampleTransitionModel(ContractModel):
    source: NonEmptyString
    action: NonEmptyString
    target: NonEmptyString


class ExampleTransitionSystemModel(ContractModel):
    states: list[NonEmptyString] = Field(min_length=1)
    initial_state: NonEmptyString
    transitions: list[ExampleTransitionModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_transitions(self) -> ExampleTransitionSystemModel:
        state_set = set(self.states)
        if len(state_set) != len(self.states):
            raise ValueError("example transition-system states must be unique")
        if self.initial_state not in state_set:
            raise ValueError("example initial state must be declared")
        for transition in self.transitions:
            if transition.source not in state_set or transition.target not in state_set:
                raise ValueError("example transitions must reference declared states")
        return self


class BehavioralWorkedExampleModel(ContractModel):
    example_id: BehavioralRelationId
    purpose: NonEmptyString
    left_system: ExampleTransitionSystemModel
    right_system: ExampleTransitionSystemModel
    tested_visible_trace: list[NonEmptyString] = Field(min_length=1)
    hidden_action: NonEmptyString
    expected_strong_bisimulation: bool
    expected_weak_matching: bool
    evidence_boundary: NonEmptyString
    explicit_non_claims: list[NonEmptyString] = Field(min_length=1)


class BehavioralRelationCatalogModel(ContractModel):
    schema_version: Literal[BEHAVIORAL_RELATIONS_SCHEMA_VERSION] = BEHAVIORAL_RELATIONS_SCHEMA_VERSION
    taxonomy_id: Literal["aces-behavioral-relations"] = "aces-behavioral-relations"
    taxonomy_revision: BehavioralTaxonomyRevision
    bibliography: list[BehavioralBibliographySourceModel] = Field(min_length=1)
    relations: dict[BehavioralRelationId, BehavioralRelationDefinitionModel] = Field(min_length=1)
    claim_surfaces: list[BehavioralClaimSurfaceModel] = Field(min_length=1)
    worked_examples: dict[BehavioralRelationId, BehavioralWorkedExampleModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_catalog_references(self) -> BehavioralRelationCatalogModel:
        source_ids = [source.source_id for source in self.bibliography]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("behavioral-relation bibliography source ids must be unique")
        relation_ids = set(self.relations)
        for key, relation in self.relations.items():
            if key != relation.relation_id:
                raise ValueError("behavioral-relation map keys must match embedded relation ids")
            missing_sources = sorted(set(relation.source_refs) - set(source_ids))
            if missing_sources:
                raise ValueError(f"relation {key!r} references unknown bibliography sources: {missing_sources}")
        surface_ids = [surface.surface_id for surface in self.claim_surfaces]
        if len(surface_ids) != len(set(surface_ids)):
            raise ValueError("behavioral claim-surface ids must be unique")
        for surface in self.claim_surfaces:
            missing_relations = sorted(
                (set(surface.intended_relation_ids) | set(surface.prohibited_relation_ids)) - relation_ids
            )
            if missing_relations:
                raise ValueError(
                    f"claim surface {surface.surface_id!r} references unknown relations: {missing_relations}"
                )
        for key, example in self.worked_examples.items():
            if key != example.example_id:
                raise ValueError("worked-example map keys must match embedded example ids")
        return self


def behavioral_relation_catalog_path() -> Path:
    return corpus_family_root(CONCEPT_AUTHORITY) / "behavioral-relations-v1.json"


@cache
def load_behavioral_relation_catalog() -> BehavioralRelationCatalogModel:
    return BehavioralRelationCatalogModel.model_validate_json(
        behavioral_relation_catalog_path().read_text(encoding="utf-8")
    )


def validate_behavioral_claim_binding(
    binding: BehavioralClaimBindingModel,
    catalog: BehavioralRelationCatalogModel | None = None,
) -> BehavioralClaimBindingModel:
    """Resolve a consumer binding against the canonical catalog."""

    catalog = load_behavioral_relation_catalog() if catalog is None else catalog
    if binding.taxonomy_id != catalog.taxonomy_id or binding.taxonomy_revision != catalog.taxonomy_revision:
        raise ValueError("behavioral claim binding taxonomy coordinates do not match the canonical catalog")
    relation = catalog.relations.get(binding.relation_id)
    if relation is None:
        raise ValueError(f"behavioral claim binding references unknown relation {binding.relation_id!r}")
    if relation.projection_required and binding.observation_projection_ref is None:
        raise ValueError(f"relation {binding.relation_id!r} requires an observation projection binding")
    return binding


__all__ = [
    "BehavioralClaimSurfaceModel",
    "BehavioralBibliographySourceModel",
    "BehavioralRelationCatalogModel",
    "BehavioralRelationDefinitionModel",
    "BehavioralWorkedExampleModel",
    "ExampleTransitionModel",
    "ExampleTransitionSystemModel",
    "behavioral_relation_catalog_path",
    "load_behavioral_relation_catalog",
    "validate_behavioral_claim_binding",
]
