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
map (`self._operations = self._store.load_records()`). Mutation is
serialized in-process by `RLock`s (`_operation_lock`,
`_participant_control_lock`, `_trusted_provisioning_plan_lock`). Nothing
invalidates or rebuilds these caches after construction: a second process
sharing the same store is invisible to the first.

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
  temporary file and `os.replace`, but a logical commit spanning snapshot
  plus record plus audit is two or three separate file replacements, and
  `operations.json` is a whole-file read-modify-replace: concurrent
  writers lose updates, and a crash between file replacements leaves the
  files mutually inconsistent. Issue #1092 documented these failures and
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

Steps 2, 4, and 5 are independently durable. A process exit after step 3
leaves an applied backend effect with a `RUNNING` record and a stale
snapshot; after step 4, a new snapshot with a non-terminal record. On
restart the record loads unchanged, and step 1 returns it to an idempotent
retry without reconciliation. This confirms the first finding of the
issue #1092 integration review and motivates ADR-104 §4 (write-ahead claim,
one atomic terminal commit, startup reconciliation). The participant
transition path does not share this defect: it commits through the store's
transition-commit methods as one guarded unit and is the template CP-2
generalizes.

## 4. The reference HTTP adapter

`control_plane_api/` implements the served surface. `_offload.py` keeps
blocking work off the event loop and serializes target mutation through a
single `asyncio.Lock` per application instance — correct while exactly one
service process owns the store, and exactly the application-local
serialization the #1092 review flagged: two service processes over one
store would each hold their own lock and their own stale caches. Bearer
authentication and target binding come from #1090/#1133
(`control_plane_security.py`, `control_plane_api_guards.py`), and workflow
timeout reconciliation fails closed per #1132
(`control_plane_timeouts.py`). These surfaces are retained under P2.

## 5. Test surfaces pinning today's behavior

- `test_runtime_control_plane.py`, `test_runtime_conformance.py` — the
  contract and in-memory behavior.
- `test_runtime_control_plane_api.py` — adapter admission, auth, offload
  serialization (#1133).
- `test_dsl_437_snapshot_durability_conformance.py`,
  `test_run_307_shared_operational_state.py` — snapshot durability and
  shared-state reads (#1148).
- PR #1136 additionally carries a 115-test crash-consistency suite bound
  to its SQLite store; the implementation program absorbs it into CP-9.

## 6. Gap summary against ADR-104

| Gap | Evidence | Owning work package |
| --- | --- | --- |
| No explicit lifecycle contract; no indeterminate terminal state | `OperationState` in `raes_contracts.runtime_state` lacks it; interrupted work stays `RUNNING` | CP-1 |
| Non-atomic terminal effects on the generic path | `execute_operation` steps 2/4/5 above | CP-2 |
| No startup reconciliation | records load unchanged at construction | CP-3 |
| Unconditional snapshot/record writes | `save_snapshot`/`save_record` have no expected revision | CP-4 |
| No ownership admission | any process may open any store | CP-5 |
| Non-transactional durable store | `LocalControlPlaneStore` JSON files | CP-6 |
| Non-atomic idempotency claims; status and snapshot reads answered from permanent caches | `find_by_idempotency` + later `save_record`; `get_operation` over `self._operations`, `get_snapshot` over `self._snapshot` | CP-7 |
| Application-local mutation serialization | `_offload.py` `asyncio.Lock` | CP-8 |
