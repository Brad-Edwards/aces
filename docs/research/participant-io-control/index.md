# Participant Information-Flow And Control Adoption

Issue [#794](https://github.com/RAESystem/rae/issues/794) assesses and
designs the participant-control model. It is a design/program artifact, not an
implementation or proof claim.

- [Architecture preflight](../../decisions/issue-794-participant-io-control-preflight.md)
- [Current-state assessment](current-state-assessment.md)
- [ADR-085](../../decisions/adrs/adr-085-participant-information-flow-and-control.md)
- [Detailed adoption design](adoption-design.md)
- [Requirement disposition](requirement-disposition.md)
- [Ordered implementation program](adoption-program.md)
- [Machine-readable acceptance manifest](adoption-program.json)

```{toctree}
:hidden:

current-state-assessment
adoption-design
requirement-disposition
adoption-program
```

The decisive finding is that ACES has adjacent participant action,
observation, visibility, runtime, intervention, orchestration, backend, and
assurance mechanisms, but not yet one portable participant ingress/egress
policy and evidence boundary. The program composes those mechanisms without a
universal message DTO, gateway, second history, or inflated relation claim.
