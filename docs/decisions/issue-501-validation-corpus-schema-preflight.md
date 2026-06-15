# Issue 501 Validation Corpus Schema Preflight

Date: 2026-06-15

Issue: #501.

Requirement: ASR-504.

This note records architecture preflight guardrails for validating shipped SDL
examples against the published JSON Schema surface. It is guidance for the
implementation and does not implement tests, change examples, edit schemas, or
alter parser behavior.

## Binding Sources

- ADR-009 makes `contracts/schemas/` the normative machine-readable schema
  authority. Python models and `schema_bundle()` are compatibility evidence.
- ADR-061 and `contracts/schema-publication-manifest.json` govern published
  schema inventory and evolution. This issue should not need a schema edit.
- ADR-014 and `.ground-control.yaml` keep `nox -s verify` as the canonical
  verification graph.
- `docs/explain/sdl/testing.md` defines `examples/scenarios/*.sdl.yaml` as the
  reusable positive example corpus.
- `implementations/python/tests/paths.py` is the existing marker-based
  repo-root and example-corpus path seam.
- `load_scenario()` / `parse_sdl()` are the SDL parsing and semantic-validation
  boundary for example files.

## Architecture Decisions

- Keep worked examples under repo-root `examples/scenarios/`. They are positive,
  reusable SDL authoring examples, not invalid fixtures and not normative
  contract fixtures.
- Validate examples through the existing loading boundary first, then validate
  the serialized model payload against the published schema file
  `contracts/schemas/sdl/sdl-authoring-input-v1.json`.
- Treat Pydantic acceptance and published-schema conformance as two separate
  claims. The new evidence must prove both; it must not replace parser,
  semantic-validator, or schema-publication tests.
- Load the published schema artifact, not a freshly generated schema, when
  proving example conformance. `schema_bundle()` remains the drift/compatibility
  proof used by existing contract gates.
- Keep the serialization choice explicit and centralized in test support:
  `model_dump(mode="json", by_alias=True)` is the contract-shaped payload. Any
  exclusions must be documented at that seam, not repeated at each assertion.
- Add a non-vacuity guard around example enumeration. A stale corpus root must
  fail loudly rather than collecting zero parametrized cases.
- If instantiated-scenario examples are added later, cover them through the same
  contract-id/serialization seam with `instantiated-scenario-v1`; do not
  conflate authoring examples with concrete instantiated artifacts.

## Required Incumbents

- Corpus discovery: `implementations/python/tests/paths.py` and
  `EXAMPLES_DIR`.
- Scenario loading: `aces_sdl.scenarios.load_scenario`,
  `aces_sdl.parser.parse_sdl`, `yaml.safe_load`, `SDLModel.extra="forbid"`,
  `SemanticValidator`, and the existing SDL error types.
- Schema authority and publication: `contracts/schemas/sdl/`,
  `contracts/schema-publication-manifest.json`, ADR-009, ADR-061,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`, and
  `tools/check_json_artifacts.py`.
- Schema validation idiom: `jsonschema.Draft202012Validator`, already used by
  contract and SDL schema tests.
- Contract-corpus resolution, when a schema path helper is needed:
  `aces_contracts.corpus.corpus_family_root("schemas")` rather than new
  `Path(__file__).parents[N]` heuristics.
- Existing tests to extend or mirror: `test_scenarios.py`,
  `test_instantiated_scenario_schema.py`, `test_runtime_contracts.py`, and
  `test_mcp_server.py`.

## Cross-Cutting Layers

- YAML/config parsing: examples must pass through `yaml.safe_load`, key
  normalization, shorthand expansion, top-level string-key checks, mapping-key
  variable rejection, and Pydantic closed-world validation.
- Semantic validation: unresolved references, ambiguity, dependency failures,
  and runtime-family reference errors must continue to fail closed through
  `SemanticValidator`. Advisories remain non-fatal but visible.
- Published schema validation: the JSON Schema validator checks the serialized
  authoring payload against the checked-in schema. It must not fetch remote
  refs, generate schemas in place, or mutate the manifest.
- Repo-path security: corpus and schema paths stay repo-relative or flow through
  existing marker/corpus seams. Do not add absolute-path, `..`, symlink, or
  environment-variable based discovery.
- Secret handling and OS exposure: tests should run in process and pass file
  paths only. Do not place scenario contents, tokens, operator secrets, or
  payload JSON in subprocess argv or logs.
- Error envelopes and leakage: keep existing `SDLParseError`,
  `SDLValidationError`, `ScenarioValidationError`, and pytest assertion
  surfaces. Failures should identify the example path and schema error, not dump
  whole scenario payloads or environment state.
- Auth, persistence, network, and control-plane layers: this work does not add
  or change runtime auth, HTTP handlers, database state, audit logging, or live
  network access.

## Extension Boundary

The extension seam is a small table of validation-corpus entries:
example root, filename glob, model loader, contract id, schema path, and
serialization options. Today that table has the authoring corpus
`examples/scenarios/*.sdl.yaml` against `sdl-authoring-input-v1`. A future
instantiated corpus should add a row for `instantiated-scenario-v1`; it should
not require a new schema loader, new path convention, or new validator wrapper.

## Gotchas And Anti-Patterns

Avoid:

- validating zero examples because `EXAMPLES_DIR` points at the old
  `implementations/python/examples` location;
- using `schema_bundle()["sdl-authoring-input-v1"]` as the primary proof of
  published-schema conformance;
- adding duplicate schema files, schema registries, validation helpers, or
  exception hierarchies;
- placing invalid controls under `examples/scenarios/`;
- proving only Pydantic acceptance and calling it published-contract
  conformance;
- serializing with field names instead of aliases, which misses YAML-facing
  fields such as `on-success`, `max-attempts`, and `class`;
- hiding all defaults/exclusions inline until the test no longer resembles the
  published contract payload;
- editing `implementations/python/src/aces/`, generated schema outputs, or
  accepted ADR text for this issue.

## Non-Goals

- Changing SDL semantics, parser normalization, instantiation behavior, or MCP
  example content.
- Editing published schemas or the schema publication manifest.
- Adding new corpus roots, package-data behavior, release workflow, control
  plane endpoints, persistence, or authentication behavior.
- Turning examples into conformance fixtures or making invalid examples part of
  the reusable example corpus.
