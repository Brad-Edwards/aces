"""Shared diagnostic contracts."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Diagnostic severity level."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Diagnostic:
    """Structured planner/runtime message."""

    code: str
    domain: str
    address: str
    message: str
    severity: Severity = Severity.ERROR

    @property
    def is_error(self) -> bool:
        return self.severity == Severity.ERROR


def diagnostic_payload(diagnostic: Diagnostic) -> dict[str, Any]:
    """Render a diagnostic as a JSON-ready mapping (severity as its string value)."""

    return {
        "code": diagnostic.code,
        "domain": diagnostic.domain,
        "address": diagnostic.address,
        "message": diagnostic.message,
        "severity": diagnostic.severity.value,
    }


__all__ = ("Diagnostic", "Severity", "diagnostic_payload")
