"""Trusted owner adapters for native semantic-projection facts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .canonical import canonical_json_digest
from .contracts.artifact_transformations import (
    ArtifactTransformationReportModel,
    ArtifactTransformationStatus,
    PreservationOutcome,
)
from .contracts.execution_state import (
    PropositionEvaluationBasis,
    PropositionTruthOutcome,
    PropositionTruthResultModel,
)
from .contracts.experiment_evidence import ExperimentEvidenceRecordModel
from .contracts.external_concept_bindings import ExternalConceptSubjectModel
from .contracts.semantic_projection import (
    SemanticProjectionApplicableCoordinateModel,
    SemanticProjectionEvidenceBoundaryModel,
    SemanticProjectionFrameModel,
    SemanticProjectionPredicateProfileModel,
    SemanticProjectionTransformationCoordinateModel,
)
from .contracts.validation_disclosure import ValidationBasisDisclosureDocumentModel

_FactOutcome = Literal["satisfied", "not-satisfied", "unknown", "unsupported"]


@dataclass(frozen=True, slots=True)
class _SemanticProjectionFact:
    predicate_id: str
    producer_contract_id: str
    subject: ExternalConceptSubjectModel
    outcome: _FactOutcome
    native_result_id: str
    native_result_digest: str
    evidence_digests: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    evidence_boundary_digest: str | None
    owner_artifact: object
    owner_evidence: tuple[ExperimentEvidenceRecordModel, ...]


class SemanticProjectionEvidenceResolver(Protocol):
    """Trusted evidence authority resolved by a service, never request payload data."""

    def __call__(
        self,
        *,
        evidence_ref: str,
        evidence_boundary: SemanticProjectionEvidenceBoundaryModel,
    ) -> ExperimentEvidenceRecordModel | None: ...


def semantic_projection_declared_configuration_coordinate(
    subjects: tuple[ExternalConceptSubjectModel, ...],
) -> SemanticProjectionApplicableCoordinateModel:
    """Bind the declared configuration axis to the complete exact subject scope."""

    ordered = tuple(
        sorted(
            subjects,
            key=lambda subject: (
                subject.subject_kind,
                subject.owning_contract_id,
                subject.lifecycle_phase.value,
                subject.canonical_ref,
                subject.artifact_digest,
            ),
        )
    )
    return SemanticProjectionApplicableCoordinateModel(
        posture="applicable",
        coordinate_id="native-subject-configuration-scope/v1",
        coordinate_version="1",
        coordinate_digest=canonical_json_digest(
            {
                "coordinate_profile": "native-subject-configuration-scope/v1",
                "subjects": [subject.model_dump(mode="json") for subject in ordered],
            }
        ),
        cut_ref="native-subject-artifact",
    )


def semantic_projection_observed_state_coordinate(
    results: tuple[PropositionTruthResultModel, ...],
    *,
    evaluation_cut_ref: str,
) -> SemanticProjectionApplicableCoordinateModel:
    """Bind the observed state axis to every exact truth result at one cut."""

    ordered = tuple(
        sorted(
            results,
            key=lambda result: (
                canonical_json_digest(result.model_dump(mode="json")),
                result.result_id,
            ),
        )
    )
    return SemanticProjectionApplicableCoordinateModel(
        posture="applicable",
        coordinate_id="observed-proposition-truth-result-set/v1",
        coordinate_version="1",
        coordinate_digest=canonical_json_digest(
            {
                "coordinate_profile": "observed-proposition-truth-result-set/v1",
                "evaluation_cut_ref": evaluation_cut_ref,
                "results": [result.model_dump(mode="json") for result in ordered],
            }
        ),
        cut_ref=evaluation_cut_ref,
    )


def semantic_projection_transformation_coordinate(
    report: ArtifactTransformationReportModel,
) -> SemanticProjectionTransformationCoordinateModel:
    """Bind one view transformation coordinate to its complete owner report."""

    return SemanticProjectionTransformationCoordinateModel(
        transformation_id=report.operation_profile,
        transformation_version=report.schema_version,
        transformation_digest=canonical_json_digest(report.model_dump(mode="json")),
        status=report.status.value,
        artifact_kind=report.artifact_kind.value,
        source_profile=report.source_profile,
        target_profile=report.target_profile,
        canonicalization_profile=report.canonicalization_profile,
        source_digest=report.source_digest,
        target_digest=report.target_digest,
        policy_digest=report.policy_digest,
        derivation_digest=report.derivation_digest,
        preservation_profile=report.preservation.profile,
        preservation_outcome=report.preservation.outcome.value,
    )


def adapt_declared_semantic_projection_fact(subject: ExternalConceptSubjectModel) -> _SemanticProjectionFact:
    """Adapt one exact native declaration; its artifact is its replay evidence."""

    if subject.owning_contract_id != "sdl-authoring-input-v1":
        raise ValueError("declared projection subjects must be owned by the SDL authoring contract")
    return _SemanticProjectionFact(
        predicate_id="declared",
        producer_contract_id=subject.owning_contract_id,
        subject=subject,
        outcome="satisfied",
        native_result_id=subject.canonical_ref,
        native_result_digest=subject.artifact_digest,
        evidence_digests=(subject.artifact_digest,),
        evidence_refs=(subject.artifact_digest,),
        evidence_boundary_digest=None,
        owner_artifact=subject,
        owner_evidence=(),
    )


def adapt_admitted_semantic_projection_fact(
    subject: ExternalConceptSubjectModel,
    disclosure: ValidationBasisDisclosureDocumentModel,
) -> _SemanticProjectionFact:
    """Adapt one already validated admission disclosure without widening it."""

    digest = canonical_json_digest(disclosure.model_dump(mode="json"))
    owner = disclosure.disclosure
    if (
        subject.owning_contract_id != "validation-basis-disclosure-v1"
        or subject.subject_kind != owner.subject_kind
        or subject.canonical_ref != owner.subject_ref.ref_id
        or subject.artifact_digest != digest
    ):
        raise ValueError("admitted projection subject must identify the exact disclosure artifact and subject")
    if any(gate.outcome != "passed" for gate in owner.gate_results):
        raise ValueError("admitted projection facts require every governed validation gate to pass")
    return _SemanticProjectionFact(
        predicate_id="admitted",
        producer_contract_id="validation-basis-disclosure-v1",
        subject=subject,
        outcome="satisfied",
        native_result_id=f"{disclosure.disclosure.profile_id}:{disclosure.disclosure.subject_ref.ref_id}",
        native_result_digest=digest,
        evidence_digests=(digest,),
        evidence_refs=(digest,),
        evidence_boundary_digest=None,
        owner_artifact=disclosure,
        owner_evidence=(),
    )


def adapt_observed_semantic_projection_fact(
    subject: ExternalConceptSubjectModel,
    result: PropositionTruthResultModel,
    *,
    evidence_boundary: SemanticProjectionEvidenceBoundaryModel,
    evidence_resolver: SemanticProjectionEvidenceResolver,
) -> _SemanticProjectionFact:
    """Adapt one incumbent observed truth result and its resolved evidence digests."""

    if result.evaluation_basis != PropositionEvaluationBasis.OBSERVED_STATE:
        raise ValueError("observed projection facts require an observed-state proposition result")
    temporal = result.temporal_context
    if temporal is None or (
        temporal.boundary_ref,
        temporal.time_domain,
        temporal.clock_authority,
    ) != (
        evidence_boundary.evaluation_cut_ref,
        evidence_boundary.time_domain,
        evidence_boundary.clock_authority,
    ):
        raise ValueError("observed evidence temporal context must match the exact projection boundary")
    digest = canonical_json_digest(result.model_dump(mode="json"))
    if (
        subject.owning_contract_id != "proposition-truth-result-v1"
        or subject.subject_kind != "proposition-truth-result"
        or subject.canonical_ref != result.result_id
        or subject.artifact_digest != digest
    ):
        raise ValueError("observed projection subject must identify the exact proposition truth result")
    outcome = {
        PropositionTruthOutcome.TRUE: "satisfied",
        PropositionTruthOutcome.FALSE: "not-satisfied",
        PropositionTruthOutcome.UNKNOWN: "unknown",
        PropositionTruthOutcome.UNSUPPORTED: "unsupported",
    }[result.proposition_outcome]
    evidence_records, resolved_digests = _resolve_evidence_records(
        tuple(result.evidence_refs), evidence_boundary, evidence_resolver
    )
    if result.probe_binding is not None and not any(
        source.ref_digest == result.probe_binding.artifact_digest
        for record in evidence_records
        for source in record.source_refs
    ):
        raise ValueError("observed evidence provenance must join the exact owner probe artifact")
    if outcome in {"satisfied", "not-satisfied"} and not resolved_digests:
        raise ValueError("decided observed projection facts require digest-stable evidence")
    if resolved_digests != tuple(sorted(set(resolved_digests))):
        raise ValueError("observed projection evidence digests must be sorted and unique")
    return _SemanticProjectionFact(
        predicate_id="observed",
        producer_contract_id="proposition-truth-result-v1",
        subject=subject,
        outcome=outcome,
        native_result_id=result.result_id,
        native_result_digest=digest,
        evidence_digests=resolved_digests,
        evidence_refs=tuple(sorted(result.evidence_refs)),
        evidence_boundary_digest=canonical_json_digest(evidence_boundary.model_dump(mode="json")),
        owner_artifact=result,
        owner_evidence=evidence_records,
    )


def adapt_verified_semantic_projection_fact(
    subject: ExternalConceptSubjectModel,
    report: ArtifactTransformationReportModel,
    *,
    evidence_boundary: SemanticProjectionEvidenceBoundaryModel,
    predicate_profile: SemanticProjectionPredicateProfileModel,
    evidence_resolver: SemanticProjectionEvidenceResolver,
) -> _SemanticProjectionFact:
    """Adapt verified preservation; evidence-free verification is impossible."""

    if (
        report.operation_profile != "verify-semantic-predicate/v1"
        or report.preservation.profile != "semantic-predicate-witness/v1"
        or report.policy_digest != predicate_profile.profile_digest
        or report.status != ArtifactTransformationStatus.SUCCESS
        or report.preservation.outcome != PreservationOutcome.VERIFIED
        or not report.preservation.evidence_digests
    ):
        raise ValueError("verified projection facts require the governed predicate-specific verifier profile")
    digest = canonical_json_digest(report.model_dump(mode="json"))
    expected_ref = f"{report.operation_profile}:{report.derivation_digest}"
    if report.source_digest != subject.artifact_digest or subject.canonical_ref not in report.affected_identities:
        raise ValueError("verified projection must join the exact native subject and governed verifier result")
    evidence_records, evidence_digests = _resolve_evidence_records(
        tuple(report.preservation.evidence_digests),
        evidence_boundary,
        evidence_resolver,
        digest_addressed=True,
    )
    return _SemanticProjectionFact(
        predicate_id="verified",
        producer_contract_id="artifact-transformation-report-v1",
        subject=subject,
        outcome="satisfied",
        native_result_id=expected_ref,
        native_result_digest=digest,
        evidence_digests=evidence_digests,
        evidence_refs=tuple(report.preservation.evidence_digests),
        evidence_boundary_digest=canonical_json_digest(evidence_boundary.model_dump(mode="json")),
        owner_artifact=report,
        owner_evidence=evidence_records,
    )


def _resolve_evidence_records(
    refs: tuple[str, ...],
    boundary: SemanticProjectionEvidenceBoundaryModel,
    resolver: SemanticProjectionEvidenceResolver,
    *,
    digest_addressed: bool = False,
) -> tuple[tuple[ExperimentEvidenceRecordModel, ...], tuple[str, ...]]:
    records = []
    digests = []
    for evidence_ref in refs:
        try:
            record = resolver(evidence_ref=evidence_ref, evidence_boundary=boundary)
        except Exception as exc:
            raise ValueError("semantic projection evidence authority resolution failed") from exc
        if record is None:
            raise ValueError("semantic projection evidence ref did not resolve authoritatively")
        digest = canonical_json_digest(record.model_dump(mode="json"))
        if digest_addressed:
            if digest != evidence_ref:
                raise ValueError("verified evidence digest does not match its authoritative artifact")
        elif record.evidence_record_id != evidence_ref:
            raise ValueError("evidence resolver returned a different owner evidence record")
        if record.capture_window_ref != boundary.evaluation_cut_ref or record.redaction_state == "withheld":
            raise ValueError("evidence artifact is not admissible at the exact boundary and cut")
        records.append(record)
        digests.append(digest)
    ordered = tuple(sorted(zip(digests, records, strict=True), key=lambda item: item[0]))
    if len({digest for digest, _ in ordered}) != len(ordered):
        raise ValueError("semantic projection evidence artifacts must be unique")
    return tuple(record for _, record in ordered), tuple(digest for digest, _ in ordered)


def _revalidate_semantic_projection_fact(
    frame: SemanticProjectionFrameModel,
    fact: _SemanticProjectionFact,
    evidence_resolver: SemanticProjectionEvidenceResolver | None,
) -> None:
    """Re-run the fixed owner adapter so raw private facts cannot bypass trust joins."""

    if fact.predicate_id == "declared" and isinstance(fact.owner_artifact, ExternalConceptSubjectModel):
        expected = adapt_declared_semantic_projection_fact(fact.owner_artifact)
    elif fact.predicate_id == "admitted" and isinstance(fact.owner_artifact, ValidationBasisDisclosureDocumentModel):
        expected = adapt_admitted_semantic_projection_fact(fact.subject, fact.owner_artifact)
    elif fact.predicate_id == "observed" and isinstance(fact.owner_artifact, PropositionTruthResultModel):
        boundary = frame.evidence_boundary
        if not isinstance(boundary, SemanticProjectionEvidenceBoundaryModel):
            raise ValueError("observed projection requires one applicable evidence boundary")
        if evidence_resolver is None:
            raise ValueError("observed projection requires a trusted evidence authority resolver")
        expected = adapt_observed_semantic_projection_fact(
            fact.subject,
            fact.owner_artifact,
            evidence_boundary=boundary,
            evidence_resolver=evidence_resolver,
        )
    elif fact.predicate_id == "verified" and isinstance(fact.owner_artifact, ArtifactTransformationReportModel):
        boundary = frame.evidence_boundary
        if not isinstance(boundary, SemanticProjectionEvidenceBoundaryModel):
            raise ValueError("verified projection requires one applicable evidence boundary")
        if evidence_resolver is None:
            raise ValueError("verified projection requires a trusted evidence authority resolver")
        expected = adapt_verified_semantic_projection_fact(
            fact.subject,
            fact.owner_artifact,
            evidence_boundary=boundary,
            predicate_profile=frame.predicate_profile,
            evidence_resolver=evidence_resolver,
        )
    else:
        raise ValueError("projection fact lacks its authoritative owner artifact")
    if expected != fact:
        raise ValueError("projection fact does not match the fixed owner adapter output")


__all__ = [
    "adapt_admitted_semantic_projection_fact",
    "adapt_declared_semantic_projection_fact",
    "adapt_observed_semantic_projection_fact",
    "adapt_verified_semantic_projection_fact",
    "semantic_projection_declared_configuration_coordinate",
    "semantic_projection_observed_state_coordinate",
    "semantic_projection_transformation_coordinate",
]
