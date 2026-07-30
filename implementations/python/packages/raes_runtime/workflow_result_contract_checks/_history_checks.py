"""Workflow history contract checks (event ordering, targets, terminal/compensation rules)."""

from __future__ import annotations

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.workflow import (
    WorkflowHistoryEvent,
    WorkflowHistoryEventType,
    WorkflowStatus,
)

from ..workflow_result_contract_compensation import (
    compensation_history_diagnostics as _compensation_history_diagnostics_impl,
)
from ._models import (
    _COMPENSATION_EVENT_TYPES,
    _TERMINAL_EVENT_TYPES,
    _contract_diagnostic,
    _WorkflowContext,
)


def _workflow_history_contract_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    if not context.history:
        return []
    diagnostics = _history_start_diagnostics(context)
    for event in context.history:
        diagnostics.extend(_history_event_diagnostics(context, event))
    diagnostics.extend(_terminal_history_diagnostics(context))
    diagnostics.extend(_running_history_diagnostics(context))
    diagnostics.extend(_compensation_history_diagnostics(context))
    return diagnostics


def _history_start_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    if context.history[0].event_type == WorkflowHistoryEventType.WORKFLOW_STARTED:
        return []
    return [_contract_diagnostic(context.address, "Workflow history must start with workflow_started.")]


def _history_event_diagnostics(
    context: _WorkflowContext,
    event: WorkflowHistoryEvent,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if event.step_name and event.step_name not in context.execution_contract.steps:
        diagnostics.append(
            _contract_diagnostic(context.address, f"Workflow history references unknown step '{event.step_name}'.")
        )
    diagnostics.extend(_switch_history_event_diagnostics(context, event))
    diagnostics.extend(_call_history_event_diagnostics(context, event))
    diagnostics.extend(_branch_history_event_diagnostics(context, event))
    diagnostics.extend(_compensation_registration_diagnostics(context, event))
    diagnostics.extend(_compensation_workflow_event_diagnostics(context, event))
    return diagnostics


def _switch_history_event_diagnostics(context: _WorkflowContext, event: WorkflowHistoryEvent) -> list[Diagnostic]:
    if event.event_type != WorkflowHistoryEventType.SWITCH_CASE_SELECTED:
        return []
    if event.step_name is not None and context.execution_contract.step_types.get(event.step_name) == "switch":
        return []
    return [_contract_diagnostic(context.address, "switch_case_selected events must reference a switch step.")]


def _call_history_event_diagnostics(context: _WorkflowContext, event: WorkflowHistoryEvent) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if event.event_type in {WorkflowHistoryEventType.CALL_STARTED, WorkflowHistoryEventType.CALL_COMPLETED}:
        if event.step_name is None or context.execution_contract.step_types.get(event.step_name) != "call":
            diagnostics.append(
                _contract_diagnostic(context.address, f"{event.event_type.value} events must reference a call step.")
            )
        else:
            expected_workflow = context.execution_contract.call_steps.get(event.step_name)
            actual_workflow = str(event.details.get("workflow_address", ""))
            if expected_workflow and actual_workflow and actual_workflow != expected_workflow:
                diagnostics.append(
                    _workflow_target_mismatch(context, event, actual_workflow, expected_workflow, "call target")
                )
    return diagnostics


def _workflow_target_mismatch(
    context: _WorkflowContext,
    event: WorkflowHistoryEvent,
    actual_workflow: str,
    expected_workflow: str,
    target_label: str,
) -> Diagnostic:
    return _contract_diagnostic(
        context.address,
        (
            f"{event.event_type.value} event workflow {actual_workflow!r} "
            f"does not match {target_label} {expected_workflow!r}."
        ),
    )


def _branch_history_event_diagnostics(context: _WorkflowContext, event: WorkflowHistoryEvent) -> list[Diagnostic]:
    if event.event_type != WorkflowHistoryEventType.BRANCH_CONVERGED:
        return []
    if event.join_step is not None and event.join_step in context.execution_contract.join_owners:
        return []
    return [_contract_diagnostic(context.address, "branch_converged events must reference a known join_step.")]


def _compensation_registration_diagnostics(context: _WorkflowContext, event: WorkflowHistoryEvent) -> list[Diagnostic]:
    if event.event_type != WorkflowHistoryEventType.COMPENSATION_REGISTERED:
        return []
    if event.step_name is not None and event.step_name in context.execution_contract.compensation_targets:
        return []
    return [_contract_diagnostic(context.address, "compensation_registered events must reference a compensable step.")]


def _compensation_workflow_event_diagnostics(
    context: _WorkflowContext, event: WorkflowHistoryEvent
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if event.event_type in {
        WorkflowHistoryEventType.COMPENSATION_WORKFLOW_STARTED,
        WorkflowHistoryEventType.COMPENSATION_WORKFLOW_COMPLETED,
        WorkflowHistoryEventType.COMPENSATION_WORKFLOW_FAILED,
    }:
        if event.step_name is None or event.step_name not in context.execution_contract.compensation_targets:
            diagnostics.append(
                _contract_diagnostic(
                    context.address,
                    f"{event.event_type.value} events must reference a compensable step.",
                )
            )
        else:
            expected_workflow = context.execution_contract.compensation_targets[event.step_name]
            actual_workflow = str(event.details.get("workflow_address", ""))
            if actual_workflow and actual_workflow != expected_workflow:
                diagnostics.append(
                    _workflow_target_mismatch(
                        context,
                        event,
                        actual_workflow,
                        expected_workflow,
                        "compensation target",
                    )
                )
    return diagnostics


def _terminal_history_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    expected_terminal = _TERMINAL_EVENT_TYPES.get(context.result.workflow_status)
    if expected_terminal is None:
        return []
    terminal_indexes = [index for index, event in enumerate(context.history) if event.event_type == expected_terminal]
    diagnostics = _missing_terminal_event_diagnostics(context, expected_terminal, terminal_indexes)
    diagnostics.extend(_compensation_order_diagnostics(context, terminal_indexes))
    return diagnostics


def _missing_terminal_event_diagnostics(
    context: _WorkflowContext,
    expected_terminal: WorkflowHistoryEventType,
    terminal_indexes: list[int],
) -> list[Diagnostic]:
    if terminal_indexes:
        return []
    return [
        _contract_diagnostic(
            context.address,
            (
                "Workflow terminal status "
                f"{context.result.workflow_status.value!r} requires a history event "
                f"{expected_terminal.value!r}."
            ),
        )
    ]


def _compensation_order_diagnostics(
    context: _WorkflowContext,
    terminal_indexes: list[int],
) -> list[Diagnostic]:
    compensation_indexes = [
        index for index, event in enumerate(context.history) if event.event_type in _COMPENSATION_EVENT_TYPES
    ]
    if compensation_indexes and terminal_indexes and terminal_indexes[-1] > compensation_indexes[0]:
        return [
            _contract_diagnostic(
                context.address,
                "Compensation events may only occur after the primary terminal workflow event.",
            )
        ]
    return []


def _running_history_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    if context.result.workflow_status != WorkflowStatus.RUNNING:
        return []
    if context.history[-1].event_type not in _TERMINAL_EVENT_TYPES.values():
        return []
    return [_contract_diagnostic(context.address, "Running workflows may not end history with a terminal event.")]


def _compensation_history_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    return _compensation_history_diagnostics_impl(
        context,
        _COMPENSATION_EVENT_TYPES,
        _contract_diagnostic,
    )
