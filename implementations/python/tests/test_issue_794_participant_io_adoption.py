"""Structural acceptance gate for issue #794's adoption program."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROGRAM_PATH = REPO_ROOT / "docs/research/participant-io-control/adoption-program.json"
MILESTONE = "Participant Information-Flow & Behavioral Equivalence"

REQUIRED_DELIVERABLES = {
    "docs/decisions/adrs/adr-085-participant-information-flow-and-control.md",
    "docs/research/participant-io-control/current-state-assessment.md",
    "docs/research/participant-io-control/adoption-design.md",
    "docs/research/participant-io-control/requirement-disposition.md",
    "docs/research/participant-io-control/adoption-program.md",
    "docs/research/participant-io-control/index.md",
}

REQUIRED_THREADS = {
    "#71",
    "SEM-208",
    "SEM-209",
    "SEM-210",
    "SEM-211",
    "SEM-212",
    "SEM-213",
    "ADR-022",
    "#74",
    "RUN-305",
    "RUN-306",
    "RUN-307",
    "RUN-308",
    "ADR-054",
    "#119",
    "SEM-219",
    "SEM-220",
    "SEM-226",
    "ADR-083",
    "#294",
    "#295",
    "#296",
    "#747",
    "ADR-081",
    "behavioral-relations-v1",
    "ACT-617",
    "RUN-310",
    "API-409",
    "#251",
    "#252",
    "#255",
    "API-406",
    "DSL-111",
    "scientific-completeness-delivery-assessment",
}

REQUIRED_CONCERNS = {
    "participant-relative-world",
    "information-flow-policy",
    "action-labels-and-hidden-actions",
    "temporal-and-order-semantics",
    "participant-input-admission",
    "participant-output-projection",
    "mixed-control-intervention",
    "participant-directed-inject-delivery",
    "input-output-transformation",
    "portable-contracts",
    "runtime-enforcement-and-evidence",
    "backend-capability-and-realization",
    "conformance-and-assurance",
    "compatibility-and-migration",
    "documentation-and-adoption",
}

REQUIRED_OPERATIONS = {
    "authorization",
    "admission",
    "withholding",
    "projection",
    "masking",
    "redaction",
    "declassification",
    "disclosure",
    "concealment",
    "revocation",
    "loss",
    "weakening",
}

REQUIRED_RELATIONS = {
    "policy-noninterference",
    "participant-projected-history-equivalence",
    "trace-inclusion",
    "forward-simulation",
    "data-refinement",
    "strong-bisimulation",
    "weak-bisimulation",
    "epistemic-indistinguishability",
}

NEW_REQUIREMENTS = {"SEM-230", "DSL-142", "API-423", "RUN-319", "ASR-535"}


def _load_program() -> dict[str, object]:
    return json.loads(PROGRAM_PATH.read_text(encoding="utf-8"))


def test_program_covers_deliverables_threads_and_semantic_concerns() -> None:
    program = _load_program()

    assert program["schema_version"] == "participant-io-adoption-program/v1"
    assert program["milestone"] == MILESTONE
    assert set(program["deliverables"]) >= REQUIRED_DELIVERABLES
    assert all((REPO_ROOT / path).is_file() for path in REQUIRED_DELIVERABLES)

    thread_dispositions = {entry["id"]: entry for entry in program["thread_dispositions"]}
    assert set(thread_dispositions) >= REQUIRED_THREADS
    for thread_id in REQUIRED_THREADS:
        entry = thread_dispositions[thread_id]
        assert entry["establishes"], thread_id
        assert entry["does_not_establish"], thread_id
        assert entry["authority"] in {"normative", "proposed", "implementation", "tracking", "assessment"}
        for field in (
            "definition_status",
            "implementation_status",
            "test_status",
            "proof_status",
            "runtime_realization",
        ):
            assert entry[field] in {
                "none",
                "proposed",
                "partial",
                "implemented",
                "tested",
                "bounded",
                "deliberately-unproved",
                "future",
                "realized",
                "unknown",
                "not-applicable",
            }, (thread_id, field)

    concerns = {entry["id"]: entry for entry in program["concerns"]}
    assert set(concerns) >= REQUIRED_CONCERNS
    assert all(concerns[concern]["decision"] and concerns[concern]["evidence_refs"] for concern in REQUIRED_CONCERNS)

    operations = {entry["operation"] for entry in program["information_flow_operations"]}
    assert operations == REQUIRED_OPERATIONS
    assert len({entry["meaning"] for entry in program["information_flow_operations"]}) == len(REQUIRED_OPERATIONS)


def test_relation_claims_are_explicit_and_do_not_promote_bounded_evidence() -> None:
    relations = {entry["relation_id"]: entry for entry in _load_program()["relation_claims"]}

    assert set(relations) >= REQUIRED_RELATIONS
    for relation_id in REQUIRED_RELATIONS:
        entry = relations[relation_id]
        for field in (
            "claim_surface",
            "projection",
            "quantifiers",
            "time_and_order",
            "scheduler_and_environment",
            "evidence_boundary",
            "assurance_status",
        ):
            assert entry[field], (relation_id, field)
        assert entry["explicit_nonclaims"], relation_id
        if entry["assurance_status"] in {"bounded", "implemented-and-tested"}:
            assert entry["quantifiers"] != "universal", relation_id
        if relation_id in {"strong-bisimulation", "weak-bisimulation", "policy-noninterference"}:
            assert entry["assurance_status"] in {"future", "deliberately-unproved"}

    assert (
        relations["policy-noninterference"]["definition"]
        != relations["participant-projected-history-equivalence"]["definition"]
    )
    assert relations["policy-noninterference"]["definition"] != relations["strong-bisimulation"]["definition"]


def test_requirement_dispositions_and_issue_program_are_complete_and_acyclic() -> None:
    program = _load_program()
    requirements = {entry["uid"]: entry for entry in program["requirement_dispositions"]}
    issues = {entry["key"]: entry for entry in program["implementation_issues"]}

    assert set(requirements) >= NEW_REQUIREMENTS
    assert all(requirements[uid]["disposition"] == "new" for uid in NEW_REQUIREMENTS)
    assert all(requirements[uid]["status"] == "DRAFT" for uid in NEW_REQUIREMENTS)
    assert all(entry["rationale"] and entry["scope"] for entry in requirements.values())

    categories = {entry["category"] for entry in issues.values()}
    assert {
        "semantic-authority",
        "sdl",
        "contracts",
        "runtime",
        "backend-obligations",
        "conformance",
        "migration",
        "documentation",
    } <= categories

    issue_numbers: set[int] = set()
    for key, entry in issues.items():
        assert isinstance(entry["issue_number"], int) and entry["issue_number"] > 0, key
        assert entry["issue_number"] not in issue_numbers, entry["issue_number"]
        issue_numbers.add(entry["issue_number"])
        assert entry["milestone"] == MILESTONE, key
        assert entry["requirements"] and set(entry["requirements"]) <= set(requirements), key
        assert entry["bounded_outcome"], key
        assert entry["non_goals"], key
        assert entry["acceptance_criteria"], key
        assert entry["assurance_evidence"], key
        assert set(entry["dependencies"]) <= set(issues), key

    indegree = {key: 0 for key in issues}
    downstream = {key: [] for key in issues}
    for key, entry in issues.items():
        for dependency in entry["dependencies"]:
            indegree[key] += 1
            downstream[dependency].append(key)
    queue = deque(key for key, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        key = queue.popleft()
        visited += 1
        for child in downstream[key]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    assert visited == len(issues), "implementation dependency graph contains a cycle"

    final_index = program["final_index"]
    assert {entry["issue_number"] for entry in final_index} == issue_numbers
    assert all(set(entry["requirements"]) == set(issues[entry["key"]]["requirements"]) for entry in final_index)
