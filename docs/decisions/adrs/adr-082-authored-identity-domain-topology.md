# ADR-082: Authored Identity-Domain Topology

## Status

accepted

## Date

2026-07-13

## Classification

Classification: FM2

Required artifacts: an explicit invariant list, a typed normalized compiler
projection, property-oriented semantic tests, cross-stage differential tests,
and admission/readback failure tests.

Waivers: no model checker is required. The topology is a finite, scenario-local
graph whose invariants are exhaustively checked by a pure analyzer and replayed
over the compiled provisioning plan.

## Context

ADR-032 defines observed directory and domain identity inventory under a
node's runtime state. That evidence can report what exists, but it cannot tell a
provisioner what domain to create, which nodes are controllers, or which
controller candidates a member may join. Inferring those facts from operating
systems, account names, SPNs, or observed inventory would make realization
backend-specific and non-reproducible.

Domain-backed scenario realization therefore needs a separate authored
topology with enough information to validate, compile, order, admit, and verify
the requested state without handling credentials or embedding provider
configuration.

## Decision

1. SDL gains a scenario-scoped `identity_domains` map. Its initial closed
   profile is `active_directory`, with a DNS name, NetBIOS name, and an explicit
   authority account reference. This is realization intent, not runtime
   observation.
2. Controller roles and membership are typed relationship edges:
   `domain_controller_for` carries `domain_controller`, while `joins_domain`
   carries `domain_join.controller_refs`. Controller candidates are explicit,
   ordered, non-empty, and unique. Generic relationship properties and node
   flags are not topology authority.
3. A domain-scoped account carries `domain_ref`. An SPN requires that explicit
   binding. The domain authority account is declared separately by the domain;
   no account name, username, or SPN is interpreted as an implicit domain.
4. One pure name-level analyzer owns topology consistency. The semantic
   validator renders its issues, and the compiler consumes its normalized node
   and account bindings. The initial Active Directory profile enforces these
   invariants:

   - every declared domain has at least one VM controller;
   - relationship type and typed detail agree;
   - duplicate controller and join facts are rejected;
   - a node cannot join a domain it controls or belong to multiple Active
     Directory domains;
   - each member's controller candidates control that same domain;
   - the authority account is placed on one of the domain's controllers;
   - every domain-bound account is placed on a node in that domain; and
   - every SPN-bearing account has an explicit domain binding.
5. Compilation emits a `DomainTopologyBinding` on each participating node and
   domain-bound account. It contains the normalized domain identity, profile,
   authority account address, node role, and canonical controller addresses.
   Those bindings are topology context and exact readback carriers; they are
   not executable controller-bootstrap instructions.
6. Each `domain_controller_for` node/domain fact additionally compiles to one
   `domain-controller-placement` provisioning resource. The placement targets
   the controller node and reuses that node's `DomainTopologyBinding`; it does
   not introduce a second domain payload. The placement is the sole portable
   instruction to establish that controller role. It orders after its target
   node, while member-node realization and every account placement bound to the
   same domain order after the domain's controller placements. The logical
   authority-account address never becomes a bootstrap dependency.
7. Provisioner capability truth uses the governed
   `supported_domain_profiles` dimension. Account creation and SPN support do
   not imply controller or join realization support.
8. A shared plan analyzer checks resources, non-delete operations, and admitted
   snapshot state. It runs in normal planning and at direct control-plane
   admission before backend validation. Backends may add stricter checks but
   cannot weaken this graph contract.
9. Each compiled topology carrier, including the controller placement, is an
   exact SEM-218 `domain-topology`
   realization requirement. Runtime snapshot readback must preserve the whole
   normalized binding; omission or approximation is a backend-contract error.
10. This decision does not define directory installation, DNS service setup,
   credential distribution, trust forests, group policy, or a provider-specific
   domain API. Those require separate profiles and capability declarations.

## Alternatives Considered

### Infer topology from accounts, SPNs, or Windows nodes

Rejected. The same inventory can represent a standalone host, a member, or a
controller, and inference would make validation and replay ambiguous.

### Store controller and membership flags on nodes

Rejected. Flags cannot express a typed target domain, ordered controller
candidates, or relationship-level provenance without parallel ad hoc fields.

### Reuse observed runtime directory identity

Rejected. It would collapse author intent and observed evidence, contradicting
ADR-032 and weakening SEM-218 non-approximation checks.

### Treat domain realization as an account feature

Rejected. Creating an account or preserving an SPN is materially weaker than
creating a domain controller or joining a machine to a domain.

## Consequences

### Positive

- Domain-backed realization is explicit, portable, and deterministic.
- Controller topology becomes actionable without treating node existence or an
  account placement as controller bootstrap.
- Semantic validation, compilation, planning, direct admission, and readback
  share one normalized graph contract.
- Backends fail closed when they do not claim the requested domain profile.
- Observed runtime identity remains an independent evidence surface.

### Negative

- Scenario authors must declare controller and join edges explicitly.
- Backend manifests and realization envelopes gain another governed capability
  dimension.
- Additional domain profiles will require explicit invariants, compiler
  projection rules, and backend conformance evidence.

### Limits

The topology proves declared intent and carrier consistency; it does not prove
that a guest successfully promoted a controller or completed a domain join.
That operational claim requires backend or guest evidence under a separately
defined realization mechanism.

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-07-24 | #845 | Distinguished topology/readback bindings from an actionable domain-controller placement and fixed controller-before-member/account lifecycle ordering. |
