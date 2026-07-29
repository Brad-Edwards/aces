"""Internal assembled evidence types for bounded necessity validation."""

from __future__ import annotations

from dataclasses import dataclass, field

from raes_contracts.contracts import PropositionTruthResultModel

from .verification_authority import (
    VerificationBinding,
    VerificationDisposition,
    VerificationRecordIdentity,
)

_ASSEMBLY_TOKEN = object()


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
    parts: _BoundedButForEvidenceParts,
) -> BoundedButForEvidence:
    """Construct one module-sealed evidence value for the trusted assembler."""

    instance = object.__new__(BoundedButForEvidence)
    for field_name in BoundedButForEvidence.__dataclass_fields__:
        value = _ASSEMBLY_TOKEN if field_name == "_assembly_token" else getattr(parts, field_name)
        object.__setattr__(instance, field_name, value)
    return instance


@dataclass(frozen=True)
class _BoundedButForEvidenceParts:
    """Typed content passed across the private assembly boundary."""

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


__all__ = (
    "BoundedButForEvidence",
    "VerificationBinding",
    "VerificationDisposition",
    "VerificationRecordIdentity",
)
