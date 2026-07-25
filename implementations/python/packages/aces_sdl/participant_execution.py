"""Autonomous execution policy for ordinary ACES participants."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from ._base import SDLModel


class ParticipantExecutionFailurePolicy(str, Enum):
    """Disposition after a native participant action fails."""

    CONTINUE = "continue"
    STOP = "stop"


class ParticipantEvaluationAuthorityMode(str, Enum):
    """Whether a participant may contribute to evaluator-plane authority."""

    NONE = "none"
    DECLARED = "declared"


class ParticipantEvaluationAuthority(SDLModel):
    """Explicit evaluator-plane authority kept separate from participant actions."""

    mode: ParticipantEvaluationAuthorityMode
    objective_refs: list[str] = Field(default_factory=list)
    proof_producer_refs: list[str] = Field(default_factory=list)
    score_authority_refs: list[str] = Field(default_factory=list)
    receipt_authority_refs: list[str] = Field(default_factory=list)

    @field_validator(
        "objective_refs",
        "proof_producer_refs",
        "score_authority_refs",
        "receipt_authority_refs",
    )
    @classmethod
    def _unique_non_empty_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("participant evaluation-authority refs must be non-empty")
        if len(values) != len(set(values)):
            raise ValueError("participant evaluation-authority refs must be unique")
        return values

    @model_validator(mode="after")
    def _validate_authority_mode(self) -> ParticipantEvaluationAuthority:
        refs = (
            self.objective_refs,
            self.proof_producer_refs,
            self.score_authority_refs,
            self.receipt_authority_refs,
        )
        if self.mode == ParticipantEvaluationAuthorityMode.NONE and any(refs):
            raise ValueError("evaluation authority mode 'none' cannot carry authority refs")
        if self.mode == ParticipantEvaluationAuthorityMode.DECLARED and not any(refs):
            raise ValueError("evaluation authority mode 'declared' requires at least one authority ref")
        return self


class ParticipantAutonomousExecutionPolicy(SDLModel):
    """Deterministic scheduler binding over existing participant semantics."""

    profile: Literal["participant-autonomous-execution/v1"] = "participant-autonomous-execution/v1"
    participant_implementation_ref: str = Field(min_length=1)
    clock_ref: str = Field(min_length=1)
    progression_policy_ref: str = Field(min_length=1)
    temporal_constraint_refs: list[str] = Field(min_length=1)
    action_order: list[str] = Field(min_length=1)
    observation_boundary_ref: str = Field(min_length=1)
    selection_strategy: Literal["ordered_cycle"] = "ordered_cycle"
    max_action_attempts: int = Field(ge=1, le=1_000_000)
    max_in_flight: int = Field(default=1, ge=1, le=1024)
    failure_policy: ParticipantExecutionFailurePolicy = ParticipantExecutionFailurePolicy.STOP
    evaluation_authority: ParticipantEvaluationAuthority

    @field_validator("temporal_constraint_refs", "action_order")
    @classmethod
    def _unique_non_empty_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("participant autonomous-execution refs must be non-empty")
        if len(values) != len(set(values)):
            raise ValueError("participant autonomous-execution refs must be unique")
        return values


__all__ = [
    "ParticipantAutonomousExecutionPolicy",
    "ParticipantEvaluationAuthority",
    "ParticipantEvaluationAuthorityMode",
    "ParticipantExecutionFailurePolicy",
]
