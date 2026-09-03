---
id: GOV-901
title: "Versioning And Compatibility Rules"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T07:16:00.634358Z
updated_at: 2026-08-12T00:00:00.000000Z
---

# GOV-901 — Versioning And Compatibility Rules

## Statement

The ecosystem shall define versioning and compatibility rules for language, semantic, processing, contract, module, and experiment surfaces.

## Rationale

Requirement inventory expansion. Compatibility claims need explicit versioning and compatibility rules across language, semantics, processing, contracts, modules, and experiments.

## Traceability

- IMPLEMENTS → ADR `docs/decisions/adrs/adr-061-published-schema-evolution-policy.md` (ADR-061 Published Schema Evolution Policy)
- IMPLEMENTS → SPEC `contracts/schema-publication-manifest.json` (Schema Publication Manifest)
- IMPLEMENTS → POLICY `tools/check_schema_publication.py` (Schema Publication Policy Checker)
- IMPLEMENTS → CONFIG `noxfile.py` (Verification Workflow Configuration)
- TESTS → TEST `implementations/python/tests/test_repo_policy_tools.py` (Repo Policy Tool Tests)
- IMPLEMENTS → CODE_FILE `tools/check_schema_publication.py` (Schema publication manifest change-ledger gate (ADR-009 §7))
- IMPLEMENTS → GITHUB_ISSUE `90` (Issue #90: Versioning, deprecation & migration governance)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-075-ecosystem-versioning-deprecation-and-migration-governance.md` (ADR-075 Ecosystem Versioning, Deprecation, and Migration Governance)
- IMPLEMENTS → SPEC `specs/evolution/versioning-deprecation-and-migration.md` (Versioning, Deprecation, and Migration Specification)
- IMPLEMENTS → CONFIG `docs/conf.py` (Docs build version derives from distribution metadata (GOV-901))
- IMPLEMENTS → SPEC `specs/authority/authority-boundary.yaml` (Authority manifest: changelog.d/ removed from non-normative roots (GOV-901))
- IMPLEMENTS → POLICY `tools/check_authority_boundary.py` (Authority-boundary gate: changelog_fragments root dropped (GOV-901))
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-019-normative-authority-boundary-manifest.md` (ADR-019 amended: changelog.d/ removed after release-please replaced towncrier (GOV-901))
- TESTS → TEST `implementations/python/tests/test_version_classification.py` (Version-literal classification tests (GOV-901))
- IMPLEMENTS → GITHUB_ISSUE `1111` (Exact-version CLI startup import boundary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_cli/entrypoint.py` (Lazy exact-version console entry point)
- IMPLEMENTS → CONFIG `implementations/python/pyproject.toml` (Installed `raes` console-script binding)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1111-gov-901-cli-version-startup-preflight.md` (Measured startup boundary and compatibility invariants)
- TESTS → TEST `implementations/python/tests/test_issue_1111_cli_version_startup.py` (Source, fallback, delegation, and startup-budget guards)
- TESTS → TEST `implementations/python/tests/test_corpus_packaging.py` (Clean installed-wheel entry-point acceptance)
- IMPLEMENTS → GITHUB_ISSUE `1097` (Standard CPython 3.14 support and bounded 3.15 admission)
- IMPLEMENTS → GITHUB_ISSUE `1100` (Fail-closed Nox option-value validation)
- IMPLEMENTS → GITHUB_ISSUE `1117` (Python 3.14-safe MCP test event-loop boundaries)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1097-python-314-support-preflight.md` (Blocking interpreter matrix, clean distribution smoke, and free-threaded preview boundary)
- IMPLEMENTS → CONFIG `noxfile.py` (Exact interpreter selection, hermetic suite, build, install, and smoke graph)
- IMPLEMENTS → CONFIG `.github/workflows/ci.yml` (Blocking CPython 3.11 through 3.14 matrix)
- IMPLEMENTS → CONFIG `.github/workflows/python-free-threaded-preview.yml` (Nonblocking scheduled/manual 3.14t preview)
- TESTS → TEST `implementations/python/tests/test_repo_policy_tools.py` (Selector handoff and compatibility-graph regression tests)
- TESTS → TEST `implementations/python/tests/test_mcp_server.py` (Deprecation-free synchronous MCP test boundaries)
