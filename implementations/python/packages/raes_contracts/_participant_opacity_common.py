"""Shared constrained values for participant-opacity contracts."""

from typing import Annotated

from pydantic import Field

SafeRef = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9._:/-]*$", max_length=256),
]
SafeKey = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9._:/|-]*$", max_length=256),
]
Revision = Annotated[
    str,
    Field(pattern=r"^[a-z0-9][a-z0-9._/-]*$", max_length=128),
]

MAX_OPACITY_POINTS = 100_000
MAX_OPACITY_DIAGNOSTICS = 64
MAX_OPACITY_MODEL_STATES = 100_000
MAX_OPACITY_MODEL_TRANSITIONS = 200_000

NORMALIZED_INPUT_PROVENANCE_NONCLAIM = (
    "No source or materializer authenticity is established by this normalized-input evidence."
)
MODEL_CHECK_PROVENANCE_NONCLAIM = (
    "No source or materializer authenticity is established by this normalized-model evidence."
)

__all__ = (
    "MAX_OPACITY_DIAGNOSTICS",
    "MAX_OPACITY_MODEL_STATES",
    "MAX_OPACITY_MODEL_TRANSITIONS",
    "MAX_OPACITY_POINTS",
    "MODEL_CHECK_PROVENANCE_NONCLAIM",
    "NORMALIZED_INPUT_PROVENANCE_NONCLAIM",
    "Revision",
    "SafeKey",
    "SafeRef",
)
