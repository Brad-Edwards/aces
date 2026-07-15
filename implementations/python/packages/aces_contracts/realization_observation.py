"""Neutral addressed realization-observation evidence DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from aces_contracts.realization_envelope import ObservationStrength, RealizationConcern


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


__all__ = ["RealizationObservation"]
