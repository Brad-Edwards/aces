# Issue 986 Portable External Concept Bindings Preflight

Date: 2026-07-30

Issue: #986.

Requirement: none. The GitHub issue title, body, acceptance criteria, and
non-goals are the authoritative contract.

This note records architecture guardrails for a typed, scheme-neutral external
concept-binding surface. It is guidance only: it does not add or change
contracts, schemas, validators, SDL behavior, fixtures, persistence, or an
implementation plan.

## Existing Authorities And The Boundary They Establish

- ADR-012 and ADR-062, `specs/concept-authority/`, and
  `contracts/concept-authority/` already own concept authority, provenance
  classification, controlled vocabularies, catalogs, and offline governance.
  A portable external binding must compose with those authorities rather than
  create another concept-family catalog or global ontology registry.
- Apparatus-manifest `ConceptBinding` binds a governed manifest vocabulary
  scope to a native RAES concept family. It is not a general external
  term-mapping assertion. Expanding that model would conflate manifest
  vocabulary governance with author-authored claims about arbitrary exact RAES
  subjects.
- SEM-217 and `semantic_binding_effects.py` already distinguish the external
  knowledge effects `annotates`, `aligns`, `refines`, and `constrains`. These
  terms do not by themselves alter schemas, runtime behavior, or admission.
  Issue #986 must reuse that meaning and must not publish a second effect
  vocabulary with subtly different semantics.
- The ATT&CK, ATLAS, and NIST CSF source contracts in
  `contracts/concept-authority/` are offline, versioned authority snapshots,
  but their current Python models are source-shaped. They are useful resolver
  inputs and fixtures, not the author-facing portable assertion shape.
- ADR-076 and `raes._declarations.DeclarationIndex` own exact SDL authoring
  identities and collision-preserving address resolution. Processor/runtime
  `CompiledAddress`, JSON Pointer, collection position, aliases, and prose
  names are not substitutes for canonical authoring identity.
- ADR-078, `raes.phase_contracts`, and the canonical digest helpers distinguish
  normalized authoring, expanded, instantiated, and snapshot subjects. A
  reference valid in one lifecycle phase is not silently valid in another.
- ADR-079 separates propositions, assertions, probe bindings, truth results,
  and outcomes. An external concept binding is none of those and cannot prove
  objective satisfaction.
- ADR-070 owns realization envelopes and capability boundaries. An external
  binding cannot grant a capability, make a subject realizable, or transform a
  value into a realizable form.
- ADR-064 and the experiment evidence contracts separate capture
  specifications, evidence records, and derived measures. A binding may cite
  evidence; it is not itself evidence or proof.
- ADR-066 and ADR-085 separate evidence, view, authorization, availability,
  delivery, redaction, declassification, and disclosure. Listing participants
  on a binding is not permission to disclose it and is not evidence that it
  was delivered.
- `ContractModel`, the shared strict types, `Diagnostic`/`DiagnosticModel`,
  conformance registries, schema publication records, generated-schema parity,
  and fixture tooling already own the cross-cutting contract lifecycle.

These decisions are sufficient for issue #986. A new ADR is not warranted
unless implementation proposes to alter SDL phase transitions, make external
bindings executable or validation-authoritative, add a network/global scheme
registry, or change realization, evidence, or participant-disclosure
boundaries.

## Architecture Decisions And Guardrails

### Publish one standalone authored assertion family

Publish one versioned, closed root contract family, provisionally identified as
`external-concept-bindings-v1`, with a stable binding-set identity and
individually stable binding identities. Its assertion value model may be reused
by other carriers, but there must be one canonical schema and one semantic
admission path.

The first contract should remain a standalone authored artifact. Embedding the
binding collection into every SDL phase would:

- make an artifact-digest subject reference self-referential;
- require propagation and transformation rules across every ADR-078 phase;
- make annotations part of SDL structure without adding semantic authority;
  and
- encourage compilers and runtimes to treat presence as behavior.

Other artifacts may refer to the standalone binding set by exact
id/version/digest. Adding a top-level SDL section or copying bindings into
compiled/runtime artifacts requires a separate phase-boundary decision.

The contract is closed. It must not contain an unconstrained metadata,
extensions, attributes, annotations, context, or arbitrary JSON object field.
Future portable dimensions belong in a versioned contract revision or a
governed extension vocabulary.

### Identify the RAES subject exactly and phase-correctly

The subject coordinate must make these independent:

- subject kind;
- owning contract or surface identity and version;
- lifecycle phase;
- exact stable canonical reference; and
- the owning artifact's canonical digest where that subject kind and phase
  admit one.

Subject resolution is exact and collision preserving. For SDL declarations,
reuse `DeclarationIndex` semantics: resolve the canonical authoring address,
preserve all alias collisions, and require exactly one result. Do not import
the private SDL index into `raes_contracts`; keep resolution behind the owning
SDL boundary or extract only a dependency-neutral collision helper if it has
more than one real caller.

A data-driven rule keyed by `(subject kind, contract/surface, lifecycle phase)`
must select the canonical reference grammar and whether a digest is required.
That is the extensibility seam for another RAES subject kind. It must not be a
chain of scheme-specific or artifact-specific conditionals inside the binding
model.

`ValidationSubjectReferenceModel`,
`ParticipantCrossingSubjectReferenceModel`, and `ExperimentReferenceModel`
demonstrate useful exact-coordinate patterns, but each has a narrower semantic
owner. Do not broaden or union them into a falsely universal subject type.

Aliases, prose labels, JSON Pointer, array position, filesystem paths, and
processor/runtime compiled addresses may be displayed as non-authoritative
context only. They never establish identity or break a tie.

### Keep the scheme coordinate portable and inert

The external coordinate must independently identify:

- scheme id and naming authority;
- exact scheme revision;
- source locator or prefixed source-content digest, with both retained when
  supplied; and
- exact concept identifier in that revision.

Scheme id, authority, revision, locator, digest, and concept id are data. No
scheme name may select a Python class, parser, validator, URL template, import
path, plugin, command, or network client.

A source locator is an inert identifier, not permission to dereference.
Reuse or extract the existing associated-artifact URI safety rules: require an
absolute URI and reject user information and secret-bearing query fields. The
scheme-source profile must additionally reject host-local paths, `file:` and
inline `data:` locators, and fragments, because the concept id is already a
separate field and fragments would create a second opaque identifier channel.
Never place a locator in a subprocess argument.
A content digest uses the existing prefixed-digest type and canonical
digest/checksum rules; it must not introduce another bare-hash format.

Use one dependency-neutral local scheme-snapshot descriptor as contextual
resolver input. It carries the asserted scheme coordinate, canonical concept
membership, and bounded deprecation/supersession facts. Existing ATT&CK and
NIST CSF snapshots must adapt to that same input and pass through the same
resolver and diagnostics. Adapters translate existing source artifacts; they
must not make the portable contract a universal scheme schema.

### Separate assertion dimensions instead of recreating a mapping string

Every binding must keep these semantically distinct:

- relationship kind;
- author motivation and its basis;
- claimed semantic effect;
- asserting perspective or party and the basis of its authority;
- participant availability intent, when present;
- assertion provenance;
- supporting evidence references;
- confidence posture and basis;
- approximation or semantic loss;
- limitations; and
- review status and review references.

Use closed or governed vocabularies from
`controlled-vocabularies-v1.json` wherever portable comparison matters.
`annotates`, `aligns`, `refines`, and `constrains` retain the SEM-217 meanings.
If Python enums remain convenient, they must be derived from or parity-tested
against the catalog; source code and the catalog cannot both be independent
authorities.

Free prose may explain motivation, limitations, or review reasoning, but prose
does not replace required typed fields. Relationship is not effect, motivation
is not confidence, scheme authority is not assertion authority, review status
is not resolution status, and assertion provenance is not evidence.

Claims with stronger meaning require stronger explicit support:

- equivalence/alignment claims need an explicit loss posture and review basis;
- refinement or approximation must disclose divergence or loss;
- confidence requires its basis; a numeric score additionally requires a
  named calibration/profile rather than an unexplained probability; and
- `constrains` has no validation effect unless it resolves to an already
  governed RAES profile or validator that independently owns that authority.

### Resolve locally with two distinct admission levels

Structural parsing/admission validates the closed artifact shape, field
formats, conditional presence, vocabulary membership, URI safety, and internal
identity uniqueness. It performs no lookup and therefore remains available for
offline parse, replay, and inspection.

Contextual semantic admission is a pure operation over explicitly supplied
local inputs:

- the exact RAES subject index for the declared contract and phase; and
- zero or more pinned scheme-snapshot descriptors.

It must not consult the network, environment, filesystem search paths, process
state, a mutable singleton registry, or “latest” scheme state.

Resolution has deterministic outcomes:

| Outcome | Required behavior |
| --- | --- |
| Resolved/current | Exactly one subject and one concept match all asserted identities, revision, locator/digest constraints, and policy gates. Only then may the declared effect be considered by an existing governed consumer. |
| Unavailable | No matching local scheme snapshot was supplied. Preserve the assertion as parseable and inspectable, mark it inactive, emit a stable bounded diagnostic, and do not fetch or infer. |
| Stale | A scheme identity is present but its revision or digest conflicts with the assertion or required profile. Fail current semantic admission; never fall back to “latest”. |
| Ambiguous | More than one subject, alias, scheme, or concept candidate matches. Fail semantic admission without first/last/set-collapse behavior. |
| Superseded | Preserve the original concept and revision plus separately supplied successor facts. Never rewrite automatically. Historical replay may resolve only against the exact original snapshot; current admission requires an explicit governed policy for superseded terms. |

An unknown concept in an available matching revision also fails semantic
admission. The resolver computes resolution state; an author cannot assert a
trusted `resolved` value.

Negative fixtures for stale, ambiguous, unknown-relation, missing-provenance,
and impermissible-disclosure cases must exercise the same public contract and
semantic admission functions as positive fixtures. “Unavailable is
inspectable” does not mean “unavailable has semantic force.”

### Participant availability is not disclosure authority

A participant scope on a binding expresses intended eligibility or
availability only. If a carrier claims actual availability, exposure, or
delivery, contextual admission must join it to the existing deny-first
participant information-flow authority, including the exact participant,
episode/snapshot, subject, exposure/crossing policy, and applicable
authorization.

Reuse `ParticipantDecisionSurfaceExposureBindingModel` and
`ParticipantCrossingOccurrenceModel` where those facts are claimed. Do not add
a binding-specific access-control list, audience gateway, declassification
mechanism, policy engine, audit store, or disclosure log. A participant id on
the assertion never bypasses redaction, information-flow control, control-plane
audience binding, or ordinary admission.

### Preserve adjacent semantic boundaries

- Native apparatus `ConceptBinding` continues to bind manifest vocabulary
  scopes to RAES concept families. The new assertion references exact RAES
  subjects and external concepts; neither replaces the other.
- A portable external binding does not create a proposition, truth result,
  objective outcome, score, or behavioral claim.
- It does not alter a realization envelope, grant a capability, authorize an
  action, mutate the transition system, or establish realization.
- Supporting evidence fields are typed references to existing evidence or
  associated-artifact contracts. Do not copy evidence payloads into the
  binding or treat citation as verification.
- The assertion itself is not a concept-family declaration, scheme snapshot,
  validation profile, participant exposure, provenance proof, or review
  decision.

## Required Cross-Cutting Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Concept authority | ADR-012, ADR-062, `specs/concept-authority/`, concept-family and controlled-vocabulary catalogs, and SEM-217 effect semantics. Extend governed terms once; do not add parallel registries or enums. |
| Exact subject identity | ADR-076, `DeclarationIndex`, owning-contract identity rules, and collision-preserving exact resolution. Keep authoring and compiled addresses distinct. |
| Lifecycle and digest | ADR-078, `raes.phase_contracts`, `canonical_sdl_digest()`, `canonical_instantiated_sdl_digest()`, and `canonical_contract_digest()`. Reuse RFC 8785/JCS plus SHA-256, extracting a dependency-neutral public helper if the current module ownership would otherwise create a conceptually wrong import; do not add binding-local JSON canonicalization. |
| Contract shape | `ContractModel(extra="forbid")`, `NonEmptyString`, `PrefixedDigestString`, RFC 3339 time, closed-unit-interval, and existing strict/discriminated value patterns. Add explicit validators where Pydantic coercion would weaken a semantic invariant. |
| URI safety | The associated-artifact absolute-URI and secret-bearing component checks. Extract a public dependency-neutral helper if reuse would otherwise require importing a private validator. |
| Schema authority | Hand-governed `contracts/schemas/`, Python `schema_bundle()` parity, and a sharded `contracts/schema-publication/entries/` record with `last_change` and content hash for each published schema change. |
| Validation | Existing model validators, controlled-vocabulary helpers, owning subject resolvers, `SemanticValidator` where SDL context is required, and the `raes_conformance` structural/semantic registries. There is one public validation path, not fixture-only logic. |
| Diagnostics | `Diagnostic`/`DiagnosticModel`, bounded SDL model diagnostics, and conformance `sanitized_failure_message()`. Emit stable codes and safe coordinates without Pydantic input echo or exception-string leakage. |
| Evidence | ADR-064/066 and `ExperimentEvidenceRecordModel` plus existing typed evidence/artifact references. Preserve evidence, measure, view, and assertion boundaries. |
| Participant flow | ADR-085 and the existing exposure/crossing/control-plane identity and policy contracts. Deny first and join exact context before claiming delivery. |
| Publication and tests | Existing public export/facade checks, JSON artifact checker, schema generator parity, conformance registry, and positive/negative fixture runner. ATT&CK and NIST CSF use identical syntax and validation code. |
| Persistence | Existing versioned contract artifacts and id/version/digest references. No new database, repository, cache, metadata side channel, or runtime snapshot stuffing is justified. |

## Cross-Cutting Security And Runtime Layers

The intended standalone contract passes through these layers:

1. **Shape and parser boundary.** `ContractModel`, strict shared types,
   conditional model validation, catalog validation, and schema validation
   reject extra fields, invalid digests, unsafe locators, missing provenance,
   unknown relationship/effect terms, and structurally invalid participant
   scopes. Models must not fetch or instantiate caller-selected code.
2. **Subject and scheme semantic boundary.** Owning subject resolvers and the
   pure local scheme resolver require exact, unique, phase-correct,
   digest/revision-matching context. Unavailable, stale, ambiguous, and
   superseded states cannot silently acquire semantic effect.
3. **Authorization and disclosure boundary.** Assertion authorship or an
   `authority` string is descriptive provenance, not authenticated identity.
   Any actual participant availability/delivery passes ADR-085's existing
   identity, audience, policy, exposure/crossing, redaction, and admission
   checks. No new auth surface is introduced by the artifact.
4. **Secret-handling boundary.** The contract contains no credentials, tokens,
   secret values, secret-reference resolution, environment-variable names, or
   credential-bearing URI components. Scheme locators and evidence references
   are inert. Existing secret providers and runtime authorization remain
   entirely outside this contract.
5. **Configuration/environment boundary.** Resolution context is an explicit
   typed argument pinned by id/revision/digest. No environment binding,
   configuration key, hidden default registry, plugin discovery, or mutable
   global selects a scheme, revision, subject, or semantic effect.
6. **OS and network boundary.** Parse, admit, replay, and inspect perform no
   live network lookup, subprocess execution, shell interpolation, command
   dispatch, or host-path access. Locators, concept ids, and authority strings
   never enter process argv.
7. **Diagnostics, error-envelope, and logging boundary.** Public failures use
   stable diagnostic codes, bounded locations, and sanitized messages. Logs may
   contain a safe binding id, scheme id/revision, subject kind/canonical ref
   when its classification permits, digest, counts, and outcome. They must not
   contain source bodies, credentials, query strings, environment dumps,
   rejected attacker-controlled values, Pydantic `input_value`, raw exception
   text, or tracebacks in public envelopes.
8. **Persistence and audit boundary.** Artifacts remain ordinary versioned
   contract documents. Do not place bindings or raw assertion fields into
   generic `metadata`, `details`, logs, audit-event payloads, or runtime
   snapshot metadata. Existing provenance, evidence, and audit records may
   reference a binding by exact identity and digest.

The initial artifact introduces no controller, service, API, authenticated
mutation, or OS integration. If an API later accepts or publishes these
artifacts, it must reuse `ControlPlaneSecurityConfig.strict_defaults()`,
verified identity, audience/target binding, role checks, request-size guards,
idempotency/fingerprints, `AuditEvent`, and the existing redacted internal-error
envelope. Those are mandatory incumbents, not reasons to add issue-specific
auth or exception hierarchies.

## Extensibility Seam

The deliberate seam is explicit resolver context, not a global scheme
registry:

- a subject-kind rule selects the owning reference grammar, phase, resolver,
  and digest requirement;
- a scheme snapshot adapter supplies the neutral pinned descriptor and concept
  membership; and
- a governed consumer decides whether a successfully resolved declared effect
  is relevant to its already-authorized operation.

A third unrelated versioned scheme should require a new snapshot adapter/data
artifact only. A new RAES subject kind should require one owner rule and
resolver only. Neither change should edit the assertion schema, add a
scheme-name branch, relax exact identity, or change offline failure behavior.

## Gotchas And Anti-Patterns

- Do not extend apparatus `ConceptBinding`, `BehavioralClaimBindingModel`, a
  validation subject, an experiment reference, or a participant-crossing
  subject until it appears generic. Their names overlap; their authorities do
  not.
- Do not migrate every existing CWE, ATT&CK, ATLAS, NIST, or free-label field
  in this issue. Existing source-shaped fields are compatibility surfaces, not
  templates for the new contract.
- Do not publish one opaque `mapping`, `relation`, or metadata string that
  collapses relationship, motivation, effect, confidence, provenance, review,
  or loss.
- Do not use names, labels, aliases, JSON Pointer, list order, case folding,
  first/last match, or set/map deduplication to resolve a subject or concept.
- Do not select “latest”, auto-upgrade a revision, auto-follow a successor,
  accept a digest mismatch, or let unavailable data degrade to a warning while
  retaining semantic effect.
- Do not make a URL required for offline validity, dereference a URL during
  validation, or hide network/cache access behind a validator.
- Do not let an author-declared effect install a validator, constrain SDL,
  rewrite propositions, alter outcomes, grant capability, establish
  realization, or bypass ordinary admission.
- Do not interpret participant scope as an ACL or delivery record.
- Do not create a second schema source, digest profile, controlled-vocabulary
  registry, fixture runner, semantic-effect enum authority, diagnostic class,
  exception hierarchy, repository, cache, audit store, or disclosure workflow.
- Do not log or echo whole rejected documents. External identifiers, locators,
  motivations, limitations, and evidence references are attacker-controlled
  until admitted.

## Non-Goals And Implementation Boundary

Issue #986 does not:

- select or mandate an external knowledge ecosystem;
- define a universal ontology or portable source format for schemes,
  participants, environments, evidence, or provenance;
- turn external concepts into SDL syntax or executable constructs;
- redesign native concept families or apparatus `ConceptBinding`;
- redesign propositions, outcomes, realization envelopes, evidence records,
  participant information-flow control, or admission;
- add live lookup, scheme synchronization, successor discovery, a global
  registry, a cache, a database, an API, or a new control plane;
- migrate all existing source-specific fields;
- add an unconstrained metadata bag; or
- make assertions true, reviewed, disclosed, or operational merely because
  they parse.
