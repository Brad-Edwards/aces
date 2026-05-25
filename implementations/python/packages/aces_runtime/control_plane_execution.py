"""Execution helpers for the runtime control plane."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from aces_contracts.planning import RuntimeDomain
from aces_contracts.runtime_state import OperationReceipt, OperationState, OperationStatus, RuntimeSnapshot

from .backend_calls import _call_backend_apply
from .control_plane_store import ControlPlaneOperationRecord


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def execute_participant_action(
    control_plane,
    *,
    method,
    request,
    address: str,
    idempotency_key: str,
    request_fingerprint: str,
) -> OperationReceipt:
    existing = control_plane._idempotent_receipt(
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    if existing is not None:
        return existing
    operation_id = str(uuid4())
    submitted_at = _utc_now()
    status = OperationStatus(
        operation_id=operation_id,
        domain=RuntimeDomain.PARTICIPANT,
        state=OperationState.RUNNING,
        submitted_at=submitted_at,
        updated_at=submitted_at,
    )
    receipt = OperationReceipt(
        operation_id=operation_id,
        domain=RuntimeDomain.PARTICIPANT,
        submitted_at=submitted_at,
        accepted=True,
    )
    control_plane._persist_record(
        ControlPlaneOperationRecord(
            receipt=receipt,
            status=status,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
    )
    result = _call_backend_apply(
        method,
        request,
        control_plane._snapshot,
        address=address,
        snapshot=control_plane._snapshot,
    )
    control_plane._snapshot = result.snapshot
    control_plane._store.save_snapshot(control_plane._snapshot)
    final_state = OperationState.SUCCEEDED if result.success else OperationState.FAILED
    final_status = OperationStatus(
        operation_id=operation_id,
        domain=RuntimeDomain.PARTICIPANT,
        state=final_state,
        submitted_at=submitted_at,
        updated_at=_utc_now(),
        diagnostics=[*status.diagnostics, *result.diagnostics],
        changed_addresses=list(result.changed_addresses),
    )
    control_plane._persist_record(
        ControlPlaneOperationRecord(
            receipt=receipt,
            status=final_status,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
    )
    return receipt


def execute_operation(
    control_plane,
    *,
    domain: RuntimeDomain,
    method,
    plan,
    address: str,
    diagnostics,
    base_snapshot: RuntimeSnapshot | None,
    idempotency_key: str,
    request_fingerprint: str,
) -> OperationReceipt:
    existing = control_plane._idempotent_receipt(
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    if existing is not None:
        return existing
    operation_id = str(uuid4())
    submitted_at = _utc_now()
    snapshot = base_snapshot if base_snapshot is not None else control_plane._snapshot
    status = OperationStatus(
        operation_id=operation_id,
        domain=domain,
        state=OperationState.RUNNING,
        submitted_at=submitted_at,
        updated_at=submitted_at,
        diagnostics=list(diagnostics),
    )
    receipt = OperationReceipt(
        operation_id=operation_id,
        domain=domain,
        submitted_at=submitted_at,
        accepted=True,
        diagnostics=list(diagnostics),
    )
    control_plane._persist_record(
        ControlPlaneOperationRecord(
            receipt=receipt,
            status=status,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
    )
    result = _call_backend_apply(
        method,
        plan,
        snapshot,
        address=address,
        snapshot=snapshot,
    )
    control_plane._snapshot = result.snapshot
    control_plane._store.save_snapshot(control_plane._snapshot)
    final_state = OperationState.SUCCEEDED if result.success else OperationState.FAILED
    final_status = OperationStatus(
        operation_id=operation_id,
        domain=domain,
        state=final_state,
        submitted_at=submitted_at,
        updated_at=_utc_now(),
        diagnostics=[*status.diagnostics, *result.diagnostics],
        changed_addresses=list(result.changed_addresses),
    )
    control_plane._persist_record(
        ControlPlaneOperationRecord(
            receipt=receipt,
            status=final_status,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
    )
    return receipt
