"""Structural acceptance gate for issue #1151's control-plane design program."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROGRAM_PATH = REPO_ROOT / "docs/research/runtime-control-plane/implementation-program.json"
MILESTONE = "Runtime Control-Plane"

REQUIRED_DELIVERABLES = {
    "docs/decisions/issue-1151-runtime-control-plane-architecture-preflight.md",
    "docs/decisions/adrs/adr-104-runtime-control-plane-architecture.md",
    "docs/research/runtime-control-plane/index.md",
    "docs/research/runtime-control-plane/current-state-assessment.md",
    "docs/research/runtime-control-plane/composition-architecture.md",
    "docs/research/runtime-control-plane/requirement-disposition.md",
    "docs/research/runtime-control-plane/implementation-program.md",
    "docs/research/runtime-control-plane/implementation-program.json",
}
REQUIRED_PROFILES = {"P0", "P1", "P2", "P3"}
REQUIRED_WORK_PACKAGES = {
    "CP-1",
    "CP-2",
    "CP-3",
    "CP-4",
    "CP-5",
    "CP-6",
    "CP-7",
    "CP-8",
    "CP-9",
    "CP-10",
    "CP-11",
    "CP-12",
}
REQUIRED_DISPOSITIONS = {
    "issue_1092",
    "pr_1136",
    "runtime_control_plane",
    "local_json_store",
    "http_adapter",
}


def _program() -> dict:
    return json.loads(PROGRAM_PATH.read_text(encoding="utf-8"))


def test_design_set_is_complete_and_present() -> None:
    program = _program()
    assert set(program["deliverables"]) == REQUIRED_DELIVERABLES
    for deliverable in REQUIRED_DELIVERABLES:
        path = REPO_ROOT / deliverable
        assert path.is_file(), f"missing deliverable {deliverable}"
        assert path.stat().st_size > 0, f"empty deliverable {deliverable}"


def test_program_names_the_requirement_and_milestone() -> None:
    program = _program()
    assert program["requirement"] == "API-404"
    assert program["milestone"] == MILESTONE
    assert program["parent_issue"] == 1151


def test_profiles_declare_claims_and_nonclaims() -> None:
    program = _program()
    profiles = {profile["id"]: profile for profile in program["profiles"]}
    assert set(profiles) == REQUIRED_PROFILES
    for profile in profiles.values():
        assert profile["nonclaims"], f"{profile['id']} must state explicit nonclaims"
    assert profiles["P3"]["claims"] == [], "P3 is a seam-only nonclaim"


def test_work_packages_form_an_acyclic_dependency_program() -> None:
    program = _program()
    packages = {package["id"]: package for package in program["work_packages"]}
    assert set(packages) == REQUIRED_WORK_PACKAGES
    for package in packages.values():
        for dependency in package["depends_on"]:
            assert dependency in packages, f"{package['id']} depends on unknown {dependency}"

    resolved: set[str] = set()
    remaining = dict(packages)
    while remaining:
        ready = [pid for pid, package in remaining.items() if set(package["depends_on"]) <= resolved]
        assert ready, f"dependency cycle among {sorted(remaining)}"
        for pid in ready:
            resolved.add(pid)
            del remaining[pid]


def test_dispositions_cover_the_deferred_surfaces() -> None:
    program = _program()
    assert set(program["dispositions"]) == REQUIRED_DISPOSITIONS


def test_adr_and_design_docs_reference_each_other() -> None:
    adr = (REPO_ROOT / "docs/decisions/adrs/adr-104-runtime-control-plane-architecture.md").read_text(encoding="utf-8")
    index = (REPO_ROOT / "docs/research/runtime-control-plane/index.md").read_text(encoding="utf-8")
    assert "#1151" in adr
    assert "adr-104-runtime-control-plane-architecture.md" in index
    assert "API-404" in index
