"""Legacy JSON import readers for the local control-plane store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from raes_contracts.runtime_state import RuntimeSnapshot

from .control_plane_store import AuditEvent, ControlPlaneOperationRecord
from .control_plane_store_paths import _participant_transition_count, _read_json_object
from .control_plane_store_records import _audit_event_from_payload, _record_from_payload
from .control_plane_store_snapshots import _snapshot_from_payload


def _read_legacy_state(
    *,
    snapshot_path: Path,
    operations_path: Path,
    audit_path: Path,
    control_state_path: Path,
) -> tuple[RuntimeSnapshot, dict[str, ControlPlaneOperationRecord], list[AuditEvent]]:
    control_state = _read_control_state(control_state_path)
    return (
        _read_snapshot(snapshot_path, control_state),
        _read_records(operations_path, control_state),
        _read_audits(audit_path, control_state),
    )


def _read_control_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json_object(path)


def _read_snapshot(path: Path, control_state: dict[str, Any]) -> RuntimeSnapshot:
    snapshot = RuntimeSnapshot()
    if path.exists():
        snapshot = _snapshot_from_payload(_read_json_object(path))
    if control_state:
        committed = _snapshot_from_payload(dict(control_state.get("snapshot", {})))
        if _participant_transition_count(committed) > _participant_transition_count(snapshot):
            snapshot = committed
    return snapshot


def _read_records(
    path: Path,
    control_state: dict[str, Any],
) -> dict[str, ControlPlaneOperationRecord]:
    records = {
        operation_id: _record_from_payload(payload)
        for operation_id, payload in dict(control_state.get("records", {})).items()
        if isinstance(payload, dict)
    }
    if path.exists():
        records.update(
            {
                operation_id: _record_from_payload(payload)
                for operation_id, payload in _read_json_object(path).items()
                if isinstance(payload, dict)
            }
        )
    return records


def _read_audits(path: Path, control_state: dict[str, Any]) -> list[AuditEvent]:
    audits = [
        _audit_event_from_payload(payload) for payload in control_state.get("audit", []) if isinstance(payload, dict)
    ]
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = _audit_event_from_payload(json.loads(line))
            if event not in audits:
                audits.append(event)
    return audits


__all__ = ("_read_legacy_state",)
