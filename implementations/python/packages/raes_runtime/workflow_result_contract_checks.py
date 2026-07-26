"""Workflow result contract validation implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.planning import RuntimeDomain
from raes_contracts.runtime_state import RuntimeSnapshot, SnapshotEntry
from raes_contracts.workflow import (
    WorkflowCompensationStatus,
    WorkflowExecutionContract,
    WorkflowExecutionState,
    WorkflowHistoryEvent,
    WorkflowHistoryEventType,
    WorkflowResultContract,
    WorkflowStatus,
    WorkflowStepExecutionState,
    validate_workflow_step_result_contract,
)

from .diagnostics import _failure_diagnostic, _parse_timestamp
from .workflow_result_contract_compensation import (
    compensation_history_diagnostics as _compensation_history_diagnostics_impl,
)
from .workflow_result_contract_context import compiled_workflow_contracts

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


def workflow_result_contract_diagnostics(
    snapshot: RuntimeSnapshot,
) -> list[Diagnostic]:
    shape_diagnostics = _snapshot_shape_diagnostics(snapshot)
    if shape_diagnostics:
        return shape_diagnostics

    workflow_entries = _workflow_entries(snapshot)
    diagnostics: list[Diagnostic] = []
    for workflow_address, workflow_result in snapshot.orchestration_results.items():
        context, context_diagnostics = _workflow_context(
            snapshot,
            workflow_entries,
            workflow_address,
            workflow_result,
        )
        diagnostics.extend(context_diagnostics)
        if context is not None:
            diagnostics.extend(_workflow_context_diagnostics(context))
    return diagnostics


def _contract_diagnostic(address: str, message: str) -> Diagnostic:
    return _failure_diagnostic(_BACKEND_CONTRACT_INVALID, address, message)


def _snapshot_shape_diagnostics(snapshot: RuntimeSnapshot) -> list[Diagnostic]:
    if not isinstance(snapshot.orchestration_results, dict):
        return [
            _contract_diagnostic(
                _ORCHESTRATION_RESULTS_ADDRESS,
                "RuntimeSnapshot.orchestration_results must be a dict.",
            )
        ]
    if not isinstance(snapshot.orchestration_history, dict):
        return [
            _contract_diagnostic(
                _ORCHESTRATION_HISTORY_ADDRESS,
                "RuntimeSnapshot.orchestration_history must be a dict.",
            )
        ]
    return []


def _workflow_entries(snapshot: RuntimeSnapshot) -> dict[str, SnapshotEntry]:
    return {
        address: entry
        for address, entry in snapshot.entries.items()
        if entry.domain == RuntimeDomain.ORCHESTRATION and entry.resource_type == "workflow"
    }


def _workflow_context(
    snapshot: RuntimeSnapshot,
    workflow_entries: dict[str, SnapshotEntry],
    workflow_address: object,
    workflow_result: object,
) -> tuple[_WorkflowContext | None, list[Diagnostic]]:
    context = None
    diagnostics = _workflow_key_diagnostics(workflow_address, workflow_result)
    if not diagnostics and isinstance(workflow_address, str) and isinstance(workflow_result, dict):
        context, diagnostics = _typed_workflow_context(
            snapshot,
            workflow_entries,
            workflow_address,
            workflow_result,
        )
    return context, diagnostics


def _workflow_key_diagnostics(workflow_address: object, workflow_result: object) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not isinstance(workflow_address, str):
        diagnostics.append(
            _contract_diagnostic(_ORCHESTRATION_RESULTS_ADDRESS, "Workflow orchestration result keys must be strings.")
        )
    elif not isinstance(workflow_result, dict):
        diagnostics.append(
            _contract_diagnostic(workflow_address, "Workflow orchestration results must use plain-data mapping values.")
        )
    return diagnostics


def _typed_workflow_context(
    snapshot: RuntimeSnapshot,
    workflow_entries: dict[str, SnapshotEntry],
    workflow_address: str,
    workflow_result: dict[str, object],
) -> tuple[_WorkflowContext | None, list[Diagnostic]]:
    context = None
    diagnostics: list[Diagnostic] = []
    workflow_entry = workflow_entries.get(workflow_address)
    if workflow_entry is None:
        diagnostics.append(
            _contract_diagnostic(
                workflow_address,
                "Workflow orchestration results must correspond to a workflow entry in the runtime snapshot.",
            )
        )
    else:
        context, diagnostics = _workflow_context_from_entry(snapshot, workflow_address, workflow_result, workflow_entry)
    return context, diagnostics


def _workflow_context_from_entry(
    snapshot: RuntimeSnapshot,
    workflow_address: str,
    workflow_result: dict[str, object],
    workflow_entry: SnapshotEntry,
) -> tuple[_WorkflowContext | None, list[Diagnostic]]:
    context = None
    contracts, diagnostics = compiled_workflow_contracts(workflow_address, workflow_entry, _contract_diagnostic)
    if contracts is not None:
        normalized_result, diagnostics = _normalized_workflow_result(workflow_address, workflow_result)
        if normalized_result is not None:
            normalized_history, diagnostics = _normalized_workflow_history(snapshot, workflow_address)
            if normalized_history is not None:
                result_contract, execution_contract = contracts
                context = _WorkflowContext(
                    workflow_address,
                    result_contract,
                    execution_contract,
                    normalized_result,
                    normalized_history,
                )
    return context, diagnostics


def _normalized_workflow_result(
    workflow_address: str,
    workflow_result: dict[str, object],
) -> tuple[WorkflowExecutionState | None, list[Diagnostic]]:
    try:
        return WorkflowExecutionState.from_payload(workflow_result), []
    except (TypeError, ValueError) as exc:
        return None, [_contract_diagnostic(workflow_address, f"Workflow result payload is invalid: {exc}")]


def _normalized_workflow_history(
    snapshot: RuntimeSnapshot,
    workflow_address: str,
) -> tuple[list[WorkflowHistoryEvent] | None, list[Diagnostic]]:
    history_payload = snapshot.orchestration_history.get(workflow_address, [])
    if not isinstance(history_payload, list):
        return None, [
            _contract_diagnostic(workflow_address, "Workflow history payload must be a list of event mappings.")
        ]
    normalized_history, diagnostics = _normalize_workflow_history_payload(workflow_address, history_payload)
    diagnostics.extend(_timestamp_diagnostics(workflow_address, normalized_history))
    return normalized_history, diagnostics


def _normalize_workflow_history_payload(
    workflow_address: str,
    history_payload: list[object],
) -> tuple[list[WorkflowHistoryEvent], list[Diagnostic]]:
    normalized_history: list[WorkflowHistoryEvent] = []
    diagnostics: list[Diagnostic] = []
    for event_payload in history_payload:
        try:
            normalized_history.append(WorkflowHistoryEvent.from_payload(event_payload))
        except (TypeError, ValueError) as exc:
            diagnostics.append(_contract_diagnostic(workflow_address, f"Workflow history payload is invalid: {exc}"))
    return normalized_history, diagnostics


def _timestamp_diagnostics(
    workflow_address: str,
    normalized_history: list[WorkflowHistoryEvent],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    previous_timestamp: datetime | None = None
    for event in normalized_history:
        try:
            current_timestamp = _parse_timestamp(event.timestamp)
        except ValueError as exc:
            diagnostics.append(
                _contract_diagnostic(workflow_address, f"Workflow history event timestamp is invalid: {exc}")
            )
            continue
        if previous_timestamp is not None and current_timestamp < previous_timestamp:
            diagnostics.append(_contract_diagnostic(workflow_address, "Workflow history timestamps must be monotonic."))
        previous_timestamp = current_timestamp
    return diagnostics


def _workflow_context_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    diagnostics = _schema_diagnostics(context)
    diagnostics.extend(_workflow_compensation_requirement_diagnostics(context))
    diagnostics.extend(_workflow_step_presence_diagnostics(context))
    diagnostics.extend(_workflow_step_contract_diagnostics(context))
    diagnostics.extend(_workflow_execution_step_diagnostics(context))
    diagnostics.extend(_workflow_history_contract_diagnostics(context))
    return diagnostics


def _schema_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if context.result.state_schema_version != context.result_contract.state_schema_version:
        diagnostics.append(
            _contract_diagnostic(
                context.address,
                (
                    "Workflow result schema version "
                    f"{context.result.state_schema_version!r} does not match "
                    f"compiled contract {context.result_contract.state_schema_version!r}."
                ),
            )
        )
    if context.result.state_schema_version != context.execution_contract.state_schema_version:
        diagnostics.append(
            _contract_diagnostic(
                context.address,
                (
                    "Workflow result schema version "
                    f"{context.result.state_schema_version!r} does not match "
                    f"execution contract {context.execution_contract.state_schema_version!r}."
                ),
            )
        )
    return diagnostics


def _workflow_compensation_requirement_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if _non_terminal_workflow_has_compensation(context):
        diagnostics.append(
            _contract_diagnostic(context.address, "Non-terminal workflows may not report compensation activity.")
        )
    if _terminal_workflow_requires_compensation(context):
        diagnostics.append(
            _contract_diagnostic(
                context.address,
                "Terminal workflow requires compensation activity for completed compensable steps.",
            )
        )
    return diagnostics


def _non_terminal_workflow_has_compensation(context: _WorkflowContext) -> bool:
    return (
        context.result.workflow_status in {WorkflowStatus.PENDING, WorkflowStatus.RUNNING}
        and context.result.compensation_status != WorkflowCompensationStatus.NOT_REQUIRED
    )


def _terminal_workflow_requires_compensation(context: _WorkflowContext) -> bool:
    return (
        context.execution_contract.compensation_mode == "automatic"
        and context.result.workflow_status.value in set(context.execution_contract.compensation_triggers)
        and bool(_successful_compensation_steps(context))
        and context.result.compensation_status == WorkflowCompensationStatus.NOT_REQUIRED
    )


def _successful_compensation_steps(context: _WorkflowContext) -> set[str]:
    return {
        step_name
        for step_name, workflow_address_target in context.execution_contract.compensation_targets.items()
        if workflow_address_target
        and step_name in context.result.steps
        and context.result.steps[step_name].lifecycle == context.result.steps[step_name].lifecycle.COMPLETED
        and context.result.steps[step_name].outcome is not None
        and context.result.steps[step_name].outcome.value == "succeeded"
    }


def _workflow_step_presence_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    unexpected_steps = sorted(
        step_name for step_name in context.result.steps if step_name not in context.result_contract.observable_steps
    )
    if unexpected_steps:
        diagnostics.append(
            _contract_diagnostic(
                context.address,
                "Workflow results include non-observable or undefined steps: " + ", ".join(unexpected_steps),
            )
        )
    missing_steps = sorted(
        step_name for step_name in context.result_contract.observable_steps if step_name not in context.result.steps
    )
    if missing_steps:
        diagnostics.append(
            _contract_diagnostic(
                context.address,
                "Workflow results must include all observable steps: " + ", ".join(missing_steps),
            )
        )
    return diagnostics


def _workflow_step_contract_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for step_name, step_state in context.result.steps.items():
        contract = context.result_contract.observable_steps.get(step_name)
        if contract is None:
            continue
        violations = validate_workflow_step_result_contract(
            contract,
            lifecycle=step_state.lifecycle.value,
            outcome=step_state.outcome.value if step_state.outcome else None,
            attempts=step_state.attempts,
        )
        diagnostics.extend(
            _contract_diagnostic(f"{context.address}.{step_name}", violation) for violation in violations
        )
    return diagnostics


def _workflow_execution_step_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for step_name, step_state in context.result.steps.items():
        step_contract = context.execution_contract.steps.get(step_name)
        if step_contract is None:
            diagnostics.append(
                _contract_diagnostic(context.address, f"Workflow results reference unknown step '{step_name}'.")
            )
            continue
        if _completed_outcome_exceeds_contract(step_state, step_contract):
            diagnostics.append(
                _contract_diagnostic(
                    f"{context.address}.{step_name}",
                    (
                        f"Completed step reports outcome {step_state.outcome.value!r} "
                        f"outside execution contract domain {step_contract.observable_outcomes!r}."
                    ),
                )
            )
    return diagnostics


def _completed_outcome_exceeds_contract(
    step_state: WorkflowStepExecutionState,
    step_contract: object,
) -> bool:
    return (
        step_state.lifecycle == step_state.lifecycle.COMPLETED
        and step_state.outcome is not None
        and step_contract.state_observable
        and step_state.outcome.value not in step_contract.observable_outcomes
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
