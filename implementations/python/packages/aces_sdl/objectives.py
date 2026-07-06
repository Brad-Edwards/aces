"""Declarative experiment objectives for the SDL.

Objectives bind together:
- who acts (`agent` or `entity`)
- what they are trying to affect (`targets`, `actions`)
- when it matters (`window`)
- how success is interpreted (`success`)

This is intentionally different from backend-specific runtime probes.
The SDL carries experiment semantics; concrete evaluation mechanics live
in runtime adapters.
"""

from enum import Enum

from pydantic import Field, field_validator, model_validator

from ._base import SDLModel, parse_enum_or_var


class SuccessMode(str, Enum):
    """How referenced success criteria combine."""

    ALL_OF = "all_of"
    ANY_OF = "any_of"


class ObjectiveSuccess(SDLModel):
    """Declarative success criteria for an objective.

    Per ADR-073, objective success references observable state (``conditions``)
    only. The OCR-inherited scoring pipeline (``metrics`` / ``evaluations`` /
    ``tlos`` / ``goals``) was removed from the SDL; graded scoring and reward
    live in the experiment/evaluator plane (ADR-055/064/069).
    """

    mode: SuccessMode | str = SuccessMode.ALL_OF
    conditions: list[str] = Field(default_factory=list)

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, v: str) -> SuccessMode | str:
        return parse_enum_or_var(v, SuccessMode, field_name="mode")

    @model_validator(mode="after")
    def validate_non_empty(self) -> "ObjectiveSuccess":
        if self.conditions:
            return self
        raise ValueError("Objective success must reference at least one condition")


class ObjectiveWindow(SDLModel):
    """Optional orchestration window constraining when an objective applies."""

    stories: list[str] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)


class Objective(SDLModel):
    """A declarative experiment objective."""

    name: str = ""
    description: str = ""
    agent: str = ""
    entity: str = ""
    actions: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    success: ObjectiveSuccess
    window: ObjectiveWindow | None = None
    depends_on: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_actor_binding(self) -> "Objective":
        has_agent = bool(self.agent)
        has_entity = bool(self.entity)
        if has_agent == has_entity:
            raise ValueError("Objective must declare exactly one of 'agent' or 'entity'")
        return self
