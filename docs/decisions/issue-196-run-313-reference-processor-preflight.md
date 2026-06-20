# Issue 196 RUN-313 Reference Processor Preflight

Date: 2026-06-20

Issue: #196.

Requirement: RUN-313.

This note records architecture preflight guardrails for the repository-owned
reference processor implementation. It is guidance for implementation only: it
does not implement a processor facade, change manifests, add conformance cases,
change schemas, or alter runtime behavior.

## Binding Sources

- ADR-008 defines the processor as the semantics-bearing layer between SDL
  authoring and backend realization. Runtime is live execution state, not the
  whole processor.
- ADR-036 defines package ownership: `aces_sdl` parses and instantiates,
  `aces_processor` compiles, plans, and owns processor declarations,
  `aces_runtime` owns live control, `aces_contracts` owns neutral DTOs, and
  backends stay behind `aces_backend_protocols`.
- ADR-009 and ADR-061 define the authority boundary: published schemas,
  fixtures, profiles, and specs are authority; reference implementation code
  consumes them and proves compatibility.
- ADR-014, `.ground-control.yaml`, `.gc/plan-rules.md`, and `noxfile.py` define
  the canonical verification graph and policy gates.
- `docs/explain/sdl/runtime-architecture.md` is the current end-to-end
  processor/runtime path: instantiate, compile, plan, apply through a runtime
  target, and validate portable envelopes at runtime boundaries.
- `docs/explain/reference/backend-conformance.md` is the nearest conformance
  pattern: conformance is artifact-driven, schema-first, uses `Diagnostic`
  envelopes, and avoids runner-local schema or profile authority.

## Architecture Decisions

- Treat the reference processor as an implementation-side orchestration surface
  over existing public seams. It may assemble parse/instantiate, compile, plan,
  manifest publication, and runtime/control-plane execution, but it must not
  create a second compiler, planner, contract model, address scheme, or
  manifest authority.
- Keep implementation ownership aligned with ADR-036. Processor-facing
  assembly belongs in `aces_processor`; live apply/control-plane behavior stays
  in `aces_runtime`; Typer commands stay in `aces_cli`; conformance runners stay
  in `aces_conformance`; neutral DTOs stay in `aces_contracts`.
- The published processor manifest remains the declaration surface. Use
  `create_reference_processor_manifest()` and
  `reference_processor_manifest_payload()` as the single manifest rendering
  path, and validate the result through `ProcessorManifestV2Model` and the
  checked-in fixture.
- `supported_contract_versions` must be evidence-backed. Do not add a contract
  id to the reference processor manifest unless the implementation actually
  emits, consumes, or validates that contract through the shared model and a
  test or conformance case exercises the path.
- End-to-end execution should drive the existing path:
  `parse_sdl_file()` or `parse_sdl()`, `instantiate_scenario()`,
  `compile_runtime_model()` / `compile_scenario_runtime_model()`, `plan()`,
  `RuntimeManager` or `RuntimeControlPlane`, and a `RuntimeTarget` supplied by
  `BackendRegistry`.
- The in-memory stub backend is a non-normative backend target for exercising
  the processor/runtime path. Do not turn `aces_backend_stubs` into processor
  authority, backend conformance authority, or a production backend.
- Any processor conformance addition should follow the backend conformance
  model: published fixture/profile artifacts plus one registered validator
  seam. Do not hard-code a second profile table, fixture loader, or schema
  registry in processor implementation code.

## Required Incumbents

- SDL ingress and validation: `aces_sdl.parser.parse_sdl_file`,
  `parse_sdl`, YAML safe loading, `_load_normalized_data`,
  `SemanticValidator`, `instantiate_scenario`, `InstantiatedScenario`,
  `SDLParseError`, `SDLValidationError`, and `SDLInstantiationError`.
- Processor path: `aces_processor.compiler.compile_runtime_model`,
  `compile_scenario_runtime_model`, `aces_processor.planner.plan`,
  `snapshot_delete_order`, `RuntimeModel`, `ExecutionPlan`,
  `resource_payload(...)`, and `aces_processor.semantics.planner`.
- Processor declarations: `ProcessorManifest`, `ProcessorCapabilitySet`,
  `ProcessorFeature`, `REFERENCE_PROCESSOR_NAME`,
  `REFERENCE_SUPPORTED_CONTRACT_VERSIONS_V2`,
  `create_reference_processor_manifest()`, and
  `reference_processor_manifest_payload()`.
- Contract authority: `ContractModel(extra="forbid")`,
  `ProcessorManifestV2Model`, `BackendManifestV2Model`, plan/result/status
  models, `schema_bundle()`, `manifest_authority`,
  `contracts/schema-publication-manifest.json`, and
  `tools/check_generated_schemas.py`.
- Apparatus compatibility and provenance:
  `validate_experiment_apparatus_context_against_manifests()`,
  `ExperimentApparatusContextModel`, `ExperimentRunModel`,
  `ApparatusIdentityModel`, `ConceptBindingEntryModel`, and
  `aces_contracts.apparatus`.
- Runtime and backend boundaries: `BackendRegistry`, `RuntimeTarget`,
  `_validate_runtime_target_shape`, `RuntimeManager`,
  `RuntimeControlPlane`, `_call_backend_apply`, `_call_backend_diagnostics`,
  `ApplyResult`, `RuntimeSnapshot`, `OperationReceipt`, and
  `OperationStatus`.
- Observability and error shape: `aces_contracts.diagnostics.Diagnostic`,
  `Severity`, runtime diagnostic helpers, operation records, control-plane
  audit events, and existing conformance report envelopes.
- CLI and workflow: `aces_cli.main`, `aces_cli.processor`, `aces_cli.conformance`,
  `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `implementations/python/pyproject.toml`, and compatibility-only wrappers
  under `implementations/python/src/aces/`.

## Cross-Cutting Layers

- SDL/config parsing: authored input must pass through existing YAML parsing,
  top-level shape checks, import expansion, variable substitution,
  closed-world Pydantic models, and semantic validation. Do not build runtime
  models directly from dictionaries to skip parser or validator behavior.
- Contract validation: portable payloads must use `aces_contracts` models and
  `schema_bundle()`. Published schema edits require
  `contracts/schema-publication-manifest.json` ledger updates and the generated
  schema drift gate; implementation-only model edits are not schema authority.
- Manifest authority: processor and backend manifest claims must pass
  `manifest_authority` allowlists, controlled vocabulary checks, concept
  binding validation, and mutual compatibility checks. Manifest compatibility
  is processor/backend apparatus compatibility, not SDL scenario meaning.
- Runtime target validation: any executable target must be constructed as a
  `RuntimeTarget` through the registry/factory seam so manifest component
  presence and method call shapes are checked before execution.
- Runtime apply boundary: backend calls must go through `_call_backend_apply`
  or `_call_backend_diagnostics`, which deep-copy snapshots, convert backend
  exceptions to diagnostics, validate `ApplyResult` shape, validate runtime
  result contracts, and revert to the baseline snapshot on contract failure.
- Control-plane security: if the reference processor exposes HTTP/JSON control,
  use `create_control_plane_app()` with `ControlPlaneSecurityConfig` rather
  than a new adapter. Defaults must remain fail-closed: no trusted header
  identities, no bearer tokens, verified proxy headers required when enabled,
  role checks on mutating/read operations, target binding, request-size limits,
  redacted internal 500s, idempotency keys, and audit records.
- Secret handling: manifests, fixtures, examples, diagnostics, and audit events
  must not carry live secrets. Experiment parameters that cannot be published
  use existing redaction/withheld shapes; backend exception text should not
  contain tokens because runtime diagnostics can surface exception messages.
- Environment and OS exposure: avoid hidden environment configuration for
  processor behavior. If a CLI or test needs subprocesses, use fixed argv,
  `sys.executable` or the nox/uv invocation, no `shell=True`, no tokens in
  argv, and no ambient home-directory, network, or package-install assumptions.
- Persistence: durable live state belongs behind `ControlPlaneStore`,
  `InMemoryControlPlaneStore`, or `LocalControlPlaneStore`. Do not create a
  second operation store or ad hoc snapshot JSON format for the processor path.
- Error envelopes: public execution and conformance failures should remain
  structured `Diagnostic` values, operation statuses, or existing SDL errors.
  Do not add processor-local exception hierarchies, log channels, raw
  tracebacks, rejected payload dumps, or backend-native object reprs.
- Import and source policy: package imports must satisfy ADR-036 and
  `tools/policy/adr_policy.yaml`; no new implementation logic belongs under
  `implementations/python/src/aces/`; non-test package files must stay within
  the ADR-015 line-cap policy.

## Extension Boundary

The main extension seam is a small reference-processor assembly API
parameterized by scenario input, instantiation parameters/profile, target name
or registry descriptor, target config, optional base snapshot, and optional
control-plane store. Future backend variations should add or select
`BackendRegistry` descriptors and manifest payloads, not edit processor control
flow.

The manifest extension seam is
`REFERENCE_SUPPORTED_CONTRACT_VERSIONS_V2` plus the contract models, fixtures,
and conformance tests that prove each claim. Adding a future processor-facing
contract should require one authority update, one validator/fixture seam, and
one manifest test update, not local string checks across compiler, CLI, and
conformance code.

The conformance extension seam is the published contract id. Processor
conformance, if added, should mirror the backend runner shape: load the
published fixture/profile corpus, validate through shared contract models, and
return structured diagnostics. Fixture-only validation can support unknown
future profile ids; live target certification cannot certify a runtime surface
the implementation does not understand.

## Gotchas And Anti-Patterns

Avoid:

- treating the Python reference processor as normative authority instead of a
  consumer and executable proof of `specs/` and `contracts/`;
- adding a second compiled-runtime schema, manifest renderer, contract-id
  allowlist, profile table, fixture loader, diagnostic class, or exception
  hierarchy;
- bypassing `instantiate_scenario()`, `compile_runtime_model()`, `plan()`,
  `RuntimeTarget`, `RuntimeManager`, or `_call_backend_apply()` for convenience;
- using backend-native state, object identities, or ad hoc dictionaries as
  portable envelopes;
- broadening `aces_cli` or `aces_mcp` into semantic owners or runtime-internal
  callers;
- making `aces_backend_stubs` production-like or normative;
- claiming support in `processor-manifest-v2` before the code path and tests
  exercise the corresponding contract;
- changing published schemas without the schema publication manifest and
  generated-schema parity gate;
- leaking secrets through command argv, environment dumps, backend exception
  strings, diagnostics, audit records, fixture payloads, or CI logs;
- adding implementation logic under the legacy `aces.*` compatibility tree;
- editing `CHANGELOG.md` directly instead of adding the required fragment when
  the later implementation is user-visible.

## Non-Goals

- No new processor implementation code in this preflight.
- No schema, fixture, manifest, conformance, CLI, runtime, or backend behavior
  changes in this preflight.
- No production Docker/cloud/simulation backend and no managed cyber range
  behavior.
- No new authentication mechanism, secret store, persistence backend, logging
  stack, network fetch path, or OS process manager.
- No migration of legacy compatibility wrappers or owning-package public
  surfaces beyond what the eventual RUN-313 implementation explicitly needs.
- No implementation plan, task breakdown, or requirement status transition.
