# Issue 726 SDL Lineage And Provenance Ledger Preflight

Date: 2026-07-12

Issue: #726.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note fixes architecture guardrails for the lineage, derivation, and
third-party provenance remediation. It does not create the ledger, audit or
change a third-party notice, correct citations, add a checker, or change SDL
semantics.

## Boundary And Authority

The implementation must keep three records distinct:

1. **Intellectual lineage** records that a source influenced ACES syntax or
   meaning. It is not evidence that source code was copied.
2. **Artifact/code derivation** records copied, translated, or structurally
   adapted source artifacts at exact paths and revisions. It is the input to
   the copyright/license disposition.
3. **Implementation examples** demonstrate behavior. Similarity in a test,
   fixture, or example is not language authority or code-derivation evidence.

`docs/explain/sdl/lineage.md`, `precedents.md`, and
`related-work-comparison.md` remain explanatory views. The auditable ledger
must be a normative, versioned contract artifact; explanatory tables consume
it and must not carry a parallel classification or source registry.

The ledger does not belong in `contracts/concept-authority/`.
`concept-families-v1.json` answers what shared concepts mean; it does not answer
whether ACES code was copied, whether syntax is compatible, or whether a notice
is owed. Establish a dedicated `contracts/provenance/` authority root for a
versioned SDL provenance ledger and govern its published schema under
`contracts/schemas/provenance/`. Adding that normative artifact family requires
the ADR-009/ADR-019 authority-boundary process and the corresponding
`specs/authority/authority-boundary.yaml` classification. Do not place the
authoritative ledger under non-normative `docs/`, `research/`, `examples/`, or
`implementations/`.

## Ledger Contract

Use one closed, versioned ledger with stable, namespaced subject identities.
The contract must express these concepts without relying on prose conventions:

- **Source records:** source id and kind; project/standard/publication identity;
  exact version, tag, commit, edition, or DOI as appropriate; immutable primary
  citation; pinned artifact URL; and reviewed license source. A Git source such
  as OCR must record the full commit, not only `v0.21.2`.
- **Subject records:** subject kind plus canonical ACES coordinate. Use existing
  catalog ids and published-schema coordinates (`contract_id` plus JSON
  Pointer), not Python module/class names or headings in explanatory docs.
- **Claims:** one subject may have multiple non-overlapping claims because its
  syntax and semantics may have different sources. Each claim states the
  lineage plane (`syntax`, `semantics`, `artifact/code`, or `example`), the
  issue-required classification, source refs, exact ACES and source artifact
  boundaries, divergence, primary citation, and compatibility status.
- **Third-party disposition:** per source and derived-artifact boundary, record
  the reviewed license/copyright material, derivation extent, whether a notice
  is required, the resulting repository artifact or a rationale for no notice,
  review date, and evidence refs. `unknown` is valid during the audit but must
  fail release acceptance for any source with an artifact/code claim.

The required classification labels mix two dimensions. Preserve the labels but
make the dimension explicit: `adopted syntax`, `adopted semantics`, `adapted`,
and `ACES-native` are lineage claims; `removed` and `planned` are disposition
claims. The schema/checker must reject `planned` or `removed` as the only claim
for a current catalog subject and must reject a current/executed compatibility
claim for a planned subject. Do not copy the concept-authority provenance enum
(`adopted`, `adapted`, `native`) or semantic-coverage statuses
(`active`, `partial`, `planned`) into this contract; those vocabularies answer
different questions.

Compatibility is also independent of provenance. Record it explicitly and
directionally (for example, ACES acceptance or behavior relative to a named
source revision). `adopted syntax` does not imply parser compatibility,
`adopted semantics` does not imply runtime compatibility, and `adapted` does
not imply incompatibility.

The phrase **direct port** is prohibited in current reader-facing prose unless
the same statement explicitly names the plane, exact source revision and
artifact boundary, and compatibility status. Prefer the ledger's precise
classification. Code comments such as the current `aces_sdl.nodes` module
header must be reconciled with the artifact/code audit rather than treated as
proof of copying.

## Coverage And Canonical Incumbents

Coverage must be derived from existing authorities, never from the current
`precedents.md` rows or from a new hand-maintained family list:

- top-level fields and authoring sections:
  `specs/sdl/sections.md`, checked against
  `contracts/schemas/sdl/sdl-authoring-input-v1.json` and `Scenario.model_fields`
  by `tools/check_sdl_catalog_parity.py`;
- node runtime families: `specs/sdl/runtime-inventory.md`, checked against
  `_runtime_service_families.RUNTIME_SERVICE_FAMILIES` by the same parity gate;
- shared concept families and recurrent normative structures:
  `contracts/concept-authority/concept-families-v1.json` and
  `reference-models-v1.json`, validated by their existing closed-world contract
  models and concept-authority governance gate; and
- published contract identity and schema coordinates:
  `contracts/schema-publication-manifest.json` and the published schemas.

The ledger checker must compare namespaced sets bidirectionally: every current
canonical subject has a ledger record, every current ledger subject resolves to
one canonical subject, and tombstoned/planned records are explicitly outside
the current set. A matching count is not coverage. The subject namespace must
distinguish a top-level section, a runtime family, a concept family, and a
reference model even when they share a word such as `relationships`.

Field-level adoption or porting claims must use exact schema pointers and exact
source paths/symbols. A family-level claim may describe a bounded family, but it
must not be presented as proof that every child field was adopted. Do not infer
field origin from the containing Python file, class inheritance, a shared field
name, or repetitive prose. The ledger shape must allow another field pointer to
be added without a schema change.

Reuse these repository mechanisms:

- authority: ADR-009, ADR-019,
  `specs/authority/authority-boundary.yaml`, and
  `tools/check_authority_boundary.py`;
- contract shape: `ContractModel(extra="forbid")`, existing constrained string
  aliases and model validators, `aces_contracts.versions`, `schema_bundle()`,
  and the valid/invalid fixture convention;
- schema publication: ADR-061,
  `contracts/schema-publication-manifest.json`,
  `tools/check_schema_publication.py`, and
  `tools/check_generated_schemas.py` (published schema is authority; generated
  output is compatibility evidence);
- artifact validation: `tools/check_json_artifacts.py`, `check-jsonschema`, and
  the existing catalog-derived validation pattern used by UCO alignment;
- policy failures and paths: `tools.policy.common.PolicyFailure`,
  `safe_repo_path`, deterministic sorting/JSON rendering, and the shared
  exception mechanism;
- workflow: the single `noxfile.py` policy/contracts graph and
  `SessionReporter`; `verify`, hooks, and CI inherit that wiring; and
- documentation/citation stance:
  `docs/explain/reference/documentation-style-guide.md` and the source-log
  discipline under `docs/research/related-work-comparison/`.

The lineage checker is a repository contract/policy checker. Its failures must
not become `SDLParseError`, `SDLValidationError`, runtime `Diagnostic`, a
control-plane DTO, or a new exception hierarchy. It observes the SDL contract;
it does not validate authored scenario instances.

## Citation And License Audit Guardrails

External identity must be verified against primary sources during the audit.
Record title, authors/maintaining body, year/edition, DOI or canonical document
identifier, and immutable URL as separate fields so a correct DOI cannot be
paired with the wrong title/year. The known CRACK row that labels the 2020
*Computers & Security* DOI as the 2018 IEEE NCA paper must be corrected as two
distinct works. A DOI resolver result is verification evidence, not a source of
ACES semantics.

CI must remain offline and deterministic. It can validate identifier syntax,
duplicate/conflicting bibliographic identities, internal references, pins, and
recorded verification metadata; it must not fetch GitHub, DOI resolvers, or
documentation sites on every run. Dead-link and citation review is a bounded
implementation-time audit whose evidence is committed in the ledger/source
notes.

License disposition must inspect the license and copyright state at each exact
source revision and the actual ACES artifact/code boundary. Repository license
detection, a project homepage badge, or a current default-branch license is not
sufficient evidence for an older commit. Do not automatically conclude that a
notice is unnecessary because the implementation is a rewrite, uses different
names, or is small. Conversely, intellectual influence alone is not copied
code. Where the audit cannot reach a supportable disposition, record the
blocker and obtain qualified legal review; the checker must never manufacture a
legal conclusion.

If a notice is required, keep the verbatim notice in the repository's
distribution-visible notice surface and point to it from the ledger. Do not
duplicate notice text in every lineage row. The wheel/sdist packages the entire
`contracts/` corpus through `implementations/python/hatch_build.py`, so the
implementation must explicitly decide whether the legal notice itself also
needs inclusion outside the corpus in built distributions; do not assume that
shipping the audit record satisfies a license's notice condition.

## Security And Operational Layers

The design passes these cross-cutting layers:

1. **Authentication/control plane:** none. No HTTP endpoint, bearer identity,
   role policy, backend, or Ground Control data path is part of the ledger.
2. **File/config shape:** parse only fixed repo-relative JSON/Markdown/schema
   paths as inert data. Closed models and published JSON Schema reject unknown
   fields and invalid unions. Any ledger-provided path passes `safe_repo_path`;
   no symlink escape, absolute path, `..`, dynamic import, or evaluated content
   is permitted.
3. **Source and semantic validators:** the checker consumes the existing SDL
   catalog parity, concept-family, reference-model, runtime-family, and schema
   publication authorities. It must not weaken or duplicate `SDLModel`,
   `SemanticValidator`, controlled-vocabulary validation, or generated-schema
   parity.
4. **Secret handling:** only public citations, repository coordinates, and
   public source metadata belong in the ledger. Do not inspect environment
   dumps, credentials, private source URLs, local Git credential helpers, or
   `/home/atomik/.secrets`; do not place tokens or private URLs in source
   records, fixtures, failures, or docs.
5. **Environment/OS exposure:** add no environment binding, daemon, network
   requirement, cache, database, or mutable state. Checked-in validation uses
   fixed argv with no shell and carries no source metadata or credentials in
   process argv. One-time authenticated research, if unavoidable, stays outside
   committed command logs and CI.
6. **Error envelope and observability:** malformed ledgers produce bounded
   `PolicyFailure` records with rule id, repo path, subject id, and line/pointer
   where available. Do not print file bodies, notice bodies, environment
   values, raw external responses, tracebacks, or credentials. Nox
   `SessionReporter` is the only new stage-level observability needed.
7. **Persistence/distribution:** validation is read-only. It writes no repaired
   ledger, fetched source, report, or cache. The checked-in contract is the
   durable record; package inclusion continues through the canonical corpus
   build seam.

## Extensibility Seam

The seam is a namespaced subject resolver plus a source-kind-discriminated pin,
not a hard-coded OCR table. Parameterize the checker by ledger path/schema,
current authoring contract id, and catalog extractors. A later SDL contract
version, runtime family, reference model, external standard edition, or
additional source revision should add a subject/source/claim record without
changing the ledger schema or adding a field-specific checker branch.

Source pins must be discriminated: Git sources require repository + full commit
+ path/symbol; standards require maintaining body + edition/version + canonical
document id; publications require bibliographic identity + DOI/immutable URL;
ACES-native claims require internal authority refs and no invented external
source. Do not force all sources into a nullable “version or commit” bag.

## Gotchas And Anti-Patterns

Avoid:

- making `precedents.md`, a spreadsheet, a README table, Python comments, or a
  research source log the authoritative ledger;
- placing derivation/license facts in the concept-family catalog or treating
  UCO alignment as SDL code provenance;
- one classification per family when syntax and semantics have different
  sources;
- using `planned` as evidence of current implementation, or hiding removed
  items by deleting their tombstones;
- claiming field-level coverage from a family label or matching counts;
- keying subjects by Python classes, filenames, prose headings, or display
  titles instead of stable catalog ids/schema coordinates;
- unpinned default-branch links, short commits, bare version strings, or DOI-only
  citations with no verified identity;
- treating semantic influence, translation, code copying, fixture similarity,
  and wire compatibility as synonyms;
- live network validation in policy/CI, vendoring whole upstream repositories,
  or committing long third-party excerpts as audit evidence;
- adding a second schema registry, catalog parser, corpus loader, policy result
  type, exception hierarchy, logger, workflow command, or CI-only check; and
- rewriting accepted ADR bodies outside ADR-059's amendment process.

## Non-Goals And Implementation Boundary

- No SDL syntax, semantic model, parser, validator, compiler, runtime, API,
  persistence, logging, schema compatibility, or package behavior changes are
  authorized by this issue.
- The ledger documents provenance; it does not promise source compatibility,
  conformance, clean-room status, or legal clearance beyond the recorded
  evidence and disposition.
- Dependency SBOM/license scanning is not a substitute for the source-derivation
  audit and is not added by this issue.
- Existing concept-family provenance, UCO alignment, semantic coverage,
  experiment provenance, and phase-derivation contracts remain distinct and
  are not migrated into the SDL provenance ledger.
- Historical accepted ADR prose is not normalized for terminology. Correct
  current explanatory docs, comments, citations, and machine-readable records;
  amend an accepted ADR only when its current normative decision is affected.
