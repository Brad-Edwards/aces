---
id: GOV-922
title: "Controlled Vocabularies And Enumerations"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T15:37:12.514093Z
updated_at: 2026-04-11T02:26:15.170014Z
---

# GOV-922 — Controlled Vocabularies And Enumerations

## Statement

The ecosystem shall define controlled vocabularies and enumerations for portable declared concepts where stable cross-artifact comparison is required, while permitting governed extension space for concepts that are RAES-native, experimental, or still evolving.

## Rationale

A mature interoperability surface needs stable portable terms where comparison matters, but it also needs governed extension space so evolving concepts do not force premature standardization or uncontrolled drift.

## Traceability

- DOCUMENTS → SPEC `specs/concept-authority/concept-authority.md` (Concept authority specification)
- TESTS → TEST `implementations/python/tests/test_controlled_vocabularies.py` (Controlled vocabulary catalog tests)
- TESTS → TEST `implementations/python/tests/test_backend_manifest.py` (Backend manifest vocabulary enforcement tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Controlled vocabulary schema publication tests)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Planner tests for SDL OS validation with governed backend vocabularies)
- DOCUMENTS → SPEC `specs/concept-authority/controlled-vocabularies.md` (Controlled vocabularies and enumerations spec)
- DOCUMENTS → SPEC `contracts/concept-authority/controlled-vocabularies-v1.json` (Authoritative controlled vocabulary catalog)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-concept-model.md` (Shared concept model design note)
- IMPLEMENTS → CODE_FILE `tools/generate_contract_schemas.py` (Schema generation routing for controlled vocabularies)
- DOCUMENTS → DOCUMENTATION `contracts/schemas/README.md` (Schema publication README)
- DOCUMENTS → DOCUMENTATION `CHANGELOG.md` (Project changelog)
