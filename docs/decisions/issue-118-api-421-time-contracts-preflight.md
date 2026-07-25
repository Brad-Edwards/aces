# Issue 118 Portable Time Contracts Preflight

Issue: #118
Requirements: API-421, ASR-528, EXP-734
Date: 2026-07-24

## Binding Authorities

- ADR-009 makes checked-in JSON Schema the normative contract authority.
- ADR-012 requires generic ACES capability rather than pack-local semantics.
- ADR-022 separates time, ordering, pacing, synchronization, and causality.
- ADR-065 and ADR-068 govern experiment provenance and replay claims.
- ADR-090 defines shared time meaning and leaves backend realization to portable
  capability and conformance contracts.

## Guardrails

- Contracts describe portable requirements, observable state, controls, and
  evidence; they do not prescribe a provider, scheduler, or deployment method.
- A backend time claim is admitted only when its closed capability declaration
  covers every required domain, authority, progression, synchronization,
  mapping, constraint, reset, and replay term.
- Runtime readback is typed and bound to the canonical declaration digest.
- Clock transition history is append-only and preserves discontinuity segments.
- Every governed experiment run records declared-versus-realized time,
  apparatus bindings, synchronization assumptions, limits, deviations, and
  evidence.
- Historical content remains ordinary initial service state. Benign activity
  remains participant behavior. Neither is elevated into a time-specific type.
- Golden/backend equivalence compares portable observable state and behavior,
  not provider or topology identity.

## Evidence Plan

- Schema and model round-trip tests for all three contracts.
- Positive and negative backend capability-admission tests.
- Runtime initialize/control/readback and append-only transition tests.
- Conformance tests joining manifest, declaration, runtime state, and run
  provenance.
- Published valid and invalid fixtures and schema change-ledger records.
- Repository policy, requirement governance, documentation, and full verifier.
