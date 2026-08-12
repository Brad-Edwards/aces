"""Branch-aware changed-code and aggregate coverage policy tests."""

from __future__ import annotations

import json
import runpy
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from coverage import Coverage
from tools import check_changed_coverage as coverage_policy

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_CONFIG = REPO_ROOT / "implementations" / "python" / "pyproject.toml"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    source = repo / "implementations" / "python" / "packages" / "demo.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    (repo / "tools").mkdir()
    (repo / "noxfile.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "init")
    _git(repo, "config", "user.email", "coverage@example.invalid")
    _git(repo, "config", "user.name", "Coverage Test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    return repo, _git(repo, "rev-parse", "HEAD")


def _report(*, line_covered: int = 1, branch_covered: int = 1) -> dict[str, object]:
    return {
        "meta": {"branch_coverage": True},
        "files": {},
        "totals": {
            "covered_lines": line_covered,
            "num_statements": 1,
            "covered_branches": branch_covered,
            "num_branches": 1,
        },
    }


def _ratchet(*, line: float = 100.0, branch: float = 100.0) -> dict[str, object]:
    return {"minimum_line_percent": line, "minimum_branch_percent": branch}


def _install_coverage_config(project: Path) -> Path:
    project.mkdir(parents=True, exist_ok=True)
    config_path = project / "pyproject.toml"
    shutil.copyfile(PROJECT_CONFIG, config_path)
    return config_path


def _main_paths(repo: Path) -> tuple[Path, Path]:
    project = repo / "implementations" / "python"
    config_path = _install_coverage_config(project)
    ratchet_path = repo / "tools" / "coverage_ratchet.json"
    ratchet_path.parent.mkdir(parents=True, exist_ok=True)
    return config_path, ratchet_path


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("implementations/python/packages/raes/core.py", True),
        ("tools/check.py", True),
        ("noxfile.py", True),
        ("implementations/python/hatch_build.py", True),
        ("implementations/python/tests/test_core.py", False),
        ("tools/data.json", False),
    ],
)
def test_measured_python_path_policy(path: str, expected: bool) -> None:
    assert coverage_policy.is_measured_python_path(path) is expected


def test_added_lines_from_zero_context_patch() -> None:
    patch = """@@ -1 +1,3 @@
-old
+one
+two
+three
@@ -9,0 +12 @@
+last
@@ -20,2 +30,0 @@
-gone
"""
    assert coverage_policy.added_lines_from_patch(patch) == {1, 2, 3, 12}
    assert coverage_policy.added_lines_from_patch("not a patch") == set()


def test_deletion_anchors_ignore_nonsemantic_base_lines() -> None:
    patch = """@@ -4 +3,0 @@
-    and second
@@ -8 +6,0 @@
-    # explanation
"""
    assert coverage_policy.deletion_anchor_lines_from_patch(
        patch,
        base_semantic_lines={4},
        current_semantic_lines={1, 2, 3, 4, 5, 6},
    ) == {3, 4}


@pytest.mark.parametrize(
    ("patch", "current_lines", "expected"),
    [
        ("@@ -1 +0,0 @@\n-old\n", {2, 3}, {2}),
        ("@@ -9 +8,0 @@\n-old\n", {1, 2}, {2}),
    ],
)
def test_deletion_anchors_use_the_available_surviving_neighbor(
    patch: str,
    current_lines: set[int],
    expected: set[int],
) -> None:
    assert (
        coverage_policy.deletion_anchor_lines_from_patch(
            patch,
            base_semantic_lines={1, 9},
            current_semantic_lines=current_lines,
        )
        == expected
    )


def test_changed_python_lines_reads_committed_and_worktree_changes(tmp_path: Path) -> None:
    repo, base = _repository(tmp_path)
    source = repo / "implementations" / "python" / "packages" / "demo.py"
    source.write_text("value = 1\nadded = 2\n", encoding="utf-8")
    (repo / "tools" / "new_check.py").write_text("ENABLED = True\n", encoding="utf-8")
    tests = repo / "implementations" / "python" / "tests"
    tests.mkdir()
    (tests / "test_demo.py").write_text("assert True\n", encoding="utf-8")

    assert coverage_policy.changed_python_lines(repo, base) == {
        "implementations/python/packages/demo.py": {2},
        "tools/new_check.py": {1},
    }


def test_changed_python_lines_checks_every_line_of_renamed_destinations(tmp_path: Path) -> None:
    repo, _ = _repository(tmp_path)
    source = repo / "implementations" / "python" / "packages" / "demo.py"
    original = "".join(f"value_{line} = {line}\n" for line in range(1, 6))
    source.write_text(original, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "expand source")
    base = _git(repo, "rev-parse", "HEAD")
    renamed = source.with_name("renamed.py")
    _git(repo, "mv", source.relative_to(repo).as_posix(), renamed.relative_to(repo).as_posix())
    renamed.write_text(f"{original}added = 6\n", encoding="utf-8")

    assert coverage_policy.changed_python_lines(repo, base) == {
        "implementations/python/packages/renamed.py": {1, 2, 3, 4, 5, 6}
    }


def test_changed_python_lines_maps_deletion_only_multiline_semantics(tmp_path: Path) -> None:
    repo, _ = _repository(tmp_path)
    source = repo / "implementations" / "python" / "packages" / "demo.py"
    source.write_text(
        """def choose(first: bool, second: bool) -> int:
    if (
        first
        and second
    ):
        return 1
    return 0
""",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add multiline branch")
    base = _git(repo, "rev-parse", "HEAD")
    source.write_text(
        """def choose(first: bool, second: bool) -> int:
    if (
        first
    ):
        return 1
    return 0
""",
        encoding="utf-8",
    )

    path = "implementations/python/packages/demo.py"
    changed = coverage_policy.changed_python_lines(repo, base)
    assert changed == {path: {3, 4}}
    assert coverage_policy.changed_coverage_failures(
        changed,
        {
            path: {
                "executed_lines": [1, 2, 3, 5],
                "missing_lines": [6],
                "executed_branches": [[2, 5]],
                "missing_branches": [[2, 6]],
            }
        },
        repo_root=repo,
    ) == [f"{path}:2->6: changed branch exit is not covered"]


def test_changed_python_lines_ignores_deletion_only_comments(tmp_path: Path) -> None:
    repo, _ = _repository(tmp_path)
    source = repo / "implementations" / "python" / "packages" / "demo.py"
    source.write_text("value = (\n    # explanation\n    1\n)\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add comment")
    base = _git(repo, "rev-parse", "HEAD")
    source.write_text("value = (\n    1\n)\n", encoding="utf-8")

    assert coverage_policy.changed_python_lines(repo, base) == {"implementations/python/packages/demo.py": set()}


def test_changed_python_lines_rejects_undecodable_current_source(tmp_path: Path) -> None:
    repo, base = _repository(tmp_path)
    source = repo / "implementations" / "python" / "packages" / "demo.py"
    source.write_bytes(b"\xff")

    with pytest.raises(coverage_policy.CoveragePolicyError, match="could not inspect changed Python source"):
        coverage_policy.changed_python_lines(repo, base)


def test_changed_python_lines_rejects_unknown_and_nonancestor_bases(tmp_path: Path) -> None:
    repo, base = _repository(tmp_path)
    with pytest.raises(coverage_policy.CoveragePolicyError, match="does not resolve"):
        coverage_policy.changed_python_lines(repo, "does-not-exist")

    (repo / "noxfile.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "second")
    descendant = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", base)
    with pytest.raises(coverage_policy.CoveragePolicyError, match="is not an ancestor"):
        coverage_policy.changed_python_lines(repo, descendant)


def test_git_failure_without_stderr_uses_stable_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        coverage_policy.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=args, returncode=1, stdout=b"", stderr=b""),
    )
    with pytest.raises(coverage_policy.CoveragePolicyError, match="git status failed"):
        coverage_policy._git(tmp_path, "status")


def test_normalized_file_records_resolves_project_repo_and_absolute_paths(tmp_path: Path) -> None:
    repo, _ = _repository(tmp_path)
    project = repo / "implementations" / "python"
    tool = repo / "tools" / "check.py"
    tool.write_text("pass\n", encoding="utf-8")
    report = {
        "files": {
            "packages/demo.py": {"executed_lines": [1]},
            "tools/check.py": {"executed_lines": [1]},
            str(repo / "noxfile.py"): {"executed_lines": [1]},
            "tests/test_demo.py": {"executed_lines": [1]},
        }
    }

    assert coverage_policy.normalized_file_records(report, repo_root=repo, project_root=project) == {
        "implementations/python/packages/demo.py": {"executed_lines": [1]},
        "tools/check.py": {"executed_lines": [1]},
        "noxfile.py": {"executed_lines": [1]},
    }


@pytest.mark.parametrize(
    "report",
    [
        {},
        {"files": []},
        {"files": {1: {}}},
        {"files": {"noxfile.py": []}},
    ],
)
def test_normalized_file_records_rejects_malformed_data(tmp_path: Path, report: dict[str, object]) -> None:
    repo, _ = _repository(tmp_path)
    with pytest.raises(coverage_policy.CoveragePolicyError):
        coverage_policy.normalized_file_records(
            report,
            repo_root=repo,
            project_root=repo / "implementations" / "python",
        )


def test_normalized_file_records_rejects_paths_outside_repository(tmp_path: Path) -> None:
    repo, _ = _repository(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text("pass\n", encoding="utf-8")
    with pytest.raises(coverage_policy.CoveragePolicyError, match="escapes the repository"):
        coverage_policy.normalized_file_records(
            {"files": {str(outside): {}}},
            repo_root=repo,
            project_root=repo / "implementations" / "python",
        )


def test_canonical_coverage_config_omits_acquired_cache_but_keeps_repo_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    project = repo / "implementations" / "python"
    config_path = _install_coverage_config(project)
    owned_tool = repo / "tools" / "owned.py"
    owned_tool.parent.mkdir(parents=True)
    owned_tool.write_text("OWNED = True\n", encoding="utf-8")
    acquired = repo / ".cache" / "raes-sdl" / "tooling" / "isabelle" / "appendix_gen.py"
    acquired.parent.mkdir(parents=True)
    acquired.write_text('print "Python 2 syntax"\n', encoding="utf-8")
    monkeypatch.chdir(project)

    measured = Coverage(config_file=str(config_path), data_file=str(tmp_path / ".coverage"))
    measured.start()
    runpy.run_path(str(owned_tool))
    measured.stop()
    measured.save()
    report_path = tmp_path / "coverage.xml"
    measured.xml_report(outfile=str(report_path))

    report = report_path.read_text(encoding="utf-8")
    assert "tools/owned.py" in report
    assert "appendix_gen.py" not in report


def test_canonical_coverage_config_passes_policy_validation() -> None:
    coverage_policy.validate_coverage_config(coverage_policy.load_toml(PROJECT_CONFIG))


@pytest.mark.parametrize(
    ("section", "key", "value", "match"),
    [
        ("run", "branch", False, "enable branch data"),
        ("run", "relative_files", False, "repository-relative files"),
        ("run", "source", ["packages"], "canonical repository source root"),
        ("run", "omit", ["*/.cache/*"], "canonical non-source paths"),
        ("run", "plugins", ["weakener"], "can narrow measurement"),
        ("report", "include_namespace_packages", False, "namespace-package"),
        ("report", "exclude_also", [".*"], "governed legacy exclusion"),
        ("report", "partial_branches", [".*"], "can suppress measurement"),
        ("report", "partial_also", [".*"], "can suppress measurement"),
        ("report", "exclude_lines", [".*"], "can suppress measurement"),
    ],
)
def test_coverage_config_rejects_scope_and_suppression_weakening(
    section: str,
    key: str,
    value: object,
    match: str,
) -> None:
    config = deepcopy(coverage_policy.load_toml(PROJECT_CONFIG))
    config["tool"]["coverage"][section][key] = value

    with pytest.raises(coverage_policy.CoveragePolicyError, match=match):
        coverage_policy.validate_coverage_config(config)


@pytest.mark.parametrize("missing", ["tool", "coverage", "run", "report"])
def test_coverage_config_requires_governed_tables(missing: str) -> None:
    config = deepcopy(coverage_policy.load_toml(PROJECT_CONFIG))
    if missing == "tool":
        config.pop("tool")
    elif missing == "coverage":
        config["tool"].pop("coverage")
    else:
        config["tool"]["coverage"].pop(missing)

    with pytest.raises(coverage_policy.CoveragePolicyError, match="must contain"):
        coverage_policy.validate_coverage_config(config)


def test_coverage_config_rejects_path_aliases() -> None:
    config = deepcopy(coverage_policy.load_toml(PROJECT_CONFIG))
    config["tool"]["coverage"]["paths"] = {"source": ["implementations/python/packages", "elsewhere"]}

    with pytest.raises(coverage_policy.CoveragePolicyError, match="path aliases"):
        coverage_policy.validate_coverage_config(config)


def test_changed_coverage_reports_missing_files_lines_and_branch_exits(tmp_path: Path) -> None:
    changed = {
        "implementations/python/packages/absent.py": {1},
        "implementations/python/packages/demo.py": {1, 2, 3, 4},
    }
    packages = tmp_path / "implementations" / "python" / "packages"
    packages.mkdir(parents=True)
    (packages / "absent.py").write_text("ABSENT = True\n", encoding="utf-8")
    (packages / "demo.py").write_text("\n".join(f"VALUE_{line} = {line}" for line in range(1, 5)), encoding="utf-8")
    records = {
        "implementations/python/packages/demo.py": {
            "executed_lines": [1],
            "missing_lines": [2],
            "excluded_lines": [4],
            "missing_branches": [[1, 2], [3, -1], [4], 5],
        }
    }

    assert coverage_policy.changed_coverage_failures(changed, records, repo_root=tmp_path) == [
        "implementations/python/packages/absent.py: changed measured Python file is absent from coverage data",
        "implementations/python/packages/demo.py:2: changed executable line is not covered",
        "implementations/python/packages/demo.py:4: changed line is excluded from coverage",
        "implementations/python/packages/demo.py:1->2: changed branch exit is not covered",
        "implementations/python/packages/demo.py:3->-1: changed branch exit is not covered",
    ]
    (tmp_path / "noxfile.py").write_text("\n" * 9, encoding="utf-8")
    assert (
        coverage_policy.changed_coverage_failures(
            {"noxfile.py": {9}},
            {"noxfile.py": {}},
            repo_root=tmp_path,
        )
        == []
    )


def test_changed_coverage_ignores_changed_comments_and_blank_lines(tmp_path: Path) -> None:
    path = "tools/comments.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text("# changed comment\n\n", encoding="utf-8")

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {1, 2}},
            {path: {}},
            repo_root=tmp_path,
        )
        == []
    )


def test_changed_coverage_maps_multiline_condition_changes_to_branch_owner(tmp_path: Path) -> None:
    path = "tools/multiline_branch.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """def choose(flag: bool) -> int:
    if (
        flag
    ):
        return 1
    return 0
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {3}},
        {
            path: {
                "executed_lines": [1, 2, 5],
                "missing_lines": [6],
                "excluded_lines": [],
                "executed_branches": [[2, 5]],
                "missing_branches": [[2, 6]],
            }
        },
        repo_root=tmp_path,
    ) == [f"{path}:2->6: changed branch exit is not covered"]


def test_changed_coverage_keeps_branch_owner_when_condition_continuation_is_reported(tmp_path: Path) -> None:
    path = "tools/reported_condition.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """def choose(flag: bool) -> int:
    if (
        check(flag)
    ):
        return 1
    return 0
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {3}},
        {
            path: {
                "executed_lines": [1, 2, 3, 5],
                "missing_lines": [6],
                "missing_branches": [[2, 6]],
            }
        },
        repo_root=tmp_path,
    ) == [f"{path}:2->6: changed branch exit is not covered"]


def test_changed_coverage_maps_multiline_loop_iterable_to_branch_owner(tmp_path: Path) -> None:
    path = "tools/multiline_loop.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """for item in (
    items
):
    consume(item)
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {2}},
        {
            path: {
                "executed_lines": [1, 2, 4],
                "missing_lines": [],
                "missing_branches": [[1, -1]],
            }
        },
        repo_root=tmp_path,
    ) == [f"{path}:1->-1: changed branch exit is not covered"]


def test_changed_coverage_maps_multiline_match_subject_to_case_branches(tmp_path: Path) -> None:
    path = "tools/multiline_match.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """match (
    value
):
    case 1:
        consume_one()
    case _:
        consume_other()
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {2}},
        {
            path: {
                "executed_lines": [1, 4, 5],
                "missing_lines": [6, 7],
                "executed_branches": [[4, 5]],
                "missing_branches": [[4, 6]],
            }
        },
        repo_root=tmp_path,
    ) == [f"{path}:4->6: changed branch exit is not covered"]


def test_changed_coverage_maps_multiline_match_guard_to_case_branch(tmp_path: Path) -> None:
    path = "tools/multiline_match_guard.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """match value:
    case int() if (
        positive(value)
    ):
        consume_positive()
    case _:
        consume_other()
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {3}},
        {
            path: {
                "executed_lines": [1, 2, 5],
                "missing_lines": [6, 7],
                "executed_branches": [[2, 5]],
                "missing_branches": [[2, 6]],
            }
        },
        repo_root=tmp_path,
    ) == [f"{path}:2->6: changed branch exit is not covered"]


def test_changed_coverage_maps_comprehension_changes_when_reported_as_branches(tmp_path: Path) -> None:
    path = "tools/multiline_comprehension.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """result = [
    normalize(value)
    for value in values
]
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {2}},
        {
            path: {
                "executed_lines": [1, 2, 3],
                "missing_lines": [],
                "executed_branches": [[3, 2]],
                "missing_branches": [[3, -1]],
            }
        },
        repo_root=tmp_path,
    ) == [f"{path}:3->-1: changed branch exit is not covered"]


def test_changed_coverage_does_not_map_unrelated_code_to_comprehension_branch(tmp_path: Path) -> None:
    path = "tools/unrelated_comprehension.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """result = [
    normalize(value)
    for value in values
]
unrelated = updated_value()
""",
        encoding="utf-8",
    )

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {5}},
            {
                path: {
                    "executed_lines": [1, 2, 3, 5],
                    "missing_lines": [],
                    "executed_branches": [[3, 2]],
                    "missing_branches": [[3, -1]],
                }
            },
            repo_root=tmp_path,
        )
        == []
    )


def test_changed_coverage_maps_multiline_expression_changes_to_statement_owner(tmp_path: Path) -> None:
    path = "tools/multiline_expression.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """value = (
    build_value()
)
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {2}},
        {path: {"executed_lines": [], "missing_lines": [1], "missing_branches": []}},
        repo_root=tmp_path,
    ) == [f"{path}:1: changed executable line is not covered"]


def test_changed_coverage_does_not_map_comment_only_continuation_lines(tmp_path: Path) -> None:
    path = "tools/multiline_comment.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """if (
    # explanation only
    enabled
):
    run()
""",
        encoding="utf-8",
    )

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {2}},
            {path: {"executed_lines": [1, 5], "missing_lines": [], "missing_branches": [[1, -1]]}},
            repo_root=tmp_path,
        )
        == []
    )


def test_changed_coverage_fails_closed_when_code_has_no_reported_owner(tmp_path: Path) -> None:
    path = "tools/unmapped.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")

    assert coverage_policy.changed_coverage_failures(
        {path: {1}},
        {path: {}},
        repo_root=tmp_path,
    ) == [f"{path}:1: changed code is absent from the coverage line mapping"]


def test_changed_coverage_ignores_docstring_only_changes(tmp_path: Path) -> None:
    path = "tools/docstrings.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        '''"""Module
documentation.
"""

class Example:
    """Class documentation."""

    def sync(self) -> None:
        """Sync documentation."""

    async def asynchronous(self) -> None:
        """Async documentation."""
''',
        encoding="utf-8",
    )

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {2, 6, 9, 12}},
            {path: {"executed_lines": [5, 8, 11], "missing_lines": [], "missing_branches": []}},
            repo_root=tmp_path,
        )
        == []
    )


def test_changed_coverage_allows_only_structural_default_exclusions(tmp_path: Path) -> None:
    path = "implementations/python/packages/declarations.py"
    source = tmp_path / path
    source.parent.mkdir(parents=True)
    source.write_text(
        """from __future__ import annotations
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from demo import Model

class Store(Protocol):
    def load(self) -> Model: ...

    def save(
        self,
        value: Model,
    ) -> None: ...

class Concrete:
    def omitted(self) -> None: ...
""",
        encoding="utf-8",
    )
    changed_lines = {4, 5, 8, 9, 10, 11, 12, 13, 14, 16}
    records = {
        path: {
            "executed_lines": [],
            "missing_lines": [],
            "excluded_lines": sorted(changed_lines),
            "missing_branches": [],
        }
    }

    assert coverage_policy.changed_coverage_failures(
        {path: changed_lines},
        records,
        repo_root=tmp_path,
    ) == [f"{path}:16: changed line is excluded from coverage"]


def test_changed_coverage_rejects_untrusted_type_checking_and_recognizes_generic_protocols(tmp_path: Path) -> None:
    path = "implementations/python/packages/qualified_declarations.py"
    source = tmp_path / path
    source.parent.mkdir(parents=True)
    source.write_text(
        """from __future__ import annotations

import typing
from typing import Protocol

if typing.TYPE_CHECKING:
    from demo import Model

class Store(Protocol[Model]):
    @property
    def item(self) -> Model:
        \"\"\"Return the current model.\"\"\"
        ...

    def implemented(self) -> None:
        return None

class Derived(Store, typing.Protocol):
    async def save(self) -> None: ...

class Generated(factory()):
    pass
""",
        encoding="utf-8",
    )
    structural_lines = {6, 7, 10, 11, 12, 13, 19}

    assert coverage_policy.changed_coverage_failures(
        {path: structural_lines},
        {
            path: {
                "executed_lines": [],
                "missing_lines": [],
                "excluded_lines": sorted(structural_lines),
                "missing_branches": [],
            }
        },
        repo_root=tmp_path,
    ) == [
        f"{path}:6: changed line is excluded from coverage",
        f"{path}:7: changed line is excluded from coverage",
        f"{path}:10: changed line is excluded from coverage",
        f"{path}:19: changed line is excluded from coverage",
    ]


@pytest.mark.parametrize(
    "prelude",
    [
        "TYPE_CHECKING = True\n",
        "from other_module import TYPE_CHECKING\n",
        "from typing import TYPE_CHECKING as TYPE_CHECKING\n",
        "from typing import TYPE_CHECKING\nTYPE_CHECKING = runtime_flag\n",
        "from typing import TYPE_CHECKING\nmodule.TYPE_CHECKING = runtime_flag\n",
        'from typing import TYPE_CHECKING\nglobals()["TYPE_CHECKING"] = True\n',
        "from typing import TYPE_CHECKING\nglobals().update(TYPE_CHECKING=True)\n",
        "from typing import TYPE_CHECKING\nglobals().update(dict(TYPE_CHECKING=True))\n",
        "from typing import TYPE_CHECKING\nglobals().update(**{'TYPE_CHECKING': True})\n",
        'from typing import TYPE_CHECKING\nsetattr(module, "TYPE_CHECKING", True)\n',
    ],
)
def test_changed_coverage_rejects_spoofed_or_rebound_type_checking(
    tmp_path: Path,
    prelude: str,
) -> None:
    path = "tools/spoofed_type_checking.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(f"{prelude}if TYPE_CHECKING:\n    hidden_runtime = 1\n", encoding="utf-8")
    if_line = len(prelude.splitlines()) + 1

    assert coverage_policy.changed_coverage_failures(
        {path: {if_line, if_line + 1}},
        {
            path: {
                "executed_lines": [],
                "missing_lines": [],
                "excluded_lines": [if_line, if_line + 1],
                "missing_branches": [],
            }
        },
        repo_root=tmp_path,
    ) == [
        f"{path}:{if_line}: changed line is excluded from coverage",
        f"{path}:{if_line + 1}: changed line is excluded from coverage",
    ]


def test_changed_coverage_allows_read_only_globals_lookup_of_type_checking(tmp_path: Path) -> None:
    path = "tools/read_type_checking.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        'from typing import TYPE_CHECKING\nglobals().get("TYPE_CHECKING")\nif TYPE_CHECKING:\n    from demo import Model\n',
        encoding="utf-8",
    )

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {3, 4}},
            {path: {"executed_lines": [], "missing_lines": [], "excluded_lines": [3, 4]}},
            repo_root=tmp_path,
        )
        == []
    )


@pytest.mark.parametrize(
    "prelude",
    [
        "Protocol = runtime_base\n",
        "from other_module import Protocol\n",
        "from typing import Protocol as Protocol\n",
        'from typing import Protocol\nglobals()["Protocol"] = runtime_base\n',
        "from typing import Protocol\nglobals().update(dict(Protocol=runtime_base))\n",
        "from typing import Protocol\nglobals().update(**{'Protocol': runtime_base})\n",
    ],
)
def test_changed_coverage_rejects_spoofed_or_rebound_protocol(tmp_path: Path, prelude: str) -> None:
    path = "tools/spoofed_protocol.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(f"{prelude}class Hidden(Protocol):\n    def runtime(self): ...\n", encoding="utf-8")
    method_line = len(prelude.splitlines()) + 2

    assert coverage_policy.changed_coverage_failures(
        {path: {method_line}},
        {
            path: {
                "executed_lines": [],
                "missing_lines": [],
                "excluded_lines": [method_line],
                "missing_branches": [],
            }
        },
        repo_root=tmp_path,
    ) == [f"{path}:{method_line}: changed line is excluded from coverage"]


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param('ns = globals()\nns["$SYMBOL"] = $VALUE', id="mapping-alias"),
        pytest.param('ns = locals()\nns["$SYMBOL"] = $VALUE', id="locals-mapping-alias"),
        pytest.param('ns = vars()\nns["$SYMBOL"] = $VALUE', id="vars-mapping-alias"),
        pytest.param('namespace = globals\nnamespace()["$SYMBOL"] = $VALUE', id="factory-alias"),
        pytest.param('exec("$SYMBOL = $VALUE")', id="exec"),
        pytest.param('exec("$SYMBOL = $VALUE", globals())', id="exec-namespace"),
        pytest.param('run = exec\nrun("$SYMBOL = $VALUE")', id="exec-alias"),
        pytest.param(
            'run = eval\nrun("globals().__setitem__(\\"$SYMBOL\\", $VALUE)")',
            id="eval-alias",
        ),
        pytest.param(
            'import sys\nvars(sys.modules[__name__])["$SYMBOL"] = $VALUE',
            id="module-vars",
        ),
        pytest.param(
            'import sys\nsys.modules[__name__].__dict__["$SYMBOL"] = $VALUE',
            id="module-dict",
        ),
        pytest.param(
            'import sys\ngetattr(sys.modules[__name__], "__dict__")["$SYMBOL"] = $VALUE',
            id="module-dict-getattr",
        ),
        pytest.param("dict.update(globals(), $SYMBOL=$VALUE)", id="dict-update-descriptor"),
        pytest.param(
            'dict.__setitem__(globals(), "$SYMBOL", $VALUE)',
            id="dict-setitem-descriptor",
        ),
        pytest.param('mutate(globals(), "$SYMBOL", $VALUE)', id="unknown-mutator"),
        pytest.param("globals().__init__($SYMBOL=$VALUE)", id="mapping-init"),
        pytest.param(
            'import builtins, sys\nbuiltins.setattr(sys.modules[__name__], "$SYMBOL", $VALUE)',
            id="builtins-setattr",
        ),
        pytest.param(
            'from builtins import setattr as assign\nimport sys\nassign(sys.modules[__name__], "$SYMBOL", $VALUE)',
            id="imported-setattr",
        ),
        pytest.param(
            'import sys\nassign = setattr\nassign(sys.modules[__name__], "$SYMBOL", $VALUE)',
            id="setattr-alias",
        ),
        pytest.param(
            'import sys\nremove = delattr\nremove(sys.modules[__name__], "$SYMBOL")',
            id="delattr-alias",
        ),
        pytest.param("reader = globals().get", id="read-method-escape"),
        pytest.param("from runtime_symbols import *", id="star-import"),
        pytest.param(
            'from builtins import globals as ns\nns()["$SYMBOL"] = $VALUE',
            id="imported-builtins-globals",
        ),
        pytest.param(
            'import builtins\nbuiltins.globals()["$SYMBOL"] = $VALUE',
            id="attribute-builtins-globals",
        ),
        pytest.param(
            'import builtins\ngetattr(builtins, "globals")()["$SYMBOL"] = $VALUE',
            id="getattr-builtins-globals",
        ),
        pytest.param(
            'import builtins\nbuiltins.getattr(builtins, "globals")()["$SYMBOL"] = $VALUE',
            id="attribute-getattr-builtins-globals",
        ),
        pytest.param(
            "from builtins import getattr as lookup\nimport builtins\n"
            'lookup(builtins, "globals")()["$SYMBOL"] = $VALUE',
            id="imported-getattr-builtins-globals",
        ),
        pytest.param(
            'import builtins\nlookup = getattr\nlookup(builtins, "globals")()["$SYMBOL"] = $VALUE',
            id="aliased-getattr-builtins-globals",
        ),
        pytest.param(
            'from builtins import vars as ns\nns()["$SYMBOL"] = $VALUE',
            id="imported-builtins-vars",
        ),
        pytest.param('__builtins__["exec"]("$SYMBOL = $VALUE")', id="builtins-mapping-exec"),
        pytest.param(
            'import inspect\ninspect.currentframe().f_globals["$SYMBOL"] = $VALUE',
            id="inspect-frame-globals",
        ),
        pytest.param(
            'import sys\nsys._getframe().f_globals["$SYMBOL"] = $VALUE',
            id="sys-frame-globals",
        ),
        pytest.param(
            'import sys\nsys._getframe().f_locals["$SYMBOL"] = $VALUE',
            id="sys-frame-locals",
        ),
    ],
)
@pytest.mark.parametrize(("symbol", "value"), [("TYPE_CHECKING", "True"), ("Protocol", "runtime_base")])
def test_structural_typing_rejects_namespace_escape_and_dynamic_rebinding(
    tmp_path: Path,
    mutation: str,
    symbol: str,
    value: str,
) -> None:
    path = f"tools/unsafe_{symbol.lower()}.py"
    rendered_mutation = mutation.replace("$SYMBOL", symbol).replace("$VALUE", value)
    prelude = f"from typing import {symbol}\n{rendered_mutation}\n"
    if symbol == "TYPE_CHECKING":
        construct = "if TYPE_CHECKING:\n    hidden_runtime = 1\n"
    else:
        construct = "class Hidden(Protocol):\n    def runtime(self): ...\n"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(f"{prelude}{construct}", encoding="utf-8")
    first_line = len(prelude.splitlines()) + 1
    changed_lines = {first_line, first_line + 1} if symbol == "TYPE_CHECKING" else {first_line + 1}

    assert coverage_policy.changed_coverage_failures(
        {path: changed_lines},
        {
            path: {
                "executed_lines": [],
                "missing_lines": [],
                "excluded_lines": sorted(changed_lines),
                "missing_branches": [],
            }
        },
        repo_root=tmp_path,
    ) == [f"{path}:{line}: changed line is excluded from coverage" for line in sorted(changed_lines)]


def test_changed_coverage_allows_proven_read_only_namespace_access_for_protocol(tmp_path: Path) -> None:
    path = "tools/read_protocol_namespace.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        'from typing import Protocol\nglobals().get("unrelated")\nglobals()["__name__"]\n'
        "class Reader(Protocol):\n    def read(self): ...\n",
        encoding="utf-8",
    )

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {5}},
            {path: {"executed_lines": [], "missing_lines": [], "excluded_lines": [5]}},
            repo_root=tmp_path,
        )
        == []
    )


def test_changed_coverage_rejects_runtime_protocol_default_expression(tmp_path: Path) -> None:
    path = "tools/protocol_default.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """from typing import Protocol

class Store(Protocol):
    def load(
        self,
        default: int = runtime_default(),
    ) -> int: ...
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {6}},
        {path: {"executed_lines": [], "missing_lines": [], "excluded_lines": [3, 4, 5, 6, 7]}},
        repo_root=tmp_path,
    ) == [f"{path}:6: changed line is excluded from coverage"]


def test_changed_coverage_rejects_runtime_protocol_annotation_expression(tmp_path: Path) -> None:
    path = "tools/protocol_annotation.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """from typing import Protocol

class Store(Protocol):
    def load(
        self,
        *args: runtime_args(),
        key: runtime_annotation(),
        **kwargs: runtime_kwargs(),
    ) -> str: ...

    def close(self): ...
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {6, 7, 8}},
        {path: {"executed_lines": [], "missing_lines": [], "excluded_lines": [3, 4, 5, 6, 7, 8, 9, 11]}},
        repo_root=tmp_path,
    ) == [
        f"{path}:6: changed line is excluded from coverage",
        f"{path}:7: changed line is excluded from coverage",
        f"{path}:8: changed line is excluded from coverage",
    ]


def test_changed_coverage_rejects_every_eager_protocol_annotation_span(tmp_path: Path) -> None:
    path = "tools/eager_protocol_annotations.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """from typing import Protocol

class Store(Protocol):
    def load(
        self,
        key: runtime_types.Key,
        value: runtime_types["Value"],
    ) -> Left | Right: ...
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {6, 7, 8}},
        {path: {"executed_lines": [], "missing_lines": [], "excluded_lines": [3, 4, 5, 6, 7, 8]}},
        repo_root=tmp_path,
    ) == [
        f"{path}:6: changed line is excluded from coverage",
        f"{path}:7: changed line is excluded from coverage",
        f"{path}:8: changed line is excluded from coverage",
    ]


def test_changed_coverage_allows_postponed_protocol_annotation_expression(tmp_path: Path) -> None:
    path = "tools/postponed_protocol_annotation.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """from __future__ import annotations
from typing import Protocol

class Store(Protocol):
    def load(
        self,
        key: runtime_annotation(),
    ) -> str: ...
""",
        encoding="utf-8",
    )

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {7}},
            {path: {"executed_lines": [], "missing_lines": [], "excluded_lines": [4, 5, 6, 7, 8]}},
            repo_root=tmp_path,
        )
        == []
    )


def test_changed_coverage_rejects_runtime_protocol_decorator_and_class_base(tmp_path: Path) -> None:
    path = "tools/protocol_runtime_headers.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """from typing import Protocol

class Store(runtime_base(), Protocol):
    @runtime_decorator()
    def load(self) -> int: ...
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {3, 4}},
        {path: {"executed_lines": [], "missing_lines": [], "excluded_lines": [3, 4, 5]}},
        repo_root=tmp_path,
    ) == [
        f"{path}:3: changed line is excluded from coverage",
        f"{path}:4: changed line is excluded from coverage",
    ]


def test_changed_coverage_allows_literal_protocol_default_declaration(tmp_path: Path) -> None:
    path = "tools/protocol_literal_default.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """from __future__ import annotations
from typing import Protocol

class Reader(Protocol):
    def read(self, size: int = ...) -> bytes: ...
""",
        encoding="utf-8",
    )

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {5}},
            {path: {"executed_lines": [], "missing_lines": [], "excluded_lines": [4, 5]}},
            repo_root=tmp_path,
        )
        == []
    )


def test_changed_coverage_allows_protocol_class_docstring(tmp_path: Path) -> None:
    path = "tools/documented_protocol.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """from __future__ import annotations
from typing import Protocol

class Reader(Protocol):
    \"\"\"Read bytes.\"\"\"

    def read(self) -> bytes: ...
""",
        encoding="utf-8",
    )

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {7}},
            {path: {"executed_lines": [], "missing_lines": [], "excluded_lines": [4, 5, 7]}},
            repo_root=tmp_path,
        )
        == []
    )


@pytest.mark.parametrize(
    "pragma",
    [
        "# pragma: no cover",
        "# pragma no branch",
        "# pragmano branch",
        "# PRAGMA : NO branch - rationale",
    ],
)
def test_changed_coverage_forbids_explicit_pragmas_on_changed_lines(tmp_path: Path, pragma: str) -> None:
    path = "tools/example.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(f'notice = "# pragma: no cover"\nif enabled:  {pragma}\n    run()\n', encoding="utf-8")

    assert coverage_policy.changed_coverage_failures(
        {path: {1, 2}},
        {
            path: {
                "executed_lines": [1, 2],
                "missing_lines": [],
                "excluded_lines": [2],
                "missing_branches": [],
            }
        },
        repo_root=tmp_path,
    ) == [f"{path}:2: coverage exclusion pragma governs changed executable code"]


def test_changed_coverage_rejects_unchanged_pragma_that_governs_changed_header(tmp_path: Path) -> None:
    path = "tools/suppressed_branch.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """if (
    enabled
):  # pragma: no branch
    run()
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {2}},
        {path: {"executed_lines": [1, 4], "missing_lines": [], "missing_branches": []}},
        repo_root=tmp_path,
    ) == [f"{path}:3: coverage exclusion pragma governs changed executable code"]


def test_changed_coverage_rejects_pragma_that_governs_changed_match_guard(tmp_path: Path) -> None:
    path = "tools/suppressed_match.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """match value:
    case int() if (
        positive(value)
    ):  # pragma: no branch
        consume_positive()
    case _:
        consume_other()
""",
        encoding="utf-8",
    )

    assert coverage_policy.changed_coverage_failures(
        {path: {3}},
        {path: {"executed_lines": [1, 2, 5], "missing_lines": [6, 7], "missing_branches": []}},
        repo_root=tmp_path,
    ) == [f"{path}:4: coverage exclusion pragma governs changed executable code"]


def test_changed_coverage_allows_unrelated_change_beside_legacy_pragma(tmp_path: Path) -> None:
    path = "tools/legacy_pragma.py"
    source = tmp_path / path
    source.parent.mkdir()
    source.write_text(
        """def guarded() -> None:
    try:
        optional_import()
    except ImportError:  # pragma: no cover
        explain_missing_dependency()

unrelated = updated_value()
""",
        encoding="utf-8",
    )

    assert (
        coverage_policy.changed_coverage_failures(
            {path: {7}},
            {
                path: {
                    "executed_lines": [1, 2, 3, 7],
                    "missing_lines": [],
                    "excluded_lines": [4, 5],
                    "missing_branches": [],
                }
            },
            repo_root=tmp_path,
        )
        == []
    )


@pytest.mark.parametrize(
    ("path", "contents", "match"),
    [
        ("tools/missing.py", None, "could not inspect changed Python source"),
        ("tools/invalid.py", "if True\n", "could not parse changed Python source"),
    ],
)
def test_changed_coverage_rejects_uninspectable_source(
    tmp_path: Path,
    path: str,
    contents: str | None,
    match: str,
) -> None:
    if contents is not None:
        source = tmp_path / path
        source.parent.mkdir()
        source.write_text(contents, encoding="utf-8")

    with pytest.raises(coverage_policy.CoveragePolicyError, match=match):
        coverage_policy.changed_coverage_failures({path: {1}}, {}, repo_root=tmp_path)


def test_aggregate_coverage_ratchet_passes_and_reports_both_regressions() -> None:
    report = {
        "meta": {"branch_coverage": True},
        "totals": {
            "covered_lines": 9,
            "num_statements": 10,
            "covered_branches": 7,
            "num_branches": 10,
        },
    }
    assert coverage_policy.aggregate_coverage_failures(report, _ratchet(line=90, branch=70)) == []
    assert coverage_policy.aggregate_coverage_failures(report, _ratchet(line=91, branch=71)) == [
        "aggregate line coverage 90.000% is below 91.000%",
        "aggregate branch coverage 70.000% is below 71.000%",
    ]


def test_aggregate_coverage_handles_empty_denominators() -> None:
    report = _report()
    report["totals"] = {
        "covered_lines": 0,
        "num_statements": 0,
        "covered_branches": 0,
        "num_branches": 0,
    }
    assert coverage_policy.aggregate_coverage_failures(report, _ratchet()) == []


@pytest.mark.parametrize(
    "report",
    [
        {},
        {"meta": {}, "totals": {}},
        {"meta": {"branch_coverage": False}, "totals": {}},
        {"meta": {"branch_coverage": True}},
    ],
)
def test_aggregate_coverage_requires_branch_metadata_and_totals(report: dict[str, object]) -> None:
    with pytest.raises(coverage_policy.CoveragePolicyError):
        coverage_policy.aggregate_coverage_failures(report, _ratchet())


@pytest.mark.parametrize(
    ("ratchet", "match"),
    [
        ({"minimum_branch_percent": 90}, "must be a number"),
        ({"minimum_line_percent": "invalid", "minimum_branch_percent": 90}, "must be a number"),
        ({"minimum_line_percent": float("inf"), "minimum_branch_percent": 90}, "between 0 and 100"),
        ({"minimum_line_percent": -1, "minimum_branch_percent": 90}, "between 0 and 100"),
        ({"minimum_line_percent": 90, "minimum_branch_percent": 101}, "between 0 and 100"),
    ],
)
def test_aggregate_coverage_rejects_invalid_ratchet_floors(
    ratchet: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(coverage_policy.CoveragePolicyError, match=match):
        coverage_policy.aggregate_coverage_failures(_report(), ratchet)


def test_ratchet_history_is_monotonic_after_initial_adoption(tmp_path: Path) -> None:
    repo, initial_base = _repository(tmp_path)
    ratchet_path = repo / "tools" / "coverage_ratchet.json"

    assert coverage_policy.base_ratchet(repo, initial_base, ratchet_path) is None

    prior = _ratchet(line=80, branch=70)
    ratchet_path.write_text(json.dumps(prior), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add ratchet")
    ratchet_base = _git(repo, "rev-parse", "HEAD")

    assert coverage_policy.base_ratchet(repo, ratchet_base, ratchet_path) == prior
    assert coverage_policy.ratchet_regression_failures(_ratchet(line=81, branch=70), prior) == []
    assert coverage_policy.ratchet_regression_failures(_ratchet(line=79, branch=69), prior) == [
        "aggregate line ratchet 79.000% is below base 80.000%",
        "aggregate branch ratchet 69.000% is below base 70.000%",
    ]
    assert coverage_policy.ratchet_regression_failures(_ratchet(), None) == []


def test_ratchet_cannot_move_away_from_its_canonical_history(tmp_path: Path) -> None:
    repo, base = _repository(tmp_path)
    renamed = repo / "tools" / "coverage_floor.json"
    renamed.write_text(json.dumps(_ratchet(line=1, branch=1)), encoding="utf-8")

    with pytest.raises(coverage_policy.CoveragePolicyError, match="must remain at the canonical path"):
        coverage_policy.base_ratchet(repo, base, renamed)


def test_missing_base_ratchet_fails_after_prior_canonical_adoption(tmp_path: Path) -> None:
    repo, _ = _repository(tmp_path)
    ratchet_path = repo / "tools" / "coverage_ratchet.json"
    ratchet_path.write_text(json.dumps(_ratchet(line=80, branch=70)), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "adopt ratchet")
    ratchet_path.unlink()
    _git(repo, "add", "-u")
    _git(repo, "commit", "-m", "remove ratchet")
    base_without_ratchet = _git(repo, "rev-parse", "HEAD")

    with pytest.raises(coverage_policy.CoveragePolicyError, match="missing at base.*after its canonical adoption"):
        coverage_policy.base_ratchet(repo, base_without_ratchet, ratchet_path)


def test_base_ratchet_rejects_outside_and_malformed_files(tmp_path: Path) -> None:
    repo, _ = _repository(tmp_path)
    outside = tmp_path / "outside.json"
    with pytest.raises(coverage_policy.CoveragePolicyError, match="escapes the repository"):
        coverage_policy.base_ratchet(repo, "HEAD", outside)

    ratchet_path = repo / "tools" / "coverage_ratchet.json"
    ratchet_path.write_bytes(b"\xff")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "invalid unicode ratchet")
    with pytest.raises(coverage_policy.CoveragePolicyError, match="is not valid JSON"):
        coverage_policy.base_ratchet(repo, "HEAD", ratchet_path)

    ratchet_path.write_text("[]", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "non-object ratchet")
    with pytest.raises(coverage_policy.CoveragePolicyError, match="must contain a JSON object"):
        coverage_policy.base_ratchet(repo, "HEAD", ratchet_path)


def test_load_json_accepts_objects_and_rejects_bad_inputs(tmp_path: Path) -> None:
    path = tmp_path / "value.json"
    path.write_text('{"value": 1}', encoding="utf-8")
    assert coverage_policy.load_json(path) == {"value": 1}

    path.write_text("[]", encoding="utf-8")
    with pytest.raises(coverage_policy.CoveragePolicyError, match="JSON object"):
        coverage_policy.load_json(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(coverage_policy.CoveragePolicyError, match="could not read"):
        coverage_policy.load_json(path)
    with pytest.raises(coverage_policy.CoveragePolicyError, match="could not read"):
        coverage_policy.load_json(tmp_path / "missing.json")


def test_load_toml_accepts_objects_and_rejects_bad_inputs(tmp_path: Path) -> None:
    path = tmp_path / "value.toml"
    path.write_text("value = 1\n", encoding="utf-8")
    assert coverage_policy.load_toml(path) == {"value": 1}

    path.write_text("value = [\n", encoding="utf-8")
    with pytest.raises(coverage_policy.CoveragePolicyError, match="could not read"):
        coverage_policy.load_toml(path)
    with pytest.raises(coverage_policy.CoveragePolicyError, match="could not read"):
        coverage_policy.load_toml(tmp_path / "missing.toml")


def test_main_pass_failure_and_policy_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo, base = _repository(tmp_path)
    project = repo / "implementations" / "python"
    source = project / "packages" / "demo.py"
    source.write_text("value = 2\n", encoding="utf-8")
    report_path = tmp_path / "coverage.json"
    config_path, ratchet_path = _main_paths(repo)
    report = _report()
    report["files"] = {str(source): {"executed_lines": [1], "missing_lines": [], "missing_branches": []}}
    report_path.write_text(json.dumps(report), encoding="utf-8")
    ratchet_path.write_text(json.dumps(_ratchet()), encoding="utf-8")
    args = [
        "--coverage-json",
        str(report_path),
        "--coverage-config",
        str(config_path),
        "--ratchet",
        str(ratchet_path),
        "--repo-root",
        str(repo),
        "--project-root",
        str(project),
        "--base-rev",
        base,
    ]

    assert coverage_policy.main(args) == 0
    assert "COVERAGE_POLICY_PASS" in capsys.readouterr().out

    report["files"] = {str(source): {"executed_lines": [], "missing_lines": [1], "missing_branches": []}}
    report_path.write_text(json.dumps(report), encoding="utf-8")
    assert coverage_policy.main(args) == 1
    assert "COVERAGE_POLICY_FAILURE" in capsys.readouterr().out

    assert coverage_policy.main([*args[:-1], "unknown"]) == 2
    assert "COVERAGE_POLICY_ERROR" in capsys.readouterr().out


def test_main_can_check_only_the_aggregate(tmp_path: Path) -> None:
    report_path = tmp_path / "coverage.json"
    config_path, ratchet_path = _main_paths(tmp_path)
    report_path.write_text(json.dumps(_report()), encoding="utf-8")
    ratchet_path.write_text(json.dumps(_ratchet()), encoding="utf-8")

    assert (
        coverage_policy.main(
            [
                "--coverage-json",
                str(report_path),
                "--coverage-config",
                str(config_path),
                "--ratchet",
                str(ratchet_path),
                "--repo-root",
                str(tmp_path),
                "--project-root",
                str(tmp_path),
            ]
        )
        == 0
    )


def test_script_entrypoint_delegates_to_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_path = tmp_path / "coverage.json"
    config_path, ratchet_path = _main_paths(tmp_path)
    report_path.write_text(json.dumps(_report()), encoding="utf-8")
    ratchet_path.write_text(json.dumps(_ratchet()), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_changed_coverage.py",
            "--coverage-json",
            str(report_path),
            "--coverage-config",
            str(config_path),
            "--ratchet",
            str(ratchet_path),
            "--repo-root",
            str(tmp_path),
            "--project-root",
            str(tmp_path),
        ],
    )

    with pytest.raises(SystemExit, match="0"):
        runpy.run_path(str(Path(coverage_policy.__file__)), run_name="__main__")
