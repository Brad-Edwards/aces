# Issue 168 Formal Semantic Validation And Reachability Preflight

Date: 2026-07-17

Issue: #168. Requirement: none; the issue title, body, protocol, and
demonstration criteria are the delivery contract.

This note fixes the repository-wide boundary for testing ACES validation and
reachability claims. It does not execute the protocol, add cases, change SDL
validity, implement a solver, or repair a finding. No new ADR is needed:
ADR-007, ADR-021, ADR-072, and the existing semantic-layer decisions already
govern assurance depth, claim evidence, validation-strength disclosure, and
cross-stage semantic ownership.

## Decision Boundary

Issue #168 is a falsification/evidence gate, not a new validator or formal
semantics design. Keep the following independently revisioned concerns:

1. **Protocol:** claim classes, exact subject and artifact stage, positive and
   single-defect negative cases, public entrypoints, expected detection,
   allowed evidence, pass/fail rules, source pins, and amendments.
2. **Execution snapshot:** the exact ACES revision, case and tool revisions,
   commands/entrypoints, bounded outcomes, diagnostics, output digests,
   deviations, and unavailable or not-run gates.
3. **Analysis and claim record:** the protocol-derived claim matrix, observed
   detection behavior, limitations, and ADR-021 evidence status.

Use the established non-normative research-bundle convention under a dedicated
`docs/research/formal-semantic-validation/` directory. If machine-readable
records are used, a focused offline checker owns their closed shape and joins.
Reuse `tools.policy.common.load_bounded_json_object`, `safe_repo_path`, and
`PolicyFailure`, plus the protocol/snapshot/analysis and bundle-manifest pattern
from `docs/research/dsl-language-evaluation/`. Do not publish the research
record as an ACES contract schema, add it to `aces_contracts`, or persist it in
runtime state.

Validation call, artifact stage, FM assurance level, validation-strength class,
gate result, and ADR-021 evidence status are independent axes. In particular:

- `FM0`-`FM3` classify the assurance artifacts required for a changed semantic
  surface; they are not results from this protocol.
- `structural` through `falsification_backed` describe a disclosed validation
  basis under ADR-072; they are not solver proof levels.
- `passed`, `failed`, `partial`, `not_run`, `not_applicable`, `unknown`,
  `unsupported`, and `withheld` are per-gate outcomes; none is an evidence
  status.
- `untested`, `partial`, `demonstrated`, and `refuted` are claim-evidence
  statuses under ADR-021; they must be derived from the frozen protocol and
  evidence rather than copied from test success.

## Claim-Class Boundaries

The issue's seven literature calls must remain separate stable protocol ids.
One result must not stand in for another.

| Claim class | Exact boundary |
| --- | --- |
| Schema validity | Source/JSON shape, closed fields, types, vocabularies, and local constraints only. Schema or Pydantic acceptance is not semantic consistency. |
| Semantic consistency | Static cross-reference, uniqueness, ambiguity, acyclicity, required-profile, redaction, and related fail-closed invariants over a parsed or instantiated model. It is not runtime feasibility. |
| Graph reachability | Reachability in one named graph with declared node/edge semantics, such as workflow control flow or compiled ordering dependencies. It is not automatically network, service, participant, or exploit reachability. |
| Constraint satisfiability | Existence or non-existence of an assignment/model for an explicitly named constraint system and domain. Local Pydantic predicates, finite-domain checks, or a topological sort are not whole-scenario satisfiability. |
| Exploit-path validity | A typed attack/exploit transition graph plus prerequisites, effects, observations, and an executable path query or proof. A vulnerability reference, network link, ACL, service declaration, objective, or successful deployment is not such a path. |
| Determinism/stability | Repeatability under named inputs, stage, environment variations, serializer, and equivalence relation. Parse/instantiate/compile byte stability does not prove runtime scheduling, backend, observation, replay, or study stability. |
| Counterfactual necessity | An intervention/ablation protocol comparing governed worlds under a named causal model and necessity criterion. Attribution vocabulary, temporal order, a replay label, or a negative fixture is not counterfactual proof. |

### Preflight truth baseline

This baseline guides evidence collection; it is not the issue's final result and
must be recomputed against the pinned execution snapshot.

- **Schema validity:** ACES has executable source, Pydantic, published-schema,
  fixture, and generated-schema parity gates. The claim is structural unless a
  later semantic gate is named separately.
- **Semantic consistency:** `SemanticValidator` and instantiation revalidation
  reject many missing/ambiguous references, duplicate identities, dependency
  cycles, workflow cycles/unreachable steps, invalid joins, and invalid
  stateful/runtime profiles. Coverage is claim-specific; the current tests are
  not a manifest proving a negative corpus for every documented claim.
- **Graph reachability:** workflow control-flow reachability/convergence and
  compiled planner ordering/refresh semantics have executable graph helpers,
  negative tests, and some property/differential evidence. They do not prove
  host/network/service reachability or exploit paths.
- **Constraint satisfiability:** bounded realization-envelope membership and
  witness generation, variable-domain checks, and other local constraints are
  narrower relations. There is no current whole-scenario SMT/Datalog-style
  satisfiability gate comparable to VSDL or CRACK.
- **Exploit-path validity:** no canonical attack-graph/exploit-transition
  analyzer was found. This class remains unsupported or untested unless the
  execution locates an actual governed executable protocol.
- **Determinism/stability:** `test_pipeline_determinism.py` witnesses the
  `parse -> instantiate -> compile` slice, including hash-seed variation. It
  must not be promoted to full processor/runtime/replay stability.
- **Counterfactual necessity:** participant attribution and behavioral-relation
  vocabularies disclose counterfactual/ablation concepts, but issue #98's
  executable behavioral/counterfactual protocol is not present as a solver or
  intervention gate. Vocabulary and invariant-oracle tests do not demonstrate
  necessity.

The issue context's `implementations/python/packages/aces_sdl/validator.py`
manifestation path is stale: `SemanticValidator` is now the mixin package at
`implementations/python/packages/aces_sdl/validator/`. Evidence and guidance
must cite the owning package, not revive the deleted monolith or the
compatibility-only `implementations/python/src/aces/` namespace.

## Corpus And Observation Boundary

- Give every claim a stable `claim_id`, named semantic subject, exact artifact
  stage, owning specification/invariant, production entrypoint, expected
  diagnostic/result, positive control, and at least one single-defect negative
  case. A documented invariant without an executable case is not demonstrated.
- Keep issue-specific cases in a versioned, manifest-backed research corpus
  alongside the bundle. Invalid cases do not belong in
  `examples/scenarios/`, which is the positive worked-example corpus. They do
  not belong in `contracts/fixtures/` unless they independently become
  normative conformance fixtures through the contract-governance process.
- A case should inject one defect and record the expected rejecting stage.
  Multi-defect stress cases may be supplemental but cannot establish detection
  attribution. Include non-vacuity controls: discovered case counts, positive
  cases that pass the intended stage, and mutations that actually change the
  targeted property.
- Execute public owning entrypoints. SDL text uses `parse_sdl_file()` when
  composition is relevant, then `instantiate_scenario()` or
  `admit_instantiated_scenario()`, `compile_runtime_model()`, `plan()`,
  `run_reference_processor()`, and the existing conformance runner only where
  the claim reaches those stages. Do not build `Scenario`, `RuntimeModel`, or
  plans directly to improve the observed result.
- Preserve the difference between a raised SDL error and returned processor or
  planner diagnostics. A plan carrying an error `Diagnostic` is invalid even
  though `plan()` returned an object. Likewise, conformance of a target API is
  not proof of a scenario graph property unless a named conformance case
  exercises that property.
- Record exact structured diagnostic fields where the public entrypoint
  supplies them. Do not score semantic validation only by matching English
  substrings, and do not synthesize a code/range from implementation internals
  when the public surface emits prose only; missing structure is a finding.
- Freeze failed observations. A product correction belongs to a separate issue
  and owning spec/code/test surfaces; it produces a new execution snapshot and
  must not overwrite the falsifying record.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required boundary |
| --- | --- |
| Authority and claims | ADR-009/019, `specs/authority/authority-boundary.yaml`, ADR-021, ADR-072, and the documentation style guide. Research reports evidence; it does not define SDL meaning or validation strength. |
| Research bundle | `docs/research/dsl-language-evaluation/`, `docs/research/related-work-comparison/`, their focused checkers/tests, and the protocol/snapshot/analysis/manifest split. Extend their bounded data-loading idiom, not their domain-specific fields. |
| Assurance classification | ADR-007, ADR-018, `specs/formal/assurance-policy.yaml`, `specs/formal/assurance-fulfillment.yaml`, and `tools/check_assurance_policy.py`. Do not infer solver assurance from FM labels or delivered Markdown. |
| Source and structural validation | `sdl-yaml/v1`, `SDLParserLimits`, `load_sdl_yaml`, mapping-key analysis, `SDLModel(extra="forbid")`, `parse_sdl()`/`parse_sdl_file()`, checked-in SDL schemas, and schema-publication parity gates. |
| Static semantics | `aces_sdl.validator.SemanticValidator`, `build_declaration_index`, `specs/sdl/references.md`, `specs/sdl/diagnostics.md`, and the existing shared semantic analyzers. Do not add evidence-only reference or graph logic. |
| Instantiation and phase admission | `instantiate_scenario()`, `admit_instantiated_scenario()`, `InstantiatedScenario`, phase contracts, post-substitution semantic validation, and the existing SDL error types. |
| Compiler and planner | `compile_runtime_model()`, canonical addresses, typed `RuntimeModel`/plan contracts, `aces_processor.semantics.planner`, `plan()`, and existing cross-stage agreement tests. Do not add a second graph/DTO/plan representation. |
| Workflow/objective semantics | `aces_sdl.semantics.workflow`, `aces_sdl.semantics.objectives`, `aces_sdl.semantics.objective_semantics`, `specs/formal/workflows/`, and `specs/formal/objectives/`. Validator and compiler evidence must share these analyzers where they already do. |
| Processor and conformance | `run_reference_processor()`, `aces_conformance`, published backend/processor manifests and profiles, `Diagnostic`/`Severity`, `ConformanceCaseResult`, and `BackendConformanceReport`. Declared capability, accepted plan, apply result, and independent observation remain distinct. |
| Tests and corpora | `test_sdl_validator.py`, `test_semantics_objectives.py`, `test_semantics_planner.py`, `test_fm2_semantics.py`, `test_pipeline_determinism.py`, `test_reference_processor.py`, conformance tests, `tests/paths.py`, and `aces_contracts.corpus` for normative corpus families only. |
| Workflow/reporting | `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, `noxfile.py`, `SessionReporter`, `tools/verify_all.py`, repo policy, Sphinx, private-key detection, and gitleaks. Add any focused gate once to the existing nox graph, not a parallel workflow. |

There is no new controller, HTTP DTO, service, repository, or mutable
persistence layer in the intended design. `RuntimeControlPlane`,
`ControlPlaneStore`, runtime snapshots, operation audit events, and experiment
archives are not stores for this research matrix.

## Cross-Cutting Validation, Security, And Operational Layers

1. **Research/config shape:** treat checked-in protocol, manifest, corpus, and
   result files as inert bounded data. Reject duplicate or unknown fields/ids,
   dangling joins, missing case coverage, unsafe paths, stale derived results,
   unpinned revisions, and unbounded counts/files. Resolve repository paths
   with `safe_repo_path`; do not add environment-selected corpus roots.
2. **SDL source/parser:** retain UTF-8 checks, byte/scalar/depth/node/alias and
   composition budgets, YAML 1.2 Core resolution, the safe loader, tag/directive
   rejection, JSON-domain checks, mapping-key conflict analysis, exact source
   profile, and file-backed module trust/lock/digest/namespace/cycle rules. No
   evaluation-only loader or preprocessor may repair a negative case.
3. **Model/schema:** use closed SDL models and, when schema conformance is the
   claim, the checked-in published schema for the correct phase. Do not use a
   freshly generated schema as authority, fetch remote refs, or create a
   research DTO in `contracts/`.
4. **Semantic/instantiation:** use the collect-all, fail-closed
   `SemanticValidator` path and concrete revalidation. `skip_semantic_validation`
   is permitted only as an explicit negative control demonstrating a stage
   boundary; it can never count as semantic acceptance.
5. **Compiler/planner/conformance:** preserve typed canonical addresses,
   manifests, capability checks, realization disclosures, ordering-cycle
   diagnostics, and `is_valid`/error-severity semantics. Invalid plans must not
   proceed to side effects. A reference/stub target is evidence only for the
   declared bounded conformance relation, never for independent live fidelity.
6. **Authentication/authorization:** the normal design is offline and adds no
   auth surface. If an existing remote control-plane adapter is exercised,
   reuse `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   target-bound roles, request-size/idempotency/fingerprint guards, audit, and
   redacted internal errors unchanged. Do not add a research-only bypass.
7. **Secrets, privacy, and error envelopes:** cases use synthetic public data.
   Preserve `SDLParseDiagnostic`, `SDLParseError`, `SDLValidationError`,
   `SDLInstantiationError`, `Diagnostic`/`Severity`, conformance results, and
   bounded `PolicyFailure` records. Never emit source documents, parameter
   maps, raw secret values, hidden answers, trust policies, environment dumps,
   backend-native objects, Pydantic input, tracebacks, or unrestricted stdout/
   stderr in evidence or logs.
8. **OS/network/supply chain:** reproduction is fixed-argv, `shell=False`,
   resource-bounded, and offline. Pass paths, ids, profiles, and digests in
   argv, not raw scenario bodies, credentials, or evidence payloads. Do not
   invoke a solver, backend daemon, OCI/network fetch, privileged namespace,
   firewall mutation, or third-party code merely because the literature call
   mentions satisfiability or reachability; such apparatus needs a separately
   declared, pinned execution boundary.
9. **Persistence/observability:** the durable public record is the Git-tracked
   sanitized protocol, corpus manifest, execution snapshot, analysis, and
   digests. Use `SessionReporter` for the repository gate and the existing
   structured diagnostic/result envelopes for observations. Add no database,
   cache, runtime metadata bag, sidecar ledger, logger, telemetry stream, or
   raw-output archive.

## Whole-Repository Scope

The evidence run must inspect or reference, without rewriting them to make the
claim pass:

- `specs/sdl/`, published SDL schemas/fixtures, schema publication manifest,
  parser/source-profile code, and positive example corpus;
- `aces_sdl` declaration indexes, semantic analyzers, validator, instantiation,
  phase admission, and SDL diagnostics;
- `aces_processor` compiler, canonical addressing, planner semantics, plan
  contracts, diagnostics, reference processor, and cross-stage tests;
- `specs/formal/` domain artifacts, assurance policy/fulfillment, semantic
  coverage inventory, property/differential tests, and state-machine oracles;
- backend/processor manifests, realization envelopes, `aces_conformance`,
  reference/stub targets, runtime result envelopes, and observation boundaries;
- ADR-021 claim evidence, ADR-072 validation/admission profiles, limitations,
  related-work source pins, and the existing research-bundle conventions; and
- `.ground-control.yaml`, `.gc/plan-rules.md`, `.pre-commit-config.yaml`,
  `noxfile.py`, `.github/workflows/ci.yml`, `tools/verify_all.py`, Sphinx, policy,
  schema, secret, and private-key gates.

## Extensibility Seam

The stable observation join is:

```text
(protocol_revision, aces_revision, claim_id, case_id, artifact_stage,
 entrypoint_id, execution_id, configuration_id)
```

`configuration_id` identifies the source/migration profile and, only when
relevant, the processor/backend manifest and target profile. Claim classes,
cases, stages, entrypoints, expected detection, and configurations are protocol
catalog data with stable ids, not Python enums or one column per current tool.
The next reasonable variation—a new solver/analyzer, additional backend,
stronger counterfactual protocol, new semantic invariant, or repeated ACES
revision—adds catalog rows and a new immutable execution snapshot. A changed
claim meaning or pass threshold creates a protocol revision. It must not require
editing SDL models, planner graph types, exception hierarchies, runtime stores,
or the prior evidence.

## Gotchas And Anti-Patterns

Avoid:

- claiming CRACK/VSDL-level assurance from schema validity, Pydantic models,
  fail-closed static checks, Markdown formal artifacts, FM classification, or a
  green assurance-fulfillment map;
- calling workflow reachability, planner ordering, topology links, service
  declarations, ACL carriage, vulnerability references, or successful apply an
  exploit-path proof;
- treating a finite witness for one realization envelope as global scenario
  satisfiability, or treating topological acyclicity as general constraint
  satisfiability;
- conflating authoring validity, instantiation admission, compiler diagnostics,
  planner validity, backend capability, target conformance, runtime behavior,
  observation strength, validation strength, and claim evidence status;
- counting direct model construction, `skip_semantic_validation`, parse-only
  inspection, a private flag, or a test-local invariant oracle as production
  semantic acceptance;
- recording only positive cases, seeding multi-defect negatives without
  attribution controls, accepting zero discovered cases, or testing only error
  message substrings;
- adding a second schema, reference resolver, graph library, constraint model,
  exception tree, diagnostic envelope, logger, corpus registry, conformance
  runner, persistence store, or CI workflow for the evidence gate;
- placing invalid research cases in `examples/scenarios/`, or changing
  production semantics and replacing the original failed snapshot so the
  protocol appears to pass; and
- exposing raw SDL, parameters, credentials, environment, host paths, solver
  dumps, backend outputs, process argv, or tracebacks in committed evidence.

## Non-Goals And Implementation Boundaries

- Do not implement solver-backed whole-scenario satisfiability, exploit-path
  analysis, network reachability, or counterfactual necessity under this issue.
- Do not change SDL syntax, schemas, parser normalization, semantic rules,
  compiler/planner/runtime behavior, backend capabilities, conformance
  profiles, validation-strength contracts, or assurance levels to improve the
  result.
- Do not complete issue #98's behavioral/counterfactual/determinism work or
  generalize the narrow existing determinism witness.
- Do not claim universal semantic correctness, complete negative coverage,
  backend independence, behavioral fidelity, or CRACK/VSDL equivalence beyond
  the exact pinned claim, cases, stages, configurations, and evidence.
- Do not add an API, service, UI, database, mutable result registry, public
  contract family, new formal-methods policy, or production telemetry path.
