"""Bounded, ambiguity-rejecting JSON ingress shared by portable contracts."""

from __future__ import annotations

import json
from typing import TypeAlias

JSONValue: TypeAlias = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]


class StrictJsonIngressError(ValueError):
    """A JSON document failed a safe pre-contract ingress check."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _duplicate_rejecting_object(
    pairs: list[tuple[str, JSONValue]],
) -> dict[str, JSONValue]:
    result: dict[str, JSONValue] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonIngressError("duplicate-member", "duplicate JSON member")
        result[key] = value
    return result


def _reject_non_finite_number(_: str) -> float:
    raise StrictJsonIngressError("non-finite-number", "JSON contains a non-finite number")


def parse_bounded_json_object(
    source: str | bytes | bytearray,
    *,
    max_bytes: int,
) -> dict[str, JSONValue]:
    """Parse one bounded JSON object without duplicate members or non-finite numbers."""

    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    encoded = source.encode("utf-8") if isinstance(source, str) else bytes(source)
    if len(encoded) > max_bytes:
        raise StrictJsonIngressError("input-too-large", "JSON input exceeds the configured byte limit")
    if not encoded.strip():
        raise StrictJsonIngressError("empty-input", "JSON input is empty")
    try:
        payload = json.loads(
            encoded,
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_non_finite_number,
        )
    except StrictJsonIngressError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictJsonIngressError("invalid-json", "JSON input is invalid") from exc
    if not isinstance(payload, dict):
        raise StrictJsonIngressError("invalid-root", "JSON input must be an object")
    return payload


__all__ = [
    "JSONValue",
    "StrictJsonIngressError",
    "parse_bounded_json_object",
]
