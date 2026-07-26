"""SEM-226 participant exposure and visibility-boundary tests."""

from __future__ import annotations

from dataclasses import fields, replace

import pytest
from pydantic import ValidationError
from raes_contracts.contracts import ParticipantDecisionSurfaceModel, ParticipantImplementationSelectionModel
from raes_processor.models import (
    ParticipantBehaviorHistoryEvent,
    ParticipantDecisionSurfaceActionAssessment,
    ParticipantDecisionSurfaceProjectionInput,
    ParticipantExposureAssessment,
    ParticipantExposureAuthorizationRecord,
    ParticipantExposureOccurrenceRecord,
    ParticipantExposurePolicyRevision,
    ParticipantExposureRealizationAssessment,
    ParticipantExposureResolvers,
    project_participant_decision_surface,
)
from test_sem_220_participant_decision_surface import (
    BEHAVIOR,
    BOUNDARY,
    EPISODE,
    PARTICIPANT,
    SCAN,
    SCAN_AFFORDANCE,
    _history,
    _runtime_model,
)

POLICY = "projection-policy.red.v1"
POLICY_REVISION = "1"
EXPOSURE_POLICY = "exposure-policy.red.v1"
SELECTION_REF = "participant-selections.red.agent.v1"
AUDIENCE = "audience.participant.red-agent"
MARKING = "markings.participant-visible.v1"
OBSERVATION_REF = f"participant-observation:{PARTICIPANT}:{EPISODE}:reveal-1"
OCCURRENCE_REF = f"{OBSERVATION_REF}:order-1"


def _selection(*, withheld_refs: tuple[str, ...] = ()) -> ParticipantImplementationSelectionModel:
    permitted_refs = tuple(ref for ref in ("context.public", SCAN, SCAN_AFFORDANCE) if ref not in withheld_refs)
    return ParticipantImplementationSelectionModel.model_validate(
        {
            "participant_address": PARTICIPANT,
            "implementation_identity": {"name": "reference-red-agent", "version": "1.0.0"},
            "manifest_ref": "participant-implementation-manifests.reference.v1",
            "manifest_digest": "sha256:" + "1" * 64,
            "selected_decision_surface_mode": "autonomous",
            "participant_contract_versions": ["participant-behavior-history-event-stream-v1"],
            "exposure_policy": {
                "policy_id": EXPOSURE_POLICY,
                "policy_version": "1",
                "policy_digest": "sha256:" + "2" * 64,
                "exposure_policy_kinds": ["task-statement"],
                "disclosed_refs": list(permitted_refs),
                "withheld_refs": list(withheld_refs),
                "tool_affordance_refs": [],
                "visibility_scope_refs": [],
                "constraints": {},
            },
        }
    )


def _authorization(
    item_ref: str,
    *,
    source_ref: str | None = None,
    source_provenance_refs: tuple[str, ...] | None = None,
    result_provenance_refs: tuple[str, ...] | None = None,
) -> ParticipantExposureAuthorizationRecord:
    source_provenance = source_provenance_refs or (f"provenance.source.{item_ref}",)
    result_provenance = result_provenance_refs or source_provenance
    return ParticipantExposureAuthorizationRecord(
        authorization_record_ref=f"exposure-authorizations.{item_ref}.v1",
        item_ref=item_ref,
        source_ref=source_ref or item_ref,
        source_layer_ref=f"source-layers.{item_ref}",
        participant_address=PARTICIPANT,
        episode_id=EPISODE,
        audience_scope_ref=AUDIENCE,
        effective_from_order=0,
        effective_through_order=None,
        implementation_selection_ref=SELECTION_REF,
        projection_policy_ref=POLICY,
        projection_policy_revision=POLICY_REVISION,
        exposure_policy_ref=EXPOSURE_POLICY,
        exposure_policy_version="1",
        exposure_policy_digest="sha256:" + "2" * 64,
        visibility_basis_ref=f"visibility-bases.{item_ref}",
        operation="disclosure",
        operation_basis_ref=f"disclosures.{item_ref}.v1",
        actor_ref="actors.runtime-projector",
        controller_ref="controllers.red-agent",
        authority_basis_ref="authorities.red-agent.v1",
        backend_support_ref="backend-support.reference.v1",
        source_marking_definition_refs=(MARKING,),
        result_marking_definition_refs=(MARKING,),
        source_provenance_refs=source_provenance,
        result_provenance_refs=result_provenance,
        evidence_refs=(f"evidence.exposure.{item_ref}",),
        provenance_refs=tuple(dict.fromkeys((*source_provenance, *result_provenance))),
        loss_and_limitations=("No known projection loss",),
    )


def _authorizations() -> dict[str, ParticipantExposureAuthorizationRecord]:
    return {item_ref: _authorization(item_ref) for item_ref in ("context.public", SCAN, SCAN_AFFORDANCE)}


def _occurrence() -> ParticipantExposureOccurrenceRecord:
    return ParticipantExposureOccurrenceRecord(
        occurrence_ref=OCCURRENCE_REF,
        item_ref="context.public",
        authorization_record_ref="exposure-authorizations.context.public.v1",
        participant_address=PARTICIPANT,
        episode_id=EPISODE,
        delivery_basis_ref="delivery-bases.runtime-projection.v1",
        delivery_order=1,
        observation_ref=OBSERVATION_REF,
        action_instance_id="reveal-1",
        observation_boundary_address=BOUNDARY,
        evidence_refs=("evidence.observation.reveal-1",),
        provenance_refs=("participant:red-agent",),
        limitations=("Delivery does not prove acknowledgement or interpretation",),
    )


def _history_through_order_2() -> tuple[ParticipantBehaviorHistoryEvent, ...]:
    history = _history()
    return (
        *history,
        replace(
            history[0],
            timestamp="2026-07-20T08:00:02Z",
            action_instance_id="later-1",
        ),
    )


def _action_assessment(*, eligibility: str = "eligible") -> ParticipantDecisionSurfaceActionAssessment:
    return ParticipantDecisionSurfaceActionAssessment(
        action_contract_address=SCAN,
        presentation_basis_ref=POLICY,
        eligibility=eligibility,
        eligibility_reason_refs=(() if eligibility == "eligible" else ("preconditions.scan.unsatisfied",)),
        constraint_refs=(f"{SCAN}.preconditions",),
        selection_shape_ref="selection-shapes.scan.v1",
        support="supported",
        support_refs=("participant-implementation.reference",),
        realization_refs=("realization.reference",),
    )


def _resolvers(
    *,
    authorizations: dict[str, ParticipantExposureAuthorizationRecord],
    selection: ParticipantImplementationSelectionModel,
    policy_revisions: tuple[ParticipantExposurePolicyRevision, ...],
    occurrences: tuple[ParticipantExposureOccurrenceRecord, ...],
) -> ParticipantExposureResolvers:
    authorization_by_ref = {record.authorization_record_ref: record for record in authorizations.values()}
    occurrence_by_ref = {record.occurrence_ref: record for record in occurrences}

    def apparatus(
        *,
        implementation_selection_ref: str,
        exposure_policy_ref: str,
        observation_order: int,
    ) -> ParticipantImplementationSelectionModel | None:
        del observation_order
        if implementation_selection_ref != SELECTION_REF or exposure_policy_ref != EXPOSURE_POLICY:
            return None
        return selection

    def authorization(
        *,
        authorization_record_ref: str,
        item_ref: str,
    ) -> ParticipantExposureAuthorizationRecord | None:
        record = authorization_by_ref.get(authorization_record_ref)
        return record if record is not None and record.item_ref == item_ref else None

    return ParticipantExposureResolvers(
        apparatus=apparatus,
        projection_policy=lambda **_: policy_revisions,
        authorization=authorization,
        occurrence=lambda *, occurrence_ref: occurrence_by_ref.get(occurrence_ref),
    )


def _projection(
    *,
    observation_order: int = 1,
    selection: ParticipantImplementationSelectionModel | None = None,
    policy_revisions: tuple[ParticipantExposurePolicyRevision, ...] | None = None,
    projection_policy_revision: str = POLICY_REVISION,
    authorizations: dict[str, ParticipantExposureAuthorizationRecord] | None = None,
    assessments: dict[str, ParticipantExposureAssessment] | None = None,
    occurrence: ParticipantExposureOccurrenceRecord | None = None,
    realized: bool = True,
    eligibility: str = "eligible",
) -> tuple[ParticipantDecisionSurfaceProjectionInput, ParticipantExposureResolvers]:
    resolved_authorizations = authorizations or _authorizations()
    resolved_occurrence = occurrence or _occurrence()
    resolved_assessments = assessments or {
        item_ref: ParticipantExposureAssessment(
            item_ref=item_ref,
            authorization_record_ref=authorization.authorization_record_ref,
            realization=(
                ParticipantExposureRealizationAssessment(OCCURRENCE_REF)
                if realized and item_ref == "context.public"
                else None
            ),
        )
        for item_ref, authorization in resolved_authorizations.items()
    }
    projection = ParticipantDecisionSurfaceProjectionInput(
        surface_id=f"decision-surfaces.red.episode-1.order-{observation_order}",
        participant_address=PARTICIPANT,
        episode_id=EPISODE,
        observation_order=observation_order,
        observation_point=f"behavior-history:{observation_order}",
        behavior_specification_address=BEHAVIOR,
        observation_boundary_address=BOUNDARY,
        context_view_ref=f"context-views.red.episode-1.order-{observation_order}",
        implementation_selection_ref=SELECTION_REF,
        decision_control_mode="autonomous",
        audience_scope_ref=AUDIENCE,
        projection_policy_ref=POLICY,
        projection_policy_revision=projection_policy_revision,
        exposure_policy_ref=EXPOSURE_POLICY,
        visibility_projection_ref=f"visibility-projection.red.order-{observation_order}",
        visible_context_refs=("context.public",),
        action_assessments={SCAN: _action_assessment(eligibility=eligibility)},
        exposure_assessments=resolved_assessments,
        form={
            "surface_form": "candidate_action_set",
            "selection_meaning_ref": "selection-meaning.candidate.v1",
            "candidate_entry_ids": [SCAN],
            "open_extension_binding_ref": None,
        },
        evidence_refs=tuple(
            dict.fromkeys(
                (
                    f"evidence.surface.red.order-{observation_order}",
                    *(ref for record in resolved_authorizations.values() for ref in record.evidence_refs),
                )
            )
        ),
        provenance_refs=tuple(
            dict.fromkeys(
                (
                    f"provenance.surface.red.order-{observation_order}",
                    *(ref for record in resolved_authorizations.values() for ref in record.provenance_refs),
                )
            )
        ),
        marking_definition_refs=tuple(
            dict.fromkeys(
                ref for record in resolved_authorizations.values() for ref in record.result_marking_definition_refs
            )
        ),
        redaction_policy_ref="redaction.red.v1",
        semantic_limitations=(
            "Presentation does not imply selection, admission, execution, result, outcome, or delivery",
        ),
    )
    return projection, _resolvers(
        authorizations=resolved_authorizations,
        selection=selection or _selection(),
        policy_revisions=policy_revisions or (ParticipantExposurePolicyRevision(POLICY, POLICY_REVISION, 0),),
        occurrences=((resolved_occurrence,) if realized else ()),
    )


def _project(
    projection: ParticipantDecisionSurfaceProjectionInput,
    resolvers: ParticipantExposureResolvers,
    *,
    history: tuple[ParticipantBehaviorHistoryEvent, ...] | None = None,
):
    return project_participant_decision_surface(
        _runtime_model(),
        history_events=history or _history(),
        projection=projection,
        exposure_resolvers=resolvers,
    )


def test_projection_emits_complete_authoritatively_resolved_bindings() -> None:
    projection, resolvers = _projection()
    surface = _project(projection, resolvers)

    bindings = {binding.item_ref: binding for binding in surface.exposure_bindings}
    assert set(bindings) == {"context.public", SCAN, SCAN_AFFORDANCE}
    assert bindings["context.public"].exposure_policy_digest == "sha256:" + "2" * 64
    assert bindings["context.public"].authorization_record_ref == "exposure-authorizations.context.public.v1"
    assert bindings["context.public"].realization is not None
    assert bindings["context.public"].realization.occurrence_ref == OCCURRENCE_REF
    assert bindings["context.public"].realization.item_ref == "context.public"
    assert (
        bindings["context.public"].realization.authorization_record_ref == "exposure-authorizations.context.public.v1"
    )
    assert set(bindings["context.public"].realization.evidence_refs).issubset(surface.evidence_refs)
    assert set(bindings["context.public"].realization.provenance_refs).issubset(surface.provenance_refs)
    assert bindings[SCAN].realization is None


def test_portable_realization_rejects_cross_item_identity() -> None:
    projection, resolvers = _projection()
    payload = _project(projection, resolvers).model_dump(mode="json")
    payload["exposure_bindings"][0]["realization"]["item_ref"] = SCAN

    with pytest.raises(ValidationError, match="item_ref must match the exposure binding"):
        ParticipantDecisionSurfaceModel.model_validate(payload)


def test_projection_request_carries_no_self_attested_authorization_booleans() -> None:
    assert {field.name for field in fields(ParticipantExposureAssessment)} == {
        "item_ref",
        "authorization_record_ref",
        "realization",
    }


def test_apparatus_and_authorization_refs_must_resolve() -> None:
    projection, resolvers = _projection()
    missing_apparatus = replace(resolvers, apparatus=lambda **_: None)
    with pytest.raises(ValueError, match="apparatus refs did not resolve"):
        _project(projection, missing_apparatus)
    missing_authorization = replace(resolvers, authorization=lambda **_: None)
    with pytest.raises(ValueError, match="no authoritative authorization"):
        _project(projection, missing_authorization)


def test_synthetic_cross_participant_selection_is_rejected() -> None:
    selection = _selection().model_copy(update={"participant_address": "participant.behavior.blue-agent"})
    projection, resolvers = _projection(selection=selection)
    with pytest.raises(ValueError, match="participant_address must match"):
        _project(projection, resolvers)


def test_future_and_stale_policy_revisions_cannot_authorize_surface() -> None:
    future = (ParticipantExposurePolicyRevision(POLICY, "2", 2),)
    projection, resolvers = _projection(policy_revisions=future)
    with pytest.raises(ValueError, match="no projection policy revision is effective"):
        _project(projection, resolvers)

    stale = (
        ParticipantExposurePolicyRevision(POLICY, "1", 0),
        ParticipantExposurePolicyRevision(POLICY, "2", 1),
    )
    projection, resolvers = _projection(policy_revisions=stale)
    with pytest.raises(ValueError, match="must match the revision effective"):
        _project(projection, resolvers)


def test_selected_exposure_policy_withholding_denies_serialization() -> None:
    projection, resolvers = _projection(selection=_selection(withheld_refs=("context.public",)))
    with pytest.raises(ValueError, match="does not permit item 'context.public'"):
        _project(projection, resolvers)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("exposure_policy_version", "0"),
        ("exposure_policy_digest", "sha256:" + "9" * 64),
    ),
)
def test_authorization_is_bound_to_selected_policy_version_and_digest(field_name: str, value: str) -> None:
    authorizations = _authorizations()
    authorizations["context.public"] = replace(authorizations["context.public"], **{field_name: value})
    projection, resolvers = _projection(authorizations=authorizations)
    with pytest.raises(ValueError, match="mismatched coordinates"):
        _project(projection, resolvers)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("participant_address", "participant.behavior.blue-agent"),
        ("episode_id", "episode-other"),
        ("audience_scope_ref", "audience.participant.blue-agent"),
        ("implementation_selection_ref", "participant-selections.synthetic.v1"),
        ("projection_policy_ref", "projection-policy.synthetic.v1"),
        ("projection_policy_revision", "999"),
        ("exposure_policy_ref", "exposure-policy.synthetic.v1"),
    ),
)
def test_authoritative_item_coordinates_must_match_surface(field_name: str, value: str) -> None:
    authorizations = _authorizations()
    authorizations["context.public"] = replace(authorizations["context.public"], **{field_name: value})
    projection, resolvers = _projection(authorizations=authorizations)
    with pytest.raises(ValueError, match="mismatched coordinates"):
        _project(projection, resolvers)


def test_future_authorization_record_is_denied() -> None:
    authorizations = _authorizations()
    authorizations["context.public"] = replace(authorizations["context.public"], effective_from_order=2)
    projection, resolvers = _projection(authorizations=authorizations)
    with pytest.raises(ValueError, match="not effective at observation_order"):
        _project(projection, resolvers)


def test_ineligible_candidate_presentation_does_not_claim_admission() -> None:
    projection, resolvers = _projection(eligibility="ineligible")
    surface = _project(projection, resolvers)
    assert surface.action_entries[0].eligibility == "ineligible"


def test_derived_exposure_rejects_dropped_source_provenance() -> None:
    authorizations = _authorizations()
    source = authorizations["context.public"]
    authorizations["context.public"] = replace(
        source,
        source_ref="truth.hidden.network-posture",
        operation="transformation",
        transformation_rule_ref="transformations.network-summary.v1",
        source_provenance_refs=("provenance.hidden.network-posture",),
        result_provenance_refs=("provenance.summary.network-posture",),
        provenance_refs=("provenance.hidden.network-posture", "provenance.summary.network-posture"),
    )
    projection, resolvers = _projection(authorizations=authorizations)
    with pytest.raises(ValueError, match="inherit source provenance"):
        _project(projection, resolvers)


@pytest.mark.parametrize(
    ("integrity_dimension", "message"),
    (
        ("source-marking-inheritance", "inherit source markings"),
        ("authorization-provenance-closure", "provenance must be carried"),
        ("surface-evidence-carriage", "evidence_refs must be carried by the surface"),
        ("surface-provenance-carriage", "provenance_refs must be carried by the surface"),
        ("surface-marking-carriage", "result markings must be carried by the surface"),
    ),
)
def test_exposure_audit_and_marking_integrity_is_deny_first(
    integrity_dimension: str,
    message: str,
) -> None:
    authorizations = _authorizations()
    authorization = authorizations["context.public"]
    if integrity_dimension == "source-marking-inheritance":
        authorizations["context.public"] = replace(
            authorization,
            source_marking_definition_refs=("markings.evaluator-only.v1",),
        )
    elif integrity_dimension == "authorization-provenance-closure":
        authorizations["context.public"] = replace(
            authorization,
            provenance_refs=("provenance.unrelated",),
        )

    projection, resolvers = _projection(authorizations=authorizations, realized=False)
    authorization = authorizations["context.public"]
    if integrity_dimension == "surface-evidence-carriage":
        projection = replace(
            projection,
            evidence_refs=tuple(ref for ref in projection.evidence_refs if ref not in authorization.evidence_refs),
        )
    elif integrity_dimension == "surface-provenance-carriage":
        projection = replace(
            projection,
            provenance_refs=tuple(
                ref for ref in projection.provenance_refs if ref not in authorization.provenance_refs
            ),
        )
    elif integrity_dimension == "surface-marking-carriage":
        projection = replace(
            projection,
            marking_definition_refs=tuple(
                ref
                for ref in projection.marking_definition_refs
                if ref not in authorization.result_marking_definition_refs
            ),
        )

    with pytest.raises(ValueError, match=message):
        _project(projection, resolvers)


@pytest.mark.parametrize(
    "source_ref",
    (
        "truth.hidden.network-posture",
        "adjudication.answer-key",
        "private.references.canary",
        "scaffold.guidance.next-action",
        "augmentation.backend.hidden-hint",
    ),
)
def test_hidden_and_augmentation_sources_require_governed_transformation(source_ref: str) -> None:
    authorizations = _authorizations()
    authorizations["context.public"] = replace(authorizations["context.public"], source_ref=source_ref)
    projection, resolvers = _projection(authorizations=authorizations)
    with pytest.raises(ValueError, match="requires a transformation rule"):
        _project(projection, resolvers)


def test_redaction_requires_resolved_redaction_policy() -> None:
    authorizations = _authorizations()
    authorizations["context.public"] = replace(
        authorizations["context.public"],
        source_ref="truth.hidden.network-posture",
        operation="redaction",
        transformation_rule_ref="transformations.redact-network-posture.v1",
    )
    projection, resolvers = _projection(authorizations=authorizations)
    with pytest.raises(ValueError, match="requires a redaction policy"):
        _project(projection, resolvers)


def test_resolved_declassification_may_replace_exact_markings_and_provenance() -> None:
    authorizations = _authorizations()
    authorizations["context.public"] = replace(
        authorizations["context.public"],
        source_ref="truth.hidden.network-posture",
        operation="declassification",
        declassification_basis_ref="declassifications.network-posture.v1",
        transformation_rule_ref="transformations.declassified-network-summary.v1",
        source_marking_definition_refs=("markings.evaluator-only.v1",),
        result_marking_definition_refs=(MARKING,),
        source_provenance_refs=("provenance.truth.network-posture",),
        result_provenance_refs=("provenance.declassified.network-posture",),
        provenance_refs=("provenance.truth.network-posture", "provenance.declassified.network-posture"),
    )
    projection, resolvers = _projection(authorizations=authorizations)
    surface = _project(projection, resolvers)
    binding = next(item for item in surface.exposure_bindings if item.item_ref == "context.public")
    assert binding.declassification_basis_ref == "declassifications.network-posture.v1"
    assert binding.result_marking_definition_refs == [MARKING]


def test_exposure_assessments_must_cover_every_serialized_item() -> None:
    authorizations = _authorizations()
    assessments = {
        item_ref: ParticipantExposureAssessment(item_ref, record.authorization_record_ref)
        for item_ref, record in authorizations.items()
        if item_ref != SCAN_AFFORDANCE
    }
    projection, resolvers = _projection(authorizations=authorizations, assessments=assessments, realized=False)
    with pytest.raises(ValueError, match="exactly cover every serialized surface ref"):
        _project(projection, resolvers)


@pytest.mark.parametrize("operation", ("withholding", "concealment", "revocation"))
def test_non_release_operations_cannot_emit_surface_items(operation: str) -> None:
    authorizations = _authorizations()
    authorizations["context.public"] = replace(authorizations["context.public"], operation=operation)
    projection, resolvers = _projection(authorizations=authorizations)
    with pytest.raises(ValueError, match="cannot emit a surface item"):
        _project(projection, resolvers)


def test_realization_must_resolve_to_observation_event_not_list_position_alone() -> None:
    occurrence = replace(
        _occurrence(),
        occurrence_ref=f"participant-observation:{PARTICIPANT}:{EPISODE}:setup-1:order-0",
        observation_ref=f"participant-observation:{PARTICIPANT}:{EPISODE}:setup-1",
        delivery_order=0,
        action_instance_id="setup-1",
    )
    projection, resolvers = _projection(occurrence=occurrence)
    assessment = replace(
        projection.exposure_assessments["context.public"],
        realization=ParticipantExposureRealizationAssessment(occurrence.occurrence_ref),
    )
    projection = replace(
        projection,
        exposure_assessments={**projection.exposure_assessments, "context.public": assessment},
    )
    with pytest.raises(ValueError, match="observation history occurrence"):
        _project(projection, resolvers)


def test_realized_occurrence_resolves_by_semantic_identity_not_sequence_position() -> None:
    projection, resolvers = _projection()
    history = _history()
    surface = _project(projection, resolvers, history=(history[1], history[0]))
    binding = next(item for item in surface.exposure_bindings if item.item_ref == "context.public")
    assert binding.realization is not None
    assert binding.realization.delivery_order == 1


def test_realized_occurrence_cannot_be_reused_for_another_exposed_item() -> None:
    occurrence = replace(
        _occurrence(),
        item_ref=SCAN,
        authorization_record_ref=f"exposure-authorizations.{SCAN}.v1",
    )
    projection, resolvers = _projection(occurrence=occurrence)
    with pytest.raises(ValueError, match="item_ref must match the exposed item"):
        _project(projection, resolvers)


def test_realized_occurrence_requires_authorization_effective_at_delivery_order() -> None:
    authorizations = _authorizations()
    authorizations["context.public"] = replace(authorizations["context.public"], effective_from_order=2)
    projection, resolvers = _projection(observation_order=2, authorizations=authorizations)
    history = _history_through_order_2()
    with pytest.raises(ValueError, match="not effective at observation_order"):
        _project(projection, resolvers, history=history)


def test_realized_occurrence_uses_exposure_policy_effective_at_delivery_order() -> None:
    projection, resolvers = _projection(observation_order=2)
    current_selection = _selection()
    delivery_selection = _selection(withheld_refs=("context.public",))

    def apparatus(
        *,
        implementation_selection_ref: str,
        exposure_policy_ref: str,
        observation_order: int,
    ) -> ParticipantImplementationSelectionModel | None:
        if implementation_selection_ref != SELECTION_REF or exposure_policy_ref != EXPOSURE_POLICY:
            return None
        return delivery_selection if observation_order == 1 else current_selection

    delivery_resolvers = replace(resolvers, apparatus=apparatus)
    history = _history_through_order_2()
    with pytest.raises(ValueError, match="delivery exposure policy does not permit"):
        _project(projection, delivery_resolvers, history=history)


def test_realized_occurrence_uses_projection_policy_effective_at_delivery_order() -> None:
    authorizations = {
        item_ref: replace(record, projection_policy_revision="2") for item_ref, record in _authorizations().items()
    }
    revisions = (
        ParticipantExposurePolicyRevision(POLICY, "1", 0),
        ParticipantExposurePolicyRevision(POLICY, "2", 2),
    )
    projection, resolvers = _projection(
        observation_order=2,
        projection_policy_revision="2",
        policy_revisions=revisions,
        authorizations=authorizations,
    )
    history = _history_through_order_2()
    with pytest.raises(ValueError, match="revision effective at observation_order"):
        _project(projection, resolvers, history=history)


def test_realized_occurrence_may_resolve_distinct_delivery_time_authorization() -> None:
    authorizations = {
        item_ref: replace(record, projection_policy_revision="2", effective_from_order=2)
        for item_ref, record in _authorizations().items()
    }
    delivery_authorization = replace(
        authorizations["context.public"],
        authorization_record_ref="exposure-authorizations.context.public.delivery-order-1",
        projection_policy_revision="1",
        effective_from_order=0,
        effective_through_order=1,
    )
    occurrence = replace(_occurrence(), authorization_record_ref=delivery_authorization.authorization_record_ref)
    revisions = (
        ParticipantExposurePolicyRevision(POLICY, "1", 0),
        ParticipantExposurePolicyRevision(POLICY, "2", 2),
    )
    projection, resolvers = _projection(
        observation_order=2,
        projection_policy_revision="2",
        policy_revisions=revisions,
        authorizations=authorizations,
        occurrence=occurrence,
    )
    current_authorization_resolver = resolvers.authorization

    def authorization(
        *,
        authorization_record_ref: str,
        item_ref: str,
    ) -> ParticipantExposureAuthorizationRecord | None:
        if authorization_record_ref == delivery_authorization.authorization_record_ref:
            return delivery_authorization if item_ref == delivery_authorization.item_ref else None
        return current_authorization_resolver(
            authorization_record_ref=authorization_record_ref,
            item_ref=item_ref,
        )

    surface = _project(
        projection,
        replace(resolvers, authorization=authorization),
        history=_history_through_order_2(),
    )
    binding = next(item for item in surface.exposure_bindings if item.item_ref == "context.public")
    assert binding.realization is not None
    assert binding.realization.authorization_record_ref == delivery_authorization.authorization_record_ref


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("occurrence_ref", "participant-observation:forged:order-1", "disagrees with behavior history"),
        ("participant_address", "participant.behavior.blue-agent", "observation history occurrence"),
        ("episode_id", "episode-other", "observation history occurrence"),
        ("action_instance_id", "forged-action", "observation history occurrence"),
        (
            "observation_boundary_address",
            "participant.observation-boundary.other",
            "observation history occurrence",
        ),
        ("observation_ref", "participant-observation:forged", "disagrees with behavior history"),
        ("evidence_refs", ("evidence.forged",), "evidence_refs must agree"),
        ("provenance_refs", ("provenance.forged",), "provenance_refs must agree"),
    ),
)
def test_realized_exposure_must_agree_with_exact_history_occurrence(
    field_name: str,
    value: object,
    message: str,
) -> None:
    occurrence = replace(_occurrence(), **{field_name: value})
    projection, resolvers = _projection(occurrence=occurrence)
    assessment = replace(
        projection.exposure_assessments["context.public"],
        realization=ParticipantExposureRealizationAssessment(occurrence.occurrence_ref),
    )
    projection = replace(
        projection,
        exposure_assessments={**projection.exposure_assessments, "context.public": assessment},
    )
    with pytest.raises(ValueError, match=message):
        _project(projection, resolvers)


def test_revocation_does_not_erase_an_earlier_exposure_record() -> None:
    projection, resolvers = _projection(observation_order=0, realized=False)
    earlier = _project(projection, resolvers)
    authorizations = _authorizations()
    authorizations["context.public"] = replace(authorizations["context.public"], operation="revocation")
    projection, resolvers = _projection(authorizations=authorizations, realized=False)
    with pytest.raises(ValueError, match="cannot emit a surface item"):
        _project(projection, resolvers)
    assert {binding.item_ref for binding in earlier.exposure_bindings} == {
        "context.public",
        SCAN,
        SCAN_AFFORDANCE,
    }
