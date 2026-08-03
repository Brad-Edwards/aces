"""Shared safe logical identity for operator-managed secret references."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

SECRET_REFERENCE_ID_PATTERN = r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"  # noqa: S105 -- identifier grammar, not material

SecretReferenceId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=256,
        pattern=SECRET_REFERENCE_ID_PATTERN,
    ),
]

__all__ = ["SECRET_REFERENCE_ID_PATTERN", "SecretReferenceId"]
