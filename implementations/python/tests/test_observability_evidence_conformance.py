"""ASR-525 observability/evidence conformance probes for issue #128."""

from __future__ import annotations

import json
from pathlib import Path

from aces_conformance.conformance import (
    observability_evidence_conformance_diagnostics,
    run_fixture_suite,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_FIXTURE = (
    REPO_ROOT / "contracts" / "fixtures" / "experiment-core" / "experiment-run-v1" / "valid" / "reference.json"
)


def _reference_run() -> dict:
    return json.loads(RUN_FIXTURE.read_text(encoding="utf-8"))


def _augmentation_disclosure() -> dict:
    return {
        "augmentation_id": "packet-capture-sidecar",
        "purpose": "evidence",
        "realization_layer": "backend",
        "classifications": ["apparatus_only", "comparability_relevant"],
        "augmented_by_ref": {
            "ref_kind": "backend",
            "ref_id": "stub-backend",
            "ref_version": "0.1.0",
        },
        "carrier_refs": [
            {
                "ref_kind": "measurement-channel",
                "ref_id": "evaluation-history-channel",
                "ref_version": "1.0.0",
            }
        ],
        "affected_refs": [
            {
                "ref_kind": "capture-spec",
                "ref_id": "capture-techvault-evidence-v1",
                "ref_version": "1.0.0",
            }
        ],
        "evidence_refs": [
            {
                "ref_kind": "evidence-record",
                "ref_id": "evidence-techvault-network-trace-001",
                "ref_version": "1.0.0",
            }
        ],
        "disclosure_policy": "Internal run-provenance disclosure; no raw packet content is embedded.",
        "markings": ["internal"],
        "observer_effect": "The sidecar observes run traffic without modifying scenario services.",
        "comparability_effect": "Compare only with runs that declare equivalent capture support.",
    }


def test_observability_evidence_conformance_accepts_traced_augmentation() -> None:
    payload = _reference_run()
    payload["augmentation_disclosures"] = [_augmentation_disclosure()]

    diagnostics = observability_evidence_conformance_diagnostics(payload)

    assert diagnostics == ()


def test_observability_evidence_conformance_requires_affected_refs() -> None:
    payload = _reference_run()
    disclosure = _augmentation_disclosure()
    disclosure["affected_refs"] = []
    payload["augmentation_disclosures"] = [disclosure]

    diagnostics = observability_evidence_conformance_diagnostics(payload)

    assert {diagnostic.code for diagnostic in diagnostics} == {"conformance.observability-evidence-invalid"}
    assert any("affected_refs" in diagnostic.address for diagnostic in diagnostics)
    assert any("must name affected_refs" in diagnostic.message for diagnostic in diagnostics)


def test_observability_evidence_conformance_requires_authored_ref_for_run_refinement() -> None:
    payload = _reference_run()
    payload["realized_form_disclosures"].append(
        {
            "concern_id": "capture-window-tightening",
            "concern_kind": "capture-window",
            "basis": "processor-realized",
            "realized_by_ref": {
                "ref_kind": "processor",
                "ref_id": "aces-reference-processor",
                "ref_version": "0.1.0",
            },
            "realized_value_summary": "Run used a narrower post-condition capture window.",
            "disclosure": "The processor narrowed the capture window for this run without rewriting the authored requirement.",
            "evidence_refs": [],
        }
    )

    diagnostics = observability_evidence_conformance_diagnostics(payload)

    assert {diagnostic.code for diagnostic in diagnostics} == {"conformance.observability-evidence-invalid"}
    assert any("authored_ref" in diagnostic.message for diagnostic in diagnostics)
    assert any("evidence_refs" in diagnostic.message for diagnostic in diagnostics)


def test_fixture_suite_exercises_experiment_run_observability_semantics(tmp_path: Path) -> None:
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / "observability-evidence.json").write_text(
        json.dumps(
            {
                "schema_version": "backend-profile/v1",
                "profile": "observability-evidence",
                "required_contracts": ["experiment-run-v1"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = run_fixture_suite(profile="observability-evidence", profiles_root=backend_dir)

    assert report.passed is True
    invalid_case = next(case for case in report.cases if case.name == "augmentation-without-affected-refs")
    assert invalid_case.valid is False
    assert invalid_case.passed is True
    assert any(
        diagnostic.code == "conformance.observability-evidence-invalid" for diagnostic in invalid_case.diagnostics
    )
