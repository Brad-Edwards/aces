"""Reservation release when a backend concurrent participant batch misbehaves."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
import raes_runtime.participant_scheduler_operations as scheduler_operations
from raes_contracts.contracts import ParticipantAutonomousExecutionStateModel
from raes_contracts.contracts.participant_execution import ParticipantExecutionServiceStateModel
from raes_contracts.runtime_state import RuntimeSnapshot
from raes_runtime.participant_scheduler_concurrency import _execute_concurrent_batch
from raes_runtime.participant_scheduler_types import SchedulerRunState

_POLICY_ADDRESS = "participant.autonomous-execution.green-users"
_IMPLEMENTATION_REF = "participant-implementation-manifests.green-worker.v1"
_PARTICIPANTS = (
    "participant.behavior.green-user-a",
    "participant.behavior.green-user-b",
)


@dataclass(frozen=True)
class _StubContext:
    """Minimal stand-in for `_DueActionContext` for the batch-failure paths."""

    policy: object
    participant_address: str
    key: str


def _execution_state(
    participant_address: str,
    *,
    in_flight: int = 0,
) -> ParticipantAutonomousExecutionStateModel:
    return ParticipantAutonomousExecutionStateModel(
        policy_address=_POLICY_ADDRESS,
        policy_digest="sha256:" + "0" * 64,
        participant_address=participant_address,
        episode_id=f"{participant_address}-autonomous-0",
        participant_implementation_ref=_IMPLEMENTATION_REF,
        clock_address="time.clock.scenario-clock",
        time_segment=0,
        lifecycle_state="running",
        next_tick=0,
        next_action_index=0,
        # attempted_actions == succeeded + failed + in_flight is a snapshot invariant.
        attempted_actions=in_flight,
        succeeded_actions=0,
        failed_actions=0,
        in_flight=in_flight,
    )


def _service_state() -> ParticipantExecutionServiceStateModel:
    digest = "sha256:" + "0" * 64
    return ParticipantExecutionServiceStateModel(
        execution_scope_ref="participant.execution-scope.green",
        policy_address=_POLICY_ADDRESS,
        desired_lifecycle="running",
        observed_lifecycle="running",
        generation=1,
        observed_generation=1,
        health="healthy",
        readiness="ready",
        accepting_new_work=True,
        draining=False,
        quiescent=True,
        resources_released=False,
        policy_digest=digest,
        binding_digest=digest,
        time_declaration_digest=digest,
        capacity=2,
        reserved=0,
        in_flight=0,
        last_transition_ref=f"operation:{_POLICY_ADDRESS}:start:generation-1",
        evidence_refs=("evidence.green-login.native-action",),
    )


def _state_key(participant_address: str) -> str:
    return f"{_POLICY_ADDRESS}.state.{participant_address}"


def _batch(participant_runtime: object, *, in_flight: int = 0) -> SimpleNamespace:
    policy = SimpleNamespace(address=_POLICY_ADDRESS, max_in_flight=2)
    states = [_execution_state(address, in_flight=in_flight) for address in _PARTICIPANTS]
    snapshot = RuntimeSnapshot(
        participant_autonomous_execution_states={
            _state_key(address): state.model_dump(mode="json")
            for address, state in zip(_PARTICIPANTS, states, strict=True)
        },
        participant_execution_services={_POLICY_ADDRESS: _service_state().model_dump(mode="json")},
    )
    run = SchedulerRunState(working=snapshot, diagnostics=[], changed=[])
    contexts = [
        _StubContext(policy=policy, participant_address=address, key=_state_key(address)) for address in _PARTICIPANTS
    ]
    return SimpleNamespace(
        policy=policy,
        time_model=None,
        participant_runtime=participant_runtime,
        current_tick=0,
        cadence_ticks=1,
        run=run,
        contexts=contexts,
        states=states,
    )


@pytest.fixture(autouse=True)
def _stub_request_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Request construction is irrelevant to the batch-failure paths under test."""

    monkeypatch.setattr(
        scheduler_operations,
        "_bound_action_request",
        lambda context, working, state: SimpleNamespace(participant_address=context.participant_address),
    )


def _assert_reservations_released(run: SchedulerRunState, before: RuntimeSnapshot) -> None:
    service = ParticipantExecutionServiceStateModel.model_validate(
        run.working.participant_execution_services[_POLICY_ADDRESS]
    )
    assert (service.in_flight, service.reserved, service.quiescent) == (0, 0, True)
    for address in _PARTICIPANTS:
        state = ParticipantAutonomousExecutionStateModel.model_validate(
            run.working.participant_autonomous_execution_states[_state_key(address)]
        )
        assert state.in_flight == 0
        assert state.attempted_actions == state.succeeded_actions + state.failed_actions + state.in_flight
    # Reverting to the pre-batch state is the point: a partly-applied occurrence
    # (a recorded failure whose next_tick/next_action_index never advanced) could
    # be serviced again at the same tick.
    assert run.working.participant_autonomous_execution_states == before.participant_autonomous_execution_states
    assert run.working.participant_execution_services == before.participant_execution_services


def test_miscounted_backend_batch_is_reported_and_releases_reservations():
    """A wrong result count previously raised, leaking every reservation.

    Reservations are taken before the backend call and only cleared per
    committed result, so escaping here left participants permanently in-flight
    and the service non-quiescent, blocking all later occurrences.
    """
    batch = _batch(SimpleNamespace(admit_actions_concurrently=lambda requests, snapshot, workers: ()))
    before = batch.run.working

    _execute_concurrent_batch(batch)

    assert batch.run.failure is not None
    codes = [diagnostic.code for diagnostic in batch.run.failure.diagnostics]
    assert "runtime.participant-concurrent-result-count-invalid" in codes
    _assert_reservations_released(batch.run, before)


def test_raising_backend_batch_is_reported_and_releases_reservations():
    """A raising backend is a conformance failure, not an exception to leak."""

    def _explode(requests, snapshot, workers):
        raise RuntimeError("backend exploded")

    batch = _batch(SimpleNamespace(admit_actions_concurrently=_explode))
    before = batch.run.working

    _execute_concurrent_batch(batch)

    assert batch.run.failure is not None
    codes = [diagnostic.code for diagnostic in batch.run.failure.diagnostics]
    assert "runtime.participant-concurrent-batch-failed" in codes
    # Only the exception type may cross the backend boundary.
    message = next(
        d.message for d in batch.run.failure.diagnostics if d.code == "runtime.participant-concurrent-batch-failed"
    )
    assert "backend exploded" not in message
    assert "RuntimeError" in message
    _assert_reservations_released(batch.run, before)


def test_rollback_withdraws_only_this_batch_reservation():
    """Pre-existing in-flight work must survive a failed batch rollback.

    `_due_contexts` does not require `in_flight == 0`, so a participant can be
    due while an earlier action is still outstanding. Clearing the aggregate
    would erase that earlier work from the counters.
    """
    batch = _batch(
        SimpleNamespace(admit_actions_concurrently=lambda requests, snapshot, workers: ()),
        in_flight=1,
    )
    before = batch.run.working

    _execute_concurrent_batch(batch)

    assert batch.run.failure is not None
    for address in _PARTICIPANTS:
        state = ParticipantAutonomousExecutionStateModel.model_validate(
            batch.run.working.participant_autonomous_execution_states[_state_key(address)]
        )
        assert (state.in_flight, state.attempted_actions) == (1, 1)
        assert state.attempted_actions == state.succeeded_actions + state.failed_actions + state.in_flight
    assert batch.run.working.participant_autonomous_execution_states == before.participant_autonomous_execution_states
