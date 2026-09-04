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

## Ownership and isolation interpretation

The current composition unit is one `RuntimeControlPlane`, one
`RuntimeTarget`, and one isolated live-state store. The target owns backend
component identity and capability declarations. The control plane owns
operations and live participant state for that unit. Participant state remains
keyed by canonical participant address inside the snapshot.

The embedding application, not the control plane, owns the mapping from an
authored scenario, experiment run, or caller population to control-plane
instances and store locations. P0--P2 do not multiplex independent targets,
runs, or service tenants in one store. A P2 service may have many authenticated
clients, but it is still one target/run authority and not a multitenant service.
The authored `deployment_tenants` from ADR-087 are scenario topology; they are
not API tenancy, storage namespaces, or authorization principals.

Persistent stores must pin their immutable target and embedder-supplied run
scope at creation and refuse a mismatched reopen. Operation ids and
idempotency claims are meaningful only inside that store scope. At P2 an
idempotency claim is additionally scoped by authenticated actor and operation
kind, so one caller cannot collide with or recover another caller's receipt.
Supporting multiplexed runs, deployment tenants, or targets is P3 work and
requires a future decision about namespace and authorization isolation.

Direct `RuntimeManager.apply()` and direct backend calls remain outside the
profile guarantees. They do not become durable merely because another control
plane in the process uses a P1 store.

## Canonical incumbents

Implementation must extend these existing owners instead of creating parallel
contracts or policy stacks:

- `raes_contracts.runtime_state` owns `RuntimeSnapshot`, `OperationReceipt`,
  `OperationStatus`, and `OperationState`; the closed Pydantic boundary models
  live in `raes_contracts.contracts` and publish through
  `schema_bundle()` into `contracts/schemas/control-plane/` and
  `contracts/schemas/snapshots/`.
- `RuntimeControlPlane`, `ControlPlaneStore`,
  `InMemoryControlPlaneStore`, and the participant transition commit methods
  are the runtime and persistence incumbents. Every mutating entry point,
  including workflow cancellation, timeout reconciliation, participant
  crossings, and rejected submissions, must use the same operation/commit
  discipline; "generic execution" is not permission for a second workflow.
- `RuntimeTarget`, `_validate_runtime_target_shape()`, backend manifests, and
  `raes_backend_protocols` own target capability and backend call shape.
  `_call_backend_apply()` and its result validators/sanitizers remain the only
  acceptance boundary for backend-produced snapshots.
- `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`,
  `_ControlPlaneApiAuth`, `RequestSizeLimitMiddleware`, and
  `_ControlPlaneCallExecutor` own HTTP composition, authentication,
  authorization, bounded request admission, worker offload, and overload.
- `Diagnostic`, `ApplyResult`, the stable redacted FastAPI error handlers, and
  `AuditEvent` are the existing failure and audit carriers. Provider-native
  errors do not define a second public exception or error-envelope hierarchy.
- `value_free_account_placement_payload()`,
  `sanitize_account_credential_result()`, and value-free backend diagnostics
  own the credential egress rule. ADR-057 remains the boundary between
  scenario facts and operator/out-of-scenario secrets.
- `raes_contracts.canonical` owns canonical JSON commitments. Request and
  semantic fingerprints must reuse it with an operation-specific domain
  separator rather than adding another serializer or digest convention.
- ADR-065 and ADR-066 keep mutable live state, control-plane operational audit,
  participant observations, captured evidence, derived analysis, and archival
  `experiment-run-v1` provenance distinct. A store row or audit event is not a
  second run-provenance record.
- ADR-009, ADR-061, the schema publication manifest,
  `tools/check_generated_schemas.py`, and `tools/check_schema_publication.py`
  govern any portable contract change. ADR-036 and
  `tools/policy/adr_policy.yaml` govern package imports. The canonical repo
  verification graph remains `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, and `tools/verify_all.py`.

## Cross-cutting gates

- **Contract and shape gate.** External JSON first passes the existing
  `ContractModel(extra="forbid")` Pydantic DTOs. Persisted snapshots and
  operation carriers must be validated against those same models before domain
  reconstruction; a provider must not accept unknown fields, coerce corrupt
  values with `str(...)`, or default missing identity/state fields. Store
  revision, lease, migration, and engine metadata remain provider-internal and
  must not be smuggled into `RuntimeSnapshot.metadata` or a duplicate public
  DTO.
- **Semantic and backend-return gate.** Target/manifest agreement continues
  through `_validate_runtime_target_shape()`. Submitted plans retain the
  existing target, manifest, base-snapshot, planner-authorization, and backend
  validation checks. Backend results continue through `_call_backend_apply()`,
  snapshot transition validators, participant information-state/crossing
  validators, realization-authority checks, and credential sanitization before
  any terminal commit.
- **Authentication and authorization gate.** P2 keeps fail-closed security
  defaults, constant-time bearer resolution, explicit opt-in to verified proxy
  headers, exact target binding, role checks, and the separate participant
  control-subject and audience-subject bindings. Store ownership, a valid
  idempotency key, or possession of an operation id grants no authorization.
  Trusted proxy deployment must strip caller-supplied identity headers.
- **Secret and configuration gate.** Bearer tokens, storage credentials,
  encryption material, host paths, raw request bodies, and backend exception
  text are operator data, not portable runtime state. They must never enter
  snapshots, operation records, audit details, diagnostics, health responses,
  migrations, fixtures, or logs. There is no incumbent control-plane
  environment loader or serve command; profile/store/security configuration
  therefore remains an explicit typed composition input. If an embedder binds
  environment or secret-manager values, it resolves them once at that boundary
  and passes values in memory, never through process argv or a portable schema.
- **HTTP admission and error-envelope gate.** Request-size admission occurs
  before FastAPI parsing; mutation and rejection-audit queues stay bounded.
  Pydantic validation retains the stable redacted 422 response, unexpected
  failures retain the stable redacted 500 response, and overload retains the
  existing 503/`Retry-After` behavior. Lease, revision, migration, recovery,
  and idempotency conflicts must be mapped to stable coarse responses or
  `Diagnostic` codes rather than returning `str(provider_exception)`.
- **Filesystem and OS gate.** A P1 store root is trusted operator configuration,
  never a path assembled directly from a target, tenant, scenario, run, or
  idempotency string. The owner must reject symlinks and non-regular files,
  enforce owner-only directories/files, verify file identity across opens,
  durably fsync data and directory-entry changes, and acquire the owner lease
  before schema inspection, migration, cache load, or reconciliation. P2 runs
  exactly one application worker for that store; application-local locks and a
  shared database do not make multi-worker invocation safe. TLS termination,
  reverse-proxy trust, service-account permissions, backup permissions, and
  process supervision remain deployment responsibilities and must be stated by
  the embedder.
- **Observability gate.** Operational logs use module loggers and bounded,
  value-free fields. The transactional audit carries stable action, actor,
  target, operation, outcome, and coarse reason data; arbitrary request or
  provider payloads do not belong in `AuditEvent.details`. Append-only means no
  logical rewrite, not tamper evidence. Health reports profile/capability,
  lease, migration, recovery, and store status without returning paths,
  identities beyond authorization scope, tokens, SQL, or exception text.
- **Lifecycle gate.** Lease acquisition precedes reads and reconciliation;
  readiness follows successful schema/integrity checks and reconciliation;
  shutdown first stops admission, drains the one mutation authority, commits
  or records indeterminacy, closes the provider, and releases the lease.
  Request cancellation or a Python thread timeout never proves that a backend
  effect stopped. Scenario time (`TimeRuntime`) is not the wall clock used for
  operation leases, deadlines, audit timestamps, or recovery.

## Extension seams

Profile declaration and provider capability discovery are the primary seam:
the core requests atomic claim, revision-CAS terminal commit, lease, audit, and
recovery-observation capabilities and fails construction when its selected
profile cannot supply them. Profile names and guarantees need one canonical
typed definition; do not duplicate them across store classes, HTTP routes, and
configuration parsers.

Backend effect observation extends the existing `RuntimeTarget`/backend
protocol and manifest pattern with neutral contract DTOs; a persistence
provider must not call backend-native APIs. A future P3 supplies coordination,
scheduling, fencing, and cache-coherence implementations behind the same
capability boundary. It must not be enabled by swapping in a "shared" database
or adding another application worker.

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
- No API/service tenancy, cross-target store, run scheduler, durable broker,
  automatic backend replay, or exactly-once external-effect claim.
- No replacement for `experiment-run-v1`, captured-evidence contracts,
  participant observation envelopes, or backend manifests.
- No serve command, deployment unit, TLS terminator, secret resolver, backup
  scheduler, or operating-system sandbox is introduced by the design issue.

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
- The atomicity and lock review applies to every store mutation, not only
  `execute_operation()`. `cancel_workflow()`, timeout reconciliation, rejected
  submissions, participant actions, crossings, and audit appends cannot retain
  independent save-snapshot/save-record workflows.
- `RuntimeSnapshot`, its Pydantic envelope, the HTTP projection, and the store
  codec already form multiple representations. They must converge on one
  strict codec/validation path; adding revision fields independently to each
  will multiply drift. Store-only metadata must remain outside the portable
  snapshot.
- An `indeterminate` terminal record is immutable history. Operator resolution
  creates a linked follow-up operation and audit event; it does not rewrite the
  original terminal outcome or discard its idempotency claim.
- Control-plane operation state, workflow status, participant lifecycle, and
  backend effect state are different state machines. Do not add
  `indeterminate` to all of them or use one transition to imply another.
- Audit persistence in a terminal transaction does not turn operational audit
  into participant-visible observation, captured evidence, archival run
  provenance, or tamper-evident logging.
- Raw HTTP-body fingerprints and unscoped client keys are not a complete
  idempotency design. Keys must be bounded and actor/operation/store scoped;
  fingerprints must be domain-separated, value-free commitments over the
  admitted semantic request using the existing canonicalization helpers.
- "One process" includes one ASGI worker. Forked/preloaded workers, multiple
  app instances, and two control-plane objects over one store must fail
  ownership admission rather than relying on deployment documentation.
