"""Workflow cancellation and timeout reconciliation for the runtime control plane.

``WorkflowControlMixin`` supplies the operator-facing workflow lifecycle
operations (cancellation and timeout reconciliation) mixed into
``RuntimeControlPlane``. It relies on the concrete control plane for the
snapshot, store, and operation-record helpers, matching the other runtime
control-plane mixins.
"""

from __future__ import annotations

from uuid import uuid4

from raes_contracts.planning import RuntimeDomain
from raes_contracts.runtime_state import (
    OperationReceipt,
    OperationState,
    OperationStatus,
)
from raes_contracts.workflow import (
    WorkflowCompensationStatus,
    WorkflowExecutionState,
    WorkflowHistoryEvent,
    WorkflowHistoryEventType,
    WorkflowStatus,
)

from .control_plane_execution import (
    SucceededOperationRequest,
    _utc_now,
    persist_succeeded_operation,
)
from .control_plane_store import ControlPlaneOperationRecord
from .control_plane_timeouts import _reconciliation_clock, workflow_timeout_update
from .control_plane_workflows import maybe_apply_compensation

_TERMINAL_WORKFLOW_STATUSES = {
    WorkflowStatus.SUCCEEDED,
    WorkflowStatus.FAILED,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.TIMED_OUT,
}


class WorkflowControlMixin:
    """Workflow cancellation and timeout reconciliation operations."""

    def cancel_workflow(
        self,
        workflow_address: str,
        *,
        run_id: str | None = None,
        reason: str = "cancelled by operator",
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        existing = self._idempotent_receipt(
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
        if existing is not None:
            return existing
        submitted_at = _utc_now()
        operation_id = str(uuid4())
        context = self._cancellable_workflow_state(
            workflow_address,
            run_id=run_id,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
        if isinstance(context, OperationReceipt):
            return context
        if context.workflow_status in _TERMINAL_WORKFLOW_STATUSES:
            receipt = persist_succeeded_operation(
                self,
                SucceededOperationRequest(
                    operation_id=operation_id,
                    domain=RuntimeDomain.ORCHESTRATION,
                    submitted_at=submitted_at,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                ),
            )
        else:
            receipt = self._cancel_active_workflow(
                workflow_address,
                normalized=context,
                reason=reason,
                operation_id=operation_id,
                submitted_at=submitted_at,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        return receipt

    def _cancellable_workflow_state(
        self,
        workflow_address: str,
        *,
        run_id: str | None,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> WorkflowExecutionState | OperationReceipt:
        result = dict(self._snapshot.orchestration_results.get(workflow_address, {}))
        rejection = None
        normalized: WorkflowExecutionState | None = None
        if not result:
            rejection = f"Unknown workflow run: {workflow_address}"
        else:
            normalized = WorkflowExecutionState.from_payload(result)
            if run_id and normalized.run_id != run_id:
                rejection = f"Workflow run_id mismatch for {workflow_address}: {run_id!r} != {normalized.run_id!r}"
        if rejection is not None:
            return self._reject_submission(
                domain=RuntimeDomain.ORCHESTRATION,
                message=rejection,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        assert normalized is not None
        return normalized

    def _cancel_active_workflow(
        self,
        workflow_address: str,
        *,
        normalized: WorkflowExecutionState,
        reason: str,
        operation_id: str,
        submitted_at: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> OperationReceipt:
        cancelled_state = WorkflowExecutionState(
            state_schema_version=normalized.state_schema_version,
            workflow_status=WorkflowStatus.CANCELLED,
            run_id=normalized.run_id,
            started_at=normalized.started_at,
            updated_at=submitted_at,
            terminal_reason=reason,
            compensation_status=WorkflowCompensationStatus.NOT_REQUIRED,
            compensation_started_at=None,
            compensation_updated_at=None,
            compensation_failures=[],
            steps=normalized.steps,
        )
        history = list(self._snapshot.orchestration_history.get(workflow_address, []))
        history.append(
            WorkflowHistoryEvent(
                event_type=WorkflowHistoryEventType.WORKFLOW_CANCELLED,
                timestamp=submitted_at,
                details={"reason": reason},
            ).to_payload()
        )
        cancelled, history = maybe_apply_compensation(
            self._snapshot,
            workflow_address=workflow_address,
            result=cancelled_state,
            history=history,
            submitted_at=submitted_at,
        )
        self._snapshot = self._snapshot.with_entries(
            dict(self._snapshot.entries),
            orchestration_results={
                **self._snapshot.orchestration_results,
                workflow_address: cancelled,
            },
            orchestration_history={
                **self._snapshot.orchestration_history,
                workflow_address: history,
            },
        )
        self._store.save_snapshot(self._snapshot)
        receipt = OperationReceipt(
            operation_id=operation_id,
            domain=RuntimeDomain.ORCHESTRATION,
            submitted_at=submitted_at,
            accepted=True,
        )
        status = OperationStatus(
            operation_id=operation_id,
            domain=RuntimeDomain.ORCHESTRATION,
            state=OperationState.SUCCEEDED,
            submitted_at=submitted_at,
            updated_at=submitted_at,
            changed_addresses=[workflow_address],
        )
        self._persist_record(
            ControlPlaneOperationRecord(
                receipt=receipt,
                status=status,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        )
        return receipt

    def reconcile_workflow_timeouts(
        self,
        *,
        now: str | None = None,
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        existing = self._idempotent_receipt(
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
        if existing is not None:
            return existing
        submitted_at = now or _utc_now()
        reconciliation_clock = _reconciliation_clock(submitted_at)
        changed: list[str] = []
        orchestration_results = dict(self._snapshot.orchestration_results)
        orchestration_history = {
            address: list(events) for address, events in self._snapshot.orchestration_history.items()
        }
        for workflow_address, entry in self._snapshot.entries.items():
            timed_out = workflow_timeout_update(
                self._snapshot,
                workflow_address,
                entry,
                orchestration_results,
                orchestration_history,
                submitted_at,
                reconciliation_clock=reconciliation_clock,
            )
            if timed_out is None:
                continue
            orchestration_results[workflow_address] = timed_out[0]
            orchestration_history[workflow_address] = timed_out[1]
            changed.append(workflow_address)
        operation_id = str(uuid4())
        self._snapshot = self._snapshot.with_entries(
            dict(self._snapshot.entries),
            orchestration_results=orchestration_results,
            orchestration_history=orchestration_history,
        )
        self._store.save_snapshot(self._snapshot)
        receipt = OperationReceipt(
            operation_id=operation_id,
            domain=RuntimeDomain.ORCHESTRATION,
            submitted_at=submitted_at,
            accepted=True,
        )
        status = OperationStatus(
            operation_id=operation_id,
            domain=RuntimeDomain.ORCHESTRATION,
            state=OperationState.SUCCEEDED,
            submitted_at=submitted_at,
            updated_at=submitted_at,
            changed_addresses=changed,
        )
        self._persist_record(
            ControlPlaneOperationRecord(
                receipt=receipt,
                status=status,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        )
        return receipt
