"""Safe, source-marked YAML composition for the SDL authoring boundary."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from ._errors import (
    SDLParseDiagnostic,
    SDLParseError,
    SDLSourcePosition,
    SDLSourceRange,
)
from ._mapping_scopes import MappingScope, is_literal_map_field, normalize_field_key

_BOOL_TAG = "tag:yaml.org,2002:bool"
_MERGE_TAG = "tag:yaml.org,2002:merge"
_STRING_TAG = "tag:yaml.org,2002:str"


class _SDLSafeLoader(yaml.SafeLoader):
    """SafeLoader that preserves implicit YAML 1.1 boolean-like map keys."""

    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self._sdl_mapping_key_context: list[bool] = []

    def compose_node(self, parent: Node | None, index: Node | None) -> Node:
        is_mapping_key = isinstance(parent, MappingNode) and index is None
        self._sdl_mapping_key_context.append(is_mapping_key)
        try:
            return super().compose_node(parent, index)
        finally:
            self._sdl_mapping_key_context.pop()

    def resolve(self, kind: type[Node], value: str | None, implicit: Any) -> str:
        tag = super().resolve(kind, value, implicit)
        if (
            kind is ScalarNode
            and self._sdl_mapping_key_context
            and self._sdl_mapping_key_context[-1]
            and tag == _BOOL_TAG
        ):
            return _STRING_TAG
        return tag


@dataclass(frozen=True)
class _Entry:
    canonical: str
    authored: str
    key_node: ScalarNode


@dataclass(frozen=True)
class _EffectiveMapping:
    entries: tuple[_Entry, ...]
    conflicts: tuple[tuple[_Entry, _Entry], ...]


class _MappingAnalyzer:
    def __init__(self) -> None:
        self.diagnostics: list[SDLParseDiagnostic] = []
        self._effective_cache: dict[tuple[int, MappingScope], _EffectiveMapping] = {}
        self._diagnostic_keys: set[tuple[Any, ...]] = set()
        self._walked: set[tuple[int, MappingScope]] = set()

    def analyze(
        self,
        root: Node,
        *,
        scope: MappingScope,
        base_tokens: list[str],
    ) -> tuple[SDLParseDiagnostic, ...]:
        self._walk(root, scope=scope, tokens=base_tokens, active=set())
        return tuple(
            sorted(
                self.diagnostics,
                key=lambda item: (
                    item.primary_range.start.line,
                    item.primary_range.start.column,
                    item.code,
                    item.pointer,
                ),
            )
        )

    def _walk(
        self,
        node: Node,
        *,
        scope: MappingScope,
        tokens: list[str],
        active: set[int],
    ) -> None:
        identity = id(node)
        if identity in active:
            self._add(
                SDLParseDiagnostic(
                    code="sdl.alias_cycle",
                    message="Cyclic YAML aliases are not valid SDL authoring input.",
                    pointer=_encode_pointer(tokens),
                    primary_range=_range_from_node(node),
                )
            )
            return

        walk_key = (identity, scope)
        if walk_key in self._walked:
            return
        self._walked.add(walk_key)

        if not isinstance(node, (MappingNode, SequenceNode)):
            return
        active.add(identity)
        try:
            if isinstance(node, SequenceNode):
                for index, item in enumerate(node.value):
                    self._walk(item, scope=scope, tokens=[*tokens, str(index)], active=active)
                return

            effective = self._effective_mapping(node, scope=scope, active=set())
            for first, conflicting in effective.conflicts:
                pointer = _encode_pointer([*tokens, conflicting.canonical])
                if first.authored == conflicting.authored:
                    message = f"Duplicate mapping key '{conflicting.authored}'."
                else:
                    message = (
                        f"Structural field keys '{first.authored}' and '{conflicting.authored}' "
                        f"both address '{conflicting.canonical}'."
                    )
                self._add(
                    SDLParseDiagnostic(
                        code="sdl.mapping_key_conflict",
                        message=message,
                        pointer=pointer,
                        authored_keys=(first.authored, conflicting.authored),
                        primary_range=_range_from_node(conflicting.key_node),
                        related_range=_range_from_node(first.key_node),
                        related_message=f"First authored key '{first.authored}'.",
                    )
                )

            for key_node, value_node in node.value:
                if _is_merge_key(key_node):
                    self._walk_merge_value(value_node, scope=scope, tokens=tokens, active=active)
                    continue
                authored = _authored_key(key_node)
                if not _is_string_key(key_node):
                    message = (
                        "SDL top-level mapping keys must be strings"
                        if not tokens
                        else f"SDL mapping key '{authored}' must be a string."
                    )
                    self._add(
                        SDLParseDiagnostic(
                            code="sdl.mapping_key_type",
                            message=message,
                            pointer=_encode_pointer([*tokens, authored]),
                            primary_range=_range_from_node(key_node),
                        )
                    )
                    continue
                canonical = normalize_field_key(authored) if scope is MappingScope.STRUCTURAL else authored
                child_tokens = [*tokens, canonical]
                if scope is MappingScope.STRUCTURAL and is_literal_map_field(
                    canonical,
                    value_is_mapping=isinstance(value_node, MappingNode),
                    value_is_sequence=isinstance(value_node, SequenceNode),
                ):
                    child_scope = MappingScope.LITERAL
                else:
                    child_scope = MappingScope.STRUCTURAL
                self._walk(value_node, scope=child_scope, tokens=child_tokens, active=active)
        finally:
            active.remove(identity)

    def _walk_merge_value(
        self,
        node: Node,
        *,
        scope: MappingScope,
        tokens: list[str],
        active: set[int],
    ) -> None:
        if isinstance(node, MappingNode):
            self._walk(node, scope=scope, tokens=tokens, active=active)
        elif isinstance(node, SequenceNode):
            for item in node.value:
                self._walk(item, scope=scope, tokens=tokens, active=active)

    def _effective_mapping(
        self,
        node: MappingNode,
        *,
        scope: MappingScope,
        active: set[int],
    ) -> _EffectiveMapping:
        cache_key = (id(node), scope)
        cached = self._effective_cache.get(cache_key)
        if cached is not None:
            return cached
        if id(node) in active:
            return _EffectiveMapping((), ())

        active.add(id(node))
        ordered: list[_Entry] = []
        conflicts: list[tuple[_Entry, _Entry]] = []
        seen: dict[str, _Entry] = {}

        def add(entry: _Entry) -> None:
            previous = seen.get(entry.canonical)
            if previous is None:
                seen[entry.canonical] = entry
                ordered.append(entry)
            else:
                conflicts.append((previous, entry))

        try:
            merge_keys: list[ScalarNode] = []
            for key_node, value_node in node.value:
                if not _is_merge_key(key_node):
                    continue
                if isinstance(key_node, ScalarNode):
                    merge_keys.append(key_node)
                for source in _merge_sources(value_node):
                    if id(source) in active:
                        continue
                    inherited = self._effective_mapping(source, scope=scope, active=active)
                    for entry in inherited.entries:
                        add(entry)

            for first, conflicting in zip(merge_keys, merge_keys[1:], strict=False):
                add(_Entry("<<", "<<", first))
                add(_Entry("<<", "<<", conflicting))

            for key_node, _value_node in node.value:
                if not _is_string_key(key_node) or _is_merge_key(key_node):
                    continue
                assert isinstance(key_node, ScalarNode)
                authored = key_node.value
                canonical = normalize_field_key(authored) if scope is MappingScope.STRUCTURAL else authored
                add(_Entry(canonical, authored, key_node))
        finally:
            active.remove(id(node))

        result = _EffectiveMapping(tuple(ordered), tuple(conflicts))
        self._effective_cache[cache_key] = result
        return result

    def _add(self, diagnostic: SDLParseDiagnostic) -> None:
        related = diagnostic.related_range
        key = (
            diagnostic.code,
            diagnostic.pointer,
            diagnostic.primary_range.start.line,
            diagnostic.primary_range.start.column,
            related.start.line if related else None,
            related.start.column if related else None,
        )
        if key not in self._diagnostic_keys:
            self._diagnostic_keys.add(key)
            self.diagnostics.append(diagnostic)


def load_sdl_yaml(
    content: str,
    *,
    path: Path | None = None,
    scope: MappingScope = MappingScope.STRUCTURAL,
    base_pointer: str = "",
) -> Any:
    """Validate and safely construct one SDL YAML document or fragment."""
    prepared = _prepare_content(content, path=path)
    loader: _SDLSafeLoader | None = None
    try:
        loader = _SDLSafeLoader(prepared)
        root = loader.get_single_node()
        if root is None:
            raise SDLParseError("SDL content is empty", path=path)
        _validate_mapping_keys(root, path=path, scope=scope, base_pointer=base_pointer)
        return loader.construct_document(root)
    except SDLParseError:
        raise
    except yaml.YAMLError as exc:
        raise _yaml_parse_error(exc, path=path) from exc
    finally:
        if loader is not None:
            loader.dispose()


def compose_sdl_yaml(
    content: str,
    *,
    path: Path | None = None,
    scope: MappingScope = MappingScope.STRUCTURAL,
    base_pointer: str = "",
) -> Node:
    """Compose and key-validate SDL YAML while retaining source nodes."""
    prepared = _prepare_content(content, path=path)
    loader: _SDLSafeLoader | None = None
    try:
        loader = _SDLSafeLoader(prepared)
        root = loader.get_single_node()
        if root is None:
            raise SDLParseError("SDL content is empty", path=path)
        _validate_mapping_keys(root, path=path, scope=scope, base_pointer=base_pointer)
        return root
    except SDLParseError:
        raise
    except yaml.YAMLError as exc:
        raise _yaml_parse_error(exc, path=path) from exc
    finally:
        if loader is not None:
            loader.dispose()


def _validate_mapping_keys(
    root: Node,
    *,
    path: Path | None,
    scope: MappingScope,
    base_pointer: str,
) -> None:
    diagnostics = _MappingAnalyzer().analyze(root, scope=scope, base_tokens=_decode_pointer(base_pointer))
    if not diagnostics:
        return
    rendered: list[str] = []
    for item in diagnostics:
        location = item.primary_range.start
        detail = (
            f"[{item.code}] {item.pointer or '/'} at line {location.line}, column {location.column}: {item.message}"
        )
        if item.related_range is not None:
            related = item.related_range.start
            detail += f" First declaration at line {related.line}, column {related.column}."
        rendered.append(detail)
    details = "SDL mapping-key validation failed:\n  " + "\n  ".join(rendered)
    raise SDLParseError(details, path=path, diagnostics=diagnostics)


def _prepare_content(content: str, *, path: Path | None) -> str:
    prepared = textwrap.dedent(content)
    if not prepared.strip():
        raise SDLParseError("SDL content is empty", path=path)
    return prepared


def _yaml_parse_error(error: yaml.YAMLError, *, path: Path | None) -> SDLParseError:
    mark = getattr(error, "problem_mark", None)
    problem = getattr(error, "problem", None)
    if mark is None:
        return SDLParseError(f"Invalid YAML: {error}", path=path)
    position = SDLSourcePosition(mark.line + 1, mark.column + 1)
    diagnostic = SDLParseDiagnostic(
        code="sdl.parse",
        message=str(problem or error),
        pointer="",
        primary_range=SDLSourceRange(start=position, end=position),
    )
    return SDLParseError(f"Invalid YAML: {error}", path=path, diagnostics=(diagnostic,))


def _is_merge_key(node: Node) -> bool:
    return isinstance(node, ScalarNode) and node.tag == _MERGE_TAG


def _is_string_key(node: Node) -> bool:
    return isinstance(node, ScalarNode) and node.tag == _STRING_TAG


def _authored_key(node: Node) -> str:
    if isinstance(node, ScalarNode):
        return node.value
    return "?"


def _merge_sources(node: Node) -> tuple[MappingNode, ...]:
    if isinstance(node, MappingNode):
        return (node,)
    if isinstance(node, SequenceNode):
        return tuple(item for item in node.value if isinstance(item, MappingNode))
    return ()


def _range_from_node(node: Node) -> SDLSourceRange:
    return SDLSourceRange(
        start=SDLSourcePosition(node.start_mark.line + 1, node.start_mark.column + 1),
        end=SDLSourcePosition(node.end_mark.line + 1, node.end_mark.column + 1),
    )


def _encode_pointer(tokens: list[str]) -> str:
    if not tokens:
        return ""
    return "/" + "/".join(token.replace("~", "~0").replace("/", "~1") for token in tokens)


def _decode_pointer(pointer: str) -> list[str]:
    if not pointer:
        return []
    if not pointer.startswith("/"):
        raise ValueError("base_pointer must be an RFC 6901 pointer")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]
