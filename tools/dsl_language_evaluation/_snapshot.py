"""Execution-snapshot validation for the DSL evaluation bundle."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from tools.dsl_language_evaluation._keys import (
    _ATTEMPT_KEYS,
    _DEVIATION_KEYS,
    _DISAGREEMENT_KEYS,
    _ETHICS_REVIEW_KEYS,
    _HISTORICAL_REVISION_FIELD,
    _MAX_CATALOG_ITEMS,
    _MAX_EXECUTION_RECORDS,
    _OBSERVATION_KEYS,
    _REVIEW_KEYS,
    _SHA_RE,
    _SNAPSHOT_KEYS,
    _SUBJECT_KEYS,
    _SURFACE_KEYS,
    _WITHDRAWAL_KEYS,
    ATTEMPT_OUTCOMES,
    OBSERVATION_OUTCOMES,
)
from tools.dsl_language_evaluation._measures import _measure_stage_ids
from tools.dsl_language_evaluation._shape import (
    _bounded_list,
    _bounded_text,
    _exact_keys,
    _failure,
    _protocol_records_by_id,
    _record_ids,
    _resolve_repository_artifact,
    _string_list,
    _valid_id,
)
from tools.dsl_language_evaluation._snapshot_completion import (
    _review_and_completion_failures,
    _SnapshotJoins,
    _subject_failures,
)
from tools.policy.common import PolicyFailure, safe_repo_path


def _validate_snapshot(
    repo_root: Path,
    protocol: Mapping[str, object],
    snapshot: dict[str, object],
    catalogs: Mapping[str, set[str]],
    scope: Mapping[str, set[str]],
    failures: list[PolicyFailure],
    *,
    path: str = "docs/research/dsl-language-evaluation/execution-snapshot-v1.json",
) -> set[str]:
    if not _exact_keys(
        snapshot,
        _SNAPSHOT_KEYS,
        failures,
        rule_id="dsl-evaluation-snapshot-shape",
        label="snapshot",
        path=path,
    ):
        return set()
    if snapshot["protocol_revision"] != protocol.get("revision"):
        failures.append(_failure("dsl-evaluation-snapshot-join", "protocol revision mismatch", path))
    revision = snapshot[_HISTORICAL_REVISION_FIELD]
    if not isinstance(revision, str) or not _SHA_RE.fullmatch(revision):
        failures.append(
            _failure(
                "dsl-evaluation-snapshot-pin",
                "RAES revision must be full Git SHA",
                path,
            )
        )
    if snapshot["execution_status"] not in {"not_started", "in_progress", "complete"}:
        failures.append(_failure("dsl-evaluation-snapshot-status", "invalid execution status", path))

    surfaces = _bounded_list(
        snapshot["public_surface"],
        _MAX_CATALOG_ITEMS,
        failures,
        rule_id="dsl-evaluation-snapshot-shape",
        label="public_surface",
        path=path,
    )
    _record_ids(
        surfaces,
        "surface_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="public surface",
        path=path,
    )
    for index, surface in enumerate(surfaces):
        if not _exact_keys(
            surface,
            _SURFACE_KEYS,
            failures,
            rule_id="dsl-evaluation-snapshot-shape",
            label=f"public_surface[{index}]",
            path=path,
        ):
            continue
        artifact = surface["artifact"]
        resolved = _resolve_repository_artifact(repo_root, artifact) if isinstance(artifact, str) else None
        if resolved is None or not resolved.exists():
            failures.append(
                _failure(
                    "dsl-evaluation-public-surface-path",
                    f"{surface['surface_id']}: unsafe or missing artifact",
                    path,
                )
            )
    _exact_keys(
        snapshot["ethics_review"],
        _ETHICS_REVIEW_KEYS,
        failures,
        rule_id="dsl-evaluation-snapshot-shape",
        label="ethics_review",
        path=path,
    )

    record_fields = {
        "subjects": _SUBJECT_KEYS,
        "attempts": _ATTEMPT_KEYS,
        "observations": _OBSERVATION_KEYS,
        "reviews": _REVIEW_KEYS,
        "deviations": _DEVIATION_KEYS,
        "withdrawals": _WITHDRAWAL_KEYS,
        "disagreements": _DISAGREEMENT_KEYS,
    }
    records: dict[str, list[object]] = {}
    for field, keys in record_fields.items():
        records[field] = _bounded_list(
            snapshot[field],
            _MAX_EXECUTION_RECORDS,
            failures,
            rule_id="dsl-evaluation-snapshot-shape",
            label=field,
            path=path,
        )
        for index, record in enumerate(records[field]):
            _exact_keys(
                record,
                keys,
                failures,
                rule_id="dsl-evaluation-snapshot-shape",
                label=f"{field}[{index}]",
                path=path,
            )
    if snapshot["execution_status"] == "not_started":
        populated = sorted(field for field, value in records.items() if value)
        if populated:
            failures.append(
                _failure(
                    "dsl-evaluation-not-started-observations",
                    f"not-started snapshot contains execution records: {populated}",
                    path,
                )
            )
        ethics = snapshot["ethics_review"]
        if isinstance(ethics, Mapping) and ethics.get("status") not in {
            "pending",
            "not_required",
        }:
            failures.append(
                _failure(
                    "dsl-evaluation-ethics-state",
                    "not-started snapshot must remain pending or explicitly not-required",
                    path,
                )
            )
        return set()

    subjects = records["subjects"]
    attempts = records["attempts"]
    observations = records["observations"]
    reviews = records["reviews"]
    withdrawals = records["withdrawals"]
    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    variants = _protocol_records_by_id(protocol, "variants", "variant_id")
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")

    _record_ids(
        subjects,
        "subject_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="subject",
        path=path,
    )
    attempt_ids = _record_ids(
        attempts,
        "attempt_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="attempt",
        path=path,
    )
    observation_ids = _record_ids(
        observations,
        "observation_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="observation",
        path=path,
    )
    review_ids = _record_ids(
        reviews,
        "review_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="review",
        path=path,
    )
    withdrawal_subject_ids = _record_ids(
        withdrawals,
        "subject_id",
        failures,
        rule_id="dsl-evaluation-snapshot-id",
        label="withdrawal",
        path=path,
    )

    subjects_by_id, withdrawal_subject_ids = _subject_failures(
        protocol, catalogs, subjects, withdrawals, withdrawal_subject_ids, failures, path
    )

    attempts_by_id: dict[str, Mapping[str, object]] = {}
    for attempt in attempts:
        if not isinstance(attempt, Mapping) or set(attempt) != _ATTEMPT_KEYS:
            continue
        attempt_id = attempt.get("attempt_id")
        if not isinstance(attempt_id, str):
            continue
        attempts_by_id[attempt_id] = attempt
        task_id = attempt.get("task_id")
        task = tasks.get(task_id) if isinstance(task_id, str) else None
        subject_id = attempt.get("subject_id")
        subject = subjects_by_id.get(subject_id) if isinstance(subject_id, str) else None
        outcome = attempt.get("outcome")
        if outcome not in ATTEMPT_OUTCOMES:
            failures.append(_failure("dsl-evaluation-attempt-outcome", f"{attempt_id}: invalid outcome", path))
        if task is None or subject is None:
            failures.append(_failure("dsl-evaluation-attempt-join", f"{attempt_id}: unknown task or subject", path))
            continue
        task_personas = _string_list(task.get("persona_ids"), non_empty=True) or []
        task_conditions = _string_list(task.get("tooling_condition_ids"), non_empty=True) or []
        task_variants = _string_list(task.get("variant_ids"), non_empty=True) or []
        if (
            attempt.get("persona_id") != subject.get("persona_id")
            or attempt.get("persona_id") not in task_personas
            or attempt.get("tooling_condition_id") not in task_conditions
            or attempt.get("variant_id") not in task_variants
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-attempt-join",
                    f"{attempt_id}: subject, persona, task, condition, or variant mismatch",
                    path,
                )
            )
        variant = variants.get(attempt.get("variant_id"))
        if variant is None or variant.get("task_id") != task_id:
            failures.append(
                _failure("dsl-evaluation-attempt-join", f"{attempt_id}: variant belongs to another task", path)
            )
        withdrawn = subject_id in withdrawal_subject_ids
        if withdrawn != (outcome == "withdrawn"):
            failures.append(
                _failure(
                    "dsl-evaluation-withdrawal-join",
                    f"{attempt_id}: withdrawn subject and attempt outcome disagree",
                    path,
                )
            )
        if not _valid_id(attempt.get("study_run_id")):
            failures.append(_failure("dsl-evaluation-attempt-identity", f"{attempt_id}: invalid study run id", path))
        if not _bounded_text(attempt.get("started_at"), maximum=100) or not _bounded_text(
            attempt.get("ended_at"), maximum=100
        ):
            failures.append(_failure("dsl-evaluation-attempt-identity", f"{attempt_id}: timestamps must be text", path))
        if _string_list(attempt.get("observation_ids")) is None:
            failures.append(
                _failure("dsl-evaluation-attempt-observation-join", f"{attempt_id}: invalid observation ids", path)
            )

    observations_by_opportunity: dict[tuple[str, str, str], Mapping[str, object]] = {}
    child_observations: dict[str, set[str]] = {attempt_id: set() for attempt_id in attempt_ids}
    for observation in observations:
        if not isinstance(observation, Mapping) or set(observation) != _OBSERVATION_KEYS:
            continue
        observation_id = observation.get("observation_id")
        attempt_id = observation.get("attempt_id")
        measure_id = observation.get("measure_id")
        artifact_stage = observation.get("artifact_stage")
        if (
            not isinstance(observation_id, str)
            or not isinstance(attempt_id, str)
            or not isinstance(measure_id, str)
            or not isinstance(artifact_stage, str)
        ):
            failures.append(
                _failure("dsl-evaluation-observation-identity", "observation identity fields must be text", path)
            )
            continue
        opportunity = (attempt_id, measure_id, artifact_stage)
        observation_dimensions = _string_list(observation.get("dimension_ids"), non_empty=True)
        if opportunity in observations_by_opportunity:
            failures.append(
                _failure(
                    "dsl-evaluation-observation-identity",
                    f"duplicate attempt-measure-stage observation at {observation_id}",
                    path,
                )
            )
        observations_by_opportunity[opportunity] = observation
        child_observations.setdefault(attempt_id, set()).add(observation_id)
        attempt = attempts_by_id.get(attempt_id)
        measure = measures.get(measure_id)
        task = tasks.get(observation.get("task_id"))
        if attempt is None or measure is None or task is None:
            failures.append(
                _failure(
                    "dsl-evaluation-observation-join",
                    f"{observation_id}: unknown parent attempt, task, or measure",
                    path,
                )
            )
            continue
        parent_fields = (
            "study_run_id",
            "task_id",
            "persona_id",
            "subject_id",
            "tooling_condition_id",
            "variant_id",
            "outcome",
        )
        if observation.get("protocol_revision") != protocol.get("revision") or any(
            observation.get(field) != attempt.get(field) for field in parent_fields
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-observation-parent-join",
                    f"{observation_id}: observation does not match its parent attempt",
                    path,
                )
            )
        task_stages = _string_list(task.get("artifact_stage_ids"), non_empty=True) or []
        measure_tasks = _string_list(measure.get("task_ids"), non_empty=True) or []
        task_dimensions = set(_string_list(task.get("dimension_ids"), non_empty=True) or [])
        measure_dimensions = set(_string_list(measure.get("dimension_ids"), non_empty=True) or [])
        expected_dimensions = task_dimensions & measure_dimensions
        parent_task_id = attempt.get("task_id")
        parent_variant_id = attempt.get("variant_id")
        try:
            applicable_stages = (
                _measure_stage_ids(measure, parent_task_id, parent_variant_id)
                if isinstance(parent_task_id, str) and isinstance(parent_variant_id, str)
                else []
            )
        except ValueError:
            applicable_stages = []
        if (
            artifact_stage not in task_stages
            or artifact_stage not in applicable_stages
            or observation.get("task_id") not in measure_tasks
            or observation_dimensions is None
            or set(observation_dimensions) != expected_dimensions
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-observation-task-join",
                    f"{observation_id}: stage, measure, or dimensions are not declared for the task",
                    path,
                )
            )
        outcome = observation.get("outcome")
        value = observation.get("value")
        if outcome not in OBSERVATION_OUTCOMES:
            failures.append(_failure("dsl-evaluation-observation-outcome", f"{observation_id}: invalid outcome", path))
        if measure_id == "task-completion":
            expected_value = 1 if outcome == "completed" else 0
            valid_value = value == expected_value and not isinstance(value, bool)
        elif outcome in {"completed", "failed"}:
            valid_value = not isinstance(value, bool) and isinstance(value, (int, float))
        else:
            valid_value = value is None
        if not valid_value:
            failures.append(
                _failure(
                    "dsl-evaluation-observation-value",
                    f"{observation_id}: value does not represent its attempt outcome",
                    path,
                )
            )
        refs = _string_list(observation.get("evidence_refs"))
        if refs is None or any(safe_repo_path(repo_root, ref) is None for ref in refs):
            failures.append(
                _failure(
                    "dsl-evaluation-observation-evidence",
                    f"{observation_id}: evidence refs must be repository-confined paths",
                    path,
                )
            )

    expected_opportunities: set[tuple[str, str, str]] = set()
    withdrawn_opportunities: set[tuple[str, str, str]] = set()
    for attempt_id, attempt in attempts_by_id.items():
        task_id = attempt.get("task_id")
        variant_id = attempt.get("variant_id")
        for measure_id, measure in measures.items():
            measure_tasks = _string_list(measure.get("task_ids"), non_empty=True) or []
            if task_id not in measure_tasks or not isinstance(task_id, str) or not isinstance(variant_id, str):
                continue
            try:
                applicable_stages = _measure_stage_ids(measure, task_id, variant_id)
            except ValueError:
                continue
            for artifact_stage in applicable_stages:
                opportunity = (attempt_id, measure_id, artifact_stage)
                if attempt.get("outcome") == "withdrawn":
                    withdrawn_opportunities.add(opportunity)
                else:
                    expected_opportunities.add(opportunity)
    actual_opportunities = set(observations_by_opportunity)
    if actual_opportunities != expected_opportunities or actual_opportunities & withdrawn_opportunities:
        failures.append(
            _failure(
                "dsl-evaluation-opportunity-coverage",
                "observations must exactly cover every non-withdrawn protocol-declared attempt-measure-stage opportunity",
                path,
            )
        )
    for attempt_id, attempt in attempts_by_id.items():
        stored_ids = _string_list(attempt.get("observation_ids"))
        if stored_ids is not None and set(stored_ids) != child_observations.get(attempt_id, set()):
            failures.append(
                _failure(
                    "dsl-evaluation-attempt-observation-join",
                    f"{attempt_id}: observation ids do not match child records",
                    path,
                )
            )

    _review_and_completion_failures(
        protocol,
        snapshot,
        scope,
        _SnapshotJoins(
            subjects_by_id=subjects_by_id,
            attempts_by_id=attempts_by_id,
            tasks=tasks,
            review_ids=review_ids,
            reviews=reviews,
            disagreements=records["disagreements"],
            withdrawal_subject_ids=withdrawal_subject_ids,
        ),
        failures,
        path,
    )
    return observation_ids
