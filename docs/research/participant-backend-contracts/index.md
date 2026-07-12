# Participant Backend-Facing Contracts Research

Issue: #76, covering API-405, API-406, API-407, API-408, and API-411.

Purpose: gather and analyze the design basis for the joint backend-facing
participant contract surface before writing the ADR, formal spec sections, and
normative schema set. The five requirements form one contract surface: API-406
defines the plain-data shapes, API-405 and API-407 declare backend support for
them, API-408 retrieves what API-406 serializes, and API-411 reports outcomes
against API-406 state shapes.

## Relationship To Prior Research

The primary-literature basis for participant semantics and participant runtime
behavior was gathered for issues #71 and #74 and is recorded, with full
citations, in:

- `specs/formal/participant-semantics/README.md` (primary-source review,
  including the knowledge/information-flow, action-language, partial
  observability, and time/ordering/causality families)
- `specs/formal/participant-runtime/README.md` (source alignment and primary
  reference surface)
- `docs/explain/sdl/lineage.md` (source map)

These notes do not repeat that review. They cover the question specific to
issue #76: how the established semantics should be carried as portable
plain-data contracts, what the prior art does for the same problem, and what
design criteria follow.

```{toctree}
:hidden:

prior-art-and-design-criteria
preflight-guardrails
```

## Contents

- [Prior art and design criteria](prior-art-and-design-criteria.md) — how
  adjacent systems serialize participant actions, observations, state,
  histories, capability declarations, retrieval surfaces, and outcomes; the
  formal analysis of contract-surface totality; and the numbered design
  criteria the ADR must satisfy.
- [Architecture preflight guardrails](preflight-guardrails.md) — repo-wide
  implementation guardrails, required incumbents, cross-cutting gates, extension
  boundaries, non-goals, and anti-patterns to keep the later ADR and schema
  work aligned with existing authority and runtime surfaces.

## Standing Constraints

- ADR-009: schemas, fixtures, and conformance profiles are authoritative;
  reference implementations are consumers. Schemas under `contracts/schemas/`
  are generated from contract models; generator inputs change, generated
  output is never hand-edited.
- ADR-012: external concept authority plus disciplined ACES-native extension;
  controlled vocabularies are governed surfaces.
- ADR-022 / ADR-054: the participant semantics and runtime models whose
  objects these contracts serialize. The contracts must not weaken, fork, or
  reinterpret those semantics.
- ADR-041: participant implementation manifest/provenance already covers the
  apparatus identity surface; the backend-facing contracts here must compose
  with it, not duplicate it.
- API-405 is already ACTIVE (PR #405): `backend-manifest/v2`
  `capabilities.participant_runtime` with governed role/feature vocabularies
  and term-level evidence criteria. The joint design ratifies that surface and
  extends it for API-407 rather than redesigning it.
