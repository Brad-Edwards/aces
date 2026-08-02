"""Trusted contextual joins for portable SEM-233 flow-control relations."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..participant_flow_policy_profiles import (
    load_participant_boundary_flow_policy_profile_revision,
)
from .participant_control_validation import validate_participant_control_occurrence_context
from .participant_crossing import (
    ParticipantCrossingDecisionDisposition,
    ParticipantCrossingDecisionModel,
)
from .participant_crossing_validation import validate_participant_crossing_occurrence_context
from .participant_flow_control import (
    ParticipantBoundaryFlowPolicyProfileModel,
    ParticipantCrossingOccurrenceFlowBindingModel,
    ParticipantFlowControlRelationModel,
    ParticipantFlowFinalDisposition,
    ParticipantFlowLabelResolutionStatus,
    ParticipantFlowRelationTargetKind,
    ParticipantFlowSinkDecisionModel,
    participant_flow_coordinate_disposition,
)
from .participant_flow_control_context import (
    ParticipantFlowActionAdmissionResolution,
    ParticipantFlowCapabilityResolution,
    ParticipantFlowControlValidationContext,
    ParticipantFlowHistoryHeadResolution,
    ParticipantFlowReleaseAuthorityCoordinate,
    ParticipantFlowSinkCoordinate,
)
from .participant_flow_control_incumbent_validation import _validate_bindings
from .runtime_facts import RuntimeFactBindingPlaneModel

if TYPE_CHECKING:
    from ..participant_binding import ParticipantActionAdmissionRequest

ParticipantFlowControlContextResolver = Callable[
    [ParticipantFlowControlRelationModel, object | None],
    ParticipantFlowControlValidationContext | None,
]


def validate_participant_flow_control_resolved_context(
    document: ParticipantFlowControlRelationModel,
    resolver: ParticipantFlowControlContextResolver | None,
    scope: object | None = None,
) -> None:
    """Resolve trusted state and fail closed before accepting a relation document."""

    if resolver is None:
        raise ValueError("participant flow-control context resolver is required")
    try:
        context = resolver(document, scope)
    except Exception:
        raise ValueError("participant flow-control context resolution failed") from None
    if not isinstance(context, ParticipantFlowControlValidationContext):
        raise ValueError("participant flow-control context did not resolve")
    try:
        validate_participant_flow_control_context(document, context)
    except (TypeError, ValueError):
        raise
    except Exception:
        raise ValueError("participant flow-control context validation failed") from None


def validate_participant_flow_control_context(
    document: ParticipantFlowControlRelationModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    """Validate exact profile, incumbent carrier, authority, and sink joins."""

    profile = _resolve_profile(document, context)
    _validate_profile_tokens(document, profile)
    _validate_trusted_flow_coordinates(document, context)
    _validate_safe_references(document, context)
    _validate_incumbent_context(context)
    _validate_bindings(document, context)
    _validate_sink_context(document, context)


def _resolve_profile(
    document: ParticipantFlowControlRelationModel,
    context: ParticipantFlowControlValidationContext,
) -> ParticipantBoundaryFlowPolicyProfileModel:
    profile_ref = document.profile
    profile = context.profiles.get((profile_ref.profile_id, profile_ref.profile_revision))
    if not isinstance(profile, ParticipantBoundaryFlowPolicyProfileModel):
        raise ValueError("participant flow-control profile revision must resolve")
    published = load_participant_boundary_flow_policy_profile_revision(
        profile_ref.profile_id,
        profile_ref.profile_revision,
        profile_ref.profile_digest,
    )
    if profile != published or profile.authority_revision != profile_ref.authority_revision:
        raise ValueError("participant flow-control profile coordinates do not match published authority")
    return profile


def _validate_profile_tokens(
    document: ParticipantFlowControlRelationModel,
    profile: ParticipantBoundaryFlowPolicyProfileModel,
) -> None:
    confidentiality = set(profile.confidentiality_obligation_refs)
    integrity = set(profile.integrity_obligation_refs)
    for label in document.labels:
        if not set(label.confidentiality_obligation_refs).issubset(confidentiality):
            raise ValueError("flow label confidentiality obligation is outside the exact profile")
        if not set(label.integrity_obligation_refs).issubset(integrity):
            raise ValueError("flow label integrity obligation is outside the exact profile")
        has_unknowns = (
            profile.unknown_confidentiality_obligation_ref in label.confidentiality_obligation_refs
            and profile.unknown_integrity_obligation_ref in label.integrity_obligation_refs
        )
        if label.resolution_status == ParticipantFlowLabelResolutionStatus.RESOLVED and (
            profile.unknown_confidentiality_obligation_ref in label.confidentiality_obligation_refs
            or profile.unknown_integrity_obligation_ref in label.integrity_obligation_refs
        ):
            raise ValueError("resolved flow label cannot carry an unknown-profile obligation")
        if label.resolution_status != ParticipantFlowLabelResolutionStatus.RESOLVED and not has_unknowns:
            raise ValueError("unresolved flow label must carry both unknown-profile obligations")
    for release in document.releases:
        replacements = getattr(release, "integrity_obligation_replacements", ())
        if any(item.result_obligation_ref not in integrity for item in replacements):
            raise ValueError("endorsement result obligation is outside the exact profile")
    if any(
        (derivation.rule_ref, derivation.rule_revision)
        != (profile.derivation_rule.rule_ref, profile.derivation_rule.rule_revision)
        for derivation in document.derivations
    ):
        raise ValueError("participant flow-control derivation must use the exact profile derivation rule")


def _validate_safe_references(
    document: ParticipantFlowControlRelationModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    evidence_refs = {
        ref
        for records in (document.labels, document.derivations, document.releases, document.sink_decisions)
        for record in records
        for ref in record.evidence_refs
    }
    if not evidence_refs.issubset(context.known_evidence_refs):
        raise ValueError("participant flow-control evidence reference must resolve")


def _validate_trusted_flow_coordinates(
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

    produced_label_refs = {
        *(derivation.result_label_ref for derivation in document.derivations),
        *(release.result_label_ref for release in document.releases),
    }
    for label in document.labels:
        if label.label_id not in produced_label_refs and context.source_labels.get(label.label_id) != label:
            raise ValueError("participant flow-control trusted source label must resolve exactly")

    known_sinks = set(context.known_sinks)
    for release in document.releases:
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
        if not any(
            (
                sink.sink_ref,
                sink.destination_ref,
                sink.audience_scope_ref,
            )
            == (
                release.sink_ref,
                release.destination_ref,
                release.audience_scope_ref,
            )
            for sink in known_sinks
        ):
            raise ValueError("participant flow-control release sink must resolve exactly")

    if any(_decision_sink_coordinate(decision) not in known_sinks for decision in document.sink_decisions):
        raise ValueError("participant flow-control final sink must resolve exactly")


def _decision_sink_coordinate(
    decision: ParticipantFlowSinkDecisionModel,
) -> ParticipantFlowSinkCoordinate:
    return ParticipantFlowSinkCoordinate(
        sink_kind=decision.sink.sink_kind,
        sink_ref=decision.sink.sink_ref,
        destination_ref=decision.sink.destination_ref,
        audience_scope_ref=decision.sink.audience_scope_ref,
    )


def _validate_incumbent_context(context: ParticipantFlowControlValidationContext) -> None:
    from ..participant_action_arguments import ParticipantValidatedActionSelection
    from ..participant_binding import (
        ParticipantActionAdmissionRequest,
        participant_action_admission_request_violations,
    )

    if any(not isinstance(plane, RuntimeFactBindingPlaneModel) for plane in context.runtime_fact_planes.values()):
        raise ValueError("runtime fact binding plane context is invalid")
    if any(not isinstance(item, ParticipantValidatedActionSelection) for item in context.action_selections.values()):
        raise ValueError("participant action selection context is invalid")
    if any(not isinstance(item, ParticipantActionAdmissionRequest) for item in context.action_admissions.values()):
        raise ValueError("participant action admission context is invalid")
    for admission in context.action_admissions.values():
        if participant_action_admission_request_violations(admission):
            raise ValueError("participant action admission context is invalid")
    _validate_incumbent_sink_resolutions(context)
    validate_participant_control_occurrence_context(
        context.control_records,
        declarations=context.control_declarations,
        known_targets=context.control_known_targets,
    )
    validate_participant_crossing_occurrence_context(
        context.crossing_records,
        known_subjects=context.crossing_subjects,
        policies=context.crossing_policies,
        known_evidence_refs=context.known_evidence_refs,
        known_authority_basis_refs=context.known_authority_refs,
    )


def _validate_incumbent_sink_resolutions(context: ParticipantFlowControlValidationContext) -> None:
    for ref, resolution in context.action_admission_resolutions.items():
        if not isinstance(resolution, ParticipantFlowActionAdmissionResolution):
            raise ValueError("participant action admission resolution context is invalid")
        admission = context.action_admissions.get(ref)
        if (
            admission is None
            or ref != resolution.action_admission_ref
            or (
                admission.participant_address,
                admission.action_contract_address,
                admission.action_instance_id,
            )
            != (
                resolution.participant_address,
                resolution.action_contract_address,
                resolution.action_instance_id,
            )
        ):
            raise ValueError("participant action admission resolution coordinates do not match")
        _validate_sink_resolution_fields(
            resolution.participant_address,
            resolution.episode_id,
            resolution.sink,
            resolution.disposition,
            "participant action admission resolution",
        )

    for ref, resolution in context.capability_resolutions.items():
        if (
            not isinstance(resolution, ParticipantFlowCapabilityResolution)
            or ref != resolution.capability_resolution_ref
        ):
            raise ValueError("participant capability resolution context is invalid")
        _validate_sink_resolution_fields(
            resolution.participant_address,
            resolution.episode_id,
            resolution.sink,
            resolution.disposition,
            "participant capability resolution",
        )

    history_identities: set[tuple[str, str, ParticipantFlowSinkCoordinate, tuple[str, ...]]] = set()
    for resolution in context.history_head_resolutions:
        if not isinstance(resolution, ParticipantFlowHistoryHeadResolution):
            raise ValueError("participant history-head resolution context is invalid")
        _validate_sink_resolution_fields(
            resolution.participant_address,
            resolution.episode_id,
            resolution.sink,
            resolution.disposition,
            "participant history-head resolution",
        )
        if not resolution.history_head_refs or resolution.history_head_refs != tuple(
            sorted(set(resolution.history_head_refs))
        ):
            raise ValueError("participant history-head resolution refs must be non-empty and canonical")
        identity = (
            resolution.participant_address,
            resolution.episode_id,
            resolution.sink,
            resolution.history_head_refs,
        )
        if identity in history_identities:
            raise ValueError("participant history-head resolution identity was reused")
        history_identities.add(identity)


def _validate_sink_resolution_fields(
    participant_address: str,
    episode_id: str,
    sink: ParticipantFlowSinkCoordinate,
    disposition: ParticipantFlowFinalDisposition,
    label: str,
) -> None:
    if not participant_address or not episode_id or not isinstance(sink, ParticipantFlowSinkCoordinate):
        raise ValueError(f"{label} scope is invalid")
    if not isinstance(disposition, ParticipantFlowFinalDisposition):
        raise ValueError(f"{label} disposition is invalid")


def _validate_sink_context(
    document: ParticipantFlowControlRelationModel,
    context: ParticipantFlowControlValidationContext,
) -> None:
    from ..participant_binding import participant_action_admission_request_violations

    crossing_decisions = {
        item.occurrence.decision_id: item.occurrence
        for item in context.crossing_records
        if isinstance(item.occurrence, ParticipantCrossingDecisionModel)
    }
    crossing_bindings = {
        binding.stage_identity_ref: binding
        for binding in document.bindings
        if isinstance(binding, ParticipantCrossingOccurrenceFlowBindingModel)
        and binding.relation_target.target_kind == ParticipantFlowRelationTargetKind.SINK_DECISION
    }
    for decision in document.sink_decisions:
        admission = context.action_admissions.get(decision.action_admission_ref)
        if admission is None or participant_action_admission_request_violations(admission):
            raise ValueError("participant flow-control sink action admission must resolve")
        incumbent_dispositions = _resolve_sink_conjunct_dispositions(decision, admission, context)
        crossing = crossing_decisions.get(decision.api_423_decision_ref)
        binding = crossing_bindings.get(decision.api_423_decision_ref)
        if crossing is None or binding is None or binding.relation_target.target_ref != decision.decision_id:
            raise ValueError("participant flow-control sink API-423 decision must resolve")
        expected = _combined_final_disposition(
            participant_flow_coordinate_disposition(
                decision.confidentiality_result,
                decision.integrity_result,
            ),
            _crossing_final_disposition(crossing),
            *incumbent_dispositions,
        )
        if decision.final_disposition != expected:
            raise ValueError("participant flow-control sink must record the exact final disposition")


def _resolve_sink_conjunct_dispositions(
    decision: ParticipantFlowSinkDecisionModel,
    admission: ParticipantActionAdmissionRequest,
    context: ParticipantFlowControlValidationContext,
) -> tuple[ParticipantFlowFinalDisposition, ...]:
    sink = _decision_sink_coordinate(decision)
    scope = (decision.subject.participant_address, decision.subject.episode_id, sink)

    admission_resolution = context.action_admission_resolutions.get(decision.action_admission_ref)
    if (
        admission_resolution is None
        or (
            admission_resolution.participant_address,
            admission_resolution.episode_id,
            admission_resolution.sink,
        )
        != scope
        or (
            admission_resolution.action_contract_address,
            admission_resolution.action_instance_id,
        )
        != (admission.action_contract_address, admission.action_instance_id)
    ):
        raise ValueError("participant flow-control sink action admission must resolve exactly")

    capability_resolution = context.capability_resolutions.get(decision.capability_resolution_ref)
    if (
        capability_resolution is None
        or (
            capability_resolution.participant_address,
            capability_resolution.episode_id,
            capability_resolution.sink,
        )
        != scope
    ):
        raise ValueError("participant flow-control capability resolution must resolve exactly")

    history_resolution = next(
        (
            resolution
            for resolution in context.history_head_resolutions
            if (
                resolution.participant_address,
                resolution.episode_id,
                resolution.sink,
                resolution.history_head_refs,
            )
            == (*scope, decision.expected_history_head_refs)
        ),
        None,
    )
    if history_resolution is None:
        raise ValueError("participant flow-control expected history head must resolve exactly")

    return (
        admission_resolution.disposition,
        capability_resolution.disposition,
        history_resolution.disposition,
    )


def _crossing_final_disposition(
    decision: ParticipantCrossingDecisionModel,
) -> ParticipantFlowFinalDisposition:
    if decision.disposition not in {
        ParticipantCrossingDecisionDisposition.PERMIT,
        ParticipantCrossingDecisionDisposition.TRANSFORM,
    }:
        if decision.disposition == ParticipantCrossingDecisionDisposition.UNSUPPORTED:
            return ParticipantFlowFinalDisposition.UNSUPPORTED
        return ParticipantFlowFinalDisposition.DENY
    return ParticipantFlowFinalDisposition.PERMIT


def _combined_final_disposition(
    *dispositions: ParticipantFlowFinalDisposition,
) -> ParticipantFlowFinalDisposition:
    values = set(dispositions)
    for disposition in (
        ParticipantFlowFinalDisposition.DENY,
        ParticipantFlowFinalDisposition.UNSUPPORTED,
        ParticipantFlowFinalDisposition.STALE,
        ParticipantFlowFinalDisposition.UNRESOLVED,
    ):
        if disposition in values:
            return disposition
    return ParticipantFlowFinalDisposition.PERMIT


__all__ = [
    "ParticipantFlowActionAdmissionResolution",
    "ParticipantFlowCapabilityResolution",
    "ParticipantFlowControlContextResolver",
    "ParticipantFlowControlValidationContext",
    "ParticipantFlowHistoryHeadResolution",
    "ParticipantFlowReleaseAuthorityCoordinate",
    "ParticipantFlowSinkCoordinate",
    "validate_participant_flow_control_context",
    "validate_participant_flow_control_resolved_context",
]
