"""Participant retrieval projections for the runtime control plane."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from aces_contracts.contracts import (
    ParticipantContextViewModel,
    ParticipantHistoryViewModel,
    ParticipantStatusViewModel,
)
from aces_contracts.planning import RuntimeDomain
from aces_contracts.runtime_state import OperationState, RuntimeSnapshot

from .control_plane_store import ControlPlaneOperationRecord

_CURRENT_SNAPSHOT_REF = "runtime.snapshot.current"


class ParticipantRetrievalMixin:
    """API-408 participant retrieval projections over recorded runtime state."""

    _snapshot: RuntimeSnapshot
    _operations: dict[str, ControlPlaneOperationRecord]

    def get_participant_status_view(self, participant_address: str) -> ParticipantStatusViewModel | None:
        if not _participant_exists(self._snapshot, participant_address):
            return None
        episode_state = self._snapshot.participant_episode_results.get(participant_address)
        episode_id = _string_value(episode_state, "episode_id") if episode_state is not None else None
        return ParticipantStatusViewModel.model_validate(
            {
                "view_id": _view_id("status", participant_address, episode_id),
                "participant_address": participant_address,
                "episode_id": episode_id,
                "generated_at": _utc_now(),
                "source_snapshot_ref": _CURRENT_SNAPSHOT_REF,
                "episode_state": _project_scope(episode_state) if episode_state is not None else None,
                "open_operation_refs": _open_participant_operation_refs(self._operations, participant_address),
                "visibility_projection_ref": _visibility_projection_ref(participant_address, "status"),
                "marking_definition_refs": [],
                "redaction_policy_ref": None,
            }
        )

    def get_participant_history_view(
        self,
        participant_address: str,
        episode_id: str,
    ) -> ParticipantHistoryViewModel | None:
        if not _participant_episode_exists(self._snapshot, participant_address, episode_id):
            return None
        episode_history = [
            _project_scope(event)
            for event in self._snapshot.participant_episode_history.get(participant_address, [])
            if event.get("episode_id") == episode_id
        ]
        behavior_history = [
            _project_scope(event)
            for event in self._snapshot.participant_behavior_history.get(participant_address, [])
            if event.get("episode_id") == episode_id
        ]
        return ParticipantHistoryViewModel.model_validate(
            {
                "view_id": _view_id("history", participant_address, episode_id),
                "participant_address": participant_address,
                "episode_id": episode_id,
                "generated_at": _utc_now(),
                "source_snapshot_ref": _CURRENT_SNAPSHOT_REF,
                "episode_history": episode_history,
                "behavior_history": behavior_history,
                "visibility_projection_ref": _visibility_projection_ref(participant_address, "history"),
                "redaction_policy_ref": None,
                "completeness": "complete",
                "completeness_basis": None,
                "marking_definition_refs": [],
            }
        )

    def get_participant_context_view(
        self,
        participant_address: str,
        *,
        view_ref: str,
        episode_id: str | None = None,
        derivation_basis_ref: str | None = None,
        payload_ref: str | None = None,
        derived_from_refs: tuple[str, ...] = (),
    ) -> ParticipantContextViewModel | None:
        if episode_id is not None:
            if not _participant_episode_exists(self._snapshot, participant_address, episode_id):
                return None
        elif not _participant_exists(self._snapshot, participant_address):
            return None
        return ParticipantContextViewModel.model_validate(
            {
                "view_id": _view_id("context", participant_address, episode_id or view_ref),
                "participant_address": participant_address,
                "episode_id": episode_id,
                "generated_at": _utc_now(),
                "source_snapshot_ref": _CURRENT_SNAPSHOT_REF,
                "view_ref": view_ref,
                "derived_from_refs": list(derived_from_refs or (_CURRENT_SNAPSHOT_REF,)),
                "derivation_basis_ref": derivation_basis_ref,
                "payload_ref": payload_ref,
                "visibility_projection_ref": _visibility_projection_ref(participant_address, "context"),
                "marking_definition_refs": [],
                "redaction_policy_ref": None,
            }
        )


def _string_value(payload: dict[str, object] | None, key: str) -> str | None:
    if payload is None:
        return None
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _participant_exists(snapshot: RuntimeSnapshot, participant_address: str) -> bool:
    return (
        participant_address in snapshot.participant_episode_results
        or participant_address in snapshot.participant_episode_history
        or participant_address in snapshot.participant_behavior_history
    )


def _participant_episode_exists(snapshot: RuntimeSnapshot, participant_address: str, episode_id: str) -> bool:
    episode_state = snapshot.participant_episode_results.get(participant_address)
    if _string_value(episode_state, "episode_id") == episode_id:
        return True
    histories = (
        snapshot.participant_episode_history.get(participant_address, []),
        snapshot.participant_behavior_history.get(participant_address, []),
    )
    return any(event.get("episode_id") == episode_id for history in histories for event in history)


def _project_scope(payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if key not in {"participant_address", "episode_id"}}


def _open_participant_operation_refs(
    operations: Mapping[str, ControlPlaneOperationRecord],
    participant_address: str,
) -> list[str]:
    return [
        operation_id
        for operation_id, record in sorted(operations.items())
        if record.status.domain == RuntimeDomain.PARTICIPANT
        and record.status.state in {OperationState.ACCEPTED, OperationState.RUNNING}
        and participant_address in record.status.changed_addresses
    ]


def _view_id(kind: str, participant_address: str, suffix: str | None) -> str:
    return f"runtime.participant-view.{kind}.{participant_address}.{suffix or 'current'}"


def _visibility_projection_ref(participant_address: str, kind: str) -> str:
    return f"runtime.visibility-projection.{kind}.{participant_address}.v1"
