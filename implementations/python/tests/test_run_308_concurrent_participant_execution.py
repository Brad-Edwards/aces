"""RUN-308 concurrent participant execution integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_contracts.contracts import (
    ParticipantJointActionRecordModel,
    ParticipantTimeManagementContextModel,
    RuntimeSnapshotEnvelopeModel,
    schema_bundle,
)
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot
from aces_runtime.backend_calls import _call_backend_apply
from aces_runtime.participant_result_contracts import participant_runtime_state_contract_diagnostics
from jsonschema import Draft202012Validator
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_ADDRESS = "hosts.web01.service.http"
PARTICIPANT_RED = "participants.red.llm"
PARTICIPANT_BLUE = "participants.blue.llm"
EPISODE = "episode-main"
T0 = "2026-06-20T08:00:00Z"


def _shared_state_record() -> dict[str, object]:
    fixture_path = (
        REPO_ROOT
        / "contracts"
        / "fixtures"
        / "participant-runtime"
        / "participant-shared-state-record-v1"
        / "valid"
        / "serialized-service-state-commit.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _behavior_event(participant_address: str, action_instance_id: str, realized_order: int) -> dict[str, object]:
    return {
        "event_type": "action_attempted",
        "timestamp": T0,
        "participant_address": participant_address,
        "episode_id": EPISODE,
        "action_instance_id": action_instance_id,
        "action_contract_address": "participant.action-contract.scan",
        "actor_provenance": f"participant:{participant_address.rsplit('.', 1)[-1]}",
        "joint_action_set_id": "joint-red-blue-0001",
        "realized_order": realized_order,
        "interaction_class": "shared_state_change",
        "shared_state_refs": [STATE_ADDRESS],
        "details": {},
    }


def _base_envelope(*, event_id: str, schema_name: str, event_type: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "schema_name": schema_name,
        "schema_version": f"{schema_name}/v1",
        "event_type": event_type,
        "extension_policy": "forbid_unknown_fields",
        "participant_address": None,
        "episode_id": None,
        "sequence_number": None,
        "occurred_at": T0,
        "recorded_at": T0,
        "ingested_at": T0,
        "clock_authority": "clock.logical.runtime",
        "ordering_basis": "serialized_backend_order",
        "logical_order_ref": "order.joint-red-blue-0001",
        "actor_ref": "runtime.coordinator",
        "producer_ref": "backend.stub",
        "authorization_scope": "operators",
    }


def _time_context(**overrides: object) -> dict[str, object]:
    payload = {
        **_base_envelope(
            event_id="tm-red-blue-0001",
            schema_name="participant-time-management-context",
            event_type="time_management_context_recorded",
        ),
        "context_id": "tm-red-blue-0001",
        "mode": "backend_serialized",
        "claim_strength": "bounded",
        "basis": "serialized_backend_order",
        "clock_ref": "clock.logical.runtime",
        "backend_serialized": True,
    }
    payload.update(overrides)
    return payload


def _joint_action(**overrides: object) -> dict[str, object]:
    payload = {
        **_base_envelope(
            event_id="joint-red-blue-0001",
            schema_name="participant-joint-action-record",
            event_type="joint_action_recorded",
        ),
        "joint_action_set_id": "joint-red-blue-0001",
        "member_event_refs": ["scan-red-0001", "scan-blue-0001"],
        "access_sets": [
            {
                "member_event_ref": "scan-red-0001",
                "shared_state_write_refs": [STATE_ADDRESS],
            },
            {
                "member_event_ref": "scan-blue-0001",
                "shared_state_read_refs": [STATE_ADDRESS],
            },
        ],
        "conflict_class": "read_write",
        "conflict_policy": "serialize",
        "isolation_guarantee": "serializable",
        "atomicity_scope": "single_object",
        "realized_order": ["scan-red-0001", "scan-blue-0001"],
        "time_management_context_ref": "tm-red-blue-0001",
    }
    payload.update(overrides)
    return payload


def _snapshot_payload(**overrides: object) -> dict[str, object]:
    shared_state = _shared_state_record()
    payload = {
        "schema_version": "runtime-snapshot/v1",
        "entries": {},
        "orchestration_results": {},
        "orchestration_history": {},
        "evaluation_results": {},
        "evaluation_history": {},
        "participant_episode_results": {},
        "participant_episode_history": {},
        "participant_behavior_history": {
            PARTICIPANT_RED: [_behavior_event(PARTICIPANT_RED, "scan-red-0001", 0)],
            PARTICIPANT_BLUE: [_behavior_event(PARTICIPANT_BLUE, "scan-blue-0001", 1)],
        },
        "shared_state_records": {STATE_ADDRESS: shared_state},
        "shared_state_history": {STATE_ADDRESS: [shared_state]},
        "joint_action_records": {"joint-red-blue-0001": _joint_action()},
        "time_management_contexts": {"tm-red-blue-0001": _time_context()},
        "metadata": {},
    }
    payload.update(overrides)
    return payload


def test_runtime_snapshot_publishes_joint_action_and_time_context_records() -> None:
    payload = _snapshot_payload()

    model = RuntimeSnapshotEnvelopeModel.model_validate(payload)
    assert model.joint_action_records["joint-red-blue-0001"].conflict_policy == "serialize"
    assert model.time_management_contexts["tm-red-blue-0001"].mode == "backend_serialized"

    validator = Draft202012Validator(schema_bundle()["runtime-snapshot-v1"])
    assert list(validator.iter_errors(payload)) == []


def test_joint_action_record_contract_rejects_unordered_conflicting_writes() -> None:
    payload = _joint_action(
        access_sets=[
            {"member_event_ref": "scan-red-0001", "shared_state_write_refs": [STATE_ADDRESS]},
            {"member_event_ref": "scan-blue-0001", "shared_state_write_refs": [STATE_ADDRESS]},
        ],
        conflict_class="none",
        conflict_policy="none",
        isolation_guarantee="none",
        realized_order=[],
        exact_concurrency_claim=True,
    )

    with pytest.raises(ValidationError, match="conflict_class"):
        ParticipantJointActionRecordModel.model_validate(payload)


def test_joint_action_record_contract_rejects_exact_claim_without_time_context() -> None:
    payload = _joint_action(
        exact_concurrency_claim=True,
        time_management_context_ref=None,
    )

    with pytest.raises(ValidationError, match="time_management_context_ref"):
        ParticipantJointActionRecordModel.model_validate(payload)


def test_time_management_context_contract_rejects_wall_clock_exact_claim() -> None:
    payload = _time_context(
        mode="display",
        claim_strength="exact",
        basis="wall_clock_only",
        clock_ref="clock.wall",
        backend_serialized=False,
    )

    with pytest.raises(ValidationError, match="wall_clock_only"):
        ParticipantTimeManagementContextModel.model_validate(payload)


def test_participant_runtime_state_diagnostics_reject_unresolved_concurrency_refs() -> None:
    payload = _snapshot_payload(
        joint_action_records={
            "joint-red-blue-0001": _joint_action(
                member_event_refs=["scan-red-0001", "scan-missing-0001"],
                access_sets=[
                    {"member_event_ref": "scan-red-0001", "shared_state_write_refs": [STATE_ADDRESS]},
                    {"member_event_ref": "scan-missing-0001", "shared_state_read_refs": [STATE_ADDRESS]},
                ],
                realized_order=["scan-red-0001", "scan-missing-0001"],
            )
        }
    )
    snapshot = RuntimeSnapshot(
        participant_behavior_history=dict(payload["participant_behavior_history"]),
        shared_state_records=dict(payload["shared_state_records"]),
        shared_state_history=dict(payload["shared_state_history"]),
        joint_action_records=dict(payload["joint_action_records"]),
        time_management_contexts=dict(payload["time_management_contexts"]),
    )

    diagnostics = participant_runtime_state_contract_diagnostics(snapshot)

    assert any("scan-missing-0001" in diagnostic.message for diagnostic in diagnostics)


def test_participant_runtime_state_diagnostics_reject_shared_state_refs_when_index_empty() -> None:
    payload = _snapshot_payload(
        shared_state_records={},
        shared_state_history={},
    )
    snapshot = RuntimeSnapshot(
        participant_behavior_history=dict(payload["participant_behavior_history"]),
        shared_state_records={},
        shared_state_history={},
        joint_action_records=dict(payload["joint_action_records"]),
        time_management_contexts=dict(payload["time_management_contexts"]),
    )

    diagnostics = participant_runtime_state_contract_diagnostics(snapshot)

    assert any(f"{STATE_ADDRESS!r} does not resolve" in diagnostic.message for diagnostic in diagnostics)


def test_participant_runtime_state_diagnostics_reject_exact_claim_with_bounded_time_context() -> None:
    payload = _snapshot_payload(
        joint_action_records={
            "joint-red-blue-0001": _joint_action(
                exact_concurrency_claim=True,
            )
        }
    )
    snapshot = RuntimeSnapshot(
        participant_behavior_history=dict(payload["participant_behavior_history"]),
        shared_state_records=dict(payload["shared_state_records"]),
        shared_state_history=dict(payload["shared_state_history"]),
        joint_action_records=dict(payload["joint_action_records"]),
        time_management_contexts=dict(payload["time_management_contexts"]),
    )

    diagnostics = participant_runtime_state_contract_diagnostics(snapshot)

    assert any("exact time-management context" in diagnostic.message for diagnostic in diagnostics)


def test_participant_runtime_state_diagnostics_reject_rollback_refs_when_history_empty() -> None:
    payload = _snapshot_payload(
        participant_behavior_history={},
        time_management_contexts={
            "tm-red-blue-0001": _time_context(
                mode="rollback",
                claim_strength="bounded",
                rollback_event_refs=["scan-red-0001"],
                backend_serialized=False,
            )
        },
    )
    snapshot = RuntimeSnapshot(
        participant_behavior_history={},
        shared_state_records=dict(payload["shared_state_records"]),
        shared_state_history=dict(payload["shared_state_history"]),
        joint_action_records={},
        time_management_contexts=dict(payload["time_management_contexts"]),
    )

    diagnostics = participant_runtime_state_contract_diagnostics(snapshot)

    assert any(
        "rollback_event_ref 'scan-red-0001' does not resolve" in diagnostic.message for diagnostic in diagnostics
    )


def test_backend_apply_rejects_rewriting_joint_action_records() -> None:
    payload = _snapshot_payload()
    base_snapshot = RuntimeSnapshot(
        participant_behavior_history=dict(payload["participant_behavior_history"]),
        shared_state_records=dict(payload["shared_state_records"]),
        shared_state_history=dict(payload["shared_state_history"]),
        joint_action_records=dict(payload["joint_action_records"]),
        time_management_contexts=dict(payload["time_management_contexts"]),
    )

    def _backend_apply(_request: object, snapshot: RuntimeSnapshot) -> ApplyResult:
        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(
                dict(snapshot.entries),
                joint_action_records={},
                time_management_contexts=dict(snapshot.time_management_contexts),
            ),
        )

    result = _call_backend_apply(
        _backend_apply,
        object(),
        base_snapshot,
        address="runtime.control-plane.concurrent-participants",
        snapshot=base_snapshot,
    )

    assert result.success is False
    assert any("joint_action_records must be append-only" in item.message for item in result.diagnostics)


def test_joint_action_and_time_context_model_round_trip() -> None:
    joint_action = ParticipantJointActionRecordModel.model_validate(_joint_action())
    time_context = ParticipantTimeManagementContextModel.model_validate(_time_context())

    assert joint_action.model_dump(mode="json")["conflict_class"] == "read_write"
    assert time_context.model_dump(mode="json")["claim_strength"] == "bounded"
