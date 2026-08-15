"""Review joins and completion-coverage validation for the execution snapshot."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from tools.dsl_language_evaluation._claims import _attempt_matches_scope
from tools.dsl_language_evaluation._keys import (
    _DISAGREEMENT_KEYS,
    _REVIEW_KEYS,
    _SUBJECT_KEYS,
    _WITHDRAWAL_KEYS,
)
from tools.dsl_language_evaluation._shape import (
    _bounded_text,
    _failure,
    _string_list,
    _valid_id,
)
from tools.policy.common import PolicyFailure


@dataclass(frozen=True)
class _SnapshotJoins:
    """Joined execution-record indexes shared by review and completion checks."""

    subjects_by_id: Mapping[str, Mapping[str, object]]
    attempts_by_id: Mapping[str, Mapping[str, object]]
    tasks: Mapping[str, Mapping[str, object]]
    review_ids: set[str]
    reviews: list[object]
    disagreements: list[object]
    withdrawal_subject_ids: set[str]


def _subject_record_failures(
    subjects_by_id: Mapping[str, Mapping[str, object]],
    catalogs: Mapping[str, set[str]],
    experience_bands: set[str],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    for subject_id, subject in subjects_by_id.items():
        if subject.get("persona_id") not in catalogs.get("persona_ids", set()):
            failures.append(_failure("dsl-evaluation-subject-join", f"{subject_id}: unknown persona", path))
        if subject.get("consent_status") not in {"consented", "withdrawn"}:
            failures.append(_failure("dsl-evaluation-consent-status", f"{subject_id}: invalid consent status", path))
        if (
            not _bounded_text(subject.get("experience_band"), maximum=200)
            or subject.get("experience_band") not in experience_bands
        ):
            failures.append(_failure("dsl-evaluation-subject-shape", f"{subject_id}: invalid experience band", path))


def _withdrawal_shape_failures(
    withdrawals: list[object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    for withdrawal in withdrawals:
        if not isinstance(withdrawal, Mapping) or set(withdrawal) != _WITHDRAWAL_KEYS:
            continue
        if (
            not _bounded_text(withdrawal.get("recorded_at"), maximum=100)
            or withdrawal.get("retained_aggregate_only") is not True
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-withdrawal-shape",
                    f"{withdrawal.get('subject_id')}: withdrawal must retain aggregate counts only",
                    path,
                )
            )


def _subject_failures(
    protocol: Mapping[str, object],
    catalogs: Mapping[str, set[str]],
    subjects: list[object],
    withdrawals: list[object],
    withdrawal_subject_ids: set[str],
    failures: list[PolicyFailure],
    path: str,
) -> tuple[dict[str, Mapping[str, object]], set[str]]:
    subjects_by_id = {
        subject["subject_id"]: subject
        for subject in subjects
        if isinstance(subject, Mapping) and set(subject) == _SUBJECT_KEYS and isinstance(subject.get("subject_id"), str)
    }
    sampling_plan = protocol.get("sampling_plan")
    experience_bands = set()
    if isinstance(sampling_plan, Mapping):
        experience_bands = set(_string_list(sampling_plan.get("experience_bands"), non_empty=True) or [])
    _subject_record_failures(subjects_by_id, catalogs, experience_bands, failures, path)
    declared_withdrawn_subjects = {
        subject_id for subject_id, subject in subjects_by_id.items() if subject.get("consent_status") == "withdrawn"
    }
    if withdrawal_subject_ids != declared_withdrawn_subjects:
        failures.append(
            _failure(
                "dsl-evaluation-withdrawal-join",
                "withdrawal records must exactly match subjects with withdrawn consent",
                path,
            )
        )
    _withdrawal_shape_failures(withdrawals, failures, path)
    return subjects_by_id, withdrawal_subject_ids


def _review_join_failures(
    review: Mapping[str, object],
    attempt: Mapping[str, object],
    reviewer: Mapping[str, object],
    tasks: Mapping[str, Mapping[str, object]],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    review_id = review.get("review_id")
    reviewer_id = review.get("reviewer_subject_id")
    task = tasks.get(attempt.get("task_id"))
    task_stages = _string_list(task.get("artifact_stage_ids"), non_empty=True) if task else None
    task_personas = _string_list(task.get("persona_ids"), non_empty=True) if task else None
    if (
        review.get("task_id") != attempt.get("task_id")
        or review.get("variant_id") != attempt.get("variant_id")
        or reviewer_id == attempt.get("subject_id")
        or reviewer.get("consent_status") != "consented"
        or task_stages is None
        or "review-judgment" not in task_stages
        or task_personas is None
        or reviewer.get("persona_id") not in task_personas
    ):
        failures.append(
            _failure(
                "dsl-evaluation-review-join",
                f"{review_id}: review does not match an eligible independent reviewer and parent task",
                path,
            )
        )


def _review_shape_failures(
    review: Mapping[str, object],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    if (
        not _bounded_text(review.get("judgment"), maximum=500)
        or isinstance(review.get("confidence"), bool)
        or not isinstance(review.get("confidence"), (int, float))
        or not 0 <= review["confidence"] <= 1
        or not _valid_id(review.get("rationale_code"))
        or not _bounded_text(review.get("fixed_at"), maximum=100)
    ):
        failures.append(
            _failure("dsl-evaluation-review-shape", f"{review.get('review_id')}: invalid fixed judgment", path)
        )


def _review_failures(
    joins: _SnapshotJoins,
    failures: list[PolicyFailure],
    path: str,
) -> Counter[str]:
    reviews_by_attempt: Counter[str] = Counter()
    for review in joins.reviews:
        if not isinstance(review, Mapping) or set(review) != _REVIEW_KEYS:
            continue
        review_id = review.get("review_id")
        attempt_id = review.get("attempt_id")
        attempt = joins.attempts_by_id.get(attempt_id) if isinstance(attempt_id, str) else None
        reviewer_id = review.get("reviewer_subject_id")
        reviewer = joins.subjects_by_id.get(reviewer_id) if isinstance(reviewer_id, str) else None
        if attempt is None or reviewer is None:
            failures.append(_failure("dsl-evaluation-review-join", f"{review_id}: unknown attempt or reviewer", path))
            continue
        _review_join_failures(review, attempt, reviewer, joins.tasks, failures, path)
        _review_shape_failures(review, failures, path)
        reviews_by_attempt[attempt_id] += 1
    return reviews_by_attempt


def _disagreement_failures(
    joins: _SnapshotJoins,
    failures: list[PolicyFailure],
    path: str,
) -> None:
    for disagreement in joins.disagreements:
        if not isinstance(disagreement, Mapping) or set(disagreement) != _DISAGREEMENT_KEYS:
            continue
        disagreement_review_ids = _string_list(disagreement["review_ids"], non_empty=True)
        linked_reviews = [
            review
            for review in joins.reviews
            if isinstance(review, Mapping)
            and disagreement_review_ids is not None
            and review.get("review_id") in disagreement_review_ids
        ]
        linked_attempts = {review.get("attempt_id") for review in linked_reviews}
        if (
            disagreement_review_ids is None
            or len(disagreement_review_ids) < 2
            or not set(disagreement_review_ids).issubset(joins.review_ids)
            or len(linked_attempts) != 1
        ):
            failures.append(
                _failure(
                    "dsl-evaluation-disagreement-join",
                    f"{disagreement['disagreement_id']}: reviews must share one parent attempt",
                    path,
                )
            )
        if disagreement["originals_preserved"] is not True:
            failures.append(
                _failure(
                    "dsl-evaluation-disagreement-preservation",
                    f"{disagreement['disagreement_id']}: originals must be preserved",
                    path,
                )
            )


def _scoped_subject_ids(
    subjects_by_id: Mapping[str, Mapping[str, object]],
    attempts_by_id: Mapping[str, Mapping[str, object]],
    scope: Mapping[str, set[str]],
) -> tuple[set[str], set[str]]:
    nonwithdrawn_subject_ids = {
        subject_id
        for subject_id, subject in subjects_by_id.items()
        if subject.get("consent_status") == "consented" and subject.get("persona_id") in scope.get("persona_ids", set())
    }
    active_subject_ids = {
        subject_id
        for subject_id in nonwithdrawn_subject_ids
        if any(
            attempt.get("subject_id") == subject_id
            and attempt.get("outcome") != "withdrawn"
            and _attempt_matches_scope(attempt, scope)
            for attempt in attempts_by_id.values()
        )
    }
    return nonwithdrawn_subject_ids, active_subject_ids


def _missing_personas(
    protocol: Mapping[str, object],
    scope: Mapping[str, set[str]],
    subjects_by_id: Mapping[str, Mapping[str, object]],
    active_subject_ids: set[str],
) -> list[str]:
    persona_minimums = {
        item["persona_id"]: item["minimum_completed_subjects"]
        for item in protocol.get("personas", [])
        if isinstance(item, Mapping)
        and isinstance(item.get("persona_id"), str)
        and isinstance(item.get("minimum_completed_subjects"), int)
        and item["persona_id"] in scope.get("persona_ids", set())
    }
    persona_counts = Counter(subjects_by_id[subject_id]["persona_id"] for subject_id in active_subject_ids)
    return sorted(
        persona_id for persona_id, minimum in persona_minimums.items() if persona_counts[persona_id] < minimum
    )


def _task_shape_coverage(
    tasks: Mapping[str, Mapping[str, object]],
    attempts_by_id: Mapping[str, Mapping[str, object]],
    scope: Mapping[str, set[str]],
) -> tuple[set[tuple[object, object, object]], set[tuple[object, object, object]]]:
    expected_task_shapes = {
        (task["task_id"], condition_id, variant_id)
        for task in tasks.values()
        if task["task_id"] in scope.get("task_ids", set())
        for condition_id in (_string_list(task.get("tooling_condition_ids"), non_empty=True) or [])
        if condition_id in scope.get("tooling_condition_ids", set())
        for variant_id in (_string_list(task.get("variant_ids"), non_empty=True) or [])
        if variant_id in scope.get("variant_ids", set())
    }
    actual_task_shapes = {
        (attempt.get("task_id"), attempt.get("tooling_condition_id"), attempt.get("variant_id"))
        for attempt in attempts_by_id.values()
        if attempt.get("outcome") != "withdrawn" and _attempt_matches_scope(attempt, scope)
    }
    return expected_task_shapes, actual_task_shapes


def _review_required_attempts(
    attempts_by_id: Mapping[str, Mapping[str, object]],
    tasks: Mapping[str, Mapping[str, object]],
    scope: Mapping[str, set[str]],
) -> set[str]:
    return {
        attempt_id
        for attempt_id, attempt in attempts_by_id.items()
        if _attempt_matches_scope(attempt, scope)
        if "review-judgment"
        in (_string_list(tasks.get(attempt.get("task_id"), {}).get("artifact_stage_ids"), non_empty=True) or [])
        and attempt.get("outcome") != "withdrawn"
    }


def _requirement_gap(
    requirement: object,
    subject_attempts: list[Mapping[str, object]],
    tasks: Mapping[str, Mapping[str, object]],
) -> str | None:
    if not isinstance(requirement, Mapping):
        return None
    task_kind_values = _string_list(requirement.get("task_kinds"), non_empty=True)
    minimum = requirement.get("minimum_assigned_attempts")
    requirement_id = requirement.get("requirement_id")
    if (
        task_kind_values is None
        or not isinstance(minimum, int)
        or isinstance(minimum, bool)
        or not isinstance(requirement_id, str)
    ):
        return None
    assigned = sum(
        tasks.get(attempt.get("task_id"), {}).get("kind") in task_kind_values for attempt in subject_attempts
    )
    return requirement_id if assigned < minimum else None


def _missing_subject_workloads(
    protocol: Mapping[str, object],
    joins: _SnapshotJoins,
    scope: Mapping[str, set[str]],
    nonwithdrawn_subject_ids: set[str],
) -> list[tuple[str, str]]:
    execution_plan = protocol.get("execution_plan", {})
    subject_task_requirements = (
        execution_plan.get("subject_task_requirements", []) if isinstance(execution_plan, Mapping) else []
    )
    if not isinstance(subject_task_requirements, list):
        return []
    missing_subject_workloads: list[tuple[str, str]] = []
    for subject_id in nonwithdrawn_subject_ids:
        subject_attempts = [
            attempt
            for attempt in joins.attempts_by_id.values()
            if attempt.get("subject_id") == subject_id
            and attempt.get("outcome") != "withdrawn"
            and _attempt_matches_scope(attempt, scope)
        ]
        for requirement in subject_task_requirements:
            gap = _requirement_gap(requirement, subject_attempts, joins.tasks)
            if gap is not None:
                missing_subject_workloads.append((subject_id, gap))
    return missing_subject_workloads


def _completion_failures(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    scope: Mapping[str, set[str]],
    joins: _SnapshotJoins,
    reviews_by_attempt: Counter[str],
    failures: list[PolicyFailure],
    path: str,
) -> None:
    nonwithdrawn_subject_ids, active_subject_ids = _scoped_subject_ids(
        joins.subjects_by_id, joins.attempts_by_id, scope
    )
    missing_personas = _missing_personas(protocol, scope, joins.subjects_by_id, active_subject_ids)
    expected_task_shapes, actual_task_shapes = _task_shape_coverage(joins.tasks, joins.attempts_by_id, scope)
    review_required_attempts = _review_required_attempts(joins.attempts_by_id, joins.tasks, scope)
    sampling_plan = protocol.get("sampling_plan", {})
    target_total = sampling_plan.get("target_total") if isinstance(sampling_plan, Mapping) else None
    ethics = snapshot["ethics_review"]
    ethics_approved = isinstance(ethics, Mapping) and ethics.get("status") == "approved"
    missing_subject_workloads = _missing_subject_workloads(protocol, joins, scope, nonwithdrawn_subject_ids)
    if missing_subject_workloads:
        failures.append(
            _failure(
                "dsl-evaluation-subject-workload",
                "complete execution does not satisfy every active subject's assigned task groups",
                path,
            )
        )
    if (
        not ethics_approved
        or missing_personas
        or not isinstance(target_total, int)
        or len(active_subject_ids) < target_total
        or not expected_task_shapes.issubset(actual_task_shapes)
        or any(reviews_by_attempt[attempt_id] == 0 for attempt_id in review_required_attempts)
        or missing_subject_workloads
    ):
        failures.append(
            _failure(
                "dsl-evaluation-completion-coverage",
                "complete execution lacks approved ethics, subject workload/minima, task/condition/variant coverage, or required independent reviews",
                path,
            )
        )


def _review_and_completion_failures(
    protocol: Mapping[str, object],
    snapshot: Mapping[str, object],
    scope: Mapping[str, set[str]],
    joins: _SnapshotJoins,
    failures: list[PolicyFailure],
    path: str,
) -> None:
    reviews_by_attempt = _review_failures(joins, failures, path)
    _disagreement_failures(joins, failures, path)
    if snapshot["execution_status"] == "complete":
        _completion_failures(protocol, snapshot, scope, joins, reviews_by_attempt, failures, path)
