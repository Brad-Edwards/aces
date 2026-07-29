"""Neutral digest-pinned verification-authority primitives.

These producer/validator identity and disposition types are shared, technique-
neutral primitives. They carry no causal, necessity, or repeatability concept;
each validation technique binds them to its own case authority and derives its
own facts. Promoted here (rather than duplicated) so bounded necessity
(ASR-513) and repeatability-consistency (ASR-514) share one authority surface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class VerificationDisposition(str, Enum):
    """Typed outcome derived by an admitted verification adapter."""

    VERIFIED = "verified"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


def _require_digest(value: str, field_name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a sha256 digest")


@dataclass(frozen=True)
class VerificationBinding:
    """Digest-pinned producer and validator identity admitted by a case."""

    producer_id: str
    producer_version: str
    producer_digest: str
    validator_id: str
    validator_version: str
    validator_digest: str

    def __post_init__(self) -> None:
        for field_name in (
            "producer_id",
            "producer_version",
            "validator_id",
            "validator_version",
        ):
            _require_text(getattr(self, field_name), field_name)
        _require_digest(self.producer_digest, "producer_digest")
        _require_digest(self.validator_digest, "validator_digest")


@dataclass(frozen=True)
class VerificationRecordIdentity:
    """Producer and validator provenance retained from one verified fact."""

    record_id: str
    record_version: str
    record_digest: str
    producer_id: str
    producer_version: str
    producer_digest: str
    validator_id: str
    validator_version: str
    validator_digest: str

    @property
    def binding(self) -> VerificationBinding:
        """Return the exact producer/validator binding retained by the record."""

        return VerificationBinding(
            producer_id=self.producer_id,
            producer_version=self.producer_version,
            producer_digest=self.producer_digest,
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            validator_digest=self.validator_digest,
        )


__all__ = (
    "VerificationBinding",
    "VerificationDisposition",
    "VerificationRecordIdentity",
)
