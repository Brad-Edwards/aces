"""Preregistered-protocol validation for the DSL evaluation bundle."""

from __future__ import annotations

from pathlib import Path

from tools.dsl_language_evaluation._keys import (
    _CONDITION_KEYS,
    _DIMENSION_KEYS,
    _MAX_CATALOG_ITEMS,
    _PERSONA_KEYS,
    _PROTOCOL_KEYS,
    _SHA_RE,
    _SOURCE_KEYS,
    _STAGE_KEYS,
    _TASK_KEYS,
    _VARIANT_KEYS,
    REQUIRED_DIMENSION_IDS,
    REQUIRED_PERSONA_IDS,
    REQUIRED_TASK_KINDS,
)
from tools.dsl_language_evaluation._protocol_plans import _plan_failures, _preregistration_failures
from tools.dsl_language_evaluation._shape import (
    _bounded_list,
    _exact_keys,
    _failure,
    _record_ids,
    _resolve_repository_artifact,
    _string_list,
    _validate_https_locator,
)
from tools.policy.common import PolicyFailure


def _validate_protocol(
    repo_root: Path,
    protocol: dict[str, object],
    failures: list[PolicyFailure],
    *,
    path: str = "docs/research/dsl-language-evaluation/protocol-v1.json",
) -> dict[str, set[str]]:
    if not _exact_keys(
        protocol,
        _PROTOCOL_KEYS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="protocol",
        path=path,
    ):
        return {}

    dimensions = _bounded_list(
        protocol["dimensions"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="dimensions",
        path=path,
    )
    personas = _bounded_list(
        protocol["personas"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="personas",
        path=path,
    )
    conditions = _bounded_list(
        protocol["tooling_conditions"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="tooling_conditions",
        path=path,
    )
    stages = _bounded_list(
        protocol["artifact_stages"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="artifact_stages",
        path=path,
    )
    sources = _bounded_list(
        protocol["sources"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="sources",
        path=path,
    )
    tasks = _bounded_list(
        protocol["tasks"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="tasks",
        path=path,
    )
    variants = _bounded_list(
        protocol["variants"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="variants",
        path=path,
    )
    measures = _bounded_list(
        protocol["measures"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="measures",
        path=path,
    )
    thresholds = _bounded_list(
        protocol["thresholds"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-protocol-shape",
        label="thresholds",
        path=path,
    )

    dimension_ids = _record_ids(
        dimensions,
        "dimension_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="dimension",
        path=path,
    )
    persona_ids = _record_ids(
        personas,
        "persona_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="persona",
        path=path,
    )
    condition_ids = _record_ids(
        conditions,
        "condition_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="tooling condition",
        path=path,
    )
    stage_ids = _record_ids(
        stages,
        "stage_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="artifact stage",
        path=path,
    )
    source_ids = _record_ids(
        sources,
        "source_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="source",
        path=path,
    )
    task_ids = _record_ids(
        tasks,
        "task_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="task",
        path=path,
    )
    variant_ids = _record_ids(
        variants,
        "variant_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="variant",
        path=path,
    )
    measure_ids = _record_ids(
        measures,
        "measure_id",
        failures,
        rule_id="dsl-evaluation-protocol-id",
        label="measure",
        path=path,
    )

    if not REQUIRED_DIMENSION_IDS.issubset(dimension_ids):
        failures.append(
            _failure(
                "dsl-evaluation-dimension-coverage",
                f"missing required dimensions: {sorted(REQUIRED_DIMENSION_IDS - dimension_ids)}",
                path,
            )
        )
    if not REQUIRED_PERSONA_IDS.issubset(persona_ids):
        failures.append(
            _failure(
                "dsl-evaluation-persona-coverage",
                f"missing required personas: {sorted(REQUIRED_PERSONA_IDS - persona_ids)}",
                path,
            )
        )
    if protocol["evidence_status_values"] != [
        "untested",
        "partial",
        "demonstrated",
        "refuted",
    ]:
        failures.append(
            _failure(
                "dsl-evaluation-status-vocabulary",
                "evidence statuses must preserve ADR-021 order and vocabulary",
                path,
            )
        )

    for index, record in enumerate(dimensions):
        _exact_keys(
            record,
            _DIMENSION_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"dimensions[{index}]",
            path=path,
        )
    for index, record in enumerate(personas):
        if not _exact_keys(
            record,
            _PERSONA_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"personas[{index}]",
            path=path,
        ):
            continue
        if (
            not isinstance(record["minimum_completed_subjects"], int)
            or isinstance(record["minimum_completed_subjects"], bool)
            or record["minimum_completed_subjects"] < 0
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-sampling-plan",
                    f"{record['persona_id']}: minimum_completed_subjects must be non-negative",
                    path,
                )
            )
    for index, record in enumerate(conditions):
        _exact_keys(
            record,
            _CONDITION_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"tooling_conditions[{index}]",
            path=path,
        )
    for index, record in enumerate(stages):
        _exact_keys(
            record,
            _STAGE_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"artifact_stages[{index}]",
            path=path,
        )

    for index, source in enumerate(sources):
        if not _exact_keys(
            source,
            _SOURCE_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"sources[{index}]",
            path=path,
        ):
            continue
        source_id = source["source_id"]
        _validate_https_locator(source["locator"], failures, source_id)
        if source["primary"] is not True:
            failures.append(
                _failure(
                    "dsl-evaluation-source-primary",
                    f"{source_id}: source must be primary",
                    path,
                )
            )
        if source["kind"] == "repository-internal":
            revision = source["revision"]
            artifact_path = source["artifact_path"]
            if not isinstance(revision, str) or not _SHA_RE.fullmatch(revision):
                failures.append(
                    _failure(
                        "dsl-evaluation-source-pin",
                        f"{source_id}: invalid Git revision",
                        path,
                    )
                )
            elif isinstance(source["locator"], str) and revision not in source["locator"]:
                failures.append(
                    _failure(
                        "dsl-evaluation-source-pin",
                        f"{source_id}: locator does not bind the declared Git revision",
                        path,
                    )
                )
            if not isinstance(artifact_path, str):
                failures.append(
                    _failure(
                        "dsl-evaluation-source-path",
                        f"{source_id}: missing artifact path",
                        path,
                    )
                )
            else:
                resolved = _resolve_repository_artifact(repo_root, artifact_path)
                if resolved is None or not resolved.exists():
                    failures.append(
                        _failure(
                            "dsl-evaluation-source-path",
                            f"{source_id}: unsafe or missing path",
                            path,
                        )
                    )
        elif source["revision"] is not None or source["artifact_path"] is not None:
            failures.append(
                _failure(
                    "dsl-evaluation-source-shape",
                    f"{source_id}: publication must not claim a repository revision/path",
                    path,
                )
            )

    task_kinds: set[str] = set()
    variants_by_task: dict[str, set[str]] = {task_id: set() for task_id in task_ids}
    for index, variant in enumerate(variants):
        if not _exact_keys(
            variant,
            _VARIANT_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"variants[{index}]",
            path=path,
        ):
            continue
        task_id = variant["task_id"]
        if not isinstance(task_id, str) or task_id not in task_ids:
            failures.append(
                _failure(
                    "dsl-evaluation-variant-join",
                    f"{variant['variant_id']}: unknown task",
                    path,
                )
            )
        else:
            variant_id = variant["variant_id"]
            if isinstance(variant_id, str):
                variants_by_task[task_id].add(variant_id)
    for index, task in enumerate(tasks):
        if not _exact_keys(
            task,
            _TASK_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"tasks[{index}]",
            path=path,
        ):
            continue
        task_id = task["task_id"]
        if not isinstance(task_id, str):
            failures.append(_failure("dsl-evaluation-protocol-id", "task id must be text", path))
            continue
        task_kind = task["kind"]
        if isinstance(task_kind, str):
            task_kinds.add(task_kind)
        else:
            failures.append(
                _failure(
                    "dsl-evaluation-task-kind-coverage",
                    f"{task_id}: task kind must be text",
                    path,
                )
            )
        joins = (
            ("persona_ids", persona_ids),
            ("dimension_ids", dimension_ids),
            ("source_refs", source_ids),
            ("artifact_stage_ids", stage_ids),
            ("tooling_condition_ids", condition_ids),
            ("variant_ids", variant_ids),
        )
        for field, allowed in joins:
            values = task[field]
            value_ids = _string_list(values, non_empty=True)
            if value_ids is None or not set(value_ids).issubset(allowed):
                failures.append(
                    _failure(
                        "dsl-evaluation-task-join",
                        f"{task_id}: invalid or empty {field}",
                        path,
                    )
                )
        task_variant_ids = task["variant_ids"]
        valid_task_variant_ids = _string_list(task_variant_ids)
        if valid_task_variant_ids is not None and set(valid_task_variant_ids) != variants_by_task.get(task_id, set()):
            failures.append(
                _failure(
                    "dsl-evaluation-task-variant-coverage",
                    f"{task_id}: task and variant catalogs disagree",
                    path,
                )
            )
    if not REQUIRED_TASK_KINDS.issubset(task_kinds):
        failures.append(
            _failure(
                "dsl-evaluation-task-kind-coverage",
                f"missing required task kinds: {sorted(REQUIRED_TASK_KINDS - task_kinds)}",
                path,
            )
        )

    catalogs_ids = {
        "dimension_ids": dimension_ids,
        "persona_ids": persona_ids,
        "condition_ids": condition_ids,
        "stage_ids": stage_ids,
        "source_ids": source_ids,
        "task_ids": task_ids,
        "variant_ids": variant_ids,
        "measure_ids": measure_ids,
    }
    _plan_failures(protocol, catalogs_ids, personas, tasks, measures, thresholds, failures, path)
    _preregistration_failures(protocol, failures, path)
    return {
        "dimension_ids": dimension_ids,
        "persona_ids": persona_ids,
        "condition_ids": condition_ids,
        "stage_ids": stage_ids,
        "task_ids": task_ids,
        "variant_ids": variant_ids,
        "measure_ids": measure_ids,
    }
