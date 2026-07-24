"""Cross-record validation for API-409 participant control occurrences."""

from __future__ import annotations

from collections.abc import Sequence

from .participant_control import (
    ParticipantApprovalOccurrenceModel,
    ParticipantCancellationOccurrenceModel,
    ParticipantControlDeclarationModel,
    ParticipantControlOccurrenceModel,
    ParticipantControlTargetContextModel,
    ParticipantControlTargetKind,
    ParticipantDenialOccurrenceModel,
    ParticipantExternalDirectionOccurrenceModel,
    ParticipantHandoffOccurrenceModel,
    ParticipantInterventionOccurrenceModel,
    ParticipantOverrideOccurrenceModel,
    ParticipantProposalOccurrenceModel,
)

TargetIndex = dict[tuple[ParticipantControlTargetKind, str], ParticipantControlTargetContextModel]


def validate_participant_control_occurrence_context(
    records: Sequence[ParticipantControlOccurrenceModel],
    *,
    declarations: Sequence[ParticipantControlDeclarationModel],
    known_targets: Sequence[ParticipantControlTargetContextModel] = (),
) -> None:
    """Fail closed when API-409 occurrences disagree across identity and policy joins."""

    declarations_by_ref: dict[str, ParticipantControlDeclarationModel] = {}
    for declaration in declarations:
        existing = declarations_by_ref.setdefault(declaration.declaration_ref, declaration)
        if existing != declaration:
            raise ValueError("declaration identity was reused with different semantics")

    records_by_event_id: dict[str, ParticipantControlOccurrenceModel] = {}
    proposal_records: dict[str, ParticipantControlOccurrenceModel] = {}
    decision_refs: set[str] = set()
    target_contexts: TargetIndex = {}
    for target in known_targets:
        _register_target(target_contexts, target)
    for record in records:
        existing = records_by_event_id.get(record.event_id)
        if existing is not None:
            if existing != record:
                raise ValueError("event identity was reused with different semantics")
            continue
        records_by_event_id[record.event_id] = record
        occurrence = record.occurrence
        _register_target(
            target_contexts,
            ParticipantControlTargetContextModel(
                target_kind=ParticipantControlTargetKind.CONTROL,
                target_ref=record.event_id,
                target_revision=occurrence.occurrence_revision,
                participant_address=record.participant_address,
                episode_id=record.episode_id,
            ),
        )
        if isinstance(occurrence, ParticipantProposalOccurrenceModel):
            existing_proposal = proposal_records.setdefault(occurrence.proposal_id, record)
            if existing_proposal != record:
                raise ValueError("proposal identity was reused with different semantics")
            _register_target(
                target_contexts,
                ParticipantControlTargetContextModel(
                    target_kind=ParticipantControlTargetKind.PROPOSAL,
                    target_ref=occurrence.proposal_id,
                    target_revision=occurrence.proposal_revision,
                    participant_address=record.participant_address,
                    episode_id=record.episode_id,
                ),
            )
        elif isinstance(occurrence, (ParticipantApprovalOccurrenceModel, ParticipantDenialOccurrenceModel)):
            if occurrence.decision_ref in decision_refs:
                raise ValueError("decision identity was reused")
            decision_refs.add(occurrence.decision_ref)
            _register_target(
                target_contexts,
                ParticipantControlTargetContextModel(
                    target_kind=ParticipantControlTargetKind.DECISION,
                    target_ref=occurrence.decision_ref,
                    target_revision=occurrence.decision_revision,
                    participant_address=record.participant_address,
                    episode_id=record.episode_id,
                ),
            )

    for record in records_by_event_id.values():
        occurrence = record.occurrence
        declaration = declarations_by_ref.get(occurrence.declaration_ref)
        if declaration is None:
            raise ValueError("declaration reference must resolve")
        if not _declaration_agrees(record, declaration):
            raise ValueError("occurrence and declaration coordinates disagree")

        if isinstance(occurrence, ParticipantProposalOccurrenceModel):
            _validate_transformed_proposal(record, proposal_records)
        elif isinstance(occurrence, (ParticipantApprovalOccurrenceModel, ParticipantDenialOccurrenceModel)):
            _validate_proposal_decision(record, proposal_records)
        else:
            _validate_occurrence_target(record, target_contexts=target_contexts)


def _declaration_agrees(
    record: ParticipantControlOccurrenceModel,
    declaration: ParticipantControlDeclarationModel,
) -> bool:
    occurrence = record.occurrence
    comparisons = (
        record.participant_address == declaration.participant_address,
        record.episode_id == declaration.episode_id,
        record.actor_ref == declaration.controller_ref,
        occurrence.kind == declaration.kind,
        occurrence.controller_ref == declaration.controller_ref,
        occurrence.controller_state_ref == declaration.controller_state_ref,
        occurrence.authority_basis_refs == declaration.authority_basis_refs,
        occurrence.controlled_scope_refs == declaration.controlled_scope_refs,
        occurrence.behavior_specification_ref == declaration.behavior_specification_ref,
        occurrence.mixed_control_policy_ref == declaration.mixed_control_policy_ref,
        occurrence.policy_revision == declaration.policy_revision,
        occurrence.expected_state_revision == declaration.expected_state_revision,
        occurrence.effective_order == declaration.effective_order,
        occurrence.valid_from_order == declaration.valid_from_order,
        occurrence.valid_until_order == declaration.valid_until_order,
    )
    return all(comparisons)


def _register_target(target_contexts: TargetIndex, target: ParticipantControlTargetContextModel) -> None:
    key = (target.target_kind, target.target_ref)
    existing = target_contexts.setdefault(key, target)
    if existing != target:
        raise ValueError("target identity was reused with different revision or scope")


def _validate_transformed_proposal(
    record: ParticipantControlOccurrenceModel,
    proposal_records: dict[str, ParticipantControlOccurrenceModel],
) -> None:
    occurrence = record.occurrence
    if not isinstance(occurrence, ParticipantProposalOccurrenceModel) or occurrence.source_proposal_ref is None:
        return
    source = proposal_records.get(occurrence.source_proposal_ref)
    if source is None:
        raise ValueError("transformed proposal source must resolve")
    source_occurrence = source.occurrence
    assert isinstance(source_occurrence, ParticipantProposalOccurrenceModel)
    if occurrence.source_proposal_revision != source_occurrence.proposal_revision:
        raise ValueError("transformed proposal source revision is stale")
    if (record.participant_address, record.episode_id) != (source.participant_address, source.episode_id):
        raise ValueError("transformed proposal scope must match its source")
    required_provenance = {source.event_id, occurrence.transformation_ref}
    if not required_provenance.issubset(record.provenance_refs):
        raise ValueError("transformed proposal provenance must bind its source and transformation")
    if not set(source.object_marking_refs).issubset(record.object_marking_refs):
        raise ValueError("transformed proposal must inherit source markings")


def _validate_proposal_decision(
    record: ParticipantControlOccurrenceModel,
    proposal_records: dict[str, ParticipantControlOccurrenceModel],
) -> None:
    occurrence = record.occurrence
    if not isinstance(occurrence, (ParticipantApprovalOccurrenceModel, ParticipantDenialOccurrenceModel)):
        return
    proposal = proposal_records.get(occurrence.proposal_ref)
    if proposal is None:
        raise ValueError("proposal reference must resolve")
    proposal_occurrence = proposal.occurrence
    assert isinstance(proposal_occurrence, ParticipantProposalOccurrenceModel)
    if occurrence.proposal_revision != proposal_occurrence.proposal_revision:
        raise ValueError("proposal revision is stale")
    if (record.participant_address, record.episode_id) != (proposal.participant_address, proposal.episode_id):
        raise ValueError("decision scope must match its proposal")
    if occurrence.effective_order <= proposal_occurrence.effective_order:
        raise ValueError("decision order must follow its proposal")
    if proposal.event_id not in record.predecessor_event_refs:
        raise ValueError("decision must follow its proposal occurrence")


def _validate_occurrence_target(
    record: ParticipantControlOccurrenceModel,
    *,
    target_contexts: TargetIndex,
) -> None:
    occurrence = record.occurrence
    if isinstance(occurrence, ParticipantExternalDirectionOccurrenceModel):
        target = (occurrence.target_kind, occurrence.target_ref, occurrence.target_revision)
    elif isinstance(occurrence, ParticipantInterventionOccurrenceModel):
        target = (
            occurrence.affected_target_kind,
            occurrence.affected_occurrence_ref,
            occurrence.affected_revision,
        )
    elif isinstance(occurrence, ParticipantHandoffOccurrenceModel):
        if occurrence.prior_controller_state_ref != occurrence.controller_state_ref:
            raise ValueError("handoff prior controller state must match the occurrence state")
        return
    elif isinstance(occurrence, ParticipantOverrideOccurrenceModel):
        target = (
            occurrence.superseded_target_kind,
            occurrence.superseded_occurrence_ref,
            occurrence.superseded_revision,
        )
    elif isinstance(occurrence, ParticipantCancellationOccurrenceModel):
        target = (occurrence.target_kind, occurrence.target_ref, occurrence.target_revision)
    else:
        return
    _validate_typed_target(
        record,
        target_kind=target[0],
        target_ref=target[1],
        target_revision=target[2],
        target_contexts=target_contexts,
    )


def _validate_typed_target(
    record: ParticipantControlOccurrenceModel,
    *,
    target_kind: ParticipantControlTargetKind,
    target_ref: str,
    target_revision: int,
    target_contexts: TargetIndex,
) -> None:
    target = target_contexts.get((target_kind, target_ref))
    if target is None:
        raise ValueError("typed target reference and kind must resolve")
    if target.target_revision != target_revision:
        raise ValueError("target revision must match")
    if (target.participant_address, target.episode_id) != (record.participant_address, record.episode_id):
        raise ValueError("target scope must match")


__all__ = ["validate_participant_control_occurrence_context"]
