"""Focused graph validators for SEM-233 participant flow-control relations."""

from __future__ import annotations

from .participant_flow_control_semantics import (
    FlowSubjectKey,
    ParticipantEffectiveFlowLabelModel,
    ParticipantFlowDeclassificationModel,
    ParticipantFlowDerivationInputModel,
    ParticipantFlowDerivationModel,
    ParticipantFlowEndorsementModel,
    ParticipantFlowLabelResolutionStatus,
    ParticipantFlowRelease,
    ParticipantFlowSinkDecisionModel,
    ParticipantFlowSubjectReferenceModel,
)


def validate_derivation(
    derivation: ParticipantFlowDerivationModel,
    labels: dict[str, ParticipantEffectiveFlowLabelModel],
) -> tuple[set[FlowSubjectKey], FlowSubjectKey]:
    """Validate one conservative join and return its graph edge coordinates."""

    inputs = [_resolve_label_input(item, labels) for item in derivation.inputs]
    result = _resolve_label(derivation.result_label_ref, labels)
    if derivation.policy != result.policy or any(derivation.policy != item.policy for item in inputs):
        raise ValueError("derivation inputs and result must use its exact policy and cut")
    if result.subject != derivation.result_subject:
        raise ValueError("derivation result label subject must match its fresh result subject")
    input_keys = {_subject_key(item.subject) for item in derivation.inputs}
    result_key = _subject_key(derivation.result_subject)
    if result_key in input_keys:
        raise ValueError("derivation requires a fresh result identity")
    _validate_derivation_obligations(inputs, result)
    _validate_derivation_resolution(inputs, result)
    _validate_derivation_lineage(derivation, inputs, result)
    return input_keys, result_key


def _validate_derivation_obligations(
    inputs: list[ParticipantEffectiveFlowLabelModel],
    result: ParticipantEffectiveFlowLabelModel,
) -> None:
    expected_confidentiality = set().union(*(set(item.confidentiality_obligation_refs) for item in inputs))
    expected_integrity = set().union(*(set(item.integrity_obligation_refs) for item in inputs))
    if (
        set(result.confidentiality_obligation_refs) != expected_confidentiality
        or set(result.integrity_obligation_refs) != expected_integrity
    ):
        raise ValueError("derivation result must equal the coordinate-wise union of all possible inputs")


def _validate_derivation_resolution(
    inputs: list[ParticipantEffectiveFlowLabelModel],
    result: ParticipantEffectiveFlowLabelModel,
) -> None:
    has_unresolved_input = any(
        item.resolution_status != ParticipantFlowLabelResolutionStatus.RESOLVED for item in inputs
    )
    if has_unresolved_input and result.resolution_status == ParticipantFlowLabelResolutionStatus.RESOLVED:
        raise ValueError("derivation with an unresolved input cannot produce a resolved label")


def _validate_derivation_lineage(
    derivation: ParticipantFlowDerivationModel,
    inputs: list[ParticipantEffectiveFlowLabelModel],
    result: ParticipantEffectiveFlowLabelModel,
) -> None:
    required_provenance = set(derivation.provenance_refs).union(*(set(item.provenance_refs) for item in inputs))
    if not required_provenance.issubset(result.provenance_refs):
        raise ValueError("derivation result must conservatively retain complete provenance")
    required_influence = (
        set(derivation.influence_refs)
        | {item.subject.subject_ref for item in derivation.inputs}
        | set().union(*(set(item.influence_refs) for item in inputs))
    )
    if not required_influence.issubset(result.influence_refs):
        raise ValueError("derivation result must conservatively retain complete influence")


def validate_release(
    release: ParticipantFlowRelease,
    labels: dict[str, ParticipantEffectiveFlowLabelModel],
) -> None:
    """Validate one exact declassification or endorsement transition."""

    source = _resolve_label(release.source_label_ref, labels)
    result = _resolve_label(release.result_label_ref, labels)
    if _subject_key(release.source_subject) == _subject_key(release.result_subject):
        raise ValueError("release requires a fresh result identity")
    if source.subject != release.source_subject or result.subject != release.result_subject:
        raise ValueError("release source and result labels must match their exact subjects")
    if release.policy != source.policy or release.policy != result.policy:
        raise ValueError("release policy and cut must match its source and result labels")
    _validate_release_resolution(source, result)
    _validate_release_lineage(source, result)
    if isinstance(release, ParticipantFlowDeclassificationModel):
        _validate_declassification(release, source, result)
    else:
        _validate_endorsement(release, source, result)


def _validate_release_resolution(
    source: ParticipantEffectiveFlowLabelModel,
    result: ParticipantEffectiveFlowLabelModel,
) -> None:
    if (
        source.resolution_status != ParticipantFlowLabelResolutionStatus.RESOLVED
        and result.resolution_status == ParticipantFlowLabelResolutionStatus.RESOLVED
    ):
        raise ValueError("release with an unresolved source cannot produce a resolved label")


def _validate_release_lineage(
    source: ParticipantEffectiveFlowLabelModel,
    result: ParticipantEffectiveFlowLabelModel,
) -> None:
    if not set(source.provenance_refs).issubset(result.provenance_refs):
        raise ValueError("release result must preserve source provenance")
    required_influence = set(source.influence_refs) | {source.subject.subject_ref}
    if not required_influence.issubset(result.influence_refs):
        raise ValueError("release result must preserve source influence")


def _validate_declassification(
    release: ParticipantFlowDeclassificationModel,
    source: ParticipantEffectiveFlowLabelModel,
    result: ParticipantEffectiveFlowLabelModel,
) -> None:
    removed = set(release.removed_confidentiality_obligation_refs)
    if not removed.issubset(source.confidentiality_obligation_refs):
        raise ValueError("declassification can remove only present confidentiality obligations")
    if set(result.confidentiality_obligation_refs) != set(source.confidentiality_obligation_refs) - removed:
        raise ValueError("declassification result must encode the exact confidentiality delta")
    if result.integrity_obligation_refs != source.integrity_obligation_refs:
        raise ValueError("declassification must leave the integrity coordinate unchanged")


def _validate_endorsement(
    release: ParticipantFlowEndorsementModel,
    source: ParticipantEffectiveFlowLabelModel,
    result: ParticipantEffectiveFlowLabelModel,
) -> None:
    replacements = release.integrity_obligation_replacements
    removed = {item.source_obligation_ref for item in replacements}
    added = {item.result_obligation_ref for item in replacements}
    if not removed.issubset(source.integrity_obligation_refs):
        raise ValueError("endorsement can replace only present integrity obligations")
    if set(result.integrity_obligation_refs) != set(source.integrity_obligation_refs) - removed | added:
        raise ValueError("endorsement result must encode the exact integrity delta")
    if result.confidentiality_obligation_refs != source.confidentiality_obligation_refs:
        raise ValueError("endorsement must leave the confidentiality coordinate unchanged")


def validate_sink_decision(
    decision: ParticipantFlowSinkDecisionModel,
    labels: dict[str, ParticipantEffectiveFlowLabelModel],
    releases: dict[str, ParticipantFlowRelease],
) -> None:
    """Validate an ordered release lineage terminating at one exact sink label."""

    label = _resolve_label(decision.label_ref, labels)
    if label.subject != decision.subject or label.policy != decision.policy:
        raise ValueError("sink decision must bind its exact effective label and policy cut")
    decision_releases = _resolve_decision_releases(decision, releases)
    _validate_decision_release_lineage(decision, decision_releases)


def _resolve_decision_releases(
    decision: ParticipantFlowSinkDecisionModel,
    releases: dict[str, ParticipantFlowRelease],
) -> list[ParticipantFlowRelease]:
    resolved: list[ParticipantFlowRelease] = []
    sink_coordinates = (
        decision.sink.sink_ref,
        decision.sink.destination_ref,
        decision.sink.audience_scope_ref,
    )
    for release_ref in decision.release_refs:
        release = releases.get(release_ref)
        if release is None:
            raise ValueError("sink decision release reference must resolve")
        if (release.sink_ref, release.destination_ref, release.audience_scope_ref) != sink_coordinates:
            raise ValueError("sink decision releases must bind the exact final sink")
        resolved.append(release)
    return resolved


def _validate_decision_release_lineage(
    decision: ParticipantFlowSinkDecisionModel,
    releases: list[ParticipantFlowRelease],
) -> None:
    for prior, successor in zip(releases, releases[1:], strict=False):
        if prior.result_label_ref != successor.source_label_ref:
            raise ValueError("sink decision releases must form one ordered label lineage")
    if releases and releases[-1].result_label_ref != decision.label_ref:
        raise ValueError("sink decision release lineage must end at the selected label")


def _resolve_label(
    label_ref: str,
    labels: dict[str, ParticipantEffectiveFlowLabelModel],
) -> ParticipantEffectiveFlowLabelModel:
    label = labels.get(label_ref)
    if label is None:
        raise ValueError("flow label reference must resolve")
    return label


def _resolve_label_input(
    item: ParticipantFlowDerivationInputModel,
    labels: dict[str, ParticipantEffectiveFlowLabelModel],
) -> ParticipantEffectiveFlowLabelModel:
    label = _resolve_label(item.label_ref, labels)
    if label.subject != item.subject:
        raise ValueError("derivation input label must match its exact subject")
    return label


def _subject_key(subject: ParticipantFlowSubjectReferenceModel) -> FlowSubjectKey:
    return (
        subject.subject_kind,
        subject.subject_ref,
        subject.subject_revision,
        subject.participant_address,
        subject.episode_id,
    )
