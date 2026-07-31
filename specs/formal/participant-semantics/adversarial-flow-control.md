# SEM-233 and ASR-536 Adversarial Participant Flow Control

Status: design authority; positive implementation and evaluation obligations
remain DRAFT.

Requirements: `SEM-233`, `ASR-536`.

Decision authority:
[ADR-101](../../../docs/decisions/adrs/adr-101-adversarial-participant-flow-control.md).

## Scope

This specification adds two revisioned profiles over the existing SEM-230,
ACT-617, API-409, API-423, RUN-310, RUN-319, API-407, experiment, and ASR-535
carriers:

1. `participant-boundary-flow-policy-v1@rev1`, which defines independent
   confidentiality and integrity coordinates, conservative explicit-flow
   derivation, release operations, and final-sink decisions; and
2. `intentional-subversion-control-evaluation-v1@rev1`, which defines the
   experimental variables and evidence boundary for honest and intentionally
   subverting participant policies.

The profiles apply to human, scripted, reinforcement-learning,
large-language-model, and external-service participants. They do not expose or
govern chain-of-thought, private model state, credentials, or undeclared
internal apparatus flows.

## State and identities

For participant `p`, episode `e`, memory scope `m`, exact state cut `c`,
flow-policy profile `phi`, source or derived value `x`, and sink `s`, the
governed state reuses:

- the SEM-230 participant/audience projection, policy decision, memory,
  adaptive-strategy, release, order, and provenance coordinates;
- ACT-617 controller and authority state;
- API-409 control occurrences;
- API-423 crossing request, decision, transformation, delivery, observation,
  and audit occurrences;
- runtime-fact source, derivation, audience, scope, freshness, and sink
  declarations;
- participant proposal, action-admission, attempt, result, and output facts;
- the RUN-310/RUN-319 append-only histories and exact expected heads;
- API-407 declared and effective capability support; and
- experiment task, protocol, study, run, apparatus, evidence, measure, and
  traceability records.

Every derived identity is fresh and binds the source identities, derivation
kind, profile and revision, exact policy/state cut, authority, destination or
sink, and safe evidence refs. No release operation mutates a prior fact.

## Flow labels

The effective label of `x` is:

```text
Label_phi(x,c) = (Conf_phi(x,c), Int_phi(x,c))
```

where:

- `Conf_phi(x,c)` is ordered by permitted audience, principal, destination, and
  sink exposure; higher labels are at least as restrictive; and
- `Int_phi(x,c)` conservatively records origins or possible writers that may
  have influenced `x`, plus the sink-required integrity predicate.

These coordinates are independent. Authentication, signatures, hashes,
markings, sensitivity, confidence, roles, and monitor scores can contribute
governed evidence but cannot define both coordinates.

### Source defaults

`SourceLabel_phi(src,c)` resolves through the revisioned source authority.
When the source, profile, revision, or authority cannot be resolved, the
result is the profile's maximum-confidentiality and minimum-trust default. A
deployment may use a narrower deny-only representation, but it cannot default
to public or trusted.

### Conservative composition

For a derivation `d` whose possible inputs are `I(d)`:

```text
Conf_phi(d,c) = join_conf { Conf_phi(x,c) | x in I(d) }
Int_phi(d,c)  = join_int  { Int_phi(x,c)  | x in I(d) }
```

`join_conf` is the profile's least upper bound. `join_int` is conservative
influence union under the profile's integrity order.

An opaque participant, model, service, script, summary, copy, redaction, or
transformation retains the join of every input that could have influenced its
result. A typed transformation can narrow the influence set only when its
closed contract and evidence establish that relation. Apparatus claims alone
cannot do so.

### Cross-participant and cross-episode carriage

API-409 handoff, API-423 crossing, controller change, participant change,
shared state, joint state, or episode reset never clears labels or provenance.
A receiving participant inherits the effective upstream label and source
history through the governed crossing.

Cross-episode replay binds the original source, profile, revision, policy
decisions, release events, SEM-230 memory scope, and expected history heads.
Replay under a later cut receives a fresh decision.

## Distinct operations

The following operations are semantically distinct:

| Operation | Effect |
| --- | --- |
| authentication | establishes principal identity and credential validity |
| authorization | permits an operation for an identity and authority |
| admission | accepts a fact, proposal, action, transition, or evidence record |
| approval | records a supervisory control decision |
| declassification | relaxes confidentiality for an exact result and sink |
| integrity endorsement | changes the admitted origin-trust coordinate for an exact result and sink |
| redaction | derives a new representation and retains influence unless a governed rule states otherwise |
| transformation | derives a new identity under a typed relation |
| trusted editing | derives a fresh proposal that re-enters normal gates |
| handoff | changes controller or authority state |
| deferral | transfers a decision obligation without authorizing the effect |
| interruption or shutdown | changes lifecycle and future enabledness |
| advice | supplies evidence or recommendation without authority |
| execution or delivery | realizes an already permitted effect or disclosure |

Declassification and endorsement each bind:

- source and fresh result identity;
- exact changed coordinate and unchanged coordinate;
- destination, audience, or sink;
- authorizing principal and authority basis;
- profile, revision, policy decision, and state cut;
- predecessor and order refs; and
- safe evidence and limitation refs.

Approval, authentication, admission, monitor output, or trusted role does not
imply either release operation.

## Final-sink decision

For effective label `l`, exact cut `c`, sink `s`, authority `a`, destination
`d`, participant `p`, and effective capability posture `k`:

```text
MayRelease_phi(p,l,s,d,a,c,k)
  = FlowPolicy_phi(l,s,d,c)
    and Authorized(a,p,s,d,c)
    and Admitted(p,s,c)
    and EffectiveCapability(k,phi,s)
    and FreshHeads(c)
```

Every conjunct is deny-first. Heuristic monitor output is not a conjunct that
can turn denial into permission. A profile may require monitor evidence as a
precondition, but only deterministic policy interprets that evidence.

The runtime evaluates `MayRelease`:

- after the last label, provenance, policy, authority, destination,
  participant, audience, capability, and state-cut resolution;
- immediately before `RuntimeTarget` or a backend performs an external
  mutation, tool action, callback, or persistent write; and
- immediately before participant-facing or external serialization, streaming,
  delivery, error output, or other disclosure.

It commits the decision and all predecessor/history changes atomically before
effect. A denial, unsupported result, missing label or provenance, ambiguous
join, stale cut, history-head conflict, or failed commit causes no external
call and no disclosure.

Each streaming chunk is either governed before release or derived from a
complete materialized value whose entire release is governed by the profile.

## Deterministic policy and heuristic monitors

Deterministic policy decides authorization, flow, capability, admission, and
release. A heuristic monitor emits a bounded observation, suspicion result, or
recommendation with identity, revision, visibility, provenance, confidence,
limitations, and safe evidence.

```text
MonitorResult != Authorization
MonitorFailure does not widen MayRelease
```

Monitor roles are apparatus and experiment declarations. A profile states:

- trusted, untrusted, or composed role;
- inputs and participant-visible outputs;
- policy, threshold, and audit knowledge;
- model or implementation identity where relevant;
- topology and shared inputs;
- independence, correlation, and collusion assumptions; and
- failure and fallback behavior.

Different monitor or model ids do not establish independence.

Human or trusted-system intervention names each authority effect. If an
intervention edits a proposal, it creates a fresh proposal with inherited
provenance and effective labels and re-enters validation, policy, capability,
and admission.

## Intentional-subversion evaluation profile

An admitted ASR-536 evaluation profile closes:

```text
Eval =
  (mode,
   main_objective,
   side_objective,
   participant_capabilities,
   apparatus,
   policy_knowledge,
   monitor_knowledge,
   audit_budget_knowledge,
   prior_outcome_visibility,
   adaptive_strategy_class,
   collusion,
   monitor_topology,
   monitor_correlation,
   audit_budget,
   audit_selection,
   intervention_protocol,
   memory_scope,
   replay_scope,
   policy_revision_scope,
   measures,
   limitations,
   nonclaims)
```

`mode` is `honest` or `attack`. Honest-but-fallible behavior and an attack
policy optimizing a side objective are separate populations.

The adaptive strategy is quantified over the facts actually visible to the
participant under SEM-230 and ADR-099. Possible feedback includes approvals,
denials, edits, deferrals, audits, handoffs, interruptions, outputs, order, and
declared timing facts. Hidden policy, threshold, audit, monitor, or objective
details do not enter the participant view unless the profile declares them
visible.

An audit budget is an evaluation-protocol coordinate unless the runtime
actually enforces it as a participant resource. Audit selection, trusted
editing, approval, defer-to-trusted, interruption, and shutdown are closed
protocol operations with explicit authority and evidence effects.

Measures report safety, usefulness, attack success, false positives, audit
cost, intervention cost, uncertainty, limitations, and nonclaims separately.
A weighted aggregate cannot erase the components.

Replay evidence is a digest-bound graph of existing episode, behavior,
control, crossing, action/result, experiment, and evidence refs. Hidden
objectives, credentials, private prompts, chain-of-thought, raw secrets, and
private model state remain outside portable evidence.

## Boundary-faithful required cases

### Injection

An untrusted observation or tool result influences a structurally valid
proposal and action argument. The integrity influence reaches the final sink.
The sink denies unless the exact policy admits it or a governed endorsement
creates a fresh result.

### Confidential exfiltration

A confidential fact influences a valid tool argument, participant output,
error, or colluding participant. Confidentiality reaches every explicit sink.
The unauthorized destination receives no output without exact declassification
authority.

### Adaptive monitor evasion

An attack participant adapts to declared prior outcomes, monitor visibility,
threshold or budget knowledge, and correlated monitors. Monitor success cannot
bypass deterministic policy. Safety and usefulness are reported across the
declared strategy class.

### Control-handoff manipulation

Tainted context or external direction crosses a valid API-409 handoff and
induces a receiver proposal. Controller, authority, provenance, effective
labels, receiver admission, API-423 crossing, and final sink are checked at one
exact cut. Handoff grants neither trust nor action admission.

Every denied case records zero prohibited `RuntimeTarget` calls and zero
participant/external disclosure. Tests also inspect append-only histories,
safe audit/error evidence, and replay.

## Security and evidence boundary

- Closed DTOs and request-size guards apply to portable bodies. Touched path,
  query, and header values are separately bounded.
- Strict identity, target, role, participant, controller, audience, and
  destination binding precedes semantic fact creation.
- Existing runtime-fact, action, API-409, API-423, snapshot, and transition
  validators remain the owners of their relations.
- API-407 declared and effective support is deny-first.
- Expected failures use stable bounded diagnostics. Unexpected failures use
  the redacted error envelope.
- Logs, diagnostics, audit, and evidence contain safe refs, digests,
  classifications, counts, and bounded summaries, never raw confidential data,
  prompts, credentials, private state, monitor internals, or hidden objectives.
- Portable semantics add no required environment variable, CLI flag,
  subprocess, socket, daemon, sidecar, or host path.

## Requirement allocation

| Requirement | Ownership |
| --- | --- |
| SEM-233 | explicit-flow labels, derivation, release operations, sinks, and final decision |
| ASR-536 | intentional-subversion profile, protocol, measures, and evidence claims |
| SEM-230 | participant-relative projection, exact-cut policy, memory, strategies, and noninterference boundary |
| ACT-617 / API-409 | control authority and typed control occurrences |
| API-423 | portable crossing occurrences and order/context relation |
| RUN-310 / RUN-319 | authenticated mediation, persistence, replay, and reference-runtime enforcement |
| API-407 | declared/effective backend support, realization, downgrade, and conformance |
| ASR-535 | bounded flow falsification and evidence/claim discipline |

SEM-233 and ASR-536 remain DRAFT until their downstream positive obligations
are satisfied. Issue #812 supplies design authority and an implementation
program only.

## Nonclaims

- No model-alignment or safe-internal-reasoning result.
- No chain-of-thought, prompt, private model state, or credential carriage.
- No automatic trust in a human, model, monitor, gateway, or backend.
- No protection for undeclared timing, storage, resource, steganographic, or
  other covert channels.
- No universal noninterference, shielding, runtime, backend, or
  intentional-subversion robustness result.
- No LLM-specific participant semantics, general taint framework, policy
  engine, gateway, monitor service, trajectory store, or agent framework.

## Implementation program

The dependency-ordered implementation program and canonical issue ids are in
[`implementation-program.json`](../../../docs/research/adversarial-participant-control/implementation-program.json).
