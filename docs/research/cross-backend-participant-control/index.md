# Mixed Cross-Backend Participant Control

Issue [#813](https://github.com/OpenRAE/rae/issues/813) defines how one
backend-neutral participant-control policy can be:

- realized alternatively in simulation or emulation/operation;
- composed across simulated and emulated/operational components in one trial;
  and
- varied across linked trials or a finite pre-admitted within-run phase
  schedule.

This delivery adopts the composition and evidence lessons from distributed
simulation, cyber ranges, co-simulation, LVC, and digital twins without adding
an HLA wire model, federation framework, or backend choice to SDL.

- [Architecture preflight](../../decisions/issue-813-cross-backend-participant-control-preflight.md)
- [ADR-102](../../decisions/adrs/adr-102-mixed-cross-backend-participant-control.md)
- [Prior art and design criteria](prior-art-and-design-criteria.md)
- [Current-state assessment](current-state-assessment.md)
- [Composition architecture](composition-architecture.md)
- [Demonstration protocol](demonstration-protocol.md)
- [Requirement disposition](requirement-disposition.md)
- [Implementation program](implementation-program.md)
- [Machine-readable program](implementation-program.json)
- [Formal SEM-234 and ASR-537 design](../../../specs/formal/participant-semantics/cross-backend-participant-control.md)

SEM-234 and ASR-537 are DRAFT. Issues #1013 through #1019 own the
dependency-ordered implementation and evidence program.

Issue #813 does not implement a mixed runtime, certify a backend, or report a
transfer or equivalence result. Revision 1 keeps exactly one acting controller
per participant and episode. Multiple realization providers are not multiple
controllers.
