"""Shared validation primitives for participant binding DTOs."""

from collections.abc import Iterable

ACTION_CONTRACT_PREFIX = "participant.action-contract."
OBSERVATION_BOUNDARY_PREFIX = "participant.observation-boundary."


def require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{field_name} must be a non-empty string")


def require_prefixed(value: str, prefix: str, field_name: str) -> None:
    require_non_empty(value, field_name)
    if not value.startswith(prefix):
        raise ValueError(f"{field_name} must be a compiled {prefix.removesuffix('.')} address")


def string_tuple(value: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise TypeError(f"{field_name} must be an iterable of strings")
    values = tuple(value)
    if any(not isinstance(item, str) or not item for item in values):
        raise TypeError(f"{field_name} entries must be non-empty strings")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} entries must be unique")
    return values
