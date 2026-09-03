# Issue 110 / GOV-904 semantic diff and impact analysis preflight

Date: 2026-08-01

Issue: #110.

Requirement: GOV-904 (`0110fe85-309a-4cd6-836b-33213c0d329a`), draft,
functional, SHOULD, wave 3. The supplied requirement payload and issue #110
acceptance criteria and non-goals are the delivery contract.

This note fixes the architecture boundary for machine-readable semantic
comparison and impact analysis. It is guidance only: it does not publish a
contract, schema, comparison profile, impact rule, fixture, API, presentation,
or implementation plan.

## Decisive current-state findings

- ADR-009 makes `contracts/schemas/`, fixtures, and profiles the portable
  authority. ADR-061 and `contracts/schema-publication/` govern schema lineage,
  compatibility, hashes, and removal. A Python-only result model is not the
  issue's portable contract.
- ADR-075 requires compatibility claims to name the surface, producer,
  consumer, direction, dimension, versions, and evidence. Structural
  acceptance, semantic equivalence, behavioral compatibility, and operational
  interoperability are not interchangeable.
- ADR-076 and `DeclarationIndex` already own collision-preserving canonical SDL
  identity. Processor compiled addresses, JSON Pointers, aliases, labels,
  module namespaces, artifact ids, and filesystem paths are related but
  distinct coordinate systems.
- ADR-078, `canonical_sdl_digest()`, and
  `canonical_instantiated_sdl_digest()` keep normalized authoring,
  composition-expanded authoring, instantiated artifacts, and canonical
  snapshots phase-distinct. Digest equality proves identity only under its
  named profile, not semantic or behavioral equivalence.
- The AUT-810 artifact-transformation surface already publishes deterministic
  source/target digests, identity maps, named preservation checks, explicit
  ambiguity/loss, and bounded diagnostics. A successful, digest-bound
  `ArtifactTransformationReportModel` is authoritative rename or migration
  evidence when its profile covers the compared artifacts. Semantic comparison
  must consume that evidence rather than inventing rename heuristics or a
  second migration report.
- Experiment-core already owns the task, archival run, study, and capture-spec
  carriers and their cross-artifact validators. In this issue, “evidence
  specification” means `ExperimentCaptureSpecModel`; it is not an
  `EvidenceRequirement`, captured `ExperimentEvidenceRecordModel`, derived
  measure, or run evidence artifact.
- External concept bindings are standalone, digest-bound assertions with a
  pure contextual admission path. They are linked comparison context, not SDL
  fields, a concept registry, or authority to alter RAES semantics.
- ADR-036 makes `raes_contracts` the owner of neutral portable DTOs and
  `raes_processor` the owner of pure semantics-bearing analysis. `raes_cli`,
  `raes_mcp`, Hub, and env-packs are consumers and presentation/orchestration
  boundaries, not semantic owners. `raes_runtime` owns mutable live state and
  must not become the comparison store.
- The repository has no authoritative whole-ecosystem dependency registry.
  `DeclarationIndex`, module provenance, experiment-core reference models and
  contextual validators, and external-binding admission each own a bounded
  part of the graph. Therefore “complete impact” can only mean complete for an
  exact, declared input scope and closure, never complete for every artifact in
  a repository or deployment.
- `SemanticProfileModel` describes cross-stage concept/interoperability
  assumptions and `ValidationProfileCatalogModel` describes admission strength.
  Neither defines comparison projection, version-pair support, dependency
  rules, or traversal limits. Reusing either merely because it contains the
  word “profile” would conflate distinct governed profile families.

These authorities are sufficient. No new ADR is warranted unless the
implementation changes phase identity, contract authority, module trust,
experiment-core ownership, runtime persistence, or control-plane security.

## Architecture decisions and guardrails

### One portable contract family and one pure reference facade

Publish one versioned, closed semantic-comparison contract family containing a
source-neutral request and result. Portable value models belong in
`raes_contracts`; the pure reference analysis facade and artifact-specific
comparison orchestration belong in `raes_processor` under the existing
ADR-036 dependency direction. Owning artifact packages continue to perform
their own admission and expose typed projection/resolution helpers where
needed.

The selected comparison profile is itself governed portable data or normative
machine-readable policy under the existing `contracts/profiles/` authority. It
pins supported artifact/phase/version pairs, projection and dependency-rule
versions, ordering, completeness semantics, and fixed ceilings. Do not leave
those meanings behind an opaque string literal in Python, and do not overload
`SemanticProfileModel` or the validation-profile catalog with them.

The reference call accepts typed, already supplied operands and explicit
resolution/evidence context. It performs no file discovery, pack selection,
URL dereference, module fetch, environment lookup, runtime query, or mutable
registry access. Do not add a file-oriented “convenience” API as the semantic
entry point. env-packs may resolve files and Hub may resolve stored artifacts,
but both must call the same source-neutral facade.

The request identifies each operand through a closed discriminated coordinate
variant for that artifact family. It preserves, rather than replaces, the
owner's identity rules:

- artifact kind and exact contract/surface identity;
- lifecycle phase;
- canonical artifact id and version where its owner defines them;
- the owning canonicalization profile and digest; and
- optional exact-representation evidence consisting of a representation
  profile, media type, and byte digest, never a host path.

The published-schema key, wire `schema_version`, domain artifact version,
module version, comparison profile, canonicalization profile, and package
release are distinct identifiers. An adapter owns the exact allowed
combinations; the implementation must not invent a generic `contract_version`
or compare these values as interchangeable strings.

The typed artifact values and explicit context are arguments to the facade.
They are not arbitrary payload unions hidden in the request. A generic
projection may exist as a private, trusted adapter result. It is not
caller-authored input or an admission substitute. Otherwise a caller could
mint semantic digests, dependency rules, or provenance and have RAES report
them as authoritative. The result binds the exact request digest, operand
coordinates/digests, comparison profile, analyzer profile/version, supplied
evidence/context digests, and declared impact-scope digest. It contains no
clock, UUID, random value, username, host location, or presentation state.

### Keep correspondence, representation, structure, and meaning independent

Do not model a change as one mutually exclusive enum. One identity
correspondence can be renamed and also structurally or semantically changed.
The portable result needs independent axes:

1. **Identity correspondence:** same, added, removed, renamed, or
   indeterminate correspondence.
2. **Textual/representation relation:** unchanged, changed, unknown, or not
   applicable under a named representation profile.
3. **Structural relation:** unchanged, changed, unknown, or incomparable under
   a named contract/structure profile.
4. **Semantic relation:** unchanged, changed, unknown, or incomparable under a
   named semantic comparison profile.

Textual change is knowable only when both exact representations are supplied
under the same admitted representation profile. A difference between two raw
byte digests can establish representation change; absence of either digest is
`unknown`, not `unchanged`. Source formatting, comments, YAML spelling, and file
location do not become semantic change.

A whole-artifact byte digest establishes only the whole-artifact
representation relation. Per-subject textual change requires a profile-owned,
digest-bound source-span or representation projection for that subject. Do not
fan one root byte-digest difference out to every declaration or accept an
unbound caller-supplied “subject representation digest.”

Structural comparison operates on admitted typed artifacts or a profile-owned
projection. It must not recursively diff arbitrary dictionaries or treat JSON
Schema acceptance as semantic equivalence. Cross-version structure is
`incomparable` unless an exact version-pair comparison/migration profile owns
the relation.

Semantic comparison is artifact-kind, phase, and version-pair specific. Every
semantic projection names the existing owning rules it applies and the fields
or relations it deliberately excludes. There is no repository-wide list of
“non-semantic fields”; provenance, timestamps, apparatus context, redaction,
or validation basis may be meaning-bearing for one artifact and not another.

Malformed requests or unadmitted supplied artifacts fail at their existing
ingress boundary. A valid request with missing context, an unresolved
reference, unsupported artifact/version pair, lossy evidence, or an exhausted
analysis bound returns a complete typed result with `unknown`, `incomparable`,
or `indeterminate` status and stable reason codes. These are ordinary domain
outcomes, not exceptions and never false `unchanged` results.

### Canonical identity is owner- and phase-specific

Use the following incumbents; do not create a universal dotted address or
generic `ArtifactReference` that erases their differences.

| Artifact | Canonical identity and admission boundary |
| --- | --- |
| Scenario | `Scenario.name` + `Scenario.version` in an explicit normalized-authoring or canonical-instantiated-snapshot phase; production parser/model validation, `SemanticValidator`, `instantiate_scenario()` / `admit_instantiated_scenario()`, and the owning canonical digest. Expanded authoring remains trusted internal context. Cross-phase comparison requires an explicit phase relation. |
| Module | Validated `ModuleDescriptor` id/version, admitted module-body canonical digest, exact content/export/manifest digests, and `ResolvedImportProvenance` established by the existing module resolver/trust path. Raw `content_digest` is representation/integrity evidence, not by itself a semantic digest. `ResolvedModule.root_file`, a source path, import namespace, or lockfile position is not portable module identity and must not cross the result boundary. |
| Task | `ExperimentTaskModel.task_id` + `task_version`, admitted closed payload digest, and task/domain validation basis. Scenario references remain references, not copied scenario identity. |
| Run | `ExperimentRunModel.run_id` + `run_version`, admitted archival payload digest, and exact task/scenario/apparatus/evidence joins. A `RuntimeSnapshot`, operation id, or mutable control-plane record is not an archival run. |
| Evidence specification | `ExperimentCaptureSpecModel.capture_spec_id` + `spec_version` and admitted payload digest. Capture intent remains distinct from evidence capture, raw evidence, derived measures, and result summaries. |
| Study | `ExperimentStudyModel.study_id` + `study_version`, admitted payload digest, and the existing task/run/membership/allocation semantic joins. |
| External concept bindings | `ExternalConceptBindingDocumentModel` set id/version/digest and each exact `ExternalConceptSubjectModel` coordinate after existing contextual admission. Assertions do not establish RAES identity or semantics by themselves. |

For closed non-SDL contracts, reuse RFC 8785/JCS through
`canonical_json_digest()` / `canonical_contract_digest()`. If the current
satisfiability-module location is conceptually wrong for new callers, expose
the existing dependency-neutral canonical helper through an appropriate public
facade; do not add a comparison-only serializer.

Map keyed child ids to embedded ids using the owning model's existing
invariants before comparison. Preserve every candidate until collision and
ambiguity analysis is complete. Never infer identity from array position,
mapping insertion order, case folding, labels, titles, paths, URI fragments,
or similar field values.

Common graph nodes use a discriminated union or wrapper around those
owner-specific coordinates. They are not a free-form `identity` string or one
bag of optional fields. `ExternalConceptSubjectModel` is a useful precedent
for exact SDL subject binding, but it does not replace task, run, study,
capture-spec, module, or artifact-root identity.

### Rename and loss require authoritative evidence

A declaration or artifact is `renamed` only when an explicitly supplied,
admitted identity map binds the exact source and target digests and covers the
relevant identity. The primary incumbent is a successful
`ArtifactTransformationReportModel`; an owning exact version-pair migration
record may serve the same role when governed by ADR-075. The map must be
injective and phase/kind correct.

Without such evidence, a removed identity plus a similar added identity stays
removed plus added. String similarity, equal titles, matching bodies, edit
distance, source history guesses, aliases, or “same position” may be
presentation hints only and must not affect the machine result. Ambiguous or
partial mappings produce indeterminate correspondence.

Preserve transformation loss, ambiguity, and named preservation limitations
from the authoritative report. Do not translate a lossy migration into a
generic semantic change that hides the loss, and do not reuse external-concept
approximation, participant-flow loss, redaction, uncertainty, or validation
strength as synonyms. Each remains an independently typed axis or evidence
reference.

### The impact graph is a bounded semantic dependency projection

The issue justifies a comparison-specific impact graph, not a generic graph
framework or global dependency registry. The request/context declares the
included artifact set, traversal roots, closure policy, and a canonical digest
of that scope. Artifact adapters project admitted owner facts into a common
bounded form:

- a node is an exact canonical subject coordinate with artifact kind, phase,
  contract/profile, identity, and digest context;
- a dependency edge records the dependent subject, dependency subject, stable
  owner rule id/version, resolution status, and provenance/evidence refs; and
- an impact path is an ordered sequence of those edges from a changed subject
  to a potentially affected dependent.

Impact completeness is relative to the declared scope. An empty path set with
an absent, partial, redacted, or unverified consumer closure is indeterminate,
not “no impact.” The result repeats the scope/closure evidence and separately
reports analysis-bound exhaustion, so consumers can distinguish incomplete
input from complete input that was truncated during traversal.

Edges come only from authoritative typed relations and their existing
resolvers. These include SDL declaration/reference indexes and formal rules,
plus module import/export/binding provenance. They also include task
scenario/protocol/artifact refs and run task/scenario/apparatus/evidence refs.
Capture-spec scope, window, channel, and requirement refs are in scope, as are
study joins and external-binding refs. Prose, `metadata`, labels, filenames,
directory co-location, logs, backend object graphs, and UI links do not create
dependencies.

The stored edge direction must be unambiguous (`dependent -> dependency`).
Impact traversal follows the reverse relation from a changed dependency to its
dependents. Every returned path repeats the owner rule on each hop, so a
consumer can explain why the artifact is affected without reverse-engineering
the analyzer.

Dependency edges are side-aware. Preserve whether an edge and its resolution
evidence occur before, after, or on both operands, and report added, removed,
or changed dependencies instead of merging equal keys with last-write-wins.
Removed subjects traverse the before graph, added subjects traverse the after
graph, and paired/renamed subjects use the comparison profile's explicit
correspondence rule across both graphs. A resolution status change is itself
meaningful and must not be overwritten.

“Affected” means the dependent may require review, revalidation, regeneration,
or policy reevaluation under the named rule. It does not mean the dependent
artifact itself changed, that runtime behavior will change, or that a backend
is affected. Backend/processor/participant realization impact may be added only
when exact capability, manifest, conformance, or realized-provenance evidence
is explicitly supplied; RAES never predicts it from names or scenario intent.

Unresolved, ambiguous, stale, withheld, lossy, redacted, unsupported, and
incomparable edges remain present with their status and limitation. Missing
context must not delete an edge and thereby imply no impact. If a dependency
cannot be resolved to an exact target, retain the safe unresolved coordinate
and mark downstream completeness indeterminate.

### Determinism and bounds are contract behavior

For the same admitted operands, request, profiles, and explicit context, the
canonical result must be identical. Normalize unordered collections by their
owner-defined canonical key. Order change records by artifact coordinate and
axis, edges by `(dependent, dependency, rule)`, paths lexicographically by
their complete edge-key sequence, reason codes uniquely, and diagnostics by
the existing stable diagnostic key. Do not let Python hash order, input file
order, traversal discovery order, or concurrency decide output.

The comparison profile owns fixed maximum operand, node, edge, path-depth,
path-count, and diagnostic limits. A request may narrow but never widen those
limits. Use cycle-safe canonical traversal and a documented minimal-path rule;
do not emit an unbounded set of all graph paths. Bound exhaustion is explicit
in result completeness, affected scopes, and diagnostics. Silent truncation is
forbidden.

The result itself is a closed contract with stable ordering invariants and a
canonical digest. It does not contain source bodies, raw before/after values,
patches, secrets, evidence payloads, or formatted prose diffs. Consumers that
are authorized to read operands may render those values separately using the
result's exact coordinates.

Comparison relation, completeness, limitation, loss, and reason vocabularies
are closed and governed in the normative contract. `DiagnosticModel` supplies
safe bounded diagnostics; arbitrary reason strings, prose, or `metadata` are
not substitutes for typed domain outcomes.

## Canonical cross-cutting concerns to reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Authority and package ownership | ADR-009/019/036, `specs/authority/authority-boundary.yaml`, and `tools/policy/adr_policy.yaml`. Portable DTOs stay in `raes_contracts`; pure cross-artifact analysis stays in `raes_processor`; SDL/module admission stays in `raes`; runtime, backends, CLI, MCP, Hub, and env-packs do not own comparison meaning. |
| SDL ingress and phases | `SDLParserLimits`, safe YAML/source validation, `Scenario` / `ExpandedScenario` / `InstantiatedScenario`, `SemanticValidator`, `DeclarationIndex`, `instantiate_scenario()`, `admit_instantiated_scenario()`, ADR-076/078, and canonical SDL/snapshot profiles. Compare admitted phases, not raw mappings. |
| Module trust and provenance | ADR-053, module registry resolution, trust policy, lockfile, version/digest/signature/export checks, composition budget, `ResolvedImportProvenance`, and namespace/collision rules. The comparison core consumes established facts; it does not resolve or fetch modules. |
| Transformation and migration | `raes.transformations`, `ArtifactTransformationReportModel`, its identity map/loss/preservation checks, ADR-075, and exact source/target migration rules. Consume authoritative mapping evidence; add no rename heuristic or migration registry. |
| Experiment-core | ADR-055/064/066; `ExperimentTaskModel`, `ExperimentRunModel`, `ExperimentCaptureSpecModel`, `ExperimentStudyModel`, their reference models, `validate_experiment_run_against_task()`, archival validators, and `validate_experiment_study_against_tasks_and_runs()`. Preserve task/run/study/capture/evidence/live-state boundaries. |
| External concepts | `ExternalConceptBindingDocumentModel`, `ExternalConceptSubjectModel`, `external_concept_subjects()`, scheme snapshot adapters, and `admit_external_concept_bindings()`. Bind supplied documents to exact operand digests; do not fetch, infer, or grant assertions semantic authority. |
| Closed contracts and identity | `ContractModel(extra="forbid")`, constrained shared scalar/digest aliases, `DiagnosticModel`, `canonical_json_digest()` / `canonical_contract_digest()`, model-specific validators, and `x-raes-invariants`. Do not duplicate base DTOs, canonical JSON, diagnostics, or semantic invariant machinery. |
| Profile authority | Existing `contracts/profiles/` authority and `raes_contracts.corpus` resolution. Publish comparison-specific profile meaning there under its own closed profile family; do not reinterpret `SemanticProfileModel`, validation profiles, backend profiles, instantiation profiles, or package versions. |
| Validation strength and uncertainty | ADR-072, governed validation profiles, `ValidationBasisDisclosureModel`, stable gate/limitation terms, and owning admission diagnostics. Bind exact supplied basis disclosures by canonical digest/reference instead of cloning a smaller “validation level” enum into the comparison contract. A comparison result does not promote structural comparison to semantic, behavioral, or evidence-backed strength. |
| JSON/schema/conformance | `parse_bounded_json_object()`, `StrictJsonIngressError`, checked-in schemas, `schema_bundle()`, conformance structural/semantic registries, `contracts/fixtures/`, `raes_contracts.corpus`, `run_fixture_suite()`, schema generation parity, and schema-publication records. Add each new contract once to these incumbents. |
| Errors and observability | Existing SDL errors for SDL ingress, Pydantic/strict-JSON errors for malformed portable input, typed `Diagnostic` / `DiagnosticModel` for expected analysis outcomes, and `sanitized_failure_message()` at adapters. Add no comparison exception hierarchy, logger, telemetry pipeline, or raw exception envelope. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `.pre-commit-config.yaml`, ADR-014, `noxfile.py`, `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, `tools/check_authority_boundary.py`, `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`, and `tools/verify_all.py`. Extend the canonical graph once; do not add a parallel workflow. |

## Cross-cutting validation, security, and operational layers

The intended design must pass every applicable layer below.

1. **Request JSON ingress.** Raw portable requests use
   `parse_bounded_json_object()` with fixed byte limits, duplicate-member and
   non-finite-number rejection, then the exact closed request model. Unknown
   fields, attacker-selected callbacks/import paths, absolute host paths,
   credential-bearing URIs, and unbounded inline artifacts are rejected before
   semantic dispatch. Any URI-bearing evidence that is deliberately retained
   uses `validate_safe_absolute_uri()` and never carries userinfo or secret
   query fields; the result normally retains only its safe digest/reference.
2. **Contract shape and schema.** Request/result/value models use
   `ContractModel`, strict constrained types, conditional model validators,
   deterministic ordering checks, and the checked-in JSON Schemas. Cross-field
   and cross-artifact obligations are published through existing
   `x-raes-invariants`; schema success alone remains structural.
3. **Artifact admission.** Scenarios pass production parser, composition,
   semantic, phase, and canonicalization gates. Modules additionally pass the
   existing resolver/trust/lock/signature/digest/export/budget boundary before
   their facts are supplied. Task, run, capture-spec, study, transformation,
   validation-basis, and external-binding values pass their exact closed model
   and owning contextual semantic validators. The comparison engine never
   substitutes a weaker local validator.
4. **Identity and dependency resolution.** Canonical owner indexes preserve
   collision candidates and require exact unique resolution. Cross-artifact
   joins bind id, version, contract/profile, phase, and digest wherever the
   owner supports them. Aliases and missing context cannot silently become a
   match or no-impact result.
5. **Canonicalization and determinism.** Owning canonicalizers bind operands;
   the shared JCS helper binds request/result/context projections. Comparison
   profiles fix projections, rule versions, traversal, ordering, and limits.
   Locale, wall clock, randomness, input ordering, and machine state have no
   effect.
6. **Authentication and authorization.** The library facade has no auth
   surface and grants no authority. Hub, env-packs, or another consuming
   repository authorizes artifact and result access through its own existing
   identity, audience, tenant, and policy boundary. Do not move this API into
   `raes_runtime` merely to reuse its auth. Only if an adapter is deliberately
   mounted on the existing RAES runtime control plane does it reuse
   `ControlPlaneSecurityConfig.strict_defaults()`, `_ControlPlaneApiAuth`,
   request-size guards, `AuditEvent`, request fingerprints, idempotency for
   persisted/retried work, and the redacted unexpected-error envelope. A
   caller-supplied provenance or authority string is never authentication.
7. **Secret and information handling.** The result carries safe ids, profiles,
   digests, rule/reason/diagnostic codes, counts, statuses, and authorized
   evidence refs only. It never copies scenario parameter values, operator
   secrets, evidence content, raw experiment parameters, private prompts,
   hidden truth, URI query strings, environment values, credentials, keys,
   backend-native objects, rejected payload values, or Pydantic `input_value`.
   A digest is identity, not redaction. Presentation consumers must enforce
   their own authorized operand views.
8. **Configuration and environment.** Artifact kind, phase, comparison
   profile, version pair, context, representation evidence, and caller-narrowed
   bounds are explicit typed inputs. Add no environment variable, config-file
   switch, service locator, plugin discovery, global “latest” selector, or
   mutable singleton registry that changes comparison meaning.
9. **OS, process, filesystem, and network exposure.** The reference facade is
   pure in-process analysis: no filesystem reads/writes, subprocess, shell,
   temporary files, network requests, privilege changes, backend calls, or
   runtime queries. Raw payloads, locators, tokens, and evidence never enter
   process argv. File selection, pack traversal, and output writes belong to
   consumers after their own confinement and authorization checks.
10. **Error envelopes and logging.** Expected unresolved, unknown,
    incomparable, lossy, unsupported, and bounded outcomes use the result plus
    `DiagnosticModel`. Adapters sanitize unexpected failures and do not expose
    `str(ValidationError)`, raw exceptions, tracebacks, source bodies, or
    rejected values. The kernel adds no logger; adapters may log only safe
    profile/version, digests, counts, stable codes, and outcome.
11. **Persistence and audit.** Comparison is read-only and introduces no
    repository, database, cache, `ControlPlaneStore`, runtime snapshot,
    operation record, or audit stream. A consumer may persist the closed result
    by its canonical identity under its existing storage/security boundary.
    Results and impact edges must not be hidden in generic `metadata`,
    `details`, logs, or runtime snapshot metadata.

## Extensibility seam

The deliberate seam is a versioned comparison profile plus explicit typed
artifact adapters and resolver context, not a dynamic plugin framework.

- The request selects a governed comparison profile and exact artifact
  kind/contract/phase/version pair. Trusted code maps that tuple to an installed
  adapter; the request cannot name Python code.
- Each adapter supplies owner-defined identity extraction, structural and
  semantic projections, dependency-edge rules, admission requirements, and
  safe reason codes. It calls existing owner validators/resolvers rather than
  recreating them. Its projection type stays behind the trusted adapter seam;
  public callers supply admitted artifacts, not asserted semantic facts.
- The stable request/result vocabulary is parameterized by subject
  coordinates, relation axes, rule ids, evidence refs, and completeness
  statuses. A new artifact kind or contract version adds one adapter/profile
  and fixtures; it must not require a new result envelope or branches scattered
  through CLI, Hub, env-packs, runtime, and backends.
- Explicit context is the second seam. It carries a typed impact-scope/closure
  declaration plus exact resolver and provenance evidence. A later
  backend-impact mode supplies exact manifests/capability/realization evidence
  and a profile that owns those rules. It does not weaken the default
  source-only analysis or add ambient backend discovery.
- Fixed profile limits may evolve by profile version. Callers may narrow them
  without changing deterministic semantics or resource ceilings.

## Gotchas and anti-patterns

- Do not use a single `change_type` that makes rename, representation,
  structure, and semantics mutually exclusive.
- Do not call digest inequality semantic change, digest equality behavioral
  equivalence, schema acceptance semantic equivalence, or successful migration
  full preservation.
- Do not guess renames from edit distance, content similarity, labels, history,
  array positions, aliases, paths, or matching digests from different profiles.
- Do not use filesystem paths, pack coordinates, URLs, JSON Pointers, or
  processor compiled addresses as universal identity. Never parse a dotted
  string to infer its address kind.
- Do not expose caller-authored generic subject/projection objects that can mint
  semantic digests, dependency edges, rule ids, admission status, or
  provenance. Do not flatten owner coordinates into one free-form identity
  string or optional-field bag.
- Do not conflate schema bundle keys, wire `schema_version` values, artifact or
  module versions, comparison/canonicalization profiles, and package versions.
- Do not attribute a whole-document byte change to individual subjects without
  a digest-bound representation mapping.
- Do not compare raw dictionaries before admission, silently drop unknown
  fields, apply model defaults before preserving source-shape evidence, or
  invent a generic recursive “semantic” JSON diff.
- Do not flatten task intent, run provenance, capture specification, raw
  evidence, derived measure, study analysis, live runtime state, and external
  concept assertion into one artifact model.
- Do not treat missing, redacted, unresolved, stale, unsupported,
  incomparable, truncated, or lossy context as absence of change or impact.
- Do not claim global impact completeness without an exact input-scope and
  closure digest. Do not merge before/after dependency edges by key and
  overwrite their side, resolution status, or provenance.
- Do not infer backend behavior, capability, realization, participant
  visibility, policy effect, or scientific validity without the exact owning
  evidence and validator.
- Do not create a second declaration index, reference catalog, controlled
  vocabulary, schema source, canonicalizer, migration registry, fixture
  runner, validation stack, diagnostic class, exception hierarchy, logger,
  repository, cache, audit store, or presentation workflow.
- Do not embed patches, raw before/after values, source documents, evidence
  bodies, unrestricted prose, arbitrary metadata, or extension dictionaries in
  the portable result.
- Do not hide network lookup, module resolution, pack traversal, “latest”
  selection, or backend introspection inside a validator or comparator.
- Do not make CLI, browser, MCP, or pack presentation a prerequisite for using
  the analysis API or for understanding the machine-readable result.

## Non-goals and implementation boundary

Issue #110 does not:

- own pack-aware filesystem selection, repository traversal, or file diff;
- render a CLI, browser, MCP, HTML, or human review experience;
- define a generic patch, merge, migration, or transformation engine;
- infer a rename without authoritative identity-map evidence;
- redefine canonical SDL, module, experiment, evidence, validation, external
  concept, capability, realization, or provenance identities;
- compare mutable live control-plane state as an archival experiment run;
- prove behavioral, observational, epistemic, strategic, backend, or
  scientific equivalence from structural/semantic comparison;
- predict processor, backend, participant, or apparatus behavior without exact
  capability, conformance, or realization evidence;
- fetch modules, external concept schemes, evidence, artifacts, or URLs;
- discover every repository/deployment consumer or claim global dependency
  closure beyond the explicitly supplied impact scope;
- add authentication, secret resolution, environment/config binding,
  subprocesses, listeners, persistence, caches, repositories, audit stores, or
  runtime operations; or
- require any presentation layer to consume the source-neutral reference API.
