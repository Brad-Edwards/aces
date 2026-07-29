"""Structural acceptance gate for issue #810's opacity program."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROGRAM_PATH = REPO_ROOT / "docs/research/participant-opacity/implementation-program.json"
MILESTONE = "Participant Information-Flow & Behavioral Equivalence"

REQUIRED_DELIVERABLES = {
    "docs/decisions/adrs/adr-099-participant-relative-predicate-opacity.md",
    "docs/research/participant-opacity/current-state-assessment.md",
    "docs/research/participant-opacity/prior-art-and-design-criteria.md",
    "docs/research/participant-opacity/requirement-disposition.md",
    "docs/research/participant-opacity/implementation-program.md",
    "specs/formal/participant-semantics/participant-predicate-opacity.md",
}
REQUIRED_REQUIREMENTS = {"SEM-230", "SEM-231", "ASR-535", "RUN-319", "API-407"}
REQUIRED_EXAMPLES = {
    "equal-pair-does-not-prove-opacity",
    "supervisor-decision-leak",
    "opacity-without-noninterference",
    "declassification-changes-knowledge",
}
REQUIRED_ASSURANCE_LANES = {
    "definition",
    "bounded-testing",
    "model-checking",
    "mathematical-proof",
    "runtime-enforcement",
    "backend-declaration",
    "backend-realization",
    "bounded-backend-conformance",
}


def _load_program() -> dict[str, object]:
    return json.loads(PROGRAM_PATH.read_text(encoding="utf-8"))


def test_program_covers_authority_examples_and_assurance_lanes() -> None:
    program = _load_program()

    assert program["schema_version"] == "participant-opacity-program/v1"
    assert program["parent_issue"] == 810
    assert program["milestone"] == MILESTONE
    assert set(program["deliverables"]) >= REQUIRED_DELIVERABLES
    assert all((REPO_ROOT / path).is_file() for path in REQUIRED_DELIVERABLES)

    requirements = {entry["uid"]: entry for entry in program["requirement_dispositions"]}
    assert set(requirements) >= REQUIRED_REQUIREMENTS
    assert requirements["SEM-231"]["disposition"] == "new"
    assert requirements["SEM-231"]["status"] == "DRAFT"
    assert requirements["SEM-230"]["disposition"] == "reuse"
    assert all(entry["scope"] and entry["rationale"] for entry in requirements.values())

    examples = {entry["id"]: entry for entry in program["worked_examples"]}
    assert set(examples) == REQUIRED_EXAMPLES
    assert all(entry["actual_secret_points"] for entry in examples.values())
    assert all(entry["observation_basis"] for entry in examples.values())
    assert all(entry["expected_result"] for entry in examples.values())
    assert all(entry["nonclaim"] for entry in examples.values())

    lanes = {entry["id"]: entry for entry in program["assurance_lanes"]}
    assert set(lanes) == REQUIRED_ASSURANCE_LANES
    assert all(entry["evidence_required"] and entry["does_not_establish"] for entry in lanes.values())


def test_relation_boundaries_and_dimensions_are_explicit() -> None:
    program = _load_program()
    boundaries = {entry["relation_id"]: entry for entry in program["relation_boundaries"]}

    assert {
        "participant-predicate-opacity",
        "policy-noninterference",
        "participant-projected-history-equivalence",
        "epistemic-indistinguishability",
        "trace-equivalence",
        "strong-bisimulation",
    } <= set(boundaries)
    assert boundaries["policy-noninterference"]["conditional_implication"] == (
        "implies opacity for every eligible predicate only under matching profiles"
    )
    assert boundaries["participant-predicate-opacity"]["reverse_implication"] == (
        "does not imply policy-noninterference"
    )
    assert all(entry["distinction"] and entry["nonclaim"] for entry in boundaries.values())

    dimensions = program["baseline_dimensions"]
    assert dimensions == {
        "nondeterminism": "possibilistic-support",
        "concurrency": "profile-required",
        "probability": "outside-baseline",
        "time": "untimed-progress-insensitive-baseline",
        "partial_order": "profile-required",
    }


def test_child_program_is_bounded_requirement_backed_and_acyclic() -> None:
    program = _load_program()
    issues = {entry["key"]: entry for entry in program["implementation_issues"]}

    assert set(issues) == {
        "bounded-falsification",
        "finite-state-model-checking",
        "mathematical-proof",
        "runtime-enforcement",
        "backend-realization",
    }

    issue_numbers: set[int] = set()
    for key, entry in issues.items():
        assert isinstance(entry["issue_number"], int) and entry["issue_number"] > 0, key
        assert entry["issue_number"] not in issue_numbers
        issue_numbers.add(entry["issue_number"])
        assert entry["milestone"] == MILESTONE
        assert entry["requirements"]
        assert set(entry["requirements"]) <= REQUIRED_REQUIREMENTS
        assert entry["bounded_outcome"]
        assert entry["negative_cases"]
        assert entry["evidence_required"]
        assert entry["explicit_nonclaims"]
        assert set(entry["dependencies"]) <= set(issues)

    incoming = {key: len(entry["dependencies"]) for key, entry in issues.items()}
    outgoing: dict[str, list[str]] = {key: [] for key in issues}
    for key, entry in issues.items():
        for dependency in entry["dependencies"]:
            outgoing[dependency].append(key)
    queue = deque(key for key, degree in incoming.items() if degree == 0)
    visited: list[str] = []
    while queue:
        key = queue.popleft()
        visited.append(key)
        for child in outgoing[key]:
            incoming[child] -= 1
            if incoming[child] == 0:
                queue.append(child)
    assert set(visited) == set(issues)
