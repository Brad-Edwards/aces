"""Experiment archival-datetime validators and study-vs-runs analysis validators."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .base import (
    _canonical_digest,
    _payload_get,
    _validate_artifact_collection_created_at,
    _validate_rfc3339_payload_field,
)
from .experiment_apparatus import (
    ExperimentApparatusComponentModel,
    ExperimentApparatusContextModel,
    ExperimentTaskModel,
)
from .experiment_artifacts import (
    _format_reference,
    _identity_matches_reference,
    _reference_satisfies_requirement,
)
from .experiment_references import (
    ExperimentParameterModel,
    ExperimentReferenceModel,
    ExperimentTaskReferenceModel,
)
from .experiment_run import ExperimentRunModel, validate_experiment_run_against_task
from .experiment_spec import ExperimentStudyModel
from .experiment_study import ExperimentConditionAssignmentModel, ExperimentStudyMembershipModel
from .participant_manifests import ParticipantImplementationSelectionModel


def validate_experiment_task_archival_datetimes(task: ExperimentTaskModel | Mapping[str, Any]) -> None:
    """Validate task-level archival timestamp semantics not carried by generic JSON Schema."""

    _validate_artifact_collection_created_at("artifact_refs", _payload_get(task, "artifact_refs"))


def validate_experiment_apparatus_context_archival_datetimes(
    apparatus_context: ExperimentApparatusContextModel | Mapping[str, Any],
) -> None:
    """Validate apparatus-context archival timestamp semantics not carried by generic JSON Schema."""

    _validate_rfc3339_payload_field(apparatus_context, "declared_at")
    _validate_artifact_collection_created_at(
        "observed_setup_evidence",
        _payload_get(apparatus_context, "observed_setup_evidence"),
    )


def validate_experiment_run_archival_datetimes(run: ExperimentRunModel | Mapping[str, Any]) -> None:
    """Validate run-level archival timestamp semantics not carried by generic JSON Schema."""

    _validate_rfc3339_payload_field(run, "started_at")
    _validate_rfc3339_payload_field(run, "ended_at")
    invalidation = _payload_get(run, "invalidation")
    if invalidation is not None:
        _validate_rfc3339_payload_field(invalidation, "invalidated_at")
    _validate_artifact_collection_created_at("evidence_artifacts", _payload_get(run, "evidence_artifacts"))


def validate_experiment_study_archival_datetimes(study: ExperimentStudyModel | Mapping[str, Any]) -> None:
    """Validate study-level archival timestamp semantics not carried by generic JSON Schema."""

    _validate_artifact_collection_created_at("report_artifacts", _payload_get(study, "report_artifacts"))
    _validate_artifact_collection_created_at("export_artifacts", _payload_get(study, "export_artifacts"))


def _task_reference_key(reference: ExperimentTaskReferenceModel) -> tuple[str, str | None]:
    return (reference.ref_id, reference.ref_version)


def _task_model_key(task: ExperimentTaskModel) -> tuple[str, str]:
    return (task.task_id, task.task_version)


def _run_model_key(run: ExperimentRunModel) -> tuple[str, str | None]:
    return (run.run_id, run.run_version)


def _task_ref_matches_task(reference: ExperimentReferenceModel, task: ExperimentTaskModel) -> bool:
    if reference.ref_digest is not None or reference.ref_path is not None:
        return False
    return (
        reference.ref_kind == "task"
        and reference.ref_id == task.task_id
        and (reference.ref_version is None or reference.ref_version == task.task_version)
    )


def _run_ref_matches_run(reference: ExperimentReferenceModel, run: ExperimentRunModel) -> bool:
    if reference.ref_digest is not None or reference.ref_path is not None:
        return False
    return (
        reference.ref_kind == "run"
        and reference.ref_id == run.run_id
        and (reference.ref_version is None or reference.ref_version == run.run_version)
    )


def _component_identity_matches_reference(
    component: ExperimentApparatusComponentModel,
    reference: ExperimentReferenceModel,
) -> bool:
    return component.component_kind == reference.ref_kind and _identity_matches_reference(component.identity, reference)


def _participant_selection_matches_reference(
    selection: ParticipantImplementationSelectionModel,
    reference: ExperimentReferenceModel,
) -> bool:
    return reference.ref_kind == "participant-implementation" and _identity_matches_reference(
        selection.implementation_identity,
        reference,
    )


def _reference_in_collection(
    references: list[ExperimentReferenceModel],
    requirement: ExperimentReferenceModel,
) -> bool:
    return any(_reference_satisfies_requirement(reference, requirement) for reference in references)


def _run_satisfies_condition_reference(run: ExperimentRunModel, requirement: ExperimentReferenceModel) -> bool:
    apparatus_context = run.apparatus_context
    if requirement.ref_kind in {"processor", "backend"}:
        return any(
            _component_identity_matches_reference(component, requirement)
            for component in apparatus_context.components.values()
        )
    if requirement.ref_kind == "participant-implementation":
        provenance = run.participant_implementation_provenance
        if provenance is None:
            return False
        return any(
            _participant_selection_matches_reference(selection, requirement)
            for selection in provenance.participant_implementations
        )
    if requirement.ref_kind == "task":
        return _reference_satisfies_requirement(run.task_ref, requirement)
    if requirement.ref_kind == "scenario-snapshot":
        return _reference_satisfies_requirement(run.scenario_snapshot_ref, requirement)
    if requirement.ref_kind == "apparatus-context":
        apparatus_context_ref = ExperimentReferenceModel(
            ref_kind="apparatus-context",
            ref_id=apparatus_context.apparatus_context_id,
            ref_version=apparatus_context.context_version,
        )
        return _reference_satisfies_requirement(apparatus_context_ref, requirement)
    if requirement.ref_kind == "manifest":
        return any(
            _reference_satisfies_requirement(selected_manifest, requirement)
            for selected_manifest in apparatus_context.selected_manifests
        )
    if requirement.ref_kind in {"profile", "capability"}:
        component_refs = [
            reference
            for component in apparatus_context.components.values()
            for reference in component.compatibility_refs
        ]
        return _reference_in_collection(
            apparatus_context.compatibility_declarations, requirement
        ) or _reference_in_collection(
            component_refs,
            requirement,
        )
    if requirement.ref_kind == "measurement-channel":
        return _reference_in_collection(apparatus_context.measurement_channels, requirement)
    if requirement.ref_kind == "evidence":
        return any(
            artifact.artifact_id == requirement.ref_id
            or any(
                _reference_satisfies_requirement(satisfied_ref, requirement)
                for satisfied_ref in artifact.satisfies_refs
            )
            for artifact in run.evidence_artifacts
        )
    return (
        _reference_in_collection(run.used_refs, requirement)
        or _reference_in_collection(run.generated_refs, requirement)
        or _reference_in_collection(run.derived_from_refs, requirement)
    )


def _parameter_satisfies_requirement(
    parameter: ExperimentParameterModel,
    requirement: ExperimentParameterModel,
) -> bool:
    return (
        parameter.name == requirement.name
        and parameter.value_kind == requirement.value_kind
        and parameter.value == requirement.value
    )


def _condition_assignment_run_criteria_signature(
    assignment: ExperimentConditionAssignmentModel,
) -> tuple[
    tuple[tuple[str, str, str | None, str | None, str | None], ...],
    tuple[tuple[str, str, str, str], ...],
]:
    reference_signature = tuple(
        sorted(
            (
                reference.ref_kind,
                reference.ref_id,
                reference.ref_version,
                _canonical_digest(reference.ref_digest),
                reference.ref_path,
            )
            for reference in assignment.required_refs
        )
    )
    parameter_signature = tuple(
        sorted(
            (
                parameter.name,
                parameter.value_kind,
                type(parameter.value).__name__,
                json.dumps(parameter.value, sort_keys=True, separators=(",", ":")),
            )
            for parameter in assignment.required_parameters
        )
    )
    return reference_signature, parameter_signature


def _run_satisfies_condition_assignment(
    run: ExperimentRunModel,
    assignment: ExperimentConditionAssignmentModel,
) -> list[str]:
    missing: list[str] = []
    missing.extend(
        _format_reference(reference)
        for reference in assignment.required_refs
        if not _run_satisfies_condition_reference(run, reference)
    )
    run_parameters = [*run.parameter_set, *run.apparatus_context.configuration_parameters]
    missing.extend(
        f"parameter:{parameter.name}:{parameter.value_kind}"
        for parameter in assignment.required_parameters
        if not any(_parameter_satisfies_requirement(candidate, parameter) for candidate in run_parameters)
    )
    return missing


def _run_is_eligible_for_study_analysis(run: ExperimentRunModel) -> bool:
    return run.run_status not in {"invalidated", "superseded"} and run.outcome_status != "not-evaluated"


def _validate_study_analysis_run_eligibility(
    study: ExperimentStudyModel,
    runs: list[ExperimentRunModel],
    evaluation_run_members: list[ExperimentStudyMembershipModel],
) -> None:
    if study.analysis_plan is None:
        return

    if not evaluation_run_members:
        raise ValueError("study analysis_plan requires at least one included evaluation-run membership")

    ambiguous_run_refs: list[str] = []
    ineligible_run_refs: list[str] = []
    for member in evaluation_run_members:
        reference_label = _format_reference(member.target_ref)
        matching_runs = [run for run in runs if _run_ref_matches_run(member.target_ref, run)]
        if len(matching_runs) > 1:
            ambiguous_run_refs.append(reference_label)
            continue
        for run in matching_runs:
            if not _run_is_eligible_for_study_analysis(run):
                ineligible_run_refs.append(f"{run.run_id}:{run.run_status}:{run.outcome_status}")

    if ambiguous_run_refs:
        joined = ", ".join(sorted(ambiguous_run_refs))
        raise ValueError(
            f"study evaluation-run memberships used for analysis must resolve to one supplied run artifact: {joined}"
        )
    if ineligible_run_refs:
        joined = ", ".join(sorted(ineligible_run_refs))
        raise ValueError(
            "study evaluation-run members used for analysis must not be invalidated, superseded, or not-evaluated: "
            f"{joined}"
        )


def _validate_study_run_allocation_coverage(
    study: ExperimentStudyModel,
    runs: list[ExperimentRunModel],
    evaluation_run_members: list[ExperimentStudyMembershipModel],
) -> None:
    allocation = study.run_allocation
    if allocation is None:
        return

    if not evaluation_run_members:
        raise ValueError("study run_allocation requires at least one included evaluation-run membership")

    condition_set = set(allocation.compared_conditions)
    grouped_run_keys: dict[str, set[tuple[str, str | None]]] = {
        condition: set() for condition in allocation.compared_conditions
    }
    condition_by_run_key: dict[tuple[str, str | None], str] = {}
    ungrouped_run_refs: list[str] = []
    unknown_groupings: list[str] = []
    ambiguous_run_refs: list[str] = []
    duplicate_run_assignments: list[str] = []
    ineligible_run_refs: list[str] = []
    unsatisfied_condition_runs: list[str] = []
    ambiguous_condition_runs: list[str] = []

    for member in evaluation_run_members:
        reference_label = _format_reference(member.target_ref)
        if member.grouping is None:
            ungrouped_run_refs.append(reference_label)
            continue
        if member.grouping not in condition_set:
            unknown_groupings.append(f"{reference_label}:{member.grouping}")
            continue

        matching_runs = [run for run in runs if _run_ref_matches_run(member.target_ref, run)]
        if len(matching_runs) > 1:
            ambiguous_run_refs.append(reference_label)
            continue
        for run in matching_runs:
            run_key = _run_model_key(run)
            prior_condition = condition_by_run_key.get(run_key)
            if prior_condition is not None:
                duplicate_run_assignments.append(f"{run.run_id}:{prior_condition},{member.grouping}")
                continue
            if not _run_is_eligible_for_study_analysis(run):
                ineligible_run_refs.append(f"{run.run_id}:{run.run_status}:{run.outcome_status}")
                continue
            assignment = allocation.condition_assignments[member.grouping]
            missing_condition_inputs = _run_satisfies_condition_assignment(run, assignment)
            if missing_condition_inputs:
                joined_missing_inputs = "|".join(sorted(missing_condition_inputs))
                unsatisfied_condition_runs.append(f"{run.run_id}:{member.grouping}:{joined_missing_inputs}")
                continue
            satisfied_other_conditions = sorted(
                condition_id
                for condition_id, candidate_assignment in allocation.condition_assignments.items()
                if condition_id != member.grouping
                and not _run_satisfies_condition_assignment(run, candidate_assignment)
            )
            if satisfied_other_conditions:
                joined_other_conditions = "|".join(satisfied_other_conditions)
                ambiguous_condition_runs.append(f"{run.run_id}:{member.grouping}:{joined_other_conditions}")
                continue
            condition_by_run_key[run_key] = member.grouping
            grouped_run_keys[member.grouping].add(run_key)

    if ungrouped_run_refs:
        joined = ", ".join(sorted(ungrouped_run_refs))
        raise ValueError(f"study run_allocation requires evaluation-run membership groupings: {joined}")
    if unknown_groupings:
        joined = ", ".join(sorted(unknown_groupings))
        raise ValueError(f"study evaluation-run groupings must be declared in compared_conditions: {joined}")
    if ambiguous_run_refs:
        joined = ", ".join(sorted(ambiguous_run_refs))
        raise ValueError(
            f"study evaluation-run membership references must resolve to one supplied run artifact: {joined}"
        )
    if duplicate_run_assignments:
        joined = ", ".join(sorted(duplicate_run_assignments))
        raise ValueError(f"study evaluation-run members must not assign the same run to multiple conditions: {joined}")
    if ineligible_run_refs:
        joined = ", ".join(sorted(ineligible_run_refs))
        raise ValueError(
            "study evaluation-run members used for analysis must not be invalidated, superseded, or not-evaluated: "
            f"{joined}"
        )
    if unsatisfied_condition_runs:
        joined = ", ".join(sorted(unsatisfied_condition_runs))
        raise ValueError(f"study evaluation-run members must satisfy their condition assignments: {joined}")
    if ambiguous_condition_runs:
        joined = ", ".join(sorted(ambiguous_condition_runs))
        raise ValueError(f"study evaluation-run members must satisfy exactly one condition assignment: {joined}")

    under_target_conditions = sorted(
        f"{condition}:{len(run_keys)}/{allocation.target_runs_per_condition}"
        for condition, run_keys in grouped_run_keys.items()
        if len(run_keys) < allocation.target_runs_per_condition
    )
    if under_target_conditions:
        joined = ", ".join(under_target_conditions)
        raise ValueError(
            f"study run_allocation target_runs_per_condition must be satisfied by included evaluation runs: {joined}"
        )


def validate_experiment_study_against_tasks_and_runs(
    study: ExperimentStudyModel,
    tasks: list[ExperimentTaskModel],
    runs: list[ExperimentRunModel] | None = None,
) -> None:
    """Validate study-level analysis semantics against concrete task/run artifacts."""

    runs = runs or []
    task_refs = [
        member.target_ref for member in study.membership.values() if member.role in {"primary-task", "comparison-task"}
    ]
    matched_tasks = [task for task in tasks if any(_task_ref_matches_task(reference, task) for reference in task_refs)]
    missing_task_refs = sorted(
        _format_reference(reference)
        for reference in task_refs
        if not any(_task_ref_matches_task(reference, task) for task in tasks)
    )
    if missing_task_refs:
        joined = ", ".join(missing_task_refs)
        raise ValueError(f"study task membership references must resolve to supplied task artifacts: {joined}")

    run_refs = [
        member.target_ref
        for member in study.membership.values()
        if member.role in {"calibration-run", "evaluation-run"}
    ]
    evaluation_run_members = [member for member in study.membership.values() if member.role == "evaluation-run"]
    evaluation_run_refs = [member.target_ref for member in evaluation_run_members]
    matched_runs = [run for run in runs if any(_run_ref_matches_run(reference, run) for reference in run_refs)]
    matched_evaluation_runs = [
        run for run in runs if any(_run_ref_matches_run(reference, run) for reference in evaluation_run_refs)
    ]
    missing_run_refs = sorted(
        _format_reference(reference)
        for reference in run_refs
        if not any(_run_ref_matches_run(reference, run) for run in runs)
    )
    if run_refs and missing_run_refs:
        joined = ", ".join(missing_run_refs)
        raise ValueError(f"study run membership references must resolve to supplied run artifacts: {joined}")

    _validate_study_analysis_run_eligibility(study, runs, evaluation_run_members)
    _validate_study_run_allocation_coverage(study, runs, evaluation_run_members)

    task_by_key = {_task_model_key(task): task for task in matched_tasks}
    for run in matched_runs:
        task = task_by_key.get(_task_reference_key(run.task_ref))
        if task is None:
            raise ValueError("study run members must reference a supplied study task artifact")
        validate_experiment_run_against_task(task, run)

    if study.analysis_plan is None:
        return
    declared_metric_ids = {
        metric_id for task in matched_tasks for metric_id in task.evaluation_protocol.metric_definitions
    }
    if not declared_metric_ids:
        raise ValueError("study analysis_plan metrics require supplied task protocol artifacts")
    ungrounded_metrics = sorted(
        metric_id for metric_id in study.analysis_plan.metrics if metric_id not in declared_metric_ids
    )
    if ungrounded_metrics:
        joined = ", ".join(ungrounded_metrics)
        raise ValueError(f"study analysis_plan metrics must be declared by included task protocols: {joined}")
    missing_run_metrics = sorted(
        f"{run.run_id}:{metric_id}"
        for run in matched_evaluation_runs
        for metric_id in study.analysis_plan.metrics
        if metric_id not in {result.metric_id for result in run.result_summaries.values()}
    )
    if missing_run_metrics:
        joined = ", ".join(missing_run_metrics)
        raise ValueError(
            "study analysis_plan metrics must have result_summaries, including explicit missing/withheld "
            f"statuses, in included evaluation runs: {joined}"
        )
