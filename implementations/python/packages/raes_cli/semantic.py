"""Offline, read-only command surface for RAES semantic operations."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import click
import typer
from raes import (
    SDL_SOURCE_FORMAT,
    SDLError,
    SDLInstantiationError,
    SDLMigrationPolicy,
    SDLParseError,
    SDLParserLimits,
    SDLValidationError,
    build_declaration_index,
    canonical_sdl_bytes,
    canonical_sdl_digest,
    format_sdl_source,
    parse_sdl,
)
from raes_conformance.conformance import contract_payload_root
from raes_processor.compiler import compile_scenario_runtime_model

from ._semantic_portable import PORTABLE_MAX_BYTES, execute_portable
from ._semantic_result import (
    CommandDiagnostic,
    CommandStatus,
    OutputFormat,
    SemanticCommandResult,
)
from ._semantic_result import (
    command_diagnostic as _diagnostic,
)
from ._semantic_result import (
    command_result as _result,
)
from ._semantic_result import (
    render_result as _render,
)

app = typer.Typer(
    help="Parse, validate, normalize, resolve, compile, transform, inspect, and check RAES artifacts.",
    no_args_is_help=True,
)

_SDL_CONTRACT_ID = SDL_SOURCE_FORMAT
_SDL_MAX_BYTES = SDLParserLimits().max_input_bytes


class TransformProfile(str, Enum):
    """Closed transformations owned by the RAES semantic layer."""

    CANONICAL = "canonical"
    FORMAT = "format"


def _read_input(source: str, *, max_bytes: int) -> bytes:
    if source == "-":
        raw = click.get_binary_stream("stdin").read(max_bytes + 1)
    else:
        path = Path(source)
        with path.open("rb") as stream:
            raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise OSError("input exceeds the configured byte limit")
    return raw


def _sdl_diagnostics(exc: SDLError) -> tuple[CommandDiagnostic, ...]:
    if isinstance(exc, SDLParseError):
        if exc.diagnostics:
            return tuple(
                _diagnostic(
                    diagnostic.code,
                    "sdl-parse",
                    "SDL input was rejected at the parse stage.",
                    address=diagnostic.pointer,
                    severity=diagnostic.severity,
                )
                for diagnostic in exc.diagnostics[:20]
            )
        return (_diagnostic("sdl.parse", "sdl-parse", "SDL input was rejected at the parse stage."),)
    if isinstance(exc, SDLValidationError):
        return (
            _diagnostic(
                "sdl.validation",
                "sdl-validation",
                f"SDL semantic validation reported {len(exc.errors)} error(s).",
            ),
        )
    if isinstance(exc, SDLInstantiationError):
        return (
            _diagnostic(
                "sdl.instantiation",
                "sdl-instantiation",
                f"SDL instantiation reported {len(exc.errors)} error(s).",
            ),
        )
    return (_diagnostic("sdl.invalid", "sdl", "SDL input was rejected."),)


def _parse_sdl_input(
    raw: bytes,
    *,
    semantic_validation: bool,
    migration_policy: SDLMigrationPolicy,
) -> tuple[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SDLParseError("SDL source must be valid UTF-8.") from exc
    scenario = parse_sdl(
        text,
        skip_semantic_validation=not semantic_validation,
        source_format=SDL_SOURCE_FORMAT,
        migration_policy=migration_policy,
    )
    return text, scenario


def _scenario_summary(scenario: Any, *, phase: str) -> dict[str, Any]:
    fields = scenario.model_dump(mode="json", by_alias=True, exclude_unset=True)
    return {
        "phase": phase,
        "root_type": "object",
        "scenario_name": scenario.name,
        "field_count": len(fields),
        "semantic_validated": bool(scenario.semantic_validated),
    }


def _inspection_payload(scenario: Any) -> dict[str, Any]:
    index = build_declaration_index(scenario)
    declarations = [
        {
            "address": declaration.address,
            "kind": declaration.kind,
            "model_path": declaration.model_path,
            "referenceable": declaration.referenceable,
            "targetable": declaration.targetable,
        }
        for declaration in index.declarations
    ]
    return {
        "phase": "inspection",
        "root_type": "object",
        "scenario_name": scenario.name,
        "declaration_count": len(declarations),
        "declarations": declarations,
    }


def _resolution_payload(scenario: Any) -> dict[str, Any]:
    index = build_declaration_index(scenario)
    aliases = index.reference_aliases()
    return {
        "phase": "resolved-references",
        "root_type": "object",
        "scenario_name": scenario.name,
        "reference_binding_count": len(aliases),
        "reference_bindings": {alias: sorted(addresses) for alias, addresses in sorted(aliases.items())},
    }


def _runtime_summary(runtime_model: Any) -> dict[str, Any]:
    collection_names = (
        "networks",
        "node_deployments",
        "feature_bindings",
        "propositions",
        "assertions",
        "injects",
        "events",
        "scripts",
        "stories",
        "workflows",
        "objectives",
    )
    return {
        "phase": "compiled-runtime-summary",
        "root_type": "object",
        "scenario_name": runtime_model.scenario_name,
        "resource_counts": {name: len(getattr(runtime_model, name)) for name in collection_names},
        "diagnostic_count": len(runtime_model.diagnostics),
    }


def _execute_sdl(
    operation: str,
    raw: bytes,
    *,
    migration_policy: SDLMigrationPolicy,
    transform: TransformProfile | None,
) -> SemanticCommandResult:
    if operation == "conformance":
        return _result(
            operation,
            status=CommandStatus.UNSUPPORTED,
            contract_id=_SDL_CONTRACT_ID,
            migration_policy=migration_policy,
        )
    semantic_validation = operation != "parse"
    try:
        text, scenario = _parse_sdl_input(
            raw,
            semantic_validation=semantic_validation,
            migration_policy=migration_policy,
        )
        advisories = tuple(
            _diagnostic(
                diagnostic.code,
                "sdl-parse",
                diagnostic.message,
                address=diagnostic.pointer,
                severity=diagnostic.severity,
            )
            for diagnostic in scenario.source_diagnostics
        )
        if operation in {"parse", "validate"}:
            strength = "structural" if operation == "parse" else "semantic"
            return _result(
                operation,
                contract_id=_SDL_CONTRACT_ID,
                payload=_scenario_summary(
                    scenario,
                    phase=("parsed-authoring" if operation == "parse" else "validated-authoring"),
                ),
                diagnostics=advisories,
                migration_policy=migration_policy,
                validation_strength=strength,
            )
        if operation == "normalize":
            formatted = format_sdl_source(text)
            digest = canonical_sdl_digest(scenario)
            return _result(
                operation,
                contract_id=_SDL_CONTRACT_ID,
                payload={
                    **_scenario_summary(scenario, phase="normalized-authoring"),
                    "content": formatted.content,
                    "digest": digest.as_dict(),
                },
                diagnostics=advisories,
                migration_policy=migration_policy,
                validation_strength="semantic",
            )
        if operation == "resolve":
            return _result(
                operation,
                contract_id=_SDL_CONTRACT_ID,
                payload=_resolution_payload(scenario),
                diagnostics=advisories,
                migration_policy=migration_policy,
                validation_strength="semantic",
            )
        if operation == "compile":
            runtime_model = compile_scenario_runtime_model(scenario)
            compiler_diagnostics = tuple(
                _diagnostic(
                    item.code,
                    item.domain,
                    "The compiler reported a diagnostic.",
                    address=item.address,
                    severity=item.severity.value,
                )
                for item in runtime_model.diagnostics
            )
            return _result(
                operation,
                contract_id=_SDL_CONTRACT_ID,
                payload=_runtime_summary(runtime_model),
                diagnostics=(*advisories, *compiler_diagnostics),
                migration_policy=migration_policy,
                validation_strength="semantic",
                processor_profile="raes-compiler/default",
            )
        if operation == "transform":
            selected = transform or TransformProfile.CANONICAL
            if selected is TransformProfile.FORMAT:
                content = format_sdl_source(text).content
                digest_payload: dict[str, str] | None = None
            else:
                content = canonical_sdl_bytes(scenario).decode("utf-8")
                digest_payload = canonical_sdl_digest(scenario).as_dict()
            payload: dict[str, Any] = {
                "phase": "transformed",
                "root_type": "object",
                "content": content,
            }
            if digest_payload is not None:
                payload["digest"] = digest_payload
            return _result(
                operation,
                contract_id=_SDL_CONTRACT_ID,
                payload=payload,
                diagnostics=advisories,
                migration_policy=migration_policy,
                validation_strength="semantic",
                transform_profile=selected.value,
            )
        if operation == "inspect":
            return _result(
                operation,
                contract_id=_SDL_CONTRACT_ID,
                payload=_inspection_payload(scenario),
                diagnostics=advisories,
                migration_policy=migration_policy,
                validation_strength="semantic",
            )
    except SDLError as exc:
        return _result(
            operation,
            status=CommandStatus.INVALID,
            contract_id=_SDL_CONTRACT_ID,
            diagnostics=_sdl_diagnostics(exc),
            migration_policy=migration_policy,
        )
    return _result(
        operation,
        status=CommandStatus.INTERNAL,
        contract_id=_SDL_CONTRACT_ID,
        diagnostics=(_diagnostic("cli.internal", "cli", "The semantic operation did not produce a result."),),
        migration_policy=migration_policy,
    )


def _execute(
    operation: str,
    source: str,
    *,
    contract_id: str,
    migration_policy: SDLMigrationPolicy,
    transform: TransformProfile | None = None,
) -> SemanticCommandResult:
    if contract_id != _SDL_CONTRACT_ID and contract_payload_root(contract_id) is None:
        return _result(
            operation,
            status=CommandStatus.USAGE,
            contract_id=None,
            diagnostics=(_diagnostic("cli.selector", "cli", "The contract selector is not supported."),),
        )
    max_bytes = _SDL_MAX_BYTES if contract_id == _SDL_CONTRACT_ID else PORTABLE_MAX_BYTES
    try:
        raw = _read_input(source, max_bytes=max_bytes)
    except OSError:
        return _result(
            operation,
            status=CommandStatus.OPERATIONAL,
            contract_id=contract_id,
            diagnostics=(_diagnostic("cli.input", "cli", "The input could not be read within the configured bounds."),),
            migration_policy=migration_policy,
        )
    try:
        if contract_id == _SDL_CONTRACT_ID:
            return _execute_sdl(
                operation,
                raw,
                migration_policy=migration_policy,
                transform=transform,
            )
        return execute_portable(operation, contract_id, raw)
    except Exception:
        return _result(
            operation,
            status=CommandStatus.INTERNAL,
            contract_id=contract_id,
            diagnostics=(_diagnostic("cli.internal", "cli", "The operation failed unexpectedly."),),
            migration_policy=migration_policy,
        )


def _run(
    operation: str,
    source: str,
    contract: str,
    output: OutputFormat,
    migration_policy: SDLMigrationPolicy,
    *,
    transform: TransformProfile | None = None,
) -> None:
    _render(
        _execute(
            operation,
            source,
            contract_id=contract,
            migration_policy=migration_policy,
            transform=transform,
        ),
        output,
    )


@app.command("parse")
def parse_command(
    source: str = typer.Argument(..., help="Input path or '-' for stdin."),
    contract: str = typer.Option(_SDL_CONTRACT_ID, "--contract", help="Explicit versioned contract id."),
    output: OutputFormat = typer.Option(OutputFormat.HUMAN, "--output"),
    migration_policy: SDLMigrationPolicy = typer.Option(SDLMigrationPolicy.REJECT, "--migration-policy"),
) -> None:
    """Perform bounded decoding and typed construction without a validity claim."""

    _run("parse", source, contract, output, migration_policy)


@app.command("validate")
def validate_command(
    source: str = typer.Argument(..., help="Input path or '-' for stdin."),
    contract: str = typer.Option(_SDL_CONTRACT_ID, "--contract", help="Explicit versioned contract id."),
    output: OutputFormat = typer.Option(OutputFormat.HUMAN, "--output"),
    migration_policy: SDLMigrationPolicy = typer.Option(SDLMigrationPolicy.REJECT, "--migration-policy"),
) -> None:
    """Run the owning structural and semantic admission checks."""

    _run("validate", source, contract, output, migration_policy)


@app.command("normalize")
def normalize_command(
    source: str = typer.Argument(..., help="Input path or '-' for stdin."),
    contract: str = typer.Option(_SDL_CONTRACT_ID, "--contract", help="Explicit versioned contract id."),
    output: OutputFormat = typer.Option(OutputFormat.HUMAN, "--output"),
    migration_policy: SDLMigrationPolicy = typer.Option(SDLMigrationPolicy.REJECT, "--migration-policy"),
) -> None:
    """Emit a deterministic normalized representation and provenance."""

    _run("normalize", source, contract, output, migration_policy)


@app.command("resolve")
def resolve_command(
    source: str = typer.Argument(..., help="Input path or '-' for stdin."),
    contract: str = typer.Option(_SDL_CONTRACT_ID, "--contract", help="Explicit versioned contract id."),
    output: OutputFormat = typer.Option(OutputFormat.HUMAN, "--output"),
    migration_policy: SDLMigrationPolicy = typer.Option(SDLMigrationPolicy.REJECT, "--migration-policy"),
) -> None:
    """Resolve and inspect local SDL declarations without acquisition or writes."""

    _run("resolve", source, contract, output, migration_policy)


@app.command("compile")
def compile_command(
    source: str = typer.Argument(..., help="Input path or '-' for stdin."),
    contract: str = typer.Option(_SDL_CONTRACT_ID, "--contract", help="Explicit versioned contract id."),
    output: OutputFormat = typer.Option(OutputFormat.HUMAN, "--output"),
    migration_policy: SDLMigrationPolicy = typer.Option(SDLMigrationPolicy.REJECT, "--migration-policy"),
) -> None:
    """Compile SDL and emit a bounded typed runtime-model summary."""

    _run("compile", source, contract, output, migration_policy)


@app.command("transform")
def transform_command(
    source: str = typer.Argument(..., help="Input path or '-' for stdin."),
    contract: str = typer.Option(_SDL_CONTRACT_ID, "--contract", help="Explicit versioned contract id."),
    transform: TransformProfile = typer.Option(..., "--transform", help="Closed transform profile."),
    output: OutputFormat = typer.Option(OutputFormat.HUMAN, "--output"),
    migration_policy: SDLMigrationPolicy = typer.Option(SDLMigrationPolicy.REJECT, "--migration-policy"),
) -> None:
    """Apply one explicitly selected RAES-owned transformation."""

    _run("transform", source, contract, output, migration_policy, transform=transform)


@app.command("inspect")
def inspect_command(
    source: str = typer.Argument(..., help="Input path or '-' for stdin."),
    contract: str = typer.Option(_SDL_CONTRACT_ID, "--contract", help="Explicit versioned contract id."),
    output: OutputFormat = typer.Option(OutputFormat.HUMAN, "--output"),
    migration_policy: SDLMigrationPolicy = typer.Option(SDLMigrationPolicy.REJECT, "--migration-policy"),
) -> None:
    """Inspect admitted typed artifacts without exposing raw values."""

    _run("inspect", source, contract, output, migration_policy)


@app.command("conformance")
def conformance_command(
    source: str = typer.Argument(..., help="Input path or '-' for stdin."),
    contract: str = typer.Option(_SDL_CONTRACT_ID, "--contract", help="Explicit versioned contract id."),
    output: OutputFormat = typer.Option(OutputFormat.HUMAN, "--output"),
    migration_policy: SDLMigrationPolicy = typer.Option(SDLMigrationPolicy.REJECT, "--migration-policy"),
) -> None:
    """Run RAES-owned local conformance checks without invoking a target."""

    _run("conformance", source, contract, output, migration_policy)
