# Issue 495 UCO Alignment Preflight

Date: 2026-06-14

Issue: #495.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for adding the UCO
alignment artifact. It is guidance for the implementation and does not add the
alignment artifact, schema, fixtures, tests, or specification references.

## Binding Sources

- ADR-012 defines UCO as concept authority for adopted and adapted
  cyber-domain families, while keeping ACES authoring syntax and contract
  structure separate from ontology structure.
- `specs/concept-authority/concept-authority.md` defines the concept-authority,
  ACES concept, and artifact-binding layers.
- `contracts/concept-authority/concept-families-v1.json` is the canonical
  family set and provenance source.
- `contracts/concept-authority/reference-models-v1.json` anchors recurrent
  ACES structures to published ACES schemas; it is not a UCO class map.
- `contracts/profiles/semantic/reference-stack-v1.json` composes ACES concept,
  contract, binding, and behavior assumptions; it must not become a UCO profile
  or capability profile.
- ADR-061 and `contracts/schema-publication-manifest.json` govern any new
  published schema.

## Architecture Decisions

- `contracts/concept-authority/uco-alignment-v1.json` is an alignment evidence
  artifact for the UCO authority claim. It must not redefine concept family
  scope, UCO semantics, SDL syntax, or ACES reference-model structure.
- The artifact should have one pinned UCO source/version/review scope and one
  keyed family-alignment map. Per-family entries record aligned UCO object
  types/properties and explicit divergence records.
- Required family coverage is catalog-derived: every `adopted` or `adapted`
  family whose `authority` is `UCO` in `concept-families-v1` must have exactly
  one alignment entry. Do not hard-code the current six-family set as a second
  source of truth.
- Divergence must be explicit. `adapted` families require at least one stated
  delta; `adopted` families still need an explicit divergence field so reviewers
  can distinguish "none recorded" from "not reviewed".
- The UCO review is primary-source evidence captured in the artifact. Validators
  and tests should not fetch the network at runtime; they should validate the
  recorded source URI, version/ref, review scope, and local mapping shape.
- References from `reference-models.md` and `semantic-profiles.md` should point
  to the mapping as alignment evidence. They should not duplicate the mapping
  or imply that reference models or semantic profiles inherit UCO syntax.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- Contract model base and closed-world validation:
  `aces_contracts.contracts.ContractModel`, existing constrained string aliases,
  `@model_validator`, and `pydantic.ValidationError`.
- Concept-authority catalog authority: `ConceptFamilyCatalogModel`,
  `ConceptFamilyDefinitionModel`, `ConceptProvenanceCategory`,
  `ConceptFamilyId`, and the cached catalog helpers near
  `_authoritative_concept_family_ids()`.
- Schema publication: `aces_contracts.versions`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and
  `contracts/schema-publication-manifest.json`. Do not hand-edit
  `contracts/schemas/`.
- JSON artifact validation: `tools/check_json_artifacts.py`, including its
  existing routing for `contracts/concept-authority/*.json` and
  `contracts/fixtures/concept-authority/<schema-name>/valid/*.json`.
- Fixture/test style:
  `contracts/fixtures/concept-authority/concept-families-v1/`,
  `contracts/fixtures/concept-authority/reference-models-v1/`,
  `implementations/python/tests/test_concept_authority.py`, and
  `implementations/python/tests/test_reference_models.py`.
- Specification references: `specs/concept-authority/reference-models.md`,
  `specs/concept-authority/semantic-profiles.md`, and
  `contracts/schemas/README.md` when a new schema is published.
- Workflow gates: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

- Contract shape gate: the alignment artifact must be a closed-world
  `ContractModel` with generated draft 2020-12 JSON Schema, valid fixtures, and
  invalid fixtures. Schema-only validation is not sufficient for catalog
  coverage or adapted-family divergence rules.
- Concept-authority gate: family ids, provenance, and UCO authority status come
  from `concept-families-v1`. The new artifact must not carry an independent
  family registry or copied family definitions.
- Schema publication gate: adding `uco-alignment-v1` means adding the generated
  schema through `schema_bundle()` and updating the publication manifest hash
  under ADR-061.
- Fixture gate: valid fixtures must schema-validate through
  `check_json_artifacts.py`; invalid fixtures must fail through the Pydantic
  model tests that exercise semantic invariants JSON Schema cannot express.
- Documentation gate: `reference-models.md` and `semantic-profiles.md` should
  explain the relationship in one direction only: ACES artifacts bind to ACES
  concept families, and the UCO alignment demonstrates the external authority
  review behind those families.
- Security and secret-handling gate: the design reads public ontology sources
  and local JSON only. Do not place credentials, private repository URLs, tokens,
  raw environment dumps, or command-line secrets in artifacts, fixtures,
  validation failures, logs, or review-scope notes.
- Auth, persistence, and error-envelope gate: this change should not touch HTTP
  auth, runtime persistence, control-plane stores, audit logs, or API error
  envelopes. Validation failures should remain `ValidationError` or existing
  policy-tool failures, not a new exception hierarchy.
- Host/OS exposure gate: any one-time source review commands used during
  implementation must avoid credentialed URLs and token-bearing process argv.
  The checked-in validator path must not shell out to ontology tooling or depend
  on network or host-specific state.

## Extension Boundary

The extension seam is the catalog-derived alignment map: family id plus
authority source/version plus reviewed UCO object/property references. Adding a
new UCO-backed adopted or adapted family should require a concept-family entry
and a matching alignment entry, not a code change to a hard-coded family list.

Future non-UCO authorities should not be forced into this artifact. The
coverage rule should select families where `authority == "UCO"`; a future
authority gets its own explicit artifact or versioned shape rather than
becoming an overloaded UCO mapping.

## Gotchas And Anti-Patterns

Avoid:

- treating UCO as SDL syntax or forcing ACES schemas to mirror ontology class
  hierarchy;
- treating the alignment as a reference-model catalog, semantic profile,
  controlled vocabulary, or backend capability profile;
- duplicating concept-family definitions or provenance rules inside the new
  artifact;
- validating only the JSON Schema shape while omitting catalog coverage and
  adapted-family divergence checks;
- letting `relationships` keep an `adapted` claim without an explicit delta;
- using prose-only notes where reviewers need object/property references;
- adding live network fetches, ontology parsers, caches, or generated ontology
  dumps to the validation path;
- adding a second schema generator, fixture loader, validator stack, exception
  hierarchy, or policy command;
- hand-editing `contracts/schemas/` or forgetting the schema publication
  manifest.

## Non-Goals

- Do not implement the alignment artifact, fixtures, schema, tests, or spec
  references in this preflight note.
- Do not expand the concept-family catalog beyond the issue's UCO alignment
  evidence need.
- Do not add UCO as an authoring format, runtime dependency, network service,
  or ontology-transformation pipeline.
- Do not change ACES reference-model semantics or semantic-profile phase
  semantics to make them UCO-shaped.
