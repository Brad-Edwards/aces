#!/usr/bin/env python3
"""Validate issue-scoped pull request bodies from trusted base-ref code.

The GitHub event payload and pull request body are untrusted input.  This
module deliberately uses only the standard library, never executes body text,
and performs read-only GitHub API requests.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RULE_SECTION = "required-section"
RULE_SUMMARY = "plain-language-summary"
RULE_ISSUES = "open-same-repository-issue"
RULE_VERIFICATION = "substantive-verification"

_SECTION_PATTERN = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_SUMMARY_BULLET = re.compile(
    r"^[ \t]*[-*][ \t]+(?:\*\*)?(Context|Problem|Fix)(?:\*\*)?[ \t]*:[ \t]*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_CLOSING_LINE = re.compile(r"^[ \t]*Closes[ \t]+#([1-9][0-9]*)[ \t]*$", re.MULTILINE)
_CHECKBOX_ONLY = re.compile(r"^[ \t]*[-*][ \t]+\[[ xX]\][ \t]*", re.MULTILINE)
_PLACEHOLDER = re.compile(
    r"(?:\b(?:todo|tbd|placeholder|n/?a)\b|brief description|add (?:context|details)|"
    r"describe (?:the )?(?:problem|fix|verification)|#(?:xx|n)\b)",
    re.IGNORECASE,
)
_EVIDENCE_HINT = re.compile(
    r"(?:`[^`]+`|\b(?:pass(?:ed|es)?|test(?:ed|s)?|verify|verified|verification|"
    r"nox|pytest|ruff|mypy|manual(?:ly)?|not run|not applicable|build|smoke)\b)",
    re.IGNORECASE,
)

IssueLookup = Callable[[int], tuple[bool, bool]]


@dataclass(frozen=True)
class BodyViolation:
    """One stable, machine-readable body-policy violation."""

    rule_id: str
    message: str


def _strip_ignored(text: str) -> str:
    """Remove HTML comments and fenced code before interpreting policy text."""

    without_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    kept: list[str] = []
    fence: tuple[str, int] | None = None
    for line in without_comments.splitlines():
        marker = re.match(r"^[ \t]*(`{3,}|~{3,})", line)
        if fence is None:
            if marker:
                token = marker.group(1)
                fence = (token[0], len(token))
                continue
            kept.append(line)
            continue
        if marker:
            token = marker.group(1)
            if token[0] == fence[0] and len(token) >= fence[1]:
                fence = None
    return "\n".join(kept)


def _sections(text: str) -> dict[str, list[str]]:
    matches = list(_SECTION_PATTERN.finditer(text))
    sections: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip().casefold()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.setdefault(name, []).append(text[match.end() : end].strip())
    return sections


def _meaningful(text: str, *, minimum_words: int = 3) -> bool:
    normalized = re.sub(r"[*_`#]", "", text).strip()
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", normalized)
    return len(normalized) >= 12 and len(words) >= minimum_words and not _PLACEHOLDER.search(normalized)


def closing_issue_numbers(body: str) -> tuple[int, ...]:
    """Return unique standalone ``Closes #N`` references in source order."""

    cleaned = _strip_ignored(body)
    return tuple(dict.fromkeys(int(match.group(1)) for match in _CLOSING_LINE.finditer(cleaned)))


def is_exempt_automation(event: dict[str, Any]) -> bool:
    """Limit exemptions to Dependabot and the repository release-please lane."""

    actor = str(event.get("sender", {}).get("login", ""))
    pull_request = event.get("pull_request", {})
    if not isinstance(pull_request, dict):
        return False
    author = str(pull_request.get("user", {}).get("login", ""))
    login = actor or author
    if login == "dependabot[bot]":
        return True
    if login == "release-please[bot]":
        return True
    head = pull_request.get("head", {})
    head_ref = str(head.get("ref", "")) if isinstance(head, dict) else ""
    return login == "github-actions[bot]" and head_ref.startswith("release-please--branches--")


def validate_pr_body(body: str, issue_lookup: IssueLookup) -> list[BodyViolation]:
    """Validate the human-authored body against the repository policy."""

    cleaned = _strip_ignored(body)
    sections = _sections(cleaned)
    violations: list[BodyViolation] = []
    required = ("plain-language summary", "issues closed", "verification")
    for name in required:
        count = len(sections.get(name, []))
        if count != 1:
            violations.append(
                BodyViolation(
                    RULE_SECTION,
                    f"PR body must contain exactly one '## {name.title()}' section; found {count}.",
                )
            )

    summaries = sections.get("plain-language summary", [])
    if len(summaries) == 1:
        fields: dict[str, str] = {}
        for match in _SUMMARY_BULLET.finditer(summaries[0]):
            fields[match.group(1).casefold()] = match.group(2)
        for field in ("context", "problem", "fix"):
            if field not in fields or not _meaningful(fields[field]):
                violations.append(
                    BodyViolation(
                        RULE_SUMMARY,
                        f"Plain-language summary needs a non-placeholder {field.title()} bullet.",
                    )
                )

    issues = sections.get("issues closed", [])
    if len(issues) == 1:
        numbers = closing_issue_numbers(f"## Issues closed\n{issues[0]}")
        if not numbers:
            violations.append(
                BodyViolation(
                    RULE_ISSUES,
                    "Issues closed must contain at least one standalone 'Closes #N' line.",
                )
            )
        for number in numbers:
            try:
                exists, is_open = issue_lookup(number)
            except Exception as exc:  # fail closed on API/configuration errors
                violations.append(BodyViolation(RULE_ISSUES, f"Could not verify issue #{number}: {exc}"))
                continue
            if not exists:
                violations.append(
                    BodyViolation(
                        RULE_ISSUES,
                        f"Closes #{number} does not target an issue in this repository.",
                    )
                )
            elif not is_open:
                violations.append(
                    BodyViolation(
                        RULE_ISSUES,
                        f"Closes #{number} targets an issue that is not open.",
                    )
                )

    verification = sections.get("verification", [])
    if len(verification) == 1:
        content = _CHECKBOX_ONLY.sub("", verification[0]).strip()
        if not _meaningful(content, minimum_words=2) or not _EVIDENCE_HINT.search(content):
            violations.append(
                BodyViolation(
                    RULE_VERIFICATION,
                    "Verification must record substantive commands, checks, or a reason a check was not run.",
                )
            )
    return violations


class GitHubIssueLookup:
    """Read-only lookup for issues in exactly one GitHub repository."""

    def __init__(self, repository: str, token: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GITHUB_REPOSITORY must have owner/repository form")
        if not token:
            raise ValueError("GH_TOKEN is required to verify closing issues")
        self._repository = repository
        self._token = token

    def __call__(self, number: int) -> tuple[bool, bool]:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self._repository}/issues/{number}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "OpenRAE-pr-body-guard",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False, False
            raise RuntimeError(f"GitHub returned HTTP {exc.code}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("GitHub returned a malformed issue response")
        # Pull requests also appear through the issues endpoint and cannot be
        # used to satisfy an issue-closing requirement.
        exists = "pull_request" not in payload
        return exists, exists and payload.get("state") == "open"


def _event(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("event payload must be a JSON object")
    return payload


def _fixture_lookup(path: Path) -> IssueLookup:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("issues fixture must be a JSON object")

    def lookup(number: int) -> tuple[bool, bool]:
        state = payload.get(str(number))
        return state is not None, state == "open"

    return lookup


def _open_issue_report(body: str, issue_lookup: IssueLookup, pr_number: int | str) -> str:
    numbers = closing_issue_numbers(body)
    open_numbers: list[int] = []
    errors: list[str] = []
    for number in numbers:
        try:
            exists, is_open = issue_lookup(number)
        except Exception as exc:
            errors.append(f"- Could not inspect `#{number}`: {exc}")
            continue
        if exists and is_open:
            open_numbers.append(number)
    lines = [f"## Closing-issue audit for PR #{pr_number}", ""]
    if open_numbers:
        lines.append("The following declared closing issues remain open:")
        lines.extend(f"- `#{number}`" for number in open_numbers)
    elif numbers:
        lines.append("All declared closing issues are closed.")
    else:
        lines.append("No standalone `Closes #N` lines were found.")
    if errors:
        lines.extend(("", "Inspection errors:", *errors))
    lines.extend(("", "This audit is read-only and never closes issues."))
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-path", type=Path, default=None)
    parser.add_argument("--issues-file", type=Path, default=None)
    parser.add_argument("--report-open-closing-issues", action="store_true")
    parser.add_argument("--summary-file", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    event_path = args.event_path or (Path(os.environ["GITHUB_EVENT_PATH"]) if os.getenv("GITHUB_EVENT_PATH") else None)
    if event_path is None:
        print(
            "pr-body-guard: GITHUB_EVENT_PATH or --event-path is required",
            file=sys.stderr,
        )
        return 2
    try:
        event = _event(event_path)
        pull_request = event.get("pull_request")
        if not isinstance(pull_request, dict):
            raise ValueError("event has no pull_request object")
        body = pull_request.get("body")
        if not isinstance(body, str):
            raise ValueError("event pull_request.body must be a string")
        if not args.report_open_closing_issues and is_exempt_automation(event):
            print("pr-body-guard: exempt trusted automation")
            return 0
        repository = str(event.get("repository", {}).get("full_name") or os.getenv("GITHUB_REPOSITORY", ""))
        lookup = (
            _fixture_lookup(args.issues_file)
            if args.issues_file
            else GitHubIssueLookup(repository, os.getenv("GH_TOKEN", ""))
        )
        if args.report_open_closing_issues:
            report = _open_issue_report(body, lookup, pull_request.get("number", "unknown"))
            if args.summary_file:
                args.summary_file.write_text(report, encoding="utf-8")
            else:
                print(report, end="")
            return 0
        violations = validate_pr_body(body, lookup)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"pr-body-guard: configuration error: {exc}", file=sys.stderr)
        return 2
    if violations:
        print("pr-body-guard: rejected pull request body", file=sys.stderr)
        for violation in violations:
            print(f"- [{violation.rule_id}] {violation.message}", file=sys.stderr)
        return 1
    print("pr-body-guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
