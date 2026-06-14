# Issue 496 Concept Authority Governance Preflight

Date: 2026-06-14

Issue: #496.

Requirement: GOV-918.

This note records architecture preflight guardrails for adding the concept
authority governance gate. It is guidance for the implementation and does not
implement the checker, tests, nox wiring, catalog edits, or ADR linkage.

## Binding Sources

- ADR-012 defines shared concept authority, ACES-native extension discipline,
  artifact concept bindings, and controlled-vocabulary authority.
- `specs/concept-authority/concept-authority.md` is the normative concept
  authority prose for families, extension discipline, and the surface model.
- `contracts/concept-authority/concept-families-v1.json` is the authoritative
  family catalog. Family ids are authoritative at the keyed map.
- `contracts/concept-authority/controlled-vocabularies-v1.json` is the
  authoritative vocabulary catalog. Vocabulary ids are authoritative at the
  keyed map.
- `contracts/concept-authority/reference-models-v1.json` and
  `contracts/profiles/semantic/reference-stack-v1.json` consume family ids;
  they must not become fallback authorities for what families exist.
- `tools/check_authority_boundary.py` is the closest policy-tool precedent for
  ADR drift checks, word-boundary matching, `--json`, exception handling, and
  focused mutation tests.

## Architecture Decisions

- Add one policy checker for concept-authority governance. It should validate
  governance linkages around the existing catalog; it should not create a new
  concept-authority schema, registry, exception hierarchy, nox session, or
  runtime validation path.
- Treat the concept-family catalog and controlled-vocabulary catalog as the
  only machine-readable authorities for family and vocabulary identity. The
  checker derives known ids from those files and from their existing Pydantic
  models rather than hard-coding the current family or vocabulary set.
- ADR linkage is a governance proof, not concept definition. Each family id in
  the catalog should be mentioned as a whole token in at least one ADR under
  `docs/decisions/adrs/`; issue preflight notes, explanatory docs, specs, and
  tests do not satisfy that linkage.
- Use the existing word-boundary pattern from `check_authority_boundary.py`.
  Substring matches such as `prose` inside `prosecution`, or `ADR-0120` for
  `ADR-012`, must not satisfy the gate.
- Relation and vocabulary cross-reference validation must be deterministic.
  Do not infer references from every word in prose. If free-text fields need
  machine-checkable references, use an explicit token convention, such as
  inline-code tokens containing `ConceptFamilyId` or controlled-vocabulary ids,
  and validate only those explicit tokens against the authoritative catalogs.
- Current-catalog green state must be achieved by real governance linkage or
  catalog prose cleanup, not by special-casing existing family ids or skipping
  native families.

## Required Incumbents

- Policy CLI and failure surface:
  `tools.policy.common.PolicyFailure`, `failures_to_json`,
  `load_exceptions`, and `apply_exceptions`.
- Policy workflow: `noxfile.py` `_run_policy`, `TARGETED_POLICY_TESTS`, and
  the existing `policy` session. Do not add a parallel verification command.
- Concept catalog validation:
  `ConceptFamilyCatalogModel`, `ConceptFamilyDefinitionModel`,
  `ConceptProvenanceCategory`, `ConceptFamilyId`, and the cached helpers near
  `_authoritative_concept_family_ids()` in
  `implementations/python/packages/aces_contracts/contracts.py`.
- Vocabulary catalog validation:
  `ControlledVocabularyCatalogModel` and
  `implementations/python/packages/aces_contracts/controlled_vocabularies.py`.
- Test style: `implementations/python/tests/test_authority_boundary.py` for
  temp-repo seeding and drift mutations, plus
  `implementations/python/tests/test_concept_authority.py` for catalog model
  invariants.
- Repo workflow guards: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

- JSON/config parsing: read checked-in JSON with `json.loads` and validate
  through existing contract models. Do not add permissive ad hoc parsing or
  coerce malformed catalog fields to empty structures.
- Markdown/ADR scanning: scan only repository ADR files from the canonical
  `docs/decisions/adrs/` directory. Treat file text as inert text; do not
  evaluate Markdown, links, code fences, or front matter.
- Repo-path security: checker inputs should be constant repo-relative paths or
  the existing `--repo-root` pattern. If future config introduces paths, route
  them through `safe_repo_path` or an equivalent absolute-path, `..`, and
  symlink-escape guard before reading.
- Policy error envelope: emit concise `PolicyFailure` records and preserve
  `--json`. Do not dump full catalog bodies, ADR text, environment variables,
  tracebacks, or raw exception chains into policy output.
- Auth and secret-handling: this gate should read local public repo files only.
  It must not use GitHub, Ground Control, network fetches, credentials, private
  repository URLs, bearer tokens, or environment-bound secrets.
- OS/runtime exposure: do not shell out for ADR scans or catalog parsing. If
  subprocess use is later required for workflow integration, use fixed argv
  lists and keep tokens or secrets out of process argv and logs.
- Schema/publication gate: this issue should not require published schema
  changes. If the implementation chooses to add structured reference fields,
  that is a separate schema-evolution change subject to ADR-061,
  `contracts/schema-publication-manifest.json`,
  `tools/check_schema_publication.py`, and `tools/check_generated_schemas.py`.

## Extension Boundary

The extension seam is catalog-derived identity plus explicit governance tokens:

- adding a concept family requires one catalog entry and at least one ADR
  whole-token mention of that family id;
- adding a relation from native-family prose to another family should use the
  same explicit family-id token convention and resolve against the catalog;
- adding a vocabulary reference from family prose should use the same explicit
  vocabulary-id token convention and resolve against
  `controlled-vocabularies-v1.json`;
- adding future authority catalogs should add a new checker parameter or helper
  over an authoritative catalog file, not hard-code another current-id list.

## Gotchas And Anti-Patterns

Avoid:

- treating specs, issue preflight notes, READMEs, fixtures, or tests as ADR
  linkage for a family id;
- assuming the current ADR corpus already spells every catalog id exactly. A
  strict whole-token scan should treat missing exact-id linkage, such as for
  `actions-and-events`, `tools-and-artifacts`, or
  `realization-and-disclosure`, as initial green-state work rather than a
  reason for checker exceptions;
- special-casing `episodes`, `runtime-inventory`, or any current family to get
  the initial catalog passing;
- validating relation rules by natural-language guesses or by matching every
  lowercase word that happens to fit `ConceptFamilyId`;
- duplicating concept-family or vocabulary definitions in the checker, tests,
  noxfile, or policy YAML;
- turning controlled vocabularies, reference models, semantic profiles, or UCO
  alignment into alternate sources of family existence;
- adding a new nox session, policy exception format, schema generator, or
  duplicate JSON artifact validator;
- weakening the existing schema, concept-binding, semantic-profile, or
  reference-model validators while adding this governance gate.

## Non-Goals

- Implementing `tools/check_concept_authority_governance.py`, nox wiring, or
  checker tests in this preflight note.
- Adding, removing, or renaming concept families or controlled vocabularies.
- Amending ADRs to satisfy the initial green state.
- Adding new SDL, manifest, provenance, reporting, runtime, API, persistence,
  auth, logging, or schema behavior.
- Changing semantic profiles, reference models, UCO alignment, or manifest
  concept-binding semantics.
