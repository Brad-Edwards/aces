---
id: API-405
title: "Participant Capability Declaration"
status: ACTIVE
type: INTERFACE
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:16:03.990625Z
updated_at: 2026-05-24T05:59:00.847841Z
---

# API-405 — Participant Capability Declaration

## Statement

Backend manifests shall declare supported participant roles, behavior features, and interaction features.

## Rationale

Requirement inventory expansion. The runtime remains agnostic, so backend support for participant behavior must be declared explicitly.

## Traceability

- IMPLEMENTS → CONFIG `contracts/concept-authority/controlled-vocabularies-v1.json` (API-405 governed participant runtime vocabularies)
- IMPLEMENTS → SPEC `contracts/schemas/backend-manifest/backend-manifest-v2.json` (Generated backend manifest v2 schema with API-405 fields)
- IMPLEMENTS → SPEC `specs/formal/runtime-contracts/README.md` (Lineage-grounded participant capability declaration standard)
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/backend-conformance.md` (Backend conformance API-405 rationale and extension boundary)
- TESTS → TEST `implementations/python/tests/test_backend_manifest.py` (Backend manifest API-405 participant capability tests)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Runtime conformance API-405 evidence tests)
