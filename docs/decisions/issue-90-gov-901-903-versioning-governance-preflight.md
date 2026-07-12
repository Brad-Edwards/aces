# Issue 90 GOV-901/902/903 Versioning Governance Preflight

Date: 2026-07-11

Issue: #90. Spawned implementation issues: #240 (GOV-901), #241 (GOV-902),
and #242 (GOV-903). Branch anchor: GOV-901.

Requirement: none. The joint design issue is the authoritative contract.

This note records architecture guardrails for the joint versioning,
deprecation, and migration policy. It is implementation guidance only: it does
not create the policy ADR, normative governance specification, lifecycle
records, migrations, compatibility adapters, validators, release changes, or
published contract changes.

## Binding Sources

- ADR-009, ADR-019, and `specs/authority/authority-boundary.yaml` make prose
  under `specs/` normative and keep implementation code non-normative. The
  governance rules belong in a normative spec; an ADR should record the
  decision and rationale without duplicating the full rule set.
- ADR-061 and `contracts/schema-publication-manifest.json` already own
  published JSON Schema lineage, `draft`/`stable` classification, canonical
  hashes, change descriptions, removal tombstones, and the conservative
  stable-schema compatibility gate. The joint policy must compose with this
  authority rather than create a second schema registry or classifier.
- ADR-010 and `tools/policy/adr_policy.yaml` own the one-way `aces.*`
  compatibility layer and package ownership boundaries. Import compatibility
  is one governed surface, not the definition of ecosystem compatibility.
- ADR-053 and `aces_sdl.module_registry` own scenario/module version matching,
  lock identities, digest and signature checks, and import trust. Module
  versions are not package versions or contract lineage identifiers.
- ADR-014, `.ground-control.yaml`, `.gc/plan-rules.md`, and `noxfile.py` make
  `nox -s verify` the canonical verification graph.
- ADR-059, `docs/decisions/adrs/adr-index.yaml`, and
  `tools/check_adr_immutability.py` govern accepted ADR evolution. ADR-061 must
  not be silently edited to absorb the new policy.
- `docs/explain/releasing.md`, `.github/workflows/release-please.yml`,
  `release-please-config.json`, `.release-please-manifest.json`, and
  `implementations/python/pyproject.toml` are the current package-release
  workflow. Release-please, Conventional Commit PR titles, and the static
  project version are the canonical incumbents.
- `specs/sdl/diagnostics.md` defines the SDL error/advisory boundary.
  `SDLParseError`, `SDLValidationError`, `SDLInstantiationError`, shared
  `Diagnostic`, Typer errors, and bounded control-plane `HTTPException`
  responses are existing delivery envelopes; lifecycle policy must not create
  a universal exception hierarchy.

## Version Domains Must Stay Distinct

The joint policy must classify the existing version domains before it defines
compatibility. A common spelling does not give two fields common semantics.

| Surface | Canonical incumbent | Meaning and guardrail |
|---|---|---|
| Python distribution and Git tag | `pyproject.toml`, release-please manifest/config/workflow | One `X.Y.Z` package release and matching `vX.Y.Z` tag. Release-please owns bumps and `CHANGELOG.md`; feature work must not hand-edit either. |
| Published contract lineage | `contracts/schema-publication-manifest.json`, ADR-061, `contracts/schemas/` | Exact contract ids such as `backend-manifest-v2` and payload discriminators such as `backend-manifest/v2`. The major suffix identifies a lineage; it is not a package version or a stability promise. |
| State/envelope schema identity | `aces_contracts.versions` and closed contract models | Exact wire discriminator such as `workflow-step-state/v1`. It selects payload shape; it is not an apparatus or package release. |
| Processor/backend support declaration | `aces_contracts.manifest_authority` and manifest models | Despite the legacy field name `supported_contract_versions`, values are exact governed contract ids, not SemVer ranges. Do not reinterpret the field in place. |
| Apparatus identity | `ApparatusIdentity`, processor/backend/participant manifests | Product/component identity version. Current contracts require only a non-empty value and compatibility blocks name counterpart implementations; they do not establish version-range negotiation. |
| SDL scenario and module | `Scenario.version`, `ModuleDescriptor.version`, `ImportDecl.version`, module registry | Author/module release identity. Import matching uses `packaging` specifiers for parseable versions and exact-string fallback otherwise. `*` means unpinned. It does not select an SDL schema version. |
| Domain artifact versions | experiment task/run/study fields, behavior `semantic_version`, external vocabulary source versions | Version the owning domain assigns to the artifact or source. It remains governed by that domain and must not inherit package or schema bump rules accidentally. |
| Decision and requirement status | ADR status/pin gate and Ground Control requirement status | Governance workflow state, not consumer-facing artifact lifecycle. `deprecated` ADR status must not be reused as a contract deprecation record. |

The normative governance spec should carry one surface-class matrix that names
the identifier syntax, authority, compatibility relation, lifecycle evidence,
and migration evidence for each class. This is a documentation seam, not a new
runtime registry or universal `Version` model.

## GOV-901 Requirement-Surface Map

The six surface names in GOV-901 are requirement taxonomy, not six new runtime
types. Their repository authorities and compatibility evidence are:

| GOV-901 surface | Existing authority and validation boundary | Compatibility guardrail |
|---|---|---|
| Language | `specs/sdl/`, `contracts/schemas/sdl/`, the SDL catalog parity gate, `SDLModel`, parser, instantiator, and `SemanticValidator` | Distinguish raw `sdl-yaml/v1`, normalized authoring contracts, derived phase contracts, and author-assigned `Scenario.version`. Schema acceptance alone does not establish semantic preservation across phases. |
| Semantic | ADR-016, `docs/explain/reference/shared-semantic-integrity.md`, `specs/concept-authority/semantic-profiles.md`, semantic profiles, concept catalogs, semantic helpers, and cross-stage agreement tests | Compatibility is phase- and construct-family-specific. `profile_id`, `concept_catalog_version`, behavior-assumption ids, and domain `semantic_version` values are separate identifiers; none is a package or SDL schema version. |
| Processing | ADR-008, ADR-036, processor manifests, `aces_contracts.manifest_authority`, compiler/planner contracts, conformance profiles, and owning `aces_processor` tests | `supported_sdl_versions` and `supported_contract_versions` are exact governed contract ids. Processing compatibility requires declared capabilities plus validation, compilation/planning, and conformance evidence; apparatus identity versions do not create range negotiation. |
| Contract | ADR-061, `contracts/schema-publication-manifest.json`, published schemas, closed `ContractModel` DTOs, exact wire discriminators, fixtures, and schema/conformance gates | Keep lineage identity, schema stability, structural compatibility, reader compatibility, and lifecycle state distinct. The manifest checker is a conservative structural floor, not proof of semantic or operational compatibility. |
| Module | ADR-053, `Scenario.module`, `ImportDecl`, `ModuleDescriptor`, `aces_sdl.module_registry`, lockfiles, and trust policy | A constraint match is only version selection. Registry allowlisting, archive safety, signature, digest, export-hash, namespace rewriting, and whole-scenario semantic validation remain independent mandatory gates. |
| Experiment | ADR-055, ADR-064, ADR-065, ADR-068, ADR-074, experiment-core schemas/models, semantic invariants, fixtures, replay/evidence checks, and conformance evidence | Contract `schema_version` and task/run/study/capture/measure domain versions have different roles. Do not infer scientific replay, evidence, or apparatus compatibility from common `v1` lineage suffixes or the package release. |

The normative surface-class matrix may keep rows at the smallest authority that
has one identifier and comparison rule; it does not need one row merely because
the requirement uses one noun. It must, however, make every row above
traceable without inference. If a future change splits a surface into an
independently released family, that family gets its own matrix row and extends
its owning checker or conformance evidence rather than creating a parallel
ecosystem registry.

## Architecture Decisions And Guardrails

- Use one umbrella ADR for the cross-surface decisions and one normative
  governance specification under `specs/`. Keep rationale and rejected
  alternatives in the ADR; keep operational rules, terms, and the surface
  matrix in the spec. Explanatory release or migration docs may point to the
  spec but must not restate a competing policy.
- Treat versioning, deprecation, and migration as related but separate
  concepts. A version identifies an artifact or lineage; compatibility is a
  directional relation between a producer and consumer; deprecation is a
  lifecycle notice while a surface still works; migration is the documented or
  executable transition. None is a synonym for another.
- Define compatibility direction explicitly: backward (new reader accepts old
  producer output), forward (old reader accepts new producer output), and full
  compatibility where both hold. Name the producer, consumer, and compared
  surface. A bare claim that a change is "compatible" is insufficient.
- Separate structural acceptance, semantic equivalence, behavioral
  compatibility, and operational interoperability. Passing JSON Schema does
  not prove that meaning or runtime behavior is preserved; sharing a package
  version does not prove that two apparatus manifests interoperate.
- Keep stability and lifecycle orthogonal. ADR-061 `draft`/`stable` says how a
  schema may evolve; active/deprecated/removed says whether consumers should
  adopt it. Do not overload `stability`, JSON Schema's `deprecated` annotation,
  ADR status, or requirement status to carry all lifecycle meanings.
- Resolve ADR-061's additive-change assumption explicitly. The reference
  `ContractModel` and `SDLModel` are closed (`extra="forbid"`), and many enum
  fields are literals. An optional property or enum addition that is additive
  to a schema can still be rejected by an older installed reader. The joint
  policy must either state the compatible-reader assumption and its evidence or
  supersede/narrow the earlier claim; it must not silently call structural
  schema growth end-to-end backward compatible.
- Define pre-1.0 package behavior deliberately. Release-please demotes a major
  breaking bump to a minor release before 1.0. The policy must say what
  compatibility a `0.y.z` consumer may rely on and must not imply ordinary
  post-1.0 SemVer guarantees while automation follows a different rubric.
- Preserve the bundled-release fact: the Python code and contract corpus ship
  in one `aces-sdl` artifact. This gives a coordinated release unit but does not
  erase independent contract ids or make an older external processor/backend
  compatible with a newer corpus automatically.
- A deprecation record must identify the exact surface, first release or
  contract lineage carrying the notice, replacement, migration reference,
  removal eligibility rule, and any security exception. Notice without a
  supported replacement and migration path is not a complete deprecation.
- Removal must be explicit and evidence-backed. For published schemas, retain
  ADR-061 version-bump rules and manifest tombstones. For Python/API/CLI/SDL
  surfaces, use their existing release notes, tests, diagnostics, and
  compatibility seams. Do not encode every removal in the schema manifest.
- Security removals need a named exception path that can shorten ordinary
  notice while recording impact, affected versions, mitigation, and migration.
  "Security" must not become an unreviewed bypass for arbitrary breaking
  changes.
- Deprecation notices are non-fatal while the old surface remains supported.
  Actual removal or an unsupported version fails through the owning surface's
  existing error envelope. Do not turn a lifecycle notice into an SDL semantic
  error, or hide an invalid removed construct as a non-fatal advisory.
- Migration guidance must be version-pair and surface specific. Human-readable
  notes belong under the existing `docs/migration/` boundary; parser/CLI
  messages may link or point to them. An automated migrator is justified only
  for deterministic transformations and must be idempotent, preserve source
  data, report lossy/ambiguous cases, and fail closed rather than silently drop
  unknown fields.
- Compatibility adapters remain at the owning boundary: `aces.*` re-exports in
  the compatibility tree, SDL normalization/composition in `aces_sdl`, contract
  readers in `aces_contracts`, CLI presentation in `aces_cli`. Do not create a
  cross-package migration service or make runtime/backend layers reinterpret
  authored source.

## Required Incumbents

- Release and package identity:
  `.github/workflows/release-please.yml`, `release-please-config.json`,
  `.release-please-manifest.json`, `implementations/python/pyproject.toml`,
  installed-distribution metadata, `aces_cli.main --version`, and
  `docs/explain/releasing.md`.
- Release classification and audit trail: `tools/check_pr_title.py`,
  `.github/workflows/pr-title-lint.yml`, Conventional Commit squash titles,
  release-please's release PR, Git tag, GitHub Release, PyPI artifact, and
  generated `CHANGELOG.md`.
- Published contracts: ADR-009, ADR-061, `contracts/README.md`,
  `contracts/schema-publication-manifest.json`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`,
  `tools/check_json_artifacts.py`, `schema_bundle()`, and the existing valid and
  invalid fixture suites.
- Contract version vocabulary: `aces_contracts.versions`,
  `aces_contracts.manifest_authority`, closed `ContractModel` DTOs, processor,
  backend, participant implementation, control-plane, profile, and conformance
  models that consume those exact ids.
- SDL/module compatibility: `Scenario`, `ModuleDescriptor`, `ImportDecl`,
  `Lockfile`, `TrustPolicy`, `_satisfies_version()`, digest/signature/version
  gates, whole-scenario semantic validation, and module registry tests.
- Compatibility direction and ownership: ADR-010,
  `tools/policy/adr_policy.yaml`, `tools/policy/repo_policy.py`, owning packages
  under `implementations/python/packages/`, and wrapper-only
  `implementations/python/src/aces/`.
- Diagnostics and errors: `specs/sdl/diagnostics.md`, SDL error classes,
  `aces_contracts.diagnostics`, Typer's current user-facing errors,
  `ControlPlaneSecurityConfig.strict_defaults()`, bounded `HTTPException`
  details, audit records, and the redacted internal-error handler.
- Repository workflow: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/verify_all.py`, ADR index and
  immutability checks, docs build, and existing release/schema/manifest tests.

## Whole-Repo View

The intended design is repository governance, not a local schema edit. Its
scope includes:

- normative policy prose under `specs/` and the authority manifest that makes
  that prose binding;
- the policy ADR, ADR index, acceptance pin, and ADR-061 relationship;
- package version metadata, release-please configuration, PR title policy,
  release workflow permissions, Git tags, PyPI publication, and changelog;
- published schemas, fixtures, profiles, concept catalogs, schema publication
  manifest, contract corpus packaging, generated-schema parity, and contract
  allowlists;
- SDL scenario/module versions, module import ranges, lockfiles, trust policy,
  parser normalization, deprecation messages, and semantic diagnostics;
- processor/backend/participant manifest identity, supported contract ids,
  compatibility declarations, conformance profiles, and runtime admission;
- explanatory release, migration, SDL, API, and contributor documentation;
- owning packages and compatibility-only wrappers; and
- policy, contract, unit, conformance, docs, and release-workflow tests in the
  canonical nox graph.

No database, service repository, runtime state store, or new controller is
needed to state this policy. Git-tracked specs, manifests, release metadata,
and tests are the persistence and audit surfaces.

## Cross-Cutting Layers

The intended design must pass every layer it touches:

- Normative authority gate: binding rules live under `specs/`; the ADR records
  why. Reference Python models, examples, docs, and generated schemas remain
  consumers/evidence. A new top-level authority root or duplicate governance
  schema is not required.
- Release-input validation: PR titles are untrusted GitHub event data and must
  continue through `tools/check_pr_title.py`, which parses event JSON without
  shell interpolation. Breaking markers and release types must match
  release-please configuration and the normative policy.
- Release security: retain pinned GitHub Actions, least-privilege job
  permissions, PyPI OIDC trusted publishing, protected environment use, and no
  stored PyPI token. A future release-policy check must not require secrets or
  widen `contents`, `pull-requests`, or `id-token` permissions.
- Package/config shapes: keep release-please's JSON config and manifest,
  `pyproject.toml` project version, and installed distribution metadata as the
  package seams. Do not add environment-variable version overrides or a second
  version file.
- Schema publication gate: schema paths remain normalized, repo-relative, and
  contained under `contracts/schemas/`; ids match filenames; hashes and change
  descriptions match content; stable incompatible edits require a new lineage;
  removals carry tombstones. Generated-schema parity remains evidence, not
  authority.
- Contract and SDL validation: exact schema discriminators and supported
  contract ids continue through closed Pydantic models, semantic validators,
  JSON Schema validation, profile/conformance checks, and manifest authority
  allowlists. Compatibility policy must not bypass these gates with coercion or
  "best effort" fallback.
- Module trust and version gate: module constraints continue through
  `packaging` specifier parsing or exact-string fallback, then lockfile,
  registry allowlist, signature, digest, export-hash, archive-safety, and
  whole-scenario validation. A version match is not a trust decision.
- Auth and control-plane gate: the design adds no endpoint. If a future API
  exposes version/support information, it must reuse strict default auth,
  read-role dependencies, request-size guards, published DTOs, audit events,
  and redacted errors. Compatibility status must never grant authorization.
- Secret-handling gate: versions, lifecycle records, compatibility reports,
  migrations, release notes, and diagnostics must not carry tokens, private
  keys, registry credentials, environment dumps, private configuration, or raw
  payloads. No secret file or new secret is needed for governance validation.
- OS/process exposure gate: keep version and base-revision values as ordinary
  validated data. Do not put credentials in process argv, shell-interpolate PR
  titles or migration input, execute user-provided version strings, or add
  subprocess-based version discovery when distribution metadata and Git
  artifacts already exist.
- Error-envelope gate: accepted-but-deprecated use gets a bounded notice in the
  owning channel; unsupported or removed input gets the existing SDL,
  contract, CLI, conformance, or HTTP error. Messages may name surface ids and
  versions but must not dump full artifacts, environment state, tracebacks, or
  secrets.
- Observability and audit: package evolution is visible through the release PR,
  tag, GitHub Release, PyPI artifact, and `CHANGELOG.md`; schema evolution
  through hashes, `last_change`, tombstones, and CI; policy verification through
  nox `START`/`PASS`/`FAIL` events. Do not add runtime logs, telemetry, or a
  database audit table for repository governance.

## Extensibility Seam

The extension seam is the normative surface-class matrix. Each row owns:

- identifier and comparison syntax;
- source of truth;
- producer and consumer roles;
- structural, semantic, behavioral, and operational compatibility claims;
- stability and lifecycle rules;
- deprecation notice and removal eligibility parameters; and
- required migration evidence.

The obvious future variation is a new independently released artifact family
or a different notice window for an existing class. It should add or amend one
matrix row and extend the owning manifest/checker, not require edits to every
parser, controller, DTO, service, repository, exception, and workflow.
Lifecycle thresholds belong as named policy parameters in the normative spec;
surface-specific machine enforcement stays with the existing schema manifest,
release workflow, module registry, or compatibility wrapper gate.

## Existing Drift To Resolve Deliberately

- `.gc/plan-rules.md`, `docs/explain/releasing.md`, the release workflow, and
  `CHANGELOG.md` say release-please owns releases and that feature work does not
  add fragments. `README.md`, `CONTRIBUTING.md`, the pull-request template, and
  `specs/authority/authority-boundary.yaml` still describe towncrier and
  `changelog.d/`; `changelog.d/` currently exists. The policy must name one
  workflow (release-please is the operating incumbent) and the repository must
  not retain contradictory contributor instructions.
- `docs/conf.py` reports `0.1.0` while the project and release manifest report
  `0.19.1`. CLI and compatibility fallbacks also use `0.1.0`, while processor
  and backend fallbacks use `0.0.0+unknown`; the FastAPI OpenAPI document
  hard-codes `0.1.0`. The design must classify package version, API description
  version, and "not installed" fallback instead of synchronizing unrelated
  literals blindly.
- No checked-in schema is currently `stable`, so ADR-061's breaking-change
  path is exercised mainly by synthetic policy tests. Promotion criteria and
  regression evidence must be explicit before the first stable promotion.
- `ImportDecl.path` is described as deprecated but accepted without an emitted
  lifecycle notice. Removed scoring fields have a useful parser migration
  pointer, while `docs/migration/README.md` only records historical repository
  moves. These are evidence that deprecation notices and migration guidance are
  not yet a coherent cross-surface lifecycle.
- `supported_contract_versions` names exact ids, and apparatus compatibility
  names implementations without version constraints. Renaming or expanding
  those published shapes is itself a compatibility change; governance must
  document present meaning before proposing a new negotiation surface.
- ADR-061's compatibility classifier is deliberately conservative and
  incomplete. Its result must be described as the enforced structural floor,
  not proof of semantic or implementation-reader compatibility.

## Gotchas And Anti-Patterns

Avoid:

- one universal `Version`, `Compatibility`, `Deprecation`, or `Migration`
  runtime model spanning package, schema, module, apparatus, and domain
  artifacts;
- treating SemVer, PEP 440, contract `vN` suffixes, state schema discriminators,
  source release ids, and ADR status as interchangeable;
- calling a change compatible without naming direction, producer, consumer,
  and structural/semantic/behavioral/operational dimension;
- equating JSON Schema acceptance with compatibility for older closed-world
  Pydantic readers;
- using package release bumps instead of independent contract ids, or using a
  new contract id for every package patch;
- reinterpreting `supported_contract_versions` as ranges, or
  `compatibility.processors/backends` as version negotiation, without a new
  governed contract change;
- duplicating the schema manifest, contract allowlists, module version matcher,
  release version file, changelog generator, validation helpers, diagnostics,
  exception hierarchy, or compatibility workflow;
- editing accepted ADR-061 without supersession or a recorded ADR-059
  amendment;
- silently accepting removed syntax, dropping unknown migration data, applying
  lossy auto-fixes, or allowing adapters to become permanent undocumented
  semantics;
- emitting deprecation warnings from multiple layers for one use, or turning
  notices into fatal semantic errors before removal;
- hand-editing package versions or `CHANGELOG.md`, reviving a parallel
  towncrier workflow, or deriving release policy from stale docs;
- adding an unauthenticated version endpoint, environment-driven compatibility
  override, token-bearing argv, raw-payload error, or runtime persistence layer
  for repository policy; and
- claiming a support window, migration capability, stable contract, or
  compatibility guarantee that no test or release artifact demonstrates.

## Non-Goals And Implementation Boundaries

- Implementing GOV-901, GOV-902, or GOV-903 in this preflight note.
- Writing the issue implementation plan or deciding the spawned issues' work
  sequencing.
- Creating the umbrella ADR, normative governance spec, lifecycle registry,
  schema, fixture, validator, migration guide, migrator, warning, adapter, or
  release gate.
- Changing package versions, tags, release-please behavior, changelog history,
  branch protection, PyPI publication, or support commitments.
- Promoting any schema to `stable`, changing a contract id, adding version
  negotiation, or redefining existing manifest fields.
- Removing compatibility wrappers, deprecated SDL syntax, legacy documents,
  or stale version literals during architecture preflight.
- Redesigning parser normalization, semantic validation, module trust,
  apparatus admission, control-plane auth, persistence, logging, or error
  handling.
- Guaranteeing compatibility with arbitrary pre-policy releases or external
  implementations for which the repository has no conformance evidence.
