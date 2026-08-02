"""Closed portable relation aggregate for SEM-233 participant boundary flow control."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, GetJsonSchemaHandler, field_validator, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from raes.participant_behavior_specification import MixedControlTransitionKind

from ..versions import PARTICIPANT_FLOW_CONTROL_RELATION_V1_SCHEMA_VERSION
from .base import ContractModel, NonEmptyString, PrefixedDigestString
from .participant_crossing_vocab import ParticipantCrossingSubjectKind
from .participant_flow_control_semantics import (
    PARTICIPANT_BOUNDARY_FLOW_POLICY_PROFILE_REV1_DIGEST,
    FlowSubjectKey,
    ParticipantBoundaryFlowPolicyProfileModel,
    ParticipantEffectiveFlowLabelModel,
    ParticipantFlowBindingKind,
    ParticipantFlowCoordinateResult,
    ParticipantFlowDeclassificationModel,
    ParticipantFlowDerivationInputModel,
    ParticipantFlowDerivationModel,
    ParticipantFlowEndorsementModel,
    ParticipantFlowFinalDisposition,
    ParticipantFlowLabelResolutionStatus,
    ParticipantFlowPolicyCutReferenceModel,
    ParticipantFlowProfileReferenceModel,
    ParticipantFlowRelationTargetKind,
    ParticipantFlowRelease,
    ParticipantFlowReleaseKind,
    ParticipantFlowRuleReferenceModel,
    ParticipantFlowSinkDecisionModel,
    ParticipantFlowSinkKind,
    ParticipantFlowSubjectKind,
    ParticipantFlowSubjectReferenceModel,
    _require_canonical_refs,
    participant_flow_coordinate_disposition,
)
from .schema_invariants import _add_raes_invariant


class ParticipantFlowRelationTargetReferenceModel(ContractModel):
    target_kind: ParticipantFlowRelationTargetKind
    target_ref: NonEmptyString


class ParticipantFlowCarrierBindingBaseModel(ContractModel):
    binding_id: NonEmptyString
    profile: ParticipantFlowProfileReferenceModel
    policy: ParticipantFlowPolicyCutReferenceModel
    relation_target: ParticipantFlowRelationTargetReferenceModel
    source_participant_address: NonEmptyString
    source_episode_id: NonEmptyString
    target_participant_address: NonEmptyString
    target_episode_id: NonEmptyString
    crossing_refs: tuple[NonEmptyString, ...] = ()
    memory_predecessor_refs: tuple[NonEmptyString, ...] = ()

    @field_validator("crossing_refs", "memory_predecessor_refs")
    @classmethod
    def _validate_canonical_refs(cls, values: tuple[str, ...], info: object) -> tuple[str, ...]:
        _require_canonical_refs(values, getattr(info, "field_name", "binding refs"))
        return values

    @model_validator(mode="after")
    def _validate_cross_scope_state(self) -> ParticipantFlowCarrierBindingBaseModel:
        cross_scope = (
            self.source_participant_address,
            self.source_episode_id,
        ) != (
            self.target_participant_address,
            self.target_episode_id,
        )
        if cross_scope and (not self.crossing_refs or not self.memory_predecessor_refs):
            raise ValueError("cross-scope bindings require crossing and memory predecessor refs")
        return self


class ParticipantRuntimeFactFlowBindingModel(ParticipantFlowCarrierBindingBaseModel):
    kind: Literal[ParticipantFlowBindingKind.RUNTIME_FACT]
    plane_ref: NonEmptyString
    declaration_ref: NonEmptyString
    fact_version_ref: NonEmptyString
    sink_ref: NonEmptyString
    binding_event_ref: NonEmptyString


class ParticipantActionArgumentFlowBindingModel(ParticipantFlowCarrierBindingBaseModel):
    kind: Literal[ParticipantFlowBindingKind.ACTION_ARGUMENT]
    action_contract_address: NonEmptyString
    proposal_ref: NonEmptyString
    normalized_argument_name: NonEmptyString
    action_admission_ref: NonEmptyString


class ParticipantControlOccurrenceFlowBindingModel(ParticipantFlowCarrierBindingBaseModel):
    kind: Literal[ParticipantFlowBindingKind.PARTICIPANT_CONTROL]
    event_id: NonEmptyString
    occurrence_kind: MixedControlTransitionKind
    occurrence_revision: int = Field(ge=1)
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    controller_ref: NonEmptyString
    authority_basis_refs: tuple[NonEmptyString, ...] = Field(min_length=1)
    control_policy_revision: NonEmptyString
    occurrence_identity_ref: NonEmptyString
    related_occurrence_refs: tuple[NonEmptyString, ...]
    predecessor_event_refs: tuple[NonEmptyString, ...]

    @field_validator("authority_basis_refs", "related_occurrence_refs", "predecessor_event_refs")
    @classmethod
    def _validate_canonical_refs(cls, values: tuple[str, ...], info: object) -> tuple[str, ...]:
        _require_canonical_refs(values, getattr(info, "field_name", "control binding refs"))
        return values


class ParticipantCrossingOccurrenceFlowBindingModel(ParticipantFlowCarrierBindingBaseModel):
    kind: Literal[ParticipantFlowBindingKind.PARTICIPANT_CROSSING]
    event_id: NonEmptyString
    stage: Literal[
        "requested",
        "decided",
        "transformed",
        "disclosed",
        "delivery-attempted",
        "delivered",
        "observed",
        "audited",
    ]
    stage_identity_ref: NonEmptyString
    related_stage_refs: tuple[NonEmptyString, ...]
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    subject_kind: ParticipantCrossingSubjectKind
    subject_contract_id: NonEmptyString
    subject_ref: NonEmptyString
    subject_revision: NonEmptyString
    subject_digest: PrefixedDigestString | None = None
    crossing_policy_id: NonEmptyString
    crossing_policy_revision: NonEmptyString
    crossing_policy_digest: PrefixedDigestString
    crossing_policy_decision_ref: NonEmptyString
    crossing_decision_cut_ref: NonEmptyString
    predecessor_event_refs: tuple[NonEmptyString, ...]

    @field_validator("related_stage_refs", "predecessor_event_refs")
    @classmethod
    def _validate_canonical_refs(cls, values: tuple[str, ...], info: object) -> tuple[str, ...]:
        _require_canonical_refs(values, getattr(info, "field_name", "crossing binding refs"))
        return values


ParticipantFlowCarrierBinding = Annotated[
    ParticipantRuntimeFactFlowBindingModel
    | ParticipantActionArgumentFlowBindingModel
    | ParticipantControlOccurrenceFlowBindingModel
    | ParticipantCrossingOccurrenceFlowBindingModel,
    Field(discriminator="kind"),
]


class ParticipantFlowControlRelationModel(ContractModel):
    """Aggregate portable SEM-233 label, release, sink, and carrier relation."""

    schema_version: Literal[PARTICIPANT_FLOW_CONTROL_RELATION_V1_SCHEMA_VERSION] = (
        PARTICIPANT_FLOW_CONTROL_RELATION_V1_SCHEMA_VERSION
    )
    document_id: NonEmptyString
    document_revision: NonEmptyString
    profile: ParticipantFlowProfileReferenceModel
    labels: tuple[ParticipantEffectiveFlowLabelModel, ...] = Field(min_length=1)
    derivations: tuple[ParticipantFlowDerivationModel, ...] = Field(min_length=1)
    releases: tuple[ParticipantFlowRelease, ...] = Field(min_length=1)
    sink_decisions: tuple[ParticipantFlowSinkDecisionModel, ...] = Field(min_length=1)
    bindings: tuple[ParticipantFlowCarrierBinding, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_relation_graph(self) -> ParticipantFlowControlRelationModel:
        labels = _unique_by_id(self.labels, "label_id", "label")
        derivations = _unique_by_id(self.derivations, "derivation_id", "derivation")
        releases = _unique_by_id(self.releases, "release_id", "release")
        decisions = _unique_by_id(self.sink_decisions, "decision_id", "sink decision")
        _unique_by_id(self.bindings, "binding_id", "carrier binding")
        self._validate_profile_coordinates()
        self._validate_derivations(labels)
        self._validate_releases(labels)
        self._validate_lineage_graph()
        self._validate_sink_decisions(labels, releases)
        self._validate_binding_targets(labels, derivations, releases, decisions)
        return self

    def _validate_profile_coordinates(self) -> None:
        records = (*self.labels, *self.derivations, *self.releases, *self.sink_decisions, *self.bindings)
        if any(record.profile != self.profile for record in records):
            raise ValueError("every flow relation record must use the document's exact profile")

    def _validate_derivations(self, labels: dict[str, ParticipantEffectiveFlowLabelModel]) -> None:
        graph: dict[FlowSubjectKey, set[FlowSubjectKey]] = {}
        for derivation in self.derivations:
            inputs = [_resolve_label_input(item, labels) for item in derivation.inputs]
            result = _resolve_label(derivation.result_label_ref, labels)
            if derivation.policy != result.policy or any(derivation.policy != item.policy for item in inputs):
                raise ValueError("derivation inputs and result must use its exact policy and cut")
            if result.subject != derivation.result_subject:
                raise ValueError("derivation result label subject must match its fresh result subject")
            input_keys = {_subject_key(item.subject) for item in derivation.inputs}
            result_key = _subject_key(derivation.result_subject)
            if result_key in input_keys:
                raise ValueError("derivation requires a fresh result identity")
            expected_confidentiality = set().union(*(set(item.confidentiality_obligation_refs) for item in inputs))
            expected_integrity = set().union(*(set(item.integrity_obligation_refs) for item in inputs))
            if (
                set(result.confidentiality_obligation_refs) != expected_confidentiality
                or set(result.integrity_obligation_refs) != expected_integrity
            ):
                raise ValueError("derivation result must equal the coordinate-wise union of all possible inputs")
            if any(item.resolution_status != ParticipantFlowLabelResolutionStatus.RESOLVED for item in inputs) and (
                result.resolution_status == ParticipantFlowLabelResolutionStatus.RESOLVED
            ):
                raise ValueError("derivation with an unresolved input cannot produce a resolved label")
            required_provenance = set(derivation.provenance_refs).union(*(set(item.provenance_refs) for item in inputs))
            if not required_provenance.issubset(result.provenance_refs):
                raise ValueError("derivation result must conservatively retain complete provenance")
            required_influence = (
                set(derivation.influence_refs)
                | {item.subject.subject_ref for item in derivation.inputs}
                | set().union(*(set(item.influence_refs) for item in inputs))
            )
            if not required_influence.issubset(result.influence_refs):
                raise ValueError("derivation result must conservatively retain complete influence")
            for source_key in input_keys:
                graph.setdefault(source_key, set()).add(result_key)
        _reject_cycles(graph)

    def _validate_releases(self, labels: dict[str, ParticipantEffectiveFlowLabelModel]) -> None:
        for release in self.releases:
            source = _resolve_label(release.source_label_ref, labels)
            result = _resolve_label(release.result_label_ref, labels)
            if _subject_key(release.source_subject) == _subject_key(release.result_subject):
                raise ValueError("release requires a fresh result identity")
            if source.subject != release.source_subject or result.subject != release.result_subject:
                raise ValueError("release source and result labels must match their exact subjects")
            if release.policy != source.policy or release.policy != result.policy:
                raise ValueError("release policy and cut must match its source and result labels")
            if (
                source.resolution_status != ParticipantFlowLabelResolutionStatus.RESOLVED
                and result.resolution_status == ParticipantFlowLabelResolutionStatus.RESOLVED
            ):
                raise ValueError("release with an unresolved source cannot produce a resolved label")
            if not set(source.provenance_refs).issubset(result.provenance_refs):
                raise ValueError("release result must preserve source provenance")
            if not (set(source.influence_refs) | {source.subject.subject_ref}).issubset(result.influence_refs):
                raise ValueError("release result must preserve source influence")
            if isinstance(release, ParticipantFlowDeclassificationModel):
                removed = set(release.removed_confidentiality_obligation_refs)
                if not removed.issubset(source.confidentiality_obligation_refs):
                    raise ValueError("declassification can remove only present confidentiality obligations")
                if set(result.confidentiality_obligation_refs) != set(source.confidentiality_obligation_refs) - removed:
                    raise ValueError("declassification result must encode the exact confidentiality delta")
                if result.integrity_obligation_refs != source.integrity_obligation_refs:
                    raise ValueError("declassification must leave the integrity coordinate unchanged")
            else:
                replacements = release.integrity_obligation_replacements
                removed = {item.source_obligation_ref for item in replacements}
                added = {item.result_obligation_ref for item in replacements}
                if not removed.issubset(source.integrity_obligation_refs):
                    raise ValueError("endorsement can replace only present integrity obligations")
                if set(result.integrity_obligation_refs) != set(source.integrity_obligation_refs) - removed | added:
                    raise ValueError("endorsement result must encode the exact integrity delta")
                if result.confidentiality_obligation_refs != source.confidentiality_obligation_refs:
                    raise ValueError("endorsement must leave the confidentiality coordinate unchanged")

    def _validate_lineage_graph(self) -> None:
        produced = [
            *(_subject_key(derivation.result_subject) for derivation in self.derivations),
            *(_subject_key(release.result_subject) for release in self.releases),
        ]
        if len(produced) != len(set(produced)):
            raise ValueError("every derivation and release requires a globally fresh result identity")

        graph: dict[FlowSubjectKey, set[FlowSubjectKey]] = {}
        for derivation in self.derivations:
            result = _subject_key(derivation.result_subject)
            for item in derivation.inputs:
                graph.setdefault(_subject_key(item.subject), set()).add(result)
        for release in self.releases:
            graph.setdefault(_subject_key(release.source_subject), set()).add(_subject_key(release.result_subject))
        _reject_cycles(graph)

    def _validate_sink_decisions(
        self,
        labels: dict[str, ParticipantEffectiveFlowLabelModel],
        releases: dict[str, ParticipantFlowRelease],
    ) -> None:
        for decision in self.sink_decisions:
            label = _resolve_label(decision.label_ref, labels)
            if label.subject != decision.subject or label.policy != decision.policy:
                raise ValueError("sink decision must bind its exact effective label and policy cut")
            decision_releases: list[ParticipantFlowRelease] = []
            for release_ref in decision.release_refs:
                release = releases.get(release_ref)
                if release is None:
                    raise ValueError("sink decision release reference must resolve")
                if (
                    release.sink_ref,
                    release.destination_ref,
                    release.audience_scope_ref,
                ) != (
                    decision.sink.sink_ref,
                    decision.sink.destination_ref,
                    decision.sink.audience_scope_ref,
                ):
                    raise ValueError("sink decision releases must bind the exact final sink")
                decision_releases.append(release)
            for prior, successor in zip(decision_releases, decision_releases[1:], strict=False):
                if prior.result_label_ref != successor.source_label_ref:
                    raise ValueError("sink decision releases must form one ordered label lineage")
            if decision_releases and decision_releases[-1].result_label_ref != decision.label_ref:
                raise ValueError("sink decision release lineage must end at the selected label")

    def _validate_binding_targets(
        self,
        labels: dict[str, ParticipantEffectiveFlowLabelModel],
        derivations: dict[str, ParticipantFlowDerivationModel],
        releases: dict[str, ParticipantFlowRelease],
        decisions: dict[str, ParticipantFlowSinkDecisionModel],
    ) -> None:
        indexes: dict[ParticipantFlowRelationTargetKind, dict[str, object]] = {
            ParticipantFlowRelationTargetKind.LABEL: labels,
            ParticipantFlowRelationTargetKind.DERIVATION: derivations,
            ParticipantFlowRelationTargetKind.RELEASE: releases,
            ParticipantFlowRelationTargetKind.SINK_DECISION: decisions,
        }
        for binding in self.bindings:
            target = indexes[binding.relation_target.target_kind].get(binding.relation_target.target_ref)
            if target is None:
                raise ValueError("carrier binding relation target must resolve")
            if binding.policy != target.policy:
                raise ValueError("carrier binding target must use its exact policy and cut")
            if binding.relation_target.target_kind == ParticipantFlowRelationTargetKind.LABEL:
                label = labels[binding.relation_target.target_ref]
                if (
                    binding.target_participant_address,
                    binding.target_episode_id,
                ) != (
                    label.subject.participant_address,
                    label.subject.episode_id,
                ):
                    raise ValueError("carrier binding target scope must match its effective label")
                source_ref = _binding_source_ref(binding)
                if source_ref not in label.influence_refs:
                    raise ValueError("carrier binding cannot erase its upstream influence")

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        _add_raes_invariant(
            json_schema,
            "participant-flow-control-resolved-context",
            "Every label, derivation, release, sink decision, and carrier binding must resolve an exact SEM-233 "
            "profile and exact incumbent runtime-fact, API-409, API-423, action-admission, capability, authority, "
            "and history decision state before it can be trusted.",
            validator="raes_contracts.contracts.validate_participant_flow_control_resolved_context",
            inputs=[
                {"contract_id": "participant-flow-control-relation-v1", "instance_path": "#"},
                {"contract_id": "runtime-fact-binding-plane-v1", "instance_path": "#"},
                {"contract_id": "participant-control-occurrence-v1", "instance_path": "#"},
                {"contract_id": "participant-crossing-occurrence-v1", "instance_path": "#"},
            ],
        )
        return json_schema


def _unique_by_id(items: tuple[object, ...], field_name: str, label: str) -> dict[str, object]:
    indexed: dict[str, object] = {}
    for item in items:
        identity = getattr(item, field_name)
        if identity in indexed:
            raise ValueError(f"{label} identity was reused")
        indexed[identity] = item
    return indexed


def _resolve_label(
    label_ref: str,
    labels: dict[str, ParticipantEffectiveFlowLabelModel],
) -> ParticipantEffectiveFlowLabelModel:
    label = labels.get(label_ref)
    if label is None:
        raise ValueError("flow label reference must resolve")
    return label


def _resolve_label_input(
    item: ParticipantFlowDerivationInputModel,
    labels: dict[str, ParticipantEffectiveFlowLabelModel],
) -> ParticipantEffectiveFlowLabelModel:
    label = _resolve_label(item.label_ref, labels)
    if label.subject != item.subject:
        raise ValueError("derivation input label must match its exact subject")
    return label


def _subject_key(subject: ParticipantFlowSubjectReferenceModel) -> FlowSubjectKey:
    return (
        subject.subject_kind,
        subject.subject_ref,
        subject.subject_revision,
        subject.participant_address,
        subject.episode_id,
    )


def _reject_cycles(graph: dict[FlowSubjectKey, set[FlowSubjectKey]]) -> None:
    visiting: set[FlowSubjectKey] = set()
    visited: set[FlowSubjectKey] = set()

    def visit(node: FlowSubjectKey) -> None:
        if node in visiting:
            raise ValueError("flow derivation cycle is not allowed")
        if node in visited:
            return
        visiting.add(node)
        for successor in graph.get(node, set()):
            visit(successor)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def _binding_source_ref(binding: ParticipantFlowCarrierBinding) -> str:
    if isinstance(binding, ParticipantRuntimeFactFlowBindingModel):
        return binding.fact_version_ref
    if isinstance(binding, ParticipantActionArgumentFlowBindingModel):
        return f"{binding.proposal_ref}:{binding.normalized_argument_name}"
    return binding.event_id


__all__ = [
    "PARTICIPANT_BOUNDARY_FLOW_POLICY_PROFILE_REV1_DIGEST",
    "ParticipantBoundaryFlowPolicyProfileModel",
    "ParticipantEffectiveFlowLabelModel",
    "ParticipantFlowBindingKind",
    "ParticipantFlowControlRelationModel",
    "ParticipantFlowCoordinateResult",
    "ParticipantFlowDeclassificationModel",
    "ParticipantFlowDerivationModel",
    "ParticipantFlowEndorsementModel",
    "ParticipantFlowFinalDisposition",
    "ParticipantFlowLabelResolutionStatus",
    "ParticipantFlowPolicyCutReferenceModel",
    "ParticipantFlowProfileReferenceModel",
    "ParticipantFlowReleaseKind",
    "ParticipantFlowRelationTargetKind",
    "ParticipantFlowRuleReferenceModel",
    "ParticipantFlowSinkDecisionModel",
    "ParticipantFlowSinkKind",
    "ParticipantFlowSubjectKind",
    "ParticipantFlowSubjectReferenceModel",
    "participant_flow_coordinate_disposition",
]
