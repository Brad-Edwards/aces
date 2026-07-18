"""Semantic policy tests for behavioral-relation claim surfaces."""

from __future__ import annotations

from copy import deepcopy

from aces_contracts.behavioral_relations import load_behavioral_relation_catalog
from tools.check_behavioral_relation_claims import (
    _validate_claim_text,
    _validate_structured_bindings,
)


def _valid_binding() -> dict[str, object]:
    return {
        "taxonomy_id": "aces-behavioral-relations",
        "taxonomy_revision": "rev2",
        "relation_id": "bounded-probe-success",
        "subject": "Named backend fixture cases",
        "left_carrier_ref": "backend-target:stub",
        "right_carrier_ref": "backend-profile:provisioning-only",
        "observation_projection_ref": "backend-conformance-case-report",
        "observation_projection_revision": "rev1",
        "quantifier_scope": "finite-cases",
        "evidence_scope": "finite",
        "evidence_boundary": "Only the two named fixture cases.",
        "assurance_status": "tested",
        "evidence_refs": ["conformance-case:manifest:valid"],
        "limitations": ["Unexecuted inputs are outside the evidence boundary."],
        "explicit_non_claims": ["Does not establish trace equivalence or bisimulation."],
    }


def test_unbound_positive_behavioral_equivalence_claim_fails():
    failures = _validate_claim_text(
        "The two backend implementations are behaviorally equivalent.",
        "docs/conformance/example.md",
    )

    assert {failure.rule_id for failure in failures} == {"behavioral-relation-unbound-positive-claim"}


def test_explicit_weaker_nonclaim_is_permitted():
    assert not _validate_claim_text(
        "The finite probe passes, but it does not establish behavioral equivalence or bisimulation.",
        "docs/conformance/example.md",
    )


def test_relation_identity_and_evidence_boundary_permit_a_scoped_claim():
    assert not _validate_claim_text(
        "Relation: `participant-projected-history-equivalence`. The two histories are equivalent only under "
        "observation projection `participant-observation-boundary/v1`; the evidence boundary is the named "
        "terminal observations in run-7.",
        "docs/conformance/example.md",
    )


def test_legacy_behavior_history_alias_is_not_a_relation_binding():
    failures = _validate_claim_text(
        '"form": "behavior-history-equivalent", "evidence_boundary": "one terminal record"',
        "implementations/python/packages/example.py",
    )

    assert failures
    assert "participant-projected-history-equivalence" in failures[0].message


def test_structured_claims_resolve_against_the_canonical_catalog():
    catalog = load_behavioral_relation_catalog()
    assert not _validate_structured_bindings(
        {"claim": _valid_binding()},
        catalog,
        "contracts/example.json",
    )

    unknown = deepcopy(_valid_binding())
    unknown["relation_id"] = "unknown-relation"
    failures = _validate_structured_bindings(
        {"claim": unknown},
        catalog,
        "contracts/example.json",
    )
    assert {failure.rule_id for failure in failures} == {"behavioral-relation-binding-invalid"}


def test_bounded_binding_cannot_be_promoted_to_universal_scope():
    catalog = load_behavioral_relation_catalog()
    promoted = deepcopy(_valid_binding())
    promoted["relation_id"] = "trace-equivalence"
    promoted["quantifier_scope"] = "all-traces"

    failures = _validate_structured_bindings(
        {"claim": promoted},
        catalog,
        "contracts/example.json",
    )
    assert failures
    assert "universal quantification" in failures[0].message
