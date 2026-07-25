"""DSL-437 benign participant autonomous execution semantics and runtime."""

from __future__ import annotations

import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from aces_backend_protocols.capability_admission import participant_autonomous_execution_capability_gaps
from aces_backend_protocols.participant_runtime_base import BaseParticipantRuntime
from aces_backend_stubs.manifest import create_stub_manifest
from aces_backend_stubs.stubs import create_stub_target
from aces_contracts.contracts import (
    ParticipantActionResultModel,
    ParticipantAutonomousExecutionStateModel,
    ParticipantImplementationManifestModel,
    ParticipantImplementationSelectionModel,
    RuntimeSnapshotEnvelopeModel,
)
from aces_contracts.contracts.time_model import TimeRuntimeStateModel
from aces_contracts.participant_binding import (
    ParticipantActionAdmissionRequest,
    ParticipantActionApplyResult,
    ParticipantNativeActionExecution,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeInitializeRequest,
    ParticipantEpisodeResetRequest,
)
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from aces_processor.compiler import compile_runtime_model
from aces_processor.compiler.time_model import time_model_contract_model
from aces_processor.planner import plan
from aces_runtime.manager import RuntimeManager
from aces_runtime.participant_clock_driver import ParticipantClockDriver
from aces_runtime.participant_scheduler import ParticipantScheduler
from aces_runtime.time_coordinator import ReferenceTimeRuntime, TimeCoordinator
from aces_sdl._errors import SDLValidationError
from aces_sdl.parser import parse_sdl
from aces_sdl.participant_behavior import ParticipantFailureClass

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = REPO_ROOT / "examples" / "scenarios" / "enterprise-participant-evidence-loop.sdl.yaml"
IMPLEMENTATION_REF = "participant-implementation-manifests.green-worker.v1"


def _scenario_yaml(*, role: str = "green") -> str:
    payload = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    payload["entities"]["enterprise-participant"]["role"] = role
    payload["objectives"] = {}
    payload["workflows"] = {}
    payload["outcome_interpretation_rules"] = {}
    specification = payload["behavior_specifications"]["participant-behavior"]
    specification["participant_role_refs"] = [role]
    specification["outcome_interpretation_rule_refs"] = []
    specification["authority_scope_refs"] = []
    specification["behavior_mode"] = "autonomous"
    specification["backend_feature_support_refs"] = [
        "action_contracts",
        "autonomous_execution",
        "behavior_history",
        "observation_boundaries",
        "temporal_contracts",
    ]
    specification["autonomous_execution"] = {
        "participant_implementation_ref": IMPLEMENTATION_REF,
        "clock_ref": "scenario-clock",
        "progression_policy_ref": "scenario-progression",
        "temporal_constraint_refs": ["green-cadence"],
        "action_order": ["probe-customer-portal-login"],
        "observation_boundary_ref": "participant-view",
        "selection_strategy": "ordered_cycle",
        "max_action_attempts": 2,
        "max_in_flight": 1,
        "failure_policy": "stop",
        "evaluation_authority": {"mode": "none"},
    }
    payload["time_domains"] = {
        "scenario": {
            "kind": "simulated",
            "tick_period_seconds": {"numerator": 1, "denominator": 1},
            "epoch": "scenario_start",
            "visibility": "participant_visible",
            "description": "Exact shared scenario time for benign participant actions.",
        }
    }
    payload["clocks"] = {
        "scenario-clock": {
            "time_domain_ref": "scenario",
            "authority_kind": "runtime",
            "authority_ref": "runtime.time-coordinator",
            "monotonicity": "non_decreasing",
            "supports_pause": True,
            "supports_reset": True,
            "description": "Authoritative shared scenario clock.",
        }
    }
    payload["time_progression_policies"] = {
        "scenario-progression": {
            "clock_ref": "scenario-clock",
            "advancement_mode": "stepped",
            "synchronization_mode": "barrier",
            "step_ticks": 10,
            "reset_behavior": "new_segment_zero",
            "replay_behavior": "restore_recorded_advances",
            "description": "Deterministic stepped progression.",
        }
    }
    payload["temporal_constraints"] = {
        "green-cadence": {
            "constraint_kind": "cadence",
            "clock_ref": "scenario-clock",
            "subject_refs": ["nodes.customer-portal"],
            "start": {"tick": 0},
            "cadence_ticks": 10,
            "description": "One benign participant action every ten ticks.",
        }
    }
    return yaml.safe_dump(payload, sort_keys=False)


def _implementation_manifest() -> ParticipantImplementationManifestModel:
    return ParticipantImplementationManifestModel.model_validate(
        {
            "schema_version": "participant-implementation-manifest/v1",
            "identity": {"name": "green-worker", "version": "1.0.0"},
            "implementation_kind": "agent",
            "supported_contract_versions": [
                "participant-implementation-manifest-v1",
                "participant-implementation-provenance-v1",
                "participant-episode-state-envelope-v1",
                "participant-episode-history-event-stream-v1",
                "participant-behavior-history-event-stream-v1",
            ],
            "compatibility": {"participant_runtimes": ["test-runtime"]},
            "concept_bindings": [
                {"scope": "implementation_kind", "family": "apparatus-declarations"},
                {
                    "scope": "capabilities.supported_participant_contracts",
                    "family": "apparatus-declarations",
                },
                {
                    "scope": "capabilities.supported_decision_surface_modes",
                    "family": "apparatus-declarations",
                },
                {
                    "scope": "capabilities.tool_affordance_expectations",
                    "family": "tools-and-artifacts",
                },
                {
                    "scope": "capabilities.exposure_policy_kinds",
                    "family": "provenance-and-evidence",
                },
            ],
            "capabilities": {
                "supported_participant_contracts": [
                    "participant-episode-state-envelope-v1",
                    "participant-episode-history-event-stream-v1",
                    "participant-behavior-history-event-stream-v1",
                ],
                "supported_decision_surface_modes": ["autonomous"],
                "tool_affordance_expectations": ["http-api"],
                "exposure_policy_kinds": ["observation-stream"],
            },
        }
    )


def _selection(participant_address: str) -> ParticipantImplementationSelectionModel:
    return ParticipantImplementationSelectionModel.model_validate(
        {
            "participant_address": participant_address,
            "implementation_identity": {"name": "green-worker", "version": "1.0.0"},
            "manifest_ref": IMPLEMENTATION_REF,
            "manifest_digest": "sha256:" + "1" * 64,
            "selected_decision_surface_mode": "autonomous",
            "participant_contract_versions": [
                "participant-episode-state-envelope-v1",
                "participant-behavior-history-event-stream-v1",
            ],
            "exposure_policy": {
                "policy_id": "green-worker-policy",
                "policy_version": "1.0.0",
                "policy_digest": "sha256:" + "2" * 64,
                "exposure_policy_kinds": ["observation-stream"],
                "disclosed_refs": ["content.task-brief"],
                "withheld_refs": ["content.evaluator-notes"],
                "tool_affordance_refs": [],
                "visibility_scope_refs": ["participants.green.visible"],
            },
        }
    )


class _NativeParticipantRuntime(BaseParticipantRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.native_actions: list[str] = []

    def _model_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
        *,
        episode_id: str,
    ) -> ParticipantNativeActionExecution:
        self.native_actions.append(request.action_instance_id)
        metadata = dict(snapshot.metadata)
        metadata["last_native_action"] = request.action_instance_id
        return ParticipantNativeActionExecution(
            apply_result=ApplyResult(
                success=True,
                snapshot=snapshot.with_entries(dict(snapshot.entries), metadata=metadata),
                changed_addresses=["native.service.customer-portal"],
            ),
            action_result=ParticipantActionResultModel(
                status="succeeded",
                participant_address=request.participant_address,
                episode_id=episode_id,
                action_instance_id=request.action_instance_id,
                action_contract_address=request.action_contract_address,
                observation_point=request.temporal_contexts[0].observation_point,
                observations=["customer portal responded"],
                evidence_refs=[],
            ),
        )

    def bind_autonomous_action(
        self,
        participant_address: str,
        action_contract_address: str,
        observation_boundary_address: str,
        participant_implementation_ref: str,
        action_instance_id: str,
        temporal_contexts: tuple[object, ...],
        snapshot: RuntimeSnapshot,
    ) -> ParticipantActionAdmissionRequest:
        del participant_implementation_ref, snapshot
        return ParticipantActionAdmissionRequest(
            participant_address=participant_address,
            action_contract_address=action_contract_address,
            observation_boundary_address=observation_boundary_address,
            action_instance_id=action_instance_id,
            implementation_manifest=_implementation_manifest(),
            implementation_selection=_selection(participant_address),
            temporal_contexts=temporal_contexts,
        )


class _FailedParticipantRuntime(_NativeParticipantRuntime):
    def _model_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
        *,
        episode_id: str,
    ) -> ParticipantNativeActionExecution:
        execution = super()._model_action(request, snapshot, episode_id=episode_id)
        assert execution.action_result is not None
        return replace(
            execution,
            action_result=execution.action_result.model_copy(
                update={
                    "status": "failed",
                    "failure_class": ParticipantFailureClass.TARGET_UNAVAILABLE,
                }
            ),
        )


class _MissingOutcomeRuntime(_NativeParticipantRuntime):
    def _model_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
        *,
        episode_id: str,
    ) -> ParticipantNativeActionExecution:
        execution = super()._model_action(request, snapshot, episode_id=episode_id)
        return replace(execution, action_result=None)


class _ContradictoryTimeRuntime(_NativeParticipantRuntime):
    def _model_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
        *,
        episode_id: str,
    ) -> ParticipantNativeActionExecution:
        execution = super()._model_action(request, snapshot, episode_id=episode_id)
        assert execution.action_result is not None
        return replace(
            execution,
            action_result=execution.action_result.model_copy(
                update={"observation_point": "time.clock.scenario-clock@segment=9,tick=999"}
            ),
        )


class _ResetFailParticipantRuntime(_NativeParticipantRuntime):
    def reset(self, request: object, snapshot: RuntimeSnapshot) -> ApplyResult:
        del request
        return ApplyResult(success=False, snapshot=snapshot)


class _SecondResetFailParticipantRuntime(_NativeParticipantRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.reset_calls = 0

    def reset(
        self,
        request: ParticipantEpisodeResetRequest,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult:
        self.reset_calls += 1
        if self.reset_calls == 2:
            return ApplyResult(success=False, snapshot=snapshot)
        return super().reset(request, snapshot)


class _NoBatchResetParticipantRuntime(_NativeParticipantRuntime):
    reset_many = None


class _PlainApplyParticipantRuntime(_NativeParticipantRuntime):
    def admit_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult:
        result = super().admit_action(request, snapshot)
        return ApplyResult(
            success=result.success,
            snapshot=result.snapshot,
            diagnostics=result.diagnostics,
            changed_addresses=result.changed_addresses,
        )


class _NonResultParticipantRuntime(_NativeParticipantRuntime):
    def admit_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
    ) -> object:
        del request, snapshot
        return object()


class _DirectContradictoryParticipantRuntime(_NativeParticipantRuntime):
    def admit_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
    ) -> ParticipantActionApplyResult:
        episode = snapshot.participant_episode_results[request.participant_address]
        mutated = snapshot.with_entries(
            dict(snapshot.entries),
            metadata={**snapshot.metadata, "direct_native_mutation": True},
        )
        return ParticipantActionApplyResult(
            success=True,
            snapshot=mutated,
            changed_addresses=[request.participant_address],
            action_result=ParticipantActionResultModel(
                status="succeeded",
                participant_address=request.participant_address,
                episode_id=episode["episode_id"],
                action_instance_id=request.action_instance_id,
                action_contract_address=request.action_contract_address,
                observation_point="time.clock.other@segment=0,tick=0",
            ),
        )


class _StaleHistoryParticipantRuntime(_NativeParticipantRuntime):
    def admit_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
    ) -> ParticipantActionApplyResult:
        result = super().admit_action(request, snapshot)
        return replace(
            result,
            snapshot=result.snapshot.with_entries(
                dict(result.snapshot.entries),
                participant_behavior_history={
                    address: list(events) for address, events in snapshot.participant_behavior_history.items()
                },
            ),
        )


class _IncompleteHistoryParticipantRuntime(_NativeParticipantRuntime):
    def admit_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
    ) -> ParticipantActionApplyResult:
        result = super().admit_action(request, snapshot)
        history = {address: list(events) for address, events in result.snapshot.participant_behavior_history.items()}
        history[request.participant_address] = history[request.participant_address][:-1]
        return replace(
            result,
            snapshot=result.snapshot.with_entries(
                dict(result.snapshot.entries),
                participant_behavior_history=history,
            ),
        )


class _WrongProvenanceParticipantRuntime(_NativeParticipantRuntime):
    def admit_action(
        self,
        request: ParticipantActionAdmissionRequest,
        snapshot: RuntimeSnapshot,
    ) -> ParticipantActionApplyResult:
        result = super().admit_action(request, snapshot)
        history = {address: list(events) for address, events in result.snapshot.participant_behavior_history.items()}
        attempted = dict(history[request.participant_address][0])
        attempted["actor_provenance"] = "participant-implementation:wrong@9.9.9"
        history[request.participant_address][0] = attempted
        return replace(
            result,
            snapshot=result.snapshot.with_entries(
                dict(result.snapshot.entries),
                participant_behavior_history=history,
            ),
        )


class _BlockingReadTimeRuntime(ReferenceTimeRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.block_reads = False
        self.read_entered = threading.Event()
        self.read_release = threading.Event()

    def state(self, snapshot: RuntimeSnapshot) -> TimeRuntimeStateModel:
        if self.block_reads:
            self.read_entered.set()
            self.read_release.wait(timeout=1.0)
        return super().state(snapshot)


def _compiled() -> tuple[object, object]:
    runtime_model = compile_runtime_model(parse_sdl(_scenario_yaml()))
    specification = runtime_model.behavior_specifications["participant.behavior-specification.participant-behavior"]
    assert specification.autonomous_execution is not None
    return runtime_model, specification.autonomous_execution


def _autonomous_manifest(runtime_model: object) -> object:
    policies = tuple(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )
    base_manifest = create_stub_manifest(with_time=True)
    assert base_manifest.participant_runtime is not None
    return replace(
        base_manifest,
        capabilities=replace(
            base_manifest.capabilities,
            participant_runtime=replace(
                base_manifest.participant_runtime,
                supported_behavior_features=(
                    base_manifest.participant_runtime.supported_behavior_features | {"autonomous_execution"}
                ),
                supports_autonomous_execution=True,
                supported_autonomous_selection_strategies=frozenset({"ordered_cycle"}),
                supported_autonomous_action_contracts=frozenset(
                    address for policy in policies for address in policy.action_contract_addresses
                ),
                supported_autonomous_observation_boundaries=frozenset(
                    policy.observation_boundary_address for policy in policies
                ),
                supported_autonomous_target_addresses=frozenset(
                    address for policy in policies for address in policy.target_addresses
                ),
                max_autonomous_participants=8,
                max_autonomous_action_attempts=8,
                max_autonomous_in_flight=1,
            ),
        ),
    )


def test_autonomous_execution_compiles_existing_participant_and_shared_time_refs() -> None:
    runtime_model, policy = _compiled()

    assert policy.participant_addresses == ("participant.behavior.participant-agent",)
    assert policy.action_contract_addresses == ("participant.action-contract.probe-customer-portal-login",)
    assert policy.clock_address == "time.clock.scenario-clock"
    assert policy.progression_policy_address == "time.policy.scenario-progression"
    assert policy.temporal_constraint_addresses == ("time.constraint.green-cadence",)
    assert "provision.node.customer-portal.service.http" in policy.target_addresses
    assert runtime_model.time_model.constraints[0].cadence_ticks == 10
    action = runtime_model.action_contracts["participant.action-contract.probe-customer-portal-login"]
    assert action.interaction_classes == ("shared_state_change",)
    assert action.shared_state_refs == ("nodes.customer-portal.services.http",)


def test_non_evaluated_autonomous_participant_must_be_green() -> None:
    scenario_yaml = _scenario_yaml(role="red")

    with pytest.raises(SDLValidationError, match="must have the green role"):
        parse_sdl(scenario_yaml)


def test_non_evaluated_autonomous_participant_cannot_widen_evaluation_authority() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["behavior_specifications"]["participant-behavior"]["authority_scope_refs"] = [
        "nodes.customer-portal.services.http"
    ]
    scenario_yaml = yaml.safe_dump(payload, sort_keys=False)

    with pytest.raises(SDLValidationError, match="cannot carry outcome-interpretation or authority-scope refs"):
        parse_sdl(scenario_yaml)


def test_autonomous_execution_requires_exactly_one_shared_clock_cadence() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["temporal_constraints"]["second-cadence"] = {
        **payload["temporal_constraints"]["green-cadence"],
        "cadence_ticks": 20,
    }
    payload["behavior_specifications"]["participant-behavior"]["autonomous_execution"][
        "temporal_constraint_refs"
    ].append("second-cadence")
    scenario_yaml = yaml.safe_dump(payload, sort_keys=False)

    with pytest.raises(SDLValidationError, match="requires exactly one cadence constraint"):
        parse_sdl(scenario_yaml)


def test_autonomous_participant_has_exactly_one_scheduler_owner() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["behavior_specifications"]["second-participant-behavior"] = {
        **payload["behavior_specifications"]["participant-behavior"],
    }
    scenario_yaml = yaml.safe_dump(payload, sort_keys=False)

    with pytest.raises(SDLValidationError, match="already controlled by behavior specification"):
        parse_sdl(scenario_yaml)


def test_backend_admission_enforces_finite_autonomous_execution_limits() -> None:
    runtime_model, _ = _compiled()
    policies = tuple(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )
    manifest = _autonomous_manifest(runtime_model)
    assert participant_autonomous_execution_capability_gaps(manifest, policies) == ()

    assert manifest.participant_runtime is not None
    constrained = replace(
        manifest,
        capabilities=replace(
            manifest.capabilities,
            participant_runtime=replace(
                manifest.participant_runtime,
                max_autonomous_action_attempts=1,
            ),
        ),
    )
    gaps = participant_autonomous_execution_capability_gaps(constrained, policies)
    assert len(gaps) == 1

    assert constrained.time is not None
    no_transaction = replace(
        constrained,
        capabilities=replace(
            constrained.capabilities,
            time=replace(
                constrained.time,
                supports_coordinated_participant_reset=False,
            ),
        ),
    )
    gaps = participant_autonomous_execution_capability_gaps(
        no_transaction,
        policies,
        runtime_model.time_model,
    )
    assert "autonomous clock reset requires coordinated participant reset support" in gaps
    assert "action attempts" in gaps[0]


def test_planner_enforces_required_participant_features_and_exact_targets() -> None:
    runtime_model, _ = _compiled()
    manifest = _autonomous_manifest(runtime_model)
    assert manifest.participant_runtime is not None
    unsupported = replace(
        manifest,
        capabilities=replace(
            manifest.capabilities,
            participant_runtime=replace(
                manifest.participant_runtime,
                supported_behavior_features=frozenset({"autonomous_execution"}),
                supported_autonomous_target_addresses=frozenset(),
            ),
        ),
    )

    execution_plan = plan(runtime_model, unsupported)

    messages = [diagnostic.message for diagnostic in execution_plan.diagnostics]
    assert any("required participant feature 'action_contracts'" in message for message in messages)
    assert any("unsupported autonomous target addresses" in message for message in messages)


def test_runtime_manager_drives_due_actions_from_shared_clock_controls() -> None:
    scenario = parse_sdl(_scenario_yaml())
    runtime_model = compile_runtime_model(scenario)
    participant_runtime = _NativeParticipantRuntime()
    target = replace(
        create_stub_target(),
        manifest=_autonomous_manifest(runtime_model),
        participant_runtime=participant_runtime,
    )
    manager = RuntimeManager(target)

    applied = manager.apply(manager.plan(scenario))

    assert applied.success
    assert len(participant_runtime.native_actions) == 1
    policy = next(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )
    skipped = manager.advance_time(policy.clock_address, ticks=20)
    assert not skipped.success
    assert skipped.diagnostics[0].code == "runtime.participant-autonomous-cadence-skipped"
    assert manager.read_time_state().clocks[policy.clock_address].coordinate.tick == 0
    paused = manager.pause_time(policy.clock_address)
    assert paused.success
    assert any(
        address.endswith(".state.participant.behavior.participant-agent") for address in paused.changed_addresses
    )
    resumed = manager.resume_time(policy.clock_address)
    assert resumed.success
    advanced = manager.advance_time(policy.clock_address, ticks=10)
    assert advanced.success
    assert len(participant_runtime.native_actions) == 2
    state = ParticipantAutonomousExecutionStateModel.model_validate(
        next(iter(advanced.snapshot.participant_autonomous_execution_states.values()))
    )
    assert state.lifecycle_state == "completed"
    reset = manager.reset_time(policy.clock_address)
    assert reset.success
    assert len(participant_runtime.native_actions) == 2
    reset_state = ParticipantAutonomousExecutionStateModel.model_validate(
        next(iter(reset.snapshot.participant_autonomous_execution_states.values()))
    )
    assert (reset_state.time_segment, reset_state.attempted_actions, reset_state.next_tick) == (1, 0, 0)
    due = manager.run_due_participant_actions()
    assert due.success
    assert len(participant_runtime.native_actions) == 3


def test_runtime_manager_rolls_back_clock_when_participant_reset_fails() -> None:
    scenario = parse_sdl(_scenario_yaml())
    runtime_model = compile_runtime_model(scenario)
    participant_runtime = _ResetFailParticipantRuntime()
    target = replace(
        create_stub_target(),
        manifest=_autonomous_manifest(runtime_model),
        participant_runtime=participant_runtime,
    )
    manager = RuntimeManager(target)
    applied = manager.apply(manager.plan(scenario))
    predecessor = applied.snapshot
    policy = next(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )

    reset = manager.reset_time(policy.clock_address)

    assert not reset.success
    assert reset.snapshot == predecessor
    assert manager.snapshot == predecessor
    state = ParticipantAutonomousExecutionStateModel.model_validate(
        next(iter(manager.snapshot.participant_autonomous_execution_states.values()))
    )
    assert state.time_segment == 0
    assert manager.read_time_state().clocks[policy.clock_address].coordinate.segment == 0


def test_reference_batch_reset_restores_base_state_when_second_participant_reset_fails() -> None:
    runtime_model, policy = _compiled()
    declaration = time_model_contract_model(runtime_model.time_model)
    assert declaration is not None
    participant_runtime = _NativeParticipantRuntime()
    time_runtime = ReferenceTimeRuntime()
    snapshot = time_runtime.initialize(declaration, RuntimeSnapshot()).snapshot
    participant_address = "participant.behavior.participant-agent"
    snapshot = participant_runtime.initialize(
        ParticipantEpisodeInitializeRequest(participant_address=participant_address),
        snapshot,
    ).snapshot
    predecessor_results = participant_runtime.results()
    predecessor_history = participant_runtime.history()
    requests = (
        ParticipantEpisodeResetRequest(participant_address=participant_address),
        ParticipantEpisodeResetRequest(participant_address="participant.behavior.missing"),
    )

    reset = time_runtime.reset_with_participants(
        policy.clock_address,
        False,
        participant_runtime,
        requests,
        snapshot,
    )

    assert not reset.success
    assert reset.snapshot == snapshot
    assert participant_runtime.results() == predecessor_results
    assert participant_runtime.history() == predecessor_history


def test_base_batch_reset_refuses_subclass_native_reset_without_atomic_override() -> None:
    participant_runtime = _SecondResetFailParticipantRuntime()
    address = "participant.behavior.participant-agent"
    snapshot = participant_runtime.initialize(
        ParticipantEpisodeInitializeRequest(participant_address=address),
        RuntimeSnapshot(),
    ).snapshot

    result = participant_runtime.reset_many(
        (ParticipantEpisodeResetRequest(participant_address=address),),
        snapshot,
    )

    assert not result.success
    assert result.snapshot == snapshot
    assert participant_runtime.reset_calls == 0
    assert "must implement their own atomic reset_many" in result.diagnostics[0].message


def test_runtime_target_rejects_autonomous_claim_without_native_binding_method() -> None:
    runtime_model, _ = _compiled()
    target = create_stub_target()
    manifest = _autonomous_manifest(runtime_model)

    with pytest.raises(ValueError, match="bind_autonomous_action"):
        replace(target, manifest=manifest)


def test_runtime_target_rejects_coordinated_reset_claim_without_batch_reset_method() -> None:
    runtime_model, _ = _compiled()
    target = create_stub_target()
    manifest = _autonomous_manifest(runtime_model)
    participant_runtime = _NoBatchResetParticipantRuntime()

    with pytest.raises(ValueError, match="reset_many"):
        replace(
            target,
            manifest=manifest,
            participant_runtime=participant_runtime,
        )


def test_scheduler_executes_native_actions_and_persists_shared_time_readback() -> None:
    runtime_model, policy = _compiled()
    scheduler = ParticipantScheduler()
    participant_runtime = _NativeParticipantRuntime()
    coordinator = TimeCoordinator(runtime_model.time_model)
    snapshot = coordinator.initialize()

    initialized = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        snapshot,
    )
    assert initialized.success
    first = scheduler.run_due(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        initialized.snapshot,
    )
    assert first.success
    assert participant_runtime.native_actions == [
        "participant.autonomous-execution.participant-behavior:participant.behavior.participant-agent:0"
    ]
    assert first.snapshot.metadata["last_native_action"] == participant_runtime.native_actions[0]

    state_key = "participant.autonomous-execution.participant-behavior.state.participant.behavior.participant-agent"
    state = ParticipantAutonomousExecutionStateModel.model_validate(
        first.snapshot.participant_autonomous_execution_states[state_key]
    )
    assert (state.attempted_actions, state.succeeded_actions, state.next_tick) == (1, 1, 10)
    assert state.time_segment == 0
    assert state.policy_digest.startswith("sha256:")
    events = first.snapshot.participant_behavior_history[state.participant_address]
    assert [event["event_type"] for event in events] == [
        "action_attempted",
        "state_transition_recorded",
        "observation_emitted",
    ]
    assert all(
        event["temporal_contexts"][0]["temporal_contract_id"] == "time.constraint.green-cadence" for event in events
    )
    assert all("segment=0,tick=0" in event["temporal_contexts"][0]["observation_point"] for event in events)

    reapplied = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        first.snapshot,
    )
    preserved = ParticipantAutonomousExecutionStateModel.model_validate(
        reapplied.snapshot.participant_autonomous_execution_states[state_key]
    )
    assert preserved.attempted_actions == 1

    paused = scheduler.set_clock_lifecycle(reapplied.snapshot, policy.clock_address, "paused").snapshot
    paused_state = ParticipantAutonomousExecutionStateModel.model_validate(
        paused.participant_autonomous_execution_states[state_key]
    )
    assert paused_state.lifecycle_state == "paused"
    resumed = scheduler.set_clock_lifecycle(paused, policy.clock_address, "running").snapshot

    advanced = coordinator.advance(resumed, policy.clock_address, ticks=10)
    second = scheduler.run_due(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        advanced,
    )
    completed = ParticipantAutonomousExecutionStateModel.model_validate(
        second.snapshot.participant_autonomous_execution_states[state_key]
    )
    assert completed.lifecycle_state == "completed"
    assert completed.attempted_actions == 2

    reset_time = coordinator.reset(second.snapshot, policy.clock_address)
    reset = scheduler.reset_clock(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        reset_time,
        policy.clock_address,
    )
    reset_state = ParticipantAutonomousExecutionStateModel.model_validate(
        reset.snapshot.participant_autonomous_execution_states[state_key]
    )
    assert (reset_state.lifecycle_state, reset_state.attempted_actions, reset_state.next_tick) == (
        "running",
        0,
        0,
    )
    assert reset.snapshot.participant_episode_results[state.participant_address]["sequence_number"] == 1


def test_scheduler_rejects_reapplication_after_material_policy_change() -> None:
    runtime_model, policy = _compiled()
    scheduler = ParticipantScheduler()
    participant_runtime = _NativeParticipantRuntime()
    snapshot = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        TimeCoordinator(runtime_model.time_model).initialize(),
    ).snapshot

    changed = scheduler.initialize(
        [replace(policy, max_action_attempts=policy.max_action_attempts + 1)],
        runtime_model.time_model,
        participant_runtime,
        snapshot,
    )

    assert not changed.success
    assert changed.diagnostics[0].code == "runtime.participant-autonomous-state-conflict"


def test_scheduler_rejects_reapplication_after_referenced_cadence_change() -> None:
    runtime_model, policy = _compiled()
    scheduler = ParticipantScheduler()
    participant_runtime = _NativeParticipantRuntime()
    snapshot = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        TimeCoordinator(runtime_model.time_model).initialize(),
    ).snapshot
    changed_constraint = replace(runtime_model.time_model.constraints[0], cadence_ticks=20)
    changed_time_model = replace(runtime_model.time_model, constraints=(changed_constraint,))

    changed = scheduler.initialize(
        [policy],
        changed_time_model,
        participant_runtime,
        snapshot,
    )

    assert not changed.success
    assert changed.diagnostics[0].code == "runtime.participant-autonomous-state-conflict"


def test_scheduler_counts_native_action_outcome_not_control_plane_success() -> None:
    runtime_model, policy = _compiled()
    scheduler = ParticipantScheduler()
    participant_runtime = _FailedParticipantRuntime()
    initialized = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        TimeCoordinator(runtime_model.time_model).initialize(),
    )

    result = scheduler.run_due(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        initialized.snapshot,
    )

    assert not result.success
    state = ParticipantAutonomousExecutionStateModel.model_validate(
        next(iter(result.snapshot.participant_autonomous_execution_states.values()))
    )
    assert (state.lifecycle_state, state.succeeded_actions, state.failed_actions) == ("failed", 0, 1)
    observation = result.snapshot.participant_behavior_history[state.participant_address][-1]
    assert observation["action_result"]["status"] == "failed"


@pytest.mark.parametrize("runtime_type", [_MissingOutcomeRuntime, _ContradictoryTimeRuntime])
def test_scheduler_rejects_invalid_native_outcome_before_committing_history_or_snapshot(
    runtime_type: type[_NativeParticipantRuntime],
) -> None:
    runtime_model, policy = _compiled()
    scheduler = ParticipantScheduler()
    participant_runtime = runtime_type()
    initialized = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        TimeCoordinator(runtime_model.time_model).initialize(),
    )

    result = scheduler.run_due(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        initialized.snapshot,
    )

    assert not result.success
    assert "last_native_action" not in result.snapshot.metadata
    assert result.snapshot.participant_behavior_history == {}
    state = ParticipantAutonomousExecutionStateModel.model_validate(
        next(iter(result.snapshot.participant_autonomous_execution_states.values()))
    )
    assert (state.lifecycle_state, state.attempted_actions, state.failed_actions) == ("failed", 1, 1)
    repeated = scheduler.run_due(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        result.snapshot,
    )
    assert repeated.success
    assert len(participant_runtime.native_actions) == 1


@pytest.mark.parametrize(
    "runtime_type",
    [
        _PlainApplyParticipantRuntime,
        _NonResultParticipantRuntime,
        _DirectContradictoryParticipantRuntime,
        _StaleHistoryParticipantRuntime,
        _IncompleteHistoryParticipantRuntime,
        _WrongProvenanceParticipantRuntime,
    ],
)
def test_scheduler_fails_closed_for_nonconforming_direct_runtime(
    runtime_type: type[_NativeParticipantRuntime],
) -> None:
    runtime_model, policy = _compiled()
    scheduler = ParticipantScheduler()
    participant_runtime = runtime_type()
    initialized = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        TimeCoordinator(runtime_model.time_model).initialize(),
    )

    result = scheduler.run_due(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        initialized.snapshot,
    )

    assert not result.success
    assert result.diagnostics[-1].code == "runtime.participant-autonomous-action-protocol-invalid"
    assert "direct_native_mutation" not in result.snapshot.metadata
    assert result.snapshot.participant_behavior_history == {}


def test_semantics_rejects_unreachable_stepped_cadence() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["temporal_constraints"]["green-cadence"]["cadence_ticks"] = 5
    scenario_yaml = yaml.safe_dump(payload, sort_keys=False)

    with pytest.raises(SDLValidationError, match="cadence points are unreachable"):
        parse_sdl(scenario_yaml)


def test_semantics_rejects_externally_paced_autonomous_clock_without_driver() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    progression = payload["time_progression_policies"]["scenario-progression"]
    progression["advancement_mode"] = "externally_paced"
    progression.pop("step_ticks")
    scenario_yaml = yaml.safe_dump(payload, sort_keys=False)

    with pytest.raises(SDLValidationError, match="has no portable runtime transition driver"):
        parse_sdl(scenario_yaml)


def test_semantics_rejects_negative_autonomous_cadence_start() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["temporal_constraints"]["green-cadence"]["start"]["tick"] = -10
    scenario_yaml = yaml.safe_dump(payload, sort_keys=False)

    with pytest.raises(SDLValidationError, match="cadence points are unreachable"):
        parse_sdl(scenario_yaml)


def test_semantics_rejects_backend_authority_for_wall_paced_autonomous_clock() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    progression = payload["time_progression_policies"]["scenario-progression"]
    progression["advancement_mode"] = "real_time"
    progression.pop("step_ticks")
    payload["clocks"]["scenario-clock"]["authority_kind"] = "backend"
    payload["clocks"]["scenario-clock"]["authority_ref"] = "backend.clock"
    scenario_yaml = yaml.safe_dump(payload, sort_keys=False)

    with pytest.raises(SDLValidationError, match="must use runtime authority"):
        parse_sdl(scenario_yaml)


def test_runtime_manager_automatically_drives_wall_paced_participant_clock() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["time_domains"]["scenario"]["tick_period_seconds"] = {"numerator": 1, "denominator": 100}
    progression = payload["time_progression_policies"]["scenario-progression"]
    progression["advancement_mode"] = "real_time"
    progression.pop("step_ticks")
    payload["temporal_constraints"]["green-cadence"]["cadence_ticks"] = 1
    scenario = parse_sdl(yaml.safe_dump(payload, sort_keys=False))
    runtime_model = compile_runtime_model(scenario)
    participant_runtime = _NativeParticipantRuntime()
    target = replace(
        create_stub_target(),
        manifest=_autonomous_manifest(runtime_model),
        participant_runtime=participant_runtime,
    )
    manager = RuntimeManager(target)

    applied = manager.apply(manager.plan(scenario))
    deadline = time.monotonic() + 1.0
    while len(participant_runtime.native_actions) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)

    assert applied.success
    assert len(participant_runtime.native_actions) == 2
    assert manager.participant_clock_driver_status()["active"] is True
    manager.destroy()
    assert manager.participant_clock_driver_status()["active"] is False


def test_wall_driver_cannot_advance_during_time_state_readback() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["time_domains"]["scenario"]["tick_period_seconds"] = {"numerator": 1, "denominator": 20}
    progression = payload["time_progression_policies"]["scenario-progression"]
    progression["advancement_mode"] = "real_time"
    progression.pop("step_ticks")
    payload["temporal_constraints"]["green-cadence"]["cadence_ticks"] = 1
    scenario = parse_sdl(yaml.safe_dump(payload, sort_keys=False))
    runtime_model = compile_runtime_model(scenario)
    time_runtime = _BlockingReadTimeRuntime()
    manager = RuntimeManager(
        replace(
            create_stub_target(),
            manifest=_autonomous_manifest(runtime_model),
            participant_runtime=_NativeParticipantRuntime(),
            time_runtime=time_runtime,
        )
    )
    assert manager.apply(manager.plan(scenario)).success
    policy = next(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )
    time_runtime.block_reads = True
    outcome: list[TimeRuntimeStateModel | Exception] = []

    def read_state() -> None:
        try:
            outcome.append(manager.read_time_state())
        except Exception as exc:
            outcome.append(exc)

    reader = threading.Thread(target=read_state)
    reader.start()
    assert time_runtime.read_entered.wait(timeout=1.0)
    predecessor = manager.snapshot
    time.sleep(0.1)

    assert manager.snapshot == predecessor
    time_runtime.read_release.set()
    reader.join(timeout=1.0)
    assert not reader.is_alive()
    assert len(outcome) == 1
    assert not isinstance(outcome[0], Exception)
    state = outcome[0]
    assert isinstance(state, TimeRuntimeStateModel)
    assert state.clocks[policy.clock_address].coordinate.tick == 0
    assert manager.destroy().success


def test_wall_driver_recomputes_after_pause_and_resume() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["time_domains"]["scenario"]["tick_period_seconds"] = {"numerator": 1, "denominator": 5}
    progression = payload["time_progression_policies"]["scenario-progression"]
    progression["advancement_mode"] = "real_time"
    progression.pop("step_ticks")
    payload["temporal_constraints"]["green-cadence"]["cadence_ticks"] = 1
    scenario = parse_sdl(yaml.safe_dump(payload, sort_keys=False))
    runtime_model = compile_runtime_model(scenario)
    participant_runtime = _NativeParticipantRuntime()
    manager = RuntimeManager(
        replace(
            create_stub_target(),
            manifest=_autonomous_manifest(runtime_model),
            participant_runtime=participant_runtime,
        )
    )
    assert manager.apply(manager.plan(scenario)).success
    policy = next(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )

    assert manager.pause_time(policy.clock_address).success
    time.sleep(0.25)
    assert manager.read_time_state().clocks[policy.clock_address].coordinate.tick == 0
    assert manager.resume_time(policy.clock_address).success
    deadline = time.monotonic() + 1.0
    while len(participant_runtime.native_actions) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)

    assert len(participant_runtime.native_actions) == 2
    assert manager.participant_clock_driver_status()["failure"] is None
    assert manager.destroy().success


def test_wall_driver_discards_transition_stale_after_manual_advance() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["time_domains"]["scenario"]["tick_period_seconds"] = {"numerator": 1, "denominator": 5}
    progression = payload["time_progression_policies"]["scenario-progression"]
    progression["advancement_mode"] = "real_time"
    progression.pop("step_ticks")
    payload["temporal_constraints"]["green-cadence"]["cadence_ticks"] = 1
    scenario = parse_sdl(yaml.safe_dump(payload, sort_keys=False))
    runtime_model = compile_runtime_model(scenario)
    participant_runtime = _NativeParticipantRuntime()
    manager = RuntimeManager(
        replace(
            create_stub_target(),
            manifest=_autonomous_manifest(runtime_model),
            participant_runtime=participant_runtime,
        )
    )
    assert manager.apply(manager.plan(scenario)).success
    policy = next(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )

    assert manager.advance_time(policy.clock_address, ticks=1).success
    time.sleep(0.25)

    assert manager.read_time_state().clocks[policy.clock_address].coordinate.tick == 1
    assert len(participant_runtime.native_actions) == 2
    assert manager.destroy().success


def test_wall_driver_stop_keeps_live_thread_owned_until_it_exits() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["time_domains"]["scenario"]["tick_period_seconds"] = {"numerator": 1, "denominator": 100}
    progression = payload["time_progression_policies"]["scenario-progression"]
    progression["advancement_mode"] = "real_time"
    progression.pop("step_ticks")
    payload["temporal_constraints"]["green-cadence"]["cadence_ticks"] = 1
    runtime_model = compile_runtime_model(parse_sdl(yaml.safe_dump(payload, sort_keys=False)))
    policy = next(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )
    participant_runtime = _NativeParticipantRuntime()
    scheduler = ParticipantScheduler()
    snapshot = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        TimeCoordinator(runtime_model.time_model).initialize(),
    ).snapshot
    snapshot = scheduler.run_due(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        snapshot,
    ).snapshot
    entered = threading.Event()
    release = threading.Event()

    def blocking_advance(_clock_address: str, _ticks: int) -> ApplyResult:
        entered.set()
        release.wait(timeout=1.0)
        return ApplyResult(success=True, snapshot=snapshot)

    driver = ParticipantClockDriver(
        [policy],
        runtime_model.time_model,
        snapshot=lambda: snapshot,
        advance=blocking_advance,
        service_due=lambda: ApplyResult(success=True, snapshot=snapshot),
        lock=threading.RLock(),
    )
    driver.start()
    assert entered.wait(timeout=1.0)

    assert driver.stop(timeout=0.01) is False
    assert driver.active
    release.set()
    assert driver.stop(timeout=1.0) is True
    assert not driver.active


def test_wall_driver_records_an_unexpected_runtime_exception() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["time_domains"]["scenario"]["tick_period_seconds"] = {"numerator": 1, "denominator": 100}
    progression = payload["time_progression_policies"]["scenario-progression"]
    progression["advancement_mode"] = "real_time"
    progression.pop("step_ticks")
    payload["temporal_constraints"]["green-cadence"]["cadence_ticks"] = 1
    runtime_model = compile_runtime_model(parse_sdl(yaml.safe_dump(payload, sort_keys=False)))
    policy = next(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )
    participant_runtime = _NativeParticipantRuntime()
    scheduler = ParticipantScheduler()
    snapshot = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        TimeCoordinator(runtime_model.time_model).initialize(),
    ).snapshot
    snapshot = scheduler.run_due(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        snapshot,
    ).snapshot

    def failing_advance(_clock_address: str, _ticks: int) -> ApplyResult:
        raise RuntimeError("clock backend failed")

    driver = ParticipantClockDriver(
        [policy],
        runtime_model.time_model,
        snapshot=lambda: snapshot,
        advance=failing_advance,
        service_due=lambda: ApplyResult(success=True, snapshot=snapshot),
        lock=threading.RLock(),
    )
    driver.start()
    deadline = time.monotonic() + 1.0
    while driver.failure is None and time.monotonic() < deadline:
        time.sleep(0.01)

    assert driver.failure is not None
    assert driver.failure.diagnostics[0].code == "runtime.participant-clock-driver-failed"
    assert driver.stop()


def test_runtime_manager_refuses_destroy_while_clock_driver_is_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = RuntimeManager(create_stub_target())
    monkeypatch.setattr(manager, "_stop_participant_clock_driver", lambda: False)

    result = manager.destroy()

    assert not result.success
    assert result.diagnostics[0].code == "runtime.participant-clock-driver-stop-timeout"


def test_preserve_value_reset_selects_reachable_cadence() -> None:
    payload = yaml.safe_load(_scenario_yaml())
    payload["time_progression_policies"]["scenario-progression"]["reset_behavior"] = "new_segment_preserve_value"
    scenario = parse_sdl(yaml.safe_dump(payload, sort_keys=False))
    runtime_model = compile_runtime_model(scenario)
    participant_runtime = _NativeParticipantRuntime()
    manager = RuntimeManager(
        replace(
            create_stub_target(),
            manifest=_autonomous_manifest(runtime_model),
            participant_runtime=participant_runtime,
        )
    )
    assert manager.apply(manager.plan(scenario)).success
    policy = next(
        specification.autonomous_execution
        for specification in runtime_model.behavior_specifications.values()
        if specification.autonomous_execution is not None
    )
    assert manager.advance_time(policy.clock_address, ticks=10).success

    reset = manager.reset_time(policy.clock_address)

    assert reset.success
    state = ParticipantAutonomousExecutionStateModel.model_validate(
        next(iter(reset.snapshot.participant_autonomous_execution_states.values()))
    )
    assert (state.time_segment, state.next_tick, state.attempted_actions) == (1, 10, 0)
    assert manager.run_due_participant_actions().success


def test_runtime_snapshot_rejects_misaddressed_autonomous_execution_state() -> None:
    state = ParticipantAutonomousExecutionStateModel(
        policy_address="participant.autonomous-execution.green-users",
        policy_digest="sha256:" + "0" * 64,
        participant_address="participant.behavior.green-user",
        episode_id="participant.behavior.green-user-autonomous-0",
        participant_implementation_ref=IMPLEMENTATION_REF,
        clock_address="time.clock.scenario-clock",
        time_segment=0,
        lifecycle_state="running",
        next_tick=0,
        next_action_index=0,
        attempted_actions=0,
        succeeded_actions=0,
        failed_actions=0,
    )

    with pytest.raises(ValueError, match="map key must equal"):
        RuntimeSnapshotEnvelopeModel(
            participant_autonomous_execution_states={"participant.autonomous-execution.wrong": state}
        )


def test_scheduler_rejects_an_unselected_participant_implementation() -> None:
    runtime_model, policy = _compiled()
    scheduler = ParticipantScheduler()
    participant_runtime = _NativeParticipantRuntime()
    snapshot = scheduler.initialize(
        [policy],
        runtime_model.time_model,
        participant_runtime,
        TimeCoordinator(runtime_model.time_model).initialize(),
    ).snapshot

    class WrongBindingRuntime(_NativeParticipantRuntime):
        def bind_autonomous_action(
            self,
            participant_address: str,
            action_contract_address: str,
            observation_boundary_address: str,
            participant_implementation_ref: str,
            action_instance_id: str,
            temporal_contexts: tuple[object, ...],
            snapshot: RuntimeSnapshot,
        ) -> ParticipantActionAdmissionRequest:
            request = super().bind_autonomous_action(
                participant_address,
                action_contract_address,
                observation_boundary_address,
                participant_implementation_ref,
                action_instance_id,
                temporal_contexts,
                snapshot,
            )
            return replace(
                request,
                implementation_selection=request.implementation_selection.model_copy(
                    update={"manifest_ref": "participant-implementation-manifests.other.v1"}
                ),
            )

    participant_runtime = WrongBindingRuntime()
    with pytest.raises(ValueError, match="does not match the autonomous execution policy"):
        scheduler.run_due(
            [policy],
            runtime_model.time_model,
            participant_runtime,
            snapshot,
        )
    assert participant_runtime.native_actions == []
