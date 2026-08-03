---
id: SEM-206
title: "Assessment Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:58.596332Z
updated_at: 2026-05-10T16:57:33.275882Z
---

# SEM-206 — Assessment Semantics

## Statement

The ecosystem shall define explicit semantics for the assessment pipeline and its scoring, aggregation, and reference constraints.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Assessment-pipeline semantic validation pass (_verify_assessment_pipeline))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/semantics/assessment.py` (Assessment-pipeline semantic source of truth (references, aggregation, dependency roles))
- IMPLEMENTS → CODE_FILE `implementations/python/src/aces/core/semantics/assessment.py` (Compatibility re-export of aces_sdl.semantics.assessment)
- IMPLEMENTS → SPEC `specs/formal/assessment/README.md` (Assessment-pipeline formal artifacts — scope and implementation mapping)
- IMPLEMENTS → SPEC `specs/formal/assessment/pipeline-consistency.md` (Assessment-pipeline consistency rules, aggregation, and dependency/refresh semantics)
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/assessment-semantics.md` (Assessment-pipeline architecture guardrails (SEM-206 preflight note))
- TESTS → TEST `implementations/python/tests/test_semantics_assessment.py` (Assessment-pipeline semantic helper tests)
- TESTS → TEST `implementations/python/tests/test_fm2_semantics.py` (Cross-stage assessment-pipeline agreement tests (TestAssessmentPipelineAgreement))
- IMPLEMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#63` (Assessment pipeline semantics (SEM-206))
- DOCUMENTS → ADR `ADR-073` (ADR-073 (proposed): Scoring and Reward Language Scope in the SDL — re-examines whether the OCR/CybORG scoring/reward surfaces belong in the SDL assessment pipeline)
- IMPLEMENTS → GITHUB_ISSUE `682` (SEM-206 — realize ADR-073 (remove SDL scoring/reward; narrow objective success to conditions))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/evaluation.py` (Runtime compilation of propositions and assertions (proposition truth and assertion-composed objective success; SDL scoring removed per ADR-073))
