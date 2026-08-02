#!/usr/bin/env python3
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.policy.common import apply_exceptions, changed_paths, failures_to_json, load_exceptions
from tools.policy.requirement_governance import (
    GroundControlAuthRequired,
    GroundControlHttpClient,
    GroundControlUnavailable,
    evaluate_requirement_governance,
    requirement_uid_from_context,
    resolve_base_url,
    resolve_timeout_seconds,
    resolve_token,
)

GOVERNED_ROOTS = ("implementations/", "contracts/", "specs/", "docs/")
REQUIREMENT_CONTEXT_EXEMPT_PATHS = {
    ".claude/agents/completion-verifier.md",
    ".claude/hooks/check_policy_after_edit.sh",
    ".claude/hooks/protect_files.sh",
    ".claude/hooks/verify-extra.sh",
    ".claude/settings.json",
    ".claude/skills/implement/SKILL.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/ci.yml",
    ".pre-commit-config.yaml",
    ".codex",
    "AGENTS.md",
    "CHANGELOG.md",
    "implementations/python/tests/test_repo_policy_tools.py",
    "implementations/python/tests/test_requirement_governance.py",
    "implementations/python/tests/test_semantic_coverage.py",
}
REQUIREMENT_CONTEXT_EXEMPT_PREFIXES = ("tools/",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate requirement order and traceability against Ground Control.")
    parser.add_argument("--staged", action="store_true", help="Check staged changes instead of working tree changes.")
    parser.add_argument("--base-rev", help="Compare against a specific git revision.")
    parser.add_argument("--json", action="store_true", help="Emit JSON failures.")
    parser.add_argument("--requirement-uid", help="Explicit requirement UID override.")
    parser.add_argument(
        "--require-governance",
        action="store_true",
        help=(
            "Fail (non-zero) when governance cannot be evaluated (endpoint unreachable, "
            "unauthenticated, or unconfigured) instead of skipping. Also enabled by "
            "GC_REQUIRE_GOVERNANCE."
        ),
    )
    parser.add_argument("paths", nargs="*", help="Explicit repo-relative paths to check.")
    return parser.parse_args()


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def report_unevaluated(*, rule_id: str, message: str, require_governance: bool, as_json: bool) -> int:
    """Emit a machine-readable, non-misleading signal that governance was not evaluated.

    Returns 1 when governance is required (so a degraded run can never be mistaken
    for a verified pass), else 0 with a diagnostic that is clearly distinct from a
    genuine pass.
    """
    status = "required-unevaluated" if require_governance else "skipped-unavailable"
    if as_json:
        print(
            json.dumps(
                [{"rule_id": rule_id, "message": message, "path": None, "status": status}],
                indent=2,
            )
        )
    else:
        suffix = "governance is required — failing" if require_governance else "skipping governance check"
        print(f"[{rule_id}] {message} — {suffix}", file=sys.stderr)
    return 1 if require_governance else 0


def current_branch(repo_root: Path) -> str | None:
    # In CI PR checkouts the repo is in detached HEAD, so
    # git branch --show-current returns empty.  Fall back to
    # GITHUB_HEAD_REF (set by GitHub Actions for pull_request events).
    branch = os.environ.get("GITHUB_HEAD_REF", "").strip()
    if not branch:
        proc = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=True,
        )
        branch = proc.stdout.strip()
    return branch or None


def requires_requirement_context(paths: list[str]) -> bool:
    for path in paths:
        if path in REQUIREMENT_CONTEXT_EXEMPT_PATHS:
            continue
        if path.startswith(REQUIREMENT_CONTEXT_EXEMPT_PREFIXES):
            continue
        if path.startswith(GOVERNED_ROOTS):
            return True
    return False


def governed_requirement_paths(paths: list[str]) -> list[str]:
    filtered: list[str] = []
    for path in paths:
        if path in REQUIREMENT_CONTEXT_EXEMPT_PATHS:
            continue
        if path.startswith(REQUIREMENT_CONTEXT_EXEMPT_PREFIXES):
            continue
        filtered.append(path)
    return filtered


def is_dev_to_main_promotion() -> bool:
    return os.environ.get("GITHUB_HEAD_REF") == "dev" and os.environ.get("GITHUB_BASE_REF") == "main"


def main() -> int:
    args = parse_args()
    paths = (
        [Path(path).as_posix() for path in args.paths]
        if args.paths
        else changed_paths(REPO_ROOT, staged=args.staged, base_rev=args.base_rev)
    )
    effective_paths = governed_requirement_paths(paths)
    uid = requirement_uid_from_context(current_branch(REPO_ROOT), args.requirement_uid)
    if not requires_requirement_context(effective_paths):
        return 0
    if is_dev_to_main_promotion():
        return 0
    if not uid:
        failure = [
            {
                "rule_id": "requirement-context-missing",
                "message": "requirement UID is missing; set RAES_REQUIREMENT_UID or include a UID like GOV-918 in the branch name",
                "path": None,
            }
        ]
        if args.json:
            print(json.dumps(failure, indent=2))
        else:
            print(
                "[requirement-context-missing] requirement UID is missing; set RAES_REQUIREMENT_UID or include a UID like GOV-918 in the branch name",
                file=sys.stderr,
            )
        return 1

    require_governance = args.require_governance or _env_flag("GC_REQUIRE_GOVERNANCE")

    base_url = resolve_base_url(REPO_ROOT)
    if base_url is None:
        return report_unevaluated(
            rule_id="ground-control-config-missing",
            message=(
                "GC_BASE_URL is not set; configure it in the environment or the repo-local "
                ".mcp.json ground-control server env"
            ),
            require_governance=require_governance,
            as_json=args.json,
        )

    client = GroundControlHttpClient(
        base_url=base_url,
        token=resolve_token(REPO_ROOT),
        timeout_seconds=resolve_timeout_seconds(),
    )
    try:
        failures = evaluate_requirement_governance(REPO_ROOT, effective_paths, client=client, requirement_uid=uid)
    except GroundControlAuthRequired as exc:
        return report_unevaluated(
            rule_id="ground-control-auth-required",
            message=f"Ground Control requires authentication ({exc})",
            require_governance=require_governance,
            as_json=args.json,
        )
    except GroundControlUnavailable as exc:
        return report_unevaluated(
            rule_id="ground-control-unavailable",
            message=str(exc),
            require_governance=require_governance,
            as_json=args.json,
        )

    failures = apply_exceptions(failures, load_exceptions(REPO_ROOT), requirement_uid=uid)
    if failures:
        if args.json:
            print(failures_to_json(failures))
        else:
            for failure in failures:
                print(failure.render(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
