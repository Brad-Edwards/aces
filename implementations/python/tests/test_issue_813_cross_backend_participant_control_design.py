"""Structural acceptance gate for issue #813's cross-backend control program."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROGRAM_PATH = REPO_ROOT / "docs/research/cross-backend-participant-control/implementation-program.json"
PARTICIPANT_MILESTONE = "Participant Information-Flow & Behavioral Equivalence"
BACKEND_MILESTONE = "Backend Contract & Conformance"

REQUIRED_DELIVERABLES = {
    "docs/decisions/adrs/adr-102-mixed-cross-backend-participant-control.md",
    "docs/research/cross-backend-participant-control/prior-art-and-design-criteria.md",
    "docs/research/cross-backend-participant-control/current-state-assessment.md",
    "docs/research/cross-backend-participant-control/composition-architecture.md",
    "docs/research/cross-backend-participant-control/demonstration-protocol.md",
    "docs/research/cross-backend-participant-control/requirement-disposition.md",
    "docs/research/cross-backend-participant-control/implementation-program.md",
    "specs/formal/participant-semantics/cross-backend-participant-control.md",
}
REQUIRED_SOURCES = {
    "hla-1516-2025",
    "nist-integrated-hla",
    "nist-ucef",
    "acting-edl-fg",
    "cyborg",
    "cygil",
    "cyberbattlesim",
    "fmi-3.0.2",
    "helics",
    "iso-23247-6",
    "digital-twin-consortium",
    "ieee-1730.1",
    "siso-sirl",
    "w3c-prov",
    "ro-crate",
}
REQUIRED_REQUIREMENTS = {
    "SEM-230",
    "SEM-234",
    "SCE-002",
    "API-407",
    "API-423",
    "RUN-310",
    "RUN-319",
    "ASR-535",
    "ASR-537",
}
REQUIRED_REALIZATION_FORMS = {
    "simulation",
    "emulation-or-operational",
    "hardware-or-native",
    "federated-composition",
}
REQUIRED_ALLOCATION_UNITS = {
    "participant-runtime",
    "controlled-scope",
    "action-family",
    "observation-source",
    "crossing-boundary",
}
REQUIRED_BOUNDARY_FIELDS = {
    "source-component-ref",
    "destination-component-ref",
    "adapter-ref",
    "authority-ref",
    "action-or-observation-mapping-ref",
    "participant-audience-policy-ref",
    "release-or-declassification-basis-ref",
    "time-mapping-ref",
    "required-support-strength",
    "mapping-loss",
    "failure-behavior",
    "evidence-refs",
}
REQUIRED_OPEN_CLOSED_AXES = {
    "control-loop",
    "world-assumption",
    "federation-membership",
}
REQUIRED_DEMONSTRATION_CASES = {
    "pure-simulation",
    "pure-emulation-or-operational",
    "simultaneous-mixed",
    "inter-trial-transition",
    "pre-admitted-phase-transition",
    "open-loop",
    "closed-loop",
    "stale-handoff",
    "concurrent-intervention",
    "unsupported-or-false-capability",
    "timestamp-only-or-unmapped-order",
    "simulation-only-observation",
    "unrealizable-action",
    "directed-delivery-failure",
    "prior-delivery-retraction",
    "bridge-metadata-leakage",
}
REQUIRED_CHILDREN = {
    "semantic-authority",
    "portable-composition-contracts",
    "trial-admission",
    "runtime-coordination",
    "backend-capability-and-conformance",
    "demonstration-and-evaluation",
    "documentation-and-claims",
}


def _load_program() -> dict[str, object]:
    return json.loads(PROGRAM_PATH.read_text(encoding="utf-8"))


def test_program_delivers_primary_source_disposition_and_draft_authority() -> None:
    program = _load_program()

    assert program["schema_version"] == "cross-backend-participant-control-program/v1"
    assert program["parent_issue"] == 813
    assert program["participant_milestone"] == PARTICIPANT_MILESTONE
    assert program["backend_coordination_milestone"] == BACKEND_MILESTONE
    assert set(program["deliverables"]) >= REQUIRED_DELIVERABLES
    assert all((REPO_ROOT / path).is_file() for path in REQUIRED_DELIVERABLES)

    sources = {entry["id"]: entry for entry in program["primary_sources"]}
    assert set(sources) >= REQUIRED_SOURCES
    for source in sources.values():
        assert source["primary_url"]
        assert source["edition_or_version"]
        assert source["adopted_lessons"]
        assert source["rejected_inferences"]
        assert source["raes_consequence"]
        assert source["nonclaims"]
    assert any(source["stronger_dimension"] for source in sources.values())
    assert sources["hla-1516-2025"]["stronger_dimension"]
    assert sources["cyborg"]["empirical_result_boundary"]
    assert sources["cygil"]["empirical_result_boundary"]

    requirements = {entry["uid"]: entry for entry in program["requirement_dispositions"]}
    assert set(requirements) >= REQUIRED_REQUIREMENTS
    for uid in ("SEM-234", "ASR-537"):
        assert requirements[uid]["disposition"] == "new"
        assert requirements[uid]["status"] == "DRAFT"
        assert requirements[uid]["ground_control_id"]
        assert requirements[uid]["scope"]
        assert requirements[uid]["rationale"]


def test_composition_profile_supports_or_and_and_without_authority_conflation() -> None:
    profile = _load_program()["composition_profile"]

    assert profile["profile_id"] == "mixed-cross-backend-participant-control-v1"
    assert profile["revision"] == "rev1"
    assert set(profile["composition_modes"]) == {
        "alternative-realization",
        "simultaneous-mixed-realization",
    }
    assert set(profile["realization_forms"]) >= REQUIRED_REALIZATION_FORMS
    assert set(profile["allocation_units"]) == REQUIRED_ALLOCATION_UNITS
    assert profile["portable_sdl_backend_neutral"] is True
    assert profile["runtime_fallback_outside_allocation"] == "reject"
    assert set(profile["boundary_required_fields"]) >= REQUIRED_BOUNDARY_FIELDS

    authority = profile["authority_model"]
    assert authority["acting_controller_cardinality"] == "exactly-one-per-participant-episode-rev1"
    assert authority["hla_ownership_is_controller_authority"] is False
    assert authority["backend_responsibility_is_action_admission"] is False
    assert authority["routing_is_disclosure_authority"] is False
    assert authority["multi_controller_status"] == "not-supported-in-rev1"
    assert authority["lease_status"] == "not-supported-in-rev1"
    assert authority["joint_or_fused_control_status"] == "not-supported-in-rev1"
    assert set(authority["distinct_relations"]) >= {
        "participant-identity",
        "acting-controller",
        "authority-basis-and-scope",
        "action-admission",
        "backend-realization-responsibility",
        "hla-object-or-attribute-ownership",
        "delivery-addressing",
        "participant-disclosure-authority",
    }


def test_trial_time_and_open_closed_axes_are_independent_and_fail_closed() -> None:
    program = _load_program()
    trial = program["trial_realization_profile"]

    assert trial["inter_trial_change"] == "linked-new-plan-entry-and-run"
    assert trial["within_run_change"] == "finite-pre-admitted-phase-schedule"
    assert trial["all_phase_apparatus_pinned_before_execution"] is True
    assert trial["late_unadmitted_join"] == "reject"
    assert trial["history_and_participant_knowledge"] == "append-only"
    assert trial["trial_identity_rewritten_by_phase_change"] is False

    axes = {entry["id"]: entry for entry in program["open_closed_axes"]}
    assert set(axes) == REQUIRED_OPEN_CLOSED_AXES
    assert axes["control-loop"]["values"] == ["open-loop", "closed-loop"]
    assert set(axes["federation-membership"]["values"]) == {"fixed", "pre-admitted-dynamic"}
    assert all(entry["authority_owner"] and entry["adoption"] for entry in axes.values())

    time = program["time_and_order_profile"]
    assert time["cross_clock_mapping_required"] is True
    assert time["timestamp_only_strength"] == "disclosed-weak"
    assert time["unmapped_clock_relation"] == "partial-or-unknown"
    assert time["backend_serialized_requires_readback"] is True
    assert time["rollback_or_retraction_erases_delivery"] is False
    assert set(time["staleness_coordinates"]) >= {
        "controller",
        "authority",
        "policy-revision",
        "state-revision",
        "history-head",
        "governed-order",
    }

    security = program["distribution_and_security_profile"]
    assert security["publish_subscribe_authorizes_disclosure"] is False
    assert security["ddm_establishes_ifc"] is False
    assert security["directed_delivery_is_participant_observation"] is False
    assert security["filtering_occurs_after_raes_authorization"] is True
    assert set(security["metadata_leakage_surface"]) >= {
        "membership",
        "subscription",
        "object-or-interaction-class",
        "region-or-destination",
        "message-size",
        "timing",
        "synchronization",
        "ownership-change",
        "retraction",
        "delivery-failure",
    }


def test_demonstration_protocol_covers_mixed_transfer_mismatch_and_zero_effects() -> None:
    program = _load_program()
    protocol = program["demonstration_protocol"]
    cases = {entry["id"]: entry for entry in protocol["cases"]}

    assert protocol["same_authored_policy_digest_required"] is True
    assert set(cases) == REQUIRED_DEMONSTRATION_CASES
    for case in cases.values():
        assert case["composition"]
        assert case["boundary"]
        assert case["expected_disposition"]
        assert set(case["required_evidence"]) >= {
            "scenario-and-policy-digests",
            "trial-and-run-identity",
            "apparatus-and-adapter-identities",
            "capability-and-conformance",
            "allocation-and-topology",
            "time-and-order",
            "mapping-loss-and-limitations",
        }
        assert case["nonclaims"]

    zero_effect_cases = {case_id for case_id, case in cases.items() if case["denial_requires_zero_prohibited_effects"]}
    assert zero_effect_cases >= {
        "stale-handoff",
        "unsupported-or-false-capability",
        "unrealizable-action",
        "directed-delivery-failure",
    }
    assert protocol["reporting_relations_are_distinct"] == [
        "bounded-conformance",
        "interoperability-readiness",
        "empirical-sim-to-em-transfer",
        "trace-inclusion",
        "bisimulation",
        "ifc-or-noninterference",
        "backend-equivalence",
    ]


def test_child_program_is_bounded_requirement_backed_milestoned_and_acyclic() -> None:
    program = _load_program()
    issues = {entry["key"]: entry for entry in program["implementation_issues"]}

    assert set(issues) == REQUIRED_CHILDREN
    issue_numbers: set[int] = set()
    for key, entry in issues.items():
        assert isinstance(entry["issue_number"], int), key
        assert entry["issue_number"] > 0, key
        assert entry["issue_number"] not in issue_numbers
        issue_numbers.add(entry["issue_number"])
        assert entry["requirements"]
        assert set(entry["requirements"]) <= REQUIRED_REQUIREMENTS
        assert {"SEM-234", "ASR-537"} & set(entry["requirements"])
        assert entry["milestone"] in {PARTICIPANT_MILESTONE, BACKEND_MILESTONE}
        assert entry["bounded_outcome"]
        assert entry["negative_cases"]
        assert entry["evidence_required"]
        assert entry["explicit_nonclaims"]
        assert set(entry["dependencies"]) <= set(issues)

    assert issues["backend-capability-and-conformance"]["milestone"] == BACKEND_MILESTONE
    assert all(
        entry["milestone"] == PARTICIPANT_MILESTONE
        for key, entry in issues.items()
        if key != "backend-capability-and-conformance"
    )

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
        "runtime-coordination",
        "backend-capability-and-conformance",
        "demonstration-and-evaluation",
    ]

    boundaries = program["claim_boundaries"]
    assert boundaries["issue_813"] == "design-authority-and-implementation-program-only"
    assert boundaries["mixed_runtime_implementation"] == "not-established"
    assert boundaries["backend_realization"] == "not-established"
    assert boundaries["cross_backend_equivalence"] == "not-established"
    assert boundaries["ifc_or_noninterference"] == "not-established"
    assert boundaries["universal_sim_to_em_transfer"] == "not-established"
