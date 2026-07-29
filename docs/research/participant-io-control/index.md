# Participant Information-Flow And Control Adoption

Issue [#794](https://github.com/RAESystem/rae/issues/794) assesses and
designs the participant-control model. The ordered child work now delivers the
SEM-230 semantics, API-423 crossing contract, RUN-319 reference-runtime
boundary, API-407 capability declarations, ASR-535 bounded assurance, and
issue #802 migration evidence.

Start with the
[published participant-control guide](../../public/participant-control.md) for
role-specific authoring, participant-implementation, operations, backend, and
research guidance. The guide explains these artifacts; it is not semantic
authority.

## Adopted authority and delivery

- [ADR-085](../../decisions/adrs/adr-085-participant-information-flow-and-control.md)
  and the
  [SEM-230 formal specification](../../../specs/formal/participant-semantics/information-flow-control.md)
  own participant-relative world, view, history, crossing-operation, policy,
  and claim boundaries.
- The
  [API-423 schema](../../../contracts/schemas/participant-runtime/participant-crossing-occurrence-v1.json)
  and contextual validator own portable crossing facts.
- RUN-319 owns reference-runtime enforcement and append-only persistence.
- API-407 owns feature support, required contracts, and policy-authorized
  downgrade.
- ASR-535 owns finite participant-policy conformance evidence.
- The [migration guide](../../migration/participant-information-flow-control.md)
  owns legacy, opt-in, required, and rollback procedures.
- The
  [behavioral-relation catalog](../../../contracts/concept-authority/behavioral-relations-v1.json)
  owns relation identity, evidence boundaries, assurance state, and
  nonclaims.

The shipped reference backend declares all six participant-policy features
unsupported. Positive runtime paths use explicit test manifests and finite
evidence. RUN-319 does not currently emit API-423's distinct `withhold`
disposition, the declassification probe drives projection, and runtime inject
delivery does not yet bind the compiled DSL-142/DSL-111 identity end to end.
These limits prevent native-backend, universal noninterference, equivalence,
simulation, refinement, or bisimulation claims.

## Design and implementation record

- [Architecture preflight](../../decisions/issue-794-participant-io-control-preflight.md)
- [Current-state assessment](current-state-assessment.md)
- [Detailed adoption design](adoption-design.md)
- [Requirement disposition](requirement-disposition.md)
- [Ordered implementation program](adoption-program.md)
- [Machine-readable acceptance manifest](adoption-program.json)
- [Issue #803 guidance preflight](../../decisions/issue-803-participant-control-guidance-preflight.md)

```{toctree}
:hidden:

current-state-assessment
adoption-design
requirement-disposition
adoption-program
```

The design record captures the pre-adoption gap and the choices used to close
it. Current delivery status comes from the shipped artifacts above, not from
the original program's draft requirement dispositions. The implementation
composes incumbent carriers without a universal message DTO, gateway, second
history, or inflated relation claim.
