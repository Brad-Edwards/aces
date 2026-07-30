"""Element listing and detail rendering for the SDL inspection tools."""

from __future__ import annotations

from ._common import _MAX_RECURSION_DEPTH, _SECTION_FIELDS, _SECTION_FIELDS_SET


def _list_elements(scenario, section_filter: str) -> str:
    """List named elements, optionally filtered by section."""
    from raes.entities import flatten_entities

    lines: list[str] = []
    for field in _SECTION_FIELDS:
        if section_filter not in ("all", "") and field != section_filter:
            continue
        data = getattr(scenario, field, None)
        if not data:
            continue
        lines.append(f"\n{field}:")
        for name in data:
            lines.append(f"  - {name}")
        # Special: show nested entities
        if field == "entities":
            flat = flatten_entities(data)
            nested = [n for n in flat if "." in n]
            if nested:
                lines.append("  (nested entities):")
                for n in nested:
                    lines.append(f"    - {n}")

    if not lines:
        if section_filter not in ("all", ""):
            return f"Section '{section_filter}' is empty or does not exist."
        return "Scenario has no named elements."

    return "\n".join(lines)


def _get_element_detail(scenario, name: str) -> str:
    """Get detailed info about a named element."""
    # Try qualified ref first (e.g. "nodes.web-server")
    if "." in name:
        parts = name.split(".", 1)
        section_name, element_name = parts[0], parts[1]
        # Only access known SDL section attributes — never arbitrary attrs.
        if section_name in _SECTION_FIELDS_SET:
            data = getattr(scenario, section_name, None)
            if isinstance(data, dict) and element_name in data:
                return _format_element(section_name, element_name, data[element_name])

    # Search all sections for bare name
    matches: list[tuple[str, str, object]] = []
    for field in _SECTION_FIELDS:
        data = getattr(scenario, field, None)
        if not data:
            continue
        if name in data:
            matches.append((field, name, data[name]))

    if not matches:
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

    if len(matches) == 1:
        section, ename, obj = matches[0]
        return _format_element(section, ename, obj)

    # Ambiguous
    lines = [f"Ambiguous name '{name}' found in multiple sections:"]
    for section, ename, _ in matches:
        lines.append(f"  - {section}.{ename}")
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
        if not value:
            return "{}"
        parts = []
        prefix = " " * indent
        for k, v in value.items():
            parts.append(f"{prefix}{k}: {_format_value(v, indent + 2, depth + 1)}")
        return "\n" + "\n".join(parts)
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(isinstance(v, str) for v in value):
            return f"[{', '.join(str(v) for v in value)}]"
        parts = []
        prefix = " " * indent
        for v in value:
            parts.append(f"{prefix}- {_format_value(v, indent + 2, depth + 1)}")
        return "\n" + "\n".join(parts)
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
