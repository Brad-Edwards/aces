"""Tests for the shared contract-corpus resolution seam (issue #537).

The published ``contracts/`` tree is the hand-governed normative authority
(ADR-009). Every corpus loader must resolve through the single
``raes_contracts.corpus`` seam so the corpus is reachable from an installed
distribution (where it ships as package data) without each loader
reconstructing a ``Path(__file__).parents[N]`` repository path.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPO_ROOT / "contracts"


def test_corpus_root_resolves_to_an_existing_directory():
    from raes_contracts.corpus import corpus_root

    root = corpus_root()
    assert isinstance(root, Path)
    assert root.is_dir()


def test_corpus_root_matches_repo_contracts_in_source_checkout():
    """In a source checkout the seam resolves to the in-repo authority tree."""

    from raes_contracts.corpus import corpus_root

    assert corpus_root() == CONTRACTS_ROOT


@pytest.mark.parametrize(
    ("family", "probe"),
    [
        ("profiles", "backend/provisioning-only.json"),
        ("fixtures", None),
        ("concept-authority", "controlled-vocabularies-v1.json"),
        ("schemas", None),
    ],
)
def test_corpus_family_root_resolves_each_normative_family(family: str, probe: str | None):
    from raes_contracts.corpus import corpus_family_root

    family_root = corpus_family_root(family)
    assert family_root == CONTRACTS_ROOT / family
    assert family_root.is_dir()
    if probe is not None:
        assert (family_root / probe).exists()


def test_family_constants_match_authority_boundary_families():
    from raes_contracts import corpus

    assert corpus.PROFILES == "profiles"
    assert corpus.FIXTURES == "fixtures"
    assert corpus.CONCEPT_AUTHORITY == "concept-authority"
    assert corpus.SCHEMAS == "schemas"


def test_backend_profiles_loader_routes_through_seam():
    from raes_contracts.backend_profiles import backend_profiles_root
    from raes_contracts.corpus import corpus_family_root

    assert backend_profiles_root() == corpus_family_root("profiles") / "backend"


def test_semantic_profiles_loader_routes_through_seam():
    from raes_contracts.corpus import corpus_family_root
    from raes_contracts.semantic_profiles import semantic_profiles_root

    assert semantic_profiles_root() == corpus_family_root("profiles") / "semantic"


def test_controlled_vocabulary_loader_routes_through_seam():
    from raes_contracts.controlled_vocabularies import controlled_vocabulary_catalog_path
    from raes_contracts.corpus import corpus_family_root

    assert controlled_vocabulary_catalog_path() == (
        corpus_family_root("concept-authority") / "controlled-vocabularies-v1.json"
    )


def test_reference_model_loader_routes_through_seam():
    from raes_contracts.corpus import corpus_family_root
    from raes_contracts.reference_models import reference_model_catalog_path

    assert reference_model_catalog_path() == (corpus_family_root("concept-authority") / "reference-models-v1.json")


def test_uco_alignment_loader_routes_through_seam():
    from raes_contracts.corpus import corpus_family_root
    from raes_contracts.uco_alignment import uco_alignment_catalog_path

    assert uco_alignment_catalog_path() == (corpus_family_root("concept-authority") / "uco-alignment-v1.json")


def test_fixtures_root_routes_through_seam():
    from raes_conformance.conformance import fixtures_root
    from raes_contracts.corpus import corpus_family_root

    assert fixtures_root() == corpus_family_root("fixtures")


@pytest.mark.parametrize(
    "module_name",
    [
        "raes_contracts.backend_profiles",
        "raes_contracts.semantic_profiles",
        "raes_contracts.controlled_vocabularies",
        "raes_contracts.reference_models",
        "raes_contracts.uco_alignment",
        "raes_contracts.contracts",
        "raes_conformance.conformance",
    ],
)
def test_no_loader_keeps_a_parents_based_repo_root(module_name: str):
    """Preflight gotcha: no default loader may stay anchored on
    ``Path(__file__).parents[N]``. The fragile per-module ``_repo_root`` helper
    must be gone once the loader routes through the corpus seam."""

    module = importlib.import_module(module_name)
    assert not hasattr(module, "_repo_root"), (
        f"{module_name} still defines a parents[N]-based _repo_root; "
        "resolve the corpus through raes_contracts.corpus instead."
    )


def test_bundled_corpus_takes_precedence_over_source_checkout(monkeypatch, tmp_path):
    """The packaged-resource path is the default for an installed distribution;
    when both a bundled corpus and a source checkout are visible, bundled wins,
    so the installed wheel is what gets exercised."""

    from raes_contracts import corpus

    bundled = tmp_path / "_corpus"
    bundled.mkdir()
    monkeypatch.setattr(corpus, "_bundled_corpus_root", lambda: bundled)
    corpus.corpus_root.cache_clear()
    try:
        assert corpus.corpus_root() == bundled
    finally:
        corpus.corpus_root.cache_clear()


def test_corpus_root_raises_when_no_corpus_is_available(monkeypatch):
    """A missing packaged corpus must surface as a hard error, never a silent
    empty corpus that would make conformance/validation pass vacuously."""

    from raes_contracts import corpus

    monkeypatch.setattr(corpus, "_bundled_corpus_root", lambda: None)
    monkeypatch.setattr(corpus, "_source_checkout_corpus_root", lambda: None)
    corpus.corpus_root.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="contract corpus is unavailable"):
            corpus.corpus_root()
    finally:
        corpus.corpus_root.cache_clear()
