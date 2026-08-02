"""Filesystem-backed runtime control-plane persistence."""

from __future__ import annotations

import json
import tempfile
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path
from typing import Any

from raes_contracts.participant_autonomous_state import require_participant_autonomous_runtime_snapshot
from raes_contracts.runtime_state import RuntimeSnapshot

from .control_plane_store import (
    AuditEvent,
    ControlPlaneOperationRecord,
    _require_expected_control_head,
    _require_expected_history_heads,
    _snapshot_from_payload,
    _snapshot_payload,
    os,
)
from .control_plane_store_records import (
    _audit_event_from_payload,
    _record_from_payload,
    _record_payload,
)


class LocalControlPlaneStore:
    """Filesystem-backed control-plane durability."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_path = self._base_dir / "snapshot.json"
        self._operations_path = self._base_dir / "operations.json"
        self._audit_path = self._base_dir / "audit.jsonl"
        self._control_state_path = self._base_dir / "control-transition-state.json"

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Write content atomically via a temporary file and os.replace."""

        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.replace(tmp, path)
        except BaseException:
            with suppress(OSError):
                os.unlink(tmp)
            raise

    def load_snapshot(self) -> RuntimeSnapshot:
        legacy_snapshot = RuntimeSnapshot()
        if self._snapshot_path.exists():
            payload = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
            legacy_snapshot = _snapshot_from_payload(payload)
        control_state = self._load_control_state()
        if control_state is None:
            return legacy_snapshot
        committed_snapshot = _snapshot_from_payload(dict(control_state.get("snapshot", {})))
        legacy_count = _participant_transition_count(legacy_snapshot)
        committed_count = _participant_transition_count(committed_snapshot)
        return committed_snapshot if committed_count > legacy_count else legacy_snapshot

    def save_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        content = json.dumps(_snapshot_payload(snapshot), indent=2, sort_keys=True) + "\n"
        self._atomic_write(self._snapshot_path, content)

    def load_records(self) -> dict[str, ControlPlaneOperationRecord]:
        records: dict[str, ControlPlaneOperationRecord] = {}
        control_state = self._load_control_state()
        if control_state is not None:
            records.update(
                {
                    operation_id: _record_from_payload(record_payload)
                    for operation_id, record_payload in dict(control_state.get("records", {})).items()
                    if isinstance(record_payload, dict)
                }
            )
        if not self._operations_path.exists():
            return records
        payload = json.loads(self._operations_path.read_text(encoding="utf-8"))
        records.update(
            {
                operation_id: _record_from_payload(record_payload)
                for operation_id, record_payload in payload.items()
                if isinstance(record_payload, dict)
            }
        )
        return records

    def save_record(self, record: ControlPlaneOperationRecord) -> None:
        records = self.load_records()
        records[record.receipt.operation_id] = record
        payload = {
            operation_id: _record_payload(operation_record) for operation_id, operation_record in records.items()
        }
        content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        self._atomic_write(self._operations_path, content)

    def find_by_idempotency(
        self,
        key: str,
    ) -> ControlPlaneOperationRecord | None:
        for record in self.load_records().values():
            if record.idempotency_key == key:
                return record
        return None

    def append_audit(self, event: AuditEvent) -> None:
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self._audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")

    def read_audit(self) -> list[AuditEvent]:
        events: list[AuditEvent] = []
        control_state = self._load_control_state()
        if control_state is not None:
            events.extend(
                _audit_event_from_payload(payload)
                for payload in control_state.get("audit", [])
                if isinstance(payload, dict)
            )
        if not self._audit_path.exists():
            return events
        for line in self._audit_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = _audit_event_from_payload(json.loads(line))
            if event not in events:
                events.append(event)
        return events

    def _load_control_state(self) -> dict[str, Any] | None:
        if not self._control_state_path.exists():
            return None
        payload = json.loads(self._control_state_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None

    def commit_control_transition(
        self,
        *,
        participant_address: str,
        expected_head: str | None,
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
        audit_event: AuditEvent,
    ) -> None:
        current_snapshot = self.load_snapshot()
        _require_expected_control_head(current_snapshot, participant_address, expected_head)
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
        current_snapshot = self.load_snapshot()
        _require_expected_history_heads(current_snapshot, expected_history_heads)
        require_participant_autonomous_runtime_snapshot(snapshot)
        records = self.load_records()
        records[record.receipt.operation_id] = record
        audits = [*self.read_audit(), audit_event]
        payload = {
            "snapshot": _snapshot_payload(snapshot),
            "records": {
                operation_id: _record_payload(operation_record) for operation_id, operation_record in records.items()
            },
            "audit": [asdict(event) for event in audits],
        }
        content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        self._atomic_write(self._control_state_path, content)


def _participant_transition_count(snapshot: RuntimeSnapshot) -> int:
    return sum(
        len(events)
        for history in (
            snapshot.participant_control_history,
            snapshot.participant_crossing_history,
            snapshot.information_state_history,
        )
        for events in history.values()
    )


__all__ = ("LocalControlPlaneStore",)
