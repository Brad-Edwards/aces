"""Integrity tests for the formal semantic-validation evidence bundle."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from tools.check_formal_semantic_validation import (
    REQUIRED_CLAIM_CLASS_IDS,
    REQUIRED_PARTICIPANT_OBLIGATION_IDS,
    evaluate,
    load_bundle,
    load_satisfiability_analysis,
    validate_bundle,
    validate_satisfiability_analysis,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _rule_ids(failures: list[object]) -> set[str]:
    return {failure.rule_id for failure in failures}


def _bundle() -> tuple[dict, dict, dict, dict, dict]:
    return tuple(deepcopy(item) for item in load_bundle(REPO_ROOT))  # type: ignore[return-value]


def test_protocol_keeps_all_literature_claim_classes_distinct() -> None:
    _, protocol, _, _, _ = _bundle()

    assert {item["claim_class_id"] for item in protocol["claim_classes"]} == REQUIRED_CLAIM_CLASS_IDS


def test_gate_requires_positive_and_negative_cases_for_every_claim_class() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    corpus["cases"] = [
        case
        for case in corpus["cases"]
        if not (case["claim_class_id"] == "graph-reachability" and case["polarity"] == "negative")
    ]

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-case-polarity" in _rule_ids(failures)


def test_gate_rejects_dangling_case_observations() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    snapshot["observations"][0]["case_id"] = "missing-case"

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-observation-case" in _rule_ids(failures)


def test_gate_rejects_unsafe_fixture_paths() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    case = next(item for item in corpus["cases"] if item["fixture_path"] is not None)
    case["fixture_path"] = "../outside.sdl.yaml"

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-case-path" in _rule_ids(failures)


def test_gate_rejects_observations_that_drift_from_executable_cases() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    observation = next(item for item in snapshot["observations"] if item["replayable"])
    observation["actual_outcome"] = "unexpected-outcome"

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-replay-drift" in _rule_ids(failures)


def test_gate_rejects_promotion_of_unsupported_solver_level_claims() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    result = next(item for item in analysis["claim_results"] if item["claim_class_id"] == "exploit-path-validity")
    result["evidence_status"] = "demonstrated"

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-unsupported-overclaim" in _rule_ids(failures)


def test_gate_requires_every_participant_semantics_obligation() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    protocol["participant_obligations"] = protocol["participant_obligations"][:-1]

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-participant-coverage" in _rule_ids(failures)
    assert {
        item["obligation_id"] for item in protocol["participant_obligations"]
    } != REQUIRED_PARTICIPANT_OBLIGATION_IDS


def test_gate_requires_positive_and_negative_participant_fixture_refs() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    protocol["participant_obligations"][0]["negative_test_ref"] = protocol["participant_obligations"][0][
        "positive_test_ref"
    ]

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-participant-fixtures" in _rule_ids(failures)


def test_gate_binds_participant_observations_to_the_declared_test_refs() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    snapshot["participant_observations"][0]["evidence_refs"].reverse()

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-participant-observation-evidence" in _rule_ids(failures)


def test_gate_replays_participant_tests_instead_of_trusting_pass_labels() -> None:
    def failed_replay(_repo_root: Path, _test_refs: list[str]) -> tuple[bool, str]:
        return False, "seeded participant fixture failure"

    failures = evaluate(REPO_ROOT, participant_test_runner=failed_replay)

    assert "formal-validation-participant-replay" in _rule_ids(failures)


def test_gate_recomputes_claim_statuses_from_frozen_observations() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    result = next(item for item in analysis["claim_results"] if item["claim_class_id"] == "schema-validity")
    result["evidence_status"] = "untested"

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-analysis-drift" in _rule_ids(failures)


def test_gate_rejects_mutable_or_unpinned_aces_revision() -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    snapshot["aces_revision"] = "dev"

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert "formal-validation-revision-pin" in _rule_ids(failures)


@pytest.mark.parametrize(
    ("artifact_name", "target_path", "expected_rule"),
    [
        ("manifest", (), "formal-validation-manifest-shape"),
        ("protocol", (), "formal-validation-protocol-shape"),
        ("protocol", ("analysis_rules",), "formal-validation-analysis-rules"),
        ("protocol", ("claim_classes", 0), "formal-validation-claim-shape"),
        ("protocol", ("participant_obligations", 0), "formal-validation-participant-shape"),
        ("corpus", (), "formal-validation-corpus-shape"),
        ("corpus", ("cases", 0), "formal-validation-case-shape"),
        ("snapshot", (), "formal-validation-snapshot-shape"),
        ("snapshot", ("commands", 0), "formal-validation-command-shape"),
        ("snapshot", ("observations", 0), "formal-validation-observation-shape"),
        (
            "snapshot",
            ("participant_observations", 0),
            "formal-validation-participant-observation-shape",
        ),
        ("analysis", (), "formal-validation-analysis-shape"),
        ("analysis", ("claim_results", 0), "formal-validation-claim-result-shape"),
        ("analysis", ("claim",), "formal-validation-claim-record"),
    ],
)
def test_gate_rejects_unknown_fields_at_every_closed_artifact_boundary(
    artifact_name: str,
    target_path: tuple[str | int, ...],
    expected_rule: str,
) -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    artifacts = {
        "manifest": manifest,
        "protocol": protocol,
        "corpus": corpus,
        "snapshot": snapshot,
        "analysis": analysis,
    }
    target = artifacts[artifact_name]
    for key in target_path:
        target = target[key]
    target["unexpected_field"] = True

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert expected_rule in _rule_ids(failures)


@pytest.mark.parametrize(
    ("artifact_name", "target_path", "replacement", "expected_rule"),
    [
        ("protocol", ("issue_number",), 999, "formal-validation-protocol-scope"),
        ("protocol", ("evidence_status_values",), [], "formal-validation-evidence-status"),
        ("protocol", ("claim_classes",), [], "formal-validation-claim-coverage"),
        (
            "protocol",
            ("claim_classes", 0, "expected_evidence_status"),
            "unsupported",
            "formal-validation-evidence-status",
        ),
        ("protocol", ("claim_classes", 0, "allowed_evidence"), [], "formal-validation-claim-evidence"),
        ("corpus", ("cases",), [], "formal-validation-case-count"),
        ("corpus", ("cases", 0, "claim_class_id"), "unknown-class", "formal-validation-case-claim"),
        ("corpus", ("cases", 0, "replay_mode"), "unknown-mode", "formal-validation-replay-mode"),
        ("corpus", ("cases", 0, "limitation"), "", "formal-validation-case-limit"),
        ("snapshot", ("protocol_revision",), "wrong-revision", "formal-validation-snapshot-revision"),
        ("snapshot", ("execution_status",), "incomplete", "formal-validation-execution-status"),
        ("snapshot", ("commands",), [], "formal-validation-commands"),
        ("snapshot", ("commands", 0, "network"), "enabled", "formal-validation-commands"),
        ("snapshot", ("commands", 1, "argv"), [], "formal-validation-participant-command"),
        ("snapshot", ("observations",), [], "formal-validation-observation-coverage"),
        ("snapshot", ("observations", 0, "execution_id"), "wrong-execution", "formal-validation-observation-join"),
        ("snapshot", ("observations", 0, "replayable"), False, "formal-validation-observation-replayable"),
        ("snapshot", ("observations", 0, "evidence_refs"), [], "formal-validation-observation-evidence"),
        (
            "snapshot",
            ("participant_observations",),
            [],
            "formal-validation-participant-observation-coverage",
        ),
        (
            "snapshot",
            ("participant_observations", 0, "execution_id"),
            "wrong-execution",
            "formal-validation-participant-observation-join",
        ),
        (
            "snapshot",
            ("participant_observations", 0, "positive_outcome"),
            "failed",
            "formal-validation-participant-result",
        ),
        (
            "snapshot",
            ("participant_observations", 0, "limitations"),
            [],
            "formal-validation-participant-observation-evidence",
        ),
        ("analysis", ("protocol_revision",), "wrong-revision", "formal-validation-analysis-join"),
        ("analysis", ("claim_results",), [], "formal-validation-analysis-result-coverage"),
        ("analysis", ("claim_results", 0, "limitations"), [], "formal-validation-claim-limitations"),
        ("analysis", ("claim", "evidence_artifacts"), ["../unsafe"], "formal-validation-claim-artifact"),
        ("analysis", ("claim", "threats_to_validity"), [], "formal-validation-claim-record"),
        ("analysis", ("limitations",), [], "formal-validation-analysis-disclosure"),
    ],
)
def test_gate_rejects_mutations_of_every_semantic_integrity_rule_family(
    artifact_name: str,
    target_path: tuple[str | int, ...],
    replacement: object,
    expected_rule: str,
) -> None:
    manifest, protocol, corpus, snapshot, analysis = _bundle()
    artifacts = {
        "protocol": protocol,
        "corpus": corpus,
        "snapshot": snapshot,
        "analysis": analysis,
    }
    target = artifacts[artifact_name]
    for key in target_path[:-1]:
        target = target[key]
    target[target_path[-1]] = replacement

    failures = validate_bundle(REPO_ROOT, manifest, protocol, corpus, snapshot, analysis)

    assert expected_rule in _rule_ids(failures)


def test_satisfiability_supplement_has_complete_replayable_control_matrix() -> None:
    manifest, snapshot, analysis = load_satisfiability_analysis(REPO_ROOT)

    assert manifest["revision"] == "2.0.0"
    assert analysis["evidence_status"] == "demonstrated"
    assert {item["control"] for item in analysis["cases"]} == {
        "positive",
        "negative",
        "unsupported",
    }
    assert analysis["execution_id"] == snapshot["execution_id"]
    assert validate_satisfiability_analysis(REPO_ROOT, manifest, snapshot, analysis) == []


def test_satisfiability_gate_rejects_missing_unsupported_control() -> None:
    manifest, snapshot, analysis = load_satisfiability_analysis(REPO_ROOT)
    analysis = deepcopy(analysis)
    analysis["cases"] = [item for item in analysis["cases"] if item["control"] != "unsupported"]

    failures = validate_satisfiability_analysis(REPO_ROOT, manifest, snapshot, analysis)

    assert "formal-satisfiability-control-coverage" in _rule_ids(failures)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("expected_outcome", "satisfiable"),
        (
            "expected_normalized_model_digest",
            "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        ),
    ],
)
def test_satisfiability_gate_rejects_mutated_frozen_observations(
    field: str,
    replacement: str,
) -> None:
    manifest, snapshot, analysis = load_satisfiability_analysis(REPO_ROOT)
    analysis = deepcopy(analysis)
    unsupported = next(item for item in analysis["cases"] if item["control"] == "unsupported")
    unsupported[field] = replacement

    failures = validate_satisfiability_analysis(REPO_ROOT, manifest, snapshot, analysis)

    assert "formal-satisfiability-replay-drift" in _rule_ids(failures)


def test_satisfiability_gate_rejects_unsafe_fixture_and_unknown_fields() -> None:
    manifest, snapshot, analysis = load_satisfiability_analysis(REPO_ROOT)
    unsafe = deepcopy(analysis)
    unsafe["cases"][0]["fixture_path"] = "../outside.sdl.yaml"
    unknown = deepcopy(analysis)
    unknown["unexpected"] = True

    assert "formal-satisfiability-case-path" in _rule_ids(
        validate_satisfiability_analysis(REPO_ROOT, manifest, snapshot, unsafe)
    )
    assert "formal-satisfiability-analysis-shape" in _rule_ids(
        validate_satisfiability_analysis(REPO_ROOT, manifest, snapshot, unknown)
    )


def test_satisfiability_gate_rejects_mutated_execution_snapshot() -> None:
    manifest, snapshot, analysis = load_satisfiability_analysis(REPO_ROOT)
    snapshot = deepcopy(snapshot)
    snapshot["observations"][0]["actual_outcome"] = "unsatisfiable"

    failures = validate_satisfiability_analysis(REPO_ROOT, manifest, snapshot, analysis)

    assert "formal-satisfiability-snapshot-drift" in _rule_ids(failures)
