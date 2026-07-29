# Issue 788 SCE-002 Admitted Trial-Plan Contract Preflight

Date: 2026-07-28

Issue: #788.

Requirements: SCE-002 and SCE-006.

This note fixes architecture guardrails for the schedule-independent admitted
trial-plan contract before implementation. It is guidance only: it does not
publish a schema, add a contract model or validator, compile or admit a plan,
instantiate SDL, schedule or execute a trial, persist an artifact, add
fixtures/tests, or define an implementation plan.

## Architecture Decisions And Boundaries

### Publish one admitted execution-intent root

- Publish one closed portable admitted-plan root, following the established
  `*-v1` contract lineage and `ContractModel(extra="forbid")` conventions. Do
  not add a draft-plan, campaign, trial, queue, batch, scheduler-job, or run
  root alongside it.
- The portable lifecycle has one immutable successful state: admitted and
  sealed. Candidate construction and validation are processor-internal.
  Queued, leased, running, cancelled, timed-out, retried, completed, and
  cleaned are attempt/runtime/evidence states and must not mutate the plan.
- The plan is complete only when every policy has an explicit outcome, every
  coordinate and archival `run_id` is allocated, every binding target is
  resolved, every required reference is pinned, and every entry carries or
  resolves all schedule-independent execution controls. A policy reference may
  remain as provenance; an unresolved sample, default, query, backend choice,
  fact lookup, or secret lookup may not.
- A scheduler consumes an entry together with the sealed plan's immutable
  shared blocks. It must not need the experiment-authoring document and must
  not interpret SDL, allocation policies, factor semantics, random streams, or
  apparatus-selection rules.

### Keep the identity graph explicit and acyclic

The contract must preserve these distinct identities:

| Identity | Authority and meaning |
| --- | --- |
| plan content identity | Canonical digest of the complete admitted plan |
| `plan_entry_id` | Stable logical entry identity derived under the entry-identity profile; never collection position |
| `run_id` | Preallocated archival identity used by `experiment-run-v1` if execution starts |
| cleanup `plan_id` | Identity of one `TrialCleanupPlanModel`, referenced by its cleanup receipt |
| `execution_attempt_id` | Runtime identity of one started attempt; absent from the admitted plan |
| operation/job/snapshot ids | Control-plane, scheduler, or runtime identities; never aliases of the above |

Do not add a second `trial_id`. In this architecture, the admitted entry and
its preallocated `run_id` provide stable trial intent, while
`execution_attempt_id` distinguishes attempts. An idempotent transport retry
before execution reuses the entry and `run_id`; a genuine re-execution requires
a new admitted coordinate and `run_id`.

The integrity dependency must be one-way:

```text
logical coordinate + pinned admitted inputs + identity profiles
  -> plan_entry_id and run_id
  -> cleanup-plan identity
  -> entry canonical digest
  -> complete-plan canonical digest
```

The digest fields themselves are excluded from their own canonical
projections, and no child points back to the enclosing plan digest. In
particular, `TrialCleanupPlanModel.plan_id` is the cleanup-plan identity, not
the admitted-plan identity. Making `plan_entry_id` equal to an entry digest
that embeds the same id, or placing the root digest inside entries, creates a
cycle and is prohibited.

Use RFC 8785/JCS plus SHA-256 through the existing
`canonical_contract_digest()` semantics. If its current satisfiability-module
placement is unsuitable, extract the same dependency-neutral helper rather
than creating a trial-plan serializer. The plan profile/domain separation and
all identity-bearing content must be inside the canonical projection. A
keyed-entry map with key/embedded-id equality, or a list whose canonical order
is validated, must make input reordering irrelevant. The root commits both to
each entry and to the complete entry set.

### Reuse owning contracts; project rather than duplicate meaning

- Reuse `TrialCoordinateModel` as the only logical-coordinate DTO. The
  coordinate profile is the extension seam and admits a closed set of named
  dimensions. It must cover the ADR/reference dimensions needed for condition,
  block/cohort, replicate, and explicit re-execution ordinal without adding a
  plan-only coordinate or arbitrary `dimensions` map.
- Reuse `ExperimentSelectionOutcomeModel` for selected values and
  `ExperimentSelectionPolicyModel` ids/kinds as provenance. A plan-owned
  selection record may add the qualified point, origin, and resolved policy
  reference, but must not copy the outcome union or execute a policy.
- Reuse `ExperimentBindingDescriptorModel` and the owner-specific target
  admission in `validate_experiment_binding_targets()`. Do not infer a target
  from parameter names, JSON pointers, `${...}` occurrences, manifest fields,
  or backend options.
- `RealizedBindingProvenanceModel` means a binding actually realized by its
  owner. Do not relabel admitted intent as realized provenance. The plan may
  carry the admitted descriptor and selection/default origin; #790 and the
  existing run contract own actual realization.
- `InstantiationRequestModel` may be an exact projection for non-secret scalar
  parameters, but its open `parameters: dict[str, Any]` is not an authority
  surface by itself. If carried, cross-validation must prove that it is exactly
  the safe projection of admitted typed bindings and contains no unresolved or
  secret value. Structural selections and origins remain explicit alongside
  it. Prefer the equivalent governed binding artifact over widening
  `parameters` into a policy bag.
- Reuse `ExperimentStochasticControlModel`,
  `RandomStreamControlBindingModel`, `RandomStreamDrawRecordModel`, and
  `StreamAddressModel`. Every stochastic entry outcome must resolve one exact
  executable control/profile/transform and record the explicit outcome or
  governed reference. A seed, descriptive stochastic control, or policy ref
  alone is incomplete.
- Reuse `TrialCleanupPlanModel` and `ExecutionRetryPolicyModel` for clean
  state, terminal-triggered cleanup, reset/compensation, verification, and
  after-effect retries. Reuse `SchedulerIsolationProofModel` at plan scope for
  any non-serial bound. Do not copy cleanup obligations or isolation
  dimensions into new trial-entry fields.
- A minimal plan-owned execution-control value may state an attempt timeout
  and the required cancellation/timeout/abort disposition because no existing
  portable DTO owns whole-trial attempt policy. It must compose with cleanup
  triggers and existing control-plane cancellation/timeout handling; it must
  not contain worker, queue, placement, host, lease, or mutable status data.
- `ExperimentTaskModel`, `ExperimentSpecModel`, and
  `ExperimentStudyModel` remain the authorities for task, design, factors,
  conditions, allocation, replication, stopping, and analysis. The plan pins
  exact references/digests and carries validated per-entry projections needed
  for execution. Repeated assignments must be equality-checked against those
  owners and are not independent definitions.
- `ExperimentApparatusContextModel` is an observed run-scoped archival
  artifact and must not be fabricated before execution. Plan intent instead
  reuses `ExperimentApparatusConstraintModel`, digest-bound
  `ExperimentManifestReferenceModel` values,
  `RealizationEnvelopeIdentityModel`, capability/profile refs, and admitted
  configuration identities. The later run owns observed apparatus context and
  realized-form disclosure.
- Required associated artifacts remain governed by
  `AssociatedArtifactManifestModel`, `ExperimentArtifactRefModel`, checksum,
  sensitivity, URI-safety, and byte-binding validators. The plan pins exact
  artifact/set identities and digests; it does not become another artifact
  catalog or copy credential-bearing locators.

The generic experiment reference vocabulary may be narrowed for plan-owned
input fields, but do not weaken existing specializations such as
`ExperimentTaskReferenceModel` or generic authored-scenario id-only semantics.
Exact plan inputs need version/digest checks against concrete supplied
artifacts, not a looser global reference rule.

### Separate structural, plan-local, and cross-artifact validation

- Structural validation belongs to the closed contract models and published
  JSON Schema: required fields, strict scalar/value unions, bounds, map-key
  equality, canonical identifier shapes, and forbidden extras.
- Plan-local semantic validation owns coordinate/entry/run/cleanup uniqueness,
  canonical ordering, entry/root digest recomputation, reference resolution
  within the plan, stochastic-control/draw joins, cleanup identity joins,
  complete materialization, execution-control consistency, and declared
  cardinality/budget equality.
- Cross-artifact admission validates the supplied task, experiment spec,
  composed family, binding descriptors, associated artifacts, selected
  manifests/capabilities, realization envelope, cleanup capability, and
  profiles against the plan's exact refs/digests. It consumes authoritative
  objects and returns bounded diagnostics; it does not fetch, select, sample,
  instantiate, repair, or compile them.
- #789 owns deterministic trial-set compilation and full admission. It must
  call these contract validators rather than reproduce their invariants. #788
  may validate a fully assembled candidate plan, but it must not implement
  selection, allocation, run-id generation, or fallback behavior.
- Any error produces a deterministic bounded `DiagnosticModel` set and no
  admitted artifact. A sealed plan may carry safe success-stage/profile/count
  facts and limitations, but never failed partial entries or raw validation
  payloads.

## Required Incumbents And Whole-Repo Reuse

- **Normative authority and publication:** ADR-009, ADR-019, ADR-061,
  `specs/authority/authority-boundary.yaml`, `contracts/schemas/`,
  `contracts/fixtures/`, per-contract records under
  `contracts/schema-publication/entries/`,
  `contracts/schema-publication-manifest.json`, `schema_bundle()`,
  `raes_contracts.versions`, `tools/generate_contract_schemas.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, and `x-raes-invariants`.
- **Scenario family and instantiation:** `load_sdl_yaml`, composition budgets,
  duplicate/canonical-key validation, module lock/digest/signature/path gates,
  `Scenario`, `ExpandedScenario`, variation-point semantic validation,
  `instantiate_scenario()`, `admit_instantiated_scenario()`,
  `InstantiationProvenance`, `SemanticDigest`,
  `canonical_instantiated_sdl_bytes()`, and SDL exception families.
- **Experiment design and bindings:** `parse_experiment_spec()` and its 64 KiB
  bounded duplicate-key/alias-rejecting loader, `ExperimentSpecModel`,
  `ExperimentRunPlanModel`, `ExperimentRunAllocationPlanModel`,
  `ExperimentConditionAssignmentModel`, selection policy/outcome models,
  `ExperimentBindingDescriptorModel`,
  `validate_experiment_binding_targets()`, and the existing factor/condition
  joins.
- **Randomness:** the accepted random-stream profiles,
  `TrialCoordinateModel`, `StreamAddressModel`,
  `RandomStreamControlBindingModel`, `RandomStreamDrawRecordModel`,
  `load_random_stream_profile()`, and the existing run stochastic-control
  reference validator. Do not use Python `random`, UUIDs, witness seeds, or
  backend RNGs.
- **Apparatus and realization:** `ExperimentApparatusConstraintModel`,
  `ExperimentManifestReferenceModel`,
  `validate_experiment_apparatus_context_against_manifests()`,
  processor/backend manifest compatibility and capability admission,
  `RealizationEnvelopeIdentityModel`, `member()`/`subsumes()`, planner
  diagnostics, and artifact-requirement admission.
- **Scheduling controls already published:** `TrialCleanupPlanModel`,
  `validate_trial_cleanup_receipt()`, `SchedulerIsolationProofModel`, backend
  cleanup capability/conformance, `WorkflowExecutionContract`,
  `WorkflowCancellationRequestModel`, `workflow_timeout_update()`, and
  existing control-plane operation submission/status/cancellation.
- **Archive, evidence, and persistence:** `ExperimentRunModel`,
  `ExperimentStudyModel`, `ExperimentRunTraceabilityModel`,
  `validate_experiment_run_against_task()`,
  `validate_experiment_study_against_tasks_and_runs()`,
  `ExperimentEvidenceRecordModel`, associated-artifact manifests,
  `OperationReceipt`, `OperationStatus`, `RuntimeSnapshot`, and
  `ControlPlaneStore`. These remain separate authorities/stores.
- **Diagnostics, API security, and observability:** `Diagnostic` /
  `DiagnosticModel`, `ControlPlaneSecurityConfig.strict_defaults()`,
  verified bearer/proxy identity, `ControlPlaneRole`, target-bound
  authorization, `request_size_guard_response()`, idempotency keys/request
  fingerprints, append-only `AuditEvent`, the redacted HTTP 500 envelope, and
  module-local logging.
- **Repository workflow:** ADR-014, `.ground-control.yaml`,
  `.gc/plan-rules.md`, `noxfile.py`, `SessionReporter`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_semantic_coverage.py`, and `tools/verify_all.py`. Extend the
  canonical contract/test sessions; do not add another CI entry point.

## Cross-Cutting Security And Runtime Gates

1. **SDL source/composition gate.** The pinned family must already have passed
   bounded SDL source parsing, closed models, duplicate/canonical-key checks,
   import confinement, lock/digest/signature verification, namespace/cycle/
   collision validation, and whole-scenario semantic admission. The plan
   validator accepts typed admitted artifacts, not raw SDL dictionaries.
2. **Experiment ingress/config-shape gate.** Authoring input passes the
   canonical bounded duplicate-key/alias-rejecting
   `parse_experiment_spec()` path and its model/cross-artifact validators.
   Descriptive allocation, red-variant, parameter, or stochastic strings never
   become executable plan fields by convention.
3. **Plan parse/shape gate.** Portable plans are bounded JSON/typed DTO input,
   not a new YAML dialect. Enforce source-byte, entry, binding, draw, artifact,
   cleanup, diagnostic, and total-plan bounds before expensive validation.
   Reject duplicate JSON keys, non-finite numbers, coercion-dependent scalar
   values, unknown fields, unknown profile versions, and non-canonical
   identities.
4. **Binding/secret gate.** Literal and secret-reference values retain the
   discriminated shapes from experiment binding and runtime-fact contracts.
   Raw credentials, provider tokens, private keys, resolved secrets, secret
   hashes, environment-variable names used as secret locators, host paths, and
   backend-native handles are absent from selections, factors, plan bytes,
   identities/digests, fixtures, diagnostics, logs, and telemetry. Secret
   dereference remains a separate deny-first run-local operation.
5. **Environment/config gate.** Ambient environment, process-global RNG,
   worker config, backend defaults, mutable parameter stores, and runtime facts
   cannot affect plan identity or content. Authored runtime environment
   requirements continue to use `RuntimeEnvironmentVariable` classification,
   provenance, and omission rules; discovered values use typed late-bound
   sinks and cannot become pre-run selectors.
6. **Artifact/apparatus gate.** Every digest-qualified reference must match a
   concrete supplied payload. Associated-artifact URI and byte checks,
   manifest identity/version/digest checks, processor/backend mutual
   compatibility, capability admission, realization-envelope membership, and
   cleanup/isolation capability evidence remain mandatory. Availability drift
   is failure/deviation, never resampling.
7. **Authentication/authorization gate.** #788 adds no HTTP or mutating
   control plane. Any future plan read/admit/dispatch endpoint reuses strict
   defaults, verified identity, read-versus-mutate roles, target scope,
   request-size limits, idempotency/fingerprints, and audit records. Plan read,
   artifact dereference, secret dereference, and execution are separate
   authorizations.
8. **OS/process exposure gate.** Validation and canonicalization stay
   in-process over typed values or bounded files/stdin. Do not put plan JSON,
   seeds/entropy refs, parameter maps, selected values, secret refs,
   credentials, or evidence payloads in argv, shell interpolation, filenames,
   stdout/stderr, or environment captures. Any adapter retains fixed argv,
   `shell=False`, bounded timeouts/output, controlled working directories,
   path confinement, and redacted subprocess diagnostics.
9. **Error-envelope gate.** Expected failures use existing SDL exceptions at
   SDL boundaries and bounded `DiagnosticModel` values at plan/processor
   boundaries. HTTP unexpected failures remain
   `{"detail":"internal server error"}`. Expose safe codes, stages, JSON
   instance paths/canonical ids, profile ids, digests, and counts only; never
   raw Pydantic input, allowed domains, selected values, secret refs, raw
   documents, backend objects, environment dumps, host paths, or tracebacks.
10. **Logging/observability gate.** Logs and audit may contain safe
    plan/entry/run ids, digests, profile versions, counts, stage outcomes, and
    durations. They are not the scientific record and must not contain plans,
    bindings, draws, payloads, or evidence bodies. Inspectable intent and
    outcomes live in plan/run/study/evidence/cleanup artifacts.
11. **Persistence gate.** #788 publishes Git-tracked contract artifacts only.
    Do not store plans in `RuntimeSnapshot.metadata`,
    `ControlPlaneOperationRecord.details`, audit blobs, tags, scheduler memory,
    a mutable parameter database, or a new repository. A future artifact
    service must preserve immutable bytes/digests and apply separate read and
    execution authorization.

## Extensibility Seam

The required seam is an exact, versioned profile set carried by the plan:

- coordinate profile;
- plan-entry and run-identity profiles;
- plan/entry canonicalization and integrity profiles;
- compiler contract/profile;
- selection policy versions;
- random-stream profile/transform versions; and
- execution-control, cleanup, and isolation contract versions.

The next logical-coordinate dimension (for example cohort or explicit
re-execution ordinal), identity algorithm, random transform, cleanup action, or
execution-control policy adds one governed profile/closed union member and
fixtures/validators. It does not alter old profile output or require scheduler,
backend, run, study, and SDL schemas to learn a generic parameter bag. No
`latest` alias, import path, callback, plugin string, expression, or arbitrary
metadata map is an extension seam.

The scheduler-facing parameter is the admitted maximum parallelism/isolation
proof, with serial execution as the default. A scheduler may choose a lower
worker count without changing any entry identity or content. Increasing the
admitted bound requires new proof/plan integrity, not mutation of entries.

## Gotchas And Anti-Patterns

Avoid:

- adding `experiment-trial-v1`, `campaign-v1`, a mutable plan status, or a
  second archival run/provenance hierarchy;
- deriving entry or run identity from list position, entry order, worker count,
  queue/batch id, UUID, wall time, hash/map order, retry count, host, process,
  thread, backend availability, or aggregate mutable state;
- circular integrity fields, including an enclosing plan digest in entries or
  equating cleanup `plan_id` with the admitted-plan digest;
- accepting a plan whose root digest passes while an entry digest, keyed id,
  cleanup join, input digest, or cardinality is inconsistent;
- carrying unresolved policies, `"auto"`, `"default"`, ranges, generators,
  queries, callbacks, or resample instructions in an admitted entry;
- treating `InstantiationRequestModel.parameters`, generic
  `ExperimentParameterModel`, or free-text allocation/stochastic fields as
  typed binding authority;
- calling admitted bindings “realized,” fabricating pre-run
  `ExperimentApparatusContextModel`, or treating scheduler jobs/operation
  receipts/runtime snapshots as plan entries;
- copying task, factor, condition, apparatus, manifest, artifact, stochastic,
  cleanup, isolation, reference, checksum, diagnostic, or redaction schemas
  instead of embedding/referencing their owners and validating equality;
- embedding the full experiment spec or SDL document merely to make an entry
  self-contained;
- resampling, clamping, substituting, dropping, reordering semantically,
  choosing another backend, or emitting a partial plan after any failure;
- using a generic metadata/details/options map for execution controls,
  apparatus configuration, policy versions, validation evidence, or future
  fields;
- adding duplicate loaders, canonicalizers, digest helpers, reference
  resolvers, exception hierarchies, diagnostic envelopes, loggers, audit
  streams, persistence repositories, fixture runners, or CI workflows; and
- changing a published schema without authoritative checked-in schema content,
  Python bundle parity, per-contract publication hash/change summary,
  compatibility classification, positive/negative fixtures,
  `x-raes-invariants`, exports, and canonical verification routing moving
  together.

## Non-Goals And Implementation Boundaries

- #788 does not compile, sample, allocate, instantiate, plan a runtime model,
  select a backend, schedule, execute, retry, cancel, clean up, archive a run,
  or record observed results.
- #789 owns deterministic trial-set compilation, run-id derivation, complete
  cross-artifact admission, atomic sealing, and schedule-permutation evidence.
- #790 owns application of one entry through public SDL
  instantiation/admission and linkage to instantiated snapshots and archival
  run provenance.
- #785/SCE-006 owns scheduler policy, placement, leases, worker management,
  attempt lifecycle, and bounded concurrency. It consumes this contract and
  the existing cleanup/isolation contracts.
- Existing task, authoring-input, run, study, apparatus-context, evidence,
  associated-artifact, runtime-fact, cleanup, isolation, and control-plane
  contracts retain their meaning and persistence authority.
- The contract does not add an artifact service, database, API, CLI/MCP tool,
  secret manager, environment binder, RNG implementation, generic expression
  language, constraint solver, adaptive policy, comparison/scoring engine, or
  replay guarantee.
- A sealed plan proves admitted execution intent and integrity. It does not
  prove artifact availability at execution time, backend behavioral
  equivalence, successful execution, clean state, complete evidence capture,
  or exact replay from a seed alone.
