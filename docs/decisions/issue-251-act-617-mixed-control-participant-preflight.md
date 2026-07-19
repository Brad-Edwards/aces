# Issue #251 — ACT-617 Mixed-Control Participant Operation Preflight

Date: 2026-07-19

Issue: #251.

Requirement: ACT-617.

This note records the architecture boundary and implementation guardrails for
the authored and compiled mixed-control participant model. It is guidance
only: it does not add SDL fields, schemas, compiler resources, contracts,
runtime mediation, persistence, or a backend realization.

## Binding Authorities

- Accepted ADR-085 and
  `docs/research/participant-io-control/adoption-design.md` define one semantic
  policy boundary over existing carriers. They require explicit controller,
  authority, order, policy-revision, disposition, and evidence coordinates
  while preserving the identity of each action, control, observation, and
  evidence fact.
- `specs/formal/participant-semantics/information-flow-control.md` is the
  SEM-230 authority for policy state, deny-first composition, ordered labels,
  projection, and the bounded `policy-noninterference` claim. Its labels are
  semantic classes, not an instruction to copy one enum into every package.
- `specs/formal/participant-behavior-model/README.md`, accepted ADR-083, and
  the ACT-607/ACT-608 SDL implementation own participant affordances,
  authority/scope references, and decision-surface mode. ACT-617 extends that
  authored behavior-policy boundary; it does not replace it.
- ADR-009, ADR-019, ADR-036, ADR-061, and ADR-080 govern package authority,
  closed models, published schemas, compatibility, and revision-pinned
  lineage. Existing package boundaries and schema-governance checks remain in
  force.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and the canonical
  `verify` session own repository workflow. No issue-local workflow or
  verification script is warranted.

ADR-085 and SEM-230 already settle the cross-cutting architecture. This issue
does not need another ADR unless implementation discovers a genuine conflict
with those accepted authorities.

## Architecture Decisions And Boundaries

### Mixed control is owned by the behavior specification

The existing `ParticipantBehaviorSpecification` is the authored owner. Add a
dedicated, closed, typed mixed-control declaration beneath that owner rather
than a parallel top-level registry. `behavior_mode: mixed-control` remains a
decision-surface classification; it is not controller state, authority,
approval, or an override mechanism.

Fail closed on co-presence: a mixed-control declaration requires the governed
`mixed-control` mode, and the exact `mixed-control` mode requires an explicit
declaration. A mode-only document must not acquire implicit autonomous,
operator, or last-writer controller semantics. This tightening is a published
SDL compatibility decision under ADR-061 and must be evaluated as such.

The declaration must use stable local identifiers and closed typed records for
controller states and permitted control transitions. Each control policy must
bind exactly one controlled `participant_ref` from the owning behavior
specification; the owner's potentially plural `participant_refs` cannot imply
one shared controller state. List position and mapping insertion order have no
semantic meaning. Explicit order coordinates do.
Local state and transition identifiers must use the existing
`PortableIdentifier` rules because their compiled addresses are portable
contract identifiers.

The authored records describe allowed policy state and transitions. They are
not runtime occurrences. API-409 (#252) owns portable decision/event
contracts, and RUN-310 (#255) owns live mediation, occurrence history, and
persistence.

### Controller identity and authority reuse existing identities and refs

A controller is a semantic subject, not an authenticated API caller. Initially
bind `controller_ref` through the existing agent/participant reference domain:
self represents autonomous control and another declared agent represents an
external controller. An operator role, OS account, bearer token,
`ControlPlaneIdentity`, implementation identity, or behavior mode cannot stand
in for that binding. A future non-participant controller must be introduced as
another closed subject-binding variant, not admitted as an arbitrary string.

Each controller state must make the following coordinates explicit:

- stable state identity, the controlled participant reference, and the
  controller subject reference;
- non-empty authority-basis references anchored in that controller's existing
  authority declarations;
- explicit scope references no broader than the owning behavior
  specification's `authority_scope_refs`;
- policy identity and revision, derived from the owning behavior
  specification identity/address and `semantic_version`;
- validity and effective-order coordinates, predecessor/state revision where
  applicable; and
- evidence/provenance references for establishment and handoff.

No field may contain a credential, policy body, prompt, secret, or ungoverned
metadata. Authority is neither inferred from possession of a control-plane
role nor widened by omission, relative scope, or an `allow_widening` switch.
If a future requirement permits delegation or widening, it needs a governed,
typed authorization relation identifying the grantor, grantee, exact added
scope, revision, validity, and evidence.

### Preserve distinct ordered facts

Proposal, approval, denial, external direction, intervention, handoff,
override, cancellation, action admission, execution attempt/result, delivery,
observation, and evidence retention remain distinct facts with distinct state
owners. ACT-617 may define authored control transitions for the control-owned
subset, but must not copy admission, execution, or observation into that state
machine. In particular:

- approval or direction targets one proposal identity and revision; it is not
  action admission and cannot prove execution;
- handoff changes controller state through an explicit transition and explicit
  completion; it changes neither participant identity nor past provenance;
- override and cancellation do not rewrite an already admitted, attempted, or
  partially completed action; downstream occurrence records must expose the
  resulting conflict or partial disposition; and
- observation is evidence of participant-visible delivery, not evidence that
  an approval or controller transition happened.

Authored transition declarations must bind a stable transition identity, a
closed SEM-230-aligned transition kind, applicable from/to state references,
the target proposal or control revision where required, an expected state or
revision, effective order/validity, deterministic disposition rules, and
evidence references. Centralize the authored transition-kind authority once.
Do not duplicate equivalent enums in `aces_sdl`, `aces_contracts`, and
`aces_runtime`; downstream contracts must reuse or explicitly map the
governed terms.

### Conflicts and stale decisions fail closed

Portable behavior cannot depend on wall-clock arrival, dictionary order,
backend scheduling, or last-writer-wins. The semantic rules are:

- repeating the same decision identity with the same semantic fingerprint is
  idempotent; reusing an identity with different content is a conflict;
- an expired, revoked, late, policy-stale, proposal-stale, or expected-state-
  mismatched decision has an explicit stale/rejected disposition and performs
  no state change;
- when the declared order resolves concurrent decisions, the first transition
  applies and each later decision is re-evaluated against the new revision;
  when the order is partial or ambiguous, the outcome is an explicit conflict
  and no implementation may choose a winner silently; and
- cancellation, override, and handoff races append truthful dispositions;
  they never manufacture retroactive non-occurrence.

The first authored realization may support only a total effective order if it
declares that limit. The model must nevertheless keep the order strategy and
coordinate as a typed seam so a later causal/partial-order variant can add
predecessor relationships without redesigning every state and transition.
Reuse the repository's existing order vocabulary and participant-relative
ordering semantics; do not invent an ACT-617-only timestamp taxonomy.

### Compilation preserves typed meaning

`aces_processor.compiler.participant_behaviors` and
`ParticipantBehaviorSpecificationRuntime` remain the compiler owners. Compile
controller states and transition declarations into typed nested runtime
records under the behavior specification, with stable child addresses derived
from the parent behavior-specification address and local identifier. Resolve
controller, authority-basis, scope, evidence, and transition refs through the
existing alias/declaration indexes, retain them as dependencies, and emit them
in deterministic order.

The existing raw `spec` projection is not a canonical semantic carrier for new
ACT-617 meaning. Nor should these authored declarations become new planning
resources, top-level `RuntimeModel` maps, live controller histories, or backend
operations. Those would leak authored policy into the runtime layer owned by
#255.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent | Required use |
| --- | --- | --- |
| Closed authored shape | `SDLModel`, `ParticipantBehaviorSpecification`, `ScenarioContent` | Extend the existing behavior owner; reject unknown keys. |
| Portable identity | `aces_sdl._identifiers.PortableIdentifier` and compiled-address validation | Use for local state/transition IDs and derived child addresses. |
| Safe input | `load_sdl_yaml`, structural normalization, duplicate/canonical-key checks, variable mapping-key rejection | Preserve the one safe YAML/shape path. |
| Semantic references | `DeclarationIndex`, targetable-reference resolution, participant-behavior analysis | Resolve exact target domains and report stable validation issues. |
| Authority and scope | agent `authority_anchors`, behavior `authority_scope_refs`, ACT-607 checks | Bind authority to the controller and enforce non-widening. |
| Decision-surface mode | controlled vocabulary scope `behavior_specifications.behavior_mode` | Keep mode classification distinct while validating co-presence. |
| Ordering pattern | participant-relative ordering semantics and `ParticipantViewTransition`'s stable ID/effective-order validation | Reuse the invariant pattern, not the view-transition DTO. |
| Composition | `aces_sdl.composition` explicit reference rewriting | Rewrite every external ref when modules are namespaced; nested local IDs remain local. |
| Compilation | `compile_behavior_specifications`, `render_compiled_address`, compiler alias/dependency indexes | Produce deterministic typed child projections under the existing resource. |
| Diagnostics | `SDLParseError`, `SDLValidationError`, `SDLInstantiationError`, compiler `Diagnostic` | Extend existing error surfaces; add no ACT-617 exception hierarchy. |
| Provenance and observability | authored evidence refs and compiled provenance; runtime `AuditEvent` only in downstream mediation | Preserve semantic evidence without adding an application logger or emitting sensitive record bodies. |
| Published shape | `contracts/schemas/sdl/sdl-authoring-input-v1.json`, `instantiated-scenario-v1.json`, `instantiated-scenario-snapshot-v1.json`, `contracts/schema-publication-manifest.json`, and `aces_contracts.contracts.schema_bundle()` parity | Update all hand-governed authoritative shapes and compatibility evidence together. |
| Evidence | existing valid/invalid fixture families, participant-behavior semantic tests, compiler parity/determinism tests | Add falsification cases for operator impersonation, stale approval, authority widening, silent handoff, duplicate/conflicting IDs, and ambiguous order without a parallel harness. |
| Lineage | `docs/explain/sdl/lineage.md` and the existing lineage-ledger/source-audit rules | Record exact delivery, evidence, nonclaims; change the ledger only for a new derivation/compatibility claim. |

The adjacent `ParticipantControlMixin` and
`ParticipantActionAdmissionRequest` are deliberately not incumbents for the
authored controller model. The former owns runtime episode/action control; the
latter owns admission and implementation selection. Extending either in #251
would conflate layers.

## Cross-Cutting Layers And Security Posture

The intended authored-to-compiled design passes these layers in order:

1. **Safe parser and structural shape.** Input passes `load_sdl_yaml`, existing
   source limits, canonical/duplicate-key checks, variable expansion rules,
   and closed Pydantic models. Variables cannot create state/transition map
   keys or bypass identifier validation.
2. **Semantic policy validation.** `SemanticValidator` resolves controller,
   controlled-participant, authority, scope, evidence, and transition refs;
   verifies mode/declaration co-presence, unique IDs/orders, state continuity,
   authority anchoring, non-widening, validity, and deterministic conflict
   rules. Missing or unresolved security coordinates fail closed.
3. **Composition and instantiation.** Existing explicit rewrite tables handle
   every external reference. Instantiation admits only semantically valid,
   normalized content and preserves the same meaning in the governed
   instantiated schemas.
4. **Compiler and contract shape.** The existing compiler/address validators
   create typed deterministic child projections. Authoring, compiled fields,
   schema bundles, and provenance must agree; raw dictionaries and free-form
   metadata are not a compatibility escape hatch.
5. **Diagnostics and error envelopes.** Validation uses stable, value-safe
   issue codes and identifiers. It must not echo raw controller payloads,
   credentials, policy bodies, environment values, or evidence content.
   Unsafe direct compiler construction reports through the existing
   `Diagnostic` surface. Future HTTP adapters retain the existing redacted
   control-plane error envelope; no stack trace or policy detail becomes a
   client response.

#251 does not introduce an HTTP auth surface, environment binding, secret
loader, CLI option, subprocess, socket, file permission, or process-argument
surface. Therefore it needs no new auth/config/OS abstraction. Credentials and
tokens must remain absent from SDL and compiled artifacts; `ACES_REQUIREMENT_UID`
is repository-workflow context only. If #252/#255 expose the model, caller
authentication and strict control-plane target authorization remain separate
gates from participant/controller authority, with size limits, canonical
fingerprints, idempotency, audit events, and redacted failures. An authenticated
operator can request a transition but cannot impersonate its semantic
controller.

Likewise, #251 writes no live controller state. Future persistence belongs in
`RuntimeSnapshot`/`ControlPlaneStore` using append-only, revisioned occurrences
and the existing `AuditEvent`/idempotency patterns, never generic snapshot
metadata. Authored evidence references and compiler provenance are the
observability surface in this issue; do not add operational logging, and do not
log decision bodies, credentials, authority material, or evidence content.

## Extensibility Seam

Keep subject binding, policy identity/revision, validity, order strategy and
coordinate, expected state revision, transition kind, disposition, and
evidence as explicit typed coordinates. The immediate next variations are a
non-participant controller subject and causal/partial ordering. Each must be
addable as a closed subject-binding or ordering variant without changing the
meaning of existing records, editing every transition shape, or accepting
arbitrary metadata.

## Gotchas And Anti-Patterns

- Do not treat `behavior_mode`, role, admission reason, authenticated caller,
  backend process, or implementation identity as controller state.
- Do not place ACT-617 fields in `extensions`, raw compiler `spec`, runtime
  metadata, action contracts, observation boundaries, or lifecycle records.
- Do not introduce a second agent, authority, scope, reference resolver,
  identifier grammar, order vocabulary, diagnostics hierarchy, schema
  generator, or verification workflow.
- Do not infer a controller, authority, scope, validity, policy revision,
  predecessor, or conflict winner from defaults or collection order.
- Do not equate approval with admission, admission with execution, result with
  observation, or audit retention with participant visibility.
- Do not erase or mutate history to represent cancellation, override, handoff,
  concealment, revocation, retry, or policy change.
- Do not copy SEM-230's label alphabet mechanically into public enums. Map each
  authored term to its state owner and publish only the subset #251 owns.
- Do not update the lineage ledger or source audit merely because delivery
  status changed. Those artifacts move only when normative derivation or
  compatibility claims change.

## Non-Goals

- Portable wire DTOs, public API routes, runtime mediation, controller
  occurrence histories, persistence, replay, or backend realization.
- Selecting a human-control service, participant gateway, identity provider,
  transport, event bus, database, or secret/configuration mechanism.
- Changing action admission, lifecycle, execution, observation, view,
  information-flow enforcement, or evidence-retention ownership.
- Claiming backend support, runtime enforcement, distributed ordering,
  noninterference proof, or full policy enforcement from schema/compiler tests.
- Generalizing controller subjects or delegation beyond the typed semantics
  needed for ACT-617.
