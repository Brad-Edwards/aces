# Issue 274 EXP-718 Controlled Randomness And Seed Preservation Preflight

Date: 2026-07-20

Issue: #274.

Requirement: EXP-718.

This note fixes implementation guardrails for the versioned random-stream suite.
It is guidance only: it does not add a generator, profile, schema, contract
field, vector, API, persistence behavior, or executable selection policy.

## Binding Decisions And Ownership

- ADR-084 and `specs/formal/scenario-variation-trial-realization/README.md`
  already own the random-stream architecture, especially SVR-012 through
  SVR-017, SVR-023, SVR-028, and SVR-031. This issue needs no second ADR and
  must not weaken those invariants to accommodate a library API.
- ADR-055, ADR-065, ADR-068, and ADR-074 keep experiment authoring, observed
  apparatus, archival run provenance, and study allocation distinct. One
  executed trial remains one `experiment-run-v1`; a random draw, stream, or
  participant episode is not another trial identity.
- ADR-036 keeps portable DTOs and profile shapes in `aces_contracts`,
  processor-owned selection/compilation in `aces_processor`, and live
  operation state in `aces_runtime`. Backends and schedulers consume admitted
  selections; they do not own an alternative randomizer.
- ADR-009/019/061 make `specs/`, `contracts/schemas/`,
  `contracts/fixtures/`, and `contracts/profiles/` authoritative. Python code
  and library defaults are reference implementations, not the cross-language
  definition.
- Existing descriptive stochastic controls stay descriptive for compatibility.
  In particular, `ExperimentStochasticControlModel.role/value`, study
  `allocation_method` / `randomization_unit`, participant
  `randomization_basis`, observation `seed_ref`, and `WitnessPolicy.seed` do
  not become executable merely because the new engine exists.

## One Profile And One Stateless API

Publish one closed, immutable random-stream profile shape under the existing
normative schema/profile corpus. An accepted profile fixes, as one compatibility
unit:

- generator family and exact version;
- root-entropy type, length, and canonical byte encoding;
- semantic-address schema and canonical byte encoding;
- key/child-stream derivation and every domain-separation label;
- raw-block and integer endianness/interpretation;
- each admitted bounded-integer, real, weighted-choice, permutation, subset,
  and sampling transform version; and
- rejection, tie, precision, exhaustion, and unsupported-operation behavior.

Changing any item mints a new profile id and new vectors. Schema version,
profile version, algorithm version, transform version, and Python package
version are different concepts and must not be substituted for one another.
The accepted profile artifact and vectors are the authority; an implementation
must dispatch only exact supported profile ids and fail closed on an unknown
id/version. Do not implement a dynamic algorithm plugin, `latest` alias, version
range, or fallback to a library default.

The callable surface is random-access and immutable. Every operation takes an
explicit admitted control, complete semantic address, transform id/parameters,
and local block/draw coordinate. It returns an output plus bounded provenance;
it exposes no process-global state, worker-local singleton, ambient seed, or
cursor-style `next()` whose result depends on prior calls. An immutable helper
object is acceptable only if its methods remain address-based and it carries no
advancing cursor.

The first accepted profile should use a standardized, fully specified
counter-addressable or PRF-style construction with implementations available to
independent languages. Its exact primitive is profile data plus normative prose,
not an accidental consequence of `random.Random`, NumPy, OpenSSL, platform
endianness, or the installed dependency version. Cryptographic secrecy is not a
claim, even if the selected primitive is cryptographic.

## Canonical Inputs, Addresses, And Collision Handling

Executable root entropy is bytes, not a JSON number. An inline public seed uses
one fixed-width canonical textual encoding so leading zeroes, integer width,
sign, Unicode, and language numeric limits cannot change its bytes. Sensitive
entropy uses a closed governed-reference variant with an immutable reference
and version; raw entropy is resolved only at an authorized in-process boundary
and is never serialized back into the control, plan, run, diagnostics, logs,
fixtures, argv, or telemetry. Do not publish a digest of low-entropy secret
material as a purportedly safe commitment.

The stream address is a closed typed DTO, not a concatenated string, arbitrary
mapping, JSON Pointer, or scheduler address. It contains only:

- the explicit experiment-owned randomness namespace;
- the logical trial coordinate, including condition/block/replicate or other
  declared coordinate dimensions;
- the selection-policy id;
- the qualified variation-point or other governed concern id;
- a closed draw-purpose id; and
- a stable local member/draw coordinate.

The experiment dimension is the randomness namespace. Per ADR-084, do not add
the aggregate experiment/spec id or content digest to the derivation input;
those remain sealed provenance. Worker, process, thread, host, queue, batch,
wall time, completion order, retry count, map/hash iteration order, backend
availability, and operation id are forbidden inputs. A numeric draw index is
valid only when it is a stable local semantic coordinate, never “the next
draw.”

Reuse the repository's RFC 8785/JCS dependency and canonical-data discipline
for a profile-defined address encoding rather than inventing ad hoc delimiter
escaping. Restrict identifier-bearing address fields to the existing portable
ASCII identifier/qualified-name rules where those concepts already use them.
Validate the typed shape before canonicalization and set explicit byte/count
budgets before hashing or derivation.

An injective address encoding is the primary collision guard. During a bounded
operation, detect duplicate semantic coordinates, duplicate canonical address
bytes, and duplicate derived stream identities among materialized addresses;
report a deterministic collision diagnostic and emit no partial result. Do not
claim a global proof against cryptographic collisions, silently merge aliases,
or resolve a collision by adding worker/order data.

## Preservation Without A Parallel Provenance Stack

Extend the existing stochastic-control lineage with a typed executable child or
variant; do not add a second top-level seed model, task, run, study, or
apparatus record. Preserve the legacy descriptive form without treating it as
executable. The owning models remain:

- `ExperimentSpecModel.run_plan.stochastic_controls` for declared pre-run
  control, namespace, root-entropy representation, and exact profile reference;
- `ExperimentApparatusConstraintModel`, processor manifest capabilities, and
  `ExperimentApparatusContextModel` for required profile support and the exact
  control/profile actually in force;
- `ExperimentRunModel.stochastic_controls` for the archival control snapshot
  and run-level draw/selection provenance;
- `ExperimentStudyModel`, allocation, condition assignments, and
  `validate_experiment_study_against_tasks_and_runs()` for common-random-number
  or controlled-randomness comparison claims across included runs; and
- `ParticipantObservationStochasticContextModel` and other participant/runtime
  carriers only for typed references to the owning run control/draw facts when
  an observation actually depends on them.

A draw/selection provenance record references its control and records the
semantic address, policy/point/purpose/local coordinate, transform and exact
version, bounded transform inputs or their already-pinned domain identity,
selected outcome, and rejection/resampling attempt facts. It does not duplicate
the root seed for every draw or expose raw generator blocks outside conformance
vectors. A sensitive selected outcome is represented by a governed reference
and sensitivity/withholding metadata, never by its raw value.

Cross-artifact validators, rather than producers by convention, must prove that
control ids resolve, profile ids are accepted and supported by selected
apparatus, apparatus/run controls agree, draw records use the referenced
control/profile, study comparison claims resolve through eligible runs, and
participant stochastic refs resolve to the same run/episode scope. A seed with
no generator/derivation/transform identity is insufficient for a reproducibility
claim.

Profile support belongs on the existing processor/apparatus capability path.
Do not stretch `supported_contract_versions` into a profile registry, encode
profile versions in a free-form backend constraint, or require a backend to
reselect values. Backends may preserve or consume an admitted value only when
their existing contract requires it.

## Canonical Incumbents To Reuse

- Contract closure and semantic invariants: `ContractModel(extra="forbid")`,
  Pydantic model validators, `x-aces-invariants`, `schema_bundle()`, and the
  existing keyed-map/key-equality convention.
- Normative publication and distribution: `contracts/schema-publication-manifest.json`,
  `contracts/schema-publication/entries/`, `aces_contracts.corpus`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`, and
  `tools/check_json_artifacts.py`.
- Experiment authority: `ExperimentStochasticControlModel`,
  `ExperimentRunPlanModel`, `ExperimentApparatusConstraintModel`,
  `ExperimentApparatusContextModel`, `ExperimentRunModel`,
  `ExperimentStudyModel`, `validate_experiment_run_against_task()`, and
  `validate_experiment_study_against_tasks_and_runs()`.
- Participant authority: `ParticipantObservationStochasticContextModel` and the
  existing participant base-envelope run/episode, provenance, marking,
  authorization-scope, and redaction fields.
- Address/canonicalization discipline: portable SDL identifiers and qualified
  names, RFC 8785/JCS canonical bytes, canonical keyed traversal, and existing
  digest helpers. Compiled runtime addresses remain a separate concept and must
  not be reused as random-stream addresses.
- Diagnostics: `aces_contracts.diagnostics.Diagnostic` / `DiagnosticModel`,
  existing processor diagnostic accumulation, stable code/domain/address
  ordering, and bounded messages. Do not add a random-stream exception tree or
  free-form error envelope.
- Security and operations: `ControlPlaneSecurityConfig.strict_defaults()`,
  request-size guards, bearer/verified-proxy identity, role/target checks,
  idempotency fingerprints, append-only `AuditEvent`, and the redacted HTTP 500
  envelope.
- Workflow and testing: ADR-014, `.ground-control.yaml`, `noxfile.py`,
  `SessionReporter`, `test_pipeline_determinism.py`'s fixed-argv cross-process
  pattern, existing contract fixtures, Hypothesis properties, and one canonical
  `verify` graph.

## Security And Whole-Path Gates

1. **Normative profile and corpus gate.** Profile ids use a bounded grammar and
   resolve through `aces_contracts.corpus` to an allowlisted family beneath the
   packaged normative corpus. The loader validates the closed profile and its
   vectors and rejects path traversal, unknown files, unknown algorithms, and
   version drift. Profile JSON never names executable code.
2. **Experiment/config shape gate.** Authored controls pass the existing
   `ExperimentSpecModel` closed shape and owning cross-artifact validators.
   `parse_experiment_spec()` currently uses `yaml.safe_load`, lacks SDL's
   duplicate-key/source-profile gate, and exposes raw Pydantic/YAML text through
   `ExperimentSpecValidationError.details` and the MCP tool. Any EXP-718 remote
   or execution-facing ingress must harden this canonical loader or accept an
   already-validated model; it must not add another loader or echo rejected
   seed/control values.
3. **SDL and trial-admission gate.** A stochastic policy targets only admitted,
   bounded scenario-family points and existing typed domains. Whole-scenario
   validation, selected processor manifest/profile support, and backend
   realization-envelope checks still run in their existing order. Randomness
   cannot widen a family domain or make an unrealizable selection admissible.
4. **Authentication/authorization gate.** No API is required by this issue. A
   later profile/control/plan/run endpoint reuses strict control-plane
   authentication, operator/backend/auditor roles, target scope, body-size
   limits, idempotency, and audit events. Permission to read a plan summary does
   not imply permission to resolve sensitive entropy or selected-value refs.
5. **Secret-resolution gate.** Public inline seeds and governed sensitive
   references are a closed union. The resolver validates reference authority,
   immutable version, caller/scope, purpose, and expected byte length before
   use. It returns bytes in process and never mutates the portable model.
   Environment-variable lookup, URI credentials, secret-store tokens, or raw
   secret values are not profile/config fields.
6. **Environment and OS exposure gate.** Selection reads no ambient environment
   and uses no process-global RNG. Cross-process witnesses may vary
   `PYTHONHASHSEED` as test apparatus, but it cannot enter derivation. Keep
   execution in process; if a conformance subprocess is needed, use fixed argv
   containing only safe profile ids and fixture paths. Never place seeds,
   entropy refs, addresses with sensitive coordinates, selected values, plans,
   tokens, or parameter maps in argv, shell interpolation, or `shell=True`.
7. **Error-envelope gate.** Shape errors stay in the existing contract/loader
   path; operational selection failures become bounded `Diagnostic` values.
   Expose safe code, stage, canonical concern address, profile id, and counts
   only. Do not render the seed, entropy ref, selected value, complete domain,
   rejected document, raw Pydantic `input`, backend object, environment, or
   traceback. HTTP retains the generic internal-error envelope.
8. **Logging/observability gate.** Reuse module-local logging and audit events.
   Log only safe ids, exact profile versions, counts, stage outcomes, and
   durations. Seeds, derived keys, raw blocks, stream addresses containing
   sensitive coordinates, selections, rejected candidates, and resampling
   values are not telemetry. Scientific inspection uses the run/study/evidence
   graph, not logs.
9. **Persistence gate.** Accepted profiles/vectors are immutable corpus files;
   controls and draw facts are sealed portable plan/run provenance. Do not put
   them in `RuntimeSnapshot.metadata`, `ControlPlaneOperationRecord.details`,
   audit `details`, tags, or a new mutable seed database. `ControlPlaneStore`
   remains live per-target operation state, not an experiment repository.

## Reliability, Test Oracles, And Bounds

- Canonical vectors cover seed decoding, address bytes, derivation, raw blocks,
  every transform, boundary values, rejection paths, and exhaustion. At least
  one zero-heavy seed/address catches lost leading zeroes and endian mistakes.
- The same vectors run through the public reference API and are sufficient for
  an independent-language implementation; tests must not compute expected
  values with the implementation under test.
- Determinism witnesses cover serial, parallel, shuffled, resumed, partitioned,
  worker-reversed, retry-before-seal, serialization round-trip, separate
  processes, and distinct hash seeds. Outputs and provenance are compared in
  canonical semantic-address order.
- Non-interference properties add an unrelated policy, point, coordinate, or
  draw and verify that every unaffected address remains byte-identical.
- Negative fixtures cover malformed/oversized coordinates, duplicate canonical
  addresses, unsupported profile/algorithm/transform versions, invalid seed
  encodings/lengths, missing or unauthorized entropy refs, impossible bounds,
  invalid weights, collision detection, rejection exhaustion, and forbidden
  sensitive inline values.
- Bounded-integer transforms use rejection rather than modulo bias and record
  attempt/rejection counts. The profile fixes a maximum attempt/block budget;
  exhaustion is a deterministic failure, never fallback, clamping, or
  unrecorded resampling. Weighted transforms avoid unspecified binary-float,
  NaN, infinity, locale, or rounding behavior.
- Statistical smoke tests are secondary, fixed-input, broad-tolerance checks
  for gross defects. They do not replace vectors/properties, use flaky p-value
  thresholds, or redefine profile output.

## Extensibility Seam

The seam is the immutable profile id plus closed dispatch over generator,
derivation, address-encoding, and transformation versions. A new generator or
transform publishes a new accepted profile (and vectors) and adds one explicit
implementation dispatch path; it does not edit old profiles, existing run
records, schedulers, backends, or scenario schemas. Profile support is an
explicit processor/apparatus capability and an admitted input, never inferred
from an installed library.

Semantic address dimensions are represented as a versioned closed coordinate
model with an explicit extension/version point. The next reasonable addition,
such as an agent-policy or observation-noise purpose, adds a governed purpose or
coordinate version without changing the meaning of existing addresses. It must
not use a catch-all metadata map in the derivation input.

## Gotchas And Anti-Patterns

Avoid:

- `random.seed()`, NumPy defaults, `secrets`, UUIDs, wall time, hash order, or a
  mutable generator shared across trials, policies, points, or workers;
- treating the experiment id/digest, list position, worker number, retry count,
  or current call count as a semantic coordinate;
- delimiter-concatenated addresses, variable-width integer seeds, native-endian
  conversion, floating-point weights without exact profile semantics, or
  in-place collection shuffles;
- interpreting legacy seed/free-text fields as executable, or using
  `WitnessPolicy.seed` / satisfiability solver `random_seed=0` as experiment
  randomness;
- resampling after backend rejection, timeout, cancellation, collision,
  constraint exhaustion, or worker failure;
- preserving only the selected value while dropping profile, address,
  transform, or rejection facts, or preserving a seed without algorithm and
  derivation identity;
- copying stochastic fields independently into authoring, apparatus, run,
  study, participant, and runtime schemas with different validators;
- adding a duplicate profile registry, schema generator, YAML loader,
  validator, exception hierarchy, diagnostic envelope, persistence repository,
  logger, audit stream, or CI workflow; and
- logging, hashing for public disclosure, or serializing sensitive entropy and
  outcomes where a governed reference is required.

## Non-Goals And Implementation Boundaries

- EXP-718 does not choose scenario variation policies, allocate or compile
  trial plans, schedule workers, execute trials, or implement replay.
- It does not make randomness SDL meaning, backend realizability, runtime fact
  binding, study analysis, or participant policy. Those consumers reference the
  governed stream suite through their existing owning contracts.
- It does not guarantee cryptographic secrecy, unpredictability, exact
  environmental replay, identical backend behavior, artifact availability, or
  recreation of hidden state.
- It does not add a secret manager, artifact repository, HTTP service,
  process-global RNG, general distribution language, dynamic plugin system, or
  parallel run/trial/provenance root.
- The implementation may publish the profile/contracts/vectors and a stateless
  reference engine. Admitted-plan compilation and scenario selection remain
  with their separately owned follow-on issues.
