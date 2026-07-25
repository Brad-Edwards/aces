"""Portable SEM-226 participant decision-surface exposure contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, StrictInt, model_validator

from .base import ContractModel, NonEmptyString
from .participant_manifests import DigestString

ParticipantExposureOperation = Literal[
    "projection",
    "masking",
    "redaction",
    "declassification",
    "disclosure",
    "transformation",
]


def _require_unique(values: list[str], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


class ParticipantDecisionSurfaceExposureRealizationModel(ContractModel):
    """Independent evidence that one authorized exposure was delivered."""

    occurrence_ref: NonEmptyString
    item_ref: NonEmptyString
    authorization_record_ref: NonEmptyString
    delivery_basis_ref: NonEmptyString
    delivery_order: StrictInt = Field(ge=0)
    observation_ref: NonEmptyString
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    provenance_refs: list[NonEmptyString] = Field(min_length=1)
    limitations: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_realization_refs(self) -> ParticipantDecisionSurfaceExposureRealizationModel:
        for field_name in ("evidence_refs", "provenance_refs", "limitations"):
            _require_unique(getattr(self, field_name), field_name)
        return self


class ParticipantDecisionSurfaceExposureBindingModel(ContractModel):
    """Resolved SEM-226 basis for one item admitted to a surface."""

    item_ref: NonEmptyString
    authorization_record_ref: NonEmptyString
    source_ref: NonEmptyString
    source_layer_ref: NonEmptyString
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    audience_scope_ref: NonEmptyString
    observation_point: NonEmptyString
    observation_order: StrictInt = Field(ge=0)
    visibility_basis_ref: NonEmptyString
    projection_policy_ref: NonEmptyString
    projection_policy_revision: NonEmptyString
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
    realization: ParticipantDecisionSurfaceExposureRealizationModel | None = None

    @model_validator(mode="after")
    def _validate_exposure_basis(self) -> ParticipantDecisionSurfaceExposureBindingModel:
        _validate_binding_ref_lists(self)
        _validate_binding_operation(self)
        _validate_binding_inheritance(self)
        _validate_binding_realization(self)
        return self


def _validate_binding_ref_lists(binding: ParticipantDecisionSurfaceExposureBindingModel) -> None:
    for field_name in (
        "source_marking_definition_refs",
        "result_marking_definition_refs",
        "source_provenance_refs",
        "result_provenance_refs",
        "evidence_refs",
        "provenance_refs",
        "loss_and_limitations",
    ):
        _require_unique(getattr(binding, field_name), field_name)


def _validate_binding_operation(binding: ParticipantDecisionSurfaceExposureBindingModel) -> None:
    if binding.source_ref != binding.item_ref and binding.transformation_rule_ref is None:
        raise ValueError("derived exposure items require transformation_rule_ref")
    transformed_operations = {"masking", "redaction", "transformation"}
    if binding.operation in transformed_operations and binding.transformation_rule_ref is None:
        raise ValueError(f"{binding.operation} exposure operations require transformation_rule_ref")
    if binding.operation == "redaction" and binding.redaction_policy_ref is None:
        raise ValueError("redaction exposure operations require redaction_policy_ref")
    if binding.operation == "declassification" and binding.declassification_basis_ref is None:
        raise ValueError("declassification exposure operations require declassification_basis_ref")


def _validate_binding_inheritance(binding: ParticipantDecisionSurfaceExposureBindingModel) -> None:
    if binding.declassification_basis_ref is None and not set(binding.source_marking_definition_refs).issubset(
        binding.result_marking_definition_refs
    ):
        raise ValueError("derived exposure results must inherit source markings unless declassification is explicit")
    if binding.declassification_basis_ref is None and not set(binding.source_provenance_refs).issubset(
        binding.result_provenance_refs
    ):
        raise ValueError("derived exposure results must inherit source provenance unless declassification is explicit")
    if not {*binding.source_provenance_refs, *binding.result_provenance_refs}.issubset(binding.provenance_refs):
        raise ValueError("source and result provenance refs must be carried by provenance_refs")


def _validate_binding_realization(binding: ParticipantDecisionSurfaceExposureBindingModel) -> None:
    if binding.realization is None:
        return
    if binding.realization.delivery_order > binding.observation_order:
        raise ValueError("realized exposure delivery_order cannot be later than the surface observation_order")
    if binding.realization.item_ref != binding.item_ref:
        raise ValueError("realized exposure item_ref must match the exposure binding")
