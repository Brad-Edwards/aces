"""Authoritative target resolution for RUN-310 supervisory occurrences."""

from __future__ import annotations

from dataclasses import dataclass

from raes_contracts.contracts import (
    ParticipantBehaviorHistoryEventModel,
    ParticipantControlOccurrenceModel,
)
from raes_contracts.contracts.participant_control import (
    ParticipantApprovalOccurrenceModel,
    ParticipantControlDisposition,
    ParticipantControlTargetContextModel,
    ParticipantControlTargetKind,
    ParticipantDenialOccurrenceModel,
    ParticipantProposalOccurrenceModel,
)
from raes_contracts.runtime_state import RuntimeSnapshot

from .participant_control_intents import (
    ParticipantApprovalControlIntent,
    ParticipantCancellationControlIntent,
    ParticipantControlIntent,
    ParticipantDenialControlIntent,
    ParticipantExternalDirectionControlIntent,
    ParticipantInterventionControlIntent,
    ParticipantOverrideControlIntent,
    ParticipantProposalControlIntent,
)


@dataclass(frozen=True)
class ResolvedParticipantControlTarget:
    """One target whose revision and runtime scope resolved exactly."""

    context: ParticipantControlTargetContextModel
    predecessor_ref: str


def resolve_participant_control_target(
    snapshot: RuntimeSnapshot,
    intent: ParticipantControlIntent,
    *,
    participant_address: str,
) -> tuple[ResolvedParticipantControlTarget | None, str | None]:
    """Resolve an intent target without accepting caller-supplied coordinates."""

    requested = _intent_target(intent)
    if requested is None:
        return None, None
    kind, reference, revision = requested
    matches = [
        candidate
        for candidate in participant_control_targets(snapshot)
        if candidate.context.target_kind is kind
        and candidate.context.target_ref == reference
        and candidate.context.target_revision == revision
        and candidate.context.participant_address == participant_address
        and candidate.context.episode_id == intent.episode_id
    ]
    if len(matches) != 1:
        return None, "invalid-target"
    return matches[0], None


def participant_control_target_contexts(
    snapshot: RuntimeSnapshot,
) -> tuple[ParticipantControlTargetContextModel, ...]:
    """Return all lifecycle targets used by API-409 contextual validation."""

    return tuple(candidate.context for candidate in participant_control_targets(snapshot))


def participant_control_targets(
    snapshot: RuntimeSnapshot,
) -> tuple[ResolvedParticipantControlTarget, ...]:
    """Project control and behavior histories into typed target coordinates."""

    targets: dict[
        tuple[ParticipantControlTargetKind, str, int, str, str],
        ResolvedParticipantControlTarget,
    ] = {}
    for events in snapshot.participant_control_history.values():
        for payload in events:
            _register_control_targets(
                targets,
                ParticipantControlOccurrenceModel.model_validate(payload),
            )
    for events in snapshot.participant_behavior_history.values():
        for payload in events:
            _register_behavior_targets(
                targets,
                ParticipantBehaviorHistoryEventModel.model_validate(payload),
            )
    return tuple(targets.values())


def _register_control_targets(
    targets: dict[
        tuple[ParticipantControlTargetKind, str, int, str, str],
        ResolvedParticipantControlTarget,
    ],
    event: ParticipantControlOccurrenceModel,
) -> None:
    occurrence = event.occurrence
    if occurrence.disposition is not ParticipantControlDisposition.ACCEPTED:
        return
    _register(
        targets,
        kind=ParticipantControlTargetKind.CONTROL,
        reference=event.event_id,
        revision=occurrence.occurrence_revision,
        participant_address=event.participant_address,
        episode_id=event.episode_id,
        predecessor_ref=event.event_id,
    )
    if isinstance(occurrence, ParticipantProposalOccurrenceModel):
        _register(
            targets,
            kind=ParticipantControlTargetKind.PROPOSAL,
            reference=occurrence.proposal_id,
            revision=occurrence.proposal_revision,
            participant_address=event.participant_address,
            episode_id=event.episode_id,
            predecessor_ref=event.event_id,
        )
    elif isinstance(occurrence, (ParticipantApprovalOccurrenceModel, ParticipantDenialOccurrenceModel)):
        _register(
            targets,
            kind=ParticipantControlTargetKind.DECISION,
            reference=occurrence.decision_ref,
            revision=occurrence.decision_revision,
            participant_address=event.participant_address,
            episode_id=event.episode_id,
            predecessor_ref=event.event_id,
        )


def _register_behavior_targets(
    targets: dict[
        tuple[ParticipantControlTargetKind, str, int, str, str],
        ResolvedParticipantControlTarget,
    ],
    event: ParticipantBehaviorHistoryEventModel,
) -> None:
    if event.event_type.value != "action_attempted":
        return
    phase = event.lifecycle_phase.value if event.lifecycle_phase is not None else None
    _register(
        targets,
        kind=ParticipantControlTargetKind.ACTION,
        reference=event.action_instance_id,
        revision=1,
        participant_address=event.participant_address,
        episode_id=event.episode_id,
        predecessor_ref=event.action_instance_id,
    )
    admission = event.admission_disposition.value if event.admission_disposition is not None else None
    if phase == "selection_or_admission" and admission == "admitted":
        _register(
            targets,
            kind=ParticipantControlTargetKind.ADMITTED_ACTION,
            reference=event.action_instance_id,
            revision=1,
            participant_address=event.participant_address,
            episode_id=event.episode_id,
            predecessor_ref=event.action_instance_id,
        )
    if phase == "execution_attempt":
        attempt_ref = event.operation_ref or event.action_instance_id
        _register(
            targets,
            kind=ParticipantControlTargetKind.ATTEMPT,
            reference=attempt_ref,
            revision=1,
            participant_address=event.participant_address,
            episode_id=event.episode_id,
            predecessor_ref=attempt_ref,
        )


def _register(
    targets: dict[
        tuple[ParticipantControlTargetKind, str, int, str, str],
        ResolvedParticipantControlTarget,
    ],
    *,
    kind: ParticipantControlTargetKind,
    reference: str,
    revision: int,
    participant_address: str,
    episode_id: str,
    predecessor_ref: str,
) -> None:
    context = ParticipantControlTargetContextModel(
        target_kind=kind,
        target_ref=reference,
        target_revision=revision,
        participant_address=participant_address,
        episode_id=episode_id,
    )
    key = (kind, reference, revision, participant_address, episode_id)
    candidate = ResolvedParticipantControlTarget(context=context, predecessor_ref=predecessor_ref)
    existing = targets.setdefault(key, candidate)
    if existing != candidate:
        raise ValueError("runtime target identity is ambiguous")


def _intent_target(
    intent: ParticipantControlIntent,
) -> tuple[ParticipantControlTargetKind, str, int] | None:
    if isinstance(intent, ParticipantProposalControlIntent):
        if intent.source_proposal_ref is None:
            return None
        assert intent.source_proposal_revision is not None
        return (
            ParticipantControlTargetKind.PROPOSAL,
            intent.source_proposal_ref,
            intent.source_proposal_revision,
        )
    if isinstance(intent, (ParticipantApprovalControlIntent, ParticipantDenialControlIntent)):
        return ParticipantControlTargetKind.PROPOSAL, intent.proposal_ref, intent.proposal_revision
    if isinstance(intent, ParticipantExternalDirectionControlIntent):
        return intent.target_kind, intent.target_ref, intent.target_revision
    if isinstance(intent, ParticipantInterventionControlIntent):
        return intent.affected_target_kind, intent.affected_occurrence_ref, intent.affected_revision
    if isinstance(intent, ParticipantOverrideControlIntent):
        return intent.superseded_target_kind, intent.superseded_occurrence_ref, intent.superseded_revision
    if isinstance(intent, ParticipantCancellationControlIntent):
        return intent.target_kind, intent.target_ref, intent.target_revision
    return None


__all__ = (
    "ResolvedParticipantControlTarget",
    "participant_control_target_contexts",
    "resolve_participant_control_target",
)
