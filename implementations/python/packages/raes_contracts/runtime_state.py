"""Shared runtime state and control-plane result contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance

from raes_contracts.addressing import require_compiled_address
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_autonomous_state import require_participant_autonomous_state_snapshot
from raes_contracts.planning import RuntimeDomain
from raes_contracts.versions import OPERATION_SCHEMA_VERSION, RUNTIME_SNAPSHOT_SCHEMA_VERSION

if TYPE_CHECKING:
    from raes_contracts.artifact_requirements import ArtifactSatisfactionDisclosureModel
    from raes_contracts.contracts import RealizationEnvelopeIdentityModel
    from raes_contracts.contracts.time_model import TimeRuntimeStateModel


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

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        for dependency in (*self.ordering_dependencies, *self.refresh_dependencies):
            require_compiled_address(dependency, field_name="dependency address")


@dataclass(frozen=True)
class RealizationProvenanceEntry:
    """SEM-218 provenance for one realized realization concern (invariant I5).

    Records, for a single realization concern that entered a runtime snapshot /
    result / history surface, its SEM-218 explicitness class and the origin of
    the realized value: ``author-declared`` (honoured exactly as the author
    wrote it), ``processor-derived`` (produced by deterministic processor
    activity), or ``backend-realized`` (picked by the backend from an open or
    constrained surface admitted by I3). It carries field-path and kind
    references only — never the realized value itself, which may carry sensitive
    material (SEM-218 host-exposure gate).
    """

    address: str
    field_path: str
    domain: str
    requirement_kind: str
    explicitness: ExplicitnessClass
    provenance: ExplicitnessProvenance
    governing_scope: str | None = None
    artifact_satisfaction: ArtifactSatisfactionDisclosureModel | None = None


@dataclass
class RuntimeSnapshot:
    """Current runtime snapshot."""

    entries: dict[str, SnapshotEntry] = field(default_factory=dict)
    orchestration_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    orchestration_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    evaluation_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    evaluation_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    proposition_truth_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    participant_episode_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    participant_episode_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    participant_behavior_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    participant_control_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    participant_autonomous_execution_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    participant_execution_services: dict[str, dict[str, Any]] = field(default_factory=dict)
    participant_resource_budget_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    participant_resource_pool_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    participant_resource_budget_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    shared_state_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    shared_state_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    joint_action_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    time_management_contexts: dict[str, dict[str, Any]] = field(default_factory=dict)
    time_model_state: TimeRuntimeStateModel | None = None
    # SEM-218 invariant I5: per-concern provenance for realized realization
    # concerns recorded across this snapshot's result / history surfaces.
    realization_provenance: tuple[RealizationProvenanceEntry, ...] = ()
    realization_envelope: RealizationEnvelopeIdentityModel | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for map_key, entry in self.entries.items():
            require_compiled_address(map_key, field_name="snapshot map key")
            if map_key != entry.address:
                raise ValueError("RuntimeSnapshot entries map key must equal embedded address")
        require_participant_autonomous_state_snapshot(self.participant_autonomous_execution_states)
        _require_participant_resource_budget_snapshot(
            self.participant_resource_budget_states,
            self.participant_resource_pool_states,
            self.participant_resource_budget_events,
        )

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
            proposition_truth_results=_mapping_update(
                updates,
                "proposition_truth_results",
                self.proposition_truth_results,
            ),
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
            participant_control_history=_history_update(
                updates,
                "participant_control_history",
                self.participant_control_history,
            ),
            participant_autonomous_execution_states=_mapping_update(
                updates,
                "participant_autonomous_execution_states",
                self.participant_autonomous_execution_states,
            ),
            participant_execution_services=_mapping_update(
                updates,
                "participant_execution_services",
                self.participant_execution_services,
            ),
            participant_resource_budget_states=_mapping_update(
                updates,
                "participant_resource_budget_states",
                self.participant_resource_budget_states,
            ),
            participant_resource_pool_states=_mapping_update(
                updates,
                "participant_resource_pool_states",
                self.participant_resource_pool_states,
            ),
            participant_resource_budget_events=_mapping_update(
                updates,
                "participant_resource_budget_events",
                self.participant_resource_budget_events,
            ),
            shared_state_records=_mapping_update(
                updates,
                "shared_state_records",
                self.shared_state_records,
            ),
            shared_state_history=_history_update(
                updates,
                "shared_state_history",
                self.shared_state_history,
            ),
            joint_action_records=_mapping_update(
                updates,
                "joint_action_records",
                self.joint_action_records,
            ),
            time_management_contexts=_mapping_update(
                updates,
                "time_management_contexts",
                self.time_management_contexts,
            ),
            time_model_state=_time_model_state_update(
                updates,
                "time_model_state",
                self.time_model_state,
            ),
            realization_provenance=_provenance_update(
                updates,
                "realization_provenance",
                self.realization_provenance,
            ),
            realization_envelope=_identity_update(
                updates,
                "realization_envelope",
                self.realization_envelope,
            ),
            metadata=_mapping_update(updates, "metadata", self.metadata),
        )


_SNAPSHOT_UPDATE_KEYS = {
    "orchestration_results",
    "orchestration_history",
    "evaluation_results",
    "evaluation_history",
    "proposition_truth_results",
    "participant_episode_results",
    "participant_episode_history",
    "participant_behavior_history",
    "participant_control_history",
    "participant_autonomous_execution_states",
    "participant_execution_services",
    "participant_resource_budget_states",
    "participant_resource_pool_states",
    "participant_resource_budget_events",
    "shared_state_records",
    "shared_state_history",
    "joint_action_records",
    "time_management_contexts",
    "time_model_state",
    "realization_provenance",
    "realization_envelope",
    "metadata",
}


def _require_participant_resource_budget_snapshot(
    states: Mapping[str, Mapping[str, Any]],
    pools: Mapping[str, Mapping[str, Any]],
    events: Mapping[str, Mapping[str, Any]],
) -> None:
    from raes_contracts.contracts.participant_resource_budgets import (
        ParticipantResourceBudgetEventModel,
        ParticipantResourceBudgetStateModel,
        ParticipantResourcePoolStateModel,
    )

    for state_ref, payload in states.items():
        state = ParticipantResourceBudgetStateModel.model_validate(payload)
        if state_ref != state.state_ref:
            raise ValueError("participant resource-budget state key must equal state_ref")
    for pool_state_ref, payload in pools.items():
        pool = ParticipantResourcePoolStateModel.model_validate(payload)
        if pool_state_ref != pool.pool_state_ref:
            raise ValueError("participant resource-pool state key must equal pool_state_ref")
    for event_id, payload in events.items():
        event = ParticipantResourceBudgetEventModel.model_validate(payload)
        if event_id != event.event_id:
            raise ValueError("participant resource-budget event key must equal event_id")


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


def _provenance_update(
    updates: Mapping[str, object],
    key: str,
    current: tuple[RealizationProvenanceEntry, ...],
) -> tuple[RealizationProvenanceEntry, ...]:
    raw = updates.get(key)
    if raw is None:
        return tuple(current)
    if not isinstance(raw, tuple) or any(not isinstance(entry, RealizationProvenanceEntry) for entry in raw):
        raise TypeError(f"{key} must be a tuple of RealizationProvenanceEntry")
    return raw


def _identity_update(
    updates: Mapping[str, object],
    key: str,
    current: RealizationEnvelopeIdentityModel | None,
) -> RealizationEnvelopeIdentityModel | None:
    from raes_contracts.contracts import RealizationEnvelopeIdentityModel

    raw = updates.get(key)
    if raw is None:
        return current
    if not isinstance(raw, RealizationEnvelopeIdentityModel):
        raise TypeError(f"{key} must be a RealizationEnvelopeIdentityModel")
    return raw


def _time_model_state_update(
    updates: Mapping[str, object],
    key: str,
    current: TimeRuntimeStateModel | None,
) -> TimeRuntimeStateModel | None:
    from raes_contracts.contracts.time_model import TimeRuntimeStateModel

    if key not in updates:
        return current
    raw = updates[key]
    if raw is None:
        return None
    if not isinstance(raw, TimeRuntimeStateModel):
        raise TypeError(f"{key} must be a TimeRuntimeStateModel")
    return raw


@dataclass
class ApplyResult:
    """Result of applying or starting a runtime plan."""

    success: bool
    snapshot: RuntimeSnapshot
    diagnostics: list[Diagnostic] = field(default_factory=list)
    changed_addresses: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_changed_addresses(self.changed_addresses)


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

    def __post_init__(self) -> None:
        _validate_changed_addresses(self.changed_addresses)


def _validate_changed_addresses(addresses: list[str]) -> None:
    for address in addresses:
        require_compiled_address(address, field_name="changed address")
    if len(addresses) != len(set(addresses)):
        raise ValueError("changed addresses must be unique")


@dataclass(frozen=True)
class RuntimeSnapshotEnvelope:
    """Portable envelope around the current runtime snapshot."""

    schema_version: str = RUNTIME_SNAPSHOT_SCHEMA_VERSION
    snapshot: RuntimeSnapshot = field(default_factory=RuntimeSnapshot)


__all__ = (
    "ApplyResult",
    "ExplicitnessClass",
    "ExplicitnessProvenance",
    "OperationReceipt",
    "OperationState",
    "OperationStatus",
    "RealizationProvenanceEntry",
    "RuntimeSnapshot",
    "RuntimeSnapshotEnvelope",
    "SnapshotEntry",
)
