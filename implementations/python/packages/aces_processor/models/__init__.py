"""Runtime data models for the SDL-native execution layer.

The runtime is split into three domains:

- provisioning: desired deployed state
- orchestration: resolved exercise control graph
- evaluation: resolved monitoring/scoring graph

The compiler produces a ``RuntimeModel`` with reusable templates separated
from bound runtime instances. The planner reconciles those instances against
the current ``RuntimeSnapshot`` and emits a composite ``ExecutionPlan``.
"""

from aces_contracts.diagnostics import Diagnostic as Diagnostic
from aces_contracts.diagnostics import Severity as Severity
from aces_contracts.evaluation import EvaluationExecutionContract as EvaluationExecutionContract
from aces_contracts.evaluation import EvaluationExecutionState as EvaluationExecutionState
from aces_contracts.evaluation import EvaluationHistoryEvent as EvaluationHistoryEvent
from aces_contracts.evaluation import EvaluationHistoryEventType as EvaluationHistoryEventType
from aces_contracts.evaluation import EvaluationResultContract as EvaluationResultContract
from aces_contracts.evaluation import EvaluationResultStatus as EvaluationResultStatus
from aces_contracts.evaluation import validate_evaluation_result as validate_evaluation_result
from aces_contracts.participant_behavior import (
    ParticipantActionPreconditionStatus as ParticipantActionPreconditionStatus,
)
from aces_contracts.participant_behavior import ParticipantActionResultStatus as ParticipantActionResultStatus
from aces_contracts.participant_behavior import ParticipantAdmissionDisposition as ParticipantAdmissionDisposition
from aces_contracts.participant_behavior import (
    ParticipantBehaviorHistoryEventType as ParticipantBehaviorHistoryEventType,
)
from aces_contracts.participant_behavior import ParticipantLifecycleOperationState as ParticipantLifecycleOperationState
from aces_contracts.participant_behavior import ParticipantObservationStatus as ParticipantObservationStatus
from aces_contracts.participant_behavior import ParticipantPhaseRealization as ParticipantPhaseRealization
from aces_contracts.participant_behavior import ParticipantRuntimeLifecyclePhase as ParticipantRuntimeLifecyclePhase
from aces_contracts.participant_behavior import (
    participant_lifecycle_field_violation_messages as participant_lifecycle_field_violation_messages,
)
from aces_contracts.participant_episode import ParticipantEpisodeControlAction as ParticipantEpisodeControlAction
from aces_contracts.participant_episode import ParticipantEpisodeExecutionState as ParticipantEpisodeExecutionState
from aces_contracts.participant_episode import ParticipantEpisodeHistoryEvent as ParticipantEpisodeHistoryEvent
from aces_contracts.participant_episode import ParticipantEpisodeHistoryEventType as ParticipantEpisodeHistoryEventType
from aces_contracts.participant_episode import (
    ParticipantEpisodeInitializeRequest as ParticipantEpisodeInitializeRequest,
)
from aces_contracts.participant_episode import ParticipantEpisodeResetRequest as ParticipantEpisodeResetRequest
from aces_contracts.participant_episode import ParticipantEpisodeRestartRequest as ParticipantEpisodeRestartRequest
from aces_contracts.participant_episode import ParticipantEpisodeStatus as ParticipantEpisodeStatus
from aces_contracts.participant_episode import ParticipantEpisodeTerminalReason as ParticipantEpisodeTerminalReason
from aces_contracts.participant_episode import ParticipantEpisodeTerminateRequest as ParticipantEpisodeTerminateRequest
from aces_contracts.participant_episode import (
    iter_participant_episode_snapshot_violations as iter_participant_episode_snapshot_violations,
)
from aces_contracts.planning import ChangeAction as ChangeAction
from aces_contracts.planning import EvaluationOp as EvaluationOp
from aces_contracts.planning import EvaluationPlan as EvaluationPlan
from aces_contracts.planning import OrchestrationOp as OrchestrationOp
from aces_contracts.planning import OrchestrationPlan as OrchestrationPlan
from aces_contracts.planning import PlannedResource as PlannedResource
from aces_contracts.planning import PlanOperation as PlanOperation
from aces_contracts.planning import ProvisioningPlan as ProvisioningPlan
from aces_contracts.planning import ProvisionOp as ProvisionOp
from aces_contracts.planning import RuntimeDomain as RuntimeDomain
from aces_contracts.runtime_state import ApplyResult as ApplyResult
from aces_contracts.runtime_state import OperationReceipt as OperationReceipt
from aces_contracts.runtime_state import OperationState as OperationState
from aces_contracts.runtime_state import OperationStatus as OperationStatus
from aces_contracts.runtime_state import RealizationProvenanceEntry as RealizationProvenanceEntry
from aces_contracts.runtime_state import RuntimeSnapshot as RuntimeSnapshot
from aces_contracts.runtime_state import RuntimeSnapshotEnvelope as RuntimeSnapshotEnvelope
from aces_contracts.runtime_state import SnapshotEntry as SnapshotEntry
from aces_contracts.versions import EVALUATION_STATE_SCHEMA_VERSION as EVALUATION_STATE_SCHEMA_VERSION
from aces_contracts.versions import OPERATION_SCHEMA_VERSION as OPERATION_SCHEMA_VERSION
from aces_contracts.versions import PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION as PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION
from aces_contracts.versions import RUNTIME_SNAPSHOT_SCHEMA_VERSION as RUNTIME_SNAPSHOT_SCHEMA_VERSION
from aces_contracts.versions import WORKFLOW_STATE_SCHEMA_VERSION as WORKFLOW_STATE_SCHEMA_VERSION
from aces_contracts.workflow import WorkflowCancellationRequest as WorkflowCancellationRequest
from aces_contracts.workflow import WorkflowCompensationStatus as WorkflowCompensationStatus
from aces_contracts.workflow import WorkflowExecutionContract as WorkflowExecutionContract
from aces_contracts.workflow import WorkflowExecutionState as WorkflowExecutionState
from aces_contracts.workflow import WorkflowHistoryEvent as WorkflowHistoryEvent
from aces_contracts.workflow import WorkflowHistoryEventType as WorkflowHistoryEventType
from aces_contracts.workflow import WorkflowResultContract as WorkflowResultContract
from aces_contracts.workflow import WorkflowStatus as WorkflowStatus
from aces_contracts.workflow import WorkflowStepExecutionState as WorkflowStepExecutionState
from aces_contracts.workflow import WorkflowStepLifecycle as WorkflowStepLifecycle
from aces_contracts.workflow import WorkflowStepOutcome as WorkflowStepOutcome
from aces_contracts.workflow import validate_workflow_step_result_contract as validate_workflow_step_result_contract
from aces_sdl.participant_temporal_semantics import ParticipantTemporalState as ParticipantTemporalState

from aces_processor.semantics.realization import CompiledRealizationRequirement as CompiledRealizationRequirement

from .action_results import (
    ParticipantActionEffectResult,
    ParticipantActionPreconditionResult,
    ParticipantActionResult,
)
from .attribution import (
    ParticipantAttributionCandidate,
    ParticipantAttributionEdge,
    ParticipantAttributionEvidenceBasis,
    ParticipantAttributionOrderingBasis,
)
from .behavior_history_violations import (
    iter_participant_behavior_history_violations,
    iter_participant_behavior_joint_action_violations,
    validate_participant_outcome_interpretation_record,
)
from .behavior_resources import (
    EventRuntime,
    ObjectiveWindowReferenceRuntime,
    ParticipantBehaviorRuntime,
    ParticipantBehaviorSpecificationRuntime,
    ParticipantObservationBoundaryRuntime,
    ParticipantOutcomeInterpretationRuleRuntime,
    ScriptRuntime,
    StoryRuntime,
    WorkflowPredicateRuntime,
    WorkflowRuntime,
    WorkflowStepRuntime,
    WorkflowStepStatePredicateRuntime,
    WorkflowSwitchCaseRuntime,
)
from .history_event import (
    ParticipantBehaviorHistoryEvent,
)
from .outcome import (
    ParticipantOutcomeInterpretationRecord,
    ParticipantOutcomeSourceRecord,
    ParticipantOutcomeTargetRecord,
)
from .resources import (
    AccountPlacement,
    AssertionRuntime,
    ConditionBinding,
    ContentPlacement,
    FeatureBinding,
    InjectBinding,
    InjectRuntime,
    NetworkRuntime,
    NodeRuntime,
    ParticipantActionContractRuntime,
    PropositionRuntime,
    ResolvedResource,
    RuntimeTemplate,
    map_backend_diagnostic_to_participant_failure,
    validate_participant_action_result_contract,
)
from .runtime_model import (
    CompiledCapabilityConstraint,
    ExecutionPlan,
    ObjectiveRuntime,
    RuntimeModel,
    resource_payload,
)
from .temporal import (
    ParticipantTemporalRuntimeContext,
    ParticipantTemporalStateTransition,
    iter_participant_temporal_state_machine_violations,
)

__all__ = [
    "AccountPlacement",
    "ApplyResult",
    "AssertionRuntime",
    "ChangeAction",
    "CompiledCapabilityConstraint",
    "CompiledRealizationRequirement",
    "ConditionBinding",
    "ContentPlacement",
    "Diagnostic",
    "EVALUATION_STATE_SCHEMA_VERSION",
    "EvaluationExecutionContract",
    "EvaluationExecutionState",
    "EvaluationHistoryEvent",
    "EvaluationHistoryEventType",
    "EvaluationOp",
    "EvaluationPlan",
    "EvaluationResultContract",
    "EvaluationResultStatus",
    "EventRuntime",
    "ExecutionPlan",
    "FeatureBinding",
    "InjectBinding",
    "InjectRuntime",
    "NetworkRuntime",
    "NodeRuntime",
    "OPERATION_SCHEMA_VERSION",
    "ObjectiveRuntime",
    "ObjectiveWindowReferenceRuntime",
    "OperationReceipt",
    "OperationState",
    "OperationStatus",
    "OrchestrationOp",
    "OrchestrationPlan",
    "PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION",
    "ParticipantActionContractRuntime",
    "ParticipantActionEffectResult",
    "ParticipantActionPreconditionResult",
    "ParticipantActionPreconditionStatus",
    "ParticipantActionResult",
    "ParticipantActionResultStatus",
    "ParticipantAdmissionDisposition",
    "ParticipantAttributionCandidate",
    "ParticipantAttributionEdge",
    "ParticipantAttributionEvidenceBasis",
    "ParticipantAttributionOrderingBasis",
    "ParticipantBehaviorHistoryEvent",
    "ParticipantBehaviorHistoryEventType",
    "ParticipantBehaviorRuntime",
    "ParticipantBehaviorSpecificationRuntime",
    "ParticipantEpisodeControlAction",
    "ParticipantEpisodeExecutionState",
    "ParticipantEpisodeHistoryEvent",
    "ParticipantEpisodeHistoryEventType",
    "ParticipantEpisodeInitializeRequest",
    "ParticipantEpisodeResetRequest",
    "ParticipantEpisodeRestartRequest",
    "ParticipantEpisodeStatus",
    "ParticipantEpisodeTerminalReason",
    "ParticipantEpisodeTerminateRequest",
    "ParticipantLifecycleOperationState",
    "ParticipantObservationBoundaryRuntime",
    "ParticipantObservationStatus",
    "ParticipantOutcomeInterpretationRecord",
    "ParticipantOutcomeInterpretationRuleRuntime",
    "ParticipantOutcomeSourceRecord",
    "ParticipantOutcomeTargetRecord",
    "ParticipantPhaseRealization",
    "ParticipantRuntimeLifecyclePhase",
    "ParticipantTemporalRuntimeContext",
    "ParticipantTemporalState",
    "ParticipantTemporalStateTransition",
    "PlanOperation",
    "PlannedResource",
    "PropositionRuntime",
    "ProvisionOp",
    "ProvisioningPlan",
    "RUNTIME_SNAPSHOT_SCHEMA_VERSION",
    "RealizationProvenanceEntry",
    "ResolvedResource",
    "RuntimeDomain",
    "RuntimeModel",
    "RuntimeSnapshot",
    "RuntimeSnapshotEnvelope",
    "RuntimeTemplate",
    "ScriptRuntime",
    "Severity",
    "SnapshotEntry",
    "StoryRuntime",
    "WORKFLOW_STATE_SCHEMA_VERSION",
    "WorkflowCancellationRequest",
    "WorkflowCompensationStatus",
    "WorkflowExecutionContract",
    "WorkflowExecutionState",
    "WorkflowHistoryEvent",
    "WorkflowHistoryEventType",
    "WorkflowPredicateRuntime",
    "WorkflowResultContract",
    "WorkflowRuntime",
    "WorkflowStatus",
    "WorkflowStepExecutionState",
    "WorkflowStepLifecycle",
    "WorkflowStepOutcome",
    "WorkflowStepRuntime",
    "WorkflowStepStatePredicateRuntime",
    "WorkflowSwitchCaseRuntime",
    "iter_participant_behavior_history_violations",
    "iter_participant_behavior_joint_action_violations",
    "iter_participant_episode_snapshot_violations",
    "iter_participant_temporal_state_machine_violations",
    "map_backend_diagnostic_to_participant_failure",
    "participant_lifecycle_field_violation_messages",
    "resource_payload",
    "validate_evaluation_result",
    "validate_participant_action_result_contract",
    "validate_participant_outcome_interpretation_record",
    "validate_workflow_step_result_contract",
]
