"""Durable storage for the per-target runtime control plane."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from raes_contracts.contracts import RealizationEnvelopeIdentityModel
from raes_contracts.contracts.time_model import TimeRuntimeStateModel
from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.participant_autonomous_state import require_participant_autonomous_runtime_snapshot
from raes_contracts.planning import RuntimeDomain
from raes_contracts.runtime_state import (
    ExplicitnessClass,
    ExplicitnessProvenance,
    OperationReceipt,
    OperationState,
    OperationStatus,
    RealizationProvenanceEntry,
    RuntimeSnapshot,
    RuntimeSnapshotEnvelope,
    SnapshotEntry,
)


@dataclass(frozen=True)
class AuditEvent:
    """Append-only security and control-plane audit event."""

    timestamp: str
    action: str
    identity: str
    allowed: bool
    target: str
    operation_id: str = ""
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ControlPlaneOperationRecord:
    """Persisted receipt/status pair for one operation."""

    receipt: OperationReceipt
    status: OperationStatus
    request_fingerprint: str = ""
    idempotency_key: str = ""


class ControlPlaneStore(Protocol):
    """Durable persistence for control-plane state."""

    def load_snapshot(self) -> RuntimeSnapshot: ...

    def save_snapshot(self, snapshot: RuntimeSnapshot) -> None: ...

    def load_records(self) -> dict[str, ControlPlaneOperationRecord]: ...

    def save_record(self, record: ControlPlaneOperationRecord) -> None: ...

    def find_by_idempotency(
        self,
        key: str,
    ) -> ControlPlaneOperationRecord | None: ...

    def append_audit(self, event: AuditEvent) -> None: ...

    def read_audit(self) -> list[AuditEvent]: ...

    def commit_control_transition(
        self,
        *,
        participant_address: str,
        expected_head: str | None,
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
        audit_event: AuditEvent,
    ) -> None: ...


def _control_history_head(snapshot: RuntimeSnapshot, participant_address: str) -> str | None:
    events = snapshot.participant_control_history.get(participant_address, ())
    if not events:
        return None
    event_id = events[-1].get("event_id")
    return event_id if isinstance(event_id, str) and event_id else None


def _require_expected_control_head(
    snapshot: RuntimeSnapshot,
    participant_address: str,
    expected_head: str | None,
) -> None:
    if _control_history_head(snapshot, participant_address) != expected_head:
        raise ValueError("expected control history head does not match durable state")


def _snapshot_payload(snapshot: RuntimeSnapshot) -> dict[str, Any]:
    require_participant_autonomous_runtime_snapshot(snapshot)
    return {
        "schema_version": RuntimeSnapshotEnvelope().schema_version,
        "entries": {
            address: {
                "address": entry.address,
                "domain": entry.domain.value,
                "resource_type": entry.resource_type,
                "payload": dict(entry.payload),
                "ordering_dependencies": list(entry.ordering_dependencies),
                "refresh_dependencies": list(entry.refresh_dependencies),
                "status": entry.status,
            }
            for address, entry in snapshot.entries.items()
        },
        "orchestration_results": dict(snapshot.orchestration_results),
        "orchestration_history": {address: list(events) for address, events in snapshot.orchestration_history.items()},
        "evaluation_results": dict(snapshot.evaluation_results),
        "evaluation_history": {address: list(events) for address, events in snapshot.evaluation_history.items()},
        "proposition_truth_results": dict(snapshot.proposition_truth_results),
        "participant_episode_results": dict(snapshot.participant_episode_results),
        "participant_episode_history": {
            participant_address: list(events)
            for participant_address, events in snapshot.participant_episode_history.items()
        },
        "participant_behavior_history": {
            participant_address: list(events)
            for participant_address, events in snapshot.participant_behavior_history.items()
        },
        "participant_control_history": {
            participant_address: list(events)
            for participant_address, events in snapshot.participant_control_history.items()
        },
        "participant_autonomous_execution_states": dict(snapshot.participant_autonomous_execution_states),
        "shared_state_records": dict(snapshot.shared_state_records),
        "shared_state_history": {
            state_address: list(records) for state_address, records in snapshot.shared_state_history.items()
        },
        "joint_action_records": dict(snapshot.joint_action_records),
        "time_management_contexts": dict(snapshot.time_management_contexts),
        "time_model_state": (
            snapshot.time_model_state.model_dump(mode="json") if snapshot.time_model_state is not None else None
        ),
        "realization_provenance": [
            {
                "address": entry.address,
                "field_path": entry.field_path,
                "domain": entry.domain,
                "requirement_kind": entry.requirement_kind,
                "explicitness": entry.explicitness.value,
                "provenance": entry.provenance.value,
                "governing_scope": entry.governing_scope,
            }
            for entry in snapshot.realization_provenance
        ],
        "realization_envelope": (
            snapshot.realization_envelope.model_dump(mode="json") if snapshot.realization_envelope is not None else None
        ),
        "metadata": dict(snapshot.metadata),
    }


def _snapshot_from_payload(payload: dict[str, Any]) -> RuntimeSnapshot:
    entries_payload = payload.get("entries", {})
    entries = {
        address: SnapshotEntry(
            address=str(entry.get("address", address)),
            domain=RuntimeDomain(str(entry.get("domain", "provisioning"))),
            resource_type=str(entry.get("resource_type", "")),
            payload=dict(entry.get("payload", {})),
            ordering_dependencies=tuple(entry.get("ordering_dependencies", ())),
            refresh_dependencies=tuple(entry.get("refresh_dependencies", ())),
            status=str(entry.get("status", "ready")),
        )
        for address, entry in entries_payload.items()
        if isinstance(entry, dict)
    }
    snapshot = RuntimeSnapshot(
        entries=entries,
        orchestration_results=dict(payload.get("orchestration_results", {})),
        orchestration_history={
            address: list(events) for address, events in payload.get("orchestration_history", {}).items()
        },
        evaluation_results=dict(payload.get("evaluation_results", {})),
        evaluation_history={address: list(events) for address, events in payload.get("evaluation_history", {}).items()},
        proposition_truth_results=dict(payload.get("proposition_truth_results", {})),
        participant_episode_results=dict(payload.get("participant_episode_results", {})),
        participant_episode_history={
            participant_address: list(events)
            for participant_address, events in payload.get("participant_episode_history", {}).items()
        },
        participant_behavior_history={
            participant_address: list(events)
            for participant_address, events in payload.get("participant_behavior_history", {}).items()
        },
        participant_control_history={
            participant_address: list(events)
            for participant_address, events in payload.get("participant_control_history", {}).items()
        },
        participant_autonomous_execution_states=dict(payload.get("participant_autonomous_execution_states", {})),
        shared_state_records=dict(payload.get("shared_state_records", {})),
        shared_state_history={
            state_address: list(records) for state_address, records in payload.get("shared_state_history", {}).items()
        },
        joint_action_records=dict(payload.get("joint_action_records", {})),
        time_management_contexts=dict(payload.get("time_management_contexts", {})),
        time_model_state=(
            TimeRuntimeStateModel.model_validate(payload["time_model_state"])
            if payload.get("time_model_state") is not None
            else None
        ),
        realization_provenance=tuple(
            RealizationProvenanceEntry(
                address=str(item.get("address", "")),
                field_path=str(item.get("field_path", "")),
                domain=str(item.get("domain", "")),
                requirement_kind=str(item.get("requirement_kind", "")),
                explicitness=ExplicitnessClass(str(item.get("explicitness", ExplicitnessClass.EXACT.value))),
                provenance=ExplicitnessProvenance(
                    str(item.get("provenance", ExplicitnessProvenance.AUTHOR_DECLARED.value))
                ),
                governing_scope=(str(item["governing_scope"]) if item.get("governing_scope") is not None else None),
            )
            for item in payload.get("realization_provenance", [])
            if isinstance(item, dict)
        ),
        realization_envelope=(
            RealizationEnvelopeIdentityModel.model_validate(payload["realization_envelope"])
            if payload.get("realization_envelope") is not None
            else None
        ),
        metadata=dict(payload.get("metadata", {})),
    )
    require_participant_autonomous_runtime_snapshot(snapshot)
    return snapshot


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


class InMemoryControlPlaneStore:
    """Simple in-memory store."""

    def __init__(self, snapshot: RuntimeSnapshot | None = None) -> None:
        self._snapshot = snapshot if snapshot is not None else RuntimeSnapshot()
        self._records: dict[str, ControlPlaneOperationRecord] = {}
        self._idempotency: dict[str, str] = {}
        self._audit: list[AuditEvent] = []

    def load_snapshot(self) -> RuntimeSnapshot:
        return self._snapshot

    def save_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        require_participant_autonomous_runtime_snapshot(snapshot)
        self._snapshot = snapshot

    def load_records(self) -> dict[str, ControlPlaneOperationRecord]:
        return dict(self._records)

    def save_record(self, record: ControlPlaneOperationRecord) -> None:
        self._records[record.receipt.operation_id] = record
        if record.idempotency_key:
            self._idempotency[record.idempotency_key] = record.receipt.operation_id

    def find_by_idempotency(
        self,
        key: str,
    ) -> ControlPlaneOperationRecord | None:
        operation_id = self._idempotency.get(key)
        if operation_id is None:
            return None
        return self._records.get(operation_id)

    def append_audit(self, event: AuditEvent) -> None:
        self._audit.append(event)

    def read_audit(self) -> list[AuditEvent]:
        return list(self._audit)

    def commit_control_transition(
        self,
        *,
        participant_address: str,
        expected_head: str | None,
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
        audit_event: AuditEvent,
    ) -> None:
        _require_expected_control_head(self._snapshot, participant_address, expected_head)
        require_participant_autonomous_runtime_snapshot(snapshot)
        records = {**self._records, record.receipt.operation_id: record}
        idempotency = dict(self._idempotency)
        if record.idempotency_key:
            idempotency[record.idempotency_key] = record.receipt.operation_id
        self._snapshot = snapshot
        self._records = records
        self._idempotency = idempotency
        self._audit = [*self._audit, audit_event]


from .control_plane_store_local import LocalControlPlaneStore  # noqa: E402

__all__ = (
    "AuditEvent",
    "ControlPlaneOperationRecord",
    "ControlPlaneStore",
    "InMemoryControlPlaneStore",
    "LocalControlPlaneStore",
    "os",
)
