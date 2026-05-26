"""Backend call adapters for runtime execution."""

from __future__ import annotations

from collections.abc import Iterable

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot

from .diagnostics import _failure_diagnostic
from .evaluation_result_contracts import evaluation_result_contract_diagnostics
from .participant_result_contracts import participant_episode_contract_diagnostics
from .workflow_result_contracts import workflow_result_contract_diagnostics

_BACKEND_CONTRACT_INVALID = "runtime.backend-contract-invalid"


def _call_backend_diagnostics(
    method,
    *args,
    address: str,
) -> list[Diagnostic]:
    try:
        result = method(*args)
    except Exception as exc:
        return [
            _failure_diagnostic(
                "runtime.backend-call-failed",
                address,
                (f"Backend method '{address}' raised {type(exc).__name__}: {exc}."),
            )
        ]

    if not isinstance(result, Iterable) or isinstance(result, (str, bytes)):
        return [
            _failure_diagnostic(
                _BACKEND_CONTRACT_INVALID,
                address,
                (f"Backend method '{address}' returned {type(result).__name__}; expected diagnostics iterable."),
            )
        ]

    diagnostics = list(result)
    if any(not isinstance(diagnostic, Diagnostic) for diagnostic in diagnostics):
        return [
            _failure_diagnostic(
                _BACKEND_CONTRACT_INVALID,
                address,
                (f"Backend method '{address}' returned a diagnostics iterable containing non-Diagnostic values."),
            )
        ]

    return diagnostics


def _call_backend_apply(
    method,
    *args,
    address: str,
    snapshot: RuntimeSnapshot,
) -> ApplyResult:
    try:
        result = method(*args)
    except Exception as exc:
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                _failure_diagnostic(
                    "runtime.backend-call-failed",
                    address,
                    (f"Backend method '{address}' raised {type(exc).__name__}: {exc}."),
                )
            ],
        )

    if not isinstance(result, ApplyResult):
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                _failure_diagnostic(
                    _BACKEND_CONTRACT_INVALID,
                    address,
                    (f"Backend method '{address}' returned {type(result).__name__}; expected ApplyResult."),
                )
            ],
        )

    if not isinstance(result.snapshot, RuntimeSnapshot):
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                _failure_diagnostic(
                    _BACKEND_CONTRACT_INVALID,
                    address,
                    (
                        f"Backend method '{address}' returned ApplyResult.snapshot "
                        f"as {type(result.snapshot).__name__}; expected RuntimeSnapshot."
                    ),
                )
            ],
        )

    if not isinstance(result.diagnostics, Iterable) or isinstance(result.diagnostics, (str, bytes)):
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                _failure_diagnostic(
                    _BACKEND_CONTRACT_INVALID,
                    address,
                    (
                        f"Backend method '{address}' returned ApplyResult.diagnostics "
                        f"as {type(result.diagnostics).__name__}; expected iterable."
                    ),
                )
            ],
        )

    if any(not isinstance(diagnostic, Diagnostic) for diagnostic in result.diagnostics):
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                _failure_diagnostic(
                    _BACKEND_CONTRACT_INVALID,
                    address,
                    (f"Backend method '{address}' returned ApplyResult.diagnostics containing non-Diagnostic values."),
                )
            ],
        )

    if not isinstance(result.changed_addresses, list):
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                _failure_diagnostic(
                    _BACKEND_CONTRACT_INVALID,
                    address,
                    (
                        f"Backend method '{address}' returned ApplyResult.changed_addresses "
                        f"as {type(result.changed_addresses).__name__}; expected list."
                    ),
                )
            ],
        )

    if any(not isinstance(changed_address, str) for changed_address in result.changed_addresses):
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                _failure_diagnostic(
                    _BACKEND_CONTRACT_INVALID,
                    address,
                    (
                        f"Backend method '{address}' returned ApplyResult.changed_addresses "
                        "containing non-string values."
                    ),
                )
            ],
        )

    if not isinstance(result.details, dict):
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                _failure_diagnostic(
                    _BACKEND_CONTRACT_INVALID,
                    address,
                    (
                        f"Backend method '{address}' returned ApplyResult.details "
                        f"as {type(result.details).__name__}; expected dict."
                    ),
                )
            ],
        )

    workflow_result_diagnostics = workflow_result_contract_diagnostics(result.snapshot)
    if workflow_result_diagnostics:
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=workflow_result_diagnostics,
        )
    evaluation_result_diagnostics = evaluation_result_contract_diagnostics(result.snapshot)
    if evaluation_result_diagnostics:
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=evaluation_result_diagnostics,
        )
    participant_episode_result_diagnostics = participant_episode_contract_diagnostics(result.snapshot)
    if participant_episode_result_diagnostics:
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=participant_episode_result_diagnostics,
        )

    return result
