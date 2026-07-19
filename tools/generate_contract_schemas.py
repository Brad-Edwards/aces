#!/usr/bin/env python3
"""Generate checked-in JSON Schema bundles for ACES external contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _schema_output_path(schemas_dir: Path, name: str) -> Path:
    if name == "aces-semantic-invariants-v1":
        return schemas_dir / "profiles" / f"{name}.json"
    if name in {
        "sdl-authoring-input-v1",
        "instantiated-scenario-v1",
        "instantiated-scenario-snapshot-v1",
        "scenario-instantiation-request-v1",
    }:
        return schemas_dir / "sdl" / f"{name}.json"
    if name.startswith("scenario-satisfiability-evidence-v"):
        return schemas_dir / "satisfiability" / f"{name}.json"
    if name.startswith("backend-manifest-v"):
        return schemas_dir / "backend-manifest" / f"{name}.json"
    if name.startswith("realization-envelope-v"):
        return schemas_dir / "realization-envelope" / f"{name}.json"
    if name.startswith("processor-manifest-v"):
        return schemas_dir / "processor-manifest" / f"{name}.json"
    if name.startswith("participant-implementation-manifest-v"):
        return schemas_dir / "participant-implementation-manifest" / f"{name}.json"
    if name.startswith("participant-implementation-provenance-v"):
        return schemas_dir / "participant-implementation-provenance" / f"{name}.json"
    if name in {"concept-families-v1", "behavioral-relations-v1"}:
        return schemas_dir / "concept-authority" / f"{name}.json"
    if name == "reference-models-v1":
        return schemas_dir / "concept-authority" / f"{name}.json"
    if name == "uco-alignment-v1":
        return schemas_dir / "concept-authority" / f"{name}.json"
    if name == "controlled-vocabularies-v1":
        return schemas_dir / "concept-authority" / f"{name}.json"
    if name in {"attack-enterprise-tactics-source-v1", "atlas-tactics-source-v1"}:
        return schemas_dir / "concept-authority" / f"{name}.json"
    if name == "reusable-asset-trust-policy-v1":
        return schemas_dir / "asset-trust" / f"{name}.json"
    if name == "sdl-lineage-ledger-v1":
        return schemas_dir / "provenance" / f"{name}.json"
    if name == "associated-artifact-manifest-v1":
        return schemas_dir / "associated-artifacts" / f"{name}.json"
    if name.startswith("semantic-profile-v"):
        return schemas_dir / "profiles" / f"{name}.json"
    if name.startswith("backend-profile-v"):
        return schemas_dir / "profiles" / f"{name}.json"
    if name.startswith("scientific-completeness-"):
        return schemas_dir / "profiles" / f"{name}.json"
    if name in {
        "participant-lifecycle-event-v1",
        "participant-observation-envelope-v1",
        "participant-shared-state-record-v1",
        "participant-joint-action-record-v1",
        "participant-time-management-context-v1",
        "participant-outcome-report-v1",
    }:
        return schemas_dir / "participant-runtime" / f"{name}.json"
    if name in {
        "participant-status-view-v1",
        "participant-history-view-v1",
        "participant-context-view-v1",
    }:
        return schemas_dir / "control-plane" / f"{name}.json"
    if name.startswith("experiment-"):
        return schemas_dir / "experiment-core" / f"{name}.json"
    if name.endswith("-plan-v1"):
        return schemas_dir / "plans" / f"{name}.json"
    if name == "runtime-snapshot-v1":
        return schemas_dir / "snapshots" / f"{name}.json"
    return schemas_dir / "control-plane" / f"{name}.json"


def write_schema_bundle(schemas_dir: Path) -> None:
    """Write the reference implementation's schema bundle into ``schemas_dir``.

    The published schemas under ``contracts/schemas/`` are the hand-governed
    normative authority (ADR-009 §7); the Python ``schema_bundle()`` is the
    reference implementation's output, kept identical to that authority as a
    compatibility proof. ``check_generated_schemas.py`` calls this with a
    throwaway directory so it can compare the reference output against the
    published normative schemas without overwriting them.
    """
    from aces_contracts.contracts import schema_bundle

    bundle = schema_bundle()
    for name, schema in bundle.items():
        output_path = _schema_output_path(schemas_dir, name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    python_root = repo_root / "implementations" / "python"
    sys.path.insert(0, str(python_root / "src"))
    sys.path.insert(0, str(python_root / "packages"))

    write_schema_bundle(repo_root / "contracts" / "schemas")


if __name__ == "__main__":
    main()
