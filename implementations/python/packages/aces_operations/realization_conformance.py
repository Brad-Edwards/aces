"""Validated persistence for machine-readable backend conformance evidence."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from aces_operations._evidence_run_validation import redaction_violations
from aces_operations.run_artifacts import atomic_write_json_artifact, run_artifact_path


def write_backend_conformance_report(
    payload: Mapping[str, object],
    *,
    output_dir: Path,
    run_id: str,
) -> Path:
    """Redaction-check and atomically persist one conformance report."""

    if redaction_violations(payload):
        raise ValueError("backend conformance report failed the redaction gate")
    target = run_artifact_path(output_dir, run_id, "conformance", "backend-conformance.json")
    atomic_write_json_artifact(target, payload)
    return target


__all__ = ["write_backend_conformance_report"]
