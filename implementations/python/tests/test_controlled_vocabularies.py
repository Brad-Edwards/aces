"""Controlled vocabulary catalog tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_contracts.contracts import AttackEnterpriseTacticsSourceModel, ControlledVocabularyCatalogModel
from aces_contracts.controlled_vocabularies import (
    controlled_vocabulary_catalog_path,
    load_controlled_vocabulary_catalog,
    validate_controlled_vocabulary_scope_values,
    validate_controlled_vocabulary_value,
)
from aces_contracts.vocabulary import (
    ConceptProvenanceCategory,
    ParticipantFeatureSupportLevel,
    ProcessorFeature,
    RealizationSupportMode,
    WorkflowFeature,
    WorkflowStatePredicateFeature,
)
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "contracts" / "concept-authority" / "controlled-vocabularies-v1.json"
ATTACK_TACTICS_SOURCE_PATH = REPO_ROOT / "contracts" / "concept-authority" / "attack-enterprise-tactics-source-v1.json"
FIXTURES_ROOT = REPO_ROOT / "contracts" / "fixtures" / "concept-authority" / "controlled-vocabularies-v1"
VALID_DIR = FIXTURES_ROOT / "valid"
INVALID_DIR = FIXTURES_ROOT / "invalid"
ATTACK_ENTERPRISE_TACTIC_TERMS_V19_1 = [
    ("reconnaissance", "TA0043", "Reconnaissance"),
    ("resource-development", "TA0042", "Resource Development"),
    ("initial-access", "TA0001", "Initial Access"),
    ("execution", "TA0002", "Execution"),
    ("persistence", "TA0003", "Persistence"),
    ("privilege-escalation", "TA0004", "Privilege Escalation"),
    ("stealth", "TA0005", "Stealth"),
    ("defense-impairment", "TA0112", "Defense Impairment"),
    ("credential-access", "TA0006", "Credential Access"),
    ("discovery", "TA0007", "Discovery"),
    ("lateral-movement", "TA0008", "Lateral Movement"),
    ("collection", "TA0009", "Collection"),
    ("command-and-control", "TA0011", "Command and Control"),
    ("exfiltration", "TA0010", "Exfiltration"),
    ("impact", "TA0040", "Impact"),
]


def test_load_controlled_vocabulary_catalog():
    catalog = load_controlled_vocabulary_catalog()

    assert catalog.schema_version == "controlled-vocabularies/v1"
    assert set(catalog.vocabularies) >= {
        "processor-features",
        "participant-implementation-kinds",
        "participant-decision-surface-modes",
        "participant-offensive-behavior-activities",
        "participant-tool-affordance-expectations",
        "participant-exposure-policy-kinds",
        "workflow-features",
        "workflow-state-predicate-features",
        "provisioner-node-types",
        "provisioner-os-families",
        "provisioner-content-types",
        "provisioner-account-features",
        "orchestrator-supported-sections",
        "evaluator-supported-sections",
        "realization-support-modes",
        "concept-provenance-categories",
    }


def test_controlled_vocabulary_catalog_path_resolves():
    assert controlled_vocabulary_catalog_path() == CATALOG_PATH


def test_controlled_vocabulary_catalog_matches_valid_fixture():
    payload = json.loads((VALID_DIR / "reference.json").read_text(encoding="utf-8"))
    authoritative = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    assert payload == authoritative
    assert ControlledVocabularyCatalogModel.model_validate(payload).vocabularies["processor-features"].terms


def test_attack_enterprise_tactics_source_pins_mitre_v19_1():
    payload = json.loads(ATTACK_TACTICS_SOURCE_PATH.read_text(encoding="utf-8"))
    source = AttackEnterpriseTacticsSourceModel.model_validate(payload)

    assert source.source_authority == "MITRE ATT&CK"
    assert source.source_domain == "enterprise-attack"
    assert source.source_version == "v19.1"
    assert source.source_digest == "sha256:bdf1ce86a4e604214c5076d37ae4dcb322678afc528df8492e6fdc1b554f5da3"
    assert source.retrieved_at == "2026-07-01"
    assert source.license_url == "https://attack.mitre.org/resources/legal-and-branding/terms-of-use/"
    assert source.license_notice.startswith("\u00a9 2026 The MITRE Corporation.")
    assert [(term.shortname, term.tactic_id, term.name) for term in source.tactics] == (
        ATTACK_ENTERPRISE_TACTIC_TERMS_V19_1
    )


def test_attack_enterprise_tactics_source_rejects_duplicate_ids_and_shortnames():
    payload = json.loads(ATTACK_TACTICS_SOURCE_PATH.read_text(encoding="utf-8"))
    payload["tactics"][1]["tactic_id"] = payload["tactics"][0]["tactic_id"]
    with pytest.raises(ValidationError, match="duplicate tactic_id"):
        AttackEnterpriseTacticsSourceModel.model_validate(payload)

    payload = json.loads(ATTACK_TACTICS_SOURCE_PATH.read_text(encoding="utf-8"))
    payload["tactics"][1]["shortname"] = payload["tactics"][0]["shortname"]
    with pytest.raises(ValidationError, match="duplicate shortname"):
        AttackEnterpriseTacticsSourceModel.model_validate(payload)


def test_controlled_vocabulary_valid_fixtures_pass_validation():
    for path in sorted(VALID_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        model = ControlledVocabularyCatalogModel.model_validate(payload)
        assert model.vocabularies, f"Valid vocabulary fixture {path.name} should declare vocabularies"


def test_controlled_vocabulary_invalid_fixtures_fail_validation():
    for path in sorted(INVALID_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        with pytest.raises(ValidationError):
            ControlledVocabularyCatalogModel.model_validate(payload)


def test_closed_enum_vocabularies_match_python_enums():
    catalog = load_controlled_vocabulary_catalog()

    assert set(catalog.vocabularies["processor-features"].terms) == {feature.value for feature in ProcessorFeature}
    assert set(catalog.vocabularies["workflow-features"].terms) == {feature.value for feature in WorkflowFeature}
    assert set(catalog.vocabularies["workflow-state-predicate-features"].terms) == {
        feature.value for feature in WorkflowStatePredicateFeature
    }
    assert set(catalog.vocabularies["realization-support-modes"].terms) == {
        mode.value for mode in RealizationSupportMode
    }
    assert set(catalog.vocabularies["concept-provenance-categories"].terms) == {
        category.value for category in ConceptProvenanceCategory
    }
    assert set(catalog.vocabularies["participant-runtime-feature-support-levels"].terms) == {
        level.value for level in ParticipantFeatureSupportLevel
    }


def test_governed_extension_values_are_allowed_for_extensible_vocabularies():
    validate_controlled_vocabulary_value("provisioner-node-types", "x-acme:bare-metal")
    validate_controlled_vocabulary_value("orchestrator-supported-sections", "x-acme:custom-stage")
    validate_controlled_vocabulary_value("participant-decision-surface-modes", "x-acme:swarm-control")


def test_behavior_specification_behavior_mode_scope_uses_decision_surface_vocabulary():
    validate_controlled_vocabulary_scope_values(
        "behavior_specifications.behavior_mode",
        ["autonomous", "human-supervised", "x-acme:swarm-control"],
    )


def test_behavior_specification_offensive_behavior_scope_uses_governed_vocabulary():
    validate_controlled_vocabulary_scope_values(
        "behavior_specifications.offensive_behavior_refs",
        ["reconnaissance", "defense-impairment", "stealth", "exfiltration", "x-acme:phishing-campaign"],
    )


def test_offensive_behavior_vocabulary_directly_adopts_pinned_attack_tactics():
    catalog = load_controlled_vocabulary_catalog()
    vocabulary = catalog.vocabularies["participant-offensive-behavior-activities"]

    assert vocabulary.source is not None
    assert vocabulary.source.provenance == "adopted"
    assert vocabulary.source.authority == "MITRE ATT&CK Enterprise"
    assert vocabulary.source.authority_version == "v19.1"
    assert (
        vocabulary.source.source_artifact_ref == "contracts/concept-authority/attack-enterprise-tactics-source-v1.json"
    )
    assert vocabulary.source.source_digest == "sha256:bdf1ce86a4e604214c5076d37ae4dcb322678afc528df8492e6fdc1b554f5da3"
    assert [(term_id, term.source_id, term.title) for term_id, term in vocabulary.terms.items()] == (
        ATTACK_ENTERPRISE_TACTIC_TERMS_V19_1
    )
    assert vocabulary.terms["defense-impairment"].source_url == "https://attack.mitre.org/tactics/TA0112"


def test_old_defense_evasion_tactic_is_not_a_pinned_attack_v19_1_term():
    with pytest.raises(ValueError, match="not a permitted term"):
        validate_controlled_vocabulary_scope_values(
            "behavior_specifications.offensive_behavior_refs",
            ["defense-evasion"],
        )


def test_unguarded_extension_values_are_rejected():
    with pytest.raises(ValueError, match="not a permitted term"):
        validate_controlled_vocabulary_value("provisioner-node-types", "bare-metal")


def test_extensions_are_rejected_for_closed_vocabularies():
    with pytest.raises(ValueError, match="does not allow extensions"):
        validate_controlled_vocabulary_value("realization-support-modes", "x-acme:custom-mode")
