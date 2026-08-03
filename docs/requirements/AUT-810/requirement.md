---
id: AUT-810
title: "Safe Deterministic RAES Artifact Transformations"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 3
created_at: 2026-04-03T07:16:00.056251Z
updated_at: 2026-08-01T15:51:08.409328Z
---

# AUT-810 — Safe Deterministic RAES Artifact Transformations

## Statement

RAES shall provide pure, deterministic, provenance-preserving refactoring and transformation operations over canonical RAES SDL and portable contract artifacts, with semantic preservation or explicit loss diagnostics. Pack-aware file orchestration and user-interface workflows remain outside RAES.

## Rationale

Narrowed to the RAES semantic transformation kernel; env-packs and Hub own pack workflows and presentation.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#102` (Safe refactoring/transformation; catalog, search & discovery surfaces (AUT-810, 812))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/composition/__init__.py` (AUT-810 composition and reference preservation)
- DOCUMENTS → GITHUB_ISSUE `RAESystem/rae#265` (Safe deterministic RAES artifact transformations (AUT-810))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/transformations.py` (AUT-810 public artifact-transformation API)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/_transformation_rename.py` (AUT-810 deterministic rename operation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/_transformation_remove.py` (AUT-810 policy-gated removal operation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/_transformation_portable.py` (AUT-810 portable-contract canonicalization and comparison)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/_transformation_bindings.py` (AUT-810 concept-binding retargeting)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/contracts/artifact_transformations.py` (AUT-810 typed transformation report contract)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_conformance/artifact_transformations.py` (AUT-810 transformation conformance surface)
- IMPLEMENTS → SPEC `contracts/schemas/artifact-transformations/artifact-transformation-report-v1.json` (AUT-810 published transformation report schema)
- IMPLEMENTS → PROOF `specs/formal/artifact-transformations/README.md` (AUT-810 semantic-preservation proof record)
- TESTS → TEST `implementations/python/tests/test_artifact_transformations.py` (AUT-810 artifact-transformation verification suite)
- IMPLEMENTS → GITHUB_ISSUE `265` (Safe deterministic RAES artifact transformations (AUT-810))
