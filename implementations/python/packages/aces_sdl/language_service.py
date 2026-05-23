"""Language-service helpers for SDL authoring tools.

The functions in this module are deliberately editor-agnostic.  They expose
completion, reference lookup, formatting, diagnostics, and structured edits as
plain JSON-like dictionaries so MCP tools, CLIs, and future LSP adapters can
share one implementation.
"""

from __future__ import annotations

from typing import Any

import yaml

from ._errors import SDLParseError, SDLValidationError
from ._language_edit import apply_edit
from ._language_metadata import REFERENCE_COMPLETION_TARGETS, SECTION_FIELD_COMPLETIONS
from ._language_references import find_references
from .parser import _load_normalized_data, parse_sdl
from .scenario import Scenario

_MAX_INPUT_BYTES = 64 * 1024
_CODE_PARSE = "sdl.parse"

_SCENARIO_METADATA_FIELDS = frozenset({"name", "version", "description", "module", "imports"})
_SECTION_FIELDS = tuple(field for field in Scenario.model_fields if field not in _SCENARIO_METADATA_FIELDS)
_TOP_LEVEL_KEYS = tuple(Scenario.model_fields)


def language_completions(
    sdl_content: str,
    *,
    cursor_path: str = "",
    prefix: str = "",
) -> dict[str, Any]:
    """Return completion items for a JSON-pointer-like SDL location."""
    size_error = _size_error(sdl_content)
    if size_error is not None:
        return size_error

    data, error = _load_completion_data(sdl_content)
    if error is not None:
        return error

    pointer = _split_pointer_or_empty(cursor_path)
    target_section = _completion_target_section(pointer)
    if target_section is not None:
        items = _reference_completion_items(data, target_section)
        context = f"reference:{target_section}"
    elif len(pointer) <= 1:
        existing = set(data) if isinstance(data, dict) else set()
        items = [
            {
                "label": key,
                "kind": "field",
                "detail": "top-level SDL key",
                "insert_text": f"{key}: ",
            }
            for key in _TOP_LEVEL_KEYS
            if key not in existing
        ]
        context = "top-level"
    else:
        section = pointer[0]
        fields = SECTION_FIELD_COMPLETIONS.get(section, ())
        items = [
            {
                "label": field,
                "kind": "field",
                "detail": f"{section} field",
                "insert_text": f"{field}: ",
            }
            for field in fields
        ]
        context = f"section:{section}"

    filtered = _filter_items(items, prefix)
    return {"status": "ok", "context": context, "items": filtered}


def language_references(sdl_content: str, symbol: str) -> dict[str, Any]:
    """Return definition and occurrence locations for an SDL symbol."""
    size_error = _size_error(sdl_content)
    if size_error is not None:
        return size_error

    return find_references(sdl_content, symbol, section_fields=_SECTION_FIELDS)


def language_format(sdl_content: str) -> dict[str, Any]:
    """Return normalized, consistently formatted SDL YAML."""
    size_error = _size_error(sdl_content)
    if size_error is not None:
        return size_error

    try:
        data = _load_normalized_data(sdl_content)
    except SDLParseError as exc:
        return _invalid("parse", _CODE_PARSE, exc.details)

    formatted = yaml.safe_dump(
        data,
        allow_unicode=False,
        default_flow_style=False,
        sort_keys=False,
    )
    diagnostics = language_diagnostics(formatted)["diagnostics"]
    status = "formatted" if not diagnostics else "formatted_with_diagnostics"
    return {"status": status, "content": formatted, "diagnostics": diagnostics}


def language_diagnostics(
    sdl_content: str,
    *,
    semantic_validation: bool = True,
) -> dict[str, Any]:
    """Parse SDL and return structured diagnostics instead of prose."""
    size_error = _size_error(sdl_content)
    if size_error is not None:
        return size_error

    try:
        parse_sdl(
            sdl_content,
            skip_semantic_validation=not semantic_validation,
        )
    except SDLParseError as exc:
        return _invalid("parse", _CODE_PARSE, exc.details)
    except SDLValidationError as exc:
        return {
            "status": "invalid",
            "stage": "semantic_validation",
            "diagnostics": [
                _diagnostic(
                    "semantic_validation",
                    "sdl.semantic",
                    message,
                )
                for message in exc.errors
            ],
        }

    return {"status": "valid", "stage": "semantic_validation" if semantic_validation else "parse", "diagnostics": []}


def apply_structured_edit(
    sdl_content: str,
    *,
    operation: str,
    pointer: str,
    value: Any = None,
) -> dict[str, Any]:
    """Apply a structured edit addressed by JSON pointer and revalidate."""
    size_error = _size_error(sdl_content)
    if size_error is not None:
        return size_error

    try:
        data = _load_normalized_data(sdl_content)
    except SDLParseError as exc:
        return _invalid("parse", _CODE_PARSE, exc.details)

    try:
        tokens = _split_pointer(pointer)
        edited = apply_edit(data, operation=operation, tokens=tokens, value=value)
    except ValueError as exc:
        return _invalid("edit", "sdl.edit", str(exc))

    content = yaml.safe_dump(
        edited,
        allow_unicode=False,
        default_flow_style=False,
        sort_keys=False,
    )
    diagnostics = language_diagnostics(content)["diagnostics"]
    status = "edited" if not diagnostics else "edited_with_diagnostics"
    return {"status": status, "content": content, "diagnostics": diagnostics}


def _load_completion_data(sdl_content: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not sdl_content.strip():
        return {}, None
    try:
        return _load_normalized_data(sdl_content), None
    except SDLParseError as exc:
        return {}, _invalid("parse", _CODE_PARSE, exc.details)


def _completion_target_section(pointer: list[str]) -> str | None:
    if len(pointer) < 3:
        return None
    section = pointer[0]
    field = pointer[-1]
    target = REFERENCE_COMPLETION_TARGETS.get((section, field))
    if target is not None:
        return target
    if len(pointer) >= 4 and pointer[-2] == "success":
        success_targets = {
            "conditions": "conditions",
            "metrics": "metrics",
            "evaluations": "evaluations",
            "tlos": "tlos",
            "goals": "goals",
        }
        return success_targets.get(field)
    return None


def _reference_completion_items(data: dict[str, Any], target_section: str) -> list[dict[str, str]]:
    if target_section == "any":
        sections = _SECTION_FIELDS
    elif target_section == "workflow_steps":
        return _workflow_step_completion_items(data)
    else:
        sections = (target_section,)

    items: list[dict[str, str]] = []
    for section in sections:
        section_data = data.get(section)
        if not isinstance(section_data, dict):
            continue
        for name in section_data:
            items.append(
                {
                    "label": str(name),
                    "kind": "reference",
                    "detail": f"{section}.{name}",
                    "insert_text": str(name),
                }
            )
    return sorted(items, key=lambda item: (item["detail"], item["label"]))


def _workflow_step_completion_items(data: dict[str, Any]) -> list[dict[str, str]]:
    workflows = data.get("workflows")
    if not isinstance(workflows, dict):
        return []
    items: list[dict[str, str]] = []
    for workflow_name, workflow in workflows.items():
        if not isinstance(workflow, dict):
            continue
        steps = workflow.get("steps")
        if not isinstance(steps, dict):
            continue
        for step_name in steps:
            label = str(step_name)
            items.append(
                {
                    "label": label,
                    "kind": "reference",
                    "detail": f"workflows.{workflow_name}.steps.{step_name}",
                    "insert_text": label,
                }
            )
    return sorted(items, key=lambda item: item["detail"])


def _filter_items(items: list[dict[str, str]], prefix: str) -> list[dict[str, str]]:
    if not prefix:
        return items
    return [item for item in items if item["label"].startswith(prefix)]


def _split_pointer_or_empty(pointer: str) -> list[str]:
    if not pointer:
        return []
    try:
        return _split_pointer(pointer)
    except ValueError:
        return []


def _split_pointer(pointer: str) -> list[str]:
    if pointer in {"", "/"}:
        return []
    if not pointer.startswith("/"):
        raise ValueError("pointer must be empty or start with '/'")
    return [_unescape_pointer_token(token) for token in pointer.split("/")[1:]]


def _unescape_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _size_error(*values: str) -> dict[str, Any] | None:
    size = sum(len(value.encode("utf-8", errors="replace")) for value in values)
    if size <= _MAX_INPUT_BYTES:
        return None
    return _invalid("input", "sdl.input_too_large", f"INPUT TOO LARGE - limit is {_MAX_INPUT_BYTES} bytes.")


def _invalid(
    stage: str,
    code: str,
    message: str,
    *,
    location: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {"status": "invalid", "stage": stage, "diagnostics": [_diagnostic(stage, code, message, location=location)]}


def _diagnostic(
    stage: str,
    code: str,
    message: str,
    *,
    location: dict[str, int] | None = None,
) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {
        "stage": stage,
        "severity": "error",
        "code": code,
        "message": message,
    }
    if location is not None:
        diagnostic["range"] = {"start": location, "end": location}
    return diagnostic
