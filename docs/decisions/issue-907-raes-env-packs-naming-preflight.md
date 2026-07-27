# Issue 907 RAES and Environment-Packs Naming Preflight

Date: 2026-07-27

Issue: #907. Requirement: none. The GitHub issue is the authoritative delivery
contract.

This note fixes the architecture boundaries for implementation. It does not
publish a package, mutate a PyPI project, define a downstream pack format, or
add a compatibility mode.

## Base-Synchronization Correction

The first preflight pass occurred before PR #921 merged. That merge completed
issue #908 / GOV-944 and accepted ADR-096, which supersedes the earlier
assumption that current ACES-bearing contract and wire identifiers would remain
unchanged. The implementation for issue #907 treats the merged identity
cutover as authoritative.

The resulting downstream sequence is release-bounded:

1. Consumers pinned to RAES 1.1.0 continue to use that release's ACES-bearing
   contract, schema, wire, workflow, runtime, and host values.
2. Consumers migrate those values atomically when adopting the next breaking
   RAES release containing PR #921, targeted as 2.0.0.
3. Consumers do not guess `raes-*` translations, combine values from both
   release lines, or add aliases, fallback reads, and last-one-wins rules.

The release's normative schemas, fixtures, and migration evidence define the
new values. This note records sequencing; it does not create a second identity
inventory.

Ground Control's project identifier is an external service-owned operational
binding, not a repository-owned product identity. The service currently exposes
only its pre-cutover project record. ADR-096 requires replacement provisioning
before repository configuration points to a new external identifier, so the
existing logical binding remains registered as an exact content-bound
operational binding until that provisioning occurs. This is the same bounded
class of exception as the retained SonarCloud project key; it does not authorize
a runtime alias or a general naming fallback.

## Architecture Decisions

### Scenario remains the SDL term; environment pack is a packaging term

`Scenario` remains the RAES SDL authored-content concept, and
`instantiate_scenario()` remains the operation that binds its variables into an
instantiated scenario. The normative SDL document phases and contract names
continue to use *scenario*.

An **environment pack** is a downstream packaging and distribution unit. It may
contain SDL scenarios and other reusable assets. It is not:

- an alias or replacement for `Scenario`;
- a new SDL document phase, schema, model, parser entry point, or validator;
- equivalent to an agentic environment or realized environment; or
- authority to restate upstream scenario, concept, or trust-policy semantics.

The downstream pack owner may define pack layout and release mechanics. This
repository remains the authority for the contained SDL and governed contract
meanings.

### Retire the `aces-sdl` PyPI project with a final pointer and archival

The `aces-sdl` PyPI project is end-of-life. Its replacement is `raes`; migration
is directly to RAES imports and commands. No removed import shim or compatibility
package is restored.

Close the old project with one final 0.23.2 legacy-line release whose code
behavior is unchanged from 0.23.1 and whose distribution metadata and long
description state that:

- the project is retired and receives no further fixes;
- `raes` is the replacement distribution;
- old imports do not carry forward; and
- consumers must follow `docs/migration/raes-rename.md`.

The EOL release must not depend on `raes`, provide aliases, or install an empty
placeholder. After its metadata and artifacts are verified on PyPI, archive the
project. Do not delete or broadly yank historical releases.

The current release path remains exclusively for `raes`. The one-time legacy
publication is a separate protected action: it must build from immutable
reviewed source, use the protected PyPI environment and short-lived OIDC
credentials, and retain no token. Issue #907 records this decision but does not
authorize the upload or archival action.

## Canonical Incumbents To Reuse

- **Identity cutover:** ADR-096,
  `docs/decisions/issue-908-raes-identity-cutover-preflight.md`,
  `docs/migration/raes-rename.md`, `tools/check_identity_cutover.py`, and
  `tools/policy/historical_identity_records.json`.
- **Normative authority and contract evolution:** ADR-009, ADR-019, ADR-061,
  `contracts/schema-publication-manifest.json`,
  `contracts/schema-publication/entries/`, `schema_bundle()`,
  `tools/check_schema_publication.py`, and
  `tools/check_generated_schemas.py`.
- **Compatibility and lifecycle:** ADR-075,
  `specs/evolution/versioning-deprecation-and-migration.md`,
  `specs/evolution/deprecation-records.yaml`, and
  `tools/check_deprecation_lifecycle.py`.
- **SDL vocabulary and phases:** ADR-001, `specs/sdl/`,
  `docs/explain/reference/glossary.md`, `raes.scenario.Scenario`,
  `raes.instantiate.instantiate_scenario`, parser and semantic validators, and
  the authored and instantiated schemas and fixtures.
- **Concept and reusable-asset authority:** ADR-012, ADR-062, ADR-071,
  `specs/concept-authority/`, `contracts/concept-authority/`, and
  `specs/supply-chain/reusable-asset-trust-integrity.md`. Environment packs
  consume these surfaces; they do not clone them.
- **Release and verification:** release-please configuration,
  `.github/workflows/release-please.yml`, the pinned PyPI publish action,
  protected `pypi` environment, OIDC trusted publishing, ADR-014,
  `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, and `tools/verify_all.py`.

## Cross-Cutting Boundaries

| Layer | Required behavior |
|---|---|
| Contracts and schemas | PR #921 remains the sole identity-cutover implementation. Issue #907 adds sequencing guidance, not aliases, schema edits, or a parallel identifier inventory. |
| SDL parse and instantiation | `Scenario` and `instantiate_scenario()` remain canonical. Pack metadata does not enter an SDL model merely because a pack contains SDL. |
| Concept and trust policy | Environment packs reference the upstream authorities and validators. They do not copy schemas or create a pack-local trust model. |
| Authentication and authorization | No runtime auth surface changes. Existing strict defaults and denial behavior remain in force. |
| Secrets and publication | No credential is added to source, docs, fixtures, logs, environment dumps, or process arguments. The future protected publication uses short-lived OIDC. |
| Persistence and host state | No read-time rewrite, cleanup service, or migration store is introduced. Operators migrate persisted values and resources at the breaking-release boundary. |
| Historical evidence | This dated correction retains exact pre-cutover naming only through ADR-096's content-bound historical-record manifest. |
| Lifecycle evidence | The legacy distribution name remains readable only in its exact content-bound ADR-075 lifecycle record; code and tests use the neutral record id `legacy-python-distribution`. |

## Extensibility Seams

- A future contract change extends its owning schema-publication entry,
  fixtures, validators, compatibility record, and versioned reader boundary.
- A future pack format extends the downstream pack manifest and containment
  references; it does not extend `Scenario` with package metadata.
- A future distribution retirement adds an exact `python-distribution`
  lifecycle record. It does not make the RAES publisher accept an arbitrary
  project name.

## Non-Goals And Anti-Patterns

- No additional contract, schema, profile, discriminator, URI, auth header,
  workflow key, host identifier, or persisted artifact rename.
- No SDL model/API rename and no `EnvironmentPack` model in this repository.
- No compatibility shim, alias registry, automatic source migrator, generic
  rename service, new exception hierarchy, or migration database.
- No downstream pack implementation.
- No package publication, PyPI project mutation, or release-workflow change.
- No mixed old/new identity handling, global replacement, copied authority,
  stored publication token, or deletion of sound historical releases.
