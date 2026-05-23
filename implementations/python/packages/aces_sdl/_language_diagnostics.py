"""Diagnostic payload helpers for SDL language-service responses."""

from __future__ import annotations

from typing import Any


def invalid(
    stage: str,
    code: str,
    message: str,
    *,
    location: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Return the common invalid response shape."""
    return {"status": "invalid", "stage": stage, "diagnostics": [diagnostic(stage, code, message, location=location)]}


def diagnostic(
    stage: str,
    code: str,
    message: str,
    *,
    location: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Return one structured diagnostic."""
    payload: dict[str, Any] = {
        "stage": stage,
        "severity": "error",
        "code": code,
        "message": message,
    }
    if location is not None:
        payload["range"] = {"start": location, "end": location}
    return payload
