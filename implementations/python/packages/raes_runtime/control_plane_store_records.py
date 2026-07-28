"""Operation-record and audit serialization for control-plane stores."""

from __future__ import annotations

from typing import Any

from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import RuntimeDomain
from raes_contracts.runtime_state import OperationReceipt, OperationState, OperationStatus

from .control_plane_store import AuditEvent, ControlPlaneOperationRecord


def _diagnostics_payload(diagnostics: list[Diagnostic]) -> list[dict[str, Any]]:
    return [
        {
            "code": diagnostic.code,
            "domain": diagnostic.domain,
            "address": diagnostic.address,
            "message": diagnostic.message,
            "severity": diagnostic.severity.value,
        }
        for diagnostic in diagnostics
    ]


def _diagnostics_from_payload(payload: list[dict[str, Any]]) -> list[Diagnostic]:
    return [
        Diagnostic(
            code=str(item.get("code", "runtime.control-plane")),
            domain=str(item.get("domain", "runtime")),
            address=str(item.get("address", "runtime.control-plane")),
            message=str(item.get("message", "")),
            severity=Severity(str(item.get("severity", "error"))),
        )
        for item in payload
    ]


def _record_payload(record: ControlPlaneOperationRecord) -> dict[str, Any]:
    return {
        "receipt": {
            "schema_version": record.receipt.schema_version,
            "operation_id": record.receipt.operation_id,
            "domain": record.receipt.domain.value,
            "submitted_at": record.receipt.submitted_at,
            "accepted": record.receipt.accepted,
            "diagnostics": _diagnostics_payload(record.receipt.diagnostics),
        },
        "status": {
            "schema_version": record.status.schema_version,
            "operation_id": record.status.operation_id,
            "domain": record.status.domain.value,
            "state": record.status.state.value,
            "submitted_at": record.status.submitted_at,
            "updated_at": record.status.updated_at,
            "diagnostics": _diagnostics_payload(record.status.diagnostics),
            "changed_addresses": list(record.status.changed_addresses),
        },
        "request_fingerprint": record.request_fingerprint,
        "idempotency_key": record.idempotency_key,
        "result_payload": record.result_payload,
        "decision_history_heads": dict(record.decision_history_heads),
        "result_history_heads": dict(record.result_history_heads),
    }


def _record_from_payload(payload: dict[str, Any]) -> ControlPlaneOperationRecord:
    receipt_payload = dict(payload.get("receipt", {}))
    status_payload = dict(payload.get("status", {}))
    receipt = OperationReceipt(
        schema_version=str(receipt_payload.get("schema_version", "runtime-operation/v1")),
        operation_id=str(receipt_payload.get("operation_id", "")),
        domain=RuntimeDomain(str(receipt_payload.get("domain", "provisioning"))),
        submitted_at=str(receipt_payload.get("submitted_at", "")),
        accepted=bool(receipt_payload.get("accepted", False)),
        diagnostics=_diagnostics_from_payload(list(receipt_payload.get("diagnostics", []))),
    )
    status = OperationStatus(
        schema_version=str(status_payload.get("schema_version", "runtime-operation/v1")),
        operation_id=str(status_payload.get("operation_id", "")),
        domain=RuntimeDomain(str(status_payload.get("domain", "provisioning"))),
        state=OperationState(str(status_payload.get("state", "accepted"))),
        submitted_at=str(status_payload.get("submitted_at", "")),
        updated_at=str(status_payload.get("updated_at", "")),
        diagnostics=_diagnostics_from_payload(list(status_payload.get("diagnostics", []))),
        changed_addresses=list(status_payload.get("changed_addresses", [])),
    )
    return ControlPlaneOperationRecord(
        receipt=receipt,
        status=status,
        request_fingerprint=str(payload.get("request_fingerprint", "")),
        idempotency_key=str(payload.get("idempotency_key", "")),
        result_payload=(dict(payload["result_payload"]) if isinstance(payload.get("result_payload"), dict) else None),
        decision_history_heads={
            str(key): (str(value) if value is not None else None)
            for key, value in dict(payload.get("decision_history_heads", {})).items()
        },
        result_history_heads={
            str(key): (str(value) if value is not None else None)
            for key, value in dict(payload.get("result_history_heads", {})).items()
        },
    )


def _audit_event_from_payload(payload: dict[str, Any]) -> AuditEvent:
    return AuditEvent(
        timestamp=str(payload.get("timestamp", "")),
        action=str(payload.get("action", "")),
        identity=str(payload.get("identity", "")),
        allowed=bool(payload.get("allowed", False)),
        target=str(payload.get("target", "")),
        operation_id=str(payload.get("operation_id", "")),
        reason=str(payload.get("reason", "")),
        details=dict(payload.get("details", {})),
    )


__all__ = ("_audit_event_from_payload", "_record_from_payload", "_record_payload")
