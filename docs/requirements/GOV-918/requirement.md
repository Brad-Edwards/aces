---
id: GOV-918
title: "Cross-Artifact Concept Binding"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T15:37:12.079287Z
updated_at: 2026-04-06T03:48:56.348597Z
---

# GOV-918 — Cross-Artifact Concept Binding

## Statement

SDL, manifests, contracts, provenance records, evidence requirements, and reporting artifacts shall bind their declared meaning to canonical concepts rather than relying only on repeated labels or artifact-local definitions.

## Rationale

Portability breaks down when SDL, processor manifests, backend manifests, and reporting surfaces reuse the same strings without binding them to shared meaning.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (ConceptBindingEntryModel and V2 manifest concept_bindings field)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/vocabulary.py` (ConceptFamilyId pattern-constrained type)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/apparatus.py` (ConceptBinding frozen dataclass)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/capabilities.py` (BackendManifest concept_bindings field)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/manifest.py` (Backend manifest emission with concept bindings)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/capabilities.py` (ProcessorManifest concept_bindings field)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/manifest.py` (Processor manifest emission with concept bindings)
- TESTS → TEST `implementations/python/tests/test_concept_authority.py` (Concept binding entry and cross-catalog validation tests)
- TESTS → TEST `implementations/python/tests/test_backend_manifest.py` (Backend manifest concept binding validation tests)
- TESTS → TEST `implementations/python/tests/test_processor_manifest.py` (Processor manifest concept binding validation tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Concept binding schema shape and drift detection tests)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-concept-model.md` (Shared concept model design guidance with GOV-918 binding example)
- DOCUMENTS → DOCUMENTATION `contracts/schemas/README.md` (Schema README documenting cross-artifact concept binding section)
- TESTS → TEST `implementations/python/tests/test_requirement_governance.py` (Requirement governance branch UID detection regression test)
- TESTS → TEST `implementations/python/tests/test_repo_policy_tools.py` (Repository policy tooling tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Conformance runner updated for concept bindings)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/__init__.py` (Contracts package init updated for concept binding exports)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/versions.py` (Contract version constants)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/control_plane_api.py` (Control plane API updated for concept binding support)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Processor models updated for concept binding support)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/semantics/workflow.py` (Workflow semantics updated for concept binding support)
- IMPLEMENTS → CODE_FILE `implementations/python/src/aces/core/runtime/contracts.py` (Compat layer contracts re-export)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Runtime manager tests updated for concept bindings)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Runtime planner tests updated for concept bindings)
- TESTS → TEST `implementations/python/tests/test_runtime_registry.py` (Runtime registry tests updated for concept bindings)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#399` (Issue #399: scenario-vs-delivery deliberate omissions classification error)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#402` (PR #402: document scenario delivery boundary)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-033-scenario-delivery-boundary-for-runtime-node-state.md` (ADR-033: Scenario/Delivery Boundary for Runtime Node State)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_mounts.py` (Runtime mount and local-control interface redaction-boundary models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_configuration.py` (Runtime configuration aggregation for mount/control redaction boundary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_filesystem.py` (Runtime filesystem sensitivity vocabulary and schema guard helper)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema redaction guards for runtime mount/control fields)
- CONSTRAINS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated scenario schema redaction guards for runtime mount/control fields)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/parser.py` (SDL parser support for runtime mount/control redaction fields)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (SDL design precedents scenario/delivery omission boundary)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/limitations.md` (SDL limitations deployment authoring boundary documentation)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference for runtime mount/control boundary fields)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL validation rules for runtime redaction boundary guards)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime model tests for mount/control redaction and duplicate validation)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (SDL model tests for runtime mount/control redaction fields)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (SDL parser tests for runtime mount/control redaction fields)
- IMPLEMENTS → GITHUB_ISSUE `400` (Audit ACES design surface for scenario-vs-delivery classification drift)
- IMPLEMENTS → PULL_REQUEST `409` (docs: fix scenario delivery drift wording)
- IMPLEMENTS → DOCUMENTATION `docs/explain/sdl/scenario-delivery-drift-audit.md` (Scenario/Delivery Classification Drift Audit and Remediation)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/index.md` (SDL guide navigation for scenario/delivery drift audit and remediation)
- DOCUMENTS → DOCUMENTATION `docs/index.md` (Published documentation toctree for scenario/delivery drift audit and remediation)
- TESTS → TEST `implementations/python/tests/test_design_drift_audit.py` (Scenario/delivery drift audit remediation coverage test)
- IMPLEMENTS → SPEC `contracts/concept-authority/concept-families-v1.json` (runtime-inventory native concept family binding nodes.*.runtime to a canonical concept)
- IMPLEMENTS → SPEC `contracts/concept-authority/reference-models-v1.json` (scenario-node-runtime reference model anchoring nodes.*.runtime to runtime-inventory)
- IMPLEMENTS → SPEC `contracts/profiles/semantic/reference-stack-v1.json` (Reference-stack semantic profile authoring-phase runtime-inventory coverage)
- DOCUMENTS → DOCUMENTATION `specs/concept-authority/concept-authority.md` (Runtime-inventory extension-governance decision path (Extension Discipline))
- TESTS → TEST `implementations/python/tests/test_reference_models.py` (Node-runtime reference model + nullable-optional binding resolution tests)
- TESTS → TEST `implementations/python/tests/test_semantic_profiles.py` (Reference-stack authoring runtime-inventory coverage test)
- IMPLEMENTS → GITHUB_ISSUE `493` (Issue #493: runtime-inventory family + reference model for nodes.*.runtime)
- IMPLEMENTS → PULL_REQUEST `532` (PR #532: add runtime-inventory concept family and node runtime reference model)
- IMPLEMENTS → CODE_FILE `tools/check_concept_authority_governance.py` (Concept-authority catalog governance gate (ADR-linkage + reference resolution))
- TESTS → TEST `implementations/python/tests/test_concept_authority_governance.py` (Concept-authority governance gate tests (failure modes, boundaries, catalog error paths))
- DOCUMENTS → ADR `docs/decisions/adrs/adr-062-concept-authority-catalog-governance-gate.md` (ADR-062: Concept-Authority Catalog Governance Gate)
- IMPLEMENTS → GITHUB_ISSUE `496` (Issue #496: Concept authority governance gate — new family requires ADR linkage (review CA-6))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Compiler updated for concept binding support)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_stubs/manifest.py` (Stub backend concept bindings declarations)
