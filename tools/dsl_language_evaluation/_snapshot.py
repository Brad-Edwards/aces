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
)
from tools.dsl_language_evaluation._shape import (
    _bounded_list,
    _exact_keys,
    _failure,
    _protocol_records_by_id,
    _record_ids,
    _resolve_repository_artifact,
)
from tools.dsl_language_evaluation._snapshot_completion import (
    _review_and_completion_failures,
    _SnapshotJoins,
    _subject_failures,
)
from tools.dsl_language_evaluation._snapshot_execution import (
    _attempt_failures,
    _ExecutionJoins,
    _observation_failures,
    _opportunity_coverage_failures,
)
from tools.policy.common import PolicyFailure


def _snapshot_header_failures(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
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


def _public_surface_failures(
    repo_root: Path,
    snapshot: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
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


def _snapshot_records(
    snapshot: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> dict[str, list[object]]:
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
    return records


def _not_started_failures(
    snapshot: Mapping[str, object],
    records: Mapping[str, list[object]],
    failures: list[PolicyFailure],
    path: str,
) -> None:
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


def _execution_record_ids(
    records: Mapping[str, list[object]],
    failures: list[PolicyFailure],
    path: str,
) -> dict[str, set[str]]:
    spec = (
        ("subjects", "subject_id", "subject", "subject_ids"),
        ("attempts", "attempt_id", "attempt", "attempt_ids"),
        ("observations", "observation_id", "observation", "observation_ids"),
        ("reviews", "review_id", "review", "review_ids"),
        ("withdrawals", "subject_id", "withdrawal", "withdrawal_subject_ids"),
    )
    ids: dict[str, set[str]] = {}
    for field, id_field, label, key in spec:
        ids[key] = _record_ids(
            records[field],
            id_field,
            failures,
            rule_id="dsl-evaluation-snapshot-id",
            label=label,
            path=path,
        )
    return ids


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
    _snapshot_header_failures(protocol, snapshot, failures, path)
    _public_surface_failures(repo_root, snapshot, failures, path)
    records = _snapshot_records(snapshot, failures, path)
    if snapshot["execution_status"] == "not_started":
        _not_started_failures(snapshot, records, failures, path)
        return set()

    subjects = records["subjects"]
    attempts = records["attempts"]
    observations = records["observations"]
    reviews = records["reviews"]
    withdrawals = records["withdrawals"]
    tasks = _protocol_records_by_id(protocol, "tasks", "task_id")
    variants = _protocol_records_by_id(protocol, "variants", "variant_id")
    measures = _protocol_records_by_id(protocol, "measures", "measure_id")
    ids = _execution_record_ids(records, failures, path)
    attempt_ids = ids["attempt_ids"]
    observation_ids = ids["observation_ids"]
    review_ids = ids["review_ids"]
    withdrawal_subject_ids = ids["withdrawal_subject_ids"]

    subjects_by_id, withdrawal_subject_ids = _subject_failures(
        protocol, catalogs, subjects, withdrawals, withdrawal_subject_ids, failures, path
    )

    joins = _ExecutionJoins(
        attempts_by_id=_attempt_failures(
            attempts, tasks, variants, subjects_by_id, withdrawal_subject_ids, failures, path
        ),
        attempt_ids=attempt_ids,
        tasks=tasks,
        measures=measures,
    )
    observations_by_opportunity, child_observations = _observation_failures(
        repo_root, protocol, observations, joins, failures, path
    )
    _opportunity_coverage_failures(joins, observations_by_opportunity, child_observations, failures, path)

    _review_and_completion_failures(
        protocol,
        snapshot,
        scope,
        _SnapshotJoins(
            subjects_by_id=subjects_by_id,
            attempts_by_id=joins.attempts_by_id,
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
