"""Reference runtime control-plane tests."""

from __future__ import annotations

import textwrap

from aces_backend_stubs.stubs import create_stub_components, create_stub_manifest
from aces_contracts.contracts import (
    ParticipantContextViewModel,
    ParticipantHistoryViewModel,
    ParticipantStatusViewModel,
)
from aces_contracts.runtime_state import RuntimeSnapshot
from aces_processor.models import iter_participant_episode_snapshot_violations

from aces.backends.stubs import create_stub_target
from aces.core.runtime.compiler import compile_runtime_model
from aces.core.runtime.control_plane import RuntimeControlPlane
from aces.core.runtime.control_plane_store import ControlPlaneOperationRecord
from aces.core.runtime.models import (
    OperationReceipt,
    OperationState,
    OperationStatus,
    ParticipantEpisodeTerminalReason,
    RuntimeDomain,
)
from aces.core.runtime.planner import plan
from aces.core.runtime.registry import RuntimeTarget
from aces.core.sdl import parse_sdl


def _scenario(yaml_str: str):
    return parse_sdl(textwrap.dedent(yaml_str))


def _episode_state(participant_address: str, episode_id: str) -> dict[str, object]:
    return {
        "state_schema_version": "participant-episode-state/v1",
        "participant_address": participant_address,
        "episode_id": episode_id,
        "sequence_number": 0,
        "status": "running",
        "terminal_reason": None,
        "initialized_at": "2026-06-05T10:00:00Z",
        "updated_at": "2026-06-05T10:00:00Z",
        "terminated_at": None,
        "last_control_action": "initialize",
        "previous_episode_id": None,
    }


def _episode_history_event(participant_address: str, episode_id: str) -> dict[str, object]:
    return {
        "event_type": "episode_running",
        "timestamp": "2026-06-05T10:00:00Z",
        "participant_address": participant_address,
        "episode_id": episode_id,
        "sequence_number": 0,
        "terminal_reason": None,
        "control_action": None,
        "details": {},
    }


def _behavior_history_event(participant_address: str, episode_id: str) -> dict[str, object]:
    return {
        "event_type": "action_attempted",
        "timestamp": "2026-06-05T10:00:01Z",
        "participant_address": participant_address,
        "episode_id": episode_id,
        "action_instance_id": f"{participant_address}.action-1",
        "details": {},
    }


def _participant_operation_record(operation_id: str, participant_address: str) -> ControlPlaneOperationRecord:
    submitted_at = "2026-06-05T10:00:00Z"
    return ControlPlaneOperationRecord(
        receipt=OperationReceipt(
            operation_id=operation_id,
            domain=RuntimeDomain.PARTICIPANT,
            submitted_at=submitted_at,
            accepted=True,
        ),
        status=OperationStatus(
            operation_id=operation_id,
            domain=RuntimeDomain.PARTICIPANT,
            state=OperationState.RUNNING,
            submitted_at=submitted_at,
            updated_at=submitted_at,
            changed_addresses=[participant_address],
        ),
    )


def test_control_plane_submits_provisioning_and_updates_snapshot():
    scenario = _scenario("""
name: provision
nodes:
  vm:
    type: vm
    os: linux
    resources: {ram: 1 gib, cpu: 1}
""")
    execution_plan = plan(compile_runtime_model(scenario), create_stub_target().manifest)
    control_plane = RuntimeControlPlane(create_stub_target())

    receipt = control_plane.submit_provisioning(execution_plan.provisioning)
    status = control_plane.get_operation(receipt.operation_id)
    snapshot = control_plane.get_snapshot()

    assert receipt.accepted is True
    assert receipt.domain == RuntimeDomain.PROVISIONING
    assert status is not None
    assert status.state == OperationState.SUCCEEDED
    assert snapshot.snapshot.entries


def test_control_plane_submits_orchestration_with_portable_workflow_state():
    scenario = _scenario("""
name: workflow
nodes:
  vm:
    type: vm
    os: linux
    resources: {ram: 1 gib, cpu: 1}
    conditions: {health: ops}
    roles: {ops: operator}
conditions:
  health: {command: /bin/true, interval: 15}
entities:
  blue: {role: blue}
objectives:
  validate:
    entity: blue
    success: {conditions: [health]}
workflows:
  response:
    start: run
    steps:
      run:
        type: objective
        objective: validate
        on-success: finish
      finish: {type: end}
""")
    target = create_stub_target()
    execution_plan = plan(compile_runtime_model(scenario), target.manifest)
    control_plane = RuntimeControlPlane(target)

    receipt = control_plane.submit_orchestration(execution_plan.orchestration)
    status = control_plane.get_operation(receipt.operation_id)
    snapshot = control_plane.get_snapshot()

    assert receipt.accepted is True
    assert status is not None
    assert status.state == OperationState.SUCCEEDED
    workflow_result = next(iter(snapshot.snapshot.orchestration_results.values()))
    assert workflow_result["workflow_status"] == "running"
    assert "run_id" in workflow_result
    assert snapshot.snapshot.orchestration_history


class TestParticipantEpisodeControlPlane:
    """RUN-311 — runtime-level participant episode control methods.

    These exercise the full ``initialize → reset → terminate → restart``
    lifecycle through the control plane, asserting that each backend
    ``ApplyResult`` is persisted into the snapshot, each operation gets
    a succeeded ``OperationStatus``, and the resulting
    ``participant_episode_results`` / ``participant_episode_history``
    satisfy the RUN-311 invariants.
    """

    def test_initialize_creates_first_episode_with_running_state(self):
        control_plane = RuntimeControlPlane(create_stub_target())

        receipt = control_plane.initialize_participant_episode("participant.alice")
        status = control_plane.get_operation(receipt.operation_id)
        snapshot = control_plane.get_snapshot()

        assert receipt.accepted is True
        assert receipt.domain == RuntimeDomain.PARTICIPANT
        assert status is not None
        assert status.state == OperationState.SUCCEEDED
        state = snapshot.snapshot.participant_episode_results["participant.alice"]
        assert state["status"] == "running"
        assert state["sequence_number"] == 0
        assert state["previous_episode_id"] is None
        assert state["last_control_action"] == "initialize"
        history = snapshot.snapshot.participant_episode_history["participant.alice"]
        assert [event["event_type"] for event in history] == [
            "episode_initialized",
            "episode_running",
        ]

    def test_initialize_twice_rejects_duplicate(self):
        control_plane = RuntimeControlPlane(create_stub_target())
        control_plane.initialize_participant_episode("participant.alice")

        receipt = control_plane.initialize_participant_episode("participant.alice")
        status = control_plane.get_operation(receipt.operation_id)

        assert status is not None
        assert status.state == OperationState.FAILED
        assert any("already has a live episode" in diag.message for diag in status.diagnostics)

    def test_reset_allocates_new_episode_preserving_identity(self):
        control_plane = RuntimeControlPlane(create_stub_target())
        control_plane.initialize_participant_episode("participant.alice")

        receipt = control_plane.reset_participant_episode("participant.alice", reason="operator reset")
        status = control_plane.get_operation(receipt.operation_id)
        snapshot = control_plane.get_snapshot()

        assert status is not None
        assert status.state == OperationState.SUCCEEDED
        state = snapshot.snapshot.participant_episode_results["participant.alice"]
        assert state["sequence_number"] == 1
        assert state["last_control_action"] == "reset"
        assert state["previous_episode_id"] == "participant.alice-episode-1"
        assert state["episode_id"] == "participant.alice-episode-2"
        assert state["status"] == "running"

    def test_reset_rejects_terminated_participant(self):
        control_plane = RuntimeControlPlane(create_stub_target())
        control_plane.initialize_participant_episode("participant.alice")
        control_plane.terminate_participant_episode(
            "participant.alice",
            terminal_reason=ParticipantEpisodeTerminalReason.COMPLETED,
        )

        receipt = control_plane.reset_participant_episode("participant.alice")
        status = control_plane.get_operation(receipt.operation_id)

        assert status is not None
        assert status.state == OperationState.FAILED
        assert any("use restart" in diag.message for diag in status.diagnostics)

    def test_terminate_drives_state_to_terminated_with_reason(self):
        control_plane = RuntimeControlPlane(create_stub_target())
        control_plane.initialize_participant_episode("participant.alice")

        receipt = control_plane.terminate_participant_episode(
            "participant.alice",
            terminal_reason=ParticipantEpisodeTerminalReason.TIMED_OUT,
        )
        status = control_plane.get_operation(receipt.operation_id)
        snapshot = control_plane.get_snapshot()

        assert status is not None
        assert status.state == OperationState.SUCCEEDED
        state = snapshot.snapshot.participant_episode_results["participant.alice"]
        assert state["status"] == "terminated"
        assert state["terminal_reason"] == "timed_out"
        assert state["terminated_at"] is not None
        history = snapshot.snapshot.participant_episode_history["participant.alice"]
        assert history[-1]["event_type"] == "episode_timed_out"
        assert history[-1]["terminal_reason"] == "timed_out"

    def test_terminate_rejects_already_terminated(self):
        control_plane = RuntimeControlPlane(create_stub_target())
        control_plane.initialize_participant_episode("participant.alice")
        control_plane.terminate_participant_episode("participant.alice")

        receipt = control_plane.terminate_participant_episode("participant.alice")
        status = control_plane.get_operation(receipt.operation_id)

        assert status is not None
        assert status.state == OperationState.FAILED
        assert any("already terminated" in diag.message for diag in status.diagnostics)

    def test_restart_resumes_from_terminated_predecessor(self):
        control_plane = RuntimeControlPlane(create_stub_target())
        control_plane.initialize_participant_episode("participant.alice")
        control_plane.terminate_participant_episode(
            "participant.alice",
            terminal_reason=ParticipantEpisodeTerminalReason.COMPLETED,
        )

        receipt = control_plane.restart_participant_episode("participant.alice")
        status = control_plane.get_operation(receipt.operation_id)
        snapshot = control_plane.get_snapshot()

        assert status is not None
        assert status.state == OperationState.SUCCEEDED
        state = snapshot.snapshot.participant_episode_results["participant.alice"]
        assert state["sequence_number"] == 1
        assert state["last_control_action"] == "restart"
        assert state["previous_episode_id"] == "participant.alice-episode-1"
        assert state["status"] == "running"

    def test_restart_rejects_non_terminated_participant(self):
        control_plane = RuntimeControlPlane(create_stub_target())
        control_plane.initialize_participant_episode("participant.alice")

        receipt = control_plane.restart_participant_episode("participant.alice")
        status = control_plane.get_operation(receipt.operation_id)

        assert status is not None
        assert status.state == OperationState.FAILED
        assert any("non-terminated" in diag.message for diag in status.diagnostics)

    def test_initialize_rejects_target_without_participant_runtime(self):
        manifest = create_stub_manifest(with_participant_runtime=False)
        components = create_stub_components(manifest=manifest)
        target = RuntimeTarget(
            name="no-participant",
            manifest=manifest,
            provisioner=components.provisioner,
            orchestrator=components.orchestrator,
            evaluator=components.evaluator,
        )
        control_plane = RuntimeControlPlane(target)

        receipt = control_plane.initialize_participant_episode("participant.alice")
        status = control_plane.get_operation(receipt.operation_id)

        assert receipt.accepted is False
        assert status is not None
        assert status.state == OperationState.FAILED
        assert any("does not provide a participant runtime" in diag.message for diag in receipt.diagnostics)

    def test_full_lifecycle_snapshot_chain_is_consistent(self):
        """End-to-end: initialize → reset → terminate → restart and verify
        history chain matches the final result (RUN-311 cross-check invariant).
        """
        control_plane = RuntimeControlPlane(create_stub_target())

        control_plane.initialize_participant_episode("participant.alice")
        control_plane.reset_participant_episode("participant.alice")
        control_plane.terminate_participant_episode(
            "participant.alice",
            terminal_reason=ParticipantEpisodeTerminalReason.COMPLETED,
        )
        control_plane.restart_participant_episode("participant.alice")

        snapshot = control_plane.get_snapshot().snapshot
        violations = list(
            iter_participant_episode_snapshot_violations(
                snapshot.participant_episode_results,
                snapshot.participant_episode_history,
            )
        )
        assert violations == [], (
            f"Full participant lifecycle must satisfy every RUN-311 snapshot invariant; got violations: {violations}"
        )

    def test_initialize_is_idempotent_via_idempotency_key(self):
        """Idempotency — a second submission with the same idempotency key
        must return the original receipt without running the backend twice.
        """
        control_plane = RuntimeControlPlane(create_stub_target())

        first = control_plane.initialize_participant_episode(
            "participant.alice",
            idempotency_key="init-alice-1",
        )
        second = control_plane.initialize_participant_episode(
            "participant.alice",
            idempotency_key="init-alice-1",
        )

        assert first.operation_id == second.operation_id
        snapshot = control_plane.get_snapshot().snapshot
        history = snapshot.participant_episode_history["participant.alice"]
        assert [event["event_type"] for event in history] == [
            "episode_initialized",
            "episode_running",
        ]

    def test_status_view_projects_current_participant_episode_state(self):
        control_plane = RuntimeControlPlane(create_stub_target())
        control_plane.initialize_participant_episode("participant.alice")

        view = control_plane.get_participant_status_view("participant.alice")

        assert isinstance(view, ParticipantStatusViewModel)
        assert view.participant_address == "participant.alice"
        assert view.episode_id == "participant.alice-episode-1"
        assert view.source_snapshot_ref == "runtime.snapshot.current"
        assert view.episode_state is not None
        assert view.episode_state.status == "running"
        episode_state = view.episode_state.model_dump(mode="json")
        assert "participant_address" not in episode_state
        assert "episode_id" not in episode_state

    def test_status_view_scopes_open_operations_to_participant(self):
        snapshot = RuntimeSnapshot(
            participant_episode_results={
                "participant.alice": _episode_state("participant.alice", "episode-1"),
                "participant.bob": _episode_state("participant.bob", "episode-1"),
            }
        )
        control_plane = RuntimeControlPlane(create_stub_target(), initial_snapshot=snapshot)
        control_plane._operations = {
            "op-alice": _participant_operation_record("op-alice", "participant.alice"),
            "op-bob": _participant_operation_record("op-bob", "participant.bob"),
        }

        view = control_plane.get_participant_status_view("participant.alice")

        assert view is not None
        assert view.open_operation_refs == ["op-alice"]

    def test_history_view_filters_to_one_participant_episode_and_projects_scope(self):
        snapshot = RuntimeSnapshot(
            participant_episode_results={
                "participant.alice": _episode_state("participant.alice", "episode-1"),
                "participant.bob": _episode_state("participant.bob", "episode-1"),
            },
            participant_episode_history={
                "participant.alice": [
                    _episode_history_event("participant.alice", "episode-1"),
                    _episode_history_event("participant.alice", "episode-2"),
                ],
                "participant.bob": [_episode_history_event("participant.bob", "episode-1")],
            },
            participant_behavior_history={
                "participant.alice": [
                    _behavior_history_event("participant.alice", "episode-1"),
                    _behavior_history_event("participant.alice", "episode-2"),
                ],
                "participant.bob": [_behavior_history_event("participant.bob", "episode-1")],
            },
        )
        control_plane = RuntimeControlPlane(create_stub_target(), initial_snapshot=snapshot)

        view = control_plane.get_participant_history_view("participant.alice", "episode-1")

        assert isinstance(view, ParticipantHistoryViewModel)
        assert view.participant_address == "participant.alice"
        assert view.episode_id == "episode-1"
        assert view.completeness == "complete"
        assert len(view.episode_history) == 1
        assert len(view.behavior_history) == 1
        for event in [*view.episode_history, *view.behavior_history]:
            payload = event.model_dump(mode="json")
            assert "participant_address" not in payload
            assert "episode_id" not in payload

    def test_context_view_is_reference_and_provenance_only(self):
        control_plane = RuntimeControlPlane(create_stub_target())
        control_plane.initialize_participant_episode("participant.alice")

        view = control_plane.get_participant_context_view(
            "participant.alice",
            view_ref="views.context.network-posture.v1",
            episode_id="participant.alice-episode-1",
            derivation_basis_ref="rules.context.network-posture.v1",
            payload_ref="evidence.context.alice.network-posture",
        )

        assert isinstance(view, ParticipantContextViewModel)
        assert view.participant_address == "participant.alice"
        assert view.episode_id == "participant.alice-episode-1"
        assert view.view_ref == "views.context.network-posture.v1"
        assert view.derived_from_refs == ["runtime.snapshot.current"]
        assert view.payload_ref == "evidence.context.alice.network-posture"

    def test_participant_retrieval_views_return_none_for_unknown_participant(self):
        control_plane = RuntimeControlPlane(create_stub_target())

        assert control_plane.get_participant_status_view("participant.unknown") is None
        assert control_plane.get_participant_history_view("participant.unknown", "episode-1") is None
        assert (
            control_plane.get_participant_context_view(
                "participant.unknown",
                view_ref="views.context.network-posture.v1",
            )
            is None
        )
