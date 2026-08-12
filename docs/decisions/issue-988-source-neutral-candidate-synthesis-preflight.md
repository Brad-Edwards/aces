# Issue 988 Source-Neutral Candidate Synthesis Preflight

Date: 2026-08-12

Issue: #988.

Requirement: none. The GitHub issue title, body, acceptance criteria, and
non-goals are the authoritative contract.

This note records architecture guardrails for source-neutral SDL candidate
synthesis and admission. It is guidance only: it does not add a contract,
schema, transformation, adapter, SDL field, admission path, or implementation
plan.

## Existing Authorities And Ownership Boundary

- Issue #986's `external-concept-bindings/v1`,
  `ExternalConceptSchemeCoordinateModel`, scheme-snapshot adapters, and
  `admit_external_concept_bindings()` already own portable external concept
  coordinates and exact source-to-RAES binding assertions. They must be reused
  wherever synthesis produces a concept binding. A source assertion that has
  no RAES subject yet is not a binding and must not be forced into that model.
- ADR-076 and `DeclarationIndex` own canonical SDL declaration identity and
  collision-preserving resolution. Generated construct identity is the final
  canonical SDL address, not a source id, JSON Pointer, list position, label,
  or adapter-local key.
- ADR-078 and `raes.phase_contracts` own normalized, expanded, instantiated,
  and snapshot phase separation. A synthesis result is normalized authoring
  input; it is not instantiated, admitted, compiled, executable, or realized.
- `raes.transformations`, `ArtifactTransformationReportModel`, and the
  all-or-none transformation convention already own operation profile,
  source/target/policy/derivation digests, checks, identity maps, preservation,
  loss, and bounded diagnostics. Candidate synthesis must compose that report
  rather than publish a second transformation envelope.
- `parse_sdl()` / `parse_sdl_file()`, `SDLParserLimits`, module composition and
  trust, `Scenario`, `SemanticValidator`, `instantiate_scenario()`,
  `admit_instantiated_scenario()`, compiler admission, and the canonical SDL
  digest helpers are the only SDL validity and admission path.
- ADR-072, the validation-profile catalog, and
  `ValidationBasisDisclosureModel` already distinguish structural, semantic,
  behavioral, and stronger validation claims. A synthesis receipt must not
  invent a smaller gate or strength vocabulary.
- ADR-080, `canonical_json_digest()`, `canonical_sdl_digest()`, and the semantic
  comparison request/result plus owner adapters already own deterministic
  artifact identity and inspectable semantic comparison. A changed source or
  transformation version must use these seams, not an issue-specific diff.
- SEM-218 explicitness provenance describes author-, processor-, and
  backend-originated values across SDL realization. It does not distinguish
  imported assertions, synthesis inference, transformation defaults, and
  author choices. Those synthesis origins need their own closed trace values
  in the synthesis record and must not widen or reinterpret
  `ExplicitnessProvenance`.
- ADR-064/066 keep assertions, evidence, derived values, and views distinct;
  ADR-085/095 and API-423 own participant information flow, disclosure, and
  delivery. Source authority, assertion provenance, author approval, and
  participant visibility are four different facts.
- ADR-009/019/036, `specs/authority/authority-boundary.yaml`, and
  `tools/policy/adr_policy.yaml` own authority and package layering. Portable
  DTOs belong in `raes_contracts`; SDL-aware pure transformation belongs with
  the incumbent `raes.transformations` boundary; retrieval and pack-aware
  orchestration remain outside this repository's SDL core.

These authorities are sufficient. A new ADR is warranted only if
implementation proposes to add synthesis syntax to SDL, alter an SDL phase or
admission transition, make source assertions validation-authoritative or
executable, add ambient retrieval/plugin discovery, or create a new
information-flow or persistence boundary.

## Architecture Decisions And Guardrails

### Emit an ordinary SDL artifact plus one digest-bound synthesis record

The output is strict ordinary `sdl-yaml/v1` and an independently versioned,
closed synthesis record that binds the candidate bytes and canonical SDL
identity. Do not add `provenance`, `source_assertions`, `semantic_loss`,
`review`, generic `metadata`, or another synthesis-only section to `Scenario`.
Doing so would create privileged SDL syntax and make manual and generated
content follow different parsers.

The synthesis record is the source-neutral exchange contract. It should carry
one stable record id/version and compose the existing
`ArtifactTransformationReportModel`. The report's source digest commits to the
complete admitted synthesis input; its target digest is the candidate's
canonical SDL semantic digest; and a separate exact-representation digest may
bind the emitted UTF-8 YAML bytes. Keep byte identity and semantic identity
distinct.

A successful report has exactly one complete candidate. A refused report has
no candidate. `needs-decision` is a typed synthesis disposition represented by
an all-or-none refused transformation plus unresolved-choice records; it is not
a partially trusted SDL output. A renderer may show a preview, but the preview
is not the candidate artifact and cannot enter admission.

### Normalize assertions without defining a universal external ontology

The input side needs one bounded source-neutral assertion family that at least
distinguishes concepts, relationships, preconditions, order constraints,
parameterization, and example references. Each assertion has a stable id and
retains its exact source coordinate and provenance. Kind-specific bodies must
be a closed discriminated union; an open subject-predicate-object bag would
force unlike meanings into one weak schema and invite source-specific keys in
`metadata`.

Use `ExternalConceptSchemeCoordinateModel` for external concept coordinates.
Use inert, digest-pinned references for source relation terms, queries, and
example artifacts. Do not pretend a source relation term is an
`ExternalConceptRelationshipKind`, an SDL `Relationship`, a workflow edge, a
proposition, or a precondition until an exact transformation rule and required
decision establish that mapping.

The source envelope pins:

- source authority and scheme/assertion-format identity;
- exact revision and content digest where supplied by the source contract;
- the digest of the complete bounded assertion set supplied to RAES;
- extraction-query profile/id/version/digest, without query execution syntax;
  and
- adapter profile/id/version/digest that produced the neutral assertions.

The core consumes supplied facts only. A locator is inert and passes
`validate_safe_absolute_uri()`; it is never permission to fetch. Retrieval,
credentials, pagination, source-specific parsing, query execution, and pack
workflow stay with env-packs/source adapters. The normalized assertion digest,
not a remote revision label alone, is the reproducibility boundary once bytes
cross into RAES.

### Keep facts, assumptions, decisions, constructs, and loss orthogonal

The synthesis record must expose five independently identified collections:

1. source assertions, which repeat no RAES claim;
2. transformation assumptions, each bound to the exact transformation profile
   and source assertion(s) on which it operates;
3. unresolved choices or blockers, with stable reason codes, alternatives, and
   affected assertions/construct intents;
4. explicit human or governed-policy decisions, with exact decision basis and
   policy id/version/digest where applicable; and
5. generated native constructs, keyed by canonical SDL address and linked to
   every contributing assertion, assumption, default, decision, and rule.

Use a closed synthesis-origin vocabulary such as imported assertion, inferred
structure, transformation default, and explicit author decision. A construct
may have several contributions; do not collapse origin to one winning enum.
Every generated semantic field must be covered under a declared construct
trace coverage profile. Untyped prose is not complete provenance.

Accepted approximation or omission is transformation loss and must remain in
the incumbent transformation report with affected identity and a bounded
diagnostic. Any loss that can change meaning additionally requires an exact
author/governed-policy decision reference. An assumption is not a fact, a
default is not a decision, a decision is not authentication, review is not
admission, and a source citation is not evidence that the native construct is
true.

### Refuse unresolved semantic choices instead of smuggling them into SDL

Ambiguous ordering, missing native semantics, unsupported relationships, and
unresolved parameterization are expected domain outcomes. They use closed
reason codes and one of these dispositions:

- `requires-decision` when a finite, explicit author or governed-policy choice
  can resolve the ambiguity without inventing hidden semantics;
- `unsupported` when the selected SDL/profile has no honest native
  representation; or
- accepted transformation loss only when a named policy permits the exact
  loss and an explicit decision accepts it.

No material unresolved outcome may produce a successful candidate. Do not hide
one in descriptions, comments, empty collections, arbitrary relationships,
`other`, `${...}` placeholders, fake workflow order, guessed preconditions, or
syntactically valid defaults. If an ordinary SDL variable honestly represents
author-controlled parameterization, generate it as an ordinary governed SDL
variable and trace that choice; an unresolved choice about whether or how to
parameterize remains a blocker.

### Re-admit emitted bytes through the production authoring path

Synthesis first builds a closed normalized-authoring value, renders it with the
incumbent deterministic SDL rendering seam, and then parses the actual emitted
bytes through strict production `parse_sdl()` with semantic validation enabled.
The object used to render the candidate is not admission evidence. A public
deterministic model-to-SDL renderer may be extracted from the existing
formatting path if it gains this second real caller; do not add a synthesis-only
YAML serializer or call `Scenario.model_validate()` as the final gate.

The initial profile should emit a self-contained normalized candidate. If a
future profile emits imports, the bytes must pass `parse_sdl_file()` and the
existing file-backed module resolver, lock/trust/digest/export checks, namespace
collision rules, and `CompositionBudget`. The synthesis core must not emulate
that resolver or fetch modules.

After review, the artifact follows exactly the manual lifecycle:

`parse/composition -> semantic validation -> instantiation -> instantiated
admission -> compiler/planner admission`.

The synthesis result records only gates that actually ran. Reuse a standalone
scenario `ValidationBasisDisclosureModel` when portable gate/strength
disclosure is required. Parsing or synthesis success never claims compilation,
planning, backend support, execution, observation, or admission.

### Make identity, replay, and comparison deterministic

The derivation digest includes the source envelope digest, extraction-query
digest, adapter profile digest, transformation profile id/version/digest,
policy digest, normalized assumption set, normalized decision set, target SDL
profile, and all output-affecting limits. It excludes wall clock, hostname,
username, filesystem location, UUIDs, random values, process state, and
presentation order.

Source assertions, assumptions, choices, decisions, construct traces, losses,
checks, and diagnostics use stable ids plus documented sorted-unique order.
Maps use embedded-id/key equality. Preserve all candidates until ambiguity has
been evaluated; never first-match or set-collapse collisions.

Positive fixtures compare both exact representation bytes where the profile
promises byte stability and `canonical_sdl_digest()` for semantic stability.
Cross-process hash-seed coverage should extend the existing pipeline
determinism witness. A changed source, query, adapter, transformation, policy,
or decision necessarily changes the derivation digest even if candidate SDL is
semantically unchanged.

For an inspectable semantic diff, compare the two admitted scenario candidates
through the existing semantic-comparison request/result and owner adapter.
Supply the synthesis transformation report as exact rename/loss evidence where
applicable. Do not recursively diff raw dictionaries or infer semantic change
from byte or derivation-digest inequality. Report derivation change and SDL
semantic change as separate axes.

### Preserve bindings and information flow without creating new policy

When synthesis creates a candidate subject corresponding to an external
concept, emit or update an ordinary `external-concept-bindings/v1` document
whose subject coordinate uses the candidate's exact lifecycle phase, canonical
address, and artifact digest. Re-run `admit_external_concept_bindings()` against
the candidate subject index and supplied pinned scheme snapshot. Do not copy a
smaller binding shape into the synthesis record.

Every trace retains source/provenance references and the information-flow
limitations already attached to its inputs. Aggregation, derivation, hashing,
or generating SDL is not declassification. The synthesis artifact itself does
not carry an ACL or grant visibility. Participant-visible inspection or
delivery must use the existing authenticated audience binding, exact-cut
policy, crossing/redaction/disclosure, and audit path. Operator secrets never
belong in the portable input, derivation, diagnostics, fixtures, or candidate;
scenario-target values remain governed by ADR-056/057 at their ordinary SDL
surface.

## Canonical Cross-Cutting Concerns To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| package and authority boundary | ADR-009/019/036, `specs/authority/authority-boundary.yaml`, and `tools/policy/adr_policy.yaml`; contracts in `raes_contracts`, SDL-aware pure transformation at `raes.transformations`, no runtime/backend ownership |
| source concepts and bindings | issue #986, `ExternalConceptSchemeCoordinateModel`, `ExternalConceptBindingDocumentModel`, local snapshot adapters, `external_concept_subjects()`, and `admit_external_concept_bindings()` |
| transformation envelope | `ArtifactTransformationReportModel`, `ArtifactTransformationPolicy`, all-or-none result convention, checks, preservation, identity map, losses, diagnostics, and canonical policy/derivation digests |
| SDL ingress and identity | `SDLParserLimits`, safe `sdl-yaml/v1` loading, `Scenario`, module composition/trust, `DeclarationIndex`, `SemanticValidator`, ADR-076/078, and exact canonical addresses |
| later admission | `instantiate_scenario()`, `admit_instantiated_scenario()`, unresolved-token rejection, canonical instantiated snapshots, and compiler/planner admission; no generated-content bypass |
| canonicalization and diff | `canonical_json_digest()`, `canonical_sdl_digest()`, exact representation digests, `SemanticComparisonRequestModel` / result, `analyze_semantic_comparison()`, and owner-specific adapters |
| validation disclosure | ADR-072, validation profiles, and `ValidationBasisDisclosureModel`; disclose only gates actually run and do not duplicate strength/gate enums |
| contract mechanics | `ContractModel(extra="forbid")`, strict shared scalar/digest/time types, discriminated unions, bounded collections, map-key identity checks, and `x-raes-invariants` |
| diagnostics and errors | `Diagnostic` / `DiagnosticModel`, existing SDL exceptions at SDL boundaries, `StrictJsonIngressError` at JSON ingress, and `sanitized_failure_message()` at conformance/API adapters; no issue-specific exception tree |
| provenance and evidence | ADR-064/066/080, typed evidence/artifact references, `ArtifactTransformationReportModel`, and candidate construct traces; keep assertion, evidence, decision, derivation, and validation basis distinct |
| information flow | ADR-056/057/085/095, existing participant audience/policy/crossing/redaction/disclosure contracts, and API-423; add no synthesis ACL or declassification rule |
| persistence | ordinary versioned contract artifacts, candidate YAML bytes, exact id/version/digest references, and the packaged corpus seam in `raes_contracts.corpus`; no database, cache, mutable registry, runtime snapshot metadata, or audit blob |
| schema and workflow | hand-governed `contracts/schemas/`, `schema_bundle()`, schema-publication entry, `contracts/fixtures/`, conformance registries, `tools/generate_contract_schemas.py`, repository policy, canonical nox/CI graph, and `tools/verify_all.py` |

## Cross-Cutting Validation, Security, And Runtime Layers

The intended design must pass every applicable layer below.

1. **Bounded portable-input shape.** Raw JSON uses
   `parse_bounded_json_object()` before the closed contract model, rejecting
   excess bytes, duplicate members, non-finite numbers, unknown fields,
   unbounded collections, malformed digests, and key/id mismatches. Source
   assertion kinds are a discriminated union, not caller-selected Python types.
2. **Source and query pinning.** Exact authority, revision, content/assertion
   digest, extraction-query coordinate, adapter profile, and transformation
   profile join before synthesis. Stale, missing, ambiguous, superseded, or
   non-reproducible inputs fail closed. Locator fields pass
   `validate_safe_absolute_uri()` and never trigger retrieval.
3. **Transformation-policy gate.** The fixed trusted transformation-profile
   registry selects code; scheme id, assertion kind, query text, URI, class
   name, module path, callback, and plugin name never do. Assumptions, defaults,
   decisions, accepted loss, and unresolved choices satisfy the exact selected
   profile before a target exists.
4. **SDL source/config shape.** Emitted UTF-8 YAML passes parser byte/depth/node
   limits, YAML 1.2 Core resolution, tag/directive/alias/duplicate-key guards,
   canonical-key handling, closed `SDLModel` construction, portable ids, and
   source diagnostics. Synthesis does not relax migration policy.
5. **Composition and filesystem trust.** A candidate with imports additionally
   passes the existing file-backed resolver, confined path handling,
   lockfile/trust/signature/version/digest/export checks, cycle and namespace
   checks, and aggregate composition budget. The core neither searches the
   filesystem nor accepts host paths as portable identity.
6. **SDL semantic and lifecycle admission.** `SemanticValidator` resolves
   references, ambiguity, uniqueness, cycles, workflows, parameterization, and
   section-specific invariants. Instantiation rejects missing bindings and
   unresolved tokens, revalidates the concrete artifact, and compiler/planner
   entry points re-admit it. No `skip_semantic_validation`, private validated
   flag, direct model construction, or candidate status bypasses these gates.
7. **Binding and provenance joins.** Generated addresses resolve uniquely;
   every contributing assertion/assumption/default/decision/rule resolves;
   source and target digests match; output concept bindings pass #986's local
   contextual admission. Missing coverage, duplicate identities, stale inputs,
   or dangling trace refs refuse the transformation.
8. **Authentication and authorization.** The pure library has no authentication
   surface and a provenance `authority` or decision actor ref is not verified
   identity. Env-packs/Hub authorize their own retrieval and authoring journey.
   If later mounted on the RAES control plane, reuse
   `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   audience/target and role checks, request-size guards, fingerprints,
   idempotency for persisted mutation, `AuditEvent`, and the generic redacted
   unexpected-error envelope.
9. **Secret and information handling.** Portable inputs and outputs contain no
   credentials, tokens, environment-variable names, secret locator query
   fields, remote headers, private prompts, operator-secret values, or resolved
   secret references. Do not assume a digest makes secret content safe.
   Participant-visible views pass incumbent deny-first information-flow policy
   over the candidate, record, source refs, losses, and diagnostics.
10. **Configuration and environment.** Every semantic selection is an explicit
    typed argument/profile/decision pinned by digest. No environment variable,
    current working directory, locale, clock, mutable singleton, installed
    plugin set, or “latest” source selects behavior. Existing parser limits may
    be narrowed by a governed profile but never widened by input.
11. **OS, process, and network exposure.** Core parse, synthesis, replay, and
    diff perform no network access, subprocess execution, shell interpolation,
    daemon calls, or host mutation. URIs, queries, source ids, candidate text,
    and secrets never enter process argv. If a determinism test uses a
    subprocess, use fixed argv and pass only safe repo fixture paths and public
    profile values.
12. **Diagnostics, errors, logs, and envelopes.** Expected ambiguity,
    unsupported semantics, stale inputs, and required decisions are typed
    dispositions with stable codes, not thrown exception prose. Malformed input
    retains existing JSON/Pydantic/SDL exception ownership; adapters sanitize
    it. Durable logs/reports may contain safe record/assertion/candidate ids,
    profile ids/versions, digests, counts, gate outcomes, and diagnostic codes.
    They must not contain raw source/candidate bodies, rejected values, query
    text, URI query strings, decisions that may disclose source content,
    Pydantic `input_value`, environment dumps, tracebacks, or raw exceptions.
13. **Persistence and publication.** The durable units are the candidate bytes,
    synthesis record, optional #986 binding document, and optional validation
    disclosure, all joined by exact identities/digests. Do not add a repository
    class, database migration, cache, generic metadata side channel, runtime
    snapshot field, or bespoke audit store. New schemas follow the normative
    schema, Python parity, publication entry, fixture, corpus packaging, and
    conformance registry workflow once each.

## Extensibility Seam

The seam is a governed transformation profile selected by exact
`(profile_id, version, digest)` and a closed source-assertion discriminated
union. A new unrelated source scheme adapts into the same assertion kinds and
uses the same synthesis engine; it does not add a scheme branch. A genuinely
new assertion semantic adds one union variant plus one profile rule and
fixtures. A new SDL target version, ordering strategy, or loss policy adds a
profile revision rather than editing the meaning of an existing derivation.

Trusted dispatch is keyed by transformation profile, never by source scheme.
This lets the next scheme reuse the core while keeping retrieval protocol,
source syntax, query language, and authoring UI outside RAES. It also prevents
the apparent extension seam from becoming a dynamic plugin/import mechanism.

## Gotchas And Anti-Patterns

Avoid:

- embedding synthesis provenance or unresolved choices in SDL descriptions,
  comments, `metadata`, relationships, variables, or a new top-level section;
- treating an authoritative external assertion as RAES truth, native semantics,
  admission, executable behavior, evidence, or a backend capability;
- forcing a not-yet-native assertion into #986's binding model, or duplicating
  the #986 scheme coordinate/binding schema inside synthesis;
- widening SEM-218 provenance to encode synthesis origins, or treating
  generated YAML as proof of explicit human authorship;
- one generic triple/JSON bag for concepts, relations, ordering, parameters,
  examples, assumptions, decisions, and loss;
- mapping unknown relations by string equality, enum label, first match,
  source ordering, array position, or scheme-specific conditionals;
- silently inventing order, preconditions, parameter defaults, identities,
  relationship direction, or native constructs to obtain schema-valid SDL;
- emitting a partial candidate on a material unresolved choice, or calling a
  preview a candidate;
- constructing `Scenario` directly and treating Pydantic success as parser or
  semantic admission; using `skip_semantic_validation`; or adding a generated
  content flag to validators/compiler/planner;
- using transformation success, validation disclosure, review acceptance, or
  source authority as synonyms for admitted/executable;
- comparing raw mappings, byte digests, or derivation digests and calling the
  result a semantic diff;
- fetching a source locator, resolving “latest,” discovering plugins, reading
  environment configuration, or putting query/source values in subprocess
  arguments from the SDL core;
- copying source bodies, evidence payloads, credentials, or rejected values
  into diagnostics, logs, fixtures, candidate metadata, or error envelopes;
- adding a synthesis exception hierarchy, logger, telemetry service, database,
  cache, controller, API, CLI-only schema, or parallel conformance workflow;
  and
- editing source-specific env-pack, Hub, or remote-retrieval behavior in this
  repository as part of the core contract.

## Non-Goals And Implementation Boundary

- No automatic semantic equivalence, truth, correctness, completeness,
  realizability, or execution claim is made about an external source.
- No external assertion becomes executable, admitted, or privileged.
- No source-specific syntax, ontology catalog, query language, catalog client,
  remote retrieval, credential flow, pagination, pack orchestration, UI, or
  demonstration belongs in the SDL core.
- No new SDL section, authoring dialect, parser bypass, validation hierarchy,
  participant policy, evidence store, persistence layer, or runtime behavior is
  authorized.
- Initial support need not cover every external semantic family. Unsupported
  source relations and missing native semantics remain explicit refused or
  decision-required outcomes.
- Candidate review and explicit decisions do not merge, admit, instantiate,
  compile, plan, realize, or execute the candidate. Those remain separate
  ordinary workflow actions.
- Hub discoverability is owned by Hub #25; env-packs/source adapters own
  retrieval and source-specific authoring pipelines.
