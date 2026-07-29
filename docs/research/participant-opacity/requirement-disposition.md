# Participant Opacity Requirement Disposition

Date: 2026-07-29

Parent issue: [#810](https://github.com/RAESystem/rae/issues/810)

Requirement allocation was completed before the implementation child issues
were created. This prevents delivery tasks from inventing requirement scope
after the fact.

| Requirement | Status | Disposition | Allocated scope |
| --- | --- | --- | --- |
| `SEM-230` | ACTIVE | reuse | Policy noninterference, exact-cut policy/release, adaptive low strategies, memory, observation projection, scheduler/environment, and order coordinates remain canonical. |
| `SEM-231` | DRAFT | new | One-sided participant-relative predicate opacity, possible-point and information-cell semantics, supervisor visibility, closed relation profiles, exact relation boundaries, and independent assurance states. |
| `ASR-535` | ACTIVE | reuse | Bounded falsification, model-check/proof evidence discipline, adversarial cases, safe counterexamples, relation claim bindings, and backend conformance. |
| `RUN-319` | ACTIVE | reuse | Any future fail-closed reference-runtime mediation, append-only decisions/evidence, and declared limitations for supported opacity profiles. |
| `API-407` | ACTIVE | reuse | Backend feature strength, required contracts, limitations, declaration, native realization, and evidence for named opacity profiles. |

`SEM-231` was created in Ground Control as a `DRAFT` requirement before child
issues #961 through #965. The child issues document it, and each reuses the
incumbent assurance/runtime/backend requirement appropriate to its bounded
outcome.

## Child Allocation

| Issue | Bounded outcome | Requirements | Prerequisites |
| --- | --- | --- | --- |
| [#961](https://github.com/RAESystem/rae/issues/961) | closed profiles and bounded falsification | `SEM-231`, `ASR-535` | #810 |
| [#962](https://github.com/RAESystem/rae/issues/962) | finite-state model checking | `SEM-231`, `ASR-535` | #810, #961 |
| [#963](https://github.com/RAESystem/rae/issues/963) | mathematical proof | `SEM-231`, `ASR-535` | #810, #961, #962 |
| [#964](https://github.com/RAESystem/rae/issues/964) | reference-runtime enforcement | `SEM-231`, `RUN-319` | #810, #961 |
| [#965](https://github.com/RAESystem/rae/issues/965) | backend declaration, realization, and bounded conformance | `SEM-231`, `API-407`, `ASR-535` | #810, #961, #962, #964 |

The dependency graph is acyclic. Definition precedes every implementation
lane; the profile/checker foundation precedes model checking, proof, runtime,
and backend work; backend conformance follows both the finite model and runtime
boundary.

## Explicit Nonclaims

Requirement allocation is not evidence of satisfaction. `SEM-231` remains
`DRAFT`. Issue #810 provides definition and bounded design tests only; it does
not satisfy or activate the downstream model-check, proof, runtime, backend, or
conformance outcomes.
