# ADR-087: Enterprise Identity and Deployment-Tenancy Authoring

## Status

accepted

## Date

2026-07-24

## Classification

Classification: FM2

Required artifacts: an explicit invariant list, pure finite-graph analyzers,
composition and instantiation differential tests, negative compatibility tests,
published schema parity, and admission tests.

Waivers: no model checker is required. The authored forest, cell, placement,
and shared-state graphs are finite and scenario-local; exhaustive graph passes
and property-oriented tests cover their invariants.

## Context

ADR-082 governs authored identity domains, controller roles, membership, and
domain-bound accounts. ADR-032 separately governs observed runtime identity
inventory. Neither surface can state that domains form a forest, identify the
root, distinguish a workforce IdP facade, classify endpoint function, preserve
logical nodes placed on carrier hosts, group nodes into tenant-owned isolation
cells, or state shared-service tenant/authentication/state/reset policy.

Encoding those facts as generic relationship properties, node login roles,
runtime inventory, descriptions, or provider configuration would leave
portable intent unvalidated and create competing authorities.

## Decision

1. SDL adds keyed `identity_forests` declarations. Each forest explicitly
   references one root domain and its complete non-empty domain membership.
   Existing `identity_domains` remain the only domain declarations. No root or
   membership is inferred.
2. SDL adds keyed `identity_facades` declarations. A facade references one
   existing named VM service and a closed exposed protocol. It is authored
   identity intent, not observed `runtime.identity_authorities`.
3. Forest trust and directory federation use specialized relationship types
   and closed typed details. Relationship endpoints own authority identity.
   Federation carries only direction, portable protocol, mapping intent, and
   facade ownership of a named server-controlled tenant claim. Credentials,
   claim values, mapper documents, and provider ids are unrepresentable.
4. `Node.endpoint_persona` is a closed VM-only scenario-function
   classification. It does not alter node login roles, participant identity,
   accounts, authorization, or inferred topology.
5. Keyed `deployment_tenants` own portable tenant identity. Keyed
   `deployment_cells` bind exactly one tenant, explicit VM membership, and a
   default-deny cross-tenant posture. A node belongs to at most one cell; when
   cells are authored, every VM belongs to exactly one.
6. Specialized carrier-placement relationships preserve source and carrier
   node identity and declare a closed kernel boundary. Placement is
   single-carrier, same-cell, non-self, non-nested, acyclic, and targets a VM
   with the carrier persona. It does not imply namespace sharing.
7. Specialized shared-service relationships connect one deployment tenant to
   one existing named VM service and independently declare tenant isolation,
   workload authentication, mutable-state references/owner, and reset-
   generation owner.
8. Cross-tenant shared-service use requires a tenant-safe isolation mode and
   tenant-scoped workload identity. Mutable state reuses
   `persistent_volumes`; ownership must agree with consumers, cannot conflict
   across bindings, and reset ownership follows state ownership.
9. One pure enterprise-identity analyzer and one pure deployment-tenancy
   analyzer own graph agreement. Thin semantic-validator adapters render their
   issues. Module composition rewrites every new reference through the
   canonical symbol maps, and instantiated admission reruns all invariants.
10. Existing scenario phase schemas publish the authored graph together. The
    compiler preserves the canonical instantiated scenario, node specs, and
    typed relationship metadata. This decision adds no provider-policy plan
    resource, capability claim, backend realization, or evidence that the
    declared state occurred.

## Alternatives Considered

### Use generic relationship properties

Rejected. Free-form properties cannot provide closed detail/type agreement,
reference ownership, or a portable compatibility matrix.

### Treat a domain as a forest

Rejected. Domain and forest identity differ even in a one-domain forest, and
an inferred root becomes ambiguous as soon as a second domain is added.

### Reuse node roles or runtime identity inventory

Rejected. Node roles authorize local logins and runtime inventory records
observed state. Neither owns endpoint business function or authored
federation authority.

### Put cells and shared-service policy in provider configuration

Rejected. Provider allocation remains operational configuration, but tenant,
cell, placement, and shared-state isolation intent are portable scenario facts
that must compose and validate before a provider is selected.

### Add plan resources for every authored policy declaration

Rejected. Carriage is already preserved by the canonical instantiated graph.
A plan resource would falsely imply realization authority and duplicate the
scenario graph.

## Consequences

### Positive

- Enterprise identity and fleet tenancy are explicit, portable, and
  composition-safe.
- Logical node and service identities survive host packing.
- Shared-service isolation, authentication, state, and reset ownership cannot
  collapse into an ambiguous boolean.
- Existing SDL remains compatible when the optional surfaces are absent.

### Negative

- Authors opting into forests or deployment cells must provide complete
  memberships.
- New enum terms require coordinated vocabulary, schema, documentation, and
  semantic review.
- Provider realization and operational proof remain separate work.

### Limits

The authored graph proves declared intent only. It does not prove directory
bootstrap, trust establishment, federation, endpoint login, cell isolation,
carrier kernel boundaries, workload authentication, state partitioning, or
reset behavior.
