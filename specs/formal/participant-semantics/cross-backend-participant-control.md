# Mixed Cross-Backend Participant-Control Composition

Requirements: SEM-234 and ASR-537.

Status: DRAFT design.

Issue: #813.

This specification composes existing scenario-family, experiment/trial,
participant-control, crossing, time, backend-capability, and evidence
authorities. It defines no wire contract or positive runtime/backend claim.

## 1. Domains

Let:

- \(S\) be an admitted backend-neutral instantiated scenario;
- \(P\) be its participants;
- \(E\) be participant episodes;
- \(U\) be stable compiled allocation units;
- \(C\) be admitted apparatus components;
- \(F\) be realization forms;
- \(A \subseteq U \times C\) be allocation;
- \(T = (C,X)\) be a directed composition topology with edges \(X\);
- \(\Phi = [\phi_0,\dots,\phi_n]\) be an optional finite phase schedule;
- \(K\) be the exact participant-control and crossing state cut;
- \(M\) be admitted cross-clock/order mappings;
- \(Q\) be the participant/audience policy and projection state;
- \(B\) be API-407 effective backend support;
- \(L\) be explicit mapping losses and limitations; and
- \(V\) be evidence and provenance.

Realization forms are:

```text
simulation
emulation-or-operational
hardware-or-native
federated-composition
```

Composition modes are:

```text
alternative-realization
simultaneous-mixed-realization
```

Allocation units are:

```text
participant-runtime
controlled-scope
action-family
observation-source
crossing-boundary
```

No backend name, adapter type, host, worker, or schedule position is an
allocation-unit identity.

## 2. Authority decomposition

For participant \(p\), episode \(e\), and cut \(K\), define:

- \(\operatorname{controller}(p,e,K)\): one effective acting controller;
- \(\operatorname{authority}(p,e,K)\): authority basis and controlled scope;
- \(\operatorname{admit}(a,K)\): action-admission relation;
- \(\operatorname{provider}(u,\phi,K)\): admitted realization provider;
- \(\operatorname{owner}(o,\alpha,K)\): optional backend-native
  object/attribute responsibility;
- \(\operatorname{route}(x,K)\): delivery addressing/transport; and
- \(\operatorname{release}(v,p,q,K)\): participant/audience disclosure
  authority.

These relations are pairwise non-substitutable:

\[
\operatorname{owner} \not\Rightarrow \operatorname{controller}
\]

\[
\operatorname{provider} \not\Rightarrow \operatorname{admit}
\]

\[
\operatorname{route} \not\Rightarrow \operatorname{release}
\]

\[
\operatorname{controller} \not\Rightarrow \operatorname{owner}
\]

Revision 1 requires:

\[
|\operatorname{controller}(p,e,K)| = 1
\]

It defines no positive lease, simultaneous scoped-controller, joint, or fused
control relation.

## 3. Backend-neutral authoring

### MCB-001 — Portable scenario independence

Scenario identity and membership are independent of \(A\), \(T\), \(\Phi\),
component manifests, and backend availability.

### MCB-002 — Allocation authority

Allocation is experiment/trial intent compiled after deterministic scenario
composition and before runtime execution.

### MCB-003 — Stable allocation targets

Every \(u \in U\) resolves through the canonical compiled-address authority and
has the same meaning across admitted realizations.

### MCB-004 — No apparatus-created meaning

An apparatus component may realize or refuse \(u\). It cannot create a
participant, controlled scope, action family, observation source, or crossing
that is absent from \(S\).

## 4. Allocation

### MCB-005 — Completeness

Every required unit has an admitted provider:

\[
\forall u \in U_{\mathrm{required}},\
\exists c \in C : (u,c) \in A
\]

### MCB-006 — Effective eligibility

\[
(u,c) \in A
\Rightarrow
B(c,u) \geq \operatorname{requiredStrength}(u)
\]

where \(B\) includes declared support, effective support, required contracts,
realization-envelope membership, limitations, downgrade, and conformance
evidence.

### MCB-007 — Closed overlap

If two providers cover the same unit, an accepted revisioned arbitration or
failover profile must define selection and failure. Revision 1 supplies no such
profile, so unexplained overlap is invalid.

### MCB-008 — No runtime fallback

A failed or unavailable provider does not authorize another component.
Fallback outside \(A\) is rejection.

### MCB-009 — Schedule independence

Allocation identity and sealed plan bytes do not depend on host, worker,
thread, queue, batching, completion order, retry count, wall time, or backend
availability.

## 5. Composition topology

Topology class is one of:

```text
single-component
integrated
unified
federated-or-bridged
nested
```

For every edge \(x \in X\), require:

```text
source component
destination component
adapter or bridge
allocated crossing scope
authority
action or observation mapping
participant/audience policy
release or declassification basis
source and destination clocks
time/order mapping
required support strength
mapping loss
failure behavior
evidence
```

### MCB-010 — Edge totality

An exchange across components is admissible only when its edge fields resolve
to revision/digest-matched authority.

### MCB-011 — Directionality

An edge \(c_i \to c_j\) does not imply \(c_j \to c_i\). Bidirectional
interaction uses two directed edges or a closed bidirectional profile.

### MCB-012 — Nested disclosure

A nested component exposes its external allocation, edge/time/policy
capabilities, digest, internal-evidence ref, and limitations. Its internal
composition is not inferred by the parent.

## 6. Control and responsibility transfer

Transfer states are:

```text
requested
offered
pending
committed
failed
expired
cancelled
stale
```

### MCB-013 — Commit establishes responsibility

Requested, offered, or pending transfer does not alter effective provider or
controller state. Only an atomic revision-fenced `committed` occurrence does.

### MCB-014 — Pull/push provenance

Acquisition initiated by the candidate and transfer initiated by the current
provider retain different initiator/negotiation evidence even when both
converge on the same commit relation.

### MCB-015 — Stale transition safety

A controller, authority, policy, capability, state-revision, history-head, or
order mismatch yields `stale` and zero prohibited effects.

### MCB-016 — No authority laundering

Provider/owner transfer never changes participant identity, acting controller,
action authority, or disclosure authority by implication.

### MCB-017 — Oscillation is not progress

Repeated valid transfers require a bounded cooldown/retry or explicit
livelock/cycle disposition before any progress guarantee may be claimed.
Revision 1 makes no such guarantee.

## 7. Information distribution

### MCB-018 — Authorization before routing

SEM-230/API-423 projection and release are resolved before publish/subscribe,
DDM, bridge filtering, directed delivery, or serialization.

### MCB-019 — Filtering may only narrow

For authorized projection \(R\) and bridge filter \(D\):

\[
D(R) \subseteq R
\]

An adapter cannot add participant-visible information.

### MCB-020 — Delivery stages remain distinct

Addressing, request, decision, delivery attempt, delivery, observation, and
audit remain distinct occurrences. No earlier stage implies a later stage.

### MCB-021 — Metadata projection

The observer profile dispositions:

```text
membership
subscription or class
region or destination
message size and cadence
synchronization
ownership/responsibility change
retraction
differential failure
```

Payload filtering does not establish metadata noninterference.

### MCB-022 — Audit is a separate audience

Authorized audit retention does not add a participant observation.

## 8. Time and order

Each component records:

```text
clock identity and authority
time domain and unit
pacing or dilation
regulating or constrained role
advance request and grant behavior
lookahead
delivery order
serialization service
rollback or replay behavior
runtime readback
```

### MCB-023 — Cross-clock mapping

Every edge between different clock domains has an admitted mapping \(M_{ij}\).
Without one, the relation is partial/unknown.

### MCB-024 — Timestamp weakness

Timestamps without governed mapping/order/readback support only
`disclosed_weak`. They do not establish causality or exact order.

### MCB-025 — Backend serialization evidence

`backend_serialized` requires a named clock, serialization service, runtime
readback, and conformance evidence.

### MCB-026 — Staleness coordinates

Staleness is evaluated over:

```text
controller
authority
capability
policy revision
state revision
history heads
governed order
```

Wall-clock age can constrain but not replace those facts.

### MCB-027 — Knowledge is append-only

Rollback, replay, concealment, and retraction append occurrences. They do not
erase prior delivery or participant knowledge.

## 9. Trial and phase realization

### MCB-028 — Inter-trial change

A realization change between trials creates a new admitted plan entry and run
id with source lineage.

### MCB-029 — Derived model identity

An emulation-derived simulator records source dataset/traces, generator and
profile revisions, model digest, coverage, unknown transitions, and
limitations.

### MCB-030 — Finite within-run phases

\(\Phi\) is finite and sealed before execution. Every possible component,
allocation, edge, clock mapping, policy, authority expectation, transition,
progress bound, and failure behavior resolves before plan sealing.

### MCB-031 — Phase commit before effect

The transition from \(\phi_i\) to \(\phi_{i+1}\) commits its exact state cut
before the next phase can cause effects.

### MCB-032 — Phase history

A transition appends prior/next phase, trigger/order, membership,
allocation, controller/authority/policy/time cuts, commit result, loss, and
evidence.

### MCB-033 — Identity preservation

A phase change does not rewrite plan id, plan-entry id, run id, prior control
or crossing histories, prior delivery, or participant knowledge.

### MCB-034 — Unadmitted join

A component absent from the sealed possible-membership set cannot join.

## 10. Open and closed axes

### MCB-035 — Control-loop posture

`open-loop` permits observation/replay without external actuation.
`closed-loop` permits a candidate action to reach ordinary control, admission,
policy, capability, time/order, commit, and effect boundaries. The posture
does not grant authority.

### MCB-036 — World assumption

`closed-world` rejects unknown entities/actions/observations/mappings.
`bounded-open-world` acknowledges possible unknowns but keeps portable
vocabularies closed and treats unknown mappings as unsupported.

### MCB-037 — Federation membership

`fixed` keeps one active component set.
`pre-admitted-dynamic` follows \(\Phi\). No other dynamic membership is
admitted.

The three axes are independent.

## 11. Runtime effect boundary

### MCB-038 — Exact-cut resolution

Before any adapter call or disclosure, resolve:

```text
authenticated caller and target
participant, controller, and audience
authority and action admission
allocation and active phase
component and adapter manifests
effective capability
policy and release
clock/order mapping
state revision and history heads
mapping loss and evidence expectations
```

### MCB-039 — Commit before effect

The exact decision and predecessor histories commit atomically before the
effect or serialization.

### MCB-040 — Zero prohibited effects

Denial, stale cut, missing/unsupported mapping, failed admission, unsupported
capability, invalid phase, or failed commit produces:

```text
zero prohibited backend calls
zero participant/external disclosures
unchanged prohibited effect state
append-only safe failure evidence
```

### MCB-041 — Adapter distrust

Backend output is revalidated and mapped through safe diagnostics. Adapter
success cannot synthesize a portable success after a failed RAES gate.

## 12. Evidence and claims

ASR-537 evidence binds:

```text
scenario and policy digests
plan, entry, coordinate, run, and replicate
participant, controller, and authority
apparatus and adapter manifests
allocation, topology, edges, and phase schedule
clocks, mappings, and realized order
capability and conformance
models, datasets, generators, seeds, and random streams
transformations, loss, uncertainty, and limitations
raw evidence, derived measures, and reproduction
```

### MCB-042 — Pure and mixed cases

The protocol covers pure simulation, pure emulation/operation, simultaneous
mixed, inter-trial transition, and pre-admitted phase transition.

### MCB-043 — Open and closed loops

The protocol covers open-loop and closed-loop cases under the same profile
identities.

### MCB-044 — Mandatory mismatches

The protocol includes stale handoff, concurrent intervention, false/unsupported
capability, timestamp-only/unmapped order, simulation-only observation,
unrealizable action, directed-delivery failure, prior-delivery retraction, and
bridge-metadata leakage.

### MCB-045 — Claim separation

These claims remain distinct:

```text
bounded conformance
interoperability readiness
empirical sim-to-em transfer
trace inclusion
bisimulation
IFC or noninterference
backend equivalence
```

Evidence for one does not satisfy another without an explicit governed
relation and binding.

## 13. Nonclaims

This design does not establish:

- portable contract or runtime implementation;
- any backend-native realization;
- HLA, FMI, HELICS, EDL-FG, CybORG, CyGIL, CyberBattleSim, or digital-twin
  compatibility;
- distributed, leased, simultaneous scoped-owner, or joint/fused controller
  support;
- exact cross-clock order without admitted mappings;
- protection from undeclared covert channels;
- general interoperability;
- universal sim-to-em transfer;
- trace inclusion or bisimulation;
- IFC/noninterference; or
- cross-backend equivalence.
