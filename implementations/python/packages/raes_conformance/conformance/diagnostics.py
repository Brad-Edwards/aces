"""Shared diagnostic helpers and conformance diagnostic-code constants."""

from __future__ import annotations

import json
from pathlib import Path

from raes_contracts.diagnostics import Diagnostic, Severity

_SEMANTIC_INVALID_DIAGNOSTIC_CODE = "conformance.semantic-invalid"
_OBSERVABILITY_EVIDENCE_INVALID_DIAGNOSTIC_CODE = "conformance.observability-evidence-invalid"


def _diagnostic(code: str, address: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        domain="conformance",
        address=address,
        message=message,
        severity=Severity.ERROR,
    )


def _diagnostic_payload(diag: Diagnostic) -> dict[str, object]:
    return {
        "code": diag.code,
        "domain": diag.domain,
        "address": diag.address,
        "severity": diag.severity.value if hasattr(diag.severity, "value") else str(diag.severity),
        "message": diag.message,
    }


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))
