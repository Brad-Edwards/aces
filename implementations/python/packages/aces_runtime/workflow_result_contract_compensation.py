"""Compensation history checks for workflow result contracts."""

from __future__ import annotations

from collections.abc import Callable

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.workflow import WorkflowCompensationStatus, WorkflowHistoryEvent, WorkflowHistoryEventType


def compensation_history_diagnostics(
    context,
    compensation_event_types: set[WorkflowHistoryEventType],
    contract_diagnostic: Callable[[str, str], Diagnostic],
) -> list[Diagnostic]:
    compensation_events = [event for event in context.history if event.event_type in compensation_event_types]
    diagnostics = _not_required_compensation_history_diagnostics(context, compensation_events, contract_diagnostic)
    diagnostics.extend(_running_compensation_history_diagnostics(context, compensation_events, contract_diagnostic))
    diagnostics.extend(_completed_compensation_history_diagnostics(context, compensation_events, contract_diagnostic))
    return diagnostics


def _not_required_compensation_history_diagnostics(
    context,
    compensation_events: list[WorkflowHistoryEvent],
    contract_diagnostic: Callable[[str, str], Diagnostic],
) -> list[Diagnostic]:
    if context.result.compensation_status != WorkflowCompensationStatus.NOT_REQUIRED or not compensation_events:
        return []
    return [
        contract_diagnostic(
            context.address, "Workflows without compensation activity may not emit compensation events."
        )
    ]


def _running_compensation_history_diagnostics(
    context,
    compensation_events: list[WorkflowHistoryEvent],
    contract_diagnostic: Callable[[str, str], Diagnostic],
) -> list[Diagnostic]:
    if context.result.compensation_status != WorkflowCompensationStatus.RUNNING:
        return []
    if any(event.event_type == WorkflowHistoryEventType.COMPENSATION_STARTED for event in compensation_events):
        return []
    return [
        contract_diagnostic(
            context.address, "compensation_status=running requires a compensation_started history event."
        )
    ]


def _completed_compensation_history_diagnostics(
    context,
    compensation_events: list[WorkflowHistoryEvent],
    contract_diagnostic: Callable[[str, str], Diagnostic],
) -> list[Diagnostic]:
    if not compensation_events:
        return []
    if context.result.compensation_status == WorkflowCompensationStatus.SUCCEEDED:
        return _final_compensation_event_diagnostics(
            context,
            compensation_events,
            WorkflowHistoryEventType.COMPENSATION_COMPLETED,
            "compensation_status=succeeded requires a final compensation_completed history event.",
            contract_diagnostic,
        )
    if context.result.compensation_status == WorkflowCompensationStatus.FAILED:
        return _final_compensation_event_diagnostics(
            context,
            compensation_events,
            WorkflowHistoryEventType.COMPENSATION_FAILED,
            "compensation_status=failed requires a final compensation_failed history event.",
            contract_diagnostic,
        )
    return []


def _final_compensation_event_diagnostics(
    context,
    compensation_events: list[WorkflowHistoryEvent],
    expected_event: WorkflowHistoryEventType,
    message: str,
    contract_diagnostic: Callable[[str, str], Diagnostic],
) -> list[Diagnostic]:
    if compensation_events[-1].event_type == expected_event:
        return []
    return [contract_diagnostic(context.address, message)]
