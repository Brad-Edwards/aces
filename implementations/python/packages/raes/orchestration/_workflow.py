"""The declarative experiment workflow control graph."""

from pydantic import Field, field_validator

from .._base import SDLModel
from .._identifiers import PortableIdentifier
from ._steps import WorkflowCompensationPolicy, WorkflowStep, WorkflowTimeoutPolicy


class Workflow(SDLModel):
    """A declarative experiment control graph over objectives."""

    description: str = ""
    start: str
    timeout: WorkflowTimeoutPolicy | None = None
    compensation: WorkflowCompensationPolicy | None = None
    steps: dict[PortableIdentifier, WorkflowStep] = Field(min_length=1)

    @field_validator("timeout", mode="before")
    @classmethod
    def parse_timeout(cls, v: object) -> object:
        if v is None or isinstance(v, WorkflowTimeoutPolicy):
            return v
        if isinstance(v, (int, float, str)):
            return {"seconds": v}
        return v

    @field_validator("compensation", mode="before")
    @classmethod
    def parse_compensation(cls, v: object) -> object:
        if v is None or isinstance(v, WorkflowCompensationPolicy):
            return v
        return v
