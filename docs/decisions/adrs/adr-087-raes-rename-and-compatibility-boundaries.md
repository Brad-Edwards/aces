# ADR-087: RAES Rename and Compatibility Boundaries

## Status

accepted

## Date

2026-07-23

## Classification

Classification: FM2
Required artifacts: ADR, downstream migration note, compatibility/deprecation records, verification evidence
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
- compatibility aliases; or
- historical/external records.

Remaining ACES references are intentional only when they are historical
records, external references, compatibility aliases, or migration
documentation. Current emitted identifiers should use RAES by default once the
owning surface is migrated.

Compatibility stays at the owning boundary. Legacy `aces.*` imports remain in
the existing compatibility tree unless a future removal record says otherwise.
CLI aliases, MCP tool aliases, schema/profile-id aliases, environment/config
aliases, and package/distribution aliases must be handled by their owning
surface and documented in the downstream migration note. Do not add a central
runtime rename service, universal identifier registry, persistence table, API
endpoint, or cross-package exception hierarchy for the rename.

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
aliases, historical records, contract/profile ids, external URLs, generated
outputs, release metadata, and fixtures that intentionally preserve previous
identifiers.

Create a central rename/alias registry. Rejected: the repository already has
surface-specific authorities and compatibility mechanisms. A central registry
would blur package, schema, CLI, MCP, workflow, and documentation ownership.

Remove all ACES identifiers immediately. Rejected: downstream users may depend
on import paths, package names, CLI commands, MCP tool names, schema/profile
ids, corpus artifacts, and environment/config keys. Removal requires explicit
deprecation/removal records and evidence under the existing governance policy.

## Consequences

RAES becomes the canonical current project identity while preserving the
project's Heron Fellowship and ACES provenance as history.

The implementation must ship with a downstream migration note that maps old
ACES names to new RAES names by surface and states which aliases remain
supported, deprecated, removed, or historical.

The rename may be breaking on some surfaces. Compatibility claims must name the
surface, direction, dimension, version or lineage, and verification evidence as
required by the ecosystem evolution policy.

The migration will touch generated artifacts only through their source-of-truth
tooling. Hand-edited generated output is not evidence that the owning surface
was migrated.

The rename does not change SDL semantics, runtime semantics, contract meaning,
security policy, or authority boundaries by itself. Any semantic change must
land under its own owning ADR/spec/contract process.
