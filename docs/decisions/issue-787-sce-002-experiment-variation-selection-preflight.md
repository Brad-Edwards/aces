# Issue 787 SCE-002 Experiment Variation-Selection Preflight

Date: 2026-07-28

Issue: #787.

Requirement: SCE-002.

This note fixes implementation guardrails for experiment-owned selection
policies and allocation bindings. It is guidance only: it does not add contract
fields, schemas, policy execution, trial entries, scheduling, persistence, or
an implementation plan.

## Existing Authorities And Gaps

- ADR-084 and
  `specs/formal/scenario-variation-trial-realization/README.md` already own the
  family/selection/plan boundary. No new ADR is needed. SDL declares the valid
  family; the experiment declares how and why points vary; later processor work
  compiles concrete selections.
- `raes.variation`, `SemanticValidator._verify_variation_points()`, and
  `specs/sdl/variation-points.md` already own the six closed point kinds,
  bounded domains, typed targets, composition rewriting, and family
  satisfiability. Issue #787 must not copy those declarations or their
  validators into experiment contracts.
- `ExperimentSpecModel`, `ExperimentRunPlanModel`,
  `ExperimentStudyFactorModel`, `ExperimentConditionAssignmentModel`, and
  `ExperimentRunAllocationPlanModel` already own pre-run factors, conditions,
  run counts, blocking, replication, and allocation. The current
  `allocation_method`, `randomization_unit`, `replication_policy`, and
  `stopping_rule` strings remain descriptive and must not drive executable
  selection.
- `ExperimentBindingDescriptorSetModel` and
  `validate_experiment_binding_targets()` already own explicit scalar
  factor/level/condition bindings to scenario, participant-implementation, and
  apparatus targets. Their scenario target includes the scenario-family,
  variation-point, and canonical target identities. Do not publish a second
  scalar target/value binding schema in selection policies.
- `ExperimentStochasticControlModel.executable_binding`,
  `RandomStreamControlBindingModel`, `StreamAddressModel`, the published
  random-stream profile corpus, and `random_stream_engine` already own root
  entropy, namespace, address, and draw-profile semantics. A policy references
  that control; it does not repeat a seed, namespace, profile, or algorithm.
- The currently published `blake3-xof-v1` profile admits only the
  `bounded-integer` transform. Weighted choice, permutation, sampling without
  replacement, and t-way construction are not executable merely because they
  can be described in a model. They require exact accepted policy/transform
  semantics and fail closed until those semantics are published and supported.
- `ExperimentRunPlanModel.stochastic_controls` currently has `min_length=1`.
  That conflicts with #787's requirement that deterministic designs need no
  synthetic seed. The authoring contract must permit no controls while still
  requiring a resolved executable control for every stochastic selection
  policy.
- `parse_experiment_spec()` uses `yaml.safe_load` but has no SDL-equivalent
  duplicate-key/source-profile gate or loader-level byte bound. Its exception,
  the MCP wrapper, and `raes_conformance.conformance.validators` currently
  render raw Pydantic/YAML exception text. Those are disclosure and
  resource-boundary gaps, not patterns to copy.

## Contract And Concept Boundaries

### Extend the existing authoring input

Selection belongs as an optional, closed child of the existing experiment run
plan. Existing experiment documents remain valid and descriptive. Identifier-
bearing policies use a keyed map with stable portable policy ids and key/id
equality, following the repository convention and matching
`StreamAddressModel.selection_policy_id`.

Do not add an `experiment-selection-v1` root, a second experiment DSL, an SDL
selection section, or trial-plan fields. The admitted plan is owned by #788;
policy execution and trial-set compilation are owned by #789.

Use one closed selection-outcome representation wherever authoring policy,
factor assignment, later plan provenance, and instantiation lineage need the
same value. Reuse strict scalar binding values where their semantics match.
Add only the structural variants that scalar bindings cannot express:
alternative/reference member id, canonical subset member ids, a complete
canonical order, and logical-timing value. Do not create one value schema per
policy kind or duplicate SDL target/domain declarations.

### Normalize policy semantics instead of multiplying overlapping kinds

The user-facing policy terms map to a small, non-overlapping algebra:

| Requested term | Owning semantic form |
| --- | --- |
| fixed | Deterministic leaf selecting one admitted outcome |
| exhaustive | Deterministic enumeration of one finite admitted point domain |
| Cartesian | Deterministic product over named finite policy/point dimensions |
| balanced | An exact allocation-count invariant, not a random selector |
| stratified | Allocation or bounded sampling within declared factor/condition strata |
| bounded random | A bounded sample policy with an exact sample count |
| weighted | The sample policy's exact positive-integer weight strategy |
| without replacement | The sample policy's explicit replacement mode and finite-population bound |
| t-way | A versioned coverage policy over finite declared dimensions |

This avoids ambiguous combinations such as a “weighted” policy nested inside a
different “without-replacement” policy with no defined ordering. If composition
between policies is needed, references are by stable policy id in a finite
acyclic graph; do not introduce recursive inline policy expressions, callbacks,
templates, or a general workflow language.

Every policy carries an explicit positive output bound or derives one with
checked integer arithmetic from independently bounded inputs. Product,
enumeration, subset/order, sample, stratum, weight-total, diagnostic, and
serialized-byte bounds are validated before materialization. Overflow,
continuous/unbounded enumeration, or an output larger than the run allocation
is admission failure.

### Keep selection purpose explicit

Pre-run selection uses a closed purpose distinction:

- **controlled factor**: the outcome is joined to declared factor, level, and
  condition identities and affects the experimental comparison;
- **nuisance variation**: the outcome varies before execution and is preserved
  for analysis/provenance, but is not silently promoted to a treatment;
- **fixed configuration**: cardinality is one and contributes no trial
  dimension; scalar cross-plane configuration continues through the existing
  binding descriptors; and
- **runtime stochasticity**: not a scenario selection purpose at all. Agent,
  scheduler, observation, and other within-run controls remain on their owning
  runtime/participant contracts and addresses.

For scalar controlled-factor/configuration cases already represented by
`ExperimentBindingDescriptorModel`, reuse that binding and its source joins.
Structural policy outcomes may need a selection-specific factor assignment,
but it must reference the authoritative policy outcome plus existing
factor/level/condition ids; it must not repeat a target and value as a second
authority.

Secret values, hidden answers, and benchmark-only truth cannot be controlled
factor levels, nuisance candidates, weights, strata, or public outcomes.
Credential parameterization uses only a governed non-sensitive secret
reference or a declared late-bound sink. A policy never resolves the reference.

## Validation Ownership And Order

Validation remains layered rather than duplicated:

1. **Experiment structural/local admission.** `ContractModel(extra="forbid")`,
   strict scalar types, finite-number checks, keyed-map equality, unique policy
   and stochastic-control ids, policy-reference acyclicity, exact control
   presence/absence rules, factor/condition joins, and allocation cardinality
   arithmetic are owned by experiment contract validators and published
   `x-raes-invariants`.
2. **Expanded-family admission.** A contextual validator consumes an already
   trusted, semantically admitted `ExpandedScenario`, not a raw mapping or an
   unchecked `Scenario`. It resolves each qualified point exactly once and
   checks point kind, selection-outcome shape, scalar/domain membership,
   structural member ids, subset cardinality, order completeness/constraints,
   timing type/unit, and policy-kind compatibility. It must reuse
   `scalar_in_domain()` and the SDL variation authority rather than reproduce
   their rules.
3. **Experiment-to-family join.** The supplied family identity must agree with
   the task/intended scenario identity and every scenario binding target. The
   exact expanded-family digest is pinned by the admitted plan in #788; do not
   mislabel an expanded family as an instantiated scenario snapshot or infer
   identity from a path.
4. **Random-stream/profile admission.** A stochastic policy resolves one unique
   `control_id`; the control must carry an executable binding, an accepted exact
   profile id, the correct randomization/sampling role, and every transform the
   policy semantics require. Deterministic policies reject a stochastic-control
   reference. A deterministic-only design may have no stochastic controls.
5. **Plan-wide/whole-scenario admission.** Cross-policy combination
   satisfiability, concrete logical coordinates, whole selected-scenario
   validation, apparatus-envelope membership, atomic plan sealing, and
   schedule-permutation witnesses remain #789 responsibilities. #787 validates
   authoring intent; it does not emit or partially preview admitted trials.

For the current random-stream suite, a finite uniform draw or bounded integer
draw may be expressible through `bounded-integer`. A weighted, permutation,
without-replacement, subset, or coverage policy is admitted only when a
versioned policy algorithm fixes canonical candidate order, address purposes,
tie handling, rejection/exhaustion, and its required random-stream transforms.
Unknown or merely declared support fails; there is no fallback to Python
`random`, an in-place shuffle, or repeated draw-until-unique.

Weights should be positive bounded integers with a bounded total unless a later
profile publishes another exact numeric representation. Binary floats, NaN,
infinity, locale-dependent decimals, implicit normalization, and zero-weight
domain members are not portable distribution parameters.

## Canonical Incumbents To Reuse

- **SDL authority:** `ExpandedScenario`, `raes.variation`,
  `raes_contracts.bounded_domains`, `SemanticValidator`,
  `DeclarationIndex` resolution/collision behavior, trusted module composition,
  canonical family digests, and the existing SDL parse/validation exceptions.
- **Experiment authority:** `ExperimentSpecModel`, `ExperimentRunPlanModel`,
  `ExperimentStudyFactorModel`, `ExperimentConditionAssignmentModel`,
  `ExperimentRunAllocationPlanModel`,
  `ExperimentBindingDescriptorSetModel`, `_validate_binding_descriptor_source`,
  and `validate_experiment_binding_targets()`.
- **Randomness authority:** `ExperimentStochasticControlModel`,
  `RandomStreamControlBindingModel`, `StreamAddressModel`,
  `TrialCoordinateModel`, `random_stream_profiles`, `random_stream_engine`, and
  the governed `random_streams.draw_purpose` vocabulary.
- **Contract mechanics:** `ContractModel(extra="forbid")`, strict Pydantic
  scalar unions, `Diagnostic` / `DiagnosticModel`, RFC 8785/JCS
  canonicalization, `schema_bundle()`, keyed-map equality, and
  `x-raes-invariants`.
- **Publication/conformance:** `contracts/schemas/experiment-core/`,
  `contracts/fixtures/experiment-core/experiment-authoring-input-v1/`,
  `contracts/schema-publication/entries/experiment-authoring-input-v1.json`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`, and the
  existing conformance validator registry/fixture runner.
- **Authoring workflow:** `parse_experiment_spec()`,
  `load_experiment_spec()`, `experiment_validate`, `experiment_scaffold`,
  allowlisted worked examples under `examples/experiments/`, and their
  discovery tests. Extend these surfaces; do not add another loader or MCP
  selection tool.
- **Repository workflow:** ADR-014, `.ground-control.yaml`,
  `.gc/plan-rules.md`, `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_authority_boundary.py`,
  `tools/check_semantic_coverage.py`,
  `tools/check_specification_coverage.py`, and `tools/verify_all.py`.

## Security And Whole-Path Gates

1. **Authoring parser/config shape.** Enforce a byte bound in the canonical
   experiment loader, not only the MCP wrapper. Reject duplicate YAML keys,
   aliases/constructs outside the accepted source profile, non-mapping roots,
   unknown fields, coercive scalar forms, non-finite numbers, and oversized
   policy graphs before cross-artifact work. Do not add a loader that is weaker
   than `parse_experiment_spec()`.
2. **SDL supply-chain and semantic gate.** Contextual validation accepts only
   the output of bounded SDL parsing, import path confinement, lock/digest and
   signature/trust checks, namespace/collision rewriting, and complete semantic
   admission. A policy cannot import modules, widen a point domain, authorize a
   document path, or select a backend default.
3. **Factor/allocation gate.** Factor, level, condition, blocking/stratum, and
   binding ids resolve exactly once. Fixed/enumerated/product/sample/coverage
   cardinalities agree with `target_run_count` or condition allocation after
   checked arithmetic. Without-replacement counts cannot exceed the eligible
   finite population.
4. **Secret-handling gate.** Raw credentials, secret entropy, resolved secret
   values, sensitive locators, and secret-derived values are absent from policy
   candidates, factors, weights, ids/digests, examples, fixtures, diagnostics,
   logs, audit details, and MCP output. Only governed non-sensitive references
   cross portable boundaries, and dereference remains a separate authorized
   run-local operation.
5. **Environment/config gate.** Selection reads no ambient environment,
   process-global RNG, mutable parameter store, backend option, runtime fact,
   or filesystem locator. Ordinary environment configuration retains its
   existing typed runtime/config owner and cannot become a hidden policy input.
6. **OS/process exposure gate.** Validation and selection stay in process over
   typed DTOs or bounded content. Do not place experiment YAML, seeds, entropy
   refs, candidate values, parameter maps, or plans in argv, shell
   interpolation, stdout/stderr, or `shell=True`. Fixed-argv subprocess tests
   may carry only safe profile ids, fixture paths, and test-apparatus settings
   such as `PYTHONHASHSEED`.
7. **Authentication/authorization gate.** #787 adds no HTTP or mutating control
   plane. Any later remote validation/compile surface reuses
   `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   target-bound roles, request-size guards, request fingerprints, idempotency
   keys, append-only `AuditEvent`, and the redacted internal-error envelope.
   Reading a design does not authorize artifact or secret dereference.
8. **Error-envelope gate.** Replace raw `str(ValidationError)`/YAML rendering in
   experiment authoring, MCP, and conformance paths with bounded diagnostics
   carrying safe code, stage, JSON-pointer/canonical id, profile id, and counts.
   Do not expose Pydantic `input_value`, rejected values/weights, complete
   domains, raw documents, secret refs, backend objects, paths outside safe
   fixture context, environment dumps, or tracebacks. Reuse the existing
   exception families and `DiagnosticModel`; do not add a selection exception
   hierarchy.
9. **Logging/observability gate.** Reuse module-local logging. Safe fields are
   spec/policy/family ids, exact profile versions, counts, stages, durations,
   and disposition codes. Seeds, addresses with sensitive coordinates,
   selected outcomes, candidate domains, payloads, and bindings are not
   telemetry. Scientific inspection remains plan/run/study provenance, not
   logs.
10. **Persistence gate.** #787 publishes Git-tracked schemas, fixtures,
    examples, and possibly immutable policy-profile artifacts only. It adds no
    controller, repository, database, cache, audit stream, runtime snapshot
    field, mutable parameter store, or plan store. Later admitted intent and
    archival evidence use the plan/run/study lineage selected by ADR-084.

## Extensibility Seam

The seam is a versioned, closed policy registry whose policies are
parameterized by stable policy id, explicit purpose, qualified point refs,
bounded inputs/output, named factor/condition/stratum joins, and—only for
stochastic policies—an existing control id plus exact policy/transform
semantics.

The next bounded policy or exact sampling algorithm adds one union member or a
new immutable policy-profile version, fixtures, semantic dispatch, and
capability declaration. It does not edit SDL point schemas, random-stream
addresses, schedulers, backends, run identities, or old profile output. An
entirely new point kind remains an SDL/ADR-084 contract change; an entirely new
random transform remains a random-stream profile change.

Flat stable policy references and a closed purpose vocabulary are the intended
extension points. A free-form `parameters` map, general expression tree,
algorithm/plugin string, `latest` profile alias, or backend-specific policy
field is not an extensibility seam.

## Gotchas And Anti-Patterns

Avoid:

- treating descriptive allocation strings, red-variant selections, a seed, or
  `WitnessPolicy.seed` as executable selection;
- requiring a dummy stochastic control for a deterministic design, or allowing
  a stochastic policy without one unique executable control;
- claiming weighted, permutation, without-replacement, or t-way support when
  the accepted profile/algorithm does not define it exactly;
- representing “balanced” as random choice instead of an allocation-count
  invariant, or treating nuisance variation as an undeclared treatment;
- copying SDL domains/targets into experiment input, copying scalar binding
  target/value fields into policies, or stretching runtime facts into pre-run
  selectors;
- using arbitrary JSON/YAML pointers, overlays, templates, callbacks,
  expressions, external queries, dynamic plugins, or backend option maps;
- unchecked Cartesian products, continuous exhaustive domains, repeated
  random draws until unique, silent weight normalization, modulo-biased
  sampling, or partial results after exhaustion;
- resampling, clamping, substituting, dropping, or changing a backend after
  policy, constraint, worker, timeout, or apparatus failure;
- deriving addresses from experiment digest, list position, map/hash order,
  worker/process/thread/host, queue/batch, wall time, retry, or backend
  availability instead of the explicit randomness namespace and semantic
  coordinates;
- adding duplicate schemas, loaders, target resolvers, domain membership
  helpers, factor-join validators, exception trees, diagnostic envelopes,
  persistence stores, loggers, audit paths, or CI workflows; and
- hand-changing a published schema without model parity, publication hash and
  summary, compatibility review, fixtures, conformance routing, examples, and
  authoring-tool updates moving together.

## Non-Goals And Implementation Boundary

- #787 does not produce concrete trial entries, logical coordinates, run ids,
  admitted plans, instantiated scenarios, schedules, executions, or archival
  run/study records.
- It does not implement general constraint solving, arbitrary probability
  distributions, adaptive difficulty, runtime observations, participant
  action selection, replay, backend selection, or analysis.
- It does not add a PRNG, secret manager, artifact service, HTTP endpoint,
  worker pool, scheduler, database, trial root, campaign runtime root, or
  experiment-specific provenance graph.
- Cross-policy whole-scenario validity, backend realizability, atomic trial-plan
  compilation, schedule independence, and run-id preallocation remain #789
  work over the contract published here and the plan contract from #788.
- Runtime fact bindings from #791, cross-plane scalar configuration bindings
  from #903, SDL instantiation from #790, and archival experiment contracts
  remain distinct authorities and are reused rather than replaced.
