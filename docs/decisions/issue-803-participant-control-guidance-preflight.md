# Issue #803 Participant I/O Control Guidance Preflight

Date: 2026-07-29

Issue: #803.

Requirement: RUN-319, with SEM-230 and API-423 as the issue's named semantic
and contract dependencies.

This note records repository-wide boundaries for participant-control
documentation. It is guidance only. It does not change participant semantics,
contracts, runtime behavior, backend declarations, conformance results,
scientific-completeness status, or lineage authority. It does not supply the
author, operator, backend, or researcher guide itself.

## Decisive Current-State Findings

The architecture is already settled. Issue #803 explains the shipped boundary;
it must not define another one:

- ADR-085 as amended by ADR-095 and SEM-230 revision `sem-230/rev2` own
  participant-relative world, view, local history, archival evidence,
  exact-cut policy resolution, independent information-flow operations, and
  nonclaims.
- API-423 `participant-crossing-occurrence-v1` owns the closed requested,
  decided, transformed, disclosed, delivery-attempted, delivered, observed,
  and audited fact stages. `validate_participant_crossing_occurrence_context()`
  owns their cross-record joins.
- RUN-319 owns the shared reference-runtime crossing boundary, trusted policy
  resolver, deny-first gates, participant crossing history, scoped
  idempotency, and expected-head atomic participant transition.
- API-407 owns the six participant-policy capability terms, support strength,
  required contracts, limitations, disclosures, evidence, and authorized
  downgrade behavior.
- ADR-081 and the current
  `raes-behavioral-relations@rev4` catalog own relation identity, quantifiers,
  claim surfaces, assurance status, evidence boundaries, and explicit
  nonclaims.
- Issue #802 and
  `docs/migration/participant-information-flow-control.md` own legacy,
  opt-in, required, and rollback interpretation. Documentation must not create
  another adoption-mode vocabulary.

No new ADR, schema, policy engine, documentation contract, example envelope,
claim registry, or runtime abstraction is warranted.

The current explanatory surface has two visible drifts that issue #803 must
correct without changing authority:

- `docs/research/participant-io-control/index.md` still describes the portable
  policy boundary as undelivered even though RUN-319, ASR-535, and issue #802
  evidence is present.
- `docs/explain/sdl/scientific-scenario-completeness.md` names behavioral
  taxonomy revision `rev1`; the canonical completeness profile and the current
  relation catalog bind `rev4`.

The version spaces must remain distinct: `sem-230/rev2` is a semantic authority
revision, `rev4` is the behavioral-taxonomy revision, and
`behavioral-relations-v1` and `participant-crossing-occurrence-v1` are contract
identities. A guide must not normalize those labels into one "version".

### Current evidence limits that examples must preserve

The documentation cannot use an example to claim a path stronger than the
repository currently executes:

1. The reference backend declares all six participant-policy features
   `unsupported`. Positive runtime behavior in tests uses explicit
   test-capable manifests and bounded evidence; it is not a shipped
   native-backend claim.
2. API-423 defines `ParticipantCrossingDecisionDisposition.WITHHOLD`, but
   RUN-319 `_decision_disposition()` currently emits only `permit`, `deny`,
   `transform`, or `unsupported`. The ASR-535 withholding expectation accepts a
   recorded `deny`. That is valid refusal evidence under the current finite
   probe, but it is not evidence that the runtime produced the semantically
   distinct `withhold` fact. A withholding example must therefore be labelled
   as semantic/contract guidance or state this reference-runtime limitation;
   it must not relabel a denial.
3. The shipped participant-view entry points construct a requested
   `projection`. No public runtime entry point constructs a requested
   `declassification`, and the ASR-535 governed-declassification case drives a
   status projection. The example can explain exact-cut declassification and
   its API-423 contract, but it cannot claim that the finite case exercised an
   independently selected `participant_declassification` runtime capability
   unless additional executable evidence exists.
4. `deliver_participant_directed_view()` records delivery of an already
   projected `ParticipantStatusViewModel` with the
   `participant-inject-delivery` interaction kind. It does not accept or bind a
   compiled DSL-142 `ParticipantInjectDelivery` or its original DSL-111
   inject/event/script/story identity. The authoring and runtime evidence must
   be described as separate delivered surfaces until an end-to-end stable-ref
   binding is executable.
5. The HTTP adapter exposes participant status, history, and context views and
   participant control occurrences. There is no generic participant-crossing
   endpoint, policy authoring endpoint, gateway, or public transformation API.
6. API-408 retains legacy behavior when no crossing resolver is configured.
   With a resolver, the HTTP adapter requires an audience candidate before
   lookup, resolves trusted crossing evidence, and commits before
   serialization. The guide must label these modes explicitly and must not
   describe default/legacy retrieval as governed participant-safe egress.

These are documentation and claim boundaries. Issue #803 is not authorization
to repair them in runtime code.

## Architecture Decisions And Guardrails

### Explanatory prose consumes authority

Reader guidance may explain the current semantics and link to the closest
authority. It must not introduce new normative operations, policy fields,
failure states, support levels, relation definitions, or migration rules.
Normative language belongs to the owning ADR, `specs/`, or `contracts/`
artifact. Examples are non-normative evidence illustrations.

Do not copy exhaustive enums, contract fields, required-contract maps, or
relation definitions into several audience pages. Use the existing identifiers
and link to the owning artifact. Where a compact comparison is necessary, one
table should map the existing operation or relation id to its owner, current
evidence, and nonclaim.

### Publish through the curated public-docs boundary

`docs/public/` is the only hosted reader-documentation source. The research
index, migration record, lineage explanation, scientific-completeness
explanation, ADRs, and preflights remain repository-visible internal records.
The issue's publish outcome cannot be satisfied solely by adding prose outside
`docs/public/`.

A hosted page must be under `docs/public/`, be reachable from that root's
toctree or an existing public route, and pass the existing public source,
output-inventory, Vale, Sphinx HTML, and linkcheck gates. Public
`include`/`literalinclude`/`download` targets must stay within `docs/public/`;
the source-boundary checker rejects cross-root includes and symlinks. Link to
repository authorities through stable repository URLs rather than copying
them into the public tree.

Use the existing task-first documentation style and route readers by role:
scenario author, participant-implementation author, runtime operator, backend
implementor, and researcher. This is presentation over one semantic boundary,
not five role-specific policy models.

### Keep examples operation- and evidence-specific

Each denial, withholding, redaction, declassification, intervention, inject
delivery, and unsupported-capability example must identify:

- whether it is authored semantics, a portable API-423 fact, reference-runtime
  behavior, backend declaration, bounded conformance, or a claim example;
- participant, episode, audience, direction, interaction kind, typed subject,
  requested operation, exact policy decision/state cut, order model, markings,
  capability posture, and safe evidence/provenance refs that actually apply;
- which independent gate or operation owns the result;
- which fact was recorded: request, decision, transformation, disclosure,
  attempted delivery, delivery, observation, or audit;
- whether backend dispatch or participant-visible serialization occurred; and
- the exact limitation and nonclaim.

An admitted decision is not a delivery. A delivery is not observation. Audit
retention is not participant disclosure. Redaction is not authorization or
declassification. Intervention and handoff remain API-409 control transitions
surrounded by API-423 crossing facts; they are not generic crossings that
replace the control state machine.

Contract-bearing examples must validate with the same published model and
contextual validator as production artifacts. Reuse current API-423 fixtures
and RUN-319/ASR-535 test builders when they demonstrate the exact case. A
hosted standalone example belongs under the existing
`docs/public/_static/examples/` convention and needs a focused test in the
current public-docs example suite. Do not add an example schema, a prose-only
validator, or a second fixture runner.

### Bind claims to the current relation authority

The claim-selection guide must use exact catalog relation ids and state the
evidence boundary beside each choice:

| Reader question | Canonical relation or evidence surface | Guardrail |
| --- | --- | --- |
| Did finite named cases pass? | `bounded-probe-success` | Bound, target, profile, cases, assumptions, and failures remain visible. |
| Are two recorded participant histories equal under one declared projection? | `participant-projected-history-equivalence` | Same participant and projection revision are required; this is not noninterference. |
| Are implementation traces contained in an abstract trace set? | `trace-inclusion` | Direction, labels, hiding, projection, and universal proof obligation are required. |
| Can steps be matched directionally? | `forward-simulation` or `backward-simulation` | State relation and direction are explicit. |
| Does a concrete state preserve abstract operations and observations? | `data-refinement` | Abstraction relation and operation obligations are explicit. |
| Are branching systems mutually matched? | `strong-bisimulation` or `weak-bisimulation` | Hidden closure, stuttering, divergence, and both directions are explicit. |
| Are unauthorized high variations invisible to a participant policy? | `policy-noninterference` | Use the complete SEM-230 adaptive-strategy, memory, exact-cut, purge, scheduler/environment, order, and declassification quantifiers. Proof remains deliberately unproved. |

Positive claim-bearing artifacts use `BehavioralClaimBindingModel` and
`validate_behavioral_claim_binding()`. Public prose should usually report the
bounded result and explicit nonclaim instead of manufacturing a structured
claim. Passing schemas, examples, runtime tests, or backend probes establish no
automatic trace relation, refinement, simulation, bisimulation,
noninterference, native realization, model check, or proof.

### Keep status and lineage views honest

The participant-control index is a navigation/current-state view, not a second
implementation program. Scientific completeness consumes the canonical
profile and delivery assessment; it must not hand-promote a concern or profile.
The lineage page records that issue #803 re-expresses the already adopted
SEM-230/API-423/RUN-319/ASR-535 lineage and maps the exact documentation and
evidence surfaces with explicit nonclaims.

Issue #803 adds no external intellectual source, normative derivation, or
compatibility claim. Therefore
`contracts/provenance/sdl-lineage-ledger-v1.json` and the lineage source audit
remain unchanged. If implementation discovers a real new derivation or
compatibility claim, that is a separately governed authority change rather
than a documentation convenience edit.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Semantic authority | ADR-085, ADR-095, and `specs/formal/participant-semantics/information-flow-control.md`. Link and explain; do not redefine. |
| Crossing contract | `ParticipantCrossingOccurrenceModel`, the closed API-423 vocabularies/stage models, `participant-crossing-occurrence-v1`, and `validate_participant_crossing_occurrence_context()`. |
| Authoring/control/inject semantics | ACT-617 mixed-control declarations, API-409 `ParticipantControlOccurrenceModel`, DSL-142 `ParticipantInjectDelivery`, and their existing compiler/semantic validators. Preserve their identities and boundaries. |
| Runtime mediation | `RuntimeControlPlane`, `ParticipantCrossingPolicyResolver`, `prepare_participant_crossing()`, `commit_prepared_crossing()`, `ParticipantControlMixin`, `ParticipantRetrievalMixin`, SEM-211 admission, and SEM-226 exposure. |
| Authentication | `ControlPlaneSecurityConfig.strict_defaults()`, `_ControlPlaneApiAuth`, `ControlPlaneIdentity`, `ParticipantControlSubjectBinding`, `ParticipantAudienceSubjectBinding`, roles, and exact target binding. |
| Backend support | `ParticipantFeatureSupport`, `PARTICIPANT_RUNTIME_POLICY_FEATURES`, `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, `resolve_participant_feature_support()`, backend profiles, and `BackendConformanceReport`. |
| Validation | Closed `ContractModel`/Pydantic shapes, API-423 contextual validation, API-409 control validation, participant snapshot and append-only transition diagnostics, and backend result validation. |
| Persistence | `RuntimeSnapshot.participant_crossing_history`, `ControlPlaneStore.commit_participant_transition()`, in-memory/local stores, expected history heads, atomic local replacement, operation records, idempotency fingerprints, and `AuditEvent`. |
| Errors and observability | `Diagnostic`, `Severity`, operation receipt/status envelopes, bounded HTTP 401/403/409 details, the redacted 500 envelope, safe audit events, operational summaries, and the conformance diagnostic sanitizer. Add no logger or exception family. |
| Claims | ADR-081, `raes-behavioral-relations@rev4`, `BehavioralClaimBindingModel`, `validate_behavioral_claim_binding()`, and `tools/check_behavioral_relation_claims.py`. |
| Migration | Issue #802 fixtures and `docs/migration/participant-information-flow-control.md`. Reuse legacy/opt-in/required and asymmetric rollback semantics. |
| Documentation | `docs/public/`, `docs/public/index.md`, `docs/explain/reference/documentation-style-guide.md`, `tools/check_public_docs.py`, and `implementations/python/tests/test_public_docs_policy.py`. |
| Lineage/completeness | `docs/explain/sdl/lineage.md`, the lineage ledger/model/checker, canonical scientific-completeness profile/delivery assessment, and `tools/check_scientific_scenario_completeness.py`. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, repo-policy, requirement-governance, behavioral-claim, lineage, public-docs, Sphinx, and full verification gates. |

## Cross-Cutting Layers And Security Posture

The guidance and any executable examples must pass every applicable layer:

1. **Authority and publication placement.** Explanatory prose stays in
   `docs/`; normative meaning stays in `specs/` and `contracts/`. Hosted
   content stays under the curated public root and cannot escape it through an
   include, download, or symlink.
2. **Example shape validation.** JSON examples pass the published schema and
   closed Pydantic model; multi-record API-423 examples also pass
   `validate_participant_crossing_occurrence_context()` with trusted subject,
   policy, evidence, and authority indexes. SDL examples retain safe YAML
   loading, parser limits, closed source models, semantic validation,
   instantiation, and post-instantiation validation. Documentation parsing is
   not a substitute.
3. **HTTP request/authentication gate.** Any live example uses
   `create_control_plane_app()` with explicit
   `ControlPlaneSecurityConfig`; strict defaults contain no principal or token.
   Bodies pass content-length and actual-byte guards, then closed DTOs.
   Bearer or trusted verified-proxy identity passes `_ControlPlaneApiAuth`,
   role authorization, and exact target binding.
4. **Participant authority/audience gate.** Ingress separately requires the
   principal-to-participant/controller binding. Governed HTTP egress requires
   one participant/audience candidate before lookup and the same binding again
   at crossing mediation. A backend/operator/auditor role alone is neither
   participant authority nor audience authorization. Direct in-process
   retrieval methods are not a standalone HTTP authentication boundary.
5. **Semantic/capability gate.** Trusted compiled/runtime state supplies exact
   policy, state cut, controller, authority, marking, exposure, and evidence
   coordinates. API-407 support is resolved per feature and strength. Missing
   resolver, required semantics, contracts, evidence, or support fails closed;
   a downgrade requires the existing policy and provenance references.
6. **Persistence and serialization gate.** API-423 facts remain append-only in
   the first-class crossing history. Expected-head
   `commit_participant_transition()` atomically binds the snapshot, operation,
   idempotency result, and audit event before dispatch or participant-visible
   serialization. The local store is a single-process/single-writer reference
   bound, not distributed linearizability. Administrative snapshots can carry
   raw crossing history; participant views must not.
7. **Error-envelope and observability gate.** Expected failures use the current
   bounded status/detail or diagnostic surfaces. Governed HTTP projection maps
   authorization failure to generic `403 forbidden` and conflicts to bounded
   `409` details; unexpected failures retain
   `{"detail":"internal server error"}`. Examples must not teach `str(exc)`,
   rejected input, hidden participant existence, policy bodies, or backend
   objects as response or log content.
8. **Secret and OS/process exposure gate.** This documentation change needs no
   credential, environment binding, secret loader, subprocess, daemon, socket,
   database, or host file. Do not invent token environment variables or CLI
   flags. Real bearer tokens, identity headers, private participant content,
   policy bodies, raw evidence, and hidden state never appear in Markdown,
   fixtures, process argv, environment variables, filenames, shell history,
   stdout/stderr, audit, or screenshots. Executable HTTP examples use an
   obvious test-only sentinel in-process, never a real credential.
9. **Claim and lineage gate.** The behavioral-claim checker scans live docs
   outside preflight records. A positive relation phrase must carry the exact
   governed relation and evidence boundary or be an explicit nonclaim. The
   lineage checker continues to validate the existing revision-pinned ledger;
   explanatory delivery evidence does not mutate provenance authority.
10. **Workflow gate.** Public guidance passes public-source containment,
    output inventory, Vale, executable example tests, Sphinx HTML, and
    linkcheck. The full repository policy still runs behavioral-claim,
    authority, lineage, completeness, requirement-governance, and verification
    checks. The branch name contains issue `803`, not requirement UID
    `RUN-319`, so governed checks use `RAES_REQUIREMENT_UID=RUN-319`.

## Extensibility Seam

The documentation seam is the tuple:

```text
(reader_role, interaction_kind, operation,
 authority_or_capability_owner, evidence_level, explicit_nonclaim)
```

Each value is backed by an existing role description, API-423 vocabulary,
API-407 feature, owning runtime/contract surface, or behavioral relation. A
future carrier, participant audience, operation, support strength, or proof
status adds a bounded row/example and evidence link. It does not require a new
guide schema, role-specific policy model, generic message object, or rewrite of
every audience section.

Keep exact ids and revisions visible so examples can be checked. Do not make
the seam an open metadata bag or build a documentation generator that becomes
a second authority. The next reasonable backend or interaction variation
should reuse the same example/evidence structure and replace only its typed
carrier, capability feature, policy coordinates, and evidence boundary.

## Gotchas And Anti-Patterns

Avoid:

- defining participant policy, authority, audience, state cuts, or relation
  meaning in explanatory prose;
- presenting the research index, migration record, lineage page, or
  scientific-completeness explanation as normative authority;
- satisfying "publish" only under non-hosted `docs/` paths;
- cross-root public includes, symlinks, copied schemas, or copied exhaustive
  vocabularies;
- inventing a participant gateway, crossing endpoint, policy authoring API,
  configuration file, environment variable, token loader, or CLI command;
- treating authentication, role, target authorization, participant authority,
  audience binding, admission, visibility, marking, declassification,
  transformation validity, and backend support as one gate;
- treating approval as admission, denial as withholding, admission as
  dispatch, schedule as delivery, delivery as observation, or audit as
  disclosure;
- treating redaction, masking, projection, hashing, summarization, loss, or
  weakening as authorization or declassification;
- presenting API-423 schema validity, a manifest declaration, method presence,
  or finite conformance as runtime or native-backend realization;
- presenting the reference backend as positively supporting participant
  policy features;
- claiming an end-to-end DSL-142 inject delivery identity from the current
  status-view delivery boundary;
- claiming a declassification capability was exercised when the runtime
  requested only projection;
- exposing administrative snapshot/crossing history as a participant view;
- showing tokens, raw payloads, hidden refs, rejected values, policy bodies,
  backend objects, exception strings, or tracebacks in examples or expected
  output;
- adding a documentation DTO, example schema, validator stack, exception
  hierarchy, logger, store, audit stream, relation registry, capability
  registry, migration mode, or verification workflow; and
- changing the lineage ledger/source audit or completeness status merely to
  make explanatory prose appear current.

## Non-Goals And Implementation Boundaries

- No implementation or repair of RUN-319, SEM-230, API-423, API-407, API-409,
  DSL-142, ASR-535, or issue #802 behavior.
- No schema, contract, controlled-vocabulary, backend manifest/profile,
  conformance report, scientific-completeness profile/assessment, or lineage
  authority change.
- No new endpoint, gateway, UI, policy engine, expression language,
  transformation runtime, provider integration, authentication mechanism,
  secret handling, environment configuration, persistence service, or OS
  sandbox.
- No synthetic legacy crossing history and no inference of permit, denial,
  withholding, delivery, observation, declassification, or enforcement from
  absent/empty history.
- No universal noninterference, trace inclusion/equivalence, simulation,
  refinement, strong/weak/probabilistic bisimulation, epistemic equivalence,
  timed/probabilistic security, native realization, model-check, or proof claim
  from documentation or finite examples.
- No promise that planned issue #810-#813 work is delivered.
