# Issue 41 Compiler Package Split Preflight

Date: 2026-07-15

Issue: #41.

Requirement: none. The GitHub issue is the implementation contract.

This note records architecture guardrails for converting
`aces_processor.compiler` from a module to a package. It does not implement the
split, change compiler behavior, drain the oversized allowlist, or alter tests.

## Binding Decisions

- The compiler is currently 2,677 lines, not the issue body's older 1,495
  lines. The split must account for the current domains and call graph.
- ADR-015 and `tools/policy/adr_policy.yaml` now enforce a 500-line cap, not
  600 lines. Every Python file in the replacement package, including
  `__init__.py`, must stay at or below 500 lines.
- ADR-036 keeps compilation in `aces_processor` and makes
  `aces_processor.compiler` an approved cross-package public import. Child
  compiler modules are implementation detail, not new public APIs.
- The repository imports only `compile_runtime_model` and
  `compile_scenario_runtime_model` from the owning-package facade. The legacy
  `aces.core.runtime.compiler` wrapper also delegates to that facade through
  `aces._compat.reexport`; both paths must keep working without caller edits.
- Release-please owns `CHANGELOG.md`. Despite the stale issue acceptance
  criterion, the implementation PR must not edit it or add a changelog
  fragment; `.gc/plan-rules.md` is the current repository policy.

## Architecture Boundary

`compiler/__init__.py` is the public facade. It re-exports the two compiler
entry points and contains no compilation logic. The current module has no
`__all__`; any new `__all__` must be limited to the supported entry points and
must be checked against the legacy re-export behavior. Preserve public
signatures, defaults, annotations, docstrings, and deliberately observable
module metadata.

Split by semantic ownership and dependency direction, not line ranges:

- shared serialization, stable deduplication, canonical address construction,
  and named-reference resolution form package-private foundations;
- provisioning owns templates, capability constraints, node/network, feature,
  content, and account compilation;
- participant contracts own action contracts, observation/view projections,
  and outcome-interpretation rules, while participant behavior/specification
  compilation remains a separate cohesive concern;
- evaluation owns propositions, assertions, condition bindings, objective
  windows, and objectives;
- orchestration owns injects, events, scripts, and stories;
- workflow compilation owns predicates, control steps, capability features,
  result/execution contracts, and compensation; it may use more than one file
  to remain below the cap, but must retain one ordered workflow coordinator;
- realization compilation owns SEM-218 designation lowering and typed
  realization requirements; and
- one package-private assembly coordinator owns admission, analysis, compiler
  invocation order, diagnostic accumulation order, and `RuntimeModel`
  construction.

Foundation modules must not import domain modules or the package facade.
Domain compilers consume foundations and existing SDL/model contracts; the
assembly coordinator passes prerequisite maps such as assertions and injects
explicitly, as the current module does. `__init__.py` imports only the public
entry-point owner. This direction prevents facade partial-initialization cycles
without introducing a registry, service container, or generic compiler
framework.

The extension seam is the existing explicit subdomain function contract:
`InstantiatedScenario`, a shared ordered `list[Diagnostic]`, and only the
prerequisite compiled maps or semantic analyses that a domain needs. A future
compiled resource family belongs in its semantic owner and is wired once into
the assembly coordinator and `RuntimeModel`; it must not require caller imports
from child modules or a second orchestration workflow.

## Required Incumbents

- **Admission and phase validation:** `instantiate_scenario()`,
  `admit_instantiated_scenario()`, their Pydantic/`SemanticValidator` checks,
  and `build_declaration_index()` remain the only admission and collision
  gates. Preserve their order, including re-admission of an already
  instantiated artifact at the compiler boundary.
- **Canonical identity:** `aces_contracts.addressing.render_compiled_address`
  remains the renderer. `RuntimeModel` and its resource DTOs continue to apply
  `require_compiled_address`, map-key/address equality, and duplicate-address
  checks. Do not add a second address grammar or parse rendered addresses back
  into SDL references.
- **Schemas and DTOs:** retain `Scenario`, `ExpandedScenario`,
  `InstantiatedScenario`, `RuntimeModel`, the existing processor model types,
  neutral `aces_contracts` workflow/evaluation contracts, and
  `aces_backend_protocols` capability enums. Do not copy, wrap, or redefine
  them in compiler submodules.
- **Semantic analyzers:** continue to use `analyze_domain_topology()`,
  `analyze_objective_window()`, `partition_objective_dependencies()`,
  `workflow_step_semantic_contract()`, `resolve_realization_designation()`, and
  `registered_realization_concerns()` as their existing single sources of
  truth.
- **Serialization and determinism:** preserve
  `model_dump(mode="json", by_alias=True)`, dict fallbacks, declaration
  iteration order, order-preserving deduplication, the value-sorted feature
  deduplication, and the current top-level compilation/diagnostic order.
- **Errors and observability:** continue to emit the existing
  `aces_contracts.diagnostics.Diagnostic` identity through
  `aces_processor.models`. Preserve diagnostic codes, domains, messages,
  severity, ordering, and existing `ValueError`/SDL exception behavior. The
  compiler adds no logging or alternate error envelope.
- **Repository workflow:** build discovery remains the existing Hatch package
  configuration. ADR-015/ADR-036 policy is enforced by
  `tools/check_repo_policy.py`; the canonical completion graph is the pinned
  nox `verify` session from `.ground-control.yaml`.

## Cross-Cutting Layers And Security

- **Structural and semantic input gates:** public compiler entry points still
  pass through closed Pydantic phase shapes, instantiation/admission semantic
  validation, declaration collision checking, and domain analyzers before
  emitting a model. Moving code must not bypass, duplicate, or reorder them.
- **Compiled contract gates:** constructed DTOs and `RuntimeModel.__post_init__`
  continue to validate address syntax, embedded/map-key agreement, uniqueness,
  workflow/evaluation contract shapes, and typed realization requirements.
- **Auth and secret handling:** compilation has no authorization decision,
  credential lookup, secret store, or trust-policy responsibility. It must not
  acquire one. Authored/bound values may enter returned `spec` payloads through
  the existing serializer, but must not be copied into logs, diagnostics, or a
  new summary surface.
- **Environment and configuration shapes:** the only variation seam remains
  explicit `parameters` and `profile` arguments processed by
  `instantiate_scenario()`. Do not bind compiler behavior from environment
  variables or add configuration schemas. Repository YAML policy shapes remain
  validated by the existing policy tooling.
- **OS/process/network/persistence exposure:** the compiler remains a pure
  in-process transformation. The split introduces no subprocess, process-argv,
  filesystem, network, database, cache, or control-plane operation, so no token
  or payload may gain an OS-level exposure path.
- **Error-envelope leakage:** SDL admission exceptions and structured compiler
  diagnostics remain the only error surfaces. Do not log raw scenarios,
  parameter values, environment values, credentials, or tracebacks, and do not
  convert collectable diagnostics into raised exceptions or vice versa.
- **Import and policy gates:** compiler submodules stay inside
  `aces_processor` and may depend only on the ADR-036 incumbents
  `aces_sdl`, `aces_contracts`, and `aces_backend_protocols`; they must not
  import `aces_runtime`, backend implementations, CLI, conformance, or MCP.

## Gotchas And Anti-Patterns

- Do not change any external `from aces_processor.compiler ...` or
  `import aces_processor.compiler` line. Keep the compatibility wrapper target
  unchanged as well.
- Do not leave both `compiler.py` and `compiler/`; package conversion is one
  replacement. Remove only the deleted path's allowlist entry, not the locked
  reference in policy code.
- Do not make `__init__.py` a second compiler, expose child modules as supported
  API, or route internal imports back through the facade.
- Do not merge participant visibility, evaluator truth, workflow state, and
  realization requirements into a generic "runtime compiler" abstraction;
  their schemas and diagnostic semantics are distinct.
- Do not optimize away the current admission/declaration-index calls, change
  helper evaluation order, sort previously insertion-ordered mappings, or
  collapse diagnostic lists. These are observable behavior under the existing
  determinism and phase-contract tests.
- Do not duplicate reference indexes, address builders, analyzer issue maps,
  DTOs, validation, diagnostics, or exception hierarchies merely to avoid a
  package-private dependency.
- Update documentation that names the deleted `compiler.py` path or private
  helper locations when the replacement paths exist; do not leave normative
  and semantic-integrity references pointing at a deleted file.
- Do not modify pre-existing tests to accommodate changed behavior. The broad
  compiler, phase, identifier, participant, objective, workflow, realization,
  determinism, reference-processor, MCP, and runtime-manager tests are the
  behavior oracle.

## Non-Goals

- No schema, SDL grammar, phase, validation, address, diagnostic, planning,
  workflow, participant, objective, or realization behavior change.
- No new public compiler abstraction, plugin/registry system, DTO, exception,
  logger, configuration surface, persistence layer, network API, or
  compatibility shim.
- No movement of compilation responsibility into `aces_sdl`, `aces_runtime`,
  `aces_contracts`, a backend package, or the legacy `implementations/python/src/aces`
  compatibility tree.
- No incidental cleanup, performance rewrite, test relaxation, policy-code
  edit, version edit, or manual changelog edit.
