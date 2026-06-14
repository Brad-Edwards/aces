"""Helpers for loading the UCO alignment evidence catalog."""

from __future__ import annotations

import json
from pathlib import Path

from .contracts import UcoAlignmentCatalogModel


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def uco_alignment_catalog_path() -> Path:
    return _repo_root() / "contracts" / "concept-authority" / "uco-alignment-v1.json"


def load_uco_alignment_catalog() -> UcoAlignmentCatalogModel:
    path = uco_alignment_catalog_path()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return UcoAlignmentCatalogModel.model_validate(payload)
