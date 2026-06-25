# Issue 567 PR Title Guard Preflight

Date: 2026-06-25

Issue: #567.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for adding a repository-side
pull-request title guard. It is implementation guidance only: it does not add
the workflow, local checker, policy config, tests, or branch-protection change.

## Architecture Decisions

- Enforce the guard in repository automation, not only in agent instructions.
  The check must run for pull request `opened`, `edited`, `synchronize`, and
  `reopened` events and must fail for agent-branded prefix titles on every
  target branch, including `dev`.
- Keep the title policy as workflow/tooling policy. Do not make it an SDL,
  contract, schema, runtime, or ADR authority change.
- Use one small repo-local title validator as the canonical policy seam. The
  GitHub Actions workflow, local tests, and any future repo-policy integration
  should call the same validator instead of carrying separate regular
  expressions in YAML, shell, and tests.
- Match Ground Control `/implement` Step 9 conventional-title semantics unless
  ACES declares an explicit `.ground-control.yaml` `workflow.pr_title` block:
  `<type>(<optional-scope>): <subject>`, a single allowed type, no compound type
  prefixes, and a subject whose first character matches `^[a-z].*$`.
- Treat the agent-branding ban as a case-insensitive prefix policy, not a
  substring ban. Titles beginning with `[codex]`, `[claude]`, `[openai]`, or
  `[chatgpt]` must fail; ordinary subjects that mention those products later in
  the title should not fail solely for that mention.

## Required Incumbents

- Workflow and verification graph: `.github/workflows/ci.yml`,
  `.ground-control.yaml`, `.gc/plan-rules.md`, `.pre-commit-config.yaml`,
  `noxfile.py`, and `tools/verify_all.py`.
- Local policy tooling: `tools/check_repo_policy.py`,
  `tools/policy/common.py` and its `PolicyFailure` render/JSON shape,
  `tools/policy/repo_policy.py`, and
  `implementations/python/tests/test_repo_policy_tools.py`.
- Ground Control title convention: `/implement` Step 9 and its
  `workflow.pr_title` config knob. ACES currently has no such block, so the
  canonical default type list should apply until the repo declares otherwise:
  `security`, `added`, `changed`, `deprecated`, `removed`, `fixed`, `feat`,
  `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `build`, `perf`, `revert`.
- GitHub Actions security posture: existing workflows use pinned third-party
  actions where actions are needed. The PR title guard should need no checkout
  and no third-party action beyond the GitHub-hosted runner unless the local
  checker is intentionally run from the repository checkout.

## Cross-Cutting Layers

- GitHub event trust boundary: the pull request title is untrusted event data.
  Read it from `$GITHUB_EVENT_PATH` via JSON parsing or pass it to the checker
  through stdin/env; do not interpolate it into shell code, `eval`, or command
  arguments that are logged.
- Workflow permissions: use the `pull_request` event and read-only
  permissions, preferably `contents: read` and `pull-requests: read` or the
  narrower effective equivalent. Do not use `pull_request_target`, write
  permissions, issue comments, labels, or branch mutations for this guard.
- Validation shape: model violations with the existing `PolicyFailure` style
  for local execution. The workflow may print concise human-readable failures,
  but it should not introduce a second exception hierarchy or custom error
  envelope.
- Config shape: if `.ground-control.yaml` gains `workflow.pr_title`, keep it as
  the repo-specific title policy data used by local title shaping. Do not make
  the workflow depend on mutable PR-controlled config without tests that prove
  malformed config fails closed.
- OS/process exposure: do not pass the full PR title in process argv, leak the
  raw event JSON, dump environment variables, or print tokens/secrets. Failure
  output may include the title or a sanitized excerpt only when it cannot expose
  credentials from surrounding event payload fields.
- Repository verification: include the local checker or its tests in the
  canonical `nox -s verify` graph through the existing tooling-test path. A
  workflow-only regular expression would drift silently from local policy.

## Extension Boundary

The extension seam belongs in the title-policy validator's data, not in a
second workflow. Parameterize:

- branded prefix tokens;
- allowed conventional types;
- subject pattern;
- whether scope is required.

That leaves room for a future ACES-specific `.ground-control.yaml`
`workflow.pr_title` block, additional banned tool prefixes, or a scope-required
policy without rewriting the workflow.

## Gotchas And Anti-Patterns

Avoid:

- copying a workflow that exempts PRs to or from `dev` for the branding ban;
- enforcing only `[codex]` and forgetting `[claude]`, `[openai]`, and
  `[chatgpt]`;
- duplicating policy regexes across YAML, shell snippets, Python tests, and
  Ground Control docs;
- using a broad substring ban that blocks legitimate titles about a product
  rather than branded prefixes;
- using `pull_request_target` or write permissions for untrusted PR metadata;
- checking only `opened` and missing `edited`, where a title can be changed
  after the initial check;
- shell-interpolating the title, passing it through process argv, or logging the
  full event payload;
- changing SDL contracts, schemas, runtime behavior, parser validation,
  published schema manifests, or compatibility wrappers for this policy-only
  issue.

## Non-Goals

- Implementing the workflow, checker, tests, changelog, or branch-protection
  configuration in this preflight.
- Changing PR creation helpers outside this repository.
- Adding a new ADR or amending accepted ADR content.
- Adding a new schema, DTO, persistence model, controller, service, logging
  channel, or exception hierarchy.
- Deciding whether repository administrators make the check required in branch
  protection after the workflow lands.
