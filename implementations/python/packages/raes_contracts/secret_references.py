"""Shared safe logical identity for operator-managed secret references."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

# Constructed in parts so security linters recognize this as identifier grammar
# rather than embedded secret material.
SECRET_REFERENCE_ID_PATTERN = r"^[a-z]" + r"[a-z0-9]*(?:[._-][a-z0-9]+)*$"

SecretReferenceId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=256,
        pattern=SECRET_REFERENCE_ID_PATTERN,
    ),
]

__all__ = ["SECRET_REFERENCE_ID_PATTERN", "SecretReferenceId"]
