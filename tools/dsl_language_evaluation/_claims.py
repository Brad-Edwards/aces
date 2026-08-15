"""Claim scope and stratum binding validation."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product

from tools.dsl_language_evaluation._keys import (
    _CLAIM_BINDING_KEYS,
    _CLAIM_SCOPE_KEYS,
    _MAX_CATALOG_ITEMS,
    _STRATUM_GROUP_KEYS,
    _STRATUM_PARTITION_AXES,
    _STRATUM_ROLES,
    MANIFEST_PATH,
)
from tools.dsl_language_evaluation._shape import (
    _bounded_list,
    _exact_keys,
    _failure,
    _protocol_records_by_id,
    _record_ids,
    _string_list,
    _valid_id,
)
from tools.policy.common import PolicyFailure


def _full_claim_scope(catalogs: Mapping[str, set[str]]) -> dict[str, set[str]]:
    return {
        "persona_ids": set(catalogs.get("persona_ids", set())),
        "task_ids": set(catalogs.get("task_ids", set())),
        "tooling_condition_ids": set(catalogs.get("condition_ids", set())),
        "variant_ids": set(catalogs.get("variant_ids", set())),
        "artifact_stage_ids": set(catalogs.get("stage_ids", set())),
        "dimension_ids": set(catalogs.get("dimension_ids", set())),
        "measure_ids": set(catalogs.get("measure_ids", set())),
    }


def _attempt_matches_scope(
    attempt: Mapping[str, object],
    scope: Mapping[str, set[str]],
) -> bool:
    return (
        attempt.get("task_id") in scope.get("task_ids", set())
        and attempt.get("persona_id") in scope.get("persona_ids", set())
        and attempt.get("tooling_condition_id") in scope.get("tooling_condition_ids", set())
        and attempt.get("variant_id") in scope.get("variant_ids", set())
    )


def _validate_claim_scope(
    protocol: Mapping[str, object],
    analysis: Mapping[str, object],
    catalogs: Mapping[str, set[str]],
    failures: list[PolicyFailure],
    *,
    path: str = "docs/research/dsl-language-evaluation/analysis-v1.json",
) -> dict[str, set[str]]:
    """Validate and resolve the exact catalog slice owned by one claim."""

    fallback = _full_claim_scope(catalogs)
    claim = analysis.get("claim")
    scope = claim.get("scope") if isinstance(claim, Mapping) else None
    if not _exact_keys(
        scope,
        _CLAIM_SCOPE_KEYS,
        failures,
        rule_id="dsl-evaluation-claim-scope",
        label="claim scope",
        path=path,
    ):
        return fallback

    catalog_fields = {
        "persona_ids": "persona_ids",
        "task_ids": "task_ids",
        "tooling_condition_ids": "condition_ids",
        "variant_ids": "variant_ids",
        "artifact_stage_ids": "stage_ids",
        "dimension_ids": "dimension_ids",
        "measure_ids": "measure_ids",
    }
    resolved: dict[str, set[str]] = {}
    for field, catalog_field in catalog_fields.items():
        values = _string_list(scope[field], non_empty=True)
        known = catalogs.get(catalog_field, set())
        if values is None or len(values) != len(set(values)) or not set(values).issubset(known):
            failures.append(
                _failure(
                    "dsl-evaluation-claim-scope",
                    f"claim scope {field} must be a non-empty unique subset of the protocol catalog",
                    path,
                )
            )
            resolved[field] = set(values or []) & known
        else:
            resolved[field] = set(values)

    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")
    for task_id in resolved["task_ids"]:
        task = tasks.get(task_id, {})
        joins = (
            ("persona_ids", "persona_ids"),
            ("tooling_condition_ids", "tooling_condition_ids"),
            ("variant_ids", "variant_ids"),
            ("artifact_stage_ids", "artifact_stage_ids"),
        )
        if any(
            not (set(_string_list(task.get(task_field), non_empty=True) or []) & resolved[scope_field])
            for task_field, scope_field in joins
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-claim-scope",
                    f"{task_id}: claim scope must retain an eligible persona, condition, variant, and stage",
                    path,
                )
            )
        if not any(
            task_id in (_string_list(measures[measure_id].get("task_ids"), non_empty=True) or [])
            for measure_id in resolved["measure_ids"]
            if measure_id in measures
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-claim-scope",
                    f"{task_id}: claim scope has no applicable measure",
                    path,
                )
            )

    thresholds = {
        threshold.get("dimension_id"): threshold
        for threshold in protocol.get("thresholds", [])
        if isinstance(threshold, Mapping) and isinstance(threshold.get("dimension_id"), str)
    }
    for dimension_id in resolved["dimension_ids"]:
        threshold = thresholds.get(dimension_id)
        conditions = threshold.get("conditions", []) if isinstance(threshold, Mapping) else []
        required_measures = {
            condition.get("measure_id")
            for condition in conditions
            if isinstance(condition, Mapping) and isinstance(condition.get("measure_id"), str)
        }
        if not required_measures or not required_measures.issubset(resolved["measure_ids"]):
            failures.append(
                _failure(
                    "dsl-evaluation-claim-scope",
                    f"{dimension_id}: claim scope must include every threshold measure",
                    path,
                )
            )
    return resolved


def _validate_claim_binding(
    protocol: Mapping[str, object],
    analysis: Mapping[str, object],
    claim_binding: object,
    catalogs: Mapping[str, set[str]],
    scope: Mapping[str, set[str]],
    failures: list[PolicyFailure],
    *,
    path: str,
) -> list[dict[str, object]]:
    """Bind one stable claim to its immutable scope and reporting strata."""

    if not _exact_keys(
        claim_binding,
        _CLAIM_BINDING_KEYS,
        failures,
        rule_id="dsl-evaluation-claim-binding",
        label="claim binding",
        path=path,
    ):
        return []
    assert isinstance(claim_binding, dict)
    claim = analysis.get("claim")
    claim_id = claim.get("claim_id") if isinstance(claim, Mapping) else None
    if not _valid_id(claim_binding["claim_id"]) or claim_binding["claim_id"] != claim_id:
        failures.append(
            _failure(
                "dsl-evaluation-claim-binding",
                "manifest claim binding must name the analysis claim_id exactly",
                path,
            )
        )

    bound_scope = claim_binding["scope"]
    if _exact_keys(
        bound_scope,
        _CLAIM_SCOPE_KEYS,
        failures,
        rule_id="dsl-evaluation-claim-binding",
        label="claim binding scope",
        path=path,
    ):
        assert isinstance(bound_scope, dict)
        for field in _CLAIM_SCOPE_KEYS:
            values = _string_list(bound_scope[field], non_empty=True)
            if values is None or len(values) != len(set(values)) or set(values) != scope.get(field, set()):
                failures.append(
                    _failure(
                        "dsl-evaluation-claim-binding",
                        f"analysis claim scope {field} must exactly match its manifest binding",
                        path,
                    )
                )

    groups = _bounded_list(
        claim_binding["strata"],
        16,
        failures,
        rule_id="dsl-evaluation-claim-strata",
        label="claim binding strata",
        path=path,
    )
    group_ids = _record_ids(
        groups,
        "group_id",
        failures,
        rule_id="dsl-evaluation-claim-strata",
        label="claim stratum group",
        path=path,
    )
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
        group_id = group["group_id"]
        role = group["role"]
        partition_by = _string_list(group["partition_by"])
        persona_ids = _string_list(group["persona_ids"], non_empty=True)
        band_ids = _string_list(group["experience_band_ids"], non_empty=True)
        condition_ids = _string_list(group["tooling_condition_ids"], non_empty=True)
        valid = (
            _valid_id(group_id)
            and role in _STRATUM_ROLES
            and partition_by is not None
            and len(partition_by) == len(set(partition_by))
            and set(partition_by).issubset(_STRATUM_PARTITION_AXES)
            and persona_ids is not None
            and len(persona_ids) == len(set(persona_ids))
            and set(persona_ids).issubset(scope.get("persona_ids", set()))
            and band_ids is not None
            and len(band_ids) == len(set(band_ids))
            and set(band_ids).issubset(experience_bands)
            and condition_ids is not None
            and len(condition_ids) == len(set(condition_ids))
            and set(condition_ids).issubset(scope.get("tooling_condition_ids", set()))
        )
        if not valid:
            failures.append(
                _failure(
                    "dsl-evaluation-claim-strata",
                    f"claim stratum group {group_id!r} has invalid role, partition axes, or catalog filters",
                    path,
                )
            )
            continue

        assert isinstance(group_id, str)
        assert isinstance(role, str)
        assert partition_by is not None
        assert persona_ids is not None
        assert band_ids is not None
        assert condition_ids is not None
        axis_values = {
            "persona_id": persona_ids,
            "experience_band": band_ids,
            "tooling_condition_id": condition_ids,
        }
        split_axes = [
            axis for axis in ("persona_id", "experience_band", "tooling_condition_id") if axis in partition_by
        ]
        combinations = product(*(axis_values[axis] for axis in split_axes)) if split_axes else [()]
        for combination in combinations:
            selected = dict(zip(split_axes, combination, strict=True))
            stratum_id = "-".join([group_id, *(str(selected[axis]) for axis in split_axes)])
            stratum_personas = {str(selected["persona_id"])} if "persona_id" in selected else set(persona_ids)
            stratum_bands = {str(selected["experience_band"])} if "experience_band" in selected else set(band_ids)
            stratum_conditions = (
                {str(selected["tooling_condition_id"])} if "tooling_condition_id" in selected else set(condition_ids)
            )
            stratum_scope = _derive_stratum_scope(
                protocol,
                scope,
                persona_ids=stratum_personas,
                experience_band_ids=stratum_bands,
                tooling_condition_ids=stratum_conditions,
            )
            if (
                not _valid_id(stratum_id)
                or not stratum_scope["task_ids"]
                or not stratum_scope["measure_ids"]
                or not stratum_scope["dimension_ids"]
            ):
                failures.append(
                    _failure(
                        "dsl-evaluation-claim-strata",
                        f"claim stratum {stratum_id!r} has no complete task/measure/dimension slice",
                        path,
                    )
                )
                continue
            expanded.append({"stratum_id": stratum_id, "role": role, "scope": stratum_scope})

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
    if len(expanded) > _MAX_CATALOG_ITEMS:
        failures.append(
            _failure(
                "dsl-evaluation-claim-strata",
                f"claim binding expands beyond {_MAX_CATALOG_ITEMS} strata",
                path,
            )
        )
        return expanded[:_MAX_CATALOG_ITEMS]
    return expanded


def _derive_stratum_scope(
    protocol: Mapping[str, object],
    claim_scope: Mapping[str, set[str]],
    *,
    persona_ids: set[str],
    experience_band_ids: set[str],
    tooling_condition_ids: set[str],
) -> dict[str, set[str]]:
    """Derive the protocol-applicable claim slice for one preregistered stratum."""

    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    selected_tasks = {
        task_id
        for task_id, task in tasks.items()
        if task_id in claim_scope.get("task_ids", set())
        and set(_string_list(task.get("persona_ids"), non_empty=True) or []) & persona_ids
        and set(_string_list(task.get("tooling_condition_ids"), non_empty=True) or []) & tooling_condition_ids
    }
    variants = _protocol_records_by_id(protocol, "variants", "variant_id")
    selected_variants = {
        variant_id
        for variant_id, variant in variants.items()
        if variant_id in claim_scope.get("variant_ids", set()) and variant.get("task_id") in selected_tasks
    }
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")
    selected_measures = {
        measure_id
        for measure_id, measure in measures.items()
        if measure_id in claim_scope.get("measure_ids", set())
        and set(_string_list(measure.get("task_ids"), non_empty=True) or []) & selected_tasks
    }
    thresholds = {
        threshold.get("dimension_id"): threshold
        for threshold in protocol.get("thresholds", [])
        if isinstance(threshold, Mapping) and isinstance(threshold.get("dimension_id"), str)
    }
    selected_dimensions = set()
    for dimension_id in claim_scope.get("dimension_ids", set()):
        threshold = thresholds.get(dimension_id)
        conditions = threshold.get("conditions", []) if isinstance(threshold, Mapping) else []
        required_measures = {
            condition.get("measure_id")
            for condition in conditions
            if isinstance(condition, Mapping) and isinstance(condition.get("measure_id"), str)
        }
        if required_measures and required_measures.issubset(selected_measures):
            selected_dimensions.add(dimension_id)
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


def resolve_claim_strata(
    protocol: Mapping[str, object],
    analysis: Mapping[str, object],
    claim_binding: Mapping[str, object],
) -> list[dict[str, object]]:
    """Resolve a validated manifest binding for recomputation and fixtures."""

    catalogs = {
        "persona_ids": set(_protocol_records_by_id(protocol, "personas", "persona_id")),
        "task_ids": set(_protocol_records_by_id(protocol, "tasks", "task_id")),
        "condition_ids": set(_protocol_records_by_id(protocol, "tooling_conditions", "condition_id")),
        "variant_ids": set(_protocol_records_by_id(protocol, "variants", "variant_id")),
        "stage_ids": set(_protocol_records_by_id(protocol, "artifact_stages", "stage_id")),
        "dimension_ids": set(_protocol_records_by_id(protocol, "dimensions", "dimension_id")),
        "measure_ids": set(_protocol_records_by_id(protocol, "measures", "measure_id")),
    }
    failures: list[PolicyFailure] = []
    scope = _validate_claim_scope(protocol, analysis, catalogs, failures, path=MANIFEST_PATH)
    strata = _validate_claim_binding(
        protocol,
        analysis,
        claim_binding,
        catalogs,
        scope,
        failures,
        path=MANIFEST_PATH,
    )
    if failures:
        raise ValueError("; ".join(f"{failure.rule_id}: {failure.message}" for failure in failures))
    return strata
