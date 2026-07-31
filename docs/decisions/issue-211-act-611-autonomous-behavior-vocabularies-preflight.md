# Issue 211 ACT-611 Autonomous Behavior Vocabularies Preflight

Date: 2026-07-30.

Issue: #211.

Requirement: ACT-611, `07f918ad-2bb7-41a5-8975-904f1129ee1e`.

This note records architecture guardrails for autonomous-service and
autonomous-agent behavior vocabularies. It is guidance only: it does not add
source records, contracts, schemas, adapters, fixtures, validators, SDL
fields, runtime behavior, or an implementation plan.

## Existing Authority And Decision

ADR-067 and `specs/formal/participant-behavior-model/README.md` remain the
native participant-behavior authority. Issue #986 and
`specs/concept-authority/external-concept-bindings.md` already publish the
scheme-neutral assertion boundary and its single offline admission path.
ACT-611 composes those authorities.

No new ADR is required. An ADR would be warranted only if implementation
proposes to make an external term executable or validation-authoritative, add
an SDL participant or behavior field, alter lifecycle identity, introduce
network resolution, or change participant information-flow or realization
boundaries.

The implementation decision is:

- publish ActivityStreams Activity types and FIPA communicative acts as two
  unrelated, versioned external schemes;
- project their pinned local source records into the existing
  `ExternalConceptSchemeSnapshotModel`;
- bind both schemes to exact `behavior_specifications.<name>` declarations
  through unchanged `external-concept-bindings/v1` syntax and
  `admit_external_concept_bindings()`; and
- keep all external terms descriptive assertions. They do not become SDL
  actions, behavior modes, participant kinds, capabilities, authority, runtime
  evidence, or outcomes.

## Primary-Source Decisions

### W3C ActivityStreams 2.0 Activity Vocabulary

- **Authority and revision:** W3C Activity Vocabulary, W3C Recommendation,
  23 May 2017. Pin the dated Recommendation identity
  `REC-activitystreams-vocabulary-20170523`, not a moving "latest" label.
- **Locator:** use the dated Recommendation at
  `https://www.w3.org/TR/2017/REC-activitystreams-vocabulary-20170523/`.
  The ActivityStreams 2.0 Core Recommendation may be retained as a supporting
  citation, but the Vocabulary Recommendation is the term authority.
- **Portable scheme coordinate:** use
  `scheme_id: w3c-activitystreams-activity-types`,
  `authority: World Wide Web Consortium`, and
  `revision: REC-activitystreams-vocabulary-20170523`.
- **Semantic level:** the extended Activity types classify activities that
  may be past, present, or future. `Application` and `Service` are Actor/Object
  types capable of performing activities; they are not Activity types and are
  not behavior classifications.
- **Adoption decision:** **directly adopted** for the normative Activity type
  IRIs only. Preserve the full
  `https://www.w3.org/ns/activitystreams#<Type>` IRI as `concept_id`.
  `Application` and `Service` may support source-scope or eligibility
  rationale, but must not be placed in the behavior-term snapshot or converted
  into RAES participant subtypes.
- **Digest strategy:** SHA-256 the retrieved bytes of the dated normative
  representation used to extract the allowlisted Activity types and record
  that prefixed digest with the exact locator and retrieval date. The checked-in
  source record is the normal offline authority; remote comparison is an
  explicit maintenance check only.
- **Citation and license:** retain the dated Recommendation, Recommendation
  status, original W3C attribution, W3C document-use/license locator, and
  applicable copyright notice. If copied definitions are published, include
  the required notice in `THIRD_PARTY_NOTICES.md`; identifiers and locally
  authored scope notes are preferable to copied prose.

ActivityStreams is deliberately broad and social-Web-oriented. A positive
binding should normally use `related-to` plus `annotates`, with explicit
approximation/loss and limitations. A stronger relationship requires its own
review basis. It never proves that a RAES action occurred or that an
ActivityStreams actor exists.

### FIPA Communicative Act Library

- **Authority and revision:** Foundation for Intelligent Physical Agents,
  FIPA Communicative Act Library Specification, document `SC00037J`, Standard
  status dated 2002-12-03.
- **Locator:** use
  `https://www.fipa.org/specs/fipa00037/SC00037J.html`; retain the FIPA
  Communicative Act repository page as a supporting citation.
- **Portable scheme coordinate:** use
  `scheme_id: fipa-communicative-act-library`,
  `authority: Foundation for Intelligent Physical Agents`, and
  `revision: SC00037J-2002-12-03`.
- **Semantic level:** the 22 approved names identify communicative acts in
  FIPA ACL, with normative feasibility-precondition and rational-effect
  semantics. They classify inter-agent communication, not arbitrary service
  behavior, action execution, workflow order, or protocol conformance.
- **Adoption decision:** **usable only as an external annotation** of a
  communication-oriented behavior specification. Preserve exact lower-case
  FIPA symbols such as `inform`, `request`, `cfp`, and `not-understood` as
  `concept_id`; do not translate labels into locally invented synonyms.
- **Digest strategy:** retain the required HTML locator, but SHA-256 the exact
  official `SC00037J.pdf` representation used to pin the specification. The
  HTML response contains dynamically rewritten email-protection markup and is
  not byte-stable; maintenance verification therefore checks the stable PDF
  bytes and separately cross-checks the ordered act identifiers against the
  HTML. Store the exact document number, status date, both locators, prefixed
  digest, and retrieval date. Admission remains offline and never discovers a
  newer FIPA document.
- **Citation and license:** retain the FIPA copyright and specification notice.
  The source expressly warns that it grants no permission for third-party
  intellectual property. Publish identifiers and locally authored scope notes,
  not copied formal models, examples, or normative descriptions, unless
  publication rights have been separately confirmed.

A binding does not claim FIPA ACL compliance. It does not import FIPA mental
state, message transport, content language, interaction protocol, feasibility
precondition, or rational-effect machinery into RAES.

### W3C PROV-O

- **Authority and revision:** W3C PROV-O Recommendation, 30 April 2013,
  `REC-prov-o-20130430`.
- **Locator:** use the dated Recommendation
  `http://www.w3.org/TR/2013/REC-prov-o-20130430/` and, if machine terms are
  ever needed, its explicitly linked OWL encoding.
- **Semantic level:** `prov:Activity` is a time-bounded occurrence involving
  entities; `prov:Agent` bears responsibility; `prov:SoftwareAgent` is running
  software. These are provenance classes and responsibility relations, not a
  vocabulary of autonomous behaviors.
- **Adoption decision:** **not semantically suitable** for ACT-611
  behavior-specification classification. Do not bind `prov:Activity`,
  `prov:Agent`, or `prov:SoftwareAgent` to a behavior specification merely
  because their English names overlap RAES concepts.
- **Digest strategy:** no ACT-611 snapshot is justified. A future provenance
  integration must pin the dated Recommendation or exact OWL bytes with
  SHA-256 and target an owning realized, observed, evidence, or provenance
  subject kind rather than silently reuse this feature's behavior target.
- **Citation and license:** retain the dated W3C Recommendation, normative
  version/status, W3C document-use rules, and attribution if future work copies
  material.

PROV-O remains useful prior art for keeping planned behavior, realized
activity, responsible agent, evidence, and provenance distinct.

### IEEE 1872.2 Autonomous Robotics Ontology

- **Authority and revision:** IEEE 1872.2-2021, *IEEE Standard for Autonomous
  Robotics (AuR) Ontology*. IEEE records Board approval on 2021-09-23 and
  publication on 2022-05-12.
- **Locators:** the authoritative IEEE standards page is
  `https://standards.ieee.org/ieee/1872.2/7094/`. IEEE links a separate public
  AuR OWL project at `https://opensource.ieee.org/aur/owl`.
- **Semantic level:** the standard extends the robotics and automation
  ontology with concepts, definitions, and axioms for autonomous-robot system
  knowledge and architectures. It is not a general autonomous-service or
  communicative-act vocabulary.
- **Adoption decision:** **usable only as an external annotation** for
  robot-specific subjects after exact source/version and semantic-level review;
  it is not an initial ACT-611 scheme and must not become a RAES robot,
  service, agent, task, goal, or behavior ontology.
- **Digest strategy:** the standard text and open-source ontology must not be
  conflated. The standard text is purchase/subscription access. The linked
  source project is BSD-3-Clause with an IEEE CLA, but its indexed project page
  exposes no release tag. Any future source record must pin an exact commit,
  hash the precise OWL files, record their license, and separately evidence
  correspondence to IEEE 1872.2-2021. `main`, a project title, or the standard
  number alone is not a digest-stable snapshot.
- **Citation and license:** do not copy the purchased standard text into the
  repository. BSD-3-Clause source material may be used only with its required
  notice, and only after provenance to the selected commit and published
  standard has been established.

## Exact Subject And Assertion Boundary

Positive ACT-611 fixtures must target the coordinate emitted by
`external_concept_subjects()` for an actual behavior declaration:

- `subject_kind` is the current declaration-index kind
  `behavior_specifications`;
- `owning_contract_id` is `sdl-authoring-input-v1` for normalized/expanded SDL;
- `lifecycle_phase` is explicit, initially `normalized-authoring`;
- `canonical_ref` is exactly `behavior_specifications.<qualified-name>`; and
- `artifact_digest` is the owning SDL artifact's
  `canonical_sdl_digest()` value.

Do not substitute the behavior spec's `spec_id`, its map key alone, a
participant ref, a prose label, JSON Pointer, array position, alias, or the
compiled `participant.behavior-specification.*` address. The external subject
adapter already projects every canonical declaration; ACT-611 must not add a
behavior-only index or resolver.

The fixture's behavior specification should use existing participant refs,
action contracts, observation boundaries, outcome rules, authority/scope refs,
`behavior_mode`, realization refs, and evidence refs as needed to establish
native meaning. The external assertion only annotates or aligns that complete
native aggregate. `behavior_mode: autonomous` is still a governed RAES mode;
neither an ActivityStreams Actor type nor a FIPA term proves autonomy.

Relationship, semantic effect, motivation, perspective, provenance,
supporting evidence, confidence, approximation/loss, limitations, review, and
participant eligibility retain the issue #986 contract meanings. Conservative
fixtures use `related-to` and `annotates`. `equivalent-to`, `aligns`,
`refines`, or `constrains` require independently reviewed support and may not
install new behavior or validation.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Native behavior meaning | ADR-067, `specs/formal/participant-behavior-model/README.md`, `ParticipantBehaviorSpecification`, and existing action, observation, outcome, authority/scope, mode, realization, evidence, and compiler boundaries. |
| Portable assertion shape | `ExternalConceptBindingDocumentModel` and the published `contracts/schemas/concept-authority/external-concept-bindings-v1.json`. Do not add `autonomous_behavior_refs`, a scheme discriminator, or a second binding contract. |
| Exact SDL subject | `DeclarationIndex`, `build_declaration_index()`, `external_concept_subjects()`, `canonical_sdl_digest()`, and lifecycle-specific owning contract ids. |
| Neutral snapshot and resolution | `ExternalConceptSchemeSnapshotModel`, `ExternalConceptSnapshotTermModel`, scheme-specific adapter functions, `admit_external_concept_bindings()`, and `ExternalConceptResolutionOutcome`. |
| Shape and primitive types | `ContractModel(extra="forbid")`, `NonEmptyString`, `PrefixedDigestString`, RFC 3339/calendar-date types, and `validate_safe_absolute_uri()`. |
| Source records | Existing ATT&CK, ATLAS, and NIST source-contract patterns under `contracts/concept-authority/`, their source-shaped Pydantic models, offline loaders through `corpus_family_root(CONCEPT_AUTHORITY)`, and explicit remote maintenance checks. |
| Corpus distribution | `raes_contracts.corpus`, the Hatch build hook, and the existing packaged `contracts/` corpus. Do not load source records through repository-relative path arithmetic in library code. |
| Schema publication | Hand-governed `contracts/schemas/`, `schema_bundle()`, `contracts/schema-publication/entries/`, publication `last_change` hashes, and generated-schema parity. |
| Conformance | `_STRUCTURAL_ONLY_VALIDATORS`, `_SEMANTIC_CONTEXT_REQUIRED_CONTRACTS`, `validate_contract_payload()`, the fixture suite, and the same public offline semantic admission function used outside tests. |
| Diagnostics | `Diagnostic`, `Severity`, stable `external-concept.*` outcomes, and `sanitized_failure_message()`. Do not add scheme-specific exception classes or echo rejected identifiers. |
| Concept governance | ADR-012, ADR-062, `specs/concept-authority/`, and `tools/check_concept_authority_governance.py`. Source snapshots are not new native concept families or controlled SDL vocabularies. |
| Third-party rights | Source-record citation/license fields and `THIRD_PARTY_NOTICES.md` when copied material requires a distributed notice. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, existing nox `contracts`/`policy`/`verify` sessions, `tools/verify_all.py`, JSON artifact checks, requirement governance, and repository policy. |

Source-specific record schemas and extraction adapters are allowed because
upstream authorities have different shapes. They are inputs to one neutral
snapshot model, not alternative author-facing contracts. Extract common source
verification mechanics only if reuse is real; do not clone an entire existing
ATT&CK/NIST checker and do not force unrelated upstream formats into a
universal source ontology.

## Cross-Cutting Layers And Security Boundary

The intended design passes these layers:

1. **SDL ingress and native semantic validation.** The target scenario passes
   the existing safe YAML parser, `SDLModel(extra="forbid")`, key and variable
   rules, `ParticipantBehaviorSpecification` validators, named-reference
   validation, controlled behavior-mode validation, and participant-behavior
   analysis. ACT-611 does not weaken native validation to make a target
   resolvable.
2. **Source-record shape and provenance.** Each checked-in source record passes
   a closed source-specific `ContractModel`, its published JSON Schema, exact
   authority/revision/locator/digest/citation/license checks, JSON artifact
   validation, and optional allowlisted remote maintenance verification.
3. **Binding structural admission.** The unchanged binding model and normative
   schema reject extra fields, unsafe or unpinned locators, invalid digests,
   incomplete provenance, invalid effect/review/loss combinations, and
   duplicate assertion identities.
4. **Exact subject resolution.** `DeclarationIndex` and
   `external_concept_subjects()` supply collision-checked, phase-correct
   declarations with the owning canonical digest. Resolution requires one
   exact behavior-specification candidate.
5. **Scheme adaptation and contextual admission.** Each source adapter emits
   the same neutral snapshot shape and preserves concept candidates as a list.
   The same resolver produces deterministic `resolved-current`, `unavailable`,
   `stale`, `ambiguous`, `superseded`, `unknown-concept`, and
   `subject-not-found` outcomes for both schemes.
6. **Conformance and error envelopes.** Structural validation remains
   registered in the canonical conformance registry; semantic context remains
   explicit. Public diagnostics use stable bounded codes and sanitized
   messages without Pydantic input echo, source bodies, raw exceptions, or
   attacker-controlled concept ids.
7. **Authentication and information flow.** The standalone artifacts add no
   auth surface. Assertion authority is provenance, not authenticated
   identity. Participant availability remains `eligibility-only`; actual
   exposure or delivery must pass existing participant identity, audience,
   authorization, redaction, crossing, and disclosure gates.
8. **Secrets, configuration, OS, and network.** Source locators and concept ids
   are inert data. Normal parse, load, adapt, admit, replay, inspect, and test
   paths perform no live lookup, environment binding, plugin discovery,
   subprocess execution, shell interpolation, filesystem search, host-path
   access, or command dispatch. No source value enters process argv. The
   artifacts contain no credentials, tokens, secret refs, or environment
   variable names.
9. **Persistence and observability.** Use versioned checked-in contract
   artifacts and exact id/version/digest references. Safe logs may record
   binding id, scheme id/revision, subject kind/ref, digest, counts, and
   resolution outcome. Do not persist source bodies or rejected values in
   generic metadata, runtime snapshots, audit details, or logs.

No controller, service, API route, store, or OS integration is justified. If a
later API accepts these artifacts, it must reuse
`ControlPlaneSecurityConfig.strict_defaults()`, verified identities,
audience/target and role checks, request-size limits, idempotency/fingerprints
for mutations, audit records, bounded `HTTPException` details, response
models, and the redacted internal-error handler.

## Whole-Repository Surfaces In Scope

- `docs/decisions/`, ADR-067, and the participant-behavior and concept-authority
  specifications;
- source records, normative schemas, fixtures, source provenance, and schema
  publication entries under `contracts/`;
- contract models/exports/schema bundle, corpus loaders, neutral snapshot
  adapters/resolver, SDL subject adapter, and conformance registries under
  `implementations/python/packages/`;
- source-integrity, exact-subject, schema-parity, resolver-outcome,
  conformance-path, packaging, and leakage tests under
  `implementations/python/tests/`;
- existing source verification, JSON artifact, generated schema, schema
  publication, concept governance, repository policy, and requirement
  governance tools; and
- `THIRD_PARTY_NOTICES.md` only when the published source material triggers a
  notice obligation.

No example-library, compiler, runtime snapshot, backend manifest, control-plane,
environment, deployment, or persistence change is required merely to publish
the two external schemes.

## Extensibility Seam

The seam is the existing neutral snapshot adapter:

- a source-specific record pins upstream authority and preserves source terms;
- an adapter projects it to `ExternalConceptSchemeSnapshotModel` without
  deduplication or semantic rewriting; and
- a governed consumer decides whether a successfully resolved assertion
  matters to an already-authorized operation.

A third scheme should add only a source record/model/schema, loader, adapter,
source verification, and fixtures. It must not edit
`external-concept-bindings/v1`, branch that contract or resolver on
`scheme_id`, add a global registry, or change offline outcomes. A future RAES
subject kind belongs in the existing subject-rule table and owning resolver,
not in a scheme adapter.

## Gotchas And Anti-Patterns

- Do not follow the pre-#986 offensive/defensive sibling-field pattern for
  ACT-611. There is no `autonomous_behavior_refs` or autonomous controlled SDL
  vocabulary.
- Do not treat ActivityStreams `Application` or `Service`, PROV-O
  `SoftwareAgent`, IEEE robot/system classes, or the word "agent" as a RAES
  participant subtype, implementation kind, or proof of independent agency.
- Do not treat ActivityStreams activities as executed actions, FIPA acts as
  messages that were sent, PROV activities as behavior definitions, or IEEE
  ontology classes as runtime capabilities.
- Do not bind participant names, roles, prose labels, action names, task ids,
  goals, aliases, compiled addresses, JSON Pointers, or unqualified strings.
- Do not use source locators with fragments as a second concept-id channel.
  ActivityStreams concept IRIs belong in `concept_id`; the dated document
  belongs in `source_locator`.
- Do not case-fold, slug, translate, merge, or deduplicate upstream concept ids.
  Preserve candidate multiplicity so ambiguity remains observable.
- Do not select "latest", follow redirects to a moving revision, rewrite
  superseded terms, accept digest mismatch, or fetch on an unavailable result.
- Do not let an assertion create action contracts, observation boundaries,
  outcomes, authority/scope, realization, evidence, information-flow policy,
  participant eligibility beyond the contract's intent-only posture, or
  conformance.
- Do not copy FIPA formal semantics or purchased IEEE text without confirmed
  rights, and do not omit W3C/BSD notices when copied material requires them.
- Do not create a second schema authority, neutral snapshot type, resolver,
  validation pass, conformance runner, exception hierarchy, logger, cache,
  database, audit store, source registry, plugin, or CI workflow.
- Digest-pinned fixture artifacts are coupled to their subject SDL. Editing a
  shared context file invalidates every binding over it; use a focused behavior
  context or deliberately update all affected digests.

## Non-Goals And Implementation Boundary

ACT-611 does not:

- define a universal ontology for agents, services, robots, tasks, actions,
  goals, capabilities, autonomy, or multi-agent interaction;
- add SDL syntax, participant types, behavior modes, controlled behavior
  fields, runtime records, backend features, APIs, stores, or deployment
  configuration;
- replace action contracts, observations, outcomes, authority/scope,
  realization envelopes, evidence, provenance, information-flow control, or
  conformance;
- claim ActivityStreams, FIPA, PROV-O, or IEEE protocol/ontology conformance;
- require or permit live network resolution during normal operation;
- import PROV-O or IEEE 1872.2 as initial behavior schemes; or
- make an external assertion true, executable, authorized, disclosed,
  realized, observed, reviewed, or evidenced merely because it parses.

## Primary References

- [W3C Activity Vocabulary Recommendation](https://www.w3.org/TR/activitystreams-vocabulary/)
- [W3C ActivityStreams 2.0 Core Recommendation](https://www.w3.org/TR/activitystreams-core/)
- [FIPA Communicative Act Library Specification SC00037J](https://www.fipa.org/specs/fipa00037/SC00037J.html)
- [W3C PROV-O Recommendation](http://www.w3.org/TR/2013/REC-prov-o-20130430/)
- [IEEE 1872.2-2021 standard page](https://standards.ieee.org/ieee/1872.2/7094/)
- [IEEE AuR OWL open-source project](https://opensource.ieee.org/aur/owl)
