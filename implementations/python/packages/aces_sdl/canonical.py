"""Versioned canonical semantic identity for validated SDL authoring scenarios."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import rfc8785

from ._errors import SDLParseError
from ._source_profile import SDL_CANONICAL_PROFILE
from .scenario import InstantiatedScenario, Scenario


@dataclass(frozen=True)
class SDLCanonicalDigest:
    """Profile-labelled digest of canonical SDL semantic bytes."""

    profile: str
    algorithm: str
    value: str

    def as_dict(self) -> dict[str, str]:
        return {"profile": self.profile, "algorithm": self.algorithm, "value": self.value}


def canonical_sdl_bytes(scenario: Scenario) -> bytes:
    """Return RFC 8785 bytes for one validated, post-expansion authoring scenario."""
    if isinstance(scenario, InstantiatedScenario):
        raise SDLParseError("Canonical SDL semantic identity requires an authoring scenario, not an instantiated one")
    if not scenario.semantic_validated:
        raise SDLParseError("Canonical SDL semantic identity requires successful semantic validation")

    payload = {
        "profile": SDL_CANONICAL_PROFILE,
        "scenario": scenario.model_dump(mode="json", by_alias=True, exclude_unset=True),
        "module_variable_specs": scenario.module_variable_specs,
        "module_node_variable_refs": scenario.module_node_variable_refs,
    }
    try:
        return rfc8785.dumps(payload)
    except rfc8785.CanonicalizationError as exc:
        raise SDLParseError(f"SDL canonicalization failed: {exc}") from exc


def canonical_sdl_digest(scenario: Scenario) -> SDLCanonicalDigest:
    """Return the profile-labelled SHA-256 digest of canonical SDL semantic bytes."""
    digest = hashlib.sha256(canonical_sdl_bytes(scenario)).hexdigest()
    return SDLCanonicalDigest(
        profile=SDL_CANONICAL_PROFILE,
        algorithm="sha256",
        value=f"sha256:{digest}",
    )
