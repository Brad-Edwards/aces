# Issue #265 / AUT-810 — Safe artifact transformations preflight

Date: 2026-07-31

Issue: #265.

Requirement status: requirement-free run; the issue is the delivery contract.

This note fixes the architecture boundary for pure, deterministic refactoring
and transformation of canonical RAES SDL and portable contracts. It is
non-normative guidance only. It does not implement an operation, publish a
schema, change SDL or contract meaning, migrate an artifact, or add a workflow.

## Decisive current-state findings

- `raes` already owns SDL models, parsing, semantic validation, composition,
  instantiation, canonical identity, declarations, references, and phase
  provenance. The public semantic transformation facade belongs there.
- The existing `raes_operations` package is the backend-evidence orchestration
  layer. Its allowed imports include runtime and libvirt surfaces. Despite its
  name, it is not the home of a pure artifact-transformation kernel.
- `raes_contracts` owns dependency-neutral closed portable models, diagnostics,
  canonical JSON, published-schema generation, and portable contract adapters.
  A portable transformation report belongs there if it is published. It must
  not import SDL implementation details to perform an operation.
- `canonical_sdl_digest()`, `canonical_instantiated_sdl_digest()`, and
  `canonical_contract_digest()` already define canonical identities. The
  `canonical-artifact-identity` relation explicitly proves canonical byte
  identity only. A rename normally changes the digest, so digest inequality is
  not loss and digest equality cannot be the rename-preservation test.
- `composition.py` already contains the namespace, reference-rewrite, merge,
  budget, and phase-provenance behavior used by imports. A second rewrite table
  would drift. The pure namespace/rewrite/merge core must be shared with that
  incumbent, while file, OCI, lock, signature, trust, and resolver behavior
  stays at the existing import boundary.
- `specs/sdl/references.md`, `DeclarationIndex`, `_module_symbols.py`, and the
  semantic validators together own reference meaning. Language-service
  completion and occurrence metadata are presentation aids, not an exhaustive
  semantic rename engine. `apply_structured_edit()` intentionally returns
  edited text even when the edit has diagnostics; that is not the atomic
  transformation contract required here.
- ADR-075 and the normative evolution specification already require automated
  migration to be deterministic, idempotent, source-preserving, explicit about
  ambiguity/loss, and fail-closed. They reject a universal migration service.
- This work is FM2: rename is an FM1 static-semantic change, but composition,
  extraction, dependency closure, and reference transport are graph semantics.
  The FM2 floor requires an invariant list, unit tests, typed contract
  coverage, and property-based or differential tests.

ADR-036, ADR-053, ADR-061, ADR-075, ADR-076, ADR-078, ADR-080, and the existing
normative specifications settle the durable architecture. No new ADR is needed
unless implementation discovers a requirement incompatible with those
authorities.

## Architecture decisions and boundaries

### One pure kernel, operation-specific entry points

Expose a small public facade from `raes`, backed by operation-specific pure
functions. Inputs include the admitted artifact, exact operation request,
closed policy, and any linked artifacts or resolution context needed to make
the result unambiguous. There is no filesystem, network, process, environment,
clock, random, singleton-registry, UI, or persistence input hidden behind an
entry point.

Do not create a generic object-tree transformation language or callback/plugin
executor. Rename, compose, extract, and exact source/target migration pairs
have different preconditions and preservation obligations. They may share one
closed report vocabulary and common admission/comparison helpers without
pretending to be the same algorithm.

Portable contract migration adapters stay with their owning contracts. The
`raes` facade may dispatch to dependency-neutral `raes_contracts` adapters;
`raes_contracts` must not import the SDL kernel. Dispatch is by exact supported
source and target contract/profile, never by a mutable notion of "current" or
"latest".

### Transactional value semantics, not filesystem atomicity

SDL models are not generally frozen. An operation must reconstruct an isolated
candidate from typed data, transform only that candidate, and pass the complete
candidate through its normal structural, semantic, phase, and canonicalization
gates before exposing it. A shallow copy, Pydantic `model_copy()` without
readmission, or temporary mutation followed by rollback is insufficient.

The public result has exactly one of these shapes:

- success: complete admitted typed output plus a complete report; or
- refusal: no output plus a complete report containing the failed condition
  and typed diagnostics.

Expected ambiguity, loss-policy, precondition, or postcondition failure is a
machine-readable refusal, not a partially useful artifact and not a new
exception family. Existing `SDLParseError`, `SDLValidationError`,
`SDLInstantiationError`, Pydantic validation, and `StrictJsonIngressError`
remain the malformed-input/programming boundaries. The caller's input object
and canonical bytes must remain unchanged for success and refusal alike.

"Atomic" in this package means all-or-none in-memory output. Atomic file
writes, rollback, pack transactions, and repository commits belong to the
consumer.

### One closed, bounded transformation report

If a portable report is published, define it once as a frozen, closed
`ContractModel` in `raes_contracts` and use the existing `DiagnosticModel` for
its general diagnostics. The report must carry, in deterministic order:

- exact operation profile/revision and result status;
- source and requested target artifact kind, lifecycle/contract profile, and
  canonicalization profile, with a source digest always and a target digest
  only for admitted output;
- machine-readable precondition and postcondition check ids and outcomes;
- affected declaration identities and an explicit before-to-after identity
  map;
- the named preservation/comparison profile, outcome, and bounded evidence;
- stable derivation from input digest(s), operation profile, and canonical
  policy digest; and
- typed loss/ambiguity records with stable kind, affected identity/address,
  and safe diagnostic.

The report is not an artifact bundle. It references inputs and outputs by typed
identity and digest; operation-specific Python results carry the actual typed
artifacts. Do not embed arbitrary payloads, raw source, open `metadata`, caller
objects, timestamps, UUIDs, usernames, host paths, or backend evidence.

A small governed loss-kind vocabulary is justified by the issue. It extends,
rather than replaces, `DiagnosticModel`. Do not reuse participant-crossing
loss or external-concept approximation types for unrelated artifact loss, and
do not introduce another general severity, diagnostic, or exception hierarchy.
Default loss and ambiguity policy is reject. An explicit policy may authorize
named, reported loss; it cannot authorize guessing. Ambiguous identity lookup
must be resolved by an exact canonical address or explicit complete mapping,
never first/last match, set collapse, or `force=True`.

### Preservation is a named relation, not a boolean

Every successful operation declares the artifact stage and comparison profile
it actually checks. `semantic_preserved: true` without a governed relation and
evidence is forbidden.

- Exact/no-op transformations may use `canonical-artifact-identity` with the
  same named canonicalization profile.
- Rename requires static semantic identity transport: a bijection maps the
  changed declaration address and every derived canonical address, and the
  resolved declaration/reference graph plus non-identity semantic fields must
  be isomorphic under that map. Compare resolved targets, not authored string
  spelling. If this relation is made public, add a narrowly scoped relation to
  the existing behavioral-relation catalog with explicit nonclaims; do not
  create a local relation registry.
- Extraction is preservation of the collective result. Recompose the returned
  root and extracted module using the declared namespace/import coordinate and
  require canonical identity with the original artifact (or the named identity
  transport relation). Validating the two files independently is not a
  preservation proof.
- Composition names every supplied module, namespace, export set, binding, and
  provenance input. Its postcondition compares the expanded result against the
  existing ADR-053 composition semantics; it does not claim that one input was
  individually preserved as the whole output.
- Contract migration uses exact source/target-version invariants, source and
  target admission, and round-trip evidence when the mapping is reversible.
  A lossy migration cannot report unqualified full preservation; it may verify
  only an explicitly named unaffected projection while still reporting every
  policy-authorized loss. Successful parsing at the target version is not a
  meaning-preservation result.

Verification over the supplied artifacts is finite verification, not a
universal proof. Neither canonical identity nor identity transport establishes
behavioral, observational, epistemic, strategic, backend, or scientific
equivalence. Any stronger public claim must use the existing governed
behavioral-relation claim machinery and meet that relation's obligations.

### Reuse the canonical identity and reference machinery

Declaration selection starts with `build_declaration_index()` and an exact
canonical address from ADR-076. The transformation must preserve declaration
kind and reject collisions, dangling references, new ambiguity, illegal target
kind, or an address map that is not injective.

The rewrite inventory must be the same semantic seam used by module
composition. Refactor dependency-neutral helpers out of `composition.py` when
necessary so composition and transformations share:

- `_module_symbols.HASHMAP_SECTIONS`, `FORWARDING_AGENTS_SECTION`,
  `symbol_index()`, exports, nested service/runtime/content aliases, and
  variable-token handling;
- the namespace/reference rewrite and section-merge behavior in
  `composition.py`;
- `_composition_provenance.py` for rebasing existing phase provenance; and
- the reference-edge obligations and owning validators enumerated by
  `specs/sdl/references.md`.

Do not create a third top-level-section catalog. `_module_symbols.HASHMAP_SECTIONS`
owns composition/declaration identities; `_mapping_scopes.HASHMAP_SECTIONS`
owns authored mapping-key interpretation. Keep those distinct. List-valued
`forwarding_agents` use a stable id while model/provenance paths are positional,
so extraction and rename must not confuse list position with identity.

Generic language-service occurrence search, JSON Pointer editing, global
string replacement, dotted-string splitting, aliases, labels, filenames, and
array positions do not establish semantic reference identity. The complete
post-transform `SemanticValidator` pass remains authoritative even after a
rewrite helper reports success.

### Keep composition/extraction pure without weakening import security

A pure compose/extract call accepts already supplied, admitted typed artifacts,
logical namespaces/export selections/bindings, and any exact resolved-import
provenance it is entitled to preserve. It does not resolve `ImportDecl.source`,
discover adjacent files, read a lockfile, fetch OCI, choose a pack path, verify
a signature, or infer trust.

The caller supplies the logical import coordinate needed by an extracted root;
RAES must not invent a path or pack layout. Artifact-native
`ExpansionProvenance` retains only facts actually established by the existing
resolver/trust boundary. Transformation derivation lives in the accompanying
report and must not masquerade as signature, lock, or trust evidence.

Existing `parse_sdl_file()` composition continues to enforce base confinement,
source budgets, resolver allowlists, version and digest pins, lock records,
signature/trust policy, exports, namespaces, cycles, bindings, and aggregate
composition budgets. Extracting the pure rewrite/merge core must not move,
duplicate, or bypass those gates.

### Treat concept bindings as linked artifacts, not SDL fields

`ExternalConceptSubjectModel` binds a canonical declaration reference to the
owning artifact digest. A rename changes the renamed canonical reference and
the whole artifact digest. Therefore every supplied binding subject for that
artifact needs its digest updated, not only bindings naming the renamed
declaration.

An operation may atomically transform explicitly supplied
`ExternalConceptBindingDocumentModel` values and then rerun their structural
and contextual semantic admission. If binding documents are not inputs, the
report exposes the identity/digest map needed by orchestration; the kernel does
not discover them. A binding cannot select a rename target, override
declaration ambiguity, or become identity authority. No concept catalog,
scheme snapshot, URI, or network lookup is implicit.

## Canonical cross-cutting concerns to reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Package ownership | ADR-036 and `tools/policy/adr_policy.yaml`; SDL kernel in `raes`, portable contracts in `raes_contracts`, conformance in `raes_conformance`, presentation only in CLI/MCP. Keep semantic code out of `raes_operations`, processor, runtime, Hub, and pack adapters. |
| SDL source admission | `SDLParserLimits`, `_yaml_loader.py`, `_source_validation.py`, `_source_profile.py`, `parse_sdl*()`, and closed `SDLModel` types. Preserve UTF-8, byte/scalar/depth/node/alias/composition bounds, YAML 1.2 Core, tag/directive, duplicate/normalized-key, finite-JSON-domain, and explicit `SDLMigrationPolicy` gates. |
| Portable JSON ingress | `parse_bounded_json_object()` and `StrictJsonIngressError`, followed by the exact closed source `ContractModel`. Inspect the raw source shape before model defaults/unknown-field rejection can erase migration evidence. Never `json.loads()` then silently project known fields. |
| Static semantics | `SemanticValidator`, `DeclarationIndex`, ADR-076 identifiers, `specs/sdl/references.md`, `specs/sdl/diagnostics.md`, and the existing domain validators. Run full admission before and after; do not duplicate validation in operation code. |
| Phase and canonical identity | ADR-078, `phase_contracts.py`, `admit_instantiated_scenario()`, `canonical_sdl_*`, `canonical_instantiated_sdl_*`, and dependency-neutral `raes_contracts.canonical`. Preserve lifecycle distinctions and use the canonicalizer owned by the artifact type. |
| Composition and provenance | ADR-053, `composition.py`, `_module_symbols.py`, `_composition_provenance.py`, resolver/lock/trust modules, and composition-budget checks. Share the pure core; leave I/O and trust orchestration at the incumbent boundary. |
| Portable evolution | ADR-061, ADR-075, `specs/evolution/versioning-deprecation-and-migration.md`, exact contract discriminators in `raes_contracts.versions`, and owning source/target models. No universal registry or cross-surface version semantics. |
| Diagnostics/errors | `Diagnostic`, `DiagnosticModel`, `Severity`, the existing SDL error hierarchy, `specs/sdl/diagnostics.md`, `_model_diagnostics.py`, and `sanitized_failure_message()`. Use stable bounded codes and safe locations; add only the transformation-specific loss vocabulary. |
| External concepts | `ExternalConceptBindingDocumentModel`, `ExternalConceptSubjectModel`, and `external_concept_subjects()`. Recompute exact refs/digests for supplied documents and rerun existing contextual resolution; do not redefine concepts or fetch schemes. |
| Schemas and fixtures | `ContractModel(extra="forbid")`, `contracts/schemas/`, `schema_bundle()`, `_MODEL_VALIDATORS` / `_STRUCTURAL_ONLY_VALIDATORS`, `contracts/fixtures/`, `raes_contracts.corpus`, `run_fixture_suite()`, ADR-061 publication records, and generated-schema checks. Extend these once if a report is published; do not duplicate schema validation or corpus loading. |
| Assurance and claims | `specs/formal/assurance-policy.yaml`, the classification/fulfillment ledgers, the behavioral-relation catalog, claim validator, and `tools/check_assurance_policy.py`. Record truthful FM2 evidence and keep finite verification distinct from proof. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `.pre-commit-config.yaml`, `noxfile.py`, `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, `tools/verify_all.py`, Sphinx, private-key detection, and gitleaks. Wire checks into the existing graph, never a parallel workflow. |

Conformance artifacts should reuse the owning fixture families. Pair source,
request, expected output/report, and refusal cases by stable case id in the
test/conformance harness instead of copying them into a generic migration or
transformation bundle. Required coverage includes composed/private/exported
references, collisions and ambiguous aliases, workflow/variation/runtime
references, list-valued forwarding agents, concept-binding digest retargeting,
recomposition, allowed and rejected loss, failure immutability, idempotent
migration, and representative portable contracts. Property/differential tests
must vary declaration order, map insertion order, canonical-equivalent inputs,
and repeated execution.

The transformation case executor belongs in `raes_conformance` as a focused
sibling to the backend-profile fixture suite. It composes the existing corpus,
contract validators, sanitized diagnostics, deterministic case ordering, and
report conventions; it must not turn `run_fixture_suite()` into a semantic
operation engine or fork another JSON Schema validator.

## Cross-cutting validation, security, and operational layers

The intended design passes these layers even though the kernel itself is
offline:

1. **Ingress and shape.** Raw SDL uses the production bounded safe loader; raw
   portable JSON uses `parse_bounded_json_object()`. Exact closed source models
   validate before interpretation and exact target models validate afterward.
   Unknown or duplicate data is refused or reported under an explicit loss
   policy, never dropped by projection.
2. **Semantic and graph admission.** `SemanticValidator`, declaration/reference
   resolution, uniqueness, ambiguity, cycles, target kinds, dependency closure,
   and phase admission run before and after. A local rewrite check cannot bypass
   an owning validator.
3. **Canonical and preservation check.** The owning canonicalizer binds both
   endpoints. The named identity, identity-transport, recomposition, or
   version-pair predicate runs after target admission. Unordered implementation
   containers are sorted by governed identity unless order is semantic.
4. **Composition/trust.** Existing file/OCI resolver, lock, digest, signature,
   allowlist, confinement, cycle, export, and budget checks remain outside the
   pure core. A transformation report cannot mint or strengthen their evidence.
5. **Contract/schema/conformance.** A published report passes `ContractModel`,
   checked-in JSON Schema, `schema_bundle()` parity, registered conformance
   validation, positive/negative fixtures, publication manifest/hash/record,
   and compatibility classification. Schema success remains structural unless
   contextual semantics are separately checked.
6. **Authentication/authorization.** The library call adds no auth surface and
   grants no authority. A later HTTP adapter must reuse
   `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   target/role checks, request size, idempotency/fingerprint, audit, and redacted
   unexpected-error behavior. An MCP adapter reuses its 64 KiB input guard and
   `json_response()` envelope. Neither adapter may let caller identity or role
   alter pure semantics.
7. **Config and environment.** Operation profile, source/target profile,
   selection, namespace, and loss policy are explicit closed inputs. Add no
   environment switch, feature flag, config file, service locator, mutable
   registry, or ambient "latest" version. Workflow requirement context is not
   an artifact field.
8. **Secrets and OS exposure.** The kernel performs no file, network,
   subprocess, shell, privilege, or temporary-file action. Reports,
   diagnostics, logs, filenames, argv, and environment captures contain no raw
   SDL values, credentials, tokens, private keys, parameter maps, URI userinfo,
   source bodies, backend objects, absolute host paths, or environment dumps.
   A digest is identity, not redaction. A future CLI accepts bounded file/stdin
   input and separate output paths; sensitive artifacts are not command-line
   arguments.
9. **Error envelopes and observability.** Expected refusals use the portable
   report and existing diagnostics. Conformance/adapters use
   `sanitized_failure_message()` rather than `str(ValidationError)` or backend
   exceptions. The pure kernel adds no logger, telemetry stream, metrics
   registry, or audit store. Adapters may log only safe operation profile,
   digests, counts, stable codes, and outcome.
10. **Persistence.** No controller, service, repository, `ControlPlaneStore`,
    runtime snapshot, database, cache, or audit event stores transformations.
    Consumers own atomic writes and pack/repository transactions after a
    successful result. A failed operation has nothing to persist as an output
    artifact.

## Extensibility seam

The stable dispatch/comparison coordinate is:

```text
(operation_profile, artifact_kind, lifecycle_phase,
 source_contract_or_canonical_profile, target_contract_or_canonical_profile,
 preservation_profile, explicit_policy)
```

The obvious next version or artifact type adds one exact adapter and one
governed comparison profile at that coordinate; it does not edit a universal
`if current_version` branch. The SDL-specific extension seam is the single
shared declaration/reference rewrite catalog used by composition and
transformations. Adding a new SDL reference-bearing field extends that catalog,
`specs/sdl/references.md`, its owning validator, composition, language tooling,
and conformance tests together—not a per-operation field list.

Extraction additionally parameterizes explicit selection/dependency-closure
policy and caller-supplied logical namespace/import coordinate. Those are data,
not filesystem discovery hooks. Caller callbacks or arbitrary policy code are
not part of the portable seam.

## Gotchas and anti-patterns

Avoid:

- placing semantic transformations in `raes_operations`, CLI/MCP adapters,
  processor, runtime, Hub, or env-packs;
- treating an editor JSON-Pointer operation or language-service occurrence list
  as semantic rename;
- comparing only pre/post digests for rename, or calling digest equality
  behavioral equivalence;
- comparing an extracted fragment and root independently instead of proving
  recomposition;
- mutating an input and rolling back on error, returning invalid output beside
  diagnostics, or writing files before all postconditions pass;
- a global string replacement, substring/dotted-name rewrite, alias-selected
  target, first/last winner, unordered-set output, or field list copied from one
  validator;
- a second declaration/reference index, section catalog, canonical JSON
  serializer, generic diagnostics envelope, exception hierarchy, schema
  registry, migration registry, fixture runner, logger, or persistence store;
- silently dropping unknown JSON members by validating into the target model,
  defaulting absent source fields before classification, or interpreting target
  parse success as preservation;
- a broad `allow_loss`, `force`, or `allow_ambiguous` boolean; policy names exact
  accepted loss kinds and ambiguity is resolved by explicit identity;
- embedding artifacts in the report, using an open metadata bag, or recording
  clock time/random ids that make a pure result nondeterministic;
- rewriting only the renamed external-concept subject while leaving other
  subjects pinned to the old whole-artifact digest;
- forging `ExpansionProvenance`, lock/signature/trust facts, or pack source
  paths inside a pure operation;
- allowing a new SDL section or reference field to land without updating the
  shared rewrite/reference/conformance seam; or
- claiming proof, behavioral equivalence, runtime support, or pack-level
  transactional safety from finite transformation fixtures.

## Non-goals

- Pack layout, file discovery, multi-file transaction management, publication,
  repository migration, or automatic linked-artifact discovery.
- Browser/editor journeys, a pack CLI workflow, MCP presentation, HTTP routes,
  controllers, backend lifecycle, runtime execution, or experiment execution.
- A generic patch language, arbitrary transformation plugin system, universal
  artifact bundle, universal version/migration registry, or new canonical
  serialization format.
- Automatic resolution of ambiguous identities, automatic acceptance of loss,
  implicit network/schema/concept lookup, or inference of missing provenance.
- Redefining SDL semantics, concept authority, existing portable contracts,
  module trust, diagnostic severity, behavioral relations, or compatibility
  guarantees merely to make a transformation succeed.
- Filesystem atomicity or persistence inside RAES; the kernel's guarantee ends
  at a complete admitted typed result and deterministic report.
