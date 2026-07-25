"""Time-indexed SEM-220 participant decision-surface projection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from raes_contracts.contracts import ParticipantDecisionSurfaceModel

from .behavior_anchor_checks import participant_observation_effective_relation
from .behavior_anchor_index import _participant_behavior_history_anchor_indexes
from .behavior_resources import (
    _PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS,
    ParticipantBehaviorSpecificationRuntime,
    ParticipantObservationBoundaryRuntime,
)
from .history_event import ParticipantBehaviorHistoryEvent
from .participant_exposure import project_participant_exposure_bindings
from .participant_exposure_authority import (
    ParticipantExposureAssessment,
    ParticipantExposureResolvers,
)
from .runtime_model import RuntimeModel


@dataclass(frozen=True)
class ParticipantDecisionSurfaceActionAssessment:
    """Order-scoped eligibility/support facts supplied by their owning gates."""

    action_contract_address: str
    presentation_basis_ref: str
    eligibility: str
    eligibility_reason_refs: tuple[str, ...]
    constraint_refs: tuple[str, ...]
    selection_shape_ref: str
    support: str
    support_refs: tuple[str, ...]
    realization_refs: tuple[str, ...]


@dataclass(frozen=True)
class ParticipantDecisionSurfaceProjectionInput:
    """Governed projection inputs that are not authored by the payload itself."""

    surface_id: str
    participant_address: str
    episode_id: str
    observation_order: int
    observation_point: str
    behavior_specification_address: str
    observation_boundary_address: str
    context_view_ref: str
    implementation_selection_ref: str
    decision_control_mode: str
    audience_scope_ref: str
    projection_policy_ref: str
    projection_policy_revision: str
    exposure_policy_ref: str
    visibility_projection_ref: str
    visible_context_refs: tuple[str, ...]
    action_assessments: Mapping[str, ParticipantDecisionSurfaceActionAssessment]
    exposure_assessments: Mapping[str, ParticipantExposureAssessment]
    form: Mapping[str, object]
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    marking_definition_refs: tuple[str, ...]
    redaction_policy_ref: str | None
    semantic_limitations: tuple[str, ...]


def _surface_action_addresses(form: Mapping[str, object]) -> tuple[str, ...]:
    surface_form = form.get("surface_form")
    if surface_form == "candidate_action_set":
        raw = form.get("candidate_entry_ids")
    elif surface_form == "constrained_form":
        raw = [form.get("action_entry_id")]
    elif surface_form == "open_ended_generation":
        raw = form.get("allowed_action_contract_addresses")
    else:
        raise ValueError(f"unsupported participant decision surface form {surface_form!r}")
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError("participant decision surface form must declare action references")
    addresses = tuple(item for item in raw if isinstance(item, str) and item)
    if len(addresses) != len(raw) or not addresses or len(set(addresses)) != len(addresses):
        raise ValueError("participant decision surface action references must be unique non-empty strings")
    return addresses


def _action_affordance_addresses(
    runtime_model: RuntimeModel,
    *,
    behavior_affordance_addresses: tuple[str, ...],
    action_address: str,
) -> tuple[str, ...]:
    return tuple(
        affordance_address
        for affordance_address in behavior_affordance_addresses
        if affordance_address in runtime_model.tool_affordances
        and action_address in runtime_model.tool_affordances[affordance_address].action_contract_addresses
    )


def _participant_visible_disposition(
    relation: Mapping[str, str],
    *,
    action_address: str,
    affordance_addresses: tuple[str, ...],
    observation_order: int,
) -> str:
    projected_refs = (action_address, *affordance_addresses)
    missing = sorted(ref for ref in projected_refs if ref not in relation)
    if missing:
        raise ValueError(
            "participant decision surface refs lack an effective view disposition at observation_order "
            f"{observation_order}: {', '.join(missing)}"
        )
    classified = {relation[ref] for ref in projected_refs}
    if len(classified) > 1:
        raise ValueError(
            f"action {action_address!r} has conflicting view dispositions at observation_order {observation_order}"
        )
    disposition = next(iter(classified), None)
    if disposition not in _PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS:
        raise ValueError(
            f"action {action_address!r} is not participant-visible at observation_order {observation_order}"
        )
    return disposition


def _validate_context_visibility(
    relation: Mapping[str, str],
    *,
    refs: tuple[str, ...],
    observation_order: int,
) -> None:
    hidden = sorted(ref for ref in refs if relation.get(ref) not in _PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS)
    if hidden:
        raise ValueError(
            "visible_context_refs are not participant-visible at observation_order "
            f"{observation_order}: {', '.join(hidden)}"
        )


def _validate_projection_history(
    history_events: Sequence[ParticipantBehaviorHistoryEvent],
    projection: ParticipantDecisionSurfaceProjectionInput,
) -> None:
    if not history_events:
        raise ValueError("participant decision surfaces require time-indexed history; a final snapshot is insufficient")
    if projection.observation_order < 0 or projection.observation_order >= len(history_events):
        raise ValueError("observation_order must identify an event in the supplied time-indexed history")
    if any(
        event.participant_address != projection.participant_address or event.episode_id != projection.episode_id
        for event in history_events
    ):
        raise ValueError("participant decision surface history must contain one participant and episode")


def _resolve_projection_scope(
    runtime_model: RuntimeModel,
    projection: ParticipantDecisionSurfaceProjectionInput,
) -> tuple[ParticipantBehaviorSpecificationRuntime, ParticipantObservationBoundaryRuntime]:
    behavior = runtime_model.behavior_specifications.get(projection.behavior_specification_address)
    if behavior is None:
        raise ValueError("behavior_specification_address does not resolve in the compiled runtime model")
    if projection.participant_address not in behavior.participant_addresses:
        raise ValueError("participant_address is outside the compiled behavior specification")
    if projection.observation_boundary_address not in behavior.observation_boundary_addresses:
        raise ValueError("observation_boundary_address is outside the compiled behavior specification")
    boundary = runtime_model.observation_boundaries.get(projection.observation_boundary_address)
    if boundary is None:
        raise ValueError("observation_boundary_address does not resolve in the compiled runtime model")
    return behavior, boundary


def _projection_visibility_relation(
    history_events: Sequence[ParticipantBehaviorHistoryEvent],
    projection: ParticipantDecisionSurfaceProjectionInput,
    boundary: ParticipantObservationBoundaryRuntime,
) -> Mapping[str, str]:
    action_attempts, state_transitions, observations = _participant_behavior_history_anchor_indexes(history_events)
    relation, _ = participant_observation_effective_relation(
        observation_index=projection.observation_order,
        boundary_address=projection.observation_boundary_address,
        boundary=boundary,
        action_attempts=action_attempts,
        state_transitions=state_transitions,
        observations=observations,
    )
    return relation


def _project_surface_action(
    runtime_model: RuntimeModel,
    behavior: ParticipantBehaviorSpecificationRuntime,
    relation: Mapping[str, str],
    projection: ParticipantDecisionSurfaceProjectionInput,
    action_address: str,
) -> tuple[dict[str, object], tuple[str, ...]]:
    if action_address not in behavior.action_contract_addresses:
        raise ValueError(f"action {action_address!r} is outside the compiled behavior specification")
    if action_address not in runtime_model.action_contracts:
        raise ValueError(f"action {action_address!r} does not resolve in the compiled runtime model")
    assessment = projection.action_assessments.get(action_address)
    if assessment is None or assessment.action_contract_address != action_address:
        raise ValueError(f"action {action_address!r} lacks a matching order-scoped assessment")
    affordance_addresses = _action_affordance_addresses(
        runtime_model,
        behavior_affordance_addresses=behavior.tool_affordance_addresses,
        action_address=action_address,
    )
    visibility = _participant_visible_disposition(
        relation,
        action_address=action_address,
        affordance_addresses=affordance_addresses,
        observation_order=projection.observation_order,
    )
    return (
        {
            "entry_id": action_address,
            "action_contract_address": action_address,
            "presentation_basis_ref": assessment.presentation_basis_ref,
            "visibility": visibility,
            "eligibility": assessment.eligibility,
            "eligibility_reason_refs": list(assessment.eligibility_reason_refs),
            "constraint_refs": list(assessment.constraint_refs),
            "selection_shape_ref": assessment.selection_shape_ref,
            "support": assessment.support,
            "support_refs": list(assessment.support_refs),
            "affordance_refs": list(affordance_addresses),
            "realization_refs": list(assessment.realization_refs),
        },
        affordance_addresses,
    )


def _project_surface_actions(
    runtime_model: RuntimeModel,
    behavior: ParticipantBehaviorSpecificationRuntime,
    relation: Mapping[str, str],
    projection: ParticipantDecisionSurfaceProjectionInput,
) -> tuple[list[dict[str, object]], list[str]]:
    entries: list[dict[str, object]] = []
    surface_affordances: list[str] = []
    for action_address in _surface_action_addresses(projection.form):
        entry, affordance_addresses = _project_surface_action(
            runtime_model,
            behavior,
            relation,
            projection,
            action_address,
        )
        entries.append(entry)
        surface_affordances.extend(affordance_addresses)
    return entries, surface_affordances


def _surface_payload(
    projection: ParticipantDecisionSurfaceProjectionInput,
    entries: list[dict[str, object]],
    surface_affordances: list[str],
    exposure_bindings: list[dict[str, object]],
) -> dict[str, object]:
    realization_evidence_refs = [
        ref
        for binding in exposure_bindings
        if isinstance(binding.get("realization"), dict)
        for ref in binding["realization"]["evidence_refs"]
    ]
    realization_provenance_refs = [
        ref
        for binding in exposure_bindings
        if isinstance(binding.get("realization"), dict)
        for ref in binding["realization"]["provenance_refs"]
    ]
    return {
        "surface_id": projection.surface_id,
        "participant_address": projection.participant_address,
        "episode_id": projection.episode_id,
        "observation_point": projection.observation_point,
        "observation_order": projection.observation_order,
        "behavior_specification_address": projection.behavior_specification_address,
        "observation_boundary_address": projection.observation_boundary_address,
        "context_view_ref": projection.context_view_ref,
        "implementation_selection_ref": projection.implementation_selection_ref,
        "decision_control_mode": projection.decision_control_mode,
        "audience_scope_ref": projection.audience_scope_ref,
        "projection_policy_ref": projection.projection_policy_ref,
        "projection_policy_revision": projection.projection_policy_revision,
        "exposure_policy_ref": projection.exposure_policy_ref,
        "visibility_projection_ref": projection.visibility_projection_ref,
        "visible_context_refs": list(projection.visible_context_refs),
        "action_entries": entries,
        "affordance_refs": list(dict.fromkeys(surface_affordances)),
        "exposure_bindings": exposure_bindings,
        "form": dict(projection.form),
        "evidence_refs": list(dict.fromkeys((*projection.evidence_refs, *realization_evidence_refs))),
        "provenance_refs": list(dict.fromkeys((*projection.provenance_refs, *realization_provenance_refs))),
        "marking_definition_refs": list(projection.marking_definition_refs),
        "redaction_policy_ref": projection.redaction_policy_ref,
        "semantic_limitations": list(projection.semantic_limitations),
    }


def project_participant_decision_surface(
    runtime_model: RuntimeModel,
    *,
    history_events: Sequence[ParticipantBehaviorHistoryEvent],
    projection: ParticipantDecisionSurfaceProjectionInput,
    exposure_resolvers: ParticipantExposureResolvers,
) -> ParticipantDecisionSurfaceModel:
    """Derive one surface from compiled meaning and one scoped history prefix."""

    _validate_projection_history(history_events, projection)
    behavior, boundary = _resolve_projection_scope(runtime_model, projection)
    relation = _projection_visibility_relation(history_events, projection, boundary)
    _validate_context_visibility(
        relation,
        refs=projection.visible_context_refs,
        observation_order=projection.observation_order,
    )
    entries, surface_affordances = _project_surface_actions(runtime_model, behavior, relation, projection)
    exposure_bindings = project_participant_exposure_bindings(
        relation,
        projection,
        entries,
        surface_affordances,
        history_events,
        exposure_resolvers,
    )
    return ParticipantDecisionSurfaceModel.model_validate(
        _surface_payload(projection, entries, surface_affordances, exposure_bindings)
    )
