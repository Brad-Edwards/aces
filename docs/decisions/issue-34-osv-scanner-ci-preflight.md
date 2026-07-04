# Issue 34 OSV Scanner CI Preflight

Date: 2026-07-04

Issue: #34.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for wiring OSV-Scanner as
an advisory CI job. It is implementation guidance only: it does not add the
workflow job, change dependency locks, add scanner config, add Trivy, change
branch protection, or triage dependency findings.

## Tool Facts Checked

- OSV-Scanner source scanning reads project lockfiles/manifests, and its
  supported Python inputs include `uv.lock`, `poetry.lock`,
  `requirements.txt`, `Pipfile.lock`, `pdm.lock`, and `pylock.toml`.
  See <https://google.github.io/osv-scanner/supported-languages-and-lockfiles/>.
- OSV-Scanner supports JSON and SARIF output through `--format json` and
  `--format sarif`. JSON is intended for machine-readable artifact capture, and
  SARIF is SARIF v2.1.0. See
  <https://google.github.io/osv-scanner/output/>.
- OSV-Scanner returns exit code `1` when vulnerabilities are found, and uses
  separate non-result error ranges for scanner failures. See
  <https://google.github.io/osv-scanner/output/#return-codes>.
- The official GitHub reusable workflows expose `scan-args`,
  `results-file-name`, `upload-sarif`, and `fail-on-vuln`; the implementation
  must still adapt those defaults to this repository's advisory, Python-only
  scope. See <https://google.github.io/osv-scanner/github-action/>.

## Architecture Decisions

- Treat OSV-Scanner as repository automation over the Python dependency tree,
  not as ACES runtime, SDL, contract, schema, parser, backend, or policy model
  behavior.
- Use the existing deterministic Python dependency input:
  `implementations/python/uv.lock`. Do not introduce `poetry.lock`,
  `requirements.txt`, generated SBOMs, or a second dependency-manager contract
  unless the Python project itself intentionally changes package manager.
- Scope the scan to `implementations/python/uv.lock` or the narrow
  `implementations/python/` project surface. Do not recursively scan the repo
  root, and do not scan `research/` vendored reference ecosystems.
- Keep the job advisory at first: vulnerability findings should produce a SARIF
  or JSON artifact and/or code-scanning annotation, but must not make the
  canonical `verify` job fail or become an implicit merge gate.
- Preserve operational signal. Prefer a scanner mode such as `fail-on-vuln:
  false` or explicit exit-code handling that treats vulnerability exit code `1`
  as advisory while still surfacing setup, missing-lockfile, or scanner failures
  clearly. If branch protection cannot keep the job non-required, use
  job-level advisory semantics intentionally and document that tradeoff in the
  workflow comment.
- Follow the repository's existing supply-chain posture: third-party actions in
  workflows are pinned to full commit SHAs with version comments. If the
  implementation uses an OSV reusable workflow or action, pin it the same way.
  If it downloads the CLI directly, put the scanner version in
  `tools/tool_versions.py` and reuse the checksum/provenance pattern already
  used by repo-managed tooling.
- Emit one durable report artifact from the job. SARIF is preferred if the
  workflow uploads to GitHub code scanning; JSON is sufficient if the acceptance
  surface is only an uploaded artifact. Do not commit generated reports.
- Do not add Trivy in this issue. The issue explicitly excludes the vendored
  `research/` Dockerfiles because they are not first-party container build
  surfaces.

## Required Incumbents

- CI workflow conventions: `.github/workflows/ci.yml`,
  `.github/workflows/pr-title-lint.yml`, `.github/workflows/release.yml`, and
  the existing pinned `actions/checkout`, `actions/setup-python`,
  `astral-sh/setup-uv`, `actions/upload-artifact`, and
  `actions/download-artifact` usage.
- Verification graph and repo policy: `.ground-control.yaml`,
  `.gc/plan-rules.md`, `.pre-commit-config.yaml`, `noxfile.py`,
  `tools/verify_all.py`, `tools/check_repo_policy.py`, and
  `tools/check_requirement_governance.py`.
- Python dependency authority: `implementations/python/pyproject.toml`,
  `implementations/python/uv.lock`, and the repository's `uv --project
  implementations/python --frozen` convention.
- Existing security automation pattern: `noxfile.py`'s hygiene/gitleaks stage,
  `tools/gitleaks_tool.py`, and `tools/tool_versions.py` if a repo-managed
  binary wrapper is needed.
- Repository security boundary: `SECURITY.md` and `.gitignore` entries that
  keep local caches, virtualenvs, coverage, and transient scanner output out of
  version control.

## Cross-Cutting Layers

- GitHub event and auth surface: use the existing `pull_request`/`push` CI
  trust posture, never `pull_request_target`. Keep `contents: read` as the
  baseline permission. Add `security-events: write` and `actions: read` only if
  SARIF is uploaded to GitHub code scanning; do not add issue, PR-write, package,
  or repository-write scopes.
- Secret-handling surface: the job should need no repository secrets. Do not
  read secret files, echo environment variables, dump GitHub event payloads, or
  pass tokens in process argv. Artifact paths and scanner logs must not include
  `.env`, local venvs, caches, or operator secrets.
- Dependency-input validation: the implementation must assert the scanned
  lockfile exists and is the tracked `implementations/python/uv.lock`. The scan
  should operate on the lockfile or project directory without generating a
  second lock, mutating dependencies, running guided remediation, or using
  package-manager fix/install commands.
- Scanner network/privacy boundary: OSV queries external advisory services with
  dependency metadata. That is acceptable for the Python dependency tree, but
  it is not acceptable to widen the scan to vendored ecosystems or arbitrary
  source trees that could contain unrelated dependency manifests.
- Artifact exposure: SARIF and JSON reports may contain package names,
  versions, advisory IDs, fixed versions, and runner file paths. Keep artifact
  names stable, retention short and intentional, and report content limited to
  OSV output. Do not upload full workspace archives, raw logs with environment
  dumps, or generated scanner caches.
- Error-envelope layer: workflow failures and annotations stay in GitHub
  Actions. Do not introduce ACES exceptions, DTOs, schemas, controllers,
  service layers, repositories, runtime audit logs, or parser diagnostics for
  OSV findings.
- Repository policy layer: the eventual implementation should pass the existing
  nox verification graph. It should not edit `contracts/`, published schemas,
  accepted ADRs, compatibility-only `implementations/python/src/aces/`, or
  module-boundary policy for this CI-only change.

## Extension Boundary

The extension seam belongs in the CI scanner invocation, not in runtime code:
parameterize the scan target list, output format, scanner version/action pin,
artifact name, and advisory-vs-gating behavior in one workflow-local place or
one tiny repo tooling helper if a wrapper is needed.

That seam leaves room for the next likely changes without redesign:

- adding a scheduled full dependency scan while keeping PR scans advisory;
- switching JSON artifact capture to SARIF/code-scanning upload;
- promoting findings to a merge gate after an explicit branch-protection
  decision;
- adding a separate first-party container scanner job if a first-party
  container build surface appears.

## Gotchas And Anti-Patterns

Avoid:

- recursively scanning `./` and accidentally including `research/`,
  third-party reference ecosystems, caches, virtualenvs, or generated outputs;
- adding Trivy, container image scans, license scans, guided remediation, or
  dependency upgrade behavior under this issue;
- adding `poetry.lock` or `requirements.txt` beside the existing `uv.lock`;
- making vulnerability findings fail the canonical `verify` job or required PR
  checks during the advisory phase;
- hiding scanner setup failures so thoroughly that the job appears healthy
  while no report artifact is produced;
- using unpinned actions, floating `latest` scanner versions, or direct binary
  downloads without checksum/provenance validation;
- using broad workflow permissions, `pull_request_target`, repository secrets,
  issue comments, labels, or branch mutations for an advisory report job;
- copying OSV output into ACES contract schemas, SDL diagnostics, runtime
  models, policy exceptions, changelog prose, or source code comments;
- committing SARIF/JSON reports, scanner caches, offline advisory databases,
  or local tool binaries.

## Non-Goals

- Implementing the workflow, scanner wrapper, artifact upload, lockfile
  assertion, tests, or changelog in this preflight.
- Triaging or suppressing current dependency findings.
- Changing Python dependencies except through a future explicit dependency
  update.
- Adding a published schema, new ADR, duplicate validation layer, duplicate
  exception hierarchy, or new persistence/logging surface.
- Adding Trivy or any container/image scanner before a first-party container
  surface exists.
- Deciding branch-protection requirements or promoting OSV findings from
  advisory to blocking.
