# Issue #1151 — Runtime Control-Plane Architecture Preflight

Date: 2026-08-17

Issue: #1151. Requirement: `API-404`.

This note frames the architecture decision before the design lands. It is
guidance only: it does not publish contracts, change runtime behavior, or
select a storage engine by incidental code change. The binding record is
ADR-104 together with the design set under
`docs/research/runtime-control-plane/`.

## Why the incumbent surfaces cannot be extended in place

Issue #1092 and PR #1136 hardened the local JSON store into a transactional
SQLite store and were deferred because the changes embed architectural
choices — single-process ownership, recovery semantics, store compatibility
rules — that the repository has never decided. The integration review of that
work recorded two structural gaps that no store swap can close by itself:

- The generic operation path performs independently durable steps (claim
  `RUNNING`, invoke the backend, save the snapshot, save terminal status). A
  process exit between steps leaves an applied backend effect with stale
  state, and restart returns the stale record to an idempotent retry without
  reconciling.
- Every `RuntimeControlPlane` instance permanently caches snapshot and
  operation maps, and HTTP mutation serialization is application-local. A
  shared database therefore does not make two application workers coherent;
  the supported topology must fail closed as one owning process until a
  revision-CAS and lease design exists.

## Decisive boundaries

- The control plane is a contract with profiled implementations, not one
  deployable service. Embedders select an operating profile; each profile
  states its guarantees and nonclaims explicitly.
- State is classified before it is stored: authoritative records (snapshots,
  operation records, idempotency claims), derived caches (rebuildable,
  never load-bearing), and append-only audit evidence. External backend
  effects are never assumed from control-plane state; they are observed or
  declared indeterminate.
- An operation is durable work with a recorded lifecycle. Terminal effects
  commit atomically (snapshot, terminal record, audit) and interrupted
  operations surface as explicit indeterminate outcomes that require
  reconciliation, never silent replay.
- Concurrency control is ownership-first: one writer per store at profile
  P1 (lease-admitted), optimistic revision checks on snapshot commits, and
  unique idempotency claims in the authoritative store.

## Non-goals for the design issue

- No storage engine is implemented or selected by code change here; the
  design constrains providers through the store contract and its required
  admission checks.
- No distributed or highly available topology is claimed. The design records
  the extension seams (lease, revision CAS, coordination provider) that a
  future profile would implement, and states the nonclaim plainly.
- No change to SDL authoring, processor compile behavior, or backend
  contracts. The control plane consumes those boundaries; it does not own
  them.

## Gotchas and anti-patterns

- A durable claim without a returned admission result is not durable; store
  providers must verify what the engine actually granted (journal mode,
  sync level), following the WAL admission finding from issue #1092.
- Idempotency receipts served from a permanent in-memory cache reintroduce
  the stale-read hazard in every multi-worker topology; receipts must be
  answered from the authoritative store or from a cache with an explicit
  coherence rule.
- Startup reconciliation must distinguish "the backend effect is known
  absent", "known applied", and "indeterminate"; collapsing these into one
  retryable failure state re-creates the replay hazard the audit found.
