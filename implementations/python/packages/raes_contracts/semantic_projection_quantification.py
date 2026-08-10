"""Finite quantification for semantic projection report rows."""

from __future__ import annotations

from .contracts.external_concept_bindings import (
    ExternalConceptBindingAssertionModel,
    ExternalConceptSubjectModel,
)
from .contracts.semantic_projection import (
    SemanticProjectionBindingObservationModel,
    SemanticProjectionClassification,
    SemanticProjectionFrameModel,
    SemanticProjectionRowModel,
    SemanticProjectionWitnessModel,
)
from .semantic_projection_facts import _SemanticProjectionFact


def quantified_projection_row(
    concept_id: str,
    frame: SemanticProjectionFrameModel,
    observations: tuple[SemanticProjectionBindingObservationModel, ...],
    all_bindings: tuple[ExternalConceptBindingAssertionModel, ...],
    bindings: tuple[ExternalConceptBindingAssertionModel, ...],
    facts: tuple[_SemanticProjectionFact, ...],
    subjects: tuple[ExternalConceptSubjectModel, ...],
) -> SemanticProjectionRowModel:
    units = _quantified_units(frame, all_bindings, bindings, facts, subjects)
    threshold = frame.quantifier.threshold
    if frame.quantifier.kind == "threshold" and threshold is not None and threshold > len(units):
        raise ValueError("projection threshold cannot exceed the exact finite quantified population")
    if any(len({fact.outcome for fact in unit_facts}) > 1 for unit_facts in units.values()):
        return SemanticProjectionRowModel(
            concept_id=concept_id,
            classification=SemanticProjectionClassification.AMBIGUOUS,
            bindings=observations,
            witnesses=(),
            reason_codes=("ambiguous-native-result-join",),
        )
    satisfied, not_satisfied, unknown = _unit_outcome_counts(units)
    classification = _quantified_classification(frame, len(units), satisfied, not_satisfied, unknown)
    witnesses = _projection_witnesses(frame, bindings, facts)
    return SemanticProjectionRowModel(
        concept_id=concept_id,
        classification=classification,
        bindings=observations,
        witnesses=witnesses if classification == SemanticProjectionClassification.WITNESS else (),
        reason_codes=_projection_reason_codes(classification),
    )


def _quantified_units(
    frame: SemanticProjectionFrameModel,
    all_bindings: tuple[ExternalConceptBindingAssertionModel, ...],
    bindings: tuple[ExternalConceptBindingAssertionModel, ...],
    facts: tuple[_SemanticProjectionFact, ...],
    subjects: tuple[ExternalConceptSubjectModel, ...],
) -> dict[object, list[_SemanticProjectionFact]]:
    units: dict[object, list[_SemanticProjectionFact]] = {}
    if frame.quantifier.quantified_unit == "distinct-native-subjects":
        units.update({_subject_key(subject): [] for subject in subjects})
    else:
        units.update({(binding.binding_id, _subject_key(binding.subject)): [] for binding in all_bindings})
    for binding in bindings:
        subject_key = _subject_key(binding.subject)
        key: object = (
            subject_key
            if frame.quantifier.quantified_unit == "distinct-native-subjects"
            else (binding.binding_id, subject_key)
        )
        units.setdefault(key, []).extend(fact for fact in facts if fact.subject == binding.subject)
    return units


def _unit_outcome_counts(
    units: dict[object, list[_SemanticProjectionFact]],
) -> tuple[int, int, int]:
    unit_outcomes = [unit_facts[0].outcome if unit_facts else "unknown" for unit_facts in units.values()]
    satisfied = sum(outcome == "satisfied" for outcome in unit_outcomes)
    not_satisfied = sum(outcome == "not-satisfied" for outcome in unit_outcomes)
    unknown = len(unit_outcomes) - satisfied - not_satisfied
    return satisfied, not_satisfied, unknown


def _projection_witnesses(
    frame: SemanticProjectionFrameModel,
    bindings: tuple[ExternalConceptBindingAssertionModel, ...],
    facts: tuple[_SemanticProjectionFact, ...],
) -> tuple[SemanticProjectionWitnessModel, ...]:
    return tuple(
        sorted(
            (
                SemanticProjectionWitnessModel(
                    subject=fact.subject,
                    native_result_id=fact.native_result_id,
                    native_result_digest=fact.native_result_digest,
                    producer_contract_id=fact.producer_contract_id,
                    predicate_profile_digest=frame.predicate_profile.profile_digest,
                    evidence_digests=fact.evidence_digests,
                )
                for fact in facts
                if fact.outcome == "satisfied" and any(fact.subject == binding.subject for binding in bindings)
            ),
            key=lambda item: (
                item.subject.canonical_ref,
                item.subject.artifact_digest,
                item.native_result_id,
                item.native_result_digest,
            ),
        )
    )


def _projection_reason_codes(
    classification: SemanticProjectionClassification,
) -> tuple[str, ...]:
    if classification == SemanticProjectionClassification.GAP:
        return ("decisive-native-negative",)
    if classification == SemanticProjectionClassification.WITNESS:
        return ()
    return ("native-result-undecidable",)


def _subject_key(subject: ExternalConceptSubjectModel) -> tuple[str, str, str, str, str]:
    return (
        subject.subject_kind,
        subject.owning_contract_id,
        subject.lifecycle_phase.value,
        subject.canonical_ref,
        subject.artifact_digest,
    )


def _quantified_classification(
    frame: SemanticProjectionFrameModel,
    population: int,
    satisfied: int,
    not_satisfied: int,
    unknown: int,
) -> SemanticProjectionClassification:
    if not population:
        classification = SemanticProjectionClassification.UNKNOWN
    elif frame.quantifier.kind == "existential":
        classification = _existential_classification(frame, population, satisfied, not_satisfied)
    elif frame.quantifier.kind == "universal":
        classification = _universal_classification(frame, population, satisfied, not_satisfied)
    else:
        classification = _threshold_classification(frame, satisfied, unknown)
    return classification


def _existential_classification(
    frame: SemanticProjectionFrameModel,
    population: int,
    satisfied: int,
    not_satisfied: int,
) -> SemanticProjectionClassification:
    classification = SemanticProjectionClassification.UNKNOWN
    if satisfied:
        classification = SemanticProjectionClassification.WITNESS
    elif frame.subject_scope.complete and not_satisfied == population:
        classification = SemanticProjectionClassification.GAP
    return classification


def _universal_classification(
    frame: SemanticProjectionFrameModel,
    population: int,
    satisfied: int,
    not_satisfied: int,
) -> SemanticProjectionClassification:
    classification = SemanticProjectionClassification.UNKNOWN
    if satisfied == population:
        classification = SemanticProjectionClassification.WITNESS
    elif frame.subject_scope.complete and not_satisfied:
        classification = SemanticProjectionClassification.GAP
    return classification


def _threshold_classification(
    frame: SemanticProjectionFrameModel,
    satisfied: int,
    unknown: int,
) -> SemanticProjectionClassification:
    threshold = frame.quantifier.threshold
    assert threshold is not None
    classification = SemanticProjectionClassification.UNKNOWN
    if satisfied >= threshold:
        classification = SemanticProjectionClassification.WITNESS
    elif frame.subject_scope.complete and satisfied + unknown < threshold:
        classification = SemanticProjectionClassification.GAP
    return classification


__all__ = ["quantified_projection_row"]
