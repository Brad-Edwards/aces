"""Shared evaluation runtime result contracts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aces_contracts.versions import EVALUATION_STATE_SCHEMA_VERSION


class EvaluationResultStatus(str, Enum):
    """Portable lifecycle for evaluator-observable results."""

    PENDING = "pending"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


class EvaluationHistoryEventType(str, Enum):
    """Portable evaluator history event kinds."""

    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_UPDATED = "evaluation_updated"
    EVALUATION_READY = "evaluation_ready"
    EVALUATION_FAILED = "evaluation_failed"


@dataclass(frozen=True)
class EvaluationResultContract:
    """Compiled contract for validating evaluator result envelopes."""

    state_schema_version: str = EVALUATION_STATE_SCHEMA_VERSION
    resource_type: str = ""
    supports_passed: bool = False
    supports_score: bool = False
    fixed_max_score: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state_schema_version, str) or not self.state_schema_version:
            raise TypeError("evaluation result contract state_schema_version must be a non-empty string")
        if not isinstance(self.resource_type, str) or not self.resource_type:
            raise TypeError("evaluation result contract resource_type must be a non-empty string")
        if not isinstance(self.supports_passed, bool):
            raise TypeError("evaluation result contract supports_passed must be a bool")
        if not isinstance(self.supports_score, bool):
            raise TypeError("evaluation result contract supports_score must be a bool")
        if self.fixed_max_score is not None:
            if isinstance(self.fixed_max_score, bool) or not isinstance(self.fixed_max_score, int):
                raise TypeError("evaluation result contract fixed_max_score must be an int or None")
            if self.fixed_max_score < 0:
                raise ValueError("evaluation result contract fixed_max_score must be >= 0")
            if not self.supports_score:
                raise ValueError("evaluation result contract fixed_max_score requires supports_score")

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> EvaluationResultContract:
        if not isinstance(payload, Mapping):
            raise TypeError("evaluation result contract must be a mapping")
        fixed_max_score_raw = payload.get("fixed_max_score")
        fixed_max_score: int | None
        if fixed_max_score_raw is None:
            fixed_max_score = None
        elif isinstance(fixed_max_score_raw, bool) or not isinstance(fixed_max_score_raw, int):
            raise TypeError("evaluation result contract fixed_max_score must be an int or None")
        else:
            fixed_max_score = fixed_max_score_raw
        return cls(
            state_schema_version=str(payload.get("state_schema_version", EVALUATION_STATE_SCHEMA_VERSION)),
            resource_type=str(payload.get("resource_type", "")),
            supports_passed=bool(payload.get("supports_passed", False)),
            supports_score=bool(payload.get("supports_score", False)),
            fixed_max_score=fixed_max_score,
        )


@dataclass(frozen=True)
class EvaluationExecutionContract:
    """Compiled contract for validating evaluator history/state transitions."""

    state_schema_version: str = EVALUATION_STATE_SCHEMA_VERSION
    resource_type: str = ""
    allowed_statuses: tuple[str, ...] = (
        EvaluationResultStatus.PENDING.value,
        EvaluationResultStatus.RUNNING.value,
        EvaluationResultStatus.READY.value,
        EvaluationResultStatus.FAILED.value,
    )
    history_event_types: tuple[str, ...] = (
        EvaluationHistoryEventType.EVALUATION_STARTED.value,
        EvaluationHistoryEventType.EVALUATION_UPDATED.value,
        EvaluationHistoryEventType.EVALUATION_READY.value,
        EvaluationHistoryEventType.EVALUATION_FAILED.value,
    )
    requires_start_event: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.state_schema_version, str) or not self.state_schema_version:
            raise TypeError("evaluation execution contract state_schema_version must be a non-empty string")
        if not isinstance(self.resource_type, str) or not self.resource_type:
            raise TypeError("evaluation execution contract resource_type must be a non-empty string")
        if any(not isinstance(status, str) for status in self.allowed_statuses):
            raise TypeError("evaluation execution contract allowed_statuses must be strings")
        if any(not isinstance(event_type, str) for event_type in self.history_event_types):
            raise TypeError("evaluation execution contract history_event_types must be strings")
        if not isinstance(self.requires_start_event, bool):
            raise TypeError("evaluation execution contract requires_start_event must be a bool")

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> EvaluationExecutionContract:
        if not isinstance(payload, Mapping):
            raise TypeError("evaluation execution contract must be a mapping")
        return cls(
            state_schema_version=str(payload.get("state_schema_version", EVALUATION_STATE_SCHEMA_VERSION)),
            resource_type=str(payload.get("resource_type", "")),
            allowed_statuses=tuple(
                str(status)
                for status in payload.get(
                    "allowed_statuses",
                    (
                        EvaluationResultStatus.PENDING.value,
                        EvaluationResultStatus.RUNNING.value,
                        EvaluationResultStatus.READY.value,
                        EvaluationResultStatus.FAILED.value,
                    ),
                )
            ),
            history_event_types=tuple(
                str(event_type)
                for event_type in payload.get(
                    "history_event_types",
                    (
                        EvaluationHistoryEventType.EVALUATION_STARTED.value,
                        EvaluationHistoryEventType.EVALUATION_UPDATED.value,
                        EvaluationHistoryEventType.EVALUATION_READY.value,
                        EvaluationHistoryEventType.EVALUATION_FAILED.value,
                    ),
                )
            ),
            requires_start_event=bool(payload.get("requires_start_event", True)),
        )


@dataclass(frozen=True)
class EvaluationHistoryEvent:
    """Internal normalized evaluator history event."""

    event_type: EvaluationHistoryEventType
    timestamp: str
    status: EvaluationResultStatus
    passed: bool | None = None
    score: float | int | None = None
    max_score: int | None = None
    detail: str | None = None
    evidence_refs: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> EvaluationHistoryEvent:
        if not isinstance(payload, Mapping):
            raise TypeError("evaluation history event must be a mapping")
        missing_keys = [key for key in ("event_type", "timestamp", "status") if key not in payload]
        if missing_keys:
            raise ValueError("evaluation history event is missing required fields: " + ", ".join(missing_keys))
        score_raw = payload.get("score")
        max_score_raw = payload.get("max_score")
        evidence_refs_raw = payload.get("evidence_refs", ())
        if isinstance(evidence_refs_raw, (str, bytes)) or not isinstance(evidence_refs_raw, Iterable):
            raise TypeError("evaluation history event evidence_refs must be an iterable of strings")
        evidence_ref_items = list(evidence_refs_raw)
        evidence_refs = tuple(str(ref) for ref in evidence_ref_items if isinstance(ref, str))
        if len(evidence_refs) != len(evidence_ref_items):
            raise TypeError("evaluation history event evidence_refs must contain only strings")
        return cls(
            event_type=(
                payload["event_type"]
                if isinstance(payload["event_type"], EvaluationHistoryEventType)
                else EvaluationHistoryEventType(str(payload["event_type"]))
            ),
            timestamp=str(payload["timestamp"]),
            status=(
                payload["status"]
                if isinstance(payload["status"], EvaluationResultStatus)
                else EvaluationResultStatus(str(payload["status"]))
            ),
            passed=(payload.get("passed") if isinstance(payload.get("passed"), bool) else None),
            score=(score_raw if isinstance(score_raw, (int, float)) and not isinstance(score_raw, bool) else None),
            max_score=(
                max_score_raw if isinstance(max_score_raw, int) and not isinstance(max_score_raw, bool) else None
            ),
            detail=(str(payload["detail"]) if payload.get("detail") is not None else None),
            evidence_refs=evidence_refs,
            details=dict(payload.get("details", {})) if isinstance(payload.get("details", {}), Mapping) else {},
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "passed": self.passed,
            "score": self.score,
            "max_score": self.max_score,
            "detail": self.detail,
            "evidence_refs": list(self.evidence_refs),
            "details": dict(self.details),
        }

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, EvaluationHistoryEventType):
            raise TypeError("event_type must be an EvaluationHistoryEventType")
        if not isinstance(self.timestamp, str) or not self.timestamp:
            raise TypeError("timestamp must be a non-empty string")
        if not isinstance(self.status, EvaluationResultStatus):
            raise TypeError("status must be an EvaluationResultStatus")
        if self.passed is not None and not isinstance(self.passed, bool):
            raise TypeError("passed must be a bool or None")
        if self.score is not None and (isinstance(self.score, bool) or not isinstance(self.score, (int, float))):
            raise TypeError("score must be numeric or None")
        if self.max_score is not None and (isinstance(self.max_score, bool) or not isinstance(self.max_score, int)):
            raise TypeError("max_score must be an int or None")
        if self.detail is not None and not isinstance(self.detail, str):
            raise TypeError("detail must be a string or None")
        if any(not isinstance(ref, str) for ref in self.evidence_refs):
            raise TypeError("evidence_refs must contain only strings")
        if not isinstance(self.details, dict):
            raise TypeError("details must be a dict")
        if self.status in {
            EvaluationResultStatus.PENDING,
            EvaluationResultStatus.RUNNING,
            EvaluationResultStatus.FAILED,
        }:
            if self.passed is not None or self.score is not None or self.max_score is not None:
                raise ValueError("pending/running/failed evaluation history events may not report result values")
        if self.status == EvaluationResultStatus.READY and self.passed is None and self.score is None:
            raise ValueError("ready evaluation history events must report passed or score")
        if self.max_score is not None and self.score is None:
            raise ValueError("evaluation history events may not report max_score without score")


@dataclass(frozen=True)
class EvaluationExecutionState:
    """Internal normalized execution state for one evaluator-observable resource."""

    state_schema_version: str = EVALUATION_STATE_SCHEMA_VERSION
    resource_type: str = ""
    run_id: str = ""
    status: EvaluationResultStatus = EvaluationResultStatus.PENDING
    observed_at: str = ""
    updated_at: str = ""
    passed: bool | None = None
    score: float | int | None = None
    max_score: int | None = None
    detail: str | None = None
    evidence_refs: tuple[str, ...] = ()

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> EvaluationExecutionState:
        if not isinstance(payload, Mapping):
            raise TypeError("evaluation result payload must be a mapping")
        missing_keys = [
            key
            for key in (
                "state_schema_version",
                "resource_type",
                "run_id",
                "status",
                "observed_at",
                "updated_at",
            )
            if key not in payload
        ]
        if missing_keys:
            raise ValueError("evaluation result payload is missing required fields: " + ", ".join(missing_keys))
        score_raw = payload.get("score")
        max_score_raw = payload.get("max_score")
        evidence_refs_raw = payload.get("evidence_refs", ())
        if isinstance(evidence_refs_raw, (str, bytes)) or not isinstance(evidence_refs_raw, Iterable):
            raise TypeError("evaluation result evidence_refs must be an iterable of strings")
        evidence_ref_items = list(evidence_refs_raw)
        evidence_refs = tuple(str(ref) for ref in evidence_ref_items if isinstance(ref, str))
        if len(evidence_refs) != len(evidence_ref_items):
            raise TypeError("evaluation result evidence_refs must contain only strings")
        return cls(
            state_schema_version=str(payload["state_schema_version"]),
            resource_type=str(payload["resource_type"]),
            run_id=str(payload["run_id"]),
            status=(
                payload["status"]
                if isinstance(payload["status"], EvaluationResultStatus)
                else EvaluationResultStatus(str(payload["status"]))
            ),
            observed_at=str(payload["observed_at"]),
            updated_at=str(payload["updated_at"]),
            passed=(payload.get("passed") if isinstance(payload.get("passed"), bool) else None),
            score=(score_raw if isinstance(score_raw, (int, float)) and not isinstance(score_raw, bool) else None),
            max_score=(
                max_score_raw if isinstance(max_score_raw, int) and not isinstance(max_score_raw, bool) else None
            ),
            detail=(str(payload["detail"]) if payload.get("detail") is not None else None),
            evidence_refs=evidence_refs,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "state_schema_version": self.state_schema_version,
            "resource_type": self.resource_type,
            "run_id": self.run_id,
            "status": self.status.value,
            "observed_at": self.observed_at,
            "updated_at": self.updated_at,
            "passed": self.passed,
            "score": self.score,
            "max_score": self.max_score,
            "detail": self.detail,
            "evidence_refs": list(self.evidence_refs),
        }

    def __post_init__(self) -> None:
        if not isinstance(self.state_schema_version, str) or not self.state_schema_version:
            raise TypeError("evaluation result state_schema_version must be a non-empty string")
        if not isinstance(self.resource_type, str) or not self.resource_type:
            raise TypeError("evaluation result resource_type must be a non-empty string")
        if not isinstance(self.run_id, str) or not self.run_id:
            raise TypeError("evaluation result run_id must be a non-empty string")
        if not isinstance(self.status, EvaluationResultStatus):
            raise TypeError("status must be an EvaluationResultStatus")
        if not isinstance(self.observed_at, str) or not self.observed_at:
            raise TypeError("observed_at must be a non-empty string")
        if not isinstance(self.updated_at, str) or not self.updated_at:
            raise TypeError("updated_at must be a non-empty string")
        if self.passed is not None and not isinstance(self.passed, bool):
            raise TypeError("passed must be a bool or None")
        if self.score is not None and (isinstance(self.score, bool) or not isinstance(self.score, (int, float))):
            raise TypeError("score must be numeric or None")
        if self.max_score is not None and (isinstance(self.max_score, bool) or not isinstance(self.max_score, int)):
            raise TypeError("max_score must be an int or None")
        if self.detail is not None and not isinstance(self.detail, str):
            raise TypeError("detail must be a string or None")
        if any(not isinstance(ref, str) for ref in self.evidence_refs):
            raise TypeError("evidence_refs must contain only strings")
        if self.status in {
            EvaluationResultStatus.PENDING,
            EvaluationResultStatus.RUNNING,
            EvaluationResultStatus.FAILED,
        }:
            if self.passed is not None or self.score is not None or self.max_score is not None:
                raise ValueError("pending/running/failed evaluation results may not report result values")
        if self.status == EvaluationResultStatus.READY and self.passed is None and self.score is None:
            raise ValueError("ready evaluation results must report passed or score")
        if self.max_score is not None and self.score is None:
            raise ValueError("evaluation results may not report max_score without score")
        if self.score is not None and self.max_score is not None and float(self.score) > float(self.max_score):
            raise ValueError("evaluation result score may not exceed max_score")


def validate_evaluation_result(
    contract: EvaluationResultContract,
    state: EvaluationExecutionState,
) -> list[str]:
    """Return contract violations for one evaluator result envelope."""

    violations: list[str] = []
    if state.resource_type != contract.resource_type:
        violations.append(
            f"Result resource_type {state.resource_type!r} does not match compiled contract {contract.resource_type!r}."
        )
    if state.state_schema_version != contract.state_schema_version:
        violations.append(
            "Result state_schema_version "
            f"{state.state_schema_version!r} does not match compiled contract "
            f"{contract.state_schema_version!r}."
        )
    if not contract.supports_passed and state.passed is not None:
        violations.append("Result may not report 'passed' for this resource type.")
    if contract.supports_passed and state.status == EvaluationResultStatus.READY and state.passed is None:
        violations.append("Ready result must report 'passed' for this resource type.")
    if not contract.supports_score and (state.score is not None or state.max_score is not None):
        violations.append("Result may not report score fields for this resource type.")
    if contract.supports_score and state.status == EvaluationResultStatus.READY and state.score is None:
        violations.append("Ready result must report 'score' for this resource type.")
    if contract.fixed_max_score is not None:
        if state.status == EvaluationResultStatus.READY and state.max_score != contract.fixed_max_score:
            violations.append(f"Ready result must report max_score {contract.fixed_max_score} for this resource type.")
    return violations


__all__ = (
    "EvaluationExecutionContract",
    "EvaluationExecutionState",
    "EvaluationHistoryEvent",
    "EvaluationHistoryEventType",
    "EvaluationResultContract",
    "EvaluationResultStatus",
    "validate_evaluation_result",
)
