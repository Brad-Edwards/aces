"""Contract-specific source validation for participant information state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from .participant_context import ParticipantContextViewModel
from .participant_decision_state_cut import (
    ParticipantDecisionSurfaceSequenceCutModel,
    ParticipantDecisionSurfaceStateCutModel,
)
from .participant_envelopes import ParticipantSharedStateRecordModel
from .participant_observation import ParticipantObservationEnvelopeModel
from .participant_runtime import ParticipantBehaviorHistoryEventModel, ParticipantEpisodeStateModel

SourceKey = tuple[str, str]


class _InformationStateRecord(Protocol):
    participant_address: str
    episode_id: str
    information_state_ref: str
    state_cut: ParticipantDecisionSurfaceStateCutModel
    audience_scope_ref: str
    visibility_projection_ref: str
    projection_policy_revision: str
    redaction_policy_ref: str
    redaction_policy_revision: str


class _InformationStateSourceCoordinate(Protocol):
    participant_address: str
    episode_id: str
    state_cut: ParticipantDecisionSurfaceStateCutModel
    audience_scope_ref: str
    visibility_projection_ref: str
    projection_policy_revision: str
    redaction_policy_ref: str
    redaction_policy_revision: str


class _InformationStateSourceRef(Protocol):
    contract_id: str
    ref: str
    relation: str


_SOURCE_RELATIONS_BY_CONTRACT: Mapping[str, frozenset[str]] = {
    "participant-observation-envelope-v1": frozenset({"observed", "disclosed"}),
    "participant-context-view-v1": frozenset({"derived", "disclosed"}),
    "participant-shared-state-record-v1": frozenset({"observed", "disclosed", "shared_state_projection"}),
    "participant-behavior-history-event-stream-v1": frozenset({"observed"}),
    "participant-episode-state-envelope-v1": frozenset({"authored_initial", "derived"}),
}


def require_source_coordinate(
    record: _InformationStateRecord,
    key: SourceKey,
    source_coordinates: Mapping[SourceKey, _InformationStateSourceCoordinate],
) -> None:
    """Require one trusted source coordinate to equal every governed record coordinate."""

    coordinate = source_coordinates.get(key)
    if coordinate is None:
        raise ValueError("information state source governed coordinate does not resolve")
    if coordinate.participant_address != record.participant_address or coordinate.episode_id != record.episode_id:
        raise ValueError("information state source participant or episode coordinate does not match")
    if coordinate.state_cut != record.state_cut:
        raise ValueError("information state source cut membership does not match the exact state cut")
    governed_coordinates = (
        ("audience scope", coordinate.audience_scope_ref, record.audience_scope_ref),
        ("visibility projection", coordinate.visibility_projection_ref, record.visibility_projection_ref),
        ("projection policy revision", coordinate.projection_policy_revision, record.projection_policy_revision),
        ("redaction policy", coordinate.redaction_policy_ref, record.redaction_policy_ref),
        ("redaction policy revision", coordinate.redaction_policy_revision, record.redaction_policy_revision),
    )
    for label, actual, expected in governed_coordinates:
        if actual != expected:
            raise ValueError(f"information state source {label} coordinate does not match")


def _validate_source_sequence_cut(record: _InformationStateRecord, sequence_number: int | None) -> None:
    if isinstance(record.state_cut, ParticipantDecisionSurfaceSequenceCutModel) and (
        sequence_number is None or sequence_number > record.state_cut.anchor_order
    ):
        raise ValueError("information state source lies after the exact sequence cut")


def _validate_observation_source(record: _InformationStateRecord, source_ref: str, resolved: object) -> None:
    observation = ParticipantObservationEnvelopeModel.model_validate(resolved)
    if observation.observation_ref != source_ref:
        raise ValueError("information state observation source identity does not match")
    if observation.participant_address != record.participant_address or observation.episode_id != record.episode_id:
        raise ValueError("information state observation source coordinate does not match")
    _validate_source_sequence_cut(record, observation.sequence_number)
    if observation.visibility_projection_ref != record.visibility_projection_ref:
        raise ValueError("information state observation visibility projection does not match")
    if observation.redaction_policy_ref != record.redaction_policy_ref:
        raise ValueError("information state observation redaction policy does not match")
    if observation.information_state_ref not in {None, record.information_state_ref}:
        raise ValueError("information state observation back-reference does not match")


def _validate_context_view_source(record: _InformationStateRecord, source_ref: str, resolved: object) -> None:
    context_view = ParticipantContextViewModel.model_validate(resolved)
    if source_ref not in {context_view.view_id, context_view.view_ref}:
        raise ValueError("information state context-view source identity does not match")
    if context_view.participant_address != record.participant_address or context_view.episode_id != record.episode_id:
        raise ValueError("information state context-view source coordinate does not match")
    if context_view.visibility_projection_ref != record.visibility_projection_ref:
        raise ValueError("information state context-view visibility projection does not match")
    if context_view.redaction_policy_ref != record.redaction_policy_ref:
        raise ValueError("information state context-view redaction policy does not match")


def _validate_shared_state_source(record: _InformationStateRecord, source_ref: str, resolved: object) -> None:
    shared_state = ParticipantSharedStateRecordModel.model_validate(resolved)
    if source_ref not in {shared_state.event_id, shared_state.state_address}:
        raise ValueError("information state shared-state source identity does not match")
    if shared_state.participant_address != record.participant_address or shared_state.episode_id != record.episode_id:
        raise ValueError("information state shared-state source coordinate does not match")
    _validate_source_sequence_cut(record, shared_state.sequence_number)
    if shared_state.visibility_projection_basis != record.visibility_projection_ref:
        raise ValueError("information state shared-state visibility projection does not match")
    if shared_state.redaction_policy_ref != record.redaction_policy_ref:
        raise ValueError("information state shared-state redaction policy does not match")


def _validate_behavior_history_source(record: _InformationStateRecord, resolved: object) -> None:
    if not isinstance(resolved, Sequence) or isinstance(resolved, (str, bytes, bytearray)) or not resolved:
        raise ValueError("information state behavior-history source must resolve to a non-empty event stream")
    for item in resolved:
        event = ParticipantBehaviorHistoryEventModel.model_validate(item)
        if event.participant_address != record.participant_address or event.episode_id != record.episode_id:
            raise ValueError("information state behavior-history source coordinate does not match")
        if isinstance(record.state_cut, ParticipantDecisionSurfaceSequenceCutModel):
            _validate_source_sequence_cut(record, event.realized_order)


def _validate_episode_state_source(record: _InformationStateRecord, source_ref: str, resolved: object) -> None:
    episode_state = ParticipantEpisodeStateModel.model_validate(resolved)
    if source_ref != episode_state.episode_id:
        raise ValueError("information state episode-state source identity does not match")
    if episode_state.participant_address != record.participant_address or episode_state.episode_id != record.episode_id:
        raise ValueError("information state episode-state source coordinate does not match")
    if (
        isinstance(record.state_cut, ParticipantDecisionSurfaceSequenceCutModel)
        and record.state_cut.history_domain == "participant_episode_lifecycle"
    ):
        _validate_source_sequence_cut(record, episode_state.sequence_number)


def validate_resolved_source(
    record: _InformationStateRecord,
    source: _InformationStateSourceRef,
    resolved: object,
) -> None:
    """Apply contract- and relation-specific source invariants."""

    allowed_relations = _SOURCE_RELATIONS_BY_CONTRACT[source.contract_id]
    if source.relation not in allowed_relations:
        raise ValueError("information state source relation is not admitted for its contract")
    if source.contract_id == "participant-observation-envelope-v1":
        _validate_observation_source(record, source.ref, resolved)
    elif source.contract_id == "participant-context-view-v1":
        _validate_context_view_source(record, source.ref, resolved)
    elif source.contract_id == "participant-shared-state-record-v1":
        _validate_shared_state_source(record, source.ref, resolved)
    elif source.contract_id == "participant-behavior-history-event-stream-v1":
        _validate_behavior_history_source(record, resolved)
    else:
        _validate_episode_state_source(record, source.ref, resolved)


__all__ = ("require_source_coordinate", "validate_resolved_source")
