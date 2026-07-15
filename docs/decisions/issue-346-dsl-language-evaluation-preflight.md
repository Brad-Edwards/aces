# Issue 346 DSL Language-Evaluation Preflight

Date: 2026-07-15

Issue: #346. Requirement: ASR-530.

ASR-530 supplies the claim-evidence rule. The issue body supplies this
protocol's research question, dimensions, tasks, and pass/fail criteria.

This note fixes architecture guardrails for evaluating ACES as a language. It
does not run the study, select study subjects, author its task corpus, change
SDL, or implement gaps found by the evaluation. No new ADR is needed: the existing
authority, claim-evidence, participant-semantics, validation-strength,
evolution, phase-contract, and source-provenance decisions already govern this
work.

## Decision Boundary

Issue #346 is a falsification/evidence bundle, not a language feature or a new
kind of SDL validity. Keep three independently revisioned concerns, following
the established related-work research bundle:

1. **Preregistered protocol:** dimensions, constructs, personas, sampling and
   experience bands, tasks and mutations, intended semantics, assistance and
   tooling conditions, artifact stages, measures, thresholds, missing-data and
   disagreement rules, validity threats, source pins, and amendments.
2. **Execution snapshot:** the exact ACES revision and public-document/tool
   surface, pseudonymous attempts, bounded observations, submitted SDL,
   production-stage outputs and diagnostics, reviewer judgments, deviations,
   withdrawals or abandoned attempts, and preserved disagreements.
3. **Analysis and claim record:** recomputed measures, pass/fail disposition,
   limitations, and ADR-021 evidence status with exact protocol and snapshot
   references.

Keep the non-normative bundle under the existing `docs/research/` convention,
in a dedicated language-evaluation directory. Do not publish it as an SDL JSON
Schema, add it to `aces_contracts`, or place research state in a runtime store.
If machine-readable records are used, one focused offline checker owns their
closed shape and cross-record invariants. It should reuse, or extract for reuse,
the bounded duplicate-key JSON-loading and safe-path idiom already used by
`tools/check_related_work_comparison.py`; it must not copy a second generic
schema/exception/logging framework.

The following constructs remain separate. A result in one column is not a
proxy for another.

| Dimension | Boundary |
| --- | --- |
| Expressiveness | Whether the declared experimental meaning is representable, not whether parsing succeeds or every possible field exists. |
| Comprehension/usability | Whether a stated persona can understand and use the public surface under a declared assistance condition, not feature breadth or maintainer familiarity. |
| Effectiveness/productivity | Task outcome, effort, error and rework measures against preregistered criteria, not elapsed time alone or a self-report alone. |
| Maintainability/evolution | Whether a controlled change preserves, changes, or invalidates declared meaning with visible migration status, not mere editability. |
| Ambiguity | Whether one artifact has more than one materially defensible meaning or two intended-equivalent authorings diverge undetected, not ordinary syntax flexibility. |
| Diagnostic quality | Whether bounded public diagnostics locate and explain a defect and guide a valid repair, not merely whether an exception occurred. |
| Reviewability | Whether an independent reviewer can identify meaning, changes, assumptions and information boundaries, not author-reviewer agreement by itself. |
| Semantic traceability | Whether intent can be followed through authored, expanded, instantiated, compiled and planned artifacts without backend-private interpretation, not path or digest presence alone. |

Scenario completeness profiles, validation/admission strength, semantic
coverage, backend conformance, researcher accessibility, and language adequacy
are related but distinct claims. In particular, `valid-sdl-fragment` or an
implemented scientific-completeness row does not demonstrate language
adequacy; issue #346 must not revise those profile meanings or store its result
as a new profile status.

ADR-021 evidence status is also not Ground Control requirement status, ADR
status, task outcome, attempt completion, review/adjudication status, or
validation strength. Store and report each axis independently. Likewise, call
a human who authors or reviews study material a `subject` or `reviewer`; reserve
`participant` for the SDL participant/agent concept. A study subject is not an
ACES participant implementation or participant-semantics record.

## Protocol And Evidence Guardrails

- Freeze all six issue personas as stable ids: benchmark designer, scenario
  author, participant-model author, backend implementer, evaluator/reviewer,
  and assurance auditor. Record relevant experience and assistance as bounded
  bands, not names, employers, free-form biographies, or a claim that one
  maintainer represents a population.
- Derive representative tasks from the already cited cyber-range/agent corpus,
  the frozen tasks in `docs/research/related-work-comparison/protocol-v1.json`,
  the participant-semantics obligations, and current non-trivial ACES examples.
  Preserve a source locator and derivation rationale. Do not substitute a
  hand-picked minimal example or the test-local `LanguageEvaluation` oracle for
  the issue's task corpus.
- Preregister positive, negative, unsupported, underspecified, and deliberately
  ambiguous cases. A negative case has one injected defect. Record
  `invalid`, `unsupported`, `underspecified`, and `profile-dependent` as
  different outcomes; none may be rewritten as another after observing tool or
  participant performance.
- Separate the sealed intended-semantics record from material supplied to an
  independent reviewer. Reviewers receive only the preregistered public
  artifacts for their condition. Reveal intent for scoring/adjudication only
  after the judgment is fixed, and preserve disagreement instead of replacing
  it with consensus prose.
- Predeclare the unit of analysis, denominators, thresholds, assistance,
  repetitions, task order/counterbalancing, time/error/rework capture,
  exclusion and missing-data handling, and stopping rule. Missing, abandoned,
  withdrawn, or tool-failed attempts remain in the denominator according to
  that rule; post-hoc task or threshold selection is a failed protocol.
- Actual human participation requires the applicable institutional ethics,
  consent, privacy, and data-protection review before collection. Commit only
  the public projection authorized by that review: normally aggregate records,
  or specifically approved minimized study-local pseudonyms with no linkage
  key in the repository. Pseudonymized data is not anonymous data. Names, email
  addresses, recordings, raw chats/prompts, keystroke streams, and unrestricted
  free text belong outside the repository in an approved controlled store, if
  collected at all. Simulated personas, maintainers, or agent walkthroughs are
  exploratory evidence and cannot support a generalized usability or
  productivity claim.
- Every tool-assisted attempt pins the ACES commit/release, source profile,
  canonicalization profile, contract ids, public documentation paths, tool and
  adapter, assistance condition, and parameters. Backend source, private
  prompts, undocumented conventions, or manual repair after scoring cannot be
  silent inputs.
- Every public claim retains ADR-021 threats, falsification criteria, named
  evidence, and one of `untested`, `partial`, `demonstrated`, or `refuted`.
  A preregistered protocol without completed independent evidence remains
  `untested` or `partial`.

## Semantic Identity And Mutation Boundary

Each task or mutation must declare the relation it expects and the artifact
stage on which that relation is observed. Do not use a generic `equivalent`
flag.

- Source-format variants may be expected to converge only after explicit
  migration and strict reparse.
- Authoring-meaning equivalence may be checked with
  `canonical_sdl_bytes()`/`canonical_sdl_digest()` only after expansion and
  semantic validation.
- Concrete equivalence after parameter binding uses admitted instantiated
  snapshots and `canonical_instantiated_sdl_digest()`.
- Processor-facing traceability uses canonical addresses and typed output from
  `compile_runtime_model()` and `plan()`.
- Reviewer equivalence is a separate observation with its own rubric and
  disagreement record.

Digest equality proves identity under the named canonicalization profile. It
does not prove behavioral, observational, epistemic, strategic, backend, or
scientific equivalence. Conversely, a source-byte or formatting difference is
not automatically a semantic difference. A mutation that changes hidden
assets, participant visibility, observations, outcomes, action meaning,
realization posture, or experiment controls must be assessed at the owning
semantic/artifact stage; it must not be hidden by comparing only a topology or
plan summary.

Maintenance exercises also pin source and target surface versions and the
claimed compatibility dimension from ADR-075: structural, semantic,
behavioral, or operational. A migration that parses is not thereby
meaning-preserving. Preserve invalidation, lossy/ambiguous migration, and
replacement status explicitly.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required boundary |
| --- | --- |
| Authority and claims | ADR-009/019, `specs/authority/authority-boundary.yaml`, ADR-021, and the documentation style guide. Research reports evidence; it does not define SDL meaning or promote a claim from prose. |
| Research bundle and sources | `docs/research/related-work-comparison/`, issue-728's protocol/snapshot/analysis split, `tools/check_related_work_comparison.py`, ADR-080, the SDL lineage ledger, and the source-audit/search-log patterns. Reuse source identities where they already exist; do not turn lineage into a study-results ledger. |
| Study personas and SDL participant semantics | The issue's six study personas; ADR-022, `specs/formal/participant-semantics/`, participant information-boundary invariants, and the existing `LanguageEvaluation` test oracle only as prior evidence of the obligation. Keep human subjects/reviewers separate from SDL participants, and do not promote the test-local dataclass into a contract. |
| Authoring corpus | `examples/scenarios/`, `examples/library/catalog.yaml`, `test_sdl_realworld.py`, `test_sdl_stress.py`, `enterprise-participant-evidence-loop.sdl.yaml`, and the related-work tasks. Reuse these by reference where suitable; invalid evaluation cases do not belong in the positive example corpus. |
| Concrete syntax and shape | `sdl-yaml/v1`, `SDLParserLimits`, `_SDLSafeLoader`, mapping-key analysis, `parse_sdl()`/`parse_sdl_file()`, closed `Scenario`/`InstantiatedScenario` models, and the checked-in SDL schemas and source-profile fixtures. The normalized schema is not a raw-YAML validator. |
| Static semantics | `SemanticValidator`, `specs/sdl/references.md`, `specs/sdl/diagnostics.md`, shared declaration/reference indexes, and fail-closed ambiguity/uniqueness/graph rules. Do not implement evaluation-only acceptance or reference resolution. |
| Tools and diagnostics | SDL CLI formatting/import verification; MCP authoring, language-service, inspection, design-assessment and claims-assessment tools; `SDLParseDiagnostic`, `SDLParseError`, `SDLValidationError`, `SDLInstantiationError`, `Diagnostic`, and `Severity`. Record the exact public entrypoint and mode: parse-only summaries are not semantic validation, inspection tools deliberately skip semantic validation, prose authoring responses are not structured language-service diagnostics, and stub planning is not backend evidence. |
| Phase traceability | `instantiate_scenario()`, `admit_instantiated_scenario()`, canonical SDL/snapshot profiles, `compile_runtime_model()`, the reference processor, `plan()`, canonical addresses, and pipeline-determinism tests. Compare typed artifacts, not raw dictionaries or backend labels. |
| Evolution | ADR-053/075/078, module/import/lock/trust handling, `specs/evolution/`, migration diagnostics, deprecation records, and canonical phase identities. Do not add an evaluation-specific version or migration registry. |
| Experiment method | ADR-055/064/065/068/074 and existing metric, evaluation-protocol, validity-note, factor, allocation, analysis, evidence, and study concepts. Reuse their meanings and validators when a record is genuinely an instance; do not mislabel a human authoring attempt as an `ExperimentRunModel` or weaken those contracts to fit this study. |
| Workflow and reporting | `.ground-control.yaml`, `.gc/plan-rules.md`, `.pre-commit-config.yaml`, ADR-014, `noxfile.py`, `SessionReporter`, repository policy, contract checks, Sphinx, `tools/verify_all.py`, private-key detection, and gitleaks. Wire any focused checker once into the canonical graph consumed by `.github/workflows/ci.yml`; do not add a parallel CI workflow. |

There is no new controller, HTTP DTO, service, runtime repository, or mutable
persistence layer in the intended design. `RuntimeControlPlane`,
`ControlPlaneStore`, runtime snapshots, audit events, and backend operation
envelopes are not stores for author/reviewer study state.

## Cross-Cutting Validation, Security, And Operational Layers

1. **Research-file gate:** load fixed checked-in protocol/snapshot/analysis data
   as inert content. Reject duplicate or unknown fields and ids, dangling refs,
   duplicate attempts, missing required persona/task/mutation coverage, unsafe
   paths, unpinned sources/toolchains, unbounded files/counts, stale derived
   output, and secret-bearing URI userinfo or query parameters. Resolve every
   repository path with `safe_repo_path`.
2. **SDL source gate:** every authored attempt enters through the production
   UTF-8 and `SDLParserLimits` checks, YAML 1.2 Core resolver, safe loader,
   tag/directive rejection, scalar/input/depth/node/alias/composition limits,
   duplicate and normalized-key collision checks, string-keyed JSON-domain
   validation, and explicit source/migration profile. No pre-parse YAML
   round-trip or evaluation-only loader is allowed.
3. **Model/schema gate:** construct the existing closed SDL models and, where
   schema conformance is claimed, validate the correctly phased JSON payload
   against the checked-in published schema. Do not use generated schema output
   as authority, create a study-specific SDL DTO, or treat schema acceptance as
   semantic success.
4. **Semantic/composition gate:** run `SemanticValidator` with collect-all,
   fail-closed reference, ambiguity, uniqueness, graph, profile and redaction
   rules. Imported scenarios additionally retain base confinement, lockfile,
   registry allowlist, version, digest, signature, export, namespace, cycle and
   composition-budget checks. The evaluation observes these results; it never
   bypasses or reclassifies them.
5. **Instantiation/processor gate:** when a task claims later-stage fidelity,
   use existing instantiation/admission, canonicalization, compiler, reference
   processor and planner entry points. Preserve diagnostics and unsupported or
   degraded output. Never infer machine distinction from a filename, raw YAML
   dictionary, backend-private field, or hand-built summary.
6. **Tool-adapter/config gate:** public MCP authoring/language/inspection paths
   retain their 64 KiB adapter limits; direct parser limits remain the library
   bound. Source format, migration policy, task condition, and assistance level
   are explicit protocol inputs, not ambient environment switches. Add no
   runtime config, listener, daemon, profile selector, or auth bypass. The
   exact public adapter response is evidence for that adapter condition; do not
   inspect an internal exception or model to silently enrich, repair, or
   reinterpret a public response.
7. **Authentication and information-boundary gate:** the offline evaluation
   adds no endpoint and traverses no control-plane authorization surface. If a
   future service exposes results, it must reuse
   `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   target-bound roles, request-size/idempotency/fingerprint guards, audit
   events, and redacted internal errors. Reviewer blinding and hidden-intent
   separation are study information boundaries, not bearer-token roles.
8. **Secret and privacy gate:** use synthetic scenario facts or already
   governed public examples. Authoritative SDL can legitimately contain
   exercise credentials under ADR-057, but published study projections,
   diagnostics, locations, task metadata, subject/reviewer records, and logs must
   never contain real operator credentials, tokens, private keys, environment
   dumps, absolute host paths, hidden answers, private prompts, raw backend
   objects, or unrestricted subject text. Normalize public locations to
   repository-relative paths or task artifact ids. Explicit
   `redacted`/`operator_secret` omission rules remain enforced; a digest is not
   redaction, and a pseudonymization linkage key never belongs in the bundle.
9. **OS, network, and supply-chain gate:** the study checker and reproduction
   path perform no live study-source or OCI import fetch, compared-project code
   execution, backend deployment, shell evaluation, privileged host access, or
   secret-bearing argv. Existing nox/CI may bootstrap its already-governed,
   pinned tools; issue #346 adds no downloader or executable dependency. Any
   separately approved behavioral execution uses a pinned, resource-bounded
   isolated apparatus with no repository/operator secrets and records only
   bounded, redacted evidence. It must not become a default CI dependency.
10. **Error-envelope and observability gate:** preserve SDL diagnostic code,
    stage, severity, bounded message, path/range and related locations when the
    selected public entrypoint emits them; absence is a diagnostic-quality
    observation, not permission to synthesize fields from internals. Preserve
    every processor `Diagnostic` field that is emitted. Research-integrity
    failures use bounded `PolicyFailure` records and `SessionReporter`. Do not
    add an issue-specific exception hierarchy, logger or telemetry stream, and
    do not dump source, parameter maps, raw responses, Pydantic input,
    tracebacks or environment state.
11. **Persistence and integrity gate:** Git-tracked protocol, sanitized
    execution snapshot, analysis, source log and checksums are the durable
    public record. Raw human-subject data, if any, follows its approved external
    retention boundary. Add no database, mutable cache, object store, runtime
    metadata field, audit blob, or result registry.

## Whole-Repository Scope

The implementation must review and, only where evidence requires it, reference
the canonical SDL prose and contracts; source-profile and conformance fixtures;
positive examples and test-only stress/real-world corpora; participant,
information-boundary, observability and outcome semantics; phase identities,
compiler/planner artifacts and determinism tests; language-service, CLI and MCP
authoring/inspection surfaces; scientific-completeness and validation-strength
profiles; evolution and deprecation policy; lineage/source records; research
bundle conventions; and the `.ground-control.yaml` / `.gc/plan-rules.md` /
`.pre-commit-config.yaml` / `noxfile.py` / `.github/workflows/ci.yml` canonical
policy, contracts, tests, docs, private-key, and secret-scanning graph.

It must not edit those owning surfaces merely to make the evaluation pass.
Every ambiguity, unsupported expression, backend-private assumption,
diagnostic failure, reviewer disagreement, migration failure, missing attempt,
or information-boundary leak is an evidence gap. A product correction belongs
to a separately scoped issue and the owning parser/spec/contract/test surface;
the original failed observation remains in the frozen snapshot.

## Extensibility Seam

The stable observation join is:

```text
(protocol_revision, study_run_id, task_id, persona_id, subject_id,
 tooling_condition_id, attempt_id, variant_id, artifact_stage)
```

`subject_id` is pseudonymous and local to the controlled study; it appears in a
public snapshot only when the applicable review permits that minimized
projection, and never with its linkage key. Dimensions, personas, tasks,
tooling/assistance conditions, variants/mutations, artifact stages, and measures
are protocol data with stable ids, not Python enums or table columns.
The obvious next variation—a new persona, tool surface, SDL/profile revision,
task, mutation family, or independent-review wave—adds catalog records and a
new execution snapshot. A changed construct, rubric, threshold, sampling rule,
or task meaning creates a protocol revision. A source/tool refresh creates a
new snapshot. Neither requires editing SDL models, contracts, controllers,
repositories, exception types, or the prior frozen evidence.

## Gotchas And Anti-Patterns

Avoid:

- inferring adequacy from schema completeness, successful parsing, accepted
  ADRs, formal prose, example count, field count, or one author's success;
- allowing `structural_only`, parse-only inspection, migration acceptance, or
  stub-backend planning to masquerade as full semantic or behavioral evidence;
- treating all author variation as ambiguity, or author-selectable specificity
  as permission for materially different hidden semantics;
- treating reviewer agreement as correctness, disagreement as documentation
  debt, or adjudicated consensus as the original independent result;
- treating canonical digest equality as behavioral equivalence, a changed
  digest as proof of material change, or a stable plan summary as proof that
  participant visibility/outcome meaning was preserved;
- collapsing invalid, unsupported, underspecified, profile-dependent,
  not-observed, not-applicable, missing and withdrawn outcomes;
- collapsing ADR-021 evidence status with requirement, ADR, validation,
  attempt, task-outcome, or review status, or treating a human study subject as
  an SDL participant/participant implementation;
- scoring diagnostics by message substring alone while ignoring stable code,
  stage, severity, locator, repair outcome and leakage;
- recording only successful attempts, allowing private source inspection,
  changing assistance mid-task, or omitting learning/order effects;
- committing identifiable participant data, raw recordings/chats/prompts,
  pseudonym linkage keys, absolute host paths, hidden answer material, real
  credentials, unrestricted third-party text, or source/backend dumps;
- putting invalid study artifacts in `examples/scenarios/`, turning research
  cases into normative fixtures, or using the research bundle as the only
  regression for a discovered defect;
- adding a DSL-evaluation schema to `contracts/`, extending experiment-core or
  completeness contracts with study-local fields, or creating a second source
  registry, parser, validator, exception tree, logger, persistence store, or CI
  workflow;
- allowing an imported task to perform a live OCI fetch during offline
  reproduction, or bypassing a public tool adapter to improve its observed
  diagnostics; and
- silently repairing the language during the evidence run and replacing the
  falsifying snapshot with post-fix results.

## Non-Goals And Implementation Boundaries

- Do not add or change SDL syntax, schemas, semantics, diagnostics, examples,
  compiler/planner behavior, backends, profiles, or migration behavior in this
  issue merely to improve the result.
- Do not implement participant behavior, authoring specificity, formal
  validation/reachability, standardized scenario coverage, or researcher
  accessibility work owned by #71, #73, #168, #164, or #178.
- Do not claim scientific adequacy, broad usability, productivity, domain
  validity, backend independence, reproducibility, or maintainability beyond
  the exact preregistered population, tasks, conditions, versions and evidence.
- Do not deploy a range, execute participant actions, evaluate model quality,
  recruit participants without applicable review/consent, or establish a
  production telemetry/analytics service.
- Do not create a new normative ADR, formal semantics, contract family, API,
  controller, service, repository, database, UI, or migration system. A future
  external interchange or hosted study service requires its own authority and
  security decision.
