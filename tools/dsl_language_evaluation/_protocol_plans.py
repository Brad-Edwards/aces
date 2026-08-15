"""Measure, threshold, sampling, and execution-plan validation for the protocol."""

from __future__ import annotations

from collections.abc import Mapping

from tools.dsl_language_evaluation._keys import (
    _ETHICS_KEYS,
    _EXECUTION_PLAN_KEYS,
    _MAX_CATALOG_ITEMS,
    _MEASURE_KEYS,
    _SAMPLING_KEYS,
    _STAGE_APPLICABILITY_KEYS,
    _SUBJECT_TASK_REQUIREMENT_KEYS,
    _THRESHOLD_CONDITION_KEYS,
    _THRESHOLD_KEYS,
    REQUIRED_TASK_KINDS,
)
from tools.dsl_language_evaluation._shape import (
    _bounded_list,
    _exact_keys,
    _failure,
    _protocol_records_by_id,
    _record_ids,
    _string_list,
)
from tools.policy.common import PolicyFailure


def _preregistration_failures(protocol: dict[str, object], failures: list[PolicyFailure], path: str) -> None:
    _exact_keys(
        protocol["ethics_and_privacy"],
        _ETHICS_KEYS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="ethics_and_privacy",
        path=path,
    )
    if not protocol["validity_threats"] or not protocol["analysis_plan"]:
        failures.append(
            _failure(
                "dsl-evaluation-preregistration",
                "validity threats and the analysis plan must be preregistered",
                path,
            )
        )
    if not isinstance(protocol["amendment_log"], list):
        failures.append(_failure("dsl-evaluation-protocol-shape", "amendment_log must be a list", path))


def _plan_failures(
    protocol: dict[str, object],
    catalogs_ids: Mapping[str, set[str]],
    personas: list[object],
    tasks: list[object],
    measures: list[object],
    thresholds: list[object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    dimension_ids = catalogs_ids["dimension_ids"]
    persona_ids = catalogs_ids["persona_ids"]
    task_ids = catalogs_ids["task_ids"]
    measure_ids = catalogs_ids["measure_ids"]
    tasks_by_id = _protocol_records_by_id(protocol, "tasks", "task_id")
    for index, measure in enumerate(measures):
        if not _exact_keys(
            measure,
            _MEASURE_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"measures[{index}]",
            path=path,
        ):
            continue
        measure_dimensions = _string_list(measure["dimension_ids"], non_empty=True)
        if measure_dimensions is None or not set(measure_dimensions).issubset(dimension_ids):
            failures.append(
                _failure(
                    "dsl-evaluation-measure-join",
                    f"{measure['measure_id']}: invalid dimension ids",
                    path,
                )
            )
        measure_tasks = _string_list(measure["task_ids"], non_empty=True)
        if measure_tasks is None or not set(measure_tasks).issubset(task_ids):
            failures.append(
                _failure(
                    "dsl-evaluation-measure-join",
                    f"{measure['measure_id']}: invalid task ids",
                    path,
                )
            )
        elif not all(
            set(measure_dimensions or []) & set(task["dimension_ids"])
            for task in tasks
            if isinstance(task, Mapping)
            and task.get("task_id") in measure_tasks
            and _string_list(task.get("dimension_ids"), non_empty=True) is not None
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-measure-join",
                    f"{measure['measure_id']}: task applicability must share a measured dimension",
                    path,
                )
            )
        applicability = _bounded_list(
            measure["stage_applicability"],
            _MAX_CATALOG_ITEMS,
            failures,
            rule_id="dsl-evaluation-measure-stage-applicability",
            label=f"measures[{index}].stage_applicability",
            path=path,
        )
        actual_stage_pairs: set[tuple[str, str]] = set()
        duplicate_stage_pairs: set[tuple[str, str]] = set()
        for applicability_index, declaration in enumerate(applicability):
            if not _exact_keys(
                declaration,
                _STAGE_APPLICABILITY_KEYS,
                failures,
                rule_id="dsl-evaluation-measure-stage-applicability",
                label=(f"measures[{index}].stage_applicability[{applicability_index}]"),
                path=path,
            ):
                continue
            task_id = declaration["task_id"]
            task = tasks_by_id.get(task_id) if isinstance(task_id, str) else None
            declaration_variants = _string_list(declaration["variant_ids"], non_empty=True)
            declaration_stages = _string_list(declaration["artifact_stage_ids"], non_empty=True)
            task_variants = (
                set(_string_list(task.get("variant_ids"), non_empty=True) or []) if task is not None else set()
            )
            task_stages = (
                set(_string_list(task.get("artifact_stage_ids"), non_empty=True) or []) if task is not None else set()
            )
            if (
                task is None
                or measure_tasks is None
                or task_id not in measure_tasks
                or declaration_variants is None
                or not set(declaration_variants).issubset(task_variants)
                or declaration_stages is None
                or not set(declaration_stages).issubset(task_stages)
            ):
                failures.append(
                    _failure(
                        "dsl-evaluation-measure-stage-applicability",
                        f"{measure['measure_id']}: invalid task, variant, or stage applicability",
                        path,
                    )
                )
                continue
            for variant_id in declaration_variants:
                pair = (task_id, variant_id)
                if pair in actual_stage_pairs:
                    duplicate_stage_pairs.add(pair)
                actual_stage_pairs.add(pair)
        expected_stage_pairs = {
            (task_id, variant_id)
            for task_id in (measure_tasks or [])
            for variant_id in (_string_list(tasks_by_id.get(task_id, {}).get("variant_ids"), non_empty=True) or [])
        }
        if actual_stage_pairs != expected_stage_pairs or duplicate_stage_pairs:
            failures.append(
                _failure(
                    "dsl-evaluation-measure-stage-coverage",
                    f"{measure['measure_id']}: every task/variant requires one stage declaration",
                    path,
                )
            )
    threshold_ids = _record_ids(
        thresholds,
        "dimension_id",
        failures,
        rule_id="dsl-evaluation-threshold-id",
        label="threshold",
        path=path,
    )
    for index, threshold in enumerate(thresholds):
        if not _exact_keys(
            threshold,
            _THRESHOLD_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"thresholds[{index}]",
            path=path,
        ):
            continue
        conditions = _bounded_list(
            threshold["conditions"],
            16,
            failures,
            rule_id="dsl-evaluation-threshold-shape",
            label=f"thresholds[{index}].conditions",
            path=path,
        )
        if threshold["logic"] != "all" or not conditions:
            failures.append(
                _failure(
                    "dsl-evaluation-threshold-shape",
                    f"{threshold['dimension_id']}: threshold requires non-empty all conditions",
                    path,
                )
            )
        for condition_index, condition in enumerate(conditions):
            if not _exact_keys(
                condition,
                _THRESHOLD_CONDITION_KEYS,
                failures,
                rule_id="dsl-evaluation-threshold-shape",
                label=f"thresholds[{index}].conditions[{condition_index}]",
                path=path,
            ):
                continue
            if (
                not isinstance(condition["measure_id"], str)
                or condition["measure_id"] not in measure_ids
                or not isinstance(condition["operator"], str)
                or condition["operator"] not in {">=", "<=", "=="}
                or isinstance(condition["target"], bool)
                or not isinstance(condition["target"], (int, float))
            ):
                failures.append(
                    _failure(
                        "dsl-evaluation-threshold-join",
                        f"{threshold['dimension_id']}: invalid measure, operator, or target",
                        path,
                    )
                )
    if threshold_ids != dimension_ids:
        failures.append(
            _failure(
                "dsl-evaluation-threshold-coverage",
                "every dimension requires exactly one preregistered threshold",
                path,
            )
        )

    if _exact_keys(
        protocol["sampling_plan"],
        _SAMPLING_KEYS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="sampling_plan",
        path=path,
    ):
        sampling = protocol["sampling_plan"]
        minimum = sampling["minimum_per_persona"]
        target = sampling["target_total"]
        if not isinstance(minimum, int) or minimum < 1 or not isinstance(target, int):
            failures.append(_failure("dsl-evaluation-sampling-plan", "invalid sample sizes", path))
        elif target < sum(
            item.get("minimum_completed_subjects", 0)
            for item in personas
            if isinstance(item, Mapping) and isinstance(item.get("minimum_completed_subjects"), int)
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-sampling-plan",
                    "target_total cannot cover the required per-persona minimum",
                    path,
                )
            )
    if _exact_keys(
        protocol["execution_plan"],
        _EXECUTION_PLAN_KEYS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="execution_plan",
        path=path,
    ):
        execution_plan = protocol["execution_plan"]
        requirements = _bounded_list(
            execution_plan["subject_task_requirements"],
            16,
            failures,
            rule_id="dsl-evaluation-subject-workload-plan",
            label="execution_plan.subject_task_requirements",
            path=path,
        )
        requirement_ids = _record_ids(
            requirements,
            "requirement_id",
            failures,
            rule_id="dsl-evaluation-subject-workload-plan",
            label="subject task requirement",
            path=path,
        )
        declared_kinds: set[str] = set()
        duplicate_kinds: set[str] = set()
        for index, requirement in enumerate(requirements):
            if not _exact_keys(
                requirement,
                _SUBJECT_TASK_REQUIREMENT_KEYS,
                failures,
                rule_id="dsl-evaluation-subject-workload-plan",
                label=f"execution_plan.subject_task_requirements[{index}]",
                path=path,
            ):
                continue
            task_kind_values = _string_list(requirement["task_kinds"], non_empty=True)
            minimum = requirement["minimum_assigned_attempts"]
            if (
                task_kind_values is None
                or not set(task_kind_values).issubset(REQUIRED_TASK_KINDS)
                or isinstance(minimum, bool)
                or not isinstance(minimum, int)
                or minimum < 1
            ):
                failures.append(
                    _failure(
                        "dsl-evaluation-subject-workload-plan",
                        f"{requirement['requirement_id']}: invalid task kinds or minimum",
                        path,
                    )
                )
                continue
            overlap = declared_kinds & set(task_kind_values)
            duplicate_kinds.update(overlap)
            declared_kinds.update(task_kind_values)
            for persona_id in persona_ids:
                if not any(
                    task.get("kind") in task_kind_values
                    and persona_id in (_string_list(task.get("persona_ids"), non_empty=True) or [])
                    for task in tasks_by_id.values()
                ):
                    failures.append(
                        _failure(
                            "dsl-evaluation-subject-workload-plan",
                            f"{requirement['requirement_id']}: no eligible task for {persona_id}",
                            path,
                        )
                    )
        if not requirement_ids or declared_kinds != REQUIRED_TASK_KINDS or duplicate_kinds:
            failures.append(
                _failure(
                    "dsl-evaluation-subject-workload-plan",
                    "subject task requirements must partition every required task kind",
                    path,
                )
            )
