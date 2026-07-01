"""Runtime data models for the SDL-native execution layer.

The runtime is split into three domains:

- provisioning: desired deployed state
- orchestration: resolved exercise control graph
- evaluation: resolved monitoring/scoring graph

The compiler produces a ``RuntimeModel`` with reusable templates separated
from bound runtime instances. The planner reconciles those instances against
the current ``RuntimeSnapshot`` and emits a composite ``ExecutionPlan``.
"""

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from aces_backend_protocols.capabilities import (
    BackendManifest,
    WorkflowFeature,
    WorkflowStatePredicateFeature,
)
from aces_contracts.diagnostics import Diagnostic as Diagnostic
from aces_contracts.diagnostics import Severity as Severity
from aces_contracts.evaluation import (
    EvaluationExecutionContract as EvaluationExecutionContract,
)
from aces_contracts.evaluation import (
    EvaluationExecutionState as EvaluationExecutionState,
)
from aces_contracts.evaluation import (
    EvaluationHistoryEvent as EvaluationHistoryEvent,
)
from aces_contracts.evaluation import (
    EvaluationHistoryEventType as EvaluationHistoryEventType,
)
from aces_contracts.evaluation import (
    EvaluationResultContract as EvaluationResultContract,
)
from aces_contracts.evaluation import (
    EvaluationResultStatus as EvaluationResultStatus,
)
from aces_contracts.evaluation import (
    validate_evaluation_result as validate_evaluation_result,
)
from aces_contracts.participant_behavior import (
    ParticipantActionPreconditionStatus as ParticipantActionPreconditionStatus,
)
from aces_contracts.participant_behavior import (
    ParticipantActionResultStatus as ParticipantActionResultStatus,
)
from aces_contracts.participant_behavior import (
    ParticipantAdmissionDisposition as ParticipantAdmissionDisposition,
)
from aces_contracts.participant_behavior import (
    ParticipantBehaviorHistoryEventType as ParticipantBehaviorHistoryEventType,
)
from aces_contracts.participant_behavior import (
    ParticipantLifecycleOperationState as ParticipantLifecycleOperationState,
)
from aces_contracts.participant_behavior import (
    ParticipantObservationStatus as ParticipantObservationStatus,
)
from aces_contracts.participant_behavior import (
    ParticipantPhaseRealization as ParticipantPhaseRealization,
)
from aces_contracts.participant_behavior import (
    ParticipantRuntimeLifecyclePhase as ParticipantRuntimeLifecyclePhase,
)
from aces_contracts.participant_behavior import (
    participant_lifecycle_field_violation_messages as participant_lifecycle_field_violation_messages,
)
from aces_contracts.participant_episode import (
    PARTICIPANT_EPISODE_CONTROL_EVENTS,
    PARTICIPANT_EPISODE_TERMINAL_EVENTS,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeControlAction as ParticipantEpisodeControlAction,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeExecutionState as ParticipantEpisodeExecutionState,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeHistoryEvent as ParticipantEpisodeHistoryEvent,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeHistoryEventType as ParticipantEpisodeHistoryEventType,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeInitializeRequest as ParticipantEpisodeInitializeRequest,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeResetRequest as ParticipantEpisodeResetRequest,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeRestartRequest as ParticipantEpisodeRestartRequest,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeStatus as ParticipantEpisodeStatus,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeTerminalReason as ParticipantEpisodeTerminalReason,
)
from aces_contracts.participant_episode import (
    ParticipantEpisodeTerminateRequest as ParticipantEpisodeTerminateRequest,
)
from aces_contracts.participant_episode import (
    iter_participant_episode_snapshot_violations as iter_participant_episode_snapshot_violations,
)
from aces_contracts.planning import (
    ChangeAction as ChangeAction,
)
from aces_contracts.planning import (
    EvaluationOp as EvaluationOp,
)
from aces_contracts.planning import (
    EvaluationPlan as EvaluationPlan,
)
from aces_contracts.planning import (
    OrchestrationOp as OrchestrationOp,
)
from aces_contracts.planning import (
    OrchestrationPlan as OrchestrationPlan,
)
from aces_contracts.planning import (
    PlannedResource as PlannedResource,
)
from aces_contracts.planning import (
    PlanOperation as PlanOperation,
)
from aces_contracts.planning import (
    ProvisioningPlan as ProvisioningPlan,
)
from aces_contracts.planning import (
    ProvisionOp as ProvisionOp,
)
from aces_contracts.planning import (
    RuntimeDomain as RuntimeDomain,
)
from aces_contracts.runtime_state import (
    ApplyResult as ApplyResult,
)
from aces_contracts.runtime_state import (
    OperationReceipt as OperationReceipt,
)
from aces_contracts.runtime_state import (
    OperationState as OperationState,
)
from aces_contracts.runtime_state import (
    OperationStatus as OperationStatus,
)
from aces_contracts.runtime_state import (
    RealizationProvenanceEntry as RealizationProvenanceEntry,
)
from aces_contracts.runtime_state import (
    RuntimeSnapshot as RuntimeSnapshot,
)
from aces_contracts.runtime_state import (
    RuntimeSnapshotEnvelope as RuntimeSnapshotEnvelope,
)
from aces_contracts.runtime_state import (
    SnapshotEntry as SnapshotEntry,
)
from aces_contracts.versions import (
    EVALUATION_STATE_SCHEMA_VERSION as EVALUATION_STATE_SCHEMA_VERSION,
)
from aces_contracts.versions import (
    OPERATION_SCHEMA_VERSION as OPERATION_SCHEMA_VERSION,
)
from aces_contracts.versions import (
    PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION as PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION,
)
from aces_contracts.versions import (
    RUNTIME_SNAPSHOT_SCHEMA_VERSION as RUNTIME_SNAPSHOT_SCHEMA_VERSION,
)
from aces_contracts.versions import (
    WORKFLOW_STATE_SCHEMA_VERSION as WORKFLOW_STATE_SCHEMA_VERSION,
)
from aces_contracts.workflow import (
    WorkflowCancellationRequest as WorkflowCancellationRequest,
)
from aces_contracts.workflow import (
    WorkflowCompensationStatus as WorkflowCompensationStatus,
)
from aces_contracts.workflow import (
    WorkflowExecutionContract as WorkflowExecutionContract,
)
from aces_contracts.workflow import (
    WorkflowExecutionState as WorkflowExecutionState,
)
from aces_contracts.workflow import (
    WorkflowHistoryEvent as WorkflowHistoryEvent,
)
from aces_contracts.workflow import (
    WorkflowHistoryEventType as WorkflowHistoryEventType,
)
from aces_contracts.workflow import (
    WorkflowResultContract as WorkflowResultContract,
)
from aces_contracts.workflow import (
    WorkflowStatus as WorkflowStatus,
)
from aces_contracts.workflow import (
    WorkflowStepExecutionState as WorkflowStepExecutionState,
)
from aces_contracts.workflow import (
    WorkflowStepLifecycle as WorkflowStepLifecycle,
)
from aces_contracts.workflow import (
    WorkflowStepOutcome as WorkflowStepOutcome,
)
from aces_contracts.workflow import (
    validate_workflow_step_result_contract as validate_workflow_step_result_contract,
)
from aces_sdl.participant_attribution_semantics import (
    OUTCOME_ATTRIBUTION_CANDIDATE_KINDS,
    STRONG_ATTRIBUTION_SUPPORT_CLASSES,
    ParticipantAttributionCandidateKind,
    ParticipantAttributionOrderingBasisKind,
    ParticipantAttributionSupportClass,
)
from aces_sdl.participant_behavior import (
    ParticipantEffectClass,
    ParticipantFailureClass,
    ParticipantInteractionClass,
    ParticipantPreconditionClass,
)
from aces_sdl.participant_outcome_semantics import (
    PROVENANCE_REQUIRED_OUTCOME_SOURCE_LAYERS,
    OutcomeInterpretationSourceLayer,
    OutcomeInterpretationTargetLayer,
)
from aces_sdl.participant_temporal_semantics import (
    ParticipantTemporalEventPoint,
    ParticipantTemporalState,
    ParticipantTimeDomain,
)
from aces_sdl.semantics.workflow import (
    WorkflowStepSemanticContract,
)

from aces_processor.semantics.realization import (
    CompiledRealizationRequirement as CompiledRealizationRequirement,
)

_PARTICIPANT_ACTION_CONTRACT_PREFIX = "participant.action-contract."
_PARTICIPANT_OBSERVATION_BOUNDARY_PREFIX = "participant.observation-boundary."
_PARTICIPANT_OUTCOME_RULE_PREFIX = "participant.outcome-interpretation-rule."
_PARTICIPANT_BEHAVIOR_HISTORY_KEY = "runtime.snapshot.participant-behavior-history"
_PARTICIPANT_EPISODE_CONTROL_EVENTS = PARTICIPANT_EPISODE_CONTROL_EVENTS
_PARTICIPANT_EPISODE_TERMINAL_EVENTS = PARTICIPANT_EPISODE_TERMINAL_EVENTS


@dataclass(frozen=True)
class RuntimeTemplate:
    """Reusable SDL definition preserved in compiled form."""

    address: str
    name: str
    spec: dict[str, Any]


@dataclass(frozen=True)
class ResolvedResource:
    """Base class for bound runtime resources."""

    address: str
    name: str
    spec: dict[str, Any]
    ordering_dependencies: tuple[str, ...] = ()
    refresh_dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class NetworkRuntime(ResolvedResource):
    """Compiled switch/network deployment."""

    node_name: str = ""


@dataclass(frozen=True)
class NodeRuntime(ResolvedResource):
    """Compiled VM deployment."""

    node_name: str = ""
    node_type: str = ""
    os_family: str = ""
    count: int | str | None = None


@dataclass(frozen=True)
class FeatureBinding(ResolvedResource):
    """Feature template bound to a specific node role."""

    node_name: str = ""
    node_address: str = ""
    feature_name: str = ""
    template_address: str = ""
    role_name: str = ""


@dataclass(frozen=True)
class ConditionBinding(ResolvedResource):
    """Condition template bound to a specific node role."""

    node_name: str = ""
    node_address: str = ""
    condition_name: str = ""
    template_address: str = ""
    role_name: str = ""
    result_contract: "EvaluationResultContract" = field(
        default_factory=lambda: EvaluationResultContract(resource_type="condition-binding")
    )
    execution_contract: "EvaluationExecutionContract" = field(
        default_factory=lambda: EvaluationExecutionContract(resource_type="condition-binding")
    )


@dataclass(frozen=True)
class InjectBinding(ResolvedResource):
    """Inject template bound to a specific node role."""

    node_name: str = ""
    node_address: str = ""
    inject_name: str = ""
    template_address: str = ""
    role_name: str = ""


@dataclass(frozen=True)
class InjectRuntime(ResolvedResource):
    """Resolved top-level inject resource."""


@dataclass(frozen=True)
class ContentPlacement(ResolvedResource):
    """Content entry resolved to a concrete target node."""

    content_name: str = ""
    target_node: str = ""
    target_address: str = ""


@dataclass(frozen=True)
class AccountPlacement(ResolvedResource):
    """Account entry resolved to a concrete target node."""

    account_name: str = ""
    node_name: str = ""
    target_address: str = ""


@dataclass(frozen=True)
class ParticipantActionContractRuntime(ResolvedResource):
    """Compiled participant action contract."""

    action_name: str = ""
    semantic_version: str = ""
    lifecycle_state: str = ""
    behavioral_granularity: str = ""
    precondition_classes: tuple[str, ...] = ()
    effect_classes: tuple[str, ...] = ()
    failure_classes: tuple[str, ...] = ()
    backend_failure_mappings: tuple[dict[str, str], ...] = ()
    interaction_classes: tuple[str, ...] = ()
    shared_state_refs: tuple[str, ...] = ()
    temporal_contract_ids: tuple[str, ...] = ()
    temporal_kinds: tuple[str, ...] = ()
    time_domains: tuple[str, ...] = ()
    clock_authorities: tuple[str, ...] = ()
    backend_timing_disclosures: tuple[dict[str, Any], ...] = ()


def map_backend_diagnostic_to_participant_failure(
    diagnostic: Diagnostic | Mapping[str, Any] | str,
    contract: ParticipantActionContractRuntime,
) -> ParticipantFailureClass:
    """Map a backend diagnostic to a portable SEM-211 failure class."""

    if isinstance(diagnostic, Diagnostic):
        code = diagnostic.code
    elif isinstance(diagnostic, Mapping):
        code = str(diagnostic.get("code", ""))
    else:
        code = str(diagnostic)

    for mapping in contract.backend_failure_mappings:
        if mapping.get("backend_error_code") == code:
            return ParticipantFailureClass(str(mapping.get("failure_class", ParticipantFailureClass.UNKNOWN.value)))
    return ParticipantFailureClass.BACKEND_ERROR if code else ParticipantFailureClass.UNKNOWN


def _as_string_set(value: Any) -> set[str]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return set()
    return {str(item) for item in value if isinstance(item, str) and item}


def _contract_sem211_precondition_refs(
    contract: ParticipantActionContractRuntime,
) -> dict[tuple[str, str], dict[str, set[str]]]:
    preconditions = contract.spec.get("preconditions", ())
    if isinstance(preconditions, (str, bytes, Mapping)) or not isinstance(preconditions, Iterable):
        return {}
    refs: dict[tuple[str, str], dict[str, set[str]]] = {}
    for item in preconditions:
        if not isinstance(item, Mapping) or not item.get("precondition_id") or not item.get("precondition_class"):
            continue
        key = (str(item.get("precondition_id", "")), str(item.get("precondition_class", "")))
        refs[key] = {
            "support_refs": _as_string_set(item.get("support_refs", ())),
            "evidence_refs": _as_string_set(item.get("evidence_refs", ())),
        }
    return refs


def _contract_sem211_effect_refs(
    contract: ParticipantActionContractRuntime,
) -> dict[tuple[str, str], dict[str, set[str]]]:
    effects = contract.spec.get("effects", ())
    if isinstance(effects, (str, bytes, Mapping)) or not isinstance(effects, Iterable):
        return {}
    refs: dict[tuple[str, str], dict[str, set[str]]] = {}
    for item in effects:
        if not isinstance(item, Mapping) or not item.get("effect_id") or not item.get("effect_class"):
            continue
        key = (str(item.get("effect_id", "")), str(item.get("effect_class", "")))
        refs[key] = {
            "target_refs": _as_string_set(item.get("target_refs", ())),
            "evidence_refs": _as_string_set(item.get("evidence_refs", ())),
        }
    return refs


def _contract_uses_sem211_action_results(contract: ParticipantActionContractRuntime) -> bool:
    return bool(contract.precondition_classes or contract.effect_classes or contract.failure_classes)


def validate_participant_action_result_contract(
    result: "ParticipantActionResult",
    contract: ParticipantActionContractRuntime,
) -> list[str]:
    """Return SEM-211 contract violations for one typed action result."""

    violations: list[str] = []
    if result.action_contract_address != contract.address:
        violations.append(
            "action_result action_contract_address "
            f"{result.action_contract_address!r} does not match compiled action contract {contract.address!r}"
        )
        return violations

    declared_precondition_classes = set(contract.precondition_classes)
    declared_effect_classes = set(contract.effect_classes)
    declared_failure_classes = set(contract.failure_classes)
    declared_precondition_refs = _contract_sem211_precondition_refs(contract)
    declared_effect_refs = _contract_sem211_effect_refs(contract)
    declared_preconditions = set(declared_precondition_refs)
    declared_effects = set(declared_effect_refs)
    reported_preconditions: set[tuple[str, str]] = set()

    for precondition in result.preconditions:
        precondition_key = (precondition.precondition_id, precondition.precondition_class.value)
        reported_preconditions.add(precondition_key)
        if precondition.precondition_class.value not in declared_precondition_classes:
            violations.append(
                f"action_result precondition {precondition.precondition_id!r} uses undeclared "
                f"precondition_class {precondition.precondition_class.value!r}"
            )
        if declared_preconditions and precondition_key not in declared_preconditions:
            violations.append(
                f"action_result precondition {precondition.precondition_id!r}/"
                f"{precondition.precondition_class.value!r} is not declared by {contract.address}"
            )
        declared_refs = declared_precondition_refs.get(precondition_key)
        if declared_refs is not None:
            undeclared_support_refs = set(precondition.support_refs) - declared_refs["support_refs"]
            undeclared_evidence_refs = set(precondition.evidence_refs) - declared_refs["evidence_refs"]
            for ref in sorted(undeclared_support_refs):
                violations.append(
                    f"action_result precondition {precondition.precondition_id!r} reports undeclared "
                    f"support_ref {ref!r}"
                )
            for ref in sorted(undeclared_evidence_refs):
                violations.append(
                    f"action_result precondition {precondition.precondition_id!r} reports undeclared "
                    f"evidence_ref {ref!r}"
                )
    for precondition_id, precondition_class in sorted(declared_preconditions - reported_preconditions):
        violations.append(
            f"action_result is missing declared precondition {precondition_id!r}/"
            f"{precondition_class!r} for {contract.address}"
        )

    for effect in result.effects:
        effect_key = (effect.effect_id, effect.effect_class.value)
        if effect.effect_class.value not in declared_effect_classes:
            violations.append(
                f"action_result effect {effect.effect_id!r} uses undeclared effect_class {effect.effect_class.value!r}"
            )
        if declared_effects and effect_key not in declared_effects:
            violations.append(
                f"action_result effect {effect.effect_id!r}/"
                f"{effect.effect_class.value!r} is not declared by {contract.address}"
            )
        declared_refs = declared_effect_refs.get(effect_key)
        if declared_refs is not None:
            undeclared_target_refs = set(effect.target_refs) - declared_refs["target_refs"]
            undeclared_evidence_refs = set(effect.evidence_refs) - declared_refs["evidence_refs"]
            for ref in sorted(undeclared_target_refs):
                violations.append(f"action_result effect {effect.effect_id!r} reports undeclared target_ref {ref!r}")
            for ref in sorted(undeclared_evidence_refs):
                violations.append(f"action_result effect {effect.effect_id!r} reports undeclared evidence_ref {ref!r}")

    declared_result_evidence_refs = {
        ref for declared_refs in declared_precondition_refs.values() for ref in declared_refs["evidence_refs"]
    } | {ref for declared_refs in declared_effect_refs.values() for ref in declared_refs["evidence_refs"]}
    reported_result_evidence_refs = {
        ref for precondition in result.preconditions for ref in precondition.evidence_refs
    } | {ref for effect in result.effects for ref in effect.evidence_refs}
    if declared_precondition_refs or declared_effect_refs:
        for ref in sorted(set(result.evidence_refs) - declared_result_evidence_refs):
            violations.append(f"action_result reports undeclared evidence_ref {ref!r}")
        for ref in sorted(set(result.evidence_refs) & declared_result_evidence_refs - reported_result_evidence_refs):
            violations.append(
                f"action_result evidence_ref {ref!r} is not grounded in reported precondition or effect evidence_refs"
            )

    if result.failure_class is not None and result.failure_class.value not in declared_failure_classes:
        violations.append(
            f"action_result failure_class {result.failure_class.value!r} is not declared by {contract.address}"
        )
    return violations


@dataclass(frozen=True)
class ParticipantObservationBoundaryRuntime(ResolvedResource):
    """Compiled participant observation projection boundary."""

    boundary_name: str = ""
    projection_basis: str = ""
    hidden_refs: tuple[str, ...] = ()
    observable_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    disclosed_refs: tuple[str, ...] = ()
    evidence_only_refs: tuple[str, ...] = ()
    discovered_refs: tuple[str, ...] = ()
    inferred_refs: tuple[str, ...] = ()
    concealed_refs: tuple[str, ...] = ()
    deceptive_refs: tuple[str, ...] = ()
    view_transitions: tuple[dict[str, Any], ...] = ()
    view_relation_timeline: tuple[dict[str, Any], ...] = ()
    realized_view_disclosure: str = ""


@dataclass(frozen=True)
class ParticipantOutcomeInterpretationRuleRuntime(ResolvedResource):
    """Compiled SEM-215 participant outcome interpretation rule."""

    rule_name: str = ""
    semantic_version: str = ""
    participant_scope: str = ""
    observation_point_basis: str = ""
    interpretation_basis: str = ""
    source_layers: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    target_layers: tuple[str, ...] = ()
    target_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParticipantBehaviorRuntime(ResolvedResource):
    """Compiled role-neutral participant behavior binding."""

    participant_name: str = ""
    entity_name: str = ""
    starting_account_refs: tuple[str, ...] = ()
    starting_account_addresses: tuple[str, ...] = ()
    initial_knowledge_addresses: tuple[str, ...] = ()
    starting_condition_refs: tuple[str, ...] = ()
    starting_condition_addresses: tuple[str, ...] = ()
    authority_anchor_refs: tuple[str, ...] = ()
    authority_anchor_addresses: tuple[str, ...] = ()
    operating_scope_refs: tuple[str, ...] = ()
    operating_scope_addresses: tuple[str, ...] = ()
    action_contract_addresses: tuple[str, ...] = ()
    observation_boundary_addresses: tuple[str, ...] = ()
    interpretation_mode: str = "role-neutral-projection"


@dataclass(frozen=True)
class ParticipantBehaviorSpecificationRuntime(ResolvedResource):
    """Compiled first-class participant behavior specification aggregate."""

    spec_name: str = ""
    semantic_version: str = ""
    lifecycle_state: str = ""
    participant_addresses: tuple[str, ...] = ()
    participant_role_refs: tuple[str, ...] = ()
    action_contract_addresses: tuple[str, ...] = ()
    observation_boundary_addresses: tuple[str, ...] = ()
    outcome_interpretation_rule_addresses: tuple[str, ...] = ()
    authority_scope_refs: tuple[str, ...] = ()
    authority_scope_addresses: tuple[str, ...] = ()
    behavior_mode: str = ""
    offensive_behavior_refs: tuple[str, ...] = ()
    realization_profile_ref: str = ""
    backend_feature_support_refs: tuple[str, ...] = ()
    evidence_contract_refs: tuple[str, ...] = ()
    extension_policy: str = ""
    extension_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class EventRuntime(ResolvedResource):
    """Resolved orchestration event."""

    condition_names: tuple[str, ...] = ()
    condition_addresses: tuple[str, ...] = ()
    inject_names: tuple[str, ...] = ()
    inject_addresses: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScriptRuntime(ResolvedResource):
    """Resolved script with event dependencies."""

    event_addresses: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoryRuntime(ResolvedResource):
    """Resolved story with script dependencies."""

    script_addresses: tuple[str, ...] = ()


@dataclass(frozen=True)
class ObjectiveWindowReferenceRuntime:
    """Normalized resolved objective/window reference."""

    raw: str
    canonical_name: str
    reference_kind: str
    dependency_roles: tuple[str, ...] = ()
    workflow_name: str = ""
    step_name: str = ""
    namespace_path: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowStepStatePredicateRuntime:
    """Resolved predicate clause over prior workflow step state."""

    step_name: str
    outcomes: tuple[WorkflowStepOutcome, ...] = ()
    min_attempts: int | str | None = None


@dataclass(frozen=True)
class WorkflowPredicateRuntime:
    """Resolved workflow predicate semantics."""

    condition_addresses: tuple[str, ...] = ()
    metric_addresses: tuple[str, ...] = ()
    evaluation_addresses: tuple[str, ...] = ()
    tlo_addresses: tuple[str, ...] = ()
    goal_addresses: tuple[str, ...] = ()
    objective_addresses: tuple[str, ...] = ()
    step_state_predicates: tuple[WorkflowStepStatePredicateRuntime, ...] = ()

    @property
    def external_addresses(self) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for address in (
            *self.condition_addresses,
            *self.metric_addresses,
            *self.evaluation_addresses,
            *self.tlo_addresses,
            *self.goal_addresses,
            *self.objective_addresses,
        ):
            if address in seen:
                continue
            seen.add(address)
            ordered.append(address)
        return tuple(ordered)


@dataclass(frozen=True)
class WorkflowSwitchCaseRuntime:
    """Resolved ordered switch-case branch semantics."""

    case_index: int
    predicate: WorkflowPredicateRuntime
    next_step: str


@dataclass(frozen=True)
class WorkflowStepRuntime:
    """Resolved workflow step semantics."""

    name: str
    step_type: str
    objective_address: str = ""
    predicate: WorkflowPredicateRuntime | None = None
    next_step: str = ""
    on_success: str = ""
    on_failure: str = ""
    on_exhausted: str = ""
    then_step: str = ""
    else_step: str = ""
    switch_cases: tuple[WorkflowSwitchCaseRuntime, ...] = ()
    default_step: str = ""
    branches: tuple[str, ...] = ()
    join_step: str = ""
    owning_parallel_step: str = ""
    called_workflow_address: str = ""
    compensation_workflow_address: str = ""
    max_attempts: int | str | None = None
    state_contract: WorkflowStepSemanticContract = field(
        default_factory=lambda: WorkflowStepSemanticContract(step_type="")
    )


@dataclass(frozen=True)
class WorkflowRuntime(ResolvedResource):
    """Resolved workflow control program."""

    start_step: str = ""
    referenced_objective_addresses: tuple[str, ...] = ()
    control_steps: dict[str, WorkflowStepRuntime] = field(default_factory=dict)
    control_edges: dict[str, tuple[str, ...]] = field(default_factory=dict)
    join_owners: dict[str, str] = field(default_factory=dict)
    step_condition_addresses: dict[str, tuple[str, ...]] = field(default_factory=dict)
    step_predicate_addresses: dict[str, tuple[str, ...]] = field(default_factory=dict)
    required_features: tuple[WorkflowFeature, ...] = ()
    required_state_predicate_features: tuple[WorkflowStatePredicateFeature, ...] = ()
    result_contract: "WorkflowResultContract" = field(default_factory=lambda: WorkflowResultContract())
    execution_contract: "WorkflowExecutionContract" = field(default_factory=lambda: WorkflowExecutionContract())
    state_schema_version: str = WORKFLOW_STATE_SCHEMA_VERSION


def _participant_observation_status_from_payload(value: Any) -> ParticipantObservationStatus | None:
    if isinstance(value, ParticipantObservationStatus):
        return value
    if value is None:
        return None
    return ParticipantObservationStatus(str(value))


def _validate_required_string(value: Any, message: str) -> None:
    if not isinstance(value, str) or not value:
        raise TypeError(message)


def _validate_optional_string(value: Any, message: str) -> None:
    if value is not None and (not isinstance(value, str) or not value):
        raise TypeError(message)


def _validate_optional_address(value: str | None, *, prefix: str, message: str) -> None:
    if value is not None and (not isinstance(value, str) or not value.startswith(prefix)):
        raise ValueError(message)


def _validate_required_address(value: str, *, prefix: str, message: str) -> None:
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValueError(message)


def _tuple_of_non_empty_strings(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise TypeError(f"{field_name} must be a list of strings")
    values = tuple(value)
    refs = tuple(str(item) for item in values if isinstance(item, str) and item)
    if len(refs) != len(values):
        raise TypeError(f"{field_name} entries must be non-empty strings")
    if len(set(refs)) != len(refs):
        raise ValueError(f"{field_name} entries must be unique")
    return refs


def _observation_point_matches_action_instance(observation_point: str, action_instance_id: str) -> bool:
    return action_instance_id in observation_point.split(":")


@dataclass(frozen=True)
class ParticipantActionPreconditionResult:
    """Resolved applicability state for one typed SEM-211 precondition."""

    precondition_id: str
    precondition_class: ParticipantPreconditionClass
    status: ParticipantActionPreconditionStatus
    participant_address: str
    episode_id: str
    action_contract_address: str
    observation_point: str
    support_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantActionPreconditionResult":
        if not isinstance(payload, Mapping):
            raise TypeError("participant action precondition result must be a mapping")
        missing = [
            key
            for key in (
                "precondition_id",
                "precondition_class",
                "status",
                "participant_address",
                "episode_id",
                "action_contract_address",
                "observation_point",
            )
            if key not in payload
        ]
        if missing:
            raise ValueError("participant action precondition result is missing required fields: " + ", ".join(missing))
        precondition_class_raw = payload.get("precondition_class")
        status_raw = payload.get("status")
        return cls(
            precondition_id=str(payload.get("precondition_id")),
            precondition_class=(
                precondition_class_raw
                if isinstance(precondition_class_raw, ParticipantPreconditionClass)
                else ParticipantPreconditionClass(str(precondition_class_raw))
            ),
            status=(
                status_raw
                if isinstance(status_raw, ParticipantActionPreconditionStatus)
                else ParticipantActionPreconditionStatus(str(status_raw))
            ),
            participant_address=str(payload.get("participant_address")),
            episode_id=str(payload.get("episode_id")),
            action_contract_address=str(payload.get("action_contract_address")),
            observation_point=str(payload.get("observation_point")),
            support_refs=_tuple_of_non_empty_strings(payload.get("support_refs", ()), field_name="support_refs"),
            evidence_refs=_tuple_of_non_empty_strings(payload.get("evidence_refs", ()), field_name="evidence_refs"),
            diagnostics=_tuple_of_non_empty_strings(payload.get("diagnostics", ()), field_name="diagnostics"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "precondition_id": self.precondition_id,
            "precondition_class": self.precondition_class.value,
            "status": self.status.value,
            "participant_address": self.participant_address,
            "episode_id": self.episode_id,
            "action_contract_address": self.action_contract_address,
            "observation_point": self.observation_point,
            "support_refs": list(self.support_refs),
            "evidence_refs": list(self.evidence_refs),
            "diagnostics": list(self.diagnostics),
        }

    def __post_init__(self) -> None:
        _validate_required_string(
            self.precondition_id,
            "precondition_id must be a non-empty string",
        )
        if not isinstance(self.precondition_class, ParticipantPreconditionClass):
            raise TypeError("precondition_class must be a ParticipantPreconditionClass")
        if not isinstance(self.status, ParticipantActionPreconditionStatus):
            raise TypeError("status must be a ParticipantActionPreconditionStatus")
        _validate_required_string(
            self.participant_address,
            "participant action precondition participant_address must be a non-empty string",
        )
        _validate_required_string(
            self.episode_id,
            "participant action precondition episode_id must be a non-empty string",
        )
        _validate_required_address(
            self.action_contract_address,
            prefix=_PARTICIPANT_ACTION_CONTRACT_PREFIX,
            message="action_contract_address must be a compiled participant action contract address",
        )
        _validate_required_string(
            self.observation_point,
            "observation_point must be a non-empty string",
        )
        _tuple_of_non_empty_strings(self.support_refs, field_name="support_refs")
        _tuple_of_non_empty_strings(self.evidence_refs, field_name="evidence_refs")
        _tuple_of_non_empty_strings(self.diagnostics, field_name="diagnostics")


@dataclass(frozen=True)
class ParticipantActionEffectResult:
    """Realized effect entry for a SEM-211 participant action result."""

    effect_id: str
    effect_class: ParticipantEffectClass
    description: str
    target_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantActionEffectResult":
        if not isinstance(payload, Mapping):
            raise TypeError("participant action effect result must be a mapping")
        missing = [key for key in ("effect_id", "effect_class", "description") if key not in payload]
        if missing:
            raise ValueError("participant action effect result is missing required fields: " + ", ".join(missing))
        effect_class_raw = payload.get("effect_class")
        return cls(
            effect_id=str(payload.get("effect_id")),
            effect_class=(
                effect_class_raw
                if isinstance(effect_class_raw, ParticipantEffectClass)
                else ParticipantEffectClass(str(effect_class_raw))
            ),
            description=str(payload.get("description")),
            target_refs=_tuple_of_non_empty_strings(payload.get("target_refs", ()), field_name="target_refs"),
            evidence_refs=_tuple_of_non_empty_strings(payload.get("evidence_refs", ()), field_name="evidence_refs"),
            diagnostics=_tuple_of_non_empty_strings(payload.get("diagnostics", ()), field_name="diagnostics"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "effect_class": self.effect_class.value,
            "description": self.description,
            "target_refs": list(self.target_refs),
            "evidence_refs": list(self.evidence_refs),
            "diagnostics": list(self.diagnostics),
        }

    def __post_init__(self) -> None:
        _validate_required_string(self.effect_id, "effect_id must be a non-empty string")
        if not isinstance(self.effect_class, ParticipantEffectClass):
            raise TypeError("effect_class must be a ParticipantEffectClass")
        _validate_required_string(
            self.description,
            "participant action effect description must be a non-empty string",
        )
        _tuple_of_non_empty_strings(self.target_refs, field_name="target_refs")
        _tuple_of_non_empty_strings(self.evidence_refs, field_name="evidence_refs")
        _tuple_of_non_empty_strings(self.diagnostics, field_name="diagnostics")
        if self.effect_class not in {ParticipantEffectClass.NO_EFFECT, ParticipantEffectClass.UNKNOWN_EFFECT}:
            if not self.target_refs and not self.evidence_refs:
                raise ValueError(f"{self.effect_class.value} effects require target_refs or evidence_refs")


_PARTICIPANT_ACTION_FAILURE_STATUSES = frozenset(
    {
        ParticipantActionResultStatus.REJECTED,
        ParticipantActionResultStatus.WITHHELD,
        ParticipantActionResultStatus.FAILED,
        ParticipantActionResultStatus.PARTIAL_SUCCESS,
        ParticipantActionResultStatus.UNKNOWN,
    }
)
_PARTICIPANT_ACTION_SUCCESS_STATUSES = frozenset(
    {
        ParticipantActionResultStatus.ACCEPTED,
        ParticipantActionResultStatus.SUCCEEDED,
        ParticipantActionResultStatus.PARTIAL_SUCCESS,
    }
)
_PARTICIPANT_ACTION_TERMINAL_EFFECT_STATUSES = frozenset(
    {
        ParticipantActionResultStatus.SUCCEEDED,
        ParticipantActionResultStatus.PARTIAL_SUCCESS,
    }
)


@dataclass(frozen=True)
class ParticipantActionResult:
    """Typed SEM-211 local result for a participant action attempt."""

    status: ParticipantActionResultStatus
    participant_address: str
    episode_id: str
    action_instance_id: str
    action_contract_address: str
    observation_point: str
    preconditions: tuple[ParticipantActionPreconditionResult, ...] = ()
    effects: tuple[ParticipantActionEffectResult, ...] = ()
    failure_class: ParticipantFailureClass | None = None
    observations: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantActionResult":
        if not isinstance(payload, Mapping):
            raise TypeError("participant action result must be a mapping")
        missing = [
            key
            for key in (
                "status",
                "participant_address",
                "episode_id",
                "action_instance_id",
                "action_contract_address",
                "observation_point",
            )
            if key not in payload
        ]
        if missing:
            raise ValueError("participant action result is missing required fields: " + ", ".join(missing))
        status_raw = payload.get("status")
        failure_raw = payload.get("failure_class")
        preconditions_raw = payload.get("preconditions", ())
        effects_raw = payload.get("effects", ())
        if isinstance(preconditions_raw, (str, bytes, Mapping)) or not isinstance(preconditions_raw, Iterable):
            raise TypeError("preconditions must be a list of participant action precondition results")
        if isinstance(effects_raw, (str, bytes, Mapping)) or not isinstance(effects_raw, Iterable):
            raise TypeError("effects must be a list of participant action effect results")
        return cls(
            status=(
                status_raw
                if isinstance(status_raw, ParticipantActionResultStatus)
                else ParticipantActionResultStatus(str(status_raw))
            ),
            participant_address=str(payload.get("participant_address")),
            episode_id=str(payload.get("episode_id")),
            action_instance_id=str(payload.get("action_instance_id")),
            action_contract_address=str(payload.get("action_contract_address")),
            observation_point=str(payload.get("observation_point")),
            preconditions=tuple(ParticipantActionPreconditionResult.from_payload(item) for item in preconditions_raw),
            effects=tuple(ParticipantActionEffectResult.from_payload(item) for item in effects_raw),
            failure_class=(
                None
                if failure_raw is None
                else (
                    failure_raw
                    if isinstance(failure_raw, ParticipantFailureClass)
                    else ParticipantFailureClass(str(failure_raw))
                )
            ),
            observations=_tuple_of_non_empty_strings(payload.get("observations", ()), field_name="observations"),
            evidence_refs=_tuple_of_non_empty_strings(payload.get("evidence_refs", ()), field_name="evidence_refs"),
            diagnostics=_tuple_of_non_empty_strings(payload.get("diagnostics", ()), field_name="diagnostics"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "participant_address": self.participant_address,
            "episode_id": self.episode_id,
            "action_instance_id": self.action_instance_id,
            "action_contract_address": self.action_contract_address,
            "observation_point": self.observation_point,
            "preconditions": [item.to_payload() for item in self.preconditions],
            "effects": [item.to_payload() for item in self.effects],
            "failure_class": self.failure_class.value if self.failure_class is not None else None,
            "observations": list(self.observations),
            "evidence_refs": list(self.evidence_refs),
            "diagnostics": list(self.diagnostics),
        }

    def __post_init__(self) -> None:
        if not isinstance(self.status, ParticipantActionResultStatus):
            raise TypeError("status must be a ParticipantActionResultStatus")
        _validate_required_string(
            self.participant_address,
            "participant action result participant_address must be a non-empty string",
        )
        _validate_required_string(
            self.episode_id,
            "participant action result episode_id must be a non-empty string",
        )
        _validate_required_string(
            self.action_instance_id,
            "participant action result action_instance_id must be a non-empty string",
        )
        _validate_required_address(
            self.action_contract_address,
            prefix=_PARTICIPANT_ACTION_CONTRACT_PREFIX,
            message="action_contract_address must be a compiled participant action contract address",
        )
        _validate_required_string(
            self.observation_point,
            "observation_point must be a non-empty string",
        )
        if not _observation_point_matches_action_instance(self.observation_point, self.action_instance_id):
            raise ValueError("action result observation_point must be anchored to action_instance_id")
        if not isinstance(self.preconditions, tuple):
            raise TypeError("preconditions must be a tuple")
        if not self.preconditions:
            raise ValueError("participant action results require precondition results")
        if any(not isinstance(item, ParticipantActionPreconditionResult) for item in self.preconditions):
            raise TypeError("preconditions must contain ParticipantActionPreconditionResult values")
        if len({item.precondition_id for item in self.preconditions}) != len(self.preconditions):
            raise ValueError("precondition result ids must be unique")
        if not isinstance(self.effects, tuple):
            raise TypeError("effects must be a tuple")
        if any(not isinstance(item, ParticipantActionEffectResult) for item in self.effects):
            raise TypeError("effects must contain ParticipantActionEffectResult values")
        if len({item.effect_id for item in self.effects}) != len(self.effects):
            raise ValueError("effect result ids must be unique")
        if self.failure_class is not None and not isinstance(self.failure_class, ParticipantFailureClass):
            raise TypeError("failure_class must be a ParticipantFailureClass or None")
        _tuple_of_non_empty_strings(self.observations, field_name="observations")
        _tuple_of_non_empty_strings(self.evidence_refs, field_name="evidence_refs")
        _tuple_of_non_empty_strings(self.diagnostics, field_name="diagnostics")
        self._validate_scope()
        self._validate_fail_closed()

    def _validate_scope(self) -> None:
        for precondition in self.preconditions:
            if precondition.participant_address != self.participant_address:
                raise ValueError("precondition participant_address must match action result participant_address")
            if precondition.episode_id != self.episode_id:
                raise ValueError("precondition episode_id must match action result episode_id")
            if precondition.action_contract_address != self.action_contract_address:
                raise ValueError(
                    "precondition action_contract_address must match action result action_contract_address"
                )
            if not _observation_point_matches_action_instance(precondition.observation_point, self.action_instance_id):
                raise ValueError("precondition observation_point must be anchored to action result action_instance_id")

    def _validate_fail_closed(self) -> None:
        blocked = [
            item
            for item in self.preconditions
            if item.status
            in {
                ParticipantActionPreconditionStatus.UNSATISFIED,
                ParticipantActionPreconditionStatus.UNRESOLVED,
            }
        ]
        if blocked and self.status in _PARTICIPANT_ACTION_SUCCESS_STATUSES:
            raise ValueError("unsatisfied or unresolved preconditions fail closed")
        if blocked and self.failure_class is None:
            raise ValueError("unsatisfied or unresolved preconditions require a portable failure_class")
        if self.status == ParticipantActionResultStatus.SUCCEEDED:
            if self.failure_class is not None:
                raise ValueError("succeeded action results may not report failure_class")
        if self.status == ParticipantActionResultStatus.ACCEPTED and self.failure_class is not None:
            raise ValueError("accepted action results may not report failure_class")
        if self.status in _PARTICIPANT_ACTION_TERMINAL_EFFECT_STATUSES:
            if not self.effects:
                raise ValueError(f"{self.status.value} action results require declared effects")
        if self.status in _PARTICIPANT_ACTION_FAILURE_STATUSES and self.failure_class is None:
            raise ValueError(f"{self.status.value} action results require a portable failure_class")


@dataclass(frozen=True)
class ParticipantAttributionCandidate:
    """Candidate endpoint for a SEM-212 attribution edge."""

    candidate_kind: ParticipantAttributionCandidateKind
    ref: str
    description: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantAttributionCandidate":
        if not isinstance(payload, Mapping):
            raise TypeError("participant attribution candidate must be a mapping")
        missing = [key for key in ("candidate_kind", "ref", "description") if key not in payload]
        if missing:
            raise ValueError("participant attribution candidate is missing required fields: " + ", ".join(missing))
        candidate_kind_raw = payload.get("candidate_kind")
        return cls(
            candidate_kind=(
                candidate_kind_raw
                if isinstance(candidate_kind_raw, ParticipantAttributionCandidateKind)
                else ParticipantAttributionCandidateKind(str(candidate_kind_raw))
            ),
            ref=str(payload.get("ref")),
            description=str(payload.get("description")),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_kind": self.candidate_kind.value,
            "ref": self.ref,
            "description": self.description,
        }

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_kind, ParticipantAttributionCandidateKind):
            raise TypeError("candidate_kind must be a ParticipantAttributionCandidateKind")
        _validate_required_string(self.ref, "participant attribution candidate ref must be a non-empty string")
        _validate_required_string(
            self.description,
            "participant attribution candidate description must be a non-empty string",
        )


@dataclass(frozen=True)
class ParticipantAttributionOrderingBasis:
    """Explicit ordering basis for a SEM-212 attribution edge."""

    basis_kind: ParticipantAttributionOrderingBasisKind
    relation_ref: str
    description: str
    ordered_event_refs: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantAttributionOrderingBasis":
        if not isinstance(payload, Mapping):
            raise TypeError("participant attribution ordering_basis must be a mapping")
        missing = [key for key in ("basis_kind", "relation_ref", "description") if key not in payload]
        if missing:
            raise ValueError("participant attribution ordering_basis is missing required fields: " + ", ".join(missing))
        basis_kind_raw = payload.get("basis_kind")
        return cls(
            basis_kind=(
                basis_kind_raw
                if isinstance(basis_kind_raw, ParticipantAttributionOrderingBasisKind)
                else ParticipantAttributionOrderingBasisKind(str(basis_kind_raw))
            ),
            relation_ref=str(payload.get("relation_ref")),
            description=str(payload.get("description")),
            ordered_event_refs=_tuple_of_non_empty_strings(
                payload.get("ordered_event_refs", ()),
                field_name="ordered_event_refs",
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "basis_kind": self.basis_kind.value,
            "relation_ref": self.relation_ref,
            "description": self.description,
            "ordered_event_refs": list(self.ordered_event_refs),
        }

    def __post_init__(self) -> None:
        if not isinstance(self.basis_kind, ParticipantAttributionOrderingBasisKind):
            raise TypeError("basis_kind must be a ParticipantAttributionOrderingBasisKind")
        _validate_required_string(self.relation_ref, "ordering_basis relation_ref must be a non-empty string")
        _validate_required_string(self.description, "ordering_basis description must be a non-empty string")
        _tuple_of_non_empty_strings(self.ordered_event_refs, field_name="ordered_event_refs")


@dataclass(frozen=True)
class ParticipantAttributionEvidenceBasis:
    """Evidence-disclosure basis for a SEM-212 attribution edge."""

    capture_apparatus: str
    granularity: str
    loss_model: str
    redaction_policy: str
    observer_effects: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantAttributionEvidenceBasis":
        if not isinstance(payload, Mapping):
            raise TypeError("participant attribution evidence_basis must be a mapping")
        missing = [
            key
            for key in (
                "capture_apparatus",
                "granularity",
                "loss_model",
                "redaction_policy",
                "observer_effects",
            )
            if key not in payload
        ]
        if missing:
            raise ValueError("participant attribution evidence_basis is missing required fields: " + ", ".join(missing))
        return cls(
            capture_apparatus=str(payload.get("capture_apparatus")),
            granularity=str(payload.get("granularity")),
            loss_model=str(payload.get("loss_model")),
            redaction_policy=str(payload.get("redaction_policy")),
            observer_effects=_tuple_of_non_empty_strings(
                payload.get("observer_effects", ()),
                field_name="observer_effects",
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "capture_apparatus": self.capture_apparatus,
            "granularity": self.granularity,
            "loss_model": self.loss_model,
            "redaction_policy": self.redaction_policy,
            "observer_effects": list(self.observer_effects),
        }

    def __post_init__(self) -> None:
        _validate_required_string(
            self.capture_apparatus,
            "evidence_basis capture_apparatus must be a non-empty string",
        )
        _validate_required_string(self.granularity, "evidence_basis granularity must be a non-empty string")
        _validate_required_string(self.loss_model, "evidence_basis loss_model must be a non-empty string")
        _validate_required_string(self.redaction_policy, "evidence_basis redaction_policy must be a non-empty string")
        observer_effects = _tuple_of_non_empty_strings(self.observer_effects, field_name="observer_effects")
        if not observer_effects:
            raise ValueError("evidence_basis observer_effects must disclose at least one observer effect")


@dataclass(frozen=True)
class ParticipantAttributionEdge:
    """Evidence-labeled SEM-212 attribution edge."""

    edge_id: str
    participant_address: str
    episode_id: str
    observation_point: str
    cause_candidate: ParticipantAttributionCandidate
    effect_candidate: ParticipantAttributionCandidate
    ordering_basis: ParticipantAttributionOrderingBasis
    evidence_basis: ParticipantAttributionEvidenceBasis
    support_class: ParticipantAttributionSupportClass
    confidence: str
    strength: str
    limitations: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    interpretation_rule_ref: str | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantAttributionEdge":
        if not isinstance(payload, Mapping):
            raise TypeError("participant attribution edge must be a mapping")
        missing = [
            key
            for key in (
                "edge_id",
                "participant_address",
                "episode_id",
                "observation_point",
                "cause_candidate",
                "effect_candidate",
                "ordering_basis",
                "evidence_basis",
                "support_class",
                "confidence",
                "strength",
                "limitations",
                "evidence_refs",
            )
            if key not in payload
        ]
        if missing:
            raise ValueError("participant attribution edge is missing required fields: " + ", ".join(missing))
        support_class_raw = payload.get("support_class")
        return cls(
            edge_id=str(payload.get("edge_id")),
            participant_address=str(payload.get("participant_address")),
            episode_id=str(payload.get("episode_id")),
            observation_point=str(payload.get("observation_point")),
            cause_candidate=ParticipantAttributionCandidate.from_payload(payload.get("cause_candidate")),
            effect_candidate=ParticipantAttributionCandidate.from_payload(payload.get("effect_candidate")),
            ordering_basis=ParticipantAttributionOrderingBasis.from_payload(payload.get("ordering_basis")),
            evidence_basis=ParticipantAttributionEvidenceBasis.from_payload(payload.get("evidence_basis")),
            support_class=(
                support_class_raw
                if isinstance(support_class_raw, ParticipantAttributionSupportClass)
                else ParticipantAttributionSupportClass(str(support_class_raw))
            ),
            confidence=str(payload.get("confidence")),
            strength=str(payload.get("strength")),
            limitations=_tuple_of_non_empty_strings(payload.get("limitations"), field_name="limitations"),
            evidence_refs=_tuple_of_non_empty_strings(payload.get("evidence_refs"), field_name="evidence_refs"),
            interpretation_rule_ref=(
                str(payload["interpretation_rule_ref"]) if payload.get("interpretation_rule_ref") is not None else None
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "participant_address": self.participant_address,
            "episode_id": self.episode_id,
            "observation_point": self.observation_point,
            "cause_candidate": self.cause_candidate.to_payload(),
            "effect_candidate": self.effect_candidate.to_payload(),
            "ordering_basis": self.ordering_basis.to_payload(),
            "evidence_basis": self.evidence_basis.to_payload(),
            "support_class": self.support_class.value,
            "confidence": self.confidence,
            "strength": self.strength,
            "limitations": list(self.limitations),
            "evidence_refs": list(self.evidence_refs),
            "interpretation_rule_ref": self.interpretation_rule_ref,
        }

    def __post_init__(self) -> None:
        _validate_required_string(self.edge_id, "participant attribution edge_id must be a non-empty string")
        _validate_required_string(
            self.participant_address,
            "participant attribution participant_address must be a non-empty string",
        )
        _validate_required_string(self.episode_id, "participant attribution episode_id must be a non-empty string")
        _validate_required_string(
            self.observation_point,
            "participant attribution observation_point must be a non-empty string",
        )
        if not isinstance(self.cause_candidate, ParticipantAttributionCandidate):
            raise TypeError("cause_candidate must be a ParticipantAttributionCandidate")
        if not isinstance(self.effect_candidate, ParticipantAttributionCandidate):
            raise TypeError("effect_candidate must be a ParticipantAttributionCandidate")
        if not isinstance(self.ordering_basis, ParticipantAttributionOrderingBasis):
            raise TypeError("ordering_basis must be a ParticipantAttributionOrderingBasis")
        if not isinstance(self.evidence_basis, ParticipantAttributionEvidenceBasis):
            raise TypeError("evidence_basis must be a ParticipantAttributionEvidenceBasis")
        if not isinstance(self.support_class, ParticipantAttributionSupportClass):
            raise TypeError("support_class must be a ParticipantAttributionSupportClass")
        _validate_required_string(self.confidence, "participant attribution confidence must be a non-empty string")
        _validate_required_string(self.strength, "participant attribution strength must be a non-empty string")
        limitations = _tuple_of_non_empty_strings(self.limitations, field_name="limitations")
        evidence_refs = _tuple_of_non_empty_strings(self.evidence_refs, field_name="evidence_refs")
        if not limitations:
            raise ValueError("participant attribution edges require limitations")
        if not evidence_refs:
            raise ValueError("participant attribution edges require evidence_refs")
        _validate_optional_string(
            self.interpretation_rule_ref,
            "interpretation_rule_ref must be a non-empty string or None",
        )
        if (
            self.support_class in STRONG_ATTRIBUTION_SUPPORT_CLASSES
            and self.ordering_basis.basis_kind == ParticipantAttributionOrderingBasisKind.TIMESTAMP_ADJACENCY
        ):
            raise ValueError("timestamp_adjacency ordering_basis cannot support strong causal attribution claims")
        if (
            self.effect_candidate.candidate_kind in OUTCOME_ATTRIBUTION_CANDIDATE_KINDS
            and self.interpretation_rule_ref is None
        ):
            raise ValueError("downstream outcome attribution requires interpretation_rule_ref")


def _outcome_source_layer_from_payload(value: Any) -> OutcomeInterpretationSourceLayer:
    if isinstance(value, OutcomeInterpretationSourceLayer):
        return value
    return OutcomeInterpretationSourceLayer(str(value))


def _outcome_target_layer_from_payload(value: Any) -> OutcomeInterpretationTargetLayer:
    if isinstance(value, OutcomeInterpretationTargetLayer):
        return value
    return OutcomeInterpretationTargetLayer(str(value))


@dataclass(frozen=True)
class ParticipantOutcomeSourceRecord:
    """Runtime source observed for a SEM-215 outcome interpretation."""

    source_id: str
    source_layer: OutcomeInterpretationSourceLayer
    ref: str
    observed_value: str
    evidence_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantOutcomeSourceRecord":
        if not isinstance(payload, Mapping):
            raise TypeError("participant outcome source record must be a mapping")
        missing = [key for key in ("source_id", "source_layer", "ref", "observed_value") if key not in payload]
        if missing:
            raise ValueError("participant outcome source record is missing required fields: " + ", ".join(missing))
        return cls(
            source_id=str(payload.get("source_id")),
            source_layer=_outcome_source_layer_from_payload(payload.get("source_layer")),
            ref=str(payload.get("ref")),
            observed_value=str(payload.get("observed_value")),
            evidence_refs=_tuple_of_non_empty_strings(payload.get("evidence_refs", ()), field_name="evidence_refs"),
            provenance_refs=_tuple_of_non_empty_strings(
                payload.get("provenance_refs", ()),
                field_name="provenance_refs",
            ),
            diagnostics=_tuple_of_non_empty_strings(payload.get("diagnostics", ()), field_name="diagnostics"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_layer": self.source_layer.value,
            "ref": self.ref,
            "observed_value": self.observed_value,
            "evidence_refs": list(self.evidence_refs),
            "provenance_refs": list(self.provenance_refs),
            "diagnostics": list(self.diagnostics),
        }

    def __post_init__(self) -> None:
        _validate_required_string(self.source_id, "participant outcome source_id must be a non-empty string")
        if not isinstance(self.source_layer, OutcomeInterpretationSourceLayer):
            raise TypeError("source_layer must be an OutcomeInterpretationSourceLayer")
        _validate_required_string(self.ref, "participant outcome source ref must be a non-empty string")
        _validate_required_string(
            self.observed_value,
            "participant outcome source observed_value must be a non-empty string",
        )
        _tuple_of_non_empty_strings(self.evidence_refs, field_name="evidence_refs")
        _tuple_of_non_empty_strings(self.provenance_refs, field_name="provenance_refs")
        _tuple_of_non_empty_strings(self.diagnostics, field_name="diagnostics")


@dataclass(frozen=True)
class ParticipantOutcomeTargetRecord:
    """Runtime target interpretation produced by a SEM-215 rule."""

    target_id: str
    target_layer: OutcomeInterpretationTargetLayer
    ref: str
    interpreted_value: str
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    governance_ref: str | None = None
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantOutcomeTargetRecord":
        if not isinstance(payload, Mapping):
            raise TypeError("participant outcome target record must be a mapping")
        missing = [
            key
            for key in (
                "target_id",
                "target_layer",
                "ref",
                "interpreted_value",
                "evidence_refs",
                "limitations",
            )
            if key not in payload
        ]
        if missing:
            raise ValueError("participant outcome target record is missing required fields: " + ", ".join(missing))
        return cls(
            target_id=str(payload.get("target_id")),
            target_layer=_outcome_target_layer_from_payload(payload.get("target_layer")),
            ref=str(payload.get("ref")),
            interpreted_value=str(payload.get("interpreted_value")),
            evidence_refs=_tuple_of_non_empty_strings(payload.get("evidence_refs"), field_name="evidence_refs"),
            limitations=_tuple_of_non_empty_strings(payload.get("limitations"), field_name="limitations"),
            governance_ref=_optional_payload_string(payload, "governance_ref"),
            diagnostics=_tuple_of_non_empty_strings(payload.get("diagnostics", ()), field_name="diagnostics"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_layer": self.target_layer.value,
            "ref": self.ref,
            "interpreted_value": self.interpreted_value,
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
            "governance_ref": self.governance_ref,
            "diagnostics": list(self.diagnostics),
        }

    def __post_init__(self) -> None:
        _validate_required_string(self.target_id, "participant outcome target_id must be a non-empty string")
        if not isinstance(self.target_layer, OutcomeInterpretationTargetLayer):
            raise TypeError("target_layer must be an OutcomeInterpretationTargetLayer")
        _validate_required_string(self.ref, "participant outcome target ref must be a non-empty string")
        _validate_required_string(
            self.interpreted_value,
            "participant outcome target interpreted_value must be a non-empty string",
        )
        if not _tuple_of_non_empty_strings(self.evidence_refs, field_name="evidence_refs"):
            raise ValueError("participant outcome targets require evidence_refs")
        if not _tuple_of_non_empty_strings(self.limitations, field_name="limitations"):
            raise ValueError("participant outcome targets require limitations")
        _validate_optional_string(self.governance_ref, "governance_ref must be a non-empty string or None")
        _tuple_of_non_empty_strings(self.diagnostics, field_name="diagnostics")
        if self.target_layer == OutcomeInterpretationTargetLayer.REWARD_SIGNAL and self.governance_ref is None:
            raise ValueError("reward_signal outcome targets require governance_ref")


def _participant_outcome_source_records_from_payload(value: Any) -> tuple[ParticipantOutcomeSourceRecord, ...]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise TypeError("outcome source_bindings must be a list of source records")
    return tuple(ParticipantOutcomeSourceRecord.from_payload(item) for item in value)


def _participant_outcome_target_records_from_payload(value: Any) -> tuple[ParticipantOutcomeTargetRecord, ...]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise TypeError("outcome target_bindings must be a list of target records")
    return tuple(ParticipantOutcomeTargetRecord.from_payload(item) for item in value)


@dataclass(frozen=True)
class ParticipantOutcomeInterpretationRecord:
    """Provenance-bearing SEM-215 interpretation of participant-local outcomes."""

    interpretation_id: str
    rule_address: str
    participant_address: str
    episode_id: str
    observation_point: str
    source_bindings: tuple[ParticipantOutcomeSourceRecord, ...]
    target_bindings: tuple[ParticipantOutcomeTargetRecord, ...]
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantOutcomeInterpretationRecord":
        if not isinstance(payload, Mapping):
            raise TypeError("participant outcome interpretation record must be a mapping")
        missing = [
            key
            for key in (
                "interpretation_id",
                "rule_address",
                "participant_address",
                "episode_id",
                "observation_point",
                "source_bindings",
                "target_bindings",
                "evidence_refs",
                "limitations",
            )
            if key not in payload
        ]
        if missing:
            raise ValueError(
                "participant outcome interpretation record is missing required fields: " + ", ".join(missing)
            )
        return cls(
            interpretation_id=str(payload.get("interpretation_id")),
            rule_address=str(payload.get("rule_address")),
            participant_address=str(payload.get("participant_address")),
            episode_id=str(payload.get("episode_id")),
            observation_point=str(payload.get("observation_point")),
            source_bindings=_participant_outcome_source_records_from_payload(payload.get("source_bindings")),
            target_bindings=_participant_outcome_target_records_from_payload(payload.get("target_bindings")),
            evidence_refs=_tuple_of_non_empty_strings(payload.get("evidence_refs"), field_name="evidence_refs"),
            limitations=_tuple_of_non_empty_strings(payload.get("limitations"), field_name="limitations"),
            diagnostics=_tuple_of_non_empty_strings(payload.get("diagnostics", ()), field_name="diagnostics"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "interpretation_id": self.interpretation_id,
            "rule_address": self.rule_address,
            "participant_address": self.participant_address,
            "episode_id": self.episode_id,
            "observation_point": self.observation_point,
            "source_bindings": [source.to_payload() for source in self.source_bindings],
            "target_bindings": [target.to_payload() for target in self.target_bindings],
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
            "diagnostics": list(self.diagnostics),
        }

    def __post_init__(self) -> None:
        _validate_required_string(
            self.interpretation_id,
            "participant outcome interpretation_id must be a non-empty string",
        )
        _validate_required_address(
            self.rule_address,
            prefix=_PARTICIPANT_OUTCOME_RULE_PREFIX,
            message="rule_address must be a compiled participant outcome interpretation rule address",
        )
        _validate_required_string(
            self.participant_address,
            "participant outcome participant_address must be a non-empty string",
        )
        _validate_required_string(self.episode_id, "participant outcome episode_id must be a non-empty string")
        _validate_required_string(
            self.observation_point,
            "participant outcome observation_point must be a non-empty string",
        )
        if not isinstance(self.source_bindings, tuple):
            raise TypeError("source_bindings must be a tuple")
        if not self.source_bindings:
            raise ValueError("participant outcome interpretations require source_bindings")
        if any(not isinstance(source, ParticipantOutcomeSourceRecord) for source in self.source_bindings):
            raise TypeError("source_bindings must contain ParticipantOutcomeSourceRecord values")
        if len({source.source_id for source in self.source_bindings}) != len(self.source_bindings):
            raise ValueError("participant outcome source_id values must be unique")
        if not isinstance(self.target_bindings, tuple):
            raise TypeError("target_bindings must be a tuple")
        if not self.target_bindings:
            raise ValueError("participant outcome interpretations require target_bindings")
        if any(not isinstance(target, ParticipantOutcomeTargetRecord) for target in self.target_bindings):
            raise TypeError("target_bindings must contain ParticipantOutcomeTargetRecord values")
        if len({target.target_id for target in self.target_bindings}) != len(self.target_bindings):
            raise ValueError("participant outcome target_id values must be unique")
        if not _tuple_of_non_empty_strings(self.evidence_refs, field_name="evidence_refs"):
            raise ValueError("participant outcome interpretations require evidence_refs")
        if not _tuple_of_non_empty_strings(self.limitations, field_name="limitations"):
            raise ValueError("participant outcome interpretations require limitations")
        _tuple_of_non_empty_strings(self.diagnostics, field_name="diagnostics")


def _participant_outcome_interpretation_records_from_payload(
    value: Any,
) -> tuple[ParticipantOutcomeInterpretationRecord, ...]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise TypeError("outcome_interpretations must be a list of interpretation records")
    return tuple(ParticipantOutcomeInterpretationRecord.from_payload(item) for item in value)


def _participant_time_domain_from_payload(value: Any) -> ParticipantTimeDomain:
    if isinstance(value, ParticipantTimeDomain):
        return value
    return ParticipantTimeDomain(str(value))


def _participant_temporal_event_point_from_payload(value: Any) -> ParticipantTemporalEventPoint:
    if isinstance(value, ParticipantTemporalEventPoint):
        return value
    return ParticipantTemporalEventPoint(str(value))


def _participant_temporal_state_from_payload(value: Any) -> ParticipantTemporalState:
    if isinstance(value, ParticipantTemporalState):
        return value
    return ParticipantTemporalState(str(value))


def _participant_temporal_event_points_from_payload(value: Any) -> tuple[ParticipantTemporalEventPoint, ...]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise TypeError("temporal event_points must be a list of event-point strings")
    points = tuple(_participant_temporal_event_point_from_payload(item) for item in value)
    if not points:
        raise ValueError("temporal event_points must be non-empty")
    if len(set(points)) != len(points):
        raise ValueError("temporal event_points must be unique")
    return points


@dataclass(frozen=True)
class ParticipantTemporalRuntimeContext:
    """Realized SEM-213 temporal context on a participant behavior event."""

    temporal_contract_id: str
    time_domain: ParticipantTimeDomain
    clock_authority: str
    event_points: tuple[ParticipantTemporalEventPoint, ...]
    observation_point: str
    backend_disclosure_refs: tuple[str, ...] = ()
    reset_boundary: str | None = None
    replay_boundary: str | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantTemporalRuntimeContext":
        if not isinstance(payload, Mapping):
            raise TypeError("participant temporal runtime context must be a mapping")
        missing = [
            key
            for key in (
                "temporal_contract_id",
                "time_domain",
                "clock_authority",
                "event_points",
                "observation_point",
            )
            if key not in payload
        ]
        if missing:
            raise ValueError("participant temporal runtime context is missing required fields: " + ", ".join(missing))
        return cls(
            temporal_contract_id=str(payload.get("temporal_contract_id")),
            time_domain=_participant_time_domain_from_payload(payload.get("time_domain")),
            clock_authority=str(payload.get("clock_authority")),
            event_points=_participant_temporal_event_points_from_payload(payload.get("event_points")),
            observation_point=str(payload.get("observation_point")),
            backend_disclosure_refs=_tuple_of_non_empty_strings(
                payload.get("backend_disclosure_refs", ()),
                field_name="backend_disclosure_refs",
            ),
            reset_boundary=_optional_payload_string(payload, "reset_boundary"),
            replay_boundary=_optional_payload_string(payload, "replay_boundary"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "temporal_contract_id": self.temporal_contract_id,
            "time_domain": self.time_domain.value,
            "clock_authority": self.clock_authority,
            "event_points": [point.value for point in self.event_points],
            "observation_point": self.observation_point,
            "backend_disclosure_refs": list(self.backend_disclosure_refs),
            "reset_boundary": self.reset_boundary,
            "replay_boundary": self.replay_boundary,
        }

    def __post_init__(self) -> None:
        _validate_required_string(
            self.temporal_contract_id,
            "participant temporal temporal_contract_id must be a non-empty string",
        )
        if not isinstance(self.time_domain, ParticipantTimeDomain):
            raise TypeError("time_domain must be a ParticipantTimeDomain")
        _validate_required_string(self.clock_authority, "participant temporal clock_authority must be non-empty")
        if not isinstance(self.event_points, tuple):
            raise TypeError("event_points must be a tuple")
        if not self.event_points:
            raise ValueError("participant temporal event_points must be non-empty")
        if any(not isinstance(point, ParticipantTemporalEventPoint) for point in self.event_points):
            raise TypeError("event_points must contain ParticipantTemporalEventPoint values")
        if len(set(self.event_points)) != len(self.event_points):
            raise ValueError("participant temporal event_points must be unique")
        _validate_required_string(self.observation_point, "participant temporal observation_point must be non-empty")
        _tuple_of_non_empty_strings(self.backend_disclosure_refs, field_name="backend_disclosure_refs")
        _validate_optional_string(self.reset_boundary, "reset_boundary must be a non-empty string or None")
        _validate_optional_string(self.replay_boundary, "replay_boundary must be a non-empty string or None")


@dataclass(frozen=True)
class ParticipantTemporalStateTransition:
    """Abstract SEM-213 deadline / dwell / timeout state transition."""

    temporal_contract_id: str
    from_state: ParticipantTemporalState
    to_state: ParticipantTemporalState
    event_point: ParticipantTemporalEventPoint
    time_domain: ParticipantTimeDomain
    clock_authority: str
    boundary_ref: str
    evidence_refs: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ParticipantTemporalStateTransition":
        if not isinstance(payload, Mapping):
            raise TypeError("participant temporal state transition must be a mapping")
        missing = [
            key
            for key in (
                "temporal_contract_id",
                "from_state",
                "to_state",
                "event_point",
                "time_domain",
                "clock_authority",
                "boundary_ref",
                "evidence_refs",
            )
            if key not in payload
        ]
        if missing:
            raise ValueError("participant temporal state transition is missing required fields: " + ", ".join(missing))
        return cls(
            temporal_contract_id=str(payload.get("temporal_contract_id")),
            from_state=_participant_temporal_state_from_payload(payload.get("from_state")),
            to_state=_participant_temporal_state_from_payload(payload.get("to_state")),
            event_point=_participant_temporal_event_point_from_payload(payload.get("event_point")),
            time_domain=_participant_time_domain_from_payload(payload.get("time_domain")),
            clock_authority=str(payload.get("clock_authority")),
            boundary_ref=str(payload.get("boundary_ref")),
            evidence_refs=_tuple_of_non_empty_strings(payload.get("evidence_refs"), field_name="evidence_refs"),
        )

    def __post_init__(self) -> None:
        _validate_required_string(
            self.temporal_contract_id,
            "participant temporal temporal_contract_id must be a non-empty string",
        )
        if not isinstance(self.from_state, ParticipantTemporalState):
            raise TypeError("from_state must be a ParticipantTemporalState")
        if not isinstance(self.to_state, ParticipantTemporalState):
            raise TypeError("to_state must be a ParticipantTemporalState")
        if not isinstance(self.event_point, ParticipantTemporalEventPoint):
            raise TypeError("event_point must be a ParticipantTemporalEventPoint")
        if not isinstance(self.time_domain, ParticipantTimeDomain):
            raise TypeError("time_domain must be a ParticipantTimeDomain")
        _validate_required_string(self.clock_authority, "participant temporal clock_authority must be non-empty")
        _validate_required_string(self.boundary_ref, "participant temporal boundary_ref must be non-empty")
        evidence_refs = _tuple_of_non_empty_strings(self.evidence_refs, field_name="evidence_refs")
        if not evidence_refs:
            raise ValueError("participant temporal state transitions require evidence_refs")


def _participant_temporal_state_transition_from_payload(
    value: ParticipantTemporalStateTransition | Mapping[str, Any],
) -> ParticipantTemporalStateTransition:
    if isinstance(value, ParticipantTemporalStateTransition):
        return value
    return ParticipantTemporalStateTransition.from_payload(value)


def iter_participant_temporal_state_machine_violations(
    transitions: Iterable[ParticipantTemporalStateTransition | Mapping[str, Any]],
) -> Iterator[tuple[str, str]]:
    """Yield SEM-213 abstract state-machine violations."""

    prior_state: dict[str, ParticipantTemporalState] = {}
    domain_authority: dict[str, tuple[ParticipantTimeDomain, str]] = {}
    terminal_states = {ParticipantTemporalState.DEADLINE_MISSED, ParticipantTemporalState.TIMEOUT}
    boundary_events = {ParticipantTemporalEventPoint.RESET, ParticipantTemporalEventPoint.REPLAY}
    boundary_states = {ParticipantTemporalState.RESET, ParticipantTemporalState.REPLAY_BOUNDARY}
    cadence_guard_events = {
        ParticipantTemporalEventPoint.SUBMIT,
        ParticipantTemporalEventPoint.START,
        ParticipantTemporalEventPoint.OBSERVED,
        ParticipantTemporalEventPoint.EFFECTIVE,
    }
    cadence_ready_states = {
        ParticipantTemporalState.CADENCE_READY,
        ParticipantTemporalState.ELIGIBLE,
        ParticipantTemporalState.RESET,
        ParticipantTemporalState.REPLAY_BOUNDARY,
    }

    for index, raw_transition in enumerate(transitions):
        locator = f"participant temporal state transition[{index}]"
        try:
            transition = _participant_temporal_state_transition_from_payload(raw_transition)
        except (TypeError, ValueError) as exc:
            yield (locator, f"participant temporal state transition is invalid: {exc}")
            continue

        key = transition.temporal_contract_id
        observed_domain_authority = (transition.time_domain, transition.clock_authority)
        if key in domain_authority and domain_authority[key] != observed_domain_authority:
            expected_domain, expected_authority = domain_authority[key]
            yield (
                locator,
                f"temporal contract {key!r} changed time domain or clock authority from "
                f"{expected_domain.value}/{expected_authority!r} to "
                f"{transition.time_domain.value}/{transition.clock_authority!r}",
            )
        else:
            domain_authority[key] = observed_domain_authority

        crosses_boundary = transition.event_point in boundary_events or transition.to_state in boundary_states
        if (
            key in prior_state
            and transition.from_state != prior_state[key]
            and prior_state[key] not in boundary_states
            and not crosses_boundary
        ):
            yield (
                locator,
                f"temporal contract {key!r} transition from_state {transition.from_state.value!r} "
                f"does not match prior to_state {prior_state[key].value!r}",
            )

        if (
            transition.from_state == ParticipantTemporalState.CADENCE_WAITING
            and transition.event_point in cadence_guard_events
            and not crosses_boundary
        ):
            yield (locator, "cadence repeated event requires cadence_ready or reset/replay boundary before reuse")
        elif (
            transition.to_state == ParticipantTemporalState.CADENCE_WAITING
            and transition.from_state not in cadence_ready_states
            and prior_state.get(key) not in cadence_ready_states
            and not crosses_boundary
        ):
            yield (locator, "cadence_waiting requires prior cadence_ready or eligible state in the same segment")

        if (
            transition.to_state == ParticipantTemporalState.DWELL_SATISFIED
            and transition.from_state != ParticipantTemporalState.DWELL_ACTIVE
            and prior_state.get(key) != ParticipantTemporalState.DWELL_ACTIVE
        ):
            yield (locator, "dwell_satisfied requires prior dwell_active state in the same temporal segment")

        if (
            transition.from_state in terminal_states
            and transition.event_point not in boundary_events
            and transition.to_state not in boundary_states
        ):
            yield (locator, "terminal temporal state requires reset or replay boundary before reuse")

        prior_state[key] = transition.to_state


def _optional_payload_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return str(value) if value is not None else None


def _participant_behavior_event_type_from_payload(value: Any) -> ParticipantBehaviorHistoryEventType:
    if isinstance(value, ParticipantBehaviorHistoryEventType):
        return value
    return ParticipantBehaviorHistoryEventType(str(value))


def _participant_interaction_class_from_payload(value: Any) -> ParticipantInteractionClass | None:
    if value is None:
        return None
    if isinstance(value, ParticipantInteractionClass):
        return value
    return ParticipantInteractionClass(str(value))


def _participant_lifecycle_phase_from_payload(
    value: str | ParticipantRuntimeLifecyclePhase | None,
) -> ParticipantRuntimeLifecyclePhase | None:
    if value is None:
        return None
    if isinstance(value, ParticipantRuntimeLifecyclePhase):
        return value
    return ParticipantRuntimeLifecyclePhase(str(value))


def _participant_phase_realization_from_payload(
    value: str | ParticipantPhaseRealization | None,
) -> ParticipantPhaseRealization | None:
    if value is None:
        return None
    if isinstance(value, ParticipantPhaseRealization):
        return value
    return ParticipantPhaseRealization(str(value))


def _participant_admission_disposition_from_payload(
    value: str | ParticipantAdmissionDisposition | None,
) -> ParticipantAdmissionDisposition | None:
    if value is None:
        return None
    if isinstance(value, ParticipantAdmissionDisposition):
        return value
    return ParticipantAdmissionDisposition(str(value))


def _participant_lifecycle_operation_state_from_payload(
    value: str | ParticipantLifecycleOperationState | None,
) -> ParticipantLifecycleOperationState | None:
    if value is None:
        return None
    if isinstance(value, ParticipantLifecycleOperationState):
        return value
    return ParticipantLifecycleOperationState(str(value))


def _participant_behavior_shared_state_refs_from_payload(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise TypeError("shared_state_refs must be a list of strings")
    return tuple(str(ref) for ref in value)


def _participant_action_result_from_payload(value: Any) -> ParticipantActionResult | None:
    if value is None:
        return None
    if isinstance(value, ParticipantActionResult):
        return value
    return ParticipantActionResult.from_payload(value)


def _participant_attribution_edges_from_payload(value: Any) -> tuple[ParticipantAttributionEdge, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise TypeError("attribution_edges must be a list of participant attribution edges")
    return tuple(
        edge if isinstance(edge, ParticipantAttributionEdge) else ParticipantAttributionEdge.from_payload(edge)
        for edge in value
    )


def _participant_temporal_contexts_from_payload(value: Any) -> tuple[ParticipantTemporalRuntimeContext, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise TypeError("temporal_contexts must be a list of participant temporal runtime contexts")
    return tuple(
        context
        if isinstance(context, ParticipantTemporalRuntimeContext)
        else ParticipantTemporalRuntimeContext.from_payload(context)
        for context in value
    )


def _participant_behavior_details_from_payload(value: Any) -> dict[str, Any]:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise TypeError("participant behavior details must be a mapping")
    details = dict(value)
    for empty_ref_key in ("visible_refs", "disclosed_refs", "evidence_refs"):
        refs = details.get(empty_ref_key)
        if isinstance(refs, (list, tuple)) and not refs:
            details.pop(empty_ref_key)
    return details


@dataclass(frozen=True)
class ParticipantBehaviorHistoryEvent:
    """Internal normalized participant behavior history event.

    The canonical record keeps actor provenance and compiled behavior-contract
    addresses. Role-neutral interpretation is a projection over those records,
    not a reason to treat raw action names or backend-native logs as behavior
    semantics.
    """

    event_type: ParticipantBehaviorHistoryEventType
    timestamp: str
    participant_address: str
    episode_id: str
    action_instance_id: str
    action_contract_address: str | None = None
    observation_boundary_address: str | None = None
    observation_status: ParticipantObservationStatus | None = None
    actor_provenance: str | None = None
    lifecycle_phase: ParticipantRuntimeLifecyclePhase | None = None
    phase_realization: ParticipantPhaseRealization | None = None
    admission_disposition: ParticipantAdmissionDisposition | None = None
    operation_ref: str | None = None
    operation_state: ParticipantLifecycleOperationState | None = None
    state_transition_kind: str | None = None
    post_state_digest: str | None = None
    joint_action_set_id: str | None = None
    realized_order: int | None = None
    interaction_class: ParticipantInteractionClass | None = None
    interaction_ref: str | None = None
    shared_state_refs: tuple[str, ...] = ()
    action_result: ParticipantActionResult | None = None
    attribution_edges: tuple[ParticipantAttributionEdge, ...] = ()
    outcome_interpretations: tuple[ParticipantOutcomeInterpretationRecord, ...] = ()
    temporal_contexts: tuple[ParticipantTemporalRuntimeContext, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> "ParticipantBehaviorHistoryEvent":
        if not isinstance(payload, Mapping):
            raise TypeError("participant behavior history event must be a mapping")
        missing_keys = [
            key
            for key in (
                "event_type",
                "timestamp",
                "participant_address",
                "episode_id",
                "action_instance_id",
            )
            if key not in payload
        ]
        if missing_keys:
            raise ValueError(
                "participant behavior history event is missing required fields: " + ", ".join(missing_keys)
            )
        return cls(
            event_type=_participant_behavior_event_type_from_payload(payload.get("event_type")),
            timestamp=str(payload.get("timestamp")),
            participant_address=str(payload.get("participant_address")),
            episode_id=str(payload.get("episode_id")),
            action_instance_id=str(payload.get("action_instance_id")),
            action_contract_address=_optional_payload_string(payload, "action_contract_address"),
            observation_boundary_address=_optional_payload_string(payload, "observation_boundary_address"),
            observation_status=_participant_observation_status_from_payload(payload.get("observation_status")),
            actor_provenance=_optional_payload_string(payload, "actor_provenance"),
            lifecycle_phase=_participant_lifecycle_phase_from_payload(payload.get("lifecycle_phase")),
            phase_realization=_participant_phase_realization_from_payload(payload.get("phase_realization")),
            admission_disposition=_participant_admission_disposition_from_payload(payload.get("admission_disposition")),
            operation_ref=_optional_payload_string(payload, "operation_ref"),
            operation_state=_participant_lifecycle_operation_state_from_payload(payload.get("operation_state")),
            state_transition_kind=_optional_payload_string(payload, "state_transition_kind"),
            post_state_digest=_optional_payload_string(payload, "post_state_digest"),
            joint_action_set_id=_optional_payload_string(payload, "joint_action_set_id"),
            realized_order=payload.get("realized_order"),
            interaction_class=_participant_interaction_class_from_payload(payload.get("interaction_class")),
            interaction_ref=_optional_payload_string(payload, "interaction_ref"),
            shared_state_refs=_participant_behavior_shared_state_refs_from_payload(
                payload.get("shared_state_refs", ())
            ),
            action_result=_participant_action_result_from_payload(payload.get("action_result")),
            attribution_edges=_participant_attribution_edges_from_payload(payload.get("attribution_edges", ())),
            outcome_interpretations=_participant_outcome_interpretation_records_from_payload(
                payload.get("outcome_interpretations", ())
            ),
            temporal_contexts=_participant_temporal_contexts_from_payload(payload.get("temporal_contexts", ())),
            details=_participant_behavior_details_from_payload(payload.get("details", {})),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "participant_address": self.participant_address,
            "episode_id": self.episode_id,
            "action_instance_id": self.action_instance_id,
            "action_contract_address": self.action_contract_address,
            "observation_boundary_address": self.observation_boundary_address,
            "observation_status": self.observation_status.value if self.observation_status is not None else None,
            "actor_provenance": self.actor_provenance,
            "lifecycle_phase": self.lifecycle_phase.value if self.lifecycle_phase is not None else None,
            "phase_realization": self.phase_realization.value if self.phase_realization is not None else None,
            "admission_disposition": (
                self.admission_disposition.value if self.admission_disposition is not None else None
            ),
            "operation_ref": self.operation_ref,
            "operation_state": self.operation_state.value if self.operation_state is not None else None,
            "state_transition_kind": self.state_transition_kind,
            "post_state_digest": self.post_state_digest,
            "joint_action_set_id": self.joint_action_set_id,
            "realized_order": self.realized_order,
            "interaction_class": self.interaction_class.value if self.interaction_class is not None else None,
            "interaction_ref": self.interaction_ref,
            "shared_state_refs": list(self.shared_state_refs),
            "action_result": self.action_result.to_payload() if self.action_result is not None else None,
            "attribution_edges": [edge.to_payload() for edge in self.attribution_edges],
            "outcome_interpretations": [record.to_payload() for record in self.outcome_interpretations],
            "temporal_contexts": [context.to_payload() for context in self.temporal_contexts],
            "details": dict(self.details),
        }

    def __post_init__(self) -> None:
        self._validate_common_fields()
        self._validate_event_type_fields()

    def _validate_common_fields(self) -> None:
        if not isinstance(self.event_type, ParticipantBehaviorHistoryEventType):
            raise TypeError("event_type must be a ParticipantBehaviorHistoryEventType")
        self._validate_required_string(self.timestamp, "participant behavior timestamp must be a non-empty string")
        self._validate_required_string(
            self.participant_address,
            "participant behavior participant_address must be a non-empty string",
        )
        self._validate_required_string(self.episode_id, "participant behavior episode_id must be a non-empty string")
        self._validate_required_string(self.action_instance_id, "action_instance_id must be a non-empty string")
        self._validate_optional_address(
            self.action_contract_address,
            prefix=_PARTICIPANT_ACTION_CONTRACT_PREFIX,
            message="action_contract_address must be a compiled participant action contract address",
        )
        self._validate_optional_address(
            self.observation_boundary_address,
            prefix=_PARTICIPANT_OBSERVATION_BOUNDARY_PREFIX,
            message="observation_boundary_address must be a compiled participant observation boundary address",
        )
        if self.observation_status is not None and not isinstance(
            self.observation_status,
            ParticipantObservationStatus,
        ):
            raise TypeError("observation_status must be a ParticipantObservationStatus or None")
        self._validate_optional_string(self.actor_provenance, "actor_provenance must be a non-empty string or None")
        self._validate_lifecycle_fields()
        self._validate_optional_state_fields()
        self._validate_realized_order()
        self._validate_interaction_type()
        if not isinstance(self.shared_state_refs, tuple):
            raise TypeError("shared_state_refs must be a tuple")
        for ref in self.shared_state_refs:
            self._validate_required_string(ref, "shared_state_refs entries must be non-empty strings")
        if len(set(self.shared_state_refs)) != len(self.shared_state_refs):
            raise ValueError("shared_state_refs entries must be unique")
        self._validate_interaction_fields()
        self._validate_action_result_type()
        self._validate_attribution_edge_types()
        self._validate_outcome_interpretation_types()
        self._validate_temporal_context_types()
        if not isinstance(self.details, dict):
            raise TypeError("participant behavior details must be a dict")

    def _validate_optional_state_fields(self) -> None:
        self._validate_optional_string(
            self.state_transition_kind,
            "state_transition_kind must be a non-empty string or None",
        )
        self._validate_optional_string(self.post_state_digest, "post_state_digest must be a non-empty string or None")
        self._validate_optional_string(
            self.joint_action_set_id,
            "joint_action_set_id must be a non-empty string or None",
        )

    def _validate_lifecycle_fields(self) -> None:
        self._validate_lifecycle_enum_types()
        self._validate_optional_string(self.operation_ref, "operation_ref must be a non-empty string or None")
        messages = participant_lifecycle_field_violation_messages(
            event_type=self.event_type,
            lifecycle_phase=self.lifecycle_phase,
            phase_realization=self.phase_realization,
            admission_disposition=self.admission_disposition,
            operation_ref=self.operation_ref,
            operation_state=self.operation_state,
        )
        if messages:
            raise ValueError(messages[0])

    def _validate_lifecycle_enum_types(self) -> None:
        expectations = (
            (
                self.lifecycle_phase,
                ParticipantRuntimeLifecyclePhase,
                "lifecycle_phase must be a ParticipantRuntimeLifecyclePhase or None",
            ),
            (
                self.phase_realization,
                ParticipantPhaseRealization,
                "phase_realization must be a ParticipantPhaseRealization or None",
            ),
            (
                self.admission_disposition,
                ParticipantAdmissionDisposition,
                "admission_disposition must be a ParticipantAdmissionDisposition or None",
            ),
            (
                self.operation_state,
                ParticipantLifecycleOperationState,
                "operation_state must be a ParticipantLifecycleOperationState or None",
            ),
        )
        for value, enum_type, message in expectations:
            if value is not None and not isinstance(value, enum_type):
                raise TypeError(message)

    def _validate_realized_order(self) -> None:
        if self.realized_order is not None and (
            not isinstance(self.realized_order, int) or isinstance(self.realized_order, bool) or self.realized_order < 0
        ):
            raise TypeError("realized_order must be a non-negative integer or None")

    def _validate_interaction_type(self) -> None:
        if self.interaction_class is not None and not isinstance(self.interaction_class, ParticipantInteractionClass):
            raise TypeError("interaction_class must be a ParticipantInteractionClass or None")
        self._validate_optional_string(self.interaction_ref, "interaction_ref must be a non-empty string or None")

    def _validate_action_result_type(self) -> None:
        if self.action_result is not None and not isinstance(self.action_result, ParticipantActionResult):
            raise TypeError("action_result must be a ParticipantActionResult or None")

    def _validate_attribution_edge_types(self) -> None:
        if not isinstance(self.attribution_edges, tuple):
            raise TypeError("attribution_edges must be a tuple")
        if any(not isinstance(edge, ParticipantAttributionEdge) for edge in self.attribution_edges):
            raise TypeError("attribution_edges must contain ParticipantAttributionEdge values")
        if len({edge.edge_id for edge in self.attribution_edges}) != len(self.attribution_edges):
            raise ValueError("participant attribution edge_id values must be unique per event")
        if self.attribution_edges and self.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            raise ValueError("participant attribution edges are only allowed on observation_emitted events")

    def _validate_outcome_interpretation_types(self) -> None:
        if not isinstance(self.outcome_interpretations, tuple):
            raise TypeError("outcome_interpretations must be a tuple")
        if any(
            not isinstance(record, ParticipantOutcomeInterpretationRecord) for record in self.outcome_interpretations
        ):
            raise TypeError("outcome_interpretations must contain ParticipantOutcomeInterpretationRecord values")
        if len({record.interpretation_id for record in self.outcome_interpretations}) != len(
            self.outcome_interpretations
        ):
            raise ValueError("participant outcome interpretation_id values must be unique per event")
        if self.outcome_interpretations and self.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            raise ValueError("participant outcome interpretations are only allowed on observation_emitted events")

    def _validate_temporal_context_types(self) -> None:
        if not isinstance(self.temporal_contexts, tuple):
            raise TypeError("temporal_contexts must be a tuple")
        if any(not isinstance(context, ParticipantTemporalRuntimeContext) for context in self.temporal_contexts):
            raise TypeError("temporal_contexts must contain ParticipantTemporalRuntimeContext values")
        if len({context.temporal_contract_id for context in self.temporal_contexts}) != len(self.temporal_contexts):
            raise ValueError("participant temporal_contract_id values must be unique per event")

    @staticmethod
    def _validate_required_string(value: Any, message: str) -> None:
        if not isinstance(value, str) or not value:
            raise TypeError(message)

    @staticmethod
    def _validate_optional_string(value: Any, message: str) -> None:
        if value is not None and (not isinstance(value, str) or not value):
            raise TypeError(message)

    @staticmethod
    def _validate_optional_address(value: str | None, *, prefix: str, message: str) -> None:
        if value is not None and (not isinstance(value, str) or not value.startswith(prefix)):
            raise ValueError(message)

    def _validate_event_type_fields(self) -> None:
        validators = {
            ParticipantBehaviorHistoryEventType.ACTION_ATTEMPTED: self._validate_action_attempted_fields,
            ParticipantBehaviorHistoryEventType.STATE_TRANSITION_RECORDED: self._validate_state_transition_fields,
            ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED: self._validate_observation_emitted_fields,
        }
        validators[self.event_type]()

    def _validate_interaction_fields(self) -> None:
        if self.joint_action_set_id is None and self.realized_order is not None:
            raise ValueError("realized_order requires joint_action_set_id")
        if self.joint_action_set_id is not None and self.realized_order is None:
            raise ValueError("joint_action_set_id requires realized_order")
        if self.interaction_class is None:
            if self.interaction_ref is not None:
                raise ValueError("interaction_ref requires interaction_class")
            return
        if self.joint_action_set_id is None:
            raise ValueError("interaction_class requires joint_action_set_id and realized_order")
        if (
            self.interaction_class
            in {
                ParticipantInteractionClass.COORDINATION,
                ParticipantInteractionClass.INTERFERENCE,
            }
            and self.interaction_ref is None
        ):
            raise ValueError(f"{self.interaction_class.value} events require interaction_ref")
        if (
            self.interaction_class
            in {
                ParticipantInteractionClass.CONTENTION,
                ParticipantInteractionClass.SHARED_STATE_CHANGE,
            }
            and not self.shared_state_refs
        ):
            raise ValueError(f"{self.interaction_class.value} events require shared_state_refs")

    def _validate_action_attempted_fields(self) -> None:
        if self.action_contract_address is None:
            raise ValueError("action_attempted events require action_contract_address")
        if self.actor_provenance is None:
            raise ValueError("action_attempted events require actor_provenance")
        if self.observation_boundary_address is not None or self.observation_status is not None:
            raise ValueError("action_attempted events may not report observation fields")
        if self.state_transition_kind is not None or self.post_state_digest is not None:
            raise ValueError("action_attempted events may not report state-transition fields")
        if self.action_result is not None:
            raise ValueError("action_attempted events may not report action_result")

    def _validate_state_transition_fields(self) -> None:
        if self.action_contract_address is None:
            raise ValueError("state_transition_recorded events require action_contract_address")
        if self.state_transition_kind is None:
            raise ValueError("state_transition_recorded events require state_transition_kind")
        if self.post_state_digest is None:
            raise ValueError("state_transition_recorded events require post_state_digest")
        if self.observation_boundary_address is not None or self.observation_status is not None:
            raise ValueError("state_transition_recorded events may not report observation fields")
        if self.action_result is not None:
            raise ValueError("state_transition_recorded events may not report action_result")

    def _validate_observation_emitted_fields(self) -> None:
        if self.action_contract_address is None:
            raise ValueError("observation_emitted events require action_contract_address")
        if self.observation_boundary_address is None:
            raise ValueError("observation_emitted events require observation_boundary_address")
        if self.observation_status is None:
            raise ValueError("observation_emitted events require observation_status")
        if self.observation_status == ParticipantObservationStatus.TERMINAL and self.post_state_digest is None:
            raise ValueError("terminal observation_emitted events require post_state_digest")
        if self.state_transition_kind is not None:
            raise ValueError("observation_emitted events may not report state_transition_kind")
        if self.action_result is not None:
            self._validate_action_result_scope()
        self._validate_attribution_edges()
        self._validate_outcome_interpretations()

    def _validate_action_result_scope(self) -> None:
        if self.action_result is None:
            return
        if self.action_result.participant_address != self.participant_address:
            raise ValueError("action_result participant_address must match event participant_address")
        if self.action_result.episode_id != self.episode_id:
            raise ValueError("action_result episode_id must match event episode_id")
        if self.action_result.action_instance_id != self.action_instance_id:
            raise ValueError("action_result action_instance_id must match event action_instance_id")
        if self.action_result.action_contract_address != self.action_contract_address:
            raise ValueError("action_result action_contract_address must match event action_contract_address")
        if (
            self.observation_status in _PARTICIPANT_TERMINAL_OBSERVATION_STATUSES
            and self.action_result.status == ParticipantActionResultStatus.ACCEPTED
        ):
            raise ValueError("terminal observation action_result must report a terminal status")

    def _validate_attribution_edges(self) -> None:
        for edge in self.attribution_edges:
            if edge.participant_address != self.participant_address:
                raise ValueError("attribution edge participant_address must match event participant_address")
            if edge.episode_id != self.episode_id:
                raise ValueError("attribution edge episode_id must match event episode_id")
            if self.action_result is not None:
                if edge.observation_point != self.action_result.observation_point:
                    raise ValueError("attribution edge observation_point must match action_result observation_point")
            elif not _observation_point_matches_action_instance(edge.observation_point, self.action_instance_id):
                raise ValueError("attribution edge observation_point must be anchored to action_instance_id")
            self._validate_attribution_candidate_grounding(edge)

    def _validate_outcome_interpretations(self) -> None:
        for record in self.outcome_interpretations:
            if record.participant_address != self.participant_address:
                raise ValueError("outcome interpretation participant_address must match event participant_address")
            if record.episode_id != self.episode_id:
                raise ValueError("outcome interpretation episode_id must match event episode_id")
            if self.action_result is not None:
                if record.observation_point != self.action_result.observation_point:
                    raise ValueError(
                        "outcome interpretation observation_point must match action_result observation_point"
                    )
            elif not _observation_point_matches_action_instance(record.observation_point, self.action_instance_id):
                raise ValueError("outcome interpretation observation_point must be anchored to action_instance_id")

    def _validate_attribution_candidate_grounding(self, edge: ParticipantAttributionEdge) -> None:
        allowed_action_refs = {self.action_instance_id}
        if self.action_contract_address is not None:
            allowed_action_refs.add(self.action_contract_address)
        if edge.cause_candidate.candidate_kind == ParticipantAttributionCandidateKind.ACTION:
            if edge.cause_candidate.ref not in allowed_action_refs:
                raise ValueError("attribution edge action cause_candidate must match the event action")
        elif edge.cause_candidate.ref not in self._attribution_grounded_refs():
            raise ValueError(f"attribution edge cause_candidate {edge.cause_candidate.ref!r} is not grounded")

        if edge.effect_candidate.candidate_kind in OUTCOME_ATTRIBUTION_CANDIDATE_KINDS:
            return
        if edge.effect_candidate.ref not in self._attribution_grounded_refs():
            raise ValueError(f"attribution edge effect_candidate {edge.effect_candidate.ref!r} is not grounded")

    def _attribution_grounded_refs(self) -> set[str]:
        refs: set[str] = {self.action_instance_id}
        if self.action_contract_address is not None:
            refs.add(self.action_contract_address)
        if self.observation_boundary_address is not None:
            refs.add(self.observation_boundary_address)
        if self.post_state_digest is not None:
            refs.add(self.post_state_digest)
        for key in _PARTICIPANT_OBSERVATION_DETAIL_REF_KEYS:
            value = self.details.get(key)
            if isinstance(value, (list, tuple)):
                refs.update(str(item) for item in value if isinstance(item, str) and item)
        if self.action_result is None:
            return refs
        refs.update(self.action_result.observations)
        refs.update(self.action_result.evidence_refs)
        for precondition in self.action_result.preconditions:
            refs.update(precondition.support_refs)
            refs.update(precondition.evidence_refs)
        for effect in self.action_result.effects:
            refs.update(effect.target_refs)
            refs.update(effect.evidence_refs)
        return refs


_PARTICIPANT_TERMINAL_OBSERVATION_STATUSES = frozenset(
    {
        ParticipantObservationStatus.TERMINAL,
        ParticipantObservationStatus.ORPHANED_ACTION,
    }
)
_PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS = frozenset({"observable", "discovered", "inferred", "disclosed", "deceptive"})
_PARTICIPANT_OBSERVATION_DETAIL_REF_KEYS = ("visible_refs", "disclosed_refs", "evidence_refs")
_PARTICIPANT_OBSERVATION_DETAIL_KEYS = frozenset(_PARTICIPANT_OBSERVATION_DETAIL_REF_KEYS)


def _participant_behavior_detail_refs(
    event: ParticipantBehaviorHistoryEvent,
    *,
    key: str,
    locator: str,
) -> tuple[tuple[str, ...], list[tuple[str, str]]]:
    if key not in event.details:
        return (), []
    value = event.details[key]
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return (), [(locator, f"observation details field {key!r} must be a list of strings")]
    items = tuple(value)
    refs = tuple(str(ref) for ref in items if isinstance(ref, str) and ref)
    if len(refs) != len(items):
        return (), [(locator, f"observation details field {key!r} must contain only non-empty strings")]
    if len(set(refs)) != len(refs):
        return (), [(locator, f"observation details field {key!r} must not contain duplicate refs")]
    return refs, []


def _participant_behavior_detail_shape_violations(
    event: ParticipantBehaviorHistoryEvent,
    *,
    locator: str,
) -> list[tuple[str, str]]:
    if not event.details:
        return []
    violations: list[tuple[str, str]] = []
    if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
        violations.append((locator, "participant behavior details are only allowed on observation_emitted events"))
    unsupported_keys = sorted(str(key) for key in event.details if key not in _PARTICIPANT_OBSERVATION_DETAIL_KEYS)
    if unsupported_keys:
        allowed = ", ".join(_PARTICIPANT_OBSERVATION_DETAIL_REF_KEYS)
        unsupported = ", ".join(unsupported_keys)
        violations.append(
            (
                locator,
                f"observation details may only contain {allowed}; unsupported fields: {unsupported}",
            )
        )
    return violations


def _participant_behavior_timeline_relations(
    boundary: ParticipantObservationBoundaryRuntime,
) -> tuple[tuple[int, dict[str, str]], ...]:
    relations: list[tuple[int, dict[str, str]]] = []
    for snapshot in boundary.view_relation_timeline:
        order = snapshot.get("effective_order")
        raw_relation = snapshot.get("view_relation", {})
        if not isinstance(order, int) or isinstance(order, bool) or not isinstance(raw_relation, Mapping):
            continue
        relations.append((order, {str(ref): str(disposition) for ref, disposition in raw_relation.items()}))
    return tuple(sorted(relations, key=lambda item: item[0]))


def _participant_behavior_initial_view_relation(
    boundary: ParticipantObservationBoundaryRuntime,
) -> dict[str, str]:
    initial_relation: dict[str, str] = {}
    for order, relation in _participant_behavior_timeline_relations(boundary):
        if order > -1:
            break
        initial_relation = dict(relation)
    return initial_relation


def _participant_behavior_view_relation_deltas_by_order(
    boundary: ParticipantObservationBoundaryRuntime,
) -> dict[int, dict[str, str]]:
    deltas: dict[int, dict[str, str]] = {}
    previous_relation: dict[str, str] | None = None
    for order, relation in _participant_behavior_timeline_relations(boundary):
        if previous_relation is None:
            previous_relation = relation
            continue
        deltas[order] = {
            ref: disposition for ref, disposition in relation.items() if previous_relation.get(ref) != disposition
        }
        previous_relation = relation
    return deltas


def _participant_behavior_transition_effective_order(transition: Mapping[str, Any]) -> int | None:
    order = transition.get("effective_order")
    if not isinstance(order, int) or isinstance(order, bool):
        return None
    return order


def _participant_behavior_transition_delta(
    transition: Mapping[str, Any],
    *,
    deltas_by_order: Mapping[int, Mapping[str, str]],
) -> dict[str, str]:
    information_ref = transition.get("information_ref")
    to_disposition = transition.get("to_disposition")
    if isinstance(information_ref, str) and information_ref and isinstance(to_disposition, str) and to_disposition:
        return {information_ref: to_disposition}
    order = _participant_behavior_transition_effective_order(transition)
    if order is None:
        return {}
    return dict(deltas_by_order.get(order, {}))


def _participant_behavior_transition_matches_relation(
    transition: Mapping[str, Any],
    *,
    relation: Mapping[str, str],
) -> bool:
    information_ref = transition.get("information_ref")
    from_disposition = transition.get("from_disposition")
    if not isinstance(information_ref, str) or not information_ref:
        return True
    if not isinstance(from_disposition, str) or not from_disposition:
        return True
    return relation.get(information_ref) == from_disposition


def _participant_behavior_observation_detail_refs(
    event: ParticipantBehaviorHistoryEvent,
    *,
    locator: str,
) -> tuple[dict[str, tuple[str, ...]], list[tuple[str, str]]]:
    detail_refs: dict[str, tuple[str, ...]] = {}
    violations: list[tuple[str, str]] = []
    for key in _PARTICIPANT_OBSERVATION_DETAIL_REF_KEYS:
        refs, ref_violations = _participant_behavior_detail_refs(event, key=key, locator=locator)
        detail_refs[key] = refs
        violations.extend(ref_violations)
    return detail_refs, violations


def _participant_behavior_disposition_ref_violations(
    *,
    locator: str,
    refs: tuple[str, ...],
    relation: Mapping[str, str],
    allowed_dispositions: frozenset[str],
    effective_order: int,
    detail_key: str,
    allowed_label: str,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for ref in refs:
        disposition = relation.get(ref)
        if disposition in allowed_dispositions:
            continue
        violations.append(
            (
                locator,
                (
                    f"observation {detail_key} may only contain {allowed_label} refs at "
                    f"effective_order {effective_order}: "
                    f"{ref!r} has disposition {disposition!r}"
                ),
            )
        )
    return violations


def _participant_behavior_evidence_ref_violations(
    *,
    locator: str,
    refs: tuple[str, ...],
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for ref in refs:
        if ref in boundary.evidence_refs or relation.get(ref) == "evidence_only":
            continue
        violations.append(
            (
                locator,
                (
                    "observation evidence_refs may only contain boundary evidence refs at "
                    f"effective_order {effective_order}: {ref!r}"
                ),
            )
        )
    return violations


def _participant_behavior_visibility_detail_violations(
    *,
    locator: str,
    detail_refs: Mapping[str, tuple[str, ...]],
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    return [
        *_participant_behavior_disposition_ref_violations(
            locator=locator,
            refs=detail_refs["visible_refs"],
            relation=relation,
            allowed_dispositions=_PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS,
            effective_order=effective_order,
            detail_key="visible_refs",
            allowed_label="participant-visible",
        ),
        *_participant_behavior_disposition_ref_violations(
            locator=locator,
            refs=detail_refs["disclosed_refs"],
            relation=relation,
            allowed_dispositions=frozenset({"disclosed"}),
            effective_order=effective_order,
            detail_key="disclosed_refs",
            allowed_label="disclosed",
        ),
        *_participant_behavior_evidence_ref_violations(
            locator=locator,
            refs=detail_refs["evidence_refs"],
            boundary=boundary,
            relation=relation,
            effective_order=effective_order,
        ),
    ]


def _participant_behavior_action_result_visible_ref_violations(
    *,
    locator: str,
    owner_label: str,
    field_name: str,
    refs: tuple[str, ...],
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    owner_prefix = f" {owner_label}" if owner_label else ""
    for ref in refs:
        disposition = relation.get(ref)
        if disposition is None and ref in boundary.hidden_refs:
            disposition = "hidden"
        if disposition is None:
            continue
        if disposition in _PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS:
            continue
        violations.append(
            (
                locator,
                (
                    f"action_result{owner_prefix} {field_name} {ref!r} is not participant-visible "
                    f"at effective_order {effective_order}: disposition {disposition!r}"
                ),
            )
        )
    return violations


def _participant_behavior_action_result_evidence_ref_violations(
    *,
    locator: str,
    owner_label: str,
    field_name: str,
    refs: tuple[str, ...],
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    owner_prefix = f" {owner_label}" if owner_label else ""
    for ref in refs:
        disposition = relation.get(ref)
        if disposition is None and ref in boundary.hidden_refs:
            disposition = "hidden"
        if ref in boundary.evidence_refs or disposition == "evidence_only":
            continue
        suffix = f": disposition {disposition!r}" if disposition is not None else ""
        violations.append(
            (
                locator,
                (
                    f"action_result{owner_prefix} {field_name} {ref!r} is not authorized evidence "
                    f"at effective_order {effective_order}{suffix}"
                ),
            )
        )
    return violations


def _participant_behavior_action_result_ref_authorization_violations(
    *,
    event: ParticipantBehaviorHistoryEvent,
    locator: str,
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    if event.action_result is None:
        return []
    violations: list[tuple[str, str]] = []
    for precondition in event.action_result.preconditions:
        owner_label = f"precondition {precondition.precondition_id!r}"
        violations.extend(
            _participant_behavior_action_result_visible_ref_violations(
                locator=locator,
                owner_label=owner_label,
                field_name="support_ref",
                refs=precondition.support_refs,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
        violations.extend(
            _participant_behavior_action_result_evidence_ref_violations(
                locator=locator,
                owner_label=owner_label,
                field_name="evidence_ref",
                refs=precondition.evidence_refs,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
    for effect in event.action_result.effects:
        owner_label = f"effect {effect.effect_id!r}"
        violations.extend(
            _participant_behavior_action_result_visible_ref_violations(
                locator=locator,
                owner_label=owner_label,
                field_name="target_ref",
                refs=effect.target_refs,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
        violations.extend(
            _participant_behavior_action_result_evidence_ref_violations(
                locator=locator,
                owner_label=owner_label,
                field_name="evidence_ref",
                refs=effect.evidence_refs,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
    violations.extend(
        _participant_behavior_action_result_evidence_ref_violations(
            locator=locator,
            owner_label="",
            field_name="evidence_ref",
            refs=event.action_result.evidence_refs,
            boundary=boundary,
            relation=relation,
            effective_order=effective_order,
        )
    )
    return violations


def _participant_behavior_attribution_evidence_ref_violations(
    *,
    locator: str,
    edge: ParticipantAttributionEdge,
    refs: tuple[str, ...],
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for ref in refs:
        disposition = relation.get(ref)
        if disposition is None and ref in boundary.hidden_refs:
            disposition = "hidden"
        if ref in boundary.evidence_refs or disposition == "evidence_only":
            continue
        suffix = f": disposition {disposition!r}" if disposition is not None else ""
        violations.append(
            (
                locator,
                (
                    f"attribution edge {edge.edge_id!r} evidence_ref {ref!r} is not authorized evidence "
                    f"at effective_order {effective_order}{suffix}"
                ),
            )
        )
    return violations


def _participant_behavior_attribution_candidate_ref_violations(
    *,
    locator: str,
    edge: ParticipantAttributionEdge,
    candidate: ParticipantAttributionCandidate,
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    if candidate.candidate_kind == ParticipantAttributionCandidateKind.ACTION:
        return []
    if candidate.candidate_kind == ParticipantAttributionCandidateKind.EVIDENCE:
        return _participant_behavior_attribution_evidence_ref_violations(
            locator=locator,
            edge=edge,
            refs=(candidate.ref,),
            boundary=boundary,
            relation=relation,
            effective_order=effective_order,
        )
    disposition = relation.get(candidate.ref)
    if disposition is None and candidate.ref in boundary.hidden_refs:
        disposition = "hidden"
    if disposition is None or disposition in _PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS:
        return []
    return [
        (
            locator,
            (
                f"attribution edge {edge.edge_id!r} {candidate.candidate_kind.value} candidate "
                f"{candidate.ref!r} is not participant-visible at effective_order {effective_order}: "
                f"disposition {disposition!r}"
            ),
        )
    ]


def _participant_behavior_attribution_ref_authorization_violations(
    *,
    event: ParticipantBehaviorHistoryEvent,
    locator: str,
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for edge in event.attribution_edges:
        violations.extend(
            _participant_behavior_attribution_evidence_ref_violations(
                locator=locator,
                edge=edge,
                refs=edge.evidence_refs,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
        violations.extend(
            _participant_behavior_attribution_candidate_ref_violations(
                locator=locator,
                edge=edge,
                candidate=edge.cause_candidate,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
        violations.extend(
            _participant_behavior_attribution_candidate_ref_violations(
                locator=locator,
                edge=edge,
                candidate=edge.effect_candidate,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
    return violations


def _participant_behavior_outcome_evidence_ref_violations(
    *,
    locator: str,
    record: ParticipantOutcomeInterpretationRecord,
    refs: tuple[str, ...],
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for ref in refs:
        disposition = relation.get(ref)
        if disposition is None and ref in boundary.hidden_refs:
            disposition = "hidden"
        if ref in boundary.evidence_refs or disposition == "evidence_only":
            continue
        suffix = f": disposition {disposition!r}" if disposition is not None else ""
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} evidence_ref {ref!r} "
                    f"is not authorized evidence at effective_order {effective_order}{suffix}"
                ),
            )
        )
    return violations


def _participant_behavior_outcome_provenance_ref_violations(
    *,
    locator: str,
    record: ParticipantOutcomeInterpretationRecord,
    refs: tuple[str, ...],
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for ref in refs:
        disposition = relation.get(ref)
        if disposition is None and ref in boundary.hidden_refs:
            disposition = "hidden"
        if ref in boundary.evidence_refs or disposition in {"evidence_only", "disclosed", "observable", "discovered"}:
            continue
        if ref not in boundary.hidden_refs and disposition not in {"hidden", "concealed", "deceptive"}:
            continue
        suffix = f": disposition {disposition!r}" if disposition is not None else ""
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} provenance_ref {ref!r} "
                    f"exposes a hidden participant-boundary ref at effective_order {effective_order}{suffix}"
                ),
            )
        )
    return violations


def _participant_behavior_outcome_ref_authorization_violations(
    *,
    event: ParticipantBehaviorHistoryEvent,
    locator: str,
    boundary: ParticipantObservationBoundaryRuntime,
    relation: Mapping[str, str],
    effective_order: int,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for record in event.outcome_interpretations:
        violations.extend(
            _participant_behavior_outcome_evidence_ref_violations(
                locator=locator,
                record=record,
                refs=record.evidence_refs,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        )
        for source in record.source_bindings:
            violations.extend(
                _participant_behavior_outcome_evidence_ref_violations(
                    locator=locator,
                    record=record,
                    refs=source.evidence_refs,
                    boundary=boundary,
                    relation=relation,
                    effective_order=effective_order,
                )
            )
            violations.extend(
                _participant_behavior_outcome_provenance_ref_violations(
                    locator=locator,
                    record=record,
                    refs=source.provenance_refs,
                    boundary=boundary,
                    relation=relation,
                    effective_order=effective_order,
                )
            )
        for target in record.target_bindings:
            violations.extend(
                _participant_behavior_outcome_evidence_ref_violations(
                    locator=locator,
                    record=record,
                    refs=target.evidence_refs,
                    boundary=boundary,
                    relation=relation,
                    effective_order=effective_order,
                )
            )
    return violations


def _participant_behavior_event_evidence_refs(event: ParticipantBehaviorHistoryEvent) -> set[str]:
    evidence_refs: set[str] = set()
    detail_refs = event.details.get("evidence_refs")
    if not isinstance(detail_refs, (str, bytes, Mapping)) and isinstance(detail_refs, Iterable):
        evidence_refs.update(str(ref) for ref in detail_refs if isinstance(ref, str) and ref)
    if event.action_result is not None:
        evidence_refs.update(event.action_result.evidence_refs)
        for precondition in event.action_result.preconditions:
            evidence_refs.update(precondition.evidence_refs)
        for effect in event.action_result.effects:
            evidence_refs.update(effect.evidence_refs)
    for edge in event.attribution_edges:
        evidence_refs.update(edge.evidence_refs)
    return evidence_refs


def _participant_episode_terminal_statuses(
    participant_episode_history: Any,
) -> dict[tuple[str, str], set[str]]:
    terminal_statuses: dict[tuple[str, str], set[str]] = {}
    if isinstance(participant_episode_history, Mapping):
        histories = participant_episode_history.values()
    elif isinstance(participant_episode_history, list):
        histories = (participant_episode_history,)
    else:
        histories = ()
    for history in histories:
        if isinstance(history, (str, bytes, Mapping)) or not isinstance(history, Iterable):
            continue
        for event in history:
            if not isinstance(event, Mapping):
                continue
            try:
                normalized = ParticipantEpisodeHistoryEvent.from_payload(event)
            except (TypeError, ValueError):
                continue
            terminal_reason = _PARTICIPANT_EPISODE_TERMINAL_EVENTS.get(normalized.event_type)
            if terminal_reason is None:
                continue
            key = (normalized.participant_address, normalized.episode_id)
            terminal_statuses.setdefault(key, set()).add(terminal_reason.value)
    return terminal_statuses


def _participant_behavior_outcome_evidence_grounding_violations(
    *,
    locator: str,
    record: ParticipantOutcomeInterpretationRecord,
    owner_label: str,
    refs: tuple[str, ...],
    grounded_evidence_refs: set[str],
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    owner = f" {owner_label}" if owner_label else ""
    for ref in refs:
        if ref in grounded_evidence_refs:
            continue
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r}{owner} evidence_ref {ref!r} "
                    "is not grounded in event evidence"
                ),
            )
        )
    return violations


def _participant_behavior_outcome_action_source_grounding_violations(
    *,
    locator: str,
    event: ParticipantBehaviorHistoryEvent,
    record: ParticipantOutcomeInterpretationRecord,
    source: ParticipantOutcomeSourceRecord,
) -> list[tuple[str, str]]:
    if source.source_layer != OutcomeInterpretationSourceLayer.PARTICIPANT_ACTION_OUTCOME:
        return []
    if event.action_result is None:
        return [
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                    "uses participant_action_outcome without an action_result"
                ),
            )
        ]
    violations: list[tuple[str, str]] = []
    if source.ref != event.action_result.action_contract_address:
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                    f"ref {source.ref!r} does not match action_result action_contract_address "
                    f"{event.action_result.action_contract_address!r}"
                ),
            )
        )
    expected_status = event.action_result.status.value
    if source.observed_value != expected_status:
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                    f"observed_value {source.observed_value!r} does not match action_result status "
                    f"{expected_status!r}"
                ),
            )
        )
    return violations


def _participant_behavior_outcome_episode_status_grounding_violations(
    *,
    locator: str,
    record: ParticipantOutcomeInterpretationRecord,
    source: ParticipantOutcomeSourceRecord,
    terminal_statuses: Mapping[tuple[str, str], set[str]],
) -> list[tuple[str, str]]:
    if source.source_layer != OutcomeInterpretationSourceLayer.PARTICIPANT_EPISODE_STATUS:
        return []
    key = (record.participant_address, record.episode_id)
    statuses = terminal_statuses.get(key, set())
    if not statuses:
        return [
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                    "participant_episode_status is not grounded by a terminal participant_episode_history event"
                ),
            )
        ]
    if source.observed_value in statuses:
        return []
    expected = ", ".join(repr(status) for status in sorted(statuses))
    return [
        (
            locator,
            (
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"observed_value {source.observed_value!r} does not match participant_episode_history terminal status "
                f"{expected}"
            ),
        )
    ]


def _participant_behavior_outcome_source_grounding_violations(
    *,
    locator: str,
    event: ParticipantBehaviorHistoryEvent,
    record: ParticipantOutcomeInterpretationRecord,
    source: ParticipantOutcomeSourceRecord,
    grounded_evidence_refs: set[str],
    terminal_statuses: Mapping[tuple[str, str], set[str]],
) -> list[tuple[str, str]]:
    violations = _participant_behavior_outcome_action_source_grounding_violations(
        locator=locator,
        event=event,
        record=record,
        source=source,
    )
    violations.extend(
        _participant_behavior_outcome_episode_status_grounding_violations(
            locator=locator,
            record=record,
            source=source,
            terminal_statuses=terminal_statuses,
        )
    )
    if (
        source.source_layer == OutcomeInterpretationSourceLayer.EVIDENCE_CLAIM
        and source.ref not in grounded_evidence_refs
    ):
        violations.append(
            (
                locator,
                (
                    f"outcome interpretation {record.interpretation_id!r} evidence_claim source "
                    f"{source.source_id!r} ref {source.ref!r} is not grounded in event evidence"
                ),
            )
        )
    violations.extend(
        _participant_behavior_outcome_evidence_grounding_violations(
            locator=locator,
            record=record,
            owner_label=f"source {source.source_id!r}",
            refs=source.evidence_refs,
            grounded_evidence_refs=grounded_evidence_refs,
        )
    )
    return violations


def _participant_behavior_outcome_event_grounding_violations(
    events: Iterable[ParticipantBehaviorHistoryEvent],
    *,
    participant_episode_history: Any = None,
) -> Iterator[tuple[str, str]]:
    terminal_statuses = _participant_episode_terminal_statuses(participant_episode_history)
    for index, event in enumerate(events):
        if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            continue
        if not event.outcome_interpretations:
            continue
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        grounded_evidence_refs = _participant_behavior_event_evidence_refs(event)
        for record in event.outcome_interpretations:
            yield from _participant_behavior_outcome_evidence_grounding_violations(
                locator=locator,
                record=record,
                owner_label="",
                refs=record.evidence_refs,
                grounded_evidence_refs=grounded_evidence_refs,
            )
            for source in record.source_bindings:
                yield from _participant_behavior_outcome_source_grounding_violations(
                    locator=locator,
                    event=event,
                    record=record,
                    source=source,
                    grounded_evidence_refs=grounded_evidence_refs,
                    terminal_statuses=terminal_statuses,
                )
            for target in record.target_bindings:
                yield from _participant_behavior_outcome_evidence_grounding_violations(
                    locator=locator,
                    record=record,
                    owner_label=f"target {target.target_id!r}",
                    refs=target.evidence_refs,
                    grounded_evidence_refs=grounded_evidence_refs,
                )


def _participant_behavior_history_anchor_indexes(
    events: Iterable[ParticipantBehaviorHistoryEvent],
) -> tuple[dict[str, int], dict[str, int], dict[tuple[str, str | None], int]]:
    action_attempts: dict[str, int] = {}
    state_transitions: dict[str, int] = {}
    observations: dict[tuple[str, str | None], int] = {}
    for index, event in enumerate(events):
        if event.event_type == ParticipantBehaviorHistoryEventType.ACTION_ATTEMPTED:
            action_attempts.setdefault(event.action_instance_id, index)
        elif event.event_type == ParticipantBehaviorHistoryEventType.STATE_TRANSITION_RECORDED:
            state_transitions.setdefault(event.action_instance_id, index)
        elif event.event_type == ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            observations.setdefault((event.action_instance_id, event.observation_boundary_address), index)
    return action_attempts, state_transitions, observations


def _participant_behavior_transition_anchor_index(
    *,
    transition: Mapping[str, Any],
    boundary_address: str,
    action_attempts: Mapping[str, int],
    state_transitions: Mapping[str, int],
    observations: Mapping[tuple[str, str | None], int],
) -> int | None:
    event_type = str(transition.get("history_event_type", ""))
    if event_type == "episode_close":
        return None
    action_instance_id = transition.get("action_instance_id")
    if not isinstance(action_instance_id, str) or not action_instance_id:
        return None
    if event_type == "action_attempted":
        return action_attempts.get(action_instance_id)
    if event_type == "state_transition_recorded":
        return state_transitions.get(action_instance_id)
    if event_type == "observation_emitted":
        return observations.get((action_instance_id, boundary_address))
    return None


def _participant_behavior_transition_anchor_violation(
    *,
    transition: Mapping[str, Any],
    boundary_address: str,
    action_attempts: Mapping[str, int],
    state_transitions: Mapping[str, int],
    observations: Mapping[tuple[str, str | None], int],
    episode_close_resolved: bool,
) -> tuple[str, str] | None:
    event_type = str(transition.get("history_event_type", ""))
    action_instance_id = transition.get("action_instance_id")
    transition_id = str(transition.get("transition_id", ""))
    locator = f"{boundary_address}.view_transitions.{transition_id}"
    if event_type == "episode_close":
        if episode_close_resolved:
            return None
        return (
            locator,
            "visibility transition anchor does not resolve to a terminal participant episode history event",
        )
    if not isinstance(action_instance_id, str) or not action_instance_id:
        return (locator, "visibility transition anchors require action_instance_id")
    event_indexes = {
        "action_attempted": action_instance_id in action_attempts,
        "state_transition_recorded": action_instance_id in state_transitions,
        "observation_emitted": (action_instance_id, boundary_address) in observations,
    }
    if event_type not in event_indexes:
        return (locator, f"visibility transition anchor has unknown history_event_type {event_type!r}")
    if event_indexes[event_type]:
        return None
    article = "an" if event_type == "observation_emitted" else "a"
    return (locator, f"visibility transition anchor does not resolve to {article} {event_type} event")


def _participant_behavior_transition_anchor_violations(
    events: list[ParticipantBehaviorHistoryEvent],
    *,
    observation_boundaries: Mapping[str, ParticipantObservationBoundaryRuntime],
    participant_episode_history: Any = None,
) -> Iterator[tuple[str, str]]:
    action_attempts, state_transitions, observations = _participant_behavior_history_anchor_indexes(events)
    episode_close_resolved = _participant_behavior_episode_close_resolved(
        events,
        participant_episode_history=participant_episode_history,
    )
    for boundary_address, boundary in observation_boundaries.items():
        for transition in boundary.view_transitions:
            violation = _participant_behavior_transition_anchor_violation(
                transition=transition,
                boundary_address=boundary_address,
                action_attempts=action_attempts,
                state_transitions=state_transitions,
                observations=observations,
                episode_close_resolved=episode_close_resolved,
            )
            if violation is not None:
                yield violation


def _participant_behavior_episode_close_resolved(
    events: list[ParticipantBehaviorHistoryEvent],
    *,
    participant_episode_history: Any,
) -> bool:
    if not isinstance(participant_episode_history, list):
        return False
    participant_addresses = {event.participant_address for event in events}
    episode_ids = {event.episode_id for event in events}
    if not participant_addresses or not episode_ids:
        return False
    closed_episode_ids: set[str] = set()
    for event in participant_episode_history:
        if not isinstance(event, Mapping):
            continue
        try:
            normalized = ParticipantEpisodeHistoryEvent.from_payload(event)
        except (TypeError, ValueError):
            continue
        if normalized.participant_address not in participant_addresses:
            continue
        if normalized.episode_id not in episode_ids:
            continue
        if normalized.event_type in _PARTICIPANT_EPISODE_TERMINAL_EVENTS:
            closed_episode_ids.add(normalized.episode_id)
    return episode_ids <= closed_episode_ids


def _participant_behavior_observation_effective_relation(
    *,
    observation_index: int,
    boundary_address: str,
    boundary: ParticipantObservationBoundaryRuntime,
    action_attempts: Mapping[str, int],
    state_transitions: Mapping[str, int],
    observations: Mapping[tuple[str, str | None], int],
) -> tuple[dict[str, str], int]:
    relation = _participant_behavior_initial_view_relation(boundary)
    deltas_by_order = _participant_behavior_view_relation_deltas_by_order(boundary)
    effective_order = -1
    for transition in sorted(
        boundary.view_transitions,
        key=lambda item: (
            _participant_behavior_transition_effective_order(item)
            if _participant_behavior_transition_effective_order(item) is not None
            else -1
        ),
    ):
        order = _participant_behavior_transition_effective_order(transition)
        if order is None:
            continue
        anchor_index = _participant_behavior_transition_anchor_index(
            transition=transition,
            boundary_address=boundary_address,
            action_attempts=action_attempts,
            state_transitions=state_transitions,
            observations=observations,
        )
        if anchor_index is None or anchor_index > observation_index:
            continue
        if not _participant_behavior_transition_matches_relation(transition, relation=relation):
            continue
        relation.update(_participant_behavior_transition_delta(transition, deltas_by_order=deltas_by_order))
        effective_order = max(effective_order, order)
    return relation, effective_order


def _participant_behavior_detail_shape_violations_for_events(
    events: list[ParticipantBehaviorHistoryEvent],
) -> Iterator[tuple[str, str]]:
    for index, event in enumerate(events):
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        yield from _participant_behavior_detail_shape_violations(event, locator=locator)


def _participant_behavior_observation_visibility_violations(
    events: list[ParticipantBehaviorHistoryEvent],
    *,
    observation_boundaries: Mapping[str, ParticipantObservationBoundaryRuntime],
) -> Iterator[tuple[str, str]]:
    action_attempts, state_transitions, observations = _participant_behavior_history_anchor_indexes(events)
    for index, event in enumerate(events):
        if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            continue
        boundary_address = event.observation_boundary_address or ""
        boundary = observation_boundaries.get(boundary_address)
        if boundary is None:
            continue
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        detail_refs, violations = _participant_behavior_observation_detail_refs(event, locator=locator)
        if violations:
            yield from violations
            continue
        if not any(detail_refs.values()):
            continue
        relation, effective_order = _participant_behavior_observation_effective_relation(
            observation_index=index,
            boundary_address=boundary_address,
            boundary=boundary,
            action_attempts=action_attempts,
            state_transitions=state_transitions,
            observations=observations,
        )
        yield from _participant_behavior_visibility_detail_violations(
            locator=locator,
            detail_refs=detail_refs,
            boundary=boundary,
            relation=relation,
            effective_order=effective_order,
        )


def _participant_behavior_action_result_ref_authorization_violations_for_events(
    events: list[ParticipantBehaviorHistoryEvent],
    *,
    observation_boundaries: Mapping[str, ParticipantObservationBoundaryRuntime],
) -> Iterator[tuple[str, str]]:
    action_attempts, state_transitions, observations = _participant_behavior_history_anchor_indexes(events)
    for index, event in enumerate(events):
        if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            continue
        if event.action_result is None and not event.attribution_edges and not event.outcome_interpretations:
            continue
        boundary_address = event.observation_boundary_address or ""
        boundary = observation_boundaries.get(boundary_address)
        if boundary is None:
            continue
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        relation, effective_order = _participant_behavior_observation_effective_relation(
            observation_index=index,
            boundary_address=boundary_address,
            boundary=boundary,
            action_attempts=action_attempts,
            state_transitions=state_transitions,
            observations=observations,
        )
        if event.action_result is not None:
            yield from _participant_behavior_action_result_ref_authorization_violations(
                event=event,
                locator=locator,
                boundary=boundary,
                relation=relation,
                effective_order=effective_order,
            )
        yield from _participant_behavior_attribution_ref_authorization_violations(
            event=event,
            locator=locator,
            boundary=boundary,
            relation=relation,
            effective_order=effective_order,
        )
        yield from _participant_behavior_outcome_ref_authorization_violations(
            event=event,
            locator=locator,
            boundary=boundary,
            relation=relation,
            effective_order=effective_order,
        )


def _participant_behavior_address_violations(
    event: ParticipantBehaviorHistoryEvent,
    *,
    locator: str,
    action_contract_addresses: set[str] | frozenset[str] | None,
    observation_boundary_addresses: set[str] | frozenset[str] | None,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    if action_contract_addresses is not None and event.action_contract_address not in action_contract_addresses:
        violations.append(
            (
                locator,
                (
                    "participant behavior event references unknown action_contract_address "
                    f"{event.action_contract_address!r}"
                ),
            )
        )
    if (
        observation_boundary_addresses is not None
        and event.observation_boundary_address is not None
        and event.observation_boundary_address not in observation_boundary_addresses
    ):
        violations.append(
            (
                locator,
                (
                    "participant behavior event references unknown observation_boundary_address "
                    f"{event.observation_boundary_address!r}"
                ),
            )
        )
    return violations


def _contract_sem213_temporal_contracts(
    contract: ParticipantActionContractRuntime,
) -> dict[str, Mapping[str, Any]]:
    temporal_contracts = contract.spec.get("temporal_contracts", ())
    if isinstance(temporal_contracts, (str, bytes, Mapping)) or not isinstance(temporal_contracts, Iterable):
        return {}
    return {
        str(temporal_contract.get("temporal_id")): temporal_contract
        for temporal_contract in temporal_contracts
        if isinstance(temporal_contract, Mapping) and temporal_contract.get("temporal_id")
    }


def _contract_sem213_backend_disclosure_ids(contract: ParticipantActionContractRuntime) -> set[str]:
    disclosures = contract.spec.get("backend_timing_disclosures", ())
    if isinstance(disclosures, (str, bytes, Mapping)) or not isinstance(disclosures, Iterable):
        return set()
    return {
        str(disclosure.get("disclosure_id"))
        for disclosure in disclosures
        if isinstance(disclosure, Mapping) and disclosure.get("disclosure_id")
    }


def _participant_temporal_context_contract_violations(
    context: ParticipantTemporalRuntimeContext,
    *,
    contract: ParticipantActionContractRuntime,
) -> list[str]:
    violations: list[str] = []
    temporal_contracts = _contract_sem213_temporal_contracts(contract)
    temporal_contract = temporal_contracts.get(context.temporal_contract_id)
    if temporal_contract is None:
        return [f"temporal context references undeclared temporal_contract_id {context.temporal_contract_id!r}"]

    declared_time_domain = str(temporal_contract.get("time_domain", ""))
    if context.time_domain.value != declared_time_domain:
        violations.append(
            f"temporal context {context.temporal_contract_id!r} time_domain {context.time_domain.value!r} "
            f"does not match compiled contract {declared_time_domain!r}"
        )

    declared_clock_authority = str(temporal_contract.get("clock_authority", ""))
    if context.clock_authority != declared_clock_authority:
        violations.append(
            f"temporal context {context.temporal_contract_id!r} clock_authority {context.clock_authority!r} "
            f"does not match compiled contract {declared_clock_authority!r}"
        )

    declared_event_points = tuple(str(point) for point in temporal_contract.get("event_points", ()))
    observed_event_points = tuple(point.value for point in context.event_points)
    if observed_event_points != declared_event_points:
        violations.append(
            f"temporal context {context.temporal_contract_id!r} event_points {observed_event_points!r} "
            f"do not match compiled contract {declared_event_points!r}"
        )

    declared_contract_disclosures = set(str(ref) for ref in temporal_contract.get("backend_disclosure_refs", ()))
    declared_disclosures = _contract_sem213_backend_disclosure_ids(contract)
    for ref in sorted(set(context.backend_disclosure_refs) - declared_contract_disclosures):
        violations.append(
            f"temporal context {context.temporal_contract_id!r} reports backend_disclosure_ref {ref!r} "
            "not declared by the temporal contract"
        )
    for ref in sorted(set(context.backend_disclosure_refs) - declared_disclosures):
        violations.append(
            f"temporal context {context.temporal_contract_id!r} reports unknown backend_disclosure_ref {ref!r}"
        )

    declared_reset_boundary = temporal_contract.get("reset_boundary")
    if declared_reset_boundary is not None and context.reset_boundary != str(declared_reset_boundary):
        violations.append(
            f"temporal context {context.temporal_contract_id!r} reset_boundary {context.reset_boundary!r} "
            f"does not match compiled contract {str(declared_reset_boundary)!r}"
        )
    declared_replay_boundary = temporal_contract.get("replay_boundary")
    if declared_replay_boundary is not None and context.replay_boundary != str(declared_replay_boundary):
        violations.append(
            f"temporal context {context.temporal_contract_id!r} replay_boundary {context.replay_boundary!r} "
            f"does not match compiled contract {str(declared_replay_boundary)!r}"
        )

    return violations


def _participant_behavior_temporal_contract_violations(
    events: Iterable[ParticipantBehaviorHistoryEvent],
    *,
    action_contracts: Mapping[str, ParticipantActionContractRuntime],
) -> Iterator[tuple[str, str]]:
    for index, event in enumerate(events):
        if not event.temporal_contexts:
            continue
        action_contract_address = event.action_contract_address or ""
        contract = action_contracts.get(action_contract_address)
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        if contract is None:
            yield (locator, f"temporal context cannot resolve action contract {action_contract_address!r}")
            continue
        for context in event.temporal_contexts:
            for violation in _participant_temporal_context_contract_violations(context, contract=contract):
                yield (locator, violation)


def _contract_sem215_source_bindings(
    rule: ParticipantOutcomeInterpretationRuleRuntime,
) -> dict[tuple[str, str], dict[str, str | set[str]]]:
    bindings = rule.spec.get("source_bindings", ())
    if isinstance(bindings, (str, bytes, Mapping)) or not isinstance(bindings, Iterable):
        return {}
    declarations: dict[tuple[str, str], dict[str, str | set[str]]] = {}
    for index, binding in enumerate(bindings):
        if not isinstance(binding, Mapping) or not binding.get("source_id") or not binding.get("source_layer"):
            continue
        declarations[(str(binding.get("source_id")), str(binding.get("source_layer")))] = {
            "ref": rule.source_refs[index] if index < len(rule.source_refs) else str(binding.get("ref", "")),
            "evidence_refs": _as_string_set(binding.get("evidence_refs", ())),
            "provenance_refs": _as_string_set(binding.get("provenance_refs", ())),
        }
    return declarations


def _contract_sem215_target_bindings(
    rule: ParticipantOutcomeInterpretationRuleRuntime,
) -> dict[tuple[str, str], dict[str, str | set[str] | None]]:
    bindings = rule.spec.get("target_bindings", ())
    if isinstance(bindings, (str, bytes, Mapping)) or not isinstance(bindings, Iterable):
        return {}
    declarations: dict[tuple[str, str], dict[str, str | set[str] | None]] = {}
    for index, binding in enumerate(bindings):
        if not isinstance(binding, Mapping) or not binding.get("target_id") or not binding.get("target_layer"):
            continue
        governance_ref = binding.get("governance_ref")
        declarations[(str(binding.get("target_id")), str(binding.get("target_layer")))] = {
            "ref": rule.target_refs[index] if index < len(rule.target_refs) else str(binding.get("ref", "")),
            "governance_ref": str(governance_ref) if governance_ref is not None else None,
            "evidence_refs": _as_string_set(binding.get("evidence_refs", ())),
            "limitations": _as_string_set(binding.get("limitations", ())),
        }
    return declarations


def _outcome_source_layer_requires_provenance(layer: str) -> bool:
    try:
        source_layer = OutcomeInterpretationSourceLayer(layer)
    except ValueError:
        return False
    return source_layer in PROVENANCE_REQUIRED_OUTCOME_SOURCE_LAYERS


def validate_participant_outcome_interpretation_record(
    record: ParticipantOutcomeInterpretationRecord,
    rule: ParticipantOutcomeInterpretationRuleRuntime,
) -> list[str]:
    """Return SEM-215 rule-conformance violations for a runtime interpretation."""

    violations: list[str] = []
    declared_sources = _contract_sem215_source_bindings(rule)
    declared_targets = _contract_sem215_target_bindings(rule)
    reported_sources: set[tuple[str, str]] = set()
    for source in record.source_bindings:
        source_key = (source.source_id, source.source_layer.value)
        reported_sources.add(source_key)
        if source_key not in declared_sources:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"is not declared by {rule.address}"
            )
            continue
        declared_refs = declared_sources[source_key]
        if source.ref != declared_refs["ref"]:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"ref {source.ref!r} does not match declared ref {declared_refs['ref']!r}"
            )
        for ref in sorted(set(source.evidence_refs) - declared_refs["evidence_refs"]):
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"reports undeclared evidence_ref {ref!r}"
            )
        for ref in sorted(set(source.provenance_refs) - declared_refs["provenance_refs"]):
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"reports undeclared provenance_ref {ref!r}"
            )
        for ref in sorted(declared_refs["provenance_refs"] - set(source.provenance_refs)):
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source.source_id!r} "
                f"omits declared provenance_ref {ref!r}"
            )
    for source_id, source_layer in sorted(declared_sources):
        if not _outcome_source_layer_requires_provenance(source_layer):
            continue
        if (source_id, source_layer) not in reported_sources:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} source {source_id!r} "
                f"with provenance-required layer {source_layer!r} is not reported"
            )
    for target in record.target_bindings:
        target_key = (target.target_id, target.target_layer.value)
        if target_key not in declared_targets:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                f"is not declared by {rule.address}"
            )
            continue
        declared_refs = declared_targets[target_key]
        if target.ref != declared_refs["ref"]:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                f"ref {target.ref!r} does not match declared ref {declared_refs['ref']!r}"
            )
        if target.governance_ref != declared_refs["governance_ref"]:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                f"governance_ref {target.governance_ref!r} does not match declared governance_ref "
                f"{declared_refs['governance_ref']!r}"
            )
        for ref in sorted(set(target.evidence_refs) - declared_refs["evidence_refs"]):
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                f"reports undeclared evidence_ref {ref!r}"
            )
        if declared_refs["limitations"] and not set(target.limitations) <= declared_refs["limitations"]:
            violations.append(
                f"outcome interpretation {record.interpretation_id!r} target {target.target_id!r} "
                "reports limitations outside the declared rule"
            )
    declared_rule_evidence_refs = _as_string_set(rule.spec.get("evidence_refs", ()))
    for ref in sorted(set(record.evidence_refs) - declared_rule_evidence_refs):
        violations.append(
            f"outcome interpretation {record.interpretation_id!r} reports undeclared evidence_ref {ref!r}"
        )
    return violations


def _participant_behavior_outcome_interpretation_rule_violations(
    events: Iterable[ParticipantBehaviorHistoryEvent],
    *,
    outcome_interpretation_rules: Mapping[str, ParticipantOutcomeInterpretationRuleRuntime],
) -> Iterator[tuple[str, str]]:
    for index, event in enumerate(events):
        if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            continue
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        for record in event.outcome_interpretations:
            rule = outcome_interpretation_rules.get(record.rule_address)
            if rule is None:
                yield (
                    locator,
                    (
                        f"outcome interpretation {record.interpretation_id!r} references unknown "
                        f"rule_address {record.rule_address!r}"
                    ),
                )
                continue
            for violation in validate_participant_outcome_interpretation_record(record, rule):
                yield (locator, violation)


def _participant_behavior_action_result_contract_violations(
    events: Iterable[ParticipantBehaviorHistoryEvent],
    *,
    action_contracts: Mapping[str, ParticipantActionContractRuntime],
) -> Iterator[tuple[str, str]]:
    for index, event in enumerate(events):
        if event.event_type != ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED:
            continue
        if event.observation_status not in _PARTICIPANT_TERMINAL_OBSERVATION_STATUSES:
            continue
        action_contract_address = event.action_contract_address or ""
        contract = action_contracts.get(action_contract_address)
        if contract is None or not _contract_uses_sem211_action_results(contract):
            continue
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        if event.action_result is None:
            yield (
                locator,
                f"terminal observation must carry SEM-211 action_result for {action_contract_address}",
            )
            continue
        for violation in validate_participant_action_result_contract(event.action_result, contract):
            yield (locator, violation)


def _normalize_participant_behavior_events(
    participant_behavior_history: list[Any],
    *,
    action_contract_addresses: set[str] | frozenset[str] | None,
    observation_boundary_addresses: set[str] | frozenset[str] | None,
    expected_participant_address: str | None = None,
) -> tuple[list[ParticipantBehaviorHistoryEvent], list[tuple[str, str]]]:
    normalized_events: list[ParticipantBehaviorHistoryEvent] = []
    violations: list[tuple[str, str]] = []
    for index, event in enumerate(participant_behavior_history):
        locator = f"{_PARTICIPANT_BEHAVIOR_HISTORY_KEY}[{index}]"
        if not isinstance(event, Mapping):
            violations.append((locator, "participant behavior history event must be a mapping"))
            continue
        try:
            normalized = ParticipantBehaviorHistoryEvent.from_payload(event)
        except (TypeError, ValueError) as exc:
            violations.append((locator, f"participant behavior history event is invalid: {exc}"))
            continue
        if expected_participant_address is not None and normalized.participant_address != expected_participant_address:
            violations.append(
                (
                    locator,
                    (
                        f"participant behavior history event outer key {expected_participant_address!r} "
                        f"does not match inner participant_address {normalized.participant_address!r}"
                    ),
                )
            )
            continue
        violations.extend(
            _participant_behavior_address_violations(
                normalized,
                locator=locator,
                action_contract_addresses=action_contract_addresses,
                observation_boundary_addresses=observation_boundary_addresses,
            )
        )
        normalized_events.append(normalized)
    return normalized_events, violations


def _participant_behavior_events_by_action_instance(
    events: list[ParticipantBehaviorHistoryEvent],
) -> dict[str, list[ParticipantBehaviorHistoryEvent]]:
    events_by_action_instance: dict[str, list[ParticipantBehaviorHistoryEvent]] = {}
    for event in events:
        events_by_action_instance.setdefault(event.action_instance_id, []).append(event)
    return events_by_action_instance


def _participant_behavior_action_instance_violation(
    action_instance_id: str,
    events: list[ParticipantBehaviorHistoryEvent],
) -> tuple[str, str] | None:
    attempts = [event for event in events if event.event_type == ParticipantBehaviorHistoryEventType.ACTION_ATTEMPTED]
    observations = [
        event
        for event in events
        if event.event_type == ParticipantBehaviorHistoryEventType.OBSERVATION_EMITTED
        and event.observation_status in _PARTICIPANT_TERMINAL_OBSERVATION_STATUSES
    ]
    transitions = [
        event for event in events if event.event_type == ParticipantBehaviorHistoryEventType.STATE_TRANSITION_RECORDED
    ]

    if len(attempts) > 1:
        return (action_instance_id, "participant action instance may only have one action_attempted event")
    if len(attempts) == 0:
        return (action_instance_id, "participant behavior events require a matching action_attempted event")
    if len(observations) != 1:
        return (
            action_instance_id,
            "participant action instance requires exactly one terminal observation or orphaned-action observation",
        )
    observation = observations[0]
    if observation.observation_status == ParticipantObservationStatus.ORPHANED_ACTION:
        return None
    if len(transitions) != 1:
        return (action_instance_id, "participant action instance requires exactly one state transition")
    if observation.post_state_digest != transitions[0].post_state_digest:
        return (
            action_instance_id,
            "terminal observation post_state_digest must match the state transition post_state_digest",
        )
    return None


def _participant_behavior_action_instance_violations(
    events: list[ParticipantBehaviorHistoryEvent],
) -> Iterator[tuple[str, str]]:
    for action_instance_id, grouped_events in _participant_behavior_events_by_action_instance(events).items():
        violation = _participant_behavior_action_instance_violation(action_instance_id, grouped_events)
        if violation is not None:
            yield violation


def _participant_behavior_joint_action_order_violations(
    events: Iterable[ParticipantBehaviorHistoryEvent],
) -> Iterator[tuple[str, str]]:
    attempts_by_joint_set: dict[str, list[ParticipantBehaviorHistoryEvent]] = {}
    for event in events:
        if (
            event.event_type == ParticipantBehaviorHistoryEventType.ACTION_ATTEMPTED
            and event.joint_action_set_id is not None
        ):
            attempts_by_joint_set.setdefault(event.joint_action_set_id, []).append(event)

    for joint_action_set_id, attempts in sorted(attempts_by_joint_set.items()):
        attempts_by_order: dict[int, list[ParticipantBehaviorHistoryEvent]] = {}
        for event in attempts:
            if event.realized_order is None:
                continue
            attempts_by_order.setdefault(event.realized_order, []).append(event)
        for realized_order, duplicate_attempts in sorted(attempts_by_order.items()):
            if len(duplicate_attempts) <= 1:
                continue
            instances = ", ".join(
                sorted(f"{event.participant_address}/{event.action_instance_id}" for event in duplicate_attempts)
            )
            yield (
                f"joint-action-set.{joint_action_set_id}",
                (
                    f"joint action set realized_order {realized_order} is assigned to "
                    f"multiple action_attempted events: {instances}"
                ),
            )


def iter_participant_behavior_history_violations(
    participant_behavior_history: Any,
    *,
    action_contract_addresses: set[str] | frozenset[str] | None = None,
    action_contracts: Mapping[str, ParticipantActionContractRuntime] | None = None,
    outcome_interpretation_rules: Mapping[str, ParticipantOutcomeInterpretationRuleRuntime] | None = None,
    observation_boundary_addresses: set[str] | frozenset[str] | None = None,
    observation_boundaries: Mapping[str, ParticipantObservationBoundaryRuntime] | None = None,
    participant_episode_history: Any = None,
    expected_participant_address: str | None = None,
) -> Iterator[tuple[str, str]]:
    """Yield every SEM-208 behavior-history invariant violation.

    The helper checks that each action instance has one terminal observation
    paired with the state transition digest it reports. When compiled address
    sets are provided, it also rejects references outside those sets. When
    compiled observation boundaries are provided, SEM-210 observation details
    and SEM-211 action-result references are checked against the time-indexed
    participant view relation.
    """

    if not isinstance(participant_behavior_history, list):
        yield (_PARTICIPANT_BEHAVIOR_HISTORY_KEY, "participant behavior history must be a list of events")
        return
    if action_contracts is not None and action_contract_addresses is None:
        action_contract_addresses = frozenset(action_contracts.keys())
    if observation_boundaries is not None and observation_boundary_addresses is None:
        observation_boundary_addresses = frozenset(observation_boundaries.keys())

    normalized_events, entry_violations = _normalize_participant_behavior_events(
        participant_behavior_history,
        action_contract_addresses=action_contract_addresses,
        observation_boundary_addresses=observation_boundary_addresses,
        expected_participant_address=expected_participant_address,
    )
    if entry_violations:
        yield from entry_violations
        return

    yield from _participant_behavior_detail_shape_violations_for_events(normalized_events)
    yield from _participant_behavior_action_instance_violations(normalized_events)
    yield from _participant_behavior_joint_action_order_violations(normalized_events)
    yield from _participant_behavior_outcome_event_grounding_violations(
        normalized_events,
        participant_episode_history=participant_episode_history,
    )
    if action_contracts is not None:
        yield from _participant_behavior_action_result_contract_violations(
            normalized_events,
            action_contracts=action_contracts,
        )
        yield from _participant_behavior_temporal_contract_violations(
            normalized_events,
            action_contracts=action_contracts,
        )
    if outcome_interpretation_rules is not None:
        yield from _participant_behavior_outcome_interpretation_rule_violations(
            normalized_events,
            outcome_interpretation_rules=outcome_interpretation_rules,
        )
    if observation_boundaries is not None:
        yield from _participant_behavior_transition_anchor_violations(
            normalized_events,
            observation_boundaries=observation_boundaries,
            participant_episode_history=participant_episode_history,
        )
        yield from _participant_behavior_observation_visibility_violations(
            normalized_events,
            observation_boundaries=observation_boundaries,
        )
        yield from _participant_behavior_action_result_ref_authorization_violations_for_events(
            normalized_events,
            observation_boundaries=observation_boundaries,
        )


def iter_participant_behavior_joint_action_violations(
    participant_behavior_history_by_participant: Any,
) -> Iterator[tuple[str, str]]:
    """Yield SEM-209 joint-action ordering violations across participant histories."""

    if not isinstance(participant_behavior_history_by_participant, Mapping):
        yield (_PARTICIPANT_BEHAVIOR_HISTORY_KEY, "participant behavior histories must be a mapping")
        return

    normalized_events: list[ParticipantBehaviorHistoryEvent] = []
    for history in participant_behavior_history_by_participant.values():
        if not isinstance(history, list):
            continue
        participant_events, entry_violations = _normalize_participant_behavior_events(
            history,
            action_contract_addresses=None,
            observation_boundary_addresses=None,
        )
        if entry_violations:
            continue
        normalized_events.extend(participant_events)

    yield from _participant_behavior_joint_action_order_violations(normalized_events)


@dataclass(frozen=True)
class MetricRuntime(ResolvedResource):
    """Resolved metric node."""

    condition_name: str = ""
    condition_addresses: tuple[str, ...] = ()
    result_contract: "EvaluationResultContract" = field(
        default_factory=lambda: EvaluationResultContract(resource_type="metric")
    )
    execution_contract: "EvaluationExecutionContract" = field(
        default_factory=lambda: EvaluationExecutionContract(resource_type="metric")
    )


@dataclass(frozen=True)
class EvaluationRuntime(ResolvedResource):
    """Resolved evaluation node."""

    metric_addresses: tuple[str, ...] = ()
    result_contract: "EvaluationResultContract" = field(
        default_factory=lambda: EvaluationResultContract(resource_type="evaluation")
    )
    execution_contract: "EvaluationExecutionContract" = field(
        default_factory=lambda: EvaluationExecutionContract(resource_type="evaluation")
    )


@dataclass(frozen=True)
class TLORuntime(ResolvedResource):
    """Resolved TLO node."""

    evaluation_address: str = ""
    result_contract: "EvaluationResultContract" = field(
        default_factory=lambda: EvaluationResultContract(resource_type="tlo")
    )
    execution_contract: "EvaluationExecutionContract" = field(
        default_factory=lambda: EvaluationExecutionContract(resource_type="tlo")
    )


@dataclass(frozen=True)
class GoalRuntime(ResolvedResource):
    """Resolved goal node."""

    tlo_addresses: tuple[str, ...] = ()
    result_contract: "EvaluationResultContract" = field(
        default_factory=lambda: EvaluationResultContract(resource_type="goal")
    )
    execution_contract: "EvaluationExecutionContract" = field(
        default_factory=lambda: EvaluationExecutionContract(resource_type="goal")
    )


@dataclass(frozen=True)
class ObjectiveRuntime(ResolvedResource):
    """Resolved objective node."""

    actor_type: str = ""
    actor_name: str = ""
    success_addresses: tuple[str, ...] = ()
    objective_dependencies: tuple[str, ...] = ()
    window_story_addresses: tuple[str, ...] = ()
    window_script_addresses: tuple[str, ...] = ()
    window_event_addresses: tuple[str, ...] = ()
    window_workflow_addresses: tuple[str, ...] = ()
    window_step_refs: tuple[str, ...] = ()
    window_step_workflow_addresses: tuple[str, ...] = ()
    window_references: tuple[ObjectiveWindowReferenceRuntime, ...] = ()
    result_contract: "EvaluationResultContract" = field(
        default_factory=lambda: EvaluationResultContract(resource_type="objective")
    )
    execution_contract: "EvaluationExecutionContract" = field(
        default_factory=lambda: EvaluationExecutionContract(resource_type="objective")
    )


@dataclass(frozen=True)
class RuntimeModel:
    """Compiled SDL runtime model.

    Reusable definitions stay as templates or metadata. Only bound runtime
    instances become planned resources.
    """

    scenario_name: str
    feature_templates: dict[str, RuntimeTemplate] = field(default_factory=dict)
    condition_templates: dict[str, RuntimeTemplate] = field(default_factory=dict)
    inject_templates: dict[str, RuntimeTemplate] = field(default_factory=dict)
    vulnerability_templates: dict[str, RuntimeTemplate] = field(default_factory=dict)
    entity_specs: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_specs: dict[str, dict[str, Any]] = field(default_factory=dict)
    relationship_specs: dict[str, dict[str, Any]] = field(default_factory=dict)
    variable_specs: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Pre-instantiation `${name}` refs on `nodes.os` and `infrastructure.count`,
    # keyed by the network/node resource address. Lets the planner reach a
    # variable's `allowed_values` even after `compile_runtime_model` substitutes
    # the resolved values onto the corresponding runtime resources. Kept on the
    # model rather than on the resources themselves so the provenance does not
    # leak into the backend-facing `resource_payload()` envelope. Inner dict
    # carries `"os"` and `"count"` keys; missing or `None` values mean the
    # field was authored as a concrete literal rather than a variable ref.
    node_variable_refs: dict[str, dict[str, str | None]] = field(default_factory=dict)
    networks: dict[str, NetworkRuntime] = field(default_factory=dict)
    node_deployments: dict[str, NodeRuntime] = field(default_factory=dict)
    feature_bindings: dict[str, FeatureBinding] = field(default_factory=dict)
    condition_bindings: dict[str, ConditionBinding] = field(default_factory=dict)
    injects: dict[str, InjectRuntime] = field(default_factory=dict)
    inject_bindings: dict[str, InjectBinding] = field(default_factory=dict)
    content_placements: dict[str, ContentPlacement] = field(default_factory=dict)
    account_placements: dict[str, AccountPlacement] = field(default_factory=dict)
    action_contracts: dict[str, ParticipantActionContractRuntime] = field(default_factory=dict)
    observation_boundaries: dict[str, ParticipantObservationBoundaryRuntime] = field(default_factory=dict)
    outcome_interpretation_rules: dict[str, ParticipantOutcomeInterpretationRuleRuntime] = field(default_factory=dict)
    participant_behaviors: dict[str, ParticipantBehaviorRuntime] = field(default_factory=dict)
    behavior_specifications: dict[str, ParticipantBehaviorSpecificationRuntime] = field(default_factory=dict)
    events: dict[str, EventRuntime] = field(default_factory=dict)
    scripts: dict[str, ScriptRuntime] = field(default_factory=dict)
    stories: dict[str, StoryRuntime] = field(default_factory=dict)
    workflows: dict[str, WorkflowRuntime] = field(default_factory=dict)
    metrics: dict[str, MetricRuntime] = field(default_factory=dict)
    evaluations: dict[str, EvaluationRuntime] = field(default_factory=dict)
    tlos: dict[str, TLORuntime] = field(default_factory=dict)
    goals: dict[str, GoalRuntime] = field(default_factory=dict)
    objectives: dict[str, ObjectiveRuntime] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    # SEM-218 typed compiler emission: each authored realization concern with
    # its preserved explicitness class. Model-side metadata (like
    # `node_variable_refs`); it never enters the backend-facing
    # `resource_payload()` envelope. Consumed by the planner realization gate.
    realization_requirements: tuple[CompiledRealizationRequirement, ...] = ()


@dataclass(frozen=True)
class ExecutionPlan:
    """Composite runtime execution plan."""

    target_name: str | None
    manifest: BackendManifest
    base_snapshot: "RuntimeSnapshot"
    scenario_name: str
    model: RuntimeModel
    provisioning: ProvisioningPlan
    orchestration: OrchestrationPlan
    evaluation: EvaluationPlan
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(diag.is_error for diag in self.diagnostics)


def resource_payload(resource: ResolvedResource) -> dict[str, Any]:
    """Convert a compiled resource to a stable planner payload."""

    payload = asdict(resource)
    payload.pop("address", None)
    payload.pop("ordering_dependencies", None)
    payload.pop("refresh_dependencies", None)
    return payload
