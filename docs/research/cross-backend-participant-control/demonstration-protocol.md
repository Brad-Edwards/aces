# Cross-Backend Participant-Control Demonstration Protocol

Date: 2026-07-31

Protocol: `cross-backend-participant-control-demonstration-v1@rev1`

Status: ASR-537 design. The protocol has not been executed.

## Purpose

The protocol determines whether one revision-pinned participant-control policy
can be realized, with stated losses, in:

- pure simulation;
- pure emulation/operation;
- simultaneous mixed composition;
- linked trial-stage changes; and
- finite pre-admitted within-run phases.

It is falsification-first. A rejected or weakened composition is a valid
result. The protocol cannot report broad parity by discarding mismatches.

## Fixed identities

Every lane pins:

- authored scenario identity, version, source digest, and canonical snapshot;
- participant-control policy/profile id, revision, and digest;
- participant, controller, authority, action, observation, inject, and
  crossing refs;
- experiment task/protocol/study ids;
- plan, plan entry, logical coordinate, run id, and replicate;
- processor, participant implementation, backend, adapter/bridge, host, and
  measurement-apparatus manifests and digests;
- allocation, topology, composition edges, and phase schedule;
- clock/time/order profiles and mappings;
- capability declarations, effective support, conformance profile, and probe
  identities;
- models, datasets, generators, random-stream profile, namespace, seed, and
  draw provenance;
- transformation/mapping profiles, losses, uncertainty, and limitations; and
- source revision, evidence bundle, and reproduction identity.

The same authored scenario and participant-control policy digest is mandatory
for the pure and mixed comparison lanes. Backend-translated inputs are derived
artifacts, not replacement authored identities.

## Apparatus lanes

### Lane S — pure simulation

Use one simulated cyber-agent environment behind a RAES adapter. A CybORG-like
or CyberBattleSim-like apparatus is acceptable if the exact API, action,
observation, time, and fidelity limits are recorded.

Lane S establishes only bounded simulated realization and conformance.

### Lane E — pure emulation or operation

Use one emulation/operational `RuntimeTarget`. The adapter maps the same
portable action and observation refs to operational procedures and readback.

Lane E establishes only the observed operational path. A deterministic stub
does not count as native operation and must be labeled separately.

### Lane M — simultaneous mixed

Use one admitted trial containing at least:

- one simulated component; and
- one emulated/operational component.

The components interact across at least one explicit composition edge. The
edge binds policy, mapping, time/order, support, failure, and evidence.

Lane M is not satisfied by running Lane S and Lane E separately.

### Lane T — linked trial transition

Run a revision-pinned progression such as:

```text
E data collection -> derived S model -> S training -> E evaluation
```

Every step is a new admitted plan entry/run with source lineage. Record unknown
transitions and model/data coverage.

### Lane P — pre-admitted phase transition

Use one run with a finite phase schedule whose components and mappings are
fully pinned before execution. Demonstrate one activation/deactivation
boundary and its atomic evidence.

## Control-loop cases

### Open-loop

Observe or replay state without an admitted external action. Assert:

- the participant receives only the authorized view;
- evidence collection does not grant action authority;
- no operational backend call occurs; and
- audit-only facts remain outside participant disclosure.

### Closed-loop

Allow a participant proposal to reach an external effect only after:

- caller/target/controller binding;
- authority and action admission;
- exact policy and state cut;
- allocation and edge resolution;
- effective capability and mapping validation;
- time/order admission; and
- atomic commit.

Remove any gate in a mutation case. The effect must disappear.

## Positive case matrix

| Case | Required result | Bound |
| --- | --- | --- |
| Pure simulation | Action, observation, control, inject, order, and evidence path realized or explicitly weakened | Lane S apparatus |
| Pure emulation/operation | Same portable refs mapped to operational procedures/readback or rejected | Lane E apparatus |
| Simultaneous mixed | One admitted edge carries an authorized action/observation between S and E components | Lane M topology |
| Inter-trial transition | New run identity and complete derivation/transfer provenance | Lane T sequence |
| Pre-admitted phase | Atomic membership/allocation change with unchanged run identity and append-only history | Lane P schedule |
| Open-loop | Observation/evidence without action authority or effect | Named participant/audience |
| Closed-loop | Commit-before-effect under every independent gate | Named action/sink |

A “positive” case may be `disclosed_weak` when the policy permits that strength.
It cannot be silently normalized to `exact`.

## Mandatory adversarial cases

### 1. Stale handoff

Resolve an approval under controller revision \(r\). Commit a handoff to
\(r+1\). Attempt the approved action.

Required result:

- stale denial;
- zero backend calls or disclosures;
- unchanged effect state;
- append-only stale occurrence and audit evidence.

### 2. Concurrent intervention

Race two controller/intervention writes at one state/history cut.

Required result:

- one commit or both denied;
- never two effective acting controllers;
- no duplicate effect;
- exact CAS/idempotency evidence.

### 3. Unsupported or false capability

Require a mixed service that is absent or falsely declared.

Required result:

- admission denial or failed conformance;
- zero prohibited effect;
- declaration, effective strength, missing evidence, and failure retained
  separately.

### 4. Timestamp-only or unmapped order

Supply wall-clock timestamps without an admitted clock/order mapping.

Required result:

- exact-order claim rejected;
- `disclosed_weak` or partial/unknown relation;
- no timestamp-as-causality statement.

### 5. Simulation-only observation

Expose an observation field in Lane S that Lane E cannot produce.

Required result:

- mismatch and source apparatus recorded;
- no parity or transfer success for behavior depending on that field;
- participant projections remain independently validated.

### 6. Unrealizable action

Admit an abstract action in Lane S whose transformed operational procedure is
unsupported or invalid.

Required result:

- fresh validation/admission rejects the transformed proposal;
- zero operational effect;
- mapping loss and diagnostic retained.

### 7. Directed-delivery failure

Address an inject to a participant through a bridge that misroutes, drops, or
cannot deliver it.

Required result:

- request and delivery-attempt evidence;
- failed delivery;
- no observation;
- no invented participant history entry.

### 8. Prior-delivery retraction

Deliver a value, then conceal or retract it under a later policy/phase.

Required result:

- retraction appended;
- original delivery and possible participant knowledge retained;
- no history deletion or retroactive noninterference claim.

### 9. Bridge-metadata leakage

Filter payload content while varying membership, destination, size, timing,
synchronization, ownership, or failure metadata with a protected fact.

Required result:

- bounded leakage finding or a separately justified projection;
- no payload-filtering-as-IFC claim.

## Additional failure cases

Run at least:

- unknown profile or revision;
- missing component/manifest;
- duplicate or overlapping allocation;
- unresolved controlled scope/action/observation ref;
- incompatible realization envelope;
- missing policy or declassification basis;
- cross-clock mapping cycle or ambiguity;
- unadmitted late join;
- phase trigger outside the admitted order;
- failed phase-transition commit;
- bridge partial delivery;
- adapter exception sanitization;
- evidence digest mismatch; and
- reproduction drift.

## Measurements

Report measures independently:

- action admission and realization disposition;
- observation field availability and transformation loss;
- delivery and observation success;
- handoff/phase transition outcome;
- exact, bounded, weak, or unsupported capability;
- logical-order coverage and unknown/partial relations;
- bridge latency and buffering only under the named clock mapping;
- mapping-loss count and severity;
- transfer task outcome;
- conformance pass/fail by case;
- zero-effect violations;
- uncertainty;
- run and reproduction cost; and
- missing evidence.

Do not collapse these into one score that hides a failed security or authority
case.

## Claim rules

### Bounded conformance

May be reported only for the exact manifest, adapter, profile, probes, and run
evidence. It says the tested obligations passed. It says nothing about
untested behavior.

### Interoperability readiness

May report whether sufficient engineering evidence exists to assess
integration risk. It does not report actual interoperability.

### Empirical sim-to-em transfer

May report the population, training/evaluation protocol, trials, measures,
uncertainty, model/data identity, and observed result. It is not universal
transfer.

### Trace inclusion or bisimulation

Requires the corresponding complete carrier, projection, relation profile, and
proof/model-check evidence. Finite demonstration traces cannot establish it.

### IFC/noninterference

Requires the exact policy, observer, strategy, memory, release, scheduler,
time/order, and hyperproperty boundary. Routing/filtering results cannot
establish it.

### Backend equivalence

Requires an independently governed relation and evidence. A common adapter,
two successful runs, or a passing mixed case is insufficient.

## Evidence bundle

Reuse existing experiment and associated-artifact carriers. The bundle
contains or references:

- admitted plan and instantiated snapshot;
- component/adapter manifests and effective capabilities;
- allocation/topology/phase profile;
- policy, control, crossing, delivery, observation, and time histories;
- backend readback and conformance reports;
- raw participant/evaluator/auditor evidence under separate projections;
- transformations, loss, limitations, and sanitized diagnostics;
- models/data/seeds/random-stream records;
- derived measures and relation-specific claims;
- environment/source/tool versions;
- cleanup and isolated-state evidence; and
- reproduction record.

Raw secrets, credentials, hidden answers, policy bodies, chain-of-thought,
private backend payloads, host paths, native ids, environment dumps, argv, and
unsanitized stderr are excluded.

## Reproduction

A reproduction:

- resolves the same revision-pinned sources and profiles;
- independently validates every portable artifact;
- uses a new explicit run/replicate identity;
- recomputes digests and derived measures;
- records deviations in apparatus, timing, mapping, or evidence; and
- does not reuse an unreviewed producer result directory.

An identical seed is not exact replay by itself.

## Exit criteria

ASR-537 remains DRAFT until:

1. #1013 through #1017 provide accepted semantic, contract, trial, runtime,
   and backend authorities;
2. every mandatory lane and adversarial case has a disposition;
3. denied cases have zero prohibited effects;
4. every result has complete apparatus/provenance binding;
5. at least one mismatch or weakening is retained rather than normalized;
6. relation claims remain separated;
7. reproduction evidence exists; and
8. #1019 reconciles the exact claims and residual gaps.
