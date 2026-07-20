# Issue 791 SCE-004 Runtime Fact Bindings Preflight

Date: 2026-07-20

Issue: #791.

Requirements: SCE-002 and SCE-004.

This note records architecture guardrails for typed runtime fact bindings used
by goal-oriented, tool-flexible scenario steps. It is implementation guidance
only: it does not add SDL syntax, schemas, generated artifacts, runtime
storage, API routes, fact producers, fixtures, tests, or an implementation
plan.

## Binding Decisions

- Scenario workflow steps remain declarative control over objectives,
  predicates, retries, calls, joins, and success/failure transitions. They do
  not become command runners, tool scripts, prompts, backend recipes, or
  execution playbooks.
- SCE-004 is satisfied through goals, success criteria, action contracts,
  participant tool-affordance semantics, and explicit late-bound inputs. It is
  not satisfied by storing hardcoded commands in a different field name.
- Runtime facts are run-local observations or governed derived values. They may
  fill only compiled late-bound sinks that were explicitly admitted before
  execution. They cannot rewrite SDL variables, variation choices, trial
  factors, topology, compiled workflow structure, snapshot identity, run id, or
  random streams.
- Fact declaration, fact value/version, visibility projection, and
  action-dispatch binding are separate concepts. A fact's existence is not a
  participant disclosure; disclosure is not action authority; action authority
  is not support; support is not execution success.
- Tool freedom belongs at the participant decision/action layer. Implementations
  may choose their own tools and techniques, but every action attempt must still
  resolve to governed action-contract and observation-boundary addresses, pass
  the existing admission gates, and emit provenance for the fact versions used.
- Secret facts are references at the portable layer. Raw secret material may be
  resolved only at an authorized run-local sink and must not enter public plans,
  summaries, diagnostics, provenance summaries, logs, argv, or fixtures.

## Required Incumbents

Reuse these surfaces before adding anything new:

- **SDL workflow and objective authority:** ADR-006, ADR-078, ADR-079,
  `aces_sdl.orchestration.WorkflowStep`, `WorkflowPredicate`,
  `SemanticValidator._verify_workflows()`, proposition/assertion/objective
  semantics, `instantiate_scenario()`, and `admit_instantiated_scenario()`.
- **Scenario variation and phase boundaries:** ADR-084, the #652 preflight,
  `Variable`, `${...}` instantiation, `InstantiationProvenance`,
  canonical instantiated snapshots, and the rule that runtime facts fill only
  typed late-bound sinks rather than pre-run variables.
- **Participant tool and information-flow semantics:** ADR-083, ADR-085,
  the #294/#796 preflights, `ParticipantToolAffordanceRuntime`,
  `ParticipantActionContractRuntime`, `ParticipantObservationBoundaryRuntime`,
  `ParticipantBehaviorRuntime`, compiled view timelines, exposure policies,
  and participant-visible context/history/status view contracts.
- **Runtime admission and history:** `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`,
  `ParticipantControlMixin.admit_participant_action()`,
  `participant_action_binding_events()`, behavior-history validators,
  append-only runtime history checks, `RuntimeControlPlane`, operation
  receipts/statuses, `_call_backend_apply()`, `_call_backend_diagnostics()`,
  `RuntimeSnapshot`, `ControlPlaneStore`, and `AuditEvent`.
- **Contracts and schema publication:** `ContractModel(extra="forbid")`,
  `schema_bundle()`, `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json`,
  `tools/generate_contract_schemas.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  and `tools/check_json_artifacts.py`.
- **Evidence, provenance, and redaction:** ADR-056, ADR-057, ADR-064,
  ADR-065, ADR-066, `ExperimentEvidenceRecordModel`,
  `ExperimentRunTraceabilityModel`,
  `ExperimentRealizedFormDisclosureModel`,
  `ParticipantObservationEnvelopeModel`, `ParticipantContextViewModel`,
  `RealizationProvenanceEntry`, `Diagnostic`, and `Severity`.
- **Security and API posture:** `create_control_plane_app()`,
  `ControlPlaneSecurityConfig.strict_defaults()`, bearer/proxy identity checks,
  `ControlPlaneRole`, request-size guards, idempotency keys, request
  fingerprints, audit events, bounded 4xx details, and the redacted FastAPI
  internal-error envelope.
- **Repository workflow:** `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_semantic_coverage.py`,
  and `tools/verify_all.py`.

## Cross-Cutting Layers And Gates

- **SDL/source gate:** any authored sink declaration must enter through bounded
  safe YAML loading, closed SDL models, portable identifier rules, normal
  reference resolution, semantic validation, instantiation, and post-
  instantiation admission. Sinks are named by stable compiled addresses and
  local ids; `${...}` cannot create, rename, or retarget them.
- **Workflow/config-shape gate:** workflow steps may reference objectives,
  predicates, step state, retries, calls, and compensation using existing
  fields only. Do not add command, shell, tool, URL, environment, provider
  option, arbitrary parameter map, or hidden backend config to workflow steps.
- **Contract-shape gate:** portable fact, fact-version, sink, and binding
  payloads, if published, must be closed `ContractModel` contracts with
  generated schema parity, positive and negative fixtures, publication-manifest
  ledger entries, and `x-aces-invariants` for cross-artifact joins.
- **Typed binding gate:** a binding validates source fact type, sink type,
  scope, participant/episode/run identity, freshness, confidence or evidence
  basis, ambiguity, authority, sensitivity, and absence behavior before action
  dispatch. Missing, stale, ambiguous, unauthorized, unsupported, wrong-type,
  wrong-scope, or secret-value-unavailable cases fail closed with explicit
  dispositions.
- **Participant visibility gate:** participant-facing fact projection must pass
  the compiled observation boundary, view relation timeline, exposure policy,
  audience scope, markings, redaction policy, evidence/provenance basis, and
  ADR-085 policy/order point. Operator/auditor retrieval is not participant
  disclosure.
- **Action-admission gate:** a bound action input must still use compiled
  action-contract and observation-boundary addresses and pass
  `ParticipantActionAdmissionRequest` compatibility, exposure-policy checks,
  SEM-211 precondition/effect semantics, behavior-history emission, and runtime
  snapshot transition validation.
- **Authentication/authorization gate:** any future HTTP fact read, fact write,
  or bound-action dispatch route must reuse control-plane strict defaults,
  target-bound caller identity, read/mutating role separation, request-size
  limits, idempotency/fingerprint handling, and audit recording. Caller
  authorization, participant authority, sink authority, and secret dereference
  authority remain independent deny-first gates.
- **Secret-handling gate:** contracts and diagnostics carry safe refs, digests,
  classifications, redaction/loss state, and bounded summaries. They do not
  carry bearer tokens, passwords, private keys, raw secret values, hidden answer
  keys, prompts, rejected input bodies, backend objects, raw evidence payloads,
  or environment dumps.
- **OS/process exposure gate:** fact resolution and action dispatch must use
  typed in-process DTOs or bounded files/stdin as needed. Do not pass fact
  values, secret refs, credentials, prompts, parameter maps, raw observations,
  or policy bodies through process argv, shell interpolation, filenames, logs,
  stdout/stderr, or environment captures. Use fixed invocation shapes, bounded
  timeouts, controlled working directories, and no `shell=True` for adapters.
- **Error-envelope and logging gate:** expected validation/runtime failures use
  SDL errors, `Diagnostic` values, operation receipts/statuses, or bounded HTTP
  4xx details. Unexpected HTTP failures keep
  `{"detail":"internal server error"}`. Logs and audit carry safe ids, codes,
  counts, digests, profile versions, stage outcomes, and durations only.
- **Persistence gate:** if facts become durable runtime state, they need a
  first-class append-only run-local carrier with immutable version history.
  They must not be stored only in `RuntimeSnapshot.metadata`,
  `ControlPlaneOperationRecord.details`, audit details, backend DTOs, raw logs,
  tags, or a mutable global key/value store. Archival claims still join through
  experiment run/evidence/provenance contracts.
- **Package boundary gate:** SDL declarations stay in `aces_sdl`, compiled
  sinks in `aces_processor`, portable DTOs in `aces_contracts`, live binding
  and security in `aces_runtime`, backend realization in backend protocol
  packages, and conformance in `aces_conformance`. Do not add implementation
  logic to compatibility-only `implementations/python/src/aces/` or import
  `aces.*` from owning packages.

## Extensibility Seam

The required seam is the compiled late-bound sink plus typed fact source kind.
A sink should be parameterized by stable sink id, target compiled address,
expected value/reference type, allowed source/scope, participant/episode/run
scope, freshness policy, sensitivity policy, evidence/provenance expectation,
authorization basis, and absence disposition. A fact version should be
parameterized by source kind, scope, type, value-or-secret-reference posture,
freshness, confidence/evidence, sensitivity, visibility markings, and immutable
version/provenance identity.

The next likely variations are a new observation source, a secret-reference
provider, a derived fact, a participant-projected fact view, or another bound
action input type. Each should add one source/sink kind or governed policy term
and corresponding validators/fixtures. It should not require a new workflow
language, another `${...}` binder, a planner/tool-selection algorithm, a second
visibility taxonomy, or a generic mutable store.

## Gotchas And Anti-Patterns

Avoid:

- putting `command`, `shell`, `tool`, `browser`, `http-api`, `prompt`, URL,
  provider config, environment lookup, or executable snippets on workflow steps
  or fact bindings;
- treating a fact name, tool label, package, ATT&CK/CVE id, endpoint, account,
  interactive-access declaration, backend capability, or manifest expectation
  as an action contract;
- reusing SDL variables, instantiation provenance, experiment factors, random
  seeds, condition assignments, canonical ids, source paths, or snapshot
  digests for runtime facts;
- letting runtime observations choose variation points, resample a trial,
  change topology, retarget workflows, select apparatus, or alter identity;
- collapsing fact declaration, value version, projection, binding, admission,
  action result, observation, evidence, and archival run provenance into one
  DTO or `details` map;
- inferring participant visibility from operator/auditor API reads, global
  runtime state, hidden truth, future disclosures, backend reachability, or
  final outcome records;
- treating stale, missing, ambiguous, unauthorized, unsupported, unknown,
  withheld, redacted, and not-applicable as interchangeable;
- storing raw fact values, secret refs, allowed domains, rejected input, raw
  evidence, commands, stdout/stderr, environment dumps, backend-native object
  reprs, or tracebacks in diagnostics, audit, logs, fixtures, provenance
  summaries, or public API responses;
- adding duplicate schema registries, loaders, validators, reference
  resolvers, exception hierarchies, stores, audit streams, log formats,
  conformance workflows, or CI entry points; and
- hand-editing generated schemas or changing published schemas without the
  publication manifest, fixture, generator-parity, and compatibility gates.

## Non-Goals And Implementation Boundary

- This preflight does not implement SCE-004, #791, fact schemas, runtime
  storage, action dispatch, API routes, backends, fixtures, tests, or status
  updates.
- SCE-004 does not add a planner, tool-selection algorithm, shell/RPC runner,
  prompt protocol, external-agent API, credential broker, policy engine,
  workflow scheduler, mutable parameter store, global fact database, or new
  experiment randomizer.
- Runtime fact binding is not pre-run SDL instantiation, scenario variation,
  trial allocation, apparatus selection, evaluator scoring, objective truth,
  participant memory, hidden answer publication, or archival study analysis.
- Secret-reference handling does not mean secret disclosure. A raw secret may
  be resolved only at an authorized sink and remains outside portable plans,
  diagnostics, summaries, logs, fixtures, and provenance summaries.
- A successful fact binding records provenance for an input dispatch. It is not
  by itself proof that the chosen participant tool was exposed, that every
  action precondition was satisfied, that a backend executed the action, or
  that objective success was achieved.
