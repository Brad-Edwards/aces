"""Durable storage for the per-target runtime control plane."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

from raes_contracts.account_credentials import (
    account_placement_has_credential_bindings,
    value_free_account_placement_payload,
)
from raes_contracts.artifact_requirements import ArtifactSatisfactionDisclosureModel
from raes_contracts.contracts import RealizationEnvelopeIdentityModel, RealizationObservationDisclosureModel
from raes_contracts.contracts.time_model import TimeRuntimeStateModel
from raes_contracts.participant_autonomous_state import require_participant_autonomous_runtime_snapshot
from raes_contracts.planning import RuntimeDomain
from raes_contracts.runtime_state import (
    ExplicitnessClass,
    ExplicitnessProvenance,
    OperationReceipt,
    OperationStatus,
    RealizationObservationDisclosure,
    RealizationProvenanceEntry,
    RuntimeSnapshot,
    RuntimeSnapshotEnvelope,
    SnapshotEntry,
)
from raes_contracts.vocabulary import ObservationStrength, RealizationVerificationScope

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

    def commit_participant_transition(
        self,
        *,
        expected_history_heads: dict[str, str | None],
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


def _snapshot_payload(snapshot: RuntimeSnapshot) -> dict[str, Any]:
    require_participant_autonomous_runtime_snapshot(snapshot)
    payload = {
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
        "participant_crossing_history": {
            participant_address: list(events)
            for participant_address, events in snapshot.participant_crossing_history.items()
        },
        "information_state_history": {
            participant_address: list(records)
            for participant_address, records in snapshot.information_state_history.items()
        },
        "participant_autonomous_execution_states": dict(snapshot.participant_autonomous_execution_states),
        "participant_execution_services": dict(snapshot.participant_execution_services),
        "participant_resource_budget_states": dict(snapshot.participant_resource_budget_states),
        "participant_resource_pool_states": dict(snapshot.participant_resource_pool_states),
        "participant_resource_budget_events": dict(snapshot.participant_resource_budget_events),
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
                "artifact_satisfaction": (
                    entry.artifact_satisfaction.model_dump(mode="json")
                    if entry.artifact_satisfaction is not None
                    else None
                ),
            }
            for entry in snapshot.realization_provenance
        ],
        "realization_observations": [
            {
                "address": entry.address,
                "field_path": entry.field_path,
                "domain": entry.domain,
                "requirement_kind": entry.requirement_kind,
                "verification_scope": entry.verification_scope.value,
                "observation_strength": entry.observation_strength.value,
                **(
                    {
                        "observed_value": entry.observed_value,
                        "operation_id": entry.operation_id,
                        "envelope_digest": entry.envelope_digest,
                        "configuration_digest": entry.configuration_digest,
                        "observer_version": entry.observer_version,
                        "sequence": entry.sequence,
                        "binding_verified": entry.binding_verified,
                    }
                    if entry.requirement_kind == "compute-substrate"
                    else {}
                ),
            }
            for entry in snapshot.realization_observations
        ],
        "realization_envelope": (
            snapshot.realization_envelope.model_dump(mode="json") if snapshot.realization_envelope is not None else None
        ),
        "metadata": dict(snapshot.metadata),
    }
    for entry in payload["entries"].values():
        if entry["resource_type"] != "account-placement":
            continue
        entry_payload = entry["payload"]
        if account_placement_has_credential_bindings(entry_payload):
            entry["payload"] = value_free_account_placement_payload(entry_payload)
    return payload


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
        participant_crossing_history={
            participant_address: list(events)
            for participant_address, events in payload.get("participant_crossing_history", {}).items()
        },
        information_state_history={
            participant_address: list(records)
            for participant_address, records in payload.get("information_state_history", {}).items()
        },
        participant_autonomous_execution_states=dict(payload.get("participant_autonomous_execution_states", {})),
        participant_execution_services=dict(payload.get("participant_execution_services", {})),
        participant_resource_budget_states=dict(payload.get("participant_resource_budget_states", {})),
        participant_resource_pool_states=dict(payload.get("participant_resource_pool_states", {})),
        participant_resource_budget_events=dict(payload.get("participant_resource_budget_events", {})),
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
                artifact_satisfaction=(
                    ArtifactSatisfactionDisclosureModel.model_validate(item["artifact_satisfaction"])
                    if item.get("artifact_satisfaction") is not None
                    else None
                ),
            )
            for item in payload.get("realization_provenance", [])
            if isinstance(item, dict)
        ),
        realization_observations=tuple(
            _realization_observation_from_payload(item)
            for item in payload.get("realization_observations", [])
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


def _realization_observation_from_payload(payload: dict[str, Any]) -> RealizationObservationDisclosure:
    model = RealizationObservationDisclosureModel.model_validate(payload)
    return RealizationObservationDisclosure(
        address=model.address,
        field_path=model.field_path,
        domain=model.domain,
        requirement_kind=model.requirement_kind,
        verification_scope=RealizationVerificationScope(model.verification_scope),
        observation_strength=ObservationStrength(model.observation_strength),
        observed_value=model.observed_value,
        operation_id=model.operation_id,
        envelope_digest=model.envelope_digest,
        configuration_digest=model.configuration_digest,
        observer_version=model.observer_version,
        sequence=model.sequence,
        binding_verified=model.binding_verified,
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
        _require_expected_history_heads(self._snapshot, expected_history_heads)
        require_participant_autonomous_runtime_snapshot(snapshot)
        records = {**self._records, record.receipt.operation_id: record}
        idempotency = dict(self._idempotency)
        if record.idempotency_key:
            idempotency[record.idempotency_key] = record.receipt.operation_id
        self._snapshot = snapshot
        self._records = records
        self._idempotency = idempotency
        self._audit = [*self._audit, audit_event]


def __getattr__(name: str) -> object:
    """Lazily expose the local store without creating an import cycle."""

    if name == "LocalControlPlaneStore":
        from .control_plane_store_local import LocalControlPlaneStore

        return LocalControlPlaneStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = (
    "AuditEvent",
    "ControlPlaneOperationRecord",
    "ControlPlaneStore",
    "InMemoryControlPlaneStore",
    "LocalControlPlaneStore",
    "ParticipantCrossingHistoryPresence",
    "os",
    "participant_crossing_history_presence",
)
