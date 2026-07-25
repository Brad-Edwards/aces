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

from pydantic import Field, field_validator, model_validator

from ._base import SDLModel, parse_enum_or_var
from .propositions import TruthCompositionMode

SuccessMode = TruthCompositionMode


class ObjectiveSuccess(SDLModel):
    """Declarative success criteria for an objective.

    Success composes backend-neutral invariant or postcondition assertions.
    Probe implementations, graded scoring, and reward remain outside this
    construct.
    """

    mode: SuccessMode | str = SuccessMode.ALL_OF
    assertions: list[str] = Field(default_factory=list)
    threshold: int | None = Field(default=None, ge=1)

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_conditions(cls, value: object) -> object:
        if isinstance(value, dict) and "conditions" in value:
            raise ValueError(
                "objective success.conditions cannot state backend-neutral truth; "
                "declare propositions and assertions, then reference success.assertions"
            )
        return value

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, v: str) -> SuccessMode | str:
        return parse_enum_or_var(v, SuccessMode, field_name="mode")

    @model_validator(mode="after")
    def validate_non_empty(self) -> "ObjectiveSuccess":
        if not self.assertions:
            raise ValueError("Objective success must reference at least one assertion")
        if self.mode == SuccessMode.AT_LEAST:
            if self.threshold is None:
                raise ValueError("at_least objective success requires threshold")
            if self.threshold > len(self.assertions):
                raise ValueError("objective success threshold cannot exceed assertion count")
        elif self.threshold is not None:
            raise ValueError("objective success threshold is valid only for at_least mode")
        return self


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
