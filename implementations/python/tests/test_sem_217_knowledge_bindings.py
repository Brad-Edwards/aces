"""SEM-217 external knowledge binding effect tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_contracts.contracts import (
    ConceptFamilyCatalogModel,
    SemanticProfileModel,
    UcoAlignmentCatalogModel,
)
from aces_contracts.semantic_binding_effects import (
    ExternalKnowledgeBindingEffect,
    semantic_profile_required_binding_effects,
    uco_alignment_binding_effects,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONCEPT_AUTHORITY_ROOT = REPO_ROOT / "contracts" / "concept-authority"
PROFILE_PATH = REPO_ROOT / "contracts" / "profiles" / "semantic" / "reference-stack-v1.json"


def _concept_catalog() -> ConceptFamilyCatalogModel:
    payload = json.loads((CONCEPT_AUTHORITY_ROOT / "concept-families-v1.json").read_text(encoding="utf-8"))
    return ConceptFamilyCatalogModel.model_validate(payload)


def _uco_alignment_catalog() -> UcoAlignmentCatalogModel:
    payload = json.loads((CONCEPT_AUTHORITY_ROOT / "uco-alignment-v1.json").read_text(encoding="utf-8"))
    return UcoAlignmentCatalogModel.model_validate(payload)


def _semantic_profile() -> SemanticProfileModel:
    payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return SemanticProfileModel.model_validate(payload)


def test_adopted_uco_binding_annotates_and_aligns_native_meaning():
    records = uco_alignment_binding_effects(_concept_catalog(), _uco_alignment_catalog())
    assets = records["assets"]

    assert assets.family == "assets"
    assert assets.provenance == "adopted"
    assert assets.effects == frozenset(
        {
            ExternalKnowledgeBindingEffect.ANNOTATES,
            ExternalKnowledgeBindingEffect.ALIGNS,
        }
    )
    assert ExternalKnowledgeBindingEffect.CONSTRAINS not in assets.effects
    assert assets.divergences == ()


def test_adapted_uco_binding_annotates_and_refines_instead_of_aligning():
    records = uco_alignment_binding_effects(_concept_catalog(), _uco_alignment_catalog())
    relationships = records["relationships"]

    assert relationships.family == "relationships"
    assert relationships.provenance == "adapted"
    assert relationships.effects == frozenset(
        {
            ExternalKnowledgeBindingEffect.ANNOTATES,
            ExternalKnowledgeBindingEffect.REFINES,
        }
    )
    assert ExternalKnowledgeBindingEffect.ALIGNS not in relationships.effects
    assert relationships.divergences


def test_required_semantic_profile_bindings_constrain_governed_surfaces():
    records = semantic_profile_required_binding_effects(_semantic_profile(), "execution")

    provisioner_node_types = next(
        record for record in records if record.scope == "capabilities.provisioner.supported_node_types"
    )
    assert provisioner_node_types.family == "assets"
    assert provisioner_node_types.effects == frozenset({ExternalKnowledgeBindingEffect.CONSTRAINS})


def test_phases_without_governed_required_bindings_have_no_constraint_effects():
    records = semantic_profile_required_binding_effects(_semantic_profile(), "authoring")

    assert records == ()


def test_invalid_semantic_profile_phase_is_rejected_explicitly():
    with pytest.raises(ValueError, match="semantic profile phase"):
        semantic_profile_required_binding_effects(_semantic_profile(), "deployment")  # type: ignore[arg-type]


def test_uco_alignment_effects_reject_catalog_without_aligned_family():
    payload = json.loads((CONCEPT_AUTHORITY_ROOT / "concept-families-v1.json").read_text(encoding="utf-8"))
    payload["families"].pop("assets")
    catalog = ConceptFamilyCatalogModel.model_validate(payload)

    with pytest.raises(ValueError, match="unknown concept family"):
        uco_alignment_binding_effects(catalog, _uco_alignment_catalog())


def test_uco_alignment_effects_reject_provenance_mismatch():
    payload = json.loads((CONCEPT_AUTHORITY_ROOT / "concept-families-v1.json").read_text(encoding="utf-8"))
    payload["families"]["relationships"]["provenance"] = "adopted"
    catalog = ConceptFamilyCatalogModel.model_validate(payload)

    with pytest.raises(ValueError, match="provenance"):
        uco_alignment_binding_effects(catalog, _uco_alignment_catalog())


def test_sem217_effect_vocabulary_is_closed_over_required_effects():
    assert {effect.value for effect in ExternalKnowledgeBindingEffect} == {
        "annotates",
        "constrains",
        "refines",
        "aligns",
    }
