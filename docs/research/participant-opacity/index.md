# Participant-Relative Opacity And Supervisor Observation Research

Issue: [#810](https://github.com/OpenRAE/rae/issues/810)

Purpose: establish the external primary-literature basis for participant-
relative opacity before architecture preflight, relation selection, formal
specification, or implementation planning. The review asks one narrow question:
what must RAES define so that an opacity claim has a precise observer,
information set, secret, supervisor-visibility model, time/order model, and
assurance scope?

This research record is not a proof that RAES is opaque and is not a runtime-
enforcement claim. The linked issue #963 artifacts separately prove the
abstract conditional theorem profile; they instantiate no RAES runtime,
deployment, participant, or backend.

## Contents

- [Architecture preflight](../../decisions/issue-810-participant-opacity-preflight.md)
- [Issue #961 bounded-falsification preflight](../../decisions/issue-961-participant-opacity-bounded-falsification-preflight.md)
- [Issue #962 finite-state model-check preflight](../../decisions/issue-962-participant-opacity-model-check-preflight.md)
- [Issue #963 mathematical-proof preflight](../../decisions/issue-963-participant-opacity-proof-preflight.md)
- [Issue #964 reference-runtime enforcement preflight](../../decisions/issue-964-participant-opacity-runtime-enforcement-preflight.md)
- [Issue #965 backend declaration, realization, and conformance preflight](../../decisions/issue-965-participant-opacity-backend-realization-preflight.md)
- [Isabelle/HOL theorem source](../../../specs/formal/participant-semantics/isabelle/Participant_Opacity.thy)
- [Checked proof evidence](../../../specs/formal/participant-semantics/participant-opacity-proof-evidence.json)
- [ADR-099](../../decisions/adrs/adr-099-participant-relative-predicate-opacity.md)
- [Prior art and design criteria](prior-art-and-design-criteria.md) — search
  method, primary and adjacent source findings, relation selection, formal
  kernel, comparison with incumbent relations, supervisor-observation
  profiles, and design criteria.
- [Current-state assessment](current-state-assessment.md)
- [Requirement disposition](requirement-disposition.md)
- [Implementation program](implementation-program.md)
- [Machine-readable implementation program](implementation-program.json)
- [Formal SEM-231 authority](../../../specs/formal/participant-semantics/participant-predicate-opacity.md)

```{toctree}
:hidden:

prior-art-and-design-criteria
current-state-assessment
requirement-disposition
implementation-program
```

## Standing Boundaries

- [ADR-081](../../decisions/adrs/adr-081-behavioral-relation-taxonomy-and-claim-discipline.md)
  owns relation identity and claim discipline.
- [ADR-085](../../decisions/adrs/adr-085-participant-information-flow-and-control.md)
  and
  [SEM-230](../../../specs/formal/participant-semantics/information-flow-control.md)
  own the incumbent participant information-flow model. Opacity must compose
  with them rather than silently redefine noninterference.
- Equal projected histories are a possible witness relation, not by themselves
  an opacity theorem.
- Runtime monitoring, finite falsification, finite-state model checking,
  mathematical proof, and backend realization are separate assurance facts.
- New child issues may not present this research record as implementation
  authority. Ground Control requirements remain the authority gate.
