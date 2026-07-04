# Issue 637 REP-003 CAGE-2 SDL Scenario Preflight

Date: 2026-07-04

Issue: #637.

Requirement: REP-003.

This note records architecture guardrails for authoring the TTCP CAGE
Challenge 2 Scenario2 as an ACES SDL document. It is guidance only: it does
not author the scenario, mapping ledger, import lockfile, tests, adapter code,
backend harness, or replication evidence.

## Binding Sources

- ADR-069 and `docs/decisions/cage-2-replication-design.md` own the CAGE-2
  replication boundary. REP-003 implements the authored-source part of that
  boundary only.
- ADR-001, ADR-002, ADR-020, ADR-022, ADR-054, ADR-060, ADR-066, and ADR-067
  own SDL, participant, observation, behavior, outcome, and evidence
  semantics. CAGE/CybORG facts must map into those surfaces.
- `specs/sdl/`, `contracts/schemas/sdl/sdl-authoring-input-v1.json`, and
  `implementations/python/packages/aces_sdl/` are the SDL authority chain.
  Do not add CAGE-specific SDL syntax, schemas, parser branches, or validators.
- `examples/scenarios/*.sdl.yaml`, `examples/README.md`,
  `docs/explain/sdl/testing.md`,
  `implementations/python/tests/test_scenarios.py`, and
  `implementations/python/tests/test_example_schema_conformance.py` define the
  positive example-corpus boundary.
- `aces sdl resolve`, `aces sdl verify-imports`, and `aces sdl publish` are the
  required composition and publication workflow. They are implemented in
  `implementations/python/packages/aces_cli/sdl.py` and
  `implementations/python/packages/aces_sdl/module_registry.py`.
- `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py` remain the workflow authority.

## Architecture Decisions

- The deliverable is a positive, reusable SDL example under
  `examples/scenarios/`, plus any small sidecar source-mapping evidence needed
  to trace CAGE-2 facts. The SDL file is the authored ACES source of truth; a
  sidecar ledger is evidence, not parser input and not a second schema.
- Keep the scenario self-contained unless module composition is genuinely
  needed. `verify-imports` reads a directory-scoped `aces.lock.json` next to
  the SDL file, so imports in a root-level example can couple all examples in
  `examples/scenarios/` to one lockfile.
- Model the three CAGE-2 subnet roles with existing `nodes`, `infrastructure`,
  node services, accounts, agents, relationships, objectives, workflows,
  action contracts, observation boundaries, outcome interpretation rules, and
  evidence requirements. Do not introduce `subnets`, `participants`,
  `cyborg_actions`, `reward_model`, or similar CAGE-specific top-level keys.
- Keep CAGE identities distinct: red policy, blue participant, green/user
  behavior, backend, evaluator, and control-plane caller are separate concepts.
  An SDL `agent` is not a participant implementation manifest, simulator
  policy object, backend identity, or evaluator identity.
- Treat CAGE action ids, gym spaces, reward vectors, terminal conditions, and
  simulator object names as source facts. They become ACES facts only through
  existing participant action contracts, observation boundaries, objectives,
  evaluation/scoring surfaces, evidence records, derived measures, or explicit
  loss disclosures.
- Publication metadata, if used, must stay ordinary SDL module metadata:
  `module.id` uses `publisher/name`, `version` is concrete, and `exports`
  matches declared sections. Module metadata must not carry hidden scenario
  semantics or source-ledger rows.

## Required Incumbents

Reuse these surfaces before adding anything new:

- SDL ingress: `parse_sdl_file()`, `parse_sdl()`, `yaml.safe_load`,
  `_load_normalized_data()`, `_HASHMAP_SECTIONS`, `_NESTED_HASHMAP_FIELDS`,
  variable-key rejection, shorthand expansion, `SDLModel(extra="forbid")`,
  `Scenario`, `ExpandedScenario`, `SemanticValidator`, `SDLParseError`,
  `SDLValidationError`, and `ScenarioValidationError`.
- Positive corpus and schema checks: `examples/scenarios/*.sdl.yaml`,
  `EXAMPLES_DIR`, `test_scenarios.py`, `test_example_schema_conformance.py`,
  `contracts/schemas/sdl/sdl-authoring-input-v1.json`, and the publication
  serialization `model_dump(mode="json", by_alias=True)`.
- Participant and behavior surfaces: `agents`, `action_contracts`,
  `observation_boundaries`, `behavior_specifications`,
  `outcome_interpretation_rules`, participant semantic analyzers, operating
  scope validation, and compiler addresses under `participant.*`.
- Topology and runtime inventory surfaces: existing `nodes`, `infrastructure`,
  node `services`, `accounts`, relationships, and node-scoped `runtime`
  families. Use runtime-family ADRs and `specs/sdl/runtime-inventory.md` for
  service/listener/identity/app/data facts instead of creating CAGE aliases.
- Objective/evidence surfaces: `objectives`, `workflows`, `metrics`,
  `evaluations`, `tlos`, `goals`, `evidence_requirements`, and the
  observability/evidence-plane rules in `specs/sdl/observability-and-evidence.md`.
- Module workflow: `resolve_lock_records()`, `load_lockfile()`,
  `load_trust_policy()`, local-import path confinement, OCI trust policy,
  digest/signature checks, bounded OCI fetch/extract limits, and
  `publish_module_to_oci_layout()`.
- Compiler/runtime proof points: `compile_runtime_model()`,
  `compile_scenario_runtime_model()`, `RuntimeModel`,
  `ParticipantActionContractRuntime`, `ParticipantObservationBoundaryRuntime`,
  and `ParticipantBehaviorRuntime`.
- Governance and release workflow: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_example_library.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`,
  `tools/verify_all.py`, and `changelog.d/`.

## Cross-Cutting Layers

- SDL/config parsing layer: the scenario must pass safe YAML loading,
  normalized SDL field keys, preserved user-defined map keys, variable-key
  rejection, closed Pydantic models, semantic validation, and advisory checks.
  Do not compile from raw CAGE YAML/Python objects or use
  `skip_semantic_validation=True` outside publication's existing descriptor
  path.
- Published-schema layer: the checked-in `sdl-authoring-input-v1` schema is the
  machine-readable contract. A scenario that only satisfies Pydantic but fails
  `test_example_schema_conformance.py` is not acceptable.
- Reference-resolution layer: cross-references must resolve through the
  existing semantic validator and qualified-reference rules. Ambiguous CAGE
  names must be disambiguated by stable ACES identifiers, not by declaration
  order or prose.
- Import/trust layer: if imports are used, local imports must stay within the
  SDL directory, OCI imports must pass trust policy, signatures, digest pins,
  bounded HTTP reads, safe tar extraction, and lockfile verification. A stale
  or scenario-incompatible `aces.lock.json` must fail closed.
- Publication layer: `publish` packages a self-contained local module graph
  and rejects remote OCI imports in the publication bundle. Optional signing
  uses an Ed25519 private key path; private keys, signer secrets, and command
  output dumps must not be committed or embedded in scenario docs.
- Participant/observation security layer: hidden truth, red policy internals,
  answer keys, evaluator state, simulator-native observations, credentials, and
  private runner config must stay out of participant-observable content.
  Observation boundaries must state what each participant can observe, what is
  hidden, and what is evidence-only.
- Secret and OS-exposure layer: scenario files, sidecar ledgers, tests,
  diagnostics, docs, command examples, process argv, logs, and publish outputs
  must not contain bearer tokens, private keys, local secret paths, raw
  environment dumps, native simulator object reprs, full tracebacks, or raw
  secret-bearing command lines. Use references, digests, redacted shapes, and
  disclosures.
- Error-envelope layer: parser and semantic failures stay on
  `SDLParseError`, `SDLValidationError`, and `ScenarioValidationError`.
  Runtime/backend/conformance errors are out of scope for REP-003 and must not
  get a scenario-specific exception hierarchy.
- Workflow/policy layer: repo policy, requirement governance, example-corpus
  tests, published-schema conformance, generated-schema parity,
  JSON-artifact checks, and full verification gates remain authoritative.

## Extensibility Boundary

The extensibility seam for REP-003 is source mapping and SDL parameters, not a
new language surface:

- a mapping-ledger row can vary upstream source version, source selector,
  source digest, CAGE fact type, ACES target, mapping rule, verification, and
  loss disclosure;
- SDL `variables` may parameterize obvious scenario variants such as red-agent
  policy label, trial length, or seed/stochastic-control declaration when those
  variants are authored facts, but they must preserve valid references and
  schema shape;
- participant/action/observation variation belongs in additional existing
  `agents`, `action_contracts`, `observation_boundaries`,
  `behavior_specifications`, objectives, workflows, and evidence requirements;
- backend-specific realization variation belongs to REP-004/REP-005 adapter
  config, manifests, provenance, and experiment/run artifacts, not to hidden
  SDL keys.

A future CAGE version, scenario variant, red policy, or seed suite should add a
ledger row, variable binding, participant/action/boundary entry, or downstream
experiment artifact. It should not require changing the SDL parser, published
schema, runtime manager, backend protocol, conformance profile authority, or
exception hierarchy.

## Gotchas And Anti-Patterns

Avoid:

- adding CAGE/CybORG-specific top-level SDL sections, schemas, validators,
  controlled vocabularies, exception types, fixture loaders, or publish scripts;
- storing unmapped CAGE facts in free-form descriptions, metadata-like fields,
  `RuntimeSnapshot` details, diagnostics, or ledger prose while claiming they
  are authored SDL semantics;
- treating three named subnets as only prose; they need concrete SDL topology
  and referenceable identifiers;
- conflating an SDL `agent` with a participant implementation manifest,
  simulator policy class, backend identity, evaluator identity, or caller
  identity;
- treating reward, score, objective satisfaction, workflow success,
  participant-local outcome, backend conformance, and replication equivalence
  as the same concept;
- committing generated publish bundles under `dist/` unless a later acceptance
  criterion explicitly asks for release artifacts;
- using remote network fetches, mutable upstream branches, private credentials,
  hidden local files, or host-specific absolute paths in default verification;
- putting invalid drafts, negative controls, or partial examples under
  `examples/scenarios/`.

## Non-Goals

- Authoring the CAGE-2 SDL scenario or mapping ledger in this preflight.
- Implementing CybORG, `aces-adapters`, `sim_adapter_base`, backend manifests,
  conformance probes, participant runtimes, or replicated runs.
- Adding or changing SDL syntax, published schemas, runtime-family models,
  controlled vocabularies, backend protocols, conformance profiles, error
  envelopes, logging/audit infrastructure, or persistence stores.
- Realizing CAGE-2 on an emulation backend or designing a hidden path for that
  deferred work.
