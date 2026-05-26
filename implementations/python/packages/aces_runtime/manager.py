"""Runtime manager for compiled SDL runtime plans."""

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.planning import ChangeAction, ProvisioningPlan, ProvisionOp, RuntimeDomain
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot, SnapshotEntry
from aces_processor.compiler import compile_scenario_runtime_model
from aces_processor.models import (
    ExecutionPlan,
)
from aces_processor.planner import plan, snapshot_delete_order

from .backend_calls import _call_backend_apply, _call_backend_diagnostics
from .diagnostics import _failure_diagnostic, _has_error_diagnostic
from .registry import RuntimeTarget, _validate_runtime_target_shape

_RUNTIME_APPLY_ADDRESS = "runtime.apply"
_APPLY_EVALUATOR_ADDRESS = "runtime.apply.evaluator"
_APPLY_ORCHESTRATOR_ADDRESS = "runtime.apply.orchestrator"
_APPLY_PHASE_FAILED = "runtime.apply-phase-failed"
_DESTROY_PHASE_FAILED = "runtime.destroy-phase-failed"


def _delete_order(entries: dict[str, SnapshotEntry]) -> list[str]:
    return snapshot_delete_order(entries)


def _provenance_diagnostics(
    execution_plan: ExecutionPlan,
    target: RuntimeTarget,
    snapshot: RuntimeSnapshot,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if execution_plan.target_name is None:
        diagnostics.append(
            _failure_diagnostic(
                "runtime.plan-target-unbound",
                _RUNTIME_APPLY_ADDRESS,
                (
                    "Execution plan is not bound to a runtime target. Use "
                    "RuntimeManager.plan() or pass target_name explicitly."
                ),
            )
        )
    elif execution_plan.target_name != target.name:
        diagnostics.append(
            _failure_diagnostic(
                "runtime.plan-target-mismatch",
                _RUNTIME_APPLY_ADDRESS,
                (f"Execution plan targets '{execution_plan.target_name}', but manager target is '{target.name}'."),
            )
        )
    if execution_plan.manifest != target.manifest:
        diagnostics.append(
            _failure_diagnostic(
                "runtime.plan-manifest-mismatch",
                _RUNTIME_APPLY_ADDRESS,
                "Execution plan manifest does not match the manager target manifest.",
            )
        )
    if execution_plan.base_snapshot != snapshot:
        diagnostics.append(
            _failure_diagnostic(
                "runtime.plan-snapshot-mismatch",
                _RUNTIME_APPLY_ADDRESS,
                "Execution plan base snapshot does not match the manager snapshot.",
            )
        )
    return diagnostics


def _maybe_synthesize_failure(
    diagnostics: list[Diagnostic],
    *,
    result: ApplyResult,
    code: str,
    address: str,
    message: str,
) -> None:
    if not result.success and not _has_error_diagnostic(result.diagnostics):
        diagnostics.append(_failure_diagnostic(code, address, message))


def _rollback_services(
    snapshot: RuntimeSnapshot,
    services: list[tuple[str, object]],
) -> ApplyResult:
    working_snapshot = snapshot
    diagnostics: list[Diagnostic] = []
    changed_addresses: list[str] = []
    success = True

    for address, service in services:
        stop_result = _call_backend_apply(
            service.stop,
            working_snapshot,
            address=address,
            snapshot=working_snapshot,
        )
        diagnostics.extend(stop_result.diagnostics)
        changed_addresses.extend(stop_result.changed_addresses)
        working_snapshot = stop_result.snapshot
        if not stop_result.success:
            success = False
            _maybe_synthesize_failure(
                diagnostics,
                result=stop_result,
                code="runtime.apply-rollback-failed",
                address=address,
                message=f"Rollback failed while stopping '{address}'.",
            )

    return ApplyResult(
        success=success,
        snapshot=working_snapshot,
        diagnostics=diagnostics,
        changed_addresses=changed_addresses,
    )


class RuntimeManager:
    """Plans and executes SDL runtime work against a target."""

    def __init__(
        self,
        target: RuntimeTarget,
        *,
        initial_snapshot: RuntimeSnapshot | None = None,
    ) -> None:
        _validate_runtime_target_shape(
            manifest=target.manifest,
            provisioner=target.provisioner,
            orchestrator=target.orchestrator,
            evaluator=target.evaluator,
            participant_runtime=target.participant_runtime,
        )
        self._target = target
        self._snapshot = initial_snapshot if initial_snapshot is not None else RuntimeSnapshot()

    @property
    def snapshot(self) -> RuntimeSnapshot:
        return self._snapshot

    def plan(
        self,
        scenario: object,
        snapshot: RuntimeSnapshot | None = None,
        *,
        parameters: dict[str, object] | None = None,
        profile: str | None = None,
    ) -> ExecutionPlan:
        model = compile_scenario_runtime_model(scenario, parameters=parameters, profile=profile)
        effective_snapshot = snapshot if snapshot is not None else self._snapshot
        return plan(
            model,
            self._target.manifest,
            effective_snapshot,
            target_name=self._target.name,
        )

    def apply(self, execution_plan: ExecutionPlan) -> ApplyResult:
        diagnostics: list[Diagnostic] = list(execution_plan.diagnostics)
        changed_addresses: list[str] = []

        precondition_failure = self._apply_precondition_failure(execution_plan, diagnostics)
        if precondition_failure is not None:
            return precondition_failure

        evaluation_needed = bool(execution_plan.evaluation.actionable_operations)
        orchestration_needed = bool(execution_plan.orchestration.actionable_operations)
        working_snapshot = execution_plan.base_snapshot
        provision_result = _call_backend_apply(
            self._target.provisioner.apply,
            execution_plan.provisioning,
            working_snapshot,
            address="runtime.apply.provisioning",
            snapshot=working_snapshot,
        )
        diagnostics.extend(provision_result.diagnostics)
        changed_addresses.extend(provision_result.changed_addresses)
        working_snapshot = provision_result.snapshot
        if not provision_result.success:
            _maybe_synthesize_failure(
                diagnostics,
                result=provision_result,
                code=_APPLY_PHASE_FAILED,
                address="runtime.apply.provisioning",
                message="Provisioning apply failed.",
            )
            self._snapshot = working_snapshot
            return ApplyResult(
                success=False,
                snapshot=self._snapshot,
                diagnostics=diagnostics,
                changed_addresses=changed_addresses,
            )

        started_evaluator = False
        if evaluation_needed and self._target.evaluator is not None:
            evaluation_result = _call_backend_apply(
                self._target.evaluator.start,
                execution_plan.evaluation,
                working_snapshot,
                address=_APPLY_EVALUATOR_ADDRESS,
                snapshot=working_snapshot,
            )
            diagnostics.extend(evaluation_result.diagnostics)
            changed_addresses.extend(evaluation_result.changed_addresses)
            working_snapshot = evaluation_result.snapshot
            if evaluation_result.success:
                started_evaluator = True
            else:
                _maybe_synthesize_failure(
                    diagnostics,
                    result=evaluation_result,
                    code=_APPLY_PHASE_FAILED,
                    address=_APPLY_EVALUATOR_ADDRESS,
                    message="Evaluator failed to start.",
                )
                rollback_result = _rollback_services(
                    working_snapshot,
                    [("runtime.rollback.evaluator", self._target.evaluator)],
                )
                diagnostics.extend(rollback_result.diagnostics)
                changed_addresses.extend(rollback_result.changed_addresses)
                working_snapshot = rollback_result.snapshot
                self._snapshot = working_snapshot
                return ApplyResult(
                    success=False,
                    snapshot=self._snapshot,
                    diagnostics=diagnostics,
                    changed_addresses=changed_addresses,
                )

        if orchestration_needed and self._target.orchestrator is not None:
            orchestration_result = _call_backend_apply(
                self._target.orchestrator.start,
                execution_plan.orchestration,
                working_snapshot,
                address=_APPLY_ORCHESTRATOR_ADDRESS,
                snapshot=working_snapshot,
            )
            diagnostics.extend(orchestration_result.diagnostics)
            changed_addresses.extend(orchestration_result.changed_addresses)
            working_snapshot = orchestration_result.snapshot
            if not orchestration_result.success:
                _maybe_synthesize_failure(
                    diagnostics,
                    result=orchestration_result,
                    code=_APPLY_PHASE_FAILED,
                    address=_APPLY_ORCHESTRATOR_ADDRESS,
                    message="Orchestrator failed to start.",
                )
                rollback_services = [
                    ("runtime.rollback.orchestrator", self._target.orchestrator),
                ]
                if started_evaluator and self._target.evaluator is not None:
                    rollback_services.append(("runtime.rollback.evaluator", self._target.evaluator))
                rollback_result = _rollback_services(working_snapshot, rollback_services)
                diagnostics.extend(rollback_result.diagnostics)
                changed_addresses.extend(rollback_result.changed_addresses)
                working_snapshot = rollback_result.snapshot
                self._snapshot = working_snapshot
                return ApplyResult(
                    success=False,
                    snapshot=self._snapshot,
                    diagnostics=diagnostics,
                    changed_addresses=changed_addresses,
                )

        self._snapshot = working_snapshot
        return ApplyResult(
            success=not _has_error_diagnostic(diagnostics),
            snapshot=self._snapshot,
            diagnostics=diagnostics,
            changed_addresses=changed_addresses,
        )

    def _apply_precondition_failure(
        self,
        execution_plan: ExecutionPlan,
        diagnostics: list[Diagnostic],
    ) -> ApplyResult | None:
        provenance_diagnostics = _provenance_diagnostics(
            execution_plan,
            self._target,
            self._snapshot,
        )
        diagnostics.extend(provenance_diagnostics)
        if provenance_diagnostics:
            return ApplyResult(
                success=False,
                snapshot=self._snapshot,
                diagnostics=diagnostics,
            )

        if not execution_plan.is_valid:
            return ApplyResult(
                success=False,
                snapshot=self._snapshot,
                diagnostics=diagnostics,
            )

        evaluation_needed = bool(execution_plan.evaluation.actionable_operations)
        if evaluation_needed and self._target.evaluator is None:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.apply-missing-evaluator",
                    _APPLY_EVALUATOR_ADDRESS,
                    "Execution plan requires an evaluator, but the target does not provide one.",
                )
            )
            return ApplyResult(
                success=False,
                snapshot=self._snapshot,
                diagnostics=diagnostics,
            )

        orchestration_needed = bool(execution_plan.orchestration.actionable_operations)
        if orchestration_needed and self._target.orchestrator is None:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.apply-missing-orchestrator",
                    _APPLY_ORCHESTRATOR_ADDRESS,
                    "Execution plan requires an orchestrator, but the target does not provide one.",
                )
            )
            return ApplyResult(
                success=False,
                snapshot=self._snapshot,
                diagnostics=diagnostics,
            )

        validation = _call_backend_diagnostics(
            self._target.provisioner.validate,
            execution_plan.provisioning,
            address="runtime.apply.provisioning.validate",
        )
        diagnostics.extend(validation)
        if _has_error_diagnostic(validation):
            return ApplyResult(
                success=False,
                snapshot=self._snapshot,
                diagnostics=diagnostics,
            )
        return None

    def status(self) -> dict[str, object]:
        info: dict[str, object] = {
            "backend": self._target.name,
            "resources": len(self._snapshot.entries),
            "domains": {
                RuntimeDomain.PROVISIONING.value: len(self._snapshot.for_domain(RuntimeDomain.PROVISIONING)),
                RuntimeDomain.ORCHESTRATION.value: len(self._snapshot.for_domain(RuntimeDomain.ORCHESTRATION)),
                RuntimeDomain.EVALUATION.value: len(self._snapshot.for_domain(RuntimeDomain.EVALUATION)),
            },
        }
        if self._target.orchestrator is not None:
            info["orchestrator"] = self._target.orchestrator.status()
            info["orchestration_results"] = self._target.orchestrator.results()
            info["orchestration_history"] = self._target.orchestrator.history()
        if self._target.evaluator is not None:
            info["evaluator"] = self._target.evaluator.status()
            info["evaluation_results"] = self._target.evaluator.results()
            info["evaluation_history"] = self._target.evaluator.history()
        return info

    def destroy(self) -> ApplyResult:
        diagnostics: list[Diagnostic] = []
        changed_addresses: list[str] = []
        working_snapshot = self._snapshot
        phases_succeeded = True

        if self._target.orchestrator is not None:
            stop_result = _call_backend_apply(
                self._target.orchestrator.stop,
                working_snapshot,
                address="runtime.destroy.orchestrator",
                snapshot=working_snapshot,
            )
            diagnostics.extend(stop_result.diagnostics)
            changed_addresses.extend(stop_result.changed_addresses)
            working_snapshot = stop_result.snapshot
            if not stop_result.success:
                phases_succeeded = False
                _maybe_synthesize_failure(
                    diagnostics,
                    result=stop_result,
                    code=_DESTROY_PHASE_FAILED,
                    address="runtime.destroy.orchestrator",
                    message="Orchestrator stop failed.",
                )

        if self._target.evaluator is not None:
            stop_result = _call_backend_apply(
                self._target.evaluator.stop,
                working_snapshot,
                address="runtime.destroy.evaluator",
                snapshot=working_snapshot,
            )
            diagnostics.extend(stop_result.diagnostics)
            changed_addresses.extend(stop_result.changed_addresses)
            working_snapshot = stop_result.snapshot
            if not stop_result.success:
                phases_succeeded = False
                _maybe_synthesize_failure(
                    diagnostics,
                    result=stop_result,
                    code=_DESTROY_PHASE_FAILED,
                    address="runtime.destroy.evaluator",
                    message="Evaluator stop failed.",
                )

        provisioning_entries = working_snapshot.for_domain(RuntimeDomain.PROVISIONING)
        delete_plan = ProvisioningPlan(
            resources={},
            operations=[
                ProvisionOp(
                    action=ChangeAction.DELETE,
                    address=address,
                    resource_type=provisioning_entries[address].resource_type,
                    payload=provisioning_entries[address].payload,
                    ordering_dependencies=(provisioning_entries[address].ordering_dependencies),
                    refresh_dependencies=(provisioning_entries[address].refresh_dependencies),
                )
                for address in _delete_order(provisioning_entries)
            ],
        )
        provision_result = _call_backend_apply(
            self._target.provisioner.apply,
            delete_plan,
            working_snapshot,
            address="runtime.destroy.provisioning",
            snapshot=working_snapshot,
        )
        diagnostics.extend(provision_result.diagnostics)
        changed_addresses.extend(provision_result.changed_addresses)
        working_snapshot = provision_result.snapshot
        if not provision_result.success:
            phases_succeeded = False
            _maybe_synthesize_failure(
                diagnostics,
                result=provision_result,
                code=_DESTROY_PHASE_FAILED,
                address="runtime.destroy.provisioning",
                message="Provisioning destroy failed.",
            )

        self._snapshot = working_snapshot
        return ApplyResult(
            success=phases_succeeded and not _has_error_diagnostic(diagnostics),
            snapshot=self._snapshot,
            diagnostics=diagnostics,
            changed_addresses=changed_addresses,
        )
