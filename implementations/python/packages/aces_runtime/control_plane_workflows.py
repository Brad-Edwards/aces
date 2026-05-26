"""Workflow helpers for the runtime control plane."""

from __future__ import annotations

from datetime import UTC, datetime

from aces_contracts.runtime_state import RuntimeSnapshot
from aces_contracts.workflow import (
    WorkflowCompensationStatus,
    WorkflowExecutionContract,
    WorkflowExecutionState,
    WorkflowHistoryEvent,
    WorkflowHistoryEventType,
)


def compiled_execution_contract(
    snapshot: RuntimeSnapshot,
    workflow_address: str,
) -> WorkflowExecutionContract | None:
    entry = snapshot.entries.get(workflow_address)
    if entry is None or not isinstance(entry.payload, dict):
        return None
    payload = entry.payload.get("execution_contract")
    if not isinstance(payload, dict):
        return None
    try:
        return WorkflowExecutionContract.from_mapping(payload)
    except (TypeError, ValueError):
        return None


def maybe_apply_compensation(
    snapshot: RuntimeSnapshot,
    *,
    workflow_address: str,
    result: WorkflowExecutionState,
    history: list[dict[str, object]],
    submitted_at: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    contract = compiled_execution_contract(snapshot, workflow_address)
    if contract is None:
        return result.to_payload(), history
    if contract.compensation_mode != "automatic":
        return result.to_payload(), history
    if result.workflow_status.value not in set(contract.compensation_triggers):
        return result.to_payload(), history

    completed_events = _completed_compensable_events(history, contract)

    if not completed_events:
        return result.to_payload(), history

    ordered = sorted(completed_events, key=lambda event: event.timestamp, reverse=True)
    mutated_history = list(history)
    _append_compensation_history(mutated_history, ordered, contract, result, submitted_at)
    return (
        _compensated_workflow_payload(result, submitted_at),
        mutated_history,
    )


def _completed_compensable_events(
    history: list[dict[str, object]],
    contract: WorkflowExecutionContract,
) -> list[WorkflowHistoryEvent]:
    completed_events: list[WorkflowHistoryEvent] = []
    for raw in history:
        event = _completed_compensable_event(raw, contract)
        if event is not None:
            completed_events.append(event)
    return completed_events


def _completed_compensable_event(
    raw: dict[str, object],
    contract: WorkflowExecutionContract,
) -> WorkflowHistoryEvent | None:
    try:
        event = WorkflowHistoryEvent.from_payload(raw)
    except (TypeError, ValueError):
        return None
    if event.event_type != WorkflowHistoryEventType.STEP_COMPLETED:
        return None
    if event.step_name is None or event.outcome is None:
        return None
    if event.outcome.value != "succeeded":
        return None
    if event.step_name not in contract.compensation_targets:
        return None
    return event


def _append_compensation_history(
    mutated_history: list[dict[str, object]],
    ordered: list[WorkflowHistoryEvent],
    contract: WorkflowExecutionContract,
    result: WorkflowExecutionState,
    submitted_at: str,
) -> None:
    mutated_history.append(
        WorkflowHistoryEvent(
            event_type=WorkflowHistoryEventType.COMPENSATION_STARTED,
            timestamp=submitted_at,
            details={"trigger": result.workflow_status.value},
        ).to_payload()
    )
    for event in ordered:
        _append_step_compensation_history(mutated_history, event, contract, submitted_at)
    mutated_history.append(
        WorkflowHistoryEvent(
            event_type=WorkflowHistoryEventType.COMPENSATION_COMPLETED,
            timestamp=submitted_at,
            details={"count": len(ordered)},
        ).to_payload()
    )


def _append_step_compensation_history(
    mutated_history: list[dict[str, object]],
    event: WorkflowHistoryEvent,
    contract: WorkflowExecutionContract,
    submitted_at: str,
) -> None:
    step_name = event.step_name or ""
    target = contract.compensation_targets[step_name]
    mutated_history.append(
        WorkflowHistoryEvent(
            event_type=WorkflowHistoryEventType.COMPENSATION_REGISTERED,
            timestamp=submitted_at,
            step_name=step_name,
            details={
                "workflow_address": target,
                "completed_at": event.timestamp,
            },
        ).to_payload()
    )
    mutated_history.append(
        WorkflowHistoryEvent(
            event_type=WorkflowHistoryEventType.COMPENSATION_WORKFLOW_STARTED,
            timestamp=submitted_at,
            step_name=step_name,
            details={"workflow_address": target},
        ).to_payload()
    )
    mutated_history.append(
        WorkflowHistoryEvent(
            event_type=WorkflowHistoryEventType.COMPENSATION_WORKFLOW_COMPLETED,
            timestamp=submitted_at,
            step_name=step_name,
            details={"workflow_address": target},
        ).to_payload()
    )


def _compensated_workflow_payload(
    result: WorkflowExecutionState,
    submitted_at: str,
) -> dict[str, object]:
    return WorkflowExecutionState(
        state_schema_version=result.state_schema_version,
        workflow_status=result.workflow_status,
        run_id=result.run_id,
        started_at=result.started_at,
        updated_at=submitted_at,
        terminal_reason=result.terminal_reason,
        compensation_status=WorkflowCompensationStatus.SUCCEEDED,
        compensation_started_at=submitted_at,
        compensation_updated_at=submitted_at,
        compensation_failures=[],
        steps=result.steps,
    ).to_payload()


def parse_timestamp(raw: str) -> datetime:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
