"""Measure opportunity derivation and result recomputation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from statistics import median

from tools.dsl_language_evaluation._claims import _attempt_matches_scope
from tools.dsl_language_evaluation._keys import _STRATUM_ROLES
from tools.dsl_language_evaluation._shape import _protocol_records_by_id, _string_list


def _measure_stage_ids(
    measure: Mapping[str, object],
    task_id: str,
    variant_id: str,
) -> list[str]:
    """Return the single preregistered stage set for a task/variant/measure."""

    declarations = measure.get("stage_applicability", [])
    if not isinstance(declarations, list):
        raise ValueError(f"{measure.get('measure_id')}: stage applicability must be a list")
    matches: list[list[str]] = []
    for declaration in declarations:
        if not isinstance(declaration, Mapping) or declaration.get("task_id") != task_id:
            continue
        variant_ids = _string_list(declaration.get("variant_ids"), non_empty=True)
        stage_ids = _string_list(declaration.get("artifact_stage_ids"), non_empty=True)
        if variant_ids is not None and variant_id in variant_ids and stage_ids is not None:
            matches.append(stage_ids)
    if len(matches) != 1:
        raise ValueError(f"{measure.get('measure_id')}: expected one stage declaration for {task_id}/{variant_id}")
    return matches[0]


def _measure_opportunities(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    scope: Mapping[str, Sequence[str] | set[str]] | None = None,
) -> tuple[
    dict[str, Mapping[str, object]],
    list[tuple[Mapping[str, object], Mapping[str, object], str, bool]],
    dict[tuple[str, str, str], Mapping[str, object]],
]:
    """Derive every attempt-measure-stage opportunity and frozen observation."""

    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")
    scope_sets = {field: set(values) for field, values in scope.items()} if scope is not None else None
    if scope_sets is not None:
        measures = {
            measure_id: measure
            for measure_id, measure in measures.items()
            if measure_id in scope_sets.get("measure_ids", set())
        }
    attempts = snapshot.get("attempts", [])
    observations = snapshot.get("observations", [])
    withdrawals = snapshot.get("withdrawals", [])
    subjects = snapshot.get("subjects", [])
    subjects_by_id = {
        subject.get("subject_id"): subject
        for subject in subjects
        if isinstance(subject, Mapping) and isinstance(subject.get("subject_id"), str)
    }
    if not isinstance(attempts, list) or not isinstance(observations, list) or not isinstance(withdrawals, list):
        raise ValueError("snapshot execution records must be lists")

    withdrawn_subjects = {
        withdrawal["subject_id"]
        for withdrawal in withdrawals
        if isinstance(withdrawal, Mapping) and isinstance(withdrawal.get("subject_id"), str)
    }
    observation_by_opportunity: dict[tuple[str, str, str], Mapping[str, object]] = {}
    for observation in observations:
        if not isinstance(observation, Mapping):
            continue
        attempt_id = observation.get("attempt_id")
        measure_id = observation.get("measure_id")
        artifact_stage = observation.get("artifact_stage")
        if not isinstance(attempt_id, str) or not isinstance(measure_id, str) or not isinstance(artifact_stage, str):
            continue
        key = (attempt_id, measure_id, artifact_stage)
        if key in observation_by_opportunity:
            raise ValueError(f"duplicate observation opportunity {attempt_id}/{measure_id}/{artifact_stage}")
        observation_by_opportunity[key] = observation

    opportunities: list[tuple[Mapping[str, object], Mapping[str, object], str, bool]] = []
    expected_keys: set[tuple[str, str, str]] = set()
    selected_attempt_ids: set[str] = set()
    for attempt in attempts:
        if not isinstance(attempt, Mapping):
            continue
        attempt_id = attempt.get("attempt_id")
        task_id = attempt.get("task_id")
        subject_id = attempt.get("subject_id")
        variant_id = attempt.get("variant_id")
        if not isinstance(attempt_id, str) or not isinstance(task_id, str) or not isinstance(variant_id, str):
            continue
        task = tasks.get(task_id)
        if task is None:
            continue
        if scope_sets is not None and not _attempt_matches_scope(attempt, scope_sets):
            continue
        if scope_sets is not None and "experience_band_ids" in scope_sets:
            subject = subjects_by_id.get(subject_id)
            if (
                not isinstance(subject, Mapping)
                or subject.get("experience_band") not in scope_sets["experience_band_ids"]
            ):
                continue
        selected_attempt_ids.add(attempt_id)
        withdrawn = (isinstance(subject_id, str) and subject_id in withdrawn_subjects) or attempt.get(
            "outcome"
        ) == "withdrawn"
        for measure in measures.values():
            task_ids = _string_list(measure.get("task_ids"), non_empty=True)
            if task_ids is None or task_id not in task_ids:
                continue
            measure_id = measure.get("measure_id")
            if not isinstance(measure_id, str):
                continue
            for artifact_stage in _measure_stage_ids(measure, task_id, variant_id):
                if scope_sets is not None and artifact_stage not in scope_sets.get("artifact_stage_ids", set()):
                    continue
                opportunities.append((attempt, measure, artifact_stage, withdrawn))
                expected_keys.add((attempt_id, measure_id, artifact_stage))

    observed_keys = set(observation_by_opportunity)
    if scope_sets is not None:
        observed_keys = {
            key
            for key in observed_keys
            if key[0] in selected_attempt_ids
            and key[1] in scope_sets.get("measure_ids", set())
            and key[2] in scope_sets.get("artifact_stage_ids", set())
        }
    extras = sorted(observed_keys - expected_keys)
    if extras:
        raise ValueError(f"observations without protocol-declared opportunities: {extras[:5]}")
    return measures, opportunities, observation_by_opportunity


def recompute_measure_results(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    *,
    scope: Mapping[str, Sequence[str] | set[str]] | None = None,
) -> dict[str, dict[str, object]]:
    """Recompute measures from the complete protocol-derived opportunity matrix."""

    measures, opportunities, observation_by_opportunity = _measure_opportunities(protocol, snapshot, scope)
    results: dict[str, dict[str, object]] = {}
    for measure_id, measure in measures.items():
        aggregation = measure.get("aggregation")
        if aggregation not in {"proportion", "median", "count"}:
            raise ValueError(f"invalid measure aggregation for {measure_id!r}")

        matching = [item for item in opportunities if item[1].get("measure_id") == measure_id]
        opportunity_count = len(matching)
        withdrawn_count = sum(withdrawn for _, _, _, withdrawn in matching)
        eligible = [(attempt, artifact_stage) for attempt, _, artifact_stage, withdrawn in matching if not withdrawn]
        denominator = len(eligible)
        values: list[int | float] = []
        supporting_ids: list[str] = []
        missing_count = 0
        abandoned_count = 0
        tool_failed_count = 0

        for attempt, artifact_stage in eligible:
            attempt_id = attempt.get("attempt_id")
            if not isinstance(attempt_id, str):
                missing_count += 1
                continue
            observation = observation_by_opportunity.get((attempt_id, measure_id, artifact_stage))
            if observation is None:
                missing_count += 1
                continue
            observation_id = observation.get("observation_id")
            if not isinstance(observation_id, str):
                raise ValueError(f"{measure_id}: observations require ids")
            supporting_ids.append(observation_id)
            outcome = observation.get("outcome")
            if outcome == "missing":
                missing_count += 1
            elif outcome == "abandoned":
                abandoned_count += 1
            elif outcome == "tool_failed":
                tool_failed_count += 1
            value = observation.get("value")
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{measure_id}: observation values must be numeric or null")
            if aggregation == "proportion" and value not in {0, 1}:
                raise ValueError(f"{measure_id}: proportion observations must be 0 or 1")
            values.append(value)

        observed_count = len(values)
        numerator: int | float | None = None
        value: int | float | None = None
        if denominator > 0 and observed_count == denominator:
            if aggregation == "proportion":
                numerator = sum(values)
                value = numerator / denominator
            elif aggregation == "median":
                value = float(median(values))
            else:
                numerator = sum(values)
                value = numerator
        results[measure_id] = {
            "statistic": aggregation,
            "numerator": numerator,
            "denominator": denominator,
            "opportunity_count": opportunity_count,
            "observed_count": observed_count,
            "missing_count": missing_count,
            "abandoned_count": abandoned_count,
            "tool_failed_count": tool_failed_count,
            "withdrawn_count": withdrawn_count,
            "value": value,
            "supporting_observation_ids": supporting_ids,
        }
    return results


def recompute_dimension_results(
    protocol: Mapping[str, object],
    measure_results: Mapping[str, Mapping[str, object]],
    *,
    dimension_ids: Sequence[str] | set[str] | None = None,
) -> dict[str, dict[str, object]]:
    """Apply protocol-declared threshold conditions to recomputed measures."""

    operators = {
        ">=": lambda actual, target: actual >= target,
        "<=": lambda actual, target: actual <= target,
        "==": lambda actual, target: actual == target,
    }
    results: dict[str, dict[str, object]] = {}
    selected_dimensions = set(dimension_ids) if dimension_ids is not None else None
    for threshold in protocol.get("thresholds", []):
        if not isinstance(threshold, Mapping):
            continue
        dimension_id = threshold.get("dimension_id")
        conditions = threshold.get("conditions")
        if (
            not isinstance(dimension_id, str)
            or threshold.get("logic") != "all"
            or not isinstance(conditions, list)
            or not conditions
        ):
            raise ValueError(f"invalid threshold for {dimension_id!r}")
        if selected_dimensions is not None and dimension_id not in selected_dimensions:
            continue
        resolved: list[tuple[Mapping[str, object], Mapping[str, object]]] = []
        for condition in conditions:
            if not isinstance(condition, Mapping):
                raise ValueError(f"{dimension_id}: threshold condition must be an object")
            measure_id = condition.get("measure_id")
            operator = condition.get("operator")
            target = condition.get("target")
            measure = measure_results.get(measure_id) if isinstance(measure_id, str) else None
            if operator not in operators or isinstance(target, bool) or not isinstance(target, (int, float)):
                raise ValueError(f"{dimension_id}: invalid threshold operator or target")
            if measure is None:
                raise ValueError(f"{dimension_id}: threshold references unknown measure {measure_id!r}")
            resolved.append((condition, measure))
        if any(measure.get("value") is None for _, measure in resolved):
            results[dimension_id] = {
                "status": "not_evaluated",
                "threshold_result": "not_evaluated",
                "condition_results": [],
                "supporting_observation_ids": [],
            }
            continue
        condition_results: list[dict[str, object]] = []
        supporting_ids: list[str] = []
        for condition, measure in resolved:
            actual = measure["value"]
            operator = condition["operator"]
            target = condition["target"]
            if isinstance(actual, bool) or not isinstance(actual, (int, float)):
                raise ValueError(f"{dimension_id}: measure value must be numeric")
            passed = operators[operator](actual, target)
            condition_results.append(
                {
                    "measure_id": condition["measure_id"],
                    "operator": operator,
                    "target": target,
                    "actual": actual,
                    "passed": passed,
                }
            )
            refs = measure.get("supporting_observation_ids", [])
            if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
                raise ValueError(f"{dimension_id}: measure observation refs must be text ids")
            for observation_id in refs:
                if observation_id not in supporting_ids:
                    supporting_ids.append(observation_id)
        results[dimension_id] = {
            "status": "evaluated",
            "threshold_result": "pass" if all(item["passed"] for item in condition_results) else "fail",
            "condition_results": condition_results,
            "supporting_observation_ids": supporting_ids,
        }
    return results


def recompute_stratum_results(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    strata: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Recompute independently persisted results for every bound claim stratum."""

    results: list[dict[str, object]] = []
    for stratum in strata:
        stratum_id = stratum.get("stratum_id")
        role = stratum.get("role")
        scope = stratum.get("scope")
        if not isinstance(stratum_id, str) or role not in _STRATUM_ROLES or not isinstance(scope, Mapping):
            raise ValueError("invalid resolved claim stratum")
        measures = recompute_measure_results(protocol, snapshot, scope=scope)
        measure_results = [
            {
                "measure_id": measure_id,
                "status": (
                    "not_evaluated"
                    if result["denominator"] == 0
                    else "incomplete"
                    if result["observed_count"] != result["denominator"]
                    else "evaluated"
                ),
                **result,
            }
            for measure_id, result in measures.items()
        ]
        dimensions = recompute_dimension_results(
            protocol,
            measures,
            dimension_ids=scope.get("dimension_ids", set()),
        )
        dimension_results = [{"dimension_id": dimension_id, **result} for dimension_id, result in dimensions.items()]
        results.append(
            {
                "stratum_id": stratum_id,
                "role": role,
                "measure_results": measure_results,
                "dimension_results": dimension_results,
            }
        )
    return results
