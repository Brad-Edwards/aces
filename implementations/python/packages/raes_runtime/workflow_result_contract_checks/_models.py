"""Shared carrier, address constants, and event-type maps for workflow result-contract checks."""

from __future__ import annotations

from dataclasses import dataclass

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.workflow import (
    WorkflowExecutionContract,
    WorkflowExecutionState,
    WorkflowHistoryEvent,
    WorkflowHistoryEventType,
    WorkflowResultContract,
    WorkflowStatus,
)

from ..diagnostics import _failure_diagnostic

_BACKEND_CONTRACT_INVALID = "runtime.backend-contract-invalid"
_ORCHESTRATION_RESULTS_ADDRESS = "runtime.apply.orchestration-results"
_ORCHESTRATION_HISTORY_ADDRESS = "runtime.apply.orchestration-history"
_TERMINAL_EVENT_TYPES = {
    WorkflowStatus.SUCCEEDED: WorkflowHistoryEventType.WORKFLOW_COMPLETED,
    WorkflowStatus.FAILED: WorkflowHistoryEventType.WORKFLOW_FAILED,
    WorkflowStatus.CANCELLED: WorkflowHistoryEventType.WORKFLOW_CANCELLED,
    WorkflowStatus.TIMED_OUT: WorkflowHistoryEventType.WORKFLOW_TIMED_OUT,
}
_COMPENSATION_EVENT_TYPES = {
    WorkflowHistoryEventType.COMPENSATION_REGISTERED,
    WorkflowHistoryEventType.COMPENSATION_STARTED,
    WorkflowHistoryEventType.COMPENSATION_WORKFLOW_STARTED,
    WorkflowHistoryEventType.COMPENSATION_WORKFLOW_COMPLETED,
    WorkflowHistoryEventType.COMPENSATION_WORKFLOW_FAILED,
    WorkflowHistoryEventType.COMPENSATION_COMPLETED,
    WorkflowHistoryEventType.COMPENSATION_FAILED,
}


@dataclass(frozen=True)
class _WorkflowContext:
    address: str
    result_contract: WorkflowResultContract
    execution_contract: WorkflowExecutionContract
    result: WorkflowExecutionState
    history: list[WorkflowHistoryEvent]


def _contract_diagnostic(address: str, message: str) -> Diagnostic:
    return _failure_diagnostic(_BACKEND_CONTRACT_INVALID, address, message)
