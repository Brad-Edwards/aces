"""Pure offline scheme-neutral semantic projection over admitted bindings."""

from __future__ import annotations

from collections import Counter

from .canonical import canonical_json_digest
from .contracts.artifact_transformations import ArtifactTransformationReportModel
from .contracts.execution_state import PropositionTruthResultModel
from .contracts.external_concept_bindings import (
    ExternalConceptApproximationPosture,
    ExternalConceptBindingAssertionModel,
    ExternalConceptBindingDocumentModel,
    ExternalConceptReviewStatus,
    ExternalConceptSubjectModel,
)
from .contracts.semantic_projection import (
    SemanticProjectionBindingObservationModel,
    SemanticProjectionClassification,
    SemanticProjectionEvidenceBoundaryModel,
    SemanticProjectionFrameModel,
    SemanticProjectionReportModel,
    SemanticProjectionRowModel,
    SemanticProjectionSummaryModel,
    canonical_semantic_projection_frame_digest,
)
from .external_concept_bindings import (
    ExternalConceptBindingAdmissionReport,
    ExternalConceptResolutionOutcome,
    ExternalConceptSchemeSnapshotModel,
    admit_external_concept_bindings,
)
from .semantic_projection_facts import (
    SemanticProjectionEvidenceResolver,
    _revalidate_semantic_projection_fact,
    _SemanticProjectionFact,
    adapt_admitted_semantic_projection_fact,
    adapt_declared_semantic_projection_fact,
    adapt_observed_semantic_projection_fact,
    adapt_verified_semantic_projection_fact,
    semantic_projection_declared_configuration_coordinate,
    semantic_projection_observed_state_coordinate,
    semantic_projection_transformation_coordinate,
)
from .semantic_projection_quantification import quantified_projection_row

_EXPECTED_PROFILE_BINDINGS = {
    "admitted": ("validation-basis-disclosure-v1", "admitted-owner-adapter"),
    "observed": ("proposition-truth-result-v1", "observed-owner-adapter"),
    "verified": ("artifact-transformation-report-v1", "verified-owner-adapter"),
}


def project_semantic_concepts(
    frame: SemanticProjectionFrameModel,
    *,
    document: ExternalConceptBindingDocumentModel,
    subjects: tuple[ExternalConceptSubjectModel, ...],
    scheme_snapshot: ExternalConceptSchemeSnapshotModel,
    native_facts: tuple[_SemanticProjectionFact, ...],
    evidence_resolver: SemanticProjectionEvidenceResolver | None = None,
) -> SemanticProjectionReportModel:
    """Project governed native results onto one exact external-scheme frame."""

    if frame.perspective.perspective_kind == "participant":
        raise ValueError(
            "participant-visible projection must be authorized and emitted by the incumbent exposure-policy service"
        )
    _validate_inputs(frame, document, subjects, scheme_snapshot, native_facts, evidence_resolver)
    admission = admit_external_concept_bindings(
        document,
        subjects=subjects,
        scheme_snapshots=(scheme_snapshot,),
    )
    selected_facts = tuple(
        fact
        for fact in native_facts
        if fact.predicate_id == frame.predicate_profile.predicate_id
        and fact.producer_contract_id == frame.predicate_profile.producer_contract_id
    )
    rows = tuple(
        _classify_concept(
            concept_id,
            included=concept_id in frame.scheme.included_concept_ids,
            frame=frame,
            document=document,
            admission=admission,
            facts=selected_facts,
            subjects=subjects,
        )
        for concept_id in sorted({term.concept_id for term in scheme_snapshot.concepts})
    )
    frame_digest = canonical_semantic_projection_frame_digest(frame)
    counts = Counter(row.classification for row in rows)
    denominator = len(frame.scheme.included_concept_ids)
    witness_count = counts[SemanticProjectionClassification.WITNESS]
    report = SemanticProjectionReportModel(
        frame=frame,
        frame_digest=frame_digest,
        rows=rows,
        summary=SemanticProjectionSummaryModel(
            predicate_id=frame.predicate_profile.predicate_id,
            predicate_profile_digest=frame.predicate_profile.profile_digest,
            frame_digest=frame_digest,
            included_denominator=denominator,
            witness_count=witness_count,
            gap_count=counts[SemanticProjectionClassification.GAP],
            unknown_count=counts[SemanticProjectionClassification.UNKNOWN],
            ambiguous_count=counts[SemanticProjectionClassification.AMBIGUOUS],
            excluded_count=counts[SemanticProjectionClassification.EXCLUDED],
            qualified_fraction=(f"{frame.predicate_profile.predicate_id}:{witness_count}/{denominator}@{frame_digest}"),
        ),
    )
    _validate_semantic_projection_report_context(report, scheme_snapshot)
    return report


def _validate_inputs(
    frame: SemanticProjectionFrameModel,
    document: ExternalConceptBindingDocumentModel,
    subjects: tuple[ExternalConceptSubjectModel, ...],
    snapshot: ExternalConceptSchemeSnapshotModel,
    facts: tuple[_SemanticProjectionFact, ...],
    evidence_resolver: SemanticProjectionEvidenceResolver | None,
) -> None:
    _validate_predicate_profile(frame)
    _validate_binding_coordinate(frame, document)
    _validate_scheme_coordinate(frame, snapshot)
    _validate_subject_scope(frame, subjects)
    _validate_projection_facts(frame, subjects, facts, evidence_resolver)
    _validate_context_authorities(frame, subjects, facts)


def _validate_predicate_profile(frame: SemanticProjectionFrameModel) -> None:
    predicate_id = frame.predicate_profile.predicate_id
    expected_producer, expected_adapter = _EXPECTED_PROFILE_BINDINGS.get(
        predicate_id,
        (frame.subject_scope.owning_contract_id, "declared-owner-adapter"),
    )
    if (frame.predicate_profile.producer_contract_id, frame.predicate_profile.adapter_id) != (
        expected_producer,
        expected_adapter,
    ):
        raise ValueError("predicate profile must bind the trusted owner contract and fixed adapter")


def _validate_binding_coordinate(
    frame: SemanticProjectionFrameModel,
    document: ExternalConceptBindingDocumentModel,
) -> None:
    if frame.binding.binding_set_digest != canonical_json_digest(document.model_dump(mode="json")):
        raise ValueError("projection binding-set digest does not match the supplied binding document")
    actual = (frame.binding.schema_version, frame.binding.binding_set_id, frame.binding.binding_set_version)
    expected = (document.schema_version, document.binding_set_id, document.binding_set_version)
    if actual != expected:
        raise ValueError("projection binding coordinate does not match the supplied binding document")


def _validate_scheme_coordinate(
    frame: SemanticProjectionFrameModel,
    snapshot: ExternalConceptSchemeSnapshotModel,
) -> None:
    actual = (
        frame.scheme.scheme_id,
        frame.scheme.authority,
        frame.scheme.revision,
        frame.scheme.source_digest.casefold(),
    )
    expected = (
        snapshot.scheme_id,
        snapshot.authority,
        snapshot.revision,
        snapshot.source_digest.casefold(),
    )
    if actual != expected:
        raise ValueError("projection scheme coordinate does not match the exact supplied snapshot")
    available_concepts = {term.concept_id for term in snapshot.concepts}
    if not set(frame.scheme.included_concept_ids).issubset(available_concepts):
        raise ValueError("projection inclusion set contains a concept absent from the exact snapshot")


def _validate_subject_scope(
    frame: SemanticProjectionFrameModel,
    subjects: tuple[ExternalConceptSubjectModel, ...],
) -> None:
    if not subjects:
        raise ValueError("projection requires an explicit finite native subject scope")
    expected_scope = (
        frame.subject_scope.subject_kind,
        frame.subject_scope.owning_contract_id,
        frame.subject_scope.lifecycle_phase,
    )
    actual_scopes = {
        (subject.subject_kind, subject.owning_contract_id, subject.lifecycle_phase) for subject in subjects
    }
    if actual_scopes != {expected_scope}:
        raise ValueError("supplied subjects must share the exact frame subject kind, owner, and lifecycle")
    supplied_digests = tuple(sorted({subject.artifact_digest for subject in subjects}))
    if supplied_digests != frame.subject_scope.artifact_digests:
        raise ValueError("supplied subject artifacts must exactly match the digest-stable frame scope")


def _validate_projection_facts(
    frame: SemanticProjectionFrameModel,
    subjects: tuple[ExternalConceptSubjectModel, ...],
    facts: tuple[_SemanticProjectionFact, ...],
    evidence_resolver: SemanticProjectionEvidenceResolver | None,
) -> None:
    if any(fact.subject not in subjects for fact in facts):
        raise ValueError("native projection facts must bind exact subjects from the declared finite scope")
    for fact in facts:
        _revalidate_semantic_projection_fact(frame, fact, evidence_resolver)


def _validate_context_authorities(
    frame: SemanticProjectionFrameModel,
    subjects: tuple[ExternalConceptSubjectModel, ...],
    facts: tuple[_SemanticProjectionFact, ...],
) -> None:
    predicate_id = frame.predicate_profile.predicate_id
    selected_facts = tuple(fact for fact in facts if fact.predicate_id == predicate_id)
    if predicate_id == "declared":
        _validate_declared_context(frame, subjects)
    elif predicate_id == "observed":
        _validate_observed_context(frame, selected_facts)
    elif predicate_id == "verified":
        _validate_verified_context(frame, selected_facts)


def _validate_declared_context(
    frame: SemanticProjectionFrameModel,
    subjects: tuple[ExternalConceptSubjectModel, ...],
) -> None:
    expected = semantic_projection_declared_configuration_coordinate(subjects)
    if frame.configuration != expected:
        raise ValueError("declared configuration coordinate must join the exact native subject scope")


def _validate_observed_context(
    frame: SemanticProjectionFrameModel,
    facts: tuple[_SemanticProjectionFact, ...],
) -> None:
    boundary = frame.evidence_boundary
    if not isinstance(boundary, SemanticProjectionEvidenceBoundaryModel):
        raise ValueError("observed state coordinate requires one applicable evidence boundary")
    results = tuple(
        fact.owner_artifact for fact in facts if isinstance(fact.owner_artifact, PropositionTruthResultModel)
    )
    expected = semantic_projection_observed_state_coordinate(
        results,
        evaluation_cut_ref=boundary.evaluation_cut_ref,
    )
    if frame.state != expected:
        raise ValueError("observed state coordinate must join the exact proposition truth result set")


def _validate_verified_context(
    frame: SemanticProjectionFrameModel,
    facts: tuple[_SemanticProjectionFact, ...],
) -> None:
    reports = tuple(
        fact.owner_artifact for fact in facts if isinstance(fact.owner_artifact, ArtifactTransformationReportModel)
    )
    expected = tuple(
        sorted(
            (semantic_projection_transformation_coordinate(report) for report in reports),
            key=lambda item: (
                item.transformation_id,
                item.transformation_version,
                item.transformation_digest,
            ),
        )
    )
    if frame.transformations != expected:
        raise ValueError("verified transformation coordinates must join the exact owner reports")


def _validate_semantic_projection_report_context(
    report: SemanticProjectionReportModel,
    snapshot: ExternalConceptSchemeSnapshotModel,
) -> None:
    """Validate joins that require the exact external scheme authority artifact."""

    expected = tuple(sorted({term.concept_id for term in snapshot.concepts}))
    actual = tuple(row.concept_id for row in report.rows)
    if actual != expected:
        raise ValueError("projection rows must exactly partition the supplied pinned scheme snapshot")


def _classify_concept(
    concept_id: str,
    *,
    included: bool,
    frame: SemanticProjectionFrameModel,
    document: ExternalConceptBindingDocumentModel,
    admission: ExternalConceptBindingAdmissionReport,
    facts: tuple[_SemanticProjectionFact, ...],
    subjects: tuple[ExternalConceptSubjectModel, ...],
) -> SemanticProjectionRowModel:
    observations = _binding_observations(concept_id, document, admission)
    if not included:
        row = _excluded_row(concept_id, observations)
    elif any(item.resolution_outcome == ExternalConceptResolutionOutcome.AMBIGUOUS.value for item in observations):
        row = _non_witness_row(
            concept_id, SemanticProjectionClassification.AMBIGUOUS, observations, "ambiguous-binding"
        )
    else:
        row = _classify_resolved_concept(concept_id, frame, observations, document, facts, subjects)
    return row


def _excluded_row(
    concept_id: str,
    observations: tuple[SemanticProjectionBindingObservationModel, ...],
) -> SemanticProjectionRowModel:
    return SemanticProjectionRowModel(
        concept_id=concept_id,
        classification=SemanticProjectionClassification.EXCLUDED,
        bindings=observations,
        witnesses=(),
        reason_codes=("outside-explicit-inclusion-set",),
    )


def _classify_resolved_concept(
    concept_id: str,
    frame: SemanticProjectionFrameModel,
    observations: tuple[SemanticProjectionBindingObservationModel, ...],
    document: ExternalConceptBindingDocumentModel,
    facts: tuple[_SemanticProjectionFact, ...],
    subjects: tuple[ExternalConceptSubjectModel, ...],
) -> SemanticProjectionRowModel:
    active = tuple(
        document.bindings[item.binding_id]
        for item in observations
        if item.resolution_outcome == ExternalConceptResolutionOutcome.RESOLVED_CURRENT.value
    )
    if not active:
        reason = observations[0].resolution_outcome if observations else "binding-missing"
        row = _non_witness_row(concept_id, SemanticProjectionClassification.UNKNOWN, observations, reason)
    else:
        eligible, limitation_reasons = _eligible_bindings(frame, active)
        if not eligible:
            row = SemanticProjectionRowModel(
                concept_id=concept_id,
                classification=SemanticProjectionClassification.UNKNOWN,
                bindings=observations,
                witnesses=(),
                reason_codes=tuple(sorted(limitation_reasons)),
            )
        else:
            all_bindings = tuple(
                binding for binding in document.bindings.values() if binding.scheme.concept_id == concept_id
            )
            row = quantified_projection_row(concept_id, frame, observations, all_bindings, eligible, facts, subjects)
    return row


def _binding_observations(
    concept_id: str,
    document: ExternalConceptBindingDocumentModel,
    admission: ExternalConceptBindingAdmissionReport,
) -> tuple[SemanticProjectionBindingObservationModel, ...]:
    resolutions = {item.binding_id: item for item in admission.results}
    observations = []
    for binding_id, binding in sorted(document.bindings.items()):
        if binding.scheme.concept_id != concept_id:
            continue
        resolution = resolutions[binding_id]
        observations.append(
            SemanticProjectionBindingObservationModel(
                binding_id=binding_id,
                resolution_outcome=resolution.outcome.value,
                relationship_kind=binding.assertion.relationship_kind.value,
                semantic_effect=binding.assertion.semantic_effect.value,
                confidence_posture=binding.confidence.posture.value,
                approximation_posture=binding.approximation.posture.value,
                loss_details=tuple(sorted(binding.approximation.loss_details)),
                limitations=tuple(sorted(binding.limitations)),
                review_status=binding.review.status.value,
            )
        )
    return tuple(observations)


def _eligible_bindings(
    frame: SemanticProjectionFrameModel,
    bindings: tuple[ExternalConceptBindingAssertionModel, ...],
) -> tuple[tuple[ExternalConceptBindingAssertionModel, ...], set[str]]:
    eligible = []
    reasons: set[str] = set()
    for binding in bindings:
        posture = binding.approximation.posture
        if (
            posture == ExternalConceptApproximationPosture.APPROXIMATE
            and not frame.predicate_profile.allow_approximate_bindings
        ):
            reasons.add("approximate-binding-not-admitted")
            continue
        if posture == ExternalConceptApproximationPosture.LOSSY and not frame.predicate_profile.allow_lossy_bindings:
            reasons.add("lossy-binding-not-admitted")
            continue
        if binding.review.status in {ExternalConceptReviewStatus.REJECTED, ExternalConceptReviewStatus.SUPERSEDED}:
            reasons.add("binding-review-not-admitted")
            continue
        eligible.append(binding)
    return tuple(eligible), reasons


def _non_witness_row(
    concept_id: str,
    classification: SemanticProjectionClassification,
    observations: tuple[SemanticProjectionBindingObservationModel, ...],
    reason: str,
) -> SemanticProjectionRowModel:
    return SemanticProjectionRowModel(
        concept_id=concept_id,
        classification=classification,
        bindings=observations,
        witnesses=(),
        reason_codes=(reason,),
    )


__all__ = [
    "adapt_admitted_semantic_projection_fact",
    "adapt_declared_semantic_projection_fact",
    "adapt_observed_semantic_projection_fact",
    "adapt_verified_semantic_projection_fact",
    "project_semantic_concepts",
    "semantic_projection_declared_configuration_coordinate",
    "semantic_projection_observed_state_coordinate",
    "semantic_projection_transformation_coordinate",
]
