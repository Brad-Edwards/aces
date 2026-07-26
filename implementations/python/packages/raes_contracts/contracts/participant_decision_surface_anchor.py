"""Typed event anchors for SEM-220 participant decision surfaces."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StrictInt, model_validator

from .base import ContractModel, NonEmptyString


def _require_unique(values: list[str], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


class _ParticipantDecisionSurfaceProjectionAnchorBase(ContractModel):
    """Coordinates shared by every trusted decision-surface event anchor."""

    participant_address: NonEmptyString
    episode_id: NonEmptyString
    decision_surface_order: StrictInt = Field(ge=0)
    event_ref: NonEmptyString
    anchor_order: StrictInt = Field(ge=0)
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    provenance_refs: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_anchor_refs(self) -> _ParticipantDecisionSurfaceProjectionAnchorBase:
        _require_unique(self.evidence_refs, "evidence_refs")
        _require_unique(self.provenance_refs, "provenance_refs")
        if self.event_ref not in self.provenance_refs:
            raise ValueError("projection anchor event_ref must be carried by provenance_refs")
        return self


class ParticipantDecisionSurfaceEpisodeReadinessAnchorModel(_ParticipantDecisionSurfaceProjectionAnchorBase):
    """RUN-311 ``episode_running`` anchor for one episode's initial surface."""

    anchor_kind: Literal["episode_readiness"]
    event_type: Literal["episode_running"]
    episode_sequence_number: StrictInt = Field(ge=0)


class ParticipantDecisionSurfaceBehaviorAnchorModel(_ParticipantDecisionSurfaceProjectionAnchorBase):
    """One terminal observation and exact prefix anchoring a later surface."""

    anchor_kind: Literal["behavior_event"]
    event_type: Literal["observation_emitted"]
    action_instance_id: NonEmptyString
    history_prefix_length: StrictInt = Field(ge=1)

    @model_validator(mode="after")
    def _validate_history_prefix(self) -> ParticipantDecisionSurfaceBehaviorAnchorModel:
        if self.history_prefix_length != self.anchor_order + 1:
            raise ValueError("behavior projection anchor history_prefix_length must equal anchor_order + 1")
        return self


ParticipantDecisionSurfaceProjectionAnchorModel = Annotated[
    ParticipantDecisionSurfaceEpisodeReadinessAnchorModel | ParticipantDecisionSurfaceBehaviorAnchorModel,
    Field(discriminator="anchor_kind"),
]
