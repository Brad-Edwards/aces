"""Operational validation for the versioned SDL YAML source profile."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, SequenceNode
from yaml.tokens import AliasToken, DirectiveToken, ScalarToken, TagToken, Token

from ._errors import SDLParseDiagnostic, SDLParseError, SDLSourcePosition, SDLSourceRange
from ._source_profile import SDL_SOURCE_FORMAT, SDLMigrationPolicy, SDLParserLimits

EMPTY_CONTENT_MESSAGE = "SDL content is empty"


def prepare_content(content: str, *, path: Path | None) -> str:
    """Reject empty or non-UTF-8-compatible source without rewriting it."""
    if not content.strip():
        raise SDLParseError(EMPTY_CONTENT_MESSAGE, path=path)
    try:
        content.encode("utf-8")
    except UnicodeEncodeError as exc:
        diagnostic = _diagnostic_at_start(
            code="sdl.utf8",
            message="SDL source must be valid UTF-8 without unpaired surrogate code points.",
            path=path,
        )
        raise SDLParseError(diagnostic.message, path=path, diagnostics=(diagnostic,)) from exc
    return content


def validate_source_format(source_format: str, *, path: Path | None) -> None:
    """Require the one implemented versioned source profile."""
    if source_format == SDL_SOURCE_FORMAT:
        return
    diagnostic = _diagnostic_at_start(
        code="sdl.source_format",
        message=f"Unsupported SDL source format '{source_format}'; expected '{SDL_SOURCE_FORMAT}'.",
        path=path,
    )
    raise SDLParseError(diagnostic.message, path=path, diagnostics=(diagnostic,))


def coerce_migration_policy(
    migration_policy: SDLMigrationPolicy | str,
    *,
    path: Path | None,
) -> SDLMigrationPolicy:
    """Validate the explicit migration-policy selector."""
    try:
        return SDLMigrationPolicy(migration_policy)
    except ValueError as exc:
        allowed = ", ".join(policy.value for policy in SDLMigrationPolicy)
        diagnostic = _diagnostic_at_start(
            code="sdl.migration_policy",
            message=f"Unsupported SDL migration policy '{migration_policy}'; expected one of: {allowed}.",
            path=path,
        )
        raise SDLParseError(diagnostic.message, path=path, diagnostics=(diagnostic,)) from exc


def validate_source_tokens(content: str, *, path: Path | None, limits: SDLParserLimits) -> None:
    """Enforce byte/scalar/alias limits and forbidden presentation tokens."""
    input_bytes = len(content.encode("utf-8"))
    if input_bytes > limits.max_input_bytes:
        _raise_source_limit(
            f"SDL source is {input_bytes} bytes; limit is {limits.max_input_bytes} bytes.",
            path=path,
        )

    aliases = 0
    try:
        for token in yaml.scan(content, Loader=yaml.SafeLoader):
            if isinstance(token, AliasToken):
                aliases += 1
                if aliases > limits.max_aliases:
                    _raise_source_limit(
                        f"SDL source has more than {limits.max_aliases} alias occurrences.",
                        path=path,
                        token=token,
                    )
            elif isinstance(token, ScalarToken):
                scalar_bytes = len(token.value.encode("utf-8"))
                if scalar_bytes > limits.max_scalar_bytes:
                    _raise_source_limit(
                        f"SDL scalar is {scalar_bytes} bytes; limit is {limits.max_scalar_bytes} bytes.",
                        path=path,
                        token=token,
                    )
            elif isinstance(token, TagToken):
                _raise_token_diagnostic(
                    code="sdl.explicit_tag",
                    message="Explicit YAML tags are not valid sdl-yaml/v1 authoring syntax.",
                    path=path,
                    token=token,
                )
            elif isinstance(token, DirectiveToken):
                _raise_token_diagnostic(
                    code="sdl.directive",
                    message="YAML directives are not valid sdl-yaml/v1 authoring syntax.",
                    path=path,
                    token=token,
                )
    except SDLParseError:
        raise
    except yaml.YAMLError as exc:
        raise yaml_parse_error(exc, path=path) from exc


def validate_source_graph(root: Node, *, path: Path | None, limits: SDLParserLimits) -> None:
    """Bound unique nodes, expanded alias work, and effective depth."""
    unique: set[int] = set()
    active: set[int] = set()
    memoized_metrics: dict[int, tuple[int, int]] = {}

    def expanded_metrics(node: Node, depth: int) -> tuple[int, int]:
        if depth > limits.max_depth:
            _raise_source_limit(f"SDL node depth exceeds {limits.max_depth}.", path=path, node=node)
        identity = id(node)
        if identity in active:
            return 0, 0
        if identity not in unique:
            unique.add(identity)
            if len(unique) > limits.max_nodes:
                _raise_source_limit(
                    f"SDL node graph has more than {limits.max_nodes} unique nodes.",
                    path=path,
                    node=node,
                )
        cached = memoized_metrics.get(identity)
        if cached is not None:
            _cost, height = cached
            if depth + height - 1 > limits.max_depth:
                _raise_source_limit(f"SDL node depth exceeds {limits.max_depth}.", path=path, node=node)
            return cached
        active.add(identity)
        try:
            cost = 1
            height = 1
            if isinstance(node, MappingNode):
                children = (child for pair in node.value for child in pair)
                for child in children:
                    child_cost, child_height = expanded_metrics(child, depth + 1)
                    cost += child_cost
                    height = max(height, child_height + 1)
                    _check_expanded_cost(cost, node=node, path=path, limits=limits)
            elif isinstance(node, SequenceNode):
                for child in node.value:
                    child_cost, child_height = expanded_metrics(child, depth + 1)
                    cost += child_cost
                    height = max(height, child_height + 1)
                    _check_expanded_cost(cost, node=node, path=path, limits=limits)
        finally:
            active.remove(identity)
        memoized_metrics[identity] = (cost, height)
        return cost, height

    expanded_metrics(root, 1)


def _check_expanded_cost(
    cost: int,
    *,
    node: Node,
    path: Path | None,
    limits: SDLParserLimits,
) -> None:
    if cost > limits.max_expanded_nodes:
        _raise_source_limit(
            f"SDL alias-expanded work exceeds {limits.max_expanded_nodes} nodes.",
            path=path,
            node=node,
        )


def validate_constructed_domain(value: object, *, path: Path | None) -> None:
    """Reject values outside the string-keyed JSON data domain."""
    active: set[int] = set()
    visited: set[int] = set()

    def visit(item: object) -> None:
        if item is None or type(item) in {str, bool, int}:  # noqa: E721 - exact domain is intentional
            return
        if type(item) is float:  # noqa: E721 - exact domain is intentional
            if math.isfinite(item):
                return
            _raise_domain_error("Non-finite numbers are not valid SDL values.", path=path)
        identity = id(item)
        if identity in active or identity in visited:
            return
        if type(item) is list:  # noqa: E721 - reject implementation-specific containers
            active.add(identity)
            try:
                for child in item:
                    visit(child)
            finally:
                active.remove(identity)
            visited.add(identity)
            return
        if type(item) is dict:  # noqa: E721 - reject custom mapping constructors
            active.add(identity)
            try:
                for key, child in item.items():
                    if not isinstance(key, str):
                        _raise_domain_error("SDL mapping keys must construct as strings.", path=path)
                    visit(child)
            finally:
                active.remove(identity)
            visited.add(identity)
            return
        _raise_domain_error(f"YAML value type '{type(item).__name__}' is outside the SDL JSON domain.", path=path)

    visit(value)


def _raise_domain_error(message: str, *, path: Path | None) -> None:
    diagnostic = _diagnostic_at_start(code="sdl.non_json_value", message=message, path=path)
    raise SDLParseError(message, path=path, diagnostics=(diagnostic,))


def _raise_source_limit(
    message: str,
    *,
    path: Path | None,
    token: Token | None = None,
    node: Node | None = None,
) -> None:
    if token is not None:
        primary_range = _range_from_marks(token.start_mark, token.end_mark)
    elif node is not None:
        primary_range = _range_from_node(node)
    else:
        primary_range = _start_range()
    diagnostic = SDLParseDiagnostic(
        code="sdl.source_limit",
        message=message,
        pointer="",
        primary_range=primary_range,
        source=str(path) if path is not None else None,
    )
    raise SDLParseError(message, path=path, diagnostics=(diagnostic,))


def _raise_token_diagnostic(*, code: str, message: str, path: Path | None, token: Token) -> None:
    diagnostic = SDLParseDiagnostic(
        code=code,
        message=message,
        pointer="",
        primary_range=_range_from_marks(token.start_mark, token.end_mark),
        source=str(path) if path is not None else None,
    )
    raise SDLParseError(message, path=path, diagnostics=(diagnostic,))


def _diagnostic_at_start(*, code: str, message: str, path: Path | None) -> SDLParseDiagnostic:
    return SDLParseDiagnostic(
        code=code,
        message=message,
        pointer="",
        primary_range=_start_range(),
        source=str(path) if path is not None else None,
    )


def _start_range() -> SDLSourceRange:
    position = SDLSourcePosition(1, 1)
    return SDLSourceRange(start=position, end=position)


def _range_from_marks(start: Any, end: Any) -> SDLSourceRange:
    return SDLSourceRange(
        start=SDLSourcePosition(start.line + 1, start.column + 1),
        end=SDLSourcePosition(end.line + 1, end.column + 1),
    )


def _range_from_node(node: Node) -> SDLSourceRange:
    return _range_from_marks(node.start_mark, node.end_mark)


def yaml_parse_error(error: yaml.YAMLError, *, path: Path | None) -> SDLParseError:
    """Translate a PyYAML error into the stable SDL parse envelope."""
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
        source=str(path) if path is not None else None,
    )
    return SDLParseError(f"Invalid YAML: {error}", path=path, diagnostics=(diagnostic,))
