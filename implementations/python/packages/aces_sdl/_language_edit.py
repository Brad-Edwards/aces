"""Structured edit primitives for SDL language-service helpers."""

from __future__ import annotations

from collections.abc import MutableMapping, MutableSequence
from typing import Any


def apply_edit(
    data: Any,
    *,
    operation: str,
    tokens: list[str],
    value: Any,
) -> Any:
    """Apply a JSON-pointer addressed edit to loaded YAML data."""
    if not tokens:
        if operation != "set":
            raise ValueError("root pointer supports only the set operation")
        return value

    operation = operation.strip().lower()
    if operation not in {"set", "delete", "append"}:
        raise ValueError("operation must be one of: set, delete, append")

    parent = _resolve_parent(data, tokens, create_missing=operation == "set")
    final = tokens[-1]
    if operation == "set":
        _assign_child(parent, final, value)
    elif operation == "delete":
        _delete_child(parent, final)
    elif operation == "append":
        target = _resolve_child(parent, final)
        if not isinstance(target, list):
            raise ValueError(f"append target '{_encode_pointer(tokens)}' is not a list")
        target.append(value)
    return data


def _resolve_parent(data: Any, tokens: list[str], *, create_missing: bool) -> Any:
    current = data
    for index, token in enumerate(tokens[:-1]):
        next_token = tokens[index + 1]
        current = _resolve_path_segment(
            current,
            token,
            next_token=next_token,
            create_missing=create_missing,
        )
    return current


def _resolve_path_segment(
    current: Any,
    token: str,
    *,
    next_token: str,
    create_missing: bool,
) -> Any:
    if isinstance(current, MutableMapping):
        return _resolve_mapping_segment(
            current,
            token,
            next_token=next_token,
            create_missing=create_missing,
        )
    if isinstance(current, MutableSequence):
        return current[_list_index(current, token)]
    raise ValueError(f"path segment '{token}' does not address a mapping or list")


def _resolve_mapping_segment(
    current: MutableMapping[str, Any],
    token: str,
    *,
    next_token: str,
    create_missing: bool,
) -> Any:
    if token not in current:
        if not create_missing:
            raise ValueError(f"missing path segment '{token}'")
        current[token] = [] if next_token.isdigit() else {}
    return current[token]


def _resolve_child(parent: Any, token: str) -> Any:
    if isinstance(parent, MutableMapping):
        if token not in parent:
            raise ValueError(f"missing path segment '{token}'")
        return parent[token]
    if isinstance(parent, MutableSequence):
        return parent[_list_index(parent, token)]
    raise ValueError(f"path segment '{token}' does not address a mapping or list")


def _assign_child(parent: Any, segment: str, value: Any) -> None:
    if isinstance(parent, MutableMapping):
        parent[segment] = value
        return
    if isinstance(parent, MutableSequence):
        if segment == "-":
            parent.append(value)
            return
        parent[_list_index(parent, segment)] = value
        return
    raise ValueError(f"path segment '{segment}' does not address a mapping or list")


def _delete_child(parent: Any, segment: str) -> None:
    if isinstance(parent, MutableMapping):
        if segment not in parent:
            raise ValueError(f"missing path segment '{segment}'")
        del parent[segment]
        return
    if isinstance(parent, MutableSequence):
        del parent[_list_index(parent, segment)]
        return
    raise ValueError(f"path segment '{segment}' does not address a mapping or list")


def _list_index(values: MutableSequence[Any], token: str) -> int:
    if not token.isdigit():
        raise ValueError(f"list path segment '{token}' is not an integer")
    index = int(token)
    if index >= len(values):
        raise ValueError(f"list index {index} is out of range")
    return index


def _encode_pointer(tokens: list[str]) -> str:
    if not tokens:
        return ""
    return "/" + "/".join(token.replace("~", "~0").replace("/", "~1") for token in tokens)
