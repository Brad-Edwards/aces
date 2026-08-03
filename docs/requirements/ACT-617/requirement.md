---
id: ACT-617
title: "Mixed-Control Participant Operation"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 3
created_at: 2026-04-03T06:15:08.540051Z
updated_at: 2026-07-24T17:25:47.134870Z
---

# ACT-617 — Mixed-Control Participant Operation

## Statement

The ecosystem shall support participants whose behavior combines autonomous operation with external direction, approval or denial, intervention, handoff, override, or cancellation through explicit controller and authority state and ordered transitions distinct from action admission, execution, and observation.

## Rationale

Issue #794 found the original mixed-control requirement sound but underspecified: portable behavior needs explicit controller identity, authority basis, validity, ordering, conflict, provenance, and handoff semantics rather than behavior modes or ad hoc overrides.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#93` (Participant derived-context views & mixed-control operation (ACT-616, 617))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#251` (Mixed-Control Participant Operation (ACT-617))
- TESTS → TEST `implementations/python/tests/test_issue_1004_apparatus_backend_capabilities.py` (ACT-617 processing-role-trust controller/authority declaration tests)
- DOCUMENTS → GITHUB_ISSUE `794` (Assess and design formal participant I/O control with information-flow and bisimulation semantics)
- DOCUMENTS → DOCUMENTATION `docs/research/participant-io-control/requirement-disposition.md` (Issue #794 participant information-flow/control requirement disposition)
- TESTS → TEST `implementations/python/tests/test_act_617_mixed_control.py` (ACT-617 mixed-control authoring, validation, composition, compiler, and fixture tests)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md#act-617` (ACT-617 lineage mapping, evidence, status, and non-claims)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/participant_behavior_specification.py` (Mixed-control participant operation authoring models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/_mixed_control.py` (Mixed-control semantic validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/_mixed_control.py` (Mixed-control compiler projection)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models/behavior_resources.py` (Mixed-control compiled behavior resources)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/composition.py` (Mixed-control composition support)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring input mixed-control schema)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated scenario mixed-control schema)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/instantiated-scenario-snapshot-v1.json` (Instantiated scenario snapshot mixed-control schema)
- IMPLEMENTS → SPEC `specs/formal/participant-behavior-model/README.md` (ACT-617 mixed-control participant formal semantics)
- IMPLEMENTS → GITHUB_ISSUE `251` (Mixed-Control Participant Operation (ACT-617))
