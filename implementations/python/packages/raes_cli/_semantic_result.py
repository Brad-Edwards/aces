"""Typed result and presentation boundary for semantic CLI commands."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

import typer
from pydantic import BaseModel, ConfigDict, Field
from raes import (
    SDL_CANONICAL_PROFILE,
    SDL_SOURCE_FORMAT,
    SDLMigrationPolicy,
)


class OutputFormat(str, Enum):
    """Supported presentation modes."""

    HUMAN = "human"
    JSON = "json"


class CommandStatus(str, Enum):
    """Stable status classes mapped onto the documented exit taxonomy."""

    SUCCESS = "success"
    INVALID = "invalid"
    USAGE = "usage"
    UNSUPPORTED = "unsupported"
    OPERATIONAL = "operational"
    INTERNAL = "internal"


_EXIT_CODES = {
    CommandStatus.SUCCESS: 0,
    CommandStatus.INVALID: 1,
    CommandStatus.USAGE: 2,
    CommandStatus.UNSUPPORTED: 3,
    CommandStatus.OPERATIONAL: 4,
    CommandStatus.INTERNAL: 70,
}


class CommandDiagnostic(BaseModel):
    """Value-free diagnostic projected from an owning semantic boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    domain: str
    address: str = ""
    message: str
    severity: str = "error"


class SemanticCommandResult(BaseModel):
    """Single typed result consumed by both human and JSON renderers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: str
    status: CommandStatus
    contract_id: str | None
    source_format: str | None = None
    migration_policy: str | None = None
    normalization_profile: str | None = None
    validation_strength: str | None = None
    processor_profile: str | None = None
    transform_profile: str | None = None
    provenance: dict[str, str] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    diagnostics: tuple[CommandDiagnostic, ...] = ()


def command_result(
    operation: str,
    *,
    status: CommandStatus = CommandStatus.SUCCESS,
    contract_id: str | None,
    payload: dict[str, Any] | None = None,
    diagnostics: tuple[CommandDiagnostic, ...] = (),
    migration_policy: SDLMigrationPolicy = SDLMigrationPolicy.REJECT,
    validation_strength: str | None = None,
    processor_profile: str | None = None,
    transform_profile: str | None = None,
) -> SemanticCommandResult:
    """Build the one result shape shared by all semantic presentations."""

    is_sdl = contract_id == SDL_SOURCE_FORMAT
    return SemanticCommandResult(
        operation=operation,
        status=status,
        contract_id=contract_id,
        source_format=SDL_SOURCE_FORMAT if is_sdl else None,
        migration_policy=migration_policy.value if is_sdl else None,
        normalization_profile=SDL_CANONICAL_PROFILE if is_sdl else None,
        validation_strength=validation_strength,
        processor_profile=processor_profile,
        transform_profile=transform_profile,
        provenance={
            "network": "disabled",
            "filesystem": "read-only",
        },
        payload=payload or {},
        diagnostics=diagnostics,
    )


def command_diagnostic(
    code: str,
    domain: str,
    message: str,
    *,
    address: str = "",
    severity: str = "error",
) -> CommandDiagnostic:
    """Build a sanitized diagnostic suitable for either renderer."""

    return CommandDiagnostic(
        code=code,
        domain=domain,
        address=address,
        message=message,
        severity=severity,
    )


def render_result(result: SemanticCommandResult, output: OutputFormat) -> None:
    """Render a result and apply the stable process-exit mapping."""

    if output is OutputFormat.JSON:
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        content = result.payload.get("content")
        if isinstance(content, str):
            typer.echo(content, nl=not content.endswith("\n"))
        else:
            typer.echo(f"{result.operation}: {result.status.value}")
        for diagnostic in result.diagnostics:
            typer.echo(
                f"{diagnostic.severity} [{diagnostic.code}] {diagnostic.message}",
                err=True,
            )
    code = _EXIT_CODES[result.status]
    if code:
        raise typer.Exit(code=code)
