# Issue 164 Standardized Configurable Specification Coverage Preflight

Date: 2026-07-17

Issue: #164. This is a requirement-free run; the issue title, body, research
question, test protocol, and demonstration criteria are the contract.

This note fixes architecture guardrails for the specification-coverage
falsification gate. It does not select or preregister the literature corpus,
author the scenarios, execute the protocol, score ACES, change the SDL, or fix
gaps exposed by the protocol. No new ADR is needed: the existing authority,
claim-evidence, phase-contract, experiment-core, realization, completeness,
and validation-strength decisions already govern the work.

## Decision Boundary

Issue #164 is a non-normative, offline evidence bundle, not a language feature,
completeness profile, backend conformance profile, or new validity class. Follow
the established `docs/research/related-work-comparison/` and
`docs/research/dsl-language-evaluation/` split:

1. a preregistered protocol containing the frozen source corpus, coverage
   strata, atomic requests, classification rules, stage obligations, and
   objective pass/fail criteria;
2. an immutable execution snapshot pinning the ACES revision, exact authored
   and contract artifacts, production entrypoints, diagnostics, derived
   addresses, and observed outcomes; and
3. a recomputable analysis and ADR-021 claim record referencing exactly one
   protocol and execution snapshot.

Protocol changes create a new protocol revision. Re-running against a new ACES
revision creates a new execution snapshot and analysis; it does not overwrite a
falsifying observation. Keep the bundle under a dedicated `docs/research/`
directory. Do not publish its local record shape under `contracts/schemas/`,
add it to `aces_contracts`, or store it in the runtime control plane.

One focused offline checker may own the closed research-file shape and
cross-record invariants. It must build on `tools.policy.common` and the existing
related-work/language-evaluation checker patterns instead of creating a generic
schema registry, loader framework, validator stack, exception hierarchy,
logger, or workflow.

## Atomic Classification And Claim Discipline

A literature request can mix portable scenario meaning, experiment design,
apparatus constraints, and backend mechanics. Decompose each request into
atomic concepts before authoring or execution, retain the parent request and
source locator, and classify each atomic concept exactly once:

| Issue classification | Sufficient evidence and boundary |
| --- | --- |
| `directly-expressible` | A named, typed ACES SDL or portable task/contract field owns the meaning; its production structural and semantic gates accept the artifact; and every preregistered downstream stage that claims to carry the concept preserves it at an exact pointer or canonical address. |
| `profile-or-manifest-constraint` | A named, versioned semantic/backend profile, processor/backend/participant manifest, experiment apparatus constraint, or realization envelope owns the constraint and is bound to the scenario/task lineage. A free-form note, tag, capability string, or unvalidated reference is insufficient. |
| `deliberately-backend-specific` | The concept is a realization mechanism rather than portable scenario meaning, and it remains in a backend manifest, apparatus context, plan/realization disclosure, or backend evidence artifact. The portable requirement it realizes must still be represented or explicitly missing; this classification cannot hide loss of core meaning. |
| `missing` | No existing typed owning surface preserves the requested meaning, or the only available encoding is description text, arbitrary metadata, an ungoverned extension, or an approximation through a different concept. Record the gap without changing the request or the evidence snapshot. |

The four classifications describe concept coverage. They are not execution
outcomes. Preserve separately:

- stage outcome (`passed`, `failed`, `unsupported`, `not_applicable`,
  `not_run`, or `tool_failed`);
- validation strength from ADR-072;
- scientific-completeness disposition and delivery status;
- backend/profile support and realization disposition; and
- ADR-021 claim status (`untested`, `partial`, `demonstrated`, or `refuted`).

A directly expressible concept can still fail because the attempted authoring
is invalid. A missing concept can be recorded correctly. A backend-specific
mechanic can be out of scope for compilation. None of those facts may be
collapsed into one `supported` boolean.

Predeclare which atomic concepts are load-bearing for the issue's core pass
criteria and which are legitimate external/backend concerns. Otherwise a
failed core concept could be reclassified after execution, or a large set of
minor successes could obscure a benchmark-relevant gap. Source strata and
minimum coverage must likewise be frozen before results are observed.

## Carrier And Lifecycle Boundaries

| Concern | Canonical owner | Guardrail |
| --- | --- | --- |
| Topology, nodes, networks, content, accounts, entities, scenario roles, agents, action/observation semantics, objectives, workflows, and authored evidence expectations | `sdl-yaml/v1`, the closed SDL models and published SDL schemas | These are scenario meaning. Do not use Docker, OpenStack, cloud-resource, or backend-driver vocabulary as structural SDL fields. |
| Evaluation intent, population/construct, metrics, validity limits, and task-to-scenario binding | `ExperimentTaskModel` / `experiment-task-v1` | A task references scenario meaning; it does not duplicate it or become an SDL section. |
| Pre-run factors, allocation, stochastic controls, episode intent, capture refs, and apparatus intent | `ExperimentSpecModel` / `experiment-authoring-input-v1` | This is experiment authoring input, not a run, runtime snapshot, or scenario. |
| Capture obligations, captured material, and derived results | SDL `evidence_requirements`, `ExperimentCaptureSpecModel`, `ExperimentEvidenceRecordModel`, and `ExperimentDerivedMeasureModel` | An authored requirement is not proof of capture; raw evidence is not a score or interpretation. |
| Processor/backend/participant selection and compatibility | Experiment apparatus constraints, manifests, profiles, realization envelopes, and apparatus context | Apparatus choice stays outside core SDL and must use versioned, validated references. |
| Processor lowering and planning | `instantiate_scenario()`, `compile_runtime_model()`, canonical addresses, `plan()`, and published plan contracts | The Python `RuntimeModel` is a typed reference-processor model, not a published exchange schema. Published instantiated SDL and plan contracts carry portable artifact claims. |
| Mutable execution and archival provenance | `aces_runtime` control-plane/snapshot contracts versus experiment run/evidence contracts | Live state must not be used as authoring intent; archival records must not be reconstructed from mutable state. |
| Coverage result and gaps | The issue-local research bundle plus ADR-021 claim record | Research results report authority; they do not define SDL semantics or silently update completeness delivery status. |

The protocol must declare an expected carrier and artifact stage for every
atomic concept. A stage is `not_applicable` only because the owning phase
contract excludes that concern, not because the implementation dropped it.
Where compiler retention is claimed, map the concept to typed compiler output
and canonical addresses, and inspect `Diagnostic` severity as well as object
construction. Where a portable exchange claim is made, validate the published
artifact, not a Python dataclass representation.

Use the explicit path `parse_sdl_file()` with semantic validation enabled,
`instantiate_scenario()`, then `compile_runtime_model()` over the admitted
instantiated artifact. This preserves distinct evidence for source/model,
semantic, instantiation, and compiler gates even though later entrypoints
defensively revalidate. Do not use `skip_semantic_validation`, private
`_semantic_validated` state, `model_construct()`, raw dictionaries, or a
filename as evidence of admission. Invoke `plan()` only for a preregistered
profile/manifest or planning claim and only with the named validated manifest;
stub planning is not backend realization evidence.

Loss checking is semantic, not a backend-term grep. Each row needs the exact
intended meaning, owning pointer/address, expected downstream projection, and
any backend-vocabulary occurrence with its artifact and reason. A term in a
description can conceal a dependency, while a backend name in a realization
disclosure can be correct. Successful parse/compile with an absent or weakened
load-bearing projection is a protocol failure.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required boundary |
| --- | --- |
| Authority and claims | ADR-009/019, `specs/authority/authority-boundary.yaml`, ADR-021, ADR-061, and the documentation style guide. Research evidence cannot create or amend normative semantics. |
| Source identity and corpus seeds | `contracts/provenance/sdl-lineage-ledger-v1.json`, `docs/research/lineage/`, `docs/research/primary/`, the frozen sources/cases in `docs/research/related-work-comparison/protocol-v1.json`, the DSL language-evaluation sources/tasks, and the experiment-core search log. Reuse an existing source identity rather than copying it. |
| Existing coverage and gap truth | `specs/sdl/scientific-scenario-completeness.md`, the REV1 taxonomy and dated delivery assessment, `tools/check_scientific_scenario_completeness.py`, `docs/explain/sdl/limitations.md`, and the scenario-delivery drift audit. Issue #164 observes these surfaces; it does not redefine their statuses. |
| SDL source and shape | `SDLParserLimits`, `_SDLSafeLoader`, mapping-key analysis, `parse_sdl()` / `parse_sdl_file()`, closed `Scenario` / `InstantiatedScenario`, and the checked-in `sdl-authoring-input-v1`, `instantiated-scenario-v1`, and snapshot schemas. The normalized schema is not a raw-YAML parser. |
| Composition and semantics | Module registry path/trust/lock/digest/export/signature gates, `SemanticValidator`, declaration/reference indexes, `specs/sdl/sections.md`, `references.md`, `diagnostics.md`, and the collect-all semantic rules. Do not implement corpus-only resolution or acceptance. |
| Phase traceability | ADR-078, `instantiate_scenario()`, `admit_instantiated_scenario()`, canonical authored/instantiated profiles, `compile_runtime_model()`, canonical addresses, and pipeline-determinism tests. Do not infer preservation from digest presence alone. |
| Experiment/task/apparatus | ADR-055/064/065/066/068/074; the task, authoring-input, capture, evidence, measure, apparatus, run, and study schemas; their `ContractModel` classes; and cross-artifact validators such as `validate_experiment_apparatus_context_against_manifests()` and `validate_experiment_run_against_task()`. |
| Profiles, manifests, and realization | Scientific-completeness and validation/admission profiles, semantic/backend profiles, processor/backend/participant manifests, `manifest_authority`, ADR-070 realization envelopes, backend capability checks, and realization disclosures. A generic `constraints` or `notes` field does not replace these typed relations. |
| Processor and runtime artifacts | ADR-008/036, `aces_processor` compiler/planner models, published provisioning/orchestration/evaluation plan schemas, runtime snapshot contracts, and experiment run provenance. Keep internal processor models, portable DTOs, live state, and archival evidence distinct. |
| Diagnostics and errors | `SDLParseDiagnostic`, `SDLParseError`, `SDLValidationError`, `SDLInstantiationError`, `ExperimentSpecValidationError` when authored experiment YAML is genuinely used, `Diagnostic`, `Severity`, and `tools.policy.common.PolicyFailure`. Do not create issue-specific exception or diagnostic types. |
| Existing scenario/test evidence | `examples/scenarios/`, `examples/experiments/`, `test_sdl_stress.py`, `test_sdl_realworld.py`, `test_scenarios.py`, `test_example_schema_conformance.py`, `test_runtime_contracts.py`, and `test_pipeline_determinism.py`. These are seeds and regression evidence, not a substitute for the preregistered literature-derived corpus. |
| Research and workflow convention | The related-work and DSL-evaluation bundle/checker/mutation-test patterns, `safe_repo_path`, bounded duplicate-safe JSON loading, `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, `noxfile.py`, `SessionReporter`, `tools/verify_all.py`, and `.github/workflows/ci.yml`. Wire a focused check once into the canonical graph; do not add another CI workflow. |

There is no new controller, HTTP DTO, service, runtime repository, or mutable
persistence layer in the intended design. `RuntimeControlPlane`,
`ControlPlaneStore`, runtime metadata, operation history, audit events, and
backend stores are not homes for literature requests or coverage results.

## Cross-Cutting Validation, Security, And Operational Layers

1. **Research-file and path gate:** load fixed checked-in protocol, snapshot,
   and analysis JSON as inert data through bounded duplicate-key-safe loading.
   Reject unknown fields/ids, dangling refs, duplicate concepts, incomplete
   source strata, unsafe paths, unbounded counts/files, mutable ACES/source
   identities, stale derived results, and non-rectangular concept-stage
   coverage. Resolve every repository path with `safe_repo_path`.
2. **Source and publication gate:** every request retains a stable source id,
   exact locator, coverage stratum, bounded paraphrase, and derivation
   rationale. Repo-local private literature cannot be the only reviewable
   evidence. Preserve bibliographic metadata and permitted excerpts, not
   copied papers or unrestricted third-party source trees. CI performs no
   source refresh.
3. **SDL parser gate:** every scenario enters through the production UTF-8,
   source-format, resource-limit, safe-loader, tag/directive, alias/depth/node,
   duplicate/normalized-key, string-keyed JSON-domain, and migration-policy
   checks. Imports retain path confinement, registry allowlists, lock/digest,
   signature/export, namespace/cycle, and composition-budget checks.
4. **Model/schema gate:** use the existing closed models and validate the
   correctly phased JSON payload against the checked-in published schema when
   schema portability is claimed. Do not generate authority from Python,
   create a corpus SDL DTO, or treat schema acceptance as semantic success.
   Contract JSON artifacts use the published experiment/manifest/plan schema,
   canonical `ContractModel`, and required semantic cross-validator.
5. **Semantic/phase/compiler gate:** semantic validation remains collect-all
   and fail closed. Instantiation must retain typed provenance, reject
   unresolved substitutions, and revalidate. Compiler observations retain
   canonical addresses and every emitted diagnostic. The checker records
   unsupported, lossy, weakened, or absent projections rather than repairing
   or reclassifying them.
6. **Profile/manifest/planner gate:** a profile/manifest classification names
   the exact contract id, version, subject identity, binding, and applicable
   validator/conformance result. Planning uses the existing backend manifest,
   realization-envelope, snapshot, and capability gates. A declared feature,
   one witness, or a successful stub plan is not proof of backend support.
7. **Config and authentication gate:** the offline bundle adds no environment
   binding, runtime configuration, listener, daemon, token, or authorization
   bypass. Protocol inputs are versioned files, not environment-selected
   semantics. No control-plane auth surface is traversed. A future API would
   require `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   target-bound roles, request-size/idempotency/fingerprint guards, audit
   events, and redacted internal errors; issue #164 must not create a weaker
   endpoint.
8. **Secret and information-boundary gate:** use synthetic case values and
   public evidence. Protocols, paths, locators, scenario names, parameters,
   diagnostics, compiled observations, logs, and reports must not contain real
   credentials, bearer tokens, private keys, URI userinfo/query secrets,
   hidden answers, raw prompts, environment dumps, host paths, backend-native
   payloads, or unrestricted source excerpts. Existing `redacted` and
   `operator_secret` omission rules still apply; do not copy legitimate
   scenario fixture secrets into coverage metadata.
9. **OS, network, and supply-chain gate:** default reproduction performs no
   live literature fetch, OCI/module fetch, backend deployment, compared-system
   execution, shell evaluation, Docker/libvirt/cloud access, privileged host
   operation, or dynamic plugin import. Pass no scenario, parameter, token, or
   locator payload through process argv. The checker and in-process production
   entrypoints use bounded fixed repository paths; separately approved live
   realization evidence is outside this issue's default gate.
10. **Error-envelope and observability gate:** preserve public SDL diagnostic
    stage, code when available, severity, bounded message, pointer/range, and
    related location, plus every processor `Diagnostic` field. Repository
    integrity failures are bounded `PolicyFailure` records reported once by
    `SessionReporter`. Do not emit raw exception reprs, Pydantic input values,
    source documents, parameter maps, full generated artifacts, tracebacks, or
    environment state, and do not add a new logger or telemetry stream.
11. **Persistence and integrity gate:** Git-tracked protocol, authored case
    artifacts, sanitized execution snapshot, analysis, source log, and content
    digests are the durable record. Store published portable artifacts or
    bounded observations of an internal compiler model, not a Python repr
    promoted as a contract. Add no database, mutable cache, object store,
    runtime metadata field, audit blob, or result registry.

## Whole-Repository Scope

The implementation must account for the normative authority manifest; SDL
prose, source profile, schemas, fixtures, composition and semantic rules;
scientific-completeness and validation-strength profiles; experiment task,
authoring, apparatus, capture, evidence, run and study contracts; processor,
backend and participant manifests; realization envelopes and disclosures;
compiled addresses, plan schemas and runtime snapshots; source lineage and
research-bundle conventions; positive examples and stress/real-world tests;
known limitations; and the repository policy, schema-publication, generated
schema, JSON artifact, docs, private-key, secret-scanning, and nox verification
graph.

The host/runtime layer is deliberately narrow: ordinary execution is offline,
in-process, unprivileged, and read-only except for normal test temporaries. It
does not traverse the HTTP control plane, runtime store, backend registry,
daemon sockets, cloud credentials, or live target hosts. If a later protocol
adds behavioral realization, that is a separately authorized evidence surface
with its own apparatus, security, redaction, and provenance boundary.

## Extensibility Seam

The stable observation join is:

```text
(protocol_revision, execution_snapshot_revision, aces_revision,
 source_id, request_id, concept_id, carrier_id, artifact_stage)
```

Sources, coverage strata, requests, concepts, carriers, stage obligations, and
classifications are protocol records with stable ids, not Python enums or
hard-coded table columns. The expected next changes—a new literature source,
new benchmark-relevant request, new ACES contract revision, new processor
stage, or new backend/profile realization—add catalog rows and a new execution
snapshot. A changed classification rule, criticality rule, threshold, or
source-selection method creates a new protocol revision. None requires editing
SDL models, experiment contracts, controllers, repositories, error types, or
the prior frozen evidence.

## Gotchas And Anti-Patterns

Avoid:

- treating the existing 19-scenario stress corpus, examples, schema breadth,
  field count, accepted ADRs, or one maintainer-authored showcase as the
  preregistered representative corpus or as a completeness proof;
- classifying a composite request once instead of separating portable intent,
  experiment intent, apparatus constraints, and realization mechanics;
- conflating entity/team roles, node account roles, SDL agents, participant
  implementations, experiment subjects, control-plane identities, or backend
  operators;
- conflating objectives with graded metrics/rewards, workflows with runtime
  operations or participant episodes, evidence requirements with captured
  evidence, apparatus context with scenario meaning, or observed runtime
  inventory with authored intent;
- counting descriptions, tags, notes, generic metadata, ungoverned extensions,
  arbitrary `constraints`, or a backend-private field as typed contract
  coverage;
- accepting parse/schema success as semantic or compiler success, accepting
  object construction while ignoring error diagnostics, or claiming retention
  without exact pointer/address evidence;
- treating internal `RuntimeModel` fields as a published portable contract,
  a plan as proof of execution, one witness as envelope subsumption, or a stub
  backend as independent realization evidence;
- using a Docker/OpenStack/cloud term scan as the backend-neutrality test,
  banning legitimate realization disclosures, or overlooking a dependency
  hidden in prose/free-form values;
- collapsing `missing`, `unsupported`, `invalid`, `not_applicable`, `not_run`,
  `tool_failed`, validation strength, completeness status, and ADR-021 evidence
  status;
- fixing SDL/contracts during the evidence run, weakening a validator to admit
  a case, moving a failed case out of the denominator, or replacing the frozen
  snapshot after a product fix;
- adding invalid research cases to the positive example corpus, making the
  research bundle the only regression for a discovered defect, or copying
  existing validators into the issue checker;
- adding a coverage schema to `contracts/`, a new source registry, parser,
  profile family, exception tree, logger, persistence store, API, or CI
  workflow; and
- making normal verification depend on the network, compared-project code,
  live backends, privileged services, private literature, or secrets.

## Non-Goals And Implementation Boundaries

- Do not add or change SDL syntax, schemas, models, semantic rules,
  diagnostics, compiler/planner behavior, experiment contracts, manifests,
  profiles, backends, examples, or completeness statuses merely to improve the
  result.
- Do not implement gaps found by the protocol. Preserve them as evidence and
  route product changes to separately scoped issues and owning authority
  surfaces.
- Do not deploy a cyber range, execute autonomous participants, compare agent
  quality, prove backend substitution, or certify independent backend
  implementability.
- Do not claim universal cyber-range coverage, scientific adequacy, usability,
  adoption, standardization, behavioral equivalence, or backend neutrality
  beyond the exact preregistered sources, concepts, carriers, stages, ACES
  revision, and evidence.
- Do not create a normative ADR, formal specification, ecosystem interchange
  schema, hosted service, controller, repository, database, dashboard, or
  migration system for this research bundle.
