---
id: ASR-511
title: "Layered Validation And Admission Profiles"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 3
created_at: 2026-04-03T07:17:04.816970Z
updated_at: 2026-07-05T03:35:08.628570Z
---

# ASR-511 — Layered Validation And Admission Profiles

## Statement

The ecosystem shall define layered validation and admission profiles distinguishing structural, semantic, behavioral, and stronger validity claims.

## Rationale

Requirement inventory expansion. Mature ecosystems need explicit validation-strength distinctions rather than a single undifferentiated validation claim.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#97` (Layered validation & admission profiles; validation-strength disclosure (ASR-511, 515))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#258` (Layered Validation And Admission Profiles (ASR-511))
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-072-validation-and-admission-profiles.md` (ADR-072 validation and admission profiles)
- IMPLEMENTS → SPEC `specs/formal/validation-admission-profiles/README.md` (Validation and admission profiles formal specification)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#97` (Issue 97: Layered validation and admission profiles)
- IMPLEMENTS → CONFIG `contracts/profiles/validation/validation-profile-catalog-v1.json` (Validation profile catalog v1)
- IMPLEMENTS → CONFIG `contracts/schemas/profiles/validation-profile-catalog-v1.json` (Published validation profile catalog schema v1)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/validation_profiles.py` (Validation profile contract models and selector)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance/validators.py` (Validation profile conformance integration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/bundle.py` (Validation profile schema bundle registration)
- TESTS → TEST `implementations/python/tests/test_validation_profiles.py` (Validation profile catalog tests)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-258-asr-511-layered-validation-profiles-preflight.md` (ASR-511 layered validation profiles design boundary)
- DOCUMENTS → DOCUMENTATION `contracts/README.md` (Validation profile catalog contract documentation)
- DOCUMENTS → DOCUMENTATION `contracts/schemas/README.md` (Published validation profile schema documentation)
- IMPLEMENTS → GITHUB_ISSUE `258` (Issue 258: Layered Validation And Admission Profiles)
- IMPLEMENTS → PULL_REQUEST `867` (PR 867: Add validation profile catalog)
