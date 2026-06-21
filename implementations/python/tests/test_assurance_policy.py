from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.check_assurance_policy import (  # noqa: E402
    ADR_CLASSIFICATION_REQUIRED_FROM,
    ADR_POLICY_RELATIVE_PATH,
    ADR_REF,
    ADR_REFS,
    ADR_TEMPLATE_RELATIVE_PATH,
    ASSURANCE_FULFILLMENT_RELATIVE_PATH,
    ASSURANCE_POLICY_RELATIVE_PATH,
    CANONICAL_LEVEL_IDS,
    CODING_STANDARDS_RELATIVE_PATH,
    FM_CLASSIFICATION_LEDGER_RELATIVE_PATH,
    FORMAL_OVERVIEW_RELATIVE_PATH,
    REQUIRED_CHANGE_CATEGORIES,
    REQUIREMENT_REF,
    evaluate_assurance_policy,
)

# A canonical, well-formed policy YAML used as the positive case and as the
# starting point for mutation in defect cases. The structure mirrors what the
# real repo's YAML asserts; only the descriptive prose is trimmed.
_GOOD_POLICY = """policy: classification-based-assurance
requirement_refs:
  - ASR-505
adr_refs:
  - ADR-007
  - ADR-018
levels:
  - id: FM0
    name: Structural
    scope: Shape, parsing, schema, and local validation only.
    change_categories: [structural]
    required_artifacts: [unit_tests]
    prohibited_artifacts: [TLA+, Alloy]
  - id: FM1
    name: Static Semantic
    scope: Cross-references, uniqueness, ambiguity, acyclicity, fail-closed resolution.
    change_categories: [semantic]
    required_artifacts: [invariant_list, unit_tests]
    recommended_artifacts: [property_based_tests]
  - id: FM2
    name: Semantic Graph / Constraint
    scope: Reachability, visibility, dependency propagation, planner ordering, portability rules.
    change_categories: [graph, constraint]
    required_artifacts:
      - invariant_list
      - unit_tests
      - typed_ir_or_contract_coverage
      - property_based_or_differential_tests
  - id: FM3
    name: Stateful / Control Semantics
    scope: State machines, branching, retries, joins, re-entry, lifecycle semantics, result contracts.
    change_categories: [stateful, control]
    required_artifacts:
      - invariant_list
      - unit_tests
      - typed_ir_or_contract_coverage
      - property_based_or_differential_tests
      - abstract_state_machine_model
    recommended_artifacts: [TLA+, Alloy]
"""

# Stub policy ADR-007 -- must reference every canonical level id AND every
# canonical level name so the drift guard fires when the name changes (the
# exact failure mode that motivated ADR-018).
_GOOD_ADR = """# ADR-007: Lightweight Formal Methods Policy

## Status
accepted

## Decision
The classification ladder is FM0 (Structural), FM1 (Static Semantic),
FM2 (Semantic Graph / Constraint), and FM3 (Stateful / Control Semantics).
"""

_GOOD_CODING_STANDARDS = """# Coding Standards

The classification levels are FM0 Structural, FM1 Static Semantic,
FM2 Semantic Graph / Constraint, and FM3 Stateful / Control Semantics.

Required artifacts per level: unit tests (FM0), invariants + unit tests
(FM1), typed IR/contract coverage and property-based or differential tests
(FM2), and an abstract state-machine model (FM3).
"""

_GOOD_FORMAL_OVERVIEW = """# Formal Specifications

| Level | Name | Required artifacts |
|-------|------|--------------------|
| FM0 | Structural | unit tests |
| FM1 | Static Semantic | invariants + unit tests |
| FM2 | Semantic Graph / Constraint | FM1 + typed IR/contract coverage + property-based or differential tests |
| FM3 | Stateful / Control Semantics | FM2 + abstract state-machine model |
"""

_GOOD_ADR_TEMPLATE = """# ADR-NNN: Title

## Status

proposed

## Date

YYYY-MM-DD

## Classification

Classification: FM<n>
Required artifacts: <artifact kinds delivered or waived>
Waivers: <none, or artifact kind plus rationale>

## Context

Describe the problem.

## Decision

State the decision.

## Alternatives Considered

List rejected options.

## Consequences

Record outcomes.
"""

_GOOD_EMPTY_LEDGER = """ledger: per-change-fm-classification
policy_ref: specs/formal/assurance-policy.yaml
entries: []
"""

# A temp repo seeded by `_seed_repo` has no `specs/formal/<domain>/` directories,
# so the classified-subsystem registry and the fulfillment map are both empty and
# the gate is clean. Tests that exercise the fulfillment check seed their own
# domain directories and pass an explicit `fulfillment_body`.
_GOOD_EMPTY_FULFILLMENT = """fulfillment: classification-based-assurance-fulfillment
policy_ref: specs/formal/assurance-policy.yaml
adr_refs:
  - ADR-007
  - ADR-018
subsystems: []
entries: []
"""


def _seed_repo(
    tmp_path: Path,
    *,
    policy_body: str = _GOOD_POLICY,
    adr_body: str | None = _GOOD_ADR,
    coding_standards_body: str | None = _GOOD_CODING_STANDARDS,
    formal_overview_body: str | None = _GOOD_FORMAL_OVERVIEW,
    adr_template_body: str | None = _GOOD_ADR_TEMPLATE,
    ledger_body: str | None = _GOOD_EMPTY_LEDGER,
    fulfillment_body: str | None = _GOOD_EMPTY_FULFILLMENT,
) -> Path:
    """Seed a temp repo skeleton with the policy YAML and referencing docs."""
    policy_path = tmp_path / ASSURANCE_POLICY_RELATIVE_PATH
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(policy_body, encoding="utf-8")

    if adr_body is not None:
        adr_path = tmp_path / ADR_POLICY_RELATIVE_PATH
        adr_path.parent.mkdir(parents=True, exist_ok=True)
        adr_path.write_text(adr_body, encoding="utf-8")

    if coding_standards_body is not None:
        cs_path = tmp_path / CODING_STANDARDS_RELATIVE_PATH
        cs_path.parent.mkdir(parents=True, exist_ok=True)
        cs_path.write_text(coding_standards_body, encoding="utf-8")

    if formal_overview_body is not None:
        fo_path = tmp_path / FORMAL_OVERVIEW_RELATIVE_PATH
        fo_path.parent.mkdir(parents=True, exist_ok=True)
        fo_path.write_text(formal_overview_body, encoding="utf-8")

    if adr_template_body is not None:
        template_path = tmp_path / ADR_TEMPLATE_RELATIVE_PATH
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(adr_template_body, encoding="utf-8")

    if ledger_body is not None:
        ledger_path = tmp_path / FM_CLASSIFICATION_LEDGER_RELATIVE_PATH
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(ledger_body, encoding="utf-8")

    if fulfillment_body is not None:
        fulfillment_path = tmp_path / ASSURANCE_FULFILLMENT_RELATIVE_PATH
        fulfillment_path.parent.mkdir(parents=True, exist_ok=True)
        fulfillment_path.write_text(fulfillment_body, encoding="utf-8")

    return tmp_path


def _flagged(failures, marker: str) -> bool:
    """Return True if some failure matches ``marker`` by rule id or substring of its render."""
    needle = marker.lower()
    return any(f.rule_id == marker or needle in f.render().lower() for f in failures)


def _write(path: Path, text: str = "placeholder\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _new_adr_body(
    *,
    classification: str | None = "FM1",
    artifacts: str | None = "unit_tests",
    waivers: str | None = "none",
) -> str:
    fields: list[str] = []
    if classification is not None:
        fields.append(f"Classification: {classification}")
    if artifacts is not None:
        fields.append(f"Required artifacts: {artifacts}")
    if waivers is not None:
        fields.append(f"Waivers: {waivers}")
    classification_section = "\n".join(fields)
    return f"""# ADR-{ADR_CLASSIFICATION_REQUIRED_FROM:03d}: New Semantic Surface

## Status

proposed

## Date

2026-06-12

## Classification

{classification_section}

## Context

This proposed ADR adds a semantic runtime surface.

## Decision

Record a semantic decision.

## Alternatives Considered

None.

## Consequences

The new decision is auditable.
"""


def _ledger_entry(
    adr: str = "ADR-023",
    *,
    fm_level: str = "FM1",
    include_unit_test: bool = True,
) -> str:
    delivered = [
        f"      - kind: invariant_list\n        path: docs/decisions/adrs/adr-{adr[-3:]}-surface.md",
    ]
    if include_unit_test:
        delivered.append(
            "      - kind: unit_tests\n        path: implementations/python/tests/test_assurance_policy_surface.py"
        )
    return f"""  - adr: {adr}
    surface: Example runtime surface
    fm_level: {fm_level}
    delivered_artifacts:
{chr(10).join(delivered)}
    waived_artifacts: []
"""


def _seed_runtime_surface(repo: Path, adr: str = "ADR-023") -> None:
    _write(repo / f"docs/decisions/adrs/adr-{adr[-3:]}-surface.md", f"# {adr}: Surface\n")
    _write(repo / "implementations/python/tests/test_assurance_policy_surface.py")


# ----------------------------------------------------------------------------- #
# Positive case -- the canonical YAML against canonical doc stubs is clean.     #
# ----------------------------------------------------------------------------- #


def test_good_policy_has_no_failures(tmp_path: Path) -> None:
    failures = evaluate_assurance_policy(_seed_repo(tmp_path))
    assert failures == []


# ----------------------------------------------------------------------------- #
# Structural module-level invariants -- these must hold by construction.        #
# ----------------------------------------------------------------------------- #


def test_canonical_level_ids_cover_fm0_to_fm3() -> None:
    # CANONICAL_LEVEL_IDS is the baseline floor (the policy may add FM4+
    # in the YAML, but it can never drop one of these).
    assert CANONICAL_LEVEL_IDS == ("FM0", "FM1", "FM2", "FM3")


def test_required_change_categories_match_asr_505_statement() -> None:
    assert set(REQUIRED_CHANGE_CATEGORIES) == {"structural", "semantic", "graph", "stateful"}


def test_requirement_ref_is_asr_505() -> None:
    assert REQUIREMENT_REF == "ASR-505"


def test_adr_ref_is_adr_007() -> None:
    assert ADR_REF == "ADR-007"


def test_adr_refs_include_both_adr_007_and_adr_018() -> None:
    # ADR-007 is the policy decision; ADR-018 governs THIS file. Both must
    # be in the YAML's adr_refs, and the validator pins both.
    assert "ADR-007" in ADR_REFS
    assert "ADR-018" in ADR_REFS


# ----------------------------------------------------------------------------- #
# YAML missing, unparseable, wrong root shape.                                  #
# ----------------------------------------------------------------------------- #


def test_missing_policy_file_is_flagged(tmp_path: Path) -> None:
    seeded = _seed_repo(tmp_path)
    (seeded / ASSURANCE_POLICY_RELATIVE_PATH).unlink()
    failures = evaluate_assurance_policy(seeded)
    assert _flagged(failures, "assurance-policy-missing")


def test_unparseable_policy_file_is_flagged(tmp_path: Path) -> None:
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body="this: is: : invalid"))
    assert _flagged(failures, "assurance-policy-parse")


def test_policy_root_must_be_mapping(tmp_path: Path) -> None:
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body="- just\n- a\n- list\n"))
    assert _flagged(failures, "assurance-policy-shape")


# ----------------------------------------------------------------------------- #
# Sequence-field type strictness -- non-list values are rejected, not coerced.  #
# This guards against the "silent coercion" failure mode where `levels:` (null) #
# or `levels: not-a-list` would have skipped every per-level check.             #
# ----------------------------------------------------------------------------- #


def test_levels_null_is_flagged_as_missing_canonical_levels(tmp_path: Path) -> None:
    body = _GOOD_POLICY[: _GOOD_POLICY.index("levels:")] + "levels:\n"
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    # Every canonical level should be reported as missing.
    for level_id in CANONICAL_LEVEL_IDS:
        assert _flagged(failures, level_id), f"expected {level_id} to be flagged when levels is null"
    assert _flagged(failures, "assurance-policy-level-missing")


def test_levels_empty_list_is_flagged_explicitly(tmp_path: Path) -> None:
    body = _GOOD_POLICY[: _GOOD_POLICY.index("levels:")] + "levels: []\n"
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-levels-empty")
    # Per-level missing checks must still fire.
    for level_id in CANONICAL_LEVEL_IDS:
        assert _flagged(failures, level_id), f"expected {level_id} to be flagged when levels is empty"


def test_levels_non_list_value_is_rejected(tmp_path: Path) -> None:
    body = _GOOD_POLICY[: _GOOD_POLICY.index("levels:")] + "levels: oops\n"
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-field-type")


def test_requirement_refs_non_list_value_is_rejected(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace("requirement_refs:\n  - ASR-505\n", "requirement_refs: ASR-505\n", 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-field-type")


def test_adr_refs_non_list_value_is_rejected(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace("adr_refs:\n  - ADR-007\n", "adr_refs: ADR-007\n", 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-field-type")


def test_level_required_artifacts_non_list_value_is_rejected(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace(
        "    required_artifacts: [unit_tests]\n",
        "    required_artifacts: unit_tests\n",
        1,
    )
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-level-field-type")


def test_level_required_artifacts_non_string_element_is_rejected(tmp_path: Path) -> None:
    # YAML `required_artifacts: [unit_tests, null]` would have been
    # silently stringified to ['unit_tests', 'None']. The strict-string
    # check rejects it.
    body = _GOOD_POLICY.replace(
        "    required_artifacts: [unit_tests]\n",
        "    required_artifacts: [unit_tests, null]\n",
        1,
    )
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-level-field-type")


def test_adr_refs_non_string_element_is_rejected(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace(
        "adr_refs:\n  - ADR-007\n  - ADR-018\n",
        "adr_refs:\n  - ADR-007\n  - ADR-018\n  - 17\n",
        1,
    )
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-field-type")


# ----------------------------------------------------------------------------- #
# Required top-level fields and value.                                          #
# ----------------------------------------------------------------------------- #


_TOP_LEVEL_FIELD_CASES = [
    ("policy", "policy: classification-based-assurance\n"),
    ("requirement_refs", "requirement_refs:\n  - ASR-505\n"),
    ("adr_refs", "adr_refs:\n  - ADR-007\n"),
    ("levels", "levels:\n"),
]


@pytest.mark.parametrize(
    ("field", "needle"),
    _TOP_LEVEL_FIELD_CASES,
    ids=[case[0] for case in _TOP_LEVEL_FIELD_CASES],
)
def test_missing_top_level_field_is_flagged(tmp_path: Path, field: str, needle: str) -> None:
    body = _GOOD_POLICY.replace(needle, "", 1)
    assert body != _GOOD_POLICY, f"setup error for field {field}: needle not found in _GOOD_POLICY"
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-field")
    # Check the failure MESSAGE (not the rendered form) contains the field
    # name -- the rule id "assurance-policy-field" itself contains "policy",
    # so a substring-on-render check would be vacuously true for the "policy"
    # case and silently mask an implementation that named the wrong field.
    assert any(field in failure.message for failure in failures), (
        f"expected a failure whose message names field {field!r}; got: {[failure.render() for failure in failures]}"
    )


def test_policy_value_must_match_canonical(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace(
        "policy: classification-based-assurance\n",
        "policy: something-else\n",
        1,
    )
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-value")


# ----------------------------------------------------------------------------- #
# Levels: ladder shape, ordering, required keys, supersets.                     #
# ----------------------------------------------------------------------------- #


def test_missing_fm_level_is_flagged(tmp_path: Path) -> None:
    # Drop the entire FM2 block from the policy.
    lines = _GOOD_POLICY.splitlines(keepends=True)
    keep: list[str] = []
    skip = False
    for line in lines:
        if line.startswith("  - id: FM2"):
            skip = True
            continue
        if skip and line.startswith("  - id: "):
            skip = False
        if not skip:
            keep.append(line)
    body = "".join(keep)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-level-missing")
    assert _flagged(failures, "FM2")


def test_duplicate_level_ids_are_flagged(tmp_path: Path) -> None:
    # Append a second FM2 block at the end. `by_id` would otherwise silently
    # keep only the second entry, masking the duplication.
    duplicate_fm2 = (
        "  - id: FM2\n"
        "    name: Semantic Graph / Constraint\n"
        "    scope: Duplicate entry that must be rejected as ambiguous.\n"
        "    change_categories: [graph, constraint]\n"
        "    required_artifacts:\n"
        "      - invariant_list\n"
        "      - unit_tests\n"
        "      - typed_ir_or_contract_coverage\n"
        "      - property_based_or_differential_tests\n"
    )
    body = _GOOD_POLICY + duplicate_fm2
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-level-duplicate")
    assert _flagged(failures, "FM2")


def test_levels_out_of_order_is_flagged(tmp_path: Path) -> None:
    lines = _GOOD_POLICY.splitlines(keepends=True)
    indices = [i for i, ln in enumerate(lines) if ln.startswith("  - id: ")]
    assert len(indices) == 4
    prologue = lines[: indices[0]]
    fm0_block = lines[indices[0] : indices[1]]
    fm1_block = lines[indices[1] : indices[2]]
    fm2_block = lines[indices[2] : indices[3]]
    fm3_block = lines[indices[3] :]
    swapped = "".join(prologue + fm0_block + fm2_block + fm1_block + fm3_block)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=swapped))
    assert _flagged(failures, "assurance-policy-level-order")


def test_level_missing_required_key_is_flagged(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace(
        "    change_categories: [structural]\n",
        "",
        1,
    )
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-level-field")


_PROPORTIONALITY_BREAK_CASES = [
    (
        "FM2-not-superset-of-FM1",
        (
            "  - id: FM2\n    name: Semantic Graph / Constraint\n"
            "    scope: Reachability, visibility, dependency propagation, planner ordering, portability rules.\n"
            "    change_categories: [graph, constraint]\n"
            "    required_artifacts:\n"
            "      - invariant_list\n"
            "      - unit_tests\n"
            "      - typed_ir_or_contract_coverage\n"
            "      - property_based_or_differential_tests\n"
        ),
        (
            "  - id: FM2\n    name: Semantic Graph / Constraint\n"
            "    scope: Reachability, visibility, dependency propagation, planner ordering, portability rules.\n"
            "    change_categories: [graph, constraint]\n"
            "    required_artifacts:\n"
            "      - invariant_list\n"
            "      - typed_ir_or_contract_coverage\n"
            "      - property_based_or_differential_tests\n"
        ),
    ),
    (
        "FM3-not-superset-of-FM2",
        (
            "  - id: FM3\n    name: Stateful / Control Semantics\n"
            "    scope: State machines, branching, retries, joins, re-entry, lifecycle semantics, result contracts.\n"
            "    change_categories: [stateful, control]\n"
            "    required_artifacts:\n"
            "      - invariant_list\n"
            "      - unit_tests\n"
            "      - typed_ir_or_contract_coverage\n"
            "      - property_based_or_differential_tests\n"
            "      - abstract_state_machine_model\n"
        ),
        (
            "  - id: FM3\n    name: Stateful / Control Semantics\n"
            "    scope: State machines, branching, retries, joins, re-entry, lifecycle semantics, result contracts.\n"
            "    change_categories: [stateful, control]\n"
            "    required_artifacts:\n"
            "      - invariant_list\n"
            "      - unit_tests\n"
            "      - property_based_or_differential_tests\n"
            "      - abstract_state_machine_model\n"
        ),
    ),
]


@pytest.mark.parametrize(
    ("case_id", "old", "new"),
    _PROPORTIONALITY_BREAK_CASES,
    ids=[case[0] for case in _PROPORTIONALITY_BREAK_CASES],
)
def test_proportionality_break_is_flagged(tmp_path: Path, case_id: str, old: str, new: str) -> None:
    body = _GOOD_POLICY.replace(old, new, 1)
    assert body != _GOOD_POLICY, f"setup error for case {case_id}"
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-proportionality")


def test_fm0_missing_tla_plus_in_prohibited_artifacts(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace(
        "    prohibited_artifacts: [TLA+, Alloy]\n",
        "    prohibited_artifacts: [Alloy]\n",
        1,
    )
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-fm0-prohibited")


def test_fm0_missing_alloy_in_prohibited_artifacts(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace(
        "    prohibited_artifacts: [TLA+, Alloy]\n",
        "    prohibited_artifacts: [TLA+]\n",
        1,
    )
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-fm0-prohibited")


# ----------------------------------------------------------------------------- #
# Required-artifact floor (per ADR-007) -- a YAML edit that drops a required    #
# artifact below the floor fails the gate. The proportionality check alone      #
# would let "everything is unit_tests" pass.                                    #
# ----------------------------------------------------------------------------- #


_REQUIRED_FLOOR_CASES = [
    (
        "FM1-loses-invariants",
        "  - id: FM1\n    name: Static Semantic\n    scope: Cross-references, uniqueness, ambiguity, acyclicity, fail-closed resolution.\n    change_categories: [semantic]\n    required_artifacts: [invariant_list, unit_tests]\n    recommended_artifacts: [property_based_tests]\n",
        "  - id: FM1\n    name: Static Semantic\n    scope: Cross-references, uniqueness, ambiguity, acyclicity, fail-closed resolution.\n    change_categories: [semantic]\n    required_artifacts: [unit_tests]\n    recommended_artifacts: [property_based_tests]\n",
    ),
    (
        "FM2-loses-typed-ir",
        "      - typed_ir_or_contract_coverage\n      - property_based_or_differential_tests\n  - id: FM3",
        "      - property_based_or_differential_tests\n  - id: FM3",
    ),
    (
        "FM3-loses-abstract-state-machine-model",
        "      - property_based_or_differential_tests\n      - abstract_state_machine_model\n    recommended_artifacts: [TLA+, Alloy]\n",
        "      - property_based_or_differential_tests\n    recommended_artifacts: [TLA+, Alloy]\n",
    ),
]


@pytest.mark.parametrize(
    ("case_id", "old", "new"),
    _REQUIRED_FLOOR_CASES,
    ids=[case[0] for case in _REQUIRED_FLOOR_CASES],
)
def test_required_artifact_floor_is_enforced(tmp_path: Path, case_id: str, old: str, new: str) -> None:
    body = _GOOD_POLICY.replace(old, new, 1)
    assert body != _GOOD_POLICY, f"setup error for case {case_id}"
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-required-floor")


def test_required_and_prohibited_overlap_is_flagged(tmp_path: Path) -> None:
    # If a level lists unit_tests as both required and prohibited, that's
    # an internal contradiction. Proportionality alone would not catch it.
    body = _GOOD_POLICY.replace(
        "    prohibited_artifacts: [TLA+, Alloy]\n",
        "    prohibited_artifacts: [TLA+, Alloy, unit_tests]\n",
        1,
    )
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-required-prohibited-overlap")


# ----------------------------------------------------------------------------- #
# Category-to-level binding -- the validator pins which level owns which        #
# canonical category, so reordering "structural" onto FM3 (or dropping it)      #
# fails the gate.                                                               #
# ----------------------------------------------------------------------------- #


_CATEGORY_BINDING_CASES = [
    ("FM0-loses-structural", "    change_categories: [structural]\n", "    change_categories: [shape]\n"),
    ("FM1-loses-semantic", "    change_categories: [semantic]\n", "    change_categories: [static]\n"),
    ("FM2-loses-graph", "    change_categories: [graph, constraint]\n", "    change_categories: [constraint]\n"),
    ("FM3-loses-stateful", "    change_categories: [stateful, control]\n", "    change_categories: [control]\n"),
]


@pytest.mark.parametrize(
    ("case_id", "old", "new"),
    _CATEGORY_BINDING_CASES,
    ids=[case[0] for case in _CATEGORY_BINDING_CASES],
)
def test_category_to_level_binding_is_enforced(tmp_path: Path, case_id: str, old: str, new: str) -> None:
    body = _GOOD_POLICY.replace(old, new, 1)
    assert body != _GOOD_POLICY, f"setup error for case {case_id}: old string not found in _GOOD_POLICY"
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-categories")


# ----------------------------------------------------------------------------- #
# Pointing refs: ASR-505 in requirement_refs, ADR-007 in adr_refs.              #
# ----------------------------------------------------------------------------- #


def test_missing_asr_505_in_requirement_refs(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace("  - ASR-505\n", "  - ASR-999\n", 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-requirement-ref")


def test_missing_adr_007_in_adr_refs(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace("  - ADR-007\n", "  - ADR-999\n", 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-adr-ref")


def test_missing_adr_018_in_adr_refs(tmp_path: Path) -> None:
    body = _GOOD_POLICY.replace("  - ADR-018\n", "", 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-adr-ref")
    assert _flagged(failures, "ADR-018")


# ----------------------------------------------------------------------------- #
# Doc drift -- each downstream doc must mention every canonical level id AND    #
# every canonical level name. The drift guard catches both kinds of regression. #
# ----------------------------------------------------------------------------- #


def test_adr_missing_level_id_is_flagged(tmp_path: Path) -> None:
    body = _GOOD_ADR.replace("FM2 (Semantic Graph / Constraint), and ", "", 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, adr_body=body))
    assert _flagged(failures, "assurance-policy-adr-drift")


def test_adr_missing_canonical_name_is_flagged(tmp_path: Path) -> None:
    # The ADR text still has 'FM2', but the canonical name has been changed --
    # this is the exact drift mode (FM2 labeled "Dynamic Semantic Rules" while
    # still saying "FM2") that ADR-018's drift guard was created to catch.
    body = _GOOD_ADR.replace("Semantic Graph / Constraint", "Dynamic Semantic Rules", 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, adr_body=body))
    assert _flagged(failures, "assurance-policy-adr-drift")


def test_coding_standards_missing_canonical_name_is_flagged(tmp_path: Path) -> None:
    body = _GOOD_CODING_STANDARDS.replace("Stateful / Control Semantics", "Cross-System Contracts", 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, coding_standards_body=body))
    assert _flagged(failures, "assurance-policy-coding-standards-drift")


def test_formal_overview_missing_canonical_name_is_flagged(tmp_path: Path) -> None:
    body = _GOOD_FORMAL_OVERVIEW.replace("Static Semantic", "Static Rules", 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, formal_overview_body=body))
    assert _flagged(failures, "assurance-policy-formal-overview-drift")


def test_drift_guard_catches_swapped_pair(tmp_path: Path) -> None:
    # Both 'FM2' and the canonical name 'Semantic Graph / Constraint' still
    # appear in the doc, but they are no longer co-located -- the FM2 row in
    # the table has been bound to 'Stateful / Control Semantics' (a real
    # canonical name belonging to FM3) and vice-versa. The presence-only
    # guards would miss this; the paired check catches it.
    bad_overview = """# Formal Specifications

| Level | Name |
|-------|------|
| FM0 | Structural |
| FM1 | Static Semantic |
| FM2 | Stateful / Control Semantics |
| FM3 | Semantic Graph / Constraint |
"""
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, formal_overview_body=bad_overview))
    assert _flagged(failures, "assurance-policy-formal-overview-drift")
    # The failure mentions the paired-co-location language so it is
    # distinguishable from raw "missing id/name" failures.
    assert any("not co-located" in failure.message for failure in failures), (
        f"expected a paired-drift failure, got {[failure.render() for failure in failures]}"
    )


def test_coding_standards_missing_artifact_keyword_is_flagged(tmp_path: Path) -> None:
    # The YAML requires `typed_ir_or_contract_coverage` for FM2/FM3. The
    # mutable doc must mention at least one keyword variant ("typed IR" or
    # "contract coverage"). A stub that names every level but mentions only
    # unit tests + invariants + property-based + abstract state-machine
    # (deliberately omitting both "typed IR" and "contract coverage")
    # triggers the gate.
    stale_coding_standards = """# Coding Standards

The classification levels are FM0 Structural, FM1 Static Semantic,
FM2 Semantic Graph / Constraint, and FM3 Stateful / Control Semantics.

Required artifacts: unit tests, invariants, property-based or differential
tests, and an abstract state-machine model.
"""
    # Belt-and-braces: confirm no keyword variant for the slug survives.
    assert "typed IR" not in stale_coding_standards
    assert "contract coverage" not in stale_coding_standards
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, coding_standards_body=stale_coding_standards))
    assert _flagged(failures, "assurance-policy-coding-standards-drift")
    assert any("typed_ir_or_contract_coverage" in failure.message for failure in failures)


def test_formal_overview_missing_artifact_keyword_is_flagged(tmp_path: Path) -> None:
    # Same shape as the coding-standards check: a stub that names every
    # level but deliberately omits both "typed IR" and "contract coverage"
    # triggers the gate.
    stale_overview = """# Formal Specifications

| Level | Name | Required artifacts |
|-------|------|--------------------|
| FM0 | Structural | unit tests |
| FM1 | Static Semantic | invariants + unit tests |
| FM2 | Semantic Graph / Constraint | FM1 + property-based or differential tests |
| FM3 | Stateful / Control Semantics | FM2 + abstract state-machine model |
"""
    assert "typed IR" not in stale_overview
    assert "contract coverage" not in stale_overview
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, formal_overview_body=stale_overview))
    assert _flagged(failures, "assurance-policy-formal-overview-drift")
    assert any("typed_ir_or_contract_coverage" in failure.message for failure in failures)


def test_adr_007_immutable_doc_is_exempt_from_artifact_keyword_drift(tmp_path: Path) -> None:
    # ADR-007 doesn't need to mention every required artifact. The mutable
    # docs do. Strip every artifact keyword from the ADR stub; the artifact-
    # keyword drift guard must stay quiet for that doc.
    minimal_adr = """# ADR-007: Lightweight Formal Methods Policy

## Status
accepted

## Decision
The classification ladder is FM0 (Structural), FM1 (Static Semantic),
FM2 (Semantic Graph / Constraint), and FM3 (Stateful / Control Semantics).
"""
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, adr_body=minimal_adr))
    assert not _flagged(failures, "assurance-policy-adr-drift")


_MISSING_DOC_CASES = [
    ("adr-missing", {"adr_body": None}, "assurance-policy-adr-missing"),
    ("coding-standards-missing", {"coding_standards_body": None}, "assurance-policy-coding-standards-missing"),
    ("formal-overview-missing", {"formal_overview_body": None}, "assurance-policy-formal-overview-missing"),
]


@pytest.mark.parametrize(
    ("case_id", "kwargs", "rule_id"),
    _MISSING_DOC_CASES,
    ids=[case[0] for case in _MISSING_DOC_CASES],
)
def test_missing_referencing_doc_is_flagged(tmp_path: Path, case_id: str, kwargs: dict, rule_id: str) -> None:
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, **kwargs))
    assert _flagged(failures, rule_id)


# ----------------------------------------------------------------------------- #
# Drift expectations derive from the YAML -- adding a level beyond FM3 makes    #
# every downstream doc obligated to mention it (and its canonical name).        #
# ----------------------------------------------------------------------------- #


_GOOD_FM4_BLOCK = (
    "  - id: FM4\n"
    "    name: Concurrent / Distributed Semantics\n"
    "    scope: Multi-process state, message ordering, distributed commit.\n"
    "    change_categories: [stateful, control, distributed]\n"
    "    required_artifacts:\n"
    "      - invariant_list\n"
    "      - unit_tests\n"
    "      - typed_ir_or_contract_coverage\n"
    "      - property_based_or_differential_tests\n"
    "      - abstract_state_machine_model\n"
    "      - distributed_state_machine_model\n"
)


def test_adding_fm4_to_yaml_requires_mutable_downstream_docs_to_mention_it(tmp_path: Path) -> None:
    # ADR-007 is immutable -- it must mention FM0..FM3 only. Adding FM4 to
    # the YAML therefore obligates the MUTABLE docs (coding-standards.md and
    # docs/specs/formal.md) but not ADR-007.
    body = _GOOD_POLICY + _GOOD_FM4_BLOCK
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-coding-standards-drift")
    assert _flagged(failures, "assurance-policy-formal-overview-drift")
    assert _flagged(failures, "FM4")


def test_adding_fm4_to_yaml_does_not_require_immutable_adr_007_to_mention_it(tmp_path: Path) -> None:
    # The mirror invariant of the test above: ADR-007's drift guard must NOT
    # fire on FM4-only additions, because ADR-007 is immutable. ADR-018 (and
    # any future superseding ADR) is the canonical seam for extending the
    # ladder.
    body = _GOOD_POLICY + _GOOD_FM4_BLOCK
    # Also extend the mutable docs so their drift guards stay quiet -- this
    # isolates the ADR-007 guard. We append a short mention with the canonical
    # name so the paired-co-location check passes.
    coding_standards_with_fm4 = (
        _GOOD_CODING_STANDARDS.rstrip() + "\nThe extended ladder now includes FM4 Concurrent / Distributed Semantics.\n"
    )
    formal_overview_with_fm4 = _GOOD_FORMAL_OVERVIEW.rstrip() + "\n| FM4 | Concurrent / Distributed Semantics |\n"
    failures = evaluate_assurance_policy(
        _seed_repo(
            tmp_path,
            policy_body=body,
            coding_standards_body=coding_standards_with_fm4,
            formal_overview_body=formal_overview_with_fm4,
        )
    )
    # Coding-standards and formal-overview drift guards must be quiet now.
    assert not _flagged(failures, "assurance-policy-coding-standards-drift")
    assert not _flagged(failures, "assurance-policy-formal-overview-drift")
    # ADR-007 drift guard must stay quiet -- it is not required to mention FM4.
    assert not _flagged(failures, "assurance-policy-adr-drift")


def test_fm4_inserted_before_fm3_is_flagged_as_out_of_order(tmp_path: Path) -> None:
    # Insert the FM4 block BEFORE FM3 in the levels list. The numeric order
    # check must fail (FM2 → FM4 → FM3 is not ascending).
    insertion_marker = "  - id: FM3\n"
    body = _GOOD_POLICY.replace(insertion_marker, _GOOD_FM4_BLOCK + insertion_marker, 1)
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-level-order")


def test_fm4_with_artifacts_not_superset_of_fm3_is_flagged(tmp_path: Path) -> None:
    # Add an FM4 block at the end whose required_artifacts drops one of
    # FM3's. The consecutive-pair proportionality check must fire across
    # every FM-numbered pair, not just FM2 → FM3.
    bad_fm4 = (
        "  - id: FM4\n"
        "    name: Concurrent / Distributed Semantics\n"
        "    scope: Multi-process state, message ordering, distributed commit.\n"
        "    change_categories: [stateful, control, distributed]\n"
        "    required_artifacts:\n"
        "      - invariant_list\n"
        "      - unit_tests\n"
        "      - typed_ir_or_contract_coverage\n"
        "      - property_based_or_differential_tests\n"
        # `abstract_state_machine_model` is intentionally omitted -- FM4 is
        # not a superset of FM3.
        "      - distributed_state_machine_model\n"
    )
    body = _GOOD_POLICY + bad_fm4
    failures = evaluate_assurance_policy(_seed_repo(tmp_path, policy_body=body))
    assert _flagged(failures, "assurance-policy-proportionality")
    assert _flagged(failures, "FM4")


# ----------------------------------------------------------------------------- #
# ADR classification and per-change FM ledger.                                  #
# ----------------------------------------------------------------------------- #


def test_new_adr_without_classification_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    _write(
        repo / f"docs/decisions/adrs/adr-{ADR_CLASSIFICATION_REQUIRED_FROM:03d}-new-semantic-surface.md",
        _new_adr_body(classification=None),
    )

    failures = evaluate_assurance_policy(repo)

    assert _flagged(failures, "adr-classification-missing")


def test_new_adr_with_unknown_fm_level_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    _write(
        repo / f"docs/decisions/adrs/adr-{ADR_CLASSIFICATION_REQUIRED_FROM:03d}-new-semantic-surface.md",
        _new_adr_body(classification="FM9"),
    )

    failures = evaluate_assurance_policy(repo)

    assert _flagged(failures, "adr-classification-level")
    assert _flagged(failures, "FM9")


def test_new_adr_missing_required_artifacts_line_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    _write(
        repo / f"docs/decisions/adrs/adr-{ADR_CLASSIFICATION_REQUIRED_FROM:03d}-new-semantic-surface.md",
        _new_adr_body(artifacts=None),
    )

    failures = evaluate_assurance_policy(repo)

    assert _flagged(failures, "adr-classification-artifacts")


def test_adr_template_missing_classification_field_is_flagged(tmp_path: Path) -> None:
    template = _GOOD_ADR_TEMPLATE.replace("Classification: FM<n>\n", "", 1)

    failures = evaluate_assurance_policy(_seed_repo(tmp_path, adr_template_body=template))

    assert _flagged(failures, "adr-template-classification")


def test_ledger_missing_existing_runtime_surface_entry_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(
        tmp_path,
        ledger_body=(
            f"ledger: per-change-fm-classification\npolicy_ref: {ASSURANCE_POLICY_RELATIVE_PATH}\nentries:\n"
            f"{_ledger_entry('ADR-023')}"
        ),
    )
    _seed_runtime_surface(repo, "ADR-023")
    _seed_runtime_surface(repo, "ADR-024")

    failures = evaluate_assurance_policy(repo)

    assert _flagged(failures, "fm-classification-ledger-coverage")
    assert _flagged(failures, "ADR-024")


def test_ledger_fm_level_must_resolve_to_policy_yaml(tmp_path: Path) -> None:
    repo = _seed_repo(
        tmp_path,
        ledger_body=(
            f"ledger: per-change-fm-classification\npolicy_ref: {ASSURANCE_POLICY_RELATIVE_PATH}\nentries:\n"
            f"{_ledger_entry(fm_level='FM9')}"
        ),
    )
    _seed_runtime_surface(repo)

    failures = evaluate_assurance_policy(repo)

    assert _flagged(failures, "fm-classification-ledger-level")
    assert _flagged(failures, "FM9")


def test_ledger_required_artifacts_must_be_delivered_or_waived(tmp_path: Path) -> None:
    repo = _seed_repo(
        tmp_path,
        ledger_body=(
            f"ledger: per-change-fm-classification\npolicy_ref: {ASSURANCE_POLICY_RELATIVE_PATH}\nentries:\n"
            f"{_ledger_entry(include_unit_test=False)}"
        ),
    )
    _seed_runtime_surface(repo)

    failures = evaluate_assurance_policy(repo)

    assert _flagged(failures, "fm-classification-ledger-artifacts")
    assert _flagged(failures, "unit_tests")


# ----------------------------------------------------------------------------- #
# Real-repo invariant -- the actual checked-in YAML and docs must be clean.     #
# ----------------------------------------------------------------------------- #


def test_real_repo_assurance_policy_is_clean() -> None:
    failures = evaluate_assurance_policy(REPO_ROOT)
    assert failures == []


# --------------------------------------------------------------------------- #
# Assurance fulfillment map (issue #485). Per classified formal-spec           #
# subsystem, every required artifact kind for its FM level must be delivered   #
# (a concrete non-empty repo path) or waived (ISO date + tracking ref).        #
# --------------------------------------------------------------------------- #


def _seed_classified_domain(repo: Path, domain: str) -> None:
    """Create specs/formal/<domain>/README.md so the coverage scan classifies it."""
    _write(repo / "specs" / "formal" / domain / "README.md", f"# {domain}\n\nInvariants under study.\n")


def _fulfillment_body(
    *,
    subsystems: list,
    entries: list,
    fulfillment: str = "classification-based-assurance-fulfillment",
    policy_ref: str = ASSURANCE_POLICY_RELATIVE_PATH,
    adr_refs=("ADR-007", "ADR-018"),
) -> str:
    return yaml.safe_dump(
        {
            "fulfillment": fulfillment,
            "policy_ref": policy_ref,
            "adr_refs": list(adr_refs),
            "subsystems": subsystems,
            "entries": entries,
        },
        sort_keys=False,
    )


def _reg(sub_id: str, path: str, fm_level: str = "FM1") -> dict:
    return {"id": sub_id, "path": path, "fm_level": fm_level}


def _entry(subsystem: str, *, delivered=(), waived=()) -> dict:
    return {
        "subsystem": subsystem,
        "delivered_artifacts": [{"kind": k, "path": p} for k, p in delivered],
        "waived_artifacts": [dict(w) for w in waived],
    }


def _seed_demo_repo(tmp_path: Path) -> Path:
    """Repo with one classified FM1 domain 'demo' and a real unit-test file."""
    repo = _seed_repo(tmp_path, fulfillment_body=None)
    _seed_classified_domain(repo, "demo")
    _write(repo / "implementations/python/tests/test_demo.py", "def test_x():\n    assert True\n")
    return repo


_DEMO_DELIVERED = (
    ("invariant_list", "specs/formal/demo/README.md"),
    ("unit_tests", "implementations/python/tests/test_demo.py"),
)


def _write_fulfillment(repo: Path, body: str) -> None:
    (repo / ASSURANCE_FULFILLMENT_RELATIVE_PATH).write_text(body, encoding="utf-8")


def test_good_single_domain_fulfillment_is_clean(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[_entry("demo", delivered=_DEMO_DELIVERED)],
        ),
    )
    assert evaluate_assurance_policy(repo) == []


def test_fulfillment_missing_file_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body=None)
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-missing")


def test_fulfillment_unparseable_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body="fulfillment: [unclosed\n")
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-parse")


def test_fulfillment_non_mapping_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body="- a\n- b\n")
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-shape")


def test_fulfillment_wrong_marker_field_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body=_fulfillment_body(subsystems=[], entries=[], fulfillment="wrong"))
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-field")


def test_fulfillment_wrong_policy_ref_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body=_fulfillment_body(subsystems=[], entries=[], policy_ref="wrong.yaml"))
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-field")


def test_fulfillment_missing_adr_ref_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body=_fulfillment_body(subsystems=[], entries=[], adr_refs=("ADR-007",)))
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-field")


def test_classified_subsystem_absent_from_registry_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body=None)
    _seed_classified_domain(repo, "demo")
    _write_fulfillment(repo, _fulfillment_body(subsystems=[], entries=[]))
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-coverage")
    assert _flagged(failures, "demo")


def test_registry_subsystem_without_entry_is_flagged(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(repo, _fulfillment_body(subsystems=[_reg("demo", "specs/formal/demo")], entries=[]))
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-entry-missing")


def test_entry_for_unknown_subsystem_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body=None)
    _write_fulfillment(repo, _fulfillment_body(subsystems=[], entries=[_entry("ghost")]))
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-entry-unknown")


def test_registry_fm_level_must_resolve_to_policy_yaml(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM9")],
            entries=[_entry("demo", delivered=_DEMO_DELIVERED)],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-level")
    assert _flagged(failures, "FM9")


def test_registry_path_must_exist_as_formal_domain(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body=None)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[_entry("demo")],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-subsystem")


def test_registry_path_escaping_repo_is_flagged(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path, fulfillment_body=None)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "../outside", "FM1")],
            entries=[_entry("demo")],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-subsystem")


def test_registry_path_outside_specs_formal_is_flagged(tmp_path: Path) -> None:
    # A directory that exists and carries a README but lives outside
    # specs/formal/<domain>/ is NOT a classified formal subsystem; the registry
    # must reject it rather than accept any repo dir that happens to hold a README.
    repo = _seed_demo_repo(tmp_path)
    _write(repo / "docs" / "notes" / "README.md", "# not a formal domain\n")
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[
                _reg("demo", "specs/formal/demo", "FM1"),
                _reg("rogue", "docs/notes", "FM1"),
            ],
            entries=[
                _entry("demo", delivered=_DEMO_DELIVERED),
                _entry("rogue", delivered=_DEMO_DELIVERED),
            ],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-subsystem")


def test_registry_nested_specs_formal_path_is_flagged(tmp_path: Path) -> None:
    # Only immediate specs/formal/<domain>/ directories are classified subsystems;
    # a deeper nested path under a domain is not a registry-valid domain path.
    repo = _seed_demo_repo(tmp_path)
    _write(repo / "specs" / "formal" / "demo" / "sub" / "README.md", "# nested\n")
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo/sub", "FM1")],
            entries=[_entry("demo", delivered=_DEMO_DELIVERED)],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-subsystem")


def test_registry_duplicate_path_alias_is_flagged(tmp_path: Path) -> None:
    # Two registry entries pointing at the same formal-domain directory is an
    # alias that would let one domain be double-counted; it must be rejected.
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[
                _reg("demo", "specs/formal/demo", "FM1"),
                _reg("demo-alias", "specs/formal/demo", "FM1"),
            ],
            entries=[
                _entry("demo", delivered=_DEMO_DELIVERED),
                _entry("demo-alias", delivered=_DEMO_DELIVERED),
            ],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-subsystem")


def test_registry_duplicate_subsystem_id_is_flagged(tmp_path: Path) -> None:
    # Two registry entries sharing the same `id` (each pointing at a distinct
    # classified domain) is ambiguous: only the first would bind in the registry
    # map, silently shadowing the second. The `seen_ids` duplicate-id check must
    # reject it; without this case that check would be dead to the suite.
    repo = _seed_demo_repo(tmp_path)
    _seed_classified_domain(repo, "other")
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[
                _reg("demo", "specs/formal/demo", "FM1"),
                _reg("demo", "specs/formal/other", "FM1"),
            ],
            entries=[_entry("demo", delivered=_DEMO_DELIVERED)],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-subsystem")
    assert any("duplicate subsystem id" in failure.message for failure in failures), (
        f"expected a duplicate-subsystem-id failure, got {[failure.render() for failure in failures]}"
    )


def test_delivered_path_missing_is_flagged(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(
                        ("invariant_list", "specs/formal/demo/README.md"),
                        ("unit_tests", "implementations/python/tests/test_missing.py"),
                    ),
                )
            ],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-artifact")


def test_delivered_path_escaping_repo_is_flagged(tmp_path: Path) -> None:
    # A delivered-artifact path that escapes the repo root must be rejected by
    # the `safe_repo_path` boundary, NOT by the "does not exist" branch. The
    # escape target is a real file OUTSIDE the repo root, so a naive
    # `Path(path).is_file()` check would accept it and silently count the kind
    # as delivered; only a genuine escape guard rejects it. This mirrors the
    # subsystem-path escape test for the delivered-artifact code path.
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_demo_repo(repo)
    outside = tmp_path / "outside.py"
    outside.write_text("def test_x():\n    assert True\n", encoding="utf-8")
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(
                        ("invariant_list", "specs/formal/demo/README.md"),
                        ("unit_tests", "../outside.py"),
                    ),
                )
            ],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-artifact")
    assert any("escapes the repo root" in failure.message for failure in failures), (
        f"expected a delivered-path escape failure, got {[failure.render() for failure in failures]}"
    )
    # The escaping path must not count as delivered, so the required kind is left
    # unsatisfied -- proving the escape was rejected, not merely accepted-but-noted.
    assert _flagged(failures, "assurance-fulfillment-artifacts")
    assert _flagged(failures, "unit_tests")


def test_delivered_empty_path_is_flagged(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    (repo / "specs/formal/demo/empty.md").write_text("", encoding="utf-8")
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(
                        ("invariant_list", "specs/formal/demo/empty.md"),
                        ("unit_tests", "implementations/python/tests/test_demo.py"),
                    ),
                )
            ],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-artifact")
    assert _flagged(failures, "empty")


def test_delivered_unknown_kind_is_flagged(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(
                        ("invariant_list", "specs/formal/demo/README.md"),
                        ("unit_tests", "implementations/python/tests/test_demo.py"),
                        ("bogus_kind", "specs/formal/demo/README.md"),
                    ),
                )
            ],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-artifact")
    assert _flagged(failures, "bogus_kind")


def test_waiver_missing_date_is_flagged(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(("invariant_list", "specs/formal/demo/README.md"),),
                    waived=({"kind": "unit_tests", "tracking": ["#1"], "rationale": "pending"},),
                )
            ],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-waiver")


def test_waiver_missing_tracking_is_flagged(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(("invariant_list", "specs/formal/demo/README.md"),),
                    waived=({"kind": "unit_tests", "date": "2026-06-13", "rationale": "pending"},),
                )
            ],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-waiver")


def test_waiver_empty_tracking_list_is_flagged(tmp_path: Path) -> None:
    # An explicitly empty `tracking: []` list (distinct from an absent key) must
    # be rejected: the contract requires at least one tracking reference. Without
    # this case, weakening the guard from "≥1 ref" to "key present" would go
    # undetected.
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(("invariant_list", "specs/formal/demo/README.md"),),
                    waived=({"kind": "unit_tests", "date": "2026-06-13", "tracking": [], "rationale": "pending"},),
                )
            ],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-waiver")
    # The empty-tracking waiver does not count, so the required kind stays unmet.
    assert _flagged(failures, "assurance-fulfillment-artifacts")
    assert _flagged(failures, "unit_tests")


def test_waiver_missing_rationale_is_flagged(tmp_path: Path) -> None:
    # A waiver that supplies a valid date and tracking ref but omits the
    # rationale must be rejected: an unjustified waiver may not silently satisfy
    # a required artifact kind. Without this case the `rationale_ok` guard in
    # `_check_fulfillment_waived` could be removed undetected.
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(("invariant_list", "specs/formal/demo/README.md"),),
                    waived=({"kind": "unit_tests", "date": "2026-06-13", "tracking": ["#1"]},),
                )
            ],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-waiver")
    # The unjustified waiver does not count, so the required kind is unsatisfied.
    assert _flagged(failures, "assurance-fulfillment-artifacts")
    assert _flagged(failures, "unit_tests")


def test_required_kind_neither_delivered_nor_waived_is_flagged(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[_entry("demo", delivered=(("invariant_list", "specs/formal/demo/README.md"),))],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-artifacts")
    assert _flagged(failures, "unit_tests")


def test_dated_tracked_waiver_satisfies_required_kind(tmp_path: Path) -> None:
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(("invariant_list", "specs/formal/demo/README.md"),),
                    waived=(
                        {
                            "kind": "unit_tests",
                            "date": "2026-06-13",
                            "tracking": ["#1"],
                            "rationale": "executable tests pending",
                        },
                    ),
                )
            ],
        ),
    )
    assert evaluate_assurance_policy(repo) == []


def test_native_yaml_date_waiver_is_accepted(tmp_path: Path) -> None:
    # An unquoted YAML date (`date: 2026-06-13`) parses to datetime.date, not a
    # string; the gate must accept it rather than force every author to quote.
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(("invariant_list", "specs/formal/demo/README.md"),),
                    waived=(
                        {
                            "kind": "unit_tests",
                            "date": datetime.date(2026, 6, 13),
                            "tracking": ["#1"],
                            "rationale": "executable tests pending",
                        },
                    ),
                )
            ],
        ),
    )
    assert evaluate_assurance_policy(repo) == []


def test_native_yaml_timestamp_waiver_is_flagged(tmp_path: Path) -> None:
    # A YAML timestamp scalar (`date: 2026-06-13 10:30:00`) parses to
    # datetime.datetime, a subclass of datetime.date. The waiver contract requires
    # a date-only YYYY-MM-DD value, so a wall-clock timestamp must be rejected
    # rather than slip through the date subclass check.
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(("invariant_list", "specs/formal/demo/README.md"),),
                    waived=(
                        {
                            "kind": "unit_tests",
                            "date": datetime.datetime(2026, 6, 13, 10, 30, 0),
                            "tracking": ["#1"],
                            "rationale": "executable tests pending",
                        },
                    ),
                )
            ],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-waiver")


def test_waiver_with_impossible_calendar_date_is_flagged(tmp_path: Path) -> None:
    # A string date that matches the YYYY-MM-DD shape but is not a real calendar
    # date (month 13, day 45) must be rejected -- a shape match alone must not
    # satisfy the waiver-date contract.
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(("invariant_list", "specs/formal/demo/README.md"),),
                    waived=(
                        {
                            "kind": "unit_tests",
                            "date": "2025-13-45",
                            "tracking": ["#1"],
                            "rationale": "executable tests pending",
                        },
                    ),
                )
            ],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    # The impossible date fails the waiver-date contract, so the waiver does not
    # count and the required kind is left unsatisfied.
    assert _flagged(failures, "assurance-fulfillment-waiver")
    assert _flagged(failures, "assurance-fulfillment-artifacts")


def test_waiver_with_invalid_day_of_month_is_flagged(tmp_path: Path) -> None:
    # 2025-02-30 is shape-valid but not a real date; it must be rejected.
    repo = _seed_demo_repo(tmp_path)
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("demo", "specs/formal/demo", "FM1")],
            entries=[
                _entry(
                    "demo",
                    delivered=(("invariant_list", "specs/formal/demo/README.md"),),
                    waived=(
                        {
                            "kind": "unit_tests",
                            "date": "2025-02-30",
                            "tracking": ["#1"],
                            "rationale": "executable tests pending",
                        },
                    ),
                )
            ],
        ),
    )
    assert _flagged(evaluate_assurance_policy(repo), "assurance-fulfillment-waiver")


def test_fm3_domain_requires_abstract_state_machine_model(tmp_path: Path) -> None:
    # An FM3 domain that does not deliver or waive abstract_state_machine_model
    # (an FM3-only required kind derived from the policy YAML) fails.
    repo = _seed_repo(tmp_path, fulfillment_body=None)
    _seed_classified_domain(repo, "stateful")
    _write(repo / "implementations/python/tests/test_stateful.py", "def test_x():\n    assert True\n")
    _write(repo / "contracts/schemas/stateful-v1.json", "{}\n")
    delivered = (
        ("invariant_list", "specs/formal/stateful/README.md"),
        ("unit_tests", "implementations/python/tests/test_stateful.py"),
        ("typed_ir_or_contract_coverage", "contracts/schemas/stateful-v1.json"),
        ("property_based_or_differential_tests", "implementations/python/tests/test_stateful.py"),
    )
    _write_fulfillment(
        repo,
        _fulfillment_body(
            subsystems=[_reg("stateful", "specs/formal/stateful", "FM3")],
            entries=[_entry("stateful", delivered=delivered)],
        ),
    )
    failures = evaluate_assurance_policy(repo)
    assert _flagged(failures, "assurance-fulfillment-artifacts")
    assert _flagged(failures, "abstract_state_machine_model")
