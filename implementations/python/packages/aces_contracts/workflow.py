"""Shared workflow runtime result contracts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aces_sdl.semantics.workflow import WorkflowStepSemanticContract
from aces_sdl.semantics.workflow import validate_workflow_step_result as _validate_workflow_step_result

from aces_contracts.versions import WORKFLOW_STATE_SCHEMA_VERSION


class WorkflowStepLifecycle(str, Enum):
    """Portable execution lifecycle for workflow-visible step state."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


class WorkflowStepOutcome(str, Enum):
    """Portable execution outcomes for workflow-visible step state."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXHAUSTED = "exhausted"


class WorkflowStatus(str, Enum):
    """Portable workflow-level execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class WorkflowCompensationStatus(str, Enum):
    """Portable workflow compensation status."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WorkflowHistoryEventType(str, Enum):
    """Portable workflow history event kinds."""

    WORKFLOW_STARTED = "workflow_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    SWITCH_CASE_SELECTED = "switch_case_selected"
    CALL_STARTED = "call_started"
    CALL_COMPLETED = "call_completed"
    BRANCH_ENTERED = "branch_entered"
    BRANCH_CONVERGED = "branch_converged"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_TIMED_OUT = "workflow_timed_out"
    COMPENSATION_REGISTERED = "compensation_registered"
    COMPENSATION_STARTED = "compensation_started"
    COMPENSATION_WORKFLOW_STARTED = "compensation_workflow_started"
    COMPENSATION_WORKFLOW_COMPLETED = "compensation_workflow_completed"
    COMPENSATION_WORKFLOW_FAILED = "compensation_workflow_failed"
    COMPENSATION_COMPLETED = "compensation_completed"
    COMPENSATION_FAILED = "compensation_failed"


@dataclass(frozen=True)
class WorkflowResultContract:
    """Compiled contract for validating portable workflow result envelopes."""

    state_schema_version: str = WORKFLOW_STATE_SCHEMA_VERSION
    observable_steps: dict[str, WorkflowStepSemanticContract] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.state_schema_version, str) or not self.state_schema_version:
            raise TypeError("workflow result contract state_schema_version must be a non-empty string")
        if not isinstance(self.observable_steps, dict):
            raise TypeError("workflow result contract observable_steps must be a dict")
        if any(not isinstance(step_name, str) for step_name in self.observable_steps):
            raise TypeError("workflow result contract step names must be strings")
        if any(not isinstance(contract, WorkflowStepSemanticContract) for contract in self.observable_steps.values()):
            raise TypeError("workflow result contract step contracts must be WorkflowStepSemanticContract values")

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> WorkflowResultContract:
        if not isinstance(payload, Mapping):
            raise TypeError("workflow result contract must be a mapping")
        observable_steps_payload = payload.get("observable_steps", {})
        if not isinstance(observable_steps_payload, Mapping):
            raise TypeError("workflow result contract observable_steps must be a mapping")
        observable_steps: dict[str, WorkflowStepSemanticContract] = {}
        for step_name, step_payload in observable_steps_payload.items():
            if not isinstance(step_name, str):
                raise TypeError("workflow result contract step names must be strings")
            if not isinstance(step_payload, Mapping):
                raise TypeError("workflow result contract step payloads must be mappings")
            observable_steps[step_name] = WorkflowStepSemanticContract.from_mapping(step_payload)
            if not observable_steps[step_name].state_observable:
                raise ValueError("workflow result contract may only include observable steps")
        return cls(
            state_schema_version=str(payload.get("state_schema_version", WORKFLOW_STATE_SCHEMA_VERSION)),
            observable_steps=observable_steps,
        )


def validate_workflow_step_result_contract(
    contract: WorkflowStepSemanticContract,
    *,
    lifecycle: str,
    outcome: str | None,
    attempts: int,
) -> tuple[str, ...]:
    """Validate a backend-reported workflow step result against a compiled contract."""

    return _validate_workflow_step_result(
        contract,
        lifecycle=lifecycle,
        outcome=outcome,
        attempts=attempts,
    )


@dataclass(frozen=True)
class WorkflowExecutionContract:
    """Compiled contract for validating workflow-level execution state/history."""

    state_schema_version: str = WORKFLOW_STATE_SCHEMA_VERSION
    start_step: str = ""
    timeout_seconds: int | None = None
    steps: dict[str, WorkflowStepSemanticContract] = field(default_factory=dict)
    step_types: dict[str, str] = field(default_factory=dict)
    control_edges: dict[str, tuple[str, ...]] = field(default_factory=dict)
    join_owners: dict[str, str] = field(default_factory=dict)
    call_steps: dict[str, str] = field(default_factory=dict)
    compensation_mode: str = "disabled"
    compensation_triggers: tuple[str, ...] = ()
    compensation_targets: dict[str, str] = field(default_factory=dict)
    compensation_ordering: str = "reverse_completion"
    compensation_failure_policy: str = "fail_workflow"
    observable_steps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.state_schema_version, str) or not self.state_schema_version:
            raise TypeError("workflow execution contract state_schema_version must be a non-empty string")
        if not isinstance(self.start_step, str):
            raise TypeError("workflow execution contract start_step must be a string")
        if self.timeout_seconds is not None:
            if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int):
                raise TypeError("workflow execution contract timeout_seconds must be an int or None")
            if self.timeout_seconds <= 0:
                raise ValueError("workflow execution contract timeout_seconds must be > 0")
        if not isinstance(self.steps, dict):
            raise TypeError("workflow execution contract steps must be a dict")
        if any(not isinstance(name, str) for name in self.steps):
            raise TypeError("workflow execution contract step names must be strings")
        if any(not isinstance(contract, WorkflowStepSemanticContract) for contract in self.steps.values()):
            raise TypeError("workflow execution contract step contracts must be WorkflowStepSemanticContract values")
        if not isinstance(self.step_types, dict):
            raise TypeError("workflow execution contract step_types must be a dict")
        if any(
            not isinstance(name, str) or not isinstance(step_type, str) for name, step_type in self.step_types.items()
        ):
            raise TypeError("workflow execution contract step_types must map strings to strings")
        if not isinstance(self.control_edges, dict):
            raise TypeError("workflow execution contract control_edges must be a dict")
        if not isinstance(self.join_owners, dict):
            raise TypeError("workflow execution contract join_owners must be a dict")
        if not isinstance(self.call_steps, dict):
            raise TypeError("workflow execution contract call_steps must be a dict")
        if any(
            not isinstance(step_name, str) or not isinstance(workflow_address, str)
            for step_name, workflow_address in self.call_steps.items()
        ):
            raise TypeError("workflow execution contract call_steps must map strings to strings")
        if not isinstance(self.compensation_mode, str):
            raise TypeError("workflow execution contract compensation_mode must be a string")
        if any(not isinstance(trigger, str) for trigger in self.compensation_triggers):
            raise TypeError("workflow execution contract compensation_triggers must be strings")
        if not isinstance(self.compensation_targets, dict):
            raise TypeError("workflow execution contract compensation_targets must be a dict")
        if any(
            not isinstance(step_name, str) or not isinstance(workflow_address, str)
            for step_name, workflow_address in self.compensation_targets.items()
        ):
            raise TypeError("workflow execution contract compensation_targets must map strings to strings")
        if not isinstance(self.compensation_ordering, str):
            raise TypeError("workflow execution contract compensation_ordering must be a string")
        if not isinstance(self.compensation_failure_policy, str):
            raise TypeError("workflow execution contract compensation_failure_policy must be a string")
        if any(not isinstance(step_name, str) for step_name in self.observable_steps):
            raise TypeError("workflow execution contract observable_steps must be strings")

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> WorkflowExecutionContract:
        if not isinstance(payload, Mapping):
            raise TypeError("workflow execution contract must be a mapping")
        steps_payload = payload.get("steps", {})
        if not isinstance(steps_payload, Mapping):
            raise TypeError("workflow execution contract steps must be a mapping")
        steps: dict[str, WorkflowStepSemanticContract] = {}
        for step_name, step_payload in steps_payload.items():
            if not isinstance(step_name, str):
                raise TypeError("workflow execution contract step names must be strings")
            if not isinstance(step_payload, Mapping):
                raise TypeError("workflow execution contract step payloads must be mappings")
            steps[step_name] = WorkflowStepSemanticContract.from_mapping(step_payload)
        control_edges_payload = payload.get("control_edges", {})
        if not isinstance(control_edges_payload, Mapping):
            raise TypeError("workflow execution contract control_edges must be a mapping")
        control_edges = {
            str(step_name): tuple(str(successor) for successor in successors)
            for step_name, successors in control_edges_payload.items()
            if isinstance(successors, Iterable)
        }
        join_owners_payload = payload.get("join_owners", {})
        if not isinstance(join_owners_payload, Mapping):
            raise TypeError("workflow execution contract join_owners must be a mapping")
        return cls(
            state_schema_version=str(payload.get("state_schema_version", WORKFLOW_STATE_SCHEMA_VERSION)),
            start_step=str(payload.get("start_step", "")),
            timeout_seconds=(int(payload["timeout_seconds"]) if payload.get("timeout_seconds") is not None else None),
            steps=steps,
            step_types={
                str(step_name): str(step_type) for step_name, step_type in payload.get("step_types", {}).items()
            },
            control_edges=control_edges,
            join_owners={str(join): str(owner) for join, owner in join_owners_payload.items()},
            call_steps={
                str(step_name): str(workflow_address)
                for step_name, workflow_address in payload.get("call_steps", {}).items()
            },
            compensation_mode=str(payload.get("compensation_mode", "disabled")),
            compensation_triggers=tuple(str(trigger) for trigger in payload.get("compensation_triggers", ())),
            compensation_targets={
                str(step_name): str(workflow_address)
                for step_name, workflow_address in payload.get("compensation_targets", {}).items()
            },
            compensation_ordering=str(payload.get("compensation_ordering", "reverse_completion")),
            compensation_failure_policy=str(payload.get("compensation_failure_policy", "fail_workflow")),
            observable_steps=tuple(str(step_name) for step_name in payload.get("observable_steps", ())),
        )


@dataclass(frozen=True)
class WorkflowHistoryEvent:
    """Internal normalized workflow history event."""

    event_type: WorkflowHistoryEventType
    timestamp: str
    step_name: str | None = None
    branch_name: str | None = None
    join_step: str | None = None
    outcome: WorkflowStepOutcome | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> WorkflowHistoryEvent:
        if not isinstance(payload, Mapping):
            raise TypeError("workflow history event must be a mapping")
        event_type_raw = payload.get("event_type")
        timestamp_raw = payload.get("timestamp")
        if event_type_raw is None or timestamp_raw is None:
            raise ValueError("workflow history event is missing required fields: event_type, timestamp")
        outcome_raw = payload.get("outcome")
        return cls(
            event_type=(
                event_type_raw
                if isinstance(event_type_raw, WorkflowHistoryEventType)
                else WorkflowHistoryEventType(str(event_type_raw))
            ),
            timestamp=str(timestamp_raw),
            step_name=(str(payload["step_name"]) if payload.get("step_name") is not None else None),
            branch_name=(str(payload["branch_name"]) if payload.get("branch_name") is not None else None),
            join_step=(str(payload["join_step"]) if payload.get("join_step") is not None else None),
            outcome=(
                outcome_raw
                if isinstance(outcome_raw, WorkflowStepOutcome)
                else (WorkflowStepOutcome(str(outcome_raw)) if outcome_raw is not None else None)
            ),
            details=dict(payload.get("details", {})) if isinstance(payload.get("details", {}), Mapping) else {},
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "step_name": self.step_name,
            "branch_name": self.branch_name,
            "join_step": self.join_step,
            "outcome": self.outcome.value if self.outcome is not None else None,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class WorkflowStepExecutionState:
    """Internal normalized execution state for one workflow-visible step."""

    lifecycle: WorkflowStepLifecycle = WorkflowStepLifecycle.PENDING
    outcome: WorkflowStepOutcome | None = None
    attempts: int = 0

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> WorkflowStepExecutionState:
        if not isinstance(payload, Mapping):
            raise TypeError("workflow step result must be a mapping")
        missing_keys = [key for key in ("lifecycle", "outcome", "attempts") if key not in payload]
        if missing_keys:
            raise ValueError("workflow step result is missing required fields: " + ", ".join(missing_keys))
        lifecycle_raw = payload.get("lifecycle")
        outcome_raw = payload.get("outcome")
        attempts_raw = payload.get("attempts")
        lifecycle = (
            lifecycle_raw
            if isinstance(lifecycle_raw, WorkflowStepLifecycle)
            else WorkflowStepLifecycle(str(lifecycle_raw))
        )
        outcome = None
        if outcome_raw is not None:
            outcome = (
                outcome_raw if isinstance(outcome_raw, WorkflowStepOutcome) else WorkflowStepOutcome(str(outcome_raw))
            )
        if isinstance(attempts_raw, bool) or not isinstance(attempts_raw, int):
            raise TypeError("workflow step attempts must be an int")
        return cls(lifecycle=lifecycle, outcome=outcome, attempts=attempts_raw)

    def to_payload(self) -> dict[str, Any]:
        return {
            "lifecycle": self.lifecycle.value,
            "outcome": self.outcome.value if self.outcome is not None else None,
            "attempts": self.attempts,
        }

    def __post_init__(self) -> None:
        if not isinstance(self.lifecycle, WorkflowStepLifecycle):
            raise TypeError("lifecycle must be a WorkflowStepLifecycle")
        if self.outcome is not None and not isinstance(self.outcome, WorkflowStepOutcome):
            raise TypeError("outcome must be a WorkflowStepOutcome or None")
        if isinstance(self.attempts, bool) or not isinstance(self.attempts, int):
            raise TypeError("attempts must be an int")
        if self.attempts < 0:
            raise ValueError("attempts must be >= 0")
        if self.lifecycle != WorkflowStepLifecycle.COMPLETED and self.outcome is not None:
            raise ValueError("non-completed workflow steps may not report an outcome")
        if self.lifecycle == WorkflowStepLifecycle.PENDING and self.attempts != 0:
            raise ValueError("pending workflow steps must report 0 attempts")


@dataclass(frozen=True)
class WorkflowExecutionState:
    """Internal normalized workflow result envelope."""

    state_schema_version: str = WORKFLOW_STATE_SCHEMA_VERSION
    workflow_status: WorkflowStatus = WorkflowStatus.PENDING
    run_id: str = ""
    started_at: str = ""
    updated_at: str = ""
    terminal_reason: str | None = None
    compensation_status: WorkflowCompensationStatus = WorkflowCompensationStatus.NOT_REQUIRED
    compensation_started_at: str | None = None
    compensation_updated_at: str | None = None
    compensation_failures: list[dict[str, Any]] = field(default_factory=list)
    steps: dict[str, WorkflowStepExecutionState] = field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> WorkflowExecutionState:
        if not isinstance(payload, Mapping):
            raise TypeError("workflow result payload must be a mapping")
        missing_keys = [
            key
            for key in (
                "state_schema_version",
                "workflow_status",
                "run_id",
                "started_at",
                "updated_at",
                "compensation_status",
                "compensation_failures",
                "steps",
            )
            if key not in payload
        ]
        if missing_keys:
            raise ValueError("workflow result payload is missing required fields: " + ", ".join(missing_keys))
        state_schema_version = str(payload.get("state_schema_version"))
        workflow_status_raw = payload.get("workflow_status")
        steps_payload = payload.get("steps")
        if not isinstance(steps_payload, Mapping):
            raise TypeError("workflow result steps must be a mapping")
        steps: dict[str, WorkflowStepExecutionState] = {}
        for step_name, step_payload in steps_payload.items():
            if not isinstance(step_name, str):
                raise TypeError("workflow result step names must be strings")
            if not isinstance(step_payload, Mapping):
                raise TypeError("workflow result step payloads must be mappings")
            steps[step_name] = WorkflowStepExecutionState.from_payload(step_payload)
        return cls(
            state_schema_version=state_schema_version,
            workflow_status=(
                workflow_status_raw
                if isinstance(workflow_status_raw, WorkflowStatus)
                else WorkflowStatus(str(workflow_status_raw))
            ),
            run_id=str(payload.get("run_id")),
            started_at=str(payload.get("started_at")),
            updated_at=str(payload.get("updated_at")),
            terminal_reason=(str(payload["terminal_reason"]) if payload.get("terminal_reason") is not None else None),
            compensation_status=(
                payload.get("compensation_status")
                if isinstance(payload.get("compensation_status"), WorkflowCompensationStatus)
                else WorkflowCompensationStatus(str(payload.get("compensation_status")))
            ),
            compensation_started_at=(
                str(payload["compensation_started_at"]) if payload.get("compensation_started_at") is not None else None
            ),
            compensation_updated_at=(
                str(payload["compensation_updated_at"]) if payload.get("compensation_updated_at") is not None else None
            ),
            compensation_failures=[
                dict(item) for item in payload.get("compensation_failures", []) if isinstance(item, Mapping)
            ],
            steps=steps,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "state_schema_version": self.state_schema_version,
            "workflow_status": self.workflow_status.value,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "terminal_reason": self.terminal_reason,
            "compensation_status": self.compensation_status.value,
            "compensation_started_at": self.compensation_started_at,
            "compensation_updated_at": self.compensation_updated_at,
            "compensation_failures": [dict(item) for item in self.compensation_failures],
            "steps": {step_name: step_state.to_payload() for step_name, step_state in self.steps.items()},
        }

    def __post_init__(self) -> None:
        if not isinstance(self.state_schema_version, str) or not self.state_schema_version:
            raise TypeError("workflow result state_schema_version must be a non-empty string")
        if not isinstance(self.workflow_status, WorkflowStatus):
            raise TypeError("workflow_status must be a WorkflowStatus")
        if not isinstance(self.run_id, str) or not self.run_id:
            raise TypeError("run_id must be a non-empty string")
        if not isinstance(self.started_at, str) or not self.started_at:
            raise TypeError("started_at must be a non-empty string")
        if not isinstance(self.updated_at, str) or not self.updated_at:
            raise TypeError("updated_at must be a non-empty string")
        if self.terminal_reason is not None and not isinstance(self.terminal_reason, str):
            raise TypeError("terminal_reason must be a string or None")
        if not isinstance(self.compensation_status, WorkflowCompensationStatus):
            raise TypeError("compensation_status must be a WorkflowCompensationStatus")
        if self.compensation_started_at is not None and not isinstance(self.compensation_started_at, str):
            raise TypeError("compensation_started_at must be a string or None")
        if self.compensation_updated_at is not None and not isinstance(self.compensation_updated_at, str):
            raise TypeError("compensation_updated_at must be a string or None")
        if not isinstance(self.compensation_failures, list):
            raise TypeError("compensation_failures must be a list")
        if any(not isinstance(item, dict) for item in self.compensation_failures):
            raise TypeError("compensation_failures entries must be dicts")
        if not isinstance(self.steps, dict):
            raise TypeError("workflow step results must be stored in a dict")
        if any(not isinstance(step_name, str) for step_name in self.steps):
            raise TypeError("workflow step result keys must be strings")
        if any(not isinstance(step_state, WorkflowStepExecutionState) for step_state in self.steps.values()):
            raise TypeError("workflow step results must be WorkflowStepExecutionState values")
        if (
            self.workflow_status
            in {
                WorkflowStatus.SUCCEEDED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
                WorkflowStatus.TIMED_OUT,
            }
            and self.terminal_reason is None
        ):
            raise ValueError("terminal workflow statuses must include terminal_reason")
        if (
            self.workflow_status in {WorkflowStatus.PENDING, WorkflowStatus.RUNNING}
            and self.terminal_reason is not None
        ):
            raise ValueError("non-terminal workflow statuses may not include terminal_reason")
        if self.workflow_status in {WorkflowStatus.PENDING, WorkflowStatus.RUNNING}:
            if self.compensation_status != WorkflowCompensationStatus.NOT_REQUIRED:
                raise ValueError("non-terminal workflow statuses may not report compensation activity")
            if self.compensation_started_at is not None or self.compensation_updated_at is not None:
                raise ValueError("non-terminal workflow statuses may not report compensation timestamps")
        if self.compensation_status == WorkflowCompensationStatus.NOT_REQUIRED:
            if self.compensation_started_at is not None or self.compensation_updated_at is not None:
                raise ValueError("compensation_status=not_required may not report compensation timestamps")
            if self.compensation_failures:
                raise ValueError("compensation_status=not_required may not report compensation failures")
        if self.compensation_status == WorkflowCompensationStatus.RUNNING and self.compensation_started_at is None:
            raise ValueError("compensation_status=running requires compensation_started_at")


@dataclass(frozen=True)
class WorkflowCancellationRequest:
    """Portable request for cancelling one workflow run."""

    workflow_address: str
    run_id: str | None = None
    reason: str = "cancelled by operator"


__all__ = (
    "WorkflowCancellationRequest",
    "WorkflowCompensationStatus",
    "WorkflowExecutionContract",
    "WorkflowExecutionState",
    "WorkflowHistoryEvent",
    "WorkflowHistoryEventType",
    "WorkflowResultContract",
    "WorkflowStatus",
    "WorkflowStepExecutionState",
    "WorkflowStepLifecycle",
    "WorkflowStepOutcome",
    "validate_workflow_step_result_contract",
)
