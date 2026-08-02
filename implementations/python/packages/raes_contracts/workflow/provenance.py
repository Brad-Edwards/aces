"""Portable provenance for governed workflow-step realization attempts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


def _validate_provenance_string_tuple(field_name: str, values: object) -> None:
    if not isinstance(values, tuple) or any(not isinstance(item, str) or not item for item in values):
        raise TypeError(f"{field_name} must be a tuple of non-empty strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} entries must be unique")


@dataclass(frozen=True)
class WorkflowStepAttemptProvenance:
    """Portable provenance for one governed workflow-step realization attempt."""

    step_name: str
    execution_mode: str
    attempt_id: str
    objective_address: str = ""
    procedure_ref: str = ""
    exposed_scaffold_refs: tuple[str, ...] = ()
    allowed_action_families: tuple[str, ...] = ()
    selected_action_family: str = ""
    selected_tool_ref: str = ""
    selected_affordance_ref: str = ""
    fact_versions: tuple[str, ...] = ()
    outcome: str = ""
    evidence_refs: tuple[str, ...] = ()
    assertion_truth_refs: tuple[str, ...] = ()
    participant_report: str = ""

    def __post_init__(self) -> None:
        for field_name in ("step_name", "execution_mode", "attempt_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.execution_mode not in {"scripted", "objective", "scaffolded"}:
            raise ValueError("execution_mode must be scripted, objective, or scaffolded")
        if self.outcome not in {"", "succeeded", "failed", "exhausted"}:
            raise ValueError("outcome must be a portable workflow step outcome")
        for field_name in (
            "exposed_scaffold_refs",
            "allowed_action_families",
            "fact_versions",
            "evidence_refs",
            "assertion_truth_refs",
        ):
            values = getattr(self, field_name)
            _validate_provenance_string_tuple(field_name, values)
        if self.outcome == "succeeded" and not (self.evidence_refs and self.assertion_truth_refs):
            raise ValueError("successful workflow step provenance requires evidence-bearing assertion truth")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> WorkflowStepAttemptProvenance:
        if not isinstance(payload, Mapping):
            raise TypeError("workflow step attempt provenance must be a mapping")
        return cls(
            step_name=str(payload.get("step_name", "")),
            execution_mode=str(payload.get("execution_mode", "")),
            attempt_id=str(payload.get("attempt_id", "")),
            objective_address=str(payload.get("objective_address", "")),
            procedure_ref=str(payload.get("procedure_ref", "")),
            exposed_scaffold_refs=tuple(payload.get("exposed_scaffold_refs", ())),
            allowed_action_families=tuple(payload.get("allowed_action_families", ())),
            selected_action_family=str(payload.get("selected_action_family", "")),
            selected_tool_ref=str(payload.get("selected_tool_ref", "")),
            selected_affordance_ref=str(payload.get("selected_affordance_ref", "")),
            fact_versions=tuple(payload.get("fact_versions", ())),
            outcome=str(payload.get("outcome", "")),
            evidence_refs=tuple(payload.get("evidence_refs", ())),
            assertion_truth_refs=tuple(payload.get("assertion_truth_refs", ())),
            participant_report=str(payload.get("participant_report", "")),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "step_name": self.step_name,
            "execution_mode": self.execution_mode,
            "attempt_id": self.attempt_id,
            "objective_address": self.objective_address,
            "procedure_ref": self.procedure_ref,
            "exposed_scaffold_refs": list(self.exposed_scaffold_refs),
            "allowed_action_families": list(self.allowed_action_families),
            "selected_action_family": self.selected_action_family,
            "selected_tool_ref": self.selected_tool_ref,
            "selected_affordance_ref": self.selected_affordance_ref,
            "fact_versions": list(self.fact_versions),
            "outcome": self.outcome,
            "evidence_refs": list(self.evidence_refs),
            "assertion_truth_refs": list(self.assertion_truth_refs),
            "participant_report": self.participant_report,
        }
