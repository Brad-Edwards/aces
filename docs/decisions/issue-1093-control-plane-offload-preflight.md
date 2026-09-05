# Issue 1093 Control-Plane Offload Preflight

Date: 2026-08-11

Issue: #1093. Requirement: API-404.

## Decision

The HTTP adapter remains asynchronous at the network boundary, but every
synchronous control-plane, backend, and durable-store call runs in AnyIO's
bounded worker pool. An application-scoped async lock admits one target-mutating
call at a time. Mutations waiting for that lock do not occupy worker threads,
so status, snapshot, authentication, and audit requests can still make
progress while a backend call is slow.

This includes audit persistence on middleware rejection paths. A malformed or
oversized request is rejected first, while its audit write is awaited through a
dedicated one-worker AnyIO capacity limiter that never borrows from the default
pool used by authentication, reads, and ordinary control-plane work. The
application retains at most
`ControlPlaneSecurityConfig.max_pending_rejection_audits` such writes (default
8, including the active write). Further rejection audits are dropped with a
bounded warning rather than retaining request tasks or starving authenticated
traffic. Audit persistence is best effort at this pre-routing boundary: an
unavailable or saturated audit store must not turn a deterministic `400` or
`413` into an exception or permit the rejected request to reach a route.

The mutation queue is bounded by
`ControlPlaneSecurityConfig.max_pending_mutations`, including the active call.
The default is 32. Admission beyond that bound returns `503` with a
`Retry-After` header instead of retaining an unbounded number of request tasks.
The value must be positive and should be sized with the deployment's upstream
connection, timeout, and retry limits.

One `FastAPI` application represents one runtime target and one event loop.
Per-application serialization prevents concurrent HTTP mutations from racing
the target's snapshot or invoking a non-thread-safe backend concurrently. This
does not create a distributed queue or make direct concurrent library calls
safe across processes.

Worker cancellation is deliberately non-abandoning under Starlette/AnyIO's
`run_in_threadpool` contract: cancellation of the awaiting request does not
kill a Python thread midway through a backend mutation. Idempotency and the
durable operation record remain the recovery surface. Backends must still
implement their own bounded I/O timeouts; offload is not a substitute for an
operation deadline or process isolation.

## Verification

Acceptance requires:

1. a blocked provisioning submission while an authenticated snapshot read
   completes within a short independent deadline;
2. one active mutation per target;
3. stable `503` overload behavior at the configured pending bound;
4. an oversized-request audit that blocks in SQLite while an independent event
   loop task continues within a short deadline;
5. saturation beyond the rejection-audit pending bound while a real
   authenticated route retains a default-pool worker and completes;
6. stable `400`/`413` rejection when audit persistence raises or is dropped;
7. unchanged HTTP auth, idempotency, error, participant, and workflow suites;
8. lint and repository policy; and
9. full verification before release.

Issue #1092 separately owns local transactional storage. A future multi-host
service must use a durable broker/worker design with explicit leases and
recovery rather than treating this in-process lock as distributed scheduling.
