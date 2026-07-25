"""Workflow-runtime assembly and execution-contract compilation."""

from typing import Any

from aces_contracts.versions import WORKFLOW_STATE_SCHEMA_VERSION
from raes.orchestration import Workflow, WorkflowStepType
from raes.scenario import InstantiatedScenario

from ..models import (
    AssertionRuntime,
    Diagnostic,
    WorkflowExecutionContract,
    WorkflowResultContract,
    WorkflowRuntime,
    WorkflowStepRuntime,
)
from .addresses import _workflow_address
from .support import _dedupe, _dedupe_by_value, _dump
from .workflow_steps import _compile_workflow_step, _WorkflowCompilationState, _WorkflowStepContext


def _workflow_timeout_seconds(workflow: Workflow) -> int | None:
    if workflow.timeout is None or not isinstance(workflow.timeout.seconds, int):
        return None
    return workflow.timeout.seconds


def _workflow_join_owners(workflow: Workflow) -> dict[str, str]:
    return {
        step.join: step_name
        for step_name, step in workflow.steps.items()
        if step.type == WorkflowStepType.PARALLEL and step.join
    }


def _workflow_result_contract_steps(
    control_steps: dict[str, WorkflowStepRuntime],
) -> dict[str, Any]:
    return {
        step_name: step_runtime.state_contract
        for step_name, step_runtime in control_steps.items()
        if step_runtime.state_contract.state_observable
    }


def _workflow_predicate_dependency_addresses(state: _WorkflowCompilationState) -> tuple[str, ...]:
    return _dedupe([address for addresses in state.step_predicate_addresses.values() for address in addresses])


def _workflow_compensation_mode(workflow: Workflow) -> str:
    return workflow.compensation.mode.value if workflow.compensation is not None else "disabled"


def _workflow_compensation_triggers(workflow: Workflow) -> tuple[str, ...]:
    return tuple(trigger.value for trigger in (workflow.compensation.on if workflow.compensation is not None else []))


def _workflow_compensation_ordering(workflow: Workflow) -> str:
    return workflow.compensation.order if workflow.compensation is not None else "reverse_completion"


def _workflow_compensation_failure_policy(workflow: Workflow) -> str:
    if workflow.compensation is None:
        return "fail_workflow"
    return workflow.compensation.failure_policy.value


def _workflow_execution_contract(
    workflow: Workflow,
    state: _WorkflowCompilationState,
    result_contract_steps: dict[str, Any],
) -> WorkflowExecutionContract:
    return WorkflowExecutionContract(
        state_schema_version=WORKFLOW_STATE_SCHEMA_VERSION,
        start_step=workflow.start,
        timeout_seconds=_workflow_timeout_seconds(workflow),
        steps={step_name: step_runtime.state_contract for step_name, step_runtime in state.control_steps.items()},
        step_types={step_name: step_runtime.step_type for step_name, step_runtime in state.control_steps.items()},
        control_edges=state.control_edges,
        join_owners=state.join_owners,
        call_steps={
            step_name: step_runtime.called_workflow_address
            for step_name, step_runtime in state.control_steps.items()
            if step_runtime.called_workflow_address
        },
        compensation_mode=_workflow_compensation_mode(workflow),
        compensation_triggers=_workflow_compensation_triggers(workflow),
        compensation_targets=state.compensation_targets,
        compensation_ordering=_workflow_compensation_ordering(workflow),
        compensation_failure_policy=_workflow_compensation_failure_policy(workflow),
        observable_steps=tuple(sorted(result_contract_steps)),
    )


def _compile_workflow_runtime(
    scenario: InstantiatedScenario,
    *,
    name: str,
    workflow: Workflow,
    assertions: dict[str, AssertionRuntime],
    diagnostics: list[Diagnostic],
) -> WorkflowRuntime:
    workflow_address = _workflow_address(name)
    state = _WorkflowCompilationState(join_owners=_workflow_join_owners(workflow))
    context = _WorkflowStepContext(
        scenario=scenario,
        workflow=workflow,
        workflow_address=workflow_address,
        state=state,
        assertions=assertions,
        diagnostics=diagnostics,
    )
    for step_name, step in workflow.steps.items():
        _compile_workflow_step(context, step_name=step_name, step=step)
    objective_addresses = _dedupe(state.referenced_objectives)
    result_contract_steps = _workflow_result_contract_steps(state.control_steps)
    predicate_dependency_addresses = _workflow_predicate_dependency_addresses(state)
    return WorkflowRuntime(
        address=workflow_address,
        name=name,
        start_step=workflow.start,
        referenced_objective_addresses=objective_addresses,
        control_steps=state.control_steps,
        control_edges=state.control_edges,
        join_owners=state.join_owners,
        step_assertion_addresses=state.step_assertion_addresses,
        step_predicate_addresses=state.step_predicate_addresses,
        required_features=_dedupe_by_value(state.required_features),
        required_state_predicate_features=_dedupe_by_value(state.required_state_predicate_features),
        result_contract=WorkflowResultContract(
            state_schema_version=WORKFLOW_STATE_SCHEMA_VERSION,
            observable_steps=result_contract_steps,
        ),
        execution_contract=_workflow_execution_contract(workflow, state, result_contract_steps),
        refresh_dependencies=_dedupe([*objective_addresses, *predicate_dependency_addresses]),
        spec=_dump(workflow),
    )


def _compile_workflows(
    scenario: InstantiatedScenario,
    assertions: dict[str, AssertionRuntime],
    diagnostics: list[Diagnostic],
) -> dict[str, WorkflowRuntime]:
    return {
        _workflow_address(name): _compile_workflow_runtime(
            scenario,
            name=name,
            workflow=workflow,
            assertions=assertions,
            diagnostics=diagnostics,
        )
        for name, workflow in scenario.workflows.items()
    }
