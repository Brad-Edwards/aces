"""Structural checks for public-project security and enrollment metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_scorecard_workflow_is_pinned_least_privilege_and_publishes_sarif() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "scorecard.yml"
    source = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(source)
    triggers = workflow.get("on", workflow.get(True))

    assert workflow["permissions"] == "read-all"
    assert "pull_request_target" not in triggers
    analysis = workflow["jobs"]["analysis"]
    assert analysis["permissions"] == {
        "contents": "read",
        "security-events": "write",
        "id-token": "write",
    }
    scorecard_step = next(
        step for step in analysis["steps"] if step.get("uses", "").startswith("ossf/scorecard-action@")
    )
    assert scorecard_step["uses"] == ("ossf/scorecard-action@2d1146689b8cda280b9bc96326124645441f03bc")
    assert scorecard_step["with"] == {
        "results_file": "results.sarif",
        "results_format": "sarif",
        "publish_results": "true",
    }
    assert "SCORECARD_TOKEN" not in source
    for match in re.finditer(r"^\s*uses:\s*([^#\s]+)", source, re.MULTILINE):
        assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", match.group(1))


def test_best_practices_proposal_is_factual_about_single_maintainer_limits() -> None:
    proposal = json.loads((REPO_ROOT / ".bestpractices.json").read_text(encoding="utf-8"))

    assert proposal["repo_url"] == "https://github.com/RAESystem/rae"
    assert proposal["license"] == "MIT"
    assert proposal["bus_factor_status"] == "Unmet"
    assert proposal["two_person_review_status"] == "Unmet"
    assert "one maintainer" in proposal["bus_factor_justification"].casefold()
    assert "badge" not in proposal


def test_publishers_build_only_the_curated_public_source() -> None:
    rtd = yaml.safe_load((REPO_ROOT / ".readthedocs.yaml").read_text(encoding="utf-8"))
    assert rtd["sphinx"] == {
        "configuration": "docs/public/conf.py",
        "fail_on_warning": True,
    }
    assert rtd["python"]["install"][0]["command"] == "sync --frozen"

    docs_workflow = (REPO_ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    assert "nox[uv]==2026.4.10" in docs_workflow
    assert "-s docs" in docs_workflow
    assert "sphinx-build" not in docs_workflow
    assert "path: docs/_build/html" in docs_workflow

    makefile = (REPO_ROOT / "docs" / "Makefile").read_text(encoding="utf-8")
    assert "SOURCEDIR     = public" in makefile
    assert "BUILDDIR      = _build" in makefile
