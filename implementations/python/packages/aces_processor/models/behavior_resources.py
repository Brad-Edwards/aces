"""Participant-behavior and workflow resource records plus shared validation helpers."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from aces_backend_protocols.capabilities import WorkflowFeature, WorkflowStatePredicateFeature
from aces_contracts.participant_behavior import ParticipantObservationStatus
from aces_contracts.versions import WORKFLOW_STATE_SCHEMA_VERSION
from aces_contracts.workflow import WorkflowExecutionContract, WorkflowResultContract, WorkflowStepOutcome
from aces_sdl.semantics.workflow import WorkflowStepSemanticContract

from .resources import ResolvedResource


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
    starting_assertion_refs: tuple[str, ...] = ()
    starting_assertion_addresses: tuple[str, ...] = ()
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
    ai_offensive_behavior_refs: tuple[str, ...] = ()
    offensive_behavior_refs: tuple[str, ...] = ()
    realization_profile_ref: str = ""
    backend_feature_support_refs: tuple[str, ...] = ()
    evidence_contract_refs: tuple[str, ...] = ()
    extension_policy: str = ""
    extension_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class EventRuntime(ResolvedResource):
    """Resolved orchestration event."""

    assertion_names: tuple[str, ...] = ()
    assertion_addresses: tuple[str, ...] = ()
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

    assertion_addresses: tuple[str, ...] = ()
    objective_addresses: tuple[str, ...] = ()
    step_state_predicates: tuple[WorkflowStepStatePredicateRuntime, ...] = ()

    @property
    def external_addresses(self) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for address in (
            *self.assertion_addresses,
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
    step_assertion_addresses: dict[str, tuple[str, ...]] = field(default_factory=dict)
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


def _optional_payload_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return str(value) if value is not None else None


_PARTICIPANT_TERMINAL_OBSERVATION_STATUSES = frozenset(
    {
        ParticipantObservationStatus.TERMINAL,
        ParticipantObservationStatus.ORPHANED_ACTION,
    }
)
_PARTICIPANT_VISIBLE_VIEW_DISPOSITIONS = frozenset({"observable", "discovered", "inferred", "disclosed", "deceptive"})
_PARTICIPANT_OBSERVATION_DETAIL_REF_KEYS = ("visible_refs", "disclosed_refs", "evidence_refs")
_PARTICIPANT_OBSERVATION_DETAIL_KEYS = frozenset(_PARTICIPANT_OBSERVATION_DETAIL_REF_KEYS)
