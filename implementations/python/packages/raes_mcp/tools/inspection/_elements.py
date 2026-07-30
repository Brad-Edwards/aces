"""Element listing and detail rendering for the SDL inspection tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._common import _MAX_RECURSION_DEPTH, _SECTION_FIELDS, _SECTION_FIELDS_SET

if TYPE_CHECKING:
    from raes import Scenario


def _list_elements(scenario: Scenario, section_filter: str) -> str:
    """List named elements, optionally filtered by section."""
    lines: list[str] = []
    for field in _SECTION_FIELDS:
        if section_filter not in ("all", "") and field != section_filter:
            continue
        data = getattr(scenario, field, None)
        if data:
            lines.extend(_section_element_lines(field, data))

    if lines:
        return "\n".join(lines)
    if section_filter not in ("all", ""):
        return f"Section '{section_filter}' is empty or does not exist."
    return "Scenario has no named elements."


def _section_element_lines(field: str, data: dict[str, object]) -> list[str]:
    lines = [f"\n{field}:"]
    lines.extend(f"  - {name}" for name in data)
    # Special: show nested entities
    if field == "entities":
        lines.extend(_nested_entity_lines(data))
    return lines


def _nested_entity_lines(data: dict[str, object]) -> list[str]:
    from raes.entities import flatten_entities

    flat = flatten_entities(data)
    nested = [n for n in flat if "." in n]
    if not nested:
        return []
    return ["  (nested entities):", *(f"    - {n}" for n in nested)]


def _get_element_detail(scenario: Scenario, name: str) -> str:
    """Get detailed info about a named element."""
    qualified = _qualified_ref_detail(scenario, name)
    if qualified is not None:
        return qualified
    matches = _bare_name_matches(scenario, name)
    if not matches:
        return _no_match_detail(scenario, name)
    return _matches_detail(name, matches)


def _qualified_ref_detail(scenario: Scenario, name: str) -> str | None:
    """Resolve a qualified ref like 'nodes.web-server', or None if it does not resolve."""
    if "." not in name:
        return None
    section_name, element_name = name.split(".", 1)
    # Only access known SDL section attributes — never arbitrary attrs.
    if section_name in _SECTION_FIELDS_SET:
        data = getattr(scenario, section_name, None)
        if isinstance(data, dict) and element_name in data:
            return _format_element(section_name, element_name, data[element_name])
    return None


def _bare_name_matches(scenario: Scenario, name: str) -> list[tuple[str, str, object]]:
    matches: list[tuple[str, str, object]] = []
    for field in _SECTION_FIELDS:
        data = getattr(scenario, field, None)
        if data and name in data:
            matches.append((field, name, data[name]))
    return matches


def _no_match_detail(scenario: Scenario, name: str) -> str:
    # Try nested entity names
    from raes.entities import flatten_entities

    if scenario.entities:
        flat = flatten_entities(scenario.entities)
        if name in flat:
            return _format_element("entities", name, flat[name])

    return (
        f"Element '{name}' not found. "
        "Use `sdl_list_elements` to see all available elements, "
        "or try a qualified ref like 'nodes.my-node'."
    )


def _matches_detail(name: str, matches: list[tuple[str, str, object]]) -> str:
    if len(matches) == 1:
        section, ename, obj = matches[0]
        return _format_element(section, ename, obj)
    # Ambiguous
    lines = [f"Ambiguous name '{name}' found in multiple sections:"]
    lines.extend(f"  - {section}.{ename}" for section, ename, _ in matches)
    lines.append("Use a qualified ref to disambiguate.")
    return "\n".join(lines)


def _format_element(section: str, name: str, obj: object) -> str:
    """Format a single element's details as readable text."""
    lines = [f"{section}.{name}"]

    if hasattr(obj, "model_dump"):
        data = obj.model_dump(exclude_defaults=True, exclude_none=True)
        for key, value in data.items():
            if isinstance(value, dict) and not value:
                continue
            if isinstance(value, list) and not value:
                continue
            lines.append(f"  {key}: {_format_value(value)}")
    else:
        lines.append(f"  {obj!r}")

    return "\n".join(lines)


def _format_value(value: object, indent: int = 4, depth: int = 0) -> str:
    """Format a value for display, handling nested structures."""
    if depth > _MAX_RECURSION_DEPTH:
        return "(...)"
    if isinstance(value, dict):
        result = _format_dict_value(value, indent, depth)
    elif isinstance(value, list):
        result = _format_list_value(value, indent, depth)
    else:
        result = _format_scalar_value(value)
    return result


def _format_dict_value(value: dict[object, object], indent: int, depth: int) -> str:
    if not value:
        return "{}"
    prefix = " " * indent
    parts = [f"{prefix}{k}: {_format_value(v, indent + 2, depth + 1)}" for k, v in value.items()]
    return "\n" + "\n".join(parts)


def _format_list_value(value: list[object], indent: int, depth: int) -> str:
    if not value:
        return "[]"
    if all(isinstance(v, str) for v in value):
        return f"[{', '.join(str(v) for v in value)}]"
    prefix = " " * indent
    parts = [f"{prefix}- {_format_value(v, indent + 2, depth + 1)}" for v in value]
    return "\n" + "\n".join(parts)


def _format_scalar_value(value: object) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
