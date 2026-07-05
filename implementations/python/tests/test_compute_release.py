"""Tests for the changelog-driven release version computation (#684).

`tools/compute_release.py` is the single source of truth for the release
version: it maps the pending towncrier changelog fragments to a SemVer bump.
These run inside `nox -s verify`, so the fragment-type -> bump contract cannot
drift from towncrier.toml or the release workflow.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.compute_release import (  # noqa: E402
    TYPE_BUMP,
    ReleaseComputationError,
    Version,
    compute,
    fragment_type,
    highest_bump,
    latest_changelog_version,
    pending_types,
)


def _write(dir_: Path, *names: str) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    for n in names:
        (dir_ / n).write_text("- a change\n", encoding="utf-8")


# --- fragment_type parsing ---


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("105.added.md", "added"),
        ("684.fixed.md", "fixed"),
        ("+towncrier-adoption.added.md", "added"),
        ("+act-601-sonarcloud-dedup.changed.md", "changed"),
        ("12.security.md", "security"),
        ("README.md", None),
        ("_template.md.jinja", None),
        (".gitignore", None),
        ("notes.md", None),  # not a typed fragment
    ],
)
def test_fragment_type(name: str, expected: str | None) -> None:
    assert fragment_type(name) == expected


# --- bump ranking ---


def test_type_bump_mapping_is_complete() -> None:
    # Every declared towncrier type must map to a bump (no silent gaps).
    assert set(TYPE_BUMP) == {
        "breaking",
        "removed",
        "added",
        "changed",
        "deprecated",
        "security",
        "fixed",
    }


@pytest.mark.parametrize(
    ("types", "expected"),
    [
        ([], None),
        (["fixed"], "patch"),
        (["security", "fixed"], "patch"),
        (["added"], "minor"),
        (["fixed", "added", "security"], "minor"),  # highest wins
        (["changed", "deprecated"], "minor"),
        (["removed"], "major"),
        (["breaking"], "major"),
        (["fixed", "added", "breaking"], "major"),  # highest wins
    ],
)
def test_highest_bump(types: list[str], expected: str | None) -> None:
    assert highest_bump(types) == expected


# --- Version arithmetic (major is real) ---


@pytest.mark.parametrize(
    ("base", "level", "expected"),
    [
        ("0.17.0", "patch", "0.17.1"),
        ("0.17.0", "minor", "0.18.0"),
        ("0.17.0", "major", "1.0.0"),  # breaking on 0.x is a real major bump
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "major", "2.0.0"),
    ],
)
def test_version_bump(base: str, level: str, expected: str) -> None:
    assert str(Version.parse(base).bumped(level)) == expected


def test_version_parse_rejects_junk() -> None:
    with pytest.raises(ReleaseComputationError):
        Version.parse("v1.2")


# --- pending_types validation ---


def test_pending_types_rejects_unknown_type(tmp_path: Path) -> None:
    _write(tmp_path, "1.added.md", "2.bogus.md")
    with pytest.raises(ReleaseComputationError, match="unknown type"):
        pending_types(tmp_path)


def test_pending_types_skips_non_fragments(tmp_path: Path) -> None:
    _write(tmp_path, "README.md", "_template.md.jinja", "1.added.md")
    assert pending_types(tmp_path) == ["added"]


# --- latest_changelog_version ---


def test_latest_changelog_version(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [0.17.0] - 2026-05-10\n\n### Added\n- x\n\n## [0.16.0] - 2026-05-10\n",
        encoding="utf-8",
    )
    assert str(latest_changelog_version(changelog)) == "0.17.0"


def test_latest_changelog_version_missing(tmp_path: Path) -> None:
    assert latest_changelog_version(tmp_path / "nope.md") is None


# --- end-to-end compute (with base override so no git is needed) ---


def test_compute_minor_from_backlog_shape(tmp_path: Path) -> None:
    # Mirrors the real backlog shape: added/changed/fixed/security -> minor.
    _write(tmp_path, "1.added.md", "2.changed.md", "3.fixed.md", "4.security.md")
    result = compute(REPO_ROOT, tmp_path, REPO_ROOT / "CHANGELOG.md", base_override="0.17.0")
    assert result["release"] is True
    assert result["bump"] == "minor"
    assert result["version"] == "0.18.0"


def test_compute_major_from_breaking(tmp_path: Path) -> None:
    _write(tmp_path, "1.added.md", "2.breaking.md")
    result = compute(REPO_ROOT, tmp_path, REPO_ROOT / "CHANGELOG.md", base_override="0.17.0")
    assert result["bump"] == "major"
    assert result["version"] == "1.0.0"


def test_compute_major_from_removed(tmp_path: Path) -> None:
    _write(tmp_path, "1.removed.md")
    result = compute(REPO_ROOT, tmp_path, REPO_ROOT / "CHANGELOG.md", base_override="0.17.0")
    assert result["bump"] == "major"
    assert result["version"] == "1.0.0"


def test_compute_patch(tmp_path: Path) -> None:
    _write(tmp_path, "1.fixed.md", "2.security.md")
    result = compute(REPO_ROOT, tmp_path, REPO_ROOT / "CHANGELOG.md", base_override="0.17.0")
    assert result["bump"] == "patch"
    assert result["version"] == "0.17.1"


def test_compute_no_release_when_empty(tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)
    result = compute(REPO_ROOT, tmp_path, REPO_ROOT / "CHANGELOG.md", base_override="0.17.0")
    assert result["release"] is False
    assert result["version"] is None
    assert result["bump"] == "none"
