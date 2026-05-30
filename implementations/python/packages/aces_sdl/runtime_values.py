"""Shared parsing helpers for SDL runtime configuration models."""

import ipaddress
import re
from enum import Enum
from typing import Any

from ._base import (
    is_variable_ref,
    parse_bool_or_var,
)

_BYTE_UNITS = {
    "b": 1,
    "kb": 1_000,
    "kib": 1_024,
    "mb": 1_000_000,
    "mib": 1_048_576,
    "gb": 1_000_000_000,
    "gib": 1_073_741_824,
    "tb": 1_000_000_000_000,
    "tib": 1_099_511_627_776,
}

_RAM_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(" + "|".join(_BYTE_UNITS) + r")\s*$",
    re.IGNORECASE,
)
_RAM_MIN_BYTES_ERROR = "RAM must be >= 1 byte"
_WINDOWS_NAMED_PIPE_PREFIXES = ("\\\\.\\pipe\\", "\\\\?\\pipe\\")

# Identifier-shape tokens used to detect secret-bearing setting names, not
# secrets themselves; the string-concatenation / ``noqa: S105`` markers silence
# bandit without dressing each line up as actual credential material. This is
# the de-duplicated union of every per-family token set that previously drifted
# across runtime_database, runtime_dns, runtime_directory_identity,
# runtime_mail_service, and runtime_security_monitoring. A setting whose name
# matches one of these may not carry a raw value regardless of how the submitter
# classified it.
SECRET_NAME_TOKENS: tuple[str, ...] = (
    "access_key",
    "access_token",  # noqa: S105
    "api_key",
    "auth_key",
    "authd.pass",
    "client_key",
    "client_secret",  # noqa: S105
    "clientsecret",
    "conninfo",
    "credential",
    "credentials",
    "enrollment_key",
    "hmac",
    "keyfile",
    "keytab",
    "krbprincipalkey",
    "passphrase",
    "passwd",
    "pass" + "word",
    "pg_hba",
    "private_key",
    "privatekey",
    "pwd",
    "refresh_token",  # noqa: S105
    "sasl_passwd",
    "sasl_password",  # noqa: S105
    "sec" + "ret",
    "shared_key",
    "supplementalcredentials",
    "token",
    "tsig",
)
# Whole-word parts (alnum-split) that independently mark a name as secret-bearing
# even when no token is a substring (sourced from runtime_dns).
SECRET_NAME_PARTS: frozenset[str] = frozenset({"key"})


def name_indicates_secret(name: str) -> bool:
    """Return whether a setting name suggests secret-bearing content.

    A name is secret-bearing when any :data:`SECRET_NAME_TOKENS` entry is a
    substring (after lowercasing and normalizing ``-`` to ``_``) or when its
    alphanumeric-split parts intersect :data:`SECRET_NAME_PARTS`.
    """
    lowered = name.lower().replace("-", "_")
    if any(token in lowered for token in SECRET_NAME_TOKENS):
        return True
    parts = frozenset(part for part in re.split(r"[^a-z0-9]+", lowered) if part)
    return bool(parts & SECRET_NAME_PARTS)


def require_symbol(value: str, *, field_name: str) -> str:
    """Validate a stable, symbol-defining identifier (no ``${var}`` placeholder).

    Symbol-defining ids are reference targets, so they must be concrete: empty
    values and ``${var}`` placeholders are rejected.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    if is_variable_ref(value):
        raise ValueError(f"{field_name} must be a stable identifier, not a variable placeholder")
    return value


def absolute_path_or_var(value: str, *, field_name: str) -> str:
    if is_variable_ref(value):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if not value.startswith("/"):
        raise ValueError(f"{field_name} must be an absolute path")
    return value


def ip_address_or_var(value: str, *, field_name: str) -> str:
    """Validate an IPv4/IPv6 address, allowing empty and ``${var}`` values."""
    if not value or is_variable_ref(value):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    try:
        ipaddress.ip_address(value)
    except ValueError as e:
        raise ValueError(f"{field_name} must be a valid IP address") from e
    return value


def is_windows_named_pipe(value: str) -> bool:
    return isinstance(value, str) and value.lower().startswith(_WINDOWS_NAMED_PIPE_PREFIXES)


def control_interface_path_or_var(value: str, *, field_name: str) -> str:
    if is_variable_ref(value):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if value.startswith("/") or is_windows_named_pipe(value):
        return value
    raise ValueError(f"{field_name} must be an absolute path or Windows named pipe")


def parse_runtime_enum_or_var(value: Any, enum_cls: type[Enum], *, field_name: str):
    if value is None or is_variable_ref(value):
        return value
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        normalized = value.lower().replace("-", "_")
        try:
            return enum_cls(normalized)
        except ValueError as e:
            allowed = ", ".join(member.value for member in enum_cls)
            raise ValueError(f"{field_name} must be one of: {allowed}") from e
    raise ValueError(f"{field_name} must be a string")


def parse_optional_bool_or_var(value: Any, *, field_name: str) -> bool | str | None:
    return parse_bool_or_var(value, field_name=field_name) if value is not None else value


def coerce_string_list(value: Any):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return value


def validate_absolute_paths(values: list[str], *, field_name: str) -> list[str]:
    return [absolute_path_or_var(value, field_name=field_name) for value in values]


def parse_ram(value: str | int) -> int | str:
    """Parse a human-readable RAM string to bytes.

    Accepts bare integers (treated as bytes) or strings like
    ``"4 GiB"``, ``"2048 MiB"``, ``"512mb"``.
    """
    if is_variable_ref(value):
        return value
    if isinstance(value, bool):
        raise ValueError("RAM must be a positive integer or human-readable size")
    if isinstance(value, int):
        if value < 1:
            raise ValueError(_RAM_MIN_BYTES_ERROR)
        return value
    value_str = str(value).strip()
    if value_str.isdigit():
        parsed = int(value_str)
        if parsed < 1:
            raise ValueError(_RAM_MIN_BYTES_ERROR)
        return parsed
    match = _RAM_PATTERN.match(value_str)
    if not match:
        raise ValueError(f"Invalid RAM value: {value_str!r}. Use a number with a unit (e.g., '4 GiB', '2048 MiB').")
    amount = float(match.group(1))
    unit = match.group(2).lower()
    parsed = int(amount * _BYTE_UNITS[unit])
    if parsed < 1:
        raise ValueError(_RAM_MIN_BYTES_ERROR)
    return parsed
