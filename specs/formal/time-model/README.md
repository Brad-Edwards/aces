# ACES Shared Time Model

This specification defines the semantic authority implemented for SEM-227,
SEM-228, SEM-229, DSL-126, DSL-127, DSL-128, RUN-317, and RUN-318.

## Authority Boundary

The SDL owns authored temporal meaning. The processor owns canonical compiled
identities. The runtime owns lifecycle control and observation. A backend may
realize those semantics only through the portable capability and conformance
contracts defined by API-421/ASR-528. Experiment records preserve the realized
model under EXP-734.

Neither host timestamps, backend scheduler order, transport receipt order, nor
map iteration order is semantic time.

## Domains And Coordinates

A time domain is:

```text
D = (kind, tick-period, epoch, visibility)
```

`tick-period` is a reduced positive rational number of SI seconds. A coordinate
on a clock is superdense:

```text
T = (segment, tick, microstep)
```

Within one segment, lexicographic `(tick, microstep)` order is meaningful under
the clock's declared monotonicity. Coordinates from different domains are
incomparable unless an explicit admitted mapping connects them.

An affine rational mapping is:

```text
target_tick = source_tick * numerator / denominator + offset_ticks
```

The exact result may be fractional. Consumers must not round it silently.

## Clocks

A clock binds one domain to one authority and declares:

- authority kind and reference;
- monotonicity;
- pause support;
- reset support; and
- jump support.

A jump is a discontinuity. It creates a new segment even when the numeric tick
moves forward. A reset or replay also creates a new segment. Prior records
remain append-only.

## Progression

Progression policy is independent from the domain:

- `real_time`: semantic ticks are paced against an apparatus clock;
- `dilated`: the declared exact ratio relates semantic and pacing progress;
- `stepped`: each accepted advance has the declared quantum;
- `event_driven`: progress follows admitted events and microsteps;
- `externally_paced`: another declared authority grants progress.

Synchronization is separately declared as none, authority-following, barrier,
or conservative. Drift is a bounded claim, not prose. Pacing does not establish
ordering or causality.

## Temporal Constraints

The first closed constraint family is:

- precedence over exactly two ordinary ACES subjects;
- duration;
- window;
- deadline; and
- cadence.

Constraints resolve one clock. Causality is intentionally absent: causal claims
remain governed by participant attribution and its evidence basis.

## Runtime State Machine

For each compiled clock:

```text
uninitialized -> running
running -> running      (advance or jump)
running -> paused
paused -> running
running|paused -> running in new segment (reset or replay)
```

Every transition has a monotonically increasing sequence and records previous
and resulting coordinates. `advance` cannot move a paused clock. A stepped
clock accepts only its exact step. Unsupported lifecycle operations fail before
state mutation.

## Invariants

1. Every clock resolves exactly one domain.
2. Every progression policy resolves exactly one clock.
3. A clock has at most one effective progression policy.
4. Mapping endpoints resolve and the authored mapping graph is acyclic.
5. Domain conversion without a mapping is invalid.
6. Semantic movement uses exact integers and rationals.
7. A discontinuity creates a new segment and does not rewrite history.
8. Equal timestamp values do not prove simultaneity or causality.
9. Temporal subject references resolve through ordinary SDL declarations.
10. Runtime control does not prove backend capability or native realization.

## Compatibility

SEM-213 participant temporal contracts remain valid. A follow-on migration may
replace their legacy inline `time_domain` and `clock_authority` strings with
references to this shared model while retaining action-specific event points
and state-machine semantics. The migration must be explicit and cannot infer a
shared clock from matching strings.

## Implementation Map

| Concern | Authority |
| --- | --- |
| SDL declarations | `aces_sdl.time_model` |
| Cross-reference validation | `aces_sdl.validator._time_model` |
| Compilation | `aces_processor.compiler.time_model` |
| Compiled identity | `aces_processor.models.time_model` |
| Runtime lifecycle | `aces_runtime.time_coordinator` |
| Focused evidence | `test_sem_227_shared_time_model.py` |
| Portable declaration contracts | `aces_contracts.contracts.time_model` |
| Backend capability and admission | `aces_backend_protocols.time_capabilities`, `aces_backend_protocols.capability_admission` |
| Runtime protocol and validated readback | `aces_backend_protocols.protocols.TimeRuntime`, `aces_runtime.time_control.RuntimeTimeControlMixin`, `aces_runtime.manager.RuntimeManager` |
| Semantic conformance | `aces_conformance.time_semantics` |
| Run provenance | `aces_contracts.contracts.experiment_run` |
| Focused portable-contract evidence | `test_api_421_time_contracts.py` |
