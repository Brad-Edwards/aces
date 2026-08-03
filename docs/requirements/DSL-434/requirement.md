---
id: DSL-434
title: "Security-monitoring detection definition semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-05-29T16:36:11.548321Z
updated_at: 2026-05-29T16:44:04.833890Z
---

# DSL-434 — Security-monitoring detection definition semantics

## Statement

The SDL shall represent loaded security-monitoring detection definitions as typed security-monitoring manager records with stable local identity, engine and native definition identity, source and content-set provenance, parsed predicate and correlation metadata, classification tags, canonical digest data, loaded/parser-accepted state, and validation that rejects ambiguous duplicate definition references.

## Rationale

Issue 434 identifies that file-level security-monitoring content-set inventory cannot support cross-range claims that the same individual detection definitions were loaded. A typed SDL manifest is required so downstream inventory consumers can compare parsed definitions without overloading content_sets or raw XML evidence.

## Traceability

- TESTS → TEST `implementations/python/tests/test_runtime_security_monitoring.py` (Runtime security-monitoring detection definition tests)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (Generated SDL authoring schema includes detection definitions)
- IMPLEMENTS → GITHUB_ISSUE `434` (Issue 434 security-monitoring detection definition semantics)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Generated instantiated scenario schema includes detection definitions)
- IMPLEMENTS → PULL_REQUEST `438` (Add runtime detection definition semantics)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-045-security-monitoring-detection-definition-semantics.md` (ADR-045 security-monitoring detection-definition semantics)
