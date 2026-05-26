"""Shared diagnostic contracts."""

from dataclasses import dataclass
from enum import Enum


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


__all__ = ("Diagnostic", "Severity")
