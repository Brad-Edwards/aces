# Runtime Control-Plane Composition Architecture

Date: 2026-08-17

Parent issue: [#1151](https://github.com/OpenRAE/rae/issues/1151)

This document expands ADR-104 into component boundaries, ownership, data and
control flow, lifecycle, persistence and coordination interactions, security
boundaries, and failure and recovery behavior. Nothing here is claimable
before its implementation work package (see the
[implementation program](implementation-program.md)) lands with tests.

## 1. Position in the RAES stack

SDL authoring and the processor produce compiled plans; backends realize
effects; `RuntimeTarget` binds a backend to a runtime. The control plane
sits between an embedding application and those boundaries: it accepts
operation submissions against a target, records their lifecycle, holds the
authoritative runtime snapshot, mediates participant transitions, and emits
audit evidence. It owns bookkeeping and admission — never backend effect
semantics, plan compilation, or SDL meaning.

## 2. The contract and its implementations

`RuntimeControlPlane` is the portable contract: submit an operation, obtain
an idempotent receipt, read snapshots, drive participant transitions, and
observe audit events. Conforming implementations differ only in the
guarantees their operating profile declares. The contract carries a
capability surface (work package CP-10) so an embedder can interrogate the
active profile's guarantees and nonclaims instead of assuming them.

## 3. Operating profiles

| Profile | Ownership | Durability | Intended embedders |
| --- | --- | --- | --- |
| P0 ephemeral | one process, no admission | none — loss of process is loss of run | hermetic tests, single-scenario embedding |
| P1 local durable | one process, lease-admitted | crash-consistent authoritative store | local tools, RAE/env-pack/ETV embedding, air-gapped hosts |
| P2 served | one owning service process, many clients | P1 core | shared local services |
| P3 coordinated | multiple processes or hosts | seam only | none — explicit nonclaim pending a future ADR |

A profile is a declaration, not a mode switch: P1 and P2 are the same core
with the adapter in front; P0 is the in-memory store under the same
contract; P3 exists only as the lease, revision, and coordination seams the
lower profiles already exercise.

## 4. State authority

- **Authoritative**: runtime snapshots, operation records, idempotency
  claims, participant transition records. They live in the profile's store
  and change only inside its transactions.
- **Derived**: in-memory snapshot and operation maps, receipt caches,
  indexes. Rebuildable from authoritative state on demand; each cache that
  survives a mutation boundary carries an explicit coherence rule
  (invalidate-on-commit under revision CAS). A derived structure never
  answers admission or receipt queries on its own authority.
- **Evidentiary**: append-only audit events with provenance. Never
  rewritten; terminal audit events commit in the same transaction as the
  state they describe.
- **External**: backend effects. The control plane records intent and
  observed outcome; where neither is observable it records indeterminacy.
  No control-plane read infers an external effect.

## 5. Operation lifecycle and control flow

1. **Admission**: the submission is validated against the target and an
   idempotency claim is taken — a unique insert in the authoritative store.
   A duplicate claim returns the recorded receipt; it never re-invokes the
   backend.
2. **Write-ahead claim**: the operation record becomes durably `RUNNING`
   before the backend is invoked.
3. **Invocation**: the backend call executes outside any store transaction;
   the store never holds locks across external effects.
4. **Terminal commit**: exactly one transaction writes the resulting
   snapshot (revision-checked), the terminal operation record, and the
   audit event. Participant transitions already follow this shape; the
   generic path adopts it (CP-2).
5. **Receipt**: idempotent reads return the committed terminal state from
   the store or a coherence-ruled cache (CP-7).

## 6. Failure and recovery behavior

After process loss, storage loss short of media failure, cancellation, or
timeout, startup reconciliation (CP-3) classifies every non-terminal
operation:

- **effect-absent**: the claim exists but the backend verifiably did not
  act; the operation fails closed with a stable diagnostic.
- **effect-applied**: backend observation confirms the effect; state is
  advanced from observation and committed atomically.
- **indeterminate**: neither is establishable; the operation terminates in
  the explicit indeterminate state, its idempotency claim is retained so
  client retries cannot blindly re-invoke, and the embedder-visible surface
  requires a deliberate resolution action.

Nothing replays automatically. Host loss and network partition reduce to
process loss at P0–P2 because ownership is single-process; the partition
cases that require distributed reasoning are exactly the P3 nonclaim.

## 7. Concurrency control

- **In-process**: existing lock discipline serializes mutation within the
  owner.
- **Cross-process**: the store lease (CP-5) admits exactly one owner; a
  second process fails closed at admission rather than corrupting state.
- **Optimistic safety net**: snapshot commits carry a revision and commit
  by compare-and-swap (CP-4), so even an ownership bug cannot silently
  overwrite; the stale writer errors.
- **Idempotency**: unique claims in the store are the concurrency-safe
  dedup primitive; caches are advisory.

## 8. Persistence and coordination seams

The store contract owns transactions, unique claims, revisions, and the
lease. Providers must verify granted admission results (journal mode, sync
level) rather than trusting requests — the WAL admission finding from issue
#1092, generalized. The clock, audit sink, lease provider, and a future
coordination provider are separate seams so `RuntimeControlPlane` never
encodes a deployment topology. A provider that cannot supply a required
capability fails construction; profiles never degrade silently.

## 9. Security boundaries

Authenticated and authorized access (API-404) terminates at the profile
boundary: P0/P1 inherit the embedding process's identity and the store's
filesystem protections (owned directories, tightened modes, identity-pinned
databases per the PR #1136 hardening); P2 adds the HTTP adapter's
authentication and target binding (#1090, #1133) in front of the same core.
Audit events carry actor provenance in every profile.

## 10. Lifecycle, configuration, and operations

The embedder owns process lifecycle, configuration, upgrade sequencing, and
backup scheduling; the control plane owns schema versioning, one-time
migration from superseded stores (with durable, fsynced backups), integrity
verification at startup, and refusing to open state it cannot verify.
Operational health and the indeterminate-operation runbook are CP-12.

## 11. What this composition does not do

It does not make two application workers coherent over a shared database
(P3 nonclaim), does not give P0 any durability, does not let the HTTP
adapter scale writes beyond its single owner, and does not decide a
specific storage engine here — CP-6 lands the P1 reference store under the
contract, and any conforming provider may replace it.
