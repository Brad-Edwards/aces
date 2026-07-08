"""Loading helpers for authored experiment specifications.

An experiment specification is the pre-run authoring/input counterpart to the
archival experiment-core outputs (run/study/apparatus-context). Unlike SDL,
the authoring input is a single nested contract document with no shorthand,
key normalization, or cross-file resolution, so loading is a thin
``yaml.safe_load`` followed by ``ExperimentSpecModel`` validation — mirroring
how the JSON fixtures under ``contracts/fixtures/experiment-core`` are checked.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from .contracts import ExperimentSpecModel

log = logging.getLogger("aces.experiment_spec")


class ExperimentSpecError(Exception):
    """Base exception for experiment-specification loading."""


class ExperimentSpecValidationError(ExperimentSpecError):
    """An experiment specification failed to parse or validate."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        self.path = path
        self.details = message
        prefix = f"{path}: " if path else ""
        super().__init__(f"{prefix}{message}")


def parse_experiment_spec(text: str, *, path: Path | None = None) -> ExperimentSpecModel:
    """Parse and validate an experiment specification from YAML text."""
    raw = text.strip()
    if not raw:
        raise ExperimentSpecValidationError("Experiment spec is empty", path=path)

    try:
        payload = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ExperimentSpecValidationError(f"YAML parse error: {exc}", path=path) from exc

    if not isinstance(payload, dict):
        raise ExperimentSpecValidationError("Experiment spec must be a YAML mapping", path=path)

    try:
        return ExperimentSpecModel.model_validate(payload)
    except ValidationError as exc:
        raise ExperimentSpecValidationError(str(exc), path=path) from exc


def load_experiment_spec(path: Path) -> ExperimentSpecModel:
    """Load and validate an authored experiment specification from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Experiment spec file not found: {path}")

    spec = parse_experiment_spec(path.read_text(encoding="utf-8"), path=path)
    log.info("Loaded experiment spec '%s' from %s", spec.spec_id, path)
    return spec


def find_experiment_specs(search_dir: Path) -> list[Path]:
    """Find all authored experiment-spec files in a directory (non-recursive)."""
    if not search_dir.is_dir():
        log.debug("Experiments directory does not exist: %s", search_dir)
        return []

    paths = sorted(search_dir.glob("*.exp.yaml"))
    log.debug("Found %d experiment spec files in %s", len(paths), search_dir)
    return paths
