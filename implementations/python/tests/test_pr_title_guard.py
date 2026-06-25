"""Tests for the repository-side PR title guard (issue #567).

These exercise the single canonical validator that both
`.github/workflows/pr-title-lint.yml` and this test suite call, so the policy
cannot drift between the workflow YAML and local enforcement. Running inside
`nox -s verify` is what keeps the guard honest.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.check_pr_title import (  # noqa: E402
    BRANDED_PREFIXES,
    CONVENTIONAL_TYPES,
    RULE_AGENT_BRAND,
    RULE_CONVENTIONAL,
    RULE_SUBJECT_LOWERCASE,
    main,
    validate_pr_title,
)

CHECKER = REPO_ROOT / "tools" / "check_pr_title.py"


def _rule_ids(title: str) -> set[str]:
    return {v.rule_id for v in validate_pr_title(title)}


# --- Agent-branding ban (the hard requirement) ---


def test_all_branded_prefixes_rejected() -> None:
    for brand in BRANDED_PREFIXES:
        title = f"[{brand}] docs: reconcile something"
        assert RULE_AGENT_BRAND in _rule_ids(title), brand


def test_branded_prefix_case_insensitive_and_spacing() -> None:
    for title in ("[CODEX] feat: x", "[ codex ] feat: x", "  [Claude] feat: x"):
        assert RULE_AGENT_BRAND in _rule_ids(title), title


def test_original_pr566_title_rejected() -> None:
    title = "[codex] docs: reconcile asset inventory methodology closeout"
    assert RULE_AGENT_BRAND in _rule_ids(title)


def test_product_name_not_at_prefix_is_allowed() -> None:
    # Only bracketed advertising *prefixes* are banned; mentioning a tool name
    # later in the subject must not fail (no broad substring ban).
    assert validate_pr_title("fix: handle codex output parsing") == []
    assert validate_pr_title("feat: add claude model id to registry") == []


# --- Conventional shape (matches /implement Step 9) ---


def test_valid_conventional_titles_pass() -> None:
    for title in (
        "feat: add repo-side pr title guard",
        "fix: correct off-by-one",
        "feat(api): add endpoint",
        "security: harden token handling",
        "ci: pin action shas",
        "feat!: breaking change to api",
        "fixed: a regression",
    ):
        assert validate_pr_title(title) == [], title


def test_all_canonical_types_accepted() -> None:
    for t in CONVENTIONAL_TYPES:
        assert validate_pr_title(f"{t}: a valid lowercase subject") == [], t


def test_compound_type_rejected() -> None:
    assert RULE_CONVENTIONAL in _rule_ids("fix/refactor: do two things")
    assert RULE_CONVENTIONAL in _rule_ids("security/docs: bundle")


def test_missing_type_rejected() -> None:
    assert RULE_CONVENTIONAL in _rule_ids("add a pr title guard")


def test_unknown_type_rejected() -> None:
    assert RULE_CONVENTIONAL in _rule_ids("wip: scratch work")


def test_no_space_after_colon_rejected() -> None:
    assert RULE_CONVENTIONAL in _rule_ids("feat:no space")


# --- Subject must start lowercase ---


def test_uppercase_subject_rejected() -> None:
    assert RULE_SUBJECT_LOWERCASE in _rule_ids("feat: Add the guard")


def test_lowercase_subject_passes() -> None:
    assert validate_pr_title("feat: add the guard") == []


def test_empty_title_rejected() -> None:
    assert validate_pr_title("") != []
    assert validate_pr_title("   ") != []


# --- Extensibility seam ---


def test_require_scope_seam() -> None:
    assert validate_pr_title("feat: no scope here", require_scope=True) != []
    assert validate_pr_title("feat(core): scoped", require_scope=True) == []


# --- CLI behavior (what the workflow invokes) ---


def test_cli_title_arg_exit_codes() -> None:
    assert main(["--title", "feat: add guard"]) == 0
    assert main(["--title", "[codex] docs: x"]) == 1


def test_cli_reads_event_json(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"title": "[codex] docs: x"}}), encoding="utf-8")
    assert main(["--event-path", str(event)]) == 1
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"pull_request": {"title": "feat: ok"}}), encoding="utf-8")
    assert main(["--event-path", str(good)]) == 0


def test_cli_missing_title_fails_closed(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({}), encoding="utf-8")
    assert main(["--event-path", str(empty)]) != 0


@pytest.mark.integration
def test_cli_subprocess_runs_standalone(tmp_path: Path) -> None:
    # The CI workflow runs the checker as a bare stdlib script; prove it needs
    # no repo dependencies and reads the title from $GITHUB_EVENT_PATH only.
    # Marked `integration` because it spawns a subprocess against the real repo
    # tree (tools/check_pr_title.py on disk), per the repo's marker contract.
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"title": "[codex] docs: x"}}), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PR_TITLE"}
    env["GITHUB_EVENT_PATH"] = str(event)
    proc = subprocess.run(
        [sys.executable, str(CHECKER)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert RULE_AGENT_BRAND in proc.stderr
