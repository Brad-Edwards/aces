# Issue 767 Explicitness Provenance Identity Preflight

Date: 2026-07-13

Issue: #767. Requirement: none; the issue is the delivery contract.

This note records architecture guardrails for the import-expansion provenance
defect. It does not implement the parser change or its regression tests.

## Decision

`ExplicitnessProvenanceRecord.model_path` is the canonical address of a field
in the expanded executable scenario. It is not the address of a source-module
field and it is not an import-event identity. Consequently,
`ExpansionProvenance.explicitness` is a projection of imported author intent
onto fields that survive in the expanded scenario, not a complete ledger of
every classified source-module container and metadata field.

Composition must retain imported declaration descendants whose paths survive
expansion, and rewrite their declaration identity through the same symbol map
used for the imported payload. It must not retain module-local `name`,
`version`, or a section aggregate such as `behavior_specifications`: those
source fields do not become distinct fields in the host scenario. The root
scenario's classifier supplies its one surviving root metadata and aggregate
record during final instantiation.

Keep the existing uniqueness invariant: one provenance object has at most one
explicitness record per final `model_path`. Adding import namespace or source
to that identity would permit conflicting classifications for one concrete
field and would break the existing path-keyed instantiation and compiler
consumers. Do not weaken `_require_unique()` and do not deduplicate records
after construction. The producer must emit the right projection before the
closed phase contract validates it.

The current development baseline already filters imported records to
descendants of composition-owned hashmap sections, which prevents the reported
0.20.0 collisions. That behavior landed incidentally and is not sufficient as
the issue's durable evidence: regression coverage must make the projection,
namespace rewriting, uniqueness, nested-import behavior, and downstream
explicitness preservation explicit.

## Existing Boundaries To Reuse

- Composition ownership remains in `aces_sdl.composition.expand_sdl_modules()`.
  Import resolution, binding, namespace rewriting, merging, traversal limits,
  and provenance construction must remain one transition rather than a second
  post-processing workflow.
- `_composition_provenance.prefixed_explicitness()` and
  `_prefixed_model_path()` are the canonical portable transformation seam.
  Reuse `_module_symbols.symbol_index()` and its `HASHMAP_SECTIONS`; they are
  the authority for composition-renamed declarations, including generated
  `__private` identities. Do not infer prefixes by splitting arbitrary dotted
  text or duplicate the symbol table.
- `_bind_scenario_content()`, `derive_instantiated_explicitness()`, and
  `_merge_expanded_provenance()` own binding and the replacement of freshly
  classified imported paths with portable records. Parameter identities must
  continue to be qualified through the import namespace at composition.
- `ExplicitnessProvenanceRecord`, `ExpansionProvenance`,
  `InstantiationProvenance`, `_validate_derivation_collections()`, and
  `_require_unique()` are the closed validation contract. Do not add a second
  record shape, uniqueness validator, DTO, or exception hierarchy.
- `InstantiatedScenario.explicitness` and the compiler's existing
  path-keyed SEM-218 lookup are the downstream contract. A record is useful
  only if its path addresses the same field in the concrete scenario.
- ADR-053, ADR-076, ADR-078, `specs/formal/sdl-phases/README.md`, and the
  normative SEM-218 specification already govern composition identity, phase
  closure, and explicitness. This bug does not need a new ADR or a new
  provenance concept.
- Verification belongs with the existing composed/nested import tests in
  `test_sdl_phase_contracts.py` and `test_sdl_module_registry.py`. The
  repository workflow remains `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/verify_all.py`, and the canonical nox graph.

There are two similarly named section catalogs with different ownership:
`_module_symbols.HASHMAP_SECTIONS` excludes variables and governs importable
declaration identities; `_mapping_scopes.HASHMAP_SECTIONS` also includes
variables and governs authored mapping-key interpretation. Composition
provenance must use the former. Do not create a third catalog or substitute the
source-mapping catalog merely because the names match.

## Cross-Cutting Layers

- **Source and migration gate:** every root and imported document must still
  pass `_source_validation.py`, `_load_normalized_data()`, the selected
  `SDLMigrationPolicy`, parser resource limits, canonical key handling, and
  closed `SDLModel` construction. The fix must not preprocess YAML or special
  case private downstream content.
- **Import trust and filesystem gate:** retain `ImportDecl` validation,
  `module_registry.resolve_import()`, local-base resolution, lockfile checks,
  version/digest/export validation, registry trust/signature policy, cycle
  detection, and `CompositionBudget`. Provenance projection occurs only after
  the import has passed those gates; it must not create another file read or
  resolver path.
- **Namespace and merge gate:** use the descriptor-restricted symbol index,
  `_namespace_payload()`, and `_merge_sections()`. A retained explicitness path
  must address the exact exported or private identity that was merged. Root
  metadata must not be fabricated as paths such as `core.name`, because no
  corresponding field exists in the expanded model.
- **Phase-contract gate:** `FrozenPhaseModel(extra="forbid")`, qualified
  parameter closure, unique final model paths, portable source validation, and
  finite scalar constraints remain fail-closed. Producer bugs must not be
  hidden by relaxing Pydantic validation.
- **Instantiation and semantic gate:** final binding must continue through
  `instantiate_scenario()`, provenance merging, `InstantiatedScenario`
  admission, and `SemanticValidator`. The root-derived record and imported
  portable record for a surviving path must not coexist; the portable record
  replaces the reclassified imported path through the existing merge.
- **Compiler/runtime gate:** downstream SEM-218 consumers continue to look up
  one record by concrete model path. No source namespace, module id, import
  record, backend payload field, runtime provenance enum, or realization rule
  should be added for this parser defect.
- **Error-envelope and observability gate:** authored failures remain
  `SDLParseError`, `SDLValidationError`, or `SDLInstantiationError` at their
  existing phase. If closed provenance validation detects an internal
  composition inconsistency, the parser boundary must convert the underlying
  `ValidationError` to a bounded `SDLParseError` and retain exception chaining;
  it must not expose a raw Pydantic dump, source body, binding values, local
  paths, or traceback. CLI and MCP adapters keep their existing redacted
  envelopes. No logger, metric, warning, or advisory is needed for successful
  projection.
- **Secret, auth, config, and OS gate:** this change introduces no credential,
  environment binding, auth/authz surface, subprocess, process argument,
  network call, daemon, or host mutation. Do not include import contents,
  parameter values, registry credentials, or absolute host paths in new
  diagnostics or fixtures.
- **Persistence and schema gate:** expansion provenance remains the existing
  internal typed carrier and instantiation provenance remains the existing
  serialized carrier. No database, repository, cache, migration, sidecar
  ledger, public field, schema version, or publication-manifest change is
  warranted unless implementation changes the public record shape—which this
  issue does not require.

## Extension Seam And Gotchas

The extension seam is the existing composition-provenance path projection and
rewrite, driven by the composition section identity strategy and symbol map.
The next reasonable variation is another importable section shape. A hashmap
section should extend the canonical composition section catalog; a list-based
section needs an explicit stable-identity-to-final-position rewrite in the same
seam. It must not be admitted by broad string-prefix matching.

In particular, scenario-level `forwarding_agents` is imported and renamed by
stable `forwarding_agent_id`, but its explicitness paths are positional
(`forwarding_agents.<index>...`). The current hashmap-only projection excludes
those records. Issue #767 must not silently include them without correctly
rebasing positions after root and sibling merges. Adding complete imported
explicitness for list-based declarations is a separate bounded semantic change;
the present fix must neither corrupt those paths nor claim that it solved them.

Nested imports are another required guardrail. The retained path may already
contain an inner namespace. Prefix only the declaration identity resolved by
the outer symbol map, preserve the remaining suffix exactly, and qualify every
referenced parameter tuple once per import level. Reclassification, string
replacement of every matching segment, or source-path-derived namespaces will
misaddress nested declarations.

Avoid:

- treating `model_path`, import namespace, module id, source URI, and authored
  source location as interchangeable identities;
- namespacing source-only `name`, `version`, variables, import declarations,
  module descriptors, or section aggregate records;
- merging duplicate records by first/last writer, equality of classification,
  weakest/strongest class, or empty reason text;
- weakening uniqueness to `(source, model_path)` or
  `(namespace, model_path)` while downstream consumers remain keyed by path;
- filtering only the three paths observed in the private report instead of
  applying the surviving-expanded-field rule;
- rerunning explicitness classification in composition or the compiler;
- adding a generic provenance database, source-coordinate schema, compatibility
  wrapper logic under `implementations/python/src/aces/`, or a second import
  workflow; and
- editing accepted ADRs, published schemas, `CHANGELOG.md`, or the committed
  package version for this narrow repair.

## Non-Goals

- Changing SEM-218 classification, realization posture, parameter/default
  semantics, module export policy, import trust policy, or semantic validation.
- Preserving explicitness for source fields that do not exist in the expanded
  scenario, or making expansion provenance a complete source-lineage ledger.
- Redesigning list-section identity, including positional forwarding-agent
  provenance, as part of the reported aggregate-path collision fix.
- Changing public contracts, canonical digest profiles, compiler/runtime
  payloads, control-plane APIs, persistence, logging, CLI commands, or MCP
  operations.
