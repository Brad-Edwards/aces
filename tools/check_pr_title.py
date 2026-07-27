#!/usr/bin/env python3
"""Repository-side PR title guard (issue #567).

This is the single source of truth for RAES pull-request title policy. The
`.github/workflows/pr-title-lint.yml` CI workflow and the
`implementations/python/tests/test_pr_title_guard.py` tests both call
``validate_pr_title`` here, so the policy cannot drift between the workflow
YAML and local enforcement.

Policy:
  * Reject agent/tool advertising bracketed prefixes such as ``[codex] ...``,
    ``[claude] ...``, ``[openai] ...``, ``[chatgpt] ...`` (case-insensitive),
    on every target branch including ``dev`` -- there is no ``dev`` exemption
    for the branding ban.
  * Enforce the Ground Control ``/implement`` Step 9 conventional title shape
    ``<type>(<optional-scope>): <subject>`` with a single allowed type.
  * Require the subject to start lowercase (``^[a-z].*$``).
  * Reject retired project naming in the text that reaches ``CHANGELOG.md``
    (issue #908). A feature PR into ``dev`` is squash-merged, so its title
    becomes the commit release-please reads, and any ``BREAKING CHANGE:``
    footer becomes a changelog entry. ``check_identity_cutover`` holds the
    generated head of ``CHANGELOG.md`` to zero retired identity occurrences,
    so without this rule a retired name in a title surfaces as a red release
    PR days later instead of on the PR that introduced it. The PR *body* is
    otherwise unchecked: discussing the retired name is legitimate, and only
    the title and breaking-change footers reach the changelog.

Security: the PR title is untrusted GitHub event data. The CLI reads it from
``$GITHUB_EVENT_PATH`` (parsed as JSON) or the ``PR_TITLE`` env var, never from
a shell-interpolated argument, and never dumps the event payload or
environment. It is intentionally stdlib-only so the CI job runs on a bare
``python`` interpreter with no third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass

# --- Policy data (the extensibility seam: parameterize, do not hard-fork) ---

#: Agent/tool advertising prefixes banned as a bracketed title prefix.
BRANDED_PREFIXES: tuple[str, ...] = ("codex", "claude", "openai", "chatgpt")

#: Canonical Ground Control ``/implement`` Step 9 allow-list, applied unless
#: RAES declares its own ``.ground-control.yaml`` ``workflow.pr_title`` block.
CONVENTIONAL_TYPES: tuple[str, ...] = (
    "security",
    "added",
    "changed",
    "deprecated",
    "removed",
    "fixed",
    "feat",
    "fix",
    "chore",
    "docs",
    "refactor",
    "test",
    "ci",
    "build",
    "perf",
    "revert",
)

#: Subject must start lowercase (matches the Step 9 rule).
SUBJECT_PATTERN: str = r"^[a-z].*$"

#: Retired project naming, word-boundary anchored so ``surfaces``,
#: ``interfaces``, ``namespaces`` and friends do not match. This is the text
#: form of ``tools/check_identity_cutover.IDENTITY_PATTERN``; the two are held
#: equivalent by ``test_pr_title_guard`` rather than imported, because this
#: module is deliberately stdlib-only and the identity checker pulls in PyYAML.
RETIRED_IDENTITY_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![A-Za-z0-9])(?:A" "CES|A" "ces|a" r"ces)(?:[-_.][A-Za-z0-9]+)*"
)

#: Only footers release-please copies into the changelog are checked.
BREAKING_CHANGE_FOOTER = re.compile(r"^\s*BREAKING[ -]CHANGE:", re.MULTILINE)

RULE_AGENT_BRAND = "pr-title-agent-brand"
RULE_CONVENTIONAL = "pr-title-conventional"
RULE_SUBJECT_LOWERCASE = "pr-title-subject-lowercase"
RULE_EMPTY = "pr-title-empty"
RULE_RETIRED_IDENTITY = "pr-title-retired-identity"


@dataclass(frozen=True)
class TitleViolation:
    """A single policy violation. Mirrors ``tools/policy/common.PolicyFailure``
    render shape without importing it (that module pulls in PyYAML, which would
    add a needless dependency to the otherwise stdlib-only CI job)."""

    rule_id: str
    message: str

    def render(self) -> str:
        return f"[{self.rule_id}] {self.message}"


def _branded_prefix_re(branded_prefixes: Sequence[str]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(p) for p in branded_prefixes)
    # Bracketed prefix only (with optional surrounding whitespace); NOT a
    # substring ban, so a subject that mentions a tool name later is fine.
    return re.compile(rf"^\s*\[\s*(?:{alternation})\s*\]", re.IGNORECASE)


def _conventional_re(types: Sequence[str]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(t) for t in types)
    # <type>(<optional-scope>)<optional breaking !>: <subject>
    return re.compile(rf"^(?:{alternation})(?:\([^()\n]+\))?(?:!)?: (?P<subject>.+)$")


def _breaking_change_footers(body: str) -> list[str]:
    """Return the ``BREAKING CHANGE:`` footer blocks release-please publishes.

    A footer runs from its marker to the next footer or the end of the body, so
    a multi-line breaking-change description is checked in full.
    """
    starts = [match.start() for match in BREAKING_CHANGE_FOOTER.finditer(body)]
    if not starts:
        return []
    bounds = starts + [len(body)]
    return [body[bounds[index] : bounds[index + 1]] for index in range(len(starts))]


def _retired_identity_violations(title: str, body: str | None) -> list[TitleViolation]:
    violations: list[TitleViolation] = []

    title_matches = RETIRED_IDENTITY_PATTERN.findall(title)
    if title_matches:
        found = ", ".join(sorted(set(title_matches)))
        violations.append(
            TitleViolation(
                RULE_RETIRED_IDENTITY,
                "PR title must not contain retired project naming "
                f"({found}). A feature PR into 'dev' is squash-merged, so this "
                "title becomes the commit release-please writes into "
                "CHANGELOG.md, where check_identity_cutover rejects it.",
            )
        )

    for footer in _breaking_change_footers(body or ""):
        footer_matches = RETIRED_IDENTITY_PATTERN.findall(footer)
        if not footer_matches:
            continue
        found = ", ".join(sorted(set(footer_matches)))
        violations.append(
            TitleViolation(
                RULE_RETIRED_IDENTITY,
                "PR body BREAKING CHANGE footer must not contain retired "
                f"project naming ({found}); release-please copies breaking-"
                "change footers into CHANGELOG.md. Prose elsewhere in the body "
                "is not checked.",
            )
        )
        break

    return violations


def validate_pr_title(
    title: str | None,
    body: str | None = None,
    *,
    branded_prefixes: Sequence[str] = BRANDED_PREFIXES,
    types: Sequence[str] = CONVENTIONAL_TYPES,
    subject_pattern: str = SUBJECT_PATTERN,
    require_scope: bool = False,
) -> list[TitleViolation]:
    """Validate ``title`` (and any changelog-bound part of ``body``) and return
    violations.

    An empty list means the title is acceptable.
    """
    violations: list[TitleViolation] = []
    stripped = (title or "").strip()

    if not stripped:
        violations.append(TitleViolation(RULE_EMPTY, "PR title is empty."))
        return violations

    # Rule 1: agent/tool advertising bracketed prefix ban. Checked first so the
    # failure message is unambiguous (a branded title also fails Rule 2).
    if _branded_prefix_re(branded_prefixes).match(stripped):
        banned = ", ".join(f"[{p}]" for p in branded_prefixes)
        violations.append(
            TitleViolation(
                RULE_AGENT_BRAND,
                "PR title must not start with an agent/tool advertising prefix "
                f"such as {banned}. Use a project-native conventional title "
                "instead.",
            )
        )
        return violations

    # Rule 4: retired project naming in changelog-bound text. Appended rather
    # than returned so a title that is both malformed and retired-named reports
    # both, and checked before the shape rules so it survives their early exit.
    violations.extend(_retired_identity_violations(stripped, body))

    # Rule 2: conventional-commit shape with a single allowed type.
    match = _conventional_re(types).match(stripped)
    if match is None:
        allowed = ", ".join(types)
        violations.append(
            TitleViolation(
                RULE_CONVENTIONAL,
                "PR title must match '<type>(<optional-scope>): <subject>' with "
                f"a single type from: {allowed}. Compound type prefixes "
                "(e.g. 'fix/refactor:') are rejected.",
            )
        )
        return violations

    if require_scope and "(" not in stripped.split(":", 1)[0]:
        violations.append(
            TitleViolation(
                RULE_CONVENTIONAL,
                "PR title must include a scope: '<type>(<scope>): <subject>'.",
            )
        )

    # Rule 3: subject starts lowercase.
    subject = match.group("subject")
    if re.match(subject_pattern, subject) is None:
        violations.append(
            TitleViolation(
                RULE_SUBJECT_LOWERCASE,
                f"PR title subject must start lowercase (match {subject_pattern!r}); got subject {subject!r}.",
            )
        )

    return violations


def _resolve_title(args: argparse.Namespace) -> tuple[str | None, str | None]:
    """Resolve the PR title and body without shell-interpolating untrusted data.

    Priority: explicit ``--title``/``--body`` (local/testing) ->
    ``$GITHUB_EVENT_PATH`` JSON (the CI path) -> ``PR_TITLE``/``PR_BODY`` env
    vars. The body is optional everywhere; only its breaking-change footers are
    inspected, and a missing body simply means there are none.
    """
    if args.title is not None:
        return args.title, args.body

    event_path = args.event_path or os.environ.get("GITHUB_EVENT_PATH")
    if event_path:
        try:
            with open(event_path, encoding="utf-8") as handle:
                event = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"pr-title-guard: could not read event JSON from {event_path}: {exc}",
                file=sys.stderr,
            )
            return None, None
        pull_request = event.get("pull_request") or {}
        title = pull_request.get("title")
        body = pull_request.get("body")
        if title is None:
            print(
                "pr-title-guard: no pull_request.title in event payload.",
                file=sys.stderr,
            )
        return title, (body if isinstance(body, str) else None)

    return os.environ.get("PR_TITLE"), os.environ.get("PR_BODY")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repository-side PR title guard (issue #567).",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="PR title to validate directly (local/testing only).",
    )
    parser.add_argument(
        "--body",
        default=None,
        help="PR body to validate alongside --title (local/testing only).",
    )
    parser.add_argument(
        "--event-path",
        default=None,
        help="Path to the GitHub event JSON (defaults to $GITHUB_EVENT_PATH).",
    )
    args = parser.parse_args(argv)

    title, body = _resolve_title(args)
    if title is None:
        # Fail closed: a pull_request event should always carry a title.
        print(
            "pr-title-guard: could not resolve a PR title to validate.",
            file=sys.stderr,
        )
        return 2

    violations = validate_pr_title(title, body)
    if violations:
        print(f"pr-title-guard: rejected PR title: {title!r}", file=sys.stderr)
        for violation in violations:
            print(f"  {violation.render()}", file=sys.stderr)
        return 1

    print(f"pr-title-guard: OK: {title!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
