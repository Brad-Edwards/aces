"""Reference async-style control plane over runtime targets.

This is a repo-owned, schema-oriented façade that exposes runtime execution as
submitted operations over plain-data-compatible envelopes. The current
implementation completes operations eagerly, but the contract surface matches an
async control plane so non-Python runtimes can evolve behind the same API.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.planning import (
    EvaluationPlan,
    OrchestrationPlan,
    ProvisioningPlan,
    RuntimeDomain,
    require_plan_operation_identity,
)
from aces_contracts.runtime_state import (
    OperationReceipt,
    OperationState,
    OperationStatus,
    RuntimeSnapshot,
    RuntimeSnapshotEnvelope,
)
from aces_contracts.workflow import (
    WorkflowCompensationStatus,
    WorkflowExecutionState,
    WorkflowHistoryEvent,
    WorkflowHistoryEventType,
    WorkflowStatus,
)

from .backend_calls import _call_backend_diagnostics
from .control_plane_execution import (
    OperationExecutionRequest,
    SucceededOperationRequest,
    execute_operation,
    persist_succeeded_operation,
)
from .control_plane_store import (
    AuditEvent,
    ControlPlaneOperationRecord,
    ControlPlaneStore,
    InMemoryControlPlaneStore,
)
from .control_plane_timeouts import workflow_timeout_update
from .control_plane_workflows import maybe_apply_compensation
from .operational_apparatus import operational_apparatus_summary
from .participant_control import ParticipantControlMixin
from .participant_retrieval import ParticipantRetrievalMixin
from .registry import RuntimeTarget

_TERMINAL_WORKFLOW_STATUSES = {
    WorkflowStatus.SUCCEEDED,
    WorkflowStatus.FAILED,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.TIMED_OUT,
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _submitted_plan_diagnostics(
    plan: ProvisioningPlan | OrchestrationPlan | EvaluationPlan,
    domain: RuntimeDomain,
    snapshot: RuntimeSnapshot,
) -> list[Diagnostic]:
    admitted = set(snapshot.entries) | {operation.address for operation in plan.operations}
    for operation in plan.operations:
        try:
            require_plan_operation_identity(domain, operation.address, operation.resource_type)
        except ValueError:
            return [
                Diagnostic(
                    code="runtime.plan-resource-incoherent",
                    domain="runtime",
                    address=f"runtime.control-plane.{domain.value}",
                    message="Submitted plan operation disagrees with the endpoint resource identity.",
                )
            ]
        dependencies = {*operation.ordering_dependencies, *operation.refresh_dependencies}
        if dependencies - admitted:
            return [
                Diagnostic(
                    code="runtime.plan-dependency-unresolved",
                    domain="runtime",
                    address=f"runtime.control-plane.{domain.value}",
                    message="Submitted plan contains a dependency outside its operations and admitted snapshot.",
                )
            ]
        existing = snapshot.entries.get(operation.address)
        if existing is not None and (
            existing.domain is not domain or existing.resource_type != operation.resource_type
        ):
            return [
                Diagnostic(
                    code="runtime.plan-resource-incoherent",
                    domain="runtime",
                    address=f"runtime.control-plane.{domain.value}",
                    message="Submitted plan disagrees with the admitted snapshot resource identity.",
                )
            ]
    return []


class RuntimeControlPlane(ParticipantControlMixin, ParticipantRetrievalMixin):
    """Reference control plane for async runtime submission and observation."""

    def __init__(
        self,
        target: RuntimeTarget,
        *,
        initial_snapshot: RuntimeSnapshot | None = None,
        store: ControlPlaneStore | None = None,
    ) -> None:
        self._target = target
        self._store = store or InMemoryControlPlaneStore(initial_snapshot)
        self._snapshot = initial_snapshot if initial_snapshot is not None else self._store.load_snapshot()
        self._operations: dict[str, ControlPlaneOperationRecord] = self._store.load_records()

    @property
    def snapshot(self) -> RuntimeSnapshot:
        return self._snapshot

    @property
    def target_name(self) -> str:
        return self._target.name

    def audit_log(self) -> list[AuditEvent]:
        return self._store.read_audit()

    def operational_apparatus_summary(self) -> dict[str, object]:
        """Return a compact operational view over existing control-plane carriers."""

        audit_events = self._store.read_audit()
        operation_records = list(self._operations.values())
        return operational_apparatus_summary(
            target_name=self._target.name,
            snapshot=self._snapshot,
            operation_records=operation_records,
            audit_events=audit_events,
        )

    def submit_provisioning(
        self,
        plan: ProvisioningPlan,
        *,
        base_snapshot: RuntimeSnapshot | None = None,
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        diagnostics = _submitted_plan_diagnostics(plan, RuntimeDomain.PROVISIONING, self._snapshot)
        if diagnostics:
            return self._reject_diagnostics(
                domain=RuntimeDomain.PROVISIONING,
                diagnostics=diagnostics,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        diagnostics = _call_backend_diagnostics(
            self._target.provisioner.validate,
            plan,
            address="runtime.control-plane.provisioning.validate",
        )
        return execute_operation(
            self,
            OperationExecutionRequest(
                domain=RuntimeDomain.PROVISIONING,
                method=self._target.provisioner.apply,
                plan=plan,
                address="runtime.control-plane.provisioning",
                diagnostics=diagnostics,
                base_snapshot=base_snapshot,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            ),
        )

    def submit_orchestration(
        self,
        plan: OrchestrationPlan,
        *,
        base_snapshot: RuntimeSnapshot | None = None,
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        if self._target.orchestrator is None:
            return self._reject_submission(
                domain=RuntimeDomain.ORCHESTRATION,
                message="Target does not provide an orchestrator.",
            )
        diagnostics = _submitted_plan_diagnostics(plan, RuntimeDomain.ORCHESTRATION, self._snapshot)
        if diagnostics:
            return self._reject_diagnostics(
                domain=RuntimeDomain.ORCHESTRATION,
                diagnostics=diagnostics,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        return execute_operation(
            self,
            OperationExecutionRequest(
                domain=RuntimeDomain.ORCHESTRATION,
                method=self._target.orchestrator.start,
                plan=plan,
                address="runtime.control-plane.orchestration",
                diagnostics=[],
                base_snapshot=base_snapshot,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            ),
        )

    def submit_evaluation(
        self,
        plan: EvaluationPlan,
        *,
        base_snapshot: RuntimeSnapshot | None = None,
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        if self._target.evaluator is None:
            return self._reject_submission(
                domain=RuntimeDomain.EVALUATION,
                message="Target does not provide an evaluator.",
            )
        diagnostics = _submitted_plan_diagnostics(plan, RuntimeDomain.EVALUATION, self._snapshot)
        if diagnostics:
            return self._reject_diagnostics(
                domain=RuntimeDomain.EVALUATION,
                diagnostics=diagnostics,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        return execute_operation(
            self,
            OperationExecutionRequest(
                domain=RuntimeDomain.EVALUATION,
                method=self._target.evaluator.start,
                plan=plan,
                address="runtime.control-plane.evaluation",
                diagnostics=[],
                base_snapshot=base_snapshot,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            ),
        )

    def get_operation(self, operation_id: str) -> OperationStatus | None:
        record = self._operations.get(operation_id)
        return None if record is None else record.status

    def get_snapshot(self) -> RuntimeSnapshotEnvelope:
        return RuntimeSnapshotEnvelope(snapshot=self._snapshot)

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

    def record_audit(
        self,
        *,
        action: str,
        identity: str,
        allowed: bool,
        target: str,
        reason: str = "",
        operation_id: str = "",
        details: dict[str, object] | None = None,
    ) -> None:
        self._store.append_audit(
            AuditEvent(
                timestamp=_utc_now(),
                action=action,
                identity=identity,
                allowed=allowed,
                target=target,
                operation_id=operation_id,
                reason=reason,
                details=dict(details or {}),
            )
        )

    def _reject_submission(
        self,
        *,
        domain: RuntimeDomain,
        message: str,
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        diagnostic = Diagnostic(
            code="runtime.control-plane.rejected",
            domain="runtime",
            address=f"runtime.control-plane.{domain.value}",
            message=message,
        )
        return self._reject_diagnostics(
            domain=domain,
            diagnostics=[diagnostic],
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )

    def _reject_diagnostics(
        self,
        *,
        domain: RuntimeDomain,
        diagnostics: list[Diagnostic],
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        operation_id = str(uuid4())
        submitted_at = _utc_now()
        receipt = OperationReceipt(
            operation_id=operation_id,
            domain=domain,
            submitted_at=submitted_at,
            accepted=False,
            diagnostics=list(diagnostics),
        )
        status = OperationStatus(
            operation_id=operation_id,
            domain=domain,
            state=OperationState.FAILED,
            submitted_at=submitted_at,
            updated_at=submitted_at,
            diagnostics=list(diagnostics),
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

    def _idempotent_receipt(
        self,
        *,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> OperationReceipt | None:
        if not idempotency_key:
            return None
        record = self._store.find_by_idempotency(idempotency_key)
        if record is None:
            return None
        if record.request_fingerprint and request_fingerprint and record.request_fingerprint != request_fingerprint:
            raise ValueError("Idempotency-Key was reused with a different request body.")
        self._operations[record.receipt.operation_id] = record
        return record.receipt

    def _persist_record(self, record: ControlPlaneOperationRecord) -> None:
        self._operations[record.receipt.operation_id] = record
        self._store.save_record(record)
