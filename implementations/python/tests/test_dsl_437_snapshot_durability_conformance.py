"""DSL-437 autonomous scheduler-state snapshot boundary tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_conformance.conformance import _semantic_diagnostics
from aces_conformance.conformance.snapshot_semantics import _snapshot_from_envelope
from aces_contracts.contracts.time_model import TimeRuntimeStateModel
from aces_contracts.runtime_state import RuntimeSnapshot
from aces_runtime.control_plane_store import InMemoryControlPlaneStore, LocalControlPlaneStore

POLICY_ADDRESS = "participant.autonomous-execution.green-users"
PARTICIPANT_ADDRESS = "participant.behavior.green-user"
STATE_ADDRESS = f"{POLICY_ADDRESS}.state.{PARTICIPANT_ADDRESS}"


def _state(**updates: object) -> dict[str, object]:
    state: dict[str, object] = {
        "policy_address": POLICY_ADDRESS,
        "policy_digest": "sha256:" + "4" * 64,
        "participant_address": PARTICIPANT_ADDRESS,
        "episode_id": f"{PARTICIPANT_ADDRESS}-autonomous-0",
        "participant_implementation_ref": "participant-implementation-manifests.green-worker.v1",
        "clock_address": "time.clock.scenario-clock",
        "time_segment": 0,
        "lifecycle_state": "running",
        "next_tick": 10,
        "next_action_index": 1,
        "attempted_actions": 1,
        "succeeded_actions": 1,
        "failed_actions": 0,
        "in_flight": 0,
        "last_action_instance_id": "green-user-action-1",
    }
    state.update(updates)
    return state


def _envelope(state: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "schema_version": "runtime-snapshot/v1",
        "participant_episode_results": {PARTICIPANT_ADDRESS: _episode()},
        "participant_autonomous_execution_states": {
            STATE_ADDRESS: _state() if state is None else state,
        },
        "time_model_state": _time_state().model_dump(mode="json"),
    }


def _episode() -> dict[str, object]:
    return {
        "state_schema_version": "participant-episode-state/v1",
        "participant_address": PARTICIPANT_ADDRESS,
        "episode_id": f"{PARTICIPANT_ADDRESS}-autonomous-0",
        "sequence_number": 0,
        "status": "running",
        "terminal_reason": None,
        "initialized_at": "2026-07-24T00:00:00Z",
        "updated_at": "2026-07-24T00:00:00Z",
        "terminated_at": None,
        "last_control_action": "initialize",
        "previous_episode_id": None,
    }


def _time_state(*, segment: int = 0) -> TimeRuntimeStateModel:
    coordinate = {"segment": segment, "tick": 0, "microstep": 0}
    return TimeRuntimeStateModel.model_validate(
        {
            "schema_version": "time-runtime-state/v1",
            "declaration_digest": "sha256:" + "3" * 64,
            "clocks": {
                "time.clock.scenario-clock": {
                    "clock_address": "time.clock.scenario-clock",
                    "time_domain_address": "time.domain.scenario",
                    "progression_policy_address": "time.progression-policy.scenario",
                    "authority_kind": "runtime",
                    "authority_ref": "runtime.clock",
                    "state": "running",
                    "coordinate": coordinate,
                    "sequence": 0,
                    "history": [
                        {
                            "sequence": 0,
                            "kind": "initialize",
                            "previous": None,
                            "resulting": coordinate,
                            "resulting_state": "running",
                        }
                    ],
                }
            },
        }
    )


def _snapshot(state: dict[str, object] | None = None) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        participant_episode_results={PARTICIPANT_ADDRESS: _episode()},
        participant_autonomous_execution_states={STATE_ADDRESS: _state() if state is None else state},
        time_model_state=_time_state(),
    )


def test_runtime_snapshot_rejects_misaddressed_autonomous_state() -> None:
    autonomous_states = {
        f"{POLICY_ADDRESS}.state.participant.behavior.other": _state(),
    }

    with pytest.raises(ValueError, match="map key must equal"):
        RuntimeSnapshot(participant_autonomous_execution_states=autonomous_states)


def test_runtime_snapshot_rejects_unaccounted_autonomous_attempts() -> None:
    autonomous_states = {
        STATE_ADDRESS: _state(
            lifecycle_state="completed",
            attempted_actions=2,
            succeeded_actions=1,
        )
    }

    with pytest.raises(ValueError, match="attempted_actions must equal"):
        RuntimeSnapshot(participant_autonomous_execution_states=autonomous_states)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("policy_digest", "not-a-digest", "canonical sha256 digest"),
        ("time_segment", -1, "time_segment"),
    ],
)
def test_runtime_snapshot_validates_policy_identity_and_time_segment(
    field: str,
    value: object,
    message: str,
) -> None:
    autonomous_states = {STATE_ADDRESS: _state(**{field: value})}

    with pytest.raises(ValueError, match=message):
        RuntimeSnapshot(participant_autonomous_execution_states=autonomous_states)


def test_control_plane_store_round_trips_valid_autonomous_state(tmp_path: Path) -> None:
    store = LocalControlPlaneStore(tmp_path / "control-plane")
    snapshot = _snapshot()

    store.save_snapshot(snapshot)
    loaded = store.load_snapshot()

    assert loaded.participant_autonomous_execution_states == {STATE_ADDRESS: _state()}
    assert loaded.participant_autonomous_execution_states[STATE_ADDRESS]["policy_digest"] == "sha256:" + "4" * 64
    assert loaded.participant_autonomous_execution_states[STATE_ADDRESS]["time_segment"] == 0


def test_control_plane_stores_revalidate_mutated_autonomous_state(tmp_path: Path) -> None:
    snapshot = _snapshot()
    snapshot.participant_autonomous_execution_states[STATE_ADDRESS] = _state(attempted_actions=2)
    memory_store = InMemoryControlPlaneStore()
    local_store = LocalControlPlaneStore(tmp_path / "control-plane")

    with pytest.raises(ValueError, match="attempted_actions must equal"):
        memory_store.save_snapshot(snapshot)
    with pytest.raises(ValueError, match="attempted_actions must equal"):
        local_store.save_snapshot(snapshot)


def test_local_control_plane_store_rejects_invalid_durable_state(tmp_path: Path) -> None:
    store = LocalControlPlaneStore(tmp_path / "control-plane")
    store.save_snapshot(_snapshot())
    snapshot_path = tmp_path / "control-plane" / "snapshot.json"
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload["participant_autonomous_execution_states"][STATE_ADDRESS]["attempted_actions"] = 2
    snapshot_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="attempted_actions must equal"):
        store.load_snapshot()


def test_local_control_plane_store_rejects_durable_clock_segment_mismatch(tmp_path: Path) -> None:
    store = LocalControlPlaneStore(tmp_path / "control-plane")
    store.save_snapshot(_snapshot())
    snapshot_path = tmp_path / "control-plane" / "snapshot.json"
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    clock = payload["time_model_state"]["clocks"]["time.clock.scenario-clock"]
    clock["coordinate"]["segment"] = 1
    clock["history"][-1]["resulting"]["segment"] = 1
    snapshot_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="must match the bound shared clock segment"):
        store.load_snapshot()


def test_conformance_conversion_preserves_autonomous_state() -> None:
    snapshot = _snapshot_from_envelope(_envelope())

    assert snapshot.participant_autonomous_execution_states == {STATE_ADDRESS: _state()}
    assert snapshot.participant_autonomous_execution_states[STATE_ADDRESS]["policy_digest"] == "sha256:" + "4" * 64
    assert snapshot.participant_autonomous_execution_states[STATE_ADDRESS]["time_segment"] == 0


def test_conformance_reports_inconsistent_terminal_autonomous_state() -> None:
    payload = _envelope(
        _state(
            lifecycle_state="completed",
            attempted_actions=2,
            succeeded_actions=1,
        )
    )

    diagnostics = _semantic_diagnostics("runtime-snapshot-v1", payload)

    assert [diagnostic.code for diagnostic in diagnostics] == ["conformance.semantic-invalid"]
    assert "attempted_actions must equal" in diagnostics[0].message


def test_durable_snapshot_rejects_clock_segment_mismatch() -> None:
    snapshot = _snapshot()
    snapshot.time_model_state = _time_state(segment=1)
    store = InMemoryControlPlaneStore()

    with pytest.raises(ValueError, match="must match the bound shared clock segment"):
        store.save_snapshot(snapshot)


def test_durable_snapshot_rejects_episode_mismatch() -> None:
    snapshot = _snapshot()
    snapshot.participant_episode_results[PARTICIPANT_ADDRESS]["episode_id"] = "wrong-episode"
    store = InMemoryControlPlaneStore()

    with pytest.raises(ValueError, match="must match the live participant episode"):
        store.save_snapshot(snapshot)
