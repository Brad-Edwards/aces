"""Workflow result contract validation implementation.

This package is a thin facade over cohesive subdomains partitioned along the
existing call graph:

* :mod:`._models` - the internal ``_WorkflowContext`` carrier, address
  constants, and terminal/compensation event-type maps.
* :mod:`._context` - snapshot-shape checks and workflow-context normalization.
* :mod:`._step_checks` - schema, compensation-requirement, and step-level checks.
* :mod:`._history_checks` - workflow history contract checks.

Diagnostic order is behavior: the fail-fast snapshot-shape check, the
workflow-result iteration, and the ordered aggregation of schema, compensation
requirement, step presence, step contract, execution contract, history, and
compensation-history diagnostics are all preserved here.

``_WorkflowContext`` is re-exported because
``workflow_result_contract_compensation.py`` imports it from this path under
``TYPE_CHECKING`` and ``workflow_result_contracts.py`` imports
``workflow_result_contract_diagnostics`` from it.
"""

from __future__ import annotations

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.runtime_state import RuntimeSnapshot

from ._context import _snapshot_shape_diagnostics, _workflow_context, _workflow_entries
from ._history_checks import _workflow_history_contract_diagnostics
from ._models import _WorkflowContext
from ._step_checks import (
    _schema_diagnostics,
    _workflow_compensation_requirement_diagnostics,
    _workflow_execution_step_diagnostics,
    _workflow_step_contract_diagnostics,
    _workflow_step_presence_diagnostics,
)


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


def _workflow_context_diagnostics(context: _WorkflowContext) -> list[Diagnostic]:
    diagnostics = _schema_diagnostics(context)
    diagnostics.extend(_workflow_compensation_requirement_diagnostics(context))
    diagnostics.extend(_workflow_step_presence_diagnostics(context))
    diagnostics.extend(_workflow_step_contract_diagnostics(context))
    diagnostics.extend(_workflow_execution_step_diagnostics(context))
    diagnostics.extend(_workflow_history_contract_diagnostics(context))
    return diagnostics
