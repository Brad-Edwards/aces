# Versioning, Deprecation, and Migration Governance

This specification is normative for ACES ecosystem evolution policy. It
implements the joint design surface for GOV-901, GOV-902, and GOV-903.

## Scope

This policy governs versioning, compatibility claims, deprecation records,
removal eligibility, and migration guidance for repository-governed ecosystem
surfaces.

It does not create a universal runtime version registry, cross-package
migration service, API endpoint, database table, or exception hierarchy. Each
surface remains owned by its existing authority, checker, schema, validator,
or adapter boundary.

## Terms

**Version identifier** means a surface-local value that identifies a release,
lineage, payload shape, source artifact, or domain artifact.

**Producer** means the surface that writes, publishes, emits, or serves an
artifact.

**Consumer** means the surface that reads, imports, validates, executes, or
otherwise depends on the artifact.

**Backward compatibility** means a newer consumer accepts and preserves the
meaning of older producer output for the named surface and dimension.

**Forward compatibility** means an older consumer accepts and safely handles
newer producer output for the named surface and dimension.

**Full compatibility** means both backward and forward compatibility hold for
the named surface and dimension.

**Structural acceptance** means the consumer accepts the artifact's syntactic
or schema shape.

**Semantic equivalence** means accepted input preserves the same ACES meaning.

**Behavioral compatibility** means runtime, CLI, API, validation, or
conformance behavior remains within the documented contract.

**Operational interoperability** means independently released components can
work together under documented admission, capability, and deployment rules.

## Surface-Class Matrix

Each surface class owns its version meaning and compatibility rule.

| Surface class | Authority | Identifier syntax | Compatibility relation | Lifecycle record | Migration evidence |
|---|---|---|---|---|---|
| Python distribution | `implementations/python/pyproject.toml`, release-please config, Git tag, PyPI artifact | SemVer package version and matching `vX.Y.Z` tag | Consumer code imports installed package APIs for the documented release | Release PR, GitHub Release, generated `CHANGELOG.md` | Release notes and package/API docs |
| Published JSON Schema | ADR-061, `contracts/schema-publication-manifest.json`, and `contracts/schema-publication/` | Contract id such as `backend-manifest-v2`; wire discriminator such as `backend-manifest/v2` | Schema lineage and stability-specific structural compatibility | Per-contract `stability` and `last_change` records; independent removal tombstones | Schema diff, fixtures, checker output, and contract docs |
| Closed contract DTO and wire envelope | `aces_contracts.versions`, contract models, manifest authority | Exact discriminator such as `workflow-step-state/v1` | Exact payload-shape selection by owning reader | Contract ADR/spec and release notes | Reader validation tests and conformance fixtures |
| Processor/backend support declaration | Manifest models and manifest authority allowlists | Exact governed contract ids, not version ranges | Declared support for named counterpart contract ids | Manifest contract lineage and conformance result | Manifest update, fixture, and conformance report |
| Apparatus or implementation identity | Processor, backend, and participant manifests | Product/component identity version string | Operational interoperability declared by manifest capability blocks | Manifest release and conformance profile | Backend/processor/participant conformance evidence |
| SDL scenario and module | SDL spec, module registry, lockfile, trust policy | Scenario/module version and import version constraint | Import constraint satisfaction plus registry, digest, signature, and semantic validation | SDL/module documentation and release notes | Migration note or deterministic source rewrite |
| Experiment task, run, study, evidence, or domain artifact | Owning experiment-core spec and contract | Domain-specific artifact version | Domain semantic or provenance compatibility | Owning ADR/spec and contract lineage | Domain fixtures, replay/evidence checks, or migration note |
| ADR | ADR-000 and ADR-059 | ADR number plus status | Citable accepted content, not runtime compatibility | Status, pin, amendment row, or supersession | New ADR or recorded amendment |
| Ground Control requirement | Ground Control requirement graph | Requirement UID and status | Traceability/workflow state, not artifact compatibility | Requirement status and IMPLEMENTS/TESTS/DOCUMENTS links | Post-merge traceability reconciliation |

New surface classes extend this table and their owning checker or
documentation. They do not create a central runtime registry by default.

## Compatibility Claims

A compatibility claim is valid only when it names:

- the surface class;
- producer and consumer;
- direction: backward, forward, or full;
- dimension: structural, semantic, behavioral, or operational;
- version or lineage range under discussion; and
- verification evidence.

A bare statement that a change is "compatible" is incomplete.

Structural acceptance is not semantic compatibility. A JSON Schema accepting
an object does not prove the object preserves SDL meaning, conformance
behavior, or runtime interoperability.

For published JSON Schemas, ADR-061 remains authoritative. Optional properties,
enum additions, and looser constraints can be additive to schema structure, but
they are not automatically forward-compatible with older closed readers. A PR
claiming end-to-end compatibility for such a change must show reader evidence
or scope the claim to structural schema compatibility only.

Before the Python package reaches 1.0, release-please may classify breaking
changes as minor releases according to the repository's release configuration.
Consumers must not infer post-1.0 SemVer stability from a `0.y.z` package
release unless a specific surface policy states it.

## Deprecation

A deprecation is a lifecycle notice for a still-supported surface. It is not a
schema stability class, ADR status, requirement status, or semantic validation
error by itself.

A complete deprecation record names:

- exact surface and identifier;
- first release, contract lineage, or documentation version carrying the
  notice;
- replacement surface or explicit no-replacement rationale;
- migration reference;
- minimum notice window or removal eligibility rule;
- verification evidence that the old surface remains supported during the
  notice window; and
- security exception, if the ordinary notice window is shortened.

Deprecated-but-supported use must remain non-fatal. The owning channel may emit
a bounded notice, advisory, warning, release-note entry, or documentation
marker. Actual removal or unsupported use fails through the owning surface's
existing SDL, contract, CLI, conformance, or HTTP error envelope.

Security exceptions may shorten ordinary notice only when the record names the
affected versions, impact, mitigation, migration path, and review authority.
The word "security" is not a blanket bypass for unreviewed breaking changes.

Repository-governed deprecation records are recorded in
`specs/evolution/deprecation-records.yaml` and validated by
`tools/check_deprecation_lifecycle.py`, which fails closed on any record that
omits a required field. That ledger is the single reviewable surface for these
notices — a CI-time governance record, not a runtime lifecycle registry,
migration service, or endpoint — and each record cites its owning surface's
existing authority rather than replacing it. A record whose `status` is
`removed` on a published JSON Schema surface references the ADR-061
schema-publication tombstone record rather than duplicating it.

## Removal

Removal is allowed only after a complete deprecation record reaches its removal
eligibility rule, or under a documented security exception.

Published JSON Schema removal follows ADR-061 and must leave the required
manifest tombstone. Other surface removals use their owning evidence:
release notes, ADR/spec updates, fixtures, tests, conformance reports, or
diagnostics.

Removal must not silently reinterpret old input as new input. If a removed
surface appears, the owning reader fails with a bounded, surface-specific
message and, when available, points to the migration reference.

## Migration

Migration guidance is surface-specific and version-pair oriented. A migration
record names:

- source surface and version or lineage;
- target surface and version or lineage;
- transformation type: manual, assisted, or automated;
- data preservation rules;
- ambiguous or lossy cases;
- validation command or evidence; and
- rollback or no-rollback statement.

Human-readable migration notes belong under the existing documentation
boundary. Automated migrators are justified only for deterministic
transformations. They must be idempotent, preserve source data, report
ambiguous or lossy cases, and fail closed rather than drop unknown fields.

Compatibility adapters stay at the owning boundary:

- legacy `aces.*` re-exports stay in the compatibility tree;
- SDL normalization and module composition stay in `aces_sdl`;
- contract readers stay in `aces_contracts`;
- CLI presentation stays in `aces_cli`; and
- backend/runtime layers do not reinterpret authored source to hide migration
  needs.

## Verification

Changes governed by this policy use the repository's existing gates unless a
surface adds a more specific checker:

- release classification and version bump evidence: PR title guard,
  release-please config, release PR, Git tag, GitHub Release, and PyPI
  artifact;
- version-identifier derivation: the docs build, CLI `--version`, and
  control-plane OpenAPI description versions derive from the installed
  distribution metadata (the release-please-owned source of truth) and fall
  back to the honest PEP 440 `0.0.0+unknown` sentinel when the distribution is
  not installed, rather than a hard-coded literal that would imply an
  unearned release; verified by version-classification tests;
- published schema evolution: schema publication checker, generated-schema
  parity, fixture validation, manifest hashes, change ledger, and tombstones;
- ADR evolution: ADR index and accepted-content pin gate;
- deprecation and lifecycle records: `specs/evolution/deprecation-records.yaml`
  validated by `tools/check_deprecation_lifecycle.py` (complete-record contract,
  removal-eligibility, and — for published schemas — a required ADR-061
  `removed_schemas` tombstone reference);
- SDL/module evolution: parser, validator, module registry, lockfile, trust,
  signature, digest, and semantic tests;
- contract and manifest evolution: closed DTO validation, manifest authority,
  fixtures, profiles, and conformance checks; and
- repository completion: `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/verify_all.py`, and the
  canonical nox verification graph.

No secret, environment dump, credential, or private configuration is required
to validate this policy.
