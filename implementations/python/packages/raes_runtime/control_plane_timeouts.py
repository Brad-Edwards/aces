"""Workflow timeout reconciliation helpers for the runtime control plane."""

from __future__ import annotations

from raes_contracts.planning import RuntimeDomain
from raes_contracts.runtime_state import RuntimeSnapshot, SnapshotEntry
from raes_contracts.workflow import (
    WorkflowCompensationStatus,
    WorkflowExecutionState,
    WorkflowHistoryEvent,
    WorkflowHistoryEventType,
    WorkflowStatus,
)

from .control_plane_workflows import maybe_apply_compensation, parse_timestamp

TIMED_OUT_REASON = "workflow timed out"
UNPARSEABLE_START_REASON = "workflow timed out: started_at could not be parsed"


def workflow_timeout_update(
    snapshot: RuntimeSnapshot,
    workflow_address: str,
    entry: SnapshotEntry,
    orchestration_results: dict[str, dict[str, object]],
    orchestration_history: dict[str, list[dict[str, object]]],
    submitted_at: str,
) -> tuple[dict[str, object], list[dict[str, object]]] | None:
    update = None
    timeout_seconds = _eligible_workflow_timeout_seconds(entry)
    normalized = _running_workflow_result(orchestration_results.get(workflow_address))
    terminal_reason = None
    if timeout_seconds is not None and normalized is not None:
        terminal_reason = _workflow_timeout_reason(normalized, timeout_seconds, submitted_at)
    if terminal_reason is not None:
        update = _timed_out_workflow_update(
            snapshot,
            workflow_address,
            normalized,
            timeout_seconds,
            orchestration_history,
            submitted_at,
            terminal_reason,
        )
    return update


def _eligible_workflow_timeout_seconds(entry: SnapshotEntry) -> int | None:
    timeout_seconds = None
    if entry.domain == RuntimeDomain.ORCHESTRATION and entry.resource_type == "workflow":
        timeout_seconds = _workflow_timeout_seconds(entry.payload)
    return timeout_seconds


def _running_workflow_result(result_payload: object) -> WorkflowExecutionState | None:
    normalized = None
    if isinstance(result_payload, dict):
        candidate = WorkflowExecutionState.from_payload(result_payload)
        if candidate.workflow_status == WorkflowStatus.RUNNING:
            normalized = candidate
    return normalized


def _workflow_timeout_seconds(payload: object) -> int | None:
    timeout = None
    if isinstance(payload, dict):
        execution_contract_payload = payload.get("execution_contract")
        if isinstance(execution_contract_payload, dict):
            timeout = _coerce_timeout_seconds(execution_contract_payload.get("timeout_seconds"))
    return timeout


def _coerce_timeout_seconds(raw: object) -> int | None:
    timeout = None
    if raw not in (None, "", 0):
        try:
            timeout = int(raw)
        except (TypeError, ValueError):
            timeout = None
    return timeout


def _workflow_timeout_reason(
    normalized: WorkflowExecutionState,
    timeout_seconds: int,
    submitted_at: str,
) -> str | None:
    """Return the terminal reason when the workflow must time out, else ``None``.

    ``submitted_at`` is the caller's reconciliation clock and governs the whole
    pass, so an unusable value is raised rather than quietly disabling every
    timeout. A running workflow whose own ``started_at`` cannot be parsed has no
    derivable deadline; reporting "not timed out" would pin it in RUNNING
    forever, so it is reclaimed under a distinct reason instead.
    """

    current = parse_timestamp(submitted_at).timestamp()
    try:
        deadline = parse_timestamp(normalized.started_at).timestamp() + timeout_seconds
    except (TypeError, ValueError):
        return UNPARSEABLE_START_REASON
    return TIMED_OUT_REASON if current >= deadline else None


def _timed_out_workflow_update(
    snapshot: RuntimeSnapshot,
    workflow_address: str,
    normalized: WorkflowExecutionState,
    timeout_seconds: int,
    orchestration_history: dict[str, list[dict[str, object]]],
    submitted_at: str,
    terminal_reason: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    timed_out_state = _timed_out_workflow_state(normalized, submitted_at, terminal_reason)
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
    terminal_reason: str,
) -> WorkflowExecutionState:
    return WorkflowExecutionState(
        state_schema_version=normalized.state_schema_version,
        workflow_status=WorkflowStatus.TIMED_OUT,
        run_id=normalized.run_id,
        started_at=normalized.started_at,
        updated_at=submitted_at,
        terminal_reason=terminal_reason,
        compensation_status=WorkflowCompensationStatus.NOT_REQUIRED,
        compensation_started_at=None,
        compensation_updated_at=None,
        compensation_failures=[],
        steps=normalized.steps,
    )
