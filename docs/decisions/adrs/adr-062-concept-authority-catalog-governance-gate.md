# ADR-062: Concept-Authority Catalog Governance Gate

## Status

accepted

## Date

2026-06-14

## Classification

Classification: FM0
Required artifacts: ADR, policy checker gate, unit tests
Waivers: none

The gate is a deterministic, filesystem-only structural checker (whole-token ADR
matching and catalog set-membership resolution); its correctness is established
structurally and verified by unit tests, with no semantic, graph, or stateful
reasoning that would warrant a higher level.

## Context

[ADR-012](adr-012-shared-concept-authority-and-aces-extension-discipline.md) §3
establishes the ACES extension discipline: an ACES-native concept family must be
an explicit, disciplined extension over the shared concept authority, declaring
`extension_scope`, `relation_rules`, and `non_ambiguity_constraints`. The
machine-readable catalog
`contracts/concept-authority/concept-families-v1.json` and its published JSON
Schema validate that those fields are *present and well-shaped*. Nothing
structural validates the *governance linkages* around the catalog:

- a family can be added to the catalog with no ADR deciding it exists — the
  "explicit extension" requirement is then satisfied on paper (the fields are
  filled in) but not in the architectural record;
- a native family's `relation_rules` can name another concept family or a
  controlled vocabulary that does not exist (a rename or typo leaves a dangling
  reference), and no gate notices.

[ADR-009](adr-009-normative-artifact-authority-and-repository-structure.md) /
[ADR-019](adr-019-normative-authority-boundary-manifest.md) already make the
*authority-boundary* machine-checkable (`tools/check_authority_boundary.py`):
which repository roots bear authority, and that every authority family is named
in the immutable ADR pair. That gate governs where authority lives; it does not
reach inside the concept-family catalog to check that each family is decided by
an ADR or that the catalog's internal cross-references resolve. Review finding
CA-6 (issue #496) records exactly this gap.

## Decision

Add one filesystem-only, deterministic `policy` gate —
`tools/check_concept_authority_governance.py`, wired into the `policy` nox
session beside `check_authority_boundary.py` — that enforces concept-authority
catalog governance over the existing catalog. It introduces no new
concept-authority schema, registry, nox session, or runtime validation path, and
derives family and vocabulary identity from the authoritative catalogs and their
existing Pydantic models (`ConceptFamilyCatalogModel`,
`ControlledVocabularyCatalogModel`) rather than from a hard-coded id list.

### 1. ADR linkage is governance proof

Every family id in `concept-families-v1.json` must appear as a **whole token** in
at least one ADR under `docs/decisions/adrs/`. The match is word-boundary
(reusing the `check_authority_boundary.py` precedent), so `prosecution` cannot
satisfy `prose` and a hyphenated id matches only as a complete token.
Specifications, explanatory docs, preflight notes, fixtures, and tests do **not**
satisfy ADR linkage — only ADRs do. Adding a new concept family therefore
requires one catalog entry **and** at least one ADR that names it.

### 2. Catalog cross-references use an explicit token convention

A cross-reference from a family's `relation_rules` to another concept family or
to a controlled vocabulary is written as an **inline-code (Markdown backtick)
token** — `` `runtime-inventory` ``, `` `processor-features` `` — and the gate
validates only those explicit tokens, never bare prose words. Each inline-code
token shaped like a concept identifier
(`^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, the `ConceptFamilyId` grammar) must resolve to
a known concept family (`concept-families-v1.json`) or controlled vocabulary
(`controlled-vocabularies-v1.json`); a token that resolves to neither is a
dangling reference and fails the gate. Inline-code spans that are not
identifier-shaped — field names (`concept_bindings`), model names
(`RuntimeConfiguration`), instance paths (`nodes.*.runtime`) — are not references
and are ignored. Reference validation is deterministic and does not infer
references from natural-language prose.

### 3. Governed concept-family set

The canonical concept-family identifiers under this gate's governance are:
`assets`, `identities`, `relationships`, `observables`, `actions-and-events`,
`tools-and-artifacts`, `scenarios`, `tasks-runs-studies`, `episodes`,
`runtime-inventory`, `apparatus-declarations`, `realization-and-disclosure`,
`provenance-and-evidence`, and `time-and-apparatus`. Enumerating them here
records their ADR linkage and documents the gate's domain; the catalog remains
the authority for which families exist, and a family added later must earn its
own ADR mention (this accepted ADR is immutable and cannot be the home for a
future family).

This gate operationalises GOV-918 (cross-artifact concept binding — references
bind to canonical concepts that exist) and GOV-919 (extension discipline for
adding new concepts). It does not change concept-binding, semantic-profile,
reference-model, or UCO-alignment semantics.

## Alternatives Considered

- **Amend ADR-012 to spell the canonical hyphenated family ids.** Rejected:
  ADR-012 is accepted and immutable under
  [ADR-059](adr-059-adr-amendment-policy-and-pin-gate.md), and amending an ADR
  solely to satisfy a new gate's initial green state is the wrong shape. A
  dedicated governance ADR that enumerates the governed set is the honest home
  for the linkage and for the gate decision.
- **Add a structured `governed_vocabularies` (or similar) field to family
  entries.** Rejected: adding a structured reference field to a published
  catalog is a schema-evolution change subject to
  [ADR-061](adr-061-published-schema-evolution-policy.md), the schema
  publication manifest, and the generated-schema gate. The inline-code prose
  convention carries machine-checkable references without changing the published
  schema.
- **Infer family/vocabulary references from `relation_rules` prose by matching
  any id-grammar-shaped word.** Rejected: natural-language inference is
  non-deterministic and false-positives on domain adjectives the prose uses
  (for example `cyber-domain`). The explicit inline-code convention makes "this
  token is a reference" an authoring decision, not a guess.

## Consequences

**Positive**

- The extension discipline ADR-012 §3 describes becomes mechanically enforced:
  a family with no deciding ADR, or a relation rule with a dangling reference,
  fails `nox -s policy`.
- The catalog and the ADR corpus cannot silently drift apart.
- The gate is filesystem-only and never calls Ground Control or the network, so
  it cannot become flaky in CI.

**Negative / costs**

- A new concept family now requires an ADR mention as well as a catalog entry —
  intended friction that keeps the architectural record honest.
- Machine-checkable catalog cross-references must adopt the inline-code token
  convention; bare-prose references are documentation only and are not validated.

**Risks**

- The gate validates only references that opt into the inline-code convention, so
  a bare-prose reference to a non-existent family is not caught. This is the
  deliberate trade for determinism; the convention is the seam future references
  use, and the authoritative catalogs remain the single source of family and
  vocabulary identity.
