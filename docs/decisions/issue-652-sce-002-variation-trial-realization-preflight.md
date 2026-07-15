# Issue 652 SCE-002 Variation And Trial-Realization Preflight

Date: 2026-07-15

Issue: #652.

Requirement: SCE-002.

This note fixes the architecture boundary for scenario-family variation and
deterministic trial realization before implementation. It is guidance only: it
does not add SDL syntax, contracts, schemas, generators, schedulers, runtime
fact behavior, persistence, or scenario content.

## Binding Authority And Current Gaps

- ADR-036 owns package boundaries. `aces_sdl` owns SDL composition,
  instantiation, and language semantics; `aces_processor` owns deterministic
  compilation, admission, and planning; `aces_runtime` owns live execution;
  `aces_contracts` owns portable cross-package DTOs. Authoring adapters and
  backends must not acquire parallel semantics.
- ADR-053 makes module composition typed, trusted, deterministic, and complete
  before downstream selection. ADR-076 keeps canonical declaration identities
  independent of source layout. ADR-078 requires closed, disjoint authoring,
  expanded, instantiated, and snapshot forms.
- SDL `Variable`, `${name}`, `instantiate_scenario()`,
  `InstantiationProvenance`, and the instantiated snapshot already own scalar
  parameter binding. SCE-002 must extend that path rather than add a template
  language or a second binder.
- ADR-055/068/074 and `ExperimentSpecModel`, `ExperimentRunPlanModel`,
  `ExperimentRunAllocationPlanModel`, `ExperimentStudyFactorModel`,
  `ExperimentParameterModel`, `ExperimentStochasticControlModel`,
  `ExperimentRunModel`, and `ExperimentStudyModel` already own experiment
  intent, factors, allocation, stochastic-control disclosure, archival runs,
  and study analysis.
- ADR-065 makes `experiment-run-v1` the archival provenance join point. One
  executed trial is one run record; a planned-trial artifact must not become a
  second archival run identity or provenance graph.
- ADR-070 and `aces_contracts.realization_envelope` supply reusable bounded
  domain descriptors and backend membership/subsumption semantics. A scenario
  validity domain, an experiment selection policy, and a backend realizability
  envelope are nevertheless three different authorities. ADR-070 remains
  `proposed`; #652 must not silently treat its status as accepted or broaden its
  expression fragment without an explicit decision.
- The existing experiment fields are not yet an executable randomization
  contract. `allocation_method`, `randomization_unit`, `replication_policy`,
  and stopping rules are descriptive strings;
  `ExperimentStochasticControlModel` does not define a generator, stream
  derivation, or draw semantics. `WitnessPolicy.seed` explicitly records a
  basis but introduces no randomness. None of these may be treated as a
  schedule-independent trial compiler by convention.

A focused #652 architecture decision must make the choices below normative
before follow-on contract or implementation work. It should amend ADR-068 and
ADR-074 where planned run identity and admitted-plan input semantics are
clarified, and reconcile ADR-070's status rather than duplicate it.

## One Pipeline And One Authority Per Boundary

| Boundary | Named authority | Input | Immutable output | Provenance rule |
| --- | --- | --- | --- | --- |
| Module composition | `aces_sdl.composition` and `module_registry` | Root SDL plus locked/trusted imports | `ExpandedScenario` with typed expansion provenance | Preserve declared import order, namespaces, module identities, checkout-independent sources, digests, exports, signer identity, and resolved module bindings per ADR-078. |
| Scenario-family declaration | SDL normative prose/schema/model and semantic validator | Composed authored scenario with named bounded variation points | Semantically valid expanded scenario family | Variation-point ids are stable canonical symbols; imported ids are namespace-qualified during composition; selected values never rename declarations. |
| Experiment design | `experiment-authoring-input-v1` and existing experiment-core models | Task/scenario-family refs, factors, allocation, typed selection and stochastic policies | Closed `ExperimentSpecModel` authoring artifact | Bind every factor/policy target to a declared variation-point id and pin referenced artifact identities/versions/digests where the existing ref model permits. Do not copy SDL declarations into the experiment document. |
| Trial-set compilation and admission | `aces_processor`, using neutral DTOs from `aces_contracts` | Admitted experiment spec, composed family, task, apparatus intent/manifests/envelopes, and explicit compiler/RNG profiles | One closed, canonical, immutable admitted trial-plan artifact | Record all input refs/digests, compiler profile, RNG/stream profile, logical trial coordinates, selected bindings, factor assignments, apparatus/envelope bindings, and bounded admission diagnostics. No plan is emitted when any entry is impossible, invalid, or unrealizable against its selected apparatus. |
| Trial realization | `aces_processor` orchestration over public `aces_sdl` APIs | One admitted plan entry plus the exact composed family it pins | Admitted `InstantiatedScenario`, canonical snapshot, then existing compiled runtime model/plans | Apply only plan-recorded structural selections and scalar bindings, call ordinary `instantiate_scenario()`/`admit_instantiated_scenario()`, and preserve selection-to-instantiation provenance. No private binder or validation bypass may mint a result. |
| Runtime fact binding | `aces_runtime` over typed neutral fact DTOs and compiled late-binding slots | Admitted compiled artifact, authorized observations/secret references | Run-local bound operation/action input plus fact-binding provenance | Facts may fill only explicitly declared late-bound sinks. Source, type, scope, freshness, sensitivity, and evidence/provenance refs are recorded; raw secrets are not. Facts cannot alter plan identity, factors, topology, structural choice, or stochastic streams. |
| Backend realization and scheduling | Existing planner/runtime/backend protocols; scheduler is an external consumer | Admitted per-trial compiled plans and selected apparatus bindings | Existing operation receipts/status, runtime snapshots, and realization disclosures | Planner applies realization-envelope membership and manifest capability checks. A scheduler may place, delay, pause, or retry admitted work under policy, but cannot select or resample scenario meaning. Backend refusal or availability change is a failure/deviation, not permission to choose another trial. |
| Archival provenance | `ExperimentRunModel`, `ExperimentStudyModel`, and existing cross-artifact validators | Sealed execution/evidence plus the admitted plan/snapshot refs | One run per executed trial and one study/allocation record | The planned run id becomes the archival `run_id` if execution starts. Runs carry actual parameter/stochastic/apparatus facts, snapshot identity, realized-form disclosures, evidence, deviations, and lineage to the plan/spec. Studies retain factor/allocation meaning. |

The admitted trial plan is an execution-intent artifact, not a scheduler queue,
live operation record, run, study, or apparatus observation. Its per-entry id is
a preallocated run identity under a versioned identity profile, not a second
kind of archival trial id. An idempotent transport retry before execution may
reuse it; a genuine re-execution after execution starts requires a newly
admitted run identity and produces a distinct run record.

## Variation And Reproducibility Guardrails

- Reuse the closed `DomainDescriptor` primitives where their value semantics
  fit: exact values, finite enums, booleans, bounded numeric intervals,
  governed references, and acyclic products. Keep SDL `Variable` as the scalar
  substitution carrier. Do not fork value typing or membership rules.
- Scenario-family structure needs a closed discriminated variation-point
  family, not JSON Patch or callbacks. The admitted kinds may cover one-of
  alternatives, bounded subsets, constrained order, and logical timing in
  addition to scalar/reference binding. Every alternative is declared,
  bounded, addressable, and independently semantically valid when selected.
- Composition resolves the complete declaration graph before selection.
  Selection may choose among declared members but may not import a new module,
  query an external catalog, execute code, create declaration keys from values,
  or mutate arbitrary JSON paths.
- Logical attack order and scenario timing are scenario/trial semantics.
  Worker launch order, queue latency, host wall time, retry backoff, and batch
  placement are scheduler/apparatus facts and cannot satisfy those variation
  points.
- Backend realizability cannot take authority from experiment selection. First
  validate a selection against the scenario-family domain; then prove the
  selected instance/requested family is within the selected backend envelope.
  An unrealizable point fails admission. Do not silently clamp, substitute,
  drop, or resample it.
- A mandatory random-stream profile must name the generator algorithm and
  version, seed encoding, canonical input encoding, semantic stream-address
  derivation, and distribution/sampling transformations. A seed alone is not a
  replay claim.
- Stream addresses derive from immutable semantic coordinates such as the
  experiment/spec identity, logical trial coordinate, variation-point or
  policy id, and draw purpose. They must never include worker id, process id,
  thread id, host, wall time, map iteration order, completion order, or retry
  count.
- Each concern receives an independent derived stream. Adding a draw for one
  variation point must not perturb another point's result. Serial, parallel,
  reversed-worker, and different-batch executions of the same admitted inputs
  must produce byte-identical trial plans.
- Canonical map traversal is by canonical identifier. Semantically ordered SDL
  lists retain their declared/selected order; a serializer must not sort away a
  meaningful order to manufacture determinism.
- Failure is deterministic and fail-closed. Constraint exhaustion, empty
  subset/order domains, invalid alternatives, duplicate coordinates, and
  apparatus mismatch produce bounded diagnostics and no admitted plan. A
  concurrency race or retry must not advance or replace a stream.

## Required Incumbents And Cross-Cutting Reuse

- **Normative authority and publication:** ADR-009/019/061,
  `specs/authority/authority-boundary.yaml`, `contracts/schemas/`,
  `contracts/fixtures/`, `contracts/schema-publication-manifest.json`,
  `schema_bundle()`, `tools/generate_contract_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`, and
  `tools/check_json_artifacts.py`. Portable trial-plan or fact contracts use
  `ContractModel(extra="forbid")`, generated parity, positive/negative fixtures,
  and `x-aces-invariants` for cross-artifact rules.
- **SDL ingress and phases:** `load_sdl_yaml`, source and composition budgets,
  duplicate/mapping-key checks, `Scenario`, `ExpandedScenario`,
  `InstantiatedScenario`, `SemanticValidator`, `instantiate_scenario()`,
  `admit_instantiated_scenario()`, `InstantiationProvenance`, RFC 8785/JCS
  snapshot canonicalization, and `SDLParseError` / `SDLValidationError` /
  `SDLInstantiationError`.
- **Composition supply chain:** `ImportDecl`, `ModuleDescriptor`,
  `resolve_import()`, path confinement, cycle/collision checks, lock and digest
  pins, export hashes, trust policy, signature verification, and bounded OCI
  extraction. A trial compiler consumes verified expansion provenance; it does
  not resolve imports itself.
- **Experiment semantics:** the existing authoring-input, task, apparatus,
  parameter, stochastic-control, factor, allocation, run, study, traceability,
  evidence, and realized-form models plus
  `validate_experiment_run_against_task()` and
  `validate_experiment_study_against_tasks_and_runs()`. Extend these owning
  contracts with typed children where needed; do not add parallel task,
  allocation, parameter, run, or study DTOs.
- **Processing and realization:** `aces_processor.compiler`, planner capability
  checks, manifests, `RuntimeModel`, typed plan DTOs, `Diagnostic`/`Severity`,
  and realization-envelope `member()`/`subsumes()`. The conformance
  `witness()` helper may share domain primitives but is not the experiment RNG
  or allocation engine.
- **Runtime, persistence, and observation:** existing backend protocols,
  `OperationReceipt`, `OperationStatus`, `RuntimeSnapshot`,
  `ControlPlaneStore`, audit events, experiment evidence records, and run
  provenance. Live snapshots/operation details remain mutable control state;
  they are not a trial-plan store or archival fact ledger.
- **Workflow and tests:** ADR-014, `.ground-control.yaml`,
  `.gc/plan-rules.md`, `noxfile.py`, `SessionReporter`, package-boundary policy,
  `test_pipeline_determinism.py`, realization-envelope Hypothesis properties,
  SDL phase/schema fixtures, experiment-contract fixtures, runtime contract
  tests, and control-plane security tests. Add schedule-permutation and
  cross-process/hash-seed witnesses to these canonical suites rather than a
  second CI workflow.

## Security And Whole-Path Gates

1. **SDL source and composition gate.** Family input passes bounded
   `sdl-yaml/v1` decoding, safe YAML construction, duplicate/canonical-key and
   JSON-domain checks, closed models, module trust/lock/digest/signature checks,
   namespace rewriting, whole-scenario semantic validation, selection,
   instantiation, and concrete semantic revalidation. No later layer may accept
   raw SDL dictionaries or skip these gates.
2. **Experiment/config shape gate.** Experiment and admitted-plan inputs pass
   closed `ContractModel`/published-schema validation plus owning cross-artifact
   validators. `parse_experiment_spec()` currently uses `yaml.safe_load`, and
   the MCP wrapper adds a 64 KiB limit, but the loader has no SDL-equivalent
   duplicate-key/source-profile gate and renders raw Pydantic/YAML error text.
   New remote or execution-facing SCE ingress must not inherit that leakage;
   either admit JSON/model artifacts after a bounded parser or harden the one
   canonical experiment loader rather than add another loader.
3. **Authentication and authorization gate.** No new HTTP endpoint is required
   for these contracts. Any later compile/admit/execute or fact-read endpoint
   must reuse `ControlPlaneSecurityConfig.strict_defaults()`, bearer or
   verified-proxy identity, operator/backend/auditor role checks, target scope,
   request-size guards, idempotency keys/fingerprints, and append-only audit
   events. Artifact dereference and secret resolution are separately authorized
   reads, not implied by permission to read a plan summary.
4. **Secret-handling gate.** Reuse `ExperimentParameterModel` redaction rules,
   SDL `redacted`/`operator_secret` omission validators, ADR-056/057, artifact
   sensitivity, and evidence redaction/loss disclosure. Secret variation values
   are references only and cannot be factor levels, condition-assignment values,
   random seeds, identity material, canonical digests, portable binding values,
   plan entries, fixtures, or diagnostics. Resolve a secret reference only at
   its authorized run-local sink.
5. **Environment/config binding gate.** No ambient environment variable,
   process-global RNG, worker-local config, backend default, mutable parameter
   store, or hidden fact source may affect selection. If an environment value is
   desired scenario state, it uses the existing typed runtime-environment shape
   and sensitivity/origin validators; if discovered at runtime, it uses an
   explicit typed late-binding slot and cannot enter scenario identity.
6. **OS/process exposure gate.** Keep selection and binding in-process over
   typed DTOs or bounded files/stdin. Never put credentials, parameter maps,
   fact values, tokens, raw plans, or secret refs in process argv; never use
   `shell=True` or interpolation. Fixed-argv determinism witnesses may expose
   only safe paths/profile ids and canonical digests.
7. **Backend admission gate.** Existing manifest authority, processor/backend
   compatibility, capability profiles, realization-envelope membership or
   subsumption, typed planning diagnostics, and target conformance all remain
   mandatory. A successful SDL selection is not proof of deployability, and a
   backend default is not an experiment selection.
8. **Error-envelope gate.** Structural failures remain at their owning parser
   or contract boundary; SDL binding failures use the existing SDL exceptions;
   processor admission/planning uses addressed `Diagnostic` values; HTTP keeps
   its redacted 500 envelope. Report codes, stages, safe canonical paths, ids,
   counts, and domain kinds only. Never render supplied/selected values,
   allowed domains, parameter/fact maps, rejected documents, raw Pydantic
   inputs, backend objects, environment dumps, or tracebacks.
9. **Logging/observability gate.** Reuse module-local logging and existing
   operation/audit reporting. Log only safe ids, digests, profile versions,
   counts, stage outcomes, and durations. Random draws, secret/fact values, raw
   bindings, scenarios, plans, and evidence bodies are not telemetry. A run's
   inspectable scientific record remains the experiment provenance/evidence
   graph, not logs.
10. **Persistence/distribution gate.** The admitted plan is a sealed portable
    artifact identified by canonical digest. Do not place it or its bindings in
    `RuntimeSnapshot.metadata`, `ControlPlaneOperationRecord.details`, an audit
    blob, tags, or a new mutable parameter database. Runtime state uses
    `ControlPlaneStore`; archival outcomes use run/study/evidence contracts. A
    future artifact service must preserve immutable bytes/digests and reuse the
    control-plane security patterns without turning the per-target store into an
    experiment repository.

## Extensibility Seam

The required seam is a versioned pair of closed profiles:

- a variation-point/selection-policy discriminated union whose domain members
  are addressed by stable canonical ids; and
- a random-stream profile whose semantic address and generator/draw versions
  are explicit inputs to trial-set compilation.

A new bounded variation kind, allocation policy, or generator version extends
one owning union/profile and its validator/fixture/property-test dispatch. It
does not require editing every scenario, backend, scheduler, or run schema.
Generator changes mint a new profile and provenance value; they never silently
change the output of an existing profile. Runtime facts have a separate seam:
typed source and sink kinds with sensitivity/freshness/evidence metadata. Adding
a new fact source must not widen which compiled sinks are late-bindable.

## Gotchas And Anti-Patterns

Avoid:

- calling `random`, `secrets`, UUID, wall time, hash iteration, or a backend
  callback during semantic trial selection without the governed stream profile;
- treating a common seed as sufficient replay provenance or sharing one mutable
  RNG across trials/variation points;
- using `WitnessPolicy.seed` or realization-envelope witness generation as the
  trial randomizer;
- free-text allocation/randomization fields driving execution directly;
- resampling after backend rejection, worker failure, timeout, or resource
  contention;
- arbitrary templates, JSON/YAML patches, callbacks, expressions, external
  queries, unbounded distributions, or a shared mutable parameter/fact store;
- generating declaration ids from selected values or putting selections in
  source paths, namespaces, compiled addresses, or task identity;
- letting runtime observations retroactively alter a trial's factors, run id,
  scenario snapshot, compiled topology, structural alternatives, or streams;
- putting experiment concepts in a new SDL root object, or SDL declarations in
  a duplicate experiment schema;
- treating trial plans as runs, scheduler jobs, operation receipts, runtime
  snapshots, studies, or replay guarantees;
- adding a duplicate schema registry, loader, validator, exception hierarchy,
  diagnostic envelope, persistence repository, logger, audit stream, or CI
  workflow; and
- exposing raw parameters/facts through current `ExperimentSpecValidationError`
  rendering, MCP summaries, HTTP errors, logs, fixtures, argv, or provenance.

## Non-Goals And Implementation Boundaries

- This preflight does not implement SCE-002, modify schemas/models, choose a
  concrete PRNG, define scenario content, or publish an implementation plan.
- SCE-002 does not create an experiment scheduler, batch executor, worker pool,
  persistence service, HTTP API, secret manager, general expression language,
  optimizer, adaptive-difficulty policy, CTI generator, or analysis engine.
- Adaptive interventions are later run events with their own policy and
  provenance. They do not rewrite the admitted baseline trial. A derived
  follow-up trial requires a new admitted identity linked to its source run.
- SCE-004 may consume typed late-bound facts and goal/tool contracts, but it
  cannot make tool choice or observations a hidden scenario-family selector.
- SCE-001/SCE-005 may propose bounded candidate scenarios or coverage targets;
  candidates enter through ordinary authoring, trust, validation, and admission
  gates. CTI is not runtime selection authority.
- SCE-006/APTL may consume admitted plans and schedule isolated executions; it
  does not own composition, randomization, instantiation, trial identity, or
  archival run/study semantics.
- Exact replay from a seed alone, behavioral equivalence across backends,
  artifact availability, and recreation of hidden backend state remain
  explicitly unsupported claims.
