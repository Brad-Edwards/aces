---
id: API-413
title: "Realization Support And Disclosure Declarations"
status: ACTIVE
type: INTERFACE
priority: MUST
wave: 2
created_at: 2026-04-05T00:54:58.521004Z
updated_at: 2026-08-11T00:00:00Z
---

# API-413 — Realization Support And Disclosure Declarations

## Statement

Processor and backend manifest surfaces shall declare the concern domains in which they can supply realizations for underspecified inputs, the kinds of constraints or exact requirements they can honor, and the realization disclosures they produce.

## Rationale

Current state: implemented. Processor and backend v2 manifest surfaces publish realization_support declarations over the shared authority stack. Backend manifests are now v2-only, and backend conformance fails when declared contract support does not cover the contracts required by the inferred runtime capability profile. Evaluator proposition declarations are binding at planner admission: compiled predicate, quantifier, evidence-channel, and v1 time-domain requirements must fit the target manifest.

## Traceability

- DOCUMENTS → DOCUMENTATION `contracts/schemas/README.md` (Published Contract Schemas Overview)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- CONSTRAINS → ADR `ADR-008` (Processor Layer And Execution Artifact Boundaries)
- CONSTRAINS → SPEC `contracts/schemas/backend-manifest/backend-manifest-v2.json` (Backend Manifest Schema v2)
- CONSTRAINS → SPEC `contracts/schemas/processor-manifest/processor-manifest-v2.json` (Processor Manifest Schema v2)
- TESTS → TEST `implementations/python/tests/test_backend_manifest.py` (Backend Manifest Realization Support Tests)
- TESTS → TEST `implementations/python/tests/test_processor_manifest.py` (Processor Manifest Realization Support Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Shared Manifest Schema Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Backend Conformance Runtime Tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/compiler/evaluation.py` (Typed evaluator capability requirement projection)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/planner/manifest_validation.py` (Fail-closed evaluator proposition admission)
- IMPLEMENTS → DOCUMENTATION `docs/decisions/issue-1036-evaluator-capability-admission-remediation.md` (Issue 1036 remediation decision)
- IMPLEMENTS → GITHUB_ISSUE `1036` (Fine-grained evaluator capability admission)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Evaluator capability admission regression tests)
