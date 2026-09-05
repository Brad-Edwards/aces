"""Markdown-prose checks: internal link targets and normative layering."""

from __future__ import annotations

from pathlib import Path

from tools.policy.common import PolicyFailure
from tools.sdl_catalog_parity._expected import _failure
from tools.sdl_catalog_parity._paths import (
    _IMPLEMENTATION_TERM_RE,
    _MARKDOWN_LINK_RE,
    DIAGNOSTICS_PATH,
)


def _link_target_exists(root: Path, source: Path, target_path: str) -> bool:
    resolved = (source.parent / target_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return False
    return resolved.exists()


def _file_link_failures(root: Path, source: Path, text: str, relative: str) -> list[PolicyFailure]:
    failures: list[PolicyFailure] = []
    for match in _MARKDOWN_LINK_RE.finditer(text):
        target = match.group("target").strip()
        if target.startswith(("#", "http:", "https:", "mailto:")):
            continue
        target_path = target.split("#", 1)[0]
        if not target_path:
            continue
        if not _link_target_exists(root, source, target_path):
            line_no = text.count("\n", 0, match.start()) + 1
            failures.append(
                _failure(
                    "sdl-catalog-link-target",
                    f"internal Markdown target at line {line_no} does not exist: {target_path}",
                    relative,
                )
            )
    return failures


def _check_internal_links(repo_root: Path, relative_paths: tuple[str, ...]) -> list[PolicyFailure]:
    root = repo_root.resolve()
    failures: list[PolicyFailure] = []
    for relative in relative_paths:
        source = repo_root / relative
        failures.extend(_file_link_failures(root, source, source.read_text(encoding="utf-8"), relative))
    return failures


def _check_diagnostic_normative_layer(text: str) -> list[PolicyFailure]:
    failures: list[PolicyFailure] = []
    in_implementation_evidence = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        is_quote = line.startswith(">")
        if is_quote and "Implementation evidence (non-normative)" in line:
            in_implementation_evidence = True
        elif not is_quote:
            in_implementation_evidence = False
        if _IMPLEMENTATION_TERM_RE.search(line) and not (is_quote and in_implementation_evidence):
            failures.append(
                _failure(
                    "sdl-catalog-normative-layer",
                    f"implementation-specific diagnostic term at line {line_no} is not marked non-normative",
                    DIAGNOSTICS_PATH,
                )
            )
    return failures
