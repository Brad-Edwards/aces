"""Crash-recovery policy for runtime control-plane startup."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.runtime_state import OperationState

from .control_plane_store import (
    INTERRUPTED_OPERATION_DIAGNOSTIC_CODE,
    ControlPlaneOperationRecord,
)
from .control_plane_store_compatibility import ControlPlaneStoreCommitAdapter


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def reconcile_interrupted_operations(
    store_commits: ControlPlaneStoreCommitAdapter,
    operations: dict[str, ControlPlaneOperationRecord],
) -> dict[str, ControlPlaneOperationRecord]:
    """Seal orphaned non-terminal records without replaying backend effects."""

    recovered_at = _utc_now()
    interrupted = tuple(
        replace(
            record,
            status=replace(
                record.status,
                state=OperationState.FAILED,
                updated_at=recovered_at,
                diagnostics=[
                    *record.status.diagnostics,
                    Diagnostic(
                        code=INTERRUPTED_OPERATION_DIAGNOSTIC_CODE,
                        domain="runtime",
                        address=f"runtime.control-plane.{record.receipt.domain.value}",
                        message=(
                            "Operation was interrupted before its terminal durable commit; "
                            "backend effects may be indeterminate and were not replayed."
                        ),
                    ),
                ],
            ),
        )
        for record in operations.values()
        if record.status.state in {OperationState.ACCEPTED, OperationState.RUNNING}
    )
    if not interrupted:
        return operations
    store_commits.reconcile_interrupted_records(interrupted)
    return {
        **operations,
        **{record.receipt.operation_id: record for record in interrupted},
    }


__all__ = ("reconcile_interrupted_operations",)
