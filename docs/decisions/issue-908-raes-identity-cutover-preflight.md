# Issue 908 RAES Identity Cutover Preflight

Date: 2026-07-26

Issue: #908. Requirement: GOV-944.

## Binding Scope

RAES is the only identity for current repository-owned surfaces. The cutover
covers published contracts, schemas, wire values, source identifiers, runtime
artifacts, environment and workflow inputs, host-visible names, current design
guidance, tools, examples, and configuration.

The cutover is semantic rather than lexical. Each occurrence is migrated
through its owning boundary. No compatibility alias, fallback read, dual-name
parser, redirect, wrapper, or runtime rename service remains.

Historical retention is limited to an exact record whose purpose is to
preserve an immutable or dated fact. Accepted pre-cutover ADR content, release
history, provenance records, and dated research or design evidence qualify
only when their exact path, content digest, record class, rationale, and
occurrence count are registered in the historical-record manifest. Directory
exemptions, globs, generated-file exclusions, and general policy waivers do
not qualify.

ADR-096 is the terminal architecture authority. ADR-093 becomes a superseded
historical decision after ADR-096 is accepted.

## Surface Decisions

| Surface | Cutover decision | Owning authority |
|---|---|---|
| Published schema URI root | Use `https://raes.dev/schemas/` | ADR-061, schema bundle, publication records |
| Contract and profile identifiers | Rename in their current draft lineages and record removal/replacement evidence | Normative schemas, publication entries, fixtures |
| Extension keywords and wire properties | Rename atomically with models, validators, schemas, fixtures, and consumers | Closed DTO and schema owners |
| Authentication headers | Expose only the RAES header family | `ControlPlaneSecurityConfig` and runtime API |
| Participant and runtime vocabulary | Rename schema names, statuses, event values, and artifact identifiers together | Runtime DTOs, specs, fixtures |
| Module artifacts | Rename lockfile, trust policy, cache, media type, and OCI annotation values | Module registry |
| Host ownership | Rename OCI labels, libvirt prefixes, guest markers, paths, and ownership namespace | Backend drivers and guest appliance |
| Environment and workflow inputs | Rename repository-owned keys in policy, CI, tests, and guidance together | Requirement governance and real-libvirt certification |
| Source and prose | Use RAES in identifiers, comments, docstrings, current docs, tools, skills, and examples | Owning package or document |
| Historical evidence | Preserve only exact content-bound records | Historical-record manifest and owning immutability controls |

## Canonical Incumbents

- Contract shape and generation:
  `raes_contracts._base.ContractModel`, `raes._base.SDLModel`,
  `schema_bundle()`, `tools/generate_contract_schemas.py`, and
  `tools/check_generated_schemas.py`.
- Publication:
  `contracts/schema-publication-manifest.json`, entries and tombstones under
  `contracts/schema-publication/`, and
  `tools/check_schema_publication.py`.
- Contract lifecycle:
  ADR-061, ADR-075,
  `specs/evolution/versioning-deprecation-and-migration.md`, and
  `specs/evolution/deprecation-records.yaml`.
- Semantic annotations:
  `schema_constraints.py`, `schema_invariants.py`, and the published RAES
  semantic-invariant profile.
- Security:
  `ControlPlaneSecurityConfig.strict_defaults()`, closed request models,
  request-size guards, role checks, denial audit events, and redacted error
  envelopes.
- Module security:
  closed trust and lockfile models, safe YAML/JSON loading, digest and
  signature verification, bounded registry reads, and safe archive extraction.
- Host boundaries:
  `provider_resource_name()`, OCI ownership inspection, libvirt ownership UUID
  checks, structured XML construction, fixed argv, bounded timeouts, and
  ownership-confined teardown.
- Workflow:
  `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `.github/workflows/ci.yml`, repository policy, requirement governance,
  schema/publication gates, gitleaks, and private-key detection.

## Cross-Cutting Requirements

### Contracts and persistence

Change reference-model sources before generated schemas. Regenerate the
published tree and update every publication entry with its current canonical
hash and contract-facing `last_change` record. A renamed schema path is a
removal plus replacement and carries a tombstone even though runtime
compatibility is intentionally absent.

Lockfiles, trust policies, runtime snapshots, evidence artifacts, OCI labels,
libvirt names, and guest paths are breaking persistence or host boundaries.
The repository does not silently rewrite existing host state or accept an old
artifact as a fallback.

### Authentication and errors

Trusted-proxy headers change through the existing security configuration.
Strict defaults, proxy trust, authentication, role checks, request-size
limits, conflict rejection, denial auditing, and redacted failures remain
unchanged. No request accepts both identity families.

Renamed validation failures continue through existing Pydantic, SDL, CLI, MCP,
runtime diagnostic, and HTTP error envelopes. No rename-specific exception
hierarchy or raw payload logging is introduced.

### Secrets and operating-system exposure

The cutover needs no credential, token, private key, environment dump, or real
payload. Connection URIs may contain credentials and therefore remain absent
from logs and evidence.

Guest writer and parser changes land together. Fixed argv, no-shell execution,
bounded reads, timeouts, safe path handling, archive containment, file modes,
redaction, and resource ownership checks remain intact.

### Whole-tree verification

The naming gate enumerates Git-tracked files directly and scans bytes so
hidden, generated, and non-text artifacts cannot evade it. A token-aware
matcher prevents incidental substrings from becoming false positives.

Historical entries are exact and content-bound. A content or occurrence-count
change invalidates the entry. The gate does not consume
`tools/policy/exceptions.yaml`.

## External Identity Preconditions

The repository targets these final identities:

- schema namespace: `https://raes.dev/schemas/`
- Sonar project: the existing pre-cutover service-owned key, retained as an
  exact operational designation
- Ground Control project: `raes-sdl`

Replacement remote resources must exist before the corresponding repository
configuration points to them. OBL-908-REMOTE-IDENTITIES-1 records that
provisioning dependency; the retained Sonar project does not require a
replacement resource.

## Non-Goals

- changing SDL, runtime, authorization, validation, or evidence semantics
  beyond identity-bearing values
- accepting old and new names together
- adding automatic host cleanup or data conversion
- creating a central identity registry, migration service, persistence store,
  endpoint, or exception family
- editing historical records merely to reduce an occurrence count
