# Issue 210 ACT-610 Defensive Behavior Vocabularies Preflight

Date: 2026-07-19.

Issue: #210.

Tracking UID: ACT-610. Contract authority: issue #210; no formal requirement
payload was supplied for this run.

This note records architecture guardrails for supporting defensive behavior
vocabularies for detection, investigation, response, containment, and recovery
oriented participant tasks, goals, or activities. It is guidance for
implementation only: it does not add SDL fields, vocabulary terms, source
artifacts, schemas, fixtures, validators, compiler output, runtime emission,
control-plane routes, or conformance behavior.

## Binding Sources

- ADR-067 and `specs/formal/participant-behavior-model/README.md` are the
  behavior-model authority. ACT-610 extends the composed participant behavior
  model; it does not create a defensive-participant stack.
- ADR-020 keeps authored participant framing in SDL `agents.*` and separates
  participant role, identity, authority anchors, and operating scope from
  runtime apparatus and control-plane concerns.
- ADR-022 owns portable action, observation, interaction, failure, attribution,
  temporal, and outcome semantics. A defensive classification does not replace
  those contracts or prove that a detection, containment, or recovery occurred.
- ADR-041, ADR-054, and ADR-060 own participant implementation manifests,
  runtime behavior evidence, retrieval views, and backend-facing carriers.
  Apparatus support and runtime evidence may support a defensive-behavior claim
  but are not its authored vocabulary.
- ADR-009, ADR-012, ADR-019, ADR-061, and ADR-062 define normative artifact
  authority, controlled-vocabulary governance, schema publication discipline,
  and concept-authority catalog gates.
- NIST CSWP 29, *The NIST Cybersecurity Framework (CSF) 2.0*, is the external
  base-term authority. Its Detect, Respond, and Recover categories directly
  cover continuous monitoring, adverse-event analysis, incident management,
  incident analysis, incident response communication, incident mitigation,
  recovery-plan execution, and recovery communication. NIST SP 800-61 Rev. 3
  confirms Detect, Respond, and Recover as the incident-response lifecycle.

## Architecture Decisions

- Add one explicit sibling governed field, `defensive_behavior_refs`, on the
  existing `ParticipantBehaviorSpecification` aggregate and its compiled
  `ParticipantBehaviorSpecificationRuntime` projection. Do not add a new
  top-level defensive model, participant subtype, role taxonomy, task or goal
  schema, workflow dialect, runtime history family, backend feature family, or
  untyped vocabulary map.
- Govern the field through one vocabulary,
  `participant-defensive-behavior-activities`, scoped only to
  `behavior_specifications.defensive_behavior_refs`. Keep it independent from
  the ATT&CK and ATLAS offensive scopes. Equal English words across catalogs do
  not imply equivalence.
- Adapt the NIST CSF 2.0 category layer under Detect, Respond, and Recover into
  the ACES participant-behavior classification, marking catalog source
  provenance as `adapted` and preserving the eight category identifiers,
  titles, and function membership: `DE.CM`
  Continuous Monitoring, `DE.AE` Adverse Event Analysis, `RS.MA` Incident
  Management, `RS.AN` Incident Analysis, `RS.CO` Incident Response Reporting
  and Communication, `RS.MI` Incident Mitigation, `RC.RP` Incident Recovery
  Plan Execution, and `RC.CO` Incident Recovery Communication. Portable term
  keys may be the repository-compatible lowercase title slugs, but every term
  must retain its exact NIST category identifier in `source_id`. ACES binding
  descriptions must be explicitly identified as adaptations; do not present
  locally authored participant semantics as verbatim NIST definitions or NIST
  endorsement.
- Pin one official NIST CSF 2.0 machine-readable Core export when available,
  plus the stable CSWP 29 publication citation, by URL, version/date, SHA-256,
  retrieval date, citation, and applicable NIST publication-use notice. The
  checked-in source snapshot, catalog terms, valid fixture, documentation, and
  offline conformance check must move together. Remote verification is an
  explicit maintenance mode, not a network dependency of normal CI.
- Treat the NIST values as intent/outcome-domain classifications attached to a
  behavior specification. They do not assert that an organizational CSF
  outcome is satisfied, that an incident exists, that a participant observed
  hidden truth, or that a response was effective. Such claims require the
  existing action, observation, outcome, evidence, runtime, and conformance
  surfaces.
- Do not use D3FEND tactics or techniques as aliases for the NIST categories.
  D3FEND models defensive countermeasure tactics and techniques at a different
  semantic level. A future D3FEND binding belongs on an explicit external
  mapping or technique-bearing action/tool surface with source system,
  identifier, relation, mapping loss, and rationale; it must not be accepted as
  an unqualified `defensive_behavior_ref`.
- Keep the catalog's governed-extension discipline. ACES-local terms use the
  existing `x-<owner>:<term>` syntax. A local extension is not a NIST CSF term
  and must not be emitted with NIST provenance.
- Schema validity remains necessary but insufficient. The owning
  implementation must exercise semantic validation, positive and negative
  authoring cases, compiler carry-through, generated-schema parity, catalog
  source parity, and leakage-safe diagnostics.

## Canonical Incumbents To Reuse

- SDL ingress and model gates: `aces_sdl.parser.parse_sdl()`,
  `parse_sdl_file()`, `_HASHMAP_SECTIONS`, key normalization, shorthand
  expansion, variable-created key rejection, `SDLModel(extra="forbid")`, and
  `Scenario.behavior_specifications`.
- Authored and compiled aggregates: `ParticipantBehaviorSpecification`, its
  list uniqueness/non-empty validators and aggregate-shape validator,
  `ParticipantBehaviorSpecificationRuntime`,
  `aces_processor.compiler._compile_behavior_specifications()`, and canonical
  `participant.behavior-specification.*` addresses.
- Participant semantics and diagnostics:
  `aces_sdl.semantics.participant_behavior.analyze_participant_behavior()`,
  `_behavior_specification_vocabulary_issues()`, `ParticipantBehaviorIssue`,
  `SemanticValidator`, and the central issue renderer in
  `aces_sdl.validator._content_objectives`.
- Vocabulary authority:
  `contracts/concept-authority/controlled-vocabularies-v1.json`,
  `ControlledVocabularyCatalogModel`, the single governed-scope allowlist,
  `load_controlled_vocabulary_catalog()`,
  `validate_controlled_vocabulary_scope_values()`, and
  `validate_controlled_vocabulary_value()`.
- External-source governance: the checked-in ATT&CK and ATLAS source artifacts,
  their source contract models, digest/metadata checks, offline-by-default
  conformance checkers, valid catalog fixture parity, and the two focused
  vocabulary test families. Reuse that publication and verification pattern;
  do not copy either taxonomy's semantics or create another catalog loader.
- Contract authority: `ContractModel`, `schema_bundle()`, `contracts/schemas/`,
  `contracts/schema-publication-manifest.json`, `contracts/fixtures/`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, and
  `tools/check_concept_authority_governance.py`.
- Catalog and lineage authority: `tools/check_sdl_catalog_parity.py`, the SDL
  section catalog, the normative lineage ledger and its checker, and the
  public/explanatory SDL documentation mirrors.
- Runtime and conformance evidence: `RuntimeSnapshot.participant_behavior_history`,
  `iter_participant_behavior_history_violations()`, participant
  episode/shared-state/concurrency validators, observation boundaries, outcome
  interpretation records, participant retrieval views, and structured
  `aces_conformance` diagnostics.
- Error and observability surfaces: `SDLParseError`, `SDLValidationError`,
  `SDLInstantiationError`, `aces_processor.models.Diagnostic`, `Severity`, API
  `HTTPException` mappings, control-plane audit events, and the redacted FastAPI
  internal-error handler.
- Workflow: `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, the
  existing `contracts`, `policy`, documentation, and test sessions,
  `.github/workflows/ci.yml`, and `tools/verify_all.py`. A focused NIST source
  checker belongs in the existing contract verification graph, not a parallel
  workflow or nox session.

## Whole-Repository Surfaces In Scope

- Design and normative prose under `docs/decisions/` and
  `specs/formal/participant-behavior-model/`.
- Concept authority, source provenance, schemas, fixtures, publication ledger,
  and lineage records under `contracts/`.
- SDL, contracts, compiler, runtime models, and conformance packages under
  `implementations/python/packages/`. Compatibility-only wrappers under
  `implementations/python/src/aces/` are not an implementation home.
- Parser, model, semantic, compiler, controlled-vocabulary, schema, catalog,
  corpus-packaging, and policy tests under `implementations/python/tests/`.
- Scenario/library examples and `docs/api/` or `docs/explain/` mirrors when the
  public SDL field becomes available.
- Canonical policy and verification tooling named above. The implementation
  must update the existing graph rather than introduce a side-channel gate.

## Cross-Cutting Layers And Security Boundary

The intended design must pass every layer it touches:

- **SDL/YAML ingress:** defensive values enter through the existing safe SDL
  parser, normalized field keys, stable symbol-defining map keys, shorthand
  handling, variable rules, and closed Pydantic models. Values are list data on
  a known field, not variable-created map keys, executable content, or an
  alternate configuration channel.
- **SDL shape validation:** the existing behavior-spec list validator enforces
  non-empty, unique strings and the aggregate validator recognizes the new list
  as a behavior surface. Unknown fields remain forbidden. Do not add a second
  DTO validator or silently coerce arbitrary objects to strings.
- **Semantic and vocabulary validation:** each resolved value passes
  `validate_controlled_vocabulary_scope_values()` for the exact defensive
  scope. Unknown values and malformed extensions produce collected
  `SDLValidationError` diagnostics through `ParticipantBehaviorIssue`; they do
  not raise a new defensive exception type or stop validation at a separate
  pass.
- **Source and concept-authority validation:** the catalog scope is admitted by
  the existing governed-scope allowlist; the source snapshot, digest, category
  identifiers, titles, order, and catalog terms are checked offline. Bind to
  existing `actions-and-events`, `tasks-runs-studies`, or
  `provenance-and-evidence` concept families according to the owning claim. Do
  not add a `defensive-behavior` concept family merely to host a vocabulary.
- **Contract/schema validation:** SDL schema changes originate from the model
  source and `schema_bundle()`, then update generated schemas, publication
  manifest `last_change`, valid/invalid fixtures, JSON checks, SDL catalog
  parity, and lineage records together. Hand-editing generated schemas or
  adding a second publication ledger is forbidden.
- **Compilation/runtime validation:** compiler carry-through preserves the
  governed values on the existing behavior-specification runtime record and
  canonical address. Runtime behavior history, observations, results, and
  conformance diagnostics remain evidence. A defensive classification alone
  cannot make a runtime success, detection-quality, containment-effectiveness,
  or recovery-completeness claim.
- **Control-plane authorization, if exposed:** existing
  `ControlPlaneSecurityConfig.strict_defaults()`, read versus mutating identity
  dependencies, request-size guards, idempotency fingerprints for mutations,
  audit records, bounded `HTTPException` details, published response models,
  and redacted internal-error envelopes remain mandatory. A defensive term is
  scenario meaning and grants no API, participant, operating-system, or backend
  authority.
- **Configuration and environment shapes:** ACT-610 adds no environment
  variable, CLI flag, backend-private configuration field, OS account, network
  listener, subprocess, or process-argument surface. Portable semantics come
  from SDL plus the checked-in catalog, never from env/argv values.
- **Secret and error-envelope exposure:** defensive refs, source artifacts,
  fixtures, diagnostics, snapshots, audit details, logs, and changelog text must
  not carry credentials, bearer tokens, hidden prompts, answer keys, private
  incident data, raw packet or command content, backend config, full scenario
  dumps, or tracebacks. Diagnostics may name the invalid term, behavior-spec id,
  and vocabulary id only. Detailed evidence stays behind existing markings,
  redaction, disclosure, digest, and evidence-reference boundaries.
- **Persistence and observability:** use scenario artifacts, the concept
  catalog, checked-in fixtures/source evidence, runtime snapshots,
  `ControlPlaneStore`, and existing audit logs. No defensive-specific database,
  repository class, cache, event stream, logger, metric namespace, or audit
  sink is warranted by a classification field.

## Extensibility Seam

The extension seam is one explicit sibling field plus its catalog scope:

- `defensive_behavior_refs` carries governed ACES adaptations of NIST CSF 2.0
  defensive category values on a behavior specification;
- the existing table-driven vocabulary validation path is parameterized by
  authored field name, governed scope, and diagnostic code;
- the compiler copies the list without interpreting it as execution order,
  state, success, or authorization; and
- exact countermeasure, technique, vendor, playbook, or action-system mappings
  retain their own source identity and mapping-loss metadata at the existing
  action/tool/concept-binding surface.

The next reasonable variation is a separately governed AI-defense or technical
countermeasure taxonomy. It should add a sibling explicit field and scope only
when its semantic authority differs, reusing the same field/scope/diagnostic
parameter seam. Do not replace discoverable schema fields with
`dict[vocabulary_id, list[str]]`, and do not merge NIST CSF, D3FEND, vendor, or
AI-defense values into one bag merely to avoid a future schema addition.

## Gotchas And Anti-Patterns

Avoid:

- using `goals` in ACT-610 as SDL evaluation `goals`, experiment tasks,
  workflow activities, objective truth, reward, or scoring semantics;
- treating NIST CSF categories as ordered incident-response phases, participant
  roles, action contracts, behavior modes, implementation kinds, backend
  support levels, control-plane permissions, or evidence-retention policy;
- claiming CSF conformance, detection quality, incident existence, successful
  investigation, effective containment, eradication, restoration, or recovery
  merely because a behavior specification carries a defensive term;
- treating a SIEM alert, rule id, IOC, case status, ticket, forensic finding,
  raw log, command, tool name, D3FEND technique, OpenC2 action, or vendor
  playbook step as an unqualified portable defensive behavior value;
- collapsing `DE.AE` and `RS.AN` into one `investigate` alias: adverse-event
  analysis and incident analysis have different NIST contexts;
- collapsing `RS.MI` into a locally named `contain` term or assuming all
  mitigation is containment; preserve the NIST source category and express
  narrower behavior through action contracts or governed extensions;
- merging defensive, ATT&CK, and ATLAS vocabularies because labels overlap;
- duplicating participant action/effect/failure/outcome schemas inside the
  vocabulary surface;
- creating another controlled-vocabulary loader, scope registry, exception
  hierarchy, schema manifest, persistence store, audit log, conformance runner,
  CI workflow, or near-copy of source-integrity utilities;
- hardcoding the initial terms independently in models, validators, compiler,
  docs, and tests; the catalog is the value authority and governed extensions
  remain valid where its policy allows them; and
- weakening hidden-truth, participant-visible observation, evidence-only,
  disclosure, redaction, or information-flow boundaries to make defensive
  evidence easier to publish.

## Non-Goals And Implementation Boundaries

- This preflight does not implement ACT-610 fields, terms, source snapshots,
  schemas, fixtures, validators, compiler changes, tests, docs, examples,
  runtime emission, API routes, persistence, or conformance diagnostics.
- ACT-610 does not redesign participant behavior specifications, participant
  framing, action contracts, observation boundaries, outcome interpretation,
  authority/scope, behavior modes, tool affordances, manifests, backend
  capabilities, objectives, experiment tasks, workflows, or runtime history.
- ACT-610 does not standardize detailed D3FEND techniques, OpenC2 actions,
  SIEM/EDR taxonomies, IOCs, forensic artifacts, case-management states,
  playbook execution, incident chronology, or vendor-native labels.
- ACT-610 does not introduce an incident-response engine, detection engine,
  SOAR/case-management service, participant runtime loop, new control-plane
  endpoint, authentication model, authorization role, store, logger, or host
  process.
- ACT-610 does not publish private incident content, credentials, prompts,
  answer keys, raw telemetry, packet contents, command output, backend-private
  configuration, hidden truth, or unredacted evidence as portable behavior
  vocabulary data.
