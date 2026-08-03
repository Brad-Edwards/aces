---
id: SEM-219
title: "Participant Tool And Affordance Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:24:26.855124Z
updated_at: 2026-07-19T20:59:21.601117Z
---

# SEM-219 — Participant Tool And Affordance Semantics

## Statement

The ecosystem shall define explicit semantics for participant tool and affordance availability, visibility, invocation, and constraint handling.

## Rationale

Primary-source refresh shows that tool-using participants need shared semantics for what affordances exist and how their constraints are interpreted across syntax, runtime, and contracts.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#119` (Participant tool/affordance & decision-surface semantics; exposure/visibility-boundary semantics (SEM-219, 220, 226))
- DOCUMENTS → ADR `docs/decisions/adrs/adr-083-participant-tool-decision-surface-and-exposure-semantics.md` (ADR-083 participant tool, decision-surface, and exposure semantics)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-119-sem-219-220-226-participant-decision-surface-preflight.md` (Issue 119 participant decision-surface architecture preflight)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared semantic integrity mapping for SEM-219/SEM-220/SEM-226)
- IMPLEMENTS → CODE_FILE `tools/check_sdl_catalog_parity.py` (SDL tool-affordance catalog parity gate)
- TESTS → TEST `implementations/python/tests/test_sem_208_participant_behavior.py` (SEM-219 participant tool-affordance semantic and compiler tests)
- TESTS → TEST `implementations/python/tests/test_sdl_catalog_parity.py` (SEM-219 SDL catalog parity tests)
- DOCUMENTS → GITHUB_ISSUE `794` (Assess and design formal participant I/O control with information-flow and bisimulation semantics)
- DOCUMENTS → DOCUMENTATION `docs/research/participant-io-control/requirement-disposition.md` (Issue #794 participant information-flow/control requirement disposition)
- IMPLEMENTS → GITHUB_ISSUE `294` (Issue 294 — Participant Tool And Affordance Semantics)
- IMPLEMENTS → SPEC `specs/formal/participant-semantics/README.md` (Normative participant tool and affordance semantics)
- IMPLEMENTS → SPEC `specs/sdl/references.md` (SDL participant tool-affordance reference contract)
- IMPLEMENTS → CONFIG `contracts/schema-publication-manifest.json` (Published SDL schema change ledger)
- IMPLEMENTS → CONFIG `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring input schema)
- IMPLEMENTS → CONFIG `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated scenario schema)
- IMPLEMENTS → CONFIG `contracts/schemas/sdl/instantiated-scenario-snapshot-v1.json` (Instantiated scenario snapshot schema)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/participant_behavior_specification.py` (Participant tool-affordance authoring model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_declarations.py` (Participant tool-affordance declaration indexing)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_language_metadata.py` (Participant tool-affordance language metadata)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_mapping_scopes.py` (Participant tool-affordance mapping scope)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/composition.py` (Participant tool-affordance module composition)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/semantics/participant_behavior.py` (Participant tool-affordance semantic validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Participant tool-affordance validator integration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/_content_objectives.py` (Participant content-reference validation integration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/_participant_tool_affordances.py` (Participant tool identity and affordance validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/addresses.py` (Canonical tool-affordance runtime addresses)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/participant_behaviors.py` (Participant tool-affordance compilation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/pipeline.py` (Tool-affordance compiler pipeline integration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models/__init__.py` (Tool-affordance runtime model exports)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models/behavior_resources.py` (Typed tool-affordance runtime resource)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models/runtime_model.py` (Tool-affordance runtime-model ownership and uniqueness)
