"""Deny-first, time-indexed SEM-226 participant exposure selection."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from aces_contracts.contracts import ParticipantExposurePolicyModel
from aces_contracts.participant_behavior import ParticipantBehaviorHistoryEventType

from .behavior_resources import _PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS
from .history_event import ParticipantBehaviorHistoryEvent
from .participant_exposure_authority import (
    ParticipantExposureApparatusResolver,
    ParticipantExposureAssessment,
    ParticipantExposureAuthorizationRecord,
    ParticipantExposureAuthorizationResolver,
    ParticipantExposureOccurrenceRecord,
    ParticipantExposurePolicyRevision,
    ParticipantExposureProjection,
    ParticipantExposureProjectionPolicyResolver,
    ParticipantExposureResolvers,
)


def _resolved_projection_policy_revisions(
    projection: ParticipantExposureProjection,
    resolver: ParticipantExposureProjectionPolicyResolver,
) -> tuple[ParticipantExposurePolicyRevision, ...]:
    try:
        revisions = tuple(
            resolver(
                projection_policy_ref=projection.projection_policy_ref,
                participant_address=projection.participant_address,
                audience_scope_ref=projection.audience_scope_ref,
            )
        )
    except Exception as exc:
        raise ValueError("participant exposure projection-policy resolution failed") from exc
    if not revisions:
        raise ValueError("participant exposure requires an authoritative projection policy sequence")
    if any(revision.policy_ref != projection.projection_policy_ref for revision in revisions):
        raise ValueError("projection policy resolver returned a revision for a different policy")
    orders = [revision.effective_order for revision in revisions]
    if len(orders) != len(set(orders)):
        raise ValueError("projection policy revisions must have unique effective_order values")
    return revisions


def _effective_projection_policy(
    revisions: Sequence[ParticipantExposurePolicyRevision],
    *,
    observation_order: int,
    expected_revision: str,
) -> ParticipantExposurePolicyRevision:
    eligible = [revision for revision in revisions if revision.effective_order <= observation_order]
    if not eligible:
        raise ValueError("no projection policy revision is effective at observation_order")
    effective = max(eligible, key=lambda revision: revision.effective_order)
    if effective.revision != expected_revision:
        raise ValueError("surface projection policy must match the revision effective at observation_order")
    return effective


def _selected_exposure_policy(
    projection: ParticipantExposureProjection,
    resolver: ParticipantExposureApparatusResolver,
    *,
    observation_order: int,
) -> ParticipantExposurePolicyModel:
    try:
        selection = resolver(
            implementation_selection_ref=projection.implementation_selection_ref,
            exposure_policy_ref=projection.exposure_policy_ref,
            observation_order=observation_order,
        )
    except Exception as exc:
        raise ValueError("participant exposure apparatus resolution failed") from exc
    if selection is None:
        raise ValueError("participant exposure apparatus refs did not resolve")
    if selection.participant_address != projection.participant_address:
        raise ValueError("implementation selection participant_address must match the exposure projection")
    if selection.selected_decision_surface_mode != projection.decision_control_mode:
        raise ValueError("implementation selection decision-surface mode must match the exposure projection")
    policy = selection.exposure_policy
    if policy.policy_id != projection.exposure_policy_ref:
        raise ValueError("selected exposure policy identity must match exposure_policy_ref")
    if policy.policy_version is None or policy.policy_digest is None:
        raise ValueError("selected exposure policy requires an explicit version and digest")
    return policy


def _serialized_surface_refs(
    projection: ParticipantExposureProjection,
    entries: list[dict[str, object]],
    surface_affordances: list[str],
) -> set[str]:
    return {
        *projection.visible_context_refs,
        *(str(entry["action_contract_address"]) for entry in entries),
        *surface_affordances,
    }


def _resolve_authorization(
    *,
    authorization_record_ref: str,
    item_ref: str,
    resolver: ParticipantExposureAuthorizationResolver,
) -> ParticipantExposureAuthorizationRecord:
    if not item_ref or not authorization_record_ref:
        raise ValueError("participant exposure assessment requires item and authorization record refs")
    try:
        authorization = resolver(
            authorization_record_ref=authorization_record_ref,
            item_ref=item_ref,
        )
    except Exception as exc:
        raise ValueError("participant exposure authorization resolution failed") from exc
    if authorization is None:
        raise ValueError(f"exposure item {item_ref!r} has no authoritative authorization")
    if authorization.authorization_record_ref != authorization_record_ref:
        raise ValueError("exposure authorization resolver returned a different record")
    if authorization.item_ref != item_ref:
        raise ValueError("exposure authorization record item_ref does not match the requested item")
    return authorization


def _validate_authorization_scope(
    authorization: ParticipantExposureAuthorizationRecord,
    projection: ParticipantExposureProjection,
    policy: ParticipantExposurePolicyModel,
    *,
    observation_order: int,
    projection_policy_revision: str,
) -> None:
    exact_coordinates = {
        "participant_address": projection.participant_address,
        "episode_id": projection.episode_id,
        "audience_scope_ref": projection.audience_scope_ref,
        "implementation_selection_ref": projection.implementation_selection_ref,
        "projection_policy_ref": projection.projection_policy_ref,
        "projection_policy_revision": projection_policy_revision,
        "exposure_policy_ref": projection.exposure_policy_ref,
        "exposure_policy_version": policy.policy_version,
        "exposure_policy_digest": policy.policy_digest,
    }
    mismatches = sorted(
        field_name
        for field_name, expected in exact_coordinates.items()
        if getattr(authorization, field_name) != expected
    )
    if mismatches:
        raise ValueError(
            f"exposure authorization {authorization.item_ref!r} has mismatched coordinates: " + ", ".join(mismatches)
        )
    if authorization.effective_from_order > observation_order or (
        authorization.effective_through_order is not None and observation_order > authorization.effective_through_order
    ):
        raise ValueError(f"exposure authorization {authorization.item_ref!r} is not effective at observation_order")


def _validate_authorization_shape(authorization: ParticipantExposureAuthorizationRecord) -> None:
    required_strings = {
        "authorization_record_ref": authorization.authorization_record_ref,
        "item_ref": authorization.item_ref,
        "source_ref": authorization.source_ref,
        "source_layer_ref": authorization.source_layer_ref,
        "visibility_basis_ref": authorization.visibility_basis_ref,
        "operation_basis_ref": authorization.operation_basis_ref,
        "actor_ref": authorization.actor_ref,
        "controller_ref": authorization.controller_ref,
        "authority_basis_ref": authorization.authority_basis_ref,
        "backend_support_ref": authorization.backend_support_ref,
        "exposure_policy_version": authorization.exposure_policy_version,
        "exposure_policy_digest": authorization.exposure_policy_digest,
    }
    missing = sorted(name for name, value in required_strings.items() if not isinstance(value, str) or not value)
    if missing:
        raise ValueError("participant exposure authorization requires non-empty refs: " + ", ".join(missing))
    for field_name in (
        "source_marking_definition_refs",
        "result_marking_definition_refs",
        "source_provenance_refs",
        "result_provenance_refs",
        "evidence_refs",
        "provenance_refs",
        "loss_and_limitations",
    ):
        values = getattr(authorization, field_name)
        if field_name in {"evidence_refs", "provenance_refs", "loss_and_limitations"} and not values:
            raise ValueError(f"exposure authorization {authorization.item_ref!r} requires {field_name}")
        if len(values) != len(set(values)) or any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"exposure authorization {authorization.item_ref!r} has invalid {field_name}")


def _validate_exposure_operation(authorization: ParticipantExposureAuthorizationRecord) -> None:
    emitted_operations = {"projection", "masking", "redaction", "declassification", "disclosure", "transformation"}
    if authorization.operation not in emitted_operations:
        raise ValueError(f"exposure authorization {authorization.item_ref!r} operation cannot emit a surface item")
    if authorization.source_ref != authorization.item_ref and authorization.transformation_rule_ref is None:
        raise ValueError(f"derived exposure item {authorization.item_ref!r} requires a transformation rule")
    if (
        authorization.operation in {"masking", "redaction", "transformation"}
        and authorization.transformation_rule_ref is None
    ):
        raise ValueError(f"{authorization.operation} exposure operation requires a transformation rule")
    if authorization.operation == "redaction" and authorization.redaction_policy_ref is None:
        raise ValueError("redaction exposure operation requires a redaction policy")
    if authorization.operation == "declassification" and authorization.declassification_basis_ref is None:
        raise ValueError("declassification exposure operation requires a declassification basis")
    if authorization.declassification_basis_ref is None and not set(
        authorization.source_marking_definition_refs
    ).issubset(authorization.result_marking_definition_refs):
        raise ValueError("derived exposure results must inherit source markings unless declassification is explicit")
    if authorization.declassification_basis_ref is None and not set(authorization.source_provenance_refs).issubset(
        authorization.result_provenance_refs
    ):
        raise ValueError("derived exposure results must inherit source provenance unless declassification is explicit")
    if not {*authorization.source_provenance_refs, *authorization.result_provenance_refs}.issubset(
        authorization.provenance_refs
    ):
        raise ValueError("source and result exposure provenance must be carried by provenance_refs")


def _event_evidence_refs(event: ParticipantBehaviorHistoryEvent) -> tuple[str, ...]:
    refs: list[str] = []
    details = event.details.get("evidence_refs")
    if not isinstance(details, (str, bytes, Mapping)) and isinstance(details, Iterable):
        refs.extend(ref for ref in details if isinstance(ref, str) and ref)
    if event.action_result is not None:
        refs.extend(event.action_result.evidence_refs)
        for precondition in event.action_result.preconditions:
            refs.extend(precondition.evidence_refs)
        for effect in event.action_result.effects:
            refs.extend(effect.evidence_refs)
    for edge in event.attribution_edges:
        refs.extend(edge.evidence_refs)
    return tuple(dict.fromkeys(refs))


def _observation_ref(event: ParticipantBehaviorHistoryEvent) -> str:
    return f"participant-observation:{event.participant_address}:{event.episode_id}:{event.action_instance_id}"


def _occurrence_ref(event: ParticipantBehaviorHistoryEvent, delivery_order: int) -> str:
    return f"{_observation_ref(event)}:order-{delivery_order}"


def _policy_permits_item(policy: ParticipantExposurePolicyModel, item_ref: str) -> bool:
    allowed_refs = {*policy.disclosed_refs, *policy.tool_affordance_refs, *policy.visibility_scope_refs}
    return item_ref not in policy.withheld_refs and item_ref in allowed_refs


def _validate_realized_exposure(
    assessment: ParticipantExposureAssessment,
    projection: ParticipantExposureProjection,
    history_events: Sequence[ParticipantBehaviorHistoryEvent],
    policy_revisions: Sequence[ParticipantExposurePolicyRevision],
    resolvers: ParticipantExposureResolvers,
) -> ParticipantExposureOccurrenceRecord | None:
    realization = assessment.realization
    if realization is None:
        return None
    if not realization.occurrence_ref:
        raise ValueError("realized exposure requires an occurrence_ref")
    try:
        occurrence = resolvers.occurrence(occurrence_ref=realization.occurrence_ref)
    except Exception as exc:
        raise ValueError("realized exposure occurrence resolution failed") from exc
    if occurrence is None or occurrence.occurrence_ref != realization.occurrence_ref:
        raise ValueError("realized exposure occurrence_ref did not resolve")
    if occurrence.item_ref != assessment.item_ref:
        raise ValueError("realized exposure occurrence item_ref must match the exposed item")
    if occurrence.delivery_order < 0 or occurrence.delivery_order > projection.observation_order:
        raise ValueError("realized exposure delivery_order must identify an occurrence at or before the surface")
    matching_events = tuple(
        event
        for event in history_events
        if event.event_type == ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED
        and event.participant_address == occurrence.participant_address
        and event.episode_id == occurrence.episode_id
        and event.action_instance_id == occurrence.action_instance_id
        and event.observation_boundary_address == occurrence.observation_boundary_address
    )
    if len(matching_events) != 1:
        raise ValueError("realized exposure must resolve to an observation history occurrence")
    event = matching_events[0]
    delivery_authorization = _resolve_authorization(
        authorization_record_ref=occurrence.authorization_record_ref,
        item_ref=occurrence.item_ref,
        resolver=resolvers.authorization,
    )
    delivery_policy = _selected_exposure_policy(
        projection,
        resolvers.apparatus,
        observation_order=occurrence.delivery_order,
    )
    delivery_revision = _effective_projection_policy(
        policy_revisions,
        observation_order=occurrence.delivery_order,
        expected_revision=delivery_authorization.projection_policy_revision,
    )
    _validate_authorization_scope(
        delivery_authorization,
        projection,
        delivery_policy,
        observation_order=occurrence.delivery_order,
        projection_policy_revision=delivery_revision.revision,
    )
    _validate_authorization_shape(delivery_authorization)
    _validate_exposure_operation(delivery_authorization)
    if not _policy_permits_item(delivery_policy, occurrence.item_ref):
        raise ValueError(f"delivery exposure policy does not permit item {occurrence.item_ref!r}")
    expected = {
        "participant_address": event.participant_address,
        "episode_id": event.episode_id,
        "action_instance_id": event.action_instance_id,
        "observation_boundary_address": event.observation_boundary_address,
        "observation_ref": _observation_ref(event),
        "occurrence_ref": _occurrence_ref(event, occurrence.delivery_order),
    }
    mismatches = sorted(name for name, value in expected.items() if getattr(occurrence, name) != value)
    if mismatches:
        raise ValueError("realized exposure occurrence disagrees with behavior history: " + ", ".join(mismatches))
    if (
        occurrence.participant_address != projection.participant_address
        or occurrence.episode_id != projection.episode_id
    ):
        raise ValueError("realized exposure occurrence is outside the surface participant and episode")
    event_evidence = _event_evidence_refs(event)
    event_provenance = (event.actor_provenance,) if event.actor_provenance is not None else ()
    if set(occurrence.evidence_refs) != set(event_evidence):
        raise ValueError("realized exposure evidence_refs must agree with the observation history occurrence")
    if set(occurrence.provenance_refs) != set(event_provenance):
        raise ValueError("realized exposure provenance_refs must agree with the observation history occurrence")
    required = (
        occurrence.delivery_basis_ref,
        occurrence.item_ref,
        occurrence.authorization_record_ref,
        *occurrence.evidence_refs,
        *occurrence.provenance_refs,
        *occurrence.limitations,
    )
    if any(not isinstance(value, str) or not value for value in required):
        raise ValueError("realized exposure requires delivery, evidence, provenance, and limitation refs")
    if not occurrence.evidence_refs or not occurrence.provenance_refs or not occurrence.limitations:
        raise ValueError("realized exposure requires evidence, provenance, and limitations")
    return occurrence


def _exposure_binding_payload(
    authorization: ParticipantExposureAuthorizationRecord,
    occurrence: ParticipantExposureOccurrenceRecord | None,
    projection: ParticipantExposureProjection,
    *,
    policy_version: str,
    policy_digest: str,
) -> dict[str, object]:
    return {
        "item_ref": authorization.item_ref,
        "authorization_record_ref": authorization.authorization_record_ref,
        "source_ref": authorization.source_ref,
        "source_layer_ref": authorization.source_layer_ref,
        "participant_address": projection.participant_address,
        "episode_id": projection.episode_id,
        "audience_scope_ref": authorization.audience_scope_ref,
        "observation_point": projection.observation_point,
        "observation_order": projection.observation_order,
        "visibility_basis_ref": authorization.visibility_basis_ref,
        "projection_policy_ref": projection.projection_policy_ref,
        "projection_policy_revision": projection.projection_policy_revision,
        "exposure_policy_ref": projection.exposure_policy_ref,
        "exposure_policy_version": policy_version,
        "exposure_policy_digest": policy_digest,
        "operation": authorization.operation,
        "operation_basis_ref": authorization.operation_basis_ref,
        "actor_ref": authorization.actor_ref,
        "controller_ref": authorization.controller_ref,
        "authority_basis_ref": authorization.authority_basis_ref,
        "source_marking_definition_refs": list(authorization.source_marking_definition_refs),
        "result_marking_definition_refs": list(authorization.result_marking_definition_refs),
        "source_provenance_refs": list(authorization.source_provenance_refs),
        "result_provenance_refs": list(authorization.result_provenance_refs),
        "declassification_basis_ref": authorization.declassification_basis_ref,
        "redaction_policy_ref": authorization.redaction_policy_ref,
        "transformation_rule_ref": authorization.transformation_rule_ref,
        "evidence_refs": list(authorization.evidence_refs),
        "provenance_refs": list(authorization.provenance_refs),
        "loss_and_limitations": list(authorization.loss_and_limitations),
        "realization": (
            {
                "occurrence_ref": occurrence.occurrence_ref,
                "item_ref": occurrence.item_ref,
                "authorization_record_ref": occurrence.authorization_record_ref,
                "delivery_basis_ref": occurrence.delivery_basis_ref,
                "delivery_order": occurrence.delivery_order,
                "observation_ref": occurrence.observation_ref,
                "evidence_refs": list(occurrence.evidence_refs),
                "provenance_refs": list(occurrence.provenance_refs),
                "limitations": list(occurrence.limitations),
            }
            if occurrence is not None
            else None
        ),
    }


def project_participant_exposure_bindings(
    relation: Mapping[str, str],
    projection: ParticipantExposureProjection,
    entries: list[dict[str, object]],
    surface_affordances: list[str],
    history_events: Sequence[ParticipantBehaviorHistoryEvent],
    resolvers: ParticipantExposureResolvers,
) -> list[dict[str, object]]:
    """Resolve and serialize the governed exposure basis for every emitted ref."""

    policy_revisions = _resolved_projection_policy_revisions(projection, resolvers.projection_policy)
    _effective_projection_policy(
        policy_revisions,
        observation_order=projection.observation_order,
        expected_revision=projection.projection_policy_revision,
    )
    policy = _selected_exposure_policy(
        projection,
        resolvers.apparatus,
        observation_order=projection.observation_order,
    )
    expected = _serialized_surface_refs(projection, entries, surface_affordances)
    if set(projection.exposure_assessments) != expected:
        raise ValueError("exposure_assessments must exactly cover every serialized surface ref")
    bindings = []
    for item_ref in sorted(expected):
        assessment = projection.exposure_assessments[item_ref]
        if assessment.item_ref != item_ref:
            raise ValueError(f"exposure assessment key {item_ref!r} must match its item_ref")
        authorization = _resolve_authorization(
            authorization_record_ref=assessment.authorization_record_ref,
            item_ref=assessment.item_ref,
            resolver=resolvers.authorization,
        )
        _validate_authorization_scope(
            authorization,
            projection,
            policy,
            observation_order=projection.observation_order,
            projection_policy_revision=projection.projection_policy_revision,
        )
        _validate_authorization_shape(authorization)
        _validate_exposure_operation(authorization)
        occurrence = _validate_realized_exposure(
            assessment,
            projection,
            history_events,
            policy_revisions,
            resolvers,
        )
        if relation.get(item_ref) not in _PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS:
            raise ValueError(f"exposure item {item_ref!r} is not participant-visible at observation_order")
        if not _policy_permits_item(policy, item_ref):
            raise ValueError(f"selected exposure policy does not permit item {item_ref!r}")
        if not set(authorization.evidence_refs).issubset(projection.evidence_refs):
            raise ValueError(f"exposure authorization {item_ref!r} evidence_refs must be carried by the surface")
        if not set(authorization.provenance_refs).issubset(projection.provenance_refs):
            raise ValueError(f"exposure authorization {item_ref!r} provenance_refs must be carried by the surface")
        if not set(authorization.result_marking_definition_refs).issubset(projection.marking_definition_refs):
            raise ValueError(f"exposure authorization {item_ref!r} result markings must be carried by the surface")
        if (
            authorization.redaction_policy_ref is not None
            and authorization.redaction_policy_ref != projection.redaction_policy_ref
        ):
            raise ValueError(f"exposure authorization {item_ref!r} redaction policy must match the surface")
        bindings.append(
            _exposure_binding_payload(
                authorization,
                occurrence,
                projection,
                policy_version=policy.policy_version,
                policy_digest=policy.policy_digest,
            )
        )
    return bindings
