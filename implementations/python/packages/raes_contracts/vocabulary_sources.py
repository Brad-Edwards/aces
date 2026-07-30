"""Load checked-in external authority snapshots without network access."""

from __future__ import annotations

import json

from .contracts import AttackEnterpriseTacticsSourceModel, NistCsfDefensiveCategorySourceModel
from .corpus import CONCEPT_AUTHORITY, corpus_family_root


def load_attack_enterprise_tactics_source() -> AttackEnterpriseTacticsSourceModel:
    path = corpus_family_root(CONCEPT_AUTHORITY) / "attack-enterprise-tactics-source-v1.json"
    return AttackEnterpriseTacticsSourceModel.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_nist_csf_defensive_categories_source() -> NistCsfDefensiveCategorySourceModel:
    path = corpus_family_root(CONCEPT_AUTHORITY) / "nist-csf-defensive-categories-source-v1.json"
    return NistCsfDefensiveCategorySourceModel.model_validate(json.loads(path.read_text(encoding="utf-8")))


__all__ = [
    "load_attack_enterprise_tactics_source",
    "load_nist_csf_defensive_categories_source",
]
