"""Execution helpers for the runtime control plane."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.planning import RuntimeDomain
from aces_contracts.runtime_state import OperationReceipt, OperationState, OperationStatus, RuntimeSnapshot

from .backend_calls import _call_backend_apply
from .control_plane_store import ControlPlaneOperationRecord


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def execute_participant_action(
    control_plane: object,
    *,
    method: Callable[..., object],
    request: object,
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
    target_address = getattr(request, "participant_address", "")
    status = OperationStatus(
        operation_id=operation_id,
        domain=RuntimeDomain.PARTICIPANT,
        state=OperationState.RUNNING,
        submitted_at=submitted_at,
        updated_at=submitted_at,
        changed_addresses=[target_address] if isinstance(target_address, str) and target_address else [],
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


def persist_succeeded_operation(
    control_plane: object,
    request: SucceededOperationRequest,
) -> OperationReceipt:
    receipt = OperationReceipt(
        operation_id=request.operation_id,
        domain=request.domain,
        submitted_at=request.submitted_at,
        accepted=True,
        diagnostics=[],
    )
    status = OperationStatus(
        operation_id=request.operation_id,
        domain=request.domain,
        state=OperationState.SUCCEEDED,
        submitted_at=request.submitted_at,
        updated_at=request.submitted_at,
        changed_addresses=list(request.changed_addresses or []),
    )
    control_plane._persist_record(
        ControlPlaneOperationRecord(
            receipt=receipt,
            status=status,
            idempotency_key=request.idempotency_key,
            request_fingerprint=request.request_fingerprint,
        )
    )
    return receipt


@dataclass(frozen=True)
class SucceededOperationRequest:
    operation_id: str
    domain: RuntimeDomain
    submitted_at: str
    idempotency_key: str
    request_fingerprint: str
    changed_addresses: list[str] | None = None


@dataclass(frozen=True)
class OperationExecutionRequest:
    domain: RuntimeDomain
    method: Callable[..., object]
    plan: object
    address: str
    diagnostics: list[Diagnostic]
    base_snapshot: RuntimeSnapshot | None
    idempotency_key: str
    request_fingerprint: str


def execute_operation(
    control_plane: object,
    request: OperationExecutionRequest,
) -> OperationReceipt:
    existing = control_plane._idempotent_receipt(
        idempotency_key=request.idempotency_key,
        request_fingerprint=request.request_fingerprint,
    )
    if existing is not None:
        return existing
    operation_id = str(uuid4())
    submitted_at = _utc_now()
    snapshot = request.base_snapshot if request.base_snapshot is not None else control_plane._snapshot
    status = OperationStatus(
        operation_id=operation_id,
        domain=request.domain,
        state=OperationState.RUNNING,
        submitted_at=submitted_at,
        updated_at=submitted_at,
        diagnostics=list(request.diagnostics),
    )
    receipt = OperationReceipt(
        operation_id=operation_id,
        domain=request.domain,
        submitted_at=submitted_at,
        accepted=True,
        diagnostics=list(request.diagnostics),
    )
    control_plane._persist_record(
        ControlPlaneOperationRecord(
            receipt=receipt,
            status=status,
            idempotency_key=request.idempotency_key,
            request_fingerprint=request.request_fingerprint,
        )
    )
    result = _call_backend_apply(
        request.method,
        request.plan,
        snapshot,
        address=request.address,
        snapshot=snapshot,
    )
    control_plane._snapshot = result.snapshot
    control_plane._store.save_snapshot(control_plane._snapshot)
    final_state = OperationState.SUCCEEDED if result.success else OperationState.FAILED
    final_status = OperationStatus(
        operation_id=operation_id,
        domain=request.domain,
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
            idempotency_key=request.idempotency_key,
            request_fingerprint=request.request_fingerprint,
        )
    )
    return receipt
