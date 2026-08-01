# Issue #212 — ACT-604 Dynamic Knowledge And Environment-State Preflight

Date: 2026-07-31

Issue: #212.

Requirement: ACT-604.

This note records the architecture boundary for closing ACT-604 against the
current repository. It is implementation guidance only: it does not add a
contract, change SDL, modify runtime state, claim backend support, define the
ACT-615 holdings taxonomy, or implement reconstruction.

## Finding

The current architecture satisfies ACT-604's authored-state, observation,
participant-history, derived-context, shared-state, information-flow, and
exact-cut requirements. It does not satisfy ACT-604 end to end.

`participant-observation-envelope-v1` and
`participant-decision-surface-v2` carry `information_state_ref` and related
history/reconstruction/proof refs. The formal participant-runtime authority
defines exact-cut reconstruction and guarantee obligations. No published
portable information-state record or governed reconstruction profile resolves
those refs, and the current structural validators do not enforce the
conditions attached to strong information guarantees. A clause-only
conformance profile would therefore preserve dangling references rather than
close them.

The smallest RAES-native closure is:

- one immutable, participant-relative
  `participant-information-state-record-v1` at an exact episode/state cut;
- one closed `participant-information-reconstruction-profile-v1` contract,
  whose immutable named profile corpus realizes the formal reconstruction
  registry without creating a plugin mechanism;
- one contextual join validator over those records and the existing
  occurrence-history, observation, decision-surface, projection, evidence,
  and profile authorities; and
- first-class append-only runtime carriage for the record, using the existing
  snapshot, atomic transition, persistence, retrieval, capability, and
  conformance paths.

No new ADR is warranted. Accepted ADR-022, ADR-054, ADR-083, ADR-085, and
ADR-095 already decide the world/view/history/evidence separation, runtime
guarantee model, participant decision surface, governed information crossing,
and exact-cut/memory-scope semantics. This note fixes the missing contract
binding under those authorities.

## Concept And Ownership Boundaries

| Concept | Canonical owner | ACT-604 use |
| --- | --- | --- |
| Authored initial framing | `agents.*.initial_knowledge`, `starting_accounts`, and `starting_assertions` plus existing SDL validators/compiler addresses | Source refs only; never dynamic truth or runtime evidence |
| Hidden world/backend/evaluator truth | ADR-022 participant semantics and authorized evidence | Never serialized as participant information merely because a backend can inspect it |
| Participant-visible occurrence | `participant-observation-envelope-v1`, behavior history, observation boundaries, and action-result transitions | Occurrence-preserving reconstruction input |
| Derived participant context or belief support | `participant-context-view-v1` and its governed transformations | Derived view, not a second fact store and not truth promotion |
| Shared operational state | `participant-shared-state-record-v1` and RUN-307 history/concurrency rules | A participant may know only an authorized projection or disclosure of a record |
| Participant decision cut | `participant-decision-surface-v2` sequence/causal cut and ADR-095 memory scope | Reused exactly; no second cut vocabulary |
| Crossing and audience policy | ADR-085, SEM-230, RUN-319 crossing policy/evidence, and API-408 retrieval | Governs participant-facing release and records it before return |
| Archival evidence and provenance | Existing evidence refs, provenance refs, markings, redaction, and audit records | Supports claims without becoming participant-visible state |
| Operational holdings kinds and lifecycle | ACT-615 | Typed refs only; ACT-604 does not define credentials, sessions, footholds, privileges, alerts, workload, assets, or liabilities |

An information-state record is a versioned claim about what one participant's
portable information state is at one exact cut under one declared projection,
memory scope, and guarantee. It is not a mutable knowledge map, a ledger of
free-form facts, a hidden-world snapshot, or an agent's private cognitive
implementation.

The record may bind a canonical state digest and an authorized payload ref,
but it must not inline an untyped fact bag. Its sources are typed refs to the
existing carriers. Source classification follows the resolved target contract
and governed relation, not an untrusted `source_kind` label. Repeated,
contradictory, deceptive, redacted, superseded, or revoked occurrences remain
distinct in history; a final-value map cannot replace them.

## Contract Guardrails

The information-state record must reuse `ParticipantRuntimeBaseEnvelopeModel`
and the existing participant address, episode identity, evidence, provenance,
marking, authorization, visibility, redaction, and schema-version conventions.
Its semantic coordinates must include:

- `information_state_ref` and a canonical digest or content-addressed payload
  ref;
- participant and episode identity;
- the existing sequence-cut or causal-cut shape, without a wire-incompatible
  copy;
- participant memory scope and reset authority where cross-episode history is
  in scope;
- occurrence-history/source refs and the applicable projection, visibility,
  redaction, and policy revisions;
- the existing `information_guarantee` vocabulary;
- reconstruction profile identity, algorithm identity/version, proof/evidence
  refs, and disclosed loss or limitations as applicable; and
- predecessor/supersession identity sufficient for append-only history without
  implying that persistence order is semantic delivery or causal order.

The reconstruction profile contract is a static profile authority, not a
runtime envelope. Follow the existing random-stream profile pattern: a
published schema plus immutable named JSON profiles loaded through the
contract-corpus resolver. Each profile is closed and versioned, and binds the
formal registry key `(algorithm_id, algorithm_version, schema_version,
projection_version)`, determinism basis, accepted input/order semantics,
fixture format, proof-artifact format, and normative artifact ref/digest.

Profiles must not contain Python import paths, shell commands, expressions,
URLs fetched at validation time, embedded credentials, or arbitrary callables.
Selection dispatches through closed trusted code. There is no `latest`, version
range, dynamic plugin discovery, or caller-selected executable.

`history_consistent` and `perfect_recall` are strong assertions. A published
record carrying either value must resolve all required state, history,
projection, reconstruction-profile, and proof/evidence refs at exactly the
same participant, episode, cut, memory scope, and policy/revision coordinates.
The reconstructed digest must equal the record's claimed digest.
`perfect_recall` additionally requires the governed prefix/occurrence-identity
and order witness defined by ADR-054 and the formal runtime model.

An unresolved profile, missing proof, mismatched coordinate, unauditable
algorithm, collapsed occurrence history, or failed reconstruction makes a
strong record invalid. A producer may publish a weaker truthful claim instead;
a validator must never silently rewrite or accept the false strong claim.
`observation_only`, `lossy_projection`, `unknown`, and `unsupported` retain
their existing distinct meanings. The weakest generally portable positive
claim is `observation_only`; a backend that cannot materialize even the
portable record declares the capability unsupported rather than synthesizing
an empty state.

The observation-envelope structural/model validation must enforce the
field-level conditions associated with its selected guarantee. The contextual
validator then resolves refs and evaluates cross-record conditions once. Do
not duplicate the same joins in API DTOs, runtime services, and backend
adapters. A decision surface's `information_state_ref` must resolve to a record
with the same participant, episode, exact cut, projection/redaction revisions,
and memory scope. If a context view names an information state as a source, it
uses a closed source-layer value and ref; it does not copy the information-state
payload.

## Runtime, Persistence, And Retrieval Boundary

Information-state records belong in one first-class append-only
`RuntimeSnapshot` history. A list's physical order is persistence order only;
semantic order comes from the record's existing exact-cut coordinates and
visible occurrence relation. Records have stable unique refs and cannot be
deleted, rewritten, or replaced by an issue-local "current knowledge" map.

Runtime integration must remain within the canonical snapshot authority:

- `RuntimeSnapshot`, `_SNAPSHOT_UPDATE_KEYS`, `with_entries()`,
  `RuntimeSnapshotEnvelopeModel`, `_snapshot_payload()`, and
  `_snapshot_from_payload()` stay shape-compatible;
- the reserved-metadata-key checks include the first-class history so metadata
  cannot smuggle a parallel state stack;
- `participant_result_contracts.py` performs the aggregate snapshot and
  transition validation;
- `ControlPlaneStore.commit_participant_transition()` persists the state,
  expected predecessor head, transition/evidence record, and audit outcome
  atomically in both in-memory and local stores; and
- local-store restart arbitration counts the information-state history in
  `_participant_transition_count()`. Omitting it can cause the loader to choose
  a stale legacy snapshot after restart even when the new history committed.

Do not append an information-state record through a separate repository call
after a decision, observation, or crossing has already committed. That creates
a crash window and an exact-cut claim with no atomic source state. Extend the
existing expected-head seam and commit protocol instead of adding another
lock, journal, repository, or transaction abstraction.

Administrative/control-plane carriage uses the existing snapshot envelope and
`/snapshot` path. Participant-facing use should normally remain indirect:
decision surfaces and API-408 context/history/status views carry governed refs
or authorized derived projections. A new raw ACT-604 endpoint is not required
to satisfy the requirement.

If direct participant-facing record retrieval is later justified, it is a new
closed RUN-319 carrier kind passed through
`ParticipantCrossingPolicyResolver`, audience-subject binding, markings,
projection/redaction, `serialize_participant_view()`, and commit-before-return.
It must fail closed when no governed resolver is configured; the legacy API-408
fallback is not an authorization path for a new sensitive carrier.

## Cross-Cutting Layers That Must Be Reused

### Contract and validation authority

- ADR-009/019 and `contracts/README.md`: hand-governed published schemas remain
  normative. Pydantic models must reproduce them through `schema_bundle()`;
  generated output is not a substitute authority.
- ADR-061 and `contracts/schema-publication/entries/`: schema publication,
  hashes, compatibility classification, and `last_change` are updated through
  the existing manifest path.
- `raes_contracts` strict models: closed enums, forbidden extra fields,
  portable refs, exact shapes, and model/schema parity. Do not add an API-only
  DTO with different semantics.
- `raes_conformance.conformance.validators._MODEL_VALIDATORS`: one structural
  validator registration per new contract, plus a contextual validator for the
  multi-record join. Use `sanitized_failure_message()` for untrusted validation
  failures.
- Existing valid/invalid contract fixtures, backend conformance targets, and
  invariant oracles: positive publication and each negative guarantee/ref/cut/
  audience path exercise production validators, not a test-only helper.

`implementations/python/tests/sem230_information_flow_model.py` is a bounded
test model. It is not a production contract, reconstruction engine, or state
store and must not be promoted into one.

### SDL and semantic compilation

The existing `raes.agents` fields and the content-objective/proposition
validators own authored starting state. `SDLModel`, `SemanticValidator`, the
processor compiler, planning diagnostics, and canonical address resolution
remain the only SDL validation/compilation path. ACT-604 does not need new SDL
syntax. If a future authored binding is genuinely required, it must compile to
the same typed runtime refs and pass the existing parse, shape, semantic,
compile, and diagnostic layers; no second parser or validator is permitted.

### Capability and backend honesty

Add any reconstruction-support term to the existing participant-runtime
behavior-feature vocabulary and map it through
`PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`,
`BACKEND_SUPPORTED_CONTRACT_IDS`, manifest validation, feature admission, and
backend conformance. Reuse the existing `exact`, `bounded`, `disclosed_weak`,
and `unsupported` support scale.

Capability strength and a record's `information_guarantee` are independent:
backend capability says what the implementation can support; the per-record
guarantee says what this state instance evidences. Exact backend support does
not promote a record to perfect recall. Do not upgrade the reference backend's
manifest until its production path and evidence actually satisfy the new
contract.

### Authentication, policy, and egress

`ControlPlaneSecurityConfig.strict_defaults()` remains the default-deny
configuration. `_ControlPlaneApiAuth.read_identity()` owns bearer or trusted-
proxy authentication and backend/operator/auditor role checks.
`ParticipantAudienceSubjectBinding` separately binds the semantic audience;
an operator role is not participant identity.

Participant-sensitive retrieval must resolve authentication, target role,
participant/audience binding, crossing policy/revision, state cut, markings,
visibility, redaction, and transformation independently. No one successful
gate widens another. Resolve the governed audience before disclosing whether a
participant, episode, or information-state ref exists.

The existing request-body/content-length middleware enforces
`max_request_bytes`, but GET path, query, and header values are not covered by
that body limit. ACT-604 should add no new caller-controlled input on the
existing retrieval path. Any later direct route must apply the shared bounded-
value validation to participant, episode, audience, ref, and idempotency values
before lookup, audit, fingerprinting, or persistence.

### Secrets, host exposure, errors, and observability

ACT-604 needs no environment variable, secret-file lookup, CLI, subprocess,
socket, daemon, or host-service change. Tokens, credentials, private prompts,
private model memory, hidden truth, and raw evidence must never enter process
arguments, environment values, filenames, refs, digests, exception text,
stdout/stderr, audit events, or logs. State carries authorized refs/digests,
markings, redaction, and provenance; operational credentials remain behind
their existing secret/auth boundary.

Reuse the existing error boundary: model/semantic failures become closed
`Diagnostic` values or sanitized conformance failures; expected access/conflict
failures use the existing `PermissionError`/`ValueError` mapping and fixed safe
HTTP details; unexpected exceptions return only
`{"detail":"internal server error"}` while audit records the exception type,
not attacker-controlled text. Do not create a participant-information-state
exception hierarchy or return Pydantic inputs/errors verbatim.

Observability is the existing `Diagnostic`, `OperationReceipt`/status,
`AuditEvent`, crossing evidence, evidence refs, provenance refs, and append-only
history. Do not add a parallel logger or emit state payloads for debugging.

### Repository workflow

`.ground-control.yaml`, `.gc/plan-rules.md`, the canonical repository-policy
and requirement-governance checks, schema publication tooling, contract
fixtures, and the `verify` session own delivery. The implementation branch must
bind `RAES_REQUIREMENT_UID=ACT-604` because `212-dynamic-knowledge-state` does
not contain the requirement UID. No issue-local validation script, generated
schema shortcut, manual version edit, or manual changelog entry is needed.

## Extensibility Seam

The stable seam is the record/profile key, not a generic knowledge abstraction:

`(participant, episode, exact_state_cut, projection_revision,
redaction_revision, memory_scope, reconstruction_profile, guarantee)`.

The reconstruction profile resolves the closed algorithm tuple
`(algorithm_id, algorithm_version, schema_version, projection_version)`.
Future algorithms, partial-order strategies, proof formats, or bounded
realizations add immutable profiles and closed trusted dispatch entries without
editing the information-state record shape or weakening historical meaning.
Future source carriers add a typed contract/ref relation and contextual join;
they do not add arbitrary dictionaries or executable registry entries.

ACT-615 holdings fit this seam as typed source refs after their owner publishes
the kinds and lifecycle. A holding becomes participant information only through
an authorized observation, disclosure, or governed reconstruction at a cut.
This allows new holding kinds without reopening ACT-604 or confusing possession
with knowledge.

## Gotchas And Anti-Patterns

- Do not equate world state, centralized-training state, backend debug state,
  evaluator truth, participant view, belief/inference, shared state, holdings,
  and archival evidence.
- Do not infer participant knowledge from shared-state read permission. A
  visible/delivered occurrence at the relevant cut is required.
- Do not collapse repeated or contradictory occurrences by value, timestamp,
  or digest. Occurrence identity and declared order are semantic.
- Do not use wall-clock timestamps, list position, database revision, or
  last-writer-wins as a portable causal/decision cut.
- Do not silently promote initial knowledge, disclosed assertions, inferred
  beliefs, deceptive observations, stale context, or holdings to truth.
- Do not erase history on concealment, revocation, supersession, reset, or
  redaction. Append the governed transition and change future visibility.
- Do not turn the reconstruction profile corpus into a plugin system, planner,
  reasoner, knowledge graph, or dynamic code-loading surface.
- Do not duplicate exact-cut, guarantee, marking, redaction, provenance,
  capability, diagnostic, exception, snapshot, repository, locking, audit, or
  egress abstractions.
- Do not validate only the edited model or a test helper. Structural validity
  without cross-ref, exact-cut, policy, reconstruction, and persistence
  validation is insufficient.
- Do not advertise perfect recall, history consistency, replay fidelity,
  convergence, epistemic equivalence, or causal truth from schema validity or
  a successful sample reconstruction.

## Explicit Non-Goals

- A generic mutable `knowledge`, `beliefs`, `holdings`, or
  `environment_state` dictionary.
- A universal BDI state, private chain-of-thought/cognitive-state carrier,
  planner, POMDP solver, epistemic reasoner, knowledge graph, or CRDT.
- A new observation, context, shared-state, decision-cut, evidence, capability,
  authentication, storage, exception, logging, or workflow stack.
- The ACT-615 operational-holdings taxonomy or lifecycle.
- A raw participant information-state API when existing governed retrieval and
  typed refs suffice.
- Backend realization or strong semantic claims unsupported by governed
  production evidence.
