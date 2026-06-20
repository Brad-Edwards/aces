# Issue 508 Related-Work Comparison Preflight

This note is the architecture preflight for GitHub issue #508. It is guidance,
not an implementation plan. It does not author the comparison matrix, perform the
research, or implement the requested documentation change.

## Architecture Decisions

- The related-work comparison is explanatory synthesis. It must not become a new
  semantic authority for ACES. ACES-side claims cite existing specs, ADRs,
  contracts, and reference notes; non-ACES cells cite primary external sources.
- The matrix is an evidence surface, not a ranking. Cells should be `yes`,
  `partial`, `no`, or `out of scope`, each with a one-line justification and
  citation. Do not infer competitor capability from memory.
- Research notes should follow the existing `docs/research/` pattern. Use a
  dedicated directory such as `docs/research/related-work-comparison/` with a
  source log, source-scope rules, and per-precedent notes. Do not introduce a
  new root-level `research/` tree unless the repository intentionally changes
  its research-root convention.
- `README.md` Lineage and `docs/explain/sdl/lineage.md` remain navigation and
  narrative source-map surfaces. Link to the new comparison page from both, and
  add the issue-required Cyber DEM/FOM differentiation in `lineage.md` without
  duplicating the whole matrix there.
- Every README lineage precedent must either appear in the matrix or be scoped
  out explicitly: OCR SDL, OCSF, CACAO, STIX, CybORG, TENA, IEEE HLA, SISO
  Cyber DEM, SISO Cyber FOM, CALDERA, and Atomic Red Team. The issue also
  requires at least one academic range/testbed DSL such as KYPO, CRACK, VSDL, or
  CyRIS.
- At least one row must honestly favor a precedent. HLA/TENA federation maturity
  and Cyber DEM/FOM standardization/interoperability status are expected
  candidates if supported by primary sources.

## Canonical Incumbents

Reuse these existing surfaces before adding new structure:

- documentation stance and citation rules:
  `docs/explain/reference/documentation-style-guide.md`
- current reference map:
  `docs/explain/reference/canonical-reference-map.md`
- SDL lineage and element provenance:
  `docs/explain/sdl/lineage.md` and `docs/explain/sdl/precedents.md`
- SDL guide and materialization limits:
  `docs/explain/sdl/index.md` and `docs/explain/sdl/limitations.md`
- shared semantic and lifecycle boundaries:
  `docs/explain/reference/shared-semantic-integrity.md`
- authoring vs instantiation:
  `specs/sdl/variables-and-instantiation.md` and
  `docs/explain/reference/explicitness-realization-semantics.md`
- objectives and workflows:
  `specs/formal/objectives/`, `docs/explain/reference/objective-semantics.md`,
  and `specs/formal/workflows/`
- participant behavior and episode semantics:
  `specs/formal/participant-semantics/README.md`, ADR-020, ADR-022, and ADR-054
- typed relationship subtypes:
  ADR-052 plus the existing `RelationshipDatabaseAccess` and
  `RelationshipMailAccess` precedents
- backend agnosticism and conformance:
  `docs/explain/reference/backend-conformance.md`, ADR-008, ADR-009, ADR-036,
  ADR-060, and `contracts/profiles/backend/`
- provenance, disclosure, and redaction:
  ADR-041, ADR-055, ADR-056, ADR-057, runtime contracts, and the experiment-core
  research notes
- time and causality:
  `docs/explain/sdl/lineage.md`, `docs/decisions/sem-213-temporal-participant-preflight.md`,
  and `specs/formal/participant-semantics/README.md`
- research-note pattern:
  `docs/research/experiment-core/` and
  `docs/research/participant-backend-contracts/`
- workflow gates:
  `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`

## Cross-Cutting Layers

The intended implementation is documentation-only, so most runtime gates must
remain untouched. That is still a design constraint:

- Auth surface: no new auth path, token handling, control-plane call, or live
  backend access belongs in this issue.
- Secret-handling surface: source notes, links, command examples, and citations
  must not include bearer tokens, credentials, private repository URLs with
  embedded tokens, private keys, or copied secret-bearing payloads.
- Env/config surface: no new environment variables, config files, or profile
  selectors are needed. If research tooling requires credentials, do not record
  them in docs or command lines.
- OS-level exposure: do not put API keys or access tokens in process argv in
  captured commands. Prefer connector-managed or local citation tooling where
  available.
- Parser/schema/validation surface: do not add SDL syntax, schemas, contract
  fixtures, validators, DTOs, exception types, logging, or persistence. Markdown
  must pass the existing MyST/Sphinx docs build and policy gates.
- Error-envelope surface: no new code means no new error envelope. If a helper is
  later proposed, it must reuse existing diagnostics instead of creating a
  comparison-specific exception or logging stack.
- Copyright/source surface: capture source metadata, scope notes, and short
  paraphrased findings. Do not commit large third-party source copies or long
  verbatim excerpts unless the repository already has a governed license basis.

## Extensibility Seam

The stable seam is the comparison dimension, not a new schema. Keep the matrix
rows as named, reviewable dimensions with short definitions near the table. A
future precedent column or academic DSL should require adding source notes and a
column, not reworking README lineage, existing ADRs, or SDL semantics.

If future work wants machine-readable comparison data, that should be a separate
governed artifact decision. Issue #508 should stay prose/table documentation.

## Gotchas And Anti-Patterns

Avoid:

- marketing posture, vague superiority claims, or ACES-winning-every-row framing
- treating docs under `docs/` or research notes as normative ACES semantics
- restating large ADR content instead of linking the owning authority
- claiming a precedent lacks a feature unless a primary source supports that
  characterization
- merging distinct systems just because they share an acronym or ecosystem
  lineage, especially Cyber DEM vs Cyber FOM and HLA vs TENA
- conflating runtime inventory with deployment format
- conflating OCSF/STIX telemetry or CTI objects with participant-visible state
- treating CACAO workflow/playbook concepts as complete ACES participant
  behavior semantics
- treating CALDERA, ATT&CK, Atomic Red Team, or tool labels as action contracts
- treating Cyber DEM as an ACES scenario model
- treating HLA/TENA federation maturity as equivalent to ACES backend
  conformance
- marking ACES time semantics as complete when the full time/clock authoring
  model is still partially materialized

## Non-Goals

This preflight does not:

- create `docs/explain/sdl/related-work-comparison.md`
- gather or characterize external primary sources
- update README lineage or `lineage.md`
- add SDL syntax, schema contracts, validators, fixtures, or code
- define a new ADR or normative spec
- complete issue #346's broader DSL language-evaluation evidence gate
- claim compatibility with any precedent system
