# Issue 178 Researcher Accessibility Protocol Preflight

Date: 2026-07-17

Issue: #178. Requirement: none.

Issue #178 is a falsification/evidence gate for a bounded accessibility claim,
not an SDL feature, authoring-tool redesign, or backend design. The issue body
is the authoritative contract.

No new ADR is needed. ADR-021 already governs claim evidence, ADR-009 and
ADR-019 govern artifact authority, and the issue-346 DSL language-evaluation
preflight already establishes the applicable protocol/snapshot/analysis,
privacy, semantic-stage, and research-integrity boundaries. This note fixes the
#178-specific guardrails without running the study, preparing its task corpus,
collecting evidence, or correcting gaps that the study may expose.

## Decision Boundary

Keep three independently revisioned concerns:

1. **Preregistered protocol:** the four issue personas, their qualification and
   infrastructure-experience bands, bounded positive and negative tasks,
   allowed public surfaces, assistance conditions, intended semantics,
   measures, denominators, pass/fail thresholds, stopping and missing-data
   rules, privacy constraints, and validity threats.
2. **Execution snapshot:** the exact ACES revision and public docs, examples,
   guidance, adapters, modes, and parameters supplied to each subject; sanitized
   attempts and submitted artifacts; exact public diagnostics; wrong turns,
   assistance, review judgments, deviations, withdrawals, and missing or
   abandoned attempts.
3. **Claim-scoped analysis:** recomputed results for the #178 accessibility
   claim, its objective pass/fail disposition, limitations, and ADR-021 evidence
   status. A versioned manifest binding fixes the stable claim id's exact
   persona, task, condition, stage, dimension, and measure scope. The analysis
   must repeat that scope exactly and persist independently recomputed results
   for each preregistered gating and comparison stratum.

Reuse the structure and integrity machinery under
`docs/research/dsl-language-evaluation/` and
`tools/check_dsl_language_evaluation.py`. The #346 language-adequacy claim and
the #178 researcher-accessibility claim remain separate analyses even when they
reuse a protocol, task, attempt, or observation. A result for one claim must not
silently promote or refute the other. Preserve existing frozen artifacts; a
changed construct, task meaning, rubric, threshold, or exclusion rule creates a
new protocol revision, while a tool/doc refresh or new execution creates a new
snapshot.

Do not introduce a second research schema, a second parser/validator hierarchy,
or a parallel persistence and reporting workflow. If the current research
bundle cannot express more than one scoped claim, the only justified seam is a
claim analysis that selects stable protocol ids; it is not a generic research
platform or a new normative contract family.

The following concepts remain distinct:

| Concept | Boundary |
| --- | --- |
| Accessibility | Correct completion by the stated persona using only the pinned public condition, not feature count, parser success, or maintainer familiarity. |
| Expressibility | Whether the intended benchmark meaning is representable or explicitly dispositioned, not whether a YAML document can be constructed. |
| Validity | Structural and semantic acceptance by the production SDL boundary, not deployability, benchmark adequacy, or accessibility. |
| Unsupported request | A validly recognized boundary that public guidance or diagnostics teaches clearly; it is not interchangeable with invalid YAML, underspecification, profile dependence, or a missing implementation. |
| Diagnostic usefulness | Whether the exact public response locates and explains the defect and supports a correct repair, not whether an internal exception contains enough information. |
| Infrastructure independence | No task success depends on cloud, Terraform, OpenStack, Docker, deployment manifests, backend source, or undocumented backend conventions. It does not claim that installing Python tooling has zero prerequisites. |
| Study subject | A researcher or reviewer in the evidence protocol, never an SDL `participant`, participant implementation, agent, or runtime principal. |
| Evidence status | ADR-021 `untested`/`partial`/`demonstrated`/`refuted`, separate from task outcome, validation result, review status, requirement status, and ADR status. |

## Persona, Task, And Evidence Guardrails

- Use stable persona ids for `security-researcher`, `benchmark-designer`,
  `backend-implementer`, and `evaluator-reviewer`. Reuse the existing latter
  three ids and meanings. Do not relabel a scenario author as a security
  researcher without the issue's qualification boundary. Record relevant SDL,
  cyber-range, cloud/container, programming, and benchmark experience as
  bounded bands rather than names, employers, or free-form biographies.
- Treat the backend implementer as a comparison and boundary-testing persona,
  not as evidence that a non-infrastructure expert succeeded. Report each
  persona, experience band, and tooling condition before any pooled result.
  Preregister which strata gate promotion. A pooled result or comparison
  population cannot mask a target-stratum failure or promote the claim.
- Separate `public-docs-only`, MCP, CLI, and direct documented-library
  conditions. Pin the exact artifact or tool name, adapter, mode, ACES commit or
  release, source/migration profile, parameters, and assistance policy. Do not
  aggregate `sdl_validate` prose, `sdl_diagnostics` structured records,
  parse-only inspection, and stub-backend planning as one equivalent “public
  tools” condition.
- Derive non-trivial tasks from the current scenario corpus, example library,
  participant/information-boundary semantics, and benchmark-relevant tasks
  already preregistered by the DSL language evaluation. Preserve source ids and
  a derivation rationale. A minimal tutorial scenario alone cannot satisfy the
  issue's benchmark-relevance criterion.
- Preregister at least positive authoring/review tasks and focused invalid,
  unsupported, underspecified, and profile-dependent cases. Give each negative
  case one intended defect or boundary. Do not rewrite one outcome class as
  another after observing the response.
- Seal intended semantics and scoring rubrics before execution. Correct task
  completion requires semantic agreement with that record at the owning
  artifact stage; a file that parses, validates, or produces a plan is not
  automatically correct. Independent reviewers fix their judgments before the
  sealed intent is revealed, and disagreement remains observable after
  adjudication.
- Measure completion, critical semantic errors, ambiguity/wrong-turn classes,
  prohibited assistance or source-inspection requests, repair cycles,
  diagnostic localization and repair, and public-surface gaps. Predeclare
  denominators, timing treatment, task order, repetitions, exclusions,
  missing-data handling, and stopping rules. Missing, abandoned, tool-failed,
  and withdrawn attempts remain explicit according to those rules.
- Record a missing doc, example, glossary entry, guidance rule, diagnostic
  field, or unsupported-boundary explanation as evidence. Do not edit the live
  surface mid-run or replace the failed snapshot. A later product correction is
  a separate issue and can be evaluated in a new snapshot.
- Human recruitment and raw-data collection require the applicable ethics,
  consent, privacy, and data-protection review. Simulated personas, maintainers,
  or agent walkthroughs are exploratory evidence only and cannot demonstrate a
  generalized researcher-accessibility claim.
- Keep the claim `untested` until qualifying observations exist. `Demonstrated`
  applies only to the exact preregistered population, tasks, conditions,
  versions, and thresholds; it is not a universal ease-of-use or backend-
  independence claim.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and boundary |
| --- | --- |
| Authority and claim discipline | ADR-009/019, `specs/authority/authority-boundary.yaml`, ADR-021, and the documentation style guide. Research under `docs/` is non-normative and cannot redefine SDL meaning. |
| Research bundle and integrity | `docs/research/dsl-language-evaluation/`, its issue-346 preflight, `tools/check_dsl_language_evaluation.py`, `tools.policy.common.load_bounded_json_object`, `safe_repo_path`, and `PolicyFailure`. Reuse the closed protocol/snapshot/analysis graph and recomputation rules; do not copy them into an accessibility-only framework. |
| Public authoring guidance | `docs/explain/getting-started.md`, `docs/explain/sdl/`, `docs/explain/reference/glossary.md`, `specs/sdl/`, `specs/agent-guidance/agent-guidance.yaml`, `aces_agent_guidance`, and `aces_intended_use_profiles`. The repository's materialized canonical guidance profile is AUT-811; do not create an AUT-807-labeled duplicate solely to mirror the issue context. |
| Examples and templates | `examples/scenarios/`, `examples/library/catalog.yaml`, `examples/library/templates/`, `examples/library/patterns/`, and `tools/check_example_library.py`. Positive examples stay non-normative and parser-validated; invalid research stimuli do not belong in the positive library. |
| Source syntax and shape | `sdl-yaml/v1`, `SDLParserLimits`, `_SDLSafeLoader`, mapping-key analysis, `parse_sdl()`/`parse_sdl_file()`, closed `SDLModel` descendants, and the published SDL schemas and source-profile fixtures. The normalized JSON Schema is not a raw-YAML validator. |
| Static semantics | `SemanticValidator`, `specs/sdl/references.md`, `specs/sdl/diagnostics.md`, and the shared declaration/reference indexes. The study observes production acceptance and never adds study-local reference resolution or validation exceptions. |
| Language-service and MCP surfaces | `aces_sdl.language_service`; `aces_mcp.tools.reference`, `authoring`, `language_service`, `inspection`, and `operations`; and `implementations/python/tests/test_language_service.py` / `test_mcp_server.py`. Record the exact entrypoint and mode because these adapters intentionally expose different envelopes and validation strength. |
| Later artifact stages | `instantiate_scenario()`, instantiated-SDL admission and canonicalization, `compile_runtime_model()`, processor `Diagnostic`/`Severity`, the reference processor, and `plan()`. Stub planning is a bounded capability check, not deployment or runtime evidence. |
| Error and reporting patterns | `SDLParseDiagnostic`, `SDLParseError`, `SDLValidationError`, `SDLInstantiationError`, processor `Diagnostic`/`Severity`, `PolicyFailure`, and nox `SessionReporter`. Do not add an accessibility exception hierarchy, logger, or telemetry channel. |
| Persistence and workflow | Git-tracked sanitized research artifacts, `.ground-control.yaml`, `.gc/plan-rules.md`, `.pre-commit-config.yaml`, ADR-014, `noxfile.py`, private-key detection, gitleaks, Sphinx, and `.github/workflows/ci.yml`. Add at most one call in the existing nox graph; never create a parallel workflow. |

There is no controller, HTTP DTO, service, runtime repository, control-plane
store, or mutable database in the intended design. `RuntimeControlPlane`,
`ControlPlaneStore`, runtime snapshots, backend audit events, experiment-run
records, and participant history are not stores for author/reviewer study data.

## Cross-Cutting Security, Validation, And Operational Layers

1. **Research-file shape gate:** research artifacts are inert, local, bounded
   JSON. Reuse duplicate-key rejection, exact-field checks, bounded ids/counts,
   referential integrity, recomputed results, and `safe_repo_path`. Reject
   absolute/traversing/symlink-escaping paths, unpinned surfaces, unsafe URI
   userinfo/query data, stale aggregates, and incomplete persona/task/condition
   coverage.
2. **SDL source gate:** every submitted SDL artifact enters through production
   UTF-8 handling, the YAML 1.2 Core resolver, `_SDLSafeLoader`, tag/directive
   rejection, duplicate and normalized-key collision checks, string-keyed JSON
   domain enforcement, and `SDLParserLimits` for input, scalar, depth, node,
   alias, import, composition, and expansion work. MCP/language-service tools
   retain their 64 KiB adapter bound; the direct parser's larger bound is not a
   reason to bypass an adapter condition.
3. **Model/schema and config-shape gate:** construct the existing closed
   `SDLModel`/`Scenario` shapes (`extra="forbid"`) and use a published schema only
   for the matching normalized phase. Representative runtime configuration
   still passes its owning validators. In particular,
   `RuntimeEnvironmentVariable` and `enforce_observed_value_redaction`,
   `RuntimeInitProcess.argv_redacted`, SSH/sudo command-redaction rules, and
   `RuntimeAppAuthorizationPrincipal`'s no-raw-credential shape remain active
   when a task touches those surfaces. Do not create a study SDL DTO or weaken
   a model to make a task pass.
4. **Semantic and composition gate:** run `SemanticValidator` with its existing
   collect-all, ambiguity, uniqueness, graph, profile, and redaction rules.
   Imported material retains base-directory confinement, registry allowlists,
   lock/version/digest/signature/export checks, namespace and cycle rules, and
   composition budgets. An offline study must not fetch an OCI/import source or
   inspect a backend to repair meaning.
5. **Instantiation/processor gate:** when a task claims more than authored SDL
   validity, use existing instantiation/admission, canonicalization, compiler,
   reference-processor, and planner entrypoints. Preserve unsupported,
   degraded, and diagnostic outcomes. Never infer success from a filename, raw
   mapping, backend label, or hand-built summary.
6. **Tool-adapter and environment gate:** source profile, migration policy,
   semantic-validation mode, intended-use profile, adapter, assistance, and
   task condition are explicit protocol data, not environment-selected
   semantics. Add no issue-specific environment variable, daemon, listener,
   backend profile, or auth bypass. Installation/setup friction is observable
   separately from task correctness.
7. **Authentication and authorization gate:** the current MCP study surface is
   local stdio and the evidence checker is offline, so #178 traverses no HTTP
   authentication or control-plane authorization layer. Do not add one. A
   future hosted surface requires a separate decision and must reuse
   `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   target-bound roles, request-size/idempotency/fingerprint guards, audit
   events, and redacted internal errors.
8. **Secret and privacy gate:** tasks use synthetic facts or governed public
   examples. Published artifacts, diagnostics, study metadata, and logs contain
   no real credentials, tokens, private keys, environment dumps, live
   infrastructure identifiers, private prompts, hidden answers, raw backend
   objects, unrestricted subject text, or pseudonym linkage keys. Existing
   `redacted`/`operator_secret` omission rules remain authoritative; a digest is
   not redaction and pseudonymized data is not anonymous data.
9. **OS, network, and supply-chain gate:** pass SDL through files or MCP message
   bodies, not secret-bearing process arguments. The study checker performs no
   network access, shell evaluation, backend deployment, container/cloud
   invocation, privileged host operation, or compared-project code execution.
   Existing pinned nox/CI bootstrap is the only default tool-install path; live
   range execution is outside this issue and must not become a CI prerequisite.
10. **Error-envelope and observability gate:** capture what the selected public
    entrypoint actually emits. Preserve parser code, stage, severity, bounded
    message, path/range, authored-key and related-location data when present;
    preserve processor code/domain/address/severity/message when present.
    `sdl_validate` prose, language-service JSON, inspection's parse-only prose,
    and operation-stage JSON are not interchangeable. Missing location, code,
    or repair direction is evidence, not permission to read source, synthesize
    fields, emit a traceback, or dump Pydantic input/environment state. Use
    content-based entrypoints or a declared sanitized projection so absolute
    host paths never enter the public bundle.
11. **Persistence and integrity gate:** the durable public record is the
    Git-tracked protocol, sanitized immutable snapshot, claim-scoped analysis,
    source/public-surface inventory, and checksums. Raw human-subject material,
    if approved for collection, stays in the approved controlled store and
    retention regime. Add no database, mutable cache, object store, runtime
    metadata field, audit blob, or result registry.

## Whole-Repository Scope

The evidence design must account for all of these surfaces without editing them
merely to improve the result:

- normative SDL prose, diagnostics, references, scientific-completeness and
  authority material under `specs/` and `contracts/`;
- explanatory authoring docs, glossary, limitations, language-service guide,
  non-trivial scenarios, templates, and patterns;
- SDL source profiles, parser/model/semantic/composition/instantiation layers,
  canonical artifacts, compiler/planner contracts, and their negative tests;
- the machine-readable agent guidance, intended-use profiles, CLI, MCP
  reference/authoring/language/inspection/assessment surfaces, and adapter
  tests;
- redaction, environment/config, command/argv, import trust, information-
  boundary, observability, and diagnostic contracts touched by selected tasks;
- the existing language-evaluation research bundle and checker; and
- the canonical Ground Control, policy, contracts, tests, docs, secret scan,
  hooks, nox, and CI graph.

Every ambiguity, backend-private assumption, divergent public explanation,
unhelpful diagnostic, unsupported request, missing example, tool-setup failure,
reviewer disagreement, or prohibited source-inspection request is an evidence
result. It is not authorization to modify the owning surface during the study.

## Extensibility Seam

The stable observation join is:

```text
(protocol_revision, snapshot_id, claim_id, persona_id, subject_id,
 condition_id, task_id, variant_id, attempt_id, artifact_stage_id, measure_id)
```

`subject_id` is study-local and pseudonymous and appears publicly only when the
applicable review permits that minimized projection. Personas, task classes,
public surfaces, adapter/mode conditions, stages, measures, and claim scopes are
versioned protocol data with stable ids, not Python enums or hard-coded issue
branches. The next public adapter, researcher experience band, scenario family,
or independent replication adds catalog records and a new snapshot. A new
claim adds a separately scoped analysis over eligible frozen observations. None
requires editing SDL models, contracts, controllers, repositories, or prior
evidence.

## Gotchas And Anti-Patterns

Avoid:

- claiming accessibility from schema completeness, parser success, accepted
  ADRs, example count, one maintainer, an agent simulation, or the existing
  not-started #346 snapshot;
- pooling backend implementers with non-infrastructure experts or treating
  prior cloud/container knowledge as an unrecorded subject characteristic;
- treating docs-only, MCP, CLI, direct-library, parse-only, semantic, migration,
  and stub-planning conditions as equivalent;
- counting a syntactically valid but semantically wrong scenario as completed,
  or treating `structural_only`/parse-only success as full validation;
- collapsing invalid, unsupported, underspecified, profile-dependent,
  unavailable, missing, abandoned, withdrawn, and not-applicable outcomes;
- scoring diagnostics by message substring alone or enriching a weak public
  response from implementation exceptions, models, tests, or backend source;
- changing docs, examples, guidance, diagnostics, or product behavior during
  execution and overwriting the falsifying observation;
- putting invalid study cases in `examples/scenarios/`, turning research cases
  into normative fixtures, or using the research bundle as the only regression
  for a discovered defect;
- adding an accessibility schema under `contracts/`, a second guidance profile,
  duplicate SDL DTO/model/validation/exception/logging stacks, or a separate CI
  workflow;
- storing study data in experiment-run, runtime, control-plane, participant,
  evidence, or backend repositories merely because those records already
  persist other kinds of observations; and
- committing raw chats/prompts, recordings, biographies, host paths, secrets,
  hidden answers, source dumps, or a pseudonym linkage key.

## Non-Goals And Implementation Boundaries

- Do not change SDL syntax, schemas, models, parser or semantic behavior,
  diagnostics, examples, guidance, compiler/planner behavior, backends,
  completeness profiles, or migration behavior merely to improve #178's
  outcome.
- Do not implement gaps found by the protocol. Record them and route each later
  correction to its owning docs, glossary, example, guidance, validator, tool,
  or backend issue while preserving the original observation.
- Do not deploy a range, execute participant cyber actions, evaluate model
  quality, prove backend portability, or require cloud, Terraform, OpenStack,
  Docker, or backend-private source for the study.
- Do not create a universal usability/research-evidence schema, hosted study
  service, API, controller, UI, database, analytics pipeline, participant
  telemetry system, or recruitment workflow.
- Do not claim general usability, scientific adequacy, productivity,
  deployability, runtime success, or infrastructure independence beyond the
  exact preregistered population, tasks, conditions, versions, and evidence.
