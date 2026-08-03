---
id: SEM-226
title: "Participant Exposure And Visibility-Boundary Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T02:10:21.522522Z
updated_at: 2026-07-22T00:28:53.750512Z
---

# SEM-226 — Participant Exposure And Visibility-Boundary Semantics

## Statement

The ecosystem shall define explicit participant exposure and visibility-boundary semantics for observations, control context, truth/adjudication assets, augmentation, and decision surfaces, including governed withholding, projection or masking, redaction, disclosure and declassification, role scope, transformation, loss, and evidence over time.

## Rationale

Issue #794 retains the ADR-083 visibility model and clarifies the distinct policy operations that must compose with SEM-230; future authorization cannot justify earlier exposure and realized delivery remains distinct from authored policy.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#119` (Participant tool/affordance & decision-surface semantics; exposure/visibility-boundary semantics (SEM-219, 220, 226))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#296` (Participant Exposure And Visibility-Boundary Semantics (SEM-226))
- DOCUMENTS → GITHUB_ISSUE `347` (Issue #347 — Multi-Organizational Authority And Governance Contracts)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-083-participant-tool-decision-surface-and-exposure-semantics.md` (ADR-083 participant tool, decision-surface, and exposure semantics)
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Formal SEM-219/SEM-220/SEM-226 participant semantics)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-119-sem-219-220-226-participant-decision-surface-preflight.md` (Issue 119 participant decision-surface architecture preflight)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared semantic integrity mapping for SEM-219/SEM-220/SEM-226)
- DOCUMENTS → GITHUB_ISSUE `794` (Assess and design formal participant I/O control with information-flow and bisimulation semantics)
- DOCUMENTS → DOCUMENTATION `docs/research/participant-io-control/requirement-disposition.md` (Issue #794 participant information-flow/control requirement disposition)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models/participant_exposure.py` (SEM-226 participant exposure projection and evidence model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models/participant_exposure_authority.py` (SEM-226 participant exposure authority and audit validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models/participant_exposure_policy.py` (SEM-226 participant exposure policy operations)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/participant_decision_surface_exposure.py` (SEM-226 serialized exposure binding contract)
- IMPLEMENTS → CONFIG `contracts/schemas/control-plane/participant-decision-surface-v1.json` (SEM-226 participant decision-surface exposure schema)
- IMPLEMENTS → SPEC `specs/formal/participant-semantics/README.md` (SEM-226 formal participant exposure semantics)
- IMPLEMENTS → GITHUB_ISSUE `296` (Participant Exposure And Visibility-Boundary Semantics (SEM-226))
- TESTS → TEST `implementations/python/tests/test_sem_226_participant_exposure.py` (SEM-226 participant exposure verification suite)
