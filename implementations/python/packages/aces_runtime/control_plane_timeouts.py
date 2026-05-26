"""Workflow timeout reconciliation helpers for the runtime control plane."""

from __future__ import annotations

from aces_contracts.planning import RuntimeDomain
from aces_contracts.runtime_state import RuntimeSnapshot, SnapshotEntry
from aces_contracts.workflow import (
    WorkflowCompensationStatus,
    WorkflowExecutionState,
    WorkflowHistoryEvent,
    WorkflowHistoryEventType,
    WorkflowStatus,
)

from .control_plane_workflows import maybe_apply_compensation, parse_timestamp


def workflow_timeout_update(
    snapshot: RuntimeSnapshot,
    workflow_address: str,
    entry: SnapshotEntry,
    orchestration_results: dict[str, dict[str, object]],
    orchestration_history: dict[str, list[dict[str, object]]],
    submitted_at: str,
) -> tuple[dict[str, object], list[dict[str, object]]] | None:
    if entry.domain != RuntimeDomain.ORCHESTRATION or entry.resource_type != "workflow":
        return None
    timeout_seconds = _workflow_timeout_seconds(entry.payload)
    if timeout_seconds is None:
        return None
    result_payload = orchestration_results.get(workflow_address)
    if not isinstance(result_payload, dict):
        return None
    normalized = WorkflowExecutionState.from_payload(result_payload)
    if normalized.workflow_status != WorkflowStatus.RUNNING:
        return None
    if not _workflow_has_timed_out(normalized, timeout_seconds, submitted_at):
        return None
    return _timed_out_workflow_update(
        snapshot,
        workflow_address,
        normalized,
        timeout_seconds,
        orchestration_history,
        submitted_at,
    )


def _workflow_timeout_seconds(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    execution_contract_payload = payload.get("execution_contract")
    if not isinstance(execution_contract_payload, dict):
        return None
    timeout_seconds = execution_contract_payload.get("timeout_seconds")
    if timeout_seconds in (None, "", 0):
        return None
    try:
        return int(timeout_seconds)
    except (TypeError, ValueError):
        return None


def _workflow_has_timed_out(
    normalized: WorkflowExecutionState,
    timeout_seconds: int,
    submitted_at: str,
) -> bool:
    try:
        deadline = parse_timestamp(normalized.started_at).timestamp() + timeout_seconds
        current = parse_timestamp(submitted_at).timestamp()
    except Exception:
        return False
    return current >= deadline


def _timed_out_workflow_update(
    snapshot: RuntimeSnapshot,
    workflow_address: str,
    normalized: WorkflowExecutionState,
    timeout_seconds: int,
    orchestration_history: dict[str, list[dict[str, object]]],
    submitted_at: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    timed_out_state = _timed_out_workflow_state(normalized, submitted_at)
    history = orchestration_history.setdefault(workflow_address, [])
    history.append(
        WorkflowHistoryEvent(
            event_type=WorkflowHistoryEventType.WORKFLOW_TIMED_OUT,
            timestamp=submitted_at,
            details={"timeout_seconds": timeout_seconds},
        ).to_payload()
    )
    return maybe_apply_compensation(
        snapshot,
        workflow_address=workflow_address,
        result=timed_out_state,
        history=history,
        submitted_at=submitted_at,
    )


def _timed_out_workflow_state(
    normalized: WorkflowExecutionState,
    submitted_at: str,
) -> WorkflowExecutionState:
    return WorkflowExecutionState(
        state_schema_version=normalized.state_schema_version,
        workflow_status=WorkflowStatus.TIMED_OUT,
        run_id=normalized.run_id,
        started_at=normalized.started_at,
        updated_at=submitted_at,
        terminal_reason="workflow timed out",
        compensation_status=WorkflowCompensationStatus.NOT_REQUIRED,
        compensation_started_at=None,
        compensation_updated_at=None,
        compensation_failures=[],
        steps=normalized.steps,
    )
