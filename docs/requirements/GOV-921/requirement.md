---
id: GOV-921
title: "Shared Reference Models"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T15:37:12.409641Z
updated_at: 2026-04-11T00:47:44.975878Z
---

# GOV-921 — Shared Reference Models

## Statement

The ecosystem shall support shared reference models for recurrent federation-relevant structures including assets, identities, relationships, observables, actions or events, tools or artifacts, and other comparable experiment objects.

## Rationale

Primary-source review shows that interoperable ecosystems repeatedly depend on shared reference models for the objects they exchange and reason about. Without them, gateway logic and profile claims become fragile and implementation-specific.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Reference model catalog contract and semantic validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/reference_models.py` (Reference model catalog loader helpers)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/versions.py` (Reference model schema version constant)
- IMPLEMENTS → SPEC `contracts/concept-authority/reference-models-v1.json` (Shared reference model catalog)
- IMPLEMENTS → SPEC `contracts/schemas/concept-authority/reference-models-v1.json` (Reference model catalog JSON Schema)
- TESTS → TEST `implementations/python/tests/test_reference_models.py` (Reference model catalog validation tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Reference model schema publication tests)
- DOCUMENTS → SPEC `specs/concept-authority/reference-models.md` (Shared reference models specification)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-concept-model.md` (Shared reference model design guidance)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-012-shared-concept-authority-and-aces-extension-discipline.md` (ADR-012 reusable structure authority note)
