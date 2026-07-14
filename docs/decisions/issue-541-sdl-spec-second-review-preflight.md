# Issue 541 SDL Specification Second-Review Preflight

Date: 2026-07-14

Issue: #541.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note fixes the architecture boundary for the independent review. It does
not review or change SDL semantics, schemas, models, validators, diagnostics, or
workflow behavior. No ADR is needed: ADR-009, ADR-019, the issue-498 preflight,
and the issue-722 catalog-parity preflight already own the relevant decisions.

## Revision-Aware Review Baseline

The review evaluates the complete language at the repository revision under
review. Numeric and behavioral examples in issue #541 describe the #540
baseline; they are not authority for rolling back later accepted SDL changes.
Three current differences are especially easy to misclassify as defects:

- `specs/sdl/sections.md` and the published authoring schema currently enumerate
  32 top-level fields. The post-#541 `realization` composition field and
  `identity_domains` authoring section account for the increase from 30.
- ADR-076 now defines dots as qualified-address syntax, not authored identifier
  content. Authored node local ids keep the 35-character limit but use the
  portable local-id grammar and therefore do not admit `.`.
- `specs/sdl/diagnostics.md` now states the accepted meaning-preservation
  criterion that resolves IMP-3. A review must verify that boundary; it must not
  restore the earlier pre-resolution wording that diagnostics only coordinates
  with IMP-3.

The durable comparison is structural and bidirectional, never count-only:
normative catalog rows, published schema members, and reference-implementation
evidence must agree at the same revision. Historical counts remain useful review
anchors, but a matching count cannot excuse a missing, renamed, or misshaped row.

## Existing Boundaries To Reuse

- Authority direction is fixed by ADR-009 and ADR-019:
  `specs/sdl/` is language-neutral normative prose,
  `contracts/schemas/sdl/*.json` is hand-governed schema authority, and
  `implementations/` is conformance evidence. No one surface is generated from
  another to make a discrepancy disappear.
- `tools/check_sdl_catalog_parity.py` is the canonical read-only three-way drift
  gate. Its bounded Markdown table parsers, `PolicyFailure` records, deterministic
  rendering, and exception mechanism are the workflow incumbents; semantic
  validator behavior remains covered by its owning tests.
- `Scenario`/`SDLModel`, `_mapping_scopes.HASHMAP_SECTIONS`, the typed
  declaration index and `SemanticValidator`, variable/instantiation admission,
  and `RUNTIME_SERVICE_FAMILIES` are implementation evidence for their existing
  concerns. Completion metadata is not validation authority, and the runtime
  registry must not be duplicated in prose tooling.
- The existing `SDLParseError`, `SDLValidationError`, and
  `SDLInstantiationError` surfaces and structured language diagnostics remain the
  only SDL error boundary. Catalog drift is a repository-policy failure, not a
  fourth SDL exception category.
- Schema edits, if an actual schema defect is found, remain governed by the
  publication manifest and generated-schema parity. A prose-only review does not
  authorize changing validation behavior to obtain agreement.

The extensibility seam is the checked catalog row shape, parameterized by the
contract version/table heading and by explicit reference-domain tokens. The next
section, edge, runtime family, or contract version adds reconciled authority and
registry rows; it does not add a second schema, metamodel, resolver, or hard-coded
count source.

## Cross-Cutting Security And Operational Guardrails

- Source/config shape continues through the safe YAML source profile, mapping-key
  collision preflight, operational/aggregate composition budgets, closed Pydantic
  models, typed declaration collision checks, semantic validation, and
  substitute-and-revalidate instantiation. Documentation corrections must not
  bypass, duplicate, or weaken any layer.
- Secret handling remains governed by ADR-056/057: explicit redaction is
  error-enforced and the name classifier is advisory. Review evidence and policy
  failures may identify paths, rows, and symbols, but must not include scenario
  values, parameter maps, source bodies, credentials, environment dumps, raw
  framework inputs, or tracebacks.
- The review introduces no authentication surface, environment binding, network
  call, process-argv data flow, temporary state, database, cache, or other
  persistence. Nox remains the single workflow entry point and its existing
  session reporting remains the observability surface.
- Authority and catalog tooling reads fixed repository-relative files as inert
  data. Internal relative links may be normalized and existence-checked without
  dereferencing them; tooling must not fetch external Markdown links, resolve SDL
  imports, or accept caller-controlled paths as part of validation.

## Gotchas And Non-Goals

Avoid count-only confirmation, generating one normative authority from another,
using editor-completion metadata as semantic truth, treating every `_ref` field
as one generic symbol domain, conflating scenario- and node-scoped
`forwarding_agents`, or collapsing SDL symbols, workflow-local ids, controlled
vocabularies, contract ids, opaque profile refs, and runtime-family addresses
into one resolver. Do not turn prose discrepancies into semantic changes without
the owning authority and tests, introduce a new diagnostic envelope, or duplicate
policy commands in CI.

This preflight does not perform the second review, prescribe an implementation
plan, change accepted ADRs, post a GitHub review summary, or authorize changes to
SDL syntax, runtime behavior, compiler behavior, APIs, storage, package versions,
or release metadata.
