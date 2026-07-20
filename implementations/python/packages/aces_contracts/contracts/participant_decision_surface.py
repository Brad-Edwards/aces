"""Portable SEM-220 participant decision-surface contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, GetJsonSchemaHandler, StrictInt, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from .base import ContractModel, NonEmptyString
from .participant_context import ParticipantContextViewModel
from .schema_invariants import _add_aces_invariant

ParticipantDecisionSurfaceVisibility = Literal[
    "observable",
    "discovered",
    "inferred",
    "disclosed",
    "deceptive",
]
ParticipantDecisionSurfaceEligibility = Literal["eligible", "ineligible", "unknown", "unsupported"]
ParticipantDecisionSurfaceSupport = Literal["supported", "unsupported", "unknown"]


def _require_unique(values: list[str], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


class ParticipantDecisionSurfaceActionEntryModel(ContractModel):
    """One presented or generable action without lifecycle implications."""

    entry_id: NonEmptyString
    action_contract_address: NonEmptyString
    presentation_basis_ref: NonEmptyString
    visibility: ParticipantDecisionSurfaceVisibility
    eligibility: ParticipantDecisionSurfaceEligibility
    eligibility_reason_refs: list[NonEmptyString] = Field(default_factory=list)
    constraint_refs: list[NonEmptyString] = Field(min_length=1)
    selection_shape_ref: NonEmptyString
    support: ParticipantDecisionSurfaceSupport
    support_refs: list[NonEmptyString] = Field(default_factory=list)
    affordance_refs: list[NonEmptyString] = Field(default_factory=list)
    realization_refs: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_entry_facts(self) -> ParticipantDecisionSurfaceActionEntryModel:
        for field_name in (
            "eligibility_reason_refs",
            "constraint_refs",
            "support_refs",
            "affordance_refs",
            "realization_refs",
        ):
            _require_unique(getattr(self, field_name), field_name)
        if self.eligibility != "eligible" and not self.eligibility_reason_refs:
            raise ValueError("eligibility_reason_refs are required unless eligibility is eligible")
        if self.eligibility == "eligible" and self.eligibility_reason_refs:
            raise ValueError("eligible action entries must not carry eligibility_reason_refs")
        if self.support == "supported" and not self.support_refs:
            raise ValueError("support_refs are required when support is supported")
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
                        "properties": {"eligibility": {"enum": ["ineligible", "unknown", "unsupported"]}},
                        "required": ["eligibility"],
                    },
                    "then": {"properties": {"eligibility_reason_refs": {"minItems": 1}}},
                },
                {
                    "if": {
                        "properties": {"support": {"const": "supported"}},
                        "required": ["support"],
                    },
                    "then": {"properties": {"support_refs": {"minItems": 1}}},
                },
            ]
        )
        return json_schema


class ParticipantDecisionSurfaceOpenEndedFormModel(ContractModel):
    surface_form: Literal["open_ended_generation"]
    selection_meaning_ref: NonEmptyString
    proposal_binding_ref: NonEmptyString
    argument_shape_ref: NonEmptyString
    validation_policy_ref: NonEmptyString
    allowed_action_contract_addresses: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_allowed_actions(self) -> ParticipantDecisionSurfaceOpenEndedFormModel:
        _require_unique(self.allowed_action_contract_addresses, "allowed_action_contract_addresses")
        return self


class ParticipantDecisionSurfaceConstrainedFormModel(ContractModel):
    surface_form: Literal["constrained_form"]
    selection_meaning_ref: NonEmptyString
    action_entry_id: NonEmptyString
    argument_shape_ref: NonEmptyString
    validation_policy_ref: NonEmptyString
    constraint_refs: list[NonEmptyString] = Field(min_length=1)
    default_disclosure_refs: list[NonEmptyString] = Field(min_length=1)
    normalization_disclosure_refs: list[NonEmptyString] = Field(min_length=1)
    omission_disclosure_refs: list[NonEmptyString] = Field(min_length=1)
    loss_disclosure_refs: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_mapping_disclosures(self) -> ParticipantDecisionSurfaceConstrainedFormModel:
        for field_name in (
            "constraint_refs",
            "default_disclosure_refs",
            "normalization_disclosure_refs",
            "omission_disclosure_refs",
            "loss_disclosure_refs",
        ):
            _require_unique(getattr(self, field_name), field_name)
        return self


class ParticipantDecisionSurfaceCandidateSetFormModel(ContractModel):
    surface_form: Literal["candidate_action_set"]
    selection_meaning_ref: NonEmptyString
    candidate_entry_ids: list[NonEmptyString] = Field(min_length=1)
    open_extension_binding_ref: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_candidate_ids(self) -> ParticipantDecisionSurfaceCandidateSetFormModel:
        _require_unique(self.candidate_entry_ids, "candidate_entry_ids")
        return self


ParticipantDecisionSurfaceFormModel = Annotated[
    ParticipantDecisionSurfaceOpenEndedFormModel
    | ParticipantDecisionSurfaceConstrainedFormModel
    | ParticipantDecisionSurfaceCandidateSetFormModel,
    Field(discriminator="surface_form"),
]


class ParticipantDecisionSurfaceModel(ContractModel):
    """One participant-local decision projection at one episode order point."""

    surface_id: NonEmptyString
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    observation_point: NonEmptyString
    observation_order: StrictInt = Field(ge=0)
    behavior_specification_address: NonEmptyString
    observation_boundary_address: NonEmptyString
    context_view_ref: NonEmptyString
    implementation_selection_ref: NonEmptyString
    decision_control_mode: NonEmptyString
    projection_policy_ref: NonEmptyString
    projection_policy_revision: NonEmptyString
    exposure_policy_ref: NonEmptyString
    visibility_projection_ref: NonEmptyString
    visible_context_refs: list[NonEmptyString] = Field(min_length=1)
    action_entries: list[ParticipantDecisionSurfaceActionEntryModel] = Field(min_length=1)
    affordance_refs: list[NonEmptyString] = Field(default_factory=list)
    form: ParticipantDecisionSurfaceFormModel
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    provenance_refs: list[NonEmptyString] = Field(min_length=1)
    marking_definition_refs: list[NonEmptyString] = Field(default_factory=list)
    redaction_policy_ref: NonEmptyString | None = None
    semantic_limitations: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_surface_relations(self) -> ParticipantDecisionSurfaceModel:
        for field_name in (
            "visible_context_refs",
            "affordance_refs",
            "evidence_refs",
            "provenance_refs",
            "marking_definition_refs",
            "semantic_limitations",
        ):
            _require_unique(getattr(self, field_name), field_name)
        entry_ids = [entry.entry_id for entry in self.action_entries]
        _require_unique(entry_ids, "action_entries.entry_id")
        action_addresses = [entry.action_contract_address for entry in self.action_entries]
        _require_unique(action_addresses, "action_entries.action_contract_address")
        entry_id_set = set(entry_ids)
        action_address_set = set(action_addresses)
        if isinstance(self.form, ParticipantDecisionSurfaceCandidateSetFormModel):
            unknown = sorted(set(self.form.candidate_entry_ids) - entry_id_set)
            if unknown:
                raise ValueError("candidate_entry_ids must reference action_entries: " + ", ".join(unknown))
        elif isinstance(self.form, ParticipantDecisionSurfaceConstrainedFormModel):
            if self.form.action_entry_id not in entry_id_set:
                raise ValueError("constrained form action_entry_id must reference action_entries")
            entry = next(item for item in self.action_entries if item.entry_id == self.form.action_entry_id)
            if entry.selection_shape_ref != self.form.argument_shape_ref:
                raise ValueError("constrained form argument_shape_ref must match the selected action entry")
        else:
            unknown = sorted(set(self.form.allowed_action_contract_addresses) - action_address_set)
            if unknown:
                raise ValueError(
                    "open-ended allowed_action_contract_addresses must reference action_entries: " + ", ".join(unknown)
                )
            mismatched = sorted(
                entry.action_contract_address
                for entry in self.action_entries
                if entry.action_contract_address in self.form.allowed_action_contract_addresses
                and entry.selection_shape_ref != self.form.argument_shape_ref
            )
            if mismatched:
                raise ValueError(
                    "open-ended argument_shape_ref must match allowed action entries: " + ", ".join(mismatched)
                )
        entry_affordances = {ref for entry in self.action_entries for ref in entry.affordance_refs}
        unknown_affordances = sorted(set(self.affordance_refs) - entry_affordances)
        if unknown_affordances:
            raise ValueError("affordance_refs must be carried by action_entries: " + ", ".join(unknown_affordances))
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        _add_aces_invariant(
            json_schema,
            "decision-surface-entry-reference-agreement",
            "Candidate, constrained-form, and open-ended action references must resolve to action entries and "
            "their governed selection shapes.",
            validator="aces_contracts.contracts.ParticipantDecisionSurfaceModel._validate_surface_relations",
            inputs=[{"contract_id": "participant-decision-surface-v1", "instance_path": "#"}],
        )
        _add_aces_invariant(
            json_schema,
            "decision-surface-presentation-not-lifecycle-evidence",
            "Surface membership or presentation carries no selection, admission, execution, result, or outcome fact; "
            "those facts remain in their existing lifecycle contracts.",
            validator="aces_contracts.contracts.ParticipantDecisionSurfaceModel",
            inputs=[{"contract_id": "participant-decision-surface-v1", "instance_path": "#"}],
        )
        return json_schema


class ParticipantDecisionSurfaceSelectionModel(ContractModel):
    """A referenced proposal selected from one surface, before admission."""

    surface_id: NonEmptyString
    observation_order: StrictInt = Field(ge=0)
    action_contract_address: NonEmptyString
    argument_shape_ref: NonEmptyString
    proposal_ref: NonEmptyString


def validate_participant_decision_surface_context(
    surface: ParticipantDecisionSurfaceModel,
    context: ParticipantContextViewModel,
) -> None:
    """Require the typed payload to agree with its SEM-214/216 envelope."""

    comparisons: tuple[tuple[str, object, object], ...] = (
        ("context_view_ref", surface.context_view_ref, context.view_id),
        ("participant_address", surface.participant_address, context.participant_address),
        ("episode_id", surface.episode_id, context.episode_id),
        ("observation_point", surface.observation_point, context.observation_point),
        ("surface_id/payload_ref", surface.surface_id, context.payload_ref),
        ("projection_policy_ref", surface.projection_policy_ref, context.derivation_basis_ref),
        ("transformation_rule_ref", surface.projection_policy_ref, context.transformation.transformation_rule_ref),
        ("visibility_projection_ref", surface.visibility_projection_ref, context.visibility_projection_ref),
        ("evidence_refs", surface.evidence_refs, context.evidence_refs),
        ("provenance_refs", surface.provenance_refs, context.provenance_refs),
        ("marking_definition_refs", surface.marking_definition_refs, context.marking_definition_refs),
        ("redaction_policy_ref", surface.redaction_policy_ref, context.redaction_policy_ref),
        ("semantic_limitations", surface.semantic_limitations, context.semantic_limitations),
    )
    mismatched = [name for name, surface_value, context_value in comparisons if surface_value != context_value]
    if mismatched:
        raise ValueError("decision surface and context view disagree on: " + ", ".join(mismatched))
