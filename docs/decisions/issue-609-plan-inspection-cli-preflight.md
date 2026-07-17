# Issue 609 Plan Inspection CLI Preflight

Date: 2026-07-17

Issue: #609.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture guardrails for exposing compiled plans as JSON.
It does not implement the command, add a serializer, change a published
contract, or define an implementation plan.

## Binding Boundaries

- ADR-008 keeps compile and plan in the semantics-bearing processor; inspection
  stops before runtime apply.
- ADR-009 and ADR-061 make `contracts/schemas/plans/` and
  `contracts/fixtures/plans/` the published authority. Python models prove
  compatibility with those artifacts; they do not replace them.
- ADR-036 assigns CLI wiring to `aces_cli`, processing to `aces_processor`,
  neutral plan DTOs to `aces_contracts`, backend declarations to
  `aces_backend_protocols`, and live apply/security/persistence to
  `aces_runtime`.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and
  `tools/policy/adr_policy.yaml` are the workflow and import-policy gates.

## Architecture Decisions

- The command is a read-only adapter over the existing reference processor
  path. Reuse `ReferenceProcessor.realize()` / `run_reference_processor()` so
  parsing, import expansion, instantiation, compilation, planning, and
  diagnostics cannot drift from library behavior. Do not reproduce the MCP
  `compile_pipeline()` or call private compiler/planner helpers from the CLI.
- The published JSON units are the three domain plans:
  `ProvisioningPlanModel`, `OrchestrationPlanModel`, and
  `EvaluationPlanModel`, each containing `PlanOperationModel` values. The
  internal `ExecutionPlan` is a composite orchestration object; there is no
  published `ExecutionPlanModel` or execution-plan schema.
- A single JSON stdout document may therefore contain `provisioning`,
  `orchestration`, and `evaluation` members whose values independently validate
  against the three published schemas, plus the aggregate execution-plan
  diagnostics needed to explain a non-zero result. That top-level object is
  only a CLI presentation envelope, not a fourth plan contract. If acceptance
  is read to require the whole stdout document to validate as one published
  contract, stop for an explicit contract decision rather than inventing an
  `ExecutionPlanModel` in implementation code.
- Add one owning-package projection from internal plan dataclasses to the
  existing Pydantic contract models and reuse it from the CLI. The projection
  must explicitly include operations, startup order, diagnostics, and the
  optional realization-envelope identity; convert enum values and tuples to
  JSON values; omit absent optional fields; and validate before
  `model_dump(mode="json")`. It must exclude the internal `resources` map,
  compiled `RuntimeModel`, backend manifest object, base snapshot, target
  binding, and other `ExecutionPlan` implementation state. Raw `asdict(plan)`
  is not contract serialization: it includes the forbidden `resources` field.
- Keep serializer ownership with the neutral plan-contract boundary, following
  the existing `backend_manifest_v2_model()` / `backend_manifest_payload()`
  renderer pattern. The CLI selects format and writes stdout; it does not own
  field mapping or contract validation.
- Treat `--manifest` as a UTF-8 JSON `backend-manifest-v2` file unless the issue
  owner specifies a backend-name selector. Validate it first with
  `BackendManifestV2Model`, then convert it through one backend-protocol-owned
  adapter to the internal `BackendManifest` used by the planner. Do not pass a
  Pydantic model or an unvalidated dictionary into planner logic, and do not
  duplicate capability, controlled-vocabulary, compatibility, or realization
  validation in `aces_cli`.
- The absent-manifest behavior must be the same clearly labelled reference
  dry-run manifest used by the incumbent MCP `sdl_plan` surface. It is a
  convenience planning target, not evidence that a backend ran or that a
  production target supports the scenario. Avoid importing
  `aces_backend_stubs.stubs` into the CLI if that also pulls live-runtime
  implementation modules into the authoring process; expose or reuse a pure
  manifest declaration seam instead.
- JSON stdout must be deterministic and automation-safe: one document, stable
  member ordering, stable operation order inherited from the planner, UTF-8,
  and a trailing newline. Human/progress text belongs on stderr. Planning
  diagnostics remain data in the emitted plan surface; admission/parse failures
  produce no partial JSON document and exit non-zero.
- Use `execution_plan.diagnostics` for the aggregate CLI diagnostics and
  `execution_plan.is_valid` for status. Do not serialize
  `ReferenceProcessorResult.diagnostics` blindly: the current reference facade
  prepends `model.diagnostics` to an execution-plan diagnostic list that already
  includes the model diagnostics, so doing so can duplicate entries.

## Required Incumbents

- CLI: `aces_cli.main`, `aces_cli.processor`, Typer `Path` arguments,
  `typer.BadParameter`, `typer.Exit`, and the JSON-output/exit convention in
  `aces_cli.conformance.backend()`.
- Processing: `aces_processor.reference.ReferenceProcessor`,
  `run_reference_processor`, `compile_scenario_runtime_model()`, and
  `aces_processor.planner.plan()` through the public reference facade.
- SDL admission: `parse_sdl_file()`, the YAML safe loader and source limits,
  module composition lock/trust handling, closed SDL Pydantic models,
  `SemanticValidator`, and `instantiate_scenario()` as reached by the reference
  processor.
- Plan authority: `aces_contracts.planning` dataclasses,
  `PlanOperationModel`, the three `*PlanModel` classes,
  `ContractModel(extra="forbid")`, `require_plan_operation_identity()`,
  `schema_bundle()`, and `contracts/fixtures/plans/*`.
- Manifest authority: `BackendManifestV2Model`, the dataclasses and validators
  in `aces_backend_protocols`, `manifest_authority`, controlled-vocabulary and
  concept-binding validation, and the existing backend manifest renderer as
  the reverse-direction pattern.
- Diagnostics and secret posture: `SDLParseError`, `SDLValidationError`,
  `SDLInstantiationError`, Pydantic `ValidationError`,
  `aces_contracts.diagnostics.Diagnostic`, and the explicit-redaction rules in
  `specs/sdl/diagnostics.md` and `aces_sdl.runtime_values`.
- Verification: plan valid/invalid fixtures, `test_runtime_contracts.py`,
  `test_runtime_planner.py`, `test_reference_processor.py`, CLI tests using
  `typer.testing.CliRunner`, the generated-schema parity gate, repo policy, and
  the canonical nox `verify` graph.

## Cross-Cutting Layers

- **SDL source gate:** use file-backed `parse_sdl_file()` so UTF-8 handling,
  the 8 MiB input bound, scalar/depth/node/alias/composition limits, forbidden
  tags/directives, duplicate/colliding-key checks, JSON-domain checks, import
  trust/lock resolution, structural closure, semantic validation, and
  instantiation all remain active. Never use `yaml.load`,
  `skip_semantic_validation`, or direct `Scenario.model_validate()` here.
- **Manifest gate:** bound the local file read before decoding; require UTF-8
  JSON mapping input; validate the closed published model; then construct the
  internal typed manifest so its capability, contract-id, compatibility,
  realization-support, concept-binding, and controlled-vocabulary validators
  run too. A local path is not permission to accept unknown fields or coerce a
  malformed declaration.
- **Realization-envelope gate:** a `backend-manifest-v2` payload carries only
  the realization-envelope identity, while planner envelope membership needs
  the full configured envelope expression. Resolve an identity only through a
  canonical, digest-checked envelope declaration. If no such declaration is
  available, reject that manifest as insufficient for planning; never drop the
  envelope, strip `realization-envelope-v1` support, or silently weaken the
  planner gate.
- **Plan contract gate:** build the published Pydantic model, which enforces
  closed fields, canonical compiled addresses, domain/resource identity,
  unique operation addresses, and valid startup-order references. Serialize
  the validated model, not internal dataclasses or `__dict__` output.
- **Secret/output gate:** explicit `redacted` and `operator_secret` SDL fields
  must already omit raw values before compile. Do not echo parameter maps,
  source documents, manifest bodies, environment variables, tracebacks, or
  exception input representations on errors. Deliberate `secret_fixture`
  scenario values may enter a plan payload, so stdout is an explicit
  user-requested disclosure surface and must never be copied to logs or a
  second diagnostic channel.
- **OS/process gate:** accept SDL and manifest paths, not inline manifest JSON,
  parameter maps, tokens, private keys, or credentials in argv. This command
  needs no subprocess, shell, environment binding, network service, temporary
  file, or permission change. Existing SDL imports may use their established
  trust-controlled resolver; the CLI must not add another fetch path.
- **Error envelope:** catch the established SDL, manifest/Pydantic, and bounded
  conversion errors at the CLI boundary and render concise stderr messages
  without raw framework payloads. Do not add a CLI exception hierarchy. When a
  plan is produced with error diagnostics, emit the complete JSON plan and use
  a non-zero exit status, matching the conformance CLI's machine-readable
  failure convention.
- **Observability and persistence:** stdout JSON, stderr diagnostics, and the
  process exit code are sufficient. Do not add telemetry, audit storage, a
  `ControlPlaneStore`, snapshot persistence, cache files, or runtime operation
  records for inspection.
- **Import/workflow policy:** `aces_cli` currently allows only
  `aces_processor.manifest` and `aces_processor.models` as public processor
  prefixes and forbids runtime imports. Any use of `aces_processor.reference`
  or a backend-manifest adapter must be reflected narrowly and deliberately in
  `tools/policy/adr_policy.yaml`; do not evade the gate through compatibility
  imports under `implementations/python/src/aces/` or local dynamic imports.

## Extension Boundary

The durable seam is the typed plan projector: it accepts an internal domain
plan (or the three domain plans from an `ExecutionPlan`) and returns the
corresponding existing contract model. The CLI's `--format` dispatch consumes
those models. A future YAML renderer, single-domain selection, or file-output
option should reuse that projector and change only presentation.

Keep backend selection as a separate input seam: default reference dry-run
manifest versus an explicitly supplied, fully resolved manifest. A future
named backend selector or base-snapshot input should change selection/planning
inputs, not serialization or published plan shapes.

## Gotchas And Anti-Patterns

Avoid:

- serializing `ExecutionPlan`, `RuntimeModel`, or plan dataclasses with
  `asdict()`, `default=str`, `__dict__`, or a generic JSON encoder;
- emitting the internal `resources` map or inventing a duplicate
  `ExecutionPlanModel`, schema, diagnostic envelope, or action enum;
- hand-mapping plan fields separately in CLI, MCP, runtime API, and tests;
- copying `ReferenceProcessorResult.diagnostics` into output without accounting
  for its current aggregate duplication;
- treating the three domain plans as one published contract or claiming the
  CLI wrapper round-trips against a schema that does not exist;
- accepting manifest capabilities without both published-model and internal
  dataclass validation, or ignoring an unresolved realization envelope;
- recompiling through a second CLI pipeline, bypassing scenario instantiation,
  or changing planner ordering for prettier JSON;
- importing live runtime/control-plane APIs for a read-only inspection command;
- writing plans, snapshots, caches, or lockfiles as a side effect;
- printing banners, warnings, progress, tracebacks, or error prose on stdout;
- leaking source/parameter/manifest values through exceptions or logs;
- editing published schemas merely to make Python serialization convenient;
- placing implementation logic in the legacy `aces.*` compatibility tree.

## Non-Goals

- Applying, provisioning, reconciling, or otherwise executing the plan.
- Adding authentication, authorization, control-plane APIs, persistence,
  telemetry, or backend discovery.
- Adding a published composite execution-plan contract, changing the three
  published plan schemas, or changing planner semantics/diagnostic ownership.
- Adding snapshot input, parameter/profile CLI syntax, YAML output, output-file
  writes, or backend runtime configuration beyond the issue's stated surface.
- Treating inspection output as run provenance, backend-conformance evidence,
  or proof that a live target can realize the plan.
- Implementing any command, serializer, manifest loader, policy change, or test
  in this preflight.
