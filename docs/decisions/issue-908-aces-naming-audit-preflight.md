# Issue 908 ACES Naming Audit Preflight

Date: 2026-07-26

Issue: #908. Requirement: none. The GitHub issue is the authoritative audit
contract.

This note classifies the remaining ACES-bearing surfaces before implementation.
It does not authorize a repository-wide replacement. The issue supplies an
inventory and asks for decisions on contract and runtime identities; it does
not provide acceptance criteria for an in-place breaking migration.

## Architecture Decision

ADR-093 remains the rename authority. Issue #908 completes its classification,
not the earlier Python import cut:

| Surface | Disposition for #908 | Owning authority |
|---|---|---|
| Current non-contract prose, comments, and private symbol names | May use RAES when meaning and emitted values do not change | Owning docs/package/tool |
| `https://aces.dev/schemas/...` | Retain for every current schema lineage; the namespace is not retired by this issue | ADR-061, published schemas, schema-publication records |
| Contract ids, profile ids, `$defs` names, annotation keywords, wire discriminators, and wire keys | Retain in current contract versions; do not rename in place | Normative schemas/fixtures/specs and closed DTOs |
| `aces-reference-processor` and other apparatus identities | Retain until an apparatus-identity migration names producer, consumer, version, and conformance evidence | Manifest owners and manifest authority |
| `aces.lock.json`, `aces-trust.yaml`, OCI media types/annotations, evidence schema ids, auth headers, host labels, kernel parameters, and resource prefixes | Retain; each is an external config, artifact, security, guest, or host-ownership protocol | Owning registry, runtime, operations, or backend boundary |
| Participant `aces.*` values | Retain as wire `schema_name` and status-mapping vocabulary; they are not message-broker topics | Participant-runtime spec, DTOs, schemas, and fixtures |
| `ACES_REQUIREMENT_UID` and `ACES_REAL_LIBVIRT_URI` | Retain as the only actual environment-variable surfaces in the audit | Requirement governance and opt-in libvirt certification |
| `ACES_NATIVE` and `ACES_RELATIVE_TO_SOURCE` | Retain as Python enum member names for provenance wire values; they are not environment variables | Provenance DTO and lineage ledger |
| Accepted ADRs, changelog history, provenance ledger, pinned research/evidence, citations, and external URLs | Preserve as historical or immutable evidence | ADR-059, ADR-080, and the owning record |

The current schema URI namespace is an identifier, not a request to resolve
schemas over the network. Repository validation uses local published schemas
and `schema_bundle()`; no HTTP resolver is present. A future RAES URI namespace
is eligible only after its target is owned and publishable, old identities
remain resolvable or are explicitly deprecated, and old and new lineages can
coexist. A global base-URL replacement is not a valid cutover.

All current schema-publication entries are `draft`, but `draft` does not make
consumer-visible identity changes non-breaking. It permits governed evolution
under ADR-061; it does not waive migration evidence, fixture coordination, or
the ecosystem compatibility rules.

No ADR amendment is required. ADR-093 already separates project identity from
contract identity, and `docs/migration/raes-rename.md` is the surface map for
the retained decisions above.

## Canonical Incumbents

Implementation must reuse these owners rather than introduce a rename layer:

- Authority and publication: ADR-009, ADR-019,
  `specs/authority/authority-boundary.yaml`, ADR-061,
  `contracts/schema-publication-manifest.json`,
  `contracts/schema-publication/entries/`,
  `tools/check_schema_publication.py`, `schema_bundle()`, and
  `tools/check_generated_schemas.py`.
- Compatibility and lifecycle: ADR-075,
  `specs/evolution/versioning-deprecation-and-migration.md`,
  `specs/evolution/deprecation-records.yaml`,
  `tools/check_deprecation_lifecycle.py`, and
  `docs/migration/raes-rename.md`.
- Contract shape and validation: `raes_contracts._base.ContractModel`,
  `raes._base.SDLModel`, the existing Pydantic models, local Draft 2020-12
  JSON Schema validation, normative fixtures, `tools/check_json_artifacts.py`,
  and `raes_contracts.corpus`.
- Semantic annotations: the existing `schema_constraints.py`,
  `schema_invariants.py`, and `contracts/schemas/profiles/`
  `aces-semantic-invariants-v1.json` profile. Internal helper names may change;
  the published `x-aces-*` protocol may not change accidentally with them.
- Module/config security: `raes.module_registry` constants and loaders,
  `yaml.safe_load`, closed `TrustPolicy`/`Lockfile` models, digest/signature
  checks, capped OCI reads, safe archive extraction, and `raes_cli.sdl`.
- Apparatus and runtime artifacts: the existing processor/backend manifest
  renderers and closed models; evidence builders and their shared redaction
  gate; participant-runtime DTOs/spec/fixtures; and the current artifact
  validators. Do not add a second identifier catalog.
- Host ownership: `provider_resource_name()`, the libvirt fixed UUID namespace,
  OCI ownership labels and inspection join, libvirt ownership checks,
  structured XML builders, fixed argv execution, bounded timeouts, and
  ownership-confined teardown.
- Runtime security and persistence:
  `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneRole`,
  bearer/trusted-proxy authentication, `request_size_guard_response()`,
  request fingerprints/idempotency, append-only audit records, redacted
  unexpected-error responses, `RuntimeSnapshot`, and
  `LocalControlPlaneStore`.
- Errors and diagnostics: existing Pydantic `ValidationError`,
  `SDLParseError`/`SDLValidationError`, Typer `BadParameter`/`Exit`,
  package-local `Diagnostic`, MCP structured JSON, and bounded HTTP JSON
  envelopes. There is no rename-specific exception hierarchy.
- Workflow: ADR-014, `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `.github/workflows/ci.yml`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/verify_all.py`, gitleaks,
  private-key detection, ADR pins, authority checks, publication checks, and
  the owning focused tests.

## Cross-Cutting Security And Whole-Path Gates

- **Published contract ingress:** edit the normative schema/fixture/spec owner
  first. JSON must remain locally parseable, closed DTOs keep
  `extra="forbid"`, schema annotations keep their existing semantic validator,
  publication records carry the current canonical hash and `last_change`, and
  `schema_bundle()` remains byte-identical. Do not fetch remote `$ref` values or
  make DNS/HTTP availability part of validation.
- **Auth surface:** `x-aces-client-verified` and
  `x-aces-client-identity` are trusted-proxy protocol fields, not branding.
  This issue leaves them unchanged. Any future dual-name adapter belongs in
  `ControlPlaneSecurityConfig`, which already parameterizes the header names;
  it must remain disabled under strict defaults, accept values only behind the
  trusted proxy boundary, reject conflicting old/new headers, enforce
  request-size limits, and audit denials. Role checks remain mandatory. The
  current bearer-token branch returns before the proxy branch's target check;
  do not claim bearer target scoping or build a header migration on that gap
  without first unifying the post-authentication target check.
- **Secret surface:** no rename needs a secret, token, credential, private key,
  environment dump, raw backend object, or real payload. Do not read secret
  files or copy real values into fixtures, docs, logs, schema examples, or
  migration records. Module trust keeps signature and digest validation.
  Evidence keeps the shared redaction gate.
- **Environment/config shape:** `ACES_REQUIREMENT_UID` remains an external
  Ground Control/workflow input. `ACES_REAL_LIBVIRT_URI` remains an opt-in test
  input and must never carry credentials. The real-libvirt tests currently read
  it directly; a naming cleanup must not add another alias or call path that
  widens that pre-existing validation gap. Do not add dotenv or a generic
  environment binder.
- **OS/host exposure:** OCI labels and libvirt names are passed by fixed argv;
  kernel parameters are visible in the guest and host process boundary; guest
  paths and evidence ids are persisted. The challenge kernel parameter must
  remain a non-secret correlation value. Preserve the fixed libvirt UUID
  namespace even if private Python symbols are renamed: changing its value
  would make existing owned objects look foreign, create duplicates, or block
  safe teardown. Do not use shell interpolation or place secrets in argv.
- **Error envelopes and logging:** a naming failure must flow through the
  owning parser/DTO/CLI/diagnostic/HTTP envelope. Do not include raw input,
  environment values, host paths, native stdout/stderr, schema bodies, or
  tracebacks. Existing audit and logs are evidence, not a second migration
  ledger; do not rewrite old records or add a rename logger.
- **Persistence:** lockfiles, trust policies, contract fixtures, evidence
  artifacts, runtime snapshot histories, append-only audit data, and native
  ownership markers may contain retained identifiers. Do not silently rewrite
  them, normalize them on read, or add a migration database/service. A future
  versioned reader adapter stays at the owning boundary and must preserve the
  source artifact.
- **Workflow:** the branch is requirement-free. Do not invent a requirement UID
  or bypass repository policy. Reuse nox and the existing owner-specific gates;
  do not add a global “zero ACES tokens” rule because retained contracts and
  historical evidence make zero both impossible and incorrect.

## Extensibility Seams

The parameter is the **surface class and version/lineage**, not a global
old-name/new-name pair.

- A future schema namespace or contract-id migration extends the existing
  per-contract `schema_bundle()` metadata path and schema-publication entry so
  old and new lineages coexist. `_schema_id_for_contract_id()` is the existing
  implementation seam; it must become lineage-aware rather than substitute one
  global base URL.
- A future auth-header variation uses the already parameterized
  `ControlPlaneSecurityConfig` fields.
- A future module artifact variation stays behind `LOCKFILE_NAME`,
  `TRUST_POLICY_NAME`, media-type constants, and their existing loaders.
- A future provider naming variation uses the existing `name_prefix` input and
  `provider_resource_name()` while preserving the separate ownership UUID
  invariant.
- A future deprecation adds its surface class/record to the existing ecosystem
  lifecycle policy and owning checker. It does not create a universal alias
  registry, runtime lookup service, endpoint, store, or exception tree.

## Gotchas And Anti-Patterns

Avoid:

- blind replacement, substring matching, or treating audit counts as a design;
- changing normative schemas only in Python or hand-editing generated copies;
- equating package names, schema `$id`, contract ids, `$defs` class names,
  annotation keywords, apparatus ids, artifact ids, auth headers, config keys,
  filenames, OCI labels, resource names, and prose;
- treating participant `schema_name` values as broker topics or introducing an
  event bus/topic registry;
- treating provenance enum members as environment variables;
- renaming `_aces_uuid` while also changing its fixed namespace value;
- changing OCI labels or provider prefixes without preserving discovery,
  ownership joins, rollback, and teardown of already-created resources;
- accepting both old and new config/header values with last-one-wins behavior;
- renaming a valid fixture string merely because the fixture is under
  `contracts/fixtures/`;
- rewriting accepted ADRs, `CHANGELOG.md`, the normative lineage ledger,
  pinned research/evidence, external URLs, or negative legacy-import tests;
- weakening closed-model, signature, digest, redaction, auth, request-size,
  path-containment, schema-publication, ADR-pin, gitleaks, or private-key gates;
- adding duplicate schemas, validators, compatibility tables, workflow logic,
  exception hierarchies, logs, stores, or migration services.

## Non-Goals And Boundaries

- Implementing issue #908 or reducing the occurrence count in this preflight.
- Retiring `aces.dev`, selecting an unverified RAES domain, or adding network
  schema resolution.
- Renaming current contract lineages, wire fields, apparatus identities,
  runtime artifacts, auth/config protocols, host ownership markers, or
  persisted records.
- Changing SDL, contract, runtime, security, observability, persistence,
  backend, or conformance semantics.
- Adding compatibility aliases for the already removed Python, CLI, or MCP
  surfaces.
- Rewriting historical records solely to erase the former project name.
