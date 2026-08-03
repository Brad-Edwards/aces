---
id: SEM-216
title: "Evidence, Evaluation, And View Boundary Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 3
created_at: 2026-04-03T07:17:04.502479Z
updated_at: 2026-06-23T04:05:31.953035Z
---

# SEM-216 — Evidence, Evaluation, And View Boundary Semantics

## Statement

The ecosystem shall define explicit semantics distinguishing runtime-observable state, captured evidence, derived evaluations, analysis outputs, and audience-specific views.

## Rationale

Requirement inventory expansion. Evidence, results, and views must remain conceptually distinct across the ecosystem.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#92` (Derived-context, evidence-boundary & external-knowledge semantics (SEM-214, 216, 217))
- DOCUMENTS → GITHUB_ISSUE `347` (Issue #347 — Multi-Organizational Authority And Governance Contracts)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (ParticipantContextViewModel SEM-216 audience boundary + evidence loss-disclosure schema rule)
- IMPLEMENTS → SPEC `contracts/schemas/control-plane/participant-context-view-v1.json` (participant-context-view-v1 schema with SEM-216 audience-boundary allOf + x-aces-invariants)
- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-evidence-record-v1.json` (experiment-evidence-record-v1 schema with SEM-216 redaction/loss-disclosure rule)
- IMPLEMENTS → SPEC `specs/formal/participant-semantics/README.md` (SEM-216 boundary-semantics section (B1-B5 + strata-to-carrier traceability))
- TESTS → TEST `implementations/python/tests/test_sem_216_boundary_semantics.py` (SEM-216 boundary-obligation tests (B1-B5 + positive + relational + schema-invariant))
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#248` (Evidence, Evaluation, And View Boundary Semantics (SEM-216))
