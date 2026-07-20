"""Dependency-neutral base primitives for closed ACES contracts."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Base model for closed-world external contracts."""

    model_config = ConfigDict(extra="forbid")


NonEmptyString = Annotated[str, Field(min_length=1)]

__all__ = ["ContractModel", "NonEmptyString"]
