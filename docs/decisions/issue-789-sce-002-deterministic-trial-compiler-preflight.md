# Issue 789 SCE-002 deterministic trial compiler preflight

Date: 2026-07-29

Issue: #789.

Requirement: SCE-002.

ADR-084, the scenario-variation reference architecture, and the formal SVR
invariants remain the design authority. This note fixes issue-specific
guardrails where the published inputs do not yet make a safe compiler behavior
obvious. It is guidance only and does not implement compilation or define an
implementation plan. It adds no schema, profile, SDL instantiation, backend
call, persistence, or API/CLI/MCP surface.

## Binding compiler boundary

- The semantic authority is one pure `raes_processor` library boundary over
  already admitted typed artifacts. It returns exactly one sealed
  `AdmittedTrialPlanModel` or one bounded, canonically ordered diagnostic set.
  It performs no source parsing, import resolution, artifact fetching, secret
  lookup by ambient name, backend call, scheduling, persistence, or other
  external write.
- `raes_contracts` continues to own the portable plan, selection, binding,
  random-stream, apparatus-reference, cleanup, isolation, and diagnostic DTOs.
  `raes` continues to own scenario-family membership, cross-point constraints,
  typed targets, selected-scenario construction, and whole-scenario semantic
  admission. The processor orchestrates those owners; it must not copy their
  unions, membership rules, target resolver, validators, or exceptions.
- Admission is ordered and atomic: verify pinned input identity/trust; compile
  coordinates; resolve policy outcomes; prove family membership and closed
  constraints; validate authoritative bindings; admit the concrete selected
  scenario; prove apparatus/manifest/profile/envelope support; assemble all
  entries; validate plan-wide uniqueness and budgets; then use the existing
  entry and plan seal helpers. Any error yields diagnostics and no plan.
- A successful plan may contain only warning/info diagnostics and fixed safe
  limitations. Any error-severity diagnostic prevents sealing. Failed entries,
  partial products, rejected values, and raw validator payloads never appear in
  `admission`.

## Preconditions the implementation must not guess

### Publish exact v1 profile semantics before treating the names as executable

`AdmittedTrialPlanProfilesModel` closes the supported names
`trial-coordinate-v1`, `trial-entry-identity-v1`,
`archival-run-identity-v1`, `trial-compiler-v1`, and `jcs-sha256-v1`, but the
repository does not yet publish the output-affecting semantics of the first
four. A string literal is not an algorithm.

Before a producer claims byte-identical conformance, the accepted profile
authority must fix:

- how condition-based and simple run allocations become unique
  `TrialCoordinateModel` values, including replicate-id encoding and canonical
  coordinate order;
- the complete, domain-separated canonical projections for admitted
  `plan_id`, `plan_entry_id`, and archival `run_id`;
- canonical domain enumeration and policy-result ordering; and
- all failure, budget, and compatibility behavior that can change plan bytes
  or diagnostics.

Those definitions must route through the existing RFC 8785/JCS helpers and
have fixed conformance fixtures. They must not live only in Python traversal
order or tests. The v1 coordinate contract has only `condition_id`, `block_id`,
and `replicate_id`; it cannot silently encode cohort, worker, attempt, or an
arbitrary dimension. Unsupported dimensions fail profile admission until an
owning contract/profile version is published.

Identity remains acyclic. A deterministic plan-level id comes from its
profile-defined admitted-input projection before entries refer to it.
Entry/run ids come from the profile-defined plan-wide intent and coordinate.
Cleanup identities then bind those ids, entry digests bind entries, and
`plan_digest` binds the complete plan. `plan_id` is not `plan_digest`. No
identity is a UUID, list position, scheduler id, wall-clock value, or digest
that contains itself.

The published plan models inherit the non-frozen `ContractModel`; their
semantic immutability comes from canonical bytes and digest revalidation, not
from Python container enforcement. The compiler must not mutate or
`model_copy(update=...)` an entry/plan after sealing. Canonical comparison and
storage use `canonical_json_bytes(model_dump(mode="json"))`, never
`model_dump_json()` or an unvalidated mutable object. A consumer reconstructs
and validates the closed plan before use.

### Do not invent missing policy-graph or allocation semantics

The authoring contract admits fixed, enumerate, product, equal-stratified, and
bounded uniform-with-replacement sample policies. It does not admit implicit
zip, cycling, truncation, padding, policy priority, or a free-text replication
algorithm.

- A fixed policy's one explicit outcome may be broadcast to every coordinate.
  That does not turn an unresolved variable default into a selection.
- Sample and equal-stratified policies already bind their output counts to the
  run allocation. Enumeration/product output that does not exactly cover its
  governed coordinate set is unsupported unless a published allocation
  profile explicitly defines the remaining mapping.
- Product references are dimensions, not additional independently emitted
  trials. Nested product traversal is canonical and acyclic. A child policy
  cannot be emitted again merely because it also appears in the registry.
- Each `AdmittedSelectionRecordModel` records the leaf policy that produced
  that point's outcome. A product coordinates leaf outcomes but has no
  `point_ref` or direct outcome, so it cannot be recorded as though it selected
  one point. If explicit product ancestry is required beyond the pinned
  authoring input, the owning plan contract needs a versioned lineage field.
- Multiple policies selecting the same point, multiple uncombined varying
  dimensions, orphaned product nodes, uncovered variation points, ambiguous
  policy roots, or output/cardinality disagreement fail with bounded
  diagnostics. Dict order, source order, and worker partitioning never resolve
  ambiguity.
- Every family variation point is selected exactly once for every emitted
  coordinate. There is no `"auto"`, implicit default, backend-selected value,
  or unrecorded fallback in a sealed entry.
- Uniform sampling uses only the existing `blake3-xof-v1` profile,
  `sampling-selection` draw purpose, `StreamAddressModel`,
  `draw_bounded_integer_batch()`, and the profile's exact bounded-integer
  transform/exhaustion budget. The first profile has no accepted permutation,
  subset, weighted-choice, without-replacement, or constraint-resampling
  transform; those operations fail closed rather than using Python `random`,
  an in-place shuffle, or repeated shared-stream draws.
- Every stochastic selection has one exact draw join: control, namespace,
  trial coordinate, leaf policy, point, draw purpose/local coordinate,
  transform id/version, rejection facts, drawn index/outcome, and admitted
  selection all agree. Canonical address bytes are unique plan-wide, unused or
  descriptive controls are not executable plan controls, and one exhausted
  draw prevents the whole plan from sealing.

Canonical enumeration is a set operation unless the owning SDL kind declares
semantic order. Keyed alternatives/members and governed references use
canonical identifiers. Numeric integer intervals use numeric order, and scalar
enum members use their profile-defined canonical scalar order. A selected
`order` outcome preserves its declared semantic order.

### A sealed plan requires the missing SDL-owned admission seam

The current `instantiate_scenario()` deliberately rejects every non-empty
`variation_points` registry, and there is no production implementation of the
existing `ScenarioBindingTargetResolver` protocol. Planner manifest and
realization-envelope membership checks also consume a concrete
instantiated/compiled form, not a raw selection record.

Consequently, issue #789 must not:

- mutate `ExpandedScenario.model_dump()` in processor code;
- import private `raes.validator._variation*` helpers as a second public
  contract;
- reproduce requires/excludes/cardinality/precedence logic;
- treat `validate_experiment_selection_against_family()` as whole-scenario
  admission; or
- seal an `admitted-sealed` plan after checking only point-local membership.

The compiler requires a pure public SDL-owned operation. It resolves canonical
variation targets, validates a complete selection against family constraints,
constructs the selected transient family, and reruns whole-scenario semantic
admission. The processor may consume that result and existing public
planner/envelope validators. The exchange artifact remains the admitted plan;
the transient selected family is not a new schema or lifecycle root. If that
owning gate is unavailable, plan admission stops rather than fabricating
success. Snapshot/run provenance integration remains #790.

### Do not synthesize authorities the authoring inputs do not provide

- `selections` is the authority for resolved variation outcomes.
  `bindings` contains only authoring-supplied authoritative binding
  descriptors and admitted target defaults. If a policy cites
  `binding_descriptor_refs`, the compiler equality-checks the descriptor's
  point, condition, factor/level, target owner, value kind/type, sensitivity,
  and selected outcome. It does not fabricate a factor, condition, descriptor,
  or duplicate scalar binder for a fixed/nuisance selection.
- `AdmittedTrialPlanInputRefsModel.binding_descriptor_set_ref` is mandatory,
  while `ExperimentSpecModel.binding_descriptors` is optional and the
  descriptor-set contract cannot represent an empty set. A compiler must not
  mint a dummy descriptor set/ref for a valid unbound singleton or
  selection-only experiment. The owning input-ref contract must define the
  absent/empty case before those experiments can produce a sealed v1 plan.
- Scenario, participant, and apparatus binding targets pass
  `validate_experiment_binding_targets()` with an SDL-owned production
  resolver and the exact selected manifests. Raw names, aliases, JSON
  pointers, `${...}` occurrences, environment names, or backend options are
  not target authority.
- The plan contract requires per-entry attempt controls and
  `TrialCleanupPlanModel` values. The experiment authoring contract does not
  define those values. The compiler must consume an explicit typed,
  identity-compatible schedule-independent input from the owning cleanup/
  execution-control authority; it must not manufacture timeouts, resource
  boundaries, cleanup actions, retry policy, or parallelism from backend
  defaults. If no acyclic typed input can provide them, the input/contract
  boundary must be corrected before sealing.
- `ExperimentApparatusContextModel` is observed archival state and is never
  constructed pre-run. Plan entries carry
  `AdmittedApparatusBindingModel` intent backed by digest-matched concrete
  processor/backend manifests, exact accepted realization-envelope identity,
  required capability/profile support, and cleanup/isolation evidence.
- `AdmittedTrialPlanInputRefsModel.scenario_family_ref` currently uses the
  `ExperimentScenarioSnapshotReferenceModel` / `scenario-snapshot` vocabulary,
  while the compiler input is an admitted `ExpandedScenario` family and #790
  owns the instantiated snapshot. Do not accept an instantiated snapshot as a
  family or silently relabel an expanded family. The owning contract must
  either define this field as the exact expanded-family semantic digest or
  publish the correct reference type/version before production use.
- Task, authoring-input, family, binding-set, associated-artifact, manifest,
  envelope, and profile references are equality-checked against the supplied
  concrete artifacts using their owning canonical identities. Do not invent a
  compiler-local task digest or loosen a specialized reference model merely to
  make every reference look alike.

## Canonical incumbents to reuse

- **SDL ingress and family authority:** `load_sdl_yaml`/`parse_sdl`, source and
  composition budgets, duplicate/canonical-key validation, module lock/digest/
  signature/path gates, `ExpandedScenario.semantic_validated`,
  `canonical_sdl_digest()`, `validate_experiment_selection_against_family()`,
  `SemanticValidator`, and the public instantiation/admission spine.
- **Experiment and selection authority:** bounded
  `parse_experiment_spec()`, `ExperimentSpecModel`,
  `ExperimentRunAllocationPlanModel`, `ExperimentSelectionPolicyModel`,
  `ExperimentSelectionOutcomeModel`, factor/condition joins, and
  `validate_experiment_binding_targets()`.
- **Domains and randomness:** `raes_contracts.bounded_domains`,
  `load_random_stream_profile()`, `decode_public_seed()`,
  `derive_stream_key()`, `StreamAddressModel`,
  `draw_bounded_integer_batch()`, `RandomStreamDrawRecordModel`, and the
  published random-stream profile/vector corpus. `WitnessPolicy.seed` and
  realization-envelope `witness()` are unrelated.
- **Plan identity and closure:** `TrialCoordinateModel`,
  `AdmittedTrialPlanProfilesModel`, `seal_admitted_trial_entry()`,
  `seal_admitted_trial_plan()`, and
  `raes_contracts._canonical.canonical_json_bytes()` /
  `canonical_json_digest()`. Do not add a plan serializer or second digest
  helper.
- **Bindings, apparatus, artifacts, and cleanup:**
  `ExperimentBindingDescriptorModel`,
  `ConfigurationTargetRegistryModel`,
  `ExperimentApparatusConstraintModel`,
  `ExperimentManifestReferenceModel`, processor/backend manifest contract
  validators, `member()`/`subsumes()`,
  `validate_associated_artifact_manifest()` with bounded staged readers,
  `TrialCleanupPlanModel`, `SchedulerIsolationProofModel`, and their existing
  validators.
- **Diagnostics and workflow:** `Diagnostic`, `DiagnosticModel`,
  `diagnostic_model()`, the bounded deterministic accumulator pattern in
  `raes_processor.satisfiability`, the fixed-argv/hash-seed witnesses in
  `test_random_stream_determinism.py` and
  `test_pipeline_determinism.py`, and the canonical `nox`/repository policy
  graph. Do not add an exception hierarchy, fixture runner, or CI entry point.
- **Persistence and provenance:** the compiler returns immutable portable
  bytes/models only. `ControlPlaneStore`, `RuntimeSnapshot`,
  operation-detail/audit records, `ExperimentRunModel`,
  `ExperimentStudyModel`, and evidence contracts keep their existing live or
  archival authority and are not compiler storage.

## Cross-cutting security and runtime gates

1. **SDL source/composition gate.** Accept only an exact, semantically admitted
   `ExpandedScenario` with verified expansion provenance and a matching
   canonical family digest. Never accept a raw dict or resolve imports while
   selecting.
2. **Experiment/config gate.** Remote/file text first passes the canonical
   64-KiB duplicate-key/alias-rejecting, finite-JSON
   `parse_experiment_spec()` path and closed model/cross-artifact validators.
   Legacy descriptive allocation/randomization strings never execute.
3. **Profile/config gate.** Every plan and random-stream profile is an exact
   supported literal/allowlisted corpus id. No `latest`, environment-selected
   implementation, import string, callback, or library default is admitted.
4. **Binding/secret gate.** Target declarations and
   `validate_experiment_binding_targets()` enforce value type, allowed kind,
   owner, alias canonicalization, and sensitivity. Only a governed
   secret-reference identity may be selected or bound for credential-shaped
   input. Raw credential material is resolved only at its authorized run-local
   sink and is never a factor, plan value, identity/digest input, fixture,
   diagnostic, log, or telemetry field.
5. **Sensitive entropy gate.** A public seed is decoded by
   `decode_public_seed()`. If a governed entropy reference is supported, an
   injected authorized in-process resolver must validate immutable reference
   version, caller/scope/purpose, and exact byte length, and must return no
   serializable carrier. Environment-variable lookup is not a resolver. Raw
   entropy and derived keys never enter the plan or secondary surfaces.
6. **Artifact/apparatus gate.** The caller immutably stages concrete bytes and
   typed manifests/envelopes. Digest, identity/version, compatibility,
   capability, random-profile, cleanup/isolation, associated-artifact byte,
   and realization membership checks all pass before sealing. The compiler
   performs no URI fetch and backend unavailability never triggers resampling.
7. **Resource gate.** One explicit processor-owned limits value bounds total
   coordinates, product expansion, per-point domain materialization,
   constraints, bindings/draws per entry, artifact reads, diagnostics, and
   canonical plan bytes before expensive work. It follows existing parser,
   composition, and associated-artifact limit patterns; ambient configuration
   cannot change semantics silently.
8. **Authentication/authorization gate.** This issue needs no HTTP or mutating
   control-plane endpoint. Any later adapter reuses
   `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy
   identity, `ControlPlaneRole`, target-bound authorization, request-size
   guards, scoped idempotency/fingerprints, and append-only `AuditEvent`.
   Plan read, artifact read, entropy/secret resolution, and execution remain
   separately authorized operations.
9. **OS/process exposure gate.** Compilation stays in-process over typed
   objects or bounded file/stdin adapters. Plan JSON, seeds, entropy/secret
   refs, selections, bindings, artifacts, or evidence are not placed in argv,
   filenames, shell interpolation, stdout/stderr, or environment captures.
   Cross-process determinism tests use fixed argv containing only safe fixture
   paths/profile ids and may vary `PYTHONHASHSEED` as test apparatus.
10. **Error-envelope and observability gate.** Expected failures become
    bounded diagnostics sorted by stage, escaped canonical address, and code.
    Messages are fixed safe text with ids/profile/counts only; never use raw
    Pydantic input, selected/rejected values, complete domains, secret refs,
    documents, backend objects, host paths, environment dumps, or tracebacks.
    A future HTTP adapter retains `{"detail":"internal server error"}` for
    unexpected failures. Logs/audit contain only safe ids, digests, profile
    versions, counts, stage outcomes, and durations; plan/run/evidence
    artifacts, not logs, are the scientific record.
11. **Persistence gate.** Compilation writes nothing. Do not put plans or
    bindings in `RuntimeSnapshot.metadata`,
    `ControlPlaneOperationRecord.details`, audit blobs, tags, scheduler state,
    or a new mutable repository. A later artifact service must preserve exact
    immutable bytes/digests and separate read from execution authorization.

## Extensibility seams

- The semantic seam is the existing exact profile set: coordinate,
  entry/run identity, compiler, selection policy, canonicalization/integrity,
  random stream/transform, execution control, cleanup, and isolation. A new
  coordinate dimension, policy, or transform mints an owning closed profile or
  contract version with fixtures; it does not change v1 output or add a
  metadata/options bag.
- The resource seam is one explicit immutable compilation-limits value. Raising
  a non-binding ceiling does not change successful plan bytes; exceeding a
  ceiling produces the same bounded failure regardless of traversal or worker
  count.
- The integration seam is typed artifact provision: exact admitted models and
  bounded readers are supplied by callers. Future artifact stores, secret
  resolvers, or adapters implement authorization/acquisition outside the pure
  compiler and cannot become selection authorities.

## Gotchas and anti-patterns

Avoid:

- treating named-but-undefined profiles as implementation freedom;
- deriving coordinates or ids from collection position, source order, Python
  hashes, UUIDs, workers, retries, time, hosts, or backend availability;
- implicit zip/cycle/broadcast beyond the fixed-policy rule, hidden policy
  roots, or interpreting free-text replication/allocation;
- shared/cursor RNGs, per-worker seeds, in-place shuffle, modulo bias, or
  resampling after a constraint/apparatus/runtime failure;
- duplicating family membership, cross-point constraints, scalar domains,
  target resolution, binding schemas, manifest validation, envelope relations,
  canonicalization, sealing, diagnostics, exceptions, logging, or persistence;
- sealing before public selected-scenario semantic and apparatus admission;
- using point-local admission as proof of whole-scenario validity;
- fabricating binding descriptors, apparatus context, cleanup plans,
  timeouts, retry policy, or isolation evidence;
- recording a selected value twice without an explicit equality-checked
  authority join, or carrying unresolved defaults/queries/backend choices;
- treating `plan_id`, `plan_digest`, `plan_entry_id`, `run_id`, cleanup
  `plan_id`, scheduler job id, operation id, and execution-attempt id as
  interchangeable;
- mutating a sealed Pydantic plan in memory or treating non-JCS JSON output as
  the canonical byte artifact; and
- emitting a partial plan, clamping, dropping, substituting, choosing another
  backend, or attaching raw validation details after any failed coordinate.

## Non-goals and claim boundary

- Issue #789 does not parse or compose SDL, publish new variation/selection
  syntax, implement selected-snapshot/run provenance, bind runtime facts,
  schedule, execute, retry, cancel, clean up, persist, analyze results, or add
  an HTTP/CLI/MCP service.
- #790 remains responsible for durable selection-to-instantiation snapshot and
  archival run linkage. SCE-006 remains responsible for scheduler/worker/
  placement policy and consumes only sealed entries.
- The admitted plan proves deterministic, bounded execution intent against the
  exact evidence available at admission. It does not prove continuing artifact
  availability, successful execution or cleanup, backend behavioral
  equivalence, unpredictability, recreation of hidden state, or exact replay
  from a seed.
