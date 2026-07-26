"""Exact-cut participant decision-surface v2 binding DTOs."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, cast

from .contracts import (
    ParticipantDecisionSurfaceCandidateSetFormModel,
    ParticipantDecisionSurfaceConstrainedFormModel,
    ParticipantDecisionSurfaceSelectionV2Model,
    ParticipantDecisionSurfaceV2Model,
    ParticipantImplementationSelectionModel,
)
from .participant_action_arguments import ParticipantValidatedActionSelection
from .participant_binding import (
    ParticipantActionAdmissionRequest,
    ParticipantDecisionSurfaceArgumentShapeResolver,
    participant_action_admission_request_violations,
)
from .participant_decision_surface_delivery import (
    ParticipantDecisionSurfaceDeliveryResolverV2,
    validate_participant_decision_surface_v2_delivery,
)


class ParticipantDecisionSurfaceApparatusResolverV2(Protocol):
    """Resolve the run selection at the exact cut used to derive a v2 surface."""

    def __call__(
        self,
        *,
        implementation_selection_ref: str,
        exposure_policy_ref: str,
        decision_cut_ref: str,
    ) -> ParticipantImplementationSelectionModel | None: ...


@dataclass(frozen=True)
class ParticipantDecisionSurfaceBindingResolversV2:
    """Governed dependencies for a delivered v2 surface selection."""

    argument_shape: ParticipantDecisionSurfaceArgumentShapeResolver
    apparatus: ParticipantDecisionSurfaceApparatusResolverV2
    delivery: ParticipantDecisionSurfaceDeliveryResolverV2


def bind_participant_decision_surface_selection_v2(
    *,
    surface: ParticipantDecisionSurfaceV2Model,
    selection: ParticipantDecisionSurfaceSelectionV2Model,
    admission_request: ParticipantActionAdmissionRequest,
    argument_shape_resolver: ParticipantDecisionSurfaceArgumentShapeResolver,
    apparatus_resolver: ParticipantDecisionSurfaceApparatusResolverV2,
    delivery_resolver: ParticipantDecisionSurfaceDeliveryResolverV2,
) -> ParticipantActionAdmissionRequest:
    """Validate a selection from an exact, currently delivered v2 view."""

    validate_participant_decision_surface_v2_delivery(surface, delivery_resolver)
    view = surface.participant_view
    assurance = surface.assurance
    delivery = surface.delivery
    assert delivery is not None
    if selection.surface_id != view.surface_id:
        raise ValueError("selection surface_id must match the participant decision surface")
    if selection.decision_epoch != view.decision_epoch:
        raise ValueError("selection decision_epoch must match the participant decision surface")
    if selection.participant_view_digest != assurance.participant_view_digest:
        raise ValueError("selection participant_view_digest must match the canonical participant view")
    if selection.delivery_ref != delivery.delivery_ref:
        raise ValueError("selection delivery_ref must match the authoritative surface delivery")
    entries = {entry.action_contract_address: entry for entry in view.action_entries}
    entry = entries.get(selection.action_contract_address)
    if entry is None:
        raise ValueError("selection action_contract_address is not carried by the participant decision surface")
    if entry.eligibility != "eligible":
        raise ValueError("participant decision surface selection is not eligible")
    if entry.support != "supported":
        raise ValueError("participant decision surface selection is not supported")
    if entry.selection_shape_ref != selection.argument_shape_ref:
        raise ValueError("selection argument_shape_ref must match the participant decision surface action entry")
    if isinstance(view.form, ParticipantDecisionSurfaceCandidateSetFormModel):
        if entry.entry_id not in view.form.candidate_entry_ids:
            raise ValueError("selection action is not a member of the participant candidate-action set")
    elif isinstance(view.form, ParticipantDecisionSurfaceConstrainedFormModel):
        if entry.entry_id != view.form.action_entry_id or selection.argument_shape_ref != view.form.argument_shape_ref:
            raise ValueError("selection does not match the constrained-form action and argument shape")
    else:
        if selection.action_contract_address not in view.form.allowed_action_contract_addresses:
            raise ValueError("open-ended proposal does not bind to an allowed governed action contract")
        if selection.argument_shape_ref != view.form.argument_shape_ref:
            raise ValueError("open-ended proposal does not bind to the governed argument shape")
    if admission_request.participant_address != view.participant_address:
        raise ValueError("admission request participant_address must match the participant decision surface")
    if admission_request.action_contract_address != selection.action_contract_address:
        raise ValueError("admission request action_contract_address must match the validated selection")
    if admission_request.observation_boundary_address != assurance.observation_boundary_address:
        raise ValueError("admission request observation_boundary_address must match the participant decision surface")
    if admission_request.implementation_selection.selected_decision_surface_mode != view.decision_control_mode:
        raise ValueError("admission request decision-control mode must match the participant decision surface")
    if (
        "participant-decision-surface-v2"
        not in admission_request.implementation_selection.participant_contract_versions
    ):
        raise ValueError("participant implementation selection must declare participant-decision-surface-v2 support")
    try:
        resolved_selection = apparatus_resolver(
            implementation_selection_ref=assurance.implementation_selection_ref,
            exposure_policy_ref=assurance.exposure_policy_ref,
            decision_cut_ref=assurance.derivation_anchor.state_cut.cut_ref,
        )
    except Exception as exc:
        raise ValueError("participant decision surface exact-cut apparatus resolution failed") from exc
    if resolved_selection is None:
        raise ValueError("participant decision surface apparatus refs did not resolve at the derivation cut")
    if resolved_selection.model_dump(mode="json") != admission_request.implementation_selection.model_dump(mode="json"):
        raise ValueError("admission request implementation selection and exposure policy must match the surface refs")
    try:
        validated_selection = argument_shape_resolver(
            action_contract_address=selection.action_contract_address,
            argument_shape_ref=selection.argument_shape_ref,
            proposal_ref=selection.proposal_ref,
            proposed_arguments=selection.arguments,
        )
    except Exception as exc:
        raise ValueError("participant decision surface argument-shape resolution failed") from exc
    if not isinstance(validated_selection, ParticipantValidatedActionSelection):
        raise ValueError("participant decision surface proposal failed governed argument-shape validation")
    if (
        validated_selection.action_contract_address,
        validated_selection.argument_shape_ref,
        validated_selection.proposal_ref,
    ) != (
        selection.action_contract_address,
        selection.argument_shape_ref,
        selection.proposal_ref,
    ):
        raise ValueError("validated participant action selection must match the governed proposal coordinates")
    bound_request = cast(
        ParticipantActionAdmissionRequest,
        replace(admission_request, validated_selection=validated_selection),
    )
    violations = participant_action_admission_request_violations(bound_request)
    if violations:
        raise ValueError(violations[0])
    return bound_request


__all__ = (
    "ParticipantDecisionSurfaceApparatusResolverV2",
    "ParticipantDecisionSurfaceBindingResolversV2",
    "bind_participant_decision_surface_selection_v2",
)
