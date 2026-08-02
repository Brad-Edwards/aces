# Adversarial participant control and boundary flow

Issue [#812](https://github.com/OpenRAE/rae/issues/812) adopts the
participant-neutral lessons from information-flow security and AI-control
research without adding an LLM-agent framework.

The parent delivery defines the threat model, architecture, DRAFT authority,
and implementation program. Issues #1001 and #1002 now publish the SEM-233
semantic authority and portable contract boundary. They do not claim runtime
or backend enforcement or a successful adversarial evaluation.

- [Architecture preflight](../../decisions/issue-812-adversarial-agent-control-preflight.md)
- [Issue #1001 SEM-233 semantic-authority preflight](../../decisions/issue-1001-sem-233-boundary-flow-semantics-preflight.md)
- [Issue #1002 SEM-233 portable-contract preflight](../../decisions/issue-1002-sem-233-portable-flow-control-contracts-preflight.md)
- [ADR-101](../../decisions/adrs/adr-101-adversarial-participant-flow-control.md)
- [Current-state and primary-source assessment](current-state-assessment.md)
- [Threat model](threat-model.md)
- [Trust and flow architecture](trust-flow-architecture.md)
- [Worked attack cases](attack-cases.md)
- [Requirement disposition](requirement-disposition.md)
- [Implementation program](implementation-program.md)
- [Machine-readable program](implementation-program.json)
- [Formal authority](../../../specs/formal/participant-semantics/adversarial-flow-control.md)

SEM-233 and ASR-536 remain DRAFT. The #1001 semantic and #1002 portable-
contract work is published; #1003, #1004, #1007, and #1008 retain the
dependency-ordered runtime, backend/apparatus, evaluation, and documentation
obligations.
