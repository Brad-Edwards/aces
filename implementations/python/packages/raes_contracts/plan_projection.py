"""Project internal plan dataclasses into published plan contract models (issue #609).

Forward counterpart of the reverse converters in
``raes_runtime.control_plane_api_models``: maps the in-memory
``raes_contracts.planning`` plan dataclasses the planner produces into the
published ``ProvisioningPlanModel`` / ``OrchestrationPlanModel`` /
``EvaluationPlanModel`` contract models. Constructing each model runs its
closed-world (``extra="forbid"``) validators -- unique operation addresses,
domain/resource identity, startup-order references -- so a projected plan is a
valid published-contract instance before serialization.

Only the published plan surface is projected: operations, startup order,
diagnostics, and (for provisioning) the realization-envelope identity. The
internal ``resources`` map and the compiled model / manifest / snapshot / target
binding carried by the composite ``ExecutionPlan`` are deliberately excluded;
they are not part of any published plan contract.
"""

from __future__ import annotations

from typing import Any

from .contracts import (
    EvaluationPlanModel,
    OrchestrationPlanModel,
    PlanOperationModel,
    ProvisioningPlanModel,
)
from .diagnostics import Diagnostic, diagnostic_payload
from .planning import EvaluationPlan, OrchestrationPlan, PlanOperation, ProvisioningPlan

__all__ = [
    "evaluation_plan_model",
    "orchestration_plan_model",
    "provisioning_plan_model",
]


def _plan_operation_model(operation: PlanOperation) -> PlanOperationModel:
    return PlanOperationModel(
        action=operation.action.value,
        address=operation.address,
        resource_type=operation.resource_type,
        payload=dict(operation.payload),
        ordering_dependencies=list(operation.ordering_dependencies),
        refresh_dependencies=list(operation.refresh_dependencies),
    )


def _diagnostic_payloads(diagnostics: list[Diagnostic]) -> list[dict[str, Any]]:
    return [diagnostic_payload(diagnostic) for diagnostic in diagnostics]


def provisioning_plan_model(plan: ProvisioningPlan) -> ProvisioningPlanModel:
    """Project a provisioning plan into its published contract model."""

    return ProvisioningPlanModel(
        operations=[_plan_operation_model(operation) for operation in plan.operations],
        diagnostics=_diagnostic_payloads(plan.diagnostics),
        realization_envelope=plan.realization_envelope,
        realization_constraints=[
            {
                "address": item.address,
                "field_path": item.field_path,
                "concern": item.concern,
                "posture": item.posture,
                "value_domain": item.value_domain,
                "governing_scope": item.governing_scope,
                "provenance": item.provenance,
            }
            for item in plan.realization_constraints
        ],
        operation_id=plan.operation_id,
    )


def orchestration_plan_model(plan: OrchestrationPlan) -> OrchestrationPlanModel:
    """Project an orchestration plan into its published contract model."""

    return OrchestrationPlanModel(
        operations=[_plan_operation_model(operation) for operation in plan.operations],
        startup_order=list(plan.startup_order),
        diagnostics=_diagnostic_payloads(plan.diagnostics),
    )


def evaluation_plan_model(plan: EvaluationPlan) -> EvaluationPlanModel:
    """Project an evaluation plan into its published contract model."""

    return EvaluationPlanModel(
        operations=[_plan_operation_model(operation) for operation in plan.operations],
        startup_order=list(plan.startup_order),
        diagnostics=_diagnostic_payloads(plan.diagnostics),
    )
