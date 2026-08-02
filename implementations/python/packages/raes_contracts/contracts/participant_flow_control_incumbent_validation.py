"""Exact incumbent carrier joins for SEM-233 flow-control validation."""

from __future__ import annotations

from collections.abc import Mapping

from .participant_control import (
    ParticipantApprovalOccurrenceModel,
    ParticipantCancellationOccurrenceModel,
    ParticipantControlOccurrenceModel,
    ParticipantDenialOccurrenceModel,
    ParticipantExternalDirectionOccurrenceModel,
    ParticipantHandoffOccurrenceModel,
    ParticipantInterventionOccurrenceModel,
    ParticipantOverrideOccurrenceModel,
    ParticipantProposalOccurrenceModel,
)
from .participant_crossing import (
    ParticipantCrossingAuditModel,
    ParticipantCrossingDecisionModel,
    ParticipantCrossingDeliveryAttemptModel,
    ParticipantCrossingDeliveryModel,
    ParticipantCrossingDisclosureModel,
    ParticipantCrossingObservationModel,
    ParticipantCrossingOccurrenceModel,
    ParticipantCrossingRequestModel,
    ParticipantCrossingTransformationModel,
)
from .participant_flow_control import (
    ParticipantActionArgumentFlowBindingModel,
    ParticipantControlOccurrenceFlowBindingModel,
    ParticipantCrossingOccurrenceFlowBindingModel,
    ParticipantFlowControlRelationModel,
    ParticipantRuntimeFactFlowBindingModel,
)
from .participant_flow_control_context import ParticipantFlowControlValidationContext


def _validate_bindings(
    document: ParticipantFlowControlRelationModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    control_records = {item.event_id: item for item in context.control_records}
    crossing_records = {item.event_id: item for item in context.crossing_records}
    for binding in document.bindings:
        if isinstance(binding, ParticipantRuntimeFactFlowBindingModel):
            _validate_runtime_fact_binding(binding, context)
        elif isinstance(binding, ParticipantActionArgumentFlowBindingModel):
            _validate_action_argument_binding(binding, context)
        elif isinstance(binding, ParticipantControlOccurrenceFlowBindingModel):
            _validate_control_binding(binding, control_records)
        else:
            _validate_crossing_binding(binding, crossing_records)


def _validate_runtime_fact_binding(
    binding: ParticipantRuntimeFactFlowBindingModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    plane = context.runtime_fact_planes.get(binding.plane_ref)
    if plane is None:
        raise ValueError("runtime fact binding plane must resolve")
    declaration = next((item for item in plane.declarations if item.fact_id == binding.declaration_ref), None)
    version = next((item for item in plane.versions if item.version_id == binding.fact_version_ref), None)
    sink = next((item for item in plane.sinks if item.sink_id == binding.sink_ref), None)
    event = next((item for item in plane.events if item.event_id == binding.binding_event_ref), None)
    if declaration is None or version is None:
        raise ValueError("runtime fact declaration and immutable fact version must resolve")
    if sink is None or event is None:
        raise ValueError("runtime fact sink and binding event must resolve")
    if version.fact_id != declaration.fact_id or (
        event.fact_id,
        event.fact_version_id,
        event.sink_id,
    ) != (
        declaration.fact_id,
        version.version_id,
        sink.sink_id,
    ):
        raise ValueError("runtime fact binding coordinates do not match")
    if (binding.source_participant_address, binding.source_episode_id) != (
        event.participant_address,
        event.episode_id,
    ):
        raise ValueError("runtime fact binding scope does not match")


def _validate_action_argument_binding(
    binding: ParticipantActionArgumentFlowBindingModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    key = (binding.action_contract_address, binding.proposal_ref)
    selection = context.action_selections.get(key)
    if selection is None:
        raise ValueError("participant normalized action selection must resolve")
    if binding.normalized_argument_name not in dict(selection.normalized_arguments):
        raise ValueError("participant normalized argument name must resolve")
    admission = context.action_admissions.get(binding.action_admission_ref)
    if admission is None:
        raise ValueError("participant action admission must resolve")
    if (
        admission.action_contract_address != binding.action_contract_address
        or admission.validated_selection != selection
        or admission.participant_address != binding.source_participant_address
    ):
        raise ValueError("participant action admission coordinates do not match")


def _validate_control_binding(
    binding: ParticipantControlOccurrenceFlowBindingModel,
    records: Mapping[str, ParticipantControlOccurrenceModel],
) -> None:
    record = records.get(binding.event_id)
    if record is None:
        raise ValueError("participant control occurrence must resolve")
    occurrence = record.occurrence
    identity, related = _control_identity(occurrence)
    coordinates_match = (
        binding.occurrence_kind,
        binding.occurrence_revision,
        binding.participant_address,
        binding.episode_id,
        binding.controller_ref,
        binding.authority_basis_refs,
        binding.control_policy_revision,
        binding.occurrence_identity_ref,
        binding.related_occurrence_refs,
        binding.predecessor_event_refs,
    ) == (
        occurrence.kind.value,
        occurrence.occurrence_revision,
        record.participant_address,
        record.episode_id,
        occurrence.controller_ref,
        tuple(sorted(occurrence.authority_basis_refs)),
        occurrence.policy_revision,
        identity,
        related,
        tuple(sorted(record.predecessor_event_refs)),
    )
    if not coordinates_match:
        raise ValueError("participant control occurrence binding coordinates do not match")
    if (binding.source_participant_address, binding.source_episode_id) != (
        record.participant_address,
        record.episode_id,
    ):
        raise ValueError("participant control occurrence binding scope does not match")


def _control_identity(occurrence: object) -> tuple[str, tuple[str, ...]]:
    if isinstance(occurrence, ParticipantProposalOccurrenceModel):
        related = tuple(
            sorted(ref for ref in (occurrence.source_proposal_ref, occurrence.transformation_ref) if ref is not None)
        )
        return occurrence.proposal_id, related
    if isinstance(occurrence, ParticipantApprovalOccurrenceModel | ParticipantDenialOccurrenceModel):
        return occurrence.decision_ref, (occurrence.proposal_ref,)
    if isinstance(occurrence, ParticipantExternalDirectionOccurrenceModel):
        return occurrence.target_ref, ()
    if isinstance(occurrence, ParticipantInterventionOccurrenceModel):
        return occurrence.intervention_ref, (occurrence.affected_occurrence_ref,)
    if isinstance(occurrence, ParticipantHandoffOccurrenceModel):
        return occurrence.resulting_controller_state_ref, tuple(
            sorted((occurrence.prior_controller_state_ref, occurrence.completion_evidence_ref))
        )
    if isinstance(occurrence, ParticipantOverrideOccurrenceModel):
        return occurrence.replacement_ref, (occurrence.superseded_occurrence_ref,)
    if isinstance(occurrence, ParticipantCancellationOccurrenceModel):
        return occurrence.target_ref, ()
    raise ValueError("participant control occurrence kind is unsupported")


def _validate_crossing_binding(
    binding: ParticipantCrossingOccurrenceFlowBindingModel,
    records: Mapping[str, ParticipantCrossingOccurrenceModel],
) -> None:
    record = records.get(binding.event_id)
    if record is None:
        raise ValueError("participant crossing occurrence must resolve")
    occurrence = record.occurrence
    identity, related = _crossing_identity(occurrence)
    subject = occurrence.subject
    policy = occurrence.policy
    coordinates_match = (
        binding.stage,
        binding.stage_identity_ref,
        binding.related_stage_refs,
        binding.participant_address,
        binding.episode_id,
        binding.subject_kind,
        binding.subject_contract_id,
        binding.subject_ref,
        binding.subject_revision,
        binding.subject_digest,
        binding.crossing_policy_id,
        binding.crossing_policy_revision,
        binding.crossing_policy_digest,
        binding.crossing_policy_decision_ref,
        binding.crossing_decision_cut_ref,
        binding.predecessor_event_refs,
    ) == (
        occurrence.stage,
        identity,
        related,
        record.participant_address,
        record.episode_id,
        subject.subject_kind.value,
        subject.contract_id,
        subject.subject_ref,
        subject.subject_revision,
        subject.subject_digest,
        policy.policy_id,
        policy.policy_revision,
        policy.policy_digest,
        policy.policy_decision_ref,
        policy.decision_cut_ref,
        tuple(sorted(record.predecessor_event_refs)),
    )
    if not coordinates_match:
        raise ValueError("participant crossing occurrence binding coordinates do not match")
    if (
        binding.policy.policy_id,
        binding.policy.policy_revision,
        binding.policy.policy_digest,
        binding.policy.policy_decision_ref,
        binding.policy.decision_cut_ref,
        binding.policy.effective_order,
    ) != (
        policy.policy_id,
        policy.policy_revision,
        policy.policy_digest,
        policy.policy_decision_ref,
        policy.decision_cut_ref,
        policy.effective_order,
    ):
        raise ValueError("participant crossing occurrence flow policy coordinates do not match")


def _crossing_identity(occurrence: object) -> tuple[str, tuple[str, ...]]:
    if isinstance(occurrence, ParticipantCrossingRequestModel):
        return occurrence.request_id, (occurrence.action_or_projection_ref,)
    if isinstance(occurrence, ParticipantCrossingDecisionModel):
        return occurrence.decision_id, (occurrence.request_ref,)
    if isinstance(occurrence, ParticipantCrossingTransformationModel):
        return occurrence.transformation_id, tuple(
            sorted(
                (
                    occurrence.decision_ref,
                    occurrence.source_subject.subject_ref,
                    occurrence.result_subject.subject_ref,
                    occurrence.rule_ref,
                )
            )
        )
    if isinstance(occurrence, ParticipantCrossingDisclosureModel):
        return occurrence.disclosure_id, tuple(
            sorted(ref for ref in (occurrence.decision_ref, occurrence.transformation_ref) if ref is not None)
        )
    if isinstance(occurrence, ParticipantCrossingDeliveryAttemptModel):
        return occurrence.attempt_id, tuple(
            sorted(
                ref
                for ref in (
                    occurrence.decision_ref,
                    occurrence.transformation_ref,
                    occurrence.owning_occurrence_ref,
                )
                if ref is not None
            )
        )
    if isinstance(occurrence, ParticipantCrossingDeliveryModel):
        return occurrence.delivery_id, tuple(
            sorted((occurrence.decision_ref, occurrence.attempt_ref, occurrence.owning_occurrence_ref))
        )
    if isinstance(occurrence, ParticipantCrossingObservationModel):
        return occurrence.observation_id, tuple(
            sorted((occurrence.decision_ref, occurrence.delivery_ref, occurrence.owning_observation_ref))
        )
    if isinstance(occurrence, ParticipantCrossingAuditModel):
        return occurrence.audit_record_ref, (occurrence.audited_event_ref,)
    raise ValueError("participant crossing occurrence stage is unsupported")
