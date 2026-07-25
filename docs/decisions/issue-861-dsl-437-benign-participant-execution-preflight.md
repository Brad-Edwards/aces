# Issue 861 Benign Participant Execution Preflight

Issue: #861
Requirement: DSL-437
Date: 2026-07-24

## Existing Authority And Precedent

- ADR-013 owns participant episode initialization, reset, restart, and
  termination.
- ADR-022 and ADR-067 own role-neutral participant action, observation,
  interaction, and behavior-specification semantics.
- ADR-041 owns participant implementation selection and provenance.
- ADR-054 owns the observable participant runtime lifecycle and append-only
  histories.
- ADR-073 keeps score and reward authority outside participant actions.
- ADR-085 owns participant information-flow and controller/authority
  separation.
- ADR-090 and ADR-091 own shared time, portable controls, backend capability,
  runtime readback, and run provenance.
- CybORG, Gymnasium/PettingZoo/OpenSpiel, TENA, IEEE HLA, ROS 2, FMI, and
  OpenSCENARIO are reviewed precedents already recorded in the SDL lineage.

No existing ACES capability schedules a behavior specification against the
shared clock and invokes native participant actions. DSL-437 fills that bounded
gap without adding a parallel participant or time model.

## Guardrails

- Benign simulated users are `green` participants, not background actors.
- Non-evaluated policies carry no objective, outcome, score, proof,
  adjudication, or receipt authority.
- All action, observation, participant, clock, progression, and temporal refs
  resolve through existing declarations and compile to canonical addresses.
- Exactly one cadence constraint determines due ticks; all temporal constraints
  are preserved in action history. Stepped cadence points must be reachable;
  real-time and dilated policies use the runtime-owned wall driver; externally
  paced autonomous policies fail closed pending a portable transition driver.
  Wall-paced policies require runtime clock authority; negative cadence starts
  and stale post-wait transitions fail closed.
- The initial scheduler is deterministic `ordered_cycle`. Stochastic policy
  behavior binds through existing apparatus/random-stream contracts.
- Plan reapplication preserves typed scheduler state only when the complete
  compiled policy and its resolved time declarations are unchanged.
- One participant has exactly one autonomous scheduler owner.
- Pause/resume/reset use shared-clock lifecycle. Reset-capable policies require
  a manifest-advertised, time-authority-owned transaction that commits the
  clock and participant episodes together or leaves native state unchanged;
  local snapshot replacement is not backend rollback.
- Shared-clock controls invoke due actions at the actual execution coordinate
  and reject transitions that would skip a due cadence.
- Native backend execution and a matching terminal typed outcome precede
  portable snapshot/history commit; action outcome is not control-plane
  success, and an invalid outcome consumes the scheduler attempt identity
  without replaying native work. Scheduler enforcement applies to direct
  protocol implementations as well as reference-base subclasses.
- Backend admission requires exact action, observation, target, feature,
  strategy, and finite-limit support.
- Capability claims alone do not prove execution, fidelity, or readback.
- No pack-specific control semantics or historical-data ontology enter ACES.

## Evidence Status

Delivered by the focused DSL-437 and surrounding regression tests:

- positive SDL parsing and canonical compilation;
- negative non-green, authority-widening, unbound declared authority,
  missing/unreachable cadence, unsupported external pacing, overlapping
  ownership, skipped cadence, changed resolved-time policy, invalid native
  outcome, and participant implementation-selection cases;
- exact autonomous feature, action, observation, target, strategy, and
  finite-limit capability admission;
- RuntimeManager-driven initial and advanced due actions through shared-clock
  pause, resume, advance, race-checked automatic real-time pacing, and
  transaction-admitted reset lifecycle;
- native binding and action execution with typed success/failure outcomes
  distinct from control-plane apply success;
- typed policy-digest and time-segment scheduler state, temporal-context
  history, unchanged-plan reapplication, lifecycle change reporting, and
  material-policy rejection; and
- durable store, API envelope, and conformance conversion/diagnostic coverage
  for valid and invalid scheduler state, including clock-segment and
  participant-episode contradictions.

Repository-wide contract, schema, lineage, policy, unit, integration, and docs
verification remains the final integration gate. Passing it does not prove a
particular production backend, service adapter, participant implementation, or
golden range executed faithfully.
