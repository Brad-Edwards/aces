---
id: API-413
title: "Realization Support And Disclosure Declarations"
status: ACTIVE
type: INTERFACE
priority: MUST
wave: 2
created_at: 2026-04-05T00:54:58.521004Z
updated_at: 2026-04-12T03:13:42.645239Z
---

# API-413 — Realization Support And Disclosure Declarations

## Statement

Processor and backend manifest surfaces shall declare the concern domains in which they can supply realizations for underspecified inputs, the kinds of constraints or exact requirements they can honor, and the realization disclosures they produce.

## Rationale

Current state: implemented. Processor and backend v2 manifest surfaces publish realization_support declarations over the shared authority stack. Backend manifests are now v2-only, and backend conformance fails when declared contract support does not cover the contracts required by the inferred runtime capability profile.

## Traceability

- DOCUMENTS → DOCUMENTATION `contracts/schemas/README.md` (Published Contract Schemas Overview)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- CONSTRAINS → ADR `ADR-008` (Processor Layer And Execution Artifact Boundaries)
- CONSTRAINS → SPEC `contracts/schemas/backend-manifest/backend-manifest-v2.json` (Backend Manifest Schema v2)
- CONSTRAINS → SPEC `contracts/schemas/processor-manifest/processor-manifest-v2.json` (Processor Manifest Schema v2)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/apparatus.py` (Shared Apparatus Declaration Dataclasses)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Shared Realization Support Contract Models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/manifest.py` (Reference Processor Realization Support Declarations)
- TESTS → TEST `implementations/python/tests/test_backend_manifest.py` (Backend Manifest Realization Support Tests)
- TESTS → TEST `implementations/python/tests/test_processor_manifest.py` (Processor Manifest Realization Support Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Shared Manifest Schema Tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/capabilities.py` (Backend Manifest Runtime Boundary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/manifest.py` (Backend Manifest Contract Emitter)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Backend Conformance Contract Validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/manifest_authority.py` (Backend Manifest Authority Sets)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/versions.py` (Backend Manifest Contract Versions)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Backend Conformance Runtime Tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_stubs/manifest.py` (Reference Backend Realization Support Declarations)
