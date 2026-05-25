"""Shared runtime diagnostic helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from aces_contracts.diagnostics import Diagnostic


def _has_error_diagnostic(diagnostics: list[Diagnostic]) -> bool:
    return any(diagnostic.is_error for diagnostic in diagnostics)


def _failure_diagnostic(code: str, address: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        domain="runtime",
        address=address,
        message=message,
    )


def _parse_timestamp(raw: str) -> datetime:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
