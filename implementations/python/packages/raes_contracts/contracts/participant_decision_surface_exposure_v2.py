"""State-cut-bound SEM-226 exposure decisions for decision-surface v2."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, StrictInt, model_validator

from .base import ContractModel, NonEmptyString
from .participant_decision_surface_exposure import ParticipantExposureOperation
from .participant_manifests import DigestString


def _require_unique(values: list[str], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


class ParticipantDecisionSurfaceExposureBindingV2Model(ContractModel):
    """One exact-cut authorization for an item admitted to a projected view.

    ``decision_epoch`` orders participant choices. ``decision_cut_ref`` and
    ``projection_policy_decision_ref`` identify the state and policy decision
    that authorized this item. None of those coordinates is a delivery fact.
    """

    item_ref: NonEmptyString
    authorization_record_ref: NonEmptyString
    source_ref: NonEmptyString
    source_layer_ref: NonEmptyString
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    audience_scope_ref: NonEmptyString
    decision_epoch: StrictInt = Field(ge=0)
    decision_cut_ref: NonEmptyString
    visibility_basis_ref: NonEmptyString
    projection_policy_ref: NonEmptyString
    projection_policy_revision: NonEmptyString
    projection_policy_decision_ref: NonEmptyString
    exposure_policy_ref: NonEmptyString
    exposure_policy_version: NonEmptyString
    exposure_policy_digest: DigestString
    operation: ParticipantExposureOperation
    operation_basis_ref: NonEmptyString
    actor_ref: NonEmptyString
    controller_ref: NonEmptyString
    authority_basis_ref: NonEmptyString
    source_marking_definition_refs: list[NonEmptyString] = Field(default_factory=list)
    result_marking_definition_refs: list[NonEmptyString] = Field(default_factory=list)
    source_provenance_refs: list[NonEmptyString] = Field(min_length=1)
    result_provenance_refs: list[NonEmptyString] = Field(min_length=1)
    declassification_basis_ref: NonEmptyString | None = None
    redaction_policy_ref: NonEmptyString | None = None
    transformation_rule_ref: NonEmptyString | None = None
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    provenance_refs: list[NonEmptyString] = Field(min_length=1)
    loss_and_limitations: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_exposure_basis(self) -> ParticipantDecisionSurfaceExposureBindingV2Model:
        for field_name in (
            "source_marking_definition_refs",
            "result_marking_definition_refs",
            "source_provenance_refs",
            "result_provenance_refs",
            "evidence_refs",
            "provenance_refs",
            "loss_and_limitations",
        ):
            _require_unique(getattr(self, field_name), field_name)
        if self.source_ref != self.item_ref and self.transformation_rule_ref is None:
            raise ValueError("derived exposure items require transformation_rule_ref")
        if self.operation in {"masking", "redaction", "transformation"} and self.transformation_rule_ref is None:
            raise ValueError(f"{self.operation} exposure operations require transformation_rule_ref")
        if self.operation == "redaction" and self.redaction_policy_ref is None:
            raise ValueError("redaction exposure operations require redaction_policy_ref")
        if self.operation == "declassification" and self.declassification_basis_ref is None:
            raise ValueError("declassification exposure operations require declassification_basis_ref")
        if self.declassification_basis_ref is None and not set(self.source_marking_definition_refs).issubset(
            self.result_marking_definition_refs
        ):
            raise ValueError(
                "derived exposure results must inherit source markings unless declassification is explicit"
            )
        if self.declassification_basis_ref is None and not set(self.source_provenance_refs).issubset(
            self.result_provenance_refs
        ):
            raise ValueError(
                "derived exposure results must inherit source provenance unless declassification is explicit"
            )
        if not {*self.source_provenance_refs, *self.result_provenance_refs}.issubset(self.provenance_refs):
            raise ValueError("source and result provenance refs must be carried by provenance_refs")
        return self


ParticipantDecisionSurfaceStateCutOrderModel = Literal[
    "control_plane_order",
    "backend_serialized_order",
    "behavior_history_order",
]


__all__ = (
    "ParticipantDecisionSurfaceExposureBindingV2Model",
    "ParticipantDecisionSurfaceStateCutOrderModel",
)
