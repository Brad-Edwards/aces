"""Neutral addressed realization-observation evidence DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from raes_contracts.addressing import require_compiled_address
from raes_contracts.realization_envelope import ObservationStrength, RealizationConcern
from raes_contracts.vocabulary import RealizationVerificationScope


@dataclass(frozen=True)
class RealizationObservation:
    """One independently read realization fact with optional conformance binding.

    Backend-local observers can keep using the five core fields. Conformance
    requires every binding field below and rejects observations that omit them;
    the defaults preserve the existing non-conformance driver boundary.
    """

    address: str
    field_path: str
    concern: RealizationConcern
    source: ObservationStrength
    value: object
    operation_id: str | None = None
    probe_digest: str | None = None
    envelope_digest: str | None = None
    configuration_digest: str | None = None
    observer_version: str | None = None
    sequence: int | None = None
    origin: str = "observed"
    binding_verified: bool = False


@dataclass(frozen=True)
class RealizationObservationDisclosure:
    """Value-free corroboration metadata for one realized inventory concern."""

    address: str
    field_path: str
    domain: str
    requirement_kind: str
    verification_scope: RealizationVerificationScope
    observation_strength: ObservationStrength

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        for field_name in ("field_path", "domain", "requirement_kind"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"RealizationObservationDisclosure.{field_name} must be non-empty")
        if not isinstance(self.verification_scope, RealizationVerificationScope):
            raise TypeError("verification_scope must be RealizationVerificationScope")
        if not isinstance(self.observation_strength, ObservationStrength):
            raise TypeError("observation_strength must be ObservationStrength")
        if self.observation_strength is ObservationStrength.NONE:
            raise ValueError("realization observation disclosure must provide non-none evidence")


__all__ = ["RealizationObservation", "RealizationObservationDisclosure"]
