from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
import tools.check_generated_schemas as check_generated_schemas
import yaml
from tools.check_adr_immutability import (
    amendment_refs,
    canonical_content,
    content_hash,
    evaluate_adr_immutability,
)
from tools.check_generated_schemas import _extra_published_schema_paths
from tools.check_json_artifacts import collect_validation_targets, should_run_full_validation
from tools.check_schema_publication import validate_schema_publication_manifest
from tools.gitleaks_tool import _checksums_asset_name, _release_asset_name, gitleaks_binary_path
from tools.policy.common import PolicyFailure
from tools.policy.repo_policy import evaluate_repo_policy


def load_noxfile_with_fake_nox(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    class FakeOptions:
        default_venv_backend = ""
        reuse_existing_virtualenvs = False
        sessions: list[str] = []

    def session(*args: object, **_kwargs: object) -> object:
        if args and callable(args[0]):
            return args[0]

        def decorate(function: object) -> object:
            return function

        return decorate

    fake_nox = types.SimpleNamespace(options=FakeOptions(), Session=object, session=session)
    monkeypatch.setitem(sys.modules, "nox", fake_nox)

    spec = importlib.util.spec_from_file_location("_aces_test_noxfile", REPO_ROOT / "noxfile.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "_aces_test_noxfile", module)
    spec.loader.exec_module(module)
    return module


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def setup_policy_repo(tmp_path: Path) -> Path:
    policy_dir = tmp_path / "tools" / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO_ROOT / "tools" / "policy" / "adr_policy.yaml", policy_dir / "adr_policy.yaml")
    # The ADR-015 size-cap gate reads tools/policy/oversized_allowlist.yaml;
    # seed an empty allowlist by default so tests that don't exercise the
    # allowlist don't trip the missing-config failure. Tests that target
    # allowlist behavior overwrite this file.
    write_text(policy_dir / "oversized_allowlist.yaml", "files: []\n")

    adr_dir = tmp_path / "docs" / "decisions" / "adrs"
    adr_dir.mkdir(parents=True, exist_ok=True)
    write_text(
        adr_dir / "adr-001-example.md",
        "# ADR-001: Example ADR\n\n## Status\nAccepted\n\n## Date\n2026-04-05\n",
    )
    write_text(
        adr_dir / "README.md",
        "| Number | Title | Status | Date |\n"
        "| --- | --- | --- | --- |\n"
        "| [001](adr-001-example.md) | Example ADR | Accepted | 2026-04-05 |\n",
    )
    for package in (
        "aces_sdl",
        "aces_processor",
        "aces_runtime",
        "aces_backend_protocols",
        "aces_backend_stubs",
        "aces_conformance",
        "aces_cli",
        "aces_mcp",
        "aces_contracts",
    ):
        write_text(
            tmp_path / "implementations" / "python" / "packages" / package / "__init__.py",
            "",
        )
    return tmp_path


def structural_runner_stub(_: dict) -> list[PolicyFailure]:
    return []


def _load_test_policy(repo_root: Path) -> dict[str, Any]:
    with (repo_root / "tools" / "policy" / "adr_policy.yaml").open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict)
    return data


def _write_test_policy(repo_root: Path, policy: dict[str, Any]) -> None:
    (repo_root / "tools" / "policy" / "adr_policy.yaml").write_text(
        yaml.safe_dump(policy, sort_keys=False),
        encoding="utf-8",
    )


def test_hygiene_parser_ignores_policy_only_verify_args(monkeypatch: pytest.MonkeyPatch) -> None:
    noxfile = load_noxfile_with_fake_nox(monkeypatch)
    calls: list[dict[str, object]] = []

    def fake_changed_paths(*, staged: bool = False, base_rev: str | None = None) -> list[str]:
        calls.append({"staged": staged, "base_rev": base_rev})
        return ["noxfile.py"]

    monkeypatch.setattr(noxfile, "_changed_paths", fake_changed_paths)

    skip_selection = noxfile._parse_hygiene_posargs(
        ["--base-rev", "origin/dev", "--skip-requirement"],
        default_all_files=False,
    )
    uid_selection = noxfile._parse_hygiene_posargs(
        ["--base-rev", "origin/dev", "--requirement-uid", "GOV-918"],
        default_all_files=False,
    )

    assert skip_selection.paths == ["noxfile.py"]
    assert skip_selection.source == "changes since origin/dev"
    assert uid_selection.paths == ["noxfile.py"]
    assert uid_selection.source == "changes since origin/dev"
    assert calls == [
        {"staged": False, "base_rev": "origin/dev"},
        {"staged": False, "base_rev": "origin/dev"},
    ]


def test_structural_policy_runner_receives_policy_input(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    captured: dict = {}

    def runner(input_document: dict) -> list[PolicyFailure]:
        captured.update(input_document)
        return [PolicyFailure("structural-check", "blocked", "contracts/schemas/backend-manifest/schema.json")]

    failures = evaluate_repo_policy(
        repo_root,
        ["contracts/schemas/backend-manifest/schema.json"],
        structural_runner=runner,
    )

    assert captured["changed"] == ["contracts/schemas/backend-manifest/schema.json"]
    assert captured["check_set"] == "full"
    assert "generated_contracts" in captured["policy"]
    assert [failure.rule_id for failure in failures] == ["structural-check"]


def test_package_import_direction_blocks_aces_compatibility_imports(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    write_text(
        repo_root / "implementations" / "python" / "packages" / "aces_processor" / "planner.py",
        "from aces.runtime import legacy\n",
    )

    failures = evaluate_repo_policy(
        repo_root,
        ["implementations/python/packages/aces_processor/planner.py"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [failure.rule_id for failure in failures] == ["compatibility-import-direction"]


def test_compatibility_layer_rejects_non_wrapper_logic(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    write_text(
        repo_root / "implementations" / "python" / "src" / "aces" / "runtime.py",
        "def build_runtime():\n    return 1\n",
    )

    failures = evaluate_repo_policy(
        repo_root,
        ["implementations/python/src/aces/runtime.py"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [failure.rule_id for failure in failures] == ["compatibility-wrapper-only"]


def test_adr_readme_must_match_adr_documents(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    write_text(
        repo_root / "docs" / "decisions" / "adrs" / "README.md",
        "| Number | Title | Status | Date |\n"
        "| --- | --- | --- | --- |\n"
        "| [001](adr-001-example.md) | Wrong Title | Accepted | 2026-04-05 |\n",
    )

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],
        structural_runner=structural_runner_stub,
    )

    assert [failure.rule_id for failure in failures] == ["adr-index-sync"]


def test_adr_index_accepts_legacy_inline_status_and_date_fields(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    write_text(
        repo_root / "docs" / "decisions" / "adrs" / "adr-001-example.md",
        "# ADR-001: Example ADR\n\n**Status:** Accepted\n**Date:** 2026-04-05\n",
    )

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],
        structural_runner=structural_runner_stub,
    )

    assert failures == []


# ── ADR-015: SDL→processor layering rule ────────────────────────────────


def _aces_sdl_file(repo_root: Path, name: str, content: str) -> str:
    """Write a synthetic file under aces_sdl/ and return its repo-relative path."""
    rel = f"implementations/python/packages/aces_sdl/{name}"
    write_text(repo_root / rel, content)
    return rel


@pytest.mark.parametrize(
    "import_line",
    [
        "import aces_processor",
        "import aces_processor.compiler",
        "from aces_processor import compiler",
        "from aces_processor.compiler import compile_runtime_model",
    ],
)
def test_layering_rule_rejects_aces_processor_imports(tmp_path: Path, import_line: str) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = _aces_sdl_file(repo_root, "_uses_processor.py", import_line + "\n")

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert "layering-rule-violation" in [f.rule_id for f in failures], (
        f"import line {import_line!r} should fire layering-rule-violation; got {[f.rule_id for f in failures]}"
    )


def test_layering_rule_does_not_match_prefix_only_package(tmp_path: Path) -> None:
    """A package merely starting with `aces_processor` (e.g. a
    hypothetical `aces_processor_extra`) is not the forbidden package."""
    repo_root = setup_policy_repo(tmp_path)
    rel = _aces_sdl_file(repo_root, "_uses_other.py", "from aces_processor_extra import thing\n")

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert failures == []


def test_layering_rule_allows_aces_sdl_importing_other_packages(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = _aces_sdl_file(
        repo_root,
        "_normal.py",
        "from aces_contracts.contracts import Scenario\nfrom aces_sdl.semantics.objectives import analyze_objective_window\n",
    )

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert failures == []


def test_layering_rule_does_not_check_files_outside_scope(tmp_path: Path) -> None:
    """An `import aces_processor` inside aces_processor itself (or any
    package other than aces_sdl) is not a layering violation."""
    repo_root = setup_policy_repo(tmp_path)
    rel = "implementations/python/packages/aces_processor/internal.py"
    write_text(repo_root / rel, "import aces_processor.models\n")

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert failures == []


# ── ADR-036: module ownership boundaries ────────────────────────────────


def install_module_boundary_policy(repo_root: Path) -> None:
    del repo_root


def test_module_boundaries_reject_processor_importing_runtime(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    install_module_boundary_policy(repo_root)
    rel = "implementations/python/packages/aces_processor/uses_runtime.py"
    write_text(repo_root / rel, "from aces_runtime.manager import RuntimeManager\n")

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert [f.rule_id for f in failures] == ["module-boundary-import"]


def test_module_boundaries_reject_runtime_importing_processor_private_modules(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    install_module_boundary_policy(repo_root)
    rel = "implementations/python/packages/aces_runtime/uses_private_processor.py"
    write_text(repo_root / rel, "from aces_processor._private import helper\n")

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert [f.rule_id for f in failures] == ["module-boundary-private-import"]


def test_module_boundaries_allow_runtime_using_processor_public_api(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    install_module_boundary_policy(repo_root)
    rel = "implementations/python/packages/aces_runtime/uses_processor.py"
    write_text(
        repo_root / rel,
        "from aces_processor.compiler import compile_runtime_model\n"
        "from aces_processor.models import RuntimeSnapshot\n"
        "from aces_processor.planner import plan\n",
    )

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert failures == []


def test_module_boundaries_reject_runtime_using_non_public_processor_module(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    install_module_boundary_policy(repo_root)
    rel = "implementations/python/packages/aces_runtime/uses_processor_semantics.py"
    write_text(repo_root / rel, "from aces_processor.semantics.planner import reverse_delete_order\n")

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert [f.rule_id for f in failures] == ["module-boundary-public-api"]


def test_module_boundaries_reject_sdl_importing_runtime(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    install_module_boundary_policy(repo_root)
    rel = "implementations/python/packages/aces_sdl/uses_runtime.py"
    write_text(repo_root / rel, "import aces_runtime\n")

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert [f.rule_id for f in failures] == ["module-boundary-import"]


def test_module_boundaries_reject_authoring_importing_runtime_internals(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    install_module_boundary_policy(repo_root)
    rel = "implementations/python/packages/aces_mcp/tools/authoring_runtime.py"
    write_text(repo_root / rel, "from aces_runtime.control_plane import RuntimeControlPlane\n")

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert [f.rule_id for f in failures] == ["module-boundary-import"]


def test_module_boundaries_reject_backend_stub_importing_processor(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = "implementations/python/packages/aces_backend_stubs/uses_processor.py"
    write_text(repo_root / rel, "from aces_processor.models import ApplyResult\n")

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert [f.rule_id for f in failures] == ["module-boundary-import"]


def test_module_boundaries_reject_backend_protocol_any_signatures(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = "implementations/python/packages/aces_backend_protocols/protocols.py"
    write_text(
        repo_root / rel,
        "from typing import Any, Protocol\n\n"
        "class Provisioner(Protocol):\n"
        "    def apply(self, plan: Any) -> Any: ...\n",
    )

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert [f.rule_id for f in failures] == ["backend-protocol-untyped-contract"]


def test_module_boundaries_config_is_required(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    policy = _load_test_policy(repo_root)
    policy.pop("module_boundaries")
    _write_test_policy(repo_root, policy)

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/adr_policy.yaml"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["policy-config-malformed"]
    assert "module_boundaries block is required" in failures[0].message


def test_module_boundaries_config_is_required_even_without_changed_paths(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    policy = _load_test_policy(repo_root)
    policy.pop("module_boundaries")
    _write_test_policy(repo_root, policy)

    failures = evaluate_repo_policy(
        repo_root,
        [],
        check_set="full",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["policy-config-malformed"]
    assert "module_boundaries block is required" in failures[0].message


def test_module_boundaries_reject_missing_module_root(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    policy = _load_test_policy(repo_root)
    policy["module_boundaries"]["modules"][0]["root"] = "implementations/python/packages/aces_typo"
    _write_test_policy(repo_root, policy)

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/adr_policy.yaml"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["policy-config-malformed"]
    assert "must resolve to an existing directory" in failures[0].message


def test_module_boundaries_reject_uncovered_package_root(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    write_text(repo_root / "implementations/python/packages/aces_new_package/__init__.py", "")

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/adr_policy.yaml"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["policy-config-malformed"]
    assert "aces_new_package" in failures[0].message
    assert "missing from module_boundaries.modules" in failures[0].message


def test_module_boundaries_full_check_scans_all_module_sources(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = "implementations/python/packages/aces_processor/latent_runtime_import.py"
    write_text(repo_root / rel, "from aces_runtime.manager import RuntimeManager\n")

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/adr_policy.yaml"],
        check_set="full",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["module-boundary-import"]
    assert failures[0].path == rel


def test_module_boundaries_reject_runtime_importing_sdl_semantics(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = "implementations/python/packages/aces_runtime/uses_sdl_workflow_semantics.py"
    write_text(repo_root / rel, "from aces_sdl.semantics.workflow import validate_workflow_step_result\n")

    failures = evaluate_repo_policy(
        repo_root,
        [rel],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["module-boundary-import"]


# ── ADR-015: 600-line source-file cap ───────────────────────────────────

# A path that is in _ADR015_INITIAL_OVERSIZED_FILES (the code constant in
# tools/policy/repo_policy.py), so the allowlist-subset (drain) check passes
# when we put it in the allowlist.
_LOCKED_PATH = "implementations/python/packages/aces_processor/models.py"


def test_oversized_source_file_over_cap_is_rejected(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = "implementations/python/packages/aces_processor/big_new_file.py"
    write_text(repo_root / rel, "x = 1\n" * 700)

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert [f.rule_id for f in failures] == ["oversized-source-file"]


def test_oversized_source_file_in_allowlist_passes(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    write_text(repo_root / "tools" / "policy" / "oversized_allowlist.yaml", f"files:\n  - {_LOCKED_PATH}\n")
    write_text(repo_root / _LOCKED_PATH, "x = 1\n" * 700)

    failures = evaluate_repo_policy(
        repo_root, [_LOCKED_PATH], check_set="file-local", structural_runner=structural_runner_stub
    )

    assert failures == []


def test_oversized_source_file_under_cap_passes(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = "implementations/python/packages/aces_processor/small.py"
    write_text(repo_root / rel, "x = 1\n" * 100)

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert failures == []


def test_oversized_cap_excludes_test_files(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = "implementations/python/tests/test_huge.py"
    write_text(repo_root / rel, "x = 1\n" * 700)

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert failures == []


def test_oversized_cap_only_checks_python_files(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    rel = "implementations/python/packages/aces_processor/data.txt"
    write_text(repo_root / rel, "line\n" * 700)

    failures = evaluate_repo_policy(repo_root, [rel], check_set="file-local", structural_runner=structural_runner_stub)

    assert failures == []


# ── ADR-015: allowlist drain (must be a subset of the code constant) ────


def test_allowlist_entry_not_in_locked_set_is_rejected(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    bogus = "implementations/python/packages/aces_processor/not_a_locked_file.py"
    write_text(repo_root / "tools" / "policy" / "oversized_allowlist.yaml", f"files:\n  - {bogus}\n")

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/oversized_allowlist.yaml"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["oversized-allowlist-locked"]


def test_allowlist_subset_of_locked_set_passes(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    # A strict subset of the 14 initial oversized entries — the drained state.
    write_text(repo_root / "tools" / "policy" / "oversized_allowlist.yaml", f"files:\n  - {_LOCKED_PATH}\n")
    write_text(repo_root / _LOCKED_PATH, "x = 1\n" * 700)

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/oversized_allowlist.yaml"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert failures == []


def test_growing_locked_set_via_config_does_not_relax_drain_check(tmp_path: Path) -> None:
    """The drain check diffs against the *code* constant, not config. Adding
    a new oversized file to the allowlist (and even re-introducing a
    `locked_initial_files` block in adr_policy.yaml) must not make it pass —
    the locked reference set is not config the same PR can edit."""
    repo_root = setup_policy_repo(tmp_path)
    sneaky = "implementations/python/packages/aces_processor/sneaky_new_big_file.py"
    write_text(repo_root / "tools" / "policy" / "oversized_allowlist.yaml", f"files:\n  - {sneaky}\n")
    write_text(repo_root / sneaky, "x = 1\n" * 700)
    # Re-add a config-level locked_initial_files block listing the sneaky file.
    config = (repo_root / "tools" / "policy" / "adr_policy.yaml").read_text()
    config += f"  locked_initial_files:\n    - {sneaky}\n"
    write_text(repo_root / "tools" / "policy" / "adr_policy.yaml", config)

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/oversized_allowlist.yaml", sneaky],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert "oversized-allowlist-locked" in [f.rule_id for f in failures], [f.message for f in failures]


def test_unsafe_locked_allowlist_entry_is_rejected(tmp_path: Path) -> None:
    """An allowlisted (and locked) path that has been replaced by a symlink
    pointing out of the tree is reported as policy-path-unsafe rather than
    silently accepted as still-over-cap debt."""
    repo_root = setup_policy_repo(tmp_path)
    write_text(repo_root / "tools" / "policy" / "oversized_allowlist.yaml", f"files:\n  - {_LOCKED_PATH}\n")
    outside = tmp_path.parent / "outside_big.py"
    write_text(outside, "x = 1\n" * 700)
    target = repo_root / _LOCKED_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(outside)

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert "policy-path-unsafe" in [f.rule_id for f in failures], [f.message for f in failures]


# ── ADR-015: schema validation (malformed config → structured failure) ──


@pytest.mark.parametrize(
    ("mutation", "marker"),
    [
        ('oversized_source_files:\n  line_cap: "nope"\n', "line_cap"),
        ("oversized_source_files: notamapping\n", "must be a mapping"),
        ("layering_rules: notalist\n", "layering_rules must be a list"),
        ("layering_rules:\n  - {}\n", "layering_rules[0].id"),
    ],
)
def test_malformed_policy_config_produces_structured_failure(tmp_path: Path, mutation: str, marker: str) -> None:
    repo_root = setup_policy_repo(tmp_path)
    # Replace the whole adr_policy.yaml with a minimal-but-malformed config.
    # Keep the keys other parts of the policy need (compatibility_layer,
    # adr_index, source_roots, generated_contracts, concept_authority) by
    # appending the mutation onto the real config.
    base = (REPO_ROOT / "tools" / "policy" / "adr_policy.yaml").read_text()
    # Drop the real layering_rules / oversized_source_files blocks so the
    # mutation is what gets validated. Cheap approach: only the mutation
    # blocks matter; strip from the first occurrence of "layering_rules:".
    cut = base.split("\nlayering_rules:", 1)[0]
    write_text(repo_root / "tools" / "policy" / "adr_policy.yaml", cut + "\n" + mutation)

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/adr_policy.yaml"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    rule_ids = [f.rule_id for f in failures]
    assert "policy-config-malformed" in rule_ids, f"expected policy-config-malformed, got {rule_ids}"
    assert any(marker in f.message for f in failures if f.rule_id == "policy-config-malformed"), (
        f"expected a failure mentioning {marker!r}; got {[f.message for f in failures]}"
    )


def test_missing_allowlist_file_produces_structured_failure(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    (repo_root / "tools" / "policy" / "oversized_allowlist.yaml").unlink()

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    rule_ids = [f.rule_id for f in failures]
    assert "policy-config-malformed" in rule_ids, f"expected policy-config-malformed, got {rule_ids}"


# ── ADR-015: stale allowlist entry (file no longer over the cap) ─────────


def test_stale_allowlist_entry_below_cap_is_rejected(tmp_path: Path) -> None:
    """An allowlist entry that was split (so the file is now small) but
    whose entry the split PR forgot to drain is flagged on the next run,
    even though the file's deletion/shrink isn't in the changed set."""
    repo_root = setup_policy_repo(tmp_path)
    write_text(repo_root / "tools" / "policy" / "oversized_allowlist.yaml", f"files:\n  - {_LOCKED_PATH}\n")
    write_text(repo_root / _LOCKED_PATH, "x = 1\n" * 100)  # well under the 600-line cap

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],  # unrelated change
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["oversized-allowlist-stale-entry"]
    assert "100 lines" in failures[0].message


def test_stale_allowlist_entry_missing_file_is_rejected(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    write_text(repo_root / "tools" / "policy" / "oversized_allowlist.yaml", f"files:\n  - {_LOCKED_PATH}\n")
    # _LOCKED_PATH file is never created.

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["oversized-allowlist-stale-entry"]
    assert "no regular file exists" in failures[0].message


def test_allowlist_entry_still_over_cap_passes(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    write_text(repo_root / "tools" / "policy" / "oversized_allowlist.yaml", f"files:\n  - {_LOCKED_PATH}\n")
    write_text(repo_root / _LOCKED_PATH, "x = 1\n" * 700)  # still over the cap → legitimate debt

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert failures == []


# ── ADR-015: required blocks + unsafe paths ─────────────────────────────


def _write_policy_without_adr015_blocks(repo_root: Path, *, extra: str = "") -> None:
    """Rewrite adr_policy.yaml dropping the layering_rules and
    oversized_source_files blocks, optionally appending `extra`."""
    base = (REPO_ROOT / "tools" / "policy" / "adr_policy.yaml").read_text()
    cut = base.split("\nlayering_rules:", 1)[0]
    write_text(repo_root / "tools" / "policy" / "adr_policy.yaml", cut + "\n" + extra)


def test_absent_layering_rules_block_is_malformed(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    # Re-add a valid oversized_source_files block so only layering_rules is absent.
    real = (REPO_ROOT / "tools" / "policy" / "adr_policy.yaml").read_text()
    oversized_block = "oversized_source_files:" + real.split("\noversized_source_files:", 1)[1]
    _write_policy_without_adr015_blocks(repo_root, extra=oversized_block)

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/adr_policy.yaml"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert any(
        f.rule_id == "policy-config-malformed" and "layering_rules is required" in f.message for f in failures
    ), [f.message for f in failures]


def test_absent_oversized_block_is_malformed(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    # Re-add a valid layering_rules block so only oversized_source_files is absent.
    real = (REPO_ROOT / "tools" / "policy" / "adr_policy.yaml").read_text()
    layering_block = "layering_rules:" + real.split("\nlayering_rules:", 1)[1].split("\noversized_source_files:", 1)[0]
    _write_policy_without_adr015_blocks(repo_root, extra=layering_block)

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/adr_policy.yaml"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert any(
        f.rule_id == "policy-config-malformed" and "oversized_source_files block is required" in f.message
        for f in failures
    ), [f.message for f in failures]


@pytest.mark.parametrize(
    "bad_content",
    [
        "[unclosed flow sequence\n",  # parse error (never-closed flow sequence)
        "- just\n- a\n- list\n",  # parses, but root is a list not a mapping
        "42\n",  # parses to a scalar
    ],
)
def test_unparseable_or_non_mapping_adr_policy_is_malformed(tmp_path: Path, bad_content: str) -> None:
    repo_root = setup_policy_repo(tmp_path)
    write_text(repo_root / "tools" / "policy" / "adr_policy.yaml", bad_content)

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["policy-config-malformed"], [f.message for f in failures]


@pytest.mark.parametrize("bad_path", ["/etc/passwd", "../../../etc/passwd"])
def test_unsafe_allowlist_path_is_rejected(tmp_path: Path, bad_path: str) -> None:
    repo_root = setup_policy_repo(tmp_path)
    config = (repo_root / "tools" / "policy" / "adr_policy.yaml").read_text()
    config = config.replace("allowlist_path: tools/policy/oversized_allowlist.yaml", f"allowlist_path: {bad_path}")
    write_text(repo_root / "tools" / "policy" / "adr_policy.yaml", config)

    failures = evaluate_repo_policy(
        repo_root,
        ["tools/policy/adr_policy.yaml"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["policy-path-unsafe"], [f.message for f in failures]


def test_unsafe_changed_path_is_rejected(tmp_path: Path) -> None:
    """A changed path that escapes the repo root (e.g. via a planted
    symlink) is reported as policy-path-unsafe rather than being read."""
    repo_root = setup_policy_repo(tmp_path)
    outside = tmp_path.parent / "outside_secret.py"
    write_text(outside, "import aces_processor\n")
    link_rel = "implementations/python/packages/aces_sdl/_link.py"
    (repo_root / "implementations" / "python" / "packages" / "aces_sdl").mkdir(parents=True, exist_ok=True)
    (repo_root / link_rel).symlink_to(outside)

    failures = evaluate_repo_policy(
        repo_root, [link_rel], check_set="file-local", structural_runner=structural_runner_stub
    )

    assert "policy-path-unsafe" in [f.rule_id for f in failures], [f.message for f in failures]
    assert "layering-rule-violation" not in [f.rule_id for f in failures]


# ── ADR-015: drain requires the file to actually have been split ────────


def test_premature_drain_is_rejected(tmp_path: Path) -> None:
    """Removing an initial oversized file from the allowlist while the file
    itself is unchanged (still over the cap) is a premature drain — the
    debt list shrank without the work being done. Caught config-wide even
    though the (unchanged, undeleted) file is not in the changed set."""
    repo_root = setup_policy_repo(tmp_path)
    # Default allowlist is empty -> _LOCKED_PATH is "claimed drained".
    write_text(repo_root / _LOCKED_PATH, "x = 1\n" * 700)  # but the file is still over cap

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],  # unrelated change
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert [f.rule_id for f in failures] == ["oversized-source-file"], [f.message for f in failures]
    assert "removed from" in failures[0].message and "700" in failures[0].message


def test_legitimate_drain_passes(tmp_path: Path) -> None:
    """An initial oversized file that has been removed from the allowlist
    AND actually split below the cap passes."""
    repo_root = setup_policy_repo(tmp_path)
    write_text(repo_root / _LOCKED_PATH, "x = 1\n" * 120)  # genuinely split below the cap

    failures = evaluate_repo_policy(
        repo_root,
        ["docs/decisions/adrs/adr-001-example.md"],
        check_set="file-local",
        structural_runner=structural_runner_stub,
    )

    assert failures == []


# ── ADR-015: config-wide checks run even when nothing changed ────────────


def test_empty_changed_still_runs_config_wide_adr015_checks(tmp_path: Path) -> None:
    """A deletion-only PR (the repo's changed-paths helper excludes
    deletions) can hand an empty changed list to the policy. The ADR-015
    config-wide invariants must still be evaluated — here, a stale allowlist
    entry is flagged with no changed files at all."""
    repo_root = setup_policy_repo(tmp_path)
    write_text(repo_root / "tools" / "policy" / "oversized_allowlist.yaml", f"files:\n  - {_LOCKED_PATH}\n")
    write_text(repo_root / _LOCKED_PATH, "x = 1\n" * 100)

    failures = evaluate_repo_policy(repo_root, [], check_set="file-local", structural_runner=structural_runner_stub)

    assert [f.rule_id for f in failures] == ["oversized-allowlist-stale-entry"], [f.message for f in failures]


def test_empty_changed_detects_deleted_allowlist_file(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    (repo_root / "tools" / "policy" / "oversized_allowlist.yaml").unlink()

    failures = evaluate_repo_policy(repo_root, [], check_set="file-local", structural_runner=structural_runner_stub)

    assert "policy-config-malformed" in [f.rule_id for f in failures], [f.message for f in failures]


def setup_json_validation_repo(tmp_path: Path) -> Path:
    write_text(
        tmp_path / "contracts" / "schemas" / "concept-authority" / "concept-families-v1.json",
        "{}\n",
    )
    write_text(
        tmp_path / "contracts" / "schemas" / "profiles" / "semantic-profile-v1.json",
        "{}\n",
    )
    write_text(
        tmp_path / "contracts" / "schemas" / "backend-manifest" / "backend-manifest-v2.json",
        "{}\n",
    )
    write_text(
        tmp_path / "contracts" / "concept-authority" / "concept-families-v1.json",
        '{"schema_version": "concept-families-v1"}\n',
    )
    write_text(
        tmp_path / "contracts" / "profiles" / "semantic" / "reference-stack-v1.json",
        '{"schema_version": "semantic-profile-v1"}\n',
    )
    write_text(
        tmp_path / "contracts" / "fixtures" / "backend-manifest" / "backend-manifest-v2" / "valid" / "stub.json",
        "{}\n",
    )
    write_text(
        tmp_path / "contracts" / "fixtures" / "backend-manifest" / "backend-manifest-v2" / "invalid" / "broken.json",
        "{}\n",
    )
    return tmp_path


def write_schema_publication_manifest(repo_root: Path, entries: list[dict[str, str]]) -> None:
    import json

    write_text(
        repo_root / "contracts" / "schema-publication-manifest.json",
        json.dumps({"schema_version": "schema-publication-manifest/v1", "schemas": entries}, indent=2) + "\n",
    )


def test_should_run_full_validation_for_schema_driver_paths() -> None:
    assert should_run_full_validation(["tools/generate_contract_schemas.py"]) is True
    assert should_run_full_validation(["implementations/python/packages/aces_contracts/contracts.py"]) is True
    # aces_sdl supplies the Scenario Pydantic model exposed by schema_bundle();
    # a change there must trigger full schema validation just like aces_contracts.
    assert should_run_full_validation(["implementations/python/packages/aces_sdl/agents.py"]) is True
    assert should_run_full_validation(["contracts/concept-authority/concept-families-v1.json"]) is False


def test_schema_publication_manifest_accepts_complete_current_schema_inventory(tmp_path: Path) -> None:
    repo_root = tmp_path
    write_text(repo_root / "contracts" / "schemas" / "sdl" / "sdl-authoring-input-v1.json", "{}\n")
    write_text(repo_root / "contracts" / "schemas" / "control-plane" / "operation-status-v1.json", "{}\n")
    write_schema_publication_manifest(
        repo_root,
        [
            {
                "contract_id": "operation-status-v1",
                "schema_path": "contracts/schemas/control-plane/operation-status-v1.json",
            },
            {
                "contract_id": "sdl-authoring-input-v1",
                "schema_path": "contracts/schemas/sdl/sdl-authoring-input-v1.json",
            },
        ],
    )

    assert validate_schema_publication_manifest(repo_root) == []


def test_schema_publication_manifest_rejects_missing_published_schema_entry(tmp_path: Path) -> None:
    repo_root = tmp_path
    write_text(repo_root / "contracts" / "schemas" / "sdl" / "sdl-authoring-input-v1.json", "{}\n")
    write_text(repo_root / "contracts" / "schemas" / "control-plane" / "operation-status-v1.json", "{}\n")
    write_schema_publication_manifest(
        repo_root,
        [
            {
                "contract_id": "sdl-authoring-input-v1",
                "schema_path": "contracts/schemas/sdl/sdl-authoring-input-v1.json",
            },
        ],
    )

    assert validate_schema_publication_manifest(repo_root) == [
        "schema manifest is missing published schema: contracts/schemas/control-plane/operation-status-v1.json"
    ]


def test_schema_publication_manifest_rejects_paths_outside_contract_schemas(tmp_path: Path) -> None:
    repo_root = tmp_path
    write_text(repo_root / "schemas" / "legacy.json", "{}\n")
    write_schema_publication_manifest(
        repo_root,
        [
            {
                "contract_id": "legacy",
                "schema_path": "schemas/legacy.json",
            },
        ],
    )

    assert validate_schema_publication_manifest(repo_root) == [
        "schema manifest path must be under contracts/schemas/: schemas/legacy.json"
    ]


def test_collect_validation_targets_includes_only_schema_governed_artifacts(tmp_path: Path) -> None:
    repo_root = setup_json_validation_repo(tmp_path)

    targets = collect_validation_targets(repo_root)

    observed = {(target.path, target.schema_path, target.mode) for target in targets}

    assert ("contracts/schemas/backend-manifest/backend-manifest-v2.json", None, "metaschema") in observed
    assert (
        "contracts/concept-authority/concept-families-v1.json",
        "contracts/schemas/concept-authority/concept-families-v1.json",
        "schema",
    ) in observed
    assert (
        "contracts/profiles/semantic/reference-stack-v1.json",
        "contracts/schemas/profiles/semantic-profile-v1.json",
        "schema",
    ) in observed
    assert (
        "contracts/fixtures/backend-manifest/backend-manifest-v2/valid/stub.json",
        "contracts/schemas/backend-manifest/backend-manifest-v2.json",
        "schema",
    ) in observed
    assert all("/invalid/" not in target.path for target in targets)


def test_collect_validation_targets_runs_full_scan_when_schema_drivers_change(tmp_path: Path) -> None:
    repo_root = setup_json_validation_repo(tmp_path)

    targets = collect_validation_targets(
        repo_root,
        paths=["implementations/python/packages/aces_contracts/contracts.py"],
    )

    assert any(target.path == "contracts/concept-authority/concept-families-v1.json" for target in targets)


def test_gitleaks_release_asset_names_match_platform_conventions(monkeypatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.machine", lambda: "x86_64")

    assert _release_asset_name("8.30.1") == "gitleaks_8.30.1_linux_x64.tar.gz"
    assert _checksums_asset_name("8.30.1") == "gitleaks_8.30.1_checksums.txt"


def test_gitleaks_binary_path_uses_repo_local_cache(tmp_path: Path) -> None:
    assert gitleaks_binary_path(tmp_path, version="8.30.1") == (
        tmp_path / ".cache" / "aces-sdl" / "tooling" / "gitleaks" / "8.30.1" / "gitleaks"
    )


def test_extra_published_schema_paths_detects_stale_generated_files(tmp_path: Path) -> None:
    schemas_root = tmp_path / "contracts" / "schemas"
    write_text(schemas_root / "backend-manifest" / "backend-manifest-v2.json", "{}\n")
    write_text(schemas_root / "backend-manifest" / "backend-manifest-v1.json", "{}\n")

    assert _extra_published_schema_paths(
        schemas_root,
        expected_relative_paths={"backend-manifest/backend-manifest-v2.json"},
    ) == ["backend-manifest/backend-manifest-v1.json"]


def test_check_generated_schemas_main_rejects_stale_extra_schema_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
    schemas_root = repo_root / "contracts" / "schemas"
    write_text(schemas_root / "backend-manifest" / "backend-manifest-v2.json", "{}\n")
    write_text(schemas_root / "backend-manifest" / "backend-manifest-v1.json", "{}\n")

    fake_generator = types.ModuleType("tools.generate_contract_schemas")
    fake_generator.main = lambda: None
    fake_generator._schema_output_path = lambda root, name: root / "backend-manifest" / f"{name}.json"
    fake_contracts = types.ModuleType("aces_contracts.contracts")
    fake_contracts.schema_bundle = lambda: {"backend-manifest-v2": {}}
    fake_package = types.ModuleType("aces_contracts")
    fake_package.contracts = fake_contracts

    monkeypatch.setattr(check_generated_schemas, "REPO_ROOT", repo_root)
    monkeypatch.setattr(check_generated_schemas, "SCHEMAS_ROOT", schemas_root)
    monkeypatch.setattr(check_generated_schemas, "PYTHON_ROOT", repo_root / "implementations" / "python")
    monkeypatch.setattr(sys, "argv", ["check_generated_schemas.py"])
    monkeypatch.setitem(sys.modules, "tools.generate_contract_schemas", fake_generator)
    monkeypatch.setitem(sys.modules, "aces_contracts", fake_package)
    monkeypatch.setitem(sys.modules, "aces_contracts.contracts", fake_contracts)

    assert check_generated_schemas.main() == 1


# --- ADR acceptance-content pin gate (ADR-059 / GOV-941) ----------------------

AMENDMENTS_TABLE_HEADER = "## Amendments\n\n| Date | Commit/PR | Summary |\n|------|-----------|---------|\n"


def _adr_dir(tmp_path: Path) -> Path:
    adr_dir = tmp_path / "docs" / "decisions" / "adrs"
    adr_dir.mkdir(parents=True, exist_ok=True)
    return adr_dir


def _make_adr(
    adr_dir: Path,
    number: str,
    *,
    status: str = "accepted",
    body: str = "\n## Context\n\nThe decision body.\n",
    amendment_rows: list[tuple[str, str, str]] | None = None,
) -> str:
    text = _adr_text(number, status=status, body=body)
    if amendment_rows:
        rows = "".join(f"| {date} | {ref} | {summary} |\n" for date, ref, summary in amendment_rows)
        text += "\n" + AMENDMENTS_TABLE_HEADER + rows
    write_text(adr_dir / f"adr-{number}-example.md", text)
    return text


def _write_manifest(adr_dir: Path, entries: list[dict], *, algorithm: str = "sha256") -> None:
    write_text(
        adr_dir / "adr-index.yaml",
        yaml.safe_dump({"hash_algorithm": algorithm, "adrs": entries}, sort_keys=False),
    )


def _entry(number: str, text: str, *, pin_text: str | None = None, amendments: list[dict] | None = None) -> dict:
    # ``pin_text`` lets a caller pin over content that is NOT byte-identical to the
    # on-disk ADR (``text``). Recorded-amendment tests rely on this to pin over the
    # *unamended* body so the gate only stays green if ``canonical_content`` truly
    # strips the ``## Amendments`` section — pinning over the amended text would be
    # tautological (both sides hashed from the same amended bytes).
    entry = {
        "id": f"ADR-{number}",
        "path": f"docs/decisions/adrs/adr-{number}-example.md",
        "pin": content_hash(pin_text if pin_text is not None else text),
    }
    if amendments is not None:
        entry["amendments"] = amendments
    return entry


def _adr_text(number: str, *, status: str = "accepted", body: str = "\n## Context\n\nThe decision body.\n") -> str:
    """The unamended ADR text ``_make_adr`` writes for ``(number, status, body)``,
    without touching disk. Used to compute a pin over body-only content so the
    amendment-stripping invariant is falsifiable."""
    return f"# ADR-{number}: Example {number}\n\n## Status\n\n{status}\n\n## Date\n\n2026-04-05\n{body}"


def _rule_ids(failures: list[PolicyFailure]) -> list[str]:
    return [failure.rule_id for failure in failures]


def _init_git_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True, capture_output=True)


def _git_commit_all(repo_root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo_root, check=True, capture_output=True, text=True)


def _git_add_all(repo_root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True, capture_output=True, text=True)


def test_adr_pin_gate_passes_on_pinned_accepted_corpus(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    accepted_one = _make_adr(adr_dir, "001")
    accepted_two = _make_adr(adr_dir, "002")
    _make_adr(adr_dir, "003", status="proposed")  # proposed ADRs are not pinned
    _write_manifest(adr_dir, [_entry("001", accepted_one), _entry("002", accepted_two)])

    assert evaluate_adr_immutability(tmp_path) == []


def test_adr_pin_gate_flags_unrecorded_edit(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    original = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", original)])
    # Edit the ADR body without updating the pin.
    _make_adr(adr_dir, "001", body="\n## Context\n\nA substantively different body.\n")

    failures = evaluate_adr_immutability(tmp_path)
    assert "adr-pin-stale" in _rule_ids(failures)


def test_adr_pin_gate_accepts_recorded_amendment(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    text = _make_adr(adr_dir, "001", amendment_rows=[("2026-06-07", "abc1234", "added a field")])
    # Pin over the *unamended* body. If canonical_content stops stripping the
    # ## Amendments section, the on-disk (amended) hash diverges from this pin and
    # the gate fires adr-pin-stale — so this assertion genuinely verifies the
    # "amendment records never change the pin" invariant rather than tautologically
    # hashing the same amended bytes on both sides.
    _write_manifest(
        adr_dir,
        [
            _entry(
                "001",
                text,
                pin_text=_adr_text("001"),
                amendments=[{"date": "2026-06-07", "ref": "abc1234", "summary": "added a field"}],
            )
        ],
    )

    # The pin is over canonical content (amendments excluded), so the recorded
    # amendment does not perturb it, and the manifest refs match the table 1:1.
    assert evaluate_adr_immutability(tmp_path) == []


def test_adr_pin_gate_flags_missing_pin(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    pinned = _make_adr(adr_dir, "001")
    _make_adr(adr_dir, "002")  # accepted but absent from the manifest
    _write_manifest(adr_dir, [_entry("001", pinned)])

    failures = evaluate_adr_immutability(tmp_path)
    assert "adr-pin-missing" in _rule_ids(failures)


def test_adr_pin_gate_flags_orphan_entry(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    proposed = _make_adr(adr_dir, "001", status="proposed")
    _write_manifest(adr_dir, [_entry("001", proposed)])  # pins a non-accepted ADR

    failures = evaluate_adr_immutability(tmp_path)
    assert "adr-pin-orphan" in _rule_ids(failures)


def test_adr_pin_gate_flags_amendment_record_mismatch(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    text = _make_adr(adr_dir, "001", amendment_rows=[("2026-06-07", "abc1234", "added a field")])
    _write_manifest(adr_dir, [_entry("001", text, amendments=[])])  # table row not mirrored in manifest

    failures = evaluate_adr_immutability(tmp_path)
    assert "adr-amendment-record-mismatch" in _rule_ids(failures)


def test_adr_pin_gate_rejects_unsupported_algorithm(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    text = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", text)], algorithm="md5")

    failures = evaluate_adr_immutability(tmp_path)
    assert _rule_ids(failures) == ["adr-manifest-malformed"]


def test_adr_pin_gate_rejects_duplicate_id(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    text = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", text), _entry("001", text)])

    failures = evaluate_adr_immutability(tmp_path)
    assert "adr-manifest-malformed" in _rule_ids(failures)


def test_adr_pin_gate_rejects_unsafe_path(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    _write_manifest(
        adr_dir,
        [{"id": "ADR-001", "path": "../outside-the-repo.md", "pin": "0" * 64}],
    )

    failures = evaluate_adr_immutability(tmp_path)
    assert "adr-manifest-path-unsafe" in _rule_ids(failures)


def test_adr_pin_gate_missing_manifest_fails_cleanly(tmp_path: Path) -> None:
    _adr_dir(tmp_path)
    failures = evaluate_adr_immutability(tmp_path)
    assert _rule_ids(failures) == ["adr-manifest-malformed"]


def test_adr_pin_gate_base_rev_flags_pin_bump_without_amendment(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    original = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", original)])
    _init_git_repo(tmp_path)
    _git_commit_all(tmp_path, "base")

    # Edit the body AND bump the pin, but record no amendment.
    edited = _make_adr(adr_dir, "001", body="\n## Context\n\nA materially changed body.\n")
    _write_manifest(adr_dir, [_entry("001", edited)])

    failures = evaluate_adr_immutability(tmp_path, base_rev="HEAD")
    assert _rule_ids(failures) == ["adr-amendment-unrecorded"]


def test_adr_pin_gate_base_rev_accepts_recorded_amendment(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    original = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", original)])
    _init_git_repo(tmp_path)
    _git_commit_all(tmp_path, "base")

    changed_body = "\n## Context\n\nA materially changed body.\n"
    edited = _make_adr(
        adr_dir,
        "001",
        body=changed_body,
        amendment_rows=[("2026-06-08", "def5678", "changed the body")],
    )
    # Pin over the unamended edited body so the recorded amendment is what makes
    # the change legitimate; a canonical_content regression that stops stripping
    # amendments would diverge this pin from the on-disk hash and fail the test.
    _write_manifest(
        adr_dir,
        [
            _entry(
                "001",
                edited,
                pin_text=_adr_text("001", body=changed_body),
                amendments=[{"date": "2026-06-08", "ref": "def5678", "summary": "changed the body"}],
            )
        ],
    )

    assert evaluate_adr_immutability(tmp_path, base_rev="HEAD") == []


def test_adr_pin_gate_base_rev_allows_supersession(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    original = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", original)])
    _init_git_repo(tmp_path)
    _git_commit_all(tmp_path, "base")

    # Supersede ADR-001: status changes (so it leaves the accepted/pinned set)
    # and a new superseding ADR-002 is added; drop ADR-001 from the manifest.
    _make_adr(adr_dir, "001", status="superseded by ADR-002")
    superseding = _make_adr(adr_dir, "002")
    _write_manifest(adr_dir, [_entry("002", superseding)])

    assert evaluate_adr_immutability(tmp_path, base_rev="HEAD") == []


def test_adr_pin_gate_staged_flags_pin_bump_without_amendment(tmp_path: Path) -> None:
    # The pre-commit invocation: ``staged=True`` compares the git *index*
    # (``git show :<path>``) against HEAD, a distinct code path from ``base_rev``
    # (which reads the working tree from disk). A staged pin bump without an
    # amendment must be flagged just like the base_rev case.
    adr_dir = _adr_dir(tmp_path)
    original = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", original)])
    _init_git_repo(tmp_path)
    _git_commit_all(tmp_path, "base")

    edited = _make_adr(adr_dir, "001", body="\n## Context\n\nA materially changed body.\n")
    _write_manifest(adr_dir, [_entry("001", edited)])
    _git_add_all(tmp_path)

    failures = evaluate_adr_immutability(tmp_path, staged=True)
    assert _rule_ids(failures) == ["adr-amendment-unrecorded"]


def test_adr_pin_gate_staged_accepts_recorded_amendment(tmp_path: Path) -> None:
    # A staged edit that records its amendment (and bumps the pin) passes — proving
    # the staged branch does not over-fire on legitimately recorded changes.
    adr_dir = _adr_dir(tmp_path)
    original = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", original)])
    _init_git_repo(tmp_path)
    _git_commit_all(tmp_path, "base")

    changed_body = "\n## Context\n\nA materially changed body.\n"
    edited = _make_adr(
        adr_dir,
        "001",
        body=changed_body,
        amendment_rows=[("2026-06-08", "def5678", "changed the body")],
    )
    # Pin over the unamended edited body (see recorded-amendment tests above): the
    # green result must depend on canonical_content actually stripping amendments.
    _write_manifest(
        adr_dir,
        [
            _entry(
                "001",
                edited,
                pin_text=_adr_text("001", body=changed_body),
                amendments=[{"date": "2026-06-08", "ref": "def5678", "summary": "changed the body"}],
            )
        ],
    )
    _git_add_all(tmp_path)

    assert evaluate_adr_immutability(tmp_path, staged=True) == []


def test_adr_pin_gate_staged_sources_head_text_from_index_not_disk(tmp_path: Path) -> None:
    # Pins down that ``head_text`` in the staged branch comes from the git *index*
    # (``git show :<path>``), not the working tree. We stage an unrecorded ADR edit
    # (with a bumped pin) and then restore the working-tree file to the committed
    # original. Now the index holds the edit while disk == HEAD, so:
    #   * the pin-hash check (which reads disk) sees the original and stays green;
    #   * the corpus checks all pass against the staged pin too, so evaluation
    #     reaches the staged unrecorded-edit detector;
    #   * only an index-sourced ``head_text`` can observe the edit and flag it.
    # If the detector read disk instead, head_text would equal base_text and the
    # edit would silently pass — exactly the false exit-0 this test forbids.
    adr_dir = _adr_dir(tmp_path)
    original = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", original)])
    _init_git_repo(tmp_path)
    _git_commit_all(tmp_path, "base")

    # Stage the edited ADR. The bumped pin must match the *index* (edited) content
    # so the disk-based pin-hash check will be green once we restore disk below.
    edited = _make_adr(adr_dir, "001", body="\n## Context\n\nA materially changed body.\n")
    _git_add_all(tmp_path)  # index now holds the edited ADR

    # Restore the working tree to the committed original while keeping the index
    # edit. Pin stays over the original content so the disk-read pin-hash is green.
    write_text(adr_dir / "adr-001-example.md", original)
    _write_manifest(adr_dir, [_entry("001", original)])

    failures = evaluate_adr_immutability(tmp_path, staged=True)
    assert _rule_ids(failures) == ["adr-amendment-unrecorded"]


def test_amendment_refs_parses_table_rows() -> None:
    text = (
        "# ADR-001: Example\n\n## Status\n\naccepted\n\n## Date\n\n2026-04-05\n\n"
        + AMENDMENTS_TABLE_HEADER
        + "| 2026-06-07 | abc1234 | first |\n| 2026-06-08 | def5678 | second |\n"
    )
    assert amendment_refs(text) == ["abc1234", "def5678"]


def test_amendment_parsing_ignores_fenced_examples(tmp_path: Path) -> None:
    # An ADR that documents the amendment format (like ADR-059) embeds a
    # ``## Amendments`` example inside a fenced code block. That example must
    # not be read as a real section, or the ADR's pin would truncate and a
    # bogus amendment would be parsed from the example row.
    adr_dir = _adr_dir(tmp_path)
    text = (
        "# ADR-001: Policy\n\n## Status\n\naccepted\n\n## Date\n\n2026-04-05\n\n"
        "## Decision\n\nRecord amendments like:\n\n"
        "```markdown\n## Amendments\n\n| Date | Commit/PR | Summary |\n"
        "|------|-----------|---------|\n| 2026-06-07 | deadbee | example |\n```\n\n"
        "## Consequences\n\nDone.\n"
    )
    write_text(adr_dir / "adr-001-example.md", text)
    assert amendment_refs(text) == []
    _write_manifest(adr_dir, [_entry("001", text)])  # _entry hashes full text; no amendments

    assert evaluate_adr_immutability(tmp_path) == []


def test_canonical_content_detects_boundary_blank_line_edits() -> None:
    # ADR-059 declares only per-line trailing whitespace and the file-final
    # newline as normalized. A leading or interior blank line is significant, so
    # adding one must change the canonical hash; toggling the final newline must
    # not. This keeps the pin from silently absorbing boundary blank-line edits.
    base = "# ADR-001: Example\n\n## Context\n\nThe body.\n"
    leading_blank = "\n" + base
    interior_blank = "# ADR-001: Example\n\n\n## Context\n\nThe body.\n"
    no_final_newline = base.rstrip("\n")
    trailing_blank = base + "\n"

    assert canonical_content(base) != canonical_content(leading_blank)
    assert canonical_content(base) != canonical_content(interior_blank)
    assert canonical_content(base) == canonical_content(no_final_newline)
    assert canonical_content(base) == canonical_content(trailing_blank)


def test_adr_pin_gate_base_rev_flags_boundary_blank_line_edit(tmp_path: Path) -> None:
    adr_dir = _adr_dir(tmp_path)
    original = _make_adr(adr_dir, "001")
    _write_manifest(adr_dir, [_entry("001", original)])
    _init_git_repo(tmp_path)
    _git_commit_all(tmp_path, "base")

    # Prepend a blank line (a boundary-only edit) and bump the pin, no amendment.
    edited = "\n" + original
    write_text(adr_dir / "adr-001-example.md", edited)
    _write_manifest(adr_dir, [_entry("001", edited)])

    failures = evaluate_adr_immutability(tmp_path, base_rev="HEAD")
    assert _rule_ids(failures) == ["adr-amendment-unrecorded"]


def test_real_repo_adr_index_is_green() -> None:
    """The committed adr-index.yaml must pin every accepted ADR honestly so the
    gate starts (and stays) green on the real corpus."""
    failures = evaluate_adr_immutability(REPO_ROOT)
    assert failures == [], "\n".join(failure.render() for failure in failures)
