"""Structural acceptance gate for issue #812's adversarial-control program."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROGRAM_PATH = REPO_ROOT / "docs/research/adversarial-participant-control/implementation-program.json"
MILESTONE = "Participant Information-Flow & Behavioral Equivalence"

REQUIRED_DELIVERABLES = {
    "docs/decisions/adrs/adr-101-adversarial-participant-flow-control.md",
    "docs/research/adversarial-participant-control/current-state-assessment.md",
    "docs/research/adversarial-participant-control/threat-model.md",
    "docs/research/adversarial-participant-control/trust-flow-architecture.md",
    "docs/research/adversarial-participant-control/attack-cases.md",
    "docs/research/adversarial-participant-control/requirement-disposition.md",
    "docs/research/adversarial-participant-control/implementation-program.md",
    "specs/formal/participant-semantics/adversarial-flow-control.md",
}
REQUIRED_REQUIREMENTS = {
    "SEM-230",
    "SEM-233",
    "ACT-617",
    "API-409",
    "API-423",
    "RUN-310",
    "RUN-319",
    "API-407",
    "ASR-535",
    "ASR-536",
}
REQUIRED_SOURCES = {
    "fides",
    "camel",
    "samos",
    "agentdojo",
    "ai-control",
    "controlarena",
    "runtime-shielding",
    "capability-security",
}
REQUIRED_THREAT_ACTORS = {
    "honest-fallible-participant",
    "intentionally-subverting-participant",
    "untrusted-content-source",
    "adaptive-policy-aware-attacker",
    "colluding-participants-or-monitors",
}
REQUIRED_ATTACK_CASES = {
    "prompt-or-tool-result-injection",
    "confidential-exfiltration",
    "adaptive-monitor-evasion",
    "control-handoff-manipulation",
}
REQUIRED_CHILDREN = {
    "semantic-authority",
    "portable-contracts",
    "runtime-enforcement",
    "apparatus-and-backend-support",
    "adversarial-evaluation",
    "documentation-and-claims",
}
REQUIRED_OPERATIONS = {
    "authentication",
    "authorization",
    "admission",
    "approval",
    "declassification",
    "integrity-endorsement",
    "redaction",
    "transformation",
    "trusted-editing",
    "deferral",
    "handoff",
    "interruption",
    "shutdown",
}
REQUIRED_SINKS = {
    "external-action",
    "tool-argument",
    "participant-output",
    "external-serialization",
    "stream-chunk",
    "error-output",
}
REQUIRED_EVALUATION_VARIABLES = {
    "mode",
    "main-objective",
    "side-objective",
    "policy-knowledge",
    "monitor-knowledge",
    "audit-budget-knowledge",
    "prior-outcome-visibility",
    "adaptive-strategy",
    "collusion",
    "monitor-topology",
    "monitor-correlation",
    "audit-budget",
    "intervention-protocol",
    "memory-scope",
}


def _load_program() -> dict[str, object]:
    return json.loads(PROGRAM_PATH.read_text(encoding="utf-8"))


def test_program_delivers_primary_source_disposition_and_authority() -> None:
    program = _load_program()

    assert program["schema_version"] == "adversarial-participant-control-program/v1"
    assert program["parent_issue"] == 812
    assert program["milestone"] == MILESTONE
    assert set(program["deliverables"]) >= REQUIRED_DELIVERABLES
    assert all((REPO_ROOT / path).is_file() for path in REQUIRED_DELIVERABLES)

    sources = {entry["id"]: entry for entry in program["primary_sources"]}
    assert set(sources) >= REQUIRED_SOURCES
    for source in sources.values():
        assert source["primary_url"]
        assert source["adopted_lessons"]
        assert source["raes_boundary"]
        assert source["nonclaims"]

    requirements = {entry["uid"]: entry for entry in program["requirement_dispositions"]}
    assert set(requirements) >= REQUIRED_REQUIREMENTS
    assert requirements["SEM-233"]["disposition"] == "new"
    assert requirements["SEM-233"]["status"] == "DRAFT"
    assert requirements["SEM-233"]["ground_control_id"]
    assert requirements["ASR-536"]["disposition"] == "new"
    assert requirements["ASR-536"]["status"] == "DRAFT"
    assert requirements["ASR-536"]["ground_control_id"]
    assert all(entry["scope"] and entry["rationale"] for entry in requirements.values())


def test_threat_model_separates_subversion_and_closes_declared_explicit_flows() -> None:
    program = _load_program()
    threat_model = program["threat_model"]

    actors = {entry["id"]: entry for entry in threat_model["actors"]}
    assert set(actors) >= REQUIRED_THREAT_ACTORS
    assert actors["honest-fallible-participant"]["intentional_subversion"] is False
    assert actors["intentionally-subverting-participant"]["intentional_subversion"] is True
    assert all(entry["capabilities"] and entry["trust_boundary"] for entry in actors.values())

    assert set(threat_model["explicit_flow_channels"]) >= {
        "observations",
        "tool-results",
        "retrieved-content",
        "participant-context",
        "retained-memory",
        "proposals",
        "action-arguments",
        "participant-outputs",
        "errors",
        "handoffs",
    }
    assert set(threat_model["crossing_scopes"]) == {
        "within-participant",
        "cross-participant",
        "cross-episode",
    }
    assert set(threat_model["outside_guarantee"]) >= {
        "undeclared-timing-channels",
        "covert-storage-channels",
        "model-steganography",
        "private-reasoning-safety",
        "monitor-honesty",
    }


def test_flow_profile_is_two_coordinate_conservative_and_fail_closed() -> None:
    profile = _load_program()["flow_policy_profile"]

    assert profile["profile_id"] == "participant-boundary-flow-policy-v1"
    assert profile["revision"] == "rev1"
    assert profile["confidentiality"]["independent_coordinate"] is True
    assert profile["integrity"]["independent_coordinate"] is True
    assert profile["confidentiality"]["join"] == "least-upper-bound"
    assert profile["integrity"]["join"] == "conservative-influence-union"
    assert profile["unknown_source_default"] == "confidential-and-untrusted"
    assert profile["missing_or_unknown_behavior"] == "deny-or-explicitly-unsupported"
    assert profile["opaque_transformation"] == "retain-join-of-all-possible-inputs"
    assert profile["historical_labels_are_immutable"] is True
    assert set(profile["distinct_operations"]) >= REQUIRED_OPERATIONS
    assert set(profile["sinks"]) >= REQUIRED_SINKS
    assert profile["final_enforcement_boundary"] == (
        "after-last-policy-and-state-cut-resolution-before-external-effect-or-disclosure"
    )
    assert profile["decision_committed_before_effect"] is True
    assert set(profile["deny_without_side_effect"]) >= {
        "missing-label",
        "missing-provenance",
        "unknown-profile",
        "stale-state-cut",
        "unsupported-capability",
        "policy-deny",
        "failed-atomic-commit",
    }


def test_control_evaluation_profile_exposes_adaptation_and_protocol_variables() -> None:
    profile = _load_program()["control_evaluation_profile"]

    assert profile["profile_id"] == "intentional-subversion-control-evaluation-v1"
    assert profile["revision"] == "rev1"
    variables = {entry["id"]: entry for entry in profile["variables"]}
    assert set(variables) >= REQUIRED_EVALUATION_VARIABLES
    assert all(entry["domain"] and entry["evidence_boundary"] for entry in variables.values())
    assert set(profile["modes"]) == {"honest", "attack"}
    assert set(profile["monitor_roles"]) >= {"trusted", "untrusted", "composed"}
    assert set(profile["interventions"]) >= {
        "human-approval",
        "trusted-editing",
        "defer-to-trusted",
        "interruption",
        "shutdown",
    }
    assert set(profile["measures"]) >= {
        "safety",
        "usefulness",
        "audit-cost",
        "intervention-cost",
        "uncertainty",
    }
    assert profile["monitor_score_authorizes_action"] is False
    assert profile["ordinary_negative_tests_establish_subversion_robustness"] is False


def test_attack_cases_reach_real_sink_and_require_no_prohibited_side_effects() -> None:
    cases = {entry["id"]: entry for entry in _load_program()["attack_cases"]}

    assert set(cases) == REQUIRED_ATTACK_CASES
    for case in cases.values():
        assert case["attack_path"]
        assert case["why_ordinary_admission_is_insufficient"]
        assert case["deterministic_boundary_result"]
        assert case["evaluation_variables"]
        assert set(case["required_evidence"]) >= {
            "semantic-result",
            "runtime-target-call-count",
            "participant-visible-output",
            "append-only-history",
            "safe-audit-or-error-evidence",
            "replay-result",
        }
        assert case["runtime_boundary"] == "RuntimeControlPlane-to-RuntimeTarget"
        assert case["denial_requires_zero_external_effects"] is True


def test_child_program_is_bounded_requirement_backed_and_acyclic() -> None:
    program = _load_program()
    issues = {entry["key"]: entry for entry in program["implementation_issues"]}

    assert set(issues) == REQUIRED_CHILDREN
    issue_numbers: set[int] = set()
    for key, entry in issues.items():
        assert isinstance(entry["issue_number"], int) and entry["issue_number"] > 0, key
        assert entry["issue_number"] not in issue_numbers
        issue_numbers.add(entry["issue_number"])
        assert entry["milestone"] == MILESTONE
        assert entry["requirements"]
        assert set(entry["requirements"]) <= REQUIRED_REQUIREMENTS
        assert {"SEM-233", "ASR-536"} & set(entry["requirements"])
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
    assert issues["documentation-and-claims"]["dependencies"] == [
        "runtime-enforcement",
        "apparatus-and-backend-support",
        "adversarial-evaluation",
    ]

    boundaries = program["claim_boundaries"]
    assert boundaries["issue_812"] == "design-authority-and-implementation-program-only"
    assert boundaries["runtime_enforcement"] == "not-established"
    assert boundaries["backend_realization"] == "not-established"
    assert boundaries["intentional_subversion_robustness"] == "not-established"
    assert boundaries["model_alignment"] == "outside-scope"
    assert boundaries["chain_of_thought"] == "excluded-from-portable-records"
    assert boundaries["covert_channels"] == "undeclared-channels-not-controlled"
