"""Reference async-style control plane over runtime targets.

This is a repo-owned, schema-oriented façade that exposes runtime execution as
submitted operations over plain-data-compatible envelopes. The current
implementation completes operations eagerly, but the contract surface matches an
async control plane so non-Python runtimes can evolve behind the same API.
"""

from __future__ import annotations

from collections.abc import Mapping
from threading import RLock
from uuid import uuid4

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.manifest_authority import PARTICIPANT_RUNTIME_POLICY_FEATURES
from raes_contracts.planning import (
    EvaluationPlan,
    OrchestrationPlan,
    ProvisioningPlan,
    RuntimeDomain,
)
from raes_contracts.runtime_state import (
    OperationReceipt,
    OperationState,
    OperationStatus,
    RuntimeSnapshot,
    RuntimeSnapshotEnvelope,
)
from raes_contracts.vocabulary import ParticipantFeatureSupportLevel
from raes_processor.models import ParticipantBehaviorSpecificationRuntime

from .backend_calls import _call_backend_diagnostics
from .control_plane_execution import (
    OperationExecutionRequest,
    _utc_now,
    execute_operation,
)
from .control_plane_store import (
    AuditEvent,
    ControlPlaneOperationRecord,
    ControlPlaneStore,
    InMemoryControlPlaneStore,
)
from .control_plane_submission import _submitted_plan_diagnostics
from .control_plane_workflow_control import WorkflowControlMixin
from .operational_apparatus import operational_apparatus_summary
from .participant_control import ParticipantControlMixin
from .participant_crossing_mediation import (
    ParticipantCrossingPolicyResolver,
    validate_persisted_crossing_history,
)
from .participant_retrieval import ParticipantRetrievalMixin
from .registry import RuntimeTarget


def _require_crossing_policy_configuration(
    target: RuntimeTarget,
    resolver: ParticipantCrossingPolicyResolver | None,
) -> None:
    capabilities = target.manifest.participant_runtime
    if capabilities is None:
        return
    enabled_policy_features = {
        declaration.feature
        for declaration in capabilities.feature_support
        if declaration.feature in PARTICIPANT_RUNTIME_POLICY_FEATURES
        and declaration.support_level != ParticipantFeatureSupportLevel.UNSUPPORTED
    }
    if enabled_policy_features and resolver is None:
        features = ", ".join(sorted(enabled_policy_features))
        raise ValueError(f"participant policy capabilities require a crossing policy resolver: {features}")


class RuntimeControlPlane(WorkflowControlMixin, ParticipantControlMixin, ParticipantRetrievalMixin):
    """Reference control plane for async runtime submission and observation."""

    def __init__(
        self,
        target: RuntimeTarget,
        *,
        initial_snapshot: RuntimeSnapshot | None = None,
        store: ControlPlaneStore | None = None,
        behavior_specifications: Mapping[str, ParticipantBehaviorSpecificationRuntime] | None = None,
        crossing_policy_resolver: ParticipantCrossingPolicyResolver | None = None,
    ) -> None:
        _require_crossing_policy_configuration(target, crossing_policy_resolver)
        self._target = target
        self._store = store or InMemoryControlPlaneStore(initial_snapshot)
        self._snapshot = initial_snapshot if initial_snapshot is not None else self._store.load_snapshot()
        self._operations: dict[str, ControlPlaneOperationRecord] = self._store.load_records()
        self._behavior_specifications = dict(behavior_specifications or {})
        self._crossing_policy_resolver = crossing_policy_resolver
        self._participant_control_lock = RLock()
        if self._snapshot.participant_crossing_history:
            if crossing_policy_resolver is None:
                raise ValueError("persisted participant crossing history requires a policy resolver")
            validate_persisted_crossing_history(self._snapshot, crossing_policy_resolver)

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
        diagnostics = _submitted_plan_diagnostics(
            plan,
            RuntimeDomain.PROVISIONING,
            self._snapshot,
            self._target.manifest,
        )
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
