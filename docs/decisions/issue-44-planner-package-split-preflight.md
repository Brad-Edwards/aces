# Issue 44 Planner Package Split Preflight

Date: 2026-07-18

Issue: #44.

Requirement: none. The GitHub issue is the implementation contract.

This note records architecture guardrails for converting
`aces_processor.planner` from a module to a package. It does not implement the
split, change planning behavior, drain the oversized allowlist, alter tests, or
add release-note content.

## Binding Decisions

- The live module is 836 lines, not the issue body's older 916-line snapshot.
  The reason for the split remains valid.
- ADR-015 and `tools/policy/adr_policy.yaml` enforce a 500-line cap, not the
  issue's older 600-line cap. Every Python file in the replacement package,
  including `__init__.py`, must stay at or below 500 lines.
- ADR-036 keeps planning in `aces_processor`. Planner child modules remain
  package-private implementation details; cross-package callers continue to
  import only `aces_processor.planner`.
- The facade's supported public API remains the exact ordered `__all__`:
  `plan`, `realization_disclosure`, and `snapshot_delete_order`. Preserve their
  signatures, defaults, annotations, docstrings, and object behavior.
  `realization_disclosure` remains the same function object owned by
  `aces_processor.semantics.realization`.
- The baseline issue-mandated grep has nine matches: eight executable external
  import lines and one policy-test fixture string. No match uses a planner child
  module, and no matching line changes. The legacy
  `aces.core.runtime.planner` compatibility wrapper is an additional consumer;
  it must keep targeting `aces_processor.planner` through
  `aces._compat.reexport`.
- Imported dependencies and private helpers that happen to be attributes of
  the current module are not supported facade exports: no repository caller
  imports them, and they are absent from `__all__`. Do not use wildcard exports
  or preserve this incidental namespace at the cost of a leaky facade.
- Release-please owns `CHANGELOG.md`. Despite the stale issue acceptance item,
  `.gc/plan-rules.md` forbids a manual changelog edit or fragment. The
  implementation must follow the live repository rule.

No new ADR is required. ADR-015, ADR-036, and the existing compiler/models
package-split precedents already decide the durable architecture; this note
only applies them to the planner's concrete contracts and failure modes.

## Architecture Boundary

`planner/__init__.py` is a thin explicit facade. It re-exports only the three
supported names and contains no planning, validation, or reconciliation logic.
Child modules use relative imports to their exact owners and never import the
facade, preventing partial-initialization cycles.

Split by the existing call graph and concept ownership, not line ranges:

- resource projection and reconciliation own `_planned_resource`, the explicit
  `RuntimeModel` resource-group table, dependency graph/order/cycle adapters,
  snapshot equality, action reconciliation, delete ordering, and the public
  `snapshot_delete_order` seam;
- finite variable-domain capability checks own the existing OS-family and
  node-count parsing, unresolved-variable handling, and capability-constraint
  lookup without inventing another variable schema;
- manifest validation owns the ordered provisioning, orchestration, and
  evaluation capability diagnostics and delegates account-feature extraction
  and variable-domain checks to their existing canonical helpers;
- domain-plan construction owns the three explicit provisioning,
  orchestration, and evaluation builders, preserving their different DTOs,
  fields, and delete/startup ordering; and
- one pipeline coordinator owns `plan()`, effective realization requirement
  materialization, the ordered diagnostic chain, topology validation, and
  final `ExecutionPlan` assembly.

The dependency direction is foundations (contracts and semantic helpers) to
resource/capability leaves, then domain builders, then the pipeline, then the
facade. Keep capability-variable validation separate from the manifest
coordinator if necessary to retain cohesive files and reasonable headroom
under 500 lines; do not replace the current explicit checks with a registry,
service container, generic validator framework, or plugin system.

The extension seams already exist and need no new abstraction. A future
planned resource family is added explicitly to the resource-group table and
the owning plan/contract domain. A future backend capability is added to the
typed `BackendManifest`/capability contract and the ordered manifest validator.
Realization-policy variation remains the existing explicit
`apparatus_realization_default: ApparatusRealizationDefaultResolver | None`
parameter; backend, state, and target variation remain the existing
`manifest`, `snapshot`, and `target_name` parameters. Do not bind any of these
from environment or global registration state.

## Required Incumbents

- **Plan and state DTOs:** `aces_contracts.planning` owns `ChangeAction`,
  `RuntimeDomain`, `PlannedResource`, the operation types, the three plan types,
  plan address/resource-type validation, and startup-order validation.
  `aces_contracts.runtime_state` owns `RuntimeSnapshot` and `SnapshotEntry`.
  `aces_processor.models` owns `RuntimeModel`, `ExecutionPlan`,
  `CompiledCapabilityConstraint`, and `resource_payload`. Do not copy, wrap, or
  redefine any of them.
- **Reconciliation semantics:** `aces_processor.semantics.planner` remains the
  single source for dependency graphs, cycles, topological/delete order,
  refresh propagation, and create/update/delete/unchanged reconciliation.
  Planner child modules adapt its `ReconciliationAction` to `ChangeAction`; they
  do not fork its algorithms.
- **Manifest and capability validation:** retain
  `aces_backend_protocols.BackendManifest` and its typed provisioner,
  orchestrator, evaluator, controlled-vocabulary, contract-version, and
  realization-envelope validation. Reuse
  `provisioner_account_features()` and
  `domain_topology_plan_diagnostics()`; do not introduce local account-feature,
  topology, node-type, OS-family, content-type, workflow-feature, or evaluator
  vocabularies.
- **SDL value and envelope semantics:** keep `MINIMUM_NODE_COUNT`, `OSFamily`,
  `extract_variable_name`, `parse_enum_or_var`, `parse_int_or_var`, and
  `aces_sdl.realization_envelope.member` as the canonical parsers and relation
  gate. Do not hand-parse `${...}` references or duplicate enum/integer-domain
  validation.
- **Realization semantics:** keep
  `materialize_realization_requirements`,
  `realization_support_diagnostics`,
  `realization_envelope_diagnostics`, and `realization_disclosure` in
  `aces_processor.semantics.realization`. The planner coordinates them; it does
  not become a second realization authority.
- **Errors and observability:** retain `aces_contracts.diagnostics.Diagnostic`
  and existing dataclass/`ValueError` boundaries. Preserve diagnostic codes,
  domains, addresses, messages, severity, multiplicity, and order. The planner
  has no logger or alternate exception hierarchy and must not acquire one.
- **Compatibility and workflow:** use the explicit facade pattern already
  established by `aces_processor.compiler` and `aces_processor.models`, retain
  the one `aces.*` compatibility wrapper, and rely on ADR-015/ADR-036 policy,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/verify_all.py`, and the pinned nox `verify` session. Remove the deleted
  path only from `tools/policy/oversized_allowlist.yaml`; the locked historical
  reference in `tools/policy/repo_policy.py` remains policy code.

## Cross-Cutting And Security Layers

- **Authoring and phase admission:** callers still reach planning only after
  the existing SDL parser, semantic validator, instantiation/admission, compiler
  analyzers, `RuntimeModel.__post_init__`, canonical-address validation, and
  duplicate-address checks. The package split must not add a raw SDL/config
  ingress or bypass these gates.
- **Manifest shape and policy:** `BackendManifest` construction still rejects
  unknown options and validates apparatus identity, processor compatibility,
  supported contract ids, realization support, concept bindings, capability
  shapes, controlled vocabulary terms, and realization-envelope pairing before
  `_validate_manifest` performs scenario-versus-backend checks.
- **Planner validation:** preserve finite OS/count domain validation,
  provisioner/orchestrator/evaluator capability diagnostics, realization
  support diagnostics, realization-envelope membership/subsumption diagnostics,
  dependency-cycle diagnostics, and domain-topology diagnostics. Preserve the
  current order: compiled-model diagnostics; manifest diagnostics; realization
  support; realization envelope; concrete envelope membership; ordering cycles;
  then topology diagnostics, with topology diagnostics also appended to the
  provisioning plan.
- **Plan-shape validation:** construction of `PlannedResource`, plan operations,
  and the three plan DTOs continues to enforce compiled addresses, embedded
  address/map-key agreement, runtime-domain/resource-type identity, unique
  operation addresses, and valid startup orders. Do not replace these contract
  validators with planner-local shape checks.
- **Auth and secret handling:** the planner makes no authorization decision and
  reads no credential store. MCP and control-plane authentication remain in
  their existing transport/API layers. Plan payloads can already contain
  authored account/content data in memory; the split must not log, summarize,
  persist, or place those payloads, parameter values, environment values,
  credentials, tokens, or private material into new diagnostics or exceptions.
- **MCP and error envelopes:** `aces_mcp.tools.operations` continues to apply
  request-size and compile-pipeline gates before `plan()` and renders only the
  existing bounded plan summary plus structured `Diagnostic` values. Preserve
  diagnostic redaction and ordering; do not expose raw plan payloads,
  tracebacks, or child-module exceptions through a new envelope.
- **Runtime, disclosure, and persistence:** `RuntimeManager` remains the plan
  consumer and `aces_runtime.backend_calls` remains the runtime realization
  disclosure gate. `RuntimeSnapshot` and existing control-plane stores remain
  the only persistence surfaces. Planner modules add no repository, database,
  cache, audit store, or snapshot metadata ledger.
- **Environment, OS, process, and network exposure:** all planner work remains
  an in-process deterministic transformation driven by explicit arguments. The
  split adds no environment binding, config schema, filesystem access,
  subprocess/argv value, shell call, socket, network request, or host mutation.
- **Import and repository policy:** child modules remain under
  `aces_processor`, whose ADR-036 boundary permits only
  `aces_backend_protocols`, `aces_contracts`, and `aces_sdl` as first-party
  dependencies. New paths and the allowlist edit continue through repository
  path-safety, module-boundary, secret/private-key, 500-line, and allowlist-drain
  checks.

## Gotchas And Anti-Patterns

- Convert `planner.py` to `planner/` atomically; never leave both import
  candidates, and do not modify any external import line or retarget the legacy
  compatibility wrapper.
- Preserve the exact `__all__` order and explicit re-export identities. Do not
  use `from ... import *`, dynamic discovery, `__getattr__`, import scanning, or
  registration side effects. Do not rewrite function `__module__` metadata or
  add pickle shims without a demonstrated compatibility contract.
- Do not import the facade from child modules. In particular, keep the pipeline
  at the top of the internal dependency graph so importing
  `aces_processor.planner` cannot observe a partially initialized package.
- Preserve resource-group and mapping insertion order, diagnostic accumulation
  order, action derivation, refresh propagation, topological/delete order,
  operation type, operation order, payload equality, and the distinction
  between plan-wide and provisioning-plan topology diagnostics.
- `RuntimeDomain.PARTICIPANT` exists, but the current planner intentionally
  builds only provisioning, orchestration, and evaluation plans. Do not use the
  split to add participant resources or a fourth plan.
- Keep the three domain builders explicit. A generic operation-builder
  abstraction risks conflating different DTOs, startup-order contracts, and
  provisioning realization-envelope behavior for little reuse.
- Do not merge backend manifest declaration validation with
  scenario-versus-manifest capability diagnostics; they are different gates.
  Do not duplicate schemas, controlled vocabularies, capability extractors,
  variable parsers, topology checks, realization semantics, reconciliation
  algorithms, diagnostics, or exception types in planner child modules.
- Do not remove apparently unused private adapters, inline semantic helpers,
  sort previously insertion-ordered data, deduplicate diagnostics, or otherwise
  perform incidental cleanup in a behavior-equality refactor.
- Historical design notes that name planner private helpers are design
  provenance, not supported import contracts. Do not leak every private helper
  through the facade merely to preserve those prose references.
- Do not modify pre-existing tests to accommodate changed behavior. Existing
  planner, realization, topology, runtime-manager, control-plane, MCP,
  reference-processor, and compatibility tests remain the behavior oracle.

## Non-Goals

- No planning, reconciliation, capability, realization, topology, validation,
  diagnostic, ordering, snapshot, payload, runtime, persistence, API, or
  security behavior change.
- No schema, contract, controlled vocabulary, manifest profile, SDL grammar,
  concept-authority, generated artifact, fixture, or conformance change.
- No new public child-module API, DTO, validator framework, exception
  hierarchy, logger, registry/plugin system, configuration surface, repository,
  persistence layer, network API, CLI/MCP endpoint, or compatibility shim.
- No movement of planner ownership into `aces_sdl`, `aces_contracts`,
  `aces_runtime`, a backend package, or the legacy
  `implementations/python/src/aces` compatibility tree.
- No incidental optimization, dead-code cleanup, test relaxation, policy-code
  change, version edit, or manual changelog edit.
