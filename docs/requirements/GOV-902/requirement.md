---
id: GOV-902
title: "Deprecation And Lifecycle Rules"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T07:16:00.772485Z
updated_at: 2026-07-11T01:46:38.073071Z
---

# GOV-902 — Deprecation And Lifecycle Rules

## Statement

The ecosystem shall define deprecation and lifecycle rules for ecosystem constructs so that supersession and removal are predictable and reviewable.

## Rationale

Requirement inventory expansion. Deprecation and removal need explicit lifecycle rules.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#90` (Versioning, deprecation & migration governance (GOV-901, 902, 903))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#241` (Deprecation And Lifecycle Rules (GOV-902))
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-075-ecosystem-versioning-deprecation-and-migration-governance.md` (ADR-075 Ecosystem Versioning, Deprecation, and Migration Governance)
- IMPLEMENTS → SPEC `specs/evolution/versioning-deprecation-and-migration.md` (Versioning, Deprecation, and Migration Specification)
- IMPLEMENTS → GITHUB_ISSUE `90` (Issue #90: Versioning, deprecation & migration governance)
- IMPLEMENTS → SPEC `specs/evolution/deprecation-records.yaml` (Ecosystem Deprecation Records ledger (GOV-902))
- IMPLEMENTS → CODE_FILE `tools/check_deprecation_lifecycle.py` (Deprecation & lifecycle policy gate (GOV-902))
- TESTS → TEST `implementations/python/tests/test_deprecation_lifecycle.py` (Deprecation-lifecycle gate tests (GOV-902))
- IMPLEMENTS → PULL_REQUEST `756` (PR #756 — realize GOV-902 deprecation & lifecycle rules)
