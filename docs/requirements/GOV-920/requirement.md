---
id: GOV-920
title: "Shared Semantic Profiles"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T15:37:12.298378Z
updated_at: 2026-04-10T23:41:24.095655Z
---

# GOV-920 — Shared Semantic Profiles

## Statement

The ecosystem shall define shared semantic profiles that declare the compatible concept, contract, and behavior assumptions required for interoperable authoring, exchange, processing, and execution.

## Rationale

Interoperability requires more than nominal support for a schema. Shared semantic profiles capture which assumptions and interpretations are expected to hold across composed artifacts and implementations.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Semantic profile contract model and validation rules)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/semantic_profiles.py` (Semantic profile loader helpers)
- IMPLEMENTS → SPEC `contracts/profiles/semantic/reference-stack-v1.json` (Reference stack shared semantic profile)
- IMPLEMENTS → SPEC `contracts/schemas/profiles/semantic-profile-v1.json` (Semantic profile JSON Schema)
- TESTS → TEST `implementations/python/tests/test_semantic_profiles.py` (Semantic profile validation and reference stack compatibility tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Semantic profile schema publication tests)
- DOCUMENTS → SPEC `specs/concept-authority/semantic-profiles.md` (Shared semantic profiles specification)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-concept-model.md` (Shared semantic profile design guidance)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-012-shared-concept-authority-and-aces-extension-discipline.md` (ADR-012 semantic profile composition note)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/versions.py` (Semantic profile schema version constant)
