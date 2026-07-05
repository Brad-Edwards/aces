# ADR-070: Realization Envelope Semantics

## Status

proposed

## Date

2026-07-04

## Classification

Classification: FM2
Required artifacts: ADR, prior-art/design-criteria note, formal invariant list,
changelog fragment
Waivers: No schema, fixture, contract-source, implementation, runtime behavior,
or conformance-runner artifact is introduced by issue #667. The executable
membership/subsumption helper, backend-manifest schema evolution, witness-based
conformance probes, and replacement of the #663 `reference_scenario` bridge are
downstream implementation work tracked by the blocked subsumption/conformance
issues, including #668.

## Context

ACES currently has two related but incomplete surfaces.

- SEM-218, defined in
  `specs/formal/realization/explicitness-and-realization.md`,
  classifies authored realization concerns as exact, constrained, or open and
  requires backend manifests to disclose coarse `realization_support`.
- Target conformance accepts `run_target_conformance(reference_scenario=...)`
  as an issue #663 bridge so fixed-topology or simulation backends are not
  failed solely because they cannot realize one hard-coded generic Linux VM
  scenario.

What ACES lacks is the set expression both sides need:

- an author can say "run this over this family of acceptable scenario
  instances";
- a backend can say "this is the family of scenario instances I can realize";
- conformance can ask whether the request is inside the backend's family and
  can derive an in-envelope witness without carrying a global default
  scenario.

The prior-art note
[`docs/research/realization-envelope/prior-art-and-design-criteria.md`](../../research/realization-envelope/prior-art-and-design-criteria.md)
reviews CUE, Dhall, JSON Schema closure, CEL/Rego admission patterns,
FMI/OGC capability declarations, and decidable SMT fragments. The common lesson
is that ACES needs a small, typed, bounded, portable expression language with a
known set relation. It should not become a second manifest language, an
arbitrary policy callback, or a solver-dependent DSL.

## Decision

Adopt a **realization envelope** as a versioned SDL semantic expression that
describes a set of scenario instances. The same expression model is used in both
directions:

- authored SDL uses it to describe acceptable variation in a scenario family;
- backend declarations use it to describe realizability.

The normative formal boundary is
`specs/formal/realization/envelope-semantics.md`.

### 1. The envelope is one SDL semantics extension

The envelope expression extends SDL semantics. It is not a new backend-manifest
capability language and not a new experiment-run-set model.

An envelope has:

- a versioned expression identity;
- typed domain descriptors based on the SDL variable model;
- scoped posture overlays for field, node, topology, app, and scenario scopes;
- closure rules that say whether unspecified values or children are allowed;
- provenance and optional digest fields when carried by or referenced from a
  manifest.

Existing surfaces remain distinct:

- `realization_support` is a coarse capability/disclosure floor;
- backend profiles remain conformance profile selectors;
- semantic profiles remain concept-binding authorities;
- experiment-core run sets record what was executed, not what could be
  realized.

### 2. Membership, subsumption, and witness generation are one relation

The implementation seam is a pure semantic helper over the versioned envelope
contract:

- `member(instance, envelope)` decides whether one concrete scenario instance is
  inside the envelope.
- `subsumes(offered, requested)` decides whether every scenario in the requested
  envelope is in the backend-offered envelope. Equivalently, the requested set
  is a subset of the offered set.
- `witness(envelope, policy, seed)` deterministically derives one concrete
  in-envelope scenario instance and then runs normal SDL structural and semantic
  validation on it.

Witness generation is not evidence of subsumption by itself. It is only the
concrete instance conformance can execute after the set relation has passed.

### 3. The admitted fragment is intentionally small

The portable fragment admits:

- exact singleton values;
- finite enum/value sets;
- booleans;
- bounded numeric intervals with inclusive/exclusive endpoints;
- governed references to controlled vocabularies or scenario registries;
- acyclic record/product structure;
- scoped closed-world extra-key rejection.

The fragment excludes arbitrary Python predicates, backend callbacks, external
queries, unbounded regex or SMT fragments, recursion, unbounded quantification,
non-linear arithmetic, and expressions that depend on hidden backend state.

This keeps membership and subsumption reducible to local domain subset checks
plus structural closure checks, and keeps witness generation deterministic.

### 4. Scope and closure are explicit

Posture applies at one of five scopes: field, node, topology, app, or scenario.
Most-specific-wins selects the effective posture for a concrete field or child
scope, but a more-specific posture may not silently widen a closed enclosing
scope. Equal-specificity conflicts are diagnostics, not merge order.

Open means the expression leaves the value to a downstream realizer at a point
the SDL semantics declares realizable. Constrained means the value must fall
inside a typed domain. Exact means the domain is a singleton. Closed-world
scope means no unspecified realizable dimensions under that scope are portable
members of the set.

### 5. Backend manifest carriage is a schema-evolution question

Current `backend-manifest-v2` can disclose coarse support through
`realization_support`. It cannot express value-level sets, scoped closure, or a
portable subsumption relation.

The selected carriage direction is a future manifest evolution that can either:

- embed a small envelope expression directly; or
- reference a published envelope artifact by contract id, digest, and version.

Both modes use the same expression contract. Neither overloads the current
`constraints: dict[str, str]` prose map as the final semantics.

### 6. Closed envelopes require negative conformance

For a closed envelope, conformance must not stop after one in-envelope witness.
It must also derive out-of-envelope probes for closed dimensions that can be
varied safely and require the backend to refuse them through the ordinary
`OperationStatus` / `Diagnostic` envelope without mutating state.

Negative conformance is the falsification surface for honesty: a backend that
declares "only this set" must prove refusal for requests outside that set, not
merely accept one allowed instance.

### 7. Sensitive values stay out of public artifacts

Envelope ids, refs, digests, domain kinds, scope paths, and bounded summaries
may appear in manifests, diagnostics, witnesses, fixtures, and conformance
reports. Credentials, bearer tokens, private keys, process argv, host paths,
backend-native ids, raw backend object representations, hidden truth, scoring
state, and full tracebacks must not.

## Alternatives Considered

### A separate backend-manifest capability language

Rejected. It would require authors and backends to reason in two languages and
would make conformance a translation problem instead of a set-relation problem.
It also risks forking validators, schemas, and diagnostics away from the SDL
semantic authority.

### Reuse only existing `realization_support` fields

Rejected. The existing fields declare support modes and kind strings. They do
not carry value domains, scope closure, typed variables, membership,
subsumption, or witness generation.

### Arbitrary policy predicates

Rejected. CEL/Rego-style admission languages are useful precedent, but ACES
needs a portable structural set expression, not a backend callback or
user-authored program. Arbitrary predicates would make decidability, witness
generation, negative conformance, and safe diagnostics harder to guarantee.

### Keep the #663 `reference_scenario` bridge

Rejected as the final design. The parameter is a useful temporary bridge, but it
requires a caller to supply the witness and does not prove the requested set is
within the backend's realizable set.

## Consequences

### Positive

- Authors and backend implementers share one semantic model for scenario sets.
- Target conformance has a principled replacement for the hard-coded/default
  reference scenario path.
- Closed-world backend claims become falsifiable through generated negative
  probes.
- Future schema and implementation work has a clear seam: versioned envelope
  expression plus pure relation helper.

### Negative

- Backend manifest evolution is required before the design can replace #663 in
  executable conformance.
- The admitted fragment is deliberately conservative; some expressive
  constraints will need governed domain extensions rather than arbitrary
  predicates.
- Implementers must keep experiment-run variation separate from realizability
  variation, which is an additional documentation and validation burden.

### Risks

- If later work widens the expression language without preserving decidability,
  subsumption and witness generation may stop being reliable CI gates.
- If negative probes echo concrete sensitive values, conformance could leak
  backend-private or author-private data. The formal spec requires diagnostics
  to name paths, refs, and kinds rather than raw values.
- If manifest carriage embeds large envelopes directly, manifests could become
  noisy and hard to review. The reference-by-contract-id/digest mode exists to
  keep large envelopes governed as separate published artifacts.
