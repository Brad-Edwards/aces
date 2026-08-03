---
id: GOV-919
title: "ACES Extension Discipline Over Shared Concept Authorities"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T15:37:12.193044Z
updated_at: 2026-04-10T01:19:05.833399Z
---

# GOV-919 — ACES Extension Discipline Over Shared Concept Authorities

## Statement

Where the adopted shared concept authority does not naturally cover experiment, runtime, apparatus, or governance concerns, the ecosystem shall define ACES-native extension concepts with explicit scope, relation rules, and non-ambiguity constraints relative to the shared authority.

## Rationale

ACES needs experiment and runtime concepts that go beyond classic cyber ontology, but those extensions must be disciplined so native meaning is extended rather than silently forked or duplicated.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Concept family native extension discipline validation and schema rules)
- TESTS → TEST `implementations/python/tests/test_concept_authority.py` (Native extension discipline model and fixture validation tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Concept family schema extension discipline shape tests)
- DOCUMENTS → DOCUMENTATION `specs/concept-authority/concept-authority.md` (Concept authority extension discipline specification)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-concept-model.md` (GOV-919 shared concept model guidance)
- DOCUMENTS → DOCUMENTATION `contracts/schemas/README.md` (Schema README concept authority catalog extension discipline documentation)
- DOCUMENTS → DOCUMENTATION `docs/decisions/adrs/adr-012-shared-concept-authority-and-aces-extension-discipline.md` (ADR-012 native extension discipline tightening decision)
- IMPLEMENTS → SPEC `contracts/concept-authority/concept-families-v1.json` (Authoritative concept family catalog with native extension discipline metadata)
- IMPLEMENTS → SPEC `contracts/schemas/concept-authority/concept-families-v1.json` (Published concept family schema enforcing native extension discipline)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#401` (SDL gap: first-class directory and domain identity semantics)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-032-directory-domain-identity-runtime-surface.md` (ADR-032 identity authority extension discipline)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md` (Identity authority lineage and source-status documentation)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (Identity authority design precedents and extension boundaries)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#407` (fix(sdl): harden identity authority refs)
