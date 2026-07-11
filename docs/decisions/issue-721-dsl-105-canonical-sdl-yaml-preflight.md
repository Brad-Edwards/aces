# Issue 721 DSL-105 Canonical SDL YAML Preflight

Date: 2026-07-11

Issue: #721.

Requirement: DSL-105, Typed Parsing, Normalization, And Authoritative SDL
Format.

This note records architecture preflight guardrails for defining one canonical
SDL YAML source format. It is guidance for the implementation. It does not
change parser behavior, schemas, examples, diagnostics, or digest semantics.

## Binding Sources

- `specs/sdl/` is the language-neutral normative SDL authority. Its
  `document-model.md` and `diagnostics.md` already own encoding, mapping
  identity, normalization scope, document phases, and fail-closed diagnostics.
- ADR-001 owns the SDL/parser decision. Its case-insensitive and hyphenated key
  handling may remain as explicitly selected migration behavior; it must not
  remain an undocumented second canonical dialect.
- ADR-009, ADR-019, and `specs/authority/authority-boundary.yaml` make
  `contracts/schemas/` and `contracts/fixtures/` normative while Python is a
  non-normative reference implementation.
- ADR-053 owns module parsing, trust, lock, digest, signature, and composition
  behavior. Canonical source handling must enter that pipeline rather than
  bypass it.
- ADR-061 and `contracts/schema-publication-manifest.json` own published-schema
  evolution and change records. The current SDL schemas are `draft`; correcting
  their phase description is allowed in place but still requires the existing
  ledger and reference-bundle parity gates.
- ADR-075 and `specs/evolution/versioning-deprecation-and-migration.md` separate
  compatibility, deprecation, and migration. A migration spelling is not a
  second stable format and must never be silently reinterpreted as canonical.

## Architecture Decisions

### One source profile

The authoritative source profile is `sdl-yaml/v1` with these rules:

- Input is UTF-8, contains exactly one YAML 1.2.2 document, and uses the YAML
  1.2 Core schema for implicit scalar resolution. YAML 1.1 coercion is not part
  of SDL: plain `yes`, `no`, `on`, and `off` are strings, while booleans are
  `true` or `false` under the Core rules.
- The constructed value domain is I-JSON/JCS-compatible: mappings, sequences,
  Unicode strings without lone surrogates, null, booleans, integers that are
  in the interoperable range `[-9007199254740991, 9007199254740991]`, and finite
  IEEE-754 binary64 numbers. The Core schema does not implicitly construct
  timestamps; date-like plain scalars are strings. Native timestamp, binary,
  set, ordered-map, pair, arbitrary-object, non-finite-number, and other
  implementation-specific values are invalid. A future need for wider integers
  or decimals requires a typed string representation and a new canonicalization
  profile, not silent implementation-dependent rounding.
- Explicit tags and tag directives are not SDL authoring syntax. Quoting is the
  portable way to force a string. A safe loader remains mandatory, but
  "SafeLoader accepted it" is not a validity rule.
- Every mapping key is a string scalar. Exact duplicates and normalized
  structural-key collisions are rejected on the source-marked node graph before
  a last-write-wins dictionary or model can be built.
- Acyclic anchors and aliases are representation-only conveniences. They add no
  identity, reference, import, or precedence semantics. Cycles and operational
  alias/node/depth budget exhaustion fail cleanly without partial construction.
- `<<` merge keys are not canonical `sdl-yaml/v1`. An explicit migration read
  may retain the current disjoint-union behavior, but it must diagnose the merge
  as non-canonical; any source/local or source/source conflict remains fatal.
- Comments, scalar style, anchor names, line endings, and mapping order do not
  change SDL meaning. Sequence order and string code points do. No Unicode
  normalization is applied to authored string data or literal map keys.

These rules belong in the normative document model and conformance fixtures,
not in PyYAML behavior notes. A conforming implementation must be able to
implement them without reading Python.

The source profile applies to authored text before convenience transforms.
`_prepare_content()` currently dedents every input and `load_scenario()` strips
it; neither operation may precede canonical source validation because it can
change source ranges, make invalid indentation valid, or change block-scalar
content. Test callers may dedent their own literals. Likewise, no corpus,
formatter, or adapter may `safe_load()` and re-dump SDL before the source profile
sees it: that destroys duplicate keys, tags, aliases, authored spellings, scalar
tags, and source locations.

### Canonical fields, migration spellings, and shorthands

- The canonical spelling of a structural field is its exact published-schema
  property name. Multiword SDL fields use lowercase `snake_case`. Intentional
  single-word wire names such as `class`, `type`, `next`, `then`, `else`, and
  `default` remain exact even when Python needs a differently named attribute.
- Existing kebab-case, mixed-case, and uppercase structural keys are migration
  spellings only. Migration matching is ASCII case-folding plus `-` to `_`, and
  only succeeds when the result is an actual canonical field in that structural
  scope. There is no fuzzy matching or typo correction.
- Canonical validation is strict by default. Migration acceptance is explicit,
  returns the same typed model, and emits a stable non-fatal diagnostic carrying
  the authored spelling, canonical spelling, JSON Pointer, and source range.
  Strict mode reports the same condition as a fatal source diagnostic. Neither
  mode may silently overwrite a canonical field or accept incompatible
  metadata/mode-based scenario dialects.
- Literal/user-defined mapping keys remain byte-for-byte authored strings. Node
  names, section identifiers, `facts`, `labels`, `log_options`, native options,
  and extension keys are not structural-field aliases. `Web-App` and `web_app`
  may therefore remain distinct identifiers where the existing mapping-scope
  catalog says the map is literal.
- The existing documented shorthands remain SDL authoring syntax, not another
  dialect. They expand once in the shared parser before typed construction.
  Canonical serialization is always longhand. Stale `min-score` guidance must
  not reintroduce the scoring surface removed by ADR-073.
- Enum values continue to use the existing case/hyphen normalization in
  `normalize_enum_value()` and `parse_enum_or_var()`; their canonical serialized
  values are the declared lowercase values. Field-key normalization and enum
  normalization remain separate concepts.

Canonical scalar and collection types are the YAML 1.2 Core-resolved types that
the normalized schema declares. A whole-string `${name}` placeholder is the
documented exception for a variable-capable typed field. Generic Pydantic
coercion is not SDL syntax: quoted integers, `yes`/`no`/`on`/`off` or `0`/`1` as
boolean spellings, arbitrary strings in a placeholder branch, and scalar-to-list
coercion are canonical only if the normative source contract explicitly names
that exact shorthand. Existing convenience coercions retained for compatibility
are migration syntax and receive the same source diagnostics as field aliases.
The published normalized schema should constrain placeholder-only string
branches to the variable-token grammar instead of advertising every string as a
valid normalized value.

### Raw syntax, normalized model, and schemas are distinct phases

The implementation must keep these boundaries explicit:

1. raw `sdl-yaml/v1` source representation;
2. normalized authoring object after key canonicalization, declared scalar and
   collection normalization, shorthand expansion, enum normalization, and typed
   structural construction;
3. expanded authoring scenario after module composition;
4. instantiated scenario after variable binding;
5. compiled/runtime artifacts.

`sdl-authoring-input-v1.json` is the normalized authoring-object schema. Its
title and description must say that it applies after YAML source-profile checks
and normalization, but before module expansion and instantiation. It is not a
validator for YAML token spelling, duplicate keys, tags, anchors, aliases, or
migration diagnostics. `instantiated-scenario-v1.json` remains the concrete
post-instantiation schema.

Do not publish a second full Scenario schema merely to label raw YAML. The raw
contract is the normative source-profile prose plus valid, invalid, and
migration fixtures under the existing SDL fixture family. Canonical reusable
examples use canonical keys, canonical enum spellings, and expanded longhand so
their directly decoded object validates against the artifact advertised for
authoring. "Directly decoded" means decoded once with the shared `sdl-yaml/v1`
resolver and source checks, not PyYAML defaults. A parse-then-`model_dump()`
schema test remains useful normalized-model evidence, but it must not be
presented as proof that the raw example matched the source contract.

`schema_bundle()`, `tools/generate_contract_schemas.py`, and
`tools/check_generated_schemas.py` remain the reference-compatibility proof.
Schema changes remain hand-governed through the existing publication manifest;
there is no second SDL schema registry, source-of-truth model, or change ledger.

### Canonical semantic serialization and digest

Canonical identity is defined over a successfully parsed, expanded, and
semantically validated authoring scenario immediately before instantiation. It
is not defined over raw YAML bytes and is unavailable for parse-only or
semantically invalid input.

The canonical payload is a versioned semantic projection, not a blind
`model_dump()` and not a claim that the bytes are round-trippable authoring YAML.
Its scenario member uses public JSON-mode values and canonical wire property
names in normalized longhand. It preserves authored field presence after
normalization: omitted defaults must not be materialized indiscriminately,
because `model_fields_set` feeds the normative SEM-218 explicitness classifier
and can change compiler/planner behavior. Shorthand-expanded fields count as
present in the normalized meaning.

The projection must also include a stable representation of every otherwise-
private channel that can change instantiation, compilation, or planning, or
prove that the channel is derivable from the scenario member. Today that
includes `module_variable_specs` and `module_node_variable_refs`; excluding them
would make scenarios with different imported-module constraints share an
identity. Derived explicitness may be omitted only when preserved field presence
and values deterministically reconstruct it. Semantic advisories, source ranges,
filesystem paths, trust/cache evidence, and explanatory provenance text are
non-semantic and excluded. The profile specification must enumerate the
projection; Python private-attribute names are not the contract.

Object members, including preserved literal keys, are serialized using the
[RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html);
arrays retain their semantic order and strings are not Unicode-normalized. Input
is already constrained to JCS's I-JSON number and Unicode domain, so
canonicalization must never round or repair a value. The canonical bytes are
UTF-8. The digest is SHA-256 over those bytes and is represented with the
repository's existing lowercase `sha256:<hex>` convention. A digest record must
identify the canonicalization profile (`aces-sdl-semantic/v1`); a bare hash must
not imply an unversioned algorithm.

This semantic digest is deliberately separate from:

- an authored file's raw byte digest;
- OCI layer, config, and manifest digests;
- module lockfile `content_digest`, `manifest_digest`, and `export_hash`; and
- signatures over the existing module signer payload.

Those existing values protect source/package integrity and supply-chain
identity. They must not be silently redefined to ignore comments, aliases,
spelling, or file layout. Conversely, a semantic digest is not a signature, a
trust decision, a secret-redaction mechanism, or proof that a scenario ran.

## Required Incumbents

- Authority and publication: `specs/sdl/document-model.md`,
  `specs/sdl/diagnostics.md`, `contracts/schemas/sdl/`,
  `contracts/fixtures/sdl/`, `contracts/schema-publication-manifest.json`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`, and
  `specs/authority/authority-boundary.yaml`.
- Source loading and mapping identity: `aces_sdl._yaml_loader`,
  `aces_sdl._mapping_scopes.MappingScope`, `HASHMAP_SECTIONS`,
  `NESTED_HASHMAP_FIELDS`, `is_literal_map_field()`, and the existing
  source-ranged mapping analyzer.
- Normalization and typing: `parser._load_normalized_data()`,
  `_normalize_keys()`, `_expand_shorthands()`, `aces_sdl._base` enum/scalar
  helpers (including the existing integer/float/boolean coercion audit surface),
  `SDLModel(extra="forbid")`, `Scenario`, `aces_sdl.explicitness`, and
  `SemanticValidator`.
- Composition and trust: `parse_sdl_file()`, `expand_sdl_modules()`,
  `ImportDecl`, `ModuleDescriptor`, `resolve_import()`, `TrustPolicy`, lockfile
  validation, digest/version/export checks, signature verification, path
  confinement, cycle rejection, and bounded OCI extraction.
- Public ingress surfaces: `parse_sdl()`, `parse_sdl_file()`,
  `load_sdl_fragment()`, `load_scenario()`, the reference processor,
  language-service format/edit/diagnostic helpers, MCP authoring and operation
  tools, the static MCP reference/example text, example-library checks, and SDL
  CLI verify/publish commands. Imported documents and fragments must use the
  same source policy as roots.
- Diagnostics and presentation: `SDLError`, `SDLParseError`,
  `SDLParseDiagnostic`, `SDLValidationError`, `ScenarioValidationError` as the
  existing high-level wrapper, `_language_diagnostics`, and MCP
  `operation_support.stage_error()`. Add codes or advisory severity to this
  envelope; do not add another exception or response hierarchy.
- Verification: `test_sdl_parser.py`, `test_yaml_mapping_keys.py`,
  `test_sdl_fuzz.py`, `test_language_service.py`, `test_mcp_server.py`,
  `test_example_schema_conformance.py`, `test_pipeline_determinism.py`, and the
  canonical nox `contracts`, `tests`, `fuzz`, `docs`, and `verify` sessions.
  Extend the existing example-corpus leg to check original source before
  parse-and-dump validation; do not create a second corpus registry.

## Cross-Cutting Security And Runtime Layers

- **YAML safety gate:** `_SDLSafeLoader` remains the only SDL composer. Its
  resolver must implement the source profile without mutating PyYAML's global
  resolver tables. It rejects unsafe/non-profile tags, duplicate keys, alias
  cycles, merge ambiguity, excessive source/scalar size and depth/node/alias
  work, non-I-JSON numbers/strings, and other non-profile values before recursive
  normalization or model construction. Count alias edges/work, not only unique
  composed nodes, because normalization can otherwise amplify a small graph.
- **Shape gates:** the mapping analyzer runs before dictionary construction;
  canonical scalar/collection shape is checked before Pydantic; then
  `SDLModel(extra="forbid")` rejects unknown structure. Existing field validators
  retain range, identifier, redaction, argv, environment-name, and domain-specific
  shape checks; `SemanticValidator` retains reference and graph closure.
  Canonicalization must bypass none of them, and `parse_float_or_var()` must not
  admit `NaN` or infinity through a quoted string.
- **Module and filesystem gates:** local imports remain base-confined; OCI and
  locked imports retain trust policy, allowed registry, version, digest,
  lockfile, export-hash, signature, extraction, namespace, and cycle checks.
  Canonicalization consumes the already validated/expanded model and must not
  create an alternate file reader or untrusted network-fetch path.
- **Secret handling:** `enforce_observed_value_redaction()` and the existing
  `redacted`/`operator_secret` omission validators still apply after
  normalization. SDL may legitimately contain scenario credentials under
  ADR-057, so canonical bytes and digests must not be logged, persisted, or
  returned as if they were sanitized. Hashing a low-entropy secret is not
  redaction.
- **MCP/input limits:** the existing 64 KiB language-service, authoring,
  inspection, and operation-tool guards remain adapter limits. The shared YAML
  loader also needs one cohesive, explicitly threaded operational-limits policy
  for raw size, scalar size, depth, nodes, and alias work so direct library/file
  callers are not an unbounded YAML-bomb path. Adapter limits may be stricter.
  Limit refusal is an operational diagnostic, not a claim that another
  implementation must consider the SDL semantically invalid; do not scatter new
  constants or ambient environment switches through adapters.
- **Auth and transport:** the current MCP surface is the existing FastMCP
  transport and introduces no new HTTP/control-plane endpoint or authorization
  model. This work must not add a bypass around a host's transport auth or put
  source text, credentials, or private keys into process arguments.
- **Configuration and OS exposure:** source-format/migration selection is an
  explicit API/CLI input, not an ambient environment variable. CLI entrypoints
  continue to accept validated file paths and private-key paths, not key values;
  no shell command construction, environment dump, or new bind/listen surface is
  required.
- **Error envelope:** canonical and migration diagnostics reuse
  `SDLParseDiagnostic` and carry codes, stage, severity, canonical pointer,
  bounded source locations, and a logical source identity when imports are
  involved. Messages may quote field-key spellings but not mapping values, full
  YAML, canonical payloads, parameter maps, environment values, secrets,
  tracebacks, or unrestricted absolute paths. Language-service and MCP adapters
  preserve the same structured record. A migrated model may be semantically
  valid while its original source remains non-conforming; do not fold source
  migration notices into `SemanticValidator.warnings` or report the raw document
  as canonical.
- **Logging and persistence:** `aces_sdl.scenarios` remains the existing
  advisory/load logging boundary and must log only bounded code/path/spelling
  metadata for migration notices. No new logger, audit stream, database, cache,
  lockfile field, or automatic digest persistence belongs in this change.

## Extension Boundary

The extension seam belongs at source ingress, not in Pydantic models,
validators, processors, or backends. A named `source_format` value pins
`sdl-yaml/v1`; an orthogonal explicit migration policy decides whether legacy
spellings/merges are rejected or canonicalized with diagnostics. Thread those
values through the existing `_load_normalized_data()` path used by strings,
files, fragments, imports, formatters, and MCP tools. Do not add scattered
`case_insensitive`, `allow_hyphens`, `allow_merge`, or `yaml_11` booleans.
Operational parser limits are a separate cohesive input to that same ingress;
they do not select language meaning and must not leak into Pydantic models.

A future source-format revision gets a new format identifier and a deliberate
compatibility relation under ADR-075. A future canonicalization algorithm gets
a new `aces-sdl-semantic/vN` identifier. Neither variation requires a second
Scenario model, validator stack, schema registry, or runtime endpoint.

## Gotchas And Anti-Patterns

Avoid:

- relying on PyYAML defaults, Pydantic coercion, or Python's `bool`-is-`int`
  behavior to define portable scalar validity;
- dedenting, stripping, `safe_load()`-round-tripping, or otherwise rewriting the
  text before source-profile and source-range validation;
- treating `Scenario.model_json_schema()` as a raw YAML grammar or treating a
  parse-then-dump example test as raw-source schema validation;
- keeping the six current kebab-case workflow serialization aliases
  (`on-success`, `on-failure`, `on-exhausted`, `max-attempts`,
  `min-attempts`, `compensate-with`) while declaring snake_case canonical;
- normalizing user identifiers, native option keys, labels, facts, extension
  keys, or JSON Pointer tokens as structural fields;
- accepting a canonical root while parsing imported modules or fragments with a
  more permissive implicit mode;
- auto-detecting dialects from top-level keys or silently treating an unknown
  field as a migration alias;
- publishing migration spellings through Pydantic `Field(alias=...)`; validation
  aliases, canonical serialization names, and Python-safe attribute names are
  different concerns;
- preserving YAML merge precedence, resolving cycles, or expanding aliases
  without resource budgets;
- using `yaml.safe_dump()` output as cross-language identity bytes; it remains a
  human formatter, not the canonical digest serialization;
- reusing phase-specific helpers merely because they say "canonical": the
  compiled-runtime witness in `test_pipeline_determinism.py`, schema-publication
  hashing, and run-artifact JSON formatting do not implement
  `aces-sdl-semantic/v1`;
- omitting defaults or private/public fields inconsistently between repeated
  canonicalization passes, materializing omitted defaults that carry authored
  explicitness, dropping module side channels that affect downstream behavior,
  or sorting arrays whose order is semantic;
- feeding arbitrary-precision integers, lone surrogates, `NaN`, or infinity to
  JCS and relying on a library to round, replace, or reject them differently;
- producing an authoritative semantic digest from
  `skip_semantic_validation=True`, a directly constructed `Scenario`, or a
  partially expanded import graph;
- replacing raw module/OCI digests or signature payloads with the semantic
  digest, or presenting a digest as authenticity, execution evidence, or
  redaction;
- duplicating `parse_sdl()` and `parse_sdl_file()` policy branches. The file
  entrypoint already can delegate to the string parser with a path; source-mode
  and diagnostic logic must have one implementation;
- adding another full SDL schema, canonical field table, shorthand engine,
  exception hierarchy, diagnostic DTO, size-limit constant, migration service,
  or schema/change manifest;
- rewriting accepted ADR bodies. Any needed ADR-001 clarification follows the
  ADR-059 amendment/pin process while current normative behavior lives in
  `specs/sdl/`.

## Non-Goals

- Implementing the parser, schema, example, fixture, formatter, diagnostic, or
  digest changes in this note.
- Adding or changing SDL domain fields, semantic reference rules, variable
  semantics, module resolution, compiler/runtime contracts, or backend behavior.
- Accepting metadata/mode-based scenarios, YAML 1.1, arbitrary tags, merge
  precedence, JSON5, TOML, or another scenario dialect.
- Building a general-purpose YAML validator, migration service, source registry,
  persistence layer, control-plane API, auth system, network service, or audit
  pipeline.
- Defining canonical identity for instantiated scenarios, compiled plans,
  runtime snapshots, evidence artifacts, or OCI packages. Those phases retain
  their existing authorities and require separate versioned decisions if they
  later need semantic digests.
- Treating formatting as source preservation. Comments, anchors, scalar style,
  and original field spelling are intentionally not recoverable from the
  normalized semantic projection.
