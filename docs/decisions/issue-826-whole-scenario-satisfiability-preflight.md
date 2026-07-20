# Issue 826 Whole-Scenario Satisfiability Preflight

Date: 2026-07-19

Issue: #826. Requirement: none; the issue title, body, and acceptance criteria
are the delivery contract.

This note fixes the repository-wide boundary for governed whole-scenario
constraint satisfiability before implementation. It does not implement a
solver, define final contract field spellings, publish schemas, add fixtures,
or constitute an implementation plan.

## Decision Boundary

The new capability is an **FM2 constraint-semantic analysis** over a fully
composed, semantically validated SDL authoring scenario. Its question is:

> Does at least one assignment in the declared, supported variable domains
> make every translated scenario constraint true at once?

The analyzed input is the `Scenario` or `ExpandedScenario` returned by the
ordinary `parse_sdl_file()` path, after module composition and semantic
validation but before instantiation. An already admitted
`InstantiatedScenario` is replay evidence for one solution; it is not the
primary analysis input, because asking whether an already concrete artifact is
satisfiable would make the gate largely vacuous.

Keep the following concepts and results separate:

- SDL parsing/schema validity proves closed shape and local predicates.
- `SemanticValidator` proves the existing static cross-reference and graph
  invariants over the current artifact, including ordinary acyclicity.
- instantiation proves that one supplied binding reconstructs and semantically
  validates as a concrete scenario.
- realization-envelope `member()`/`subsumes()` proves a bounded relation
  between a requested realization and a backend capability envelope.
- workflow reachability/topological ordering proves properties of one named
  graph.
- runtime propositions, preconditions, postconditions, assertions, and
  objectives describe temporal or goal truth, not static simultaneous
  constraints.
- whole-scenario satisfiability proves existence or non-existence of a model
  only for the explicitly versioned theory and translated coverage claimed by
  this capability.

No existing relation can be renamed or wrapped to satisfy this issue. Issue
#168's failed/untested evidence must remain immutable; implementation produces
a new execution snapshot and analysis rather than rewriting the prior finding.

The first implementation needs a focused ADR because it adds the repository's
first governed solver dependency, normalized constraint artifact, and
satisfiability result contract. That ADR and the normative specification under
`specs/formal/` must land before or with code. This preflight does not assign an
ADR number or make non-normative guidance the semantic authority.

## Versioned Theory And Translation Boundary

The initial normative theory should be deliberately small: finite-domain
constraint satisfaction over declared SDL variables and whole-field variable
references. It must have a stable theory id and revision. The specification
must enumerate, rather than imply:

- admitted scalar sorts;
- how a declared variable domain is obtained and ordered;
- every translated variable-bearing target kind and its domain restriction;
- the supported equality/domain-membership operators;
- canonical symbol, domain-member, and clause identity/order;
- resource limits; and
- explicit exclusions and unsupported dispositions.

Boolean domains are intrinsically finite. String and integer variables need an
explicit finite `allowed_values` domain in the first profile. Number/float
semantics, unbounded domains, partial-string interpolation, arbitrary
expressions, and variable-dependent semantic predicates are unsupported until
a later theory revision defines their exact representation and comparison
rules. A default is one candidate or a convenience binding; it must not be
mistaken for the complete domain.

The symbol set includes every referenced variable and every unreferenced
`required` variable that ordinary instantiation still requires. An optional,
unreferenced variable may be absent exactly as `instantiate_scenario()` already
permits; it must not force an invented value. A referenced optional variable
still needs a governed finite domain because leaving its token unresolved would
make the witness inadmissible.

Use one versioned translation-coverage table in `aces_processor`. Each
remaining variable occurrence in the composed model must receive exactly one
disposition: translated by a named handler or rejected as unsupported with a
stable diagnostic. The table should reuse `Variable`, `VariableType`,
`WholeFieldVariableReference`, `x-aces-variable-reference`, the existing
`parse_*_or_var` rules, enums, bounds, and canonical addresses. It must not
copy enum values or invent a second variable type system. Agreement tests must
make a newly variable-capable field fail governance until the table explicitly
supports or excludes it.

Composition already binds imported-module parameters through
`_bind_scenario_content()` and removes imported variable declarations before
constructing `ExpandedScenario`. The initial solver therefore ranges only over
the root variables that survive composition. It must treat imported bindings
and their digests as fixed provenance, not recover variable declarations from
the imported source or re-solve import selection under a second composition
semantics.

Do not attempt a generic Pydantic/JSON-Schema-to-solver compiler. Pydantic and
the published schemas do not encode all `SemanticValidator` and
post-instantiation behavior, so such a compiler would silently claim a weaker
theory. The translator is total over the declared profile, not total over all
ACES meaning.

One shared variable occurring at otherwise individually admissible target
sites can make the conjunction unsatisfiable. That shared-symbol behavior is
the minimum non-vacuity control the negative fixture must demonstrate. The
positive control must exercise the same translation path with a reproducible
solution. Unsupported cases must contain a real variable occurrence beyond the
profile, not merely malformed SDL that the ordinary parser already rejects.

## Normalized Model, Solver, And Result Contracts

Use closed portable DTOs in `aces_contracts` for the normalized constraint
model, solver configuration, and result/evidence. Publish them through the
existing schema bundle and publication manifest. They are derived artifacts,
not new SDL authoring sections.

The normalized model should contain only governed data:

- theory and translation profile ids;
- source identity and semantic digest joins;
- stable qualified symbols, scalar sorts, and finite ordered domains; and
- stable clauses with operator/kind, symbol references, and safe canonical
  source addresses.

It must not make raw SMT-LIB, an arbitrary solver expression, Python callback,
or open option map into portable authority. Canonical bytes use the existing
RFC 8785/JCS plus SHA-256 convention.

The intended first adapter is the official in-process Z3 Python API, isolated
behind a small public `aces_processor.satisfiability` boundary. The exact
`z3-solver` release must be equality-pinned in `pyproject.toml` and `uv.lock`;
the engine's own version/build must also be captured. The governed solver
profile explicitly fixes logic/tactic, automatic-configuration behavior,
random seed, model and unsat-core modes, parallelism/thread count, deterministic
work/resource limit, and every other output-affecting option. Defaults are not
a configuration contract; a separate wall-clock watchdog is operational only.

The public outcome is a closed enum with exactly:

- `satisfiable`;
- `unsatisfiable`; or
- `unsupported`.

Outcome is not `Diagnostic.severity`, a validation-strength label, an ADR-021
evidence status, or a boolean `holds`. `unknown`, timeout, resource exhaustion,
unsupported theory behavior, and incomplete translation must never be mapped
to satisfiable or unsatisfiable. Malformed input and internal/operational
failure remain failures at their owning boundary rather than fabricated solver
outcomes.

Every completed outcome carries a stable primary diagnostic code and bounded
safe address, including positive `satisfiable` and negative `unsatisfiable`
results; the typed outcome remains authoritative and is never reconstructed
from that code. `aces_contracts.diagnostics.Diagnostic` and
`diagnostic_payload()` are the incumbent in-memory vocabulary, but there is no
closed published `DiagnosticModel` today: existing plan/operation contracts use
`list[dict[str, Any]]`. Do not copy that open shape or define a
satisfiability-local diagnostic record. Close the shared diagnostic payload at
the contract boundary once, preserving `code`, `domain`, `address`, `message`,
and `Severity`, and reuse it in the evidence contract.

The evidence envelope binds all of the following with closed cross-object
validators:

1. SHA-256 of the exact root source bytes and a safe source identity;
2. `canonical_sdl_digest()` of the validated post-expansion authoring meaning,
   plus the existing import/expansion provenance and its source digests as a
   separate join (the canonical semantic digest intentionally excludes that
   provenance object);
3. theory and translation profile ids plus the canonical normalized-model
   digest;
4. the complete governed solver configuration and its digest;
5. the typed outcome and bounded diagnostics; and
6. exactly one outcome-specific payload.

For `satisfiable`, the payload is the canonical
`InstantiatedScenarioSnapshot` witness and its digest. Decode the canonical
model assignment, then call `instantiate_scenario()` and
`admit_instantiated_scenario()` as an independent replay gate. Reuse
`InstantiationProvenance.bindings`; do not emit a second raw binding map.

For `unsatisfiable`, the first profile may emit governed unsatisfiable-core
evidence: a deterministic subset of stable normalized clause ids bound to the
exact model and solver configuration. Call it an unsatisfiable core, not a
proof certificate. Replay must reconstruct and recheck those exact clauses.
For `unsupported`, emit stable reason codes and safe addresses, with neither a
witness nor a core. Model validators enforce this exclusivity and every digest
join.

## Determinism And Resource Governance

Solver determinism is an application property; a pin and seed alone do not
establish it.

- Canonically sort symbols, finite domain members, clauses, diagnostics, and
  core ids. Preserve SDL list order only where that order is semantic.
- Do not use an arbitrary solver model as the portable witness. Define one
  canonical total order per admitted scalar sort, then select the first
  satisfiable domain member for each canonically ordered symbol through repeated
  bounded solver checks and replay it through ordinary instantiation/admission.
- Do not expose a solver-returned core without a stability rule. A bounded,
  deletion-based reduction over sorted named clauses is the preferred initial
  rule; its order and minimality claim must be specified. A subset-minimal core
  is not necessarily a globally minimum core.
- Bound source bytes through `SDLParserLimits`, then separately bound symbol,
  clause, per-domain-member, total-domain-product, diagnostic, and core
  cardinalities. Use a deterministic solver work/resource limit as the
  governed evidence budget. A wall-clock watchdog may protect the local
  process, but expiry is an operational failure and cannot become a
  reproducible semantic outcome. Exceeding a deterministic governed bound
  yields typed `unsupported`; only an unexpected adapter/internal failure uses
  the operational-error channel. Neither condition is partial success.
- Repeat evidence across processes and hash seeds. Mutate source bytes,
  semantic content, one normalized clause, solver configuration, witness,
  clause/core membership, and digest joins; replay must reject each stale or
  weakened artifact.
- Tests must establish that the production adapter is actually invoked, that a
  single translated defect changes the outcome, that both controls are
  discovered, and that an empty/unsupported corpus cannot satisfy the gate.

## Package, Entrypoint, And Persistence Boundaries

ADR-036 ownership applies:

- `aces_contracts` owns neutral normalized-model, solver-profile, and evidence
  DTOs and their cross-object validators;
- `aces_processor.satisfiability` owns translation, coverage disposition,
  solver adaptation, deterministic witness/core selection, and replay;
- `aces_cli.processor` exposes the production command; and
- `aces_sdl` remains solver-free and owns parsing, composition, variables,
  instantiation, admission, and semantic identity.

Do not add implementation to compatibility-only `implementations/python/src/aces/`
or introduce a new top-level package. Adding the public processor subpackage
requires the corresponding `tools/policy/adr_policy.yaml` public-import
allowlist update for `aces_cli`, while preserving every forbidden edge and the
ADR-015 500-line cap.

Expose one read-only production command under the existing `aces processor`
surface, taking a bounded SDL file path and a closed named analysis profile and
emitting one JSON evidence envelope. Tests and the issue #168 research checker
must call this production service/CLI; no test-local translator or `tools/`
implementation may define its semantics. The checker currently hard-codes the
v1 `unsupported` replay mode and evidence status. Add a new protocol, corpus,
execution-snapshot, and analysis revision selected by the bundle manifest;
preserve every v1 file and observation unchanged. Recommended exit behavior is
`0` for completed satisfiable or unsatisfiable analysis, `2` after emitting an
unsupported result, and `1` for malformed input or operational failure.

The result is an immutable returned/emitted artifact. This issue adds no
controller, HTTP endpoint, mutable service, repository, database, cache,
`ControlPlaneStore` record, runtime snapshot metadata, experiment-run archive,
or bespoke logger. A later experiment/evidence contract may reference the
artifact by governed identity and digest; it must not copy it into an open
metadata bag.

## Validation-Strength Disclosure

Update the canonical validation-profile documentation and issue #168 evidence
matrix when the production surface exists. Keep four independent fields:

- capability id/profile and exact theory coverage;
- outcome (`satisfiable`, `unsatisfiable`, or `unsupported`);
- gate execution status under ADR-072; and
- claim-evidence status under ADR-021.

A replayed SAT witness or governed UNSAT core can support an evidence-backed
claim for the exact theory/configuration it binds. Mutation and negative-control
results can support falsification-backed disclosure only when the named
protocol's thresholds pass. Neither outcome by itself upgrades schema,
semantic, reachability, realizability-envelope, behavioral, or other admission
profiles. Unsupported or not-run analysis must remain visible and cannot be
collapsed into ordinary semantic validity.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required boundary |
| --- | --- |
| Authority and disclosure | ADR-007/009/019/021/072, `specs/authority/authority-boundary.yaml`, `specs/formal/assurance-policy.yaml`, the future focused ADR/normative spec, and validation-profile terminology. A preflight, generated schema, or passing test is not normative theory authority. |
| SDL ingress and composition | `sdl-yaml/v1`, `SDLParserLimits`, `load_sdl_yaml`, `parse_sdl_file()`, safe YAML and mapping-key gates, module trust/lock/digest/signature/path/cycle checks, `Scenario`/`ExpandedScenario`, and `SemanticValidator`. No solver-specific parser or import resolver. |
| Variables and target typing | `Variable`, `VariableType`, `${name}`, `WholeFieldVariableReference`, `x-aces-variable-reference`, `parse_enum_or_var`, `parse_int_or_var`, `parse_bool_or_var`, existing enum/bound validators, and instantiation's substitution rules. No duplicate domain/type system. |
| Phase and replay evidence | ADR-078, `canonical_sdl_digest()`, `instantiate_scenario()`, `admit_instantiated_scenario()`, `InstantiationProvenance`, `InstantiatedScenarioSnapshot`, and `canonical_instantiated_sdl_digest()`. Do not trust private validation flags or emit duplicate bindings. |
| Narrow existing relations | ADR-070, `aces_contracts.realization_envelope`, `member()`/`subsumes()`/`witness()`, workflow analyzers, and planner graph logic. Reuse compatible scalar/domain primitives only; never reuse their result or claim boundary as whole-scenario satisfiability. |
| Contracts and publication | `ContractModel(extra="forbid")`, `schema_bundle()`, `contracts/schemas/`, `contracts/fixtures/`, `contracts/schema-publication-manifest.json`, schema change ledger, generated-schema parity, and JSON artifact checks. Add one contract family, not an authority root or schema registry. |
| Diagnostics and errors | `Diagnostic`, `Severity`, `diagnostic_payload()`, `SDLParseError`, `SDLValidationError`, `SDLInstantiationError`, `specs/sdl/diagnostics.md`, and `aces_cli.processor._sdl_error_summary()`. Unsatisfiable is a completed result, not an exception. |
| Production processing | ADR-036, `aces_processor`, `aces_cli.processor`, `run_reference_processor()` conventions, and the `aces processor` Typer group. `aces_mcp.tools.inspection` and its semantic-validation bypass are not admissible entrypoints. |
| Evidence and tests | `docs/research/formal-semantic-validation/`, its protocol/snapshot/analysis/manifest and focused checker, positive/negative contract fixtures, `test_pipeline_determinism.py`, Hypothesis/property tests, and mutation/agreement tests. Preserve the previous evidence record. |
| Workflow and supply chain | `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014/015, `noxfile.py`, `SessionReporter`, `tools/verify_all.py`, module-boundary policy, OSV scanning, lockfile review, `THIRD_PARTY_NOTICES.md`, gitleaks, and private-key detection. Add a focused gate once to the existing graph, not a parallel workflow. |

## Security And Whole-Path Gates

The intended design passes every layer below.

1. **Source/parser gate.** Input uses `parse_sdl_file()` with the existing UTF-8,
   byte/scalar/depth/node/alias, YAML 1.2 Core, directive/tag, JSON-domain,
   duplicate/canonical-key, closed-model, mapping-key, and semantic-validation
   gates. File-backed imports retain trust policy, lock/digest/signature,
   namespace, path-confinement, collision, and cycle enforcement. The analyzer
   never accepts a raw mapping or `skip_semantic_validation=True` artifact.
   Today `parse_sdl_file()` calls `Path.read_text()` before the loader enforces
   `SDLParserLimits`, and local composition repeats unbounded `read_text()` /
   `read_bytes()` calls. Harden one shared root/import ingress to read at most
   `max_input_bytes + 1` bytes, reject overflow before UTF-8/YAML work, and reuse
   the same exact bytes for parsing and content digesting; a prior `stat()` check
   alone is TOCTOU-prone. Do not add a solver-only reader. Preserve the ordinary
   parser's diagnostics and use a portable logical source identity rather than
   an absolute host path in evidence.
2. **Translation/config shape gate.** Closed contracts and the central coverage
   table reject unknown profile ids/options, duplicate symbols/clauses,
   duplicate domain members under the existing SDL JSON-scalar equality rules,
   dangling references, sort/domain mismatches, unsupported occurrences, empty
   required domains, excessive counts, and inconsistent digest joins. Profiles
   are explicit function/CLI inputs, not ambient environment variables or open
   dictionaries.
3. **Solver gate.** The adapter constructs solver terms from the normalized DTO;
   it never parses caller-supplied SMT, loads plugins, invokes callbacks, makes
   network requests, or accepts arbitrary tactics/options. It fixes resource
   bounds, single-thread/parallel behavior, model/core modes, seed, logic, and
   automatic configuration. `unknown` and budget exhaustion fail closed.
4. **Authentication/authorization gate.** The local read-only CLI adds no auth
   surface. A later remote adapter must reuse
   `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy
   identity, role and target authorization, request-size guards, idempotency/
   fingerprints for mutations, audit summaries, and the redacted internal-error
   handler. Solver access is not a reason for a privileged research bypass.
5. **Secret/sensitivity gate.** Existing explicit `redacted`/`operator_secret`
   omission rules remain authoritative; name heuristics remain advisory. A
   normalized domain or witness can still contain sensitive authored or
   synthetic credential values, so evidence inherits source sensitivity and is
   never presumed public. Diagnostics/logs must not render values, domains,
   binding maps, source documents, solver expressions/models, trust policy,
   Pydantic input, or tracebacks.
6. **Environment and OS/process gate.** There is no environment-selected solver
   path, seed, tactic, profile, corpus root, or secret. The in-process API avoids
   a solver subprocess entirely. Only a safe file path/profile id appears in
   CLI argv; raw scenario text, assignments, credentials, tokens, models, and
   evidence do not. Any future external solver is a separate adapter/decision
   using fixed argv, stdin for bounded data, `shell=False`, and equivalent
   sandbox/resource controls.
7. **Error-envelope gate.** Source faults retain the bounded SDL exception
   channels and sanitized CLI rendering. Analysis diagnostics use stable codes,
   domain `scenario-satisfiability`, safe RFC 6901/canonical addresses, bounded
   messages, and the existing `Diagnostic` payload. Raw native/Pydantic errors
   are never public. The CLI top boundary converts adapter/internal failures to
   one fixed, value-free stderr summary and exit `1` while retaining the cause
   only for library callers; it must not let Typer/native tracebacks or solver
   exception text become the public envelope. Solver unsatisfiability is not
   rendered as a 500/error; an internal exception is not rendered as
   `unsupported`.
8. **Supply-chain/workflow gate.** Review Z3's license and native-wheel/platform
   support, add the required notice if applicable, equality-pin the dependency
   and lock artifacts, run OSV, and retain repository secret/private-key,
   schema-publication, package-boundary, source-size, docs, and verify gates.
   No runtime download or solver binary discovery is permitted.
9. **Persistence/observability gate.** Emit/store only the closed evidence
   artifact through caller-selected ordinary file handling. If operational
   metrics are later added, restrict them to safe profile ids, digests, counts,
   outcomes, and durations. Do not log or persist source bodies, domains,
   witnesses, cores, or native solver dumps in control-plane/audit metadata.

## Extensibility Seam

The explicit seam is a closed triple:

```text
(theory_profile, translation_profile, solver_profile)
```

Expose only governed analysis-profile ids that map to compatible triples; do
not let callers freely combine individually valid ids. Resolve the selected
triple once and pass it into one analysis service rather than selecting it
through globals or environment state. The normalized model and result contracts
are solver-neutral; a narrow adapter protocol permits a later independently pinned engine for
differential evidence without changing SDL or weakening v1. A new supported
domain/constraint family extends the normative theory, one central coverage
disposition, translator, fixtures, replay, and mutation evidence. It does not
add arbitrary plugins or silently broaden an existing profile.

The next reasonable input variation is a future admitted scenario-variation or
trial-plan artifact under ADR-084. It should add a translation/input profile
that produces the same normalized model, not overload realization-envelope
membership, rewrite the authoring-scenario profile, or make experiment
selection part of solver configuration.

## Gotchas And Anti-Patterns

Avoid:

- presenting schema/Pydantic acceptance, semantic validation, acyclicity,
  workflow reachability, realizability-envelope membership, a concrete
  instantiated artifact, or FM/validation-strength labels as satisfiability;
- conjoining objectives, success assertions, workflow pre/postconditions,
  runtime truth, adversarial goals, backend feasibility, or observation claims
  as simultaneous static constraints merely because they contain predicates;
- solving an already instantiated scenario as the main positive control;
- treating local non-empty domains as a proof that shared whole-scenario
  assignments exist;
- ignoring, concretizing by default, or warning through an unhandled variable
  occurrence; unsupported coverage is a fail-closed typed result;
- reading an unbounded file and applying `SDLParserLimits` only after the bytes
  are already resident, hashing newline-normalized text instead of exact source
  bytes, or recording an absolute checkout path as portable provenance;
- compiling arbitrary JSON Schema/Pydantic validators, Python expressions,
  JSONPath, SMT-LIB, callbacks, or free-form solver options;
- using arbitrary model/core order, solver defaults, wall time, process id,
  thread scheduling, hash iteration, or an unrecorded seed in evidence;
- calling a core a certificate, claiming global minimum when only
  subset-minimality is established, or accepting a witness/core without replay;
- exposing source/domain/binding/model content through diagnostic messages,
  argv, logs, audit entries, Pydantic errors, stack traces, or test snapshots;
- adding a solver dependency without exact pin, lock, license/platform, and
  vulnerability review;
- adding a second variable/domain model, schema registry, canonicalizer,
  digest shape, exception hierarchy, diagnostic envelope, import resolver,
  persistence store, logger, controller, MCP-only implementation, or CI
  workflow; and
- overwriting issue #168's prior evidence or counting a test-local solver,
  empty fixture discovery, unsupported case, or weakened mutation as a pass.

## Non-Goals And Implementation Boundaries

- This preflight does not implement issue #826, choose final field names or an
  exact Z3 release, publish the normative theory, or provide an implementation
  plan.
- The initial capability is not a general SMT service, theorem prover, model
  checker, optimizer, planner, scheduler, attack-graph/exploit-path validator,
  counterfactual engine, or runtime behavioral validator.
- It does not prove deployment feasibility, backend realizability, reachability,
  objective success, exploitability, temporal correctness, scenario quality,
  or equivalence across solvers/theory revisions.
- It does not add SDL expressions, unbounded numeric/string reasoning, float
  semantics, interpolation semantics, quantifiers, stochastic choice, or
  future scenario-variation syntax by implication.
- It does not add HTTP/MCP endpoints, authentication policy, mutable runtime or
  experiment persistence, secret resolution, subprocess execution, or network
  access.
- A supported result is valid only for the exact source, expanded semantic
  identity, normalized-model profile/digest, solver build/configuration, and
  result evidence it binds. Any change requires re-analysis; compatibility is
  never inferred from a green result produced under another profile.
