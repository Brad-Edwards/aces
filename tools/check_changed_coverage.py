"""Enforce branch-aware aggregate and changed-code coverage policy."""

from __future__ import annotations

import argparse
import ast
import io
import json
import math
import re
import subprocess
import tokenize
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@", re.MULTILINE)
_FORBIDDEN_COVERAGE_PRAGMA = re.compile(r"#\s*pragma\s*:\s*no\s+(?:cover|branch)\b", re.IGNORECASE)
_MEASURED_PREFIXES = ("implementations/python/packages/", "tools/")
_MEASURED_FILES = frozenset({"noxfile.py", "implementations/python/hatch_build.py"})


class CoveragePolicyError(RuntimeError):
    """Raised when coverage policy inputs cannot be trusted."""


def _git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ("git", *args),
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise CoveragePolicyError(detail or f"git {' '.join(args)} failed")
    return result


def _validate_base(repo_root: Path, base_rev: str) -> None:
    try:
        _git(repo_root, "rev-parse", "--verify", f"{base_rev}^{{commit}}")
    except CoveragePolicyError as exc:
        raise CoveragePolicyError(f"coverage base {base_rev!r} does not resolve to a commit") from exc
    ancestor = _git(repo_root, "merge-base", "--is-ancestor", base_rev, "HEAD", check=False)
    if ancestor.returncode != 0:
        raise CoveragePolicyError(f"coverage base {base_rev!r} is not an ancestor of HEAD")


def is_measured_python_path(path: str) -> bool:
    """Return whether a repository-relative path belongs to the coverage policy."""

    return path.endswith(".py") and (path in _MEASURED_FILES or path.startswith(_MEASURED_PREFIXES))


def added_lines_from_patch(patch: str) -> set[int]:
    """Return destination line numbers from zero-context unified diff hunks."""

    lines: set[int] = set()
    for match in _HUNK.finditer(patch):
        start = int(match.group("start"))
        count = int(match.group("count") or "1")
        lines.update(range(start, start + count))
    return lines


def changed_python_lines(repo_root: Path, base_rev: str) -> dict[str, set[int]]:
    """Return changed measured Python destination lines since an exact ancestor."""

    _validate_base(repo_root, base_rev)
    changed_names = _git(
        repo_root,
        "diff",
        "--name-only",
        "-z",
        "--diff-filter=AMR",
        "--find-renames",
        base_rev,
        "--",
    ).stdout.split(b"\0")
    untracked_names = _git(repo_root, "ls-files", "--others", "--exclude-standard", "-z").stdout.split(b"\0")
    paths = sorted(
        path
        for raw in {*changed_names, *untracked_names}
        if raw and is_measured_python_path(path := raw.decode("utf-8", errors="surrogateescape"))
    )
    changed: dict[str, set[int]] = {}
    for path in paths:
        tracked = _git(repo_root, "ls-files", "--error-unmatch", "--", path, check=False).returncode == 0
        if tracked:
            patch = _git(
                repo_root,
                "diff",
                "--unified=0",
                "--no-ext-diff",
                "--find-renames",
                base_rev,
                "--",
                path,
            ).stdout.decode("utf-8", errors="replace")
            changed[path] = added_lines_from_patch(patch)
        else:
            changed[path] = set(range(1, len((repo_root / path).read_bytes().splitlines()) + 1))
    return changed


def _repository_path(raw_path: str, repo_root: Path, project_root: Path) -> str:
    path = Path(raw_path)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        project_candidate = (project_root / path).resolve()
        repo_candidate = (repo_root / path).resolve()
        resolved = project_candidate if project_candidate.exists() else repo_candidate
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise CoveragePolicyError(f"coverage path escapes the repository: {raw_path}") from exc


def normalized_file_records(
    report: Mapping[str, Any],
    *,
    repo_root: Path,
    project_root: Path,
) -> dict[str, Mapping[str, Any]]:
    """Index Coverage.py file records by repository-relative destination path."""

    raw_files = report.get("files")
    if not isinstance(raw_files, Mapping):
        raise CoveragePolicyError("coverage JSON has no files mapping")
    records: dict[str, Mapping[str, Any]] = {}
    for raw_path, record in raw_files.items():
        if not isinstance(raw_path, str) or not isinstance(record, Mapping):
            raise CoveragePolicyError("coverage JSON contains a malformed file record")
        path = _repository_path(raw_path, repo_root, project_root)
        if is_measured_python_path(path):
            records[path] = record
    return records


def _terminal_name(node: ast.expr) -> str | None:
    while isinstance(node, ast.Subscript):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_ellipsis_declaration(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    return (
        len(body) == 1
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and body[0].value.value is Ellipsis
    )


def _is_declaration_only_protocol(node: ast.ClassDef) -> bool:
    declarations = [
        member
        for member in node.body
        if not (
            isinstance(member, ast.Expr)
            and isinstance(member.value, ast.Constant)
            and isinstance(member.value.value, str)
        )
    ]
    return bool(declarations) and all(
        isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_ellipsis_declaration(member)
        for member in declarations
    )


def _structural_exclusion_lines(source: str, *, path: str) -> set[int]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        raise CoveragePolicyError(f"could not parse changed Python source {path}: {exc.msg}") from exc

    source_lines = source.splitlines()
    structural: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _terminal_name(node.test) == "TYPE_CHECKING":
            first_body_line = min(statement.lineno for statement in node.body)
            structural.update(range(node.lineno, first_body_line))
            for statement in node.body:
                structural.update(range(statement.lineno, (statement.end_lineno or statement.lineno) + 1))

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not any(_terminal_name(base) == "Protocol" for base in node.bases):
            continue
        if _is_declaration_only_protocol(node):
            end = node.end_lineno or node.lineno
            while end < len(source_lines) and not source_lines[end].strip():
                end += 1
            structural.update(range(node.lineno, end + 1))
            continue
        for declaration in node.body:
            if not isinstance(declaration, (ast.FunctionDef, ast.AsyncFunctionDef)) or not _is_ellipsis_declaration(
                declaration
            ):
                continue
            start = min(
                (decorator.lineno for decorator in declaration.decorator_list),
                default=declaration.lineno,
            )
            structural.update(range(start, (declaration.end_lineno or declaration.lineno) + 1))
    return structural


def _source_coverage_policy(
    repo_root: Path,
    path: str,
    changed_lines: set[int],
) -> tuple[set[int], set[int]]:
    source_path = repo_root / path
    try:
        source = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CoveragePolicyError(f"could not inspect changed Python source {path}: {exc}") from exc
    structural = _structural_exclusion_lines(source, path=path)
    forbidden = {
        token.start[0]
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT
        and token.start[0] in changed_lines
        and _FORBIDDEN_COVERAGE_PRAGMA.search(token.string)
    }
    return structural, forbidden


def changed_coverage_failures(
    changed: Mapping[str, set[int]],
    records: Mapping[str, Mapping[str, Any]],
    *,
    repo_root: Path,
) -> list[str]:
    """Return deterministic failures for uncovered changed lines and branches."""

    failures: list[str] = []
    for path, changed_lines in sorted(changed.items()):
        structural_exclusions, forbidden_pragmas = _source_coverage_policy(repo_root, path, changed_lines)
        for line in sorted(forbidden_pragmas):
            failures.append(f"{path}:{line}: explicit coverage exclusion pragma is forbidden on changed code")
        record = records.get(path)
        if record is None:
            failures.append(f"{path}: changed measured Python file is absent from coverage data")
            continue
        executed = {int(line) for line in record.get("executed_lines", [])}
        missing = {int(line) for line in record.get("missing_lines", [])}
        excluded = {int(line) for line in record.get("excluded_lines", [])}
        executable_changed = changed_lines & (executed | missing)
        for line in sorted(executable_changed & missing):
            failures.append(f"{path}:{line}: changed executable line is not covered")
        for line in sorted((changed_lines & excluded) - structural_exclusions - forbidden_pragmas):
            failures.append(f"{path}:{line}: changed line is excluded from coverage")
        missing_branches = {
            (int(edge[0]), int(edge[1]))
            for edge in record.get("missing_branches", [])
            if isinstance(edge, Sequence) and len(edge) == 2
        }
        for source, destination in sorted(edge for edge in missing_branches if edge[0] in changed_lines):
            failures.append(f"{path}:{source}->{destination}: changed branch exit is not covered")
    return failures


def aggregate_coverage_failures(report: Mapping[str, Any], ratchet: Mapping[str, Any]) -> list[str]:
    """Return failures when line or branch totals fall below the recorded ratchet."""

    meta = report.get("meta")
    totals = report.get("totals")
    if not isinstance(meta, Mapping) or meta.get("branch_coverage") is not True:
        raise CoveragePolicyError("coverage JSON must contain branch coverage")
    if not isinstance(totals, Mapping):
        raise CoveragePolicyError("coverage JSON has no totals mapping")
    covered_lines = int(totals["covered_lines"])
    statements = int(totals["num_statements"])
    covered_branches = int(totals["covered_branches"])
    branches = int(totals["num_branches"])
    line_percent = 100.0 if statements == 0 else 100.0 * covered_lines / statements
    branch_percent = 100.0 if branches == 0 else 100.0 * covered_branches / branches
    minimum_line = _minimum_percent(ratchet, "minimum_line_percent")
    minimum_branch = _minimum_percent(ratchet, "minimum_branch_percent")
    failures = []
    if line_percent + 1e-12 < minimum_line:
        failures.append(f"aggregate line coverage {line_percent:.3f}% is below {minimum_line:.3f}%")
    if branch_percent + 1e-12 < minimum_branch:
        failures.append(f"aggregate branch coverage {branch_percent:.3f}% is below {minimum_branch:.3f}%")
    return failures


def _minimum_percent(ratchet: Mapping[str, Any], key: str) -> float:
    try:
        value = float(ratchet[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise CoveragePolicyError(f"coverage ratchet {key!r} must be a number") from exc
    if not math.isfinite(value) or not 0.0 <= value <= 100.0:
        raise CoveragePolicyError(f"coverage ratchet {key!r} must be between 0 and 100")
    return value


def base_ratchet(
    repo_root: Path,
    base_rev: str,
    ratchet_path: Path,
) -> Mapping[str, Any] | None:
    """Load the ratchet recorded at the exact base, if it already existed."""

    try:
        relative_path = ratchet_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise CoveragePolicyError(f"coverage ratchet path escapes the repository: {ratchet_path}") from exc
    result = _git(repo_root, "show", f"{base_rev}:{relative_path}", check=False)
    if result.returncode != 0:
        return None
    try:
        value = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CoveragePolicyError(f"coverage ratchet at base {base_rev!r} is not valid JSON") from exc
    if not isinstance(value, Mapping):
        raise CoveragePolicyError(f"coverage ratchet at base {base_rev!r} must contain a JSON object")
    return value


def ratchet_regression_failures(
    current: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
) -> list[str]:
    """Return failures when a checked-in aggregate floor is lowered."""

    if previous is None:
        return []
    failures: list[str] = []
    for key, label in (("minimum_line_percent", "line"), ("minimum_branch_percent", "branch")):
        current_minimum = _minimum_percent(current, key)
        previous_minimum = _minimum_percent(previous, key)
        if current_minimum + 1e-12 < previous_minimum:
            failures.append(f"aggregate {label} ratchet {current_minimum:.3f}% is below base {previous_minimum:.3f}%")
    return failures


def load_json(path: Path) -> Mapping[str, Any]:
    """Load one JSON object with a stable policy error on malformed input."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CoveragePolicyError(f"could not read {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise CoveragePolicyError(f"{path} must contain a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-json", type=Path, required=True)
    parser.add_argument("--ratchet", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--base-rev")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = load_json(args.coverage_json)
        ratchet = load_json(args.ratchet)
        records = normalized_file_records(
            report,
            repo_root=args.repo_root,
            project_root=args.project_root,
        )
        failures = aggregate_coverage_failures(report, ratchet)
        if args.base_rev is not None:
            changed = changed_python_lines(args.repo_root, args.base_rev)
            failures.extend(
                ratchet_regression_failures(
                    ratchet,
                    base_ratchet(args.repo_root, args.base_rev, args.ratchet),
                )
            )
            failures.extend(
                changed_coverage_failures(
                    changed,
                    records,
                    repo_root=args.repo_root,
                )
            )
    except CoveragePolicyError as exc:
        print(f"COVERAGE_POLICY_ERROR: {exc}")
        return 2
    if failures:
        for failure in failures:
            print(f"COVERAGE_POLICY_FAILURE: {failure}")
        return 1
    print("COVERAGE_POLICY_PASS: aggregate ratchet and 100% changed-code coverage satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
