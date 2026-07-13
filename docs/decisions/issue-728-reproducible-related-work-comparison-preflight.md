# Issue 728 Reproducible Related-Work Comparison Preflight

Date: 2026-07-13

Issue: #728. This is a requirement-free run; the issue title, body, and
acceptance criteria are the contract.

This note fixes the architecture guardrails for rebuilding the related-work
comparison. It does not select the corpus, extract or score sources, execute
authoring tasks, rewrite the public comparison, or implement a checker. No new
ADR is needed: ADR-009, ADR-014, ADR-021, ADR-061, ADR-077, and ADR-080 already
govern authority, workflow, claim evidence, schema publication, artifact
identity, and source pinning. This note supersedes only the prose-only deferral
in the issue #508 preflight now that issue #728 explicitly requires a frozen
extraction matrix and reproduction bundle.

## Decision Boundary

The comparison is non-normative research synthesis. It may report what the
evidence demonstrates about ACES, but it must not define ACES semantics, change
SDL validity, or become a capability contract for external systems.

Keep three independently revisioned concerns:

1. **Protocol**: inclusion/exclusion rules, scope strata, system identities, the
   twelve axes, task and negative-case definitions, rubrics, evidence rules,
   analysis rules, and an amendment log. These are frozen before extraction.
2. **Extraction snapshot**: pinned sources and the observations, rationales,
   limitations, and evidence locators for one assessed corpus. A source refresh
   creates a new snapshot; it does not silently rewrite the protocol.
3. **Analysis and publication**: Pareto results, any sensitivity analyses, and
   bounded public claims derived from an exact protocol and extraction
   snapshot. Headline conclusions are outputs, never independently maintained
   booleans or prose-only assertions.

The machine-readable extraction surface belongs under the existing
`docs/research/related-work-comparison/` tree with its protocol and source log.
It is the single input to the reader-facing matrix. The public page at
`docs/explain/sdl/related-work-comparison.md` must be generated from it or
mechanically checked against it. `README.md`, `lineage.md`, and the changelog
must not carry parallel copies of the matrix.

Do not publish the research shape as an ACES JSON Schema or add it to
`aces_contracts`. It is not an ecosystem interoperability contract. A future
external interchange format requires a separate authority and schema decision;
until then, one focused offline repository checker owns the closed research
shape and cross-record invariants.

## Axis Boundaries

The protocol must retain all twelve issue-required axes as distinct stable ids.
Subcriteria may be atomic, but one result must not stand in for another axis.

| Axis | Boundary that prevents conflation |
| --- | --- |
| Expressive breadth | Representable concern/task coverage, not correctness, maturity, or quality. |
| Semantic precision | Defined meaning, reference rules, and ambiguity control, not parser strictness or feature count. |
| Formal analyzability | Explicit formal models, decidable properties, or executable analyses, not ordinary schema/semantic validation. |
| Concrete-syntax soundness | Source-profile definition, parsing, canonicalization, diagnostics, and rejecting negative cases, not semantic breadth. |
| Composition/versioning | Reuse, imports, identity, evolution, compatibility, and migration, not release cadence alone. |
| Experiment design | Tasks, factors, allocation, stochastic controls, measures, studies, and validity limits, not scenario objectives or workflow steps alone. |
| Participant modeling | Actions, observations, visibility, episodes, outcomes, and multi-participant interaction, not a generic actor/role field. |
| Provenance/evidence | Capture intent, evidence identity, lineage, integrity, redaction, and derivation, not the mere existence of logs or signatures. |
| Interoperability | A defined exchange or conformance boundary between independent implementations, not backend count or format export alone. |
| Usability | Predeclared authoring-task observations such as completion, effort, errors, diagnostics, and documentation support, not breadth by proxy. |
| Implementation maturity | Shipped executable behavior, releases, conformance evidence, maintenance, and independent use, not accepted designs or formal prose. |
| Governance/community | Standards/governance process, independent participation, adoption, and maintenance continuity, not repository popularity or implementation maturity. |

Cyber DEM and Cyber FOM, CRACK and VSDL, and CRACK/KYPO/CyRIS must not share
composite score cells. Each assessed system or version has one stable
`system_id` and one declared scope stratum. Related artifacts may be linked, but
their evidence and outcomes remain independently attributable.

## Measurement And Evidence Model

The protocol, not a hard-coded table, defines the system, axis, and task sets.
The checker derives rectangular coverage from those ids so adding a system is a
data change and changing an axis meaning requires a protocol revision.

For every system-axis cell, preserve separately:

- applicability and the scope rationale;
- axis-specific observed result or measurement;
- contributing representative tasks and negative cases;
- scoring/rubric rationale;
- primary-source evidence refs with exact locators;
- extraction method and, where relevant, tool/version identity;
- assessor, independent-review or adjudication status, and preserved disagreement
  for judgment-bearing results;
- limitations, missing evidence, and confidence; and
- the extraction snapshot and protocol revisions.

Do not collapse applicability, observation, evidence strength, implementation
status, and quality into `yes`/`partial`/`no`. `not applicable`, `not observed`,
`not implemented`, and `not evaluated` have different meanings. Out-of-scope
cells are neither wins nor zeroes. A missing primary source is an evidence gap
that constrains or blocks the claim, not evidence of absence.

Every positive, partial, negative, and out-of-scope cell needs primary-source
support and a reproducible rationale. An absence claim must record the pinned
source boundaries and search/extraction procedure that failed to find the
capability. A citation to a project home page is not a cell rationale.

ACES implementation claims require both meaning and delivery evidence when the
axis concerns executable behavior. An accepted ADR or formal specification can
establish intended semantics but cannot by itself establish implementation.
Use the published schema/fixture corpus, production parser/validator/compiler
or conformance path, and focused tests as applicable. Preserve `partial`,
`missing`, and `deliberately-excluded` outcomes from the current scientific-
completeness delivery assessment instead of upgrading them from prose.

Representative authoring tasks must declare the authored requirement, unit of
observation, applicability, permitted assistance, inputs, expected artifacts,
and success/partial/failure criteria before execution. Negative cases must name
the single injected defect and the expected rejection or diagnostic. For ACES,
run cases through the production `sdl-yaml/v1` source boundary, published
schema, `parse_sdl`/`parse_sdl_file`, and `SemanticValidator`; do not use a
comparison-only parser or acceptance shim. For a system with no applicable
concrete syntax or executable tool, use source extraction and record the task as
not applicable rather than treating non-execution as failure.

Usability observations must also disclose author population, relevant prior
experience, assistance, repetitions, timing/error collection, and missing or
abandoned attempts. Maintainer-only or single-author task evidence is
exploratory and cannot support a generalized usability claim. Judgment-bearing
rubrics need an independent second extraction or an explicit adjudication and
disagreement record; agreement is evidence about scoring reliability, not proof
that the rubric measures the right construct.

## Corpus And Source Freeze

Pre-register included and excluded systems, the comparison unit, and scope
strata before recording outcomes. Cross-scope observations may be informative,
but only like-for-like, applicable measurements may support a comparative or
Pareto claim.

Every source entry must have an immutable or drift-detectable identity:

- Git source: repository, full 40-hex commit, exact artifact path, and license
  disposition where bytes or code are retained;
- standard: maintaining body, exact edition/version/status, stable locator, and
  section/page locator;
- publication: title, authors, year, venue, DOI or other stable identifier, and
  exact cited location; and
- mutable official documentation: product/release context, retrieval date,
  exact page/section, and content digest or an archived immutable locator. If it
  cannot be frozen, record that limitation and do not use it for an unqualified
  headline claim.

The assessed ACES version is also a corpus member. Pin an already-existing
release or commit plus the relevant repository artifact paths; never record
`HEAD`, `dev`, a branch name, or "current". The containing Git commit freezes the
comparison bundle itself, avoiding an impossible self-referential commit hash.

ADR-080 and `sdl-lineage-ledger-v1` remain the authority for ACES derivation,
lineage, compatibility, and third-party notice disposition. Do not add
comparison scores or tasks to that ledger. Where a comparison source already
has a lineage citation/source id, reference it or mechanically require the
shared immutable identity fields to agree; do not fork its DOI, version, or
commit. Comparison-only sources stay in the research bundle rather than being
added to lineage merely to obtain a source registry.

Archive the extraction matrix and bounded evidence metadata, not unrestricted
copies of third-party standards, papers, repositories, or documentation. Keep
paraphrases and precise locators; retain source bytes only when licensing and
repository policy permit it. A digest detects drift but does not prove
authenticity or continued availability.

## Analysis And Public Claims

The primary result is the per-axis evidence surface plus scope-qualified Pareto
strengths. There is no default total score or total-order winner.

Pareto analysis is valid only over declared, directionally comparable metrics
and a declared applicable system set. Nominal labels and out-of-scope cells must
not be coerced into ordinal numbers merely to calculate a frontier.

Any aggregate or weighted analysis must be a separate, versioned analysis model
that declares metric normalization, direction, missing/out-of-scope handling,
weights, weight rationale, and the range of "reasonable" alternative weights
before results are examined. Preserve the sensitivity results. If reasonable
alternatives reverse a headline, disclose the reversal and narrow or withdraw
the headline; never select weights after extraction to restore a preferred
winner. Derived tables must be recomputable from observations and analysis
parameters rather than copied back into cells.

Keep these claims explicitly distinct:

- **broadest combined surface observed in this corpus**: a corpus-, version-,
  task-, axis-, and measurement-qualified breadth statement;
- **highest quality**: prohibited unless a separate quality construct, valid
  measures, evidence, and justified analysis model support it; and
- **standardized/mature**: claims about governance, implementation, adoption,
  and release evidence, never inferred from breadth or semantic precision.

Every public conclusion must reference the exact protocol, extraction snapshot,
analysis model, and supporting cell/observation ids. Public wording follows
`docs/explain/reference/documentation-style-guide.md`: uncertainty, reversals,
ACES gaps, and corpus limits are part of the claim, not footnotes that can be
dropped from summaries. The protocol must retain construct, corpus-selection,
source-availability, assessor, implementation-version, and external-validity
threats plus residual limits, following ADR-021's falsification-first boundary.

## Canonical Incumbents And Reuse

| Concern | Canonical incumbent and required boundary |
| --- | --- |
| Normative authority | ADR-009/019 and `specs/authority/authority-boundary.yaml`. `docs/` consumes authority; comparison data does not define SDL meaning. |
| Claim evidence | ADR-021's claim statement, threats, falsification protocol, pass/fail criteria, evidence artifacts, and evidence status. Do not create a second maturity-claim vocabulary. |
| Documentation and publication | `documentation-style-guide.md`, `canonical-reference-map.md`, the existing comparison page, research directory, docs index, and Sphinx build. |
| External source identity | ADR-080, `contracts/provenance/sdl-lineage-ledger-v1.json`, `tools/check_sdl_lineage.py`, and `docs/research/lineage/source-audit-2026-07-12.md`. Reuse identity rules without turning lineage into a scoring ledger. |
| ACES delivery truth | `specs/sdl/scientific-scenario-completeness.md`, its REV1 taxonomy and dated delivery assessment, `tools/check_scientific_scenario_completeness.py`, `limitations.md`, and `scenario-delivery-drift-audit.md`. |
| Concrete syntax | `sdl-yaml/v1`, `SDLParserLimits`, safe YAML loading, mapping-key analysis, closed `SDLModel` shapes, `parse_sdl`, `SemanticValidator`, `sdl-authoring-input-v1`, and example/schema negative controls. |
| Semantics and formal analysis | `specs/sdl/`, `specs/formal/`, semantic coverage policy, and the existing parser/instantiate/compiler/planner tests. Formal prose and executable analyzers remain distinguishable. |
| Composition and evolution | SDL module/import/lock semantics, ADR-053/075/076/078, `specs/evolution/`, and deprecation governance. |
| Experiment design | ADR-055/068/074, `experiment-task-v1`, `experiment-study-v1`, `ExperimentAnalysisPlanModel`, and experiment-core validity rules are methodological incumbents. Do not force a literature corpus into an ACES runtime study contract. |
| Participant modeling | ADR-013/020/022/054/067/069 and `specs/formal/participant-semantics/`. Generic roles, workflows, rewards, and episodes are not interchangeable. |
| Provenance and evidence | ADR-064/065/066/077, experiment evidence/run contracts, associated-artifact integrity rules, and observability/evidence-plane separation. A comparison bundle is not captured runtime evidence. |
| Interoperability and maturity | Published processor/backend manifests, backend/semantic profiles, realization envelopes, conformance fixtures/runners, and distribution-visible releases. Declared support and independently demonstrated conformance remain separate. |
| Diagnostics and workflow | `tools.policy.common.PolicyFailure`, `safe_repo_path`, `noxfile.py` `SessionReporter`, ADR-014, `tools/verify_all.py`, repo policy, contracts checks, and Sphinx. |

There is no controller, API DTO, service, runtime repository, or persistence
store in this feature. Do not add one. `ControlPlaneStore`, runtime snapshots,
operation envelopes, and the experiment archive are not homes for literature-
comparison state.

## Validation, Security, And Operational Layers

1. **Research shape and path gate:** load only fixed, checked-in data as inert
   content; reject duplicate/unknown ids and fields, unsafe paths, missing refs,
   non-rectangular coverage, and unpinned source identities. Resolve every
   repository path through `safe_repo_path` and apply bounded file/count limits.
2. **ACES source/shape gate:** ACES authoring cases pass the existing UTF-8,
   source-size/token/graph limits, YAML 1.2 safe loader, duplicate/conflicting-key
   checks, closed Pydantic model, published JSON Schema, semantic validation,
   and post-instantiation validation where instantiation is claimed. The
   comparison checker observes those results; it does not replace them.
3. **Contract/config gate:** add no runtime config, environment binding, schema,
   profile, manifest, or package DTO. `tools/check_json_artifacts.py` remains
   scoped to published contract artifacts; do not add comparison-specific
   branches to it. A focused checker owns only research-bundle and publication-
   drift invariants.
4. **Authentication/authorization gate:** no API, control-plane endpoint, live
   repository credential, or authorization path is in scope. Source acquisition
   happens outside offline verification. Do not add a weaker public endpoint for
   comparison data.
5. **Secret and URI gate:** protocol, URLs, commands, task outputs, diagnostics,
   and source metadata must not contain credentials, bearer tokens, private
   keys, cookies, private prompts, environment dumps, URI userinfo, or secret-
   bearing query parameters. Follow ADR-077's safe-locator rule and existing
   gitleaks/private-key hygiene. Never place credentials in process argv.
6. **OS and supply-chain gate:** normal nox/CI checks perform no network fetch,
   clone, package installation from compared projects, shell evaluation, or
   third-party code execution. If executable external task evidence is gathered,
   do it in a separately controlled, pinned, resource-bounded environment with
   no repository secrets or privileged host access, then commit only bounded
   results and provenance.
7. **Error-envelope and observability gate:** checker failures use bounded
   `PolicyFailure` records with stable rule ids and system/axis/task locations,
   reported once through `SessionReporter`. ACES task failures retain
   `SDLParseError`, `SDLValidationError`, `SDLInstantiationError`, and existing
   `Diagnostic`/`Severity` surfaces. Do not add a comparison exception hierarchy,
   logger, telemetry path, raw payload dump, or traceback-as-output contract.
8. **Persistence and integrity gate:** Git-tracked protocol, extraction, and
   derived artifacts are the durable record. Add no database, mutable cache,
   runtime metadata, audit blob, or object store. Git and pinned source identity
   establish reproducibility; checksums establish byte identity, not trust or
   authenticity.

The focused checker should be wired once into the canonical `noxfile.py` graph
through `SessionReporter`, alongside the existing lineage/evidence integrity
checks, rather than through a new CI workflow. Its tests should follow existing
mutation and non-vacuity patterns: a missing cell/evidence ref, mutable source,
composite system, suppressed weighting reversal, stale public summary, or
ACES implementation claim with no executable evidence must fail.

## Extensibility Seam

The stable join is:

```text
(protocol_revision, extraction_snapshot, system_id, axis_id, task_or_case_id)
```

Derived claims additionally name `(analysis_model_id, analysis_revision,
weight_profile_id-or-none)`. System, source, task, and axis ids live in data, not
parallel Python constants or hand-authored table columns. Adding a system or
task extends the preregistered corpus; refreshing a source creates a new
extraction snapshot; changing an axis or rubric creates a protocol revision;
and adding alternate weights creates an analysis profile without rewriting the
observations.

## Gotchas And Anti-Patterns

Avoid:

- composite system columns or silently borrowing one component's strength for
  another component;
- feature counting, binary presence labels, or document section counts as a
  proxy for semantics, usability, maturity, or quality;
- treating a formal specification as an executable analyzer, a parser rejection
  as semantic precision, a timestamp as time semantics, a log as provenance, a
  format export as interoperability, or repository activity as adoption;
- treating `not found` as `no`, `out of scope` as zero, missing evidence as
  negative evidence, or inaccessible sources as reproducible evidence;
- using accepted ADRs, proposed syntax, roadmap issues, examples, or the dated
  scientific-completeness taxonomy alone as proof of implemented behavior;
- counting ACES runtime inventory fields while ignoring missing authored syntax,
  partial episode/time behavior, or deliberately excluded scoring semantics;
- post-hoc dimensions, task selection, exclusions, normalizations, weights, or
  definitions of "reasonable" that favor the observed result;
- a stored winner flag, manually synchronized public table, hidden sensitivity
  reversal, or Pareto calculation over incomparable or nominal values;
- copying the comparison into README/lineage, putting scores in the lineage
  ledger, or registering the research matrix as a backend/semantic/profile
  contract;
- a second source registry that disagrees with existing lineage identities, a
  second validator/exception/logging stack, or a second CI workflow;
- live-link availability as a CI invariant, unpinned external execution in CI,
  or committing third-party source copies without license review; and
- promotional claims such as "most comprehensive" or "highest quality" without
  the exact bounded evidence and analysis the words require.

## Non-Goals And Implementation Boundaries

- Do not change SDL grammar, schemas, models, parser behavior, semantic
  validation, compiler/planner/runtime behavior, backend conformance, or
  experiment contracts to improve a comparison result.
- Do not implement missing syntax, time semantics, formal verification,
  participant behavior, usability tooling, interoperability, or governance
  maturity as part of this issue.
- Do not create a universal research-evidence schema, bibliographic service,
  scoring service, API/UI, database, registry, source mirror, or external
  execution platform.
- Do not claim compatibility, standardization, scientific validity, independent
  adoption, implementation maturity, or quality beyond the pinned evidence.
- Do not require a total-order conclusion. A defensible outcome may be a set of
  Pareto strengths, explicit evidence gaps, and no overall winner.
