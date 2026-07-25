# Issue 117 Shared Time Model Preflight

Issue: #117
Requirements: SEM-227, SEM-228, SEM-229, DSL-126, DSL-127, DSL-128, RUN-317,
RUN-318
Date: 2026-07-24

## Binding Authorities

- ADR-022 separates timestamps, ordering, causality, pacing, synchronization,
  and clock authority.
- SEM-213 owns participant-local schedules, cadence, deadlines, dwell, latency,
  windows, reset, and replay state.
- ADR-065 and ADR-068 own run provenance and replay claims.
- ADR-078 owns the closed SDL phase lifecycle.
- Issue #118 owns portable backend capability, conformance, and experiment-run
  provenance contracts for the model defined here.

## Guardrails

- Semantic time always resolves to a declared domain and clock.
- Distinct domains are incomparable without an admitted mapping.
- Tick periods and mappings use reduced exact rational values.
- Equal timestamps do not establish simultaneity, ordering, or causality.
- Temporal constraints use ordinary ACES references; they do not create a
  second event, participant, workflow, or evaluation model.
- Reset, replay, or backward jump starts a new segment and appends history.
- Runtime state cannot silently change clock authority or progression policy.
- Control-plane audit timestamps and watchdog timeouts remain operational
  apparatus unless explicitly bound through the shared model.
- Backend support and realized provenance are deferred to #118, not inferred
  from the reference coordinator.

## Evidence Plan

- Positive parse-to-compile test for every declaration family.
- Negative tests for dangling refs, implicit conversion, invalid rational
  values, and policy/clock lifecycle mismatch.
- Runtime transition tests for advance, pause, resume, reset, and segment
  history.
- Composition test proving imported clock/domain/policy refs are namespaced
  consistently.
- Generated-schema parity and publication-manifest update.
- Repository policy, governance, and full verifier.
