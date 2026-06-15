# Issue 506 Determinism Witness Preflight

Date: 2026-06-15

Issue: #506.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for adding a narrow
determinism witness for parse -> instantiate -> compile. It is guidance for the
implementation and does not add the witness test, change parser/compiler
behavior, or update the parser documentation citation.

## Binding Sources

- `docs/explain/sdl/parser.md` makes the documented claim: file-backed import
  expansion is deterministic and in-memory parsing rejects imports.
- ADR-053 fixes the module-composition model: imports are typed SDL
  composition, resolved through lock/trust/digest/version checks, expanded
  before semantic validation, and compiled as one canonical scenario.
- ADR-016 fixes the lifecycle order: authoring, validation, instantiation,
  compilation, planning, execution, observation. This issue witnesses only the
  first four phases.
- ADR-004 fixes the compiler boundary: `compile_runtime_model()` is a pure
  normalization pass from an instantiated scenario into canonical runtime
  resources.
- `.ground-control.yaml`, `noxfile.py`, and `implementations/python/pyproject.toml`
  define the verification graph. The witness must live under
  `implementations/python/tests/` so CI and `nox -s verify` run it.

## Architecture Decisions

- Test the public pipeline, not internals: `parse_sdl_file(...)`,
  `instantiate_scenario(...)`, and `compile_runtime_model(...)`.
  `parse_sdl(...)`, `expand_sdl_modules(...)`, direct `Scenario(...)`
  construction, and compiler helper calls are the wrong witness surface.
- Build the representative scenario as temp files through `tmp_path`, including
  at least one local module import, explicit namespace, module exports, variables
  with defaults or provided parameters, multiple agents, multiple features, and
  multiple relationships. This exercises import expansion, map-key preservation,
  reference rewriting, variable substitution, and ordered collection surfaces.
- Compare the compiled artifact with one canonical serializer local to the
  witness. The serializer should convert dataclasses and Pydantic/contract
  models to plain JSON-compatible data, then use
  `json.dumps(..., sort_keys=True, separators=(",", ":"))`. Do not compare
  `repr(...)`, object ids, dict iteration text, or pretty JSON.
- Enumerate explicitly timestamp-typed compiled fields in the test. Today the
  parse/instantiate/compile path does not generate timestamps; timestamp-shaped
  values are authored data. If the witness fixture avoids timestamp-bearing
  runtime inventory, the exclusion set should be empty and asserted as such.
- The `PYTHONHASHSEED` variation must be a subprocess pass over the same
  temp-file scenario graph. Use fixed argv, `sys.executable`, a controlled
  `env`, and captured stdout containing only the canonical serialization or a
  digest of it. Do not use `shell=True` or embed secrets in argv.
- After the test exists, `docs/explain/sdl/parser.md` should cite the test by
  stable test name or file path. Do not pre-cite a non-existent test.

## Required Incumbents

- Parser and composition: `aces_sdl.parser.parse_sdl_file`,
  `_load_normalized_data`, `ImportDecl`, `ModuleDescriptor`,
  `aces_sdl.composition.expand_sdl_modules`, and
  `aces_sdl.module_registry.resolve_import`.
- Validation and instantiation: `SDLModel(extra="forbid")`,
  `SemanticValidator`, `instantiate_scenario`, `InstantiatedScenario`, and
  `SDLInstantiationError` / `SDLParseError` / `SDLValidationError`.
- Compilation: `aces_processor.compiler.compile_runtime_model`,
  `RuntimeModel`, existing compiler dataclasses, and `resource_payload(...)`
  where backend-facing resource shape is relevant.
- Existing test patterns: `test_sdl_module_registry.py` for temp-file module
  imports and lock/trust behavior, `test_runtime_models.py` for compile
  assertions, `test_instantiated_scenario_schema.py` for concrete instantiated
  payload constraints, and `test_corpus_packaging.py` for fixed-argv subprocess
  style.
- Verification workflow: `nox -s tests` for the default CI pytest sweep and
  `nox -s verify` for the full repository gate.

## Cross-Cutting Layers

- YAML/config parsing: the witness must enter through `parse_sdl_file(...)`,
  which uses `yaml.safe_load`, top-level mapping checks, key normalization,
  shorthand expansion, variable-key rejection, import expansion, and
  `extra="forbid"` Pydantic construction.
- Module supply-chain validation: local imports still pass through
  `ImportDecl`, module descriptor validation, version checks, digest pins when
  authored, optional lockfile checks, allowed-parameter checks, namespace
  collision rejection, reserved `__private` namespace rejection, and import-cycle
  detection. The test should not bypass those layers with direct payload merges.
- Semantic validation: the root expanded scenario must pass the existing
  `SemanticValidator`; missing, ambiguous, or unexported references must remain
  hard errors rather than being normalized away by the witness.
- Instantiated-shape validation: variable substitution must go through
  `instantiate_scenario(...)`, including variable type checks, undeclared
  parameter rejection, unresolved-placeholder rejection, `InstantiatedScenario`
  revalidation, and post-substitution semantic validation.
- Compiler contracts: compilation must use the existing `RuntimeModel` and
  dataclass resources. The witness must not introduce a second compiled schema,
  duplicate DTO, or alternate address generator.
- Secret-handling surface: fixture data should avoid real credentials. If an
  environment/runtime secret-shaped value is needed, use existing redaction
  classifications and assert only the classification, not raw secret material.
- Environment and OS exposure: the subprocess should set only
  `PYTHONHASHSEED` and any minimal import-path/cwd variables needed to import
  the project under pytest. Pass scenario paths as argv values, never shell
  fragments, and never place tokens, private keys, or operator secrets in argv
  or stdout.
- Error envelopes: failures should be ordinary pytest assertion failures or the
  existing SDL exception types. Do not add a new exception hierarchy, logging
  channel, CLI wrapper, or diagnostic envelope for the witness.
- Auth, persistence, and network layers: this issue should touch none of them.
  No control-plane auth, HTTP API, database, runtime manager, backend registry,
  OCI network fetch, or audit-log behavior is in scope.

## Extension Boundary

The extensibility seam is the canonical serializer plus a small fixture builder
parameterized by scenario root path, parameters, and hash seed. Future
determinism witnesses can reuse that seam for other pipeline phases or broader
ASR-514 coverage without editing production parser, composition, instantiation,
or compiler code.

If future compiled models add genuinely generated timestamp fields, add those
field paths to the explicit exclusion list with a comment naming the producer.
Do not introduce broad key-name scrubbing such as dropping every field whose
name contains `time`.

## Gotchas And Anti-Patterns

Avoid:

- comparing `repr(model)`, object identity, insertion-order pretty JSON, or
  unsorted dict text;
- mutating production code only to make the witness deterministic unless the
  test exposes a real nondeterminism bug that the implementation deliberately
  fixes;
- constructing `Scenario` or `RuntimeModel` objects directly instead of passing
  through parse, import resolution, instantiation, and compilation;
- adding a duplicate schema, duplicate validator, duplicate exception hierarchy,
  or duplicate module-import workflow for test convenience;
- using sets in fixture construction where the witness is supposed to exercise
  authored order and stable compiler order;
- masking nondeterminism by sorting away ordered collection values that are
  semantically ordered, such as authored list fields, workflow steps, or
  compiled tuples;
- making the subprocess test depend on the developer's ambient environment,
  home directory, network, installed package, or shell;
- running an OCI registry or generating signing keys for this narrow witness
  when a local file import is enough to exercise composition order;
- updating `docs/explain/sdl/parser.md` with a citation before the executable
  test lands.

## Non-Goals

- Proving all ASR-514 determinism and stability properties.
- Redesigning module composition, lockfile semantics, trust policy, parser
  normalization, variable substitution, compiler ordering, or runtime planning.
- Adding a public canonical-serialization API or published compiled-runtime
  JSON schema.
- Changing contract schemas, generated schema bundles, formal specs, or the
  compatibility-only `implementations/python/src/aces/` wrappers.
- Adding control-plane, backend, persistence, auth, logging, or network
  behavior.
