---
id: EXP-732
title: "Realized Evidence Sources And Augmentation Provenance"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:59:50.853423Z
updated_at: 2026-06-28T18:07:50.939654Z
---

# EXP-732 — Realized Evidence Sources And Augmentation Provenance

## Statement

The ecosystem shall preserve, as part of run and apparatus provenance, the authored evidence requirements, the realized evidence sources used to satisfy them, and any processor or backend augmentation added for capture, evaluation, or operation.

## Rationale

Honest experiment interpretation requires preserving not only what data were captured, but also how the capture requirement was satisfied and what augmentation was added along the way.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#128` (Operational apparatus observability; observation-augmentation disclosure contracts; observability-plane/augmentation conformance; evidence-requirement refinement & realized-evidence provenance (RUN-316, API-419, ASR-525, EXP-731, 732))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#342` (Realized Evidence Sources And Augmentation Provenance (EXP-732))
- DOCUMENTS → GITHUB_ISSUE `347` (Issue #347 — Multi-Organizational Authority And Governance Contracts)
- IMPLEMENTS → GITHUB_ISSUE `128` (Issue #128 - Observability evidence conformance implementation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Augmentation provenance diagnostics require affected, carrier, and evidence references)
- IMPLEMENTS → DOCUMENTATION `docs/research/experiment-core/issue-342-exp-732-evidence-source-augmentation-provenance-preflight-guardrails.md` (Evidence source augmentation provenance preflight guardrails)
- TESTS → TEST `implementations/python/tests/test_observability_evidence_conformance.py` (Tests verify augmentation provenance diagnostics for evidence and carriers)
- TESTS → TEST `contracts/fixtures/experiment-core/experiment-run-v1/invalid/augmentation-without-affected-refs.json` (Semantic-invalid fixture for missing augmentation affected_refs)
