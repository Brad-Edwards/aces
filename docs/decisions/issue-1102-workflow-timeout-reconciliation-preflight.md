# Issue 1102 Workflow Timeout Reconciliation Preflight

Date: 2026-08-11

Issue: #1102. Requirements: RUN-317 and RUN-318.

## Decision

Workflow timeout reconciliation treats persisted timestamps as untrusted
durable input. The reconciliation clock is parsed once per operation, and all
timestamps require an explicit ISO-8601 offset before normalization to UTC.
`started_at <= updated_at <= reconciliation clock` is required. Malformed,
naive, or non-monotonic values fail with stable, value-free conflicts; they do
not synthesize a timeout, mutate history, or activate timeout compensation.
Persisted timeout configuration is likewise either absent or a strictly
positive integer. Invalid values cannot silently disable reconciliation or
become an immediate timeout.

Timeout admission compares the exact integral whole-second component of
`now - started_at` with the configured integer duration. It does not use
`timedelta.total_seconds()` because float rounding over large spans can turn a
timestamp just below the boundary into an early timeout, and it does not add an
unbounded duration to a timestamp because that can overflow. The boundary
remains inclusive according to the incumbent workflow state-machine contract.
Only a proven elapsed duration produces `workflow_status: timed_out` and a
`workflow_timed_out` history event. Already-terminal results are unchanged, so
reconciliation remains idempotent across restart.

This is operational wall-clock timeout handling. It does not reinterpret SDL
logical time, participant episode time, simulated clocks, or backend-native
deadlines as interchangeable evidence.

## Verification

Tests cover malformed, naive, offset, future, and non-monotonic timestamps;
invalid timeout values; exact and large-span sub-boundaries; enormous durations;
empty-control-plane clock validation; compensation non-triggering for invalid
state; and terminal replay idempotency. The runtime timeout suite, lint, policy,
and canonical verification remain required.
