"""Shared runtime state and control-plane result contracts."""

from __future__ import annotations

from collections.abc import Mapping
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
        **updates: object,
    ) -> RuntimeSnapshot:
        _validate_snapshot_update_keys(updates)
        return RuntimeSnapshot(
            entries=entries,
            orchestration_results=_mapping_update(
                updates,
                "orchestration_results",
                self.orchestration_results,
            ),
            orchestration_history=_history_update(
                updates,
                "orchestration_history",
                self.orchestration_history,
            ),
            evaluation_results=_mapping_update(updates, "evaluation_results", self.evaluation_results),
            evaluation_history=_history_update(updates, "evaluation_history", self.evaluation_history),
            participant_episode_results=_mapping_update(
                updates,
                "participant_episode_results",
                self.participant_episode_results,
            ),
            participant_episode_history=_history_update(
                updates,
                "participant_episode_history",
                self.participant_episode_history,
            ),
            participant_behavior_history=_history_update(
                updates,
                "participant_behavior_history",
                self.participant_behavior_history,
            ),
            metadata=_mapping_update(updates, "metadata", self.metadata),
        )


_SNAPSHOT_UPDATE_KEYS = {
    "orchestration_results",
    "orchestration_history",
    "evaluation_results",
    "evaluation_history",
    "participant_episode_results",
    "participant_episode_history",
    "participant_behavior_history",
    "metadata",
}


def _validate_snapshot_update_keys(updates: Mapping[str, object]) -> None:
    unknown = sorted(key for key in updates if key not in _SNAPSHOT_UPDATE_KEYS)
    if unknown:
        raise TypeError("unknown runtime snapshot update fields: " + ", ".join(unknown))


def _mapping_update(
    updates: Mapping[str, object],
    key: str,
    current: Mapping[str, Any],
) -> dict[str, Any]:
    raw = updates.get(key)
    if raw is None:
        return dict(current)
    if not isinstance(raw, Mapping):
        raise TypeError(f"{key} must be a mapping")
    return dict(raw)


def _history_update(
    updates: Mapping[str, object],
    key: str,
    current: Mapping[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    raw = updates.get(key)
    if raw is None:
        return {address: list(events) for address, events in current.items()}
    if not isinstance(raw, Mapping):
        raise TypeError(f"{key} must be a mapping")
    return {str(address): list(events) for address, events in raw.items()}


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
