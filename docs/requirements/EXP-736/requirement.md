---
id: EXP-736
title: "Experiment Authoring Input Specification"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-07-09T05:57:25.978357Z
updated_at: 2026-07-09T05:58:08.572458Z
---

# EXP-736 — Experiment Authoring Input Specification

## Statement

The ecosystem shall support authoring and validating an experiment specification (pre-run authoring input) that binds an experiment task to a run plan — stochastic controls/seeds, episode controls (turn order, step count, termination), red-variant selection, and either a condition allocation or a target run count — as an input artifact distinct from the archival run, study, and apparatus-context records it produces.

## Rationale

Requirement inventory expansion. The experiment-core contracts are archival provenance outputs; specifying an experiment before execution needs a first-class authoring-input surface analogous to SDL scenario authoring. Decided by ADR-074 (issue #675).

## Traceability

- IMPLEMENTS → GITHUB_ISSUE `675` (Issue #675: experiment authoring surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/experiment_spec.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/versions.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/server.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/experiment_authoring.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/operations.py`
- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-authoring-input-v1.json` (experiment-authoring-input-v1 published schema)
- TESTS → TEST `implementations/python/tests/test_experiment_authoring.py`
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py`
- TESTS → TEST `implementations/python/tests/test_example_schema_conformance.py`
- TESTS → TEST `implementations/python/tests/paths.py`
- DOCUMENTS → ADR `docs/decisions/adrs/adr-074-experiment-authoring-input-contract-boundary.md` (ADR-074: Experiment Authoring-Input Contract Boundary)
- DOCUMENTS → SPEC `specs/formal/experiment-core/README.md` (Experiment-core formal spec)
