# Issue 722 Normative SDL Catalog Parity Preflight

Date: 2026-07-11

Issue: #722.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture guardrails for reconciling the normative SDL
catalogs with the live authoring contract. It does not edit the catalogs,
schemas, models, validators, examples, or release workflow. No new ADR is
needed: ADR-009, ADR-019, and the issue-498 preflight already fix the authority
direction and catalog boundary; this issue adds enforcement and repairs drift
within that boundary.

## Binding Authorities And Incumbents

- `specs/sdl/README.md`, `document-model.md`, `sections.md`, `references.md`,
  `runtime-inventory.md`, and `diagnostics.md` are the language-neutral
  normative SDL prose authority.
- `contracts/schemas/sdl/sdl-authoring-input-v1.json` is the published,
  hand-governed structural enumeration. `contracts/schema-publication-manifest.json`,
  `tools/check_schema_publication.py`, and ADR-061 govern any change to it.
- `Scenario.model_fields` and `schema_bundle()` are reference-implementation
  evidence. `tools/check_generated_schemas.py` already proves that generated
  output matches the published schema without rewriting that authority.
- `_mapping_scopes.HASHMAP_SECTIONS` owns parser treatment of authored map keys;
  `_module_symbols.HASHMAP_SECTIONS` owns the narrower module-composable symbol
  set. They have different jobs and must not be merged merely to make their
  counts equal.
- `SemanticValidator._named_ref_index()`, its targetable filtering,
  `aces_sdl.semantics.participant_behavior`, and
  `_language_metadata.REFERENCE_COMPLETION_TARGETS` are implementation evidence
  for reference validation and authoring-tool navigation. Completion metadata
  is not a semantic validator and is not a complete reference registry.
- `_runtime_service_families.RUNTIME_SERVICE_FAMILIES` is the existing
  node-runtime family registry. Its key, collection, primary id, and child-ref
  tree must be compared with `specs/sdl/runtime-inventory.md`; no second runtime
  family registry is warranted.
- Behavior-specific governed domains already exist in
  `controlled-vocabularies-v1`, the controlled-vocabulary validation helpers,
  and `aces_contracts.manifest_authority`. Do not replace those domains with a
  generic SDL-symbol lookup.

## Authority Direction And Parity Boundary

The release check must be a read-only, three-way compatibility proof:

1. parse top-level field names, requiredness, and shapes from the published
   authoring schema;
2. parse the normative rows from `specs/sdl/sections.md` and
   `specs/sdl/references.md`; and
3. inspect the reference implementation's model and existing registries as
   realization evidence.

All comparisons are bidirectional set comparisons. A schema/model field absent
from the catalog and a catalog field absent from the schema/model are both
failures. The check must never generate or overwrite normative prose or a
published schema, and implementation metadata must never be used to render the
normative tables. That preserves independent implementation authority while
making drift visible.

The dated preflight inspection for this issue yields 28 top-level fields: five
metadata or composition fields and 23 authoring sections, of which 22 are
map-keyed and one (`forwarding_agents`) is list-valued; it also finds 17
node-scoped runtime families. Those are issue evidence, not a new maintained
count source. Current-language values may appear durably only in a
checker-validated catalog summary or derived report. Explanatory prose, model
docstrings, schema descriptions, MCP text, and examples should otherwise use
count-free wording. The OCR stress fixture's "14 sections" may remain only
where it is explicitly a fixture-scope claim, not a claim about the live
language.

## Catalog Row Contract

Every top-level row must carry enough information to support an independent
implementation without opening Python:

- kind: metadata/composition or authoring section;
- document phase, using the vocabulary in `document-model.md` section 7 rather
  than processor/runtime phase names;
- value shape: scalar, fixed mapping, map keyed by authored identity, or list;
- requiredness and default/omission behavior;
- identity source: scenario name, mapping key, list element id, or none;
- outbound reference edges or an explicit `none`; and
- the normative semantic owner (SDL file, formal spec, and/or owning ADR).

The phase column must distinguish fields consumed by composition or
instantiation from fields that survive those phases. It must not call compiled
runtime output an SDL document phase. The identity column must distinguish map
keys from in-element ids, especially scenario-level `forwarding_agents`.

The checker should parse stable table headings and exact columns, following the
bounded Markdown-table pattern in `tools/check_semantic_coverage.py`. Missing
headings, malformed rows, duplicate fields, unknown shape/phase tokens, and a
blank coverage cell are policy failures, not parser tracebacks. Do not add a
parallel YAML catalog or a second full SDL schema to make Markdown easier to
check.

## Reference-Edge Semantics

Reference rows need exact canonical source paths, not broad prose such as
"authority refs." Each row must name its candidate domain, resolution phase,
failure behavior, and semantic owner. The catalog must distinguish at least:

- SDL symbol sets and the generic targetable set;
- aggregate-local symbols such as workflow steps and observation information;
- derived domains such as participant roles;
- governed controlled-vocabulary scopes;
- published contract-id registries;
- qualified runtime-family/child paths; and
- opaque external/profile refs that currently receive only shape validation.

An `_ref` suffix does not make those domains interchangeable. The catalog is a
coverage and meaning contract; it must not be used to generate semantic
validation or a new exception path.

For `behavior_specifications`, the live candidate and validation semantics to
record are:

| Field | Candidate domain and current validation |
|-------|-----------------------------------------|
| `participant_refs` | Keys in `agents`; unresolved variables defer to instantiation; dangling refs are fatal. |
| `participant_role_refs` | Role values of flattened entities actually bound by declared agents, not arbitrary agent keys or every enum value; dangling refs are fatal. |
| `action_contract_refs` | Keys in `action_contracts`; dangling refs are fatal. |
| `observation_boundary_refs` | Keys in `observation_boundaries`; dangling refs are fatal. |
| `outcome_interpretation_rule_refs` | Keys in `outcome_interpretation_rules`; dangling refs are fatal. |
| `authority_scope_refs` | The generic targetable alias index, with exact-one resolution and fatal dangling/ambiguity; it is not Agent `operating_scope` and not unrestricted `any`. |
| `behavior_mode` | Controlled-vocabulary scope `behavior_specifications.behavior_mode`; this is a governed term, not an SDL symbol ref. |
| `ai_offensive_behavior_refs` | Controlled-vocabulary scope `behavior_specifications.ai_offensive_behavior_refs`. |
| `offensive_behavior_refs` | Controlled-vocabulary scope `behavior_specifications.offensive_behavior_refs`. |
| `backend_feature_support_refs` | Union of `participant-runtime-behavior-features` and `participant-runtime-interaction-features`. |
| `evidence_contract_refs` | The published processor/backend/participant contract-id sets from `aces_contracts.manifest_authority`, not every schema-bundle id. |
| `realization_profile_ref` | Optional non-empty opaque profile reference today; the catalog must not claim local resolution that the implementation does not perform. |

Reference lists also retain the existing model-level non-empty and per-field
uniqueness checks. Every list-valued behavior reference above skips a whole
unresolved `${name}` value during authoring semantic validation and is checked
again after instantiation; scalar `behavior_mode` does not use that path, while
`realization_profile_ref` currently has no semantic resolver. Deferral must be
stated per field according to the actual validator, not asserted generically
for every governed value.

`REFERENCE_COMPLETION_TARGETS` remains completion/navigation metadata. Every
entry it exposes must have a normative reference row, but the reverse need not
hold because not every governed or opaque domain has editor completions. Its
current `("behavior_specifications", "authority_scope_refs"): "any"` entry is
broader than semantic validation and must be reconciled with the shared
targetable policy rather than documented as true. Do not copy the validator's
targetable exclusions into another unowned list.

Runtime-family parity is structural rather than numeric: compare every family
key, collection, primary id, and recursively addressable child collection
between `RUNTIME_SERVICE_FAMILIES` and the runtime-family index. A matching
count with a renamed or missing row is still a failure. Scenario-level
`forwarding_agents` remains a top-level list section; node-level
`nodes.<node>.runtime.forwarding_agents` remains a runtime family.

The extensibility seam is the checked row shape, parameterized by contract
target (published schema path, model class, and catalog table heading) and by
reference-domain token. Adding the next section, edge, or runtime family should
add authority/model/registry rows without adding a hard-coded count or a
field-specific branch to the checker. A future authoring-contract version can
reuse the same extractors with a second contract target; it must not silently
mix v1 and v2 rows.

## Release Gate And Failure Surface

Use one dedicated catalog-parity checker and wire it once into the canonical
nox verification graph. The natural home is the `contracts` leg beside schema
publication and generated-schema drift because the check compares published
contract structure with normative prose and its implementation. `verify`, the
pre-push hook, and CI then inherit it; do not duplicate the command in GitHub
Actions or release-please workflows. Relevant `specs/sdl/`, SDL model/registry,
schema, checker, and checker-test paths should trigger the contracts leg in the
optimized pre-commit graph.

The gate must scan the complete live catalogs on every invocation, not only
changed rows. It should reuse `tools.policy.common.PolicyFailure`, deterministic
sorting, JSON rendering, and the existing exception mechanism. Store source
line numbers while parsing so failures and the eventual #541 closure evidence
identify exact catalog rows. Catalog drift is a repository-policy failure; it
must not become `SDLParseError`, `SDLValidationError`, a runtime diagnostic, or
a new SDL exception hierarchy.

Focused checker tests should cover malformed and duplicate rows, missing and
extra top-level fields, wrong requiredness/shape/identity, map/list confusion,
reference rows with wrong candidate domains, missing runtime families or child
refs, checked-summary drift, and a passing live-repository integration case.
Existing semantic tests remain the evidence for actual reference behavior; the
policy test does not replace them.

## Cross-Cutting Security And Operational Layers

- **Authentication/control plane:** none is in scope. The checker performs no
  network access, API calls, authorization decisions, or control-plane
  mutation. `ControlPlaneSecurityConfig` and HTTP handlers must not be pulled
  into this repository-policy concern.
- **File and config shape:** read only fixed repo-relative catalog/schema paths
  and canonical package registries. Parse JSON and Markdown as inert data. If a
  future CLI makes paths configurable, pass them through
  `tools.policy.common.safe_repo_path`; never follow catalog links or imports.
- **Schema/model validation:** retain `SDLModel(extra="forbid")`, source-profile
  checks, `SemanticValidator`, controlled-vocabulary validation, and
  `tools/check_generated_schemas.py`. The parity gate observes these surfaces;
  it does not bypass or duplicate them.
- **Secret handling:** do not inspect scenario values, environment dumps,
  credentials, or arbitrary files. Failure messages may name repo paths,
  catalog line numbers, field paths, and expected/actual identifiers, but must
  not print file bodies, schema payloads, environment values, tracebacks, or
  secrets. Existing hygiene, private-key, and gitleaks stages remain the
  repository secret gates.
- **Environment and OS exposure:** add no environment binding and no external
  command that carries data in process argv. Nox should invoke the checker with
  a static script path through the frozen project environment. The checker
  writes no files and needs no temporary or persistent state.
- **Errors and observability:** malformed inputs become bounded
  `PolicyFailure` records and a non-zero exit. Nox `SessionReporter` is the
  canonical stage log; no new logger, telemetry sink, HTTP error envelope, or
  raw exception traceback is needed.
- **Persistence:** none. Do not rewrite catalogs, generated schemas, the schema
  manifest, caches, or reports as a side effect of checking parity.

## Stale-Surface Audit Guardrails

The reconciliation must cover all reader-facing completeness claims, not only
the two normative tables. Current audit targets include:

- `specs/sdl/README.md` acceptance questions and the stale reconciliation note
  in `document-model.md`;
- the current/future contradiction in `observability-and-evidence.md` and the
  evidence-syntax limitation in `docs/explain/sdl/limitations.md`;
- the incomplete overview and non-canonical `behavior-specifications` spelling
  in `docs/explain/sdl/sections.md`;
- numeric completeness claims in `docs/explain/sdl/index.md`,
  `docs/explain/sdl/complex-scenarios.md`, and
  `docs/explain/reference/glossary.md`;
- static counts, accepted section names, and example claims in
  `aces_mcp.tools.reference`; and
- examples/tests that claim complete-language coverage while exercising only a
  historical subset.

Model and published-schema descriptions are count-free in the current tree;
preserve that property. A documentation count and a validation-pass count are
different concepts and must not be made equal. Likewise, an example can claim
coverage of named constructs it actually asserts, but not "all sections"
without a checked comparison to the catalog.

## Gotchas And Anti-Patterns

Avoid:

- generating normative prose from `Scenario`, or generating implementation
  registries from normative Markdown;
- adding a YAML/JSON meta-schema that duplicates the existing catalog and
  published SDL schema;
- treating `REFERENCE_COMPLETION_TARGETS` as validation authority or using
  `"any"` where the validator uses targetable, role-derived, or governed sets;
- inferring semantics solely from `_ref`/`_refs` naming;
- collapsing controlled-vocabulary refs, contract ids, evidence refs, profile
  refs, SDL symbols, and runtime-family refs into one resolver;
- broadening or narrowing live validation merely to make prose match; any true
  semantic change needs its own authority and tests;
- equating map-keyed authoring sections with module-exportable symbols;
- counting `imports` as the one list-valued authoring section, or counting the
  two forwarding-agent placements as one surface;
- describing `evidence_requirements` as future syntax or as captured evidence;
- adding a second policy command directly to CI/release workflows; or
- hand-editing schema descriptions without the publication-manifest ledger and
  generated-bundle parity required by ADR-061 and repo policy.

## Non-Goals And Implementation Boundary

- No SDL syntax, model field, schema structure, reference candidate set,
  validation severity, compiler output, or runtime behavior changes are
  authorized by this issue.
- No validator consolidation, general SDL metamodel, documentation generator,
  new runtime-family registry, exception hierarchy, API, database, or
  persistence layer is in scope.
- Do not rewrite accepted historical ADR bodies; current catalogs and
  explanatory docs carry the reconciliation.
- Do not close or comment on #541 from this work. The implementation should
  produce line-addressable repository evidence that a separately authorized
  workflow can cite.
- Do not add changelog fragments or edit package versions; release-please owns
  those surfaces.
