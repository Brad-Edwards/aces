# ADR-093: RAES Rename and Compatibility Boundaries

## Status

superseded by ADR-096

## Date

2026-07-23

## Classification

Classification: FM2
Required artifacts: ADR, downstream migration note, removal/migration evidence, verification evidence
Waivers: none

## Context

The project is being adopted by international AI security researchers. At the
AI Security Workshop in Toronto, Canada, on July 23, 2026, the group decided to
rename the project to Reproducible Agentic Environments System (RAES) so the
project identity matches that research audience and the system's reproducible
agent-environment focus.

The work was originally developed as part of the Heron AI Security Fellowship
cohort project `agent-environments`, as a potential instantiation of that
project's RFCs. The previous ACES / ACES SDL naming therefore records project
history, but it is no longer the intended current project identity.

The repository contains many name-bearing surfaces: prose, package metadata,
Python import packages, CLI entry points, MCP server/tool names, generated and
published schemas, profile ids, examples, fixtures, workflow configuration,
GitHub/Sonar/release metadata, and historical decision records. A blind text
replacement would risk breaking consumers, corrupting historical records, and
moving governed contract identifiers without the existing compatibility and
schema-publication controls.

Existing decisions already define the relevant boundaries:

- ADR-009 and ADR-019 separate normative artifacts from reference
  implementations.
- ADR-010 and ADR-036 define package ownership and the compatibility-only
  legacy `aces.*` import layer.
- ADR-061 governs published JSON Schema identifiers and schema publication.
- ADR-075 and `specs/evolution/versioning-deprecation-and-migration.md` govern
  compatibility, deprecation, removal, and migration records across surfaces.

## Decision

Rename the canonical current project identity to Reproducible Agentic
Environments System (RAES). Current repository-owned prose and emitted
user-facing identifiers should prefer RAES, with the full name introduced on
first user-facing mention and RAES used thereafter.

The rename is a coordinated surface migration, not a mechanical search and
replace. Each name-bearing occurrence must be classified by surface ownership
before it is changed:

- current-state prose and documentation;
- source API and import paths;
- distribution and package metadata;
- CLI command and MCP server/tool surfaces;
- published contracts, profile ids, schema annotations, and fixture data;
- generated artifacts;
- workflow, release, CI, and quality-service metadata;
- removed legacy public aliases; or
- historical/external records.

Remaining ACES references are intentional only when they are historical
records, external references, governed contract identifiers, workflow keys
owned by external automation, or migration documentation. Current source
imports and emitted identifiers use RAES.

Public command and MCP surfaces make a hard cut to RAES. The `aces` and
`aces-mcp` console scripts and the `aces_*` MCP tool aliases are removed instead
of retained as compatibility aliases. The Python distribution surface moves to
`raes` for new PyPI publication.

Legacy `aces.*`, `aces_sdl`, and `aces_*` Python import packages are removed by
the package-boundary hard cut. No aliases, wrappers, import hooks, or fallback
imports are provided. Do not add a central runtime rename service, universal
identifier registry, persistence table, API endpoint, or cross-package
exception hierarchy for the rename.

Published schema and contract identifiers remain governed by ADR-061 and the
schema-publication manifest. If a contract id, schema `$id`, profile id, or
wire discriminator changes from ACES to RAES, the change must carry the
required manifest metadata, compatibility/deprecation record, fixture/test
evidence, and generated-schema parity proof. A generator edit alone is not a
contract rename.

Historical accepted ADRs, changelog history, citations, external URLs, issue
records, and third-party references should not be rewritten just to erase the
old name. If current guidance inside an accepted ADR needs to change, use the
ADR-059 amendment or supersession process.

## Alternatives Considered

Rename documentation only. Rejected: it would leave package metadata, CLI/MCP
surfaces, contracts, examples, fixtures, and generated artifacts contradicting
the new project identity.

Blind repository-wide replacement. Rejected: it would break compatibility
source imports, historical records, contract/profile ids, external URLs,
generated outputs, release metadata, and fixtures that intentionally preserve
previous identifiers.

Create a central rename/alias registry. Rejected: the repository already has
surface-specific authorities and compatibility mechanisms. A central registry
would blur package, schema, CLI, MCP, workflow, and documentation ownership.

Remove all ACES identifiers immediately. Rejected: import paths, published
schema/profile ids, corpus artifacts, historical records, and
environment/config keys have different owning authorities. Issue #866 removes
old public command, MCP, distribution, and guidance names now, while leaving
source-module and governed-contract migrations to their own evidence-backed
work.

## Consequences

RAES becomes the canonical current project identity while preserving the
project's Heron Fellowship and ACES provenance as history.

The implementation must ship with a downstream migration note that maps old
ACES names to new RAES names by surface and states which names are removed,
migrated, retained as source/contract identifiers, external, or historical.

The rename is intentionally breaking on the public command, MCP, guidance, and
Python distribution surfaces. Remaining compatibility claims must name the
surface, direction, dimension, version or lineage, and verification evidence as
required by the ecosystem evolution policy.

The migration will touch generated artifacts only through their source-of-truth
tooling. Hand-edited generated output is not evidence that the owning surface
was migrated.

The rename does not change SDL semantics, runtime semantics, contract meaning,
security policy, or authority boundaries by itself. Any semantic change must
land under its own owning ADR/spec/contract process.

## Amendments

| Date | Commit/PR | Summary |
|---|---|---|
| 2026-07-24 | #866 | Revised the decision from compatibility-preserving rename boundaries to a hard cutover for public command, MCP, guidance, and Python distribution surfaces after implementation clarification. |
| 2026-07-25 | #866-pypi-name-correction | Corrected the RAES PyPI distribution target to the `raes` project name and removed the erroneous suffix-bearing slug from current emitted surfaces. |
| 2026-07-25 | #884 | MOD-884 supersedes the retained `aces_sdl` source-import boundary: top-level `raes` becomes the only SDL import namespace, with no compatibility alias or shim. |
| 2026-07-25 | #894 | Completed the hard cut across every owning Python package: `aces`, `aces_sdl`, and all `aces_*` import namespaces are removed without aliases, wrappers, import hooks, or fallbacks. |
