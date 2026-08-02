"""Shared apparatus declaration dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .vocabulary import ObservationStrength, RealizationSupportMode, RealizationVerificationScope

if TYPE_CHECKING:
    from .artifact_requirements import ArtifactMechanismCapability

DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND = "declared-capability-match"
RUNTIME_REALIZATION_DOMAIN = "runtime-realization"


def _require_non_empty_strings(values: frozenset[str], *, field_name: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{field_name} must not contain empty strings")


@dataclass(frozen=True)
class ApparatusIdentity:
    """Stable identity for an apparatus surface."""

    name: str
    version: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ApparatusIdentity.name must be non-empty")
        if not self.version.strip():
            raise ValueError("ApparatusIdentity.version must be non-empty")


@dataclass(frozen=True)
class ConceptBinding:
    """Binds a vocabulary surface path to a canonical concept family."""

    scope: str
    family: str

    def __post_init__(self) -> None:
        if not self.scope.strip():
            raise ValueError("ConceptBinding.scope must be non-empty")
        if not self.family.strip():
            raise ValueError("ConceptBinding.family must be non-empty")


@dataclass(frozen=True)
class RealizationObservationCapability:
    """Declared concern-specific corroboration available from a backend."""

    verification_scope: RealizationVerificationScope
    observation_strength: ObservationStrength

    def __post_init__(self) -> None:
        if not isinstance(self.verification_scope, RealizationVerificationScope):
            raise TypeError("verification_scope must be RealizationVerificationScope")
        if not isinstance(self.observation_strength, ObservationStrength):
            raise TypeError("observation_strength must be ObservationStrength")
        if self.observation_strength is ObservationStrength.NONE:
            raise ValueError("realization observation capability must provide non-none evidence")


@dataclass(frozen=True)
class RealizationSupportDeclaration:
    """Declared realization-support and disclosure surface for one concern domain."""

    domain: str
    support_mode: RealizationSupportMode
    supported_constraint_kinds: frozenset[str] = frozenset()
    supported_exact_requirement_kinds: frozenset[str] = frozenset()
    disclosure_kinds: frozenset[str] = frozenset()
    observation_capabilities: dict[str, RealizationObservationCapability] = field(default_factory=dict)
    artifact_mechanisms: tuple[ArtifactMechanismCapability, ...] = ()
    constraints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.domain.strip():
            raise ValueError("RealizationSupportDeclaration.domain must be non-empty")
        _require_non_empty_strings(self.supported_constraint_kinds, field_name="supported_constraint_kinds")
        _require_non_empty_strings(
            self.supported_exact_requirement_kinds,
            field_name="supported_exact_requirement_kinds",
        )
        _require_non_empty_strings(self.disclosure_kinds, field_name="disclosure_kinds")
        if any(not kind.strip() for kind in self.observation_capabilities):
            raise ValueError("observation_capabilities must not contain empty concern kinds")
        if any(
            not isinstance(capability, RealizationObservationCapability)
            for capability in self.observation_capabilities.values()
        ):
            raise TypeError("observation_capabilities values must be RealizationObservationCapability")
        if not self.disclosure_kinds:
            raise ValueError("RealizationSupportDeclaration.disclosure_kinds must not be empty")
        if not (self.supported_constraint_kinds or self.supported_exact_requirement_kinds):
            raise ValueError(
                "RealizationSupportDeclaration must declare supported_constraint_kinds "
                "or supported_exact_requirement_kinds"
            )
        if self.support_mode == RealizationSupportMode.EXACT_ONLY and self.supported_constraint_kinds:
            raise ValueError("exact-only realization support must not declare supported_constraint_kinds")
        identities = [
            (
                capability.mechanism.mechanism,
                capability.mechanism.profile,
                capability.mechanism.version,
                capability.mechanism.digest,
            )
            for capability in self.artifact_mechanisms
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("artifact_mechanisms must not contain duplicate mechanism profiles")
