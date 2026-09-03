"""Preregistered-protocol validation for the DSL evaluation bundle."""

from __future__ import annotations

from collections.abc import Mapping
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

_CATALOG_FIELDS = (
    ("dimensions", "dimension_id", "dimension"),
    ("personas", "persona_id", "persona"),
    ("tooling_conditions", "condition_id", "tooling condition"),
    ("artifact_stages", "stage_id", "artifact stage"),
    ("sources", "source_id", "source"),
    ("tasks", "task_id", "task"),
    ("variants", "variant_id", "variant"),
    ("measures", "measure_id", "measure"),
)


def _protocol_catalog_records(
    protocol: dict[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> dict[str, list[object]]:
    records: dict[str, list[object]] = {}
    for field, _id_field, _label in (*_CATALOG_FIELDS, ("thresholds", "", "")):
        records[field] = _bounded_list(
            protocol[field],
            _MAX_CATALOG_ITEMS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=field,
            path=path,
        )
    return records


def _protocol_catalog_ids(
    records: Mapping[str, list[object]],
    failures: list[PolicyFailure],
    path: str,
) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = {}
    for field, id_field, label in _CATALOG_FIELDS:
        ids[_ID_KEYS[field]] = _record_ids(
            records[field],
            id_field,
            failures,
            rule_id="dsl-evaluation-protocol-id",
            label=label,
            path=path,
        )
    return ids


_ID_KEYS = {
    "dimensions": "dimension_ids",
    "personas": "persona_ids",
    "tooling_conditions": "condition_ids",
    "artifact_stages": "stage_ids",
    "sources": "source_ids",
    "tasks": "task_ids",
    "variants": "variant_ids",
    "measures": "measure_ids",
}


def _required_coverage_failures(
    protocol: dict[str, object],
    dimension_ids: set[str],
    persona_ids: set[str],
    failures: list[PolicyFailure],
    path: str,
) -> None:
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


def _catalog_shape_failures(
    records: Mapping[str, list[object]],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    for index, record in enumerate(records["dimensions"]):
        _exact_keys(
            record,
            _DIMENSION_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"dimensions[{index}]",
            path=path,
        )
    for index, record in enumerate(records["personas"]):
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
    for index, record in enumerate(records["tooling_conditions"]):
        _exact_keys(
            record,
            _CONDITION_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"tooling_conditions[{index}]",
            path=path,
        )
    for index, record in enumerate(records["artifact_stages"]):
        _exact_keys(
            record,
            _STAGE_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"artifact_stages[{index}]",
            path=path,
        )


def _repository_source_failures(
    repo_root: Path,
    source: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    source_id = source["source_id"]
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


def _source_entry_failures(
    repo_root: Path,
    source: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
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
        _repository_source_failures(repo_root, source, failures, path)
    elif source["revision"] is not None or source["artifact_path"] is not None:
        failures.append(
            _failure(
                "dsl-evaluation-source-shape",
                f"{source_id}: publication must not claim a repository revision/path",
                path,
            )
        )


def _variants_by_task(
    variants: list[object],
    task_ids: set[str],
    failures: list[PolicyFailure],
    path: str,
) -> dict[str, set[str]]:
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
    return variants_by_task


def _task_entry_failures(
    task: Mapping[str, object],
    task_id: str,
    ids: Mapping[str, set[str]],
    variants_by_task: Mapping[str, set[str]],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    joins = (
        ("persona_ids", ids["persona_ids"]),
        ("dimension_ids", ids["dimension_ids"]),
        ("source_refs", ids["source_ids"]),
        ("artifact_stage_ids", ids["stage_ids"]),
        ("tooling_condition_ids", ids["condition_ids"]),
        ("variant_ids", ids["variant_ids"]),
    )
    for field, allowed in joins:
        value_ids = _string_list(task[field], non_empty=True)
        if value_ids is None or not set(value_ids).issubset(allowed):
            failures.append(
                _failure(
                    "dsl-evaluation-task-join",
                    f"{task_id}: invalid or empty {field}",
                    path,
                )
            )
    valid_task_variant_ids = _string_list(task["variant_ids"])
    if valid_task_variant_ids is not None and set(valid_task_variant_ids) != variants_by_task.get(task_id, set()):
        failures.append(
            _failure(
                "dsl-evaluation-task-variant-coverage",
                f"{task_id}: task and variant catalogs disagree",
                path,
            )
        )


def _task_failures(
    records: Mapping[str, list[object]],
    ids: Mapping[str, set[str]],
    variants_by_task: Mapping[str, set[str]],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    task_kinds: set[str] = set()
    for index, task in enumerate(records["tasks"]):
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
        _task_entry_failures(task, task_id, ids, variants_by_task, failures, path)
    if not REQUIRED_TASK_KINDS.issubset(task_kinds):
        failures.append(
            _failure(
                "dsl-evaluation-task-kind-coverage",
                f"missing required task kinds: {sorted(REQUIRED_TASK_KINDS - task_kinds)}",
                path,
            )
        )


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

    records = _protocol_catalog_records(protocol, failures, path)
    ids = _protocol_catalog_ids(records, failures, path)

    _required_coverage_failures(protocol, ids["dimension_ids"], ids["persona_ids"], failures, path)
    _catalog_shape_failures(records, failures, path)

    for index, source in enumerate(records["sources"]):
        if _exact_keys(
            source,
            _SOURCE_KEYS,
            failures,
            rule_id="dsl-evaluation-protocol-shape",
            label=f"sources[{index}]",
            path=path,
        ):
            _source_entry_failures(repo_root, source, failures, path)

    variants_by_task = _variants_by_task(records["variants"], ids["task_ids"], failures, path)
    _task_failures(records, ids, variants_by_task, failures, path)

    _plan_failures(protocol, ids, records, failures, path)
    _preregistration_failures(protocol, failures, path)
    return {
        "dimension_ids": ids["dimension_ids"],
        "persona_ids": ids["persona_ids"],
        "condition_ids": ids["condition_ids"],
        "stage_ids": ids["stage_ids"],
        "task_ids": ids["task_ids"],
        "variant_ids": ids["variant_ids"],
        "measure_ids": ids["measure_ids"],
    }
