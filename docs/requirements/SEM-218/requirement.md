---
id: SEM-218
title: "Explicitness And Realization Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T00:54:58.405111Z
updated_at: 2026-05-18T02:32:39.252532Z
---

# SEM-218 — Explicitness And Realization Semantics

## Statement

The ecosystem shall define semantics distinguishing binding author declarations from concerns left open to processor or backend realization, including when realization is permitted, when explicit declarations must be honored, and when unsupported exact requirements must be rejected rather than silently approximated.

## Rationale

Current state: identified gap. Honest portability requires normative semantics for what is binding, what may be realized later, and when approximation is forbidden.

## Traceability

- IMPLEMENTS → GITHUB_ISSUE `1043` (Issue #1043 forwarding-agent realization semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/runtime_forwarding_agent.py` (Forwarding-agent ownership-role model)
- TESTS → TEST `implementations/python/tests/test_issue_1043_forwarding_agent_posture.py` (Forwarding-agent ownership and evidence-binding tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/validator/_evidence_requirements.py` (Evidence-plane validation for forwarding-agent ownership roles)
- TESTS → TEST `implementations/python/tests/test_issue_1043_realization_corroboration.py` (Forwarding-agent realization corroboration tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/realization_observation.py` (Value-bearing, operation- and apparatus-bound runtime realization observations)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/apparatus.py` (Typed realization observation capabilities)
- IMPLEMENTS → PULL_REQUEST `369` (PR #369 feat(sdl): add runtime inventory surfaces)
- DOCUMENTS → GITHUB_ISSUE `363` (Issue #363 exact runtime filesystem facts must be expressible, not approximated)
- IMPLEMENTS → GITHUB_ISSUE `72` (Explicitness & realization semantics: binding declarations vs processor/backend realization (SEM-218))
- IMPLEMENTS → SPEC `specs/formal/realization/explicitness-and-realization.md` (SEM-218 normative spec: Explicitness And Realization Semantics)
- IMPLEMENTS → SPEC `specs/formal/realization/README.md` (SEM-218 realization-spec domain README)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/explicitness-realization-semantics.md` (SEM-218 implementer-facing companion (non-normative))
- IMPLEMENTS → PULL_REQUEST `163` (docs: add SEM-218 explicitness and realization semantics spec)
- DOCUMENTS → GITHUB_ISSUE `368` (Issue #368 exact container host/security/mount facts must be expressible, not approximated)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime compiler tests requiring exact declared runtime facts and clean diagnostics)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL validation documentation for exact runtime declarations and typed runtime facts)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/limitations.md` (SDL limitations documentation clarifying runtime facts now expressible through typed fields)
- IMPLEMENTS → GITHUB_ISSUE `489` (Issue #489 SEM-218 realization enforcement 1/3: explicitness classifier + substitution-downgrade rule)
- IMPLEMENTS → PULL_REQUEST `529` (PR #529 feat: add explicitness classifier semantics)
- TESTS → TEST `implementations/python/tests/test_sem_218_explicitness.py` (SEM-218 explicitness classifier and substitution downgrade regression tests)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared semantic integrity explanation updated for SEM-218 explicitness classifier realization)
- TESTS → TEST `implementations/python/tests/test_sem_218_realization.py` (SEM-218 part-2 tests: compiler emission class preservation + planner realization gate)
- IMPLEMENTS → GITHUB_ISSUE `490` (Issue #490 SEM-218 realization enforcement 2/3: typed compiler emission + planner gate)
- TESTS → TEST `implementations/python/tests/test_sem_218_runtime_realization.py` (SEM-218 runtime gate + provenance tests (Execution/Observation rows))
- IMPLEMENTS → GITHUB_ISSUE `491` (SEM-218 realization enforcement 3/3 (issue #491))
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-760-sem-218-provenance-preservation-preflight.md` (Issue 760 SEM-218 provenance-preservation architecture preflight)
- TESTS → TEST `implementations/python/tests/test_sem_218_realization_designation.py` (SEM-218 scoped realization posture cascade, planner gate, and provenance regression tests)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-539-realization-posture-cascade-preflight.md` (Issue 539 SEM-218 realization-posture cascade architecture preflight)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-985-runtime-configuration-realization-concerns-preflight.md` (Issue 985 runtime-configuration realization-concern architecture preflight)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/_stateful_resource_references.py` (Runtime mount and stateful-resource destination conflict enforcement)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/compiler/realization_requirements.py` (RuntimeConfiguration lowering into typed SEM-218 realization requirements)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/planner/__init__.py` (Public planner realization disclosure and snapshot sanitization surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/planner/core.py` (Planner materialization and reconciliation of runtime realization requirements)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/planner/operations.py` (Deterministic planner operations for realization concern reconciliation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/planner/ordering.py` (Ordering rules for realization concern plan operations)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization.py` (SEM-218 runtime realization disclosure and safe observation integration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization_concern_observations.py` (Strict observed realization-concern contracts and commitment validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization_concern_projections.py` (Canonical safe projections for runtime realization concerns)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization_concerns.py` (Canonical runtime realization concern descriptor registry)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization_runtime_evaluation.py` (Runtime realization comparison and mismatch evaluation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization_snapshot_sanitization.py` (Safe backend realization snapshot sanitization)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_runtime/backend_calls.py` (Backend realization observation sanitization and disclosure enforcement)
- TESTS → TEST `implementations/python/tests/test_issue_985_realization_projection.py` (Issue 985 canonical realization projection and sanitization tests)
- TESTS → TEST `implementations/python/tests/test_issue_985_runtime_observation_contract.py` (Issue 985 strict runtime observation contract tests)
- TESTS → TEST `implementations/python/tests/test_issue_985_runtime_realization_concerns.py` (Issue 985 compiler, planner, and backend realization concern tests)
- IMPLEMENTS → GITHUB_ISSUE `985` (Issue #985 lower RuntimeConfiguration dimensions into realization concerns)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/validator/__init__.py` (Semantic validation hook for SEM-218 explicitness classification diagnostics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/runtime_configuration.py` (Exact node-scoped runtime declaration aggregation and duplicate validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/runtime_filesystem.py` (Typed runtime filesystem facts with exact path, ownership, mode, digest, and sensitivity fields)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/runtime_container.py` (Typed runtime container host, security, and health declarations)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/explicitness.py` (SEM-218 exact, constrained, and open explicitness classifier)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/scenario.py` (Scenario explicitness metadata surface for downstream consumers)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/instantiate.py` (Instantiation path preserving authored explicitness through variable substitution)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/_capability_constraints.py` (Finite-domain realization constraints retained during instantiation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/models/runtime_model.py` (RuntimeModel realization requirement metadata field)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/runtime_state.py` (SEM-218 realization provenance ledger on runtime snapshots)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/realization_designation.py` (Scoped realization cascade, addressed compute-substrate constraints, and canonical scope resolution)
- IMPLEMENTS → GITHUB_ISSUE `1066` (Portable runtime process-resource-limit realization semantics)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1066-runtime-resource-limits-preflight.md` (Issue 1066 architecture and supported-target inventory)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (Portable SDL process-resource-limit authoring guidance)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/nodes.py` (Canonical compute/switch resource-kind semantics and node-scoped runtime constraints)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/phase_contracts.py` (Process-limit constraint provenance across SDL phases)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/runtime_resource_limits.py` (Portable process-resource-limit authoring model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/validator/_core.py` (Process-limit semantic validation integration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/validator/_runtime_process_limits.py` (Process-limit selector and cross-reference validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_backend_protocols/manifest.py` (Backend manifest process-limit capability publication)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_backend_protocols/process_resource_limits.py` (Manifest adapter for typed process-limit capability domains)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/contracts/__init__.py` (Public process-limit contract facade)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/contracts/_exports.py` (Process-limit contract exports)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/contracts/capabilities.py` (Process-limit capability contract model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/vocabulary.py` (Governed process-limit resource and scope vocabulary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/realization_envelope_carrier.py` (Selected-configuration binding for typed process-limit capability domains)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/compiler/provisioning.py` (Process-limit constraint provenance compilation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization_process_limits.py` (Typed process-limit admission and constraint semantics)
- TESTS → TEST `implementations/python/tests/test_issue_1066_runtime_resource_limits.py` (Absent, exact, constrained, open, unsupported, substituted, excess, and evidence conformance)
- IMPLEMENTS → GITHUB_ISSUE `1076` (Compute-node intent separated from backend virtualization mechanism)
- IMPLEMENTS → PULL_REQUEST `1082` (Compute-kind and realization-substrate implementation)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1076-compute-node-realization-semantics-preflight.md` (Evidence-based authority analysis and architecture guardrails)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/_legacy_node_migration.py` (Meaning-preserving legacy VM migration to compute plus an exact virtual-machine constraint)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/compute_substrate.py` (Governed compute-substrate constraint invariants)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization_requirement.py` (Typed compiled realization requirements carrying substrate authority metadata)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization_compute_substrate.py` (Fail-closed compute-substrate evidence evaluation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/semantics/realization_runtime_common.py` (Shared runtime realization evidence and non-approximation rules)
- IMPLEMENTS → CONFIG `contracts/realization-envelopes/reference-emulation/in-process-v1.json` (Governed in-process emulation realization envelope)
- IMPLEMENTS → CONFIG `contracts/realization-envelopes/reference-emulation/oci-container-v1.json` (Configuration-bound OCI container realization envelope)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_reference_backend/envelopes.py` (Reference driver-mode to realization-envelope binding)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_reference_backend/drivers/oci_observation.py` (Owned OCI daemon readback for actual substrate evidence)
- TESTS → TEST `implementations/python/tests/test_issue_1076_compute_realization.py` (Compute-kind, substrate constraints, migration, cross-backend admission, and evidence-binding conformance)
