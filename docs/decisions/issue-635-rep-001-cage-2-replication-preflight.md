# Issue 635 REP-001 CAGE-2 Replication Architecture Preflight

Date: 2026-07-01

Issue: #635.

Requirement: REP-001.

This note records architecture guardrails for the REP-001 design work. It is
guidance only: it does not publish the accepted ADR or design record, author the
CAGE-2 SDL scenario, create `aces-adapters`, implement a CybORG adapter, add a
backend harness, or claim replication equivalence.

## Binding Sources

- ADR-001, ADR-002, ADR-004, ADR-008, ADR-020, ADR-022, ADR-054, ADR-060,
  ADR-066, and ADR-067 own SDL, runtime, participant, observation, and outcome
  semantics. CAGE-2 terms must map into those surfaces; they must not redefine
  them.
- ADR-009, ADR-012, ADR-019, ADR-061, and ADR-062 own normative artifact
  authority, schema publication, concept authority, controlled vocabularies, and
  governed extension discipline.
- ADR-036 owns Python package boundaries. Backends and adapters consume
  `aces_backend_protocols`, `aces_contracts`, `aces_runtime` public seams, and
  `aces_conformance`; core packages must not import concrete adapter packages.
- ADR-063 and the issue #197, #601, and #614 preflight notes define the
  concrete-backend portable-fact boundary: realization is a backend side effect;
  portable outputs are manifests, plans, snapshots, diagnostics, participant
  histories, evidence, and experiment records.
- ADR-064, ADR-065, ADR-066, and ADR-068 own experiment evidence, run
  provenance, plane separation, replication, and replay-claim boundaries.
- The upstream CAGE Challenge 2 repository and paper are source evidence for
  scenario facts, fixed-step episodes, red-agent variants, reward/scoring,
  turn order, and evaluation protocol. The REP-001 ADR must pin exact upstream
  repository commits or releases and cite the source paths it maps.
- `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, `noxfile.py`, and
  `tools/verify_all.py` remain the repository workflow and verification
  authority.

## Architecture Decisions

- REP-001 should produce an accepted ADR plus a design record, not code. The
  ADR decides architecture and boundaries; the design record carries the
  source-to-ACES mapping evidence, adapter protocol mapping, monorepo layout,
  equivalence criteria, and cross-repo workflow.
- The CAGE-2 to ACES SDL mapping must be a mapping ledger over pinned upstream
  facts. Each host, subnet, service, account, role, action, observation,
  turn-order rule, terminal condition, reward component, red-agent variant,
  randomization control, and score/evaluation fact must be mapped, explicitly
  declared out of scope, or loss-disclosed. Do not introduce CAGE-specific SDL
  syntax to make the mapping convenient.
- The CybORG adapter is a conformant simulation backend. It implements the
  existing `Provisioner`, `Orchestrator`, `Evaluator`, and `ParticipantRuntime`
  protocols through ACES contracts and manifests. It must not expose CybORG
  gym/PettingZoo tuples, native action ids, reward arrays, simulator objects, or
  backend-private state as portable ACES payloads.
- `sim_adapter_base` is an adapter-monorepo convenience package, not a new ACES
  semantic authority. It can factor simulator-driver plumbing, seed/clock
  controls, action/observation projection helpers, manifest helpers, and
  conformance harness utilities, but it must consume ACES contracts rather than
  fork protocols, schemas, diagnostics, fixtures, or conformance profiles.
- `aces-adapters` should be a co-located set of independent adapter projects.
  Each adapter owns its own dependency lockfile and virtual environment; the
  root may orchestrate CI but must not make adapters share one resolved
  dependency graph. Shared packages must be versioned and consumed like ordinary
  dependencies so a CybORG pin cannot constrain an unrelated adapter.
- The backend conformance harness in `aces-adapters` should invoke or wrap the
  existing ACES conformance runner and published backend profiles. It may add
  simulator-specific probes and seeded equivalence checks, but it must not
  maintain a second profile table, schema registry, fixture corpus, manifest
  renderer, exception hierarchy, or result envelope.
- Replication/equivalence is evidence over canonical artifacts: the same
  authored ACES SDL scenario must parse, validate, compile, plan, and execute
  through independent conformant backends with declared manifests and bounded
  stochastic controls. Success criteria belong in `experiment-study-v1`,
  `experiment-run-v1`, evidence records, derived measures, backend manifests,
  runtime snapshots, participant histories, and conformance reports, not in
  ad hoc notebook output or CI logs.
- Cross-repo work is issue-driven from ACES. The ACES REP-001 issue owns the
  requirement and ADR/design authority; downstream `aces-adapters` issues and
  PRs reference the ACES issue, REP UID, pinned design record, and acceptance
  evidence. Adapter implementation status must not be inferred from ACES docs
  alone.
- Emulation realization of CAGE-2 is explicitly out of scope. Do not design
  hidden hooks for an emulation backend, libvirt realization path, or mixed
  sim/emulation equivalence claim in REP-001.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- SDL ingress and semantics: `parse_sdl()`, `parse_sdl_file()`,
  `SDLModel(extra="forbid")`, `SemanticValidator`, `compile_runtime_model()`,
  `compile_scenario_runtime_model()`, planner semantics, participant behavior
  analysis, action contracts, observation boundaries, outcome interpretation,
  scoring, objectives, workflows, and evidence requirement validators.
- Backend protocols and manifests:
  `aces_backend_protocols.protocols.Provisioner`, `Orchestrator`, `Evaluator`,
  `ParticipantRuntime`, `BackendManifest`, `BackendCapabilitySet`,
  `ProvisionerCapabilities`, `OrchestratorCapabilities`,
  `EvaluatorCapabilities`, `ParticipantRuntimeCapabilities`,
  `ObservationCapabilities`, `RealizationSupportDeclaration`,
  `backend_manifest_payload()`, and capability-gap helpers.
- Neutral runtime contracts: `ProvisioningPlan`, `OrchestrationPlan`,
  `EvaluationPlan`, `RuntimeSnapshot`, `SnapshotEntry`, `ApplyResult`,
  `Diagnostic`, `Severity`, `OperationReceipt`, `OperationStatus`,
  participant episode requests, `ParticipantActionAdmissionRequest`, participant
  behavior events, shared-state records, and time-management contexts.
- Runtime and control-plane gates: `BackendRegistry`, `RuntimeTarget`,
  `RuntimeTargetComponents`, `_validate_runtime_target_shape()`,
  `RuntimeManager`, `RuntimeControlPlane`, `_call_backend_diagnostics()`,
  `_call_backend_apply()`, `ControlPlaneStore`, `LocalControlPlaneStore`,
  request fingerprints, idempotency keys, audit records, and redacted HTTP
  error handling.
- Participant runtime base: `BaseParticipantRuntime` for ACES participant
  episode lifecycle. Simulator stepping, agent order, reward bookkeeping, and
  CybORG driver state belong behind adapter-owned driver leaves, not in the base
  class.
- Conformance and contract authority: `run_target_conformance()`,
  `contracts/profiles/backend/*.json`, `contracts/fixtures/**`,
  `BackendManifestV2Model`, `schema_bundle()`,
  `contracts/schema-publication-manifest.json`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`, and
  `tools/check_json_artifacts.py`.
- Concept and vocabulary authority:
  `contracts/concept-authority/controlled-vocabularies-v1.json`,
  `contracts/concept-authority/concept-families-v1.json`,
  `validate_controlled_vocabulary_scope_values()`, concept-binding validators,
  and the governed `x-<owner>:<term>` extension syntax.
- Experiment and replication artifacts: `ExperimentTaskModel`,
  `ExperimentRunModel`, `ExperimentStudyModel`,
  `ExperimentRunAllocationPlanModel`, `ExperimentApparatusContextModel`,
  `ExperimentCaptureSpecModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentDerivedMeasureModel`, and their cross-artifact validators.
- Existing backend patterns: `aces_backend_stubs` only as a non-normative test
  oracle; `aces_reference_backend` and `aces_backend_libvirt` only for registry,
  manifest, driver-boundary, and portable-fact patterns, not as superclasses or
  hidden authorities.
- Workflow and policy: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `implementations/python/pyproject.toml`,
  `tools/policy/adr_policy.yaml`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config ingress: scenario artifacts must pass safe YAML loading, closed
  SDL models, semantic validation, compilation, planning, and advisory checks.
  Do not build plans from raw CAGE YAML/Python objects or bypass parser and
  validator gates.
- Upstream-source evidence: CAGE-2 inputs must be pinned by repository URL,
  commit or release, file path, and content digest where practical. Runtime
  code must not fetch remote CAGE assets during verification or conformance.
- Manifest/config layer: adapter support claims must validate through
  `BackendManifest`, `BackendManifestV2Model`, supported-contract allowlists,
  controlled vocabularies, concept bindings, realization-support declarations,
  and published backend profiles. Adapter config is target factory config, not
  hidden SDL fields or ambient environment.
- Runtime target layer: component presence must match manifest claims, and
  protocol methods must pass `_validate_runtime_target_shape()`. A CybORG
  backend that declares all four protocols must provide all four components;
  partial work must declare only evidence-backed capabilities.
- Backend apply layer: every backend call must return `Diagnostic` or
  `ApplyResult` values accepted by `_call_backend_diagnostics()` and
  `_call_backend_apply()`. The apply gate deep-copies snapshots, wraps
  unexpected exceptions, validates snapshot and history contracts, and rejects
  invalid output through `runtime.backend-contract-invalid`.
- Participant and observation layer: action admission must flow through
  `ParticipantActionAdmissionRequest`, compiled action-contract addresses,
  compiled observation-boundary addresses, implementation provenance, exposure
  policy, and participant history validators. Red/blue/green CybORG agents,
  backend identity, evaluator identity, participant implementation identity,
  and control-plane caller identity are distinct.
- Evaluation and reward layer: CAGE reward vectors and final score must map to
  ACES evaluation/objective/derived-measure surfaces with declared limitations.
  Reward is not participant-local outcome, workflow success, objective success,
  or conformance by itself.
- Experiment/replication layer: repeated runs and equivalence evidence must use
  `experiment-run-v1` plus `experiment-study-v1` membership/allocation,
  factors, condition assignments, stochastic controls, evidence records, and
  derived measures. Do not infer replication from repeated simulator calls or
  operation ids.
- Conformance layer: contract/profile/fixture loading must use the published
  ACES corpus and path-confined overrides. Report failures as structured
  `Diagnostic` values; do not execute fixture content, fetch remote fixtures,
  or echo malformed payload bodies in diagnostics.
- Control-plane security layer: any HTTP or service harness must reuse
  `ControlPlaneSecurityConfig.strict_defaults()`, explicit identities or bearer
  tokens, role checks, request-size limits, idempotency fingerprints, audit
  events, and redacted internal-error envelopes. Tokens must not be passed in
  process argv or printed in logs.
- Secret and OS-exposure layer: CybORG configs, dependency pins, seed values,
  local paths, credentials, bearer tokens, private keys, hidden scenario truth,
  process argv, environment dumps, native simulator object reprs, stdout/stderr,
  and full tracebacks must not enter SDL, snapshots, diagnostics, audit records,
  fixtures, evidence records, docs, or changelog text. If a subprocess leaf is
  unavoidable, use fixed argv, no `shell=True`, bounded timeouts, controlled
  working directories, and redacted diagnostics.
- Persistence layer: live state uses `RuntimeSnapshot` and `ControlPlaneStore`;
  archival evidence uses experiment/evidence/provenance contracts. Do not add
  adapter-specific stores, audit logs, or result databases as portable
  authority.
- Workflow/policy layer: ACES changes still pass repo policy, requirement
  governance, generated-schema parity, schema publication, JSON artifact, docs,
  and full nox verification gates. `aces-adapters` should define an analogous
  per-adapter CI matrix, but it should not weaken ACES gates or mirror their
  code blindly.

## Equivalence Guardrail

The REP-001 design should define equivalence as tiered evidence, not a single
boolean:

- authored-source equivalence: one ACES SDL scenario, no backend-specific SDL
  branches, and a complete pinned CAGE-2 mapping ledger;
- contract equivalence: each backend manifest validates, declares only
  evidence-backed support, and passes the applicable backend conformance
  profile plus participant/evaluation/runtime contract checks;
- execution-control equivalence: same trial length, red-agent variant, seed or
  stochastic-control declaration, logical step count, agent turn order,
  episode termination rule, and participant implementation selection;
- state/observation equivalence: mapped topology, services, privileges,
  visibility, observations, action admissibility, and shared-state transitions
  match the declared ACES semantics, with every mismatch either failing or
  carrying a mapping-loss disclosure;
- outcome/evaluation equivalence: reward components, objective results,
  evidence, derived measures, and cumulative score match the declared
  equivalence margins and confidence/evidence criteria.

If a backend cannot expose a fact needed for one tier, the result is a disclosed
weaker claim or a failed equivalence check. It is not acceptable to fill the gap
with fixture-local assertions, simulator-native logs, or prose-only evidence.

## Extensibility Boundary

The seam for future variation is:

- a source-mapping ledger parameterized by upstream source version, scenario id,
  red-agent policy, trial length, seed/stochastic-control policy, and declared
  loss disclosures;
- the backend registry descriptor/config seam for target construction and
  injected simulator drivers;
- a `sim_adapter_base` driver/projection layer parameterized by simulator
  package/version, clock/step policy, action translator, observation projector,
  reward/evaluator projector, and conformance probe set;
- published backend profile ids and contract ids loaded from ACES artifacts,
  not hard-coded enum branches in adapter CI;
- a per-adapter CI matrix axis for adapter project path, lockfile, Python
  version, optional simulator extras, conformance profile, and seed suite.

A future simulator backend, CybORG version, CAGE scenario, red-agent variant,
or seed suite should add a mapping-ledger row, target config value, driver
implementation, adapter project, or CI matrix entry. It should not require
changing ACES core contracts, SDL syntax, runtime manager, control plane,
schema registry, conformance profile authority, or experiment artifact
identity.

## Gotchas And Anti-Patterns

Avoid:

- treating CAGE-2 narrative names, CybORG class names, gym spaces, action ids,
  reward vectors, or leaderboard scores as ACES semantics without an explicit
  mapping and loss disclosure;
- adding CAGE/CybORG-specific SDL sections, schemas, vocabularies, manifest
  blocks, backend profiles, exception hierarchies, persistence stores, audit
  logs, or conformance runners when existing ACES surfaces carry the fact;
- subclassing `aces_backend_stubs` or copying stub capability claims into the
  CybORG adapter;
- declaring `ParticipantRuntime`, evaluator, observation, or feature-support
  capabilities before the adapter emits the required contracts and evidence;
- using `RuntimeSnapshot.metadata`, `ApplyResult.details`, notebook outputs,
  raw simulator logs, or CI stdout as portable scenario, participant, reward,
  or equivalence authority;
- merging backend identity, participant implementation identity, simulator
  policy identity, evaluator identity, and HTTP caller identity;
- claiming bit-for-bit state identity when the design only proves declared
  semantic equivalence with margins and disclosures;
- making default verification depend on network fetches, external simulator
  state, privileged host access, private credentials, or one global dependency
  lock shared by all adapters;
- routing cross-repo implementation status through informal comments instead of
  linked issues, PRs, requirement UID references, and readback evidence.

## Non-Goals

- Implementing the REP-001 ADR/design record in this preflight note.
- Authoring the CAGE-2 SDL scenario, mapping ledger, examples, tests,
  conformance probes, experiment artifacts, or evidence bundles.
- Creating `aces-adapters`, `sim_adapter_base`, a CybORG backend package,
  dependency lockfiles, CI workflows, or cross-repo issues.
- Adding or changing ACES SDL syntax, published schemas, backend profiles,
  concept vocabularies, control-plane APIs, runtime stores, conformance
  authority, exception hierarchies, or logging/audit infrastructure.
- Realizing CAGE-2 on an emulation backend or designing a hidden path for that
  deferred work.
