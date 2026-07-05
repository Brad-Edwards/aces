#!/usr/bin/env python3
"""Compute the next release version from towncrier changelog fragments (#684).

This is the single source of truth for the aces-sdl release version. The version
is DERIVED from the pending changelog fragments in ``changelog.d/`` — the same
fragments towncrier collates into ``CHANGELOG.md`` — so the changelog, the git
tag, and the built artifact version can never disagree. There is no version
string to hand-edit.

Fragment type -> SemVer bump (highest pending bump wins):

    breaking, removed          -> MAJOR   (backward-incompatible change / removal)
    added, changed, deprecated -> MINOR
    security, fixed            -> PATCH

Major is real: a ``breaking`` (or ``removed``) fragment on a 0.x base bumps to
1.0.0. There is no pre-1.0 suppression.

Base version resolution (what the bump is applied to):
    1. the highest ``v<major>.<minor>.<patch>`` git tag, else
    2. the latest ``## [<version>]`` header in CHANGELOG.md, else
    3. 0.0.0

If there are no pending fragments there is nothing consumer-visible to ship and
the tool reports no release.

Usage:
    compute_release.py                 # prints next version, or 'none'
    compute_release.py --format bump   # prints 'major' | 'minor' | 'patch' | 'none'
    compute_release.py --format json   # prints {base, bump, version, release, counts}
    compute_release.py --require-release  # exit 3 if there is nothing to release

Stdlib-only so it runs on a bare interpreter in CI with no install step.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

#: Fragment type -> bump level. Keep in sync with towncrier.toml's declared
#: types and with tools/check_pr_title.py's allowed types.
MAJOR = "major"
MINOR = "minor"
PATCH = "patch"

TYPE_BUMP: dict[str, str] = {
    "breaking": MAJOR,
    "removed": MAJOR,
    "added": MINOR,
    "changed": MINOR,
    "deprecated": MINOR,
    "security": PATCH,
    "fixed": PATCH,
}

#: Rank so we can take the highest pending bump.
_BUMP_RANK = {PATCH: 1, MINOR: 2, MAJOR: 3}

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_CHANGELOG_HEADER_RE = re.compile(r"^##\s*\[(\d+\.\d+\.\d+)\]")


class ReleaseComputationError(RuntimeError):
    """A fragment or version input was malformed."""


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> Version:
        m = _SEMVER_RE.match(text.strip())
        if not m:
            raise ReleaseComputationError(f"not a semantic version: {text!r}")
        return cls(int(m[1]), int(m[2]), int(m[3]))

    def bumped(self, level: str) -> Version:
        if level == MAJOR:
            return Version(self.major + 1, 0, 0)
        if level == MINOR:
            return Version(self.major, self.minor + 1, 0)
        if level == PATCH:
            return Version(self.major, self.minor, self.patch + 1)
        raise ReleaseComputationError(f"unknown bump level: {level!r}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def fragment_type(filename: str) -> str | None:
    """Return the towncrier type for a fragment filename, or None if the file is
    not a fragment (README, template, non-markdown).

    Fragment names are ``<issue>.<type>.md`` or ``+<slug>.<type>.md``; the type is
    the token immediately before the ``.md`` suffix.
    """
    if not filename.endswith(".md"):
        return None
    if filename == "README.md" or filename.startswith("_"):
        return None
    parts = filename.split(".")
    if len(parts) < 3:
        # e.g. "notes.md" — not a typed fragment; ignore rather than guess.
        return None
    return parts[-2]


def pending_types(changelog_dir: Path) -> list[str]:
    """All fragment types present in ``changelog_dir``.

    Raises if a fragment carries a type that is not a declared towncrier type,
    so a typo'd fragment fails the release loudly instead of being silently
    dropped from the version calculation.
    """
    if not changelog_dir.is_dir():
        raise ReleaseComputationError(f"changelog dir not found: {changelog_dir}")
    types: list[str] = []
    unknown: list[str] = []
    for entry in sorted(changelog_dir.iterdir()):
        if not entry.is_file():
            continue
        ftype = fragment_type(entry.name)
        if ftype is None:
            continue
        if ftype not in TYPE_BUMP:
            unknown.append(entry.name)
            continue
        types.append(ftype)
    if unknown:
        raise ReleaseComputationError(
            f"changelog fragments with unknown type (expected one of {sorted(TYPE_BUMP)}): {unknown}"
        )
    return types


def highest_bump(types: list[str]) -> str | None:
    """The highest SemVer bump implied by the pending fragment types, or None."""
    best: str | None = None
    for t in types:
        level = TYPE_BUMP[t]
        if best is None or _BUMP_RANK[level] > _BUMP_RANK[best]:
            best = level
    return best


def latest_git_tag(repo_root: Path) -> Version | None:
    """Highest ``v<semver>`` git tag, or None (no tags / not a git repo)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "tag", "--list", "v*"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    versions = []
    for line in out.splitlines():
        m = _TAG_RE.match(line.strip())
        if m:
            versions.append(Version(int(m[1]), int(m[2]), int(m[3])))
    if not versions:
        return None
    return max(versions, key=lambda v: (v.major, v.minor, v.patch))


def latest_changelog_version(changelog_file: Path) -> Version | None:
    """The first ``## [X.Y.Z]`` header in the changelog, or None."""
    if not changelog_file.is_file():
        return None
    for line in changelog_file.read_text(encoding="utf-8").splitlines():
        m = _CHANGELOG_HEADER_RE.match(line.strip())
        if m:
            return Version.parse(m[1])
    return None


def resolve_base(repo_root: Path, changelog_file: Path) -> Version:
    return latest_git_tag(repo_root) or latest_changelog_version(changelog_file) or Version(0, 0, 0)


def compute(
    repo_root: Path,
    changelog_dir: Path,
    changelog_file: Path,
    base_override: str | None = None,
) -> dict:
    base = Version.parse(base_override) if base_override else resolve_base(repo_root, changelog_file)
    types = pending_types(changelog_dir)
    bump = highest_bump(types)
    counts: dict[str, int] = {}
    for t in types:
        counts[t] = counts.get(t, 0) + 1
    if bump is None:
        return {"base": str(base), "bump": "none", "version": None, "release": False, "counts": counts}
    version = base.bumped(bump)
    return {"base": str(base), "bump": bump, "version": str(version), "release": True, "counts": counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--changelog-dir", type=Path, default=None, help="default: <repo-root>/changelog.d")
    parser.add_argument("--changelog-file", type=Path, default=None, help="default: <repo-root>/CHANGELOG.md")
    parser.add_argument("--base", default=None, help="override the base version (e.g. 0.17.0)")
    parser.add_argument(
        "--format",
        choices=("version", "bump", "json", "changelog-version"),
        default="version",
        help=(
            "version=next version from fragments (or 'none'); bump=level; json=all; "
            "changelog-version=latest version already written in CHANGELOG.md "
            "(what the release workflow tags on main after collation)"
        ),
    )
    parser.add_argument(
        "--require-release",
        action="store_true",
        help="exit 3 when there is nothing consumer-visible to release",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    changelog_dir = (args.changelog_dir or repo_root / "changelog.d").resolve()
    changelog_file = (args.changelog_file or repo_root / "CHANGELOG.md").resolve()

    if args.format == "changelog-version":
        current = latest_changelog_version(changelog_file)
        print(str(current) if current else "")
        return 0

    try:
        result = compute(repo_root, changelog_dir, changelog_file, args.base)
    except ReleaseComputationError as exc:
        print(f"compute_release: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result))
    elif args.format == "bump":
        print(result["bump"])
    else:  # version
        print(result["version"] if result["release"] else "none")

    if args.require_release and not result["release"]:
        print("compute_release: no releasable fragments pending", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
