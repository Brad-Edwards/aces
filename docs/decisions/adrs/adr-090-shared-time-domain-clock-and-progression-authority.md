# ADR-090: Shared Time-Domain, Clock, And Progression Authority

## Status

accepted

## Date

2026-07-24

## Classification

Classification: FM3

Required artifacts: primary-source research note, authority-boundary decision,
formal invariants, executable SDL/compiler/runtime slice, negative tests,
schema publication, lineage, and requirement traceability.

Waivers: none.

## Context

ACES has participant-local temporal contracts, event ordering evidence,
experiment clock descriptions, backend time-management disclosures, and
operational timestamps. None is a general shared authority. The missing model
causes opaque clock strings, incomparable timestamps, backend-local pacing, and
private scheduling concepts such as the rejected live-activity clock.

The [research note](../../research/time-model/prior-art-and-design-criteria.md)
reviews ROS 2, FMI, HLA, TENA, and OpenSCENARIO. The normative algebra and
runtime invariants are in the [formal time-model specification](../../../specs/formal/time-model/README.md).

## Decision

### 1. Add one shared authored model

SDL gains governed maps for `time_domains`, `clocks`,
`time_domain_mappings`, `time_progression_policies`, and
`temporal_constraints`. They participate in ordinary composition,
instantiation, canonicalization, and declaration governance.

### 2. Use exact superdense time

Resolution and scale are reduced positive rationals. Runtime values are integer
ticks with non-negative microsteps. Float time is not semantic authority.

### 3. Require explicit authority and conversion

Every semantic clock resolves one domain and one authority. Distinct domains
are incomparable without an explicit exact mapping. No backend, participant,
or evaluator may infer conversion from equal units or nearby timestamps.

### 4. Separate progression concerns

Advancement mode, pacing ratio, synchronization mode, drift bound, pause,
reset, and replay are distinct declarations. Support for one does not imply the
others.

### 5. Keep ordering and causality distinct

Temporal constraints govern precedence, duration, windows, deadlines, and
cadence. They do not establish causality. Causality remains an
evidence-supported attribution claim under ADR-022.

### 6. Make lifecycle discontinuities observable

Jump, reset, and replay create a new temporal segment and append a transition.
They never rewrite earlier readings. Runtime advancement, pause, resume, reset,
and replay fail before mutation when the compiled policy does not permit them.

### 7. Preserve plane boundaries

SDL describes WHAT temporal behavior is required. A backend describes and
proves HOW it realizes and controls that behavior. The reference coordinator
demonstrates semantics but does not establish backend capability.

Host UTC timestamps and watchdogs remain operational apparatus. Historical
files remain ordinary initial service state. Benign activity remains ordinary
participant behavior. Neither becomes a special time ontology.

## Consequences

- Backend portability can be assessed against explicit time requirements.
- Golden and backend ranges can compare observed temporal behavior without
  requiring identical topology, scheduler, or provider.
- Existing participant temporal contracts require a deliberate reference
  migration rather than string matching.
- API-421, ASR-528, and EXP-734 must publish capability, conformance, and
  realized-run contracts before a backend may claim native support.

## Rejected Alternatives

- A universal timestamp.
- Floating-point semantic time.
- Backend-local scheduler authority.
- A live-activity-specific scheduler or clock.
- Timestamp-derived causality.
- Treating archived or historical content as a time-domain declaration.
