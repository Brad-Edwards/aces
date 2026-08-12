# ruff: noqa: E402, I001
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
import os
import shutil
import subprocess
import sys
import tempfile

import nox

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gitleaks_tool import ensure_gitleaks
from tools.osv_scanner_tool import (
    OSVScanOutcome,
    classify_osv_exit_code,
    ensure_osv_scanner,
    run_osv_scanner,
)
from tools.tool_versions import PRE_COMMIT_HOOKS_TOOL_SPEC, RUFF_TOOL_SPEC
from tools.vale_tool import ensure_vale
from tools.parallel_verification import VerificationLane, run_verification_lanes
from tools.verification_plan import (
    collect_git_changes,
    plan_for_changes,
    resolve_upstream,
    select_changed_python_tests,
)

PROJECT_ROOT = REPO_ROOT / "implementations" / "python"
PUBLIC_DOCS_ROOT = REPO_ROOT / "docs" / "public"
DOCS_BUILD_ROOT = REPO_ROOT / "docs" / "_build"
PUBLIC_DOCS_ENTRYPOINTS = (
    "README.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "GOVERNANCE.md",
    "MAINTAINERS.md",
    "SECURITY.md",
    "SUPPORT.md",
)
PUBLIC_DOCS_EXAMPLE_TESTS = (
    "implementations/python/tests/test_public_docs_policy.py::test_checked_in_quickstart_scenario_parses",
    "implementations/python/tests/test_public_docs_policy.py::test_readme_quickstart_matches_checked_in_scenario",
    "implementations/python/tests/test_public_docs_policy.py::test_participant_control_claim_example_is_bounded",
)
RUFF_CONFIG = PROJECT_ROOT / "pyproject.toml"
OSV_LOCKFILE_PATH = PROJECT_ROOT / "uv.lock"
OSV_REPORT_PATH = PROJECT_ROOT / "osv-scanner-report.json"
TARGETED_POLICY_TESTS = [
    "implementations/python/tests/test_repo_policy_tools.py",
    "implementations/python/tests/test_requirement_governance.py",
    "implementations/python/tests/test_semantic_coverage.py",
    "implementations/python/tests/test_assurance_policy.py",
    "implementations/python/tests/test_authority_boundary.py",
    "implementations/python/tests/test_concept_authority_governance.py",
    "implementations/python/tests/test_agent_guidance_policy.py",
    "implementations/python/tests/test_example_library_policy.py",
    "implementations/python/tests/test_public_docs_policy.py",
    "implementations/python/tests/test_public_project_readiness.py",
    "implementations/python/tests/test_vale_tool.py",
    "implementations/python/tests/test_verification_plan.py",
]
CONTRACT_TRIGGER_PREFIXES = (
    "contracts/",
    "implementations/python/packages/raes_contracts/",
    "implementations/python/packages/raes_backend_protocols/",
    "implementations/python/packages/raes_processor/",
    "tools/generate_contract_schemas.py",
    "tools/check_json_artifacts.py",
)
FULL_TEST_TRIGGER_PREFIXES = ("implementations/python/",)
TOOLING_TEST_TRIGGER_PREFIXES = (
    "tools/",
    ".github/workflows/ci.yml",
    ".pre-commit-config.yaml",
    "noxfile.py",
)
EXCLUDED_PREFIXES = ("research/",)
PRIVATE_KEY_EXCLUDE_PREFIXES = ("implementations/python/tests/",)
MAX_LARGE_FILE_KB = "500"
VERIFY_PROJECT_SYNCED_ENV = "RAES_VERIFY_PROJECT_SYNCED"
VERIFY_COVERAGE_FILE_ENV = "RAES_VERIFY_COVERAGE_FILE"
JSON_SCHEMA_WORKERS_ENV = "RAES_JSON_SCHEMA_WORKERS"

nox.options.default_venv_backend = "none"
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["verify"]


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    detail: str = ""
    duration_s: float | None = None


@dataclass(frozen=True)
class HygieneSelection:
    paths: list[str]
    source: str


class SessionReporter:
    def __init__(self, session: nox.Session, session_name: str) -> None:
        self.session = session
        self.session_name = session_name
        self.results: list[StageResult] = []

    def run(self, name: str, func: Callable[[], None], *, detail: str = "") -> None:
        self._log("START", name, detail)
        started = perf_counter()
        try:
            func()
        except Exception:
            duration_s = perf_counter() - started
            self.results.append(StageResult(name=name, status="FAIL", detail=detail, duration_s=duration_s))
            self._log("FAIL", name, detail, duration_s)
            raise
        duration_s = perf_counter() - started
        self.results.append(StageResult(name=name, status="PASS", detail=detail, duration_s=duration_s))
        self._log("PASS", name, detail, duration_s)

    def skip(self, name: str, reason: str) -> None:
        self.results.append(StageResult(name=name, status="SKIP", detail=reason))
        self._log("SKIP", name, reason)

    def summary(self) -> None:
        self.session.log(f"[{self.session_name}] stage summary:")
        if not self.results:
            self.session.log(f"[{self.session_name}]   SKIP no stages executed")
            return
        for result in self.results:
            duration = f" ({result.duration_s:.2f}s)" if result.duration_s is not None else ""
            detail = f" :: {result.detail}" if result.detail else ""
            self.session.log(f"[{self.session_name}]   {result.status:<4} {result.name}{duration}{detail}")

    def _log(self, status: str, name: str, detail: str, duration_s: float | None = None) -> None:
        duration = f" ({duration_s:.2f}s)" if duration_s is not None else ""
        suffix = f" :: {detail}" if detail else ""
        self.session.log(f"[{self.session_name}] {status}: {name}{duration}{suffix}")


def _run(
    session: nox.Session,
    *args: str,
    silent: bool = False,
    env: dict[str, str] | None = None,
) -> None:
    session.run(*args, external=True, silent=silent, env=env)


def _git_lines(*args: str) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _changed_paths(*, staged: bool = False, base_rev: str | None = None) -> list[str]:
    if staged:
        return _normalize_paths(_git_lines("diff", "--name-only", "--diff-filter=d", "--cached"))
    if base_rev:
        return _normalize_paths(_git_lines("diff", "--name-only", "--diff-filter=d", base_rev, "HEAD"))
    return _normalize_paths(_git_lines("diff", "--name-only", "--diff-filter=d", "HEAD"))


def _sync_project(session: nox.Session) -> None:
    if os.environ.get(VERIFY_PROJECT_SYNCED_ENV) == str(os.getppid()):
        return
    _run(
        session,
        "uv",
        "sync",
        "--project",
        str(PROJECT_ROOT),
        "--all-extras",
        "--frozen",
    )


def _run_project_python(session: nox.Session, script: str, *args: str) -> None:
    _run(
        session,
        "uv",
        "run",
        "--project",
        str(PROJECT_ROOT),
        "--frozen",
        "python",
        script,
        *args,
    )


def _run_uv_tool(session: nox.Session, spec: str, *args: str) -> None:
    _run(session, "uv", "tool", "run", "--from", spec, *args)


def _run_external_subprocess(*args: str) -> None:
    proc = subprocess.run(
        args,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    raise RuntimeError(f"{Path(args[0]).name} failed with exit code {proc.returncode}")


def _run_ruff(session: nox.Session, *args: str, project_relative: bool = False) -> None:
    command = [
        "uv",
        "tool",
        "run",
        "--from",
        RUFF_TOOL_SPEC,
        "ruff",
    ]
    if project_relative:
        with session.chdir(PROJECT_ROOT):
            _run(session, *command, *args)
        return
    _run(session, *command, "--config", str(RUFF_CONFIG), *args)


def _run_pytest(
    session: nox.Session,
    *args: str,
    coverage_file: Path | None = None,
    append_coverage: bool = False,
    finalize_coverage: bool = False,
    parallel: bool = False,
) -> None:
    _sync_project(session)
    normalized_args = [
        str((REPO_ROOT / arg).relative_to(PROJECT_ROOT)) if arg.startswith("implementations/python/") else arg
        for arg in args
    ]
    command = ["uv", "run", "--frozen", "python", "-m", "pytest"]
    if parallel:
        command.extend(["-n", "auto", "--maxprocesses=8", "--dist=worksteal"])
    coverage_env: dict[str, str] | None = None
    if coverage_file is not None:
        coverage_env = {"COVERAGE_FILE": str(coverage_file)}
        command.extend(["--cov", "--cov-config=pyproject.toml", "--cov-report="])
        if append_coverage:
            command.append("--cov-append")
    command.extend(normalized_args)
    with session.chdir(PROJECT_ROOT):
        _run(session, *command, env=coverage_env)
        if finalize_coverage:
            _run(session, "uv", "run", "--frozen", "coverage", "xml", env=coverage_env)
            _run(
                session,
                "uv",
                "run",
                "--frozen",
                "coverage",
                "report",
                "--fail-under=50",
                "--format=total",
                env=coverage_env,
            )


def _split_policy_session_args(posargs: list[str]) -> tuple[list[str], list[str], bool]:
    repo_args: list[str] = []
    requirement_args: list[str] = []
    skip_requirement = False
    index = 0
    while index < len(posargs):
        arg = posargs[index]
        if arg == "--skip-requirement":
            skip_requirement = True
            index += 1
            continue
        if arg == "--requirement-uid":
            requirement_args.extend([arg, posargs[index + 1]])
            index += 2
            continue
        if arg == "--base-rev":
            repo_args.extend([arg, posargs[index + 1]])
            requirement_args.extend([arg, posargs[index + 1]])
            index += 2
            continue
        repo_args.append(arg)
        requirement_args.append(arg)
        index += 1
    return repo_args, requirement_args, skip_requirement


def _parse_hygiene_posargs(posargs: Sequence[str], *, default_all_files: bool) -> HygieneSelection:
    staged = False
    base_rev: str | None = None
    all_files = default_all_files
    explicit_paths: list[str] = []
    index = 0
    values = list(posargs)
    while index < len(values):
        arg = values[index]
        if arg == "--staged":
            staged = True
            all_files = False
            index += 1
            continue
        if arg == "--all-files":
            all_files = True
            staged = False
            base_rev = None
            index += 1
            continue
        if arg == "--base-rev":
            base_rev = values[index + 1]
            all_files = False
            index += 2
            continue
        if arg == "--skip-requirement":
            index += 1
            continue
        if arg == "--requirement-uid":
            index += 2
            continue
        explicit_paths.append(arg)
        all_files = False
        index += 1
    if explicit_paths:
        return HygieneSelection(paths=_normalize_paths(explicit_paths), source="explicit path selection")
    if staged:
        return HygieneSelection(
            paths=_changed_paths(staged=True),
            source="staged tracked files",
        )
    if base_rev:
        return HygieneSelection(
            paths=_changed_paths(base_rev=base_rev),
            source=f"changes since {base_rev}",
        )
    if all_files:
        return HygieneSelection(paths=_tracked_repo_paths(), source="tracked repository files")
    return HygieneSelection(paths=_changed_paths(), source="working tree changes")


def _tracked_repo_paths() -> list[str]:
    return _normalize_paths(_git_lines("ls-files", "--cached", "--others", "--exclude-standard"))


def _normalize_paths(paths: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in paths:
        path = Path(raw).as_posix().strip("/")
        if not path or path.startswith(EXCLUDED_PREFIXES):
            continue
        absolute = REPO_ROOT / path
        if not absolute.is_file() or path in seen:
            continue
        seen.add(path)
        normalized.append(path)
    return normalized


def _text_paths(paths: list[str]) -> list[str]:
    text_paths: list[str] = []
    for path in paths:
        try:
            sample = (REPO_ROOT / path).read_bytes()[:8192]
        except OSError:
            continue
        if b"\x00" in sample:
            continue
        try:
            sample.decode("utf-8")
        except UnicodeDecodeError:
            continue
        text_paths.append(path)
    return text_paths


def _suffix_paths(paths: list[str], suffixes: tuple[str, ...]) -> list[str]:
    suffix_set = {suffix.lower() for suffix in suffixes}
    return [path for path in paths if Path(path).suffix.lower() in suffix_set]


def _chunked(paths: Sequence[str], *, size: int = 200) -> list[list[str]]:
    return [list(paths[index : index + size]) for index in range(0, len(paths), size)]


def _paths_trigger(paths: Iterable[str], prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefixes) or path in prefixes for path in paths)


def _run_pre_commit_hook(_session: nox.Session, command: str, *args: str, paths: list[str]) -> None:
    for batch in _chunked(paths):
        _run_external_subprocess(
            "uv",
            "tool",
            "run",
            "--from",
            PRE_COMMIT_HOOKS_TOOL_SPEC,
            command,
            *args,
            *batch,
        )


def _run_gitleaks_dir_scan(session: nox.Session, paths: list[str]) -> None:
    binary = ensure_gitleaks(REPO_ROOT)
    with tempfile.TemporaryDirectory(prefix="raes-gitleaks-") as tmpdir:
        scan_root = Path(tmpdir) / "scan"
        scan_root.mkdir()
        for path in paths:
            source = (REPO_ROOT / path).resolve()
            target = scan_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source)
        _run_external_subprocess(
            str(binary),
            "dir",
            "--config",
            str(REPO_ROOT / ".gitleaks.toml"),
            "--follow-symlinks",
            "--no-banner",
            "--redact",
            "--log-level",
            "warn",
            str(scan_root),
        )


def _run_hygiene(
    session: nox.Session,
    reporter: SessionReporter,
    *,
    posargs: Sequence[str],
    default_all_files: bool,
) -> None:
    selection = _parse_hygiene_posargs(posargs, default_all_files=default_all_files)
    paths = selection.paths
    detail = f"{len(paths)} files from {selection.source}"
    if not paths:
        reporter.skip(
            "hygiene / candidate path resolution",
            f"no files selected from {selection.source}",
        )
        return

    text_paths = _text_paths(paths)
    yaml_paths = _suffix_paths(paths, (".yaml", ".yml"))
    json_paths = _suffix_paths(paths, (".json",))
    private_key_paths = [path for path in paths if not path.startswith(PRIVATE_KEY_EXCLUDE_PREFIXES)]

    reporter.run(
        "hygiene / trailing whitespace",
        lambda: _run_pre_commit_hook(session, "trailing-whitespace-fixer", paths=text_paths),
        detail=f"{len(text_paths)} text files from {selection.source}",
    ) if text_paths else reporter.skip("hygiene / trailing whitespace", "no text files selected")

    reporter.run(
        "hygiene / eof newline",
        lambda: _run_pre_commit_hook(session, "end-of-file-fixer", paths=text_paths),
        detail=f"{len(text_paths)} text files from {selection.source}",
    ) if text_paths else reporter.skip("hygiene / eof newline", "no text files selected")

    reporter.run(
        "hygiene / yaml syntax",
        lambda: _run_pre_commit_hook(session, "check-yaml", "--unsafe", paths=yaml_paths),
        detail=f"{len(yaml_paths)} YAML files from {selection.source}",
    ) if yaml_paths else reporter.skip("hygiene / yaml syntax", "no YAML files selected")

    reporter.run(
        "hygiene / json syntax",
        lambda: _run_pre_commit_hook(session, "check-json", paths=json_paths),
        detail=f"{len(json_paths)} JSON files from {selection.source}",
    ) if json_paths else reporter.skip("hygiene / json syntax", "no JSON files selected")

    reporter.run(
        "hygiene / added large files",
        lambda: _run_pre_commit_hook(
            session,
            "check-added-large-files",
            "--maxkb",
            MAX_LARGE_FILE_KB,
            paths=paths,
        ),
        detail=detail,
    )

    reporter.run(
        "hygiene / merge conflict markers",
        lambda: _run_pre_commit_hook(session, "check-merge-conflict", paths=text_paths),
        detail=f"{len(text_paths)} text files from {selection.source}",
    ) if text_paths else reporter.skip("hygiene / merge conflict markers", "no text files selected")

    reporter.run(
        "hygiene / private key detection",
        lambda: _run_pre_commit_hook(session, "detect-private-key", paths=private_key_paths),
        detail=f"{len(private_key_paths)} files from {selection.source}",
    ) if private_key_paths else reporter.skip("hygiene / private key detection", "no eligible files selected")

    reporter.run(
        "hygiene / gitleaks",
        lambda: _run_gitleaks_dir_scan(session, paths),
        detail=detail,
    )


def _run_policy(session: nox.Session, reporter: SessionReporter, *args: str) -> None:
    _sync_project(session)
    reporter.run(
        "policy / conftest self-verify",
        lambda: _run(
            session,
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT),
            "--frozen",
            "python",
            "-c",
            "from tools.policy.conftest_tool import verify_conftest_policy; verify_conftest_policy()",
        ),
    )
    repo_args, requirement_args, skip_requirement = _split_policy_session_args(list(args))
    arg_list = list(args)
    adr_pin_args: list[str] = []
    if "--base-rev" in arg_list:
        base_index = arg_list.index("--base-rev")
        if base_index + 1 < len(arg_list):
            adr_pin_args = ["--base-rev", arg_list[base_index + 1]]
    reporter.run(
        "policy / repo policy",
        lambda: _run_project_python(session, "tools/check_repo_policy.py", *repo_args),
    )
    if skip_requirement:
        reporter.skip("policy / requirement governance", "skipped by --skip-requirement")
    else:
        reporter.run(
            "policy / requirement governance",
            lambda: _run_project_python(session, "tools/check_requirement_governance.py", *requirement_args),
        )
    # check_semantic_coverage.py validates live files on disk, not a staged
    # snapshot, so it is meaningless (and misleading) under --staged. It runs in
    # the working-tree policy invocations (`policy`, `hook-pre-push`, `verify`).
    if "--staged" in args:
        reporter.skip(
            "policy / semantic coverage ADR",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / assurance policy ADR",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / authority boundary ADR",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / deprecation lifecycle records",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / concept authority governance",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / behavioral relation claims",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / agent guidance profile",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / example library catalog",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / project positioning",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / identity cutover",
            "skipped on staged check; runs on push and verify",
        )
        reporter.skip(
            "policy / ADR acceptance-content pin",
            "skipped on staged check; runs on push and verify",
        )
    else:
        reporter.run(
            "policy / semantic coverage ADR",
            lambda: _run_project_python(session, "tools/check_semantic_coverage.py"),
        )
        reporter.run(
            "policy / assurance policy ADR",
            lambda: _run_project_python(session, "tools/check_assurance_policy.py"),
        )
        reporter.run(
            "policy / authority boundary ADR",
            lambda: _run_project_python(session, "tools/check_authority_boundary.py"),
        )
        reporter.run(
            "policy / deprecation lifecycle records",
            lambda: _run_project_python(session, "tools/check_deprecation_lifecycle.py"),
        )
        reporter.run(
            "policy / concept authority governance",
            lambda: _run_project_python(session, "tools/check_concept_authority_governance.py"),
        )
        reporter.run(
            "policy / behavioral relation claims",
            lambda: _run_project_python(session, "tools/check_behavioral_relation_claims.py"),
        )
        reporter.run(
            "policy / agent guidance profile",
            lambda: _run_project_python(session, "tools/check_agent_guidance.py"),
        )
        reporter.run(
            "policy / example library catalog",
            lambda: _run_project_python(session, "tools/check_example_library.py"),
        )
        reporter.run(
            "policy / project positioning",
            lambda: _run_project_python(session, "tools/check_project_positioning.py"),
        )
        reporter.run(
            "policy / identity cutover",
            lambda: _run_project_python(session, "tools/check_identity_cutover.py"),
        )
        reporter.run(
            "policy / ADR acceptance-content pin",
            lambda: _run_project_python(session, "tools/check_adr_immutability.py", *adr_pin_args),
        )


def _run_contracts(session: nox.Session, reporter: SessionReporter, *args: str) -> None:
    _sync_project(session)
    arg_list = list(args)
    schema_publication_args: list[str] = []
    json_artifact_args: list[str] = []
    index = 0
    while index < len(arg_list):
        arg = arg_list[index]
        if arg == "--staged":
            json_artifact_args.append(arg)
            index += 1
            continue
        if arg == "--base-rev":
            if index + 1 < len(arg_list):
                base_rev = arg_list[index + 1]
                schema_publication_args = ["--base-rev", base_rev]
                json_artifact_args.extend(["--base-rev", base_rev])
            index += 2
            continue
        if arg == "--requirement-uid":
            index += 2
            continue
        if arg == "--skip-requirement" or arg.startswith("-"):
            index += 1
            continue
        json_artifact_args.append(arg)
        index += 1
    reporter.run(
        "contracts / schema publication manifest",
        lambda: _run_project_python(session, "tools/check_schema_publication.py", *schema_publication_args),
    )
    reporter.run(
        "contracts / generated schema drift",
        lambda: _run_project_python(session, "tools/check_generated_schemas.py"),
    )
    reporter.run(
        "contracts / SDL catalog parity",
        lambda: _run_project_python(session, "tools/check_sdl_catalog_parity.py"),
    )
    reporter.run(
        "contracts / SDL lineage provenance",
        lambda: _run_project_python(session, "tools/check_sdl_lineage.py"),
    )
    reporter.run(
        "contracts / scientific-scenario completeness",
        lambda: _run_project_python(session, "tools/check_scientific_scenario_completeness.py"),
    )
    reporter.run(
        "contracts / reproducible related-work comparison",
        lambda: _run_project_python(session, "tools/check_related_work_comparison.py"),
    )
    reporter.run(
        "contracts / DSL language-evaluation evidence",
        lambda: _run_project_python(session, "tools/check_dsl_language_evaluation.py"),
    )
    reporter.run(
        "contracts / standardized specification coverage",
        lambda: _run_project_python(session, "tools/check_specification_coverage.py"),
    )
    reporter.run(
        "contracts / formal semantic-validation evidence",
        lambda: _run_project_python(session, "tools/check_formal_semantic_validation.py"),
    )
    reporter.run(
        "contracts / json artifact validation",
        lambda: _run_project_python(session, "tools/check_json_artifacts.py", *json_artifact_args),
    )
    reporter.run(
        "contracts / ATT&CK tactic vocabulary conformance",
        lambda: _run_project_python(session, "tools/check_attack_tactic_vocabulary.py"),
    )
    reporter.run(
        "contracts / ATLAS tactic vocabulary conformance",
        lambda: _run_project_python(session, "tools/check_atlas_tactic_vocabulary.py"),
    )
    reporter.run(
        "contracts / NIST CSF defensive vocabulary conformance",
        lambda: _run_project_python(session, "tools/check_nist_csf_defensive_vocabulary.py"),
    )
    reporter.run(
        "contracts / autonomous behavior vocabulary conformance",
        lambda: _run_project_python(session, "tools/check_autonomous_behavior_vocabularies.py"),
    )


def _run_participant_opacity_proof(session: nox.Session, reporter: SessionReporter) -> None:
    reporter.run(
        "formal proof / participant opacity",
        lambda: _run_project_python(session, "tools/check_participant_opacity_proof.py"),
        detail="Isabelle2025-2 :: offline kernel replay",
    )


def _run_lint(session: nox.Session, reporter: SessionReporter) -> None:
    reporter.run(
        "lint / ruff format (project)",
        lambda: _run_ruff(session, "format", "--check", ".", project_relative=True),
    )
    reporter.run(
        "lint / ruff check (project)",
        lambda: _run_ruff(session, "check", ".", project_relative=True),
    )
    reporter.run(
        "lint / ruff format (tooling)",
        lambda: _run_ruff(session, "format", "--check", "tools", "noxfile.py"),
    )
    reporter.run(
        "lint / ruff check (tooling)",
        lambda: _run_ruff(session, "check", "tools", "noxfile.py"),
    )


def _run_changed_lint(session: nox.Session, reporter: SessionReporter, paths: list[str]) -> None:
    prefix = "implementations/python/"
    project_paths = []
    for path in paths:
        if path.startswith(prefix) and path.endswith(".py"):
            project_paths.append(path[len(prefix) :])
    if project_paths:
        reporter.run(
            "lint / ruff format (changed project files)",
            lambda: _run_ruff(session, "format", "--check", *project_paths, project_relative=True),
            detail=f"{len(project_paths)} files",
        )
        reporter.run(
            "lint / ruff check (changed project files)",
            lambda: _run_ruff(session, "check", *project_paths, project_relative=True),
            detail=f"{len(project_paths)} files",
        )
    else:
        reporter.skip(
            "lint / ruff format (changed project files)",
            "no changed project Python files",
        )
        reporter.skip(
            "lint / ruff check (changed project files)",
            "no changed project Python files",
        )

    tooling_paths = [
        path for path in paths if (path.startswith("tools/") or path == "noxfile.py") and path.endswith(".py")
    ]
    if tooling_paths:
        reporter.run(
            "lint / ruff format (changed tooling files)",
            lambda: _run_ruff(session, "format", "--check", *tooling_paths),
            detail=f"{len(tooling_paths)} files",
        )
        reporter.run(
            "lint / ruff check (changed tooling files)",
            lambda: _run_ruff(session, "check", *tooling_paths),
            detail=f"{len(tooling_paths)} files",
        )
    else:
        reporter.skip(
            "lint / ruff format (changed tooling files)",
            "no changed tooling Python files",
        )
        reporter.skip(
            "lint / ruff check (changed tooling files)",
            "no changed tooling Python files",
        )


def _run_tests(
    session: nox.Session,
    reporter: SessionReporter,
    coverage_file: Path,
    posargs: list[str] | None = None,
    *,
    finalize_coverage: bool = True,
) -> None:
    args = list(posargs) if posargs else ["-q"]
    parallel = not posargs
    execution = "xdist auto, max 8, worksteal" if parallel else "explicit selection, serial"
    reporter.run(
        "tests / pytest",
        lambda: _run_pytest(
            session,
            *args,
            coverage_file=coverage_file,
            finalize_coverage=finalize_coverage,
            parallel=parallel,
        ),
        detail=f"{' '.join(args)} :: {execution}",
    )


def _run_fuzz(session: nox.Session, reporter: SessionReporter) -> None:
    reporter.run(
        "tests / pytest fuzz",
        lambda: _run_pytest(session, "-m", "fuzz", "-v"),
    )


def _run_integration_tests(
    session: nox.Session,
    reporter: SessionReporter,
    *,
    coverage_file: Path | None = None,
    append_coverage: bool = False,
    finalize_coverage: bool = False,
) -> None:
    reporter.run(
        "tests / pytest integration",
        lambda: _run_pytest(
            session,
            "-m",
            "integration",
            "-v",
            coverage_file=coverage_file,
            append_coverage=append_coverage,
            finalize_coverage=finalize_coverage,
        ),
    )


def _finalize_parallel_coverage(session: nox.Session, coverage_dir: Path) -> None:
    coverage_file = coverage_dir / ".coverage"
    coverage_env = {"COVERAGE_FILE": str(coverage_file)}
    with session.chdir(PROJECT_ROOT):
        _run(
            session,
            "uv",
            "run",
            "--frozen",
            "coverage",
            "combine",
            "--keep",
            str(coverage_dir),
            env=coverage_env,
        )
        _run(session, "uv", "run", "--frozen", "coverage", "xml", env=coverage_env)
        _run(
            session,
            "uv",
            "run",
            "--frozen",
            "coverage",
            "report",
            "--fail-under=50",
            "--format=total",
            env=coverage_env,
        )


def _run_docker_integration_tests(session: nox.Session, reporter: SessionReporter) -> None:
    reporter.run(
        "tests / pytest docker integration",
        lambda: _run_pytest(session, "-m", "docker", "-v", *session.posargs),
    )


def _run_osv_scan(_session: nox.Session, reporter: SessionReporter) -> None:
    def _scan() -> None:
        lockfile = OSV_LOCKFILE_PATH
        if not lockfile.exists():
            raise RuntimeError(f"osv-scan: tracked lockfile not found: {lockfile.relative_to(REPO_ROOT)}")
        binary = ensure_osv_scanner(REPO_ROOT)
        exit_code = run_osv_scanner(lockfile, OSV_REPORT_PATH, binary=binary)
        report_rel = OSV_REPORT_PATH.relative_to(REPO_ROOT)
        outcome = classify_osv_exit_code(exit_code)
        if outcome is OSVScanOutcome.FINDINGS:
            raise RuntimeError(f"osv-scanner reported vulnerabilities (exit code {exit_code}); see {report_rel}")
        if outcome is OSVScanOutcome.SCANNER_ERROR:
            raise RuntimeError(
                f"osv-scanner failed with scanner/setup error exit code {exit_code}; report at {report_rel}"
            )

    reporter.run(
        "osv-scan / uv.lock",
        _scan,
        detail=str(OSV_LOCKFILE_PATH.relative_to(REPO_ROOT)),
    )


def _run_docs(
    session: nox.Session,
    reporter: SessionReporter,
    *,
    include_external_links: bool = True,
) -> None:
    _sync_project(session)
    html_dir = DOCS_BUILD_ROOT / "html"
    linkcheck_dir = DOCS_BUILD_ROOT / "linkcheck"

    def _build(builder: str, output_dir: Path, *, clean: bool = False) -> None:
        if clean:
            shutil.rmtree(output_dir, ignore_errors=True)
        _run(
            session,
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT),
            "--frozen",
            "sphinx-build",
            "-W",
            "--keep-going",
            "-b",
            builder,
            str(PUBLIC_DOCS_ROOT),
            str(output_dir),
        )

    reporter.run(
        "docs / public source boundary",
        lambda: _run_project_python(session, "tools/check_public_docs.py"),
    )
    reporter.run(
        "docs / Vale reader style",
        lambda: _run(
            session,
            str(ensure_vale(REPO_ROOT)),
            "--config=.vale.ini",
            "--glob=*.md",
            *PUBLIC_DOCS_ENTRYPOINTS,
            str(PUBLIC_DOCS_ROOT),
        ),
        detail="Stripe-inspired RAES style",
    )
    reporter.run(
        "docs / executable quickstart",
        lambda: _run(
            session,
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT),
            "--frozen",
            "python",
            "-m",
            "pytest",
            "-q",
            *PUBLIC_DOCS_EXAMPLE_TESTS,
        ),
    )
    reporter.run(
        "docs / Sphinx HTML",
        lambda: _build("html", html_dir, clean=True),
        detail=f"{PUBLIC_DOCS_ROOT.relative_to(REPO_ROOT)} -> {html_dir.relative_to(REPO_ROOT)}",
    )
    reporter.run(
        "docs / public output inventory",
        lambda: _run_project_python(
            session,
            "tools/check_public_docs.py",
            "--output",
            str(html_dir),
        ),
    )
    if include_external_links:
        reporter.run(
            "docs / Sphinx link check",
            lambda: _build("linkcheck", linkcheck_dir),
            detail=str(PUBLIC_DOCS_ROOT.relative_to(REPO_ROOT)),
        )


def _run_docs_linkcheck(session: nox.Session, reporter: SessionReporter) -> None:
    _sync_project(session)
    linkcheck_dir = DOCS_BUILD_ROOT / "linkcheck"
    reporter.run(
        "docs / Sphinx external link check",
        lambda: _run(
            session,
            "uv",
            "run",
            "--project",
            str(PROJECT_ROOT),
            "--frozen",
            "sphinx-build",
            "-W",
            "--keep-going",
            "-b",
            "linkcheck",
            str(PUBLIC_DOCS_ROOT),
            str(linkcheck_dir),
        ),
        detail=str(PUBLIC_DOCS_ROOT.relative_to(REPO_ROOT)),
    )


@nox.session
def hygiene(session: nox.Session) -> None:
    reporter = SessionReporter(session, "hygiene")
    try:
        _run_hygiene(session, reporter, posargs=session.posargs, default_all_files=True)
    finally:
        reporter.summary()


@nox.session
def policy(session: nox.Session) -> None:
    reporter = SessionReporter(session, "policy")
    try:
        _run_policy(session, reporter, *session.posargs)
    finally:
        reporter.summary()


@nox.session
def lint(session: nox.Session) -> None:
    reporter = SessionReporter(session, "lint")
    try:
        _run_lint(session, reporter)
    finally:
        reporter.summary()


@nox.session
def contracts(session: nox.Session) -> None:
    reporter = SessionReporter(session, "contracts")
    try:
        _run_contracts(session, reporter, *session.posargs)
    finally:
        reporter.summary()


@nox.session(name="participant-opacity-proof")
def participant_opacity_proof(session: nox.Session) -> None:
    """Replay the pinned, network-isolated SEM-231 mathematical proof."""

    reporter = SessionReporter(session, "participant-opacity-proof")
    try:
        _run_participant_opacity_proof(session, reporter)
    finally:
        reporter.summary()


@nox.session
def tests(session: nox.Session) -> None:
    reporter = SessionReporter(session, "tests")
    try:
        with tempfile.TemporaryDirectory(prefix="raes-coverage-") as coverage_dir:
            _run_tests(
                session,
                reporter,
                Path(coverage_dir) / ".coverage",
                list(session.posargs),
            )
    finally:
        reporter.summary()


@nox.session
def fuzz(session: nox.Session) -> None:
    reporter = SessionReporter(session, "fuzz")
    try:
        _run_fuzz(session, reporter)
    finally:
        reporter.summary()


@nox.session
def integration(session: nox.Session) -> None:
    """Run pytest with the `integration` marker only.

    The default test session excludes subprocess, build, installed-distribution,
    and whole-system tests. This session opts them in. `verify` wires this session
    in after the parallel test sweep so CI keeps both layers covered.
    """
    reporter = SessionReporter(session, "integration")
    try:
        _sync_project(session)
        _run_integration_tests(session, reporter)
    finally:
        reporter.summary()


@nox.session(name="integration_docker")
def integration_docker(session: nox.Session) -> None:
    """Run the opt-in container-runtime integration tests (`docker` marker).

    Requires a real container runtime (docker/podman). The tests self-skip
    cleanly when no runtime is available unless
    `RAES_DOCKER_INTEGRATION_REQUIRED=1` selects the fail-closed release mode.
    This session is intentionally NOT wired into `verify`, so the canonical
    verification graph stays hermetic.
    """
    reporter = SessionReporter(session, "integration_docker")
    try:
        _sync_project(session)
        _run_docker_integration_tests(session, reporter)
    finally:
        reporter.summary()


@nox.session
def docs(session: nox.Session) -> None:
    reporter = SessionReporter(session, "docs")
    try:
        _run_docs(session, reporter)
    finally:
        reporter.summary()


@nox.session(name="docs-local")
def docs_local(session: nox.Session) -> None:
    """Run deterministic documentation checks without external HTTP requests."""

    reporter = SessionReporter(session, "docs-local")
    try:
        _run_docs(session, reporter, include_external_links=False)
    finally:
        reporter.summary()


@nox.session(name="docs-links")
def docs_links(session: nox.Session) -> None:
    """Check external documentation links; intended for the dedicated CI job."""

    reporter = SessionReporter(session, "docs-links")
    try:
        _run_docs_linkcheck(session, reporter)
    finally:
        reporter.summary()


@nox.session(name="osv_scan")
def osv_scan(session: nox.Session) -> None:
    """Required OSV-Scanner sweep over the Python dependency lockfile (#1098).

    This remains outside `verify` / `hook-pre-push` because acquiring and running
    OSV-Scanner requires network access. The standalone CI job is gating: both
    findings and scanner/setup errors fail, with distinct diagnostics, while CI
    still publishes the JSON report artifact.
    """
    reporter = SessionReporter(session, "osv_scan")
    try:
        _run_osv_scan(session, reporter)
    finally:
        reporter.summary()


@nox.session(name="hook-pre-commit")
def hook_pre_commit(session: nox.Session) -> None:
    reporter = SessionReporter(session, "hook-pre-commit")
    changed = [Path(arg).as_posix() for arg in session.posargs if not arg.startswith("-")]
    changed_tests = select_changed_python_tests(changed)
    try:
        _run_hygiene(session, reporter, posargs=changed, default_all_files=False)
        _run_policy(session, reporter, "--staged")
        _run_changed_lint(session, reporter, changed)
        if _paths_trigger(changed, CONTRACT_TRIGGER_PREFIXES):
            _run_contracts(session, reporter)
        else:
            reporter.skip("contracts / generated schema drift", "no contract-bearing changes")
            reporter.skip("contracts / json artifact validation", "no contract-bearing changes")
        if changed_tests:
            reporter.run(
                "tests / directly changed pytest modules",
                lambda: _run_pytest(session, *changed_tests, "-q"),
                detail=" ".join(changed_tests),
            )
        elif _paths_trigger(changed, FULL_TEST_TRIGGER_PREFIXES):
            reporter.skip(
                "tests / pytest",
                "no directly changed test module; full regression runs at pre-push and completion",
            )
        elif _paths_trigger(changed, TOOLING_TEST_TRIGGER_PREFIXES):
            reporter.run(
                "tests / targeted tooling tests",
                lambda: _run_pytest(session, *TARGETED_POLICY_TESTS, "-q"),
                detail=" ".join(TARGETED_POLICY_TESTS),
            )
        else:
            reporter.skip(
                "tests / pytest",
                "no implementation or tooling test trigger paths changed",
            )
    finally:
        reporter.summary()


@nox.session(name="hook-pre-push")
def hook_pre_push(session: nox.Session) -> None:
    reporter = SessionReporter(session, "hook-pre-push")
    try:
        _run_changed_verification(session, reporter, list(session.posargs))
    finally:
        reporter.summary()


def _changed_base_rev(posargs: list[str]) -> str:
    if "--base-rev" in posargs:
        index = posargs.index("--base-rev")
        if index + 1 >= len(posargs):
            raise ValueError("--base-rev requires a revision")
        return posargs[index + 1]
    return resolve_upstream(REPO_ROOT)


def _run_changed_verification(
    session: nox.Session,
    reporter: SessionReporter,
    posargs: list[str],
) -> None:
    try:
        base_rev = _changed_base_rev(posargs)
        changes = collect_git_changes(REPO_ROOT, base_rev)
        plan = plan_for_changes(changes)
        session.log(f"change-aware verification against {base_rev}: {plan.reason}; {len(changes)} change records")
    except (RuntimeError, ValueError) as exc:
        base_rev = None
        plan = plan_for_changes([])
        session.log(f"change classification failed closed to the full local gate: {exc}")

    policy_args = ["--base-rev", base_rev] if base_rev is not None else []
    _run_hygiene(session, reporter, posargs=["--all-files"], default_all_files=True)
    _run_policy(session, reporter, *policy_args)
    _run_lint(session, reporter)
    if plan.contracts:
        _run_contracts(session, reporter, *policy_args)
    else:
        reporter.skip("contracts / governed artifact graph", plan.reason)
    if plan.regression:
        with tempfile.TemporaryDirectory(prefix="raes-coverage-") as coverage_dir:
            _run_tests(session, reporter, Path(coverage_dir) / ".coverage")
    else:
        reporter.skip("tests / pytest", plan.reason)
    if plan.fuzz:
        _run_fuzz(session, reporter)
    else:
        reporter.skip("tests / pytest fuzz", plan.reason)
    if plan.docs:
        _run_docs(session, reporter)
    else:
        reporter.skip("docs / sphinx-build", plan.reason)


@nox.session(name="verify-changed")
def verify_changed(session: nox.Session) -> None:
    """Run the fail-closed local gate selected from changes since the upstream ref."""

    reporter = SessionReporter(session, "verify-changed")
    try:
        _run_changed_verification(session, reporter, list(session.posargs))
    finally:
        reporter.summary()


def _required_coverage_file() -> Path:
    value = os.environ.get(VERIFY_COVERAGE_FILE_ENV)
    if not value:
        raise RuntimeError(f"{VERIFY_COVERAGE_FILE_ENV} is required for an orchestrated coverage lane")
    return Path(value)


@nox.session(name="verify-static-lane")
def verify_static_lane(session: nox.Session) -> None:
    """Internal lane for full-tree hygiene, policy, and lint checks."""

    reporter = SessionReporter(session, "verify-static-lane")
    posargs = list(session.posargs)
    include_policy = "--include-policy" in posargs
    if include_policy:
        posargs.remove("--include-policy")
    try:
        _run_hygiene(
            session,
            reporter,
            posargs=posargs or ["--all-files"],
            default_all_files=True,
        )
        if include_policy:
            _run_policy(session, reporter, *posargs)
        _run_lint(session, reporter)
    finally:
        reporter.summary()


@nox.session(name="verify-tests-lane")
def verify_tests_lane(session: nox.Session) -> None:
    """Internal unit-test lane that emits an independently combinable data file."""

    reporter = SessionReporter(session, "verify-tests-lane")
    try:
        _run_tests(
            session,
            reporter,
            _required_coverage_file(),
            finalize_coverage=False,
        )
    finally:
        reporter.summary()


@nox.session(name="verify-integration-lane")
def verify_integration_lane(session: nox.Session) -> None:
    """Internal integration lane with coverage isolated from the unit workers."""

    reporter = SessionReporter(session, "verify-integration-lane")
    try:
        _run_integration_tests(
            session,
            reporter,
            coverage_file=_required_coverage_file(),
            append_coverage=False,
            finalize_coverage=False,
        )
    finally:
        reporter.summary()


def _verification_lanes(
    *,
    posargs: Sequence[str],
    coverage_dir: Path,
    include_policy: bool,
    cpu_count: int | None = None,
) -> tuple[VerificationLane, ...]:
    available_cpus = cpu_count if cpu_count is not None else _available_cpu_count()
    shared_posargs = tuple(posargs)
    static_posargs = (("--include-policy",) if include_policy else ()) + shared_posargs
    return (
        VerificationLane(
            name="unit-tests",
            nox_session="verify-tests-lane",
            env={
                VERIFY_COVERAGE_FILE_ENV: str(coverage_dir / ".coverage.unit"),
                "PYTEST_ADDOPTS": f"-o cache_dir={coverage_dir / 'pytest-unit'}",
                "PYTEST_XDIST_AUTO_NUM_WORKERS": str(max(1, min(8, available_cpus // 2))),
            },
        ),
        VerificationLane(
            name="integration-tests",
            nox_session="verify-integration-lane",
            env={
                VERIFY_COVERAGE_FILE_ENV: str(coverage_dir / ".coverage.integration"),
                "PYTEST_ADDOPTS": f"-o cache_dir={coverage_dir / 'pytest-integration'}",
            },
        ),
        VerificationLane(
            name="contracts",
            nox_session="contracts",
            posargs=shared_posargs,
            env={JSON_SCHEMA_WORKERS_ENV: str(max(1, min(4, available_cpus // 4)))},
        ),
        VerificationLane(
            name="static",
            nox_session="verify-static-lane",
            posargs=static_posargs,
        ),
        VerificationLane(
            name="participant-opacity-proof",
            nox_session="participant-opacity-proof",
        ),
        VerificationLane(
            name="docs-local",
            nox_session="docs-local",
            env={
                "PYTEST_ADDOPTS": f"-o cache_dir={coverage_dir / 'pytest-docs'}",
            },
        ),
    )


def _available_cpu_count() -> int:
    if hasattr(os, "sched_getaffinity"):
        try:
            return max(1, len(os.sched_getaffinity(0)))
        except OSError:
            pass
    return max(1, os.cpu_count() or 1)


def _verification_lane_workers(*, cpu_count: int, lane_count: int) -> int:
    return min(lane_count, 4, max(1, cpu_count // 2))


def _run_parallel_verification(
    session: nox.Session,
    reporter: SessionReporter,
    *,
    include_policy: bool,
) -> None:
    reporter.run(
        "verify / locked project environment",
        lambda: _sync_project(session),
        detail="one synchronization shared by all isolated lanes",
    )
    reporter.run(
        "verify / shared policy toolchain",
        lambda: _run_project_python(
            session,
            "-c",
            "from tools.policy.conftest_tool import ensure_conftest; ensure_conftest()",
        ),
        detail="prime checksum-verified Conftest before parallel policy tests",
    )
    with tempfile.TemporaryDirectory(prefix="raes-coverage-") as coverage_root:
        coverage_dir = Path(coverage_root)
        available_cpus = _available_cpu_count()
        lanes = _verification_lanes(
            posargs=session.posargs,
            coverage_dir=coverage_dir,
            include_policy=include_policy,
            cpu_count=available_cpus,
        )
        lane_workers = _verification_lane_workers(
            cpu_count=available_cpus,
            lane_count=len(lanes),
        )
        results = []

        def _execute_lanes() -> None:
            results.extend(
                run_verification_lanes(
                    lanes,
                    nox_python=Path(sys.executable),
                    noxfile=Path(__file__).resolve(),
                    repo_root=REPO_ROOT,
                    base_env={
                        VERIFY_PROJECT_SYNCED_ENV: str(os.getpid()),
                        "PYTHONUNBUFFERED": "1",
                    },
                    max_workers=lane_workers,
                )
            )
            for result in results:
                session.log(
                    f"[verify] lane {result.name}: "
                    f"{'PASS' if result.returncode == 0 else 'FAIL'} ({result.duration_s:.2f}s)"
                )
                if result.output:
                    print(result.output, end="" if result.output.endswith("\n") else "\n")
            failures = [result for result in results if result.returncode != 0]
            if failures:
                failed = ", ".join(f"{result.name} (exit {result.returncode})" for result in failures)
                raise RuntimeError(f"parallel verification lanes failed: {failed}")

        reporter.run(
            "verify / isolated deterministic lanes",
            _execute_lanes,
            detail=(
                "unit, integration, contracts, static, proof, docs-local :: "
                f"{lane_workers} lane workers on {available_cpus} CPUs"
            ),
        )
        reporter.run(
            "verify / combined coverage",
            lambda: _finalize_parallel_coverage(session, coverage_dir),
            detail="unit + integration data files",
        )


@nox.session
def verify(session: nox.Session) -> None:
    reporter = SessionReporter(session, "verify")
    try:
        _run_parallel_verification(session, reporter, include_policy=True)
    finally:
        reporter.summary()


@nox.session(name="verify-completion")
def verify_completion(session: nox.Session) -> None:
    """Run the completion graph whose Ground Control pair runs policy next."""

    reporter = SessionReporter(session, "verify-completion")
    try:
        _run_parallel_verification(session, reporter, include_policy=False)
    finally:
        reporter.summary()
