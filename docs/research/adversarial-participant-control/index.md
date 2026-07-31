# Adversarial Participant Control and Boundary Flow

Issue [#812](https://github.com/OpenRAE/rae/issues/812) adopts the
participant-neutral lessons from information-flow security and AI-control
research without adding an LLM-agent framework.

This delivery defines the threat model, architecture, DRAFT authority, and
implementation program. It does not claim runtime or backend enforcement or a
successful adversarial evaluation.

- [Architecture preflight](../../decisions/issue-812-adversarial-agent-control-preflight.md)
- [ADR-101](../../decisions/adrs/adr-101-adversarial-participant-flow-control.md)
- [Current-state and primary-source assessment](current-state-assessment.md)
- [Threat model](threat-model.md)
- [Trust and flow architecture](trust-flow-architecture.md)
- [Worked attack cases](attack-cases.md)
- [Requirement disposition](requirement-disposition.md)
- [Implementation program](implementation-program.md)
- [Machine-readable program](implementation-program.json)
- [Formal authority](../../../specs/formal/participant-semantics/adversarial-flow-control.md)

SEM-233 and ASR-536 are DRAFT. Issues #1001, #1002, #1003, #1004, #1007,
and #1008 own the dependency-ordered delivery work.
