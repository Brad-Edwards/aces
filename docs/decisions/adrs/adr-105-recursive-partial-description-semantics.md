# ADR-105: Recursive Partial Description Semantics

## Status

proposed

## Date

2026-09-05

## Classification

Classification: FM3
Required artifacts: decision record, typed finite reference model, algebraic
checks, explicit abstract transition system, counterexamples, acceptance matrix.
Waivers: No production schema, parser, compiler, backend or capture migration is
published by this design deliverable. Public syntax is not selected.

## Context

Issue [#1201](https://github.com/OpenRAE/rae/issues/1201), under SEM-218, asks
for a compositional semantic contract before implementation migrations.
Its 2026-09-05 governing intent is the binding design criterion: authors
constrain what matters, backends choose permitted realizations, and requested
reports describe the result at an honest depth and basis. Extensible catalogs
alone do not correct compulsory installation detail or unconditional evidence.

Existing SEM-218, SEM-219, ADR-012/033/034/064/066/070 and artifact/profile
contracts provide the owners. Current aggregate explicitness, specimen guards,
open-demand subsumption and descriptor-derived corroboration do not yet meet
all the new examples. Existing accepted specifications retain their meaning.

## Decision

Propose the [review-1 semantic contract](../../research/partial-description/semantics.md)
and its [executable evidence](../../research/partial-description/verification.md).
The rules there are normative **within this candidate design**, including the
governing intent; they are not assertions about current SDL behavior. Acceptance
of this ADR and migration of production contracts are distinct events.

1. Separate presence, constraints, knowledge, default selection, delegation,
   closure and lifecycle authority. Undefined contributes no local statement;
   unknown and redacted information grant no realization permission.
2. Apply an open scope recursively to unspecified descendants. Conjoin explicit
   constraints; a precise child never closes a sibling or loses its force.
   Optional presence is conditional satisfaction, not unconstrained presence.
3. Name the universe of every closed record or collection. Stable semantic
   identity governs matching; positional inventory order does not.
4. Reuse `runtime.software_components` as the owner of software presence and
   version refinement, retaining `runtime.packages` for explicit package
   coordinates. Acquisition and final repository state are separate refinements.
5. Preserve universal `subsumes(B, R)` as `R ⊆ B`. Delegated admission requires
   selection **and delivery** of a permitted supported witness under execution
   policy. One witness cannot establish a universal capability claim.
6. Let complete abstract transition/interaction models execute at their declared
   level. Do not require an invented concrete-machine description.
7. Keep realization reports, observation demand, collection, retention, export
   and operational inputs separate through ADR-064/066 owners. Apply prohibitions
   before collection, not only at the response boundary.
8. Introduce these changed meanings only at an explicitly negotiated revision.
   Review the compact model before selecting public syntax or migrating consumers.

## Alternatives Considered

- A larger product enum or extensible installation catalog still forces detail
  the author did not select and cannot satisfy the abstraction examples.
- Making every field optional loses required presence, conditional optional
  constraints and admission diagnostics.
- Replacing subsumption with overlap silently weakens universal claims.
- Collecting complete state and filtering reports violates collection prohibitions.
- A wholesale CUE migration is unnecessary. CUE's constraint lattice and local
  closure are useful precedents; RAE still owns authority and observation policy.
- An independent finite Python oracle makes the quantifier and composition
  examples inspectable without publishing another production relation engine.

## Consequences

The common authoring path can remain sparse while detailed refinements stay
binding. Private mechanisms need author profiles only when constrained or
exchanged with semantic claims. Existing owners avoid a third software inventory
or a new evidence plane.

The cost is explicit revision negotiation and preservation of recursive
constraints across compiler, admission and observation boundaries. A finite
oracle checks only its declared worlds and transitions; passing it cannot prove
production integration, backend capability, independent observation or general
solver completeness. The acceptance matrix states these limits.

The PR review is the review record for the proposal and executable evidence.
This ADR stays proposed until maintainer ratification; no accepted ADR pin or
published schema is changed by merely adding it.
