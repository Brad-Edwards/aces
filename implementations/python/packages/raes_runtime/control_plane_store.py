"""Durable storage for the per-target runtime control plane."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import TYPE_CHECKING, Any, Protocol

from raes_contracts.participant_autonomous_state import require_participant_autonomous_runtime_snapshot
from raes_contracts.runtime_state import (
    OperationReceipt,
    OperationState,
    OperationStatus,
    RuntimeSnapshot,
)

from .control_plane_store_snapshots import (
    _snapshot_from_payload as _snapshot_from_payload,
)
from .control_plane_store_snapshots import (
    _snapshot_payload as _snapshot_payload,
)

if TYPE_CHECKING:
    from .control_plane_store_local import LocalControlPlaneStore


class ParticipantCrossingHistoryPresence(str, Enum):
    """Source-level API-423 history presence before snapshot defaults apply."""

    ABSENT = "absent"
    PRESENT_EMPTY = "present-empty"
    PRESENT = "present"


def participant_crossing_history_presence(
    payload: dict[str, Any],
) -> ParticipantCrossingHistoryPresence:
    """Classify raw runtime-snapshot input without inventing historical meaning."""

    if "participant_crossing_history" not in payload:
        return ParticipantCrossingHistoryPresence.ABSENT
    history = payload["participant_crossing_history"]
    if not isinstance(history, dict):
        raise ValueError("participant_crossing_history must be an object")
    if not history:
        return ParticipantCrossingHistoryPresence.PRESENT_EMPTY
    return ParticipantCrossingHistoryPresence.PRESENT


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
    result_payload: dict[str, Any] | None = None
    decision_history_heads: dict[str, str | None] = field(default_factory=dict)
    result_history_heads: dict[str, str | None] = field(default_factory=dict)


INTERRUPTED_OPERATION_DIAGNOSTIC_CODE = "runtime.control-plane.operation-interrupted"
_NON_TERMINAL_OPERATION_STATES = {OperationState.ACCEPTED, OperationState.RUNNING}


def _require_operation_record_identity(record: ControlPlaneOperationRecord) -> None:
    if record.receipt.operation_id != record.status.operation_id:
        raise ValueError("operation receipt and status identities do not match")
    if record.receipt.domain != record.status.domain:
        raise ValueError("operation receipt and status domains do not match")
    if record.receipt.submitted_at != record.status.submitted_at:
        raise ValueError("operation receipt and status submission times do not match")


def _require_same_operation_identity(
    existing: ControlPlaneOperationRecord,
    replacement: ControlPlaneOperationRecord,
) -> None:
    _require_operation_record_identity(existing)
    _require_operation_record_identity(replacement)
    if existing.receipt != replacement.receipt:
        raise ValueError("operation receipt is immutable after its durable claim")
    if (
        existing.status.schema_version,
        existing.status.operation_id,
        existing.status.domain,
        existing.status.submitted_at,
        existing.idempotency_key,
        existing.request_fingerprint,
    ) != (
        replacement.status.schema_version,
        replacement.status.operation_id,
        replacement.status.domain,
        replacement.status.submitted_at,
        replacement.idempotency_key,
        replacement.request_fingerprint,
    ):
        raise ValueError("operation identity is immutable after its durable claim")


def _require_terminal_operation_transition(
    existing: ControlPlaneOperationRecord | None,
    replacement: ControlPlaneOperationRecord,
) -> bool:
    """Validate a terminal transition and return whether it changes the record."""

    _require_operation_record_identity(replacement)
    if replacement.status.state in _NON_TERMINAL_OPERATION_STATES:
        raise ValueError("terminal operation commit requires a terminal status")
    if existing is None:
        return True
    _require_same_operation_identity(existing, replacement)
    if existing.status.state in _NON_TERMINAL_OPERATION_STATES:
        return True
    if existing != replacement:
        raise ValueError("a terminal operation record cannot be rewritten")
    return False


def _require_interrupted_operation_transition(
    existing: ControlPlaneOperationRecord | None,
    replacement: ControlPlaneOperationRecord,
) -> bool:
    """Validate conservative startup recovery for one interrupted operation."""

    if existing is None:
        raise ValueError("interrupted operation no longer exists in durable state")
    _require_same_operation_identity(existing, replacement)
    if replacement.status.state != OperationState.FAILED:
        raise ValueError("interrupted operation recovery must persist a failed status")
    if not any(
        diagnostic.code == INTERRUPTED_OPERATION_DIAGNOSTIC_CODE for diagnostic in replacement.status.diagnostics
    ):
        raise ValueError("interrupted operation recovery requires its stable diagnostic")
    if existing.status.state in _NON_TERMINAL_OPERATION_STATES:
        return True
    if existing != replacement:
        raise ValueError("a terminal operation record cannot be rewritten during recovery")
    return False


class ControlPlaneStore(Protocol):
    """Legacy-compatible durable persistence for control-plane state."""

    def load_snapshot(self) -> RuntimeSnapshot: ...

    def save_snapshot(self, snapshot: RuntimeSnapshot) -> None: ...

    def load_records(self) -> dict[str, ControlPlaneOperationRecord]: ...

    def save_record(self, record: ControlPlaneOperationRecord) -> None: ...

    def claim_record(self, record: ControlPlaneOperationRecord) -> ControlPlaneOperationRecord: ...

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

    def commit_participant_transition(
        self,
        *,
        expected_history_heads: dict[str, str | None],
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
        audit_event: AuditEvent,
    ) -> None: ...


class AtomicControlPlaneStore(ControlPlaneStore, Protocol):
    """Optional crash-atomic terminal commit and recovery capabilities."""

    def commit_terminal_operation(
        self,
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
    ) -> None: ...

    def reconcile_interrupted_records(
        self,
        records: tuple[ControlPlaneOperationRecord, ...],
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


def _participant_history_head(snapshot: RuntimeSnapshot, history_key: str) -> str | None:
    history_name, separator, participant_address = history_key.partition(":")
    histories = {
        "participant_episode_history": snapshot.participant_episode_history,
        "participant_behavior_history": snapshot.participant_behavior_history,
        "participant_control_history": snapshot.participant_control_history,
        "participant_crossing_history": snapshot.participant_crossing_history,
        "information_state_history": snapshot.information_state_history,
    }
    history = histories.get(history_name)
    if not separator or not participant_address or history is None:
        raise ValueError("participant transition history key is not supported")
    events = history.get(participant_address, ())
    if not events:
        return None
    event_id = events[-1].get("event_id")
    if isinstance(event_id, str) and event_id:
        return event_id
    encoded = json.dumps(events[-1], sort_keys=True, separators=(",", ":"), default=str).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _require_expected_history_heads(
    snapshot: RuntimeSnapshot,
    expected_history_heads: dict[str, str | None],
) -> None:
    for history_key, expected_head in expected_history_heads.items():
        if _participant_history_head(snapshot, history_key) != expected_head:
            raise ValueError("expected participant history head does not match durable state")


class InMemoryControlPlaneStore:
    """Simple in-memory store."""

    def __init__(self, snapshot: RuntimeSnapshot | None = None) -> None:
        self._lock = RLock()
        self._snapshot = snapshot if snapshot is not None else RuntimeSnapshot()
        self._records: dict[str, ControlPlaneOperationRecord] = {}
        self._idempotency: dict[str, str] = {}
        self._audit: list[AuditEvent] = []

    def load_snapshot(self) -> RuntimeSnapshot:
        with self._lock:
            return self._snapshot

    def save_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        require_participant_autonomous_runtime_snapshot(snapshot)
        with self._lock:
            self._snapshot = snapshot

    def load_records(self) -> dict[str, ControlPlaneOperationRecord]:
        with self._lock:
            return dict(self._records)

    def save_record(self, record: ControlPlaneOperationRecord) -> None:
        with self._lock:
            self._save_record(record)

    def claim_record(self, record: ControlPlaneOperationRecord) -> ControlPlaneOperationRecord:
        with self._lock:
            if record.idempotency_key:
                existing = self.find_by_idempotency(record.idempotency_key)
                if existing is not None:
                    return existing
            self._save_record(record)
            return record

    def commit_terminal_operation(
        self,
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
    ) -> None:
        """Atomically publish a snapshot with its terminal operation record."""

        require_participant_autonomous_runtime_snapshot(snapshot)
        with self._lock:
            existing = self._records.get(record.receipt.operation_id)
            changed = _require_terminal_operation_transition(existing, record)
            if not changed:
                if self._snapshot != snapshot:
                    raise ValueError("terminal operation retry does not match the durable snapshot")
                return
            records = {**self._records, record.receipt.operation_id: record}
            idempotency = dict(self._idempotency)
            if record.idempotency_key:
                existing_operation_id = idempotency.get(record.idempotency_key)
                if existing_operation_id is not None and existing_operation_id != record.receipt.operation_id:
                    raise ValueError("idempotency key already belongs to another operation")
                idempotency[record.idempotency_key] = record.receipt.operation_id
            self._snapshot = snapshot
            self._records = records
            self._idempotency = idempotency

    def reconcile_interrupted_records(
        self,
        records: tuple[ControlPlaneOperationRecord, ...],
    ) -> None:
        """Atomically replace orphaned non-terminal records during startup."""

        with self._lock:
            staged = dict(self._records)
            for record in records:
                existing = staged.get(record.receipt.operation_id)
                if _require_interrupted_operation_transition(existing, record):
                    staged[record.receipt.operation_id] = record
            self._records = staged

    def find_by_idempotency(
        self,
        key: str,
    ) -> ControlPlaneOperationRecord | None:
        with self._lock:
            operation_id = self._idempotency.get(key)
            if operation_id is None:
                return None
            return self._records.get(operation_id)

    def append_audit(self, event: AuditEvent) -> None:
        with self._lock:
            self._audit.append(event)

    def read_audit(self) -> list[AuditEvent]:
        with self._lock:
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
        with self._lock:
            _require_expected_control_head(self._snapshot, participant_address, expected_head)
            self.commit_participant_transition(
                expected_history_heads={
                    f"participant_control_history:{participant_address}": expected_head,
                },
                snapshot=snapshot,
                record=record,
                audit_event=audit_event,
            )

    def commit_participant_transition(
        self,
        *,
        expected_history_heads: dict[str, str | None],
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
        audit_event: AuditEvent,
    ) -> None:
        with self._lock:
            _require_expected_history_heads(self._snapshot, expected_history_heads)
            require_participant_autonomous_runtime_snapshot(snapshot)
            records = {**self._records, record.receipt.operation_id: record}
            idempotency = dict(self._idempotency)
            if record.idempotency_key:
                existing_operation_id = idempotency.get(record.idempotency_key)
                if existing_operation_id is not None and existing_operation_id != record.receipt.operation_id:
                    raise ValueError("idempotency key already belongs to another operation")
                idempotency[record.idempotency_key] = record.receipt.operation_id
            self._snapshot = snapshot
            self._records = records
            self._idempotency = idempotency
            self._audit = [*self._audit, audit_event]

    def _save_record(self, record: ControlPlaneOperationRecord) -> None:
        if record.idempotency_key:
            existing_operation_id = self._idempotency.get(record.idempotency_key)
            if existing_operation_id is not None and existing_operation_id != record.receipt.operation_id:
                raise ValueError("idempotency key already belongs to another operation")
            self._idempotency[record.idempotency_key] = record.receipt.operation_id
        self._records[record.receipt.operation_id] = record


def __getattr__(name: str) -> object:
    """Lazily expose the local store without creating an import cycle."""

    if name == "LocalControlPlaneStore":
        from .control_plane_store_local import LocalControlPlaneStore

        return LocalControlPlaneStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = (
    "AtomicControlPlaneStore",
    "AuditEvent",
    "ControlPlaneOperationRecord",
    "ControlPlaneStore",
    "INTERRUPTED_OPERATION_DIAGNOSTIC_CODE",
    "InMemoryControlPlaneStore",
    "LocalControlPlaneStore",
    "ParticipantCrossingHistoryPresence",
    "participant_crossing_history_presence",
)
