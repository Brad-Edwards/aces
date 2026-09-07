"""Atomic backend observation capture-offer declaration."""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass


def _validate_unique_non_empty_strings(field_name: str, values: Collection[str]) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{field_name} must not contain empty strings")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicate values")


_JSON_POINTER_RE = re.compile(r"^(?:/(?:[^~/]|~[01])*)*$")


@dataclass(frozen=True)
class ObservationCaptureOffer:
    """One atomic field/artifact capture promise used for admission."""

    offer_id: str
    offer_version: str
    output_contract: str
    field_selectors: tuple[str, ...]
    artifact_roles: frozenset[str]
    media_types: frozenset[str]
    capture_kind: str
    source_classes: frozenset[str]
    source_refs: frozenset[str]
    scopes: frozenset[str]
    channel_kinds: frozenset[str]
    channel_refs: frozenset[str]
    window_kinds: frozenset[str]
    integrity_modes: frozenset[str]
    sensitivity: str
    availability: str
    fidelity: str
    disclosure: str
    retention_policy_refs: frozenset[str]
    export_policy: str
    redaction_policy: str | None = None
    scope_refs: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        scalar_fields = ("offer_id", "offer_version", "output_contract", "capture_kind", "sensitivity")
        if any(not getattr(self, field_name).strip() for field_name in scalar_fields):
            raise ValueError("capture offer identity and semantic fields must be non-empty")
        for field_name in (
            "artifact_roles",
            "media_types",
            "source_classes",
            "source_refs",
            "scopes",
            "scope_refs",
            "channel_kinds",
            "channel_refs",
            "window_kinds",
            "integrity_modes",
            "retention_policy_refs",
        ):
            _validate_unique_non_empty_strings(f"ObservationCaptureOffer.{field_name}", getattr(self, field_name))
        if len(self.field_selectors) != len(set(self.field_selectors)):
            raise ValueError("ObservationCaptureOffer.field_selectors must not contain duplicate values")
        if not all((self.field_selectors, self.artifact_roles, self.media_types, self.source_classes, self.scopes)):
            raise ValueError("capture offers require fields, artifact roles, media types, source classes, and scopes")
        if not self.channel_kinds and not self.channel_refs:
            raise ValueError("capture offers must declare channel_kinds or channel_refs")
        if not self.window_kinds or not self.integrity_modes:
            raise ValueError("capture offers require window and integrity semantics")
        if any(_JSON_POINTER_RE.fullmatch(selector) is None for selector in self.field_selectors):
            raise ValueError("capture offer field_selectors must be canonical RFC 6901 JSON Pointers")
        if "*" in self.scope_refs:
            raise ValueError("capture offer scope_refs must name exact authored targets")
        if self.availability not in {"available", "unsupported", "unavailable"}:
            raise ValueError("capture offer availability is not governed")
        if self.fidelity not in {"complete", "lossy"}:
            raise ValueError("capture offer fidelity is not governed")
        if self.disclosure not in {"full", "redacted", "withheld"}:
            raise ValueError("capture offer disclosure is not governed")
        if (self.disclosure == "full") != (self.redaction_policy is None):
            raise ValueError("redacted or withheld capture offers require exactly one redaction_policy")
        if self.redaction_policy is not None and not self.redaction_policy.strip():
            raise ValueError("capture offer redaction_policy must be non-empty")
        if self.export_policy not in {"not-required", "available", "unavailable", "withheld", "prohibited"}:
            raise ValueError("capture offer export_policy is not governed")

    def to_payload(self) -> dict[str, object]:
        """Return the canonical plain-data representation."""

        return {
            "offer_id": self.offer_id,
            "offer_version": self.offer_version,
            "output_contract": self.output_contract,
            "field_selectors": list(self.field_selectors),
            "artifact_roles": sorted(self.artifact_roles),
            "media_types": sorted(self.media_types),
            "capture_kind": self.capture_kind,
            "source_classes": sorted(self.source_classes),
            "source_refs": sorted(self.source_refs),
            "scopes": sorted(self.scopes),
            "scope_refs": sorted(self.scope_refs),
            "channel_kinds": sorted(self.channel_kinds),
            "channel_refs": sorted(self.channel_refs),
            "window_kinds": sorted(self.window_kinds),
            "integrity_modes": sorted(self.integrity_modes),
            "sensitivity": self.sensitivity,
            "availability": self.availability,
            "fidelity": self.fidelity,
            "disclosure": self.disclosure,
            "retention_policy_refs": sorted(self.retention_policy_refs),
            "export_policy": self.export_policy,
            "redaction_policy": self.redaction_policy,
        }


__all__ = ["ObservationCaptureOffer"]
