# Issue #725 — Objective Truth Semantics Preflight

Date: 2026-07-12

Issue: #725.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This is implementation guidance only. It does not define new SDL syntax,
publish a schema, change runtime behavior, or provide an implementation plan.

## Problem Boundary

The current `Condition` has four meanings that must be separated:

1. `aces_sdl.conditions.Condition` is an executable command-plus-schedule or a
   package `Source`.
2. `nodes.*.conditions` turns that template into a node-bound evaluation
   resource (`ConditionBinding`).
3. events, agent starting state, workflow predicates, and objective success
   treat the same name as an observable state claim.
4. `EvaluationResultContract.passed` reports a backend-produced Boolean without
   preserving the proposition, evidence adequacy, or inability to decide it.

An executable check is not a proposition. Exit status, package identity,
polling cadence, retries, and environment are realization details; none states
what must be true. The implementation must establish backend-neutral truth
before selecting or executing a probe.

## Semantic Model And Boundaries

Use one canonical proposition model. Do not create separate condition,
workflow-predicate, objective-predicate, and backend-predicate languages.

- A **proposition** is a named, declarative, side-effect-free expression over a
  governed stable SDL address/property or an evidence-bearing observation. Its
  inspectable meaning includes the typed subject/property, predicate family and
  operator, expected value or bound, units where applicable, quantification,
  and evidence admissibility. It contains no command, package, callback,
  credential, query language, polling policy, or backend id.
- An **assertion** is a typed use of a proposition. It adds semantic role
  (`precondition`, `invariant`, or `postcondition`), expected polarity, scope,
  and governed temporal/evidence context. Keep this a use-site contract over a
  proposition, not a second expression language. A negative assertion expects
  the proposition to be false; it is not a special probe kind and must not turn
  unknown into true.
- A **probe binding** is a capability-checked realization artifact that binds a
  proposition to an executable observation mechanism. It carries backend,
  implementation/artifact identity, version or digest, bound target, supported
  predicate/observation/time capabilities, and realization/evidence
  provenance. It does not change proposition meaning.
- A **truth result** is a portable claim about one proposition evaluation. It
  carries truth value, proposition and assertion identities, observation and
  clock context, binding provenance, evidence refs, and loss/redaction or
  limitation disclosure. It is not a score, reward, operation status, or
  evaluator lifecycle status.

The proposition expression must be a closed, discriminated typed union, not a
universal `operator + Any` tuple. Predicate families should bind to governed
property types and add only their meaningful operators. Subjects resolve via
the existing canonical SDL address/reference machinery. Do not admit JSONPath,
JMESPath, arbitrary Python, shell, regex-as-policy, or backend-native field
paths as portable semantics. Quantifiers operate over an explicitly resolved,
finite subject set; thresholds use the owning property's type and unit rather
than untyped strings.

Declared-state propositions and observed-state propositions are distinct.
Static SDL facts may be decided from an admitted instantiated scenario.
Runtime facts require an observation contract and evidence basis. An authored
`evidence_requirement` remains capture intent, not proof; a truth result must
cite the captured evidence or observation record that actually supports it.

## Assertion And Composition Semantics

- Preconditions determine whether the scoped operation/objective is applicable
  at its governed start boundary. A false, unknown, or unsupported precondition
  is not successful execution and must fail closed; it must not be rewritten as
  objective failure without preserving the applicability result.
- Invariants are evaluated over a governed window. Sampling a point does not
  prove an interval invariant unless the proposition's observation contract
  declares the sampling/coverage rule and the evidence satisfies it.
- Postconditions are evaluated at the governed completion boundary. Command
  completion or operation success is not proof of a postcondition.
- Objective success composes assertion results, not probe exit codes. Its
  expression must reference declared invariant/postcondition assertions and use
  one shared composition implementation also consumed by workflows where the
  same truth algebra applies.

The portable truth domain is exactly `true`, `false`, `unknown`, and
`unsupported` for this issue:

- `unknown`: the proposition is supported in principle, but available evidence
  cannot decide it (missing, stale, partial, conflicting, redacted, lossy beyond
  the declared bound, or probe failure).
- `unsupported`: the selected backend/binding cannot realize the required
  predicate, observation strength, evidence basis, or governed temporal
  guarantee.

Negation swaps only `true` and `false`; it preserves `unknown` and
`unsupported`. For `all_of`, any `false` is decisive and all `true` yields
`true`; otherwise `unsupported` dominates `unknown`. For `any_of`, any `true`
is decisive and all `false` yields `false`; otherwise `unsupported` dominates
`unknown`. Empty composition is invalid. Unknown or unsupported never counts
as objective success. This is truth composition, not arithmetic scoring.

Lossy or partial evidence may produce `true`/`false` only when the proposition
declares an admissible loss/uncertainty bound and the evidence proves it stayed
within that bound. Otherwise it produces `unknown`. Capability absence produces
`unsupported`; ordinary absence of an observation from a capable mechanism is
`unknown`, not `false`. Contradictory observations remain `unknown` unless a
governed conflict/aggregation rule decides them.

## Time And Evidence Guardrails

Objective `window` references already have one name-level authority:
`aces_sdl.semantics.objectives.analyze_objective_window`. Reuse it for
story/script/event/workflow scope and dependency refresh; do not duplicate its
resolution rules in proposition evaluation.

Those references do not by themselves define clock time. Any cadence,
duration, freshness, deadline, dwell, or interval claim must use the governed
time concepts established by ADR-022 and the existing typed time carriers:
time domain, clock authority, event/boundary identity, and any disclosed weaker
or unsupported guarantee. Reuse `ParticipantTimeDomain`, participant temporal
contracts/runtime contexts, and `ExperimentClockContextModel` only within
their owning boundaries; do not pretend either is a general SDL clock. If no
governed carrier exists for a desired proposition window, leave that form
unsupported until the time model adds one. `Condition.interval`, backend wall
clock, host monotonic time, evaluator timestamps, and polling retries are never
portable temporal semantics.

Evidence ownership remains governed by ADR-064/066 and
`specs/sdl/observability-and-evidence.md`: SDL evidence requirements express
capture intent, experiment evidence records carry captured evidence, and
derived measures/evaluator outputs remain separate. Truth-result provenance
may reference these carriers but must not copy raw evidence into diagnostics,
snapshots, audit details, or free-form result `details`.

## Migration Of Current Conditions

Migration must be explicit and loss-aware:

- `Condition.command`, `interval`, `timeout`, `retries`, `start_period`, and
  `environment` map only to a legacy command probe binding and its execution
  policy. They do not define a proposition.
- `Condition.source` maps only to a package/artifact-backed probe binding. The
  existing `Source.name/version` is identity, not integrity or semantic proof;
  executable probe artifacts must also pass the applicable ADR-071 reusable
  asset trust/integrity policy and record verified provenance.
- A migrator cannot infer expected truth, target property, polarity, threshold,
  quantifier, temporal semantics, or evidence adequacy from arbitrary command
  text or a package name. It must require an explicit proposition/assertion
  mapping or emit a bounded migration error. A compatibility adapter may map
  zero/nonzero exit status as a disclosed legacy observation, but may not claim
  backend-neutral semantic equivalence.
- Objective `success.conditions`, workflow predicate conditions, event
  conditions, and agent `starting_conditions` migrate to assertion/proposition
  references according to their owning role. `nodes.*.conditions` migrates to
  probe placement/binding. These consumers must not continue sharing one
  ambiguous namespace silently.
- Preserve existing identifiers through an explicit migration ledger where the
  mapping is one-to-one. Ambiguous, lossy, or unmapped entries fail closed; do
  not first-match or silently drop them. Apply the versioning/deprecation rules
  in ADR-075 and `specs/evolution/versioning-deprecation-and-migration.md`.

## Canonical Incumbents To Reuse

- **Authority and publication:** ADR-009/019/061, `specs/authority/authority-boundary.yaml`,
  `contracts/schemas/`, `contracts/schema-publication-manifest.json`,
  `schema_bundle()`, `tools/check_schema_publication.py`, and
  `tools/check_generated_schemas.py`. Published schemas are the normative
  machine-readable authority; generator parity is a compatibility proof.
- **Concept authority:** ADR-012/062, the `observables` concept family,
  `scenario-condition` reference model, controlled-vocabulary validation,
  semantic profiles, and manifest `concept_bindings`. Evolve the existing
  observable reference model; do not publish a competing concept catalog.
- **SDL ingress and phases:** `load_sdl_yaml`, `sdl-yaml/v1` limits and mapping
  checks, `SDLModel(extra="forbid")`, canonical identifiers/addresses,
  variables, composition, `instantiate_scenario`, instantiated-artifact
  admission, and post-instantiation semantic revalidation.
- **Shared semantics:** `SemanticValidator`, the named-reference index,
  `analyze_objective_semantics`, `partition_objective_dependencies`,
  `analyze_objective_window`, and the existing validator/compiler agreement
  pattern. Extend this pure semantic seam; do not add validator-only or
  backend-only truth rules.
- **Processor/runtime contracts:** `compile_runtime_model`, `ObjectiveRuntime`,
  `ConditionBinding` migration paths, canonical evaluation addresses,
  `EvaluationExecutionContract`, evaluation history/state validation,
  `Diagnostic`, `OperationStatus`, `OperationReceipt`, and `RuntimeSnapshot`.
  Truth results need a typed carrier; they must not be hidden in `spec`,
  `metadata`, `details`, tags, or log text. Lifecycle `ready/failed` remains
  orthogonal to truth `true/false/unknown/unsupported`.
- **Backend capability and realization:** `EvaluatorCapabilities`,
  `BackendManifestV2Model`, `backend_manifest_payload()`, governed capability
  scopes, realization-support diagnostics/disclosure, and realization
  provenance. Extend the evaluator capability surface with governed predicate,
  observation-strength, evidence, and time dimensions rather than adding a
  proposition-specific manifest or backend callback registry.
- **Evidence and trust:** `EvidenceRequirement`, experiment capture/evidence
  contracts, evidence refs and checksums, redaction/loss disclosure, ADR-071's
  reusable-asset trust policy, and existing module/artifact digest/signature
  mechanisms where the asset family applies.
- **Errors and observability:** `SDLParseError`, `SDLValidationError`,
  `SDLInstantiationError`, collect-all semantic diagnostics, `Diagnostic`,
  control-plane audit summaries, and the redacted API exception handler. Do not
  introduce a proposition exception hierarchy or logging pipeline.
- **Tests and conformance:** the published valid/invalid fixture corpus,
  schema-independent fixture validation, semantic agreement tests,
  backend-manifest/conformance helpers, and runtime result-contract tests.

## Security And Cross-Cutting Layers

The intended design passes these layers and must satisfy each one:

1. **Source/parser gate:** propositions and assertions are inert structured
   data decoded through `load_sdl_yaml`; parsing, validation, language service,
   MCP, canonicalization, and compilation never execute a probe. Source limits,
   duplicate-key checks, canonical fields, and safe YAML construction remain in
   force.
2. **Closed shape and reference gate:** `SDLModel(extra="forbid")`, published
   schemas, portable identifiers, typed addresses, and `SemanticValidator`
   reject unknown fields, untyped operands, dangling/ambiguous refs, invalid
   operators for a property type, empty compositions, and assertion cycles.
3. **Instantiation/config gate:** existing variable typing, allowed-value
   constraints, substitution, unresolved-token rejection, and semantic
   revalidation apply. Do not add environment-variable or CLI binding for
   expected values, thresholds, commands, or credentials.
4. **Capability/admission gate:** backend manifests must declare support for the
   required predicate family, observation/evidence strength, and temporal
   guarantee. Planner/runtime admission returns existing structured diagnostics
   for unsupported realization; it never approximates silently.
5. **Executable artifact gate:** probe packages/images/scripts are untrusted
   realization inputs. Apply existing allowlist, digest, signature, source-size,
   and trust-policy mechanisms as applicable. Never treat `Source.name` or a
   successful import as proof of safe execution.
6. **OS/process gate:** no secret, bearer token, credential, private key, raw
   environment value, or hidden truth may enter command text, process argv,
   filenames, diagnostics, or logs. New adapters use fixed argv and no shell
   where possible, bounded time/output/resource limits, a controlled working
   directory/environment, least privilege, and explicit output redaction. The
   legacy command compatibility path must be policy-gated and must not become
   the portable probe contract.
7. **Runtime/API gate:** any live truth/probe operation reuses
   `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy
   identity, target-bound role authorization, request-size limits, idempotency
   fingerprints, audit records, and the existing redacted internal-error
   response. A backend-native exception or probe stdout/stderr is never the
   public error envelope.
8. **Persistence/evidence gate:** persist typed truth, binding provenance,
   digests, clock context, evidence refs, and bounded loss summaries through
   versioned contracts. Do not persist raw command output, credentials, host
   paths, backend-native objects, complete evidence payloads, or full
   tracebacks in snapshots, result `details`, audit records, or fixtures.

## Extensibility Seam

The required seam is a pure proposition analysis/evaluation contract
parameterized by:

- governed predicate family and property type;
- canonical subject resolver;
- quantifier/threshold semantics;
- assertion role and polarity;
- truth algebra/composition operator;
- governed temporal-context resolver; and
- evidence-admissibility and observation-strength policy.

The compiler lowers the same analyzed proposition into a capability request;
backend adapters supply versioned probe bindings and observations against that
request. Adding one reasonable future predicate family, observation carrier,
or time-domain carrier should add a governed union member, capability term,
binding implementation, fixtures, and tests. It must not require edits to every
objective/workflow consumer or a new per-backend truth implementation.

## Required Fixture Semantics

The contract corpus must prove, independently of one backend implementation:

- positive and negative assertions over the same typed proposition;
- ambiguous/insufficient evidence yielding `unknown` rather than false;
- absent backend capability yielding `unsupported` rather than unknown;
- lossy/redacted evidence staying unknown unless an admitted bound decides it;
- composition and negation over all four truth values;
- two materially different probe bindings producing equivalent truth results
  for the same proposition, with distinct binding provenance; and
- a backend that reports `true`/`false` without the required evidence,
  capability, clock context, or binding provenance being rejected.

## Gotchas And Anti-Patterns

Avoid:

- renaming `Condition` to `Predicate` while leaving command/source fields in it;
- treating command exit zero, package success, HTTP 2xx, or probe completion as
  portable truth without an explicit typed mapping;
- treating missing evidence, timeout, redaction, unsupported capability, and
  false as the same value;
- Boolean negation that turns unknown/unsupported into success;
- reusing participant action preconditions as objective assertions: they own
  action applicability and support/evidence refs, not general state logic;
- reusing evaluator `passed`, score, reward, derived measure, operation
  success, or workflow step outcome as the proposition truth model;
- using objective-window membership, polling interval, timestamps, or host
  clocks as an implicit temporal model;
- universal string operators, free-form property paths, opaque constraint
  bags, backend query languages, or arbitrary callbacks in SDL;
- letting a backend author or rewrite proposition meaning while binding it;
- duplicating schemas, reference resolvers, truth tables, capability catalogs,
  validators, exceptions, diagnostics, audit logs, stores, or conformance
  runners; and
- leaking commands, environment values, evidence content, hidden truth,
  backend-native ids, host paths, stdout/stderr, or tracebacks through portable
  artifacts or errors.

## Non-Goals And Implementation Boundaries

- This preflight does not implement #725, choose final serialized field names,
  publish a schema/ADR/formal spec, migrate examples, or change runtime output.
- It does not add a general rules engine, policy engine, CEP/stream processor,
  temporal logic language, solver, query language, remote probe service, or
  plugin system.
- It does not define statistical grading, confidence intervals, reward,
  leaderboard scores, derived measures, or experiment analysis. Those remain
  in the experiment/evaluator plane.
- It does not collapse world state, participant-visible observation, authored
  capture intent, captured evidence, or derived analysis into one truth store.
- It does not make participant action preconditions or workflow step outcomes
  aliases for objective assertions.
- It does not authorize arbitrary command execution or make legacy conditions
  semantically portable. Legacy compatibility is a disclosed migration aid,
  not the target architecture.
- SDL semantics stay in `aces_sdl`, neutral portable DTOs in `aces_contracts`,
  compilation/planning in `aces_processor`, live admission/state in
  `aces_runtime`, backend declarations in `aces_backend_protocols`, and concrete
  probe execution in backend adapters. No implementation logic belongs under
  compatibility-only `implementations/python/src/aces/`.
