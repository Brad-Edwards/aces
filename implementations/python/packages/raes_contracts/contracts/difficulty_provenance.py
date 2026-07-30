"""Run-level adaptive-difficulty provenance and pure-resolution result."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field, model_validator

from ..canonical import canonical_json_digest
from ..diagnostics import DiagnosticModel
from .base import ContractModel, NonEmptyString
from .difficulty_adaptation import (
    DifficultyDecisionRecordModel,
    DifficultyInterventionRecordModel,
    DifficultyPolicyModel,
)
from .experiment_references import ExperimentReferenceModel

if TYPE_CHECKING:
    from .experiment_run import ExperimentRunModel
    from .experiment_spec import ExperimentSpecModel


class DifficultyRunProvenanceModel(ContractModel):
    """Run-level policy snapshot, decisions, intervention outcomes, and validity treatment."""

    design_ref: ExperimentReferenceModel
    policy: DifficultyPolicyModel
    baseline_variant_id: NonEmptyString
    decisions: list[DifficultyDecisionRecordModel] = Field(default_factory=list, max_length=1024)
    interventions: list[DifficultyInterventionRecordModel] = Field(default_factory=list, max_length=1024)
    comparison_disposition: Literal[
        "fixed-baseline",
        "adaptation-is-treatment",
        "scaffold-exposure-is-treatment",
        "descriptive-only",
    ]
    validity_disclosure: NonEmptyString

    @model_validator(mode="after")
    def _validate_provenance(self) -> DifficultyRunProvenanceModel:
        self._validate_design_ref()
        if self.baseline_variant_id != self.policy.baseline_variant_id:
            raise ValueError("difficulty provenance baseline_variant_id must match the policy baseline")
        if self.policy.condition == "fixed":
            if self.decisions or self.interventions:
                raise ValueError("fixed difficulty provenance must not contain decisions or interventions")
            if self.comparison_disposition != "fixed-baseline":
                raise ValueError("fixed difficulty provenance requires fixed-baseline comparison disposition")
            return self
        if self.comparison_disposition == "fixed-baseline":
            raise ValueError("adaptive difficulty provenance must disclose adaptation as treatment")
        expected_disposition = {
            "adaptive": "adaptation-is-treatment",
            "scaffolded": "scaffold-exposure-is-treatment",
        }[self.policy.condition]
        if self.comparison_disposition not in {expected_disposition, "descriptive-only"}:
            raise ValueError(f"{self.policy.condition} policy treatment disposition is inconsistent")
        self._validate_decisions()
        self._validate_interventions()
        return self

    def _validate_design_ref(self) -> None:
        if (
            self.design_ref.ref_kind != "authoring-input"
            or self.design_ref.ref_version is None
            or self.design_ref.ref_digest is None
            or self.design_ref.ref_path is not None
        ):
            raise ValueError("difficulty design_ref must be a versioned digest-bound authoring-input reference")

    def _validate_decisions(self) -> None:
        coordinates = [decision.state_cut.coordinate for decision in self.decisions]
        if coordinates != sorted(set(coordinates)):
            raise ValueError("difficulty decisions must use strictly increasing state cuts")
        run_ids: set[str] = set()
        decision_ids: set[str] = set()
        for decision in self.decisions:
            run_ids.add(decision.run_id)
            if decision.decision_id in decision_ids:
                raise ValueError("difficulty decision ids must be unique")
            decision_ids.add(decision.decision_id)
            if (
                decision.policy_id != self.policy.policy_id
                or decision.policy_version != self.policy.policy_version
                or decision.policy_digest != self.policy.policy_digest
                or decision.validity_effect != self.policy.validity_effect
            ):
                raise ValueError("difficulty decisions must match the archived policy identity")
            self._validate_selected_decision(decision)
            if decision.disposition != "unsupported":
                observations = {observation.source_id: observation for observation in decision.observation_refs}
                if set(observations) != set(self.policy.observation_sources):
                    raise ValueError("difficulty decisions must archive every declared observation source")
                for source_id, observation in observations.items():
                    maximum_age = self.policy.observation_sources[source_id].maximum_age
                    if decision.state_cut.coordinate - observation.observed_cut.coordinate > maximum_age:
                        raise ValueError("difficulty decision observations exceed the declared freshness bound")
        prior_head: str | None = None
        for decision in self.decisions:
            if decision.prior_history_head != prior_head:
                raise ValueError("difficulty decisions must form one append-only history-head chain")
            prior_head = decision.history_head
        if len(run_ids) > 1:
            raise ValueError("difficulty decisions must belong to one run")

    def _validate_selected_decision(self, decision: DifficultyDecisionRecordModel) -> None:
        if decision.disposition != "selected":
            return
        rule = self.policy.threshold_rules.get(decision.trigger_rule_id)
        if rule is None or rule.action_id != decision.selected_action_id:
            raise ValueError("selected difficulty decisions must resolve a declared policy rule and action")
        action = self.policy.actions.get(decision.selected_action_id)
        if action is None or decision.affected_refs != action.affected_refs:
            raise ValueError("selected difficulty decision affected refs must match the declared policy action")

    def _validate_interventions(self) -> None:
        decisions = {decision.decision_id: decision for decision in self.decisions}
        intervention_ids: set[str] = set()
        for intervention in self.interventions:
            if intervention.intervention_id in intervention_ids:
                raise ValueError("difficulty intervention ids must be unique")
            intervention_ids.add(intervention.intervention_id)
            decision = decisions.get(intervention.decision_id)
            if decision is None or decision.selected_action_id != intervention.action_id:
                raise ValueError("difficulty interventions must resolve a selected decision action")
            action = self.policy.actions.get(intervention.action_id)
            if action is None or intervention.affected_refs != action.affected_refs:
                raise ValueError("difficulty interventions must match the declared policy action")
            if intervention.run_id != decision.run_id:
                raise ValueError("difficulty intervention run_id must match its decision")
            if action.action_kind == "follow-up-trial":
                if intervention.follow_up_run_ref is None:
                    raise ValueError("follow-up-trial interventions require a follow_up_run_ref")
                if intervention.follow_up_run_ref.ref_id == intervention.run_id:
                    raise ValueError("adaptive follow-up run identity must differ from the source run")
            elif intervention.follow_up_run_ref is not None:
                raise ValueError("in-run difficulty interventions must not claim a follow-up run")


class DifficultyResolutionResultModel(ContractModel):
    """One pure resolver result."""

    decision: DifficultyDecisionRecordModel | None = None
    diagnostics: list[DiagnosticModel] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def _validate_result(self) -> DifficultyResolutionResultModel:
        if (self.decision is None) == (not self.diagnostics):
            raise ValueError("difficulty resolution must return exactly one decision or diagnostic set")
        return self


def validate_experiment_difficulty_against_spec(
    spec: ExperimentSpecModel,
    run: ExperimentRunModel,
    condition_id: str,
) -> None:
    """Admit a run only against its exact authored condition and policy snapshot."""

    allocation = spec.run_plan.allocation
    if allocation is None:
        raise ValueError("difficulty run admission requires condition-based authoring allocation")
    assignment = allocation.condition_assignments.get(condition_id)
    if assignment is None:
        raise ValueError("difficulty condition must resolve to the authoring allocation")
    if run.task_ref.ref_id != spec.task_ref.ref_id or run.task_ref.ref_version != spec.task_ref.ref_version:
        raise ValueError("difficulty run task reference must match the authoring design")

    provenance = run.difficulty_provenance
    if provenance is None:
        if assignment.difficulty_condition == "fixed":
            return
        raise ValueError("adaptive and scaffolded difficulty conditions require run provenance")
    if provenance.policy.condition != assignment.difficulty_condition:
        raise ValueError("run difficulty condition must match the assigned authoring condition")

    registry = spec.run_plan.difficulty_policy_registry
    if registry is None:
        raise ValueError("difficulty run provenance requires an authored policy registry")
    policy_id = assignment.difficulty_policy_id or registry.default_policy_id
    admitted_policy = registry.policies.get(policy_id)
    if admitted_policy is None or provenance.policy != admitted_policy:
        raise ValueError("run difficulty provenance must contain the exact admitted policy snapshot")

    design_ref = provenance.design_ref
    expected_design_digest = canonical_json_digest(spec.model_dump(mode="json"))
    if (
        design_ref.ref_id != spec.spec_id
        or design_ref.ref_version != spec.spec_version
        or design_ref.ref_digest != expected_design_digest
    ):
        raise ValueError("difficulty authoring design reference must match the exact admitted spec")


__all__ = [
    "DifficultyResolutionResultModel",
    "DifficultyRunProvenanceModel",
    "validate_experiment_difficulty_against_spec",
]
