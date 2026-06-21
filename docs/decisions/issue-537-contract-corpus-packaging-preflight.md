# Issue 537 Contract Corpus Packaging Preflight

Date: 2026-06-14

Issue: #537.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for shipping the published
contract corpus with the `aces-sdl` Python distribution. It is guidance for the
implementation and does not implement package-data wiring, resource loaders,
tests, release automation, or the release itself.

## Binding Sources

- ADR-009 defines `contracts/` as the normative machine-readable artifact
  boundary and implementations as consumers of those artifacts.
- ADR-019 and `specs/authority/authority-boundary.yaml` are the canonical
  machine-readable authority-boundary seam: `contracts/schemas/`,
  `contracts/fixtures/`, `contracts/profiles/`, and
  `contracts/concept-authority/` are separate normative families.
- ADR-061 and `contracts/schema-publication-manifest.json` govern published
  schema inventory and schema compatibility. Package-data work must not add a
  second schema registry or change-ledger.
- The Python distribution is declared in
  `implementations/python/pyproject.toml`; release notes are towncrier
  fragments under `changelog.d/`, and CI already treats `v*` tags as release
  events.

## Architecture Decisions

- Keep the top-level `contracts/` tree as the normative source of truth. A
  packaged corpus is a distribution copy of that authority, not a second
  authority root and not an implementation-owned schema set.
- Resolve default corpus reads through a single `importlib.resources`-backed
  seam in `aces_contracts`. The seam should expose package resources for
  `schemas`, `fixtures`, `profiles`, and `concept-authority`; callers should
  not each reconstruct repository paths.
- Preserve explicit local-development overrides such as `--fixtures-root` and
  `--profiles-root`. Overrides are caller-controlled filesystem inputs and must
  stay distinct from packaged-resource defaults.
- Backend profile identity remains artifact-driven: the JSON payload and file
  stem are still checked by `load_backend_profile_from_path()`, and adding a
  new profile JSON must not require a Python enum edit for fixture conformance.
- The conformance CLI report envelope remains stable. Missing or malformed
  packaged resources should surface through existing structured diagnostics
  such as `conformance.profile-load-failed` or `conformance.fixture-missing`,
  with sanitized messages.
- SDL semantic validation should consume the same packaged concept-authority
  artifacts as backend conformance. Do not create a separate SDL-only
  vocabulary loader or duplicate concept-authority cache.
- Versioned releases bind Python code and packaged corpus by artifact version.
  Do not conflate the package version/tag (`pyproject.toml`, Git tag, release
  notes) with JSON Schema lineage suffixes such as `*-v1`.

## Required Incumbents

- Package metadata and release conventions:
  `implementations/python/pyproject.toml`, `README.md` versioning guidance,
  `towncrier.toml`, `changelog.d/`, `.github/workflows/ci.yml`, and the
  `noxfile.py` verification graph.
- Authority and validation gates: ADR-009, ADR-019, ADR-061,
  `contracts/README.md`, `specs/authority/authority-boundary.yaml`,
  `tools/check_authority_boundary.py`, `tools/check_schema_publication.py`,
  `tools/check_generated_schemas.py`, and `tools/check_json_artifacts.py`.
- Corpus loaders to converge on the shared seam:
  `aces_contracts.backend_profiles`, `controlled_vocabularies`,
  `semantic_profiles`, `reference_models`, and the concept-family loader in
  `aces_contracts.contracts`.
- Conformance surfaces:
  `aces_conformance.conformance.fixtures_root()`,
  `backend_profiles_root()`, `required_contracts()`, `run_fixture_suite()`,
  `run_target_conformance()`, and `aces_cli.conformance`.
- Validation surfaces:
  closed-world `ContractModel` descendants, `schema_bundle()`,
  `manifest_authority` contract-id allowlists,
  `validate_controlled_vocabulary_scope_values()`, `Diagnostic`/`Severity`,
  and existing SDL `SDLParseError` / `SDLValidationError` behavior.
- Tests to extend instead of bypass:
  `test_backend_profiles.py`, `test_backend_conformance_cli.py`,
  `test_runtime_conformance.py`, `test_controlled_vocabularies.py`,
  `test_concept_authority.py`, `test_reference_models.py`,
  `test_semantic_profiles.py`, and policy tests for package/build metadata if
  new verification tooling is added.

## Cross-Cutting Layers

- Package-data config: `pyproject.toml` should include the corpus in both wheel
  and sdist. Include the four normative families as data; do not package
  generated caches, tests, secrets, `.git`, build output, or ad hoc copies from
  outside the declared corpus.
- Resource loading: use `importlib.resources.files()` for default reads and
  `as_file()` only at boundaries that truly need a concrete `Path`. Do not
  assume resources are ordinary directories; zipped wheels and non-editable
  installs must stay viable.
- Filesystem override security: keep profile ids and similar caller-controlled
  names behind `_validate_backend_profile_id()` and root-confinement checks such
  as `_path_is_within()`. Reject absolute paths, `..`, separators in ids, and
  symlink escapes before file reads when an override root is involved.
- JSON/config parsing: continue using `json.loads()` followed by the existing
  Pydantic closed-world models. Do not evaluate JSON, fetch remote refs, or
  coerce malformed package metadata or corpus payloads into empty defaults.
- Contract/vocabulary validation: reuse `BackendProfileModel`,
  `ControlledVocabularyCatalogModel`, `ReferenceModelCatalogModel`,
  `SemanticProfileModel`, `schema_bundle()`, and
  `manifest_authority` allowlists. Do not duplicate schemas or validators to
  make packaged-resource tests pass.
- Error envelopes and leakage control: keep conformance failures in
  `Diagnostic` envelopes and SDL failures in the established SDL errors. Do
  not dump file contents, rejected payloads, environment variables, absolute
  site-packages paths, raw tracebacks, or build backend internals into CLI
  JSON.
- Workflow gates: `nox -s contracts`, `nox -s policy`, `nox -s tests`, and
  `nox -s verify` remain the canonical gates. Any installed-wheel smoke test
  should be added to the existing nox/test graph, not a separate release-only
  script with different semantics.
- Secret and OS exposure: runtime loaders should read packaged data only. They
  should not shell out, read auth tokens, inspect Git remotes, or require
  environment variables. Release publishing may need credentials, but those
  belong to maintainer/CI release workflow state and must not appear in argv,
  logs, package metadata, fixtures, or diagnostics.
- Auth, persistence, and HTTP layers: this issue does not add or change
  control-plane auth, persistence, APIs, audit logs, or request handling. If a
  later user-visible API exposes corpus inspection, it must separately reuse
  the existing control-plane security and redacted error patterns.

## Extension Boundary

The extension seam is one package-resource corpus resolver, parameterized by
normative family and relative artifact path. Adding a future corpus family
should require one include-pattern update, one resolver family entry, and the
existing artifact validation gates, not edits to every loader.

Tests should keep override roots as parameters for local corpus development.
The default installed-distribution test must exercise the package-resource path
with no repository `contracts/` tree present, so a source-checkout fallback
cannot mask a missing wheel payload.

Release extensibility belongs to the package version and changelog path:
future releases should bump `pyproject.toml`, add a `changelog.d/` fragment,
build wheel/sdist artifacts containing the corpus, and create a `v*` tag or
GitHub Release. Schema stability promotions remain ADR-061 manifest changes,
not package-version side effects.

## Gotchas And Anti-Patterns

Avoid:

- leaving any default loader anchored on `Path(__file__).parents[N]`;
- adding a second `contracts/` copy to source control without declaring which
  copy is authoritative;
- moving normative authority under `implementations/python/` as an
  implementation-owned package directory;
- making tests pass by setting `--fixtures-root`, `--profiles-root`, or
  `PYTHONPATH` in the installed-wheel acceptance path;
- using `importlib.resources` in one loader while concept-authority or
  semantic-profile loaders keep source-tree heuristics;
- introducing environment variables as hidden corpus-root configuration;
- swallowing missing packaged resources and returning empty contract/profile
  sets;
- exposing full validation errors that include rejected corpus payloads;
- duplicating backend profile tables, schema registries, vocabulary catalogs,
  fixture loaders, exception hierarchies, nox sessions, or release scripts;
- treating a Git tag as evidence that the wheel actually contains the corpus;
- editing accepted ADR bodies in place instead of following ADR-059 amendment
  rules when architecture text needs to change.

## Non-Goals

- Changing contract payload shapes, schema stability classes, backend profile
  semantics, controlled vocabulary terms, or SDL semantic rules.
- Redesigning conformance, profile capability inference, live target probing,
  or the conformance JSON report format.
- Adding runtime persistence, control-plane endpoints, authentication,
  authorization, audit logging, or network access.
- Publishing credentials or requiring live GitHub/PyPI access from runtime
  code.
- Cutting the actual release in this preflight note.
