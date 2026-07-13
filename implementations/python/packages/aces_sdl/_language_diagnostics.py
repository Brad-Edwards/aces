"""Diagnostic payload helpers for SDL language-service responses."""

from __future__ import annotations

from typing import Any

from ._errors import SDLParseError


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


def parse_error(error: SDLParseError) -> dict[str, Any]:
    """Preserve structured parser diagnostics in language-service responses."""
    if error.diagnostics:
        return {
            "status": "invalid",
            "stage": "parse",
            "diagnostics": [item.as_dict() for item in error.diagnostics],
        }
    return invalid("parse", "sdl.parse", error.details)
