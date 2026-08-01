"""Shared exact participant state-cut contracts for decision and information surfaces."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StrictInt, model_validator

from .base import ContractModel, NonEmptyString

ParticipantDecisionSurfaceStateCutOrderModel = Literal[
    "control_plane_order",
    "backend_serialized_order",
    "behavior_history_order",
]


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
        if len(self.predecessor_event_refs) != len(set(self.predecessor_event_refs)):
            raise ValueError("predecessor_event_refs must not contain duplicates")
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
        if len(self.frontier_event_refs) != len(set(self.frontier_event_refs)):
            raise ValueError("frontier_event_refs must not contain duplicates")
        return self


ParticipantDecisionSurfaceStateCutModel = Annotated[
    ParticipantDecisionSurfaceSequenceCutModel | ParticipantDecisionSurfaceCausalCutModel,
    Field(discriminator="cut_kind"),
]


__all__ = (
    "ParticipantDecisionSurfaceCausalCutModel",
    "ParticipantDecisionSurfaceSequenceCutModel",
    "ParticipantDecisionSurfaceStateCutModel",
    "ParticipantDecisionSurfaceStateCutOrderModel",
)
