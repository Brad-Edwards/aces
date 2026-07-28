"""Internal assembled evidence types for bounded necessity validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from raes_contracts.contracts import PropositionTruthResultModel

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ASSEMBLY_TOKEN = object()


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


@dataclass(frozen=True, init=False)
class BoundedButForEvidence:
    """Evidence assembled only from validator-derived, run-bound artifacts."""

    case_digest: str
    baseline_world_id: str
    baseline_run_ref: str
    baseline_truth: PropositionTruthResultModel
    counterfactual_world_id: str
    counterfactual_run_ref: str
    counterfactual_truth: PropositionTruthResultModel
    intervention_disposition: VerificationDisposition
    intervention_evidence_refs: tuple[str, ...]
    matching_disposition: VerificationDisposition
    unmatched_dimension_refs: tuple[str, ...]
    cleanup_disposition: VerificationDisposition
    cleanup_evidence_refs: tuple[str, ...]
    residual_state: tuple[str, ...]
    verification_binding: VerificationBinding
    verification_identities: tuple[VerificationRecordIdentity, ...]
    _assembly_token: object = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("use assemble_bounded_but_for_evidence() to construct comparison evidence")

    def _has_authentic_assembly(self) -> bool:
        return self._assembly_token is _ASSEMBLY_TOKEN


def _new_bounded_but_for_evidence(
    *,
    case_digest: str,
    baseline_world_id: str,
    baseline_run_ref: str,
    baseline_truth: PropositionTruthResultModel,
    counterfactual_world_id: str,
    counterfactual_run_ref: str,
    counterfactual_truth: PropositionTruthResultModel,
    intervention_disposition: VerificationDisposition,
    intervention_evidence_refs: tuple[str, ...],
    matching_disposition: VerificationDisposition,
    unmatched_dimension_refs: tuple[str, ...],
    cleanup_disposition: VerificationDisposition,
    cleanup_evidence_refs: tuple[str, ...],
    residual_state: tuple[str, ...],
    verification_binding: VerificationBinding,
    verification_identities: tuple[VerificationRecordIdentity, ...],
) -> BoundedButForEvidence:
    """Construct one module-sealed evidence value for the trusted assembler."""

    instance = object.__new__(BoundedButForEvidence)
    values = locals()
    for field_name in BoundedButForEvidence.__dataclass_fields__:
        value = _ASSEMBLY_TOKEN if field_name == "_assembly_token" else values[field_name]
        object.__setattr__(instance, field_name, value)
    return instance


__all__ = (
    "BoundedButForEvidence",
    "VerificationBinding",
    "VerificationDisposition",
    "VerificationRecordIdentity",
)
