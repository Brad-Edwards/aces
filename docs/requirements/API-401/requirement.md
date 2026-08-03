---
id: API-401
title: "Backend Identity, Capability, And Compatibility Manifest"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:40:04.856534Z
updated_at: 2026-04-05T20:44:06.649973Z
---

# API-401 — Backend Identity, Capability, And Compatibility Manifest

## Statement

The ecosystem shall define a backend manifest by which a backend declares its identity, supported external contracts, supported operational features, compatibility surface, and declared constraints, independent of any one task's authored specificity or realized form.

## Rationale

Current state: implemented. Backends now publish a shared-apparatus manifest v2 that declares identity, supported contract versions, compatibility, constraints, and nested capability blocks; backend-manifest/v1 remains published as a compatibility surface.

## Traceability

- DOCUMENTS → DOCUMENTATION `contracts/README.md` (Contracts Overview)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- CONSTRAINS → ADR `ADR-004` (SDL Runtime Layer)
- CONSTRAINS → ADR `ADR-008` (Processor Layer And Execution Artifact Boundaries)
- CONSTRAINS → SPEC `contracts/schemas/backend-manifest/backend-manifest-v1.json` (Backend Manifest Schema)
- CONSTRAINS → SPEC `contracts/profiles/backend/full-remote-control-plane.json` (Backend Full Remote Control Plane Profile)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/capabilities.py` (Backend Capability Declarations)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/registry.py` (Runtime Target Registry Manifest Integration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Backend Manifest Conformance Validation)
- TESTS → TEST `implementations/python/tests/test_runtime_registry.py` (Runtime Registry Manifest Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Backend Manifest Conformance Tests)
- DOCUMENTS → DOCUMENTATION `contracts/schemas/README.md` (Published Contract Schemas Overview)
- CONSTRAINS → SPEC `contracts/schemas/backend-manifest/backend-manifest-v2.json` (Backend Manifest Schema v2)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Shared Apparatus Contract Models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/manifest.py` (Backend Manifest Payload Renderers)
- TESTS → TEST `implementations/python/tests/test_backend_manifest.py` (Backend Manifest Contract Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Shared Contract Schema Tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_stubs/manifest.py` (Reference Stub Backend Manifest)
