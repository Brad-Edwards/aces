"""Durable commit and cache-reconciliation helpers for the control plane."""

from __future__ import annotations

from raes_contracts.runtime_state import RuntimeSnapshot

from .control_plane_recovery import reconcile_interrupted_operations
from .control_plane_store import AuditEvent, ControlPlaneOperationRecord, ControlPlaneStore
from .control_plane_store_compatibility import ControlPlaneStoreCommitAdapter


class RuntimeDurabilityMixin:
    """Keep live caches aligned with durable state after every store outcome."""

    _store: ControlPlaneStore
    _store_commits: ControlPlaneStoreCommitAdapter
    _snapshot: RuntimeSnapshot
    _operations: dict[str, ControlPlaneOperationRecord]

    def _commit_terminal_operation(
        self,
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
    ) -> None:
        self._assert_runtime_owner()
        try:
            self._store_commits.commit_terminal_operation(snapshot, record)
        except BaseException as exc:
            self._resynchronize_after_store_error(exc)
            raise
        self._publish_committed_state(snapshot, record)

    def _commit_control_transition(
        self,
        *,
        participant_address: str,
        expected_head: str | None,
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
        audit_event: AuditEvent,
    ) -> None:
        self._assert_runtime_owner()
        try:
            self._store.commit_control_transition(
                participant_address=participant_address,
                expected_head=expected_head,
                snapshot=snapshot,
                record=record,
                audit_event=audit_event,
            )
        except BaseException as exc:
            self._resynchronize_after_store_error(exc)
            raise
        self._publish_committed_state(snapshot, record)

    def _commit_participant_transition(
        self,
        *,
        expected_history_heads: dict[str, str | None],
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
        audit_event: AuditEvent,
    ) -> None:
        self._assert_runtime_owner()
        try:
            self._store.commit_participant_transition(
                expected_history_heads=expected_history_heads,
                snapshot=snapshot,
                record=record,
                audit_event=audit_event,
            )
        except BaseException as exc:
            self._resynchronize_after_store_error(exc)
            raise
        self._publish_committed_state(snapshot, record)

    def _publish_committed_state(
        self,
        snapshot: RuntimeSnapshot,
        record: ControlPlaneOperationRecord,
    ) -> None:
        self._snapshot = snapshot
        self._operations[record.receipt.operation_id] = record

    def _resynchronize_after_store_error(self, error: BaseException) -> None:
        """Refresh both caches after a store call with an uncertain outcome."""

        try:
            snapshot = self._store.load_snapshot()
            operations = self._store.load_records()
            operations = reconcile_interrupted_operations(self._store_commits, operations)
        except Exception as reconciliation_error:
            self._poison_runtime_durability()
            error.add_note(
                "Durable state could not be reconciled after the store error; "
                f"this runtime is poisoned until restart ({reconciliation_error!r})."
            )
            return
        self._snapshot = snapshot
        self._operations = operations


__all__ = ("RuntimeDurabilityMixin",)
