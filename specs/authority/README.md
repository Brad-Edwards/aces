# Authority Boundary

This directory contains the canonical machine-readable manifest of the
normative-artifact authority boundary that
[ADR-009](../../docs/decisions/adrs/adr-009-normative-artifact-authority-and-repository-structure.md)
decided in prose.

## Files

- [`authority-boundary.yaml`](authority-boundary.yaml) — canonical manifest
  for ASR-517. Enumerates each normative authority root (`specs/`,
  `contracts/schemas/`, `contracts/fixtures/`, `contracts/profiles/`,
  `contracts/concept-authority/`), each non-normative root
  (`implementations/`, `docs/`, `examples/`, `research/`, `notes/`,
  `tools/`), the legacy top-level directories ADR-009
  transitioned out (`schemas/`, `conformance/`, `src/`), the
  schema-authority direction (no published schema may live under
  `implementations/`), and the `normative_artifact_families` block described
  below.

## Artifact-family classification

`authority_roots` classify whole directory trees, and `specs/` carries the
default family `prose`. Some artifacts under a normative root are not prose —
the agent-usable guidance profile (`specs/agent-guidance/agent-guidance.yaml`,
AUT-811) is machine-readable governance guidance, not a prose specification.
The `normative_artifact_families` block classifies such artifacts explicitly:
each entry pins one artifact path to a distinct authority `family` (for
agent-guidance, `governance-guidance`) so the artifact's authority class is
decidable from the manifest alone. Such a classified, governed scope is a
**surface** in the
[concept-authority](../concept-authority/concept-authority.md) sense.

The classification follows a **most-specific rule**: an artifact path is
strictly more specific than any root prefix, so an explicit
`normative_artifact_families[].artifact` entry classifies that exact file and
the containing root supplies the default family for every other artifact. The
next governed non-prose artifact is classified by adding one entry here plus a
focused test in
[`test_authority_boundary.py`](../../implementations/python/tests/test_authority_boundary.py);
no parallel list lives anywhere else in the repo.
`tools/check_authority_boundary.py` validates each entry's shape, that the
artifact exists under a normative authority root, and pins the canonical
agent-guidance binding against silent drift.

## Governance

- [ADR-009](../../docs/decisions/adrs/adr-009-normative-artifact-authority-and-repository-structure.md)
  — authority decision (immutable)
- [ADR-019](../../docs/decisions/adrs/adr-019-normative-authority-boundary-manifest.md)
  — canonical-seam decision that governs the YAML
- [`tools/check_authority_boundary.py`](../../tools/check_authority_boundary.py)
  — structural gate; wired into `nox -s policy`
- [`docs/explain/reference/normative-artifact-authority.md`](../../docs/explain/reference/normative-artifact-authority.md)
  — contributor-facing guardrails note
