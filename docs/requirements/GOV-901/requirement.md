---
id: GOV-901
title: "Versioning And Compatibility Rules"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T07:16:00.634358Z
updated_at: 2026-06-14T02:41:58.145594Z
---

# GOV-901 — Versioning And Compatibility Rules

## Statement

The ecosystem shall define versioning and compatibility rules for language, semantic, processing, contract, module, and experiment surfaces.

## Rationale

Requirement inventory expansion. Compatibility claims need explicit versioning and compatibility rules across language, semantics, processing, contracts, modules, and experiments.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#90` (Versioning, deprecation & migration governance (GOV-901, 902, 903))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#240` (Versioning And Compatibility Rules (GOV-901))
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#497` (Published Schema Version Policy And Compatibility Gate)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-061-published-schema-evolution-policy.md` (ADR-061 Published Schema Evolution Policy)
- IMPLEMENTS → SPEC `contracts/schema-publication-manifest.json` (Schema Publication Manifest)
- IMPLEMENTS → POLICY `tools/check_schema_publication.py` (Schema Publication Policy Checker)
- IMPLEMENTS → CONFIG `noxfile.py` (Verification Workflow Configuration)
- TESTS → TEST `implementations/python/tests/test_repo_policy_tools.py` (Repo Policy Tool Tests)
- IMPLEMENTS → CODE_FILE `tools/check_schema_publication.py` (Schema publication manifest change-ledger gate (ADR-009 §7))
- IMPLEMENTS → GITHUB_ISSUE `90` (Issue #90: Versioning, deprecation & migration governance)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-075-ecosystem-versioning-deprecation-and-migration-governance.md` (ADR-075 Ecosystem Versioning, Deprecation, and Migration Governance)
- IMPLEMENTS → SPEC `specs/evolution/versioning-deprecation-and-migration.md` (Versioning, Deprecation, and Migration Specification)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_cli/main.py` (CLI --version honest distribution-metadata derivation (GOV-901))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_api.py` (Control-plane OpenAPI description version derivation (GOV-901))
- IMPLEMENTS → CODE_FILE `implementations/python/src/aces/__init__.py` (aces namespace version honest not-installed sentinel (GOV-901))
- IMPLEMENTS → CONFIG `docs/conf.py` (Docs build version derives from distribution metadata (GOV-901))
- IMPLEMENTS → SPEC `specs/authority/authority-boundary.yaml` (Authority manifest: changelog.d/ removed from non-normative roots (GOV-901))
- IMPLEMENTS → POLICY `tools/check_authority_boundary.py` (Authority-boundary gate: changelog_fragments root dropped (GOV-901))
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-019-normative-authority-boundary-manifest.md` (ADR-019 amended: changelog.d/ removed after release-please replaced towncrier (GOV-901))
- TESTS → TEST `implementations/python/tests/test_version_classification.py` (Version-literal classification tests (GOV-901))
