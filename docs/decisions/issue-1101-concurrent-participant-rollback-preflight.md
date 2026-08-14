# Issue 1101 Concurrent Participant Rollback Preflight

Date: 2026-08-11

Issue: #1101. Requirement: RUN-308.

## Decision

A concurrent dispatch and its serialized commit have two distinct failure
boundaries. Before native dispatch, the scheduler retains a deeply isolated
pre-batch `RuntimeSnapshot`; binding, reservation, or dispatch-copy failure can
restore that snapshot because no native action was submitted. Once the backend
batch method is entered, an exception, cancellation, or result collection that
cannot be paired with the submitted requests is indeterminate native work. The
scheduler settles every submitted action id as a failed, non-retryable attempt
and releases only that batch's accounting delta. It never restores those action
ids to a due state that could replay an unknown side effect.

Once results can be paired, each result envelope is deeply detached from the
backend and every dispatched peer is settled. Each worker receives an isolated
predecessor. Valid peer snapshots are revision-checked and committed in
deterministic request order. The merge classifies every `RuntimeSnapshot` field:
all backend-owned mapping and value fields use three-way merge, while autonomous
scheduler state and execution-service state are protected and must equal the
reserved predecessor. This exhaustive ownership guard makes a new snapshot
field fail at import/test time until it receives an explicit owner. Committed
nested values are detached so a retained backend result cannot mutate
authoritative state after return.

Three-way composition is conservative rather than implicit conflict
resolution. The compiler carries each action contract's interaction classes,
shared-state footprint, related actions, commutativity declaration, and merge
rule reference into the execution binding. Overlapping semantic footprints
remain on the serial path unless both actions declare commutativity or the same
governed merge rule. At commit, a second write to the same snapshot field/key
or scalar revision is rejected even when the values compare equal; this runtime
does not implement a value-level merge algorithm merely because a contract
authorizes concurrent execution.

An individually invalid result never contributes its backend snapshot; its own
scheduler occurrence transitions to protocol failure while valid peers remain
committed. A normal failed outcome under `failure_policy: stop` is recorded, but
stop takes effect only after all peers in the already-dispatched chunk are
settled. Later chunks are not dispatched. A merge conflict rejects the
conflicting peer with a stable diagnostic rather than leaking a backend key or
discarding peers committed earlier in the serialized order.

Service accounting is delta based. Admission adds only the chunk's in-flight
count, completion subtracts the same count, and pre-existing reserved or
in-flight work remains authoritative. If normal final settlement raises, the
portable boundary records a stable failure and restores the isolated pre-batch
service counters rather than leaking the exception or leaving the batch live.
Already in-flight participants are not selected again. Due work is scanned once
and processed by an iterative, capacity-bounded chunk loop; participant count
therefore cannot consume Python call-stack depth.

The same-tick request set is bound once against one isolated predecessor before
chunk dispatch. This removes one whole-snapshot copy per chunk while preserving
the common-predecessor and pre-dispatch rollback boundary. Dispatch and returned
result isolation still copy the mutable `RuntimeSnapshot`; the 800-participant
test is a bounded operational qualification, not a claim of asymptotically
linear memory-copy cost. A persistent or immutable snapshot carrier would be a
separate contract change and is not implied here.

The backend call remains a trust boundary. Portable diagnostics contain stable
codes and fixed messages, never native exception text or type, traceback, host
path, mapping key, credential, or participant data. This change does not claim
that native side effects can be rolled back. It records an indeterminate
dispatch as non-retryable precisely because rollback cannot be proved.

## Rejected Alternatives

- Treat the whole paired batch as all-or-nothing: native peers have already run,
  so discarding valid results makes portable state diverge from observed work.
- Restore scheduler attempts after entering backend dispatch: transport failure
  cannot prove absence of a native side effect, and restoring the stable action
  id permits blind replay.
- Stop committing at the first failed peer: later peers in the same chunk have
  also run and must be settled before stop affects undispatched work.
- Clear all service counters: this releases reservations owned by other work.
- Retain a shallow rollback alias: nested backend mutation can corrupt the
  supposed pre-batch snapshot even when dispatch raises.
- Recompute all due work recursively after each chunk: this is quadratic and
  fails at ordinary Python recursion limits.

## Verification

Tests cover pre-dispatch rollback; raised, cancelled, and miscounted dispatched
backends; non-retryable action identity; per-worker and post-result mutation
isolation; exhaustive snapshot-field ownership; serial/concurrent projection
equivalence; protocol-invalid typed and untyped results; public failure
snapshots; delta-preserved service accounting; revision-checked metadata; mixed
success/failure peers under stop; rejected changed-address isolation; normalized
service-settlement exceptions; stable diagnostics; explicit capacity backpressure;
declared semantic-conflict serialization and explicit commutativity/merge-rule
admission; deferred final-materialization failure normalization; and an
800-participant iterative run through real reservation and settlement with one
due scan and one policy-wide binding snapshot. The focused participant scheduler suite, runtime suite, lint,
policy, and canonical verification remain required.
