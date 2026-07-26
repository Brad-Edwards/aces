"""Realization plan, snapshot, and operation-receipt contracts."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator
from raes.explicitness import ExplicitnessClass, ExplicitnessProvenance

from ..addressing import CompiledAddress
from ..planning import RuntimeDomain, require_plan_operation_identity
from ..versions import OPERATION_SCHEMA_VERSION, RUNTIME_SNAPSHOT_SCHEMA_VERSION
from .base import ContractModel, NonEmptyString
from .execution_state import (
    EvaluationHistoryEventModel,
    EvaluationResultStateModel,
    PropositionTruthResultModel,
    WorkflowExecutionStateModel,
    WorkflowHistoryEventModel,
)
from .participant_control import ParticipantControlOccurrenceModel
from .participant_envelopes import (
    ParticipantJointActionRecordModel,
    ParticipantSharedStateRecordModel,
    ParticipantTimeManagementContextModel,
)
from .participant_execution import ParticipantExecutionServiceStateModel
from .participant_runtime import (
    ParticipantAutonomousExecutionStateModel,
    ParticipantBehaviorHistoryEventModel,
    ParticipantEpisodeHistoryEventModel,
    ParticipantEpisodeStateModel,
)
from .time_model import TimeRuntimeStateModel


class PlanOperationModel(ContractModel):
    action: str
    address: CompiledAddress
    resource_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ordering_dependencies: list[CompiledAddress] = Field(default_factory=list)
    refresh_dependencies: list[CompiledAddress] = Field(default_factory=list)


def _require_unique_operation_addresses(operations: list[PlanOperationModel]) -> None:
    addresses = [operation.address for operation in operations]
    if len(addresses) != len(set(addresses)):
        raise ValueError("Plan operation addresses must be unique")


def _require_operation_identities(operations: list[PlanOperationModel], domain: RuntimeDomain) -> None:
    for operation in operations:
        require_plan_operation_identity(domain, operation.address, operation.resource_type)


def _require_startup_order_addresses(
    operations: list[PlanOperationModel],
    startup_order: list[str],
) -> None:
    if len(startup_order) != len(set(startup_order)):
        raise ValueError("Plan startup_order addresses must be unique")
    operation_addresses = {operation.address for operation in operations}
    unknown = set(startup_order) - operation_addresses
    if unknown:
        raise ValueError("Plan startup_order must reference admitted operation addresses")


class RealizationEnvelopeIdentityModel(ContractModel):
    """Immutable realization-envelope identity carried across runtime contracts."""

    contract_id: Literal["realization-envelope-v1"] = "realization-envelope-v1"
    envelope_id: NonEmptyString
    schema_version: Literal["realization-envelope/v1"] = "realization-envelope/v1"
    digest: Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
    configuration_digest: Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]


class ProvisioningPlanModel(ContractModel):
    operations: list[PlanOperationModel] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    realization_envelope: RealizationEnvelopeIdentityModel | None = None

    @model_validator(mode="after")
    def _validate_operation_addresses(self) -> ProvisioningPlanModel:
        _require_unique_operation_addresses(self.operations)
        _require_operation_identities(self.operations, RuntimeDomain.PROVISIONING)
        return self


class OrchestrationPlanModel(ContractModel):
    operations: list[PlanOperationModel] = Field(default_factory=list)
    startup_order: list[CompiledAddress] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_operation_addresses(self) -> OrchestrationPlanModel:
        _require_unique_operation_addresses(self.operations)
        _require_operation_identities(self.operations, RuntimeDomain.ORCHESTRATION)
        _require_startup_order_addresses(self.operations, self.startup_order)
        return self


class EvaluationPlanModel(ContractModel):
    operations: list[PlanOperationModel] = Field(default_factory=list)
    startup_order: list[CompiledAddress] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_operation_addresses(self) -> EvaluationPlanModel:
        _require_unique_operation_addresses(self.operations)
        _require_operation_identities(self.operations, RuntimeDomain.EVALUATION)
        _require_startup_order_addresses(self.operations, self.startup_order)
        return self


class SnapshotEntryModel(ContractModel):
    address: CompiledAddress
    domain: str
    resource_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ordering_dependencies: list[CompiledAddress] = Field(default_factory=list)
    refresh_dependencies: list[CompiledAddress] = Field(default_factory=list)
    status: str = "ready"


class RealizationProvenanceEntryModel(ContractModel):
    """SEM-218 invariant I5: provenance for one realized realization concern.

    Distinguishes ``author-declared`` / ``processor-derived`` / ``backend-realized``
    origins for a realized concern recorded on the snapshot's result / history
    surfaces. Carries field-path and kind references only (never the realized
    value, per the SEM-218 host-exposure gate). Kept distinct from ADR-054
    lifecycle ``phase_realization`` and API-407 participant feature support.
    """

    address: NonEmptyString
    field_path: NonEmptyString
    domain: NonEmptyString
    requirement_kind: NonEmptyString
    explicitness: ExplicitnessClass
    provenance: ExplicitnessProvenance
    governing_scope: NonEmptyString | None = None


class RuntimeSnapshotEnvelopeModel(ContractModel):
    """Published envelope for a live runtime snapshot.

    Participant episode surfaces (``participant_episode_results`` and
    ``participant_episode_history``) are both keyed by the stable
    ``participant_address`` of the participant the state/history belongs
    to. SEM-208 participant behavior history is keyed the same way and
    records action, observation, and state-transition events with compiled
    behavior-contract addresses. The episode results map carries the
    currently-live episode state per participant; prior episodes survive only
    through append-only history streams and the ``previous_episode_id`` chain
    on each state.
    """

    schema_version: Literal[RUNTIME_SNAPSHOT_SCHEMA_VERSION] = RUNTIME_SNAPSHOT_SCHEMA_VERSION
    entries: dict[CompiledAddress, SnapshotEntryModel] = Field(default_factory=dict)
    orchestration_results: dict[str, WorkflowExecutionStateModel] = Field(default_factory=dict)
    orchestration_history: dict[str, list[WorkflowHistoryEventModel]] = Field(default_factory=dict)
    evaluation_results: dict[str, EvaluationResultStateModel] = Field(default_factory=dict)
    evaluation_history: dict[str, list[EvaluationHistoryEventModel]] = Field(default_factory=dict)
    proposition_truth_results: dict[str, PropositionTruthResultModel] = Field(default_factory=dict)
    participant_episode_results: dict[str, ParticipantEpisodeStateModel] = Field(default_factory=dict)
    participant_episode_history: dict[str, list[ParticipantEpisodeHistoryEventModel]] = Field(default_factory=dict)
    participant_behavior_history: dict[str, list[ParticipantBehaviorHistoryEventModel]] = Field(default_factory=dict)
    participant_control_history: dict[str, list[ParticipantControlOccurrenceModel]] = Field(default_factory=dict)
    participant_autonomous_execution_states: dict[str, ParticipantAutonomousExecutionStateModel] = Field(
        default_factory=dict
    )
    participant_execution_services: dict[str, ParticipantExecutionServiceStateModel] = Field(default_factory=dict)
    shared_state_records: dict[str, ParticipantSharedStateRecordModel] = Field(default_factory=dict)
    shared_state_history: dict[str, list[ParticipantSharedStateRecordModel]] = Field(default_factory=dict)
    joint_action_records: dict[str, ParticipantJointActionRecordModel] = Field(default_factory=dict)
    time_management_contexts: dict[str, ParticipantTimeManagementContextModel] = Field(default_factory=dict)
    time_model_state: TimeRuntimeStateModel | None = None
    realization_provenance: list[RealizationProvenanceEntryModel] = Field(default_factory=list)
    realization_envelope: RealizationEnvelopeIdentityModel | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_entry_addresses(self) -> RuntimeSnapshotEnvelopeModel:
        for map_key, entry in self.entries.items():
            if map_key != entry.address:
                raise ValueError("Runtime snapshot entries map key must equal embedded address")
        for map_key, state in self.participant_autonomous_execution_states.items():
            expected = f"{state.policy_address}.state.{state.participant_address}"
            if map_key != expected:
                raise ValueError(
                    "Autonomous participant state map key must equal the embedded policy and participant address"
                )
        for map_key, state in self.participant_execution_services.items():
            if map_key != state.execution_scope_ref:
                raise ValueError("Participant execution service map key must equal execution_scope_ref")
        return self


class OperationReceiptModel(ContractModel):
    schema_version: Literal[OPERATION_SCHEMA_VERSION] = OPERATION_SCHEMA_VERSION
    operation_id: str
    domain: str
    submitted_at: str
    accepted: bool
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


class OperationStatusModel(ContractModel):
    schema_version: Literal[OPERATION_SCHEMA_VERSION] = OPERATION_SCHEMA_VERSION
    operation_id: str
    domain: str
    state: str
    submitted_at: str
    updated_at: str
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    changed_addresses: list[CompiledAddress] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_changed_addresses(self) -> OperationStatusModel:
        if len(self.changed_addresses) != len(set(self.changed_addresses)):
            raise ValueError("changed addresses must be unique")
        return self
