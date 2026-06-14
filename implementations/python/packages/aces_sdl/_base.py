"""Base model configuration and shared helpers for the SDL package."""

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class SDLModel(BaseModel):
    """Base for all SDL Pydantic models."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


_VARIABLE_NAME_PATTERN = r"[A-Za-z_][A-Za-z0-9_-]*"
# Single source of truth for the ``${name}`` substitution token, shared by the
# instantiation engine, SEM-218 explicitness analysis, the InstantiatedScenario
# model validator, and the published instantiated-scenario JSON Schema
# constraint (issue #500). The capturing group yields the variable name for
# ``.findall`` / ``match.group(1)`` consumers. ``VARIABLE_TOKEN_RE`` matches a
# token embedded anywhere in a string; ``_VARIABLE_REF_RE`` matches a
# whole-string placeholder.
VARIABLE_TOKEN_PATTERN = r"\$\{(" + _VARIABLE_NAME_PATTERN + r")\}"
VARIABLE_TOKEN_RE = re.compile(VARIABLE_TOKEN_PATTERN)
_VARIABLE_REF_RE = re.compile(r"^" + VARIABLE_TOKEN_PATTERN + r"$")


def is_variable_ref(v: Any) -> bool:
    """Return whether ``v`` is a full ``${var_name}`` placeholder."""
    return isinstance(v, str) and _VARIABLE_REF_RE.fullmatch(v) is not None


def contains_variable_token(v: Any) -> bool:
    """Return whether ``v`` is a string containing any ``${name}`` token.

    Unlike :func:`is_variable_ref` (whole-string placeholder only), this also
    matches tokens embedded within a larger string, e.g. ``"host-${index}"``.
    """
    return isinstance(v, str) and VARIABLE_TOKEN_RE.search(v) is not None


def extract_variable_name(v: str) -> str | None:
    """Return the referenced variable name, if ``v`` is a placeholder."""
    match = _VARIABLE_REF_RE.fullmatch(v) if isinstance(v, str) else None
    return match.group(1) if match else None


def normalize_enum_value(v: str) -> str:
    """Normalize a string for case-insensitive enum matching.

    SDL enum authoring accepts hyphen aliases for underscore-valued members so
    YAML-facing values can use either common spelling without per-family drift.
    """
    if is_variable_ref(v):
        return v
    return v.lower().replace("-", "_") if isinstance(v, str) else v


def parse_enum_or_var(
    value: Any,
    enum_cls: type[Enum],
    *,
    field_name: str = "value",
) -> Any:
    """Parse an enum-backed field while allowing full ``${var}`` placeholders."""
    if value is None or is_variable_ref(value):
        return value
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        normalized = normalize_enum_value(value)
        try:
            return enum_cls(normalized)
        except ValueError as e:
            allowed = ", ".join(member.value for member in enum_cls)
            raise ValueError(f"{field_name} must be one of: {allowed}") from e
    raise ValueError(f"{field_name} must be a string")


def parse_int_or_var(
    value: Any,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
    field_name: str = "value",
) -> int | str:
    """Parse an integer field while allowing ``${var}`` placeholders."""
    if is_variable_ref(value) or value is None:
        return value
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
        parsed = int(value.strip())
    else:
        raise ValueError(f"{field_name} must be an integer")

    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{field_name} must be <= {maximum}")
    return parsed


def parse_float_or_var(
    value: Any,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    field_name: str = "value",
) -> float | str:
    """Parse a float field while allowing ``${var}`` placeholders."""
    if is_variable_ref(value) or value is None:
        return value
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number")
    if isinstance(value, (int, float)):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value.strip())
        except ValueError as e:
            raise ValueError(f"{field_name} must be a number") from e
    else:
        raise ValueError(f"{field_name} must be a number")

    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{field_name} must be <= {maximum}")
    return parsed


def parse_bool_or_var(value: Any, *, field_name: str = "value") -> bool | str:
    """Parse a boolean field while allowing ``${var}`` placeholders."""
    if is_variable_ref(value) or value is None:
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        truthy = {"true", "1", "yes", "on"}
        falsy = {"false", "0", "no", "off"}
        if lowered in truthy:
            return True
        if lowered in falsy:
            return False
    raise ValueError(f"{field_name} must be a boolean")
