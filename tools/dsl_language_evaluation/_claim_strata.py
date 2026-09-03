"""Claim-binding stratum expansion and per-stratum scope derivation."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product

from tools.dsl_language_evaluation._keys import (
    _STRATUM_GROUP_KEYS,
    _STRATUM_PARTITION_AXES,
    _STRATUM_ROLES,
)
from tools.dsl_language_evaluation._shape import (
    _exact_keys,
    _failure,
    _protocol_records_by_id,
    _string_list,
    _valid_id,
)
from tools.policy.common import PolicyFailure


def _thresholds_by_dimension(protocol: Mapping[str, object]) -> dict[object, Mapping[str, object]]:
    return {
        threshold.get("dimension_id"): threshold
        for threshold in protocol.get("thresholds", [])
        if isinstance(threshold, Mapping) and isinstance(threshold.get("dimension_id"), str)
    }


def _threshold_measures(threshold: Mapping[str, object] | None) -> set[object]:
    conditions = threshold.get("conditions", []) if isinstance(threshold, Mapping) else []
    return {
        condition.get("measure_id")
        for condition in conditions
        if isinstance(condition, Mapping) and isinstance(condition.get("measure_id"), str)
    }


def _unique_subset(values: list[str] | None, allowed: set[str]) -> bool:
    return values is not None and len(values) == len(set(values)) and set(values).issubset(allowed)


def _validated_group_filters(
    group: Mapping[str, object],
    scope: Mapping[str, set[str]],
    experience_bands: set[str],
) -> tuple[str, str, list[str], list[str], list[str], list[str]] | None:
    """Return (group_id, role, partition_by, personas, bands, conditions) or None."""

    group_id = group["group_id"]
    role = group["role"]
    partition_by = _string_list(group["partition_by"])
    persona_ids = _string_list(group["persona_ids"], non_empty=True)
    band_ids = _string_list(group["experience_band_ids"], non_empty=True)
    condition_ids = _string_list(group["tooling_condition_ids"], non_empty=True)
    identity_valid = _valid_id(group_id) and isinstance(group_id, str)
    role_valid = isinstance(role, str) and role in _STRATUM_ROLES
    valid = all(
        (
            identity_valid,
            role_valid,
            _unique_subset(partition_by, _STRATUM_PARTITION_AXES),
            _unique_subset(persona_ids, scope.get("persona_ids", set())),
            _unique_subset(band_ids, experience_bands),
            _unique_subset(condition_ids, scope.get("tooling_condition_ids", set())),
        )
    )
    if not valid:
        return None
    assert partition_by is not None
    assert persona_ids is not None
    assert band_ids is not None
    assert condition_ids is not None
    return group_id, role, partition_by, persona_ids, band_ids, condition_ids


def _expanded_strata(
    protocol: Mapping[str, object],
    scope: Mapping[str, set[str]],
    groups: list[object],
    failures: list[PolicyFailure],
    path: str,
) -> list[dict[str, object]]:
    experience_bands = set()
    sampling_plan = protocol.get("sampling_plan")
    if isinstance(sampling_plan, Mapping):
        experience_bands = set(_string_list(sampling_plan.get("experience_bands"), non_empty=True) or [])
    expanded: list[dict[str, object]] = []
    for index, group in enumerate(groups):
        if not _exact_keys(
            group,
            _STRATUM_GROUP_KEYS,
            failures,
            rule_id="dsl-evaluation-claim-strata",
            label=f"claim binding strata[{index}]",
            path=path,
        ):
            continue
        assert isinstance(group, dict)
        filters = _validated_group_filters(group, scope, experience_bands)
        if filters is None:
            failures.append(
                _failure(
                    "dsl-evaluation-claim-strata",
                    f"claim stratum group {group['group_id']!r} has invalid role, partition axes, or catalog filters",
                    path,
                )
            )
            continue
        expanded.extend(_expanded_group_strata(protocol, scope, group, filters, failures, path))
    return expanded


def _expanded_strata_failures(
    groups: list[object],
    group_ids: set[str],
    expanded: list[dict[str, object]],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    expanded_ids = [str(item["stratum_id"]) for item in expanded]
    if len(group_ids) != len(groups) or len(expanded_ids) != len(set(expanded_ids)) or not expanded:
        failures.append(
            _failure(
                "dsl-evaluation-claim-strata",
                "claim binding requires unique groups and expanded stratum ids",
                path,
            )
        )
    if not any(item["role"] == "gating" for item in expanded):
        failures.append(_failure("dsl-evaluation-claim-strata", "claim binding requires a gating stratum", path))


def _expanded_group_strata(
    protocol: Mapping[str, object],
    scope: Mapping[str, set[str]],
    group: Mapping[str, object],
    filters: tuple[str, str, list[str], list[str], list[str], list[str]],
    failures: list[PolicyFailure],
    path: str,
) -> list[dict[str, object]]:
    del group
    group_id, role, partition_by, persona_ids, band_ids, condition_ids = filters
    axis_values = {
        "persona_id": persona_ids,
        "experience_band": band_ids,
        "tooling_condition_id": condition_ids,
    }
    split_axes = [axis for axis in ("persona_id", "experience_band", "tooling_condition_id") if axis in partition_by]
    combinations = product(*(axis_values[axis] for axis in split_axes)) if split_axes else [()]
    expanded: list[dict[str, object]] = []
    for combination in combinations:
        selected = dict(zip(split_axes, combination, strict=True))
        stratum_id = "-".join([group_id, *(str(selected[axis]) for axis in split_axes)])
        stratum_scope = _combination_scope(protocol, scope, filters, selected)
        if _incomplete_stratum(stratum_id, stratum_scope):
            failures.append(
                _failure(
                    "dsl-evaluation-claim-strata",
                    f"claim stratum {stratum_id!r} has no complete task/measure/dimension slice",
                    path,
                )
            )
            continue
        expanded.append({"stratum_id": stratum_id, "role": role, "scope": stratum_scope})
    return expanded


def _combination_scope(
    protocol: Mapping[str, object],
    scope: Mapping[str, set[str]],
    filters: tuple[str, str, list[str], list[str], list[str], list[str]],
    selected: Mapping[str, object],
) -> dict[str, set[str]]:
    _, _, _, persona_ids, band_ids, condition_ids = filters
    return _derive_stratum_scope(
        protocol,
        scope,
        persona_ids={str(selected["persona_id"])} if "persona_id" in selected else set(persona_ids),
        experience_band_ids={str(selected["experience_band"])} if "experience_band" in selected else set(band_ids),
        tooling_condition_ids=(
            {str(selected["tooling_condition_id"])} if "tooling_condition_id" in selected else set(condition_ids)
        ),
    )


def _incomplete_stratum(stratum_id: str, stratum_scope: Mapping[str, set[str]]) -> bool:
    return (
        not _valid_id(stratum_id)
        or not stratum_scope["task_ids"]
        or not stratum_scope["measure_ids"]
        or not stratum_scope["dimension_ids"]
    )


def _derive_stratum_scope(
    protocol: Mapping[str, object],
    claim_scope: Mapping[str, set[str]],
    *,
    persona_ids: set[str],
    experience_band_ids: set[str],
    tooling_condition_ids: set[str],
) -> dict[str, set[str]]:
    """Derive the protocol-applicable claim slice for one preregistered stratum."""

    selected_tasks = _stratum_tasks(protocol, claim_scope, persona_ids, tooling_condition_ids)
    selected_variants = _stratum_variants(protocol, claim_scope, selected_tasks)
    selected_measures = _stratum_measures(protocol, claim_scope, selected_tasks)
    selected_dimensions = _stratum_dimensions(protocol, claim_scope, selected_measures)
    return {
        "persona_ids": set(persona_ids),
        "experience_band_ids": set(experience_band_ids),
        "task_ids": selected_tasks,
        "tooling_condition_ids": set(tooling_condition_ids),
        "variant_ids": selected_variants,
        "artifact_stage_ids": set(claim_scope.get("artifact_stage_ids", set())),
        "dimension_ids": selected_dimensions,
        "measure_ids": selected_measures,
    }


def _stratum_tasks(
    protocol: Mapping[str, object],
    claim_scope: Mapping[str, set[str]],
    persona_ids: set[str],
    tooling_condition_ids: set[str],
) -> set[str]:
    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    return {
        task_id
        for task_id, task in tasks.items()
        if task_id in claim_scope.get("task_ids", set())
        and set(_string_list(task.get("persona_ids"), non_empty=True) or []) & persona_ids
        and set(_string_list(task.get("tooling_condition_ids"), non_empty=True) or []) & tooling_condition_ids
    }


def _stratum_variants(
    protocol: Mapping[str, object],
    claim_scope: Mapping[str, set[str]],
    selected_tasks: set[str],
) -> set[str]:
    variants = _protocol_records_by_id(protocol, "variants", "variant_id")
    return {
        variant_id
        for variant_id, variant in variants.items()
        if variant_id in claim_scope.get("variant_ids", set()) and variant.get("task_id") in selected_tasks
    }


def _stratum_measures(
    protocol: Mapping[str, object],
    claim_scope: Mapping[str, set[str]],
    selected_tasks: set[str],
) -> set[str]:
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")
    return {
        measure_id
        for measure_id, measure in measures.items()
        if measure_id in claim_scope.get("measure_ids", set())
        and set(_string_list(measure.get("task_ids"), non_empty=True) or []) & selected_tasks
    }


def _stratum_dimensions(
    protocol: Mapping[str, object],
    claim_scope: Mapping[str, set[str]],
    selected_measures: set[str],
) -> set[str]:
    thresholds = _thresholds_by_dimension(protocol)
    selected_dimensions = set()
    for dimension_id in claim_scope.get("dimension_ids", set()):
        required_measures = _threshold_measures(thresholds.get(dimension_id))
        if required_measures and required_measures.issubset(selected_measures):
            selected_dimensions.add(dimension_id)
    return selected_dimensions
