---
id: RUN-300
title: "Processing Model And Lifecycle"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:07.574340Z
updated_at: 2026-04-11T03:02:10.624502Z
---

# RUN-300 — Processing Model And Lifecycle

## Statement

The ecosystem shall provide a processing model that carries valid scenarios through instantiation, compilation, planning, execution, and live observation while preserving scenario meaning across those stages.

## Rationale

Current state: partially implemented. The SDL ecosystem needs a processing model that preserves scenario meaning through live execution rather than leaving lifecycle behavior implicit or backend-defined, while keeping contracts and archival run artifacts as distinct concerns.

## Traceability

- IMPLEMENTS → GITHUB_ISSUE `28` (RUN-300: Processing Model And Lifecycle)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/instantiate.py` (aces_sdl.instantiate — scenario instantiation stage)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/manager.py` (aces_processor.manager — runtime execution stage and provenance enforcement)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (aces_processor.models — RuntimeModel/ExecutionPlan/RuntimeSnapshot contracts)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/control_plane.py` (aces_processor.control_plane — live observation state surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/control_plane_api.py` (aces_processor.control_plane_api — live observation API surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/manifest.py` (aces_processor.manifest — processor manifest used as planning provenance)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/capabilities.py` (aces_processor.capabilities — backend capability enforcement for lifecycle)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (aces_contracts.contracts — portable workflow/evaluation state envelope)
- TESTS → TEST `implementations/python/tests/test_run_300_lifecycle.py` (RUN-300 five-stage lifecycle integrity test (new))
- TESTS → TEST `implementations/python/tests/test_fm2_semantics.py` (FM-2 semantics — instantiation/compilation diagnostics)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime model contract tests)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Runtime planner reconciliation and provenance tests)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Runtime manager apply/rollback/provenance tests)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane.py` (Runtime control-plane live-observation tests)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane_api.py` (Runtime control-plane API envelope tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Runtime contract model tests)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Runtime conformance tests across the stack)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (aces_sdl.validator — semantic validation for instantiated scenarios)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (aces_processor.compiler scenario compilation stage)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/planner/__init__.py` (aces_processor.planner — reconciliation and execution planning stage)
