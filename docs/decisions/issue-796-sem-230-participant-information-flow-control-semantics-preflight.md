# Issue #796 — SEM-230 Participant Information-Flow And Control Semantics Preflight

Date: 2026-07-17

Issue: #796.

Requirement: SEM-230.

This note records architecture guardrails for publishing the participant-
relative information-flow and control semantics. It is implementation guidance
only: it does not define the SEM-230 formal model, accept ADR-085, revise the
behavioral-relation catalog, add policy or runtime contracts, change SDL,
implement enforcement, or establish a noninterference claim.

## Binding Authorities

- Proposed ADR-085 and
  `docs/research/participant-io-control/adoption-design.md` define the intended
  composition boundary: one policy/evidence relation over existing carriers,
  not one gateway, transport, message, lifecycle, view, store, or logger.
- Accepted ADR-022 and `specs/formal/participant-semantics/README.md` own world
  truth, participant-visible state, participant-local history, archival
  evidence, actions, observation boundaries, visibility transitions, and
  participant-relative ordering.
- Accepted ADR-054 and `specs/formal/participant-runtime/README.md` own the
  observable lifecycle, qualified visible-history projection
  `H_{tr,policy}`, delivery/order semantics, information guarantees, markings,
  redaction, shared state, concurrency, replay, and runtime nonclaims.
- Proposed ADR-083 and the SEM-219/220/226 sections of the participant
  semantics specification own authored affordances, participant-local decision
  surfaces, and exposure. SEM-230 composes with those concepts; it does not
  make their still-open runtime implementation complete.
- Accepted ADR-081, `specs/formal/behavioral-relations/README.md`,
  `contracts/concept-authority/behavioral-relations-v1.json`, and
  `BehavioralClaimBindingModel` are the only relation vocabulary and claim-
  binding authority. A participant-policy relation must land there, not in a
  local registry.
- ADR-009, ADR-019, ADR-036, ADR-059, ADR-061, and ADR-080 govern authority
  placement, package ownership, accepted-ADR evolution, published schemas, and
  revision-pinned SDL lineage. ADR-007/018 and
  `specs/formal/assurance-policy.yaml` classify this stateful/control change as
  FM3. ADR-021 governs falsification-first evidence.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and the canonical
  `verify` session own repository workflow. No issue-local verification script
  or workflow is needed.

The #794 research bundle is design evidence, not normative authority. Normative
SEM-230 meaning must be published under `specs/` and the existing concept-
authority catalog before later contract or runtime issues consume it.

## Architecture Decisions And Authority Placement

### One policy relation, not one carrier

SEM-230 defines the semantic coordinates, decision composition, labelled
transitions, projection/hiding, policy-revision rules, and claim boundary for a
participant-directed crossing. The crossing tuple in ADR-085 is a relation over
typed existing refs; it is not authorization to publish a generic payload bag
or `ParticipantMessage` DTO.

The formal policy state and crossing relation may name participant, episode,
direction, interaction kind, source, actor, controller, authority basis,
action/projection ref, observation and order point, time/order model, policy
identity/revision, markings, declassification, transformation, disposition,
backend posture, evidence, provenance, and loss. Payload ownership stays with
the existing action, observation, lifecycle, context, control, inject,
history, and evidence carriers.

Issue #796 must not publish an API-423 crossing schema or a RUN-319 policy-
decision store. Those are deliberately downstream because a contract or store
must consume settled semantics rather than define them accidentally.

### Extend the existing formal subsystems

Keep SEM-230 in the existing `participant-semantics` FM3 subsystem. A focused
sibling such as
`specs/formal/participant-semantics/information-flow-control.md`, linked from
the subsystem README, is preferable to another top-level formal-spec root or
another large append-only README section. It must reuse the existing symbols
and qualified runtime definitions rather than redefine `W`, `V`, `H`, `X`,
delivery, visible occurrence identity, markings, or order.

The same change may extend
`specs/formal/behavioral-relations/README.md` for the reader-facing relation
definition. Do not create a second information-flow relation specification,
claim-binding model, proof-status scale, or assurance registry.

The clause-to-artifact-to-assurance matrix belongs with the SEM-230 formal
authority. Its rows must distinguish formal definition, machine-readable
relation entry, executable abstract counterexample/policy check, production
enforcement status, backend realization status, and proof status. A row cannot
use issue closure, schema validity, or a passing test as a substitute for a
stronger status.

### Evolve the relation catalog honestly

`policy-noninterference` belongs in the existing
`aces-behavioral-relations` catalog and on a dedicated participant-information-
flow claim surface. The current `BehavioralRelationDefinitionModel` already
has carriers, transition signature, projection, quantification, scheduler and
environment treatment, nondeterminism, concurrency, probability, time,
partial order, proof obligation, evidence boundary, assurance, bibliography,
and nonclaims. Use those fields plus the formal specification; do not publish a
second relation schema merely to restate them.

Adding a relation changes the revisioned taxonomy. The catalog must advance
from `rev1` to a new revision such as `rev2`; silently adding a relation while
retaining `taxonomy_revision: rev1` would invalidate every revision-pinned
claim. The `behavioral-relations/v1` schema discriminator and `-v1` schema
filename describe the catalog contract shape and need not change when the
shape is unchanged.

Advancing the taxonomy has a whole-repository blast radius because
`validate_behavioral_claim_binding()` resolves bindings only against the
current catalog. All current in-repository producers and fixtures must pin the
new catalog revision together, including:

- `_bounded_conformance_claim()` in `aces_conformance.conformance`;
- the evidence-run artifact projection in `aces_operations`;
- scientific-completeness profile claim bindings;
- experiment-study fixtures and claim tests;
- concept-authority catalog fixtures; and
- relation-facing specifications and explanatory documents.

That coordinated current-revision update is not a claim that arbitrary stored
`rev1` artifacts were migrated. Preserving or dual-reading historical
serialized claim bindings requires an explicit revision archive/resolver and
belongs to issue #802 unless the supported-input contract already requires it.
Do not add a one-off `rev1` fallback inside one consumer, and do not rewrite old
evidence while pretending it was originally issued against the new revision.

ADR-081 remains the taxonomy-discipline authority and must not be silently
edited. Proposed ADR-085 can explicitly authorize the new relation/revision
before acceptance. Accepting ADR-085 must also satisfy ADR-059 pin/index rules
and record truthful FM3 artifacts in the classification/fulfillment ledgers;
ADR status alone does not satisfy SEM-230.

### Keep the label alphabet mapped to existing state owners

The SEM-230 labelled transition system needs a closed formal label table. Each
label must identify its state owner and map to existing lifecycle, visibility,
action, control, delivery, or evidence carriers where those already exist.
For example, proposal, admission, attempt, result, observation, disclosure,
concealment, and revocation already have adjacent owned concepts; SEM-230 must
not create synonyms with different meanings.

New semantic labels such as policy change, declassification, transformation,
or weakening may be defined where no incumbent exists. If a machine-readable
alphabet is needed in this issue, extend
`contracts/concept-authority/controlled-vocabularies-v1.json` and its existing
validation/fixture path. Do not add an implementation-local enum, standalone
label JSON file, or public schema field solely to make the prose look typed.
API-423 owns later wire carriage.

Observable and hidden are functions of participant, audience, policy revision,
and order point. They are never intrinsic booleans on a source label. A `tau`
mapping must name the hidden set, closure rule, stuttering treatment,
divergence treatment, and projection revision. Backend-internal work is not
automatically `tau`.

## Formal And Concept Boundaries

### Reuse the qualified information-state model

SEM-230 must build on these existing objects rather than introduce another
world/view/history vocabulary:

- `W_t`: world/backend/evaluator truth;
- `V_p,t`: the time-indexed participant view relation;
- `H_{tr,policy}(p,e,t)`: the occurrence-preserving participant-visible
  history under one trace, projection, marking/redaction policy, and order
  point;
- `X_t`: archival evidence and authorized audit state;
- existing action contracts and the ADR-083 decision-surface projection; and
- the runtime information-state/guarantee definitions only at the assurance
  strength their evidence supports.

Policy revision is state. A revision takes effect at a declared order point;
it cannot authorize an earlier crossing. Retries preserve idempotency identity
but require a fresh decision when policy, controller, authority, subject,
marking, or relevant state changed. Timestamp equality, receipt order, or
last-writer-wins is not a portable order rule.

Participant-local history is append-only knowledge evidence. Concealment,
revocation, rollback, supersession, redaction, or policy change affects future
projection/authority and may append a new visible occurrence; it does not erase
an earlier delivery or retroactively edit the participant's history.

### Keep independent gates and operations independent

The formal decision composition is deny-first. At minimum, caller
authentication, control-plane target authorization, participant/controller
authority, action applicability/admission, audience visibility, marking
authorization, declassification authority, backend support, and transformation
result validity are independent gates. Success at one gate cannot widen a
failure or unresolved fact at another.

The specification must preserve these distinctions:

- authentication/authorization binds a caller; participant authority binds the
  semantic subject/controller; admission decides whether a crossing may
  proceed now;
- projection/masking selects a view; redaction changes an already authorized
  representation; declassification changes the governed release basis;
  disclosure/delivery records a release/realization;
- withholding records non-release; concealment and revocation change future
  availability; none proves erasure of prior knowledge;
- transformation creates a new source/result identity with provenance,
  markings, rule/revision, evidence, and disclosed loss. A transformed action
  is a new proposal and receives fresh structural, semantic, and admission
  validation; and
- loss, unknown, unsupported, and weakening are not successful security
  transformations. A weaker realization removes the stronger capability or
  relation claim.

Presentation, candidate membership, eligibility, selection, approval,
admission, attempt, result, delivery, observation, and archival retention are
separate transition facts. Audit retention is an authorized evidence audience,
not participant egress.

### Define one exact baseline noninterference obligation

The baseline `policy-noninterference` definition is a participant-policy
hyperproperty, not projected-history equality and not a synonym for
bisimulation. For fixed declared participant/episode scope, model,
environment class, scheduler class, order model, and policy-revision sequence,
it quantifies over low-equivalent initial states and input histories. Equal
admitted low inputs, equal participant-policy purge results, and equal
permitted declassification schedules require equality of the sets of projected
participant-visible histories despite variations in unauthorized high inputs.

The definition must make the following explicit, with no prose defaults:

- state, trace/run, input, observation, environment, and scheduler
  quantifiers;
- the low-equivalence relation and which policy/order point determines it;
- dynamic purge treatment as policy revisions change;
- permitted declassification events, authority, release dimensions, and
  schedule equality;
- visible occurrence identity and partial/total/simultaneous order comparison;
- nondeterministic support-set semantics;
- concurrency and partial-order treatment;
- termination, progress, divergence, and wall-clock timing sensitivity; and
- probability treatment and the bound/model to which executable evidence
  applies.

The adopted baseline is termination- and progress-insensitive and excludes
wall-clock timing. Nondeterministic systems compare declared sets of projected
histories. Probabilistic claims compare measures and require a separately
governed probabilistic relation/binding; a sample set is not a probability
measure. Partial-order claims compare the declared visible order relation, not
one convenient linearization.

The catalog assurance for this obligation is definition-only and deliberately
unproved unless issue #796 actually supplies stronger governed evidence.
Finite counterexamples, leakage tests, and policy checks are bounded
falsification evidence. They do not establish universal noninterference,
trace inclusion/equivalence, simulation, refinement, strong/weak
bisimulation, epistemic indistinguishability, timing security, or backend
realization.

## Canonical Incumbents To Reuse

- **Participant semantics:** `ParticipantViewRule`,
  `ParticipantViewTransition`, `ParticipantObservationBoundary`, compiled
  `view_relation_timeline`, SEM-211 action contracts/admission, and the
  existing participant semantics analyzers, validator, compiler addresses,
  and behavior-history checks.
- **Runtime semantics:** `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`,
  `ParticipantControlMixin`, `RuntimeSnapshot`, and `ControlPlaneStore`.
  Their delivered slices are adjacent primitives, not proof that the complete
  policy path exists.
- **Views:** `ParticipantObservationEnvelopeModel`,
  `ParticipantContextViewModel`, `ParticipantHistoryViewModel`, and
  `ParticipantStatusViewModel`. The current API-408 retrieval implementation
  uses role-authorized control-plane reads and `_project_scope()`; it is not a
  participant-subject authorization or safe egress enforcement point.
- **Relations:** `BehavioralRelationCatalogModel`,
  `BehavioralRelationDefinitionModel`, `BehavioralClaimSurfaceModel`,
  `BehavioralClaimBindingModel`, `load_behavioral_relation_catalog()`, and
  `validate_behavioral_claim_binding()`.
- **Concepts and capability:** the existing concept-family and controlled-
  vocabulary catalogs, `ParticipantFeatureSupportModel`,
  `ParticipantRuntimeCapabilitiesModel`,
  `participant_runtime_capability_contract_gaps()`, and the exact/bounded/
  disclosed-weak/unsupported support scale. Capability is apparatus metadata;
  it is not semantic authority or realization proof.
- **Contracts and publication:** `ContractModel(extra="forbid")`,
  `schema_bundle()`, `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json`,
  `tools/check_generated_schemas.py`, and
  `tools/check_schema_publication.py`. No new published schema is required for
  SEM-230 when the relation catalog shape remains adequate.
- **Diagnostics, audit, and persistence:** `Diagnostic`, `Severity`,
  `OperationReceipt`, `OperationStatus`, `AuditEvent`, append-only runtime
  histories, and existing evidence/provenance refs. Do not add an IFC
  exception family, logger, audit stream, database, or metadata bag.
- **Security:** `ControlPlaneSecurityConfig.strict_defaults()`, bearer or
  verified-proxy identity, target-bound roles, request-size guards,
  idempotency keys, request fingerprints, audit events, and the redacted
  `{"detail":"internal server error"}` envelope.
- **Assurance and policy:** `test_behavioral_relations.py` counterexample/
  property style, `test_participant_semantics_invariant_oracle.py` as adjacent
  I1-I18 evidence only, `tools/check_behavioral_relation_claims.py`,
  `tools.policy.common.PolicyFailure`, the FM classification/fulfillment
  ledgers, and the canonical nox `verify` graph.
- **Lineage:** the participant section of `docs/explain/sdl/lineage.md`,
  `SDLLineageLedgerModel`, and `tools/check_sdl_lineage.py`. The prose section
  must state exact ACES mappings, delivery status, evidence, and nonclaims.
  The ledger and source audit change only if the implementation makes a new
  normative derivation or compatibility claim about an SDL subject; citing
  Goguen-Meseguer and Sabelfeld-Sands as intellectual lineage alone does not
  imply wire or semantic compatibility.

## Cross-Cutting Layers And Security Posture

Issue #796 is a semantic-authority change. Its direct execution surface is
local repository validation, not an HTTP endpoint, backend, host process, or
policy engine. The intended downstream design nevertheless crosses the layers
below, and later issues must preserve these gates rather than interpreting the
formal tuple independently.

| Layer | Canonical gate | Required posture |
| --- | --- | --- |
| Normative artifact placement | `specs/authority/authority-boundary.yaml`, ADR-009/019, `tools/check_authority_boundary.py` | Formal meaning stays under the existing participant/behavioral formal subsystems; machine-readable relation meaning stays under concept authority. Research and docs do not become alternate authority. |
| Catalog shape and references | `ContractModel`, `BehavioralRelationCatalogModel`, published `behavioral-relations-v1` schema, catalog fixture runner | Closed fields, key/id agreement, bibliography resolution, claim-surface resolution, exact taxonomy revision, explicit assurance/nonclaims. No permissive dict or duplicate schema. |
| Claim validation | `BehavioralClaimBindingModel`, `validate_behavioral_claim_binding()`, `tools/check_behavioral_relation_claims.py` | Current bindings resolve to the catalog. Extend the existing policy checker for positive noninterference assertions; do not add a separate IFC claim scanner. Definitions and explicit nonclaims remain permitted. |
| SDL source and semantic admission | `load_sdl_yaml()`, source budgets and duplicate-key-safe loading, `SDLModel(extra="forbid")`, `SemanticValidator.validate()`, `instantiate_scenario()`, and post-instantiation admission | No SEM-230 policy body or executable expression enters SDL in #796. Later authored refs remain inert, closed, resolved, bounded, and revalidated after substitution. Unknown required refs fail closed. |
| Contract/API shape | Pydantic request models, `ContractModel`, published schemas, request-size guard | Later API-423/RUN-319 payloads use typed refs and bounded closed bodies. No generic message/policy/payload map and no raw hidden payload in diagnostics. |
| Caller and target authorization | `_ControlPlaneApiAuth`, bearer/verified proxy identity, `ControlPlaneRole`, target binding | Authenticate and authorize the caller first, but separately bind participant subject/controller/authority and audience. Operator or auditor role never grants participant visibility or action authority by itself. |
| Participant policy/admission | SEM-211 admission helper, view timeline, markings, declassification and backend-support gates | Compose deny-first at the effective policy/order point. Missing or stale required state rejects or reports unsupported; capability and visibility cannot grant authority. |
| Idempotency and ordering | request fingerprint/idempotency-key handling, participant/runtime order carriers | A duplicate with the same fingerprint may reuse a result only while relevant policy/controller/state coordinates are unchanged. Timestamp or receipt order is not substituted for the declared order model. |
| Persistence and audit | `RuntimeSnapshot`, `ControlPlaneStore`, `AuditEvent`, typed evidence/provenance refs | Decisions and realizations are append-only and separately evidenced. Persist safe ids, revisions, digests, reason codes, evidence refs, and loss summaries—not credentials, hidden payloads, policy bodies, or backend objects. |
| Error envelope and observability | `Diagnostic`, bounded 4xx detail, redacted FastAPI exception handler, `PolicyFailure` for repo gates | Stable public-safe codes/refs only. Never return raw rejected input, policy text, hidden values, stdout/stderr, environment dumps, backend exceptions, or tracebacks. No new exception hierarchy or logging path. |
| Config/env binding | Existing typed manifests/configs; `.ground-control.yaml` only for workflow | SEM-230 adds no environment-variable, token, secret-loader, or CLI-policy shape. `ACES_REQUIREMENT_UID=SEM-230` is workflow context, never a semantic contract field. |
| Secret and OS exposure | Existing observed-value redaction discipline and fixed repository verification commands | #796 needs no network, daemon, privilege, shell evaluation, or secret access. Later adapters must keep tokens, credentials, raw policy/payload data, and hidden truth out of process argv, filenames, environment captures, logs, diagnostics, fixtures, and audit details. |
| Governance and documentation | ADR-059 pin gate, FM assurance policy/fulfillment, lineage checker, Sphinx `-W`, canonical `verify` | Proposed/accepted/implemented/tested/model-checked/proved/runtime-realized remain independent statuses. Documentation cannot promote one into another. |

`specs/formal/assurance-fulfillment.yaml` currently carries historical waivers
for the participant-semantics subsystem even though later participant tests
exist. Do not cite those waivers as SEM-230 evidence. Reconcile the subsystem
entry only against concrete artifacts delivered for the required FM3 kinds;
do not remove a waiver merely because a related test file exists.

## Extensibility Seam

The extension seam belongs in the formal participant-policy/relation
coordinates, not in a universal DTO or runtime service. It must be
parameterized by:

- participant, episode, audience, direction, and crossing kind;
- policy identity, revision sequence, effective order, and validity interval;
- controller/authority coordinates and subject binding;
- label alphabet, observable/hidden projection, redaction/marking, and
  declassification/transformation rules;
- sequential, total, partial, causal, simultaneous, timed, or backend-
  serialized order model;
- environment and scheduler class;
- termination, progress, divergence, timing, nondeterminism, concurrency,
  partial-order, and probability assumptions; and
- evidence boundary and independent definition/implementation/test/proof/
  runtime-realization status.

The obvious next variations are a timed claim, a probabilistic claim, a
partial-order-preserving claim, or a new governed crossing/label. Selecting one
must add or bind the relevant explicit parameters and stronger evidence; it
must not edit the baseline relation in place, assume defaults from a backend,
or require every carrier to adopt a new generic envelope.

## Assurance Guardrails

- The existing I1-I18 participant invariant oracle does not encode SEM-230 and
  must not be relabelled as noninterference evidence. A SEM-230 abstract model
  and counterexamples must remain explicitly test-local unless a later issue
  delivers production enforcement.
- Executable cases must include at least unauthorized-high variation that is
  purged, authorized declassification that changes the low history only at the
  governed order point, future policy change that cannot authorize the past,
  redaction without authorization, transformation requiring fresh admission,
  participant-relative hiding, and a finite passing case that still carries a
  universal nonclaim.
- Property checks should exercise low-equivalence/purge stability, append-only
  visible history, order sensitivity, marking/declassification intersection,
  and mutation of every assumption dimension. They remain bounded to the
  generated model and case domain.
- Extend the existing behavioral-claim policy gate so an unbound positive
  noninterference assertion fails unless it names `policy-noninterference` and
  an evidence boundary, or is an explicit definition/nonclaim. Keep the
  checker catalog-derived; do not hard-code a second relation registry.
- The catalog entry must add revision-pinned primary sources and explicit
  nonclaims. Worked examples that assume the current strong/weak-bisimulation
  example shape must not be overloaded to represent an information-flow
  hyperproperty; use a focused abstract counterexample test unless the general
  example contract is deliberately and compatibly evolved.
- A bounded model check, if supplied, records model, bound, tool/version,
  assumptions, explored state count, result/counterexample, artifact digest,
  and reproduction command. Without that evidence the assurance status stays
  deliberately unproved. A green unit/property suite is not a model check.

## Gotchas And Anti-Patterns

Avoid:

- changing the catalog contents while retaining `taxonomy_revision: rev1`, or
  bumping the revision in only one producer;
- creating `policy-noninterference` in a standalone schema, local enum,
  scientific profile, backend manifest, or test registry instead of the
  behavioral-relation catalog;
- defining observable/hidden as global event flags or treating every backend-
  internal step as `tau`;
- redefining `H` as a set of payload values and thereby collapsing repeated
  equal/redacted deliveries or losing visible partial order;
- using API-408 `_project_scope()` or a role-authorized retrieval route as
  participant audience authorization;
- treating operator authorization, participant authority, action admission,
  visibility, marking authorization, declassification, redaction, and delivery
  as one Boolean;
- treating redaction, hashing, summarization, loss, or weakening as
  declassification or as proof the source was authorized;
- allowing a transformed action to inherit admission from its source;
- applying a later policy revision, approval, controller handoff, or disclosure
  retroactively;
- equating scheduling with delivery, delivery with observation, or audit
  retention with participant disclosure;
- equating schema/catalog validity, capability declaration, finite leakage
  tests, projected-history equality, or backend probe success with universal
  noninterference, trace inclusion, equivalence, refinement, or bisimulation;
- adding a participant IFC gateway, policy engine, policy-expression language,
  database, logger, exception hierarchy, authentication stack, transport, or
  workflow branch in this semantic-authority issue;
- storing raw policy bodies, hidden payloads, credentials, prompts, answer
  keys, private memory, backend objects, host paths, argv, stdout/stderr,
  environment dumps, or tracebacks in contracts, fixtures, diagnostics, audit,
  issue evidence, or docs; and
- updating the SDL lineage ledger merely because the prose cites intellectual
  lineage, or omitting a ledger/source-audit update when a real normative
  derivation or compatibility claim did change.

## Non-Goals And Implementation Boundary

Issue #796 may publish normative formal semantics, the existing catalog's new
relation/revision and claim surface, bounded abstract counterexamples/property
checks, the existing claim-policy gate extension, the reviewable assurance
matrix, ADR-085 governance state, and the required participant-lineage update.

It does not:

- add or change SDL authoring fields, compiler IR, public policy/crossing DTOs,
  JSON API routes, runtime mediation, persistence, transport, gateway, backend
  adapter behavior, capability terms, or migration logic;
- implement ACT-617/API-409 mixed control, SEM-219/220/226 decision-surface
  exposure, DSL-142 participant-directed injects, API-423 crossing contracts,
  RUN-319 runtime enforcement, API-407 backend declarations, or ASR-535
  backend/formal assurance;
- certify API-408 as participant-safe egress or any backend as realizing the
  policy;
- require participant prompts, chain-of-thought, private memory, internal
  policy state, credentials, hidden answers, or backend-private traces; or
- claim universal noninterference, trace inclusion/equivalence, simulation,
  refinement, epistemic equivalence, timed/probabilistic security, or strong/
  weak bisimulation.
