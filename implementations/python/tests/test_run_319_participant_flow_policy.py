"""RUN-319 operation-bound participant information-flow enforcement tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from threading import Barrier, Thread
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from raes.participant_behavior_specification import MixedControlTransitionKind
from raes_backend_protocols.backend_manifest import BackendManifest
from raes_backend_protocols.capabilities import ParticipantFeatureSupport
from raes_backend_stubs.stubs import create_stub_target
from raes_contracts.contracts.participant_crossing import (
    ParticipantCrossingGateDisposition,
    ParticipantCrossingOperation,
    ParticipantCrossingPolicyReferenceModel,
    ParticipantCrossingSubjectReferenceModel,
)
from raes_contracts.participant_binding import ParticipantActionAdmissionRequest
from raes_contracts.runtime_state import RuntimeSnapshot, RuntimeSnapshotEnvelope
from raes_contracts.vocabulary import ParticipantFeatureSupportLevel
from raes_operations.deterministic_participant_fixtures import (
    build_implementation_manifest,
    build_implementation_selection,
)
from raes_processor.models import (
    MixedControlControllerStateRuntime,
    MixedControlDispositionRulesRuntime,
    MixedControlTransitionRuntime,
    ParticipantBehaviorRuntime,
    ParticipantBehaviorSpecificationRuntime,
)
from raes_runtime.control_plane import RuntimeControlPlane
from raes_runtime.control_plane_api_models import _snapshot_model
from raes_runtime.control_plane_security import (
    ControlPlaneIdentity,
    ControlPlaneRole,
    ParticipantAudienceSubjectBinding,
    ParticipantControlSubjectBinding,
)
from raes_runtime.control_plane_store import (
    InMemoryControlPlaneStore,
    LocalControlPlaneStore,
    _snapshot_from_payload,
    _snapshot_payload,
)
from raes_runtime.operational_apparatus import operational_apparatus_summary
from raes_runtime.participant_control_intents import ParticipantHandoffControlIntent
from raes_runtime.participant_crossing_boundary import _action_subject
from raes_runtime.participant_crossing_egress import _view_subject
from raes_runtime.participant_crossing_mediation import (
    ParticipantCrossingEvidence,
    ParticipantCrossingIntent,
    ParticipantCrossingPolicyResolution,
    ParticipantCrossingSemanticGates,
    ParticipantCrossingTransformationResolution,
    ParticipantCrossingValidationContext,
)
from raes_runtime.participant_result_contracts import (
    participant_runtime_history_transition_diagnostics,
    participant_runtime_state_contract_diagnostics,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
_PARTICIPANT = "participant.behavior.red-agent"
_CONTROLLER = "participant.behavior.supervisor"
_AUDIENCE = "audience:red-operator"
_ACTION = "participant.action-contract.contain-host"
_TRANSFORMED_ACTION = "participant.action-contract.redacted-contain-host"
_OBSERVATION = "participant.observation-boundary.red-view"


def _crossing_request() -> dict[str, object]:
    fixture = (
        REPO_ROOT
        / "contracts"
        / "fixtures"
        / "participant-runtime"
        / "participant-crossing-occurrence-v1"
        / "valid"
        / "request.json"
    )
    return json.loads(fixture.read_text(encoding="utf-8"))


def _evidence() -> ParticipantCrossingEvidence:
    return ParticipantCrossingEvidence(
        audience_scope_ref=_AUDIENCE,
        required_evidence_refs=["evidence-requirement:crossing-decision"],
        provenance_refs=["provenance:crossing-1"],
        evidence_refs=["evidence:crossing-1"],
        object_marking_refs=["marking:participant-control"],
        authorization_scope="scope:red-team",
        loss_and_limitations=["limitation:bounded-reference-runtime"],
    )


def _identity(*, bound: bool = True, audience_bound: bool = False) -> ControlPlaneIdentity:
    return ControlPlaneIdentity(
        identity="operator.red",
        roles=frozenset({ControlPlaneRole.OPERATOR}),
        target_name="stub",
        participant_control_subjects=(
            (
                ParticipantControlSubjectBinding(
                    participant_address=_PARTICIPANT,
                    controller_ref=_CONTROLLER,
                ),
            )
            if bound
            else ()
        ),
        participant_audience_subjects=(
            (
                ParticipantAudienceSubjectBinding(
                    participant_address=_PARTICIPANT,
                    audience_scope_ref=_AUDIENCE,
                ),
            )
            if audience_bound
            else ()
        ),
    )


def _behavior() -> ParticipantBehaviorRuntime:
    return ParticipantBehaviorRuntime(
        address=_PARTICIPANT,
        name="red-agent",
        spec={},
        authority_anchor_refs=("red-team",),
        authority_anchor_addresses=("authority:red-team",),
        action_contract_addresses=(_ACTION, _TRANSFORMED_ACTION),
        observation_boundary_addresses=(_OBSERVATION,),
    )


def _admission_request(
    *,
    action_contract_address: str = _ACTION,
    action_instance_id: str = "action-1",
) -> ParticipantActionAdmissionRequest:
    return ParticipantActionAdmissionRequest(
        participant_address=_PARTICIPANT,
        action_contract_address=action_contract_address,
        observation_boundary_address=_OBSERVATION,
        action_instance_id=action_instance_id,
        implementation_manifest=build_implementation_manifest(),
        implementation_selection=build_implementation_selection(_PARTICIPANT),
        evidence_refs=("evidence:action",),
        observation_boundary_evidence_refs=("evidence:action",),
    )


def _policy_capable_target(
    *features: str,
    support_level: ParticipantFeatureSupportLevel = ParticipantFeatureSupportLevel.EXACT,
):
    selected_features = set(features or ("participant_ingress_admission",))
    target = create_stub_target()
    manifest = target.manifest
    capabilities = manifest.participant_runtime
    assert capabilities is not None
    feature_support = tuple(
        (
            ParticipantFeatureSupport(
                feature=entry.feature,
                support_level=support_level,
                constraint_refs=(
                    (f"constraint:{entry.feature}:bounded",)
                    if support_level is ParticipantFeatureSupportLevel.BOUNDED
                    else ()
                ),
                limitation_refs=(
                    (f"limitation:{entry.feature}:bounded",)
                    if support_level is not ParticipantFeatureSupportLevel.EXACT
                    else ()
                ),
                disclosure_refs=(
                    (f"disclosure:{entry.feature}:bounded",)
                    if support_level is not ParticipantFeatureSupportLevel.EXACT
                    else ()
                ),
                evidence_refs=(f"evidence:backend:{entry.feature}",),
            )
            if entry.feature in selected_features
            else entry
        )
        for entry in capabilities.feature_support
    )
    participant_runtime = replace(
        capabilities,
        supported_behavior_features=(capabilities.supported_behavior_features | selected_features),
        feature_support=feature_support,
    )
    updated_manifest = BackendManifest(
        identity=manifest.identity,
        supported_contract_versions=manifest.supported_contract_versions,
        compatibility=manifest.compatibility,
        realization_support=manifest.realization_support,
        concept_bindings=manifest.concept_bindings,
        constraints=manifest.constraints,
        capabilities=replace(manifest.capabilities, participant_runtime=participant_runtime),
        realization_envelope=manifest.realization_envelope,
    )
    return replace(target, manifest=updated_manifest)


class _StaticCrossingResolver:
    def __init__(
        self,
        *,
        gate_overrides: dict[str, ParticipantCrossingGateDisposition] | None = None,
        allowed_downgrades: dict[str, ParticipantFeatureSupportLevel] | None = None,
    ) -> None:
        self.gate_overrides = gate_overrides or {}
        self.allowed_downgrades = allowed_downgrades or {}
        self.seen_intents: list[ParticipantCrossingIntent] = []
        self.subjects: list[ParticipantCrossingSubjectReferenceModel] = []
        self.evidence_refs: set[str] = set()
        self.authority_refs: set[str] = {
            "authority:red-team",
            "entities.red-team",
            "runtime.authority:participant-projection",
        }
        fixture_policy = ParticipantCrossingPolicyReferenceModel.model_validate(
            _crossing_request()["occurrence"]["policy"]
        )
        self.policy = fixture_policy.model_copy(
            update={
                "effective_order": 0,
                "valid_from_order": 0,
                "valid_until_order": 1000,
            }
        )

    def resolve(
        self,
        intent: ParticipantCrossingIntent,
        snapshot: RuntimeSnapshot,
    ) -> ParticipantCrossingPolicyResolution:
        del snapshot
        self._remember(intent)
        defaults = {
            "participant_authority": ParticipantCrossingGateDisposition.PERMIT,
            "action_admission": (
                ParticipantCrossingGateDisposition.PERMIT
                if intent.direction.value == "ingress"
                else ParticipantCrossingGateDisposition.NOT_APPLICABLE
            ),
            "visibility": (
                ParticipantCrossingGateDisposition.PERMIT
                if intent.direction.value == "egress"
                else ParticipantCrossingGateDisposition.NOT_APPLICABLE
            ),
            "marking_authorization": ParticipantCrossingGateDisposition.PERMIT,
            "declassification": ParticipantCrossingGateDisposition.NOT_APPLICABLE,
            "transformation_validity": ParticipantCrossingGateDisposition.NOT_APPLICABLE,
        }
        if intent.requested_operation in {
            ParticipantCrossingOperation.PROJECTION,
            ParticipantCrossingOperation.MASKING,
            ParticipantCrossingOperation.REDACTION,
            ParticipantCrossingOperation.TRANSFORMATION,
            ParticipantCrossingOperation.DECLASSIFICATION,
        }:
            defaults["transformation_validity"] = ParticipantCrossingGateDisposition.PERMIT
        defaults.update(self.gate_overrides)
        return ParticipantCrossingPolicyResolution(
            policy=self.policy,
            gates=ParticipantCrossingSemanticGates(**defaults),
            reason_code="policy-satisfied",
            allowed_downgrades=self.allowed_downgrades,
            downgrade_policy_ref=("policy:downgrade:authorized" if self.allowed_downgrades else None),
            downgrade_provenance_ref=("provenance:downgrade:authorized" if self.allowed_downgrades else None),
        )

    def _remember(self, intent: ParticipantCrossingIntent) -> None:
        self.seen_intents.append(intent)
        if intent.subject not in self.subjects:
            self.subjects.append(intent.subject)
        self.evidence_refs.update(intent.evidence_refs)
        self.evidence_refs.update(intent.required_evidence_refs)
        self.authority_refs.update(intent.authority_basis_refs)

    def validation_context(
        self,
        snapshot: RuntimeSnapshot,
        participant_address: str,
    ) -> ParticipantCrossingValidationContext:
        del snapshot, participant_address
        return ParticipantCrossingValidationContext(
            known_subjects=tuple(self.subjects),
            policies=(self.policy,),
            known_evidence_refs=frozenset(
                {
                    *self.evidence_refs,
                    "evidence:backend:participant_ingress_admission",
                    "evidence:backend:participant_egress_projection",
                    "evidence:backend:participant_transformation",
                    "evidence:backend:participant_intervention",
                }
            ),
            known_authority_basis_refs=frozenset(self.authority_refs),
        )


def _action_plane(
    resolver: _StaticCrossingResolver,
    *,
    target: object | None = None,
    store: object | None = None,
) -> RuntimeControlPlane:
    plane = RuntimeControlPlane(
        target or _policy_capable_target(),
        crossing_policy_resolver=resolver,
        store=store,
    )
    plane.initialize_participant_episode(_PARTICIPANT, episode_id="episode-1")
    return plane


def _admit(
    plane: RuntimeControlPlane,
    *,
    request: ParticipantActionAdmissionRequest | None = None,
    idempotency_key: str = "crossing-action",
    identity: ControlPlaneIdentity | None = None,
):
    return plane.admit_participant_action(
        _behavior(),
        request or _admission_request(),
        identity=identity or _identity(),
        crossing_evidence=_evidence(),
        idempotency_key=idempotency_key,
    )


def test_crossing_history_is_first_class_serialized_and_operational_state() -> None:
    request = _crossing_request()
    snapshot = RuntimeSnapshot(participant_crossing_history={_PARTICIPANT: [request]})

    restored = _snapshot_from_payload(_snapshot_payload(snapshot))
    published = _snapshot_model(RuntimeSnapshotEnvelope(snapshot=snapshot))
    summary = operational_apparatus_summary(
        target_name="reference",
        snapshot=snapshot,
        operation_records=[],
        audit_events=[],
    )

    assert restored.participant_crossing_history == {_PARTICIPANT: [request]}
    assert published.participant_crossing_history[_PARTICIPANT][0].event_id == request["event_id"]
    assert summary["runtime_surfaces"]["participant_crossing_history"] == 1


def test_crossing_history_is_preserved_and_append_only() -> None:
    request = _crossing_request()
    snapshot = RuntimeSnapshot(participant_crossing_history={_PARTICIPANT: [request]})
    rewritten = RuntimeSnapshot(
        participant_crossing_history={
            _PARTICIPANT: [{**request, "event_id": "crossing-occurrence.requested.rewritten"}]
        },
    )

    assert snapshot.with_entries({}).participant_crossing_history == snapshot.participant_crossing_history
    assert any(
        "append-only" in diagnostic.message
        for diagnostic in participant_runtime_history_transition_diagnostics(snapshot, rewritten)
    )
    invalid = RuntimeSnapshot(participant_crossing_history={"participants.other": [request]})
    assert any(
        "map key" in diagnostic.message for diagnostic in participant_runtime_state_contract_diagnostics(invalid)
    )


def test_caller_evidence_cannot_describe_the_protected_operation() -> None:
    payload = {
        **_evidence().model_dump(mode="json"),
        "interaction_kind": "denial",
        "participant_address": "participant.attacker",
    }
    with pytest.raises(ValidationError, match="interaction_kind"):
        ParticipantCrossingEvidence.model_validate(payload)


def test_action_boundary_authorizes_and_finalizes_one_operation() -> None:
    resolver = _StaticCrossingResolver()
    plane = _action_plane(resolver)

    receipt = _admit(plane)

    assert receipt.accepted is True
    assert len(plane.snapshot.participant_behavior_history[_PARTICIPANT]) >= 2
    crossing = plane.snapshot.participant_crossing_history[_PARTICIPANT]
    assert [item["occurrence"]["stage"] for item in crossing] == ["requested", "decided"]
    assert len(plane._operations) == 2  # episode initialization plus the combined action
    audit = plane.audit_log()[-1]
    assert audit.action == "admit_participant_action"
    assert audit.operation_id == receipt.operation_id
    assert audit.details["crossing_decision_id"] == crossing[-1]["occurrence"]["decision_id"]


def test_action_boundary_derives_exact_subject_and_semantics_from_request() -> None:
    resolver = _StaticCrossingResolver()
    plane = _action_plane(resolver)
    request = _admission_request()

    _admit(plane, request=request)

    resolved = resolver.seen_intents[0]
    assert resolved.interaction_kind.value == "action-proposal"
    assert resolved.action_or_projection_ref == request.action_contract_address
    assert resolved.subject == _action_subject(plane, request)
    assert resolved.participant_address == request.participant_address
    assert resolved.episode_id == "episode-1"


def test_configured_action_ingress_cannot_bypass_crossing_mediation() -> None:
    plane = _action_plane(_StaticCrossingResolver())
    behavior = _behavior()
    request = _admission_request()
    identity = _identity()

    with pytest.raises(ValueError, match="requires crossing evidence"):
        plane.admit_participant_action(
            behavior,
            request,
            identity=identity,
        )

    assert plane.snapshot.participant_behavior_history == {}
    assert plane.snapshot.participant_crossing_history == {}


def test_policy_capable_target_requires_crossing_resolver_at_startup() -> None:
    target = _policy_capable_target()
    with pytest.raises(ValueError, match="policy capabilities require a crossing policy resolver"):
        RuntimeControlPlane(target)


def test_unsupported_backend_never_executes_the_incumbent_action() -> None:
    resolver = _StaticCrossingResolver()
    plane = _action_plane(resolver, target=create_stub_target())

    receipt = _admit(plane)

    assert receipt.accepted is False
    assert plane.snapshot.participant_behavior_history == {}
    decision = plane.snapshot.participant_crossing_history[_PARTICIPANT][-1]["occurrence"]
    assert decision["disposition"] == "unsupported"
    assert decision["gates"]["backend_support"] == "unsupported"


@pytest.mark.parametrize(
    "gate",
    ["participant_authority", "action_admission", "marking_authorization"],
)
def test_independent_ingress_gate_denials_do_not_execute_action(gate: str) -> None:
    resolver = _StaticCrossingResolver(gate_overrides={gate: ParticipantCrossingGateDisposition.DENY})
    plane = _action_plane(resolver)

    receipt = _admit(plane, idempotency_key=f"denied-{gate}")

    assert receipt.accepted is False
    assert plane.snapshot.participant_behavior_history == {}
    decision = plane.snapshot.participant_crossing_history[_PARTICIPANT][-1]["occurrence"]
    assert decision["gates"][gate] == "deny"


def test_identity_denials_are_security_audited_without_participant_facts() -> None:
    plane = _action_plane(_StaticCrossingResolver())
    identity = _identity(bound=False)

    with pytest.raises(PermissionError, match="subject"):
        _admit(plane, identity=identity)

    assert plane.snapshot.participant_crossing_history == {}
    assert plane.snapshot.participant_behavior_history == {}
    assert plane.audit_log()[-1].reason == "subject-forbidden"
    assert plane.audit_log()[-1].details == {}


def test_operation_bound_idempotency_replays_neither_decision_nor_action() -> None:
    plane = _action_plane(_StaticCrossingResolver())

    first = _admit(plane, idempotency_key="same-operation")
    retry = _admit(plane, idempotency_key="same-operation")

    assert retry.operation_id == first.operation_id
    assert len(plane.snapshot.participant_crossing_history[_PARTICIPANT]) == 2
    behavior_count = len(plane.snapshot.participant_behavior_history[_PARTICIPANT])
    assert behavior_count >= 2
    different_request = _admission_request(action_instance_id="different")
    with pytest.raises(ValueError, match="different semantics"):
        _admit(
            plane,
            request=different_request,
            idempotency_key="same-operation",
        )
    assert len(plane.snapshot.participant_behavior_history[_PARTICIPANT]) == behavior_count


def test_operation_bound_idempotency_rejects_replay_after_state_cut_advances() -> None:
    plane = _action_plane(_StaticCrossingResolver())

    _admit(plane, idempotency_key="state-cut-bound")
    _admit(
        plane,
        request=_admission_request(action_instance_id="later-action"),
        idempotency_key="later-operation",
    )

    with pytest.raises(ValueError, match="state cut advanced"):
        _admit(plane, idempotency_key="state-cut-bound")


class _TransformedActionResolver(_StaticCrossingResolver):
    def __init__(self, *, deny_fresh: bool = False) -> None:
        super().__init__()
        self.deny_fresh = deny_fresh
        self.governed_request: ParticipantActionAdmissionRequest | None = None

    def resolve_operation(
        self,
        intent: ParticipantCrossingIntent,
        snapshot: RuntimeSnapshot,
        carrier: object,
    ) -> ParticipantCrossingPolicyResolution:
        assert isinstance(carrier, ParticipantActionAdmissionRequest)
        self._remember(intent)
        self.governed_request = replace(
            carrier,
            action_contract_address=_TRANSFORMED_ACTION,
            action_instance_id=f"{carrier.action_instance_id}-redacted",
        )
        result_subject = _action_subject(SimpleNamespace(_snapshot=snapshot), self.governed_request)
        if result_subject not in self.subjects:
            self.subjects.append(result_subject)
        base = super().resolve(intent, snapshot)
        return replace(
            base,
            gates=replace(
                base.gates,
                transformation_validity=ParticipantCrossingGateDisposition.PERMIT,
            ),
            required_operation=ParticipantCrossingOperation.REDACTION,
            transformation=ParticipantCrossingTransformationResolution(
                result_subject=result_subject,
                rule_ref="rule:redact-action",
                rule_revision="1",
                result_marking_refs=("marking:participant-control",),
            ),
        )

    def resolve(
        self,
        intent: ParticipantCrossingIntent,
        snapshot: RuntimeSnapshot,
    ) -> ParticipantCrossingPolicyResolution:
        resolution = super().resolve(intent, snapshot)
        if self.governed_request is not None and intent.subject.subject_ref.endswith(
            self.governed_request.action_instance_id
        ):
            if self.deny_fresh:
                return replace(
                    resolution,
                    gates=replace(
                        resolution.gates,
                        action_admission=ParticipantCrossingGateDisposition.DENY,
                    ),
                )
        return resolution

    def transform_ingress(
        self,
        intent: ParticipantCrossingIntent,
        governed_subject: ParticipantCrossingSubjectReferenceModel,
        carrier: object,
    ) -> ParticipantActionAdmissionRequest:
        del intent, governed_subject, carrier
        assert self.governed_request is not None
        return self.governed_request


def test_transformed_action_is_revalidated_and_the_governed_carrier_executes() -> None:
    resolver = _TransformedActionResolver()
    plane = _action_plane(
        resolver,
        target=_policy_capable_target(
            "participant_ingress_admission",
            "participant_transformation",
        ),
    )

    receipt = _admit(plane)

    assert receipt.accepted is True
    history = plane.snapshot.participant_crossing_history[_PARTICIPANT]
    assert [item["occurrence"]["stage"] for item in history] == [
        "requested",
        "decided",
        "transformed",
        "requested",
        "decided",
    ]
    behavior = plane.snapshot.participant_behavior_history[_PARTICIPANT]
    assert all(
        item.get("action_contract_address") == _TRANSFORMED_ACTION
        for item in behavior
        if "action_contract_address" in item
    )


def test_fresh_denial_of_transformed_action_prevents_backend_execution() -> None:
    resolver = _TransformedActionResolver(deny_fresh=True)
    plane = _action_plane(
        resolver,
        target=_policy_capable_target(
            "participant_ingress_admission",
            "participant_transformation",
        ),
    )

    receipt = _admit(plane)

    assert receipt.accepted is False
    assert plane.snapshot.participant_behavior_history == {}
    assert plane.snapshot.participant_crossing_history[_PARTICIPANT][-1]["occurrence"]["disposition"] == "deny"


def _status_evidence_call(
    plane: RuntimeControlPlane,
    *,
    identity: ControlPlaneIdentity,
    idempotency_key: str,
):
    return plane.get_participant_status_view(
        _PARTICIPANT,
        identity=identity,
        crossing_evidence=_evidence(),
        idempotency_key=idempotency_key,
    )


def test_egress_requires_separate_audience_authority_and_commits_before_return() -> None:
    resolver = _StaticCrossingResolver()
    plane = _action_plane(
        resolver,
        target=_policy_capable_target(
            "participant_egress_projection",
            "participant_transformation",
        ),
    )
    unbound_identity = _identity()

    with pytest.raises(PermissionError, match="audience"):
        _status_evidence_call(plane, identity=unbound_identity, idempotency_key="egress-unbound")
    assert plane.snapshot.participant_crossing_history == {}

    view = _status_evidence_call(
        plane,
        identity=_identity(audience_bound=True),
        idempotency_key="egress-bound",
    )

    assert view is not None
    assert view.participant_address == _PARTICIPANT
    assert plane.snapshot.participant_crossing_history[_PARTICIPANT][-1]["occurrence"]["disposition"] == "permit"
    assert plane.audit_log()[-1].operation_id in plane._operations


class _TransformedEgressResolver(_StaticCrossingResolver):
    def __init__(self) -> None:
        super().__init__()
        self.governed_view: object | None = None

    def resolve_operation(
        self,
        intent: ParticipantCrossingIntent,
        snapshot: RuntimeSnapshot,
        carrier: object,
    ) -> ParticipantCrossingPolicyResolution:
        self._remember(intent)
        self.governed_view = carrier.model_copy(
            update={
                "view_id": f"{carrier.view_id}.redacted",
                "redaction_policy_ref": "policy:redacted-status",
                "marking_definition_refs": ["marking:participant-control", "marking:redacted"],
            }
        )
        result_subject = _view_subject(
            self.governed_view,
            participant_address=intent.participant_address,
            episode_id=intent.episode_id,
            subject_kind=intent.subject.subject_kind,
        )
        if result_subject not in self.subjects:
            self.subjects.append(result_subject)
        base = super().resolve(intent, snapshot)
        return replace(
            base,
            gates=replace(
                base.gates,
                transformation_validity=ParticipantCrossingGateDisposition.PERMIT,
            ),
            required_operation=ParticipantCrossingOperation.REDACTION,
            transformation=ParticipantCrossingTransformationResolution(
                result_subject=result_subject,
                rule_ref="rule:redact-status",
                rule_revision="1",
                result_marking_refs=("marking:participant-control", "marking:redacted"),
            ),
        )

    def transform_egress(
        self,
        intent: ParticipantCrossingIntent,
        governed_subject: ParticipantCrossingSubjectReferenceModel,
        carrier: object,
    ) -> object:
        del intent, governed_subject, carrier
        return self.governed_view


def test_egress_transformation_returns_only_the_committed_governed_view() -> None:
    resolver = _TransformedEgressResolver()
    plane = _action_plane(
        resolver,
        target=_policy_capable_target(
            "participant_egress_projection",
            "participant_transformation",
        ),
    )

    view = _status_evidence_call(
        plane,
        identity=_identity(audience_bound=True),
        idempotency_key="egress-redacted",
    )
    retry = _status_evidence_call(
        plane,
        identity=_identity(audience_bound=True),
        idempotency_key="egress-redacted",
    )

    assert view is not None
    assert view.redaction_policy_ref == "policy:redacted-status"
    assert view.marking_definition_refs == ["marking:participant-control", "marking:redacted"]
    assert retry == view
    history = plane.snapshot.participant_crossing_history[_PARTICIPANT]
    assert [item["occurrence"]["stage"] for item in history] == [
        "requested",
        "decided",
        "transformed",
    ]


def test_missing_visibility_gate_fails_closed_without_serializing_output() -> None:
    resolver = _StaticCrossingResolver(gate_overrides={"visibility": ParticipantCrossingGateDisposition.NOT_APPLICABLE})
    plane = _action_plane(
        resolver,
        target=_policy_capable_target(
            "participant_egress_projection",
            "participant_transformation",
        ),
    )
    audience_identity = _identity(audience_bound=True)

    with pytest.raises(PermissionError, match="not permitted"):
        _status_evidence_call(
            plane,
            identity=audience_identity,
            idempotency_key="egress-no-visibility",
        )

    decision = plane.snapshot.participant_crossing_history[_PARTICIPANT][-1]["occurrence"]
    assert decision["gates"]["visibility"] == "unknown"


def test_authorized_downgrade_records_only_effective_backend_strength() -> None:
    feature = "participant_ingress_admission"
    resolver = _StaticCrossingResolver(allowed_downgrades={feature: ParticipantFeatureSupportLevel.BOUNDED})
    plane = _action_plane(
        resolver,
        target=_policy_capable_target(
            feature,
            support_level=ParticipantFeatureSupportLevel.BOUNDED,
        ),
    )

    receipt = _admit(plane)

    assert receipt.accepted is True
    history = plane.snapshot.participant_crossing_history[_PARTICIPANT]
    assert all(item["occurrence"]["backend_posture"] == "bounded" for item in history)


def _control_specification() -> ParticipantBehaviorSpecificationRuntime:
    autonomous = MixedControlControllerStateRuntime(
        address="participant.behavior-specification.controlled.controller-state.autonomous",
        name="autonomous",
        spec={},
        state_id="autonomous",
        controller_ref="supervisor",
        controller_address=_CONTROLLER,
        authority_basis_refs=("red-team",),
        authority_basis_addresses=("entities.red-team",),
        scope_refs=("web",),
        scope_addresses=("nodes.web",),
        policy_revision="1.0.0",
        valid_from_order=0,
        valid_until_order=20,
        authority_status="active",
        evidence_refs=("authority-evidence",),
        evidence_addresses=("evidence.authority",),
    )
    supervised = replace(
        autonomous,
        address="participant.behavior-specification.controlled.controller-state.supervised",
        name="supervised",
        state_id="supervised",
    )
    transition = MixedControlTransitionRuntime(
        address="participant.behavior-specification.controlled.control-transition.handoff",
        name="handoff",
        spec={},
        transition_id="handoff",
        transition_kind=MixedControlTransitionKind.HANDOFF.value,
        from_state_address=autonomous.address,
        to_state_address=supervised.address,
        policy_revision="1.0.0",
        expected_state_revision=0,
        resulting_state_revision=1,
        effective_order=1,
        valid_from_order=0,
        valid_until_order=20,
        completion_evidence_refs=("handoff-evidence",),
        completion_evidence_addresses=("evidence.handoff",),
    )
    return ParticipantBehaviorSpecificationRuntime(
        address="participant.behavior-specification.controlled",
        name="controlled",
        spec={},
        spec_name="controlled",
        participant_addresses=(_PARTICIPANT,),
        behavior_mode="mixed-control",
        mixed_control_participant_address=_PARTICIPANT,
        mixed_control_policy_revision="1.0.0",
        mixed_control_order_strategy="total-effective-order",
        mixed_control_initial_state_address=autonomous.address,
        mixed_control_dispositions=MixedControlDispositionRulesRuntime(
            duplicate="idempotent",
            stale="reject",
            revoked="reject",
            late="reject",
            concurrent="reject",
            conflict="reject",
        ),
        controller_states=(autonomous, supervised),
        control_transitions=(transition,),
    )


def test_supervisory_control_derives_handoff_semantics_and_commits_one_transition() -> None:
    resolver = _StaticCrossingResolver()
    specification = _control_specification()
    plane = RuntimeControlPlane(
        _policy_capable_target(
            "participant_ingress_admission",
            "participant_intervention",
        ),
        behavior_specifications={specification.address: specification},
        crossing_policy_resolver=resolver,
    )
    intent = ParticipantHandoffControlIntent(
        declaration_ref=specification.control_transitions[0].address,
        episode_id="episode-1",
        client_correlation_id="handoff-1",
        policy_revision="1.0.0",
        expected_state_revision=0,
        provenance_refs=["provenance:handoff"],
        evidence_refs=["evidence:handoff"],
        object_marking_refs=["marking:participant-control"],
        limitation_refs=["limitation:none"],
        completion_evidence_ref="evidence:handoff",
    )

    receipt = plane.record_participant_control(
        _PARTICIPANT,
        intent,
        identity=_identity(),
        crossing_evidence=_evidence(),
        idempotency_key="handoff",
    )

    assert receipt.accepted is True
    assert resolver.seen_intents[0].interaction_kind.value == "handoff"
    assert len(plane.snapshot.participant_control_history[_PARTICIPANT]) == 1
    assert len(plane.snapshot.participant_crossing_history[_PARTICIPANT]) == 2
    assert len(plane._operations) == 1


def test_crossing_history_restarts_and_operation_replays_idempotently(tmp_path: Path) -> None:
    resolver = _StaticCrossingResolver()
    store_path = tmp_path / "control-plane"
    first = _action_plane(resolver, store=LocalControlPlaneStore(store_path))
    receipt = _admit(first, idempotency_key="restart-crossing")

    restarted_resolver = _StaticCrossingResolver()
    restarted_resolver.subjects = list(resolver.subjects)
    restarted_resolver.evidence_refs = set(resolver.evidence_refs)
    restarted = RuntimeControlPlane(
        _policy_capable_target(),
        store=LocalControlPlaneStore(store_path),
        crossing_policy_resolver=restarted_resolver,
    )
    retry = _admit(restarted, idempotency_key="restart-crossing")

    assert retry.operation_id == receipt.operation_id
    assert len(restarted.snapshot.participant_crossing_history[_PARTICIPANT]) == 2


class _FailingCommitStore(InMemoryControlPlaneStore):
    def commit_participant_transition(self, **kwargs: object) -> None:
        del kwargs
        raise RuntimeError("injected atomic write failure")


def test_atomic_write_failure_leaves_backend_and_histories_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = _StaticCrossingResolver()
    store = _FailingCommitStore()
    target = _policy_capable_target()
    runtime = target.participant_runtime
    assert runtime is not None
    original = runtime.admit_action
    calls = 0

    def tracked_admit_action(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime, "admit_action", tracked_admit_action)
    plane = _action_plane(resolver, store=store, target=target)

    with pytest.raises(RuntimeError, match="atomic write failure"):
        _admit(plane)

    assert calls == 0
    assert plane.snapshot.participant_crossing_history == {}
    assert plane.snapshot.participant_behavior_history == {}
    assert store.load_snapshot().participant_crossing_history == {}
    assert store.load_snapshot().participant_behavior_history == {}


class _BarrierResolver(_StaticCrossingResolver):
    def __init__(self, barrier: Barrier) -> None:
        super().__init__()
        self.barrier = barrier

    def resolve(
        self,
        intent: ParticipantCrossingIntent,
        snapshot: RuntimeSnapshot,
    ) -> ParticipantCrossingPolicyResolution:
        resolution = super().resolve(intent, snapshot)
        self.barrier.wait(timeout=5)
        return resolution


def test_concurrent_operation_cannot_commit_against_a_stale_history_cut() -> None:
    base = RuntimeControlPlane(
        _policy_capable_target(),
        crossing_policy_resolver=_StaticCrossingResolver(),
    )
    base.initialize_participant_episode(_PARTICIPANT, episode_id="episode-1")
    store = base._store
    barrier = Barrier(2)
    planes = [
        RuntimeControlPlane(
            _policy_capable_target(),
            store=store,
            crossing_policy_resolver=_BarrierResolver(barrier),
        )
        for _ in range(2)
    ]
    results: list[object] = []

    def run(index: int) -> None:
        try:
            results.append(
                _admit(
                    planes[index],
                    request=_admission_request(action_instance_id=f"concurrent-{index}"),
                    idempotency_key=f"concurrent-{index}",
                )
            )
        except Exception as exc:  # noqa: BLE001 - concurrency outcome is the assertion surface
            results.append(exc)

    threads = [Thread(target=run, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert any(
        "expected participant history head" in str(result) for result in results if isinstance(result, Exception)
    )
    durable = store.load_snapshot()
    assert len(durable.participant_crossing_history[_PARTICIPANT]) == 2


class _MissingPolicyResolver(_StaticCrossingResolver):
    def resolve(
        self,
        intent: ParticipantCrossingIntent,
        snapshot: RuntimeSnapshot,
    ) -> ParticipantCrossingPolicyResolution:
        del intent, snapshot
        raise ValueError("secret policy lookup detail")


def test_missing_policy_fails_closed_with_safe_diagnostic_and_audit() -> None:
    plane = _action_plane(_MissingPolicyResolver())

    receipt = _admit(plane, idempotency_key="missing-policy")

    assert receipt.accepted is False
    assert plane.snapshot.participant_behavior_history == {}
    assert plane.snapshot.participant_crossing_history == {}
    assert receipt.diagnostics[0].code == "runtime.participant-crossing-policy-unresolved"
    assert "secret" not in receipt.diagnostics[0].message
    assert plane.audit_log()[-1].reason == "policy-unresolved"


def test_runtime_exposes_no_detached_crossing_recorder() -> None:
    plane = _action_plane(_StaticCrossingResolver())

    assert not hasattr(plane, "record_participant_crossing")
