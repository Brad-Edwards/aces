# Issue 898 Portable Participant Execution Control Preflight

Issue: #898

Requirement: none; the issue is the authoritative contract.

Date: 2026-07-26

This note fixes architecture guardrails before implementation. It is not an
implementation plan and adds no schema, runtime, backend, control-plane,
conformance, or release behavior.

## Authority Decision

Issue #898 extends the existing autonomous-participant path; it does not create
a second scheduler, actor, action, lifecycle, time, backend, or control-plane
root.

The portable execution controller is a capability-specific extension of the
existing `RuntimeTarget.participant_runtime` component, following the incumbent
`AutonomousParticipantRuntime`, `CoordinatedParticipantResetRuntime`, and
`CoordinatedParticipantTimeRuntime` protocol pattern. Do not add a sibling
`participant_executor`, worker-service registry, or pack-owned controller to
`RuntimeTarget`.

The implementation changes the authority boundary recorded by ADR-092: it
makes the autonomous scheduler/executor remotely controllable and admits
backend-native bounded concurrency. The normative change therefore requires an
in-band ADR-092 amendment and pin update under ADR-059 in the same change that
publishes the contracts. A new ADR would split one autonomous-execution
decision across two authorities. ADR-091 already owns portable time
control/readback and need not be amended unless its time semantics change.

## Concept Boundaries

Keep these state machines distinct and join them by typed references:

| Concern | Canonical owner | Issue #898 boundary |
| --- | --- | --- |
| Authored autonomous behavior | ADR-092, `ParticipantBehaviorSpecification.autonomous_execution` | Unchanged; no new SDL root or pack-local scheduler syntax. |
| Participant episode | ADR-013, RUN-311, `ParticipantRuntime.initialize/reset/restart/terminate` | Episode identity and terminal state; not executor-service health, readiness, drain, or teardown. |
| Per-participant scheduler continuation | `ParticipantAutonomousExecutionStateModel` | Remains the policy/participant cursor and accounting state. It is not service health or an operation receipt. |
| Execution-service lifecycle | New capability-specific protocol on the incumbent participant runtime | Start, pause, resume, drain, reset-generation coordination, health/readiness, and teardown for one admitted execution scope. |
| Shared time | ADR-090/091, `TimeRuntime`, `time-runtime-state-v1` | Clock control, coordinate, segment, transition history, and pacing provenance. Executor pause cannot mint a private clock. |
| Native action execution | `ParticipantActionAdmissionRequest`, `ParticipantNativeActionExecution`, `ParticipantActionResultModel` | Exact action-to-target binding, native outcome, and safe provenance before portable history commit. |
| Control-plane operation | `OperationReceipt`, `OperationStatus`, `RuntimeDomain.PARTICIPANT` | Asynchronous acknowledgement/status for lifecycle mutations. It does not report participant action success. |
| Supervisory participant control | ADR-085/RUN-310, `ParticipantControlIntent` and control occurrences | Human/controller authority over participant decisions; not operational executor lifecycle. |
| Teardown | Execution-service resource release after drain | Does not terminate an episode, reset shared time, delete scenario services, or erase evidence. |

The control target is an admitted execution scope identified by run/target,
compiled autonomous policy address, and execution generation. It is not an
individual action name, backend process id, participant episode id, or URL.

## Portable Contract And Protocol Guardrails

### Exact action-to-target support

The current manifest has independent
`supported_autonomous_action_contracts` and
`supported_autonomous_target_addresses` lists. Their cross product is not an
execution claim. The compiled policy likewise carries action contracts and an
aggregate target set without preserving which action refers to which targets.

Issue #898 must extend `capabilities.participant_runtime` with one closed,
relational execution-binding entry that preserves at least:

- compiled participant action-contract address;
- every compiled target address required by that action's preconditions and
  effects, including the named service address when the target is a service;
- the selected participant-implementation/adapter binding or its safe
  apparatus reference;
- exact support/constraint and evidence references; and
- finite action, timeout, retry, and concurrency limits that apply to the
  binding.

Compiler output must preserve the same action-to-target relation. Admission
matches complete binding entries, never membership in two independent lists,
action-name conventions, resource-type guesses, native adapter discovery, or a
free-form manifest `constraints` string.

The binding extends `ParticipantActionAdmissionRequest` and the existing
participant implementation manifest/provenance join. It must not create a
second action request DTO, copy target-service configuration into SDL, or make
the backend manifest the participant implementation identity.

### Execution control and readback

Publish the minimum closed participant-runtime contract needed to carry an
execution control request and typed execution-service readback. Reuse
`OperationReceiptModel` and `OperationStatusModel` for mutation acknowledgement
and polling, and reuse `runtime-snapshot-v1` for the durable joined state. Do
not publish participant-specific copies of those envelopes.

The execution readback must distinguish:

- desired and observed execution lifecycle;
- execution generation and the request generation most recently observed;
- liveness/health from readiness to accept governed work;
- accepting-new-work, draining, quiescent, and terminal/resource-released
  conditions;
- admitted policy/binding/time declaration digests and execution-scope refs;
- bounded capacity, reserved/in-flight counts, and safe last-transition
  identity;
- per-policy scheduler-state references rather than copied scheduler cursors;
  and
- pacing-loss/deviation and evidence references rather than backend logs.

Health means the controller can make an observation. Readiness means the
admitted bindings, time authority, workers, and native adapters can accept
governed work for the observed generation. Neither is participant episode
`running`, generic `SnapshotEntry.status`, HTTP reachability alone, or proof
that an action executed.

Every mutating request carries the expected execution generation. The control
plane and backend reject a stale generation before reserving native work.
Completions from an older generation may be retained as bounded late/stale
evidence, but they cannot mutate current portable state or be silently retried.
Execution generation must not be overloaded onto `episode_id`, clock segment,
policy digest, operation id, snapshot schema version, or control-history head.

### Lifecycle semantics

- **Start** binds the admitted execution scope and generation, proves
  readiness, and then permits due-action reservation. A receipt acknowledging
  the request is not readiness.
- **Pause** stops new reservations and preserves continuation. It must
  coordinate with the bound shared-time authority or record explicit pacing
  loss; allowing the clock to skip a due coordinate remains invalid.
- **Resume** revalidates generation, bindings, readiness, shared-time state,
  and missed-coordinate rules before accepting work.
- **Drain** rejects new reservations, waits only within a declared finite
  bound for in-flight native calls, and ends quiescent or failed/degraded with
  explicit unresolved-operation evidence.
- **Reset** uses the existing atomic shared-time/participant reset contract
  when scenario semantics require reset, then advances execution generation.
  Replacing a snapshot or scheduler cursor is not native rollback.
- **Teardown** is idempotent after drain, releases executor/adapter resources,
  and forbids future work for that generation while preserving operation,
  snapshot, behavior-history, and realized-time evidence.

Reset, teardown, timeout, cancellation, and transport failure do not prove that
an indeterminate native side effect did not occur.

### Bounded concurrency and commit safety

The current `ParticipantScheduler.run_due()` loops policies and participants
serially under the participant execution lock. `max_in_flight` is currently an
admission/accounting field, not proof of concurrent execution. Conformance must
reject a backend that claims bounded concurrency but only changes the counter
or runs the existing serialized loop.

Concurrency is bounded by the minimum of the policy, binding, backend-manifest,
and execution-service limits. Reservation increments in-flight accounting
atomically before native dispatch. Drain/reset/teardown close reservation
before waiting for or rejecting completions.

Native calls may run concurrently, but portable snapshot/history commit has one
revision/generation-checked owner. Workers must not share a mutable
`RuntimeSnapshot`, merge whole snapshots returned from the same predecessor, or
hold the global control-plane lock across unbounded native I/O. Build on
`ParticipantNativeActionExecution` and the `BaseParticipantRuntime` commit
path: execute against an immutable reservation, then validate and commit the
typed terminal result, behavior history, scheduler accounting, joint-action
record, and shared-state revisions against current generation.

Actual overlap and realized ordering use the existing RUN-308
`ParticipantJointActionRecordModel`,
`ParticipantTimeManagementContextModel`, shared-state revision/conflict
contracts, ordering basis, isolation guarantee, and interaction classes. Equal
ticks, multiple threads, a worker-pool size, or `in_flight > 1` alone do not
prove simultaneity, isolation, or conflict handling.

## Relevant Precedent

Internal precedent is controlling:

- ADR-013, ADR-022, ADR-041, ADR-054, ADR-060, ADR-066, ADR-072, ADR-085,
  ADR-090, ADR-091, and ADR-092;
- RUN-308 concurrency/joint-action/time-management carriers and RUN-311
  episode lifecycle;
- the issue #599 participant implementation-binding preflight, issue #861
  native autonomous-execution guardrails, and issue #897 activity-policy
  extension; and
- the issue #197 target/control-plane and issue #604 drain/teardown,
  idempotency, ownership, redaction, and snapshot-commit precedents.

External precedent supplies design criteria, not wire or semantic authority:

- [FMI 3.0.2 Scheduled Execution](https://fmi-standard.org/docs/3.0.2/)
  separates importer-controlled activation, state-machine legality, and
  termination quiescence; it explicitly does not make parallel computation
  part of the FMI API.
- [gRPC health checking](https://grpc.io/docs/guides/health-checking/) uses a
  distinct service health readback whose status is maintained by the
  implementation; endpoint presence is not health truth.
- [Google AIP-151](https://google.aip.dev/151) uses one reusable long-running
  operation resource and explicit parallel-operation behavior rather than a
  bespoke status type per lifecycle call.
- [Kubernetes Pod conditions](https://kubernetes.io/docs/concepts/workloads/pods/pod-condition/)
  bind a reported condition to the generation it observed, providing precedent
  for rejecting stale readiness.
- [OASIS TOSCA 2.0](https://docs.oasis-open.org/tosca/TOSCA/v2.0/cs01/TOSCA-v2.0-cs01.html)
  separates lifecycle interface operations from their implementation
  artifacts, supporting the RAES portable-operation/backend-owned-adapter
  boundary.

RAES adopts none of those APIs, schemas, lifecycle tokens, transports, or
compatibility claims.

## Canonical Cross-Cutting Incumbents

| Layer | Incumbent to extend |
| --- | --- |
| SDL ingress | `parse_sdl`, `load_sdl_yaml`, `SDLParserLimits`, safe YAML/duplicate/merge-key checks, and closed `SDLModel` shapes |
| Semantic validation | `raes.semantics.participant_behavior`, `raes.validator._participant_execution_renderers`, `raes.validator._time_model`, and existing action/target/service reference resolution |
| Compilation | `_compile_autonomous_execution`, `ParticipantAutonomousExecutionRuntime`, `ParticipantActionContractRuntime`, canonical address helpers, and canonical contract digests |
| Apparatus binding | `ParticipantImplementationManifestModel`, `ParticipantImplementationSelectionModel`, participant implementation provenance/configuration contracts, and `ParticipantActionAdmissionRequest` |
| Manifest/admission | `ParticipantRuntimeCapabilitiesModel`, `ParticipantRuntimeCapabilities`, manifest round-trip adapters, `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, `participant_runtime_capability_contract_gaps()`, `participant_autonomous_execution_capability_gaps()`, and `_participant_execution_diagnostics()` |
| Runtime target | `RuntimeTarget`, `RuntimeTargetComponents`, `BackendRegistry`, `_validate_runtime_target_shape()`, `_require_invokable_method()`, and capability-specific protocols on `participant_runtime` |
| Native execution | `AutonomousParticipantRuntime`, `BaseParticipantRuntime`, `ParticipantNativeActionExecution`, `ParticipantActionApplyResult`, `autonomous_action_result_violation()`, and backend-owned adapter leaves |
| Scheduling/time | `ParticipantScheduler`, scheduler operation helpers, `RuntimeParticipantExecutionMixin`, `ParticipantClockDriver`, `RuntimeTimeControlMixin`, `TimeRuntime`, and coordinated reset protocols |
| Concurrency | RUN-308 joint-action, time-management, shared-state revision/conflict, ordering, isolation, and interaction-class contracts/validators |
| Control plane | `RuntimeControlPlane`, `execute_participant_action()`, `create_control_plane_app()`, `OperationReceipt`, `OperationStatus`, request fingerprints, and idempotency records |
| Persistence | `RuntimeSnapshot.participant_autonomous_execution_states`, first-class participant/time/history maps, `ControlPlaneStore`, `InMemoryControlPlaneStore`, and `LocalControlPlaneStore` |
| Result validation | `_call_backend_apply()`, `participant_runtime_state_contract_diagnostics()`, `participant_runtime_history_transition_diagnostics()`, and `require_participant_autonomous_runtime_snapshot()` |
| Observability | `Diagnostic`, `AuditEvent`, operation records, typed runtime snapshots/history, realized-time provenance, and `operational_apparatus_summary()` |
| Conformance | `profile_for_manifest()`, `_target_adapter_cases()`, target live probes, snapshot semantics, `time_model_conformance_diagnostics()`, backend fixtures/profiles, and bounded conformance reports |
| Publication/workflow | `ContractModel`, `schema_bundle()`, authored schemas and fixtures, schema-publication entries/manifest, canonical nox `verify`, Ground Control traceability, and release-please |

Do not duplicate these as pack DTOs, backend-local public schemas, API-only
models, worker-state repositories, or adapter-specific exception/log streams.

## Whole-Path Security And Validation Gates

1. **SDL/parser gate.** Action, target, participant, policy, time, and
   implementation refs still pass parser limits, closed authoring models,
   semantic validation, canonical compilation, and address resolution. No
   endpoint, URI, command, adapter name, credential, or worker configuration is
   accepted from an untyped action field.
2. **Configuration and secret-reference gate.** Participant implementation
   configuration continues through
   `ConfigurationTargetRegistryModel` and the existing literal versus
   `secret-reference` validators. Manifests, bindings, control requests,
   receipts, snapshots, history, and provenance carry safe refs/digests, never
   resolved credentials. Issue #898 adds no environment-variable binding or
   secret resolver.
3. **Manifest/admission gate.** Closed manifest models, controlled
   vocabularies, exact relational binding entries, finite limits, required
   contract ids, and term-level evidence all agree across internal and wire
   models. Independent action/target membership, method presence, installed
   adapter libraries, or schema publication cannot satisfy admission.
4. **Runtime-target gate.** Component presence still matches the manifest.
   Claimed lifecycle, concurrency, native binding, coordinated reset, and time
   behavior require invokable capability-specific methods, but signature probes
   remain structural only; live conformance proves behavior.
5. **Control-plane authentication gate.** New HTTP mutations stay inside
   `create_control_plane_app()` with `ControlPlaneSecurityConfig.strict_defaults()`,
   bearer or verified-proxy identity, operator/backend mutating roles,
   `ControlPlaneIdentity.target_name` binding, request-size limits, request
   fingerprints, idempotency keys, and `AuditEvent`. Executor operations are
   target operations, not RUN-310 participant-subject authority and not
   auditor mutations.
6. **Remote-target/SSRF gate.** A request names only admitted canonical
   execution/action/target addresses. Backend registration resolves those to
   preconfigured adapter leaves. Caller-supplied URLs, sockets, hostnames,
   connection strings, filesystem paths, commands, and arbitrary headers never
   cross the portable control boundary.
7. **Backend apply/commit gate.** `_call_backend_apply()` retains baseline
   copying, exception wrapping, result-shape validation, snapshot semantic
   validation, append-only history checks, and invalid-result rejection.
   Generation/revision checks run both before native reservation and before
   completion commit. No stale or failed result replaces durable current state.
8. **Persistence gate.** Service readback gets a first-class closed snapshot
   field/carrier; scheduler continuation stays in
   `participant_autonomous_execution_states`; action evidence stays in behavior
   history; time stays in `time_model_state` and realized-time provenance.
   `RuntimeSnapshot.metadata`, `ApplyResult.details`, audit reason text, and a
   new participant database are not state stores.
9. **OS/process gate.** Backend adapters use in-process APIs or fixed argv with
   no shell, bounded input/output/time, controlled working directory and
   environment, and no credentials or action payloads in argv. Worker,
   process, thread, host, pid, socket, and backend-native object ids stay
   private unless a safe evidence reference explicitly governs them.
10. **Error-envelope gate.** Expected failures are bounded `Diagnostic`
    values in existing operation status and conformance reports. Conflict
    responses disclose only safe lifecycle/generation codes. The generic
    redacted HTTP 500 handler remains the unexpected-error boundary; raw
    Pydantic inputs, adapter errors, tracebacks, paths, command output,
    credentials, and backend reprs do not cross it.
11. **Observability gate.** Typed receipts, statuses, health/readiness,
    snapshots, behavior histories, joint-action/time-management records,
    realized-time deviations, and audit events are the evidence surface. Logs
    may carry safe ids, generations, counts, durations, and stable low-cardinality
    codes only. Do not create a second audit log, evidence stream, logger, or
    metric schema as contract authority.

## Extensibility, Compatibility, And Traceability

The primary extension seam is a versioned execution-binding entry plus a
versioned execution-control/readback contract on the incumbent participant
runtime component. A new product adapter adds a binding implementation and
evidence; a new lifecycle operation or state-machine meaning requires a new
contract version. Neither requires new SDL participant semantics, a new
control plane, or edits to pack-local schedulers.

Concurrency policy remains parameterized by finite capacity, per-binding
limits, isolation/conflict guarantee, drain timeout, and execution generation.
The next reasonable variation—another service adapter or a backend-native
scheduler—must fit behind that seam while preserving the same request,
readback, history, time, and conformance contracts.

Existing backends that do not claim portable autonomous execution remain
valid. A backend that already claims `supports_autonomous_execution` must add
the new contract ids, relational bindings, lifecycle/readback support, and live
evidence before the released capability can remain truthful; silent inference
or compatibility fallback is forbidden. Follow ADR-061/075 for additive versus
breaking schema/profile changes and migration notice.

Do not create a new backend profile merely to name this optional capability.
Extend the existing conditional participant-runtime capability/evidence checks
and the `FULL_REMOTE_CONTROL_PLANE` live-probe path when the manifest claims
autonomous execution. A profile or schema file is not execution evidence.

There is no Ground Control requirement UID to invent. Traceability must join
issue #898, the ADR-092 amendment, normative contracts/specification, manifest
claim, runtime and backend implementation, focused/live/negative conformance
cases, PR, released package, migration guidance, and the external consumer
`autarchy-ai/penumbra-scenarios#556`. Release-please owns `CHANGELOG.md` and
package versioning.

## Gotchas And Anti-Patterns

Avoid:

- a `participant_executor` target component, pack-owned scheduler/control API,
  second action request, second time service, or second operation store;
- treating episode initialize/reset/restart/terminate as executor
  start/reset/teardown;
- treating RUN-310 supervisory control intents as operational scheduler
  lifecycle;
- inferring action-to-target support from separate lists or treating every
  supported action as executable against every supported target;
- discovering adapters from action names, ATT&CK/tool labels, URLs, environment
  variables, imports, reflection, or native resource types;
- claiming concurrency from `max_in_flight`, thread count, same-tick execution,
  or overlapping log timestamps without RUN-308 evidence;
- concurrent mutation or last-writer-wins merging of whole runtime snapshots;
- holding a global lock across unbounded native service I/O;
- accepting stale completions after reset/teardown, or replaying indeterminate
  native actions after a timeout or transport error;
- allowing executor pause to advance past due shared-time coordinates without
  a governed disposition and pacing-deviation evidence;
- treating health, readiness, receipt acceptance, action outcome, episode
  status, and control-plane operation status as synonyms;
- treating drain as cancellation, teardown as scenario-resource deletion, or
  snapshot replacement as native rollback;
- placing credentials, adapter endpoints, raw service state, native ids,
  commands, argv, stdout/stderr, tracebacks, or environment dumps in portable
  artifacts; and
- adding duplicate schemas, validators, exception hierarchies, repositories,
  audit logs, fixture runners, conformance engines, or release workflows.

## Non-Goals And Implementation Boundaries

- No Penumbra, KeplerOps, product, service, deployment, pack, historical-data,
  or private scheduler semantics enter RAES.
- No new SDL actor, action, target-service, clock, calendar, workflow, or
  evaluation authority is introduced.
- RAES specifies portable bindings, lifecycle meaning, control/readback, and
  evidence; each backend owns adapter implementation, worker topology,
  transport, deployment, credential resolution, and native resource cleanup.
- The reference runtime need not prove production throughput, human realism,
  exactly-once native side effects, native rollback, or universal concurrency
  equivalence.
- This issue does not redesign participant episodes, supervisory control,
  shared-time semantics, participant implementation identity, scoring,
  objectives, experiment allocation, or scenario-service lifecycle.
- Default verification remains hermetic and unprivileged. Real service/daemon
  proofs are explicit opt-in evidence and cannot replace portable negative and
  state-machine conformance tests.
