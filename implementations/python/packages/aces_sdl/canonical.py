"""Versioned canonical semantic identity for validated SDL authoring scenarios."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import rfc8785
from pydantic import ConfigDict

from ._base import SDLModel
from ._errors import SDLParseError
from ._source_profile import SDL_CANONICAL_PROFILE
from .scenario import ExpandedScenario, InstantiatedScenario, Scenario

INSTANTIATED_SNAPSHOT_PROFILE = "aces-sdl-instantiated-snapshot/v1"


@dataclass(frozen=True)
class SDLCanonicalDigest:
    """Profile-labelled digest of canonical SDL semantic bytes."""

    profile: str
    algorithm: str
    value: str

    def as_dict(self) -> dict[str, str]:
        return {"profile": self.profile, "algorithm": self.algorithm, "value": self.value}


def canonical_sdl_bytes(scenario: Scenario | ExpandedScenario) -> bytes:
    """Return RFC 8785 bytes for one validated, post-expansion authoring scenario."""
    if isinstance(scenario, InstantiatedScenario):
        raise SDLParseError("Canonical SDL semantic identity requires an authoring scenario, not an instantiated one")
    if not scenario.semantic_validated:
        raise SDLParseError("Canonical SDL semantic identity requires successful semantic validation")

    excluded_fields = {"expansion_provenance"}
    if not scenario.variation_points:
        excluded_fields.add("variation_points")
    payload = {
        "profile": SDL_CANONICAL_PROFILE,
        "scenario": scenario.model_dump(
            mode="json",
            by_alias=True,
            exclude_unset=True,
            exclude=excluded_fields,
        ),
        "module_variable_specs": scenario.module_variable_specs,
        "module_node_variable_refs": scenario.module_node_variable_refs,
    }
    try:
        return rfc8785.dumps(payload)
    except rfc8785.CanonicalizationError as exc:
        raise SDLParseError(f"SDL canonicalization failed: {exc}") from exc


def canonical_sdl_digest(scenario: Scenario | ExpandedScenario) -> SDLCanonicalDigest:
    """Return the profile-labelled SHA-256 digest of canonical SDL semantic bytes."""
    digest = hashlib.sha256(canonical_sdl_bytes(scenario)).hexdigest()
    return SDLCanonicalDigest(
        profile=SDL_CANONICAL_PROFILE,
        algorithm="sha256",
        value=f"sha256:{digest}",
    )


class InstantiatedScenarioSnapshot(SDLModel):
    """Sealed canonical envelope for one portable instantiated artifact."""

    model_config = ConfigDict(
        title="SDL Instantiated Scenario Snapshot v1",
        extra="forbid",
        frozen=True,
        json_schema_extra={"x-aces-document-phase": "canonical-instantiated-snapshot"},
    )

    profile: Literal["aces-sdl-instantiated-snapshot/v1"]
    scenario: InstantiatedScenario


def canonical_instantiated_sdl_bytes(scenario: InstantiatedScenario) -> bytes:
    """Return RFC 8785 bytes for one admitted instantiated artifact."""

    # Keep canonicalization pure with respect to the caller's private validation
    # flags while applying the same structural and semantic admission boundary
    # used by the compiler.
    from .instantiate import admit_instantiated_scenario

    admitted = admit_instantiated_scenario(
        InstantiatedScenario.model_validate(scenario.model_dump(mode="python", by_alias=True))
    )
    snapshot = InstantiatedScenarioSnapshot(
        profile=INSTANTIATED_SNAPSHOT_PROFILE,
        scenario=admitted,
    )
    try:
        return rfc8785.dumps(snapshot.model_dump(mode="json"))
    except rfc8785.CanonicalizationError as exc:
        raise SDLParseError(f"Instantiated SDL canonicalization failed: {exc}") from exc


def canonical_instantiated_sdl_digest(scenario: InstantiatedScenario) -> SDLCanonicalDigest:
    """Return the profile-labelled digest of an instantiated snapshot."""

    digest = hashlib.sha256(canonical_instantiated_sdl_bytes(scenario)).hexdigest()
    return SDLCanonicalDigest(
        profile=INSTANTIATED_SNAPSHOT_PROFILE,
        algorithm="sha256",
        value=f"sha256:{digest}",
    )
