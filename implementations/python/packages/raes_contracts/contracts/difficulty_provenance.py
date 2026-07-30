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
    from .experiment_conditions import ExperimentConditionAssignmentModel
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
        self._validate_decision_order()
        self._validate_decision_ids()
        for decision in self.decisions:
            self._validate_decision_policy_identity(decision)
            self._validate_selected_decision(decision)
            self._validate_decision_observations(decision)
        self._validate_decision_history_chain()
        if len({decision.run_id for decision in self.decisions}) > 1:
            raise ValueError("difficulty decisions must belong to one run")

    def _validate_decision_order(self) -> None:
        coordinates = [decision.state_cut.coordinate for decision in self.decisions]
        if coordinates != sorted(set(coordinates)):
            raise ValueError("difficulty decisions must use strictly increasing state cuts")

    def _validate_decision_ids(self) -> None:
        decision_ids = [decision.decision_id for decision in self.decisions]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("difficulty decision ids must be unique")

    def _validate_decision_policy_identity(self, decision: DifficultyDecisionRecordModel) -> None:
        identity_matches = (
            decision.policy_id == self.policy.policy_id
            and decision.policy_version == self.policy.policy_version
            and decision.policy_digest == self.policy.policy_digest
            and decision.validity_effect == self.policy.validity_effect
        )
        if not identity_matches:
            raise ValueError("difficulty decisions must match the archived policy identity")

    def _validate_decision_observations(self, decision: DifficultyDecisionRecordModel) -> None:
        observations = {observation.source_id: observation for observation in decision.observation_refs}
        if set(observations) != set(self.policy.observation_sources):
            raise ValueError("difficulty decisions must archive every declared observation source")
        substituted_source = any(
            observation.source_ref != self.policy.observation_sources[source_id].source_ref
            for source_id, observation in observations.items()
        )
        if substituted_source:
            raise ValueError("difficulty decision observations must match the exact policy source definitions")
        stale_observation = any(
            decision.state_cut.coordinate - observation.observed_cut.coordinate
            > self.policy.observation_sources[source_id].maximum_age
            for source_id, observation in observations.items()
        )
        if stale_observation:
            raise ValueError("difficulty decision observations exceed the declared freshness bound")

    def _validate_decision_history_chain(self) -> None:
        prior_head: str | None = None
        for decision in self.decisions:
            if decision.prior_history_head != prior_head:
                raise ValueError("difficulty decisions must form one append-only history-head chain")
            prior_head = decision.history_head

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
        intervention_ids = [intervention.intervention_id for intervention in self.interventions]
        if len(intervention_ids) != len(set(intervention_ids)):
            raise ValueError("difficulty intervention ids must be unique")
        for intervention in self.interventions:
            self._validate_intervention(intervention, decisions)

    def _validate_intervention(
        self,
        intervention: DifficultyInterventionRecordModel,
        decisions: dict[str, DifficultyDecisionRecordModel],
    ) -> None:
        decision = decisions.get(intervention.decision_id)
        if decision is None or decision.selected_action_id != intervention.action_id:
            raise ValueError("difficulty interventions must resolve a selected decision action")
        action = self.policy.actions.get(intervention.action_id)
        if action is None or intervention.affected_refs != action.affected_refs:
            raise ValueError("difficulty interventions must match the declared policy action")
        if intervention.run_id != decision.run_id:
            raise ValueError("difficulty intervention run_id must match its decision")
        self._validate_follow_up_reference(intervention, action.action_kind)

    @staticmethod
    def _validate_follow_up_reference(
        intervention: DifficultyInterventionRecordModel,
        action_kind: str,
    ) -> None:
        if action_kind == "follow-up-trial":
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

    assignment = _difficulty_assignment(spec, condition_id)
    _validate_difficulty_task_ref(spec, run)
    provenance = run.difficulty_provenance
    if provenance is None:
        _validate_absent_difficulty_provenance(assignment)
        return
    if provenance.policy.condition != assignment.difficulty_condition:
        raise ValueError("run difficulty condition must match the assigned authoring condition")
    _validate_admitted_difficulty_policy(spec, provenance, assignment)
    _validate_difficulty_design_ref(spec, provenance)


def _difficulty_assignment(
    spec: ExperimentSpecModel,
    condition_id: str,
) -> ExperimentConditionAssignmentModel:
    allocation = spec.run_plan.allocation
    if allocation is None:
        raise ValueError("difficulty run admission requires condition-based authoring allocation")
    assignment = allocation.condition_assignments.get(condition_id)
    if assignment is None:
        raise ValueError("difficulty condition must resolve to the authoring allocation")
    return assignment


def _validate_difficulty_task_ref(spec: ExperimentSpecModel, run: ExperimentRunModel) -> None:
    task_matches = run.task_ref.ref_id == spec.task_ref.ref_id and run.task_ref.ref_version == spec.task_ref.ref_version
    if not task_matches:
        raise ValueError("difficulty run task reference must match the authoring design")


def _validate_absent_difficulty_provenance(assignment: ExperimentConditionAssignmentModel) -> None:
    if assignment.difficulty_condition != "fixed":
        raise ValueError("adaptive and scaffolded difficulty conditions require run provenance")


def _validate_admitted_difficulty_policy(
    spec: ExperimentSpecModel,
    provenance: DifficultyRunProvenanceModel,
    assignment: ExperimentConditionAssignmentModel,
) -> None:
    registry = spec.run_plan.difficulty_policy_registry
    if registry is None:
        raise ValueError("difficulty run provenance requires an authored policy registry")
    policy_id = assignment.difficulty_policy_id or registry.default_policy_id
    admitted_policy = registry.policies.get(policy_id)
    if admitted_policy is None or provenance.policy != admitted_policy:
        raise ValueError("run difficulty provenance must contain the exact admitted policy snapshot")


def _validate_difficulty_design_ref(
    spec: ExperimentSpecModel,
    provenance: DifficultyRunProvenanceModel,
) -> None:
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
