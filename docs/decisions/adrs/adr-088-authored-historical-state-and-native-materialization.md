# ADR-088: Authored Historical State and Native Materialization

## Status

accepted

## Date

2026-07-24

## Classification

Classification: FM2

Required artifacts: an explicit invariant list, pure finite-graph analysis,
composition and instantiation differential tests, deterministic-address
collision tests, published schema parity, and compiler-preservation tests.

Waivers: no model checker is required. Historical event, object, relationship,
materialization, and readback graphs are finite and scenario-local; exhaustive
graph passes and property-oriented tests cover their invariants.

## Context

Scenario authors need coherent pre-existing enterprise history across native
products. Existing SDL content, orchestration events, participant histories,
runtime inventory, experiment baselines, and reconciliation snapshots have
different owners and cannot serve as an authored historical authority.

Product exports, native identifiers, adapter options, credentials, and raw
corpus bodies would make authored meaning provider-specific and unsafe.
Inferring time or causality from product timestamps or materialization order
would also make identity and lifecycle nondeterministic.

ADR-087 already owns deployment tenants, cells, shared-service mutable state,
and reset-generation ownership. Historical state must bind to that contract
rather than create another tenancy or reset lifecycle.

## Decision

1. SDL adds one keyed, closed `historical_baselines` section. A baseline owns
   its version, actor bindings, semantic objects, logical events, historical
   relationship refs, provider-neutral materialization bindings, and
   participant-equivalent readback requirements.
2. Actor bindings classify one baseline-local role while identity resolves to
   an existing entity, agent, account, or named node service. Exercise roles
   and product authorization are not reinterpreted.
3. Semantic object identity is the baseline-local object key and kind. Labels,
   content, timestamps, product names, native ids, adapter choices, and event
   order never contribute to that identity.
4. Historical object links reuse top-level `Relationship` declarations with
   the `historical_object_link` type and closed typed detail. Both endpoints
   are distinct objects in one owning baseline. Free-form relationship
   properties cannot carry historical semantics.
5. Events use a finite unique logical order coordinate. Predecessor and causal
   refs are separate same-baseline graphs; both are acyclic and point
   backward. Object creation, mutation, deletion, governed restoration,
   linkage, and single-writer authority are checked as one lifecycle.
6. Every semantic object has exactly one provider-neutral materialization
   binding to an existing named service and a versioned interface profile.
   Bindings declare explicit ordering and readback requirements but add no
   provider adapter, endpoint, command, credential, native id, plan resource,
   or realization claim. Backend manifests declare exact supported historical
   interface profiles and object kinds in a dedicated optional capability
   block; this declaration does not replace exact SEM-218 realization support.
7. Baseline and binding tenant and cell must agree. The baseline names the
   range-level reset lifecycle authority, while every materialization binding
   names an ADR-087 `uses_shared_service` relationship from that tenant to its
   exact native target service. This permits one causal baseline to span real
   products without weakening per-product reset ownership. A reset generation
   is an address isolation input, not a reset controller.
8. Readback requirements reuse existing observed-state `Proposition`,
   `Assertion`, evidence, and participant observation-boundary semantics. A
   readback assertion must name the exact semantic object. Unsupported or
   unknown remains distinct from success.
9. Semantic addresses use the
   `aces-historical-semantic-address/v1` profile. RFC 8785 canonical bytes over
   the exact profile, range instance, deployment tenant, reset generation,
   baseline id/version, and local object id are hashed with the distinct
   `aces-authored-historical-state|semantic-address|v1` domain. Duplicate
   coordinates, canonical bytes, and digest collisions fail the whole batch.
   The complete admitted baseline also receives an
   `aces-historical-baseline-digest/v1` identity over its id and full typed
   payload under the separate
   `aces-authored-historical-state|baseline-digest|v1` domain.
10. The compiler preserves the admitted instantiated baseline graph on
    `RuntimeModel.realization_instance` and emits typed baseline-digest and
    semantic-address maps. It does not create historical provisioning,
    orchestration, or evaluation resources.
11. Baseline metadata is bounded and inert. Historical objects may reference
    ordinary SDL `Content`, but inline historical corpus bodies, executable
    material, private keys, credential literals, and credential-bearing URIs
    fail semantic admission.
12. Module composition namespaces the baseline and all nested declaration
    addresses, rewrites external and canonical nested refs through the central
    symbol maps, and reruns all invariants after instantiation.

## Alternatives Considered

### Treat content or runtime inventory as historical authority

Rejected. Content carries staged scenario data and runtime inventory records
observed product state; neither owns authored versioned history.

### Add product-specific bootstrap blocks

Rejected. Native ids, endpoints, commands, exports, and option maps would make
portable meaning depend on one adapter and would bypass existing realization
and evidence boundaries.

### Add another edge, predicate, or lifecycle system

Rejected. `Relationship`, `Proposition`/`Assertion`, ADR-087 ownership, and the
existing semantic-validator pattern already own those concerns.

### Compile one plan resource per historical object

Rejected. Metadata carriage is not an executable operation. A future native
materializer must enter the existing resolved-resource and plan lifecycle only
when an executable adapter contract exists.

## Consequences

### Positive

- Authored history has one portable authority and deterministic identity.
- Causality, lifecycle, tenancy, reset, native-interface, and readback
  inconsistencies fail before provider selection.
- Module composition and instantiation preserve nested historical identity.
- Runtime compilation carries intent without overstating realization support.

### Negative

- Authors must provide complete event, ownership, materialization, and readback
  graphs for every historical object.
- New object, interface, and projection families require coordinated closed
  vocabulary, schema, validator, capability, and readback work.
- Provider adapters and native correlation evidence remain separate work.

### Limits

An admitted or compiled historical baseline proves authored intent and
deterministic semantic addressing only. It does not prove native object
creation, product timestamps, native causality, participant visibility,
successful reset, adapter correctness, or cross-backend equivalence.

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-07-24 | #859 | Separated range-level baseline reset authority from per-binding native reset ownership so one causal baseline can span multiple real product services while every binding remains tenant-bound to its exact target. |
