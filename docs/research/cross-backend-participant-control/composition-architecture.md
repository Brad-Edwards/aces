# Mixed Cross-Backend Participant-Control Composition Architecture

Date: 2026-07-31

Status: design authority for SEM-234. No contract or runtime implementation.

## 1. Authority layers

The design uses one one-way authority chain:

```text
portable authored scenario and participant policy
  -> experiment realization-profile selection
  -> deterministic allocation/topology/phase admission
  -> ordinary SDL instantiation and semantic admission
  -> exact participant control and crossing cut
  -> selected realization provider and adapter
  -> external effect or participant disclosure
  -> observed apparatus, histories, conformance, and run evidence
```

No later layer rewrites an earlier artifact. Apparatus cannot change SDL
meaning. Runtime cannot change admitted allocation. Evidence cannot authorize
what happened.

## 2. Composition profile

The profile identity is:

```text
mixed-cross-backend-participant-control-v1@rev1
```

It supports two modes.

### Alternative realization

The same scenario/policy digest is admitted separately for:

- simulation; or
- emulation/operation.

Each run has its own plan entry, run id, apparatus, allocation, realized time,
loss, and evidence. A comparison may relate them. They are not one run.

### Simultaneous mixed realization

One admitted trial pins two or more apparatus components. At least one
component is simulated and at least one is emulated/operational for the
mandatory ASR-537 case.

The profile does not require all components to share one runtime technology.
It requires every edge to be explicit.

## 3. Allocation

### Allocation units

Revision 1 is a closed union:

| Unit | Meaning |
| --- | --- |
| participant runtime | Realize the participant implementation/control loop |
| controlled scope | Realize the governed assets/resources under an authority scope |
| action family | Translate and execute one governed action-contract family |
| observation source | Produce one governed observation/source family |
| crossing boundary | Realize transport/translation for one directed boundary |

These are stable compiled refs. They are not arbitrary paths, filters, Python
callbacks, backend commands, or runtime labels.

### Allocation invariants

Let:

- \(U\) be all required allocation units in the instantiated scenario;
- \(C\) be the admitted apparatus components;
- \(A \subseteq U \times C\) be allocation;
- \(G\) be an optional closed arbitration profile; and
- \(\operatorname{eligible}(u,c)\) be API-407 effective support plus
  realization-envelope admission.

Revision 1 requires:

1. **Completeness**:
   \[
   \forall u \in U,\ \exists c \in C : (u,c) \in A
   \]
2. **Eligibility**:
   \[
   (u,c) \in A \Rightarrow \operatorname{eligible}(u,c)
   \]
3. **No unexplained overlap**:
   \[
   (u,c_1),(u,c_2) \in A \land c_1 \ne c_2
   \Rightarrow G \text{ resolves realization responsibility}
   \]
4. **No implicit fallback**: a failed provider does not select another member
   of \(C\) unless a future admitted failover profile names that transition.
5. **Stable identity**: component and unit refs do not depend on worker,
   schedule, host, backend availability, or phase outcome.

Revision 1 does not publish a failover or arbitration profile. Overlap is
therefore rejected unless the two entries cover different non-overlapping
subscopes under an incumbent authority.

## 4. Topology and edges

### Topology classes

- **single-component**: one realization provider;
- **integrated**: components share one coordinator/runtime boundary;
- **unified**: components expose one governed external composition surface;
- **federated/bridged**: independent runtime domains exchange through explicit
  bridges; and
- **nested**: one admitted component is itself a closed composition.

The class describes structure. It does not establish compatibility or trust.

### Edge contract sketch

Future #1014 contracts should represent:

```text
composition edge
  identity + revision
  source component + destination component
  allocated crossing scope
  adapter/bridge identity + manifest
  portable action/observation refs
  transformation/mapping profile
  participant/audience policy ref
  release/declassification basis
  source and destination clock refs
  cross-clock/order mapping
  required API-407 features and strengths
  mapping loss and limitations
  failure/retry/partial-delivery behavior
  evidence/provenance expectations
```

The edge references API-423 occurrence history. It does not duplicate request,
decision, release, delivery, observation, or audit carriers.

### Nested composition

A nested component exposes:

- one admitted component identity and digest;
- its externally visible allocation units;
- its edge/time/policy capabilities;
- its internal-composition evidence ref; and
- limitations.

The parent profile cannot infer internal authority or hide an unproven loss.
An unresolved nested profile is unsupported.

## 5. Control and ownership

### Acting control

For one participant \(p\), episode \(e\), and order cut \(o\):

```text
controller(p,e,o) = exactly one active controller
```

The existing authority basis, controlled scope, policy revision, state
revision, validity interval, idempotency, and history heads remain binding.

### Realization responsibility

For allocation unit \(u\):

```text
provider(u, phase, cut) = one admitted apparatus component
```

`provider` determines which component may attempt realization after admission.
It does not grant the acting controller authority or change the action
contract.

### HLA ownership

An HLA adapter may expose an object/attribute ownership state:

```text
unowned | owned(component) | transfer-pending | transfer-failed
```

That state is evidence about mutation responsibility. The runtime still joins
it with:

- current acting controller;
- current authority scope;
- action admission;
- allocation;
- API-407 support;
- exact policy/time/order cut; and
- atomic commit.

Ownership acquisition cannot authorize an otherwise denied action.

### Transfer protocol

The design-level states are:

```text
requested
  -> offered
  -> pending
  -> committed

requested | offered | pending
  -> failed | expired | cancelled | stale
```

The request records pull/push initiator, desired scope, prior owner/provider,
candidate, controller/authority cut, clock/order, capability, and evidence.
Only `committed` changes effective responsibility. A stale transition has no
effect.

### Deferred authority profiles

Revision 1 rejects:

- lease: validity windows lack lease identity, renewal, expiry, and fencing;
- simultaneous scoped controllers: one controller state cannot carry distinct
  concurrent owners;
- joint/fused control: a list lacks quorum, priority, arbitration, unanimity,
  conflict, and failure rules; and
- oscillation tolerance: repeated valid transfers can still livelock.

These require a later version. They are not hidden inside an extension map.

## 6. Information distribution and security

### Order of operations

```text
authenticate caller and bind target
  -> resolve participant/controller/audience
  -> resolve allocation and component manifests
  -> resolve exact policy/state/order cut
  -> authorize and project through SEM-230/API-423
  -> validate mapping and effective capability
  -> prepare occurrence/history/evidence
  -> atomically commit decision
  -> invoke adapter or serialize disclosure
  -> append result/readback/failure
```

Any failed gate before effect produces no prohibited backend call or
disclosure.

### Bridge trust boundary

The adapter/bridge is untrusted with respect to portable meaning. It may:

- transform representations;
- narrow delivery;
- pace or buffer messages;
- serialize events;
- expose metadata;
- fail partially; and
- return backend-native diagnostics.

It cannot:

- invent participant/action/observation identities;
- widen a participant projection;
- select a different provider;
- reinterpret controller authority;
- silently discard loss;
- convert failed delivery into observation; or
- persist policy/evidence in a side store.

Backend exceptions pass the existing sanitization boundary. Secrets, policy
bodies, hidden observations, payloads, host paths, private ids, and credentials
do not enter portable artifacts, argv, environment dumps, logs, or errors.

### Metadata projection

Each participant and auditor profile decides which of these are visible:

- membership and join/leave;
- subscription/class;
- region and destination;
- size and cadence;
- synchronization/time request/grant;
- ownership/responsibility transfer;
- retraction; and
- failure/timeout.

An audit audience may retain more than the participant. That does not imply
participant disclosure.

## 7. Time and order

For every component \(c\), record:

- clock identity and authority;
- time domain and unit;
- pacing/dilation;
- regulating/constrained role;
- advancement and grant service;
- lookahead;
- receive/timestamp/serialized order;
- rollback/replay behavior; and
- runtime readback.

For edge \(c_i \to c_j\), an admitted mapping is:

```text
M_ij:
  source clock/domain
  destination clock/domain
  mapping kind and revision
  monotonicity/order guarantees
  uncertainty/precision
  buffering/lookahead
  failure and unmapped behavior
  evidence
```

If \(M_{ij}\) is absent, cross-clock order is partial/unknown. If only
timestamps exist, support is `disclosed_weak`.

The exact staleness predicate includes:

```text
controller
authority basis and scope
capability result
policy revision
state revision
history heads
governed order
```

Wall-clock age may be an additional constraint. It cannot replace these
coordinates.

## 8. Trial and phase semantics

### Inter-trial change

A progression such as:

```text
emulation data collection
  -> derived simulator generation
  -> simulated training
  -> emulation evaluation
```

uses distinct entries/runs. Each derived artifact records its source data,
model/profile, version, generator, unknown transitions, and digest. A new run
can link to the prior one without reusing its identity.

### Within-run phase schedule

Let \(P = [p_0,\dots,p_n]\) be a finite admitted phase sequence. Each phase
records:

- active component set;
- allocation;
- edge set;
- controller/authority expectation;
- clock/order mappings;
- policy and release expectations;
- entry and exit predicates;
- maximum progress bound;
- failure disposition; and
- evidence.

All referenced components and mappings are pinned in the sealed plan. A
transition appends:

```text
prior phase
next phase
trigger and order cut
prior and next active membership
controller/authority/policy/time cuts
commit result
loss and evidence
```

It does not rewrite the plan/run id, prior histories, or participant knowledge.
If transition admission or commit fails, the next phase has no effects.

## 9. Open/closed axes

### Control loop

- **open-loop**: observe, replay, or evaluate without external actuation;
- **closed-loop**: participant output may reach an external effect after all
  ordinary control, admission, capability, policy, time, and commit gates.

Closed-loop is not authority.

### World assumption

- **closed-world**: unknown entities/actions/observations/mappings are absent
  or invalid under the profile;
- **bounded-open-world**: unknowns may exist, but portable action and
  observation vocabularies remain closed and unknown mappings are unsupported.

Bounded-open-world is not permissive fallback.

### Federation membership

- **fixed**: active membership does not change;
- **pre-admitted dynamic**: active membership follows the finite phase
  schedule.

Dynamic is not arbitrary late join.

## 10. Evidence architecture

The run evidence graph reuses existing carriers:

```text
scenario/policy/plan/run identities
  -> component and adapter manifests
  -> allocation/topology/phase profile
  -> capability and conformance
  -> control/crossing/time histories
  -> raw observations and backend readback
  -> mapping loss and limitations
  -> derived conformance/transfer/readiness measures
  -> behavioral claim bindings and nonclaims
```

Required provenance includes:

- scenario and policy digests;
- trial coordinate, plan entry, and run id;
- participant implementation, processor, backend, bridge, and host identities;
- component allocation and topology;
- model/data/seed/random-stream identity;
- time mapping and realized order;
- capability and conformance profile;
- transformations and losses;
- software/source revisions;
- raw and derived evidence;
- uncertainty and limitations; and
- reproduction identity/result.

## 11. Failure taxonomy

The design reuses existing diagnostics and dispositions. Downstream contracts
need stable cases for:

- missing or unknown profile/revision;
- duplicate or unresolved component/scope;
- incomplete or overlapping allocation;
- incompatible apparatus;
- unsupported capability;
- failed or false conformance;
- missing policy/authority;
- stale controller/state/history cut;
- unmapped clock/order;
- invalid phase transition;
- failed atomic commit;
- backend/bridge failure;
- partial delivery;
- observation mismatch;
- mapping loss beyond admitted bounds; and
- evidence/provenance incompleteness.

No case causes implicit fallback.

## 12. Extensibility seam

A future backend adds:

- a manifest and adapter identity;
- supported realization forms and allocation units;
- edge mapping profiles;
- time/order capabilities;
- policy projection behavior;
- loss/failure declarations; and
- conformance evidence.

It does not change SDL or add branches throughout the runtime.

A future controller-composition profile can add lease or joint authority by
versioning the authority subprofile. It does not change mixed realization
allocation or pretend provider multiplicity already supplied that semantics.
