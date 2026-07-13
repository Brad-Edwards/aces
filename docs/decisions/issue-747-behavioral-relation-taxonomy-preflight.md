# Issue 747 Behavioral-Relation Taxonomy Preflight

Date: 2026-07-13

Issue: #747.

Requirement: none. The issue title, body, and acceptance criteria are the
authoritative contract.

This note fixes the architecture guardrails for the behavioral-relation
taxonomy and conflation audit. It does not publish the taxonomy, change a
schema or report, classify every repository statement, add a policy gate, or
claim a new proof. A dedicated ADR is required when the new shared concept
family is registered: ADR-012/062 governance deliberately rejects a concept
family with no owning ADR. Existing ADRs establish the carrier boundaries but
none currently owns the cross-repository behavioral-relation vocabulary.

Classify the taxonomy, claim-binding constraints, and semantic coverage gate as
FM2 under `specs/formal/assurance-policy.yaml`: they constrain relations and
evidence across existing graphs and carriers. A later change that adds or
changes executable runtime transition semantics, an abstract state-machine
model, or model-checking behavior is FM3 and needs its own assurance artifacts;
the taxonomy must not smuggle that work into an FM2 catalog change.

## Decision Boundary

The taxonomy answers: **what relation or deliberately weaker predicate is a
claim about, over which carriers and observations, under which quantifiers,
and with what evidence or proof status?** It does not turn every claim into
behavioral equivalence.

Validity, profile satisfaction, finite probe success, artifact identity,
realization-envelope membership, behavioral relations, epistemic relations,
strategic relations, and statistical claims are different kinds of claim.
Some are predicates or set relations rather than transition-system relations.
The catalog must say so explicitly instead of inventing transition labels for
a non-behavioral claim.

ACES must have one machine-readable, revision-labelled claim/relation catalog
under `contracts/concept-authority/`, backed by one formal specification under
`specs/formal/behavioral-relations/`. Register `behavioral-relations` as a
concept family through the existing concept-authority governance. Reader prose,
reports, profiles, studies, tests, and policy checks reference stable relation
ids from that catalog; they must not keep private copies of the relation list.
The formal prose may explain the mathematics, but its tables and the catalog
must be generated from or mechanically checked against one another.

Do not put this authority in backend profiles, scientific-completeness
profiles, semantic-invariant profiles, validation-strength profiles,
realization envelopes, or participant-runtime DTOs. Those are consumers with
different owners. Do not create a generic claim graph: when ADR-072's
validation-basis disclosure becomes executable, relation reference and
evidence boundary compose with that disclosure rather than replacing it.

## Canonical Relation Record

Every catalog entry needs stable identity and enough structure to prevent a
name from carrying several meanings:

- catalog revision, stable relation id, display name, and class
  (`predicate`, `set-relation`, `behavioral`, `epistemic`, `strategic`, or
  `empirical`);
- left and right carrier/state spaces and, where applicable, initial states;
- action/transition labels, transition relation, and the declared partition
  between observable, hidden, and stuttering actions, or an explicit
  not-applicable rationale;
- observation/information-state projection, including its subject/audience,
  policy revision, redaction scope, and treatment of order and simultaneity;
- direction, quantification over states, traces, schedulers, strategies,
  environments, and observations, plus existential/universal choices;
- explicit treatment of nondeterminism, concurrency, probability, time, and
  partial order, each recorded as supported, parameterized, abstracted, or
  outside the relation's scope;
- the property legitimately preserved and the proof obligation that would
  establish it;
- separately, the bounded evidence that current ACES tooling can produce;
- explicit non-claims and incompatible claim surfaces;
- assurance status with evidence references, distinguishing `defined`,
  `implemented`, `tested`, `model-checked`, `proved`,
  `deliberately-unproved`, and `future`; and
- references into a revision-pinned primary-source bibliography.

Do not compress those assurance states into one maturity number. A relation
can be mathematically defined but not implemented, or tested on finite cases
without being proved. A proof status attaches to a named proposition, model
revision, assumptions, and proof artifact; it never attaches to a relation
name in the abstract.

The catalog must distinguish at least structural validity, semantic validity,
capability declaration/profile satisfaction, bounded fixture/probe success,
canonical artifact or digest identity, realization-envelope membership and
subsumption, trace inclusion, trace equivalence, forward simulation, backward
simulation/data refinement, strong bisimulation, weak/observational
bisimulation, participant-relative observation equivalence, epistemic
indistinguishability, alternating/strategic equivalence, probabilistic
variants, statistical similarity/equivalence, and empirical adequacy. Digest
identity and realization subsumption belong in the catalog as explicit
non-behavioral controls because they are common sources of overclaim.

The bibliography is part of this same revisioned authority. Use stable source
ids pinned to an exact paper version, proceedings/book edition, DOI, ISBN, or
equivalent immutable publication identity. Each relation cites source ids.
Do not create a second bibliography registry or rely on floating web pages.
Primary sources must cover Park/Milner bisimulation, the linear-time versus
branching-time spectrum, refinement/simulation, weak/observational
equivalence, epistemic models, and alternating/game-based equivalences.

## Relation Decisions By Claim Surface

| Surface | Relation ACES may name now | Evidence/status boundary | Prohibited promotion |
| --- | --- | --- | --- |
| SDL to instantiated or canonical artifact | A deterministic phase function plus phase-specific invariant preservation on admitted inputs. Canonical serialization/digest equality is artifact identity only. | Existing unit, fixture, round-trip, canonicalization, and property tests are finite/tested evidence. Universal preservation remains deliberately unproved unless a proposition and proof artifact are supplied. | Do not call phase success data refinement, simulation, trace equivalence, or bisimulation. |
| Abstract ACES runtime to a backend realization | The intended universal relation is one-way projected trace inclusion/soundness, parameterized by an explicit abstraction/projection: `Proj(Traces_backend) subseteq Traces_abstract`. | Current target conformance supplies bounded fixture/probe evidence only. Forward simulation may later discharge trace inclusion, but is not established by a successful run. | Do not infer backward simulation, completeness, trace equivalence, or bisimulation from provisioning, snapshot, episode, witness, or negative-probe success. |
| Backend to backend | Finite invariant agreement, matched named probes, or a separately defined statistical study relation over stated metrics/populations. | Existing cross-backend corpus evidence is a bounded comparison with explicit non-claims. | A shared result, digest, compiled address set, terminal record, or finite trace is not universal same behavior. |
| Participant-visible behavior | Participant-relative projected-history equivalence/indistinguishability parameterized by participant, observation-boundary policy and revision, redaction, visible ordering/simultaneity, and disclosed stochastic context. | Reuse the participant-runtime projection and `ParticipantObservationBoundary`; evidence can establish equality of selected projected histories. | Never compare global state as participant-visible state or infer future behavioral/strategic equivalence from one equal observation history. |
| Multi-agent interaction | Current ACES may claim structural validity and finite trace/capability coverage for recorded joint action, chance, simultaneous/parallel activity, and mean-field surfaces. | Strong/weak, epistemic, probabilistic, alternating, and strategic relations can be defined in the taxonomy but remain future/unproved unless their complete model and quantifiers exist. | Do not call two systems strategically equivalent without game states, players, legal joint actions, observation partitions, strategy class, coalition quantifiers, chance kernel, scheduler/fairness, and winning objective. |
| Independent adequacy study | A bounded empirical or statistical relation with named population, sampling frame, metric/estimand, equivalence or similarity criterion, uncertainty, and limitations. | Reuse experiment task/run/study/evidence/derived-measure and falsification-status contracts. Evidence classification references the catalog relation id. | Statistical equivalence/non-inferiority is not behavioral equivalence; repeated observations cannot be promoted to a universal proof. |

The abstract-runtime row does not retroactively turn the existing realization
envelope into behavioral refinement. Envelope membership, subsumption,
witnesses, and negative probes are set-theoretic realization-support relations.
The participant row also does not create a new projection: the formal
participant runtime already defines `O_(p, projection, t)` and projected
history indistinguishability. The taxonomy names and constrains that seam.

At present ACES should formalize the claim distinctions above, participant
projection equivalence, and the intended projected-trace-inclusion obligation.
Full trace equivalence, forward/backward simulation proofs, data refinement,
strong/weak bisimulation proofs, timed or partial-order bisimulation,
probabilistic bisimulation, and alternating/strategic equivalence are future
work. They are inappropriate on current conformance, completeness, replay,
and backend-comparison surfaces unless a later artifact establishes their
models and proof obligations.

## Required Counterexamples And Examples

The normative specification must make the quantifier boundary concrete:

- A finite-probe counterexample needs two labelled transition systems that
  share the tested successful trace while one has another enabled transition
  the other cannot match. Both implementations pass the finite probe; they are
  not bisimilar. Extend the same example or add a game variant where an
  unprobed coalition has a winning choice in only one structure, showing why
  probe agreement is not strategic equivalence.
- A hidden-action example needs an abstract visible action and a backend path
  with a declared hidden `tau` step before or after it. Strong matching fails
  on the unmatched hidden step; weak matching may succeed through `tau` closure
  only under the declared hiding projection. Divergence sensitivity, stability,
  and termination treatment must be explicit, not silently assumed.

These examples explain definitions; they are not evidence that ACES backends
satisfy the relations.

## Existing Cross-Cutting Contracts To Reuse

| Concern | Canonical incumbent and boundary |
| --- | --- |
| Normative authority and packaging | ADR-009/012/019/061/062, `specs/authority/authority-boundary.yaml`, `contracts/concept-authority/`, `aces_contracts.corpus.CONCEPT_AUTHORITY`, `corpus_family_root()`, `ContractModel(extra="forbid")`, `schema_bundle()`, `contracts/schema-publication-manifest.json`, contract fixtures, and generated-corpus parity. Add one catalog/model/loader path, not a second registry. |
| Assurance and claim strength | ADR-021's `untested`/`partial`/`demonstrated`/`refuted` falsification statuses; ADR-072's validation-strength and validation-basis disclosure; `specs/formal/assurance-policy.yaml`. Relation identity, validation strength, evidence status, and proof status remain independent axes. |
| SDL lifecycle | ADR-016/078, `load_sdl_yaml`/`parse_sdl`, `SDLModel`, `SemanticValidator`, `instantiate_scenario()`, canonical snapshots and phase contracts, and `docs/explain/reference/shared-semantic-integrity.md`. The taxonomy classifies their claims and does not become another parser or semantic validator. |
| Realization and refinement language | ADR-070, `specs/formal/realization/`, `aces_contracts.realization_envelope`, and `aces_sdl.realization_envelope`. Preserve membership/subsumption/witness semantics and classify them as non-behavioral. |
| Participant observation and information flow | ADR-022/054/067, `specs/formal/participant-semantics/`, `specs/formal/participant-runtime/`, `ParticipantObservationBoundary`, `ParticipantViewRule`, projected histories, observation kernels, joint action, chance, simultaneous moves, and mean-field records. Reuse the existing projection rather than adding a global-state view or duplicate DTO. |
| Conformance | Existing `ConformanceCaseResult`, `BackendConformanceReport`, `run_fixture_suite()`, `run_target_conformance()`, CLI `_report_payload()`, backend profile loader/path confinement, `schema_bundle()`, `Diagnostic`, and committed reports under `docs/conformance/`. Enrich the existing disclosure; do not add a parallel equivalence report. |
| Scientific completeness | `contracts/profiles/scientific-completeness/`, `specs/sdl/scientific-scenario-completeness.md`, and `tools/check_scientific_scenario_completeness.py`. Every REV1 claim references the new catalog; the existing phrase coverage must not become an independent relation list. |
| Studies and empirical evidence | ADR-055/064/065/066/068/074 and existing experiment authoring, task, run, study, allocation, apparatus, evidence, traceability, derived-measure, uncertainty, missingness, multiplicity, and realized-form contracts. Issue #729 must bind relation/evidence classification here, not create a study store or claim graph. |
| Errors and observability | Existing SDL parse/validation/instantiation errors, collect-all semantic diagnostics, `Diagnostic`/`Severity`, conformance report diagnostics, `tools.policy.common.PolicyFailure`, and `SessionReporter`. No new exception hierarchy, logger, audit channel, or telemetry stack is warranted. |
| Persistence | Static taxonomy in the checked-in and packaged contract corpus; current conformance report carriers for conformance; experiment-core records for archival studies; `RuntimeSnapshot`/`ControlPlaneStore` for live state. Relation classification does not justify a database, cache, audit blob, or runtime metadata bag. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, the canonical `noxfile.py` policy/contracts/docs/verify graph, `tools/verify_all.py`, repository policy, requirement governance, schema publication, generated-schema, JSON artifact, concept-authority, assurance, semantic-coverage, and docs checks. Wire a focused checker once into this graph. |

Compatibility package `implementations/python/src/aces` remains logic-free.
Owning packages must keep dependency direction and must not import through the
`aces.*` compatibility namespace.

## Conflation Audit And Semantic Gate

The initial audit is a human semantic classification, not a search-and-replace
exercise. It covers ACES-authored normative specifications, ADRs, design and
explanatory documentation, public API/CLI text, conformance reports, backend
and scientific profiles, runtime probes, examples, tests, and academic claim
prose. Vendored or archived third-party source text is not an ACES claim and
must not be rewritten merely because it contains a keyword.

Known high-risk incumbents that require explicit classification include:

- `specs/formal/participant-runtime/README.md` currently describes an
  implementation as refining the design when concrete traces project to valid
  abstract traces. That sentence must either name projected trace inclusion
  with direction and quantification or use weaker language; it does not define
  simulation or data refinement as written.
- `_cross_backend_corpus_backend_runs.py` uses
  `behavior-history-equivalent` for a terminal participant observation. That
  needs an explicit participant projection and finite-history relation or a
  weaker recorded-observation statement.
- cross-backend digests, compiled address equality, and evidence-surface
  presence are finite invariant agreement only. Preserve the ledger's existing
  non-claim that it is not an equivalence proof.
- realization-envelope witnesses and negative probes, conformance fixtures and
  injected-adapter probes, replay-support claims, serializability, statistical
  equivalence, simulation backends, and cyber observables all use potentially
  overloaded words in legitimate domain-specific senses. The gate must
  recognize their qualifiers rather than ban the words.

The machine gate should consume relation ids from the canonical catalog and
use `tools.policy.common.PolicyFailure`, `safe_repo_path`, exception handling,
and JSON output conventions. It should detect high-risk affirmative claim
patterns and structured claim fields, then accept either:

1. a precise catalog relation reference plus subject, projection/quantifier
   where applicable, evidence boundary, assurance status, and non-claims; or
2. deliberately weaker language that states the bounded observation and says
   why no equivalence relation is established.

For prose, keep the relation reference and boundary in the same paragraph or a
stable claim block. For structured reports/profiles, use typed fields rather
than searching prose. If a reviewed audit inventory is retained, key entries
by repository path plus stable statement/anchor identity, not mutable line
numbers. Exceptions must be narrow, reasoned, path-confined, and governed by
the existing policy exception mechanism. Do not hard-code a second relation
vocabulary in the checker, reduce the audit to keyword banning, or allow a
negation token anywhere on a line to suppress an unrelated positive claim.

Conformance output in particular must say the subject/profile, exact fixtures
and probe ids, whether execution used fixtures, an injected adapter, a live
daemon, or a guest, the finite quantification, relation/evidence class,
projection if any, limitations, and explicit non-claims. The existing `passed`
boolean remains an aggregation of named cases; it is never a universal
behavioral-equivalence result. Reuse and extend `BackendConformanceReport` and
its CLI serialization rather than creating a new output envelope.

## Security And Operational Layers

This work is static authority, validation, and bounded reporting. The layers it
passes through, and those it deliberately does not, are:

1. **Repository path and data ingress:** load only fixed catalog, schema,
   profile, report, and source paths as inert data through
   `aces_contracts.corpus` and existing JSON/model loaders. Any checker-owned
   evidence or audit path passes `safe_repo_path`; reject absolute paths,
   `..`, symlink escape, duplicate identities, dynamic import/evaluation, and
   network fetches.
2. **Contract/config shape:** the catalog and any new structured relation
   reference use closed `ContractModel` shapes, generated published schemas,
   `x-aces-invariants` where JSON Schema cannot express the rule, valid/invalid
   fixtures, the schema-publication manifest/hash/change ledger, generated
   bundle parity, JSON artifact checks, and concept-authority governance. Do
   not store relation ids in free-form metadata.
3. **SDL and experiment validators:** if an audited claim is carried by SDL,
   it still passes safe YAML/source limits, duplicate-key checks,
   `SDLModel(extra="forbid")`, semantic validation, instantiation and
   post-instantiation validation. Experiment claims still pass their existing
   contract and cross-artifact validators. Relation classification observes
   those results and does not bypass or duplicate them.
4. **Backend/profile validation:** conformance still uses the closed backend
   profile id grammar, root confinement, manifest/capability checks, schema
   bundle, semantic checks, and bounded target cases. A relation reference
   cannot turn unsupported gaps or not-run probes into passes.
5. **Authentication and authorization:** no new endpoint or auth decision is in
   scope. If a later API exposes relation evaluation, it must reuse
   `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   target-bound role authorization, request-size limits, idempotency,
   fingerprints, and audit events; no taxonomy-specific weaker endpoint.
6. **Secrets and information flow:** catalogs, reports, diagnostics, logs,
   examples, and studies carry safe ids, refs, digests, counts, and bounded
   summaries only. Never copy tokens, keys, credentials, prompts, hidden truth,
   redacted participant state, raw evidence, backend object representations,
   environment dumps, or rejected payloads into a relation disclosure.
   Participant-relative claims use the existing information-flow projection.
7. **Environment and OS/process exposure:** no environment binding, daemon,
   shell evaluation, network service, or new subprocess is needed. Policy runs
   use fixed argv in the nox environment. Do not put claim prose, untrusted
   paths, evidence content, credentials, or tokens in process argv, and do not
   use `shell=True`.
8. **Error envelopes and observability:** malformed contract content fails via
   bounded Pydantic/contract diagnostics; conformance uses `Diagnostic` and
   must retain the existing sanitized load-error behavior; policy drift uses
   `PolicyFailure`; CLI JSON keeps the existing report envelope. Do not echo
   rejected documents, backend exception representations, raw values, full
   tracebacks, or hidden observations. `SessionReporter` is the workflow
   observability seam; no new logger is needed.
9. **Persistence and distribution:** the versioned catalog is checked-in
   contract authority and packaged by the existing corpus. Conformance and
   study classifications remain in their existing report/experiment carriers.
   Do not persist claims in snapshots, audit blobs, tags, caches, or a new
   service.

## Extensibility Seam

The reusable key is `(taxonomy_id, taxonomy_revision, relation_id)`. A claim
binding adds subject/left and right carrier refs, projection ref and revision,
quantifier/evidence boundary, assurance status, evidence/proof refs, and
limitations. Relation semantics change by publishing a new taxonomy revision;
adding a new relation adds a catalog entry; adding a new consumer adds a claim
binding without modifying the catalog's meaning.

Probability, time, partial order, scheduler/fairness, strategy class,
coalitions, chance kernels, simultaneous moves, mean-field aggregation, and
observation policies are explicit parameters or declared unsupported
dimensions. They are not booleans hidden in a generic `equivalent` relation.
This seam permits later probabilistic, timed, partial-order, or alternating
relations without re-editing every report schema or redefining existing ids.

## Gotchas And Anti-Patterns

Avoid:

- treating schema/semantic validity, capability declaration, profile
  satisfaction, admission, deployability, or realization support as behavior;
- turning finite fixtures, probes, snapshots, traces, outcomes, digests,
  canonical JSON, or terminal observations into a universal quantifier;
- calling a projection a refinement without direction, retrieve/abstraction
  relation, quantification, and preservation obligation;
- hiding all backend-internal work as `tau` without a governed projection, or
  omitting divergence, fairness, quiescence, failure, and termination choices;
- treating trace equality as branching equivalence, participant observation
  equality as epistemic or strategic equivalence, or global state as visible;
- treating repeated runs, deterministic seeds, replay-support provenance, or
  reproduction of one result as behavioral equivalence or reproducibility of
  every execution;
- treating a statistical equivalence margin as bisimulation or empirical
  adequacy as proof of implementation conformance;
- one overloaded `relation`, `profile`, `conformance`, `equivalent`,
  `refinement`, or `status` string with no namespace/revision;
- duplicating the participant projection, transition system, concept catalog,
  schema registry, validation-basis disclosure, evidence graph, report DTO,
  exception hierarchy, logger, persistence store, policy exception format, or
  CI workflow;
- editing generated schemas directly, loading taxonomy files by ad hoc
  repository-relative paths, or implementing logic in the compatibility
  package; and
- a regex gate that bans terms, blesses any nearby negation, scans vendored
  literature as ACES claims, or forces mathematically false boilerplate.

## Non-Goals And Implementation Boundaries

- Do not prove that any current backend implements the abstract runtime, that
  two backends are bisimilar, or that any coalition has the same strategy.
- Do not add a model checker, theorem prover, strategy engine, scheduler,
  probability engine, game solver, replay engine, or statistical analysis
  engine.
- Do not change SDL grammar, canonicalization, participant runtime behavior,
  realization-envelope semantics, backend behavior, or experiment semantics
  merely to name their claim boundaries.
- Do not make behavioral equivalence a prerequisite for structural/semantic
  validity, profile declaration, ordinary conformance, or REV1 matrix
  construction. Those surfaces must instead disclose the weaker relation they
  establish.
- Do not backfill a generic relation field into every artifact. Add a reference
  only to governed claim surfaces, and compose with ADR-072 disclosure when it
  becomes available.
- Do not certify external scientific adequacy, backend completeness,
  participant knowledge, replay reproducibility, or universal information-flow
  security. The taxonomy states definitions, evidence boundaries, status, and
  deliberate non-claims.
- Do not rewrite quoted primary-source terminology or archived third-party
  research text. Audit ACES's own use and contextualize citations.
