"""Reference navigation helpers for SDL language-service surfaces."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from ._declarations import DeclarationIndex
from ._errors import SDLParseError
from ._identifiers import QualifiedName
from ._language_diagnostics import parse_error as _parse_error
from ._language_metadata import REFERENCE_COMPLETION_TARGETS
from ._reference_targetability import is_targetable_section
from ._yaml_loader import compose_sdl_yaml

_SUCCESS_REFERENCE_TARGETS = frozenset({"assertions"})


def find_references(
    sdl_content: str,
    symbol: str,
    *,
    section_fields: Collection[str],
    declaration_index: DeclarationIndex | None = None,
) -> dict[str, Any]:
    """Return definition and occurrence locations for an SDL symbol."""
    if not sdl_content.strip():
        result = {"status": "ok", "symbol": symbol, "definitions": [], "occurrences": []}
    else:
        root, error = _compose_yaml(sdl_content)
        result = (
            error
            if error is not None
            else _reference_result(root, symbol, section_fields, declaration_index=declaration_index)
        )
    return result


def _reference_result(
    root: Node | None,
    symbol: str,
    section_fields: Collection[str],
    *,
    declaration_index: DeclarationIndex | None,
) -> dict[str, Any]:
    if root is None:
        return {"status": "ok", "symbol": symbol, "definitions": [], "occurrences": []}
    definitions = _collect_definitions(root, section_fields)
    if declaration_index is not None:
        definitions = [
            definition
            for definition in definitions
            if declaration_index.declaration_for(definition["qualified_name"]) is not None
        ]
    occurrences: list[dict[str, Any]] = []
    spellings = (
        declaration_index.spellings_for(symbol)
        if declaration_index is not None
        else frozenset({symbol, _bare_symbol(symbol)})
    )
    if declaration_index is not None and _is_variation_member_symbol(symbol):
        spellings = frozenset({*spellings, _bare_symbol(symbol)})
    _collect_occurrences(
        root,
        spellings,
        [],
        occurrences,
        qualified_section=_qualified_symbol_section(symbol),
    )
    return {
        "status": "ok",
        "symbol": symbol,
        "definitions": [item for item in definitions if _definition_matches_symbol(item, symbol)],
        "occurrences": occurrences,
    }


def _compose_yaml(sdl_content: str) -> tuple[Node | None, dict[str, Any] | None]:
    try:
        return compose_sdl_yaml(sdl_content), None
    except SDLParseError as exc:
        return None, _parse_error(exc)


def _collect_definitions(root: Node, section_fields: Collection[str]) -> list[dict[str, Any]]:
    if not isinstance(root, MappingNode):
        return []
    definitions: list[dict[str, Any]] = []
    for key_node, value_node in root.value:
        section = _scalar_value(key_node)
        if section not in section_fields or not isinstance(value_node, MappingNode):
            continue
        _collect_section_definitions(section, value_node, [section], definitions)
    return definitions


def _collect_section_definitions(
    section: str,
    node: MappingNode,
    path: list[str],
    definitions: list[dict[str, Any]],
    *,
    prefix: str = "",
) -> None:
    for key_node, value_node in node.value:
        name = _scalar_value(key_node)
        if name is None:
            continue
        qualified_name = f"{section}.{prefix}{name}"
        definition_path = [*path, name]
        definitions.append(
            {
                "name": name,
                "qualified_name": qualified_name,
                "section": section,
                "path": _encode_pointer(definition_path),
                "range": _range_from_node(key_node),
            }
        )
        if section == "entities" and isinstance(value_node, MappingNode):
            nested = _mapping_child(value_node, "entities")
            if isinstance(nested, MappingNode):
                _collect_section_definitions(
                    section,
                    nested,
                    [*definition_path, "entities"],
                    definitions,
                    prefix=f"{prefix}{name}.",
                )
        if section == "variation_points" and isinstance(value_node, MappingNode):
            for container in ("alternatives", "members"):
                nested = _mapping_child(value_node, container)
                if isinstance(nested, MappingNode):
                    _collect_section_definitions(
                        section,
                        nested,
                        [*definition_path, container],
                        definitions,
                        prefix=f"{prefix}{name}.{container}.",
                    )


def _collect_occurrences(
    node: Node,
    spellings: Collection[str],
    path: list[str],
    occurrences: list[dict[str, Any]],
    *,
    qualified_section: str | None,
) -> None:
    if isinstance(node, MappingNode):
        _collect_mapping_occurrences(
            node,
            spellings,
            path,
            occurrences,
            qualified_section=qualified_section,
        )
        return

    if isinstance(node, SequenceNode):
        _collect_sequence_occurrences(
            node,
            spellings,
            path,
            occurrences,
            qualified_section=qualified_section,
        )
        return

    if isinstance(node, ScalarNode):
        _append_scalar_occurrence(
            node,
            spellings,
            path,
            occurrences,
            qualified_section=qualified_section,
        )


def _collect_mapping_occurrences(
    node: MappingNode,
    spellings: Collection[str],
    path: list[str],
    occurrences: list[dict[str, Any]],
    *,
    qualified_section: str | None,
) -> None:
    for key_node, value_node in node.value:
        key = _scalar_value(key_node)
        key_path = [*path, str(key)] if key is not None else [*path, "?"]
        if _is_matching_occurrence(
            key,
            spellings,
            key_path,
            qualified_section=qualified_section,
            mapping_key=True,
        ):
            _append_occurrence(
                occurrences,
                value=key,
                path=key_path,
                kind="mapping_key",
                node=key_node,
            )
        _collect_occurrences(
            value_node,
            spellings,
            key_path,
            occurrences,
            qualified_section=qualified_section,
        )


def _collect_sequence_occurrences(
    node: SequenceNode,
    spellings: Collection[str],
    path: list[str],
    occurrences: list[dict[str, Any]],
    *,
    qualified_section: str | None,
) -> None:
    for index, item in enumerate(node.value):
        _collect_occurrences(
            item,
            spellings,
            [*path, str(index)],
            occurrences,
            qualified_section=qualified_section,
        )


def _append_scalar_occurrence(
    node: ScalarNode,
    spellings: Collection[str],
    path: list[str],
    occurrences: list[dict[str, Any]],
    *,
    qualified_section: str | None,
) -> None:
    value = _scalar_value(node)
    if _is_matching_occurrence(
        value,
        spellings,
        path,
        qualified_section=qualified_section,
        mapping_key=False,
    ):
        _append_occurrence(
            occurrences,
            value=value,
            path=path,
            kind="scalar",
            node=node,
        )


def _is_matching_occurrence(
    value: str | None,
    spellings: Collection[str],
    path: list[str],
    *,
    qualified_section: str | None,
    mapping_key: bool,
) -> bool:
    return (
        value is not None
        and value in spellings
        and _include_occurrence(
            path,
            qualified_section=qualified_section,
            mapping_key=mapping_key,
        )
    )


def _append_occurrence(
    occurrences: list[dict[str, Any]],
    *,
    value: str | None,
    path: list[str],
    kind: str,
    node: Node,
) -> None:
    occurrences.append(
        {
            "value": value,
            "path": _encode_pointer(path),
            "kind": kind,
            "range": _range_from_node(node),
        }
    )


def _mapping_child(node: MappingNode, key: str) -> Node | None:
    for key_node, value_node in node.value:
        if _scalar_value(key_node) == key:
            return value_node
    return None


def _scalar_value(node: Node) -> str | None:
    if isinstance(node, ScalarNode):
        return str(node.value)
    return None


def _definition_matches_symbol(definition: dict[str, Any], symbol: str) -> bool:
    qualified_section = _qualified_symbol_section(symbol)
    if qualified_section is not None:
        return definition["qualified_name"] == symbol
    return definition["name"] == symbol


def _qualified_symbol_section(symbol: str) -> str | None:
    try:
        parts = QualifiedName.parse(symbol).parts
    except (TypeError, ValueError):
        return None
    return parts[0] if len(parts) > 1 else None


def _is_variation_member_symbol(symbol: str) -> bool:
    try:
        parts = QualifiedName.parse(symbol).parts
    except (TypeError, ValueError):
        return False
    return len(parts) >= 4 and parts[0] == "variation_points" and parts[-2] in {"alternatives", "members"}


def _include_occurrence(
    path: list[str],
    *,
    qualified_section: str | None,
    mapping_key: bool,
) -> bool:
    if qualified_section is None:
        return True
    target = _reference_target_for_path(path, mapping_key=mapping_key)
    if target in {qualified_section, "any"}:
        return True
    return target == "targetable" and is_targetable_section(qualified_section)


def _reference_target_for_path(path: list[str], *, mapping_key: bool) -> str | None:
    if len(path) < 3:
        return None
    field = path[-2] if mapping_key or path[-1].isdigit() else path[-1]
    target = REFERENCE_COMPLETION_TARGETS.get((path[0], field))
    if target is not None:
        return target
    if path[0] == "variation_points" and field == "members":
        return "variation_points"
    if len(path) >= 4 and path[-2] == "success":
        return field if field in _SUCCESS_REFERENCE_TARGETS else None
    return None


def _bare_symbol(symbol: str) -> str:
    try:
        return QualifiedName.parse(symbol).parts[-1]
    except (TypeError, ValueError):
        return symbol


def _range_from_node(node: Node) -> dict[str, dict[str, int]]:
    return {
        "start": _location_from_mark(node.start_mark),
        "end": _location_from_mark(node.end_mark),
    }


def _location_from_mark(mark: Any | None) -> dict[str, int]:
    if mark is None:
        return {"line": 0, "column": 0}
    return {"line": mark.line + 1, "column": mark.column + 1}


def _encode_pointer(tokens: list[str]) -> str:
    if not tokens:
        return ""
    return "/" + "/".join(_escape_pointer_token(token) for token in tokens)


def _escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")
