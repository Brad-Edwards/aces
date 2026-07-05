"""Tests for the release version computation (tools/release.py, #684).

Locks the fragment-type -> SemVer bump rubric so it cannot drift from
towncrier.toml or the release workflow. Runs inside `nox -s verify`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import release  # noqa: E402
from tools.release import KNOWN_TYPES, current_version, next_version, pending_types  # noqa: E402


@pytest.mark.parametrize(
    ("base", "types", "expected"),
    [
        ((0, 17, 0), {"fixed"}, "0.17.1"),
        ((0, 17, 0), {"security", "fixed"}, "0.17.1"),
        ((0, 17, 0), {"added"}, "0.18.0"),
        ((0, 17, 0), {"fixed", "added", "security"}, "0.18.0"),  # highest wins
        ((0, 17, 0), {"changed", "deprecated"}, "0.18.0"),
        ((0, 17, 0), {"removed"}, "0.18.0"),  # pre-1.0: removed is a minor
        ((1, 2, 3), {"removed"}, "2.0.0"),  # >= 1.0: removed is a major
        ((1, 2, 3), {"added"}, "1.3.0"),
        ((1, 2, 3), {"fixed"}, "1.2.4"),
    ],
)
def test_next_version(base: tuple[int, int, int], types: set[str], expected: str) -> None:
    assert next_version(base, types) == expected


@pytest.mark.parametrize("types", [set(), {"breaking"}])
def test_next_version_no_auto_bump(types: set[str]) -> None:
    # No fragments, or only `breaking` (which never auto-escalates), => no bump.
    assert next_version((0, 17, 0), types) is None


def test_breaking_is_recorded_but_does_not_escalate() -> None:
    # A breaking fragment alongside a real change is collated but does not raise
    # the bump beyond what the other fragments imply.
    assert next_version((0, 17, 0), {"breaking", "added"}) == "0.18.0"
    assert next_version((0, 17, 0), {"breaking", "fixed"}) == "0.17.1"


def test_breaking_is_a_known_type() -> None:
    assert "breaking" in KNOWN_TYPES


def test_current_version_reads_the_committed_literal() -> None:
    major, minor, patch = current_version()
    assert (major, minor, patch) >= (0, 17, 0)


def test_pending_types_rejects_unknown_type(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "1.added.md").write_text("- x\n", encoding="utf-8")
    (tmp_path / "2.bogus.md").write_text("- x\n", encoding="utf-8")
    monkeypatch.setattr(release, "FRAGMENTS", tmp_path)
    with pytest.raises(SystemExit):
        pending_types()


def test_pending_types_skips_non_fragments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "_template.md.jinja").write_text("x\n", encoding="utf-8")
    (tmp_path / "1.breaking.md").write_text("- x\n", encoding="utf-8")
    monkeypatch.setattr(release, "FRAGMENTS", tmp_path)
    assert pending_types() == {"breaking"}
