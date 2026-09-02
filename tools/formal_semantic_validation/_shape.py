"""Shape, digest, and id primitives for formal validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypeGuard

from tools.formal_semantic_validation._types import _ID_RE
from tools.policy.common import PolicyFailure


def _failure(rule_id: str, message: str, path: str | None = None) -> PolicyFailure:
    return PolicyFailure(rule_id, message, path)


def _is_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _closed_object(
    value: object,
    expected_keys: set[str],
    *,
    rule_id: str,
    label: str,
    failures: list[PolicyFailure],
    path: str,
) -> bool:
    if not isinstance(value, Mapping):
        failures.append(_failure(rule_id, f"{label} must be an object", path))
        return False
    keys = set(value)
    if keys != expected_keys:
        failures.append(
            _failure(
                rule_id,
                f"{label} must use the closed key set; missing={sorted(expected_keys - keys)!r}, "
                f"unknown={sorted(keys - expected_keys)!r}",
                path,
            )
        )
        return False
    return True


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: object, *, nonempty: bool = True) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return False
    return (not nonempty or bool(value)) and all(_nonempty_string(item) for item in value)


def _stable_ids(items: object, key: str) -> tuple[set[str], bool]:
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
        return set(), False
    values: list[str] = []
    for item in items:
        valid = isinstance(item, Mapping) and _nonempty_string(item.get(key))
        value = str(item[key]) if valid else ""
        if not valid or not _ID_RE.fullmatch(value):
            return set(), False
        values.append(value)
    return set(values), len(values) == len(set(values))


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _diagnostic_payload(exc: Exception, repo_root: Path) -> object:
    errors = getattr(exc, "errors", None)
    payload: object = errors if errors is not None else str(exc)
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return rendered.replace(str(repo_root.resolve()), "<repo>")
