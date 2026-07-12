"""ACES Scenario Description Language (SDL).

A backend-agnostic scenario specification language ported from the
Open Cyber Range SDL and extended with sections for content, accounts,
relationships, agents, objectives, workflows, and variables.
"""

from importlib import import_module

__all__ = [
    "canonical_sdl_bytes",
    "canonical_sdl_digest",
    "build_declaration_index",
    "instantiate_scenario",
    "InstantiatedScenario",
    "SDLCanonicalDigest",
    "SDL_CANONICAL_PROFILE",
    "SDLFormatResult",
    "format_sdl_source",
    "load_sdl_fragment",
    "parse_sdl",
    "parse_sdl_file",
    "Scenario",
    "SDLError",
    "SDLInstantiationError",
    "SDLMigrationPolicy",
    "SDLParserLimits",
    "SDL_SOURCE_FORMAT",
    "SDLParseDiagnostic",
    "SDLParseError",
    "SDLSourcePosition",
    "SDLSourceRange",
    "SDLValidationError",
    "VARIABLE_TOKEN_PATTERN",
]


def __getattr__(name: str):
    if name in {
        "SDLError",
        "SDLInstantiationError",
        "SDLParseDiagnostic",
        "SDLParseError",
        "SDLSourcePosition",
        "SDLSourceRange",
        "SDLValidationError",
    }:
        module = import_module("aces_sdl._errors")
    elif name in {"canonical_sdl_bytes", "canonical_sdl_digest", "SDLCanonicalDigest"}:
        module = import_module("aces_sdl.canonical")
    elif name in {"format_sdl_source", "SDLFormatResult"}:
        module = import_module("aces_sdl.formatting")
    elif name in {
        "SDL_CANONICAL_PROFILE",
        "SDLMigrationPolicy",
        "SDLParserLimits",
        "SDL_SOURCE_FORMAT",
    }:
        module = import_module("aces_sdl._source_profile")
    elif name == "VARIABLE_TOKEN_PATTERN":
        module = import_module("aces_sdl._base")
    elif name == "build_declaration_index":
        module = import_module("aces_sdl._declarations")
    elif name == "instantiate_scenario":
        module = import_module("aces_sdl.instantiate")
    elif name in {"load_sdl_fragment", "parse_sdl", "parse_sdl_file"}:
        module = import_module("aces_sdl.parser")
    elif name in {"InstantiatedScenario", "Scenario"}:
        module = import_module("aces_sdl.scenario")
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
