"""Tests for trusted-base pull request body governance."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.check_pr_body as pr_body  # noqa: E402
from tools.check_pr_body import (  # noqa: E402
    RULE_ISSUES,
    RULE_SECTION,
    RULE_SUMMARY,
    RULE_VERIFICATION,
    closing_issue_numbers,
    is_exempt_automation,
    main,
    validate_pr_body,
)

CHECKER = REPO_ROOT / "tools/check_pr_body.py"


def _body(issue: int = 123) -> str:
    return f"""## Plain-language summary

- **Context:** Contributors need one reviewable delivery contract.
- **Problem:** Empty pull request bodies hide delivery scope and evidence.
- **Fix:** The trusted guard validates structured human-authored content.

## Issues closed

Closes #{issue}

## Verification

- `pytest tests/test_pr_body_guard.py`: passed
"""


def _lookup(states: dict[int, str]):
    def lookup(number: int) -> tuple[bool, bool]:
        state = states.get(number)
        return state is not None, state == "open"

    return lookup


def _rules(body: str, states: dict[int, str] | None = None) -> set[str]:
    lookup = _lookup({123: "open"} if states is None else states)
    return {violation.rule_id for violation in validate_pr_body(body, lookup)}


def test_complete_body_passes() -> None:
    assert validate_pr_body(_body(), _lookup({123: "open"})) == []


@pytest.mark.parametrize("heading", ["Plain-language summary", "Issues closed", "Verification"])
def test_each_required_section_is_mandatory_and_unique(heading: str) -> None:
    missing = _body().replace(f"## {heading}\n", "### Removed\n", 1)
    duplicate = _body() + f"\n## {heading}\nExtra content that must not create ambiguity.\n"
    assert RULE_SECTION in _rules(missing)
    assert RULE_SECTION in _rules(duplicate)


@pytest.mark.parametrize("field", ["Context", "Problem", "Fix"])
def test_summary_bullets_reject_placeholders(field: str) -> None:
    body = _body().replace(
        next(line for line in _body().splitlines() if field in line),
        f"- **{field}:** TODO",
    )
    assert RULE_SUMMARY in _rules(body)


def test_only_standalone_closing_lines_count() -> None:
    body = _body().replace("Closes #123", "Related: Closes #123")
    assert closing_issue_numbers(body) == ()
    assert RULE_ISSUES in _rules(body)


@pytest.mark.parametrize("state", ["closed", "missing"])
def test_closing_reference_must_be_an_open_same_repository_issue(state: str) -> None:
    states = {} if state == "missing" else {123: state}
    assert RULE_ISSUES in _rules(_body(), states)


def test_comments_and_fenced_code_cannot_satisfy_policy() -> None:
    hidden = """<!--
## Plain-language summary
- Context: Hidden context is not reviewer-visible evidence.
- Problem: Hidden problem is not reviewer-visible evidence.
- Fix: Hidden fix is not reviewer-visible evidence.
-->
```markdown
## Issues closed
Closes #123
## Verification
- `pytest`: passed
```
"""
    rules = _rules(hidden)
    assert RULE_SECTION in rules


def test_comments_and_fenced_examples_do_not_add_fake_issue_references() -> None:
    body = _body() + "\n<!-- Closes #999 -->\n```text\nCloses #888\n```\n"
    seen: list[int] = []

    def lookup(number: int) -> tuple[bool, bool]:
        seen.append(number)
        return number == 123, number == 123

    assert validate_pr_body(body, lookup) == []
    assert seen == [123]


def test_verification_checklist_without_evidence_is_rejected() -> None:
    body = _body().replace("- `pytest tests/test_pr_body_guard.py`: passed", "- [ ] Tests pass")
    assert RULE_VERIFICATION in _rules(body)


@pytest.mark.parametrize(
    ("login", "head", "expected"),
    [
        ("dependabot[bot]", "dependabot/pip/x", True),
        ("release-please[bot]", "release-please--branches--dev", True),
        ("github-actions[bot]", "release-please--branches--dev", True),
        ("github-actions[bot]", "feature", False),
        ("renovate[bot]", "renovate/x", False),
        ("human", "feature", False),
    ],
)
def test_automation_exemptions_are_narrow(login: str, head: str, expected: bool) -> None:
    event = {
        "sender": {"login": login},
        "pull_request": {"user": {"login": login}, "head": {"ref": head}},
    }
    assert is_exempt_automation(event) is expected


def test_cli_uses_event_and_issue_fixture(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    issues = tmp_path / "issues.json"
    event.write_text(
        json.dumps(
            {
                "repository": {"full_name": "OpenRAE/rae"},
                "sender": {"login": "human"},
                "pull_request": {"number": 7, "body": _body(), "user": {"login": "human"}},
            }
        ),
        encoding="utf-8",
    )
    issues.write_text(json.dumps({"123": "open"}), encoding="utf-8")
    assert main(["--event-path", str(event), "--issues-file", str(issues)]) == 0


def test_lookup_failures_and_http_shapes_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="owner/repository"):
        pr_body.GitHubIssueLookup("invalid", "token")
    with pytest.raises(ValueError, match="GH_TOKEN"):
        pr_body.GitHubIssueLookup("OpenRAE/rae", "")

    lookup = pr_body.GitHubIssueLookup("OpenRAE/rae", "token")
    monkeypatch.setattr(
        pr_body.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: io.StringIO('{"state":"open"}'),
    )
    assert lookup(12) == (True, True)
    monkeypatch.setattr(
        pr_body.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: io.StringIO('{"state":"open","pull_request":{}}'),
    )
    assert lookup(12) == (False, False)
    monkeypatch.setattr(
        pr_body.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: io.StringIO("[]"),
    )
    with pytest.raises(RuntimeError, match="malformed"):
        lookup(12)


def test_validation_and_report_record_lookup_errors() -> None:
    def failing(_number: int) -> tuple[bool, bool]:
        raise RuntimeError("offline")

    violations = validate_pr_body(_body(), failing)
    assert any("Could not verify issue #123" in item.message for item in violations)
    report = pr_body._open_issue_report(_body(), failing, 7)
    assert "Inspection errors" in report and "never closes issues" in report
    assert "All declared closing issues are closed" in pr_body._open_issue_report(_body(), _lookup({123: "closed"}), 7)
    assert "No standalone" in pr_body._open_issue_report("No references", _lookup({}), 7)


def test_cli_rejects_missing_or_malformed_events(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    malformed = tmp_path / "event.json"
    malformed.write_text("[]", encoding="utf-8")
    assert main(["--event-path", str(malformed)]) == 2
    assert "configuration error" in capsys.readouterr().err


def test_cli_exempts_trusted_automation_before_api_configuration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "sender": {"login": "dependabot[bot]"},
                "pull_request": {"body": "", "user": {"login": "dependabot[bot]"}},
            }
        ),
        encoding="utf-8",
    )
    assert main(["--event-path", str(event)]) == 0
    assert "exempt trusted automation" in capsys.readouterr().out


def test_cli_renders_rejections_and_stdout_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    event = tmp_path / "event.json"
    issues = tmp_path / "issues.json"
    event.write_text(json.dumps({"pull_request": {"number": 9, "body": "incomplete"}}), encoding="utf-8")
    issues.write_text("{}", encoding="utf-8")
    args = ["--event-path", str(event), "--issues-file", str(issues)]
    assert main(args) == 1
    assert "rejected pull request body" in capsys.readouterr().err
    assert main([*args, "--report-open-closing-issues"]) == 0
    assert "Closing-issue audit for PR #9" in capsys.readouterr().out


def test_report_mode_is_read_only_and_lists_open_issues(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    issues = tmp_path / "issues.json"
    summary = tmp_path / "summary.md"
    event.write_text(
        json.dumps(
            {
                "repository": {"full_name": "OpenRAE/rae"},
                "pull_request": {"number": 7, "body": _body()},
            }
        ),
        encoding="utf-8",
    )
    issues.write_text(json.dumps({"123": "open"}), encoding="utf-8")
    assert (
        main(
            [
                "--event-path",
                str(event),
                "--issues-file",
                str(issues),
                "--report-open-closing-issues",
                "--summary-file",
                str(summary),
            ]
        )
        == 0
    )
    assert "`#123`" in summary.read_text(encoding="utf-8")
    assert "read-only" in summary.read_text(encoding="utf-8")


def test_workflows_use_trusted_code_and_read_only_permissions() -> None:
    guard_source = (REPO_ROOT / ".github/workflows/pr-body-policy.yml").read_text(encoding="utf-8")
    audit_source = (REPO_ROOT / ".github/workflows/post-merge-closing-issue-audit.yml").read_text(encoding="utf-8")
    guard = yaml.safe_load(guard_source)
    audit = yaml.safe_load(audit_source)

    assert "pull_request_target" not in guard_source
    checkout = guard["jobs"]["body-guard"]["steps"][0]
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.base.sha }}"
    assert guard["permissions"] == {"contents": "read", "issues": "read", "pull-requests": "read"}
    assert audit["permissions"] == {"contents": "read", "issues": "read", "pull-requests": "read"}
    assert "gh issue close" not in audit_source
    assert "--method" not in audit_source


@pytest.mark.integration
def test_checker_runs_as_a_standalone_stdlib_script(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    issues = tmp_path / "issues.json"
    event.write_text(
        json.dumps(
            {
                "repository": {"full_name": "OpenRAE/rae"},
                "sender": {"login": "human"},
                "pull_request": {"body": _body(), "user": {"login": "human"}},
            }
        ),
        encoding="utf-8",
    )
    issues.write_text(json.dumps({"123": "open"}), encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if key != "GH_TOKEN"}
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--event-path", str(event), "--issues-file", str(issues)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
