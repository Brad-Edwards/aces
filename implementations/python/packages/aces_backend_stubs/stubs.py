"""Stub runtime backends for compiler/planner testing."""

from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

from aces_backend_protocols.capabilities import (
    PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS,
    PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE,
    PARTICIPANT_RUNTIME_ROLE_SCOPE,
    BackendCapabilitySet,
    BackendManifest,
    EvaluatorCapabilities,
    ObservationCapabilities,
    OrchestratorCapabilities,
    ParticipantRuntimeCapabilities,
    ProvisionerCapabilities,
    WorkflowFeature,
    WorkflowStatePredicateFeature,
)
from aces_backend_protocols.participant_runtime_base import BaseParticipantRuntime
from aces_contracts.apparatus import ConceptBinding, RealizationSupportDeclaration
from aces_contracts.diagnostics import Diagnostic
from aces_contracts.manifest_authority import BACKEND_SUPPORTED_CONTRACT_IDS
from aces_contracts.planning import ChangeAction, EvaluationPlan, OrchestrationPlan, ProvisioningPlan, RuntimeDomain
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot, SnapshotEntry
from aces_contracts.versions import EVALUATION_STATE_SCHEMA_VERSION
from aces_contracts.vocabulary import RealizationSupportMode
from aces_runtime.registry import RuntimeTarget, RuntimeTargetComponents

REFERENCE_BACKEND_SUPPORTED_CONTRACT_VERSIONS = tuple(
    filter(lambda contract_id: contract_id != "realization-envelope-v1", BACKEND_SUPPORTED_CONTRACT_IDS)
)
REFERENCE_PARTICIPANT_ROLES = frozenset(
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_ROLE_SCOPE]
)
REFERENCE_PARTICIPANT_BEHAVIOR_FEATURES = frozenset(
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_BEHAVIOR_FEATURE_SCOPE]
)
REFERENCE_PARTICIPANT_INTERACTION_FEATURES = frozenset(
    PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS[PARTICIPANT_RUNTIME_INTERACTION_FEATURE_SCOPE]
)


def _current_backend_version() -> str:
    try:
        return distribution_version("aces-sdl")
    except PackageNotFoundError:
        return "0.0.0+unknown"


def create_stub_manifest(
    *,
    with_participant_runtime: bool = True,
    with_observation: bool = True,
    **config,
) -> BackendManifest:
    """Return the fully capable stub manifest.

    ``with_participant_runtime=False`` omits the participant runtime
    capability block so legacy tests that construct targets with only
    provisioner/orchestrator/evaluator components still satisfy
    ``registry.target-shape-mismatch`` validation. Production callers
    should leave this at its default.
    """

    del config
    supported_contract_versions = set(REFERENCE_BACKEND_SUPPORTED_CONTRACT_VERSIONS)
    if not with_participant_runtime:
        supported_contract_versions.discard("participant-episode-state-envelope-v1")
        supported_contract_versions.discard("participant-episode-history-event-stream-v1")
        supported_contract_versions.discard("participant-behavior-history-event-stream-v1")
        supported_contract_versions.discard("participant-lifecycle-event-v1")
        supported_contract_versions.discard("participant-observation-envelope-v1")
        supported_contract_versions.discard("participant-shared-state-record-v1")
        supported_contract_versions.discard("participant-joint-action-record-v1")
        supported_contract_versions.discard("participant-time-management-context-v1")
        supported_contract_versions.discard("participant-outcome-report-v1")
    if not with_observation:
        supported_contract_versions.discard("experiment-capture-spec-v1")
        supported_contract_versions.discard("experiment-evidence-record-v1")
        supported_contract_versions.discard("experiment-derived-measure-v1")
        supported_contract_versions.discard("experiment-run-v1")
    concept_bindings = (
        ConceptBinding(scope="capabilities.provisioner.supported_node_types", family="assets"),
        ConceptBinding(scope="capabilities.provisioner.supported_os_families", family="assets"),
        ConceptBinding(scope="capabilities.provisioner.supported_content_types", family="tools-and-artifacts"),
        ConceptBinding(scope="capabilities.provisioner.supported_account_features", family="identities"),
        ConceptBinding(scope="capabilities.orchestrator.supported_sections", family="actions-and-events"),
        ConceptBinding(scope="capabilities.evaluator.supported_sections", family="observables"),
    )
    if with_participant_runtime:
        concept_bindings += (
            ConceptBinding(
                scope="capabilities.participant_runtime.supported_participant_roles",
                family="identities",
            ),
            ConceptBinding(
                scope="capabilities.participant_runtime.supported_behavior_features",
                family="actions-and-events",
            ),
            ConceptBinding(
                scope="capabilities.participant_runtime.supported_interaction_features",
                family="relationships",
            ),
        )
    if with_observation:
        concept_bindings += (
            ConceptBinding(
                scope="capabilities.observation.supported_capture_kinds",
                family="provenance-and-evidence",
            ),
            ConceptBinding(
                scope="capabilities.observation.supported_channel_kinds",
                family="apparatus-declarations",
            ),
            ConceptBinding(
                scope="capabilities.observation.supported_sealing_modes",
                family="provenance-and-evidence",
            ),
        )
    return BackendManifest(
        name="stub",
        version=_current_backend_version(),
        supported_contract_versions=frozenset(supported_contract_versions),
        compatible_processors=frozenset({"aces-reference-processor"}),
        concept_bindings=concept_bindings,
        realization_support=(
            RealizationSupportDeclaration(
                domain="runtime-realization",
                support_mode=RealizationSupportMode.CONSTRAINED,
                supported_constraint_kinds=frozenset(
                    {
                        "node-type",
                        "os-family",
                        "content-type",
                        "account-feature",
                        "workflow-feature",
                        "workflow-state-predicate",
                    }
                ),
                supported_exact_requirement_kinds=frozenset({"declared-capability-match"}),
                disclosure_kinds=frozenset(
                    {
                        "backend-manifest-v2",
                        "runtime-snapshot-v1",
                        "operation-status-v1",
                    }
                ),
            ),
        ),
        capabilities=BackendCapabilitySet(
            provisioner=ProvisionerCapabilities(
                name="stub-provisioner",
                supported_node_types=frozenset({"vm", "switch"}),
                supported_os_families=frozenset({"linux", "windows", "macos", "freebsd", "other"}),
                supported_content_types=frozenset({"file", "dataset", "directory"}),
                supported_account_features=frozenset(
                    {"groups", "mail", "spn", "shell", "home", "disabled", "auth_method"}
                ),
                max_total_nodes=None,
                supports_acls=True,
                supports_accounts=True,
            ),
            orchestrator=OrchestratorCapabilities(
                name="stub-orchestrator",
                supported_sections=frozenset({"injects", "events", "scripts", "stories", "workflows"}),
                supports_workflows=True,
                supports_condition_refs=True,
                supports_inject_bindings=True,
                supported_workflow_features=frozenset(
                    {
                        WorkflowFeature.DECISION,
                        WorkflowFeature.SWITCH,
                        WorkflowFeature.CALL,
                        WorkflowFeature.PARALLEL_BARRIER,
                        WorkflowFeature.RETRY,
                        WorkflowFeature.FAILURE_TRANSITIONS,
                        WorkflowFeature.CANCELLATION,
                        WorkflowFeature.TIMEOUTS,
                        WorkflowFeature.COMPENSATION,
                    }
                ),
                supported_workflow_state_predicates=frozenset(
                    {
                        WorkflowStatePredicateFeature.OUTCOME_MATCHING,
                        WorkflowStatePredicateFeature.ATTEMPT_COUNTS,
                    }
                ),
            ),
            evaluator=EvaluatorCapabilities(
                name="stub-evaluator",
                supported_sections=frozenset({"conditions", "objectives"}),
                supports_scoring=True,
                supports_objectives=True,
            ),
            participant_runtime=(
                ParticipantRuntimeCapabilities(
                    name="stub-participant-runtime",
                    supported_participant_roles=REFERENCE_PARTICIPANT_ROLES,
                    supported_behavior_features=REFERENCE_PARTICIPANT_BEHAVIOR_FEATURES,
                    supported_interaction_features=REFERENCE_PARTICIPANT_INTERACTION_FEATURES,
                )
                if with_participant_runtime
                else None
            ),
            observation=(
                ObservationCapabilities(
                    name="stub-observation",
                    supported_capture_kinds=frozenset({"artifact", "log", "observation", "telemetry", "trace"}),
                    supported_channel_kinds=frozenset(
                        {
                            "backend-log",
                            "evaluation-history",
                            "file-artifact",
                            "participant-observation",
                            "runtime-snapshot",
                            "workflow-history",
                        }
                    ),
                    supported_evidence_contracts=frozenset(
                        {
                            "experiment-capture-spec-v1",
                            "experiment-evidence-record-v1",
                            "experiment-derived-measure-v1",
                            "experiment-run-v1",
                        }
                    ),
                    supported_media_types=frozenset({"application/json", "text/plain"}),
                    supported_sealing_modes=frozenset({"digest", "immutable-store"}),
                    supports_redaction=True,
                    supports_loss_disclosure=True,
                    supports_chain_of_custody=False,
                )
                if with_observation
                else None
            ),
        ),
    )


class StubProvisioner:
    """In-memory provisioner."""

    def validate(self, plan: ProvisioningPlan) -> list[Diagnostic]:
        return []

    def apply(
        self,
        plan: ProvisioningPlan,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult:
        entries = dict(snapshot.entries)
        changed_addresses: list[str] = []
        for op in plan.operations:
            if op.action == ChangeAction.DELETE:
                entries.pop(op.address, None)
                changed_addresses.append(op.address)
                continue
            status = "unchanged" if op.action == ChangeAction.UNCHANGED else "applied"
            entries[op.address] = SnapshotEntry(
                address=op.address,
                domain=RuntimeDomain.PROVISIONING,
                resource_type=op.resource_type,
                payload=op.payload,
                ordering_dependencies=op.ordering_dependencies,
                refresh_dependencies=op.refresh_dependencies,
                status=status,
            )
            if op.action != ChangeAction.UNCHANGED:
                changed_addresses.append(op.address)

        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(entries),
            changed_addresses=changed_addresses,
        )


class StubOrchestrator:
    """In-memory orchestrator."""

    def __init__(self) -> None:
        self._running = False
        self._startup_order: list[str] = []
        self._results: dict[str, dict[str, object]] = {}
        self._history: dict[str, list[dict[str, object]]] = {}

    def start(
        self,
        plan: OrchestrationPlan,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult:
        entries = dict(snapshot.entries)
        results = dict(snapshot.orchestration_results)
        history = {
            workflow_address: list(events) for workflow_address, events in snapshot.orchestration_history.items()
        }
        changed_addresses: list[str] = []
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        for op in plan.operations:
            if op.action == ChangeAction.DELETE:
                entries.pop(op.address, None)
                results.pop(op.address, None)
                history.pop(op.address, None)
                changed_addresses.append(op.address)
                continue
            status = "queued" if op.resource_type in {"event", "script", "story", "workflow"} else "bound"
            entries[op.address] = SnapshotEntry(
                address=op.address,
                domain=RuntimeDomain.ORCHESTRATION,
                resource_type=op.resource_type,
                payload=op.payload,
                ordering_dependencies=op.ordering_dependencies,
                refresh_dependencies=op.refresh_dependencies,
                status=status,
            )
            if op.resource_type == "workflow":
                result_contract = op.payload.get("result_contract", {})
                observable_steps = result_contract.get("observable_steps", {})
                observable_steps = {
                    step_name: {
                        "lifecycle": "pending",
                        "outcome": None,
                        "attempts": 0,
                    }
                    for step_name, step_payload in observable_steps.items()
                    if isinstance(step_payload, dict)
                }
                results[op.address] = {
                    "state_schema_version": result_contract.get(
                        "state_schema_version",
                        op.payload.get("state_schema_version", "workflow-step-state/v1"),
                    ),
                    "workflow_status": "running",
                    "run_id": f"{op.address}-run",
                    "started_at": now,
                    "updated_at": now,
                    "terminal_reason": None,
                    "compensation_status": "not_required",
                    "compensation_started_at": None,
                    "compensation_updated_at": None,
                    "compensation_failures": [],
                    "steps": observable_steps,
                }
                history[op.address] = [
                    {
                        "event_type": "workflow_started",
                        "timestamp": now,
                        "step_name": op.payload.get("execution_contract", {}).get("start_step"),
                        "branch_name": None,
                        "join_step": None,
                        "outcome": None,
                        "details": {},
                    }
                ]
            if op.action != ChangeAction.UNCHANGED:
                changed_addresses.append(op.address)
        self._running = bool(plan.resources)
        self._startup_order = list(plan.startup_order)
        self._results = results
        self._history = history
        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(
                entries,
                orchestration_results=results,
                orchestration_history=history,
            ),
            changed_addresses=changed_addresses,
        )

    def status(self) -> dict[str, object]:
        return {
            "running": self._running,
            "startup_order": list(self._startup_order),
            "results": len(self._results),
        }

    def results(self) -> dict[str, dict[str, object]]:
        return dict(self._results)

    def history(self) -> dict[str, list[dict[str, object]]]:
        return {workflow_address: list(events) for workflow_address, events in self._history.items()}

    def stop(self, snapshot: RuntimeSnapshot) -> ApplyResult:
        entries = {
            address: entry for address, entry in snapshot.entries.items() if entry.domain != RuntimeDomain.ORCHESTRATION
        }
        removed = [
            address for address, entry in snapshot.entries.items() if entry.domain == RuntimeDomain.ORCHESTRATION
        ]
        self._running = False
        self._startup_order = []
        self._results = {}
        self._history = {}
        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(
                entries,
                orchestration_results={},
                orchestration_history={},
            ),
            changed_addresses=removed,
        )


class StubEvaluator:
    """In-memory evaluator."""

    def __init__(self) -> None:
        self._running = False
        self._startup_order: list[str] = []
        self._results: dict[str, dict[str, object]] = {}
        self._history: dict[str, list[dict[str, object]]] = {}

    def start(
        self,
        plan: EvaluationPlan,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult:
        entries = dict(snapshot.entries)
        changed_addresses: list[str] = []
        results = dict(snapshot.evaluation_results)
        history = {address: list(events) for address, events in snapshot.evaluation_history.items()}
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        for op in plan.operations:
            if op.action == ChangeAction.DELETE:
                entries.pop(op.address, None)
                results.pop(op.address, None)
                history.pop(op.address, None)
                changed_addresses.append(op.address)
                continue
            entries[op.address] = SnapshotEntry(
                address=op.address,
                domain=RuntimeDomain.EVALUATION,
                resource_type=op.resource_type,
                payload=op.payload,
                ordering_dependencies=op.ordering_dependencies,
                refresh_dependencies=op.refresh_dependencies,
                status="evaluating",
            )
            result_contract = op.payload.get("result_contract", {})
            resource_type = str(result_contract.get("resource_type", op.resource_type))
            result_payload: dict[str, object] = {
                "state_schema_version": result_contract.get(
                    "state_schema_version",
                    EVALUATION_STATE_SCHEMA_VERSION,
                ),
                "resource_type": resource_type,
                "run_id": "evaluation-run",
                "status": "ready",
                "observed_at": now,
                "updated_at": now,
                "detail": f"stub result for {op.address}",
                "evidence_refs": [],
            }
            if result_contract.get("supports_score"):
                fixed_max_score = result_contract.get("fixed_max_score")
                result_payload["score"] = fixed_max_score if fixed_max_score is not None else 100
                result_payload["max_score"] = fixed_max_score if fixed_max_score is not None else 100
            if result_contract.get("supports_passed"):
                result_payload["passed"] = True
            results[op.address] = result_payload
            history[op.address] = [
                {
                    "event_type": "evaluation_started",
                    "timestamp": now,
                    "status": "running",
                    "passed": None,
                    "score": None,
                    "max_score": None,
                    "detail": None,
                    "evidence_refs": [],
                    "details": {},
                },
                {
                    "event_type": "evaluation_ready",
                    "timestamp": now,
                    "status": "ready",
                    "passed": result_payload.get("passed"),
                    "score": result_payload.get("score"),
                    "max_score": result_payload.get("max_score"),
                    "detail": result_payload.get("detail"),
                    "evidence_refs": list(result_payload.get("evidence_refs", [])),
                    "details": {},
                },
            ]
            if op.action != ChangeAction.UNCHANGED:
                changed_addresses.append(op.address)
        self._running = bool(plan.resources)
        self._startup_order = list(plan.startup_order)
        self._results = results
        self._history = history
        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(
                entries,
                evaluation_results=results,
                evaluation_history=history,
            ),
            changed_addresses=changed_addresses,
        )

    def status(self) -> dict[str, object]:
        return {
            "running": self._running,
            "startup_order": list(self._startup_order),
            "results": len(self._results),
        }

    def results(self) -> dict[str, dict[str, object]]:
        return dict(self._results)

    def history(self) -> dict[str, list[dict[str, object]]]:
        return {address: list(events) for address, events in self._history.items()}

    def stop(self, snapshot: RuntimeSnapshot) -> ApplyResult:
        entries = {
            address: entry for address, entry in snapshot.entries.items() if entry.domain != RuntimeDomain.EVALUATION
        }
        removed = [address for address, entry in snapshot.entries.items() if entry.domain == RuntimeDomain.EVALUATION]
        self._running = False
        self._startup_order = []
        self._results = {}
        self._history = {}
        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(
                entries,
                evaluation_results={},
                evaluation_history={},
            ),
            changed_addresses=removed,
        )


class StubParticipantRuntime(BaseParticipantRuntime):
    """In-memory participant runtime that drives RUN-311 transitions.

    Delegates the full episode lifecycle to ``BaseParticipantRuntime``; the
    stub backend injects no domain side-effects.
    """


def create_stub_components(
    *,
    manifest: BackendManifest,
    **config,
) -> RuntimeTargetComponents:
    """Factory for stub runtime components."""

    del config
    return RuntimeTargetComponents(
        provisioner=StubProvisioner(),
        orchestrator=StubOrchestrator(),
        evaluator=StubEvaluator(),
        participant_runtime=StubParticipantRuntime() if manifest.has_participant_runtime else None,
    )


def create_stub_target(**config) -> RuntimeTarget:
    """Convenience helper returning the fully configured stub target."""

    manifest = create_stub_manifest(**config)
    components = create_stub_components(manifest=manifest, **config)
    return RuntimeTarget(
        name="stub",
        manifest=manifest,
        provisioner=components.provisioner,
        orchestrator=components.orchestrator,
        evaluator=components.evaluator,
        participant_runtime=components.participant_runtime,
    )
