# Related-Work Comparison Research

Issue: #508 (review LIT-1), also resolving review LIT-4.

Purpose: gather the primary-source basis for a feature-by-feature comparison of
ACES against precedent systems before writing
[`docs/explain/sdl/related-work-comparison.md`](../../explain/sdl/related-work-comparison.md).
The comparison answers the first question of any peer review of a new language:
dimension by dimension, what can ACES express that the precedents cannot, and
where do the precedents still lead ACES.

These notes do not characterize competitor capabilities from memory. Every
non-ACES claim in the comparison page is grounded in a precedent's own
documentation, standard text, source, or originating-author literature, recorded
in [`search-log.md`](search-log.md) with the exact source and a supporting
finding.

## Relationship To Prior Research

Element-level provenance and the source map already exist and are not repeated
here:

- [`docs/explain/sdl/precedents.md`](../../explain/sdl/precedents.md) — element-by-element
  source mapping.
- [`docs/explain/sdl/lineage.md`](../../explain/sdl/lineage.md) — narrative
  source map by concern area.
- `specs/formal/participant-semantics/README.md` — participant-semantics
  primary-source review.

This note covers the question specific to issue #508: how ACES and the
precedents compare across named expressivity dimensions, with each cell
traceable to a primary source.

## Contents

- [Search log](search-log.md) — the source rule, tooling, per-system primary
  sources with URLs/DOIs, and the grounded findings behind every non-ACES cell
  in the comparison matrix.

:::{toctree}
:hidden:

search-log
:::

## Source Rule

- Non-ACES cells cite the precedent's primary documentation: the maintaining
  body's standard text, the originating authors' peer-reviewed papers or
  technical reports, official project documentation, or the project's own
  source. Secondary summaries are used only to locate primary sources or where
  no primary source is available, and are identified as secondary.
- ACES cells cite repository authority: specs under `specs/`, ADRs under
  `docs/decisions/adrs/`, contracts under `contracts/`, or the reference notes
  in `docs/explain/`. The comparison page is explanatory synthesis; it is not a
  new authority for ACES semantics.
- Where a capability could not be grounded in a primary source, it is recorded
  as a confidence gap rather than asserted.

## Scope Boundaries

- The comparison is an evidence surface, not a ranking. Cells are `yes`,
  `partial`, `no`, or `out of scope`, each with a one-line justification and a
  citation.
- At least one dimension honestly favors a precedent. In practice several do:
  HLA-grounded time management and federation interoperability (SISO Cyber
  DEM/FOM, TENA/HLA), OASIS-standardized workflow taxonomy and signed
  provenance (CACAO), executed RL episode discipline (CybORG), and formal
  scenario verification (CRACK).
- Maturity is stated honestly: several ACES surfaces are formally specified but
  still materializing in the runtime, and ACES time semantics are not complete.
