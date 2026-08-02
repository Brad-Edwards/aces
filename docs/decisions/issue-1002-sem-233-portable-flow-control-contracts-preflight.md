# Issue 1002 sem-233 portable flow-control contracts preflight

Date: 2026-08-02

Issue: #1002.

Primary requirement: `SEM-233`.

Reused requirements: `SEM-230`, `API-409`, and `API-423`.

This note records architecture guardrails for publishing the portable SEM-233
contract boundary. It is guidance only. It does not publish a model, schema,
profile artifact, fixture, runtime resolver, store field, API route, backend
capability, conformance result, or information-flow claim.

## Decisive current-state findings

- The #1001 dependency is present on `dev`: ADR-101 and
  `specs/formal/participant-semantics/adversarial-flow-control.md` publish
  `sem-233/rev1` and the exact
  `participant-boundary-flow-policy-v1@rev1` powerset algebra. Issue #1002
  must encode that authority, not reinterpret it.
- SEM-230 owns participant-relative projection, exact cuts, memory, adaptive
  strategies, release schedules, and the `policy-noninterference` claim
  boundary. SEM-233 adds independent confidentiality and integrity obligation
  coordinates; it does not add another behavioral relation.
- Runtime facts already own typed source, scope, freshness, sensitivity,
  provenance, audience, binding, and action-input sink semantics. API-409
  already owns proposal, approval, denial, intervention, handoff, override,
  and cancellation occurrences. API-423 already owns crossing subjects,
  policy/cut coordinates, transformations, disclosure, delivery, observation,
  audit, and predecessor validation.
- None of those incumbents is a complete SEM-233 label or derivation. In
  particular, `RuntimeFactSensitivity`, object markings, signatures, digests,
  confidence, roles, and API-423 declassification do not also supply the
  integrity coordinate or conservative influence graph.
- The three incumbent published schemas are `draft`, but changing them is
  still unnecessary and would couple contract publication to runtime snapshot,
  history, capability, and migration surfaces. SEM-233 records can bind them
  by exact typed reference while preserving their occurrence identities and
  validators.
- ADR-101 already decides the relevant architecture. No ADR amendment or new
  ADR is warranted unless implementation discovers a genuine conflict with
  the two-coordinate algebra or existing carrier ownership.

The primary workflow UID is `SEM-233`; `SEM-230`, `API-409`, and `API-423` are
reused authorities. Because the branch name contains no requirement UID,
repository verification for the implementation uses
`RAES_REQUIREMENT_UID=SEM-233`. Contract delivery must not be recorded as a
new SEM-230 runtime or assurance result.

## Architecture decisions and guardrails

### Publish one profile root and one relation-document root

Use two new closed published schema roots, not a schema per nested record and
not fields on every incumbent carrier:

1. a flow-policy profile contract and corpus artifact for the exact immutable
   `participant-boundary-flow-policy-v1@rev1` definition; and
2. one flow-control relation document whose closed nested records cover
   effective labels, derivations, coordinate-specific release operations,
   final-sink decisions, and typed incumbent-carrier bindings.

The split is a security and versioning boundary. Operational records carry the
profile id, exact revision, and canonical digest; they do not embed or accept
an inline policy body. The profile artifact carries the closed confidentiality
and integrity obligation universes, normalization/order/join identifiers,
unknown-source posture, source-label resolver identity, derivation-rule
identity, release-authority identity, sink-policy identity, authority revision,
and explicit nonclaims. It is declarative data, not an expression language or
policy engine.

The relation document follows the incumbent `RuntimeFactBindingPlaneModel`
aggregate pattern: nested records are independently identified and
cross-referenced, while one root permits complete local graph validation and a
single publication/compatibility boundary. It is a portable validation and
resolver document, not a new event stream, participant history, runtime store,
message envelope, or control-plane service.

Do not publish separate label, derivation, release, decision, and binding root
schemas unless an independently versioned interoperability boundary is first
demonstrated. Shared coordinates belong in common nested `ContractModel`
types, not copied `$defs` or near-identical validators.

### Keep profile, policy, cut, and schema revisions distinct

Every record must distinguish:

- the published schema contract/version;
- SEM-233 authority revision `sem-233/rev1`;
- flow-profile id, revision, and digest;
- the concrete API-423 policy id, revision, and digest; and
- the exact decision/state-cut identity and revision or order coordinates.

The flow profile defines the algebra. A concrete participant policy decides
which profile obligations are present or satisfied at a cut. The API-423
policy reference is not the profile identity, and matching revision strings do
not establish identity or compatibility.

Profile loading must mirror the hardened behavioral-relation profile path. It
validates the portable id before path construction, uses strict bounded JSON
ingress, and applies closed model validation. It then checks requested-artifact
identity, the canonical digest, the exact revision, and the historical revision
registry. There is no `latest`, version range, caller-selected root,
environment-selected policy, or unknown-revision fallback.

### Model immutable labels and derivations without carrying values

An effective-label record binds a fresh label identity to one exact profile and
concrete policy/cut. It also binds governed subject identity, resolution status,
canonical sorted unique confidentiality- and integrity-obligation refs,
provenance/influence refs, and safe evidence refs.
The two coordinates are always present. Missing one is invalid; an unresolved
label is explicit and deny-equivalent rather than an empty coordinate.

A derivation record binds a fresh result identity and label to the complete
possible-input set, input-label refs, and exact rule and apparatus refs. It also
binds predecessor refs, provenance/influence refs, and any closed non-influence
assertion with its evidence. Its local validator must reject identity reuse,
cycles, dangling inputs, cross-profile joins, non-canonical token sets, a weak
result, and an ungoverned caller-declared omission.

Portable label and derivation records carry refs, revisions, safe digests,
closed dispositions, and bounded evidence references. They do not carry a
runtime-fact value, secret reference value, action argument value, observation
payload, prompt, policy body, rejected input, backend object, or hidden state.
A digest of confidential content is not automatically safe to disclose and
must not be required when an opaque incumbent identity/revision is sufficient.

### Keep declassification and endorsement as distinct fresh-result operations

Release operations form a closed discriminated union:

- declassification changes only named confidentiality obligations; and
- integrity endorsement changes only named integrity obligations while
  retaining the immutable possible-writer/influence refs that caused them.

Both bind the exact source identity and label, a fresh result identity and
label, the unchanged coordinate, and exact removed or replaced obligations.
They also bind sink or destination, participant/audience scope, authority
basis, profile/policy/cut, predecessor/order refs, evidence, and limitations.
The validator must prove the source obligations exist, the authority resolves
for the exact coordinate and sink, the result delta is exact, and the other
coordinate is unchanged.

API-423 already names declassification. A SEM-233 declassification binding may
join that exact transformation/disclosure stage. API-423 has no integrity-
endorsement operation; do not overload its declassification enum or add a
synonym. An endorsement binds a normal fresh API-423 transformation plus the
separate SEM-233 endorsement record. Approval, authentication, admission,
handoff, redaction, editing, monitor output, and role membership imply neither
operation.

### Add only the SEM-233 part of a final-sink decision

A final-sink decision records the resolved effective-label ref, exact sink,
destination/audience, profile/policy/cut, and both satisfaction results. It also
records release, API-423 decision, action-admission, capability-resolution, and
expected history-head refs. The remaining fields are final disposition, a
bounded reason code, evidence, and limitations.

It must reference rather than copy API-423's caller/target/participant,
visibility, marking, declassification, backend-support, and transformation
gates. The contextual validator verifies that those existing gates and the
new two coordinate checks all permit before the SEM-233 final disposition can
be `permit`. Any deny, unknown, unsupported, stale, ambiguous, unresolved, or
missing conjunct yields a non-permit disposition. `deny`, `unsupported`,
`stale`, and `unresolved` remain distinguishable.

The contract records what a trusted resolver decided. It does not execute the
decision, commit it, invoke `RuntimeTarget`, serialize participant output, or
prove that a backend enforced it. Those are #1003/#1004 obligations.

### Bind incumbent carriers through closed variants

Carrier bindings are a discriminated union with exact contract/stage kinds,
not an open `contract_id`, `metadata`, or path string. The required joins are:

| Incumbent | Binding precision |
| --- | --- |
| runtime fact | exact declaration, immutable version, compiled sink, and binding event as applicable; fact name or “latest” alone is insufficient |
| action argument | exact `ParticipantValidatedActionSelection` action-contract address, proposal ref, and normalized argument name; never copy the argument value |
| API-409 | exact event id, occurrence kind/revision, participant/episode, controller/authority, target/proposal/handoff coordinates, and predecessor relation |
| API-423 | exact event id, stage-specific identity, typed subject revision/digest, participant/episode, policy/cut, predecessor, transformation/disclosure relation, and sink decision |

Each binding points from an incumbent identity to the applicable label,
derivation, release, or sink-decision identity. It does not change the
incumbent occurrence or share its identity. Cross-participant and cross-episode
bindings carry both scopes plus crossing and memory/predecessor refs. Handoff,
controller change, participant change, and episode reset never clear upstream
label or provenance state.

Do not modify `ParticipantRuntimeBaseEnvelopeModel`,
`ParticipantControlOccurrenceModel`, `ParticipantCrossingOccurrenceModel`, or
`RuntimeFactBindingPlaneModel` for #1002. Do not add a second crossing/control
history to `RuntimeSnapshot`. If an incumbent carrier cannot be joined by its
existing stable identity, stop and revisit the contract boundary rather than
copying its payload or adding a generic extension bag.

### Give each invariant one owning validator

The new relation document owns only SEM-233-local and cross-family joins:

- exact profile/token resolution and canonical two-coordinate algebra;
- immutable label and derivation identity, union, provenance, and graph
  invariants;
- coordinate-specific fresh-result release deltas;
- final-sink conjunction and disposition; and
- exact agreement between its binding variants and already validated
  incumbent records.

It must delegate incumbent meaning to:

- `RuntimeFactBindingPlaneModel` and runtime-fact binding policy for fact,
  scope, freshness, audience, secret-reference, and sink semantics;
- `ParticipantValidatedActionSelection`,
  `ParticipantActionAdmissionRequest`, and
  `participant_action_admission_request_violations()` for normalized action
  arguments and admission;
- `validate_participant_control_occurrence_context()` for API-409 declaration,
  controller, target, revision, and handoff joins; and
- `validate_participant_crossing_occurrence_context()` for API-423 subject,
  policy, predecessor, transformation, disclosure, delivery, observation,
  evidence, marking, and order joins.

Use one typed non-wire validation context and one public resolver-backed
contextual validator, following
`ParticipantInformationStateValidationContext` and
`validate_participant_information_state_resolved_context()`. The resolver
supplies exact profile, source/sink/authority, incumbent record, and safe
evidence indexes from trusted state. It is not serialized in the portable
document. Resolver absence, exception, malformed context, unknown identity,
stale revision, digest mismatch, or incomplete predecessor graph fails closed
with a value-independent `ValueError`.

The published relation schema must expose this boundary through
`x-raes-invariants` whose inputs name the new contract plus
`runtime-fact-binding-plane-v1`, `participant-control-occurrence-v1`, and
`participant-crossing-occurrence-v1`. JSON Schema validates shape; it does not
claim to execute the contextual join.

### Preserve compatibility and claim honesty

The new contracts are additive companion authorities. Existing API-409,
API-423, runtime-fact, snapshot, manifest, and participant-view payloads retain
their current shape and meaning. Absence of a SEM-233 relation document or
binding means `legacy/unknown/unsupported` for this stronger profile, never an
implicit empty label, permit, enforcement, or migration result.

Do not add the new contract ids to backend/processor/participant supported-
contract allowlists, backend profiles, API-407 feature requirements, or
existing backend manifests in #1002. Contract publication is not apparatus or
backend support; #1004 owns those positive declarations. Do not add the new
records to `RuntimeSnapshot`, `ControlPlaneStore`, operation fingerprints,
idempotency state, or runtime histories; #1003 owns the persistence and final-
sink path.

Conformance registration must report the strongest honest result as
`structural-context-required` unless the exact resolver context is supplied.
A passing model/JSON Schema validation must not be reported as semantic
admission, final-sink enforcement, backend realization, or adversarial
robustness.

## Canonical incumbents to reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| semantic authority | ADR-085/095/101, SEM-230, and `adversarial-flow-control.md`; encode exact revision 1 without changing its algebra or claim boundary |
| contract primitives | `ContractModel(extra="forbid")`, `NonEmptyString`, `PrefixedDigestString`, existing RFC3339 and bounded identifier types, discriminated unions, and canonical sorted/unique collection patterns |
| safe corpus ingress | `parse_bounded_json_object()`, `StrictJsonIngressError`, `canonical_json_digest()`, `raes_contracts.corpus`, portable-id-before-path validation, cached exact-revision profile loaders, and historical profile registries |
| runtime facts and action arguments | `RuntimeFactBindingPlaneModel`, `validate_binding()`, `ParticipantValidatedActionSelection`, `ParticipantActionAdmissionRequest`, and existing action admission validators |
| control and crossing | API-409/API-423 models, vocabularies, contextual validators, typed subjects, exact policy refs, fresh transformation identities, and predecessor stages |
| diagnostics and errors | `Diagnostic`, `DiagnosticModel`, `Severity`, value-independent `ValueError`, `sanitized_failure_message()`, and the existing redacted unexpected-error envelope |
| publication | hand-governed `contracts/schemas/`, `schema_bundle()`, schema metadata and `x-raes-invariants`, valid/invalid fixtures, sharded schema-publication entries, and the compatibility classifier |
| packaging and conformance | `raes_contracts.corpus`, the existing Hatch corpus force-include, and `raes_conformance.conformance.validators`; use the shared shipped corpus and classify contextual strength honestly |
| workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, repository policy, requirement governance, JSON/schema publication, generated parity, docs, and full verification gates |

No second policy registry, source/sink registry, action or crossing hierarchy,
context validator stack, exception hierarchy, logger, audit channel, store,
corpus loader, schema generator, or workflow script is justified.

## Cross-cutting layers and security posture

The #1002 design passes the following layers. Layers explicitly outside this
contract-only issue remain downstream boundaries, not silently satisfied ones.

1. **Trusted profile/corpus ingress.** The profile is loaded from the shipped
   `contracts/profiles/` authority through `raes_contracts.corpus`. Profile ids
   are grammar/allowlist checked before path construction. Bounded duplicate-
   rejecting JSON parsing precedes closed model validation; exact id, revision,
   authority revision, and digest must agree. No arbitrary filesystem or URL
   loader is added.
2. **Contract shape and resource bounds.** Both roots and every nested object
   use `ContractModel`. Strings, token universes, graph collections, refs, and
   nested lists have explicit length/count bounds. Token/ref sets are canonical
   sorted and unique. Unknown keys, missing coordinates, duplicate identities,
   non-finite numbers, oversized artifacts, and ambiguous union variants are
   rejected before contextual interpretation.
3. **Local semantic validation.** The relation model proves internal profile,
   label, derivation, release, graph, and final-disposition consistency. Empty,
   unknown, or missing state never normalizes to public/trusted. Historical
   labels and provenance are immutable; transformations create fresh results.
4. **Incumbent contextual validation.** The resolver-backed validator joins
   exact runtime-fact, action-argument/admission, API-409, API-423, source,
   sink, authority, evidence, profile/policy/cut, and predecessor indexes. It
   calls the owning incumbent validators and adds only SEM-233 cross-family
   checks. Schema-valid unresolved joins fail closed.
5. **Authentication and authorization boundary.** #1002 adds no HTTP or live
   operation path, so it does not traverse
   `ControlPlaneSecurityConfig.strict_defaults()`, `_ControlPlaneApiAuth`, role
   and target binding, or participant/controller/audience subject binding.
   Portable authority refs are evidence coordinates, not proof that a caller
   was authenticated. #1003 must obtain them from the trusted runtime identity
   and policy context, never a request field, header, or query parameter.
6. **Secret-handling boundary.** Contracts contain no raw secret, secret value,
   prompt, credential, token, private model state, hidden objective, rejected
   record, inline policy, or confidential counterexample. Existing runtime
   secret references remain opaque. Logs and diagnostics may carry bounded
   safe ids, classifications, counts, and non-content digests only; hashing a
   secret does not authorize disclosure.
7. **Configuration and environment shapes.** Portable contract publication
   adds no environment variable, CLI option, config bag, feature flag, dynamic
   import, provider setting, or caller-selected profile root. Exact profile
   selection is a trusted resolver input. The existing workflow UID is the only
   environment binding relevant to #1002.
8. **OS/process exposure.** #1002 adds no subprocess, shell command, socket,
   daemon, sidecar, host path, network fetch, or temporary secret file. No
   label, value, policy body, argument, credential, or evidence payload enters
   process argv, environment, filenames, stdout, or stderr.
9. **Persistence and final-sink boundary.** #1002 does not traverse
   `RuntimeSnapshot`, expected history heads, operation idempotency,
   `ControlPlaneStore.commit_participant_transition()`, `RuntimeTarget`, or
   participant/external serialization. It defines the exact portable records
   #1003 must consume; it establishes no atomicity, zero-side-effect denial,
   restart, replay, or enforcement claim.
10. **Error envelopes, logging, and audit.** Model and contextual failures use
    bounded value-independent messages and the incumbent exception posture;
    do not add a SEM-233 exception hierarchy or logger. Conformance routes
    failures through `sanitized_failure_message()` so Pydantic rejected input
    is not persisted. Any future HTTP adapter keeps the generic
    `{"detail":"internal server error"}` unexpected-failure envelope and safe
    `AuditEvent` details.
11. **Publication, packaging, and compatibility.** The hand-governed schemas,
    Python reference models, valid/invalid fixtures, `schema_bundle()`, schema
    output routing, publication entries with `last_change` and current content
    hash, generated parity, semantic-invariant annotations, conformance
    registry, and wheel/sdist corpus all move consistently. A generator edit
    does not authorize the schema, and a schema file without the other surfaces
    is incomplete.
12. **Assurance and traceability.** Formal assurance may advance only the
    portable-contract/structural-validation rows actually delivered. SEM-233
    remains DRAFT while runtime, backend, and evaluation obligations remain
    open. SEM-230/API-409/API-423 traceability records reuse; they do not absorb
    ownership of the new contract or gain stronger implementation claims.

## Whole-repository surfaces in scope

- **Authority and guidance:** ADR-101, SEM-230, the SEM-233 formal authority,
  the adversarial-control research record, assurance fulfillment, and this
  preflight. Accepted ADR text remains unchanged.
- **Contract code:** `raes_contracts` versions, closed models, canonical digest
  and bounded ingress helpers, exact profile loader/history seam, public
  exports, and `schema_bundle()`.
- **Published corpus:** the flow-profile artifact, two normative schema roots,
  valid/invalid fixtures, schema-publication entries, and schema output routing.
  The existing packaging hook already ships the entire `contracts/` tree.
- **Context incumbents:** runtime-fact models/policy, normalized action
  selection/admission, API-409 models/context validator, and API-423
  models/context validator. Their published schemas and histories remain
  unchanged.
- **Validation and diagnostics:** `x-raes-invariants`, semantic-profile
  annotation checks, conformance validator/strength registries, `Diagnostic`,
  and sanitized failure rendering.
- **Verification:** repository policy, requirement governance, JSON artifacts,
  schema publication/compatibility, generated parity, authority boundary,
  focused contract/context tests, docs, and the canonical full verification
  command.

Backend manifests/profiles, API-407 feature declarations, runtime mediation,
snapshots/stores, HTTP routes/security configuration, conformance probes, and
public positive claims are reviewed as boundaries but are not changed by
#1002.

## Extensibility seam

The stable profile seam is:

```text
(profile_id,
 profile_revision,
 profile_digest,
 authority_revision,
 confidentiality_obligation_universe,
 integrity_obligation_universe,
 source_label_resolver_ref/revision,
 derivation_rule_ref/revision,
 release_authority_ref/revision,
 sink_policy_ref/revision,
 unknown_behavior)
```

The stable relation seam adds exact subject/carrier identity, participant and
episode scopes, and concrete policy/cut. It also adds effective-label,
derivation/release, sink/destination/audience, incumbent-decision, expected-head,
evidence, and limitation coordinates.

A new token, source declaration, sink rule, participant kind, destination, or
authority is data in a new exact profile revision and resolver context; it does
not require fields on every carrier. A genuinely new carrier family adds one
closed binding variant and resolver adapter, not a free-form contract id. A
third policy coordinate or quantitative leakage metric changes the algebra.
Timed, probabilistic, or covert-flow properties do too. Such changes require a
governed profile/schema decision and cannot hide in a token set or metadata.

## Gotchas and anti-patterns

Avoid:

- treating the schema contract id, SEM-233 authority revision, flow-profile
  revision, concrete policy revision, and decision cut as interchangeable;
- a single `trusted`, `safe`, sensitivity, marking, signature, digest,
  confidence, role, or monitor-score field standing in for both coordinates;
- allowing one coordinate to default when only the other is supplied;
- using empty sets, missing labels/provenance, unknown sources, unresolved
  profile revisions, ambiguous joins, or absent bindings as public/trusted;
- open `taint`, `security_labels`, `policy`, `monitor`, `context`, headers,
  query parameters, environment, backend-options, or `agent_message` maps;
- copying source values, action arguments, prompts, policies, rejected input,
  backend objects, or private state into label, derivation, release, binding,
  decision, fixture, diagnostic, or evidence records;
- treating a content digest as safe disclosure or as source authenticity,
  authority, provenance, or integrity endorsement;
- mutating a historical label/provenance record, reusing a result identity, or
  letting policy change reinterpret an old source/release/decision;
- excluding context, retained/shared state, destination/tool arguments, error
  branches, transformations, handoffs, participant changes, or episode replay
  from possible influences without a closed evidenced non-influence relation;
- treating redaction, sanitization, summarization, parsing, trusted editing,
  approval, admission, authorization, authentication, handoff, or monitor output
  as declassification or endorsement;
- overloading API-423 declassification as integrity endorsement or adding
  SEM-233 fields to the shared participant envelope;
- resolving a runtime fact by name/latest, an action argument without its
  proposal/action contract, an API-409 occurrence without target/controller
  context, or an API-423 fact without exact stage/policy/predecessor context;
- duplicating runtime-fact, API-409, API-423, action-admission, capability, or
  publication validation inside the new model;
- a second exception hierarchy, diagnostics format, logger, audit stream,
  persistence store, schema registry, corpus loader, generator, or CI script;
- adding contract support to backend/processor/participant manifests or
  profiles before #1004 supplies the owning capability and evidence;
- storing the new relation in snapshot `metadata`, operation details, audit
  details, logs, or an issue-local file instead of the #1003 governed seam;
  and
- reporting contract/model/fixture success as final-sink enforcement, backend
  realization, noninterference, shielding, monitor honesty, model alignment,
  covert-channel control, or intentional-subversion robustness.

## Non-goals and implementation boundaries

- No change to SEM-230/SEM-233 formal semantics, accepted ADRs, behavioral
  relation taxonomy, or noninterference definition.
- No change to API-409, API-423, runtime-fact, action, observation, participant
  envelope, view, snapshot, history, operation, audit, or evidence carrier
  shapes.
- No SDL syntax, participant message, generic policy/taint engine, gateway,
  monitor service, trajectory store, agent framework, or LLM-specific format.
- No API route, authentication mechanism, config/env surface, secret resolver,
  runtime policy evaluator, final-sink enforcement, `RuntimeTarget` call,
  serialization path, persistence, idempotency, replay, or store migration.
- No backend/apparatus capability declaration, downgrade, realization,
  conformance probe, or public positive guidance.
- No chain-of-thought, prompt, credential, raw secret, private model state,
  hidden objective, or secret-bearing counterexample carriage.
- No universal information-flow, noninterference, runtime, backend,
  adversarial-robustness, alignment, monitor-trust, or covert-channel claim.
