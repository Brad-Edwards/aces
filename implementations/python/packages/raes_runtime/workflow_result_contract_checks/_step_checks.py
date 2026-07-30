"""Schema, compensation-requirement, and step-level workflow result-contract checks."""

from __future__ import annotations

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.workflow import (
    WorkflowCompensationStatus,
    WorkflowStatus,
    WorkflowStepExecutionState,
    validate_workflow_step_result_contract,
)

from ._models import _contract_diagnostic, _WorkflowContext


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
