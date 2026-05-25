from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_DOC = REPO_ROOT / "docs/explain/sdl/scenario-delivery-drift-audit.md"
SECTIONS_DOC = REPO_ROOT / "docs/explain/sdl/sections.md"

REQUIRED_SURFACES = (
    "ADR-021",
    "ADR-022",
    "ADR-023",
    "ADR-024",
    "ADR-025",
    "ADR-026",
    "ADR-027",
    "ADR-028",
    "ADR-029",
    "ADR-030",
    "ADR-031",
    "ADR-032",
    "ADR-033",
    "ADR-034",
    "lineage.md",
    "sections.md",
    "validation.md",
    "limitations.md",
    "runtime-architecture.md",
    "precedents.md",
    "specs/",
    "contracts/",
    "implementations/python/packages/aces_sdl/",
)

REQUIRED_FINDING_FIELDS = (
    "**Surface:**",
    "**Citation:**",
    "**Suspect exclusion or scope language:**",
    "**Boundary analysis:**",
    "**Disposition:**",
)

REQUIRED_FINDING_CODES = (
    "D-001",
    "A-001",
    "A-002",
    "A-003",
    "A-004",
    "A-005",
    "R-001",
    "R-002",
    "R-003",
    "R-004",
    "R-005",
    "R-006",
    "R-007",
)


def test_scenario_delivery_drift_audit_covers_issue_scope() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    assert "# Scenario/Delivery Classification Drift Audit and Remediation" in text
    assert "## Audit Coverage" in text
    assert "## Findings" in text
    assert "audit catalogue only" not in text
    assert "current-drift" not in text

    coverage_section = text.split("## Audit Coverage", maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
    for surface in REQUIRED_SURFACES:
        assert surface in coverage_section
    assert "| sections.md | `docs/explain/sdl/sections.md` | fixed-drift |" in coverage_section


def test_scenario_delivery_drift_findings_have_evidence_fields() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    finding_sections = []
    finding_codes = set()
    for section in text.split("\n### "):
        if match := re.match(r"^([A-Z]-\d+)", section):
            finding_sections.append(section)
            finding_codes.add(match.group(1))

    assert finding_sections
    for code in REQUIRED_FINDING_CODES:
        assert code in finding_codes
    assert any(code.startswith("D-") for code in finding_codes)

    for section in finding_sections:
        for field in REQUIRED_FINDING_FIELDS:
            assert field in section


def test_sections_runtime_summary_uses_corrected_boundary() -> None:
    text = SECTIONS_DOC.read_text(encoding="utf-8")

    assert "not authored deployable\nfeatures or exposed network services" not in text
    assert "participant-observable and analysis-relevant runtime state" in text
    assert "does not exclude host-published\nbindings" in text
