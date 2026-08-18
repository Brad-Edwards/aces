# Runtime Control-Plane Implementation Program

Date: 2026-08-17

Parent issue: [#1151](https://github.com/OpenRAE/rae/issues/1151)

Milestone: `Runtime Control-Plane`

The machine-readable authority is
[`implementation-program.json`](implementation-program.json).

## Definition delivered by issue 1151

Issue #1151 delivers ADR-104, the current-state assessment, the profiled
composition architecture, the requirement and surface disposition, and this
dependency-ordered program. It does not implement any work package below;
each package is filed as its own issue in the Runtime Control-Plane
milestone when this design is accepted, and no guarantee is claimable before
its package lands with tests.

## Dependency graph

```text
 CP-1 lifecycle contract
   |         \
   v          v
 CP-2 atomic  CP-4 revision CAS      CP-5 store lease
 terminal        |                      |
 commit          |                      |
   |             +----------+-----------+
   v                        |
 CP-3 startup               v
 reconciliation        CP-6 transactional local store (re-lands PR #1136)
   |                        |
   |                        v
   |                   CP-7 idempotency claims in store
   |                        |
   +------------+           v
                |      CP-8 served profile (HTTP adapter)
                v           |
          CP-9 crash/profile conformance suite
                |
                v
          CP-10 profile declaration and capability discovery
                |
                +--> CP-11 API-404 requirement update
                +--> CP-12 recovery runbook and operator tooling
```

## Work packages

Each package below becomes one milestone issue with this scope, ordering,
and verification expectation. Requirement traceability is `API-404`
throughout; packages touching snapshot semantics also cite `SEM-222`.

### CP-1 — Operation lifecycle contract

Define the operation lifecycle in contracts: states including the explicit
indeterminate terminal outcome, the stable diagnostics that accompany each
transition, and the state-transition table. Update
`contracts/schemas/control-plane` accordingly. Verification: contract tests
enumerate every legal and illegal transition. Depends on: nothing.

### CP-2 — Atomic terminal commit

Rework the generic execution path so the running claim is durable before
backend invocation and the terminal transition commits snapshot, terminal
record, and audit event in one store transaction, matching the participant
transition path. Unify in-process locking behind one operation lock — the
generic path is unlocked today and the participant and manager paths hold
two unordered locks. Verification: kill-point tests at every step boundary
show no observable partial terminal state; concurrent in-process
submission tests. Depends on: CP-1.

### CP-3 — Startup reconciliation

Classify every non-terminal operation at startup as effect-absent,
effect-applied, or indeterminate, using backend observation where the
backend offers it; never replay automatically; park indeterminate outcomes
behind the CP-1 diagnostic and an embedder-visible surface. Verification:
restart tests per classification, including the no-observation backend.
Depends on: CP-1, CP-2.

### CP-4 — Snapshot revision compare-and-swap

Version every snapshot commit; a writer holding a stale revision fails
closed. Demote in-memory maps to rebuildable derived state with an explicit
coherence rule. Verification: interleaved-writer tests and cache-rebuild
tests. Depends on: CP-1.

### CP-5 — Store lease admission

Contract a store ownership lease; exactly one owner per store at P1/P2.
Local implementation follows the PR #1136 lease module. Verification:
concurrent-process admission tests. Depends on: nothing (integrates with
CP-4).

### CP-6 — Transactional local store

Re-land the PR #1136 store work — already implemented across
`API-404-durable-store-successor`, `API-404-fsync-wal`, and
`integration-openrae-current-dev` (atomic `claim_record`,
`AtomicControlPlaneStore` with `commit_terminal_operation` and
`reconcile_interrupted_records`, `RuntimeOwnerLease`, fsync path
discipline, compatibility adapter) — under the CP-1/CP-2/CP-4/CP-5
contracts: WAL admission by returned result, unique idempotency claims,
path and permission hardening, integrity digests, one-time migration with
durable backups. Recovery behavior conforms to CP-3 instead of blanket
interrupted-to-failed conversion. Verification: the absorbed
crash-consistency suite plus store-contract conformance. Depends on: CP-1,
CP-2, CP-4, CP-5.

### CP-7 — Atomic idempotency claims and cache demotion

Make the idempotency lookup-and-claim one atomic store operation (unique
claim), and demote the permanent status and snapshot caches behind
`get_operation`/`get_snapshot` to rebuildable derived state with an
explicit coherence rule. Verification: multi-restart retry tests;
stale-cache injection. Depends on: CP-6.

### CP-8 — Served profile alignment

Bring the reference HTTP adapter to profile P2: single owning service
process, owner-serialized mutations, reads carrying the snapshot revision
they observed, and explicit stale-read rules. Move the API-408 retrieval
routes off the mutation lock by giving evidence appends their own ordered
path, so reads stop contending with backend mutation latency. Verification:
extension of the #1133 admission suite. Depends on: CP-4, CP-7.

### CP-9 — Crash and profile conformance suite

One suite that runs each profile's guarantee set: kill-point injection at
every commit boundary, restart reconciliation assertions, lease contention,
revision conflicts, and P0's explicit nonclaims. Absorbs the 115-test crash
suite from PR #1136. Depends on: CP-2, CP-3, CP-6.

### CP-10 — Profile declaration and capability discovery

Embedders select a profile and can interrogate its guarantees and nonclaims
programmatically; `docs/explain/sdl/runtime-architecture.md` gains the
profile model. Depends on: CP-1 through CP-8.

### CP-11 — API-404 requirement update

Rewrite API-404 traceability to the profiled contract, recording which
clauses each profile satisfies and P0's durability waiver; sync Ground
Control. Depends on: CP-10.

### CP-12 — Recovery runbook and operator tooling

Operator flow for indeterminate operations, backup/restore, upgrade and
migration sequencing, and health surfaces. Depends on: CP-3, CP-6.
