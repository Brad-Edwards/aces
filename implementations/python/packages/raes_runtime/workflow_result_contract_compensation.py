"""Compensation history checks for workflow result contracts."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.workflow import WorkflowCompensationStatus, WorkflowHistoryEvent, WorkflowHistoryEventType

if TYPE_CHECKING:
    from .workflow_result_contract_checks import _WorkflowContext


def compensation_history_diagnostics(
    context: _WorkflowContext,
    compensation_event_types: set[WorkflowHistoryEventType],
    contract_diagnostic: Callable[[str, str], Diagnostic],
) -> list[Diagnostic]:
    compensation_events = [event for event in context.history if event.event_type in compensation_event_types]
    diagnostics = _not_required_compensation_history_diagnostics(context, compensation_events, contract_diagnostic)
    diagnostics.extend(_running_compensation_history_diagnostics(context, compensation_events, contract_diagnostic))
    diagnostics.extend(_completed_compensation_history_diagnostics(context, compensation_events, contract_diagnostic))
    return diagnostics


def _not_required_compensation_history_diagnostics(
    context: _WorkflowContext,
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
    context: _WorkflowContext,
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
    context: _WorkflowContext,
    compensation_events: list[WorkflowHistoryEvent],
    contract_diagnostic: Callable[[str, str], Diagnostic],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    expected = _expected_final_compensation_event(context)
    if compensation_events and expected is not None:
        expected_event, message = expected
        diagnostics = _final_compensation_event_diagnostics(
            context,
            compensation_events,
            expected_event,
            message,
            contract_diagnostic,
        )
    return diagnostics


def _expected_final_compensation_event(
    context: _WorkflowContext,
) -> tuple[WorkflowHistoryEventType, str] | None:
    expected = None
    if context.result.compensation_status == WorkflowCompensationStatus.SUCCEEDED:
        expected = (
            WorkflowHistoryEventType.COMPENSATION_COMPLETED,
            "compensation_status=succeeded requires a final compensation_completed history event.",
        )
    elif context.result.compensation_status == WorkflowCompensationStatus.FAILED:
        expected = (
            WorkflowHistoryEventType.COMPENSATION_FAILED,
            "compensation_status=failed requires a final compensation_failed history event.",
        )
    return expected


def _final_compensation_event_diagnostics(
    context: _WorkflowContext,
    compensation_events: list[WorkflowHistoryEvent],
    expected_event: WorkflowHistoryEventType,
    message: str,
    contract_diagnostic: Callable[[str, str], Diagnostic],
) -> list[Diagnostic]:
    if compensation_events[-1].event_type == expected_event:
        return []
    return [contract_diagnostic(context.address, message)]
