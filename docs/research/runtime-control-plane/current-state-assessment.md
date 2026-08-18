# Runtime Control-Plane Current-State Assessment

Date: 2026-08-17

Parent issue: [#1151](https://github.com/OpenRAE/rae/issues/1151)

Evidence below cites the `dev` tree at the time of assessment
(`701858d1`). Line-level behavior was verified by direct reading, not
inferred from documentation.

## 1. The contract surface today

`raes_runtime/control_plane.py` defines `RuntimeControlPlane`. Its
constructor binds one `RuntimeTarget`, one `ControlPlaneStore` (default
`InMemoryControlPlaneStore`), then loads and permanently caches the
snapshot (`self._snapshot = … load_snapshot()`) and the full operation-record
map (`self._operations = self._store.load_records()`). Nothing invalidates
or rebuilds these caches after construction: a second process sharing the
same store is invisible to the first.

In-process locking is partial and unordered. `_participant_control_lock`
covers participant actions and control mediation, and the separate
`RuntimeManager` mixin holds its own `_participant_execution_lock` with no
ordering discipline between the two; the generic operation path holds no
lock at all, so concurrent direct library submissions race `_snapshot`,
`_operations`, and the store writes even before any multi-process question
arises. The HTTP adapter's mutation lock protects only HTTP callers.

## 2. The store protocol

`control_plane_store.py::ControlPlaneStore` (a `Protocol`) exposes
`load_snapshot`, `save_snapshot`, `load_records`, `save_record`,
`find_by_idempotency`, `append_audit`, `read_audit`, and two transition
commits: `commit_control_transition(expected_head=…)` and
`commit_participant_transition(expected_history_heads=…)`. The transition
commits are the one place the store contract already expresses atomic
multi-record commits guarded by expected-head compare-and-swap
(`_require_expected_control_head`, `_require_expected_history_heads`).
Snapshots and generic operation records have no revision or expectation
parameter: `save_snapshot` and `save_record` overwrite unconditionally.

Two implementations exist on `dev`:

- `InMemoryControlPlaneStore` — dictionaries, no durability, correct for
  profile P0.
- `LocalControlPlaneStore` (`control_plane_store_local.py`) — four JSON
  files (`snapshot.json`, `operations.json`, `audit.jsonl`,
  `control-transition-state.json`). Each write is atomic per file via a
  temporary file and `os.replace` with no fsync of the file or directory,
  but a logical commit spanning snapshot plus record plus audit is two or
  three separate file replacements; `operations.json` is a whole-file
  read-modify-replace (concurrent writers lose updates, idempotency lookup
  is a linear scan), `audit.jsonl` is an unlocked append, and
  `load_snapshot` arbitrates between `snapshot.json` and the committed
  transition blob by comparing a participant-transition count — a
  heuristic, not a version. Issue #1092 documented these failures and
  PR #1136 replaced this store with a transactional SQLite design; both
  are deferred to this decision.

## 3. The generic execution path

`control_plane_execution.py::execute_operation` performs, in order:

1. `_idempotent_receipt(...)` — `find_by_idempotency` against the store,
   while `get_operation` and `get_snapshot` answer from the permanent
   caches; in the JSON store the lookup and the later claim are separate
   steps, not one atomic unique claim;
2. `_persist_record(...)` with `OperationState.RUNNING`;
3. `_call_backend_apply(...)` — the external effect;
4. `control_plane._store.save_snapshot(...)`;
5. `_persist_record(...)` with the terminal `SUCCEEDED`/`FAILED` status.

Steps 2, 4, and 5 are independently durable, the in-memory snapshot is
reassigned before the durable write (a failed `save_snapshot` diverges
memory from disk), and no lock guards the sequence. A process exit after
step 3 leaves an applied backend effect with a `RUNNING` record and a stale
snapshot; after step 4, a new snapshot with a non-terminal record. On
restart the record loads unchanged, and step 1 returns it to an idempotent
retry without reconciliation. `OperationState.ACCEPTED` exists in
`raes_contracts.runtime_state` but is never used — the path claims straight
to `RUNNING`. The idempotency check itself is check-then-act: two
concurrent submissions with one key can both miss the lookup and both mint
operations, and a record persisted with an empty request fingerprint
disables the reuse-mismatch check for every later retry. This confirms the
first finding of the issue #1092 integration review and motivates ADR-104
§4 (write-ahead claim, one atomic terminal commit, startup reconciliation).
The participant transition path does not share the atomicity defect: it
commits through the store's transition-commit methods as one guarded unit
and is the template CP-2 generalizes.

## 4. The reference HTTP adapter

`control_plane_api/` implements the served surface behind one composition
boundary, `create_control_plane_app(control_plane, *, security=None)`.
`_offload.py` keeps blocking work off the event loop and serializes target
mutation through a single `asyncio.Lock` per application instance — correct
while exactly one service process owns the store, and exactly the
application-local serialization the #1092 review flagged: two service
processes over one store would each hold their own lock and their own stale
caches. The three API-408 participant-retrieval `GET` routes also go
through the mutation lock because they append evidence, coupling read
throughput to backend mutation latency (a CP-8 concern). Bearer
authentication and target binding come from #1090/#1133
(`control_plane_security.py`, `control_plane_api_guards.py`), and workflow
timeout reconciliation fails closed per #1132
(`control_plane_timeouts.py`). These surfaces are retained under P2.

Nothing in the repository runs the adapter: `create_control_plane_app` is a
factory, `uvicorn` is a declared but unused dependency, and there is no
serve entrypoint or CLI command. Every consumer today is an embedded ASGI
test client, so the served topology is asserted by documentation — the
issue #1093 preflight states plainly that the in-process lock "does not
create a distributed queue" and that "a future multi-host service must use
a durable broker/worker design with explicit leases and recovery" — which
is exactly the boundary ADR-104 records as profile P2 and the P3 nonclaim.

## 5. Test surfaces pinning today's behavior

- `test_runtime_control_plane.py`, `test_runtime_conformance.py` — the
  contract and in-memory behavior.
- `test_runtime_control_plane_api.py` — adapter admission, auth, offload
  serialization (#1133).
- `test_dsl_437_snapshot_durability_conformance.py`,
  `test_run_307_shared_operational_state.py` — snapshot durability and
  shared-state reads (#1148).
- PR #1136 and its successor branches additionally carry
  `test_issue_1092_control_plane_crash_consistency.py` (~1,250 lines):
  terminal-commit idempotence, per-write-boundary rollback, restart
  reconciliation, second-owner rejection with clean handoff, WAL and
  integrity guards, and legacy-migration rollback. The implementation
  program absorbs it into CP-9 as the acceptance bar the new lifecycle
  must keep meeting.

The durable-store implementation itself exists, unlanded, on three
branches (`API-404-durable-store-successor`, `API-404-fsync-wal`, and the
`integration-openrae-current-dev` integration branch): an atomic
`claim_record`, an `AtomicControlPlaneStore` capability protocol with
`commit_terminal_operation` and `reconcile_interrupted_records`, a
flock-based `RuntimeOwnerLease`, fsync-disciplined path helpers, a
compatibility adapter for legacy stores, and a unified `_operation_lock`.
Its shape converges with ADR-104 §§4–5; CP-6 reconciles and re-lands that
work rather than redesigning it.

## 6. Gap summary against ADR-104

| Gap | Evidence | Owning work package |
| --- | --- | --- |
| No explicit lifecycle contract; no indeterminate terminal state | `OperationState` lacks it (`ACCEPTED` exists unused); interrupted work stays `RUNNING` | CP-1 |
| Generic path unlocked; two unordered lock domains | no lock in `execute_operation`; `_participant_control_lock` vs the manager's `_participant_execution_lock` | CP-2, CP-4 |
| Non-atomic terminal effects on the generic path | `execute_operation` steps 2/4/5 above | CP-2 |
| No startup reconciliation | records load unchanged at construction | CP-3 |
| Unconditional snapshot/record writes | `save_snapshot`/`save_record` have no expected revision | CP-4 |
| No ownership admission | any process may open any store | CP-5 |
| Non-transactional durable store | `LocalControlPlaneStore` JSON files | CP-6 |
| Non-atomic idempotency claims; status and snapshot reads answered from permanent caches | `find_by_idempotency` + later `save_record`; `get_operation` over `self._operations`, `get_snapshot` over `self._snapshot` | CP-7 |
| Application-local mutation serialization | `_offload.py` `asyncio.Lock` | CP-8 |
