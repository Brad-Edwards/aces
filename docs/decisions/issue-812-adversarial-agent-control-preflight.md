# Issue 812 adversarial participant control and boundary-IFC preflight

Date: 2026-07-30

Issue: #812.

Requirements: none. The GitHub issue title, body, acceptance criteria, and
non-goals are the contract. Requirement-backed child work must not begin until
its owning DRAFT Ground Control authority exists.

This note records repository-wide architecture guardrails for the threat-model,
boundary information-flow, and AI-control evaluation design. It is guidance
only. It does not adopt a threat model or publish or amend an ADR or formal
specification. It also does not add a contract, change runtime enforcement,
declare a backend capability, create an evaluation, open child issues, or
establish robustness against intentional subversion.

## Decisive current-state findings

RAES already has the correct participant-neutral control skeleton. Issue #812
must compose it rather than add an LLM-agent framework:

- ADR-085, ADR-095, SEM-230 revision 2, and API-423/RUN-319 already define
  deny-first crossing mediation, exact state cuts, participant-relative
  observation, adaptive strategies, cross-episode memory, distinct crossing
  stages, and append-only evidence.
- ACT-617 and API-409/RUN-310 already distinguish participant proposals,
  approvals, denials, external direction, intervention, handoff, override,
  cancellation, action admission, and execution.
- API-407 already owns declared and effective backend feature strength,
  limitations, downgrade, required contracts, and realization evidence.
- ASR-535 and the experiment contracts already separate bounded semantic
  falsification, runtime enforcement, backend conformance, model checking,
  proof, task/run/study coordinates, evidence, derived measures, and
  limitations.
- The runtime-fact binding plane already models typed observation, derived,
  tool-result, and secret-reference sources; sensitivity, scope, freshness,
  audience, provenance, allowed sink sources, and protected secret sinks.
- ADR-099 and SEM-231 already require supervisor visibility, adaptive
  strategies, coalitions, memory, release, order, and timing to be explicit
  when those facts are in the observer's surface.

The missing authority is narrower but security-critical:

1. no portable relation currently carries independent confidentiality and
   integrity coordinates with conservative propagation through participant
   context, derivation, proposals, arguments, transformations, handoffs, and
   sinks;
2. `RuntimeFactSensitivity` is not an integrity label, `RawDataIntegrityModel`
   is content-integrity metadata rather than source trust, object markings are
   references rather than a complete flow lattice, and API-423 markings alone
   do not supply transitive derivation;
3. ordinary structural/semantic admission does not decide whether an otherwise
   valid action or output was derived from untrusted or confidential data;
4. intentional subversion, adaptive monitor evasion, collusion, audit-budget
   exhaustion, and trusted/untrusted monitor roles are not current runtime
   guarantees; and
5. RAES has no one revisioned control-evaluation profile binding honest/attack
   mode, main/side objectives, attacker knowledge, monitor topology, audit and
   intervention protocol, memory, safety/usefulness measures, and replay
   evidence.

These gaps warrant a DRAFT architecture authority during issue #812. It should
amend or compose ADR-085 rather than silently reinterpret it. This preflight
does not make that decision and must not be treated as the required DRAFT
authority.

## Primary-source disposition

| Source | Adoptable lesson | RAES boundary |
| --- | --- | --- |
| [FIDES](https://arxiv.org/abs/2505.23643) | Independent confidentiality and integrity labels, conservative propagation, default-untrusted external data, and deterministic checks before consequential actions. | Generalize to typed participant flows and sinks; do not adopt its LLM message or tool framework. |
| [CaMeL](https://arxiv.org/abs/2503.18813) | Separate trusted control from untrusted data, preserve provenance/capabilities, quarantine untrusted processing, and enforce policy at tool calls. | Quarantine and typed extraction are apparatus capabilities; they are not portable prompt semantics or automatic endorsement. |
| [SAMOS](https://research.ibm.com/publications/securing-mcp-based-agent-workflows) | Intercept every tool call and retain session-level flow context so individually legitimate calls cannot compose into leakage. | RUN-319 is the common mediation owner; an MCP gateway may be one backend realization, never the semantic boundary. |
| [AgentDojo](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) | Evaluate task utility separately from security under indirect prompt injection and adaptive attacks in dynamic tool environments. | Reuse experiment task/run/study/evidence contracts; no benchmark-specific runtime semantics. |
| [AI Control](https://arxiv.org/abs/2312.06942) | Evaluate protocols against intentionally subverting policies using limited trusted labor, trusted editing, untrusted monitoring, collusion countermeasures, audit, and shutdown. | Trusted/untrusted are declared experimental roles and assumptions, not proof that a model or human is trustworthy. |
| [ControlArena](https://control-arena.aisi.org.uk/) | Make honest/attack modes, main/side tasks, monitor visibility, defer-to-trusted protocols, audit/shutdown, safety/usefulness, and trajectory export explicit. | Represent these through RAES experiment and participant-control authorities; do not import its policy, scaffold, trajectory, or scorer object model. |
| [runtime shielding](https://arxiv.org/abs/1501.02573) | A shield is a final runtime mediator for a formally defined safety property, not a general trust score. | Only a deterministic, complete sink policy may be called shielding; a heuristic monitor is evidence and advice, not authorization. |

The useful common lesson is complete mediation of explicit flows at the last
enforceable boundary. None of these systems establishes model alignment,
chain-of-thought safety, monitor honesty, or protection from undeclared covert
channels.

## Architecture decisions and guardrails

### Keep confidentiality and integrity independent

The DRAFT authority must define two independent, revisioned coordinates:

- **confidentiality** constrains which audiences, principals, destinations, or
  sink classes may receive information; and
- **integrity** records which origins or possible writers may have influenced
  information and what minimum trust a sink requires.

A single `trusted`, `safe`, `secret`, role, sensitivity, confidence, marking,
or monitor-score field cannot represent both. Content hashes establish byte
integrity, not origin trust. Authentication establishes principal identity,
not content integrity. Confidentiality authorization does not endorse
untrusted data, and integrity endorsement does not declassify a secret.

The label algebra, ordering, conservative join, source defaults, and permitted
release operations belong to one revisioned policy profile. Opaque
transformations by a participant, model, external service, or script retain the
join of all inputs that could have influenced their result. Missing labels,
unknown sources, unresolved profile revisions, unsupported propagation, or
ambiguous joins fail closed or produce an explicit unsupported result; they
never become public or trusted by default.

Declassification is an authorized confidentiality relaxation. Endorsement is
an authorized integrity upgrade. Both name the exact source, result,
dimensions, destination or sink, authority, policy revision/state cut, and
evidence, and both create a new derived identity. Neither mutates historical
labels. Redaction, projection, admission, approval, and authentication remain
separate operations.

### Propagate across existing carriers instead of adding a generic agent event

Flow state must follow the existing typed path:

```text
observation/tool result/runtime fact
  -> participant context and retained memory
  -> proposal or participant output
  -> derived/transformed value and action arguments
  -> API-423 crossing decision
  -> final external-action or disclosure sink
```

The normative design should define one relation over these carriers and use
typed refs, revisions, digests, provenance, and exact policy/cut coordinates.
It must not add an open `context`, `taint`, `agent_message`, `tool_call`,
`monitor_metadata`, or `security_labels` map beside them.

The focused contract seam is the existing runtime-fact and API-423 crossing
composition. Do not add fields to `ParticipantRuntimeBaseEnvelopeModel` merely
to make every participant carrier look uniform; that would change unrelated
contracts before the shared semantics are settled. Do not copy runtime-fact
source/sensitivity validation into action, crossing, route, or backend code.
One resolver-backed contextual validator must join source facts, derivations,
effective labels, policy, authority, sink, crossing predecessors, and evidence.

Cross-participant flow uses API-423 typed crossings, API-409 control/handoff,
and shared/joint-state authorities. A receiver inherits the effective labels
and provenance of upstream context. Direct participant messages, generic
handoff payloads, or controller changes do not reset labels. Cross-episode
replay names the SEM-230 memory scope and preserves source/profile/revision
history; episode reset is not declassification or endorsement.

### Enforce immediately before every irreversible effect

The final RAES-enforceable sink boundary is:

- immediately before `RuntimeTarget` or a backend adapter performs an external
  mutation or tool action; and
- immediately before an external or participant-facing value is serialized,
  delivered, written, or otherwise disclosed.

Earlier schema validation, action admission, proposal approval, monitor review,
planning-time capability checks, or API-423 request construction is necessary
but not sufficient. The runtime resolves the effective flow labels, exact
policy/state cut, sink capability and destination, principal/participant/
audience authority, and API-407 effective support while the relevant history
heads are stable. It durably records the decision through the existing atomic
participant transition before dispatch or serialization. A denied,
unsupported, stale, or failed commit causes no backend call and no release.

Backends that can bypass this point cannot claim realization. A gateway,
apparatus wrapper, prompt, SDK, or monitor may add defense in depth but cannot
be the sole boundary. Streaming, multipart output, callbacks, errors, and tool
arguments are sinks too; policy must cover each chunk or complete materialized
value before exposure, according to the governed profile.

### Keep deterministic policy, monitoring, and control protocols distinct

Deterministic policy gates decide authorization, permitted flow, capability,
admission, and final sink release. A heuristic monitor emits a bounded,
revisioned observation, suspicion result, or recommendation with provenance,
visibility, limitations, and confidence. Its score never authorizes an action
and missing or failed monitor output never widens permission.

Monitor roles are experimental/apparatus declarations: trusted, untrusted, or
composed, with visibility, policy knowledge, shared inputs, independence or
correlation assumptions, possible collusion channels, and failure behavior.
Two monitors do not imply independent evidence. A “trusted model” is trusted
only within the named control-evaluation profile and capability boundary.

Human or trusted-system intervention must state which operation it performs:

- one-action authorization;
- declassification for named data and destination;
- endorsement/admission of an untrusted-derived value;
- trusted editing/transformation;
- control transition, deferral, handoff, interruption, or shutdown; or
- advice/evidence with no authority effect.

If one intervention performs more than one operation, each is explicit and
independently authorized. Trusted editing creates a fresh proposal/result with
inherited provenance and effective labels, then re-enters normal validation,
policy, capability, and action admission. Approval is never execution, monitor
trust, declassification, or label erasure.

### Make intentional subversion an explicit experimental mode

Honest-but-fallible behavior and an attack policy optimizing a side objective
are different experimental modes. Invalid ordinary behavior, random negative
tests, prompt-injection examples, or a green conformance suite cannot establish
intentional-subversion robustness.

A control-evaluation profile must close at least:

- honest or attack mode, main objective, protected side objective, and success
  conditions;
- participant capabilities and apparatus, policy and monitor visibility,
  threshold/audit-budget knowledge, prior-outcome visibility, and allowed
  collusion;
- adaptive strategy class over approvals, denials, edits, deferrals, handoffs,
  interruptions, outputs, ordering, and any declared timing observations;
- monitor identities, trust assumptions, topology, correlation, visibility,
  revision, and failure behavior;
- audit budget, sample/selection rule, intervention, trusted editing,
  defer-to-trusted, shutdown, and interruption protocol;
- episode reset, persistent/shared memory, replay, policy revision, and
  learning across episodes; and
- safety, usefulness, intervention/audit cost, uncertainty, limitations, and
  nonclaims as separate measures.

Use `ExperimentTaskModel`, `ExperimentEvaluationProtocolModel`,
`ExperimentStudyModel`, `ExperimentRunModel`, apparatus and factor contracts,
`ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`,
`ExperimentRunTraceabilityModel`, and `BehavioralClaimBindingModel`. An audit
budget is an evaluation/protocol coordinate, not a participant compute
`ParticipantResourceBudget` unless the runtime actually enforces that resource.
A monitor score is a measure, not a policy decision.

Until trajectory authority exists, a replayable trajectory is a digest-bound
graph of existing episode, behavior, control, crossing, action/result, and
experiment evidence refs with explicit observation/evidence boundaries. Do not
publish a second trajectory schema for this issue or copy a ControlArena log.
Hidden red-team objectives, credentials, private prompts, chain-of-thought, and
raw secrets remain outside portable evidence.

### Require boundary-faithful attack cases

| Case | Why ordinary admission is insufficient | Required boundary result |
| --- | --- | --- |
| Prompt/tool-result injection | An untrusted observation can produce a structurally valid, authorized action and valid arguments while redirecting control or destination. | Source defaults to untrusted; influence propagates through context and proposal; quarantine has no consequential capability; the final sink denies unless the exact integrity policy permits or governed endorsement occurs. |
| Confidential exfiltration | Reading a secret and sending an individually valid message or tool call may each be allowed while their composition leaks through arguments, output, errors, or a colluding participant. | Confidentiality propagates to every explicit derived sink; destination/audience policy blocks release and records safe evidence. Timing/covert channels remain a separate nonclaim. |
| Adaptive monitor evasion | A participant can learn from approvals, denials, edits, deferrals, audit frequency, or thresholds and shift to low-suspicion attacks. | The evaluation varies knowledge and adaptive strategy, accounts for audit-budget exhaustion and monitor correlation, and reports safety/usefulness separately. A monitor pass does not bypass deterministic gates. |
| Control-handoff manipulation | A valid API-409 handoff or external direction can transfer tainted context, change apparent authority, or induce a trusted participant to execute an attack. | Controller/authority change, flow labels, provenance, memory, receiver admission, and API-423 crossing are independently checked at one state cut; handoff never resets trust or grants action admission. |

Each case must assert both the semantic result and the absence of prohibited
side effects across backend calls, participant-visible output, snapshot
histories, audit/evidence, errors, and replay. Cases that bypass the real
`RuntimeControlPlane`/`RuntimeTarget`/store boundary are contract tests, not
runtime-control evidence.

## Canonical incumbents to reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Normative semantics | ADR-085, ADR-095, ADR-099, SEM-230, SEM-231, `Effective(rho,c)`, `MayCross`, exact cuts, strategy and memory scopes. Add no agent-local world, history, policy, or observer semantics. |
| Action and capability | SEM-211, `ParticipantActionAdmissionRequest`, `participant_action_admission_request_violations()`, ACT-622 decision-surface binding, action contract argument definitions, and participant implementation capability manifests. |
| Control and handoff | ACT-617, API-409 `ParticipantControlOccurrenceModel`, `validate_participant_control_occurrence_context()`, RUN-310 mediation, controller/authority binding, and `participant_control_history`. |
| Flow inputs and sinks | Runtime-fact declaration/version/sink/binding models, `RuntimeFactBindingPlane`, `validate_binding()`, `RuntimeFactDispatchCommand`, secret references, and protected sink handling. Extend their meaning through governed composition; do not fork source, sensitivity, freshness, or sink validation. |
| Crossing and projection | API-423 `ParticipantCrossingOccurrenceModel`, `ParticipantCrossingIntent`, `ParticipantCrossingPolicyResolver`, `validate_participant_crossing_occurrence_context()`, SEM-226 projection/exposure, and `participant_crossing_history`. |
| Runtime and persistence | `RuntimeControlPlane`, `RuntimeTarget`, `RuntimeSnapshot`, full-snapshot/transition diagnostics, `ControlPlaneStore.commit_participant_transition()`, expected history heads, operation records, idempotency, and both shipped stores. |
| Backend posture | API-407 `ParticipantFeatureSupport`, `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, `resolve_participant_feature_support()`, backend manifests, declared/effective strength, downgrade evidence, and `BackendConformanceReport`. |
| Evaluation and claims | Existing experiment task/protocol/study/run/apparatus/factor/evidence/measure/traceability contracts, behavioral relation profiles, `BehavioralClaimBindingModel`, and ASR-535 assurance axes. |
| Auth and transport | `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`, `_ControlPlaneApiAuth`, `ControlPlaneIdentity`, role/target/participant-subject binding, `request_size_guard_response()`, closed DTOs, and semantic request fingerprints. |
| Errors and observability | `Diagnostic`, `Severity`, operation envelopes, the generic redacted 500 handler, `sanitized_failure_message()`, `AuditEvent`, safe evidence/provenance refs, and ADR-066 plane separation. |
| Contract governance | `ContractModel`, controlled vocabularies, `schema_bundle()`, hand-governed schemas/fixtures/publication entries, `x-raes-invariants`, concept authority, and lineage checks. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, `tools/verify_all.py`, and existing policy, requirement, schema, semantic, conformance, and documentation gates. |

## Cross-cutting security layers

The intended design must pass every layer below; success at one does not
replace another.

1. **Source and apparatus declaration.** Participant implementation manifests
   and experiment apparatus declare capabilities and trusted/untrusted roles
   without embedding prompts, credentials, policy bodies, or private state.
   External observations/tool results default to untrusted when a trusted,
   revisioned source resolver cannot label them.
2. **Transport shape and size.** Existing HTTP entry uses the content-length
   and actual-byte guard followed by closed Pydantic DTOs. Path, query, and
   header values are not covered by the body guard; touched surfaces must use a
   shared bounded validator. No open label/policy/monitor maps are accepted.
3. **Authentication and binding.** Strict bearer or verified-proxy auth,
   exact target matching, role checks, participant/controller subject binding,
   and audience/destination authority precede semantic fact creation.
   Authentication never supplies data trust or declassification.
4. **Structural and semantic validation.** `ContractModel`, runtime-fact and
   action validators, API-409/API-423 resolver-backed contextual validation,
   exact revision/digest/cut joins, and full-snapshot/append-only transition
   validation all run. Validation logic has one owner per relation.
5. **Deterministic policy and capability.** The resolved flow profile,
   action admission, exposure/declassification authority, and API-407
   declared/effective support compose deny-first. Monitor output cannot
   override an unresolved, stale, unsupported, or denied gate.
6. **Final runtime sink.** The same in-process and HTTP path reaches
   `RuntimeControlPlane` immediately before `RuntimeTarget` dispatch or
   serialization. The effective labels and sink are rechecked at the stable
   state cut, and the decision is atomically committed before effect.
7. **Persistence, idempotency, and replay.** `RuntimeSnapshot` histories and
   `ControlPlaneStore.commit_participant_transition()` bind source/derivation,
   policy/cut, labels, sink, controller/authority, capability posture, semantic
   fingerprint, and expected heads. A retry returns the same decision; a
   changed cut/profile/label/authority conflicts or receives a fresh decision.
8. **Projection, errors, audit, and evidence.** Project before serialization.
   Expected failures use stable bounded codes/messages; unexpected failures use
   the generic redacted 500 path. Logs, `AuditEvent.details`, diagnostics, and
   evidence contain only safe refs, digests, classifications, counts, and
   bounded summaries—never raw content, secrets, prompts, policies, monitor
   internals, hidden objectives, or exception text derived from them.
9. **Configuration, secrets, and OS exposure.** Portable semantics add no
   environment variable, CLI flag, shell command, subprocess, socket, daemon,
   or sidecar requirement. Provider/apparatus configuration uses existing
   config/manifest registries and secret references. Tokens, prompts, policy
   bodies, tool arguments, and confidential values never enter process argv,
   environment, host paths, stdout/stderr, or unbounded crash reports.
10. **Publication and verification.** Any later contract change updates the
    authoritative model, schema, fixtures, publication manifest `last_change`
    and content hash, generator parity, concept authority, lineage where
    normative derivation changes, and focused/full verification. No runtime-
    only field or documentation prose may substitute for published authority.

## Extensibility seam

The stable runtime seam is a revisioned flow-policy profile referenced by
existing runtime-fact, action, crossing, and backend records. It parameterizes
the confidentiality and integrity domains, conservative composition, trusted
source declarations, declassification/endorsement authorities, sink
requirements, exact policy/state cut, participant and cross-episode memory
scope, and fail-closed unknown behavior. Resolvers provide the immutable
profile and derivation graph; runtime and backend names never become policy
branches.

The stable evaluation seam is a separate revisioned control-evaluation profile
bound through existing experiment artifacts. It parameterizes honest/attack
mode, objectives, attacker knowledge, adaptive strategy, monitor topology and
visibility, audit/intervention protocol, memory/replay, and measures. This
allows another participant apparatus, label domain, monitor protocol, backend,
multimodal source, or evaluation strategy without revising the canonical
carrier or inventing a generic agent framework.

## Work decomposition boundary

Before requirement-backed children are opened, issue #812 must publish its
DRAFT Ground Control authority and requirement disposition. Later children
must keep semantic authority, portable contracts, runtime enforcement, backend
or apparatus support, adversarial evaluation, and documentation as distinct
ownership surfaces with explicit dependencies. This preflight intentionally
does not enumerate, order, or implement those children.

## Gotchas and anti-patterns

- Do not use `RuntimeFactSensitivity`, object markings, confidence, roles,
  signatures, content hashes, or a `trusted` boolean as a two-coordinate IFC
  model.
- Do not create a second action, crossing, handoff, trajectory, experiment,
  evidence, policy, capability, diagnostic, exception, audit, or persistence
  hierarchy.
- Do not encode security semantics in `RuntimeSnapshot.metadata`,
  `AuditEvent.details`, apparatus `metadata`/`constraints`, free-form
  diagnostics, prompt text, backend-specific options, or logs.
- Do not make an HTTP gateway, MCP proxy, participant scaffold, prompt
  sanitizer, monitor, or model wrapper the only enforcement point.
- Do not treat schema validity, action admission, approval, role membership,
  declassification, endorsement, monitor score, backend declaration, runtime
  enforcement, and backend conformance as interchangeable evidence.
- Do not trust content because a participant copied, summarized, redacted,
  edited, or transformed it. Conservative influence remains until an explicit
  governed operation changes one label coordinate.
- Do not allow human approval to silently erase provenance or simultaneously
  authorize, admit, declassify, endorse, and execute.
- Do not infer independent monitors, non-collusion, or trusted-model behavior
  from different process/model ids. Record the assumption and test correlated
  failure where claimed.
- Do not disclose exact thresholds, hidden policy/monitor details, red-team
  side objectives, or secret-bearing counterexamples in participant-visible
  errors or audit evidence unless the selected experiment explicitly makes
  them observable.
- Do not claim intentional-subversion robustness, universal noninterference,
  shielding, backend realization, or covert-channel protection from ordinary
  negative tests, a green benchmark, or monitor accuracy.

## Non-goals and implementation boundaries

- No model-alignment claim, proof of safe internal reasoning, chain-of-thought
  capture, private prompt/state capture, credential capture, or participant
  implementation introspection.
- No replacement of participant-neutral action, observation, control, crossing,
  experiment, or evidence semantics with LLM chat/tool formats.
- No general-purpose policy engine, taint-analysis framework, message bus,
  participant gateway, monitor service, trajectory store, or agent scaffold.
- No claim that every explicit flow is observable inside an opaque apparatus,
  or that undeclared timing, resource, storage, model-steganographic, or other
  covert channels are controlled.
- No automatic trust in a human, model, monitor, backend, or external service;
  every role is a bounded authority or experimental assumption.
- No positive backend capability or assurance promotion without the existing
  declaration, realization, and conformance evidence paths.
- No DRAFT authority, requirement creation, child-issue creation, contract
  publication, runtime change, or evaluation delivery in this preflight.
