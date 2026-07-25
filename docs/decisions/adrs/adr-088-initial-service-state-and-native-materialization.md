# ADR-088: Initial Service State and Native Materialization

Issue: #859. Requirement: DSL-436.

## Status

accepted

## Date

2026-07-24

## Classification

Classification: FM2

Required artifacts: one concrete gap case, closed profile contracts, negative
admission tests, phase/schema parity, reset correlation, and run-provenance
contracts. Before a backend claims a standardized profile, that backend also
requires an operational native materializer, control-path conformance, and
participant-equivalent readback proof for the claimed profile.

Waivers: none. A schema, manifest declaration, fake adapter, or planned-state
echo cannot substitute for operational materialization and readback evidence.

## Context

Top-level `content` already owns authored files, directories, datasets, items,
and source references. It compiles through `ContentPlacement` into the existing
provisioning plan, and provisioner manifests already declare supported content
types. Scenario snapshots, variation bindings, random-stream controls,
stateful resources, deployment tenancy, reset ownership, propositions,
observation boundaries, evidence records, and experiment-run provenance own
their adjacent concerns.

The concrete gap is narrower: `Content.target` currently resolves only to a VM
node, and the reference materializer realizes content through node bootstrap.
That cannot express or prove exact insertion into a named service-owned store
such as a mailbox, application collection, or database through the service's
native interface. A content-type capability declaration also cannot prove that
the native object was created or that a participant can read the required
state.

Age, old timestamps, narrative history, and product event logs do not create a
new authored object family. A prior design added `historical_baselines`,
historical objects, actors, events, relationships, address profiles, and
lifecycle graphs. That parallel ontology duplicated existing content,
relationship, assertion, tenancy, and provenance authorities while still
lacking an operational native materializer. This decision rejects that design.

## Decision

1. Top-level `content` remains the only authored authority for initial files,
   datasets, messages, records, and comparable scenario data. SDL adds no
   `historical_baselines`, historical object, age, narrative-history, or
   product-event-history class.
2. Versioned content identity reuses the canonical `content.<id>` declaration
   address under the immutable instantiated-scenario snapshot identity. The
   canonical content payload digest distinguishes revisions. Externally staged
   bytes also require the existing immutable source or associated-artifact
   identity and digest rules. Product-native ids never participate.
3. Ordinary node content placement remains unchanged. Only content that cannot
   be realized by node placement may carry a closed service-target
   materialization requirement. It references one existing named service, one
   versioned provider-neutral interface profile, exact typed requirements, the
   governing ADR-087 shared-service/reset-ownership relationship when state is
   shared, ordering dependencies, and existing assertion/evidence/participant
   observation-boundary refs.
4. A standardized interface profile is a closed discriminated contract, not an
   arbitrary options map. It describes portable operation and readback
   semantics; it cannot contain vendor names, endpoints, commands, queries,
   table names, SDK types, credentials, environment variables, host paths, or
   native ids.
5. ACES may standardize a provider-neutral interface profile independently of
   any concrete backend so that scenario authors, validators, compilers, and
   runtimes share one portable control contract. Standardization does not
   declare backend support. Before a backend manifest claims the profile, that
   backend's conformance evidence must prove ownership-safe native
   materialization, control through the ACES runtime path, fresh native
   readback, projection through the declared participant observation boundary,
   and assertion/evidence satisfaction. Manifest support is necessary for
   scenario admission but is never proof of an execution result.
6. Compilation extends the existing content-placement path. Service-target
   requirements retain the canonical content identity, exact target service,
   profile/version, typed requirements, dependencies, tenancy/reset ownership,
   and readback refs through `RuntimeModel`, `PlannedResource`,
   `PlanOperation`, and `SnapshotEntry`. A second materialization plan,
   repository, lifecycle engine, or exception hierarchy is forbidden.
7. Admission composes the existing provisioner content capability check with a
   profile-specific capability declaration and SEM-218 exact-realization
   support. Missing profile, content-kind, exact requirement, target, reset
   ownership, or required observation support fails before backend I/O. No
   downgrade or first-supported-profile selection is permitted.
8. Successful execution produces a fresh `RealizationObservation` at the
   profile's required strength. The current snapshot/provenance carrier retains
   the admitted content identity and a safe evidence reference, not raw service
   data. `experiment-evidence-record-v1` retains the observed result, and
   `experiment-run-v1` retains the scenario snapshot, apparatus manifests,
   reset/run correlation, realized-form disclosure, and evidence traceability.
   Desired state, backend support, and observation remain distinct.
9. Reset ownership is reused from ADR-087. A reset re-executes the same admitted
   materialization contract under its run/reset correlation, records a fresh
   observation, and never adopts or deletes a native object by name alone.
   Participant episode reset, backend restart, volume lifecycle, and
   shared-service reset ownership remain separate concepts.
10. Deterministic generated content reuses variation bindings,
    `InstantiationProvenance`, random-stream profiles/addresses/draw records,
    and run stochastic controls. Interface profiles do not add seeds, clocks,
    implicit randomness, declaration-order selection, or provider-generated
    authored identity.
11. Composition, instantiation, the four scenario-containing published
    schemas, schema publication records, content capability vocabulary,
    lineage, reference catalogs, fixtures, conformance, examples, and tests
    move together. Schema validity alone is not semantic or operational
    conformance.
12. Backend and golden-range equivalence is observational, not structural.
    ACES does not require the delivery backend to reproduce the golden range's
    provider, product adapter, deployment topology, bootstrap mechanism, or
    native identifiers. It requires the backend to admit and control the same
    portable contracts and the realized scenario to satisfy the same declared
    participant-visible assertions and evidence requirements.

## Alternatives Considered

### Add an authored historical-state graph

Rejected. It violates the issue boundary, duplicates existing authorities, and
turns age or narrative history into a semantic object class without addressing
the actual service-target execution gap.

### Put product bootstrap payloads in content

Rejected. Vendor exports, native queries, commands, credentials, and provider
options would make SDL provider-specific and bypass exact capability,
secret-handling, and evidence gates.

### Treat a capability declaration or planned snapshot as proof

Rejected. A manifest describes apparatus support and a snapshot records desired
or admitted state. Neither is independent evidence that native state exists or
is participant-visible.

### Require a product adapter before defining the portable contract

Rejected. It would make ACES vocabulary depend on a favored backend and prevent
independent backend implementation. The portable profile defines what a
conformant backend must do; backend support remains a separately tested claim.

## Consequences

### Positive

- The change is confined to the demonstrated service-target gap.
- Content, tenancy, reset, assertion, evidence, and run-provenance authorities
  remain singular.
- Unsupported exact requirements fail closed before mutation.
- New service families can add evidence-backed profiles without changing
  content identity or creating a new topology.

### Negative

- A standardized profile can exist before any backend implements it, so tools
  must keep vocabulary support, backend capability support, and observed
  execution evidence visibly distinct.
- Existing content placement and manifest contracts need a narrow typed
  extension across every published phase.
- Reset/run evidence must retain correlation without persisting raw product
  content or native identifiers in portable state.

### Limits

An admitted materialization contract proves authored intent. A manifest proves
declared support. Only fresh evidence from the operational path can prove the
observed materialization result, and only the declared participant projection
can support participant-equivalent readback. Cross-backend equivalence is
limited to the declared portable contract and observable assertions; it does
not establish product history, native creation time, event-log authenticity,
provider identity, or implementation equivalence.

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-07-24 | #859 | Separated range-level baseline reset authority from per-binding native reset ownership so one causal baseline can span multiple real product services while every binding remains tenant-bound to its exact target. |
| 2026-07-24 | #862 | Replaced the historical-baseline ontology with the smallest content-owned, evidence-gated service-materialization extension required by the redesigned issue boundary. |
