# Requirement and Surface Disposition

Date: 2026-08-17

Parent issue: [#1151](https://github.com/OpenRAE/rae/issues/1151)

This document records the evidence-backed disposition of every incumbent
control-plane surface, requirement, and in-flight change, as ADR-104 §7
requires. Dispositions are one of: **retain**, **change**, **split**,
**supersede**, or **remove**.

## Requirements

| Requirement | Disposition | Detail |
| --- | --- | --- |
| `API-404` (ACTIVE, wave 1) | retain, change | Remains the control-plane authority. Work package CP-11 rewrites its traceability to the profiled contract and records which clauses (authenticated access, durable state, idempotent submission, auditable lifecycle) each profile satisfies; P0 explicitly waives durability. |
| `SEM-222` (touched by PR #1136) | retain | Snapshot semantic-integrity obligations are unchanged by this design; the P1 store must preserve them through the round-trip codec guard PR #1136 introduced. |
| Adjacent UIDs bound to these surfaces (`API-402`, `API-403`, `API-408`, `RUN-300`, `RUN-304`, `RUN-308`, `RUN-311`, `RUN-316`–`RUN-319`, `SEM-230`, `SEM-233`, `DSL-435`–`DSL-437`, `SEM-204`, `SEM-214`) | retain | Their statements are unchanged. `API-403` already pins the per-target contract that profile P2 keeps; `RUN-319`/`SEM-233` constrain the append-only transition commits the design preserves; `API-408`'s retrieval routes gain a read path off the mutation lock under CP-8 without a statement change. |

## Code surfaces

| Surface | Disposition | Detail |
| --- | --- | --- |
| `raes_runtime.control_plane.RuntimeControlPlane` | retain, change | Stays the portable contract entry point. CP-1/CP-2 change the operation lifecycle to write-ahead claims and atomic terminal commits; CP-7 makes idempotency claims atomic and demotes the status/snapshot caches. |
| Generic operation execution path (`control_plane_execution`) | change | Four independently durable steps become claim → invoke → one terminal transaction (snapshot, terminal record, audit). CP-2. |
| Participant transition CAS path | retain | Already commits snapshot, record, and audit as one unit; becomes the template the generic path adopts. |
| In-memory default store | retain | Profile P0's store. Gains the store-contract conformance surface (CP-1, CP-9) with no durability claims. |
| `LocalControlPlaneStore` (JSON, whole-file replace) | supersede | Migration source only. The P1 transactional store replaces it; a one-time import with durable backups (per PR #1136) carries state forward. Removal follows after the migration window, tracked in CP-6. |
| SQLite store modules from PR #1136 (`control_plane_store_local`, `_paths`, `_lease`, `_snapshots`, `_compatibility`, `_legacy`, `control_plane_durability`, `control_plane_lifecycle`, `control_plane_recovery`) | change, adopt | Principal input to CP-6. WAL admission by returned result, unique idempotency claims, atomic participant commits, POSIX path hardening, integrity digests, and migration/backup durability are adopted as designed. The blanket interrupted-to-`FAILED` startup conversion is reworked to CP-3's classification (effect-absent / effect-applied / indeterminate). |
| Reference HTTP adapter (`control_plane_api*`) | retain, change | Becomes the P2 reference. CP-8 pins single-owner service posture, owner-serialized mutation, and revision-carrying reads with explicit stale-read rules. |
| `RuntimeTarget` and backend contracts | retain | Outside control-plane authority (ADR-104 §6). Unchanged. |
| Permanent snapshot/operation caches in `RuntimeControlPlane` | change | Demoted to derived state: rebuildable, coherence-ruled, never authoritative for receipts or admission. CP-4/CP-7. |

## In-flight work

| Item | Disposition | Detail |
| --- | --- | --- |
| Issue #1092 | supersede | Its problem statement is absorbed by ADR-104 §§3–5 and its remedy is re-scoped into CP-1 through CP-7. Close #1092 when those work packages are filed, linking each residual gap from its integration-review addendum to the package that owns it. |
| PR #1136 and successor branches (`API-404-durable-store-successor`, `API-404-fsync-wal`, `integration-openrae-current-dev`) | split, adopt | Deferred by the maintainer pending this design. The implemented atomic `claim_record`, `AtomicControlPlaneStore` (`commit_terminal_operation`, `reconcile_interrupted_records`), `RuntimeOwnerLease`, fsync path discipline, compatibility adapter, and unified `_operation_lock` re-land as CP-6 (with CP-2/CP-5 contracts), recovery reworked under CP-3's classification, and the crash-consistency suite absorbed into CP-9. The PR's preflight note (`issue-1092-local-control-plane-durability-preflight.md`) lands with CP-6 as the store-level design record, subordinate to ADR-104. |
| Issue #8 (API-404 tracking) | retain | Gains the profile-scoped acceptance framing through CP-11. |

## Documentation and test surfaces

| Surface | Disposition | Detail |
| --- | --- | --- |
| `docs/explain/sdl/runtime-architecture.md` | change | Gains the profile model and the operation-lifecycle description once CP-10 lands; until then it must not claim durability or multi-process support. |
| `test_issue_1092_control_plane_crash_consistency.py` (successor branches, ~1,250 lines) | adopt | Absorbed into CP-9's profile conformance suite with kill-point injection at every commit boundary of the new lifecycle; it is the acceptance bar the re-landed store must keep meeting. |
| `test_http_api_admission` / offload surfaces (#1133) | retain | P2 admission behavior is unchanged by this design; CP-8 extends the same suite. |
