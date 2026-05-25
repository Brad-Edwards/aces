"""Shared runtime state and control-plane result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.planning import RuntimeDomain
from aces_contracts.versions import OPERATION_SCHEMA_VERSION, RUNTIME_SNAPSHOT_SCHEMA_VERSION


class OperationState(str, Enum):
    """Lifecycle for async control-plane operations."""

    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class SnapshotEntry:
    """Recorded runtime state for a single canonical resource."""

    address: str
    domain: RuntimeDomain
    resource_type: str
    payload: dict[str, Any]
    ordering_dependencies: tuple[str, ...] = ()
    refresh_dependencies: tuple[str, ...] = ()
    status: str = "ready"


@dataclass
class RuntimeSnapshot:
    """Current runtime snapshot."""

    entries: dict[str, SnapshotEntry] = field(default_factory=dict)
    orchestration_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    orchestration_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    evaluation_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    evaluation_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    participant_episode_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    participant_episode_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    participant_behavior_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get(self, address: str) -> SnapshotEntry | None:
        return self.entries.get(address)

    def for_domain(self, domain: RuntimeDomain) -> dict[str, SnapshotEntry]:
        return {address: entry for address, entry in self.entries.items() if entry.domain == domain}

    def with_entries(
        self,
        entries: dict[str, SnapshotEntry],
        *,
        orchestration_results: dict[str, dict[str, Any]] | None = None,
        orchestration_history: dict[str, list[dict[str, Any]]] | None = None,
        evaluation_results: dict[str, dict[str, Any]] | None = None,
        evaluation_history: dict[str, list[dict[str, Any]]] | None = None,
        participant_episode_results: dict[str, dict[str, Any]] | None = None,
        participant_episode_history: dict[str, list[dict[str, Any]]] | None = None,
        participant_behavior_history: dict[str, list[dict[str, Any]]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            entries=entries,
            orchestration_results=(
                dict(self.orchestration_results) if orchestration_results is None else dict(orchestration_results)
            ),
            orchestration_history=(
                {workflow_address: list(events) for workflow_address, events in self.orchestration_history.items()}
                if orchestration_history is None
                else {workflow_address: list(events) for workflow_address, events in orchestration_history.items()}
            ),
            evaluation_results=(
                dict(self.evaluation_results) if evaluation_results is None else dict(evaluation_results)
            ),
            evaluation_history=(
                {address: list(events) for address, events in self.evaluation_history.items()}
                if evaluation_history is None
                else {address: list(events) for address, events in evaluation_history.items()}
            ),
            participant_episode_results=(
                dict(self.participant_episode_results)
                if participant_episode_results is None
                else dict(participant_episode_results)
            ),
            participant_episode_history=(
                {
                    participant_address: list(events)
                    for participant_address, events in self.participant_episode_history.items()
                }
                if participant_episode_history is None
                else {
                    participant_address: list(events)
                    for participant_address, events in participant_episode_history.items()
                }
            ),
            participant_behavior_history=(
                {
                    participant_address: list(events)
                    for participant_address, events in self.participant_behavior_history.items()
                }
                if participant_behavior_history is None
                else {
                    participant_address: list(events)
                    for participant_address, events in participant_behavior_history.items()
                }
            ),
            metadata=dict(self.metadata) if metadata is None else dict(metadata),
        )


@dataclass
class ApplyResult:
    """Result of applying or starting a runtime plan."""

    success: bool
    snapshot: RuntimeSnapshot
    diagnostics: list[Diagnostic] = field(default_factory=list)
    changed_addresses: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationReceipt:
    """Portable acknowledgment for an accepted control-plane operation."""

    schema_version: str = OPERATION_SCHEMA_VERSION
    operation_id: str = ""
    domain: RuntimeDomain = RuntimeDomain.PROVISIONING
    submitted_at: str = ""
    accepted: bool = True
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass(frozen=True)
class OperationStatus:
    """Portable status for a submitted control-plane operation."""

    schema_version: str = OPERATION_SCHEMA_VERSION
    operation_id: str = ""
    domain: RuntimeDomain = RuntimeDomain.PROVISIONING
    state: OperationState = OperationState.ACCEPTED
    submitted_at: str = ""
    updated_at: str = ""
    diagnostics: list[Diagnostic] = field(default_factory=list)
    changed_addresses: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RuntimeSnapshotEnvelope:
    """Portable envelope around the current runtime snapshot."""

    schema_version: str = RUNTIME_SNAPSHOT_SCHEMA_VERSION
    snapshot: RuntimeSnapshot = field(default_factory=RuntimeSnapshot)


__all__ = (
    "ApplyResult",
    "OperationReceipt",
    "OperationState",
    "OperationStatus",
    "RuntimeSnapshot",
    "RuntimeSnapshotEnvelope",
    "SnapshotEntry",
)
