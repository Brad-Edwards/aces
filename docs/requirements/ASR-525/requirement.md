---
id: ASR-525
title: "Observability Plane And Augmentation Disclosure Conformance"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
created_at: 2026-04-05T01:59:51.101356Z
updated_at: 2026-06-28T18:07:50.939628Z
---

# ASR-525 — Observability Plane And Augmentation Disclosure Conformance

## Statement

The ecosystem shall maintain conformance fixtures and checks that distinguish scenario-native observability, authored evidence requirements, and processor or backend augmentation, and that verify required augmentation disclosure where such claims apply.

## Rationale

The ecosystem needs executable checks against silent instrumentation and plane confusion, not just prose guidance about keeping these concerns separate.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#128` (Operational apparatus observability; observation-augmentation disclosure contracts; observability-plane/augmentation conformance; evidence-requirement refinement & realized-evidence provenance (RUN-316, API-419, ASR-525, EXP-731, 732))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#340` (Observability Plane And Augmentation Disclosure Conformance (ASR-525))
- IMPLEMENTS → GITHUB_ISSUE `128` (Issue #128 - Observability evidence conformance implementation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Semantic diagnostics distinguish observability planes and reject incomplete augmentation disclosure)
- TESTS → TEST `implementations/python/tests/test_observability_evidence_conformance.py` (Tests verify observability augmentation and run-refinement conformance diagnostics)
- TESTS → TEST `contracts/fixtures/experiment-core/experiment-run-v1/invalid/augmentation-without-affected-refs.json` (Semantic-invalid fixture for incomplete augmentation provenance)
