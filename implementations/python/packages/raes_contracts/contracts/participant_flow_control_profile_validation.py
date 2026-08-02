"""Profile-token and trusted-coordinate validators for SEM-233 flow control."""

from __future__ import annotations

from .participant_flow_control import (
    ParticipantBoundaryFlowPolicyProfileModel,
    ParticipantEffectiveFlowLabelModel,
    ParticipantFlowControlRelationModel,
    ParticipantFlowDerivationModel,
    ParticipantFlowLabelResolutionStatus,
    ParticipantFlowRelease,
    ParticipantFlowSinkDecisionModel,
)
from .participant_flow_control_context import (
    ParticipantFlowControlValidationContext,
    ParticipantFlowReleaseAuthorityCoordinate,
    ParticipantFlowSinkCoordinate,
)


def validate_profile_tokens(
    document: ParticipantFlowControlRelationModel,
    profile: ParticipantBoundaryFlowPolicyProfileModel,
) -> None:
    """Validate every profile-governed token and derivation rule coordinate."""

    confidentiality = set(profile.confidentiality_obligation_refs)
    integrity = set(profile.integrity_obligation_refs)
    for label in document.labels:
        _validate_label_profile_tokens(label, profile, confidentiality, integrity)
    for release in document.releases:
        _validate_release_profile_tokens(release, integrity)
    for derivation in document.derivations:
        _validate_derivation_profile_rule(derivation, profile)


def _validate_label_profile_tokens(
    label: ParticipantEffectiveFlowLabelModel,
    profile: ParticipantBoundaryFlowPolicyProfileModel,
    confidentiality: set[str],
    integrity: set[str],
) -> None:
    if not set(label.confidentiality_obligation_refs).issubset(confidentiality):
        raise ValueError("flow label confidentiality obligation is outside the exact profile")
    if not set(label.integrity_obligation_refs).issubset(integrity):
        raise ValueError("flow label integrity obligation is outside the exact profile")
    unknown_confidentiality = profile.unknown_confidentiality_obligation_ref in label.confidentiality_obligation_refs
    unknown_integrity = profile.unknown_integrity_obligation_ref in label.integrity_obligation_refs
    if label.resolution_status == ParticipantFlowLabelResolutionStatus.RESOLVED and (
        unknown_confidentiality or unknown_integrity
    ):
        raise ValueError("resolved flow label cannot carry an unknown-profile obligation")
    if label.resolution_status != ParticipantFlowLabelResolutionStatus.RESOLVED and not (
        unknown_confidentiality and unknown_integrity
    ):
        raise ValueError("unresolved flow label must carry both unknown-profile obligations")


def _validate_release_profile_tokens(release: ParticipantFlowRelease, integrity: set[str]) -> None:
    replacements = getattr(release, "integrity_obligation_replacements", ())
    if any(item.result_obligation_ref not in integrity for item in replacements):
        raise ValueError("endorsement result obligation is outside the exact profile")


def _validate_derivation_profile_rule(
    derivation: ParticipantFlowDerivationModel,
    profile: ParticipantBoundaryFlowPolicyProfileModel,
) -> None:
    expected = (profile.derivation_rule.rule_ref, profile.derivation_rule.rule_revision)
    if (derivation.rule_ref, derivation.rule_revision) != expected:
        raise ValueError("participant flow-control derivation must use the exact profile derivation rule")


def validate_safe_references(
    document: ParticipantFlowControlRelationModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    """Require all evidence references to resolve in the trusted context."""

    evidence_refs = {
        ref
        for records in (document.labels, document.derivations, document.releases, document.sink_decisions)
        for record in records
        for ref in record.evidence_refs
    }
    if not evidence_refs.issubset(context.known_evidence_refs):
        raise ValueError("participant flow-control evidence reference must resolve")


def validate_trusted_flow_coordinates(
    document: ParticipantFlowControlRelationModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    """Join relation records to exact trusted policy, source, authority, and sink state."""

    _validate_trusted_policy_cuts(document, context)
    _validate_trusted_source_labels(document, context)
    known_release_sinks = {
        (sink.sink_ref, sink.destination_ref, sink.audience_scope_ref) for sink in context.known_sinks
    }
    for release in document.releases:
        _validate_trusted_release(release, context, known_release_sinks)
    known_sinks = set(context.known_sinks)
    if any(_decision_sink_coordinate(decision) not in known_sinks for decision in document.sink_decisions):
        raise ValueError("participant flow-control final sink must resolve exactly")


def _validate_trusted_policy_cuts(
    document: ParticipantFlowControlRelationModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    policy_records = (
        *document.labels,
        *document.derivations,
        *document.releases,
        *document.sink_decisions,
        *document.bindings,
    )
    for record in policy_records:
        if context.policy_cuts.get(record.policy.decision_cut_ref) != record.policy:
            raise ValueError("participant flow-control trusted policy cut must resolve exactly")


def _validate_trusted_source_labels(
    document: ParticipantFlowControlRelationModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    produced_label_refs = {
        *(derivation.result_label_ref for derivation in document.derivations),
        *(release.result_label_ref for release in document.releases),
    }
    for label in document.labels:
        if label.label_id not in produced_label_refs and context.source_labels.get(label.label_id) != label:
            raise ValueError("participant flow-control trusted source label must resolve exactly")


def _validate_trusted_release(
    release: ParticipantFlowRelease,
    context: ParticipantFlowControlValidationContext,
    known_sinks: set[tuple[str, str, str]],
) -> None:
    authority = ParticipantFlowReleaseAuthorityCoordinate(
        kind=release.kind,
        authority_basis_ref=release.authority_basis_ref,
        authority_revision=release.authority_revision,
        sink_ref=release.sink_ref,
        destination_ref=release.destination_ref,
        audience_scope_ref=release.audience_scope_ref,
    )
    if authority not in context.release_authorities:
        raise ValueError("participant flow-control exact release authority must resolve")
    if release.authority_basis_ref not in context.known_authority_refs:
        raise ValueError("participant flow-control release authority must resolve")
    sink = (release.sink_ref, release.destination_ref, release.audience_scope_ref)
    if sink not in known_sinks:
        raise ValueError("participant flow-control release sink must resolve exactly")


def _decision_sink_coordinate(decision: ParticipantFlowSinkDecisionModel) -> ParticipantFlowSinkCoordinate:
    return ParticipantFlowSinkCoordinate(
        sink_kind=decision.sink.sink_kind,
        sink_ref=decision.sink.sink_ref,
        destination_ref=decision.sink.destination_ref,
        audience_scope_ref=decision.sink.audience_scope_ref,
    )
