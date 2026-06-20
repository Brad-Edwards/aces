"""UCO alignment evidence catalog tests (concept-authority review CA-5).

These tests validate the UCO alignment mapping artifact's shape, its
catalog-derived coverage of adopted/adapted cyber-domain families, and the
divergence-record discipline. They validate locally recorded evidence only and
never fetch the UCO ontology over the network (per the issue #495 preflight
note).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_contracts.contracts import ConceptFamilyCatalogModel, UcoAlignmentCatalogModel
from aces_contracts.uco_alignment import (
    load_uco_alignment_catalog,
    uco_alignment_catalog_path,
)
from aces_contracts.versions import UCO_ALIGNMENT_SCHEMA_VERSION
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "contracts" / "concept-authority" / "uco-alignment-v1.json"
CONCEPT_FAMILIES_PATH = REPO_ROOT / "contracts" / "concept-authority" / "concept-families-v1.json"
FIXTURES_ROOT = REPO_ROOT / "contracts" / "fixtures" / "concept-authority" / "uco-alignment-v1"
VALID_DIR = FIXTURES_ROOT / "valid"
INVALID_DIR = FIXTURES_ROOT / "invalid"

UCO_NAMESPACE_BASE = "https://ontology.unifiedcyberontology.org/uco/"
CYBER_DOMAIN_FAMILIES = {
    "assets",
    "identities",
    "relationships",
    "observables",
    "actions-and-events",
    "tools-and-artifacts",
}


def _uco_cyber_family_provenance() -> dict[str, str]:
    payload = json.loads(CONCEPT_FAMILIES_PATH.read_text(encoding="utf-8"))
    catalog = ConceptFamilyCatalogModel.model_validate(payload)
    return {
        family_id: family.provenance.value
        for family_id, family in catalog.families.items()
        if family.provenance.value in {"adopted", "adapted"} and family.authority == "UCO"
    }


def test_uco_alignment_schema_version_constant():
    assert UCO_ALIGNMENT_SCHEMA_VERSION == "uco-alignment/v1"


def test_load_uco_alignment_catalog():
    catalog = load_uco_alignment_catalog()
    assert catalog.schema_version == "uco-alignment/v1"
    assert catalog.uco_version == "1.4.0"
    assert catalog.uco_reference
    assert catalog.review_scope


def test_uco_alignment_catalog_path_resolves():
    assert uco_alignment_catalog_path() == CATALOG_PATH


def test_uco_alignment_catalog_matches_valid_fixture():
    payload = json.loads((VALID_DIR / "reference.json").read_text(encoding="utf-8"))
    authoritative = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert payload == authoritative
    UcoAlignmentCatalogModel.model_validate(authoritative)


def test_every_adopted_adapted_uco_family_has_alignment_entry():
    """Acceptance criterion: every adopted/adapted UCO family has a checkable entry."""
    catalog = load_uco_alignment_catalog()
    assert set(catalog.alignments) == set(_uco_cyber_family_provenance())
    assert set(catalog.alignments) >= CYBER_DOMAIN_FAMILIES


def test_pinned_uco_version_and_reference_recorded():
    catalog = load_uco_alignment_catalog()
    assert catalog.uco_version == "1.4.0"
    assert "1.4.0" in catalog.uco_reference
    assert catalog.uco_reference.startswith("https://")


def test_each_alignment_entry_is_internally_consistent():
    catalog = load_uco_alignment_catalog()
    expected = _uco_cyber_family_provenance()
    for family_id, alignment in catalog.alignments.items():
        assert alignment.concept_family == family_id
        assert alignment.provenance.value == expected[family_id]
        assert alignment.uco_types, family_id
        for uco_type in alignment.uco_types:
            prefix, sep, local = uco_type.uco_class.partition(":")
            assert sep == ":" and prefix and local, uco_type.uco_class
            assert uco_type.iri == f"{UCO_NAMESPACE_BASE}{prefix}/{local}"


def test_relationships_is_adapted_with_enumerated_divergences():
    catalog = load_uco_alignment_catalog()
    relationships = catalog.alignments["relationships"]
    assert relationships.provenance.value == "adapted"
    assert len(relationships.divergences) >= 1


def test_adopted_families_record_explicit_empty_divergences():
    catalog = load_uco_alignment_catalog()
    for family_id, alignment in catalog.alignments.items():
        if alignment.provenance.value == "adopted":
            assert alignment.divergences == [], family_id


def test_valid_fixtures_pass_validation():
    for path in sorted(VALID_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        model = UcoAlignmentCatalogModel.model_validate(payload)
        assert model.alignments, f"Valid fixture {path.name} should declare alignments"


def test_invalid_fixtures_fail_validation():
    paths = sorted(INVALID_DIR.glob("*.json"))
    assert paths, "expected invalid fixtures to exist"
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        with pytest.raises(ValidationError):
            UcoAlignmentCatalogModel.model_validate(payload)


def test_missing_family_fixture_reports_coverage_gap():
    payload = json.loads((INVALID_DIR / "missing-family.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError, match="cover|adopted|adapted|missing"):
        UcoAlignmentCatalogModel.model_validate(payload)


def test_provenance_mismatch_fixture_rejected():
    payload = json.loads((INVALID_DIR / "provenance-mismatch.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError, match="provenance"):
        UcoAlignmentCatalogModel.model_validate(payload)


def test_adapted_without_divergence_fixture_rejected():
    payload = json.loads((INVALID_DIR / "adapted-without-divergence.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError, match="divergence"):
        UcoAlignmentCatalogModel.model_validate(payload)


def test_iri_mismatch_fixture_rejected():
    payload = json.loads((INVALID_DIR / "iri-mismatch.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError, match="iri|IRI|canonical"):
        UcoAlignmentCatalogModel.model_validate(payload)


def test_native_family_fixture_rejected():
    payload = json.loads((INVALID_DIR / "native-family.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        UcoAlignmentCatalogModel.model_validate(payload)
