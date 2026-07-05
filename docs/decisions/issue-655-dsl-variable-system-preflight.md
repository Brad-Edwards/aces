# Issue 655 DSL Variable System Preflight

Date: 2026-07-05

Issue: #655.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for SDL variable
declaration, substitution, and static validation semantics. It is guidance for
the implementation and does not implement the variable contract, edit schemas,
or change reference behavior.

## Binding Sources

- `specs/sdl/` is the normative SDL prose authority. In particular,
  `variables-and-instantiation.md`, `document-model.md`, `references.md`, and
  `diagnostics.md` already define the authored/instantiated distinction,
  placeholder grammar, key restrictions, reference deferral, and fail-closed
  diagnostic stages.
- `contracts/schemas/sdl/` is the machine-readable normative companion under
  ADR-009 and ADR-061. Any schema edit must stay synchronized with
  `contracts/schema-publication-manifest.json` and the generated-bundle
  compatibility proof.
- `aces_sdl` owns parsing, variable models, instantiation, and SDL semantic
  validation per ADR-036. Processor, runtime, CLI, MCP, and backend packages
  consume those APIs; they must not define parallel SDL variable semantics.
- Module composition is governed by ADR-053: imports are typed SDL modules,
  instantiated before merge when parameters are supplied, namespace-rewritten,
  and then validated as one canonical scenario.

## Architecture Guardrails

- Keep one variable concept: a top-level `variables` declaration and `${name}`
  placeholders in values. Do not introduce a second template language, expression
  evaluator, environment-variable binding model, or backend-specific parameter
  schema.
- Preserve the identity/value boundary. User-defined mapping keys create the
  SDL symbol table and must remain concrete; placeholders are value
  substitutions only. This includes embedded tokens such as `host-${index}`, not
  only whole-string `${index}` keys.
- Treat full-value placeholders and embedded tokens as the same declared-token
  grammar with different replacement behavior. The reference implementation
  should reuse the existing token helpers in `aces_sdl._base` rather than adding
  new regexes or per-field scanners.
- Static validation must check every placeholder token against declared
  variables before execution. Reference-oriented validation should continue to
  defer concrete reference resolution for placeholder-backed values until after
  instantiation, then rerun semantic validation on the concrete scenario.
- Keep `scenario-instantiation-request-v1.parameters` open. The request schema
  cannot know a scenario's declared variables; undeclared parameters, required
  variables, type mismatches, and `allowed_values` violations belong to
  `instantiate_scenario()`, not a duplicated request-schema validator.
- An instantiated scenario is concrete. It must not carry unresolved `${...}`
  tokens and must not treat `variables` definitions as live authoring variables.
  Any retained instantiation context or module-variable provenance is metadata
  for downstream consumers, not a second authoring surface.
- Keep imported-module variable provenance narrow. Existing side channels
  (`module_variable_specs`, `module_node_variable_refs`, `node_variable_refs`)
  support planner capability checks for known finite-domain fields such as
  `nodes.os` and `infrastructure.count`; do not generalize this into backend
  forecasting for every substituted field without a new contract decision.
- Use the existing diagnostic boundary: parse/structural errors,
  `SDLValidationError` for semantic validation, `SDLInstantiationError` for
  binding/substitution/concrete revalidation, and advisories only for
  non-fatal quality/deployability observations.

## Required Incumbents

- Authority and publication: ADR-009, ADR-061,
  `specs/authority/authority-boundary.yaml`,
  `contracts/schema-publication-manifest.json`,
  `tools/check_schema_publication.py`,
  `tools/check_generated_schemas.py`, and `.gc/plan-rules.md`.
- SDL grammar and phases: `specs/sdl/README.md`,
  `specs/sdl/document-model.md`, `specs/sdl/references.md`,
  `specs/sdl/variables-and-instantiation.md`, and
  `specs/sdl/diagnostics.md`.
- Reference implementation: `aces_sdl.variables.Variable`,
  `VariableType`, `aces_sdl._base.VARIABLE_TOKEN_RE`,
  `VARIABLE_TOKEN_PATTERN`, `is_variable_ref`, `contains_variable_token`,
  `extract_variable_name`, `parser._reject_variable_mapping_keys`,
  `SemanticValidator._verify_variables`, and `instantiate_scenario`.
- Published contracts: `sdl-authoring-input-v1.json`,
  `instantiated-scenario-v1.json`, and
  `scenario-instantiation-request-v1.json`.
- Composition and downstream use: `aces_sdl.composition`,
  `aces_sdl._module_provenance`, `aces_processor.compiler`, and
  `aces_processor.planner`.
- Test patterns to extend: `test_sdl_parser.py`,
  `test_sdl_validator.py`, `test_sdl_models.py`,
  `test_instantiated_scenario_schema.py`,
  `test_runtime_planner.py`, and schema fixture tests under
  `contracts/fixtures/sdl/`.

## Cross-Cutting Layers

- YAML/config parsing: `yaml.safe_load`, top-level mapping checks, field-key
  normalization, preserved user-defined keys, shorthand expansion, and
  `SDLModel(extra="forbid")` structural closure.
- Published-schema validation: closed object shapes in `contracts/schemas/sdl`,
  instantiated-schema token-forbid constraints, schema-publication manifest
  hashes, and generated-bundle drift checks.
- Semantic validation: reference indexes, variable-token declaration checks,
  ambiguity rejection, dependency/control-flow closure, and collect-all error
  reporting.
- Module security: local/OCI/locked import resolution, repo-relative path
  handling, import cycle rejection, namespace collision rejection, digest pins,
  lockfile/export-hash checks, trust policy, signature verification, and bounded
  OCI bundle extraction.
- Secret handling and OS exposure: explicit `redacted`/`operator_secret`
  omission validators, posture-only credential models, and command/argv
  redaction rules remain in force after substitution. Do not document or test
  parameter passing in a way that places real secrets in process argv or error
  output.
- Error envelopes: language-service diagnostics and SDL exceptions should name
  paths and failing refs without dumping full scenario payloads, environment
  values, or secret-bearing parameter maps.

## Extension Boundary

Future variable types or constraints extend the stable four-step instantiation
contract: choose a value, type-check it, constraint-check it, then substitute
and revalidate the concrete scenario. The parameterization seam belongs in the
variable declaration and the instantiation request's `parameters`/`profile`
surface, not in ad hoc per-field knobs.

If a future backend-capability check needs finite-domain information after
substitution, add an explicit provenance seam for that field and document why
the runtime layer needs the pre-instantiation variable name. Do not infer a
general cross-layer obligation from the existing `nodes.os` and
`infrastructure.count` support.

## Gotchas And Anti-Patterns

Avoid:

- treating `${name}` as a reference target instead of a substitution token;
- allowing embedded placeholders in identifier-defining keys because they are
  not whole-string placeholders;
- validating only full-value placeholders while the contract permits embedded
  tokens in larger strings;
- silently ignoring undeclared instantiation parameters or unresolved optional
  variables that are still referenced;
- making `allowed_values` a backend hint rather than an instantiation-time
  closed set;
- duplicating variable type checks in processor, runtime, CLI, MCP, or backend
  code instead of using `instantiate_scenario()`;
- tightening `scenario-instantiation-request-v1.parameters` with scenario-local
  knowledge it cannot possess;
- leaking module-private variables into the merged authored scenario;
- weakening instantiated-schema token rejection because the Python model already
  rejects unresolved placeholders;
- creating new exception classes, diagnostic envelopes, schema registries, or
  policy ledgers for this work.

## Non-Goals

- Implementing SDL variable substitution or validation changes in this note.
- Implementing backend plan realization; that remains tracked separately in the
  reference backend work.
- Adding runtime auth, persistence, control-plane endpoints, audit logging, or
  network behavior.
- Rewriting explanatory docs wholesale. Narrow follow-up edits may align stale
  "full-value only" wording with the normative contract, but the normative
  source remains `specs/sdl/`.
