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

from raes_contracts.contracts import ParticipantInformationStateContextResolver
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.manifest_authority import PARTICIPANT_RUNTIME_POLICY_FEATURES
from raes_contracts.plan_projection import provisioning_plan_digest
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
from .control_plane_durability import RuntimeDurabilityMixin
from .control_plane_execution import (
    OperationExecutionRequest,
    _utc_now,
    execute_operation,
)
from .control_plane_lifecycle import RuntimeLifecycleMixin, runtime_owned
from .control_plane_recovery import reconcile_interrupted_operations
from .control_plane_store import (
    AuditEvent,
    ControlPlaneOperationRecord,
    ControlPlaneStore,
    InMemoryControlPlaneStore,
)
from .control_plane_store_compatibility import adapt_control_plane_store
from .control_plane_submission import _submitted_plan_diagnostics
from .control_plane_workflow_control import WorkflowControlMixin
from .operational_apparatus import operational_apparatus_summary
from .participant_control import ParticipantControlMixin
from .participant_crossing_mediation import (
    ParticipantCrossingPolicyResolver,
    validate_persisted_crossing_history,
)
from .participant_information_state_validation import require_participant_information_state_snapshot
from .participant_retrieval import ParticipantRetrievalMixin
from .registry import RuntimeTarget as _RuntimeTarget


def _require_crossing_policy_configuration(
    target: _RuntimeTarget,
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


def _require_final_sink_flow_control_configuration(
    resolver: ParticipantCrossingPolicyResolver | None,
    enforce_final_sink_flow_control: bool,
) -> None:
    """Reject a policy resolver that cannot resolve the SEM-233 final-sink permit.

    Final-sink enforcement is fail-closed by default: a control plane that
    governs participant crossings must resolve a fresh exact-cut SEM-233 permit
    immediately before every effect. A resolver without ``resolve_flow_sink_decision``
    cannot, so the control plane refuses to construct rather than silently
    admitting effects with no final-sink decision. A deployment that intentionally
    runs the legacy API-423-only path passes ``enforce_final_sink_flow_control=False``.
    """

    if not enforce_final_sink_flow_control or resolver is None:
        return
    if not callable(getattr(resolver, "resolve_flow_sink_decision", None)):
        raise ValueError(
            "participant final-sink flow-control enforcement requires the crossing policy "
            "resolver to implement resolve_flow_sink_decision; pass "
            "enforce_final_sink_flow_control=False to run the legacy API-423-only path"
        )


class RuntimeControlPlane(
    RuntimeLifecycleMixin,
    RuntimeDurabilityMixin,
    WorkflowControlMixin,
    ParticipantControlMixin,
    ParticipantRetrievalMixin,
):
    """Reference control plane for async runtime submission and observation."""

    def __init__(
        self,
        target: _RuntimeTarget,
        *,
        initial_snapshot: RuntimeSnapshot | None = None,
        store: ControlPlaneStore | None = None,
        behavior_specifications: Mapping[str, ParticipantBehaviorSpecificationRuntime] | None = None,
        crossing_policy_resolver: ParticipantCrossingPolicyResolver | None = None,
        information_state_context_resolver: ParticipantInformationStateContextResolver | None = None,
        enforce_final_sink_flow_control: bool = True,
    ) -> None:
        self._initialize_runtime_lifecycle()
        _require_crossing_policy_configuration(target, crossing_policy_resolver)
        _require_final_sink_flow_control_configuration(crossing_policy_resolver, enforce_final_sink_flow_control)
        self._target = target
        self._enforce_final_sink_flow_control = enforce_final_sink_flow_control
        self._store = store or InMemoryControlPlaneStore(initial_snapshot)
        try:
            self._store_commits = adapt_control_plane_store(self._store)
            acquire_runtime_lease = getattr(self._store, "acquire_runtime_lease", None)
            if callable(acquire_runtime_lease):
                self._runtime_lease = acquire_runtime_lease()
            self._snapshot = initial_snapshot if initial_snapshot is not None else self._store.load_snapshot()
            self._operations: dict[str, ControlPlaneOperationRecord] = self._store.load_records()
            self._operations = reconcile_interrupted_operations(self._store_commits, self._operations)
            self._behavior_specifications = dict(behavior_specifications or {})
            self._crossing_policy_resolver = crossing_policy_resolver
            self._information_state_context_resolver = information_state_context_resolver
            self._operation_lock = RLock()
            self._participant_control_lock = self._operation_lock
            self._trusted_provisioning_plan_lock = RLock()
            self._trusted_provisioning_plan_digests: set[str] = set()
            require_participant_information_state_snapshot(
                self._snapshot,
                information_state_context_resolver,
            )
            if self._snapshot.participant_crossing_history:
                if crossing_policy_resolver is None:
                    raise ValueError("persisted participant crossing history requires a policy resolver")
                validate_persisted_crossing_history(self._snapshot, crossing_policy_resolver)
        except BaseException:
            self.close()
            raise

    @property
    @runtime_owned
    def snapshot(self) -> RuntimeSnapshot:
        self._assert_runtime_owner()
        return self._snapshot

    @property
    @runtime_owned
    def target_name(self) -> str:
        self._assert_runtime_owner()
        return self._target.name

    @runtime_owned
    def audit_log(self) -> list[AuditEvent]:
        self._assert_runtime_owner()
        return self._store.read_audit()

    @runtime_owned
    def operational_apparatus_summary(self) -> dict[str, object]:
        """Return a compact operational view over existing control-plane carriers."""

        self._assert_runtime_owner()
        audit_events = self._store.read_audit()
        with self._operation_lock:
            operation_records = list(self._operations.values())
        return operational_apparatus_summary(
            target_name=self._target.name,
            snapshot=self._snapshot,
            operation_records=operation_records,
            audit_events=audit_events,
        )

    @runtime_owned
    def register_planner_produced_provisioning_plan(self, plan: ProvisioningPlan) -> str:
        """Trust one exact planner artifact for later HTTP relay submission.

        This method is an in-process authority boundary and is deliberately not
        exposed by the HTTP control plane. Relay principals can submit a
        registered artifact, but cannot mint or widen its realization policy.
        """

        self._assert_runtime_owner()
        digest = provisioning_plan_digest(plan)
        with self._trusted_provisioning_plan_lock:
            self._trusted_provisioning_plan_digests.add(digest)
        return digest

    @runtime_owned
    def is_planner_authorized_provisioning_plan(self, plan: ProvisioningPlan) -> bool:
        """Return whether the exact published plan was registered in-process."""

        self._assert_runtime_owner()
        digest = provisioning_plan_digest(plan)
        with self._trusted_provisioning_plan_lock:
            return digest in self._trusted_provisioning_plan_digests

    @runtime_owned
    def submit_provisioning(
        self,
        plan: ProvisioningPlan,
        *,
        base_snapshot: RuntimeSnapshot | None = None,
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        self._assert_runtime_owner()
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

    @runtime_owned
    def submit_orchestration(
        self,
        plan: OrchestrationPlan,
        *,
        base_snapshot: RuntimeSnapshot | None = None,
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        self._assert_runtime_owner()
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

    @runtime_owned
    def submit_evaluation(
        self,
        plan: EvaluationPlan,
        *,
        base_snapshot: RuntimeSnapshot | None = None,
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        self._assert_runtime_owner()
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

    @runtime_owned
    def get_operation(self, operation_id: str) -> OperationStatus | None:
        self._assert_runtime_owner()
        with self._operation_lock:
            record = self._operations.get(operation_id)
        return None if record is None else record.status

    @runtime_owned
    def get_snapshot(self) -> RuntimeSnapshotEnvelope:
        self._assert_runtime_owner()
        return RuntimeSnapshotEnvelope(snapshot=self._snapshot)

    @runtime_owned
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
        self._assert_runtime_owner()
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
        persisted = self._claim_record(
            ControlPlaneOperationRecord(
                receipt=receipt,
                status=status,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        )
        return persisted.receipt

    def _idempotent_receipt(
        self,
        *,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> OperationReceipt | None:
        self._assert_runtime_owner()
        if not idempotency_key:
            return None
        record = self._store.find_by_idempotency(idempotency_key)
        if record is None:
            return None
        if record.request_fingerprint and request_fingerprint and record.request_fingerprint != request_fingerprint:
            raise ValueError("Idempotency-Key was reused with a different request body.")
        with self._operation_lock:
            self._operations[record.receipt.operation_id] = record
        return record.receipt

    def _claim_record(self, record: ControlPlaneOperationRecord) -> ControlPlaneOperationRecord:
        self._assert_runtime_owner()
        persisted = self._store_commits.claim_record(record)
        if (
            persisted.request_fingerprint
            and record.request_fingerprint
            and persisted.request_fingerprint != record.request_fingerprint
        ):
            raise ValueError("Idempotency-Key was reused with a different request body.")
        with self._operation_lock:
            self._operations[persisted.receipt.operation_id] = persisted
        return persisted
