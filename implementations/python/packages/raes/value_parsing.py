"""Public value parsing helpers shared with processor support analysis."""

from ._base import (
    VARIABLE_REFERENCE_SCHEMA_MARKER,
    VARIABLE_TOKEN_RE,
    WholeFieldVariableReference,
    extract_variable_name,
    is_variable_ref,
    normalize_enum_value,
    parse_enum_or_var,
    parse_int_or_var,
)


def variable_names_in_value(value: str) -> tuple[str, ...]:
    """Return variable names found in a scalar, preserving first occurrence."""

    return tuple(dict.fromkeys(VARIABLE_TOKEN_RE.findall(value)))


__all__ = [
    "VARIABLE_REFERENCE_SCHEMA_MARKER",
    "WholeFieldVariableReference",
    "extract_variable_name",
    "is_variable_ref",
    "normalize_enum_value",
    "parse_enum_or_var",
    "parse_int_or_var",
    "variable_names_in_value",
]
