# Issue 738 Associated Artifact Manifests Preflight

Date: 2026-07-12

Issue: #738.

Requirement: none. The issue title, body, and acceptance criteria are the
authoritative contract.

This note records architecture guardrails for scenario- and
experiment-associated non-semantic artifact manifests. It is implementation
guidance only. It does not add normative specification text, schemas, contract
models, validators, fixtures, trust-policy entries, packaging behavior, APIs,
storage, or runtime behavior.

## Binding Sources

- ADR-009, ADR-019, `specs/authority/authority-boundary.yaml`, and
  `contracts/README.md` keep normative prose under `specs/`, normative schemas
  and fixtures under `contracts/`, and Python under the non-normative reference
  implementation boundary.
- ADR-055 and `specs/formal/experiment-core/README.md` own experiment tasks,
  authoring inputs, apparatus context, runs, studies, typed references,
  `ExperimentArtifactRefModel`, `ExperimentChecksumModel`, and cross-artifact
  validators. Identifier-bearing collections use keyed maps when uniqueness is
  part of the portable contract.
- ADR-064 through ADR-066 own captured evidence, derived analysis, provenance,
  sensitivity/redaction, and the rule that archival evidence is not scenario
  meaning or live runtime state.
- ADR-071 and `specs/supply-chain/reusable-asset-trust-integrity.md` keep
  identity, integrity, and authenticity distinct; treat reusable asset as a
  family-specific role; and forbid a universal `TrustedAsset` payload.
- ADR-053 owns module registry, lockfile, OCI, signature, bounded-read, and
  archive-extraction behavior. A scenario companion manifest must not become a
  second module package, registry, lockfile, or archive format.
- The canonical SDL profile in `aces_sdl.canonical` identifies validated,
  expanded SDL meaning only. Its `aces-sdl-semantic/v1` bytes and digest must
  not absorb documentation, starter material, evaluator assets, reports,
  profiles, operator material, or other companion bytes.
- ADR-059 governs changes to accepted ADRs. Any implementation amendment to
  ADR-055 or ADR-071 needs an amendment row and pin update, or a superseding
  ADR; accepted text must not be edited silently.
- ADR-061, ADR-075, `contracts/schema-publication-manifest.json`, and
  `specs/evolution/versioning-deprecation-and-migration.md` govern contract
  lineage, compatibility, publication records, and migration.

## Architecture Decisions

### One standalone attachment contract, not a package model

Publish one closed, versioned associated-artifact-manifest contract. It is a
portable statement that one exact artifact-reference set is attached to one
explicit parent. It is not an SDL section, experiment record subtype, archive
index, live-directory inventory, trust decision, acquisition request, or
universal reusable-asset payload.

The contract has a closed scope discriminator and a constrained parent
reference:

- scenario scope permits `scenario` and `scenario-snapshot` parents;
- experiment scope permits the existing experiment artifact families named by
  the issue: task, experiment authoring input, apparatus context, run, and
  study; and
- the scope and parent kind must agree. Catch-all `other` parents are not
  conformant attachment points.

Reuse `ExperimentReferenceModel` and its constrained reference patterns rather
than creating a second generic reference vocabulary. Add the missing explicit
authoring-input reference kind at that shared seam if needed; do not disguise
it as `protocol`, `manifest`, or `other`. Parent matching remains
family-specific because task, authoring-input, apparatus, run, study, scenario,
and scenario-snapshot payloads have different identity fields.

A generic `scenario` parent is an association to a conceptual scenario id only.
It cannot make a snapshot-integrity claim and must retain the existing id-only
restriction. A `scenario-snapshot` parent may carry the incumbent version and
digest binding, which the parent matcher checks by applying
`canonical_sdl_digest()` to a validated, expanded scenario. Experiment parent
refs bind the incumbent id/version fields. They must not gain a `ref_digest`
until that parent family has a normative canonical payload profile and a
validator for it; a generic experiment reference field is not permission to
self-certify a parent digest. The manifest never changes the scenario's
semantic digest.

### Reuse the incumbent artifact descriptor

The artifact entry must deliberately reuse or factor the incumbent
`ExperimentArtifactRefModel` / `ExperimentChecksumModel` shape: stable local
`artifact_id`, role, media type, URI, checksum, byte size, source, creation
time, sensitivity, optional description, and applicable provenance/evidence
links. Do not publish a scenario-only copy of those fields.

Scenario companion roles may extend the shared role vocabulary where the
existing roles are insufficient, but role remains a closed contract field.
Do not use media type, filename suffix, directory name, URI path, or free-form
description as a hidden role discriminator.

Within one manifest:

- `artifact_id` is an opaque, case-sensitive, stable local identity. It is not
  a path and is not content identity.
- `(checksum algorithm, checksum value, size)` identifies payload bytes. The
  URI is a non-authoritative locator; checksum validation establishes
  immutability even if a locator is mutable.
- In the portable manifest, the URI is an absolute, non-secret URI (including a
  content-addressed URN where appropriate), not a pack-relative filesystem
  path. URI scheme support and acquisition remain consumer policy. Userinfo,
  bearer material, or other embedded credentials are forbidden.
- Artifact entries use a keyed object map, with each key equal to the embedded
  `artifact_id`. This follows ADR-055 and makes duplicate local ids impossible
  in the constructed portable object. Duplicate JSON member names must still
  fail at the JSON ingress boundary rather than being accepted with
  last-write-wins behavior.
- Reusing an artifact id in a different manifest is allowed because ids are
  manifest-local. Repeating the same checksum under distinct ids is allowed
  when the producer intentionally gives the same bytes distinct roles or
  locators; both entries remain in the canonical set and both must validate.
- One URI must not make conflicting checksum, size, or media-type claims in the
  same manifest. Exact duplicate descriptors under different keys are invalid
  aliasing, not two artifacts.

`source` and provenance fields are assertions, not authenticity evidence.
`sensitivity` governs handling and disclosure but does not grant entitlement.
No sensitivity value may weaken byte binding. Restricted or redacted metadata
must still retain the non-secret checksum and size needed for verification.

### Separate logical manifest identity from set identity

The manifest needs a stable logical id/version and a separately computed
associated-artifact-set digest. The set digest is derived; a caller cannot
establish it by supplying a string.

Define a versioned canonicalization profile for the abstract contract. Its
canonical projection contains the profile id, attachment scope, exact parent
reference, and exact keyed artifact-reference set. It excludes the set-digest
field itself and excludes filesystem traversal order, archive metadata,
materialization paths, manifest filenames, export tiers, and packaging-layout
metadata. Digest spellings must be normalized by the profile so equivalent hex
case does not create different set identities; URI strings, opaque ids, and
descriptive values must not receive filesystem- or platform-dependent
normalization.

Use the repository's incumbent RFC 8785/JCS and lowercase prefixed-digest
convention unless the normative specification records a compelling
incompatibility. Keep the associated-artifact canonicalization profile
distinct from `aces-sdl-semantic/v1`: equal SDL meaning does not imply equal
attachment sets, and equal attachment sets do not imply equal SDL meaning.

The set digest changes when the parent reference or any canonical artifact
entry changes. It does not change merely because a downstream archive orders
files differently or chooses another safe layout.

### Byte binding is a mandatory cross-artifact gate

Closed schema/model validation proves shape only. Full conformance and every
integrity/trust claim require a named cross-artifact validator that receives:

- the validated manifest;
- the concrete parent artifact when parent-payload identity must be checked;
  and
- one concrete, explicitly supplied byte stream for every artifact id.

The validator computes each declared checksum and byte size from the supplied
bytes, checks that every manifest entry has exactly one byte binding, checks
the parent reference against the supplied parent, and recomputes the set digest
from canonical contract data. A mapping that supplies only a caller-asserted
digest, size, path, URI, or prior validation boolean is not a byte binding. A
missing byte stream is a conformance failure, not an optional or offline mode.

The validator must not fetch URIs, walk directories, unpack archives, resolve
registry credentials, or infer a payload from a filename. Acquisition and
materialization are caller responsibilities. The validator consumes already
staged bytes through a narrow reader/resolver parameter so filesystem, object
store, OCI, and in-memory consumers can share the same checksum logic without
putting those transports into the ACES contract.

Reads must be streaming and bounded. Reject declared artifact counts,
per-artifact sizes, or total sizes that exceed caller-supplied policy limits
before reading; stop at the declared size plus one byte when detecting a size
mismatch; and never buffer an unbounded artifact set. Follow the bounded-read
pattern in `aces_sdl.module_registry`, but do not import its OCI-private
helpers or its archive semantics into the portable validator.

### Attachment never implies inheritance

The only attachment established by a manifest is its exact `parent_ref`.
Scenario attachments are not automatically task attachments; task attachments
are not automatically authoring-input, run, apparatus, or study attachments;
run attachments are not automatically study attachments; and study membership
does not copy member attachments into the study.

Attaching the same bytes at another scope requires another conforming manifest
whose own parent reference names that scope. Because the parent participates in
set identity, the two manifests have different set digests even when their
artifact maps are identical. Lineage between those manifests may use existing
typed references, but lineage does not create attachment or inheritance.

### Trust mapping is family-specific

Keep four claims distinct:

1. the semantic SDL digest identifies validated expanded SDL meaning;
2. the associated-artifact-set digest identifies one parent plus one exact
   artifact-reference set;
3. each `artifact_checksum` binds one entry to concrete payload bytes; and
4. authenticity is an independently verified signature/trust-policy decision.

The parent asset retains its incumbent integrity mechanism. Associated bytes do
not contribute to the scenario semantic digest, scenario-snapshot digest, task
identity, run identity, apparatus identity, authoring-input identity, or study
identity.

Map the manifest/set as a distinct `associated_artifact_set` reusable-asset
family under ADR-071. Its set digest is `integrity_digest`; its referenced
payloads require `artifact_checksum`. This requires the reusable-asset trust
policy contract and reference fixture to gain the new family while preserving
the existing `reusable_scenario` and experiment-family mappings. A signature
over the set digest may satisfy `authenticity_signature`; the manifest digest
or checksum alone never does.

This is not a scenario-distribution/bundle asset family. A distribution may use
the manifest, but archive or filesystem layout remains downstream. A generic
scenario attachment cannot satisfy reusable-scenario snapshot integrity. A
snapshot-scoped manifest can be independently trusted as an associated set,
but it still does not alter the parent snapshot digest.

## Required Incumbents

- Authority and publication: `specs/`, `contracts/schemas/`,
  `contracts/fixtures/`, `contracts/schema-publication-manifest.json`,
  `specs/authority/authority-boundary.yaml`, `ContractModel`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `tools/check_json_artifacts.py`.
- Experiment identity and artifacts: `ExperimentReferenceModel`,
  `ExperimentScenarioReferenceModel`,
  `ExperimentScenarioSnapshotReferenceModel`, `ExperimentTaskReferenceModel`,
  `ExperimentArtifactRefModel`, `ExperimentChecksumModel`,
  `ExperimentTaskModel`, `ExperimentSpecModel`,
  `ExperimentApparatusContextModel`, `ExperimentRunModel`,
  `ExperimentStudyModel`, `_canonical_digest()`,
  `_experiment_reference_key()`, `_validate_unique_experiment_references()`,
  and the task/run/study cross-artifact validators.
- Portable semantic invariants: `_add_aces_invariant()`,
  `AcesSemanticInvariantEntryModel`, the `x-aces-invariants` profile, and
  `validate_aces_semantic_invariant_annotations()`. Payload-byte binding must
  be published as a named required semantic invariant; generic JSON Schema
  consumers must not claim full conformance after shape validation alone. The
  current invariant `inputs` shape names contract instances only, so it must
  name the manifest and applicable parent contracts while the validator's
  public callable contract explicitly requires external byte readers. Do not
  invent a synthetic JSON "bytes contract" or falsely describe a digest map as
  the payload input; extend the semantic-invariant profile deliberately only if
  portable discovery of non-contract inputs becomes a broader requirement.
- Canonical identity: `aces_sdl.canonical` and its RFC 8785 implementation as
  a serialization precedent only. Associated-artifact canonicalization belongs
  in the contract-owned package, not in SDL semantic identity code.
- Trust policy: `ReusableAssetTrustPolicyModel`,
  `ReusableAssetFamilyTrustPolicyModel`, `REUSABLE_ASSET_FAMILIES`, the
  normative trust specification, the published trust-policy schema, and its
  valid/invalid fixture family.
- Diagnostics and conformance: `aces_contracts.diagnostics.Diagnostic`,
  `Severity`, `aces_conformance.conformance`, `_MODEL_VALIDATORS`,
  `_fixture_case_diagnostics()`, and the existing structured CLI report. Reuse
  this envelope instead of adding an artifact-manifest exception hierarchy.
- Corpus and installed-distribution access: `aces_contracts.corpus`, the
  existing `schemas` and `fixtures` families, Python package `force-include`
  rules, and installed-corpus tests. Do not add a second manifest/schema loader.
- Manifest capability authority: `aces_contracts.manifest_authority` allowlists
  describe processor/backend/participant runtime support, not every published
  contract. Do not add the standalone manifest contract to those allowlists or
  backend profiles unless that surface actually consumes it.
- Persistence precedents, if a later producer writes a manifest:
  `aces_operations.run_artifacts.atomic_write_json_artifact()` and
  `LocalControlPlaneStore._atomic_write()` demonstrate same-directory temporary
  files plus `os.replace`. They are precedents for atomic writes, not authority
  to store attachment manifests in control-plane state.
- Workflow gates: `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_authority_boundary.py`, `tools/check_adr_immutability.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

The intended design must pass each layer it touches:

- **JSON/config ingress:** parse local JSON as data, reject duplicate member
  names before object construction, then apply the published Draft 2020-12
  schema and closed `ContractModel(extra="forbid")` model. Do not evaluate
  content, resolve remote schema references, or accept unknown fields.
- **Shape validation:** enforce scope/parent discrimination, parent-kind
  constraints, keyed artifact-id equality, checksum length/algorithm, byte
  sizes, RFC 3339 creation times, closed role/sensitivity values, and locator
  shape through shared contract validators. Reuse archival datetime validators
  rather than creating another date parser.
- **Cross-artifact semantic validation:** run parent matching, collision rules,
  set-digest recomputation, and one-to-one payload-byte binding after shape
  validation. Publish these requirements through `x-aces-invariants` and make
  conformance invoke the same validator rather than reimplementing its logic.
- **Trust-policy gate:** evaluate parent integrity, set integrity, payload
  checksums, and authenticity as separate evidence classes. Trust status never
  grants authorization or bypasses sensitivity handling.
- **Secret-handling surface:** manifests carry public verification metadata,
  not bearer tokens, registry credentials, signed-URL secrets, private keys,
  raw credentials, hidden prompts, answer keys, environment dumps, or raw
  payloads. URI userinfo and credential-bearing query strings are nonconformant
  producer behavior and must never be echoed in diagnostics.
- **Resource and acquisition surface:** the core validator performs no network,
  archive, registry, or directory acquisition. Downstream acquisition applies
  its own allowlists, timeouts, root confinement, archive safety, and immutable
  staging before passing bounded readers to the validator.
- **OS/process exposure:** no subprocess, shell, environment-variable policy
  channel, token-bearing argv, ambient current-directory walk, symlink-following
  traversal, or host-absolute path belongs in contract validation. The byte
  resolver is an in-process parameter, not a CLI secret channel.
- **Persistence:** no ACES control-plane or runtime persistence changes are in
  scope. Do not place manifests or validation status in `RuntimeSnapshot`,
  `RuntimeSnapshot.metadata`, `ControlPlaneStore`, operation records, or audit
  details. Downstream consumers own immutable staging, atomic promotion,
  retention, and use-time revalidation.
- **Logging/observability:** conformance emits stable `Diagnostic` code, domain,
  address, severity, and bounded message. It may name the contract field or
  artifact id, but must not include payload bytes, full rejected objects,
  credential-bearing URIs, environment data, or tracebacks. There is no new
  runtime metric or log stream in this issue.
- **HTTP/auth surface, if later exposed:** use
  `ControlPlaneSecurityConfig.strict_defaults()`, `_MutatingIdentity` versus
  `_ReadIdentity`, `request_size_guard_response()`, request fingerprints and
  idempotency, `record_audit()`, published request/response models, and the
  redacted 500 handler. Validation success is not authentication,
  authorization, or entitlement. URI fetching must not occur inside a request
  handler merely because a manifest was accepted.
- **Error envelopes:** Pydantic/JSON Schema shape failures stay contract
  failures; semantic and byte-binding failures use `Diagnostic`; a thin
  convenience validator may raise existing `ValueError` after diagnostics are
  available. SDL parsing errors remain SDL errors, and future HTTP adapters use
  bounded `HTTPException` details plus the existing redacted internal-error
  envelope. Do not add a parallel exception tree.

## Conformance Diagnostics And Negative Cases

Use one diagnostic producer as the source of truth, with stable codes for at
least:

- missing concrete payload binding or a digest-only/caller-asserted binding;
- payload checksum mismatch and payload size mismatch;
- recomputed set-digest mismatch;
- parent reference or parent payload mismatch;
- scope/parent-kind confusion;
- duplicate artifact id, keyed-id mismatch, exact descriptor aliasing, and
  conflicting claims for one locator; and
- changed artifact set under a previously asserted set digest.

Diagnostics must distinguish structural invalidity from unverified integrity.
An otherwise well-shaped manifest with no supplied bytes is structurally valid
but not fully conformant and cannot satisfy trust policy.

Valid fixtures must cover generic scenario, sealed scenario-snapshot, and every
supported experiment parent family without duplicating contract shapes.
Focused invalid fixtures must cover both attachment scopes and every negative
case above. Cross-artifact tests must mutate the parent, artifact set, bytes,
checksum, and size independently so no test passes because two claims drifted
together. Schema-only tests and model/semantic tests remain distinct.

## Downstream Packaging And Consumer Boundary

Scenario-pack tooling owns filesystem layout, manifest filename, archive or OCI
layout, traversal rules, release tiers, catalog metadata, and materialization.
It may produce the ACES portable manifest only after selecting a stable byte
set; a walk over a live mutable directory is not an atomic snapshot and is not
the ACES asset model.

Consumers own acquisition, immutable staging, storage, entitlement, and
use-time verification. They must stage the parent and every referenced payload,
run ACES shape and byte-binding validation, derive rather than trust the set
digest, atomically promote the verified set, retain the manifest with the
verified bytes, and verify again before use when storage guarantees do not make
that redundant. A caller-supplied package digest may be retained as untrusted
metadata, but cannot be persisted as ACES conformance or trust evidence unless
it equals the validator-derived set digest.

## Extensibility Seam

The seam is a closed attachment scope plus constrained parent-reference kind,
the versioned canonicalization profile, and an injected bounded byte resolver.
Adding a future parent family should require one constrained reference/matcher,
one schema enum/union extension, and focused fixtures; it must not require
changing SDL semantics, every experiment root, storage, archive layout,
conformance diagnostics, and trust code independently.

Adding future artifact roles extends the shared artifact-role vocabulary.
Adding a canonicalization revision publishes a new profile and compatibility
evidence; it does not silently reinterpret existing set digests. Adding a new
transport implements the downstream resolver/acquisition boundary and leaves
the manifest and byte validator unchanged.

## Gotchas And Anti-Patterns

Avoid:

- changing `canonical_sdl_digest()` or treating companions as SDL meaning;
- creating `TrustedAsset`, `ScenarioBundle`, `ScenarioPack`, or a second
  experiment artifact descriptor with duplicated fields;
- using a live directory walk, archive order, inode metadata, permissions,
  symlink targets, manifest filename, or export tier in portable set identity;
- accepting a caller-supplied package/set digest without recomputing it and
  binding every referenced checksum to concrete bytes;
- treating `artifact_id`, URI, filename, parent id, schema validity, or a prior
  validation boolean as integrity or authenticity;
- allowing generic scenario refs to carry version/digest/path qualifiers or
  using experiment `other` refs to avoid a missing typed parent kind;
- inferring attachment or trust across scenario, task, authoring-input,
  apparatus, run, and study scopes;
- duplicating checksum models, reference vocabularies, canonical JSON helpers,
  schema registries, corpus loaders, trust-policy tables, semantic validators,
  diagnostics, exception hierarchies, persistence stores, audit logs, or nox
  workflows;
- fetching remote URIs, walking paths, extracting archives, or following
  symlinks in the contract model or core byte validator;
- storing verification state in live runtime snapshots or reconstructing an
  archival manifest from mutable control-plane state;
- logging raw bytes, full validation inputs, credential-bearing locators,
  secrets, or absolute host paths; and
- hand-editing generated/reference schema output, silently editing accepted
  ADRs, or treating implementation models as normative authority.

## Non-Goals And Implementation Boundaries

- No scenario-pack directory layout, manifest filename, archive/OCI layout,
  filesystem traversal algorithm, release tier, or catalog metadata.
- No SDL syntax or semantic identity change.
- No Shifter ingestion, storage, entitlement, launchability, or API policy.
- No acquisition workflow, registry, object store, persistence service,
  retention job, background verifier, or use-time launch integration.
- No new cryptography, signer discovery, key distribution, certificate
  authority, transparency log, or secret-bearing payload.
- No automatic inheritance between attachment scopes and no mutation of parent
  asset identity when attachments change.
- No reuse of module archive layout, lockfiles, or registry signatures as the
  associated-artifact manifest contract.
- No runtime/control-plane endpoint, config/environment setting, subprocess,
  database table, or new logging stream.
- No implementation work in this preflight note.
