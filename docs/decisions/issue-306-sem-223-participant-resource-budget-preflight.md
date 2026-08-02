# Issue 306 SEM-223 Participant Budget, Quota, And Exhaustion Preflight

Issue: #306

Requirement: SEM-223.

Date: 2026-08-02

This note records the repository-wide boundary for SEM-223. It is guidance
only: it adds no SDL syntax, schema, contract, runtime, backend, API, storage,
or implementation plan.

## Binding Decision

ADR-097 and `specs/formal/participant-semantics/autonomous-execution.md` V3
already own the semantics required by SEM-223. An implementation must extend
that one participant-resource-budget family, not create a generic quota
facility or a second execution path.

Keep four authorities separate and join them only by the canonical typed
identities already defined by that family:

| Fact | Canonical owner |
| --- | --- |
| Authored/admitted limit and demand | `ParticipantResourceBudgetPolicy` and compiled resource demands |
| Configured logical capacity and isolation | `ParticipantResourcePoolCapacity` in `backend-manifest-v2.capabilities.participant_runtime` |
| Current reservation, use, and exhaustion | `ParticipantResourceBudgetState`, `ParticipantResourcePoolState`, and append-only budget events in `RuntimeSnapshot` |
| Measured realization | exact native measurement vector and evidence refs, projected through existing history, operation, and conformance surfaces |

Participant episode reset, execution generation, tenant/shared-service/fleet
ownership, scheduler lifecycle, and shared-time segment are distinct axes.
In particular, an episode or segment reset must not erase aggregate use,
capacity, or active leases unless that resource's declared reset/reconciliation
owner permits it.

## Required Reuse And Admission Path

- **Authoring and semantic admission:** use `load_sdl_yaml`, `SDLParserLimits`,
  closed `SDLModel` shapes, `SemanticValidator`, composition rewriting, and
  `instantiate_scenario` / `admit_instantiated_scenario`. Do not accept a
  budget from an environment variable, a free-form `constraints` field, or an
  unvalidated backend dictionary.
- **Portable contracts and compilation:** reuse the closed
  `ParticipantResource*` models, `schema_bundle()`, published-schema ledger,
  canonical compiler addresses, and the V1/V2 legacy projection. A new
  resource kind belongs in the governed resource-kind/meter-profile catalog
  and accounting-mode conformance table; it is not a free-form map key, unit,
  or provider-specific field.
- **Planner/backend admission:** reuse
  `participant_resource_budget_gaps()` and the existing participant-runtime
  manifest capability root. Admission is all-or-nothing across the complete
  resource vector, owner/parent graph, meter, reset mode, configured pool,
  isolation, fairness policy, and execution binding.
- **Runtime/persistence:** reuse the participant scheduler resource hooks,
  `reserve_participant_resources`, settlement/reconciliation functions,
  `ControlPlaneStore` atomic transition pattern, `RuntimeSnapshot`, and
  generation fencing. A single canonical physical-pool ledger owns every
  shared allocation; service `capacity`/`reserved`/`in_flight` remain a
  validated projection, never an independently mutable counter.
- **Errors and evidence:** reuse `Diagnostic`, `ApplyResult`,
  `OperationReceipt`/`OperationStatus`, `AuditEvent`, existing histories, and
  conformance reports. A throttle/rejection is a typed, safe event and
  diagnostic; it is not a new exception hierarchy, raw backend error, log
  message, or telemetry-only fact.

## Cross-Cutting Security And Operational Gates

1. Source ingress applies safe YAML construction, duplicate/merge-key and
   source-size/alias/node limits before closed-model and relational semantic
   validation. Unknown fields and invalid owner, parent, meter, unit, or reset
   relations fail closed.
2. Instantiated artifacts, compiler output, planner admission, runtime-snapshot
   validation, and conformance validation must preserve the same canonical
   resource identity; no layer may recompute it from strings or backend ids.
3. A control-plane mutation uses `ControlPlaneSecurityConfig` authentication,
   backend/operator authorization, target binding, request-size limits,
   idempotency/request fingerprints, atomic durable commit, and `AuditEvent`.
   Readback uses existing read authorization and audience/tenant markings.
4. Portable artifacts, diagnostics, HTTP error envelopes, audit records, and
   telemetry contain only logical ids, bounded quantities, meter/profile refs,
   digests, dispositions, and evidence refs. They exclude credentials, bearer
   tokens, prompts, model inputs/outputs, images, host paths, device ids,
   backend-private objects, environment dumps, and raw tracebacks. Do not put
   secrets in process argv or capability configuration.
5. OCI/cgroup limits, service-side quotas, filesystem quotas, accelerator
   claims, and tenant partitions are backend realization evidence, not portable
   proof. Capability support, configured capacity, current availability, and
   measured use remain non-interchangeable.

## Guardrails, Non-Goals, And Anti-Patterns

- Reserve the complete vector atomically before native work; commit only an
  exact bounded measurement vector with matching operation, generation,
  resource, unit, meter, and evidence. Cancellation, timeout, stale
  completion, failure, teardown, and reset release or reconcile exactly once.
- Preserve append-only history and generation fencing. Do not delete prior use
  on reset, treat a copied snapshot as native rollback, or allow a retry to
  bypass an exhausted parent/pool.
- Do not infer priority from participant role, evaluation authority, source
  order, or tenant identity. Fairness, borrowing, reclaim, queue, and
  starvation obligations are explicit and evidence-bearing.
- Do not conflate an evaluation/audit budget with an enforced participant
  resource budget; it becomes one only when this runtime accounting path
  enforces the resource.
- Do not select a provider, scheduler, tokenizer, accelerator, billing model,
  cloud project, or telemetry format. SEM-223 neither proves throughput,
  fairness, isolation, OS enforcement, nor exposes private model/evaluator
  material.
