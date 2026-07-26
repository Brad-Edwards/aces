"""Portable participant decision-surface v2 contracts.

Version 2 separates the participant-visible decision view from its trusted
derivation and from delivery. A decision epoch is a participant-choice
coordinate; a state cut is the causal/history coordinate used to derive it.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, GetJsonSchemaHandler, StrictInt, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from .base import ContractModel, NonEmptyString
from .participant_decision_surface import (
    ParticipantDecisionSurfaceActionEntryModel,
    ParticipantDecisionSurfaceFormModel,
    _require_unique,
    _surface_entry_indexes,
    _validate_surface_affordances,
    _validate_surface_form_relations,
)
from .participant_decision_surface_exposure_v2 import (
    ParticipantDecisionSurfaceExposureBindingV2Model,
    ParticipantDecisionSurfaceStateCutOrderModel,
)
from .participant_manifests import DigestString
from .participant_runtime import ParticipantRuntimeDeliveryBasis
from .schema_invariants import _add_aces_invariant


class ParticipantDecisionSurfaceSequenceCutModel(ContractModel):
    """A complete prefix ending at one event in a declared total order."""

    cut_kind: Literal["sequence_prefix"]
    cut_ref: NonEmptyString
    history_domain: Literal["participant_episode_lifecycle", "participant_behavior_history"]
    order_model: ParticipantDecisionSurfaceStateCutOrderModel
    anchor_event_ref: NonEmptyString
    anchor_order: StrictInt = Field(ge=0)
    history_prefix_length: StrictInt = Field(ge=1)
    predecessor_event_refs: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_prefix(self) -> ParticipantDecisionSurfaceSequenceCutModel:
        _require_unique(self.predecessor_event_refs, "predecessor_event_refs")
        if self.history_prefix_length != self.anchor_order + 1:
            raise ValueError("history_prefix_length must equal anchor_order + 1")
        if self.anchor_event_ref in self.predecessor_event_refs:
            raise ValueError("anchor_event_ref must not also be a predecessor_event_ref")
        return self


class ParticipantDecisionSurfaceCausalCutModel(ContractModel):
    """A downward-closed causal frontier for a partially ordered realization."""

    cut_kind: Literal["causal_frontier"]
    cut_ref: NonEmptyString
    history_domain: NonEmptyString
    order_model: Literal["causal_partial_order"]
    frontier_event_refs: list[NonEmptyString] = Field(min_length=1)
    predecessor_closure_ref: NonEmptyString

    @model_validator(mode="after")
    def _validate_frontier(self) -> ParticipantDecisionSurfaceCausalCutModel:
        _require_unique(self.frontier_event_refs, "frontier_event_refs")
        return self


ParticipantDecisionSurfaceStateCutModel = Annotated[
    ParticipantDecisionSurfaceSequenceCutModel | ParticipantDecisionSurfaceCausalCutModel,
    Field(discriminator="cut_kind"),
]


class _ParticipantDecisionSurfaceAnchorV2Base(ContractModel):
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    decision_epoch: StrictInt = Field(ge=0)
    event_ref: NonEmptyString
    state_cut: ParticipantDecisionSurfaceStateCutModel
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    provenance_refs: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_anchor(self) -> _ParticipantDecisionSurfaceAnchorV2Base:
        _require_unique(self.evidence_refs, "evidence_refs")
        _require_unique(self.provenance_refs, "provenance_refs")
        if self.event_ref not in self.provenance_refs:
            raise ValueError("derivation anchor event_ref must be carried by provenance_refs")
        if isinstance(self.state_cut, ParticipantDecisionSurfaceSequenceCutModel):
            if self.event_ref != self.state_cut.anchor_event_ref:
                raise ValueError("event_ref must equal the sequence state cut anchor_event_ref")
        elif self.event_ref not in self.state_cut.frontier_event_refs:
            raise ValueError("event_ref must belong to the causal state cut frontier")
        return self


class ParticipantDecisionSurfaceEpisodeReadinessAnchorV2Model(_ParticipantDecisionSurfaceAnchorV2Base):
    """The initial decision epoch derived from a trusted ``episode_running`` cut."""

    anchor_kind: Literal["episode_readiness"]
    event_type: Literal["episode_running"]
    episode_sequence_number: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def _validate_initial_epoch(self) -> ParticipantDecisionSurfaceEpisodeReadinessAnchorV2Model:
        if self.decision_epoch != 0:
            raise ValueError("episode-readiness anchors require decision_epoch zero")
        if (
            isinstance(self.state_cut, ParticipantDecisionSurfaceSequenceCutModel)
            and self.state_cut.history_domain != "participant_episode_lifecycle"
        ):
            raise ValueError("episode-readiness sequence cuts must use participant_episode_lifecycle")
        return self


class ParticipantDecisionSurfaceBehaviorAnchorV2Model(_ParticipantDecisionSurfaceAnchorV2Base):
    """A later decision epoch derived from a terminal participant observation."""

    anchor_kind: Literal["behavior_event"]
    event_type: Literal["observation_emitted"]
    action_instance_id: NonEmptyString

    @model_validator(mode="after")
    def _validate_behavior_epoch(self) -> ParticipantDecisionSurfaceBehaviorAnchorV2Model:
        if self.decision_epoch < 1:
            raise ValueError("behavior anchors require decision_epoch greater than zero")
        if (
            isinstance(self.state_cut, ParticipantDecisionSurfaceSequenceCutModel)
            and self.state_cut.history_domain != "participant_behavior_history"
        ):
            raise ValueError("behavior sequence cuts must use participant_behavior_history")
        return self


ParticipantDecisionSurfaceDerivationAnchorV2Model = Annotated[
    ParticipantDecisionSurfaceEpisodeReadinessAnchorV2Model | ParticipantDecisionSurfaceBehaviorAnchorV2Model,
    Field(discriminator="anchor_kind"),
]


class ParticipantDecisionSurfaceViewV2Model(ContractModel):
    """The complete payload made available to one participant for one choice."""

    surface_id: NonEmptyString
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    decision_epoch: StrictInt = Field(ge=0)
    information_state_ref: NonEmptyString
    context_view_ref: NonEmptyString
    decision_control_mode: NonEmptyString
    visible_context_refs: list[NonEmptyString] = Field(min_length=1)
    action_entries: list[ParticipantDecisionSurfaceActionEntryModel] = Field(min_length=1)
    affordance_refs: list[NonEmptyString] = Field(default_factory=list)
    form: ParticipantDecisionSurfaceFormModel
    marking_definition_refs: list[NonEmptyString] = Field(default_factory=list)
    redaction_policy_ref: NonEmptyString | None = None
    semantic_limitations: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_view(self) -> ParticipantDecisionSurfaceViewV2Model:
        for field_name in (
            "visible_context_refs",
            "affordance_refs",
            "marking_definition_refs",
            "semantic_limitations",
        ):
            _require_unique(getattr(self, field_name), field_name)
        entries_by_id, entries_by_address = _surface_entry_indexes(self.action_entries)
        _validate_surface_form_relations(self.form, entries_by_id, entries_by_address)
        _validate_surface_affordances(self.affordance_refs, self.action_entries)
        return self


class ParticipantDecisionSurfaceAssuranceV2Model(ContractModel):
    """Trusted derivation, policy, provenance, and evidence for one view."""

    participant_address: NonEmptyString
    episode_id: NonEmptyString
    decision_epoch: StrictInt = Field(ge=0)
    behavior_specification_address: NonEmptyString
    observation_boundary_address: NonEmptyString
    implementation_selection_ref: NonEmptyString
    audience_scope_ref: NonEmptyString
    projection_policy_ref: NonEmptyString
    projection_policy_revision: NonEmptyString
    projection_policy_decision_ref: NonEmptyString
    exposure_policy_ref: NonEmptyString
    visibility_projection_ref: NonEmptyString
    participant_memory_scope: Literal["episode_local_reset", "persistent_across_episodes"]
    memory_reset_authority_ref: NonEmptyString | None = None
    participant_view_digest: DigestString
    derivation_anchor: ParticipantDecisionSurfaceDerivationAnchorV2Model
    exposure_bindings: list[ParticipantDecisionSurfaceExposureBindingV2Model] = Field(min_length=1)
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    provenance_refs: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_assurance(self) -> ParticipantDecisionSurfaceAssuranceV2Model:
        _require_unique(self.evidence_refs, "evidence_refs")
        _require_unique(self.provenance_refs, "provenance_refs")
        if self.participant_memory_scope == "episode_local_reset":
            if self.memory_reset_authority_ref is None:
                raise ValueError("episode_local_reset memory scope requires memory_reset_authority_ref")
        elif self.memory_reset_authority_ref is not None:
            raise ValueError("persistent_across_episodes memory scope must not claim a reset authority")
        anchor = self.derivation_anchor
        comparisons = (
            ("participant_address", anchor.participant_address, self.participant_address),
            ("episode_id", anchor.episode_id, self.episode_id),
            ("decision_epoch", anchor.decision_epoch, self.decision_epoch),
        )
        mismatched = [name for name, anchor_value, assurance_value in comparisons if anchor_value != assurance_value]
        if mismatched:
            raise ValueError("derivation anchor disagrees with assurance on: " + ", ".join(mismatched))
        if not set(anchor.evidence_refs).issubset(self.evidence_refs):
            raise ValueError("derivation anchor evidence_refs must be carried by assurance")
        if not set(anchor.provenance_refs).issubset(self.provenance_refs):
            raise ValueError("derivation anchor provenance_refs must be carried by assurance")
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
                        "properties": {"participant_memory_scope": {"const": "episode_local_reset"}},
                        "required": ["participant_memory_scope"],
                    },
                    "then": {
                        "required": ["memory_reset_authority_ref"],
                        "properties": {"memory_reset_authority_ref": {"type": "string", "minLength": 1}},
                    },
                },
                {
                    "if": {
                        "properties": {"participant_memory_scope": {"const": "persistent_across_episodes"}},
                        "required": ["participant_memory_scope"],
                    },
                    "then": {"properties": {"memory_reset_authority_ref": {"type": "null"}}},
                },
            ]
        )
        return json_schema


class ParticipantDecisionSurfaceDeliveryV2Model(ContractModel):
    """Evidence that the exact participant view became available to its subject."""

    delivery_ref: NonEmptyString
    surface_id: NonEmptyString
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    decision_epoch: StrictInt = Field(ge=0)
    participant_view_digest: DigestString
    delivery_basis: ParticipantRuntimeDeliveryBasis
    delivery_cut_ref: NonEmptyString
    delivery_authorization_ref: NonEmptyString
    delivery_policy_decision_ref: NonEmptyString
    observation_ref: NonEmptyString
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    provenance_refs: list[NonEmptyString] = Field(min_length=1)
    limitations: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_delivery_refs(self) -> ParticipantDecisionSurfaceDeliveryV2Model:
        for field_name in ("evidence_refs", "provenance_refs", "limitations"):
            _require_unique(getattr(self, field_name), field_name)
        if self.delivery_basis in {"unknown", "unsupported"}:
            raise ValueError("delivered decision surfaces require an affirmative delivery_basis")
        return self


def _view_exposed_refs(view: ParticipantDecisionSurfaceViewV2Model) -> set[str]:
    return {
        *view.visible_context_refs,
        *(entry.action_contract_address for entry in view.action_entries),
        *view.affordance_refs,
    }


class ParticipantDecisionSurfaceV2Model(ContractModel):
    """A projected or delivered v2 decision surface with separated trust planes."""

    schema_version: Literal["participant-decision-surface/v2"]
    surface_state: Literal["projected", "delivered"]
    participant_view: ParticipantDecisionSurfaceViewV2Model
    assurance: ParticipantDecisionSurfaceAssuranceV2Model
    delivery: ParticipantDecisionSurfaceDeliveryV2Model | None = None

    @model_validator(mode="after")
    def _validate_surface(self) -> ParticipantDecisionSurfaceV2Model:
        view = self.participant_view
        assurance = self.assurance
        coordinate_comparisons = (
            ("participant_address", assurance.participant_address, view.participant_address),
            ("episode_id", assurance.episode_id, view.episode_id),
            ("decision_epoch", assurance.decision_epoch, view.decision_epoch),
        )
        mismatched = [
            name for name, assurance_value, view_value in coordinate_comparisons if assurance_value != view_value
        ]
        if mismatched:
            raise ValueError("assurance disagrees with the participant view on: " + ", ".join(mismatched))

        from ..satisfiability import canonical_contract_digest

        if assurance.participant_view_digest != canonical_contract_digest(view):
            raise ValueError("assurance participant_view_digest must match the canonical participant view")

        bindings = {binding.item_ref: binding for binding in assurance.exposure_bindings}
        _require_unique([binding.item_ref for binding in assurance.exposure_bindings], "exposure_bindings.item_ref")
        expected = _view_exposed_refs(view)
        if bindings.keys() != expected:
            missing = sorted(expected - bindings.keys())
            extra = sorted(bindings.keys() - expected)
            details = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unexpected " + ", ".join(extra))
            raise ValueError("exposure_bindings must exactly cover participant view refs: " + "; ".join(details))
        for binding in assurance.exposure_bindings:
            comparisons = (
                ("participant_address", binding.participant_address, view.participant_address),
                ("episode_id", binding.episode_id, view.episode_id),
                ("decision_epoch", binding.decision_epoch, view.decision_epoch),
                ("decision_cut_ref", binding.decision_cut_ref, assurance.derivation_anchor.state_cut.cut_ref),
                ("audience_scope_ref", binding.audience_scope_ref, assurance.audience_scope_ref),
                ("projection_policy_ref", binding.projection_policy_ref, assurance.projection_policy_ref),
                (
                    "projection_policy_revision",
                    binding.projection_policy_revision,
                    assurance.projection_policy_revision,
                ),
                (
                    "projection_policy_decision_ref",
                    binding.projection_policy_decision_ref,
                    assurance.projection_policy_decision_ref,
                ),
                ("exposure_policy_ref", binding.exposure_policy_ref, assurance.exposure_policy_ref),
            )
            binding_mismatches = [
                name for name, binding_value, expected_value in comparisons if binding_value != expected_value
            ]
            if binding_mismatches:
                raise ValueError(
                    f"exposure binding {binding.item_ref!r} disagrees with the surface on: "
                    + ", ".join(binding_mismatches)
                )
            if not set(binding.evidence_refs).issubset(assurance.evidence_refs):
                raise ValueError(f"exposure binding {binding.item_ref!r} evidence must be carried by assurance")
            if not set(binding.provenance_refs).issubset(assurance.provenance_refs):
                raise ValueError(f"exposure binding {binding.item_ref!r} provenance must be carried by assurance")

        if self.surface_state == "projected" and self.delivery is not None:
            raise ValueError("projected surfaces must not carry delivery")
        if self.surface_state == "delivered" and self.delivery is None:
            raise ValueError("delivered surfaces require delivery")
        if self.delivery is not None:
            delivery_comparisons = (
                ("surface_id", self.delivery.surface_id, view.surface_id),
                ("participant_address", self.delivery.participant_address, view.participant_address),
                ("episode_id", self.delivery.episode_id, view.episode_id),
                ("decision_epoch", self.delivery.decision_epoch, view.decision_epoch),
                (
                    "participant_view_digest",
                    self.delivery.participant_view_digest,
                    assurance.participant_view_digest,
                ),
            )
            delivery_mismatches = [
                name
                for name, delivery_value, expected_value in delivery_comparisons
                if delivery_value != expected_value
            ]
            if delivery_mismatches:
                raise ValueError("delivery disagrees with the participant view on: " + ", ".join(delivery_mismatches))
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
            "decision-surface-v2-plane-separation",
            "The participant view contains only participant-available choice material; derivation, policy, evidence, "
            "provenance, and delivery remain in separate assurance and delivery planes.",
            validator="raes_contracts.contracts.ParticipantDecisionSurfaceV2Model._validate_surface",
            inputs=[{"contract_id": "participant-decision-surface-v2", "instance_path": "#"}],
        )
        _add_aces_invariant(
            json_schema,
            "decision-surface-v2-exact-cut-policy",
            "Each exposed item is bound to the derivation state cut and exact policy decision, independently of the "
            "participant decision epoch.",
            validator="raes_contracts.contracts.ParticipantDecisionSurfaceV2Model._validate_surface",
            inputs=[{"contract_id": "participant-decision-surface-v2", "instance_path": "#/assurance"}],
        )
        _add_aces_invariant(
            json_schema,
            "decision-surface-v2-delivery-before-selection",
            "A surface is actionable only in delivered state, with delivery bound to the canonical participant view.",
            validator="raes_contracts.contracts.ParticipantDecisionSurfaceV2Model._validate_surface",
            inputs=[{"contract_id": "participant-decision-surface-v2", "instance_path": "#/delivery"}],
        )
        _add_aces_invariant(
            json_schema,
            "decision-surface-v2-explicit-memory-scope",
            "Assurance declares whether participant-visible memory persists across episodes; an episode-local claim "
            "requires an authoritative reset of every participant-visible memory channel.",
            validator=("raes_contracts.contracts.ParticipantDecisionSurfaceAssuranceV2Model._validate_assurance"),
            inputs=[{"contract_id": "participant-decision-surface-v2", "instance_path": "#/assurance"}],
        )
        json_schema.setdefault("allOf", []).extend(
            [
                {
                    "if": {
                        "properties": {"surface_state": {"const": "delivered"}},
                        "required": ["surface_state"],
                    },
                    "then": {
                        "required": ["delivery"],
                        "properties": {"delivery": {"not": {"type": "null"}}},
                    },
                },
                {
                    "if": {
                        "properties": {"surface_state": {"const": "projected"}},
                        "required": ["surface_state"],
                    },
                    "then": {"properties": {"delivery": {"type": "null"}}},
                },
            ]
        )
        return json_schema


class ParticipantDecisionSurfaceSelectionV2Model(ContractModel):
    """A proposal selected from the exact delivered v2 participant view."""

    surface_id: NonEmptyString
    decision_epoch: StrictInt = Field(ge=0)
    participant_view_digest: DigestString
    delivery_ref: NonEmptyString
    action_contract_address: NonEmptyString
    argument_shape_ref: NonEmptyString
    proposal_ref: NonEmptyString
    arguments: dict[
        NonEmptyString,
        str | int | float | bool | list[str | int | float | bool],
    ] = Field(default_factory=dict)


__all__ = (
    "ParticipantDecisionSurfaceAssuranceV2Model",
    "ParticipantDecisionSurfaceBehaviorAnchorV2Model",
    "ParticipantDecisionSurfaceCausalCutModel",
    "ParticipantDecisionSurfaceDeliveryV2Model",
    "ParticipantDecisionSurfaceDerivationAnchorV2Model",
    "ParticipantDecisionSurfaceEpisodeReadinessAnchorV2Model",
    "ParticipantDecisionSurfaceSelectionV2Model",
    "ParticipantDecisionSurfaceSequenceCutModel",
    "ParticipantDecisionSurfaceStateCutModel",
    "ParticipantDecisionSurfaceV2Model",
    "ParticipantDecisionSurfaceViewV2Model",
)
