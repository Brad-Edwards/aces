"""Shared diagnostic contracts."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class DiagnosticModel(BaseModel):
    """Closed portable diagnostic shape for published contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(pattern=r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$", max_length=128)
    domain: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
    address: str = Field(pattern=r"^(?:/(?:[^~/]|~[01])*)*$", max_length=4096)
    message: str = Field(min_length=1, max_length=512)
    severity: Severity = Severity.ERROR


def diagnostic_payload(diagnostic: Diagnostic) -> dict[str, Any]:
    """Render a diagnostic as a JSON-ready mapping (severity as its string value)."""

    return {
        "code": diagnostic.code,
        "domain": diagnostic.domain,
        "address": diagnostic.address,
        "message": diagnostic.message,
        "severity": diagnostic.severity.value,
    }


def diagnostic_model(diagnostic: Diagnostic) -> DiagnosticModel:
    """Convert the internal immutable diagnostic to its closed contract model."""

    return DiagnosticModel(**diagnostic_payload(diagnostic))


__all__ = ("Diagnostic", "DiagnosticModel", "Severity", "diagnostic_model", "diagnostic_payload")
