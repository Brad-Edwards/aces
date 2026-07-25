"""Derived operational apparatus summaries for the runtime control plane."""

from __future__ import annotations

from typing import Any

from aces_contracts.planning import RuntimeDomain
from aces_contracts.runtime_state import OperationState, RuntimeSnapshot

from .control_plane_store import AuditEvent, ControlPlaneOperationRecord

_RECENT_OPERATION_LIMIT = 10
_RECENT_AUDIT_LIMIT = 10


def operational_apparatus_summary(
    *,
    target_name: str,
    snapshot: RuntimeSnapshot,
    operation_records: list[ControlPlaneOperationRecord],
    audit_events: list[AuditEvent],
) -> dict[str, object]:
    """Return a compact operational view over existing control-plane carriers."""

    return {
        "target": target_name,
        "resources": _resource_summary(snapshot),
        "runtime_surfaces": _runtime_surface_summary(snapshot),
        "operations": _operation_summary(operation_records),
        "audit": _audit_summary(audit_events),
    }


def _count_by_value(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _resource_summary(snapshot: RuntimeSnapshot) -> dict[str, object]:
    by_domain = {domain.value: 0 for domain in RuntimeDomain}
    statuses: list[str] = []
    resource_types: list[str] = []
    for entry in snapshot.entries.values():
        by_domain[entry.domain.value] = by_domain.get(entry.domain.value, 0) + 1
        statuses.append(entry.status)
        resource_types.append(entry.resource_type)
    return {
        "total": len(snapshot.entries),
        "by_domain": by_domain,
        "by_status": _count_by_value(statuses),
        "by_resource_type": _count_by_value(resource_types),
    }


def _history_count(events_by_address: dict[str, list[dict[str, Any]]]) -> int:
    return sum(len(events) for events in events_by_address.values())


def _runtime_surface_summary(snapshot: RuntimeSnapshot) -> dict[str, int]:
    return {
        "orchestration_results": len(snapshot.orchestration_results),
        "orchestration_history": _history_count(snapshot.orchestration_history),
        "evaluation_results": len(snapshot.evaluation_results),
        "proposition_truth_results": len(snapshot.proposition_truth_results),
        "evaluation_history": _history_count(snapshot.evaluation_history),
        "participant_episode_results": len(snapshot.participant_episode_results),
        "participant_episode_history": _history_count(snapshot.participant_episode_history),
        "participant_behavior_history": _history_count(snapshot.participant_behavior_history),
        "shared_state_records": len(snapshot.shared_state_records),
        "shared_state_history": _history_count(snapshot.shared_state_history),
        "joint_action_records": len(snapshot.joint_action_records),
        "time_management_contexts": len(snapshot.time_management_contexts),
        "time_model_clocks": len(snapshot.time_model_state.clocks) if snapshot.time_model_state is not None else 0,
        "realization_provenance": len(snapshot.realization_provenance),
    }


def _diagnostic_codes(record: ControlPlaneOperationRecord) -> list[str]:
    codes: list[str] = []
    for diagnostic in [*record.receipt.diagnostics, *record.status.diagnostics]:
        if diagnostic.code not in codes:
            codes.append(diagnostic.code)
    return codes


def _operation_record_summary(record: ControlPlaneOperationRecord) -> dict[str, object]:
    return {
        "operation_id": record.status.operation_id,
        "domain": record.status.domain.value,
        "state": record.status.state.value,
        "submitted_at": record.status.submitted_at,
        "updated_at": record.status.updated_at,
        "changed_addresses": list(record.status.changed_addresses),
        "diagnostic_count": len(record.receipt.diagnostics) + len(record.status.diagnostics),
        "diagnostic_codes": _diagnostic_codes(record),
    }


def _operation_summary(records: list[ControlPlaneOperationRecord]) -> dict[str, object]:
    by_state = {state.value: 0 for state in OperationState}
    for record in records:
        state = record.status.state.value
        by_state[state] = by_state.get(state, 0) + 1
    recent = [_operation_record_summary(record) for record in records[-_RECENT_OPERATION_LIMIT:]]
    return {
        "total": len(records),
        "by_state": by_state,
        "recent": recent,
    }


def _audit_event_summary(event: AuditEvent) -> dict[str, object]:
    return {
        "timestamp": event.timestamp,
        "action": event.action,
        "identity": event.identity,
        "allowed": event.allowed,
        "target": event.target,
        "operation_id": event.operation_id,
        "reason": event.reason,
    }


def _audit_summary(events: list[AuditEvent]) -> dict[str, object]:
    recent = [_audit_event_summary(event) for event in events[-_RECENT_AUDIT_LIMIT:]]
    allowed = sum(1 for event in events if event.allowed)
    return {
        "total": len(events),
        "allowed": allowed,
        "denied": len(events) - allowed,
        "recent": recent,
    }
