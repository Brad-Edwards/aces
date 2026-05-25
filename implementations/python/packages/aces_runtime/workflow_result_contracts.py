"""Workflow result contract validation for runtime backends."""

from __future__ import annotations

from datetime import datetime

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.planning import RuntimeDomain
from aces_contracts.runtime_state import RuntimeSnapshot
from aces_contracts.workflow import (
    WorkflowCompensationStatus,
    WorkflowExecutionContract,
    WorkflowExecutionState,
    WorkflowHistoryEvent,
    WorkflowHistoryEventType,
    WorkflowResultContract,
    WorkflowStatus,
    validate_workflow_step_result_contract,
)

from .diagnostics import _failure_diagnostic, _parse_timestamp


def workflow_result_contract_diagnostics(
    snapshot: RuntimeSnapshot,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not isinstance(snapshot.orchestration_results, dict):
        return [
            _failure_diagnostic(
                "runtime.backend-contract-invalid",
                "runtime.apply.orchestration-results",
                "RuntimeSnapshot.orchestration_results must be a dict.",
            )
        ]
    if not isinstance(snapshot.orchestration_history, dict):
        return [
            _failure_diagnostic(
                "runtime.backend-contract-invalid",
                "runtime.apply.orchestration-history",
                "RuntimeSnapshot.orchestration_history must be a dict.",
            )
        ]
    workflow_entries = {
        address: entry
        for address, entry in snapshot.entries.items()
        if entry.domain == RuntimeDomain.ORCHESTRATION and entry.resource_type == "workflow"
    }

    for workflow_address, workflow_result in snapshot.orchestration_results.items():
        if not isinstance(workflow_address, str):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    "runtime.apply.orchestration-results",
                    "Workflow orchestration result keys must be strings.",
                )
            )
            continue
        if not isinstance(workflow_result, dict):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    ("Workflow orchestration results must use plain-data mapping values."),
                )
            )
            continue

        workflow_entry = workflow_entries.get(workflow_address)
        if workflow_entry is None:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    ("Workflow orchestration results must correspond to a workflow entry in the runtime snapshot."),
                )
            )
            continue

        payload = workflow_entry.payload
        result_contract_payload = payload.get("result_contract") if isinstance(payload, dict) else None
        execution_contract_payload = payload.get("execution_contract") if isinstance(payload, dict) else None
        if not isinstance(result_contract_payload, dict):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    "Workflow snapshot payload is missing compiled result_contract.",
                )
            )
            continue
        if not isinstance(execution_contract_payload, dict):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    "Workflow snapshot payload is missing compiled execution_contract.",
                )
            )
            continue

        try:
            result_contract = WorkflowResultContract.from_mapping(result_contract_payload)
        except (TypeError, ValueError) as exc:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    f"Workflow result_contract is invalid: {exc}",
                )
            )
            continue
        try:
            execution_contract = WorkflowExecutionContract.from_mapping(execution_contract_payload)
        except (TypeError, ValueError) as exc:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    f"Workflow execution_contract is invalid: {exc}",
                )
            )
            continue

        try:
            normalized_result = WorkflowExecutionState.from_payload(workflow_result)
        except (TypeError, ValueError) as exc:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    f"Workflow result payload is invalid: {exc}",
                )
            )
            continue

        history_payload = snapshot.orchestration_history.get(workflow_address, [])
        if not isinstance(history_payload, list):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    "Workflow history payload must be a list of event mappings.",
                )
            )
            continue
        normalized_history: list[WorkflowHistoryEvent] = []
        for event_payload in history_payload:
            try:
                normalized_history.append(WorkflowHistoryEvent.from_payload(event_payload))
            except (TypeError, ValueError) as exc:
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        workflow_address,
                        f"Workflow history payload is invalid: {exc}",
                    )
                )
        if normalized_history:
            previous_timestamp: datetime | None = None
            for event in normalized_history:
                try:
                    current_timestamp = _parse_timestamp(event.timestamp)
                except ValueError as exc:
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            workflow_address,
                            f"Workflow history event timestamp is invalid: {exc}",
                        )
                    )
                    continue
                if previous_timestamp is not None and current_timestamp < previous_timestamp:
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            workflow_address,
                            "Workflow history timestamps must be monotonic.",
                        )
                    )
                previous_timestamp = current_timestamp

        if normalized_result.state_schema_version != result_contract.state_schema_version:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    (
                        "Workflow result schema version "
                        f"{normalized_result.state_schema_version!r} does not match "
                        f"compiled contract {result_contract.state_schema_version!r}."
                    ),
                )
            )
        if normalized_result.state_schema_version != execution_contract.state_schema_version:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    (
                        "Workflow result schema version "
                        f"{normalized_result.state_schema_version!r} does not match "
                        f"execution contract {execution_contract.state_schema_version!r}."
                    ),
                )
            )

        successful_compensation_steps = {
            step_name
            for step_name, workflow_address_target in execution_contract.compensation_targets.items()
            if workflow_address_target
            and step_name in normalized_result.steps
            and normalized_result.steps[step_name].lifecycle == normalized_result.steps[step_name].lifecycle.COMPLETED
            and normalized_result.steps[step_name].outcome is not None
            and normalized_result.steps[step_name].outcome.value == "succeeded"
        }

        if (
            normalized_result.workflow_status in {WorkflowStatus.PENDING, WorkflowStatus.RUNNING}
            and normalized_result.compensation_status != WorkflowCompensationStatus.NOT_REQUIRED
        ):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    "Non-terminal workflows may not report compensation activity.",
                )
            )

        if (
            execution_contract.compensation_mode == "automatic"
            and normalized_result.workflow_status.value in set(execution_contract.compensation_triggers)
            and successful_compensation_steps
            and normalized_result.compensation_status == WorkflowCompensationStatus.NOT_REQUIRED
        ):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    "Terminal workflow requires compensation activity for completed compensable steps.",
                )
            )

        unexpected_steps = sorted(
            step_name for step_name in normalized_result.steps if step_name not in result_contract.observable_steps
        )
        if unexpected_steps:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    ("Workflow results include non-observable or undefined steps: " + ", ".join(unexpected_steps)),
                )
            )

        missing_steps = sorted(
            step_name for step_name in result_contract.observable_steps if step_name not in normalized_result.steps
        )
        if missing_steps:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    workflow_address,
                    ("Workflow results must include all observable steps: " + ", ".join(missing_steps)),
                )
            )

        for step_name, step_state in normalized_result.steps.items():
            contract = result_contract.observable_steps.get(step_name)
            if contract is None:
                continue
            violations = validate_workflow_step_result_contract(
                contract,
                lifecycle=step_state.lifecycle.value,
                outcome=step_state.outcome.value if step_state.outcome else None,
                attempts=step_state.attempts,
            )
            for violation in violations:
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        f"{workflow_address}.{step_name}",
                        violation,
                    )
                )

        for step_name, step_state in normalized_result.steps.items():
            if step_name not in execution_contract.steps:
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        workflow_address,
                        f"Workflow results reference unknown step '{step_name}'.",
                    )
                )
                continue
            if step_state.lifecycle == step_state.lifecycle.COMPLETED:
                step_contract = execution_contract.steps[step_name]
                if (
                    step_state.outcome is not None
                    and step_contract.state_observable
                    and step_state.outcome.value not in step_contract.observable_outcomes
                ):
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            f"{workflow_address}.{step_name}",
                            (
                                f"Completed step reports outcome {step_state.outcome.value!r} "
                                f"outside execution contract domain "
                                f"{step_contract.observable_outcomes!r}."
                            ),
                        )
                    )

        terminal_event_types = {
            WorkflowStatus.SUCCEEDED: WorkflowHistoryEventType.WORKFLOW_COMPLETED,
            WorkflowStatus.FAILED: WorkflowHistoryEventType.WORKFLOW_FAILED,
            WorkflowStatus.CANCELLED: WorkflowHistoryEventType.WORKFLOW_CANCELLED,
            WorkflowStatus.TIMED_OUT: WorkflowHistoryEventType.WORKFLOW_TIMED_OUT,
        }
        if normalized_history:
            compensation_event_types = {
                WorkflowHistoryEventType.COMPENSATION_REGISTERED,
                WorkflowHistoryEventType.COMPENSATION_STARTED,
                WorkflowHistoryEventType.COMPENSATION_WORKFLOW_STARTED,
                WorkflowHistoryEventType.COMPENSATION_WORKFLOW_COMPLETED,
                WorkflowHistoryEventType.COMPENSATION_WORKFLOW_FAILED,
                WorkflowHistoryEventType.COMPENSATION_COMPLETED,
                WorkflowHistoryEventType.COMPENSATION_FAILED,
            }
            if normalized_history[0].event_type != WorkflowHistoryEventType.WORKFLOW_STARTED:
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        workflow_address,
                        "Workflow history must start with workflow_started.",
                    )
                )
            for event in normalized_history:
                if event.step_name and event.step_name not in execution_contract.steps:
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            workflow_address,
                            f"Workflow history references unknown step '{event.step_name}'.",
                        )
                    )
                if (
                    event.event_type == WorkflowHistoryEventType.SWITCH_CASE_SELECTED
                    and event.step_name is not None
                    and execution_contract.step_types.get(event.step_name) != "switch"
                ):
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            workflow_address,
                            "switch_case_selected events must reference a switch step.",
                        )
                    )
                if event.event_type in {
                    WorkflowHistoryEventType.CALL_STARTED,
                    WorkflowHistoryEventType.CALL_COMPLETED,
                }:
                    if event.step_name is None or execution_contract.step_types.get(event.step_name) != "call":
                        diagnostics.append(
                            _failure_diagnostic(
                                "runtime.backend-contract-invalid",
                                workflow_address,
                                f"{event.event_type.value} events must reference a call step.",
                            )
                        )
                    elif execution_contract.call_steps.get(event.step_name):
                        expected_workflow = execution_contract.call_steps[event.step_name]
                        actual_workflow = str(event.details.get("workflow_address", ""))
                        if actual_workflow and actual_workflow != expected_workflow:
                            diagnostics.append(
                                _failure_diagnostic(
                                    "runtime.backend-contract-invalid",
                                    workflow_address,
                                    (
                                        f"{event.event_type.value} event workflow "
                                        f"{actual_workflow!r} does not match call target "
                                        f"{expected_workflow!r}."
                                    ),
                                )
                            )
                if event.event_type == WorkflowHistoryEventType.BRANCH_CONVERGED:
                    if event.join_step is None or event.join_step not in execution_contract.join_owners:
                        diagnostics.append(
                            _failure_diagnostic(
                                "runtime.backend-contract-invalid",
                                workflow_address,
                                "branch_converged events must reference a known join_step.",
                            )
                        )
                if event.event_type == WorkflowHistoryEventType.COMPENSATION_REGISTERED:
                    if event.step_name is None or event.step_name not in execution_contract.compensation_targets:
                        diagnostics.append(
                            _failure_diagnostic(
                                "runtime.backend-contract-invalid",
                                workflow_address,
                                "compensation_registered events must reference a compensable step.",
                            )
                        )
                if event.event_type in {
                    WorkflowHistoryEventType.COMPENSATION_WORKFLOW_STARTED,
                    WorkflowHistoryEventType.COMPENSATION_WORKFLOW_COMPLETED,
                    WorkflowHistoryEventType.COMPENSATION_WORKFLOW_FAILED,
                }:
                    if event.step_name is None or event.step_name not in execution_contract.compensation_targets:
                        diagnostics.append(
                            _failure_diagnostic(
                                "runtime.backend-contract-invalid",
                                workflow_address,
                                f"{event.event_type.value} events must reference a compensable step.",
                            )
                        )
                    else:
                        expected_workflow = execution_contract.compensation_targets[event.step_name]
                        actual_workflow = str(event.details.get("workflow_address", ""))
                        if actual_workflow and actual_workflow != expected_workflow:
                            diagnostics.append(
                                _failure_diagnostic(
                                    "runtime.backend-contract-invalid",
                                    workflow_address,
                                    (
                                        f"{event.event_type.value} event workflow "
                                        f"{actual_workflow!r} does not match compensation target "
                                        f"{expected_workflow!r}."
                                    ),
                                )
                            )
            expected_terminal = terminal_event_types.get(normalized_result.workflow_status)
            if expected_terminal is not None:
                terminal_indexes = [
                    index for index, event in enumerate(normalized_history) if event.event_type == expected_terminal
                ]
                if not terminal_indexes:
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            workflow_address,
                            (
                                "Workflow terminal status "
                                f"{normalized_result.workflow_status.value!r} requires "
                                f"a history event {expected_terminal.value!r}."
                            ),
                        )
                    )
                compensation_indexes = [
                    index
                    for index, event in enumerate(normalized_history)
                    if event.event_type in compensation_event_types
                ]
                if compensation_indexes and terminal_indexes:
                    if terminal_indexes[-1] > compensation_indexes[0]:
                        diagnostics.append(
                            _failure_diagnostic(
                                "runtime.backend-contract-invalid",
                                workflow_address,
                                "Compensation events may only occur after the primary terminal workflow event.",
                            )
                        )
            if (
                normalized_result.workflow_status == WorkflowStatus.RUNNING
                and normalized_history[-1].event_type in terminal_event_types.values()
            ):
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        workflow_address,
                        "Running workflows may not end history with a terminal event.",
                    )
                )
            compensation_events = [
                event for event in normalized_history if event.event_type in compensation_event_types
            ]
            if normalized_result.compensation_status == WorkflowCompensationStatus.NOT_REQUIRED and compensation_events:
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        workflow_address,
                        "Workflows without compensation activity may not emit compensation events.",
                    )
                )
            if normalized_result.compensation_status == WorkflowCompensationStatus.RUNNING and not any(
                event.event_type == WorkflowHistoryEventType.COMPENSATION_STARTED for event in compensation_events
            ):
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        workflow_address,
                        "compensation_status=running requires a compensation_started history event.",
                    )
                )
            if (
                normalized_result.compensation_status == WorkflowCompensationStatus.SUCCEEDED
                and compensation_events
                and compensation_events[-1].event_type != WorkflowHistoryEventType.COMPENSATION_COMPLETED
            ):
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        workflow_address,
                        "compensation_status=succeeded requires a final compensation_completed history event.",
                    )
                )
            if (
                normalized_result.compensation_status == WorkflowCompensationStatus.FAILED
                and compensation_events
                and compensation_events[-1].event_type != WorkflowHistoryEventType.COMPENSATION_FAILED
            ):
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        workflow_address,
                        "compensation_status=failed requires a final compensation_failed history event.",
                    )
                )

    return diagnostics
