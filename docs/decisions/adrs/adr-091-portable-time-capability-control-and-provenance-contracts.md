# ADR-091: Portable Time Capability, Control, And Provenance Contracts

## Status

accepted

## Date

2026-07-24

## Classification

Classification: FM3

Required artifacts: authority-boundary decision, formal invariants, published
contracts, capability admission, runtime control/readback, semantic
conformance, experiment provenance, negative tests, and traceability.

Waivers: none.

## Context

ADR-090 defines shared time semantics in SDL and the reference runtime, but
explicitly does not let that implementation prove backend support. Portable
materialization needs a contract that tells a backend what it must realize, a
closed declaration of what the backend can support, observable runtime state,
and run evidence that compares the declared and realized model.

Without that boundary, scenario packs would need private scheduler and control
semantics, or ACES would infer capability from implementation presence. Both
would violate ADR-012 and make an independently developed backend impossible
to admit and compare against a golden range.

## Decision

### 1. Publish three portable contracts

`time-model-v1` is the canonical backend-neutral projection of compiled SDL.
`time-runtime-state-v1` carries typed clock readback and append-only transition
history. `realized-time-model-v1` records run-scoped realization and apparatus
provenance.

### 2. Require closed backend capability admission

`backend-manifest-v2` gains an optional time capability. A backend that claims
it declares supported domain, authority, progression, synchronization,
mapping, constraint, reset, and replay terms, finite limits where applicable,
and support for controls, exact mappings, append-only history, and run
provenance. Planning fails closed when any required term is absent.

### 3. Make control and readback runtime responsibilities

The runtime protocol provides initialize, advance, pause, resume, jump, reset,
and state operations. The runtime manager validates every successful readback
against the admitted declaration and rejects transition-history rewriting.

The protocol says what control and observation mean. A backend owns how those
operations are materialized.

### 4. Join claims in conformance

A time conformance claim requires all of:

- an admitted backend capability;
- a canonical declaration;
- typed runtime state bound to the declaration digest; and
- realized run provenance bound to the run and declaration.

No single artifact proves conformance by itself.

### 5. Preserve experiment and scenario boundaries

`experiment-run-v1` gains additive realized-time provenance. SDL and scenario
metadata need no pack-specific extension beyond the shared model. Historical
files remain initial service state, and deterministic benign activity remains
ordinary green-participant behavior governed by the shared clock.

### 6. Define golden comparison at the portable boundary

An independently implemented backend is comparable to a golden range when it
materializes, controls, and exposes the required portable state and behavior.
Provider, host layout, scheduler implementation, and topology identity are not
equivalence criteria unless the scenario explicitly makes them observable.

## Consequences

- Scenario packs can require time behavior without defining private control
  APIs.
- Backends can reject unsupported time models before provisioning.
- Runtime and experiment evidence expose drift, limits, deviations, and clock
  history without elevating backend implementation details into SDL.
- Existing backends remain valid without a time capability but cannot admit a
  scenario that requires the shared model.

## Rejected Alternatives

- Infer support from a backend implementing similarly named methods.
- Treat a reference coordinator as proof of native backend support.
- Put scheduler or live-activity control semantics in a scenario pack.
- Require golden and backend deployments to share provider or topology.
- Model historical content as a first-class time concept.
