"""Backend call adapters for runtime execution."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from copy import deepcopy

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.planning import ProvisioningPlan
from aces_contracts.runtime_state import ApplyResult, RealizationProvenanceEntry, RuntimeSnapshot
from aces_processor.models import CompiledRealizationRequirement
from aces_processor.planner import realization_disclosure

from .diagnostics import _failure_diagnostic
from .evaluation_result_contracts import evaluation_result_contract_diagnostics
from .participant_result_contracts import (
    participant_runtime_history_transition_diagnostics,
    participant_runtime_state_contract_diagnostics,
)
from .workflow_result_contracts import workflow_result_contract_diagnostics

_BACKEND_CONTRACT_INVALID = "runtime.backend-contract-invalid"


def _call_backend_diagnostics(
    method: Callable[..., object],
    *args: object,
    address: str,
) -> list[Diagnostic]:
    try:
        result = method(*args)
    except Exception as exc:
        diagnostics = [_backend_call_failed(address, exc)]
    else:
        invalid_message = _diagnostics_iterable_violation(result, address)
        if invalid_message is not None:
            diagnostics = [_backend_contract_invalid(address, invalid_message)]
        else:
            diagnostics = list(result)
            invalid_message = _diagnostics_values_violation(diagnostics, address)
            if invalid_message is not None:
                diagnostics = [_backend_contract_invalid(address, invalid_message)]
    return diagnostics


def _call_backend_apply(
    method: Callable[..., object],
    *args: object,
    address: str,
    snapshot: RuntimeSnapshot,
    realization_requirements: tuple[CompiledRealizationRequirement, ...] = (),
    realization_plan: ProvisioningPlan | None = None,
) -> ApplyResult:
    baseline_snapshot = deepcopy(snapshot)
    backend_snapshot = deepcopy(snapshot)
    backend_args = tuple(backend_snapshot if arg is snapshot else arg for arg in args)
    try:
        result = method(*backend_args)
    except Exception as exc:
        return _failed_apply_result(baseline_snapshot, _backend_call_failed(address, exc))
    return _finalize_backend_apply(
        result,
        address=address,
        baseline_snapshot=baseline_snapshot,
        realization_requirements=realization_requirements,
        realization_plan=realization_plan,
    )


def _finalize_backend_apply(
    result: object,
    *,
    address: str,
    baseline_snapshot: RuntimeSnapshot,
    realization_requirements: tuple[CompiledRealizationRequirement, ...],
    realization_plan: ProvisioningPlan | None,
) -> ApplyResult:
    """Validate a backend's apply result and gate its realized snapshot.

    Rejects (returning the baseline snapshot, ``success=False``) on a malformed
    result, a snapshot-contract violation, or a SEM-218 non-approximation
    violation; otherwise returns the backend result, augmented with the
    realization-provenance ledger when the gate disclosed one.
    """

    invalid_message = _apply_result_contract_violation(result, address)
    if invalid_message is not None:
        return _failed_apply_result(baseline_snapshot, _backend_contract_invalid(address, invalid_message))
    assert isinstance(result, ApplyResult)
    contract_diagnostics = _snapshot_contract_diagnostics(result.snapshot)
    if not contract_diagnostics:
        contract_diagnostics = _snapshot_transition_contract_diagnostics(baseline_snapshot, result.snapshot)
    realization_provenance: tuple[RealizationProvenanceEntry, ...] = ()
    if not contract_diagnostics and realization_requirements and realization_plan is not None:
        # SEM-218 I2 non-approximation gate + I5 provenance disclosure.
        contract_diagnostics, realization_provenance = realization_disclosure(
            realization_requirements,
            realization_plan,
            result.snapshot,
        )
    if contract_diagnostics:
        return ApplyResult(success=False, snapshot=baseline_snapshot, diagnostics=contract_diagnostics)
    if realization_provenance:
        return _with_realization_provenance(result, realization_provenance)
    return result


def _with_realization_provenance(
    result: ApplyResult,
    provenance: tuple[RealizationProvenanceEntry, ...],
) -> ApplyResult:
    """Attach the SEM-218 provenance ledger to a successful apply's snapshot."""

    return ApplyResult(
        success=result.success,
        snapshot=result.snapshot.with_entries(
            dict(result.snapshot.entries),
            realization_provenance=provenance,
        ),
        diagnostics=result.diagnostics,
        changed_addresses=result.changed_addresses,
        details=result.details,
    )


def _backend_call_failed(address: str, exc: Exception) -> Diagnostic:
    return _failure_diagnostic(
        "runtime.backend-call-failed",
        address,
        f"Backend method '{address}' raised {type(exc).__name__}: {exc}.",
    )


def _backend_contract_invalid(address: str, message: str) -> Diagnostic:
    return _failure_diagnostic(_BACKEND_CONTRACT_INVALID, address, message)


def _failed_apply_result(snapshot: RuntimeSnapshot, diagnostic: Diagnostic) -> ApplyResult:
    return ApplyResult(success=False, snapshot=snapshot, diagnostics=[diagnostic])


def _diagnostics_iterable_violation(result: object, address: str) -> str | None:
    message = None
    if not isinstance(result, Iterable) or isinstance(result, (str, bytes)):
        message = f"Backend method '{address}' returned {type(result).__name__}; expected diagnostics iterable."
    return message


def _diagnostics_values_violation(diagnostics: list[object], address: str) -> str | None:
    message = None
    if any(not isinstance(diagnostic, Diagnostic) for diagnostic in diagnostics):
        message = f"Backend method '{address}' returned a diagnostics iterable containing non-Diagnostic values."
    return message


def _apply_result_contract_violation(result: object, address: str) -> str | None:
    message = _apply_result_shape_violation(result, address)
    if message is None and isinstance(result, ApplyResult):
        message = _apply_result_diagnostics_violation(result, address)
    if message is None and isinstance(result, ApplyResult):
        message = _apply_result_changed_addresses_violation(result, address)
    if message is None and isinstance(result, ApplyResult):
        message = _apply_result_details_violation(result, address)
    return message


def _apply_result_shape_violation(result: object, address: str) -> str | None:
    message = None
    if not isinstance(result, ApplyResult):
        message = f"Backend method '{address}' returned {type(result).__name__}; expected ApplyResult."
    elif not isinstance(result.snapshot, RuntimeSnapshot):
        message = (
            f"Backend method '{address}' returned ApplyResult.snapshot "
            f"as {type(result.snapshot).__name__}; expected RuntimeSnapshot."
        )
    return message


def _apply_result_diagnostics_violation(result: ApplyResult, address: str) -> str | None:
    message = None
    if not isinstance(result.diagnostics, Iterable) or isinstance(result.diagnostics, (str, bytes)):
        message = (
            f"Backend method '{address}' returned ApplyResult.diagnostics "
            f"as {type(result.diagnostics).__name__}; expected iterable."
        )
    elif any(not isinstance(diagnostic, Diagnostic) for diagnostic in result.diagnostics):
        message = f"Backend method '{address}' returned ApplyResult.diagnostics containing non-Diagnostic values."
    return message


def _apply_result_changed_addresses_violation(result: ApplyResult, address: str) -> str | None:
    message = None
    if not isinstance(result.changed_addresses, list):
        message = (
            f"Backend method '{address}' returned ApplyResult.changed_addresses "
            f"as {type(result.changed_addresses).__name__}; expected list."
        )
    elif any(not isinstance(changed_address, str) for changed_address in result.changed_addresses):
        message = f"Backend method '{address}' returned ApplyResult.changed_addresses containing non-string values."
    return message


def _apply_result_details_violation(result: ApplyResult, address: str) -> str | None:
    if isinstance(result.details, dict):
        return None
    return f"Backend method '{address}' returned ApplyResult.details as {type(result.details).__name__}; expected dict."


def _snapshot_contract_diagnostics(snapshot: RuntimeSnapshot) -> list[Diagnostic]:
    diagnostics = workflow_result_contract_diagnostics(snapshot)
    if diagnostics:
        return diagnostics
    diagnostics = evaluation_result_contract_diagnostics(snapshot)
    if diagnostics:
        return diagnostics
    return participant_runtime_state_contract_diagnostics(snapshot)


def _snapshot_transition_contract_diagnostics(
    previous_snapshot: RuntimeSnapshot,
    next_snapshot: RuntimeSnapshot,
) -> list[Diagnostic]:
    return participant_runtime_history_transition_diagnostics(previous_snapshot, next_snapshot)
