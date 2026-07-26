"""Closed caller-intent models for RUN-310 supervisory mediation."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator
from raes_contracts.contracts.participant_control import ParticipantControlTargetKind


class ParticipantControlIntentBase(BaseModel):
    """Caller-owned coordinates shared by all supervisory intents."""

    model_config = ConfigDict(extra="forbid")

    declaration_ref: str = Field(min_length=1)
    episode_id: str = Field(min_length=1)
    client_correlation_id: str = Field(min_length=1)
    policy_revision: str = Field(min_length=1)
    expected_state_revision: int = Field(ge=0)
    provenance_refs: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    object_marking_refs: list[str] = Field(min_length=1)
    limitation_refs: list[str] = Field(min_length=1)


class ParticipantProposalControlIntent(ParticipantControlIntentBase):
    kind: Literal["proposal"] = "proposal"
    proposal_id: str = Field(min_length=1)
    proposal_revision: int = Field(gt=0)
    action_contract_ref: str = Field(min_length=1)
    decision_surface_ref: str | None = None
    proposal_binding_ref: str | None = None
    payload_ref: str | None = None
    payload_digest: str | None = None
    source_proposal_ref: str | None = None
    source_proposal_revision: int | None = Field(default=None, gt=0)
    transformation_ref: str | None = None

    @model_validator(mode="after")
    def _require_one_payload_source(self) -> ParticipantProposalControlIntent:
        if (self.payload_ref is None) == (self.payload_digest is None):
            raise ValueError("proposal intent requires exactly one payload reference or digest")
        return self


class ParticipantApprovalControlIntent(ParticipantControlIntentBase):
    kind: Literal["approval"] = "approval"
    proposal_ref: str = Field(min_length=1)
    proposal_revision: int = Field(gt=0)
    decision_ref: str = Field(min_length=1)
    decision_revision: int = Field(gt=0)


class ParticipantDenialControlIntent(ParticipantControlIntentBase):
    kind: Literal["denial"] = "denial"
    proposal_ref: str = Field(min_length=1)
    proposal_revision: int = Field(gt=0)
    decision_ref: str = Field(min_length=1)
    decision_revision: int = Field(gt=0)


class ParticipantExternalDirectionControlIntent(ParticipantControlIntentBase):
    kind: Literal["external-direction"] = "external-direction"
    target_kind: Literal[
        ParticipantControlTargetKind.PROPOSAL,
        ParticipantControlTargetKind.ACTION,
        ParticipantControlTargetKind.CONTROL,
    ]
    target_ref: str = Field(min_length=1)
    target_revision: int = Field(gt=0)


class ParticipantInterventionControlIntent(ParticipantControlIntentBase):
    kind: Literal["intervention"] = "intervention"
    affected_target_kind: Literal[
        ParticipantControlTargetKind.ACTION,
        ParticipantControlTargetKind.CONTROL,
        ParticipantControlTargetKind.ATTEMPT,
    ]
    affected_occurrence_ref: str = Field(min_length=1)
    affected_revision: int = Field(gt=0)
    intervention_ref: str = Field(min_length=1)


class ParticipantHandoffControlIntent(ParticipantControlIntentBase):
    kind: Literal["handoff"] = "handoff"
    completion_evidence_ref: str = Field(min_length=1)


class ParticipantOverrideControlIntent(ParticipantControlIntentBase):
    kind: Literal["override"] = "override"
    superseded_target_kind: Literal[
        ParticipantControlTargetKind.CONTROL,
        ParticipantControlTargetKind.DECISION,
    ]
    superseded_occurrence_ref: str = Field(min_length=1)
    superseded_revision: int = Field(gt=0)
    replacement_ref: str = Field(min_length=1)


class ParticipantCancellationControlIntent(ParticipantControlIntentBase):
    kind: Literal["cancellation"] = "cancellation"
    target_kind: Literal[
        ParticipantControlTargetKind.PROPOSAL,
        ParticipantControlTargetKind.DECISION,
        ParticipantControlTargetKind.ADMITTED_ACTION,
        ParticipantControlTargetKind.ATTEMPT,
    ]
    target_ref: str = Field(min_length=1)
    target_revision: int = Field(gt=0)


ParticipantControlIntent: TypeAlias = Annotated[
    ParticipantProposalControlIntent
    | ParticipantApprovalControlIntent
    | ParticipantDenialControlIntent
    | ParticipantExternalDirectionControlIntent
    | ParticipantInterventionControlIntent
    | ParticipantHandoffControlIntent
    | ParticipantOverrideControlIntent
    | ParticipantCancellationControlIntent,
    Field(discriminator="kind"),
]


__all__ = (
    "ParticipantApprovalControlIntent",
    "ParticipantCancellationControlIntent",
    "ParticipantControlIntent",
    "ParticipantControlIntentBase",
    "ParticipantDenialControlIntent",
    "ParticipantExternalDirectionControlIntent",
    "ParticipantHandoffControlIntent",
    "ParticipantInterventionControlIntent",
    "ParticipantOverrideControlIntent",
    "ParticipantProposalControlIntent",
)
