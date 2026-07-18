# Issue 43 Contracts Package Split Preflight

Date: 2026-07-17

Issue: #43.

Requirement: none. The GitHub issue is the implementation contract.

This note records architecture guardrails for converting
`aces_contracts.contracts` from one module to a package. It does not implement
the split, change a contract or schema, drain the oversized allowlist, alter
tests, or add release-note content.

## Binding Decisions

- The live target is 8,430 lines, not the issue body's older 1,256 lines. The
  split must preserve all contract families accumulated since that snapshot.
- ADR-015 and `tools/policy/adr_policy.yaml` now enforce a 500-line cap, not
  600 lines. Every Python file in `aces_contracts/contracts/`, including
  `__init__.py`, must remain at or below 500 lines.
- `contracts/__init__.py` is the stable `aces_contracts.contracts` facade. No
  external import line targeting that facade changes, and child modules are
  implementation details rather than new supported import surfaces.
- Preserve the current ordered 219-name `__all__` exactly. Also preserve facade
  attributes used by current importers but absent from `__all__`:
  `NonEmptyString`, `ParticipantObservationDetailsModel`,
  `_collapse_nullable_optional_schema`, `_resolve_instance_path_schema`,
  `_resolve_ref_schema`, `_resolve_schema_pointer`, and
  `_validate_reference_model_schema_binding`.
- Preserve every published semantic-invariant locator beginning with
  `aces_contracts.contracts.`. These strings are checked by
  `_resolve_semantic_validator()` and are embedded in checked-in schemas; they
  must continue to resolve through the facade rather than changing to child
  module paths.
- Preserve the legacy `aces.core.runtime.contracts` wrapper, which delegates to
  this facade through `aces._compat.reexport`.
- The implementation removes the deleted path only from
  `tools/policy/oversized_allowlist.yaml`. The locked historical reference in
  `tools/policy/repo_policy.py` remains: ADR-015 uses it to prove that the
  allowlist only shrinks.
- Release-please owns `CHANGELOG.md`. Despite the stale issue acceptance item,
  `.gc/plan-rules.md` forbids editing `CHANGELOG.md` or adding a fragment; the
  implementation must follow the live repository rule.

## Architecture Boundary

Keep one dependency direction:

1. closed-model foundations and constrained scalar aliases;
2. schema annotation/constraint helpers;
3. domain models and their domain validators;
4. the schema-bundle assembler; and
5. the thin public facade.

Foundation modules must not import domain modules, the schema-bundle assembler,
or the facade. Domain modules import foundations and earlier domain types
directly. The bundle assembler may consume all domain models, but its existing
late imports of sibling contract modules must stay late. The facade explicitly
re-exports supported names and contains no model, validation, or bundle logic.

Split by semantic ownership rather than line ranges. The live cohesive domains
are: common Pydantic contract primitives; JSON Schema constraints and semantic
invariant annotations; workflow/evaluation/truth envelopes; participant
episode, behavior, observation, shared-state, concurrency, outcome, and view
contracts; plans, snapshots, capabilities, and manifests; experiment
references, artifacts, capture/evidence, apparatus, task, run, study, and
authoring contracts; concept/reference/vocabulary/semantic-profile catalogs;
reusable-asset trust policy; and bundle assembly. Large experiment and
participant domains may use more than one dependency-directed file to satisfy
the cap, but must not be collapsed into generic "runtime" or "experiment data"
abstractions.

Keep model-specific `model_validator` and `__get_pydantic_json_schema__` logic
with the model it constrains. Keep multi-model validators with their semantic
owner. Shared helpers are justified only when multiple domains already use the
same rule; a `common.py` dumping ground, generic model registry, service
container, or plugin framework would replace one oversized file with concept
confusion.

Existing `aces_contracts` sibling modules currently import the facade. Any
sibling that participates in bundle construction must instead import the exact
foundation or owning child module needed during initialization; internal
submodules must never route dependencies back through `contracts.__init__`.
Retain local imports where they currently break real cycles, especially bundle
access to backend profiles, behavioral relations, provenance, scientific
completeness, and realization-envelope models.

The extension seam remains explicit and data-shaped: a future contract model
belongs to its semantic owner, is deliberately re-exported if public, and is
wired once into the existing contract-id-to-schema mapping in
`_raw_schema_bundle()`. Cross-cutting schema transforms continue to accept
`contract_id` plus the schema and run from the single ordered loop in
`schema_bundle()`. Do not introduce discovery, import scanning, or registration
side effects.

## Required Incumbents

- **Closed contract shapes:** `ContractModel` with
  `ConfigDict(extra="forbid")`, existing `Annotated`/`Field` aliases, Pydantic
  `model_validator` methods, and model-specific JSON Schema hooks.
- **Schema/version authority:** `aces_contracts.versions`,
  `contracts/schemas/`, `contracts/schema-publication-manifest.json`,
  `schema_bundle()`, `tools/generate_contract_schemas.py`, and
  `tools/check_generated_schemas.py`. The split changes no generated schema,
  contract id, version, manifest hash, fixture, or authority artifact.
- **Semantic and concept authority:** `aces_contracts.vocabulary`,
  `manifest_authority`, `corpus.corpus_family_root`, existing concept catalogs,
  controlled-vocabulary validators, semantic profiles, and the invariant
  annotation/resolution machinery. Do not copy authority sets or load corpus
  files through a new path heuristic.
- **Identity and planning:** `aces_contracts.addressing`,
  `aces_contracts.planning`, canonical compiled-address schemas, plan-domain
  maps, and `require_plan_operation_identity` remain the single identity
  sources.
- **Compatibility:** explicit facade exports and `aces._compat.reexport` remain
  the repository's compatibility mechanisms. Do not add a second shim layer or
  wildcard exports that leak imported dependencies.
- **Errors and observability:** retain Pydantic `ValidationError` composition
  and existing `ValueError`/`KeyError` boundaries, messages, and ordering. This
  module has no logger or alternate error envelope; the refactor must not add
  one or create a duplicate exception hierarchy.
- **Persistence:** contract models remain data-only. The only filesystem reads
  here are governed concept-corpus reads through `corpus_family_root`; there is
  no repository, database, cache, or write path to abstract.
- **Workflow:** ADR-015/ADR-036, `tools/check_repo_policy.py`, the generated
  schema drift gate, schema publication checks, and the pinned nox `verify`
  session remain the canonical completion graph.

## Cross-Cutting And Security Layers

- **Structural validation:** all payloads still enter the same closed Pydantic
  models, constrained scalar fields, and model validators. Moving a class must
  not weaken `extra="forbid"`, field strictness, cardinality, uniqueness,
  cross-field validation, or validation order.
- **Portable JSON Schema validation:** every model and schema hook must emit
  JSON equal to the checked-in normative schema. Preserve `$defs`, `$ref`,
  conditionals, ACES metadata, contract ordering, and post-processing order;
  passing model tests while changing schema output is a failure.
- **Semantic-invariant resolution:** `_resolve_semantic_validator()` continues
  to resolve the existing published callable locators, including facade-based
  class methods and functions. The split must not broaden accepted locator
  syntax, execute validators during resolution, or rewrite locators to private
  child modules.
- **URI and secret-bearing locator validation:** keep
  `_validate_associated_artifact_uri()` with the associated-artifact model and
  preserve its absolute-URI, credential-userinfo, and secret-query-name gates.
  Do not generalize it into a looser shared URL parser.
- **Trust/authenticity validation:** reusable-asset integrity, signature
  threshold, signer-set-reference, provenance, and governance-source rules
  remain the existing Pydantic and portable-schema constraints. Do not add key
  material, a new trust store, or a parallel evidence schema.
- **Authorization and secret handling:** this package makes no authorization
  decision and reads no credential store. References, digests, sensitivity
  markings, and public verification metadata remain data; raw credentials or
  secret values must not be added to models, diagnostics, logs, or exceptions.
- **Environment and configuration shapes:** the split adds no environment
  binding. Existing explicit request/profile/parameter fields remain the only
  configuration inputs; no behavior may depend on environment variables or a
  new config schema.
- **OS, process, network, and persistence exposure:** model validation remains
  in-process. The split adds no subprocess, process-argv value, network call,
  database, cache, filesystem write, or caller-controlled path traversal. The
  existing read-only corpus resolver remains the only filesystem seam.
- **Error-envelope leakage:** preserve current bounded validation messages and
  exception types. Do not log or embed raw payloads, URI query values,
  environment values, credentials, corpus contents, or tracebacks.
- **Package and repository policy:** child modules remain under
  `aces_contracts`, whose ADR-036 boundary allows only `aces_sdl` as a
  first-party dependency. Every replacement file must pass the 500-line gate,
  import-boundary checks, secret/private-key scanning, and the canonical verify
  graph.

## Gotchas And Anti-Patterns

- Do not leave both `contracts.py` and `contracts/`; conversion is one atomic
  replacement. Do not change external `aces_contracts.contracts` import lines.
- Do not assume `__all__` alone is the compatibility inventory. Current callers
  use seven additional facade attributes, including five private schema-binding
  helpers, and published invariant strings resolve additional facade members.
- Do not use wildcard re-exports. They would expose Pydantic, `aces_sdl`,
  version, and helper imports that happened to be module globals in the old
  file and make initialization order unstable.
- Do not import the facade from child modules. That produces partially
  initialized package failures, especially when a sibling such as
  `realization_envelope` or `backend_profiles` is imported before the facade.
- Do not rely on unresolved cross-module annotations. Pydantic needs every
  referenced field type available in the defining module; preserve the
  dependency DAG with explicit imports rather than a global `model_rebuild()`
  registry.
- Do not change schema-bundle key order, schema post-processor order, invariant
  ordering, validator strings, error messages, defaults, aliases, model dump
  behavior, enum identity, or digest canonicalization while moving code.
- Do not redefine constrained strings, reference DTOs, validation helpers,
  authority sets, exception types, or schema fragments in several subdomains.
- Do not hand-edit generated schemas or the publication manifest to absorb
  refactor drift. Refactor output must match the existing authority artifacts.
- Do not rewrite class `__module__` metadata or add pickle shims without an
  independently demonstrated compatibility contract. Repository authority is
  the language-neutral schema plus stable facade imports, not Python pickle
  bytes or private child-module locations.
- Update durable prose/spec references that name the deleted `contracts.py`
  source path to the facade package or correct semantic owner. Leave test-local
  literal paths alone when they intentionally exercise policy behavior; do not
  modify pre-existing tests to accommodate the split.
- Do not edit `CHANGELOG.md`, versions, ADR bodies, policy code, or unrelated
  contract behavior as incidental cleanup.

## Non-Goals

- No contract, schema, validator, error, semantic-invariant, identity,
  canonicalization, trust, URI, manifest, corpus, fixture, or conformance
  behavior change.
- No new public child-module API, model registry, generic contract framework,
  DTO, exception hierarchy, logger, configuration surface, persistence layer,
  network API, CLI, or compatibility namespace.
- No movement of neutral DTO ownership into SDL, processor, runtime, backend,
  conformance, CLI, MCP, or the legacy `implementations/python/src/aces` tree.
- No schema regeneration churn, publication-manifest change, test relaxation,
  performance rewrite, version edit, or release-note edit.
