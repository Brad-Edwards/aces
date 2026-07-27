"""Fail-closed change classification for the fast local verification lane."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class ChangeRecord:
    """One status-aware Git change, retaining both sides of a rename."""

    status: str
    path: str
    old_path: str | None = None

    @property
    def paths(self) -> tuple[str, ...]:
        return (self.path,) if self.old_path is None else (self.old_path, self.path)


@dataclass(frozen=True)
class VerificationPlan:
    """The expensive stages required for a set of changes."""

    contracts: bool
    regression: bool
    fuzz: bool
    docs: bool
    reason: str


FULL_PLAN = VerificationPlan(
    contracts=True,
    regression=True,
    fuzz=True,
    docs=True,
    reason="full verification required",
)

_SAFE_PROSE_FILES = {
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
}
_EVIDENCE_PREFIXES = ("docs/research", "specs")


def _under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def _is_safe_prose(path: str) -> bool:
    return path in _SAFE_PROSE_FILES or _under(path, "docs")


def _is_evidence(path: str) -> bool:
    return any(_under(path, prefix) for prefix in _EVIDENCE_PREFIXES)


def plan_for_changes(changes: list[ChangeRecord]) -> VerificationPlan:
    """Select a local plan; anything uncertain escalates to the full graph."""

    if not changes:
        return FULL_PLAN
    if any(change.status not in {"A", "M"} for change in changes):
        return replace(FULL_PLAN, reason="deletion, rename, copy, or type change")

    paths = [path for change in changes for path in change.paths]
    if all(_is_safe_prose(path) or _is_evidence(path) for path in paths):
        if any(_is_evidence(path) for path in paths):
            return VerificationPlan(
                contracts=True,
                regression=False,
                fuzz=False,
                docs=True,
                reason="research evidence or formal specification changed",
            )
        return VerificationPlan(
            contracts=False,
            regression=False,
            fuzz=False,
            docs=True,
            reason="non-authoritative prose changed",
        )

    return FULL_PLAN


def _run_git(repo_root: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return proc.stdout


def collect_git_changes(repo_root: Path, base_rev: str) -> list[ChangeRecord]:
    """Return status-aware changes from ``base_rev`` through the working tree."""

    raw = _run_git(repo_root, "diff", "--name-status", "-z", "--find-renames", base_rev)
    fields = raw.decode("utf-8").split("\0")
    if fields and fields[-1] == "":
        fields.pop()

    changes: list[ChangeRecord] = []
    index = 0
    while index < len(fields):
        status_token = fields[index]
        status = status_token[:1]
        index += 1
        if status in {"R", "C"}:
            old_path, path = fields[index : index + 2]
            changes.append(ChangeRecord(status=status, old_path=old_path, path=path))
            index += 2
        else:
            changes.append(ChangeRecord(status=status, path=fields[index]))
            index += 1

    tracked_paths = {path for change in changes for path in change.paths}
    untracked = _run_git(repo_root, "ls-files", "--others", "--exclude-standard", "-z")
    for path in untracked.decode("utf-8").split("\0"):
        if path and path not in tracked_paths:
            changes.append(ChangeRecord(status="A", path=path))
    return changes


def resolve_upstream(repo_root: Path) -> str:
    """Resolve the current branch's remote-tracking ref."""

    return (
        _run_git(
            repo_root,
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{upstream}",
        )
        .decode("utf-8")
        .strip()
    )
