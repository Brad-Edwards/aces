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
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_HUNK = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<start>\d+)(?:,(?P<count>\d+))? @@",
    re.MULTILINE,
)
_FORBIDDEN_COVERAGE_PRAGMA = re.compile(r"#\s*pragma\s*:?\s*no\s+(?:cover|branch)\b", re.IGNORECASE)
_MEASURED_PREFIXES = ("implementations/python/packages/", "tools/")
_MEASURED_FILES = frozenset({"noxfile.py", "implementations/python/hatch_build.py"})
_CANONICAL_COVERAGE_CONFIG = "implementations/python/pyproject.toml"
_CANONICAL_RATCHET = "tools/coverage_ratchet.json"
_COVERAGE_SOURCE = ("../..",)
_COVERAGE_OMIT = frozenset(
    {
        "*/.cache/*",
        "*/docs/*",
        "*/implementations/python/.venv/*",
        "*/implementations/python/tests/*",
    }
)
_COVERAGE_EXCLUDE_ALSO = ("def " + "_default_runner",)
_FORBIDDEN_RUN_OPTIONS = frozenset({"include", "plugins", "source_dirs", "source_pkgs"})
_FORBIDDEN_REPORT_OPTIONS = frozenset(
    {
        "exclude_lines",
        "ignore_errors",
        "include",
        "omit",
        "partial_also",
        "partial_branches",
    }
)
_NON_CODE_TOKEN_TYPES = frozenset(
    {
        tokenize.COMMENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.INDENT,
        tokenize.NEWLINE,
        tokenize.NL,
    }
)


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


def deletion_anchor_lines_from_patch(
    patch: str,
    *,
    base_semantic_lines: set[int],
    current_semantic_lines: set[int],
) -> set[int]:
    """Map semantic deletion-only hunks to surviving destination neighbors."""

    anchors: set[int] = set()
    for match in _HUNK.finditer(patch):
        old_start = int(match.group("old_start"))
        old_count = int(match.group("old_count") or "1")
        new_start = int(match.group("start"))
        new_count = int(match.group("count") or "1")
        if new_count != 0 or not set(range(old_start, old_start + old_count)) & base_semantic_lines:
            continue
        before = [line for line in current_semantic_lines if line <= max(1, new_start)]
        after = [line for line in current_semantic_lines if line >= max(1, new_start + 1)]
        if before:
            anchors.add(max(before))
        if after:
            anchors.add(min(after))
    return anchors


def _semantic_physical_lines(source: str, *, path: str) -> set[int]:
    tree = _parse_source(source, path=path)
    tokens = tuple(tokenize.generate_tokens(io.StringIO(source).readline))
    return _significant_source_lines(tokens) - _docstring_lines(tree)


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
            destination_lines = added_lines_from_patch(patch)
            base_source = _git(repo_root, "show", f"{base_rev}:{path}", check=False)
            if base_source.returncode == 0:
                try:
                    before = base_source.stdout.decode("utf-8")
                    after = (repo_root / path).read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    raise CoveragePolicyError(f"could not inspect changed Python source {path}: {exc}") from exc
                destination_lines.update(
                    deletion_anchor_lines_from_patch(
                        patch,
                        base_semantic_lines=_semantic_physical_lines(before, path=path),
                        current_semantic_lines=_semantic_physical_lines(after, path=path),
                    )
                )
            changed[path] = destination_lines
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


def _canonical_policy_path(repo_root: Path, path: Path, expected: str, *, label: str) -> str:
    try:
        relative_path = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise CoveragePolicyError(f"{label} path escapes the repository: {path}") from exc
    if relative_path != expected:
        raise CoveragePolicyError(f"{label} must remain at the canonical path {expected}")
    return relative_path


def load_toml(path: Path) -> Mapping[str, Any]:
    """Load one TOML object with a stable policy error on malformed input."""

    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise CoveragePolicyError(f"could not read {path}: {exc}") from exc


def _required_mapping(parent: Mapping[str, Any], key: str, *, label: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise CoveragePolicyError(f"coverage config must contain {label}")
    return value


def validate_coverage_config(config: Mapping[str, Any]) -> None:
    """Reject coverage configuration that can narrow or suppress the gate."""

    tool = _required_mapping(config, "tool", label="[tool]")
    coverage = _required_mapping(tool, "coverage", label="[tool.coverage]")
    if "paths" in coverage:
        raise CoveragePolicyError("coverage config path aliases can merge unrelated source files")
    run = _required_mapping(coverage, "run", label="[tool.coverage.run]")
    report = _required_mapping(coverage, "report", label="[tool.coverage.report]")

    if run.get("branch") is not True:
        raise CoveragePolicyError("coverage config must enable branch data")
    if run.get("relative_files") is not True:
        raise CoveragePolicyError("coverage config must use repository-relative files")
    if tuple(run.get("source", ())) != _COVERAGE_SOURCE:
        raise CoveragePolicyError("coverage config must measure the canonical repository source root")
    configured_omit = run.get("omit")
    if (
        not isinstance(configured_omit, Sequence)
        or isinstance(configured_omit, (str, bytes))
        or len(configured_omit) != len(_COVERAGE_OMIT)
        or set(configured_omit) != _COVERAGE_OMIT
    ):
        raise CoveragePolicyError("coverage config omit list must contain only canonical non-source paths")
    forbidden_run = sorted(_FORBIDDEN_RUN_OPTIONS & run.keys())
    if forbidden_run:
        raise CoveragePolicyError(f"coverage config run option can narrow measurement: {forbidden_run[0]}")

    if report.get("include_namespace_packages") is not True:
        raise CoveragePolicyError("coverage config must discover namespace-package source files")
    if tuple(report.get("exclude_also", ())) != _COVERAGE_EXCLUDE_ALSO:
        raise CoveragePolicyError("coverage config may contain only the governed legacy exclusion")
    forbidden_report = sorted(_FORBIDDEN_REPORT_OPTIONS & report.keys())
    if forbidden_report:
        raise CoveragePolicyError(f"coverage config report option can suppress measurement: {forbidden_report[0]}")


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


def _literal_expression(node: ast.expr) -> bool:
    try:
        ast.literal_eval(node)
    except (ValueError, TypeError):
        return False
    return True


def _annotation_expressions(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[ast.expr, ...]:
    arguments = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    annotations = [argument.annotation for argument in arguments if argument.annotation is not None]
    for variadic in (node.args.vararg, node.args.kwarg):
        if variadic is not None and variadic.annotation is not None:
            annotations.append(variadic.annotation)
    if node.returns is not None:
        annotations.append(node.returns)
    return tuple(annotations)


def _has_dynamic_eager_evaluation(node: ast.expr) -> bool:
    dynamic_nodes = (
        ast.Await,
        ast.Call,
        ast.DictComp,
        ast.GeneratorExp,
        ast.Lambda,
        ast.ListComp,
        ast.NamedExpr,
        ast.SetComp,
        ast.Yield,
        ast.YieldFrom,
    )
    return any(isinstance(candidate, dynamic_nodes) for candidate in ast.walk(node))


def _postpones_annotations(tree: ast.Module) -> bool:
    return any(
        isinstance(statement, ast.ImportFrom)
        and statement.module == "__future__"
        and any(alias.name == "annotations" for alias in statement.names)
        for statement in tree.body
    )


def _protocol_declaration_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    annotations_postponed: bool,
) -> set[int]:
    lines = set(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    unsafe_defaults = [default for default in node.args.defaults if not _literal_expression(default)]
    unsafe_defaults.extend(
        default for default in node.args.kw_defaults if default is not None and not _literal_expression(default)
    )
    runtime_expressions = list(unsafe_defaults)
    if not annotations_postponed:
        runtime_expressions.extend(
            annotation for annotation in _annotation_expressions(node) if _has_dynamic_eager_evaluation(annotation)
        )
    for expression in runtime_expressions:
        lines.difference_update(range(expression.lineno, (expression.end_lineno or expression.lineno) + 1))
    return lines


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


def _namespace_mapping_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"globals", "locals", "vars"}
        and not node.args
        and not node.keywords
    )


def _dynamic_symbol_rebinding(node: ast.AST, symbol: str) -> bool:
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.ctx, (ast.Store, ast.Del))
        and _namespace_mapping_call(node.value)
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == symbol
    ):
        return True
    if not isinstance(node, ast.Call):
        return False
    if (
        isinstance(node.func, ast.Name)
        and node.func.id in {"setattr", "delattr"}
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == symbol
    ):
        return True
    if not isinstance(node.func, ast.Attribute) or not _namespace_mapping_call(node.func.value):
        return False
    if node.func.attr not in {"__setitem__", "pop", "setdefault", "update"}:
        return False
    return any(
        isinstance(candidate, ast.Constant) and candidate.value == symbol
        for argument in node.args
        for candidate in ast.walk(argument)
    ) or any(keyword.arg == symbol for keyword in node.keywords)


def _rebinds_imported_symbol(node: ast.AST, symbol: str) -> bool:
    return (
        isinstance(node, ast.Name)
        and node.id == symbol
        and isinstance(node.ctx, (ast.Store, ast.Del))
        or isinstance(node, ast.Attribute)
        and node.attr == symbol
        and isinstance(node.ctx, (ast.Store, ast.Del))
        or isinstance(node, ast.arg)
        and node.arg == symbol
        or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name == symbol
        or isinstance(node, ast.ExceptHandler)
        and node.name == symbol
        or isinstance(node, (ast.MatchAs, ast.MatchStar))
        and node.name == symbol
        or isinstance(node, ast.MatchMapping)
        and node.rest == symbol
        or _dynamic_symbol_rebinding(node, symbol)
    )


def _trusted_typing_import_lines(tree: ast.Module, symbol: str) -> tuple[int, ...]:
    canonical_aliases: set[int] = set()
    import_lines: list[int] = []
    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom) or statement.level != 0 or statement.module != "typing":
            continue
        for alias in statement.names:
            if alias.name == symbol and alias.asname is None:
                canonical_aliases.add(id(alias))
                import_lines.append(statement.lineno)

    for node in ast.walk(tree):
        if isinstance(node, ast.alias):
            bound_name = node.asname or node.name.split(".", maxsplit=1)[0]
            if bound_name == symbol and id(node) not in canonical_aliases:
                return ()
        elif _rebinds_imported_symbol(node, symbol):
            return ()
    return tuple(import_lines)


def _canonical_typing_reference(node: ast.expr, symbol: str) -> bool:
    while isinstance(node, ast.Subscript):
        node = node.value
    return isinstance(node, ast.Name) and node.id == symbol


def _parse_source(source: str, *, path: str) -> ast.Module:
    try:
        return ast.parse(source, filename=path)
    except SyntaxError as exc:
        raise CoveragePolicyError(f"could not parse changed Python source {path}: {exc.msg}") from exc


def _structural_exclusion_lines(tree: ast.Module) -> set[int]:
    structural: set[int] = set()
    type_checking_import_lines = _trusted_typing_import_lines(tree, "TYPE_CHECKING")
    protocol_import_lines = _trusted_typing_import_lines(tree, "Protocol")
    annotations_postponed = _postpones_annotations(tree)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "TYPE_CHECKING"
            and any(line < node.lineno for line in type_checking_import_lines)
        ):
            first_body_line = min(statement.lineno for statement in node.body)
            structural.update(range(node.lineno, first_body_line))
            for statement in node.body:
                structural.update(range(statement.lineno, (statement.end_lineno or statement.lineno) + 1))

    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.ClassDef)
            or not any(_canonical_typing_reference(base, "Protocol") for base in node.bases)
            or not any(line < node.lineno for line in protocol_import_lines)
        ):
            continue
        if _is_declaration_only_protocol(node):
            for declaration in node.body:
                if isinstance(declaration, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    structural.update(
                        _protocol_declaration_lines(
                            declaration,
                            annotations_postponed=annotations_postponed,
                        )
                    )
            continue
        for declaration in node.body:
            if not isinstance(declaration, (ast.FunctionDef, ast.AsyncFunctionDef)) or not _is_ellipsis_declaration(
                declaration
            ):
                continue
            structural.update(
                _protocol_declaration_lines(
                    declaration,
                    annotations_postponed=annotations_postponed,
                )
            )
    return structural


def _significant_source_lines(tokens: Sequence[tokenize.TokenInfo]) -> set[int]:
    significant: set[int] = set()
    for token in tokens:
        if token.type in _NON_CODE_TOKEN_TYPES:
            continue
        significant.update(range(token.start[0], token.end[0] + 1))
    return significant


def _docstring_lines(tree: ast.Module) -> set[int]:
    lines: set[int] = set()
    containers = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, containers) or not node.body:
            continue
        statement = node.body[0]
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
            if isinstance(statement.value.value, str):
                lines.update(range(statement.lineno, (statement.end_lineno or statement.lineno) + 1))
    return lines


def _owning_coverage_line(tree: ast.Module, physical_line: int, coverage_lines: set[int]) -> int | None:
    candidates: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start in coverage_lines and start <= physical_line <= end:
            candidates.append((end - start, start))
    return min(candidates)[1] if candidates else None


def _contains_line(node: ast.AST, physical_line: int) -> bool:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    return isinstance(start, int) and isinstance(end, int) and start <= physical_line <= end


def _branch_header_owners(tree: ast.Module, physical_line: int, branch_sources: set[int]) -> set[int]:
    owners: set[int] = set()
    for node in ast.walk(tree):
        header_nodes: tuple[ast.AST, ...]
        if isinstance(node, (ast.If, ast.While, ast.IfExp)):
            header_nodes = (node.test,)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            header_nodes = (node.target, node.iter)
        elif isinstance(node, ast.Match):
            case_sources = {case.pattern.lineno for case in node.cases if case.pattern.lineno in branch_sources}
            if _contains_line(node.subject, physical_line):
                owners.update(case_sources)
            for case in node.cases:
                source = case.pattern.lineno
                case_header = (case.pattern,) if case.guard is None else (case.pattern, case.guard)
                if source in branch_sources and any(_contains_line(part, physical_line) for part in case_header):
                    owners.add(source)
            continue
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            if _contains_line(node, physical_line):
                start = node.lineno
                end = node.end_lineno or start
                owners.update(source for source in branch_sources if start <= source <= end)
            continue
        else:
            continue
        if node.lineno in branch_sources and any(_contains_line(header, physical_line) for header in header_nodes):
            owners.add(node.lineno)
    return owners


def _semantic_owner_spans(tree: ast.Module) -> tuple[tuple[int, int], ...]:
    """Return statement-like spans to which an inline coverage pragma can apply."""

    spans: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.stmt, ast.ExceptHandler)):
            continue
        start = node.lineno
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            start = min((decorator.lineno for decorator in node.decorator_list), default=start)
        spans.add((start, node.end_lineno or node.lineno))
        if isinstance(node, ast.Match):
            for case in node.cases:
                case_end = max(
                    (statement.end_lineno or statement.lineno for statement in case.body),
                    default=case.pattern.end_lineno or case.pattern.lineno,
                )
                spans.add((case.pattern.lineno, case_end))
    return tuple(sorted(spans, key=lambda span: (span[1] - span[0], span[0], span[1])))


def _governing_coverage_pragmas(
    tokens: Sequence[tokenize.TokenInfo],
    *,
    tree: ast.Module,
    significant_changed: set[int],
    significant_lines: set[int],
) -> set[int]:
    """Return pragma lines whose semantic statement owns changed code."""

    owner_spans = _semantic_owner_spans(tree)
    governed: set[int] = set()
    for token in tokens:
        pragma_line = token.start[0]
        if (
            token.type != tokenize.COMMENT
            or pragma_line not in significant_lines
            or not _FORBIDDEN_COVERAGE_PRAGMA.search(token.string)
        ):
            continue
        owner = next((span for span in owner_spans if span[0] <= pragma_line <= span[1]), None)
        if owner is not None and any(owner[0] <= line <= owner[1] for line in significant_changed):
            governed.add(pragma_line)
    return governed


def _branch_edges(record: Mapping[str, Any], key: str) -> set[tuple[int, int]]:
    return {
        (int(edge[0]), int(edge[1]))
        for edge in record.get(key, [])
        if isinstance(edge, Sequence) and not isinstance(edge, (str, bytes)) and len(edge) == 2
    }


def _expanded_execution_lines(
    changed_lines: set[int],
    *,
    significant_lines: set[int],
    tree: ast.Module,
    record: Mapping[str, Any],
) -> tuple[set[int], set[int]]:
    coverage_lines = {
        int(line) for key in ("executed_lines", "missing_lines", "excluded_lines") for line in record.get(key, [])
    }
    branch_edges = _branch_edges(record, "executed_branches") | _branch_edges(record, "missing_branches")
    branch_sources = {source for source, _destination in branch_edges}
    for source, destination in branch_edges:
        coverage_lines.add(source)
        if destination > 0:
            coverage_lines.add(destination)

    significant_changed = (changed_lines & significant_lines) - _docstring_lines(tree)
    expanded = set(significant_changed)
    unmapped: set[int] = set()
    for physical_line in significant_changed:
        expanded.update(_branch_header_owners(tree, physical_line, branch_sources))
    candidates = significant_changed - coverage_lines
    for physical_line in sorted(candidates):
        owner = _owning_coverage_line(tree, physical_line, coverage_lines)
        if owner is None:
            unmapped.add(physical_line)
        else:
            expanded.add(owner)
    return expanded, unmapped


def _source_coverage_policy(
    repo_root: Path,
    path: str,
    changed_lines: set[int],
) -> tuple[ast.Module, set[int], set[int], set[int]]:
    source_path = repo_root / path
    try:
        source = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CoveragePolicyError(f"could not inspect changed Python source {path}: {exc}") from exc
    tree = _parse_source(source, path=path)
    tokens = tuple(tokenize.generate_tokens(io.StringIO(source).readline))
    structural = _structural_exclusion_lines(tree)
    significant_lines = _significant_source_lines(tokens)
    significant_changed = (changed_lines & significant_lines) - _docstring_lines(tree)
    forbidden = _governing_coverage_pragmas(
        tokens,
        tree=tree,
        significant_changed=significant_changed,
        significant_lines=significant_lines,
    )
    return tree, structural, forbidden, significant_lines


def changed_coverage_failures(
    changed: Mapping[str, set[int]],
    records: Mapping[str, Mapping[str, Any]],
    *,
    repo_root: Path,
) -> list[str]:
    """Return deterministic failures for uncovered changed lines and branches."""

    failures: list[str] = []
    for path, changed_lines in sorted(changed.items()):
        tree, structural_exclusions, forbidden_pragmas, significant_lines = _source_coverage_policy(
            repo_root, path, changed_lines
        )
        for line in sorted(forbidden_pragmas):
            failures.append(f"{path}:{line}: coverage exclusion pragma governs changed executable code")
        record = records.get(path)
        if record is None:
            failures.append(f"{path}: changed measured Python file is absent from coverage data")
            continue
        execution_lines, unmapped_lines = _expanded_execution_lines(
            changed_lines,
            significant_lines=significant_lines,
            tree=tree,
            record=record,
        )
        for line in sorted(unmapped_lines):
            failures.append(f"{path}:{line}: changed code is absent from the coverage line mapping")
        executed = {int(line) for line in record.get("executed_lines", [])}
        missing = {int(line) for line in record.get("missing_lines", [])}
        excluded = {int(line) for line in record.get("excluded_lines", [])}
        executable_changed = execution_lines & (executed | missing)
        for line in sorted(executable_changed & missing):
            failures.append(f"{path}:{line}: changed executable line is not covered")
        for line in sorted((execution_lines & excluded) - structural_exclusions - forbidden_pragmas):
            failures.append(f"{path}:{line}: changed line is excluded from coverage")
        missing_branches = _branch_edges(record, "missing_branches")
        for source, destination in sorted(edge for edge in missing_branches if edge[0] in execution_lines):
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

    relative_path = _canonical_policy_path(
        repo_root,
        ratchet_path,
        _CANONICAL_RATCHET,
        label="coverage ratchet",
    )
    result = _git(repo_root, "show", f"{base_rev}:{relative_path}", check=False)
    if result.returncode != 0:
        history = _git(repo_root, "log", "--format=%H", base_rev, "--", relative_path).stdout
        if history.strip():
            raise CoveragePolicyError(f"coverage ratchet is missing at base {base_rev!r} after its canonical adoption")
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
    for key, label in (
        ("minimum_line_percent", "line"),
        ("minimum_branch_percent", "branch"),
    ):
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
    parser.add_argument("--coverage-config", type=Path, required=True)
    parser.add_argument("--ratchet", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--base-rev")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _canonical_policy_path(
            args.repo_root,
            args.coverage_config,
            _CANONICAL_COVERAGE_CONFIG,
            label="coverage config",
        )
        _canonical_policy_path(
            args.repo_root,
            args.ratchet,
            _CANONICAL_RATCHET,
            label="coverage ratchet",
        )
        validate_coverage_config(load_toml(args.coverage_config))
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
