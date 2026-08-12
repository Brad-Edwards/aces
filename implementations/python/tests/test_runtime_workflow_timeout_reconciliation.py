"""Workflow timeout reconciliation edge cases for the runtime control plane."""

from __future__ import annotations

import pytest
from raes_contracts.planning import RuntimeDomain
from raes_contracts.runtime_state import RuntimeSnapshot, SnapshotEntry
from raes_contracts.workflow import WorkflowExecutionState, WorkflowStatus
from raes_runtime.control_plane_timeouts import (
    TIMED_OUT_REASON,
    UNPARSEABLE_START_REASON,
    workflow_timeout_update,
)

_WORKFLOW_ADDRESS = "orchestration.workflow.response"


def _workflow_entry(timeout_seconds: int = 1) -> SnapshotEntry:
    return SnapshotEntry(
        address=_WORKFLOW_ADDRESS,
        domain=RuntimeDomain.ORCHESTRATION,
        resource_type="workflow",
        payload={"execution_contract": {"timeout_seconds": timeout_seconds}},
    )


def _running_result(started_at: str) -> dict[str, object]:
    """Build a persisted RUNNING workflow payload with ``started_at`` as recorded.

    The payload is edited after construction because the model rejects values it
    considers unusable, while reconciliation reads snapshots back through
    ``WorkflowExecutionState.from_payload`` and must cope with whatever the store
    actually holds.
    """

    payload = WorkflowExecutionState(
        workflow_status=WorkflowStatus.RUNNING,
        run_id="run-1",
        started_at="2000-01-01T00:00:00Z",
        updated_at="2000-01-01T00:00:00Z",
    ).to_payload()
    payload["started_at"] = started_at
    return payload


def _reconcile(started_at: str, submitted_at: str) -> tuple[dict[str, object], list[dict[str, object]]] | None:
    return workflow_timeout_update(
        RuntimeSnapshot(),
        _WORKFLOW_ADDRESS,
        _workflow_entry(),
        {_WORKFLOW_ADDRESS: _running_result(started_at)},
        {},
        submitted_at,
    )


def test_expired_workflow_is_timed_out():
    update = _reconcile("2000-01-01T00:00:00Z", "2000-01-01T00:01:00Z")

    assert update is not None
    assert update[0]["workflow_status"] == WorkflowStatus.TIMED_OUT.value
    assert update[0]["terminal_reason"] == TIMED_OUT_REASON


def test_workflow_inside_its_deadline_is_left_running():
    assert _reconcile("2000-01-01T00:00:00Z", "2000-01-01T00:00:00Z") is None


@pytest.mark.parametrize("started_at", ["None", "not-a-timestamp", "2000-13-45T99:99:99Z"])
def test_workflow_with_unparseable_started_at_is_reclaimed(started_at: str):
    """A running workflow with no derivable deadline must not stay RUNNING forever.

    Swallowing the parse failure and reporting "not timed out" pinned such a
    workflow in RUNNING for the lifetime of the control plane, so reconciliation
    could never reclaim it.
    """
    update = _reconcile(started_at, "2000-01-01T00:01:00Z")

    assert update is not None
    assert update[0]["workflow_status"] == WorkflowStatus.TIMED_OUT.value
    assert update[0]["terminal_reason"] == UNPARSEABLE_START_REASON


def test_unparseable_reconciliation_clock_is_raised_not_swallowed():
    """A bad caller-supplied ``now`` governs every workflow, so it must surface.

    Reported as ``ValueError``; the HTTP adapter maps that to 409 rather than
    silently disabling timeouts for the whole pass.
    """
    with pytest.raises(ValueError):
        _reconcile("2000-01-01T00:00:00Z", "not-a-timestamp")
