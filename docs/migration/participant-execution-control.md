# Participant Execution Control Migration

Issue #898 strengthens `capabilities.participant_runtime` for every backend
that declares `autonomous_execution`. Backends that do not make that claim are
unchanged.

An autonomous backend must now:

- replace independent action/target support as its admission authority with
  exact `execution_bindings`;
- declare all `start`, `pause`, `resume`, `drain`, `reset`, and `teardown`
  controls;
- declare bounded concurrency with positive service capacity and at least two
  concurrent actions;
- implement native binding, lifecycle mutation/readback, and bounded batch
  methods; and
- publish the three participant execution contract ids plus operation
  receipt/status and runtime snapshot support.

Do not inherit or emulate lifecycle success by editing the portable snapshot.
The backend control method must perform and observe scheduler/shared-time
coordination, bounded drain, reset, and resource release. RAES rejects a
successful return whose readback did not change to the action-specific state
or did not add operation and evidence references.

Action requests are generation bound. Reset and shared-clock reset increment
the generation; stale queued work and stale native completions are rejected.
Pause stops new admission, bounded drain requires zero reserved/in-flight work,
and teardown releases resources. A wall-pacing failure is visible as degraded,
not-ready, paused service state with a pacing-deviation evidence reference.

Existing scenario SDL and both autonomous policy profiles remain valid. The
change is backend-facing and fail closed: a previous autonomous manifest
without execution bindings and lifecycle/concurrency declarations is rejected
during manifest validation or planning. Conditional target conformance also
executes two native actions and the lifecycle, so adding placeholder methods is
not sufficient.
