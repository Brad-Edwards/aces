"""Shared constants and the bounded canonical parse path for the SDL inspection tools."""

from __future__ import annotations

_MAX_INPUT_BYTES = 64 * 1024

_SECTION_FIELDS = [
    "nodes",
    "infrastructure",
    "features",
    "conditions",
    "vulnerabilities",
    "entities",
    "injects",
    "events",
    "scripts",
    "stories",
    "content",
    "accounts",
    "relationships",
    "agents",
    "objectives",
    "workflows",
    "variables",
]

_SECTION_FIELDS_SET = frozenset(_SECTION_FIELDS)

_MAX_RECURSION_DEPTH = 20


def _parse_or_error(sdl_content: str):
    """Attempt to parse SDL, returning a Scenario or an error string."""
    if len(sdl_content.encode("utf-8", errors="replace")) > _MAX_INPUT_BYTES:
        return f"INPUT TOO LARGE — limit is {_MAX_INPUT_BYTES} bytes."

    from raes import SDLParseError, SDLValidationError, parse_sdl

    try:
        return parse_sdl(sdl_content, skip_semantic_validation=True)
    except SDLParseError as exc:
        return f"PARSE ERROR:\n{exc.details}"
    except SDLValidationError as exc:
        # Shouldn't happen with skip_semantic_validation=True, but be safe
        bullets = "\n".join(f"  - {e}" for e in exc.errors)
        return f"VALIDATION ERRORS:\n{bullets}"
