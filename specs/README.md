# Specs

`specs/` is the home for normative prose under the
[RAES SDL authority boundary](authority/authority-boundary.yaml). Every
document under this directory is authoritative independent of any reference
implementation or code-generation pipeline.

## Authority Manifest

The canonical machine-readable manifest of which roots carry which authority
lives at:

- [`specs/authority/authority-boundary.yaml`](authority/authority-boundary.yaml)
  — canonical authority manifest (ASR-517)

The decisions that govern this manifest:

- [ADR-009](../docs/decisions/adrs/adr-009-normative-artifact-authority-and-repository-structure.md)
  — the authority decision (immutable)
- [ADR-019](../docs/decisions/adrs/adr-019-normative-authority-boundary-manifest.md)
  — the canonical-seam decision that governs the manifest YAML

Drift between the YAML, ADR-009, ADR-019, and this README is guarded by
[`tools/check_authority_boundary.py`](../tools/check_authority_boundary.py),
which runs in `nox -s policy` (and therefore in `verify` and the pre-push
hook).

## Subdirectories

- `authority/` — the canonical authority-boundary manifest
- `agent-guidance/` — the agent-usable governance-guidance profile
  (AUT-811). It is machine-readable rather than prose, so the manifest
  classifies `agent-guidance.yaml` as a `governance-guidance` artifact via
  the `normative_artifact_families` block (see
  [`authority/README.md`](authority/README.md)) rather than the default
  `prose` family of the `specs/` root.
- `concept-authority/` — concept-family and controlled-vocabulary
  authority artifacts (governed by ADR-012)
- `evolution/` — ecosystem versioning, deprecation, removal, and migration
  governance for GOV-901, GOV-902, and GOV-903 (governed by ADR-075)
- `sdl/` — the language-neutral normative SDL authoring specification
  (the catalog set the published `contracts/schemas/sdl/` schemas must
  agree with; governed by ADR-001 and ADR-009)
- `formal/` — optional formal-methods artifacts for semantic and
  stateful subsystems (governed by ADR-007 and ADR-018), including the
  behavioral-relation taxonomy and claim discipline governed by ADR-081
- `supply-chain/` — normative prose for the Packaging & Supply Chain
  wave, including reusable-asset trust/authenticity/integrity, associated
  artifact manifests, and portable artifact requirement satisfaction
  (governed by ADR-071, ADR-077, and ADR-098)
Revision-pinned lineage and derivation records live under the normative
`contracts/provenance/` authority registered by ADR-019; explanatory lineage
pages consume that record rather than defining a parallel source registry.
