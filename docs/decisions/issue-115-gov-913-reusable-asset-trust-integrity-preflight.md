# Issue 115 GOV-913 Reusable Asset Trust And Integrity Preflight

Date: 2026-07-05

Issue: #115.

Requirement: GOV-913,
`5425aaa9-935e-4706-a8ef-809dcd1ae469`.

This note records architecture guardrails for trust, authenticity, and
integrity policies over reusable scenarios, modules, tasks, studies, behavior
vocabularies, and comparable reusable assets. It is guidance for implementation
only: it does not add SDL fields, trust policies, schemas, fixtures, validators,
runtime behavior, APIs, persistence, or conformance cases.

## Binding Sources

- ADR-009, ADR-019, `specs/authority/authority-boundary.yaml`, and
  `contracts/README.md` define normative artifact authority. Reusable asset
  policy must respect `specs/`, `contracts/`, `implementations/`, `docs/`, and
  `examples/` boundaries.
- ADR-012 and ADR-062 govern concept families, controlled vocabularies, ACES
  native extension discipline, and catalog linkage. Behavior vocabulary trust
  belongs in this lane, not in artifact-local free strings.
- ADR-053 and the issue #12, #13, #14, and #551 preflight notes already define
  SDL module composition trust: module descriptors, imports, lock records,
  digest pins, signature verification, registry trust policy, bounded OCI
  reads, safe tar extraction, and checkout-independent lock identities.
- ADR-041 owns participant implementation manifests and run-level provenance:
  selected manifest refs, manifest/configuration digests, decision-surface
  mode, exposure policy, and the rule that portable artifacts carry references
  and digests rather than secrets or raw private configuration.
- ADR-055, ADR-064, ADR-065, and ADR-066 own experiment tasks, studies, run
  provenance, evidence records, raw-content checksums, derived analysis, and
  observability/evidence plane separation. Integrity evidence for experiments
  must reuse those contracts instead of runtime logs or evaluator detail.
- ADR-056 and ADR-057 own shared secret/redaction boundaries for runtime
  observed values and credential-like names. Reusable asset trust records must
  not become a path for raw credentials, prompts, answer keys, or hidden
  adjudication state.
- ADR-061 and `contracts/schema-publication-manifest.json` govern any published
  schema change. If GOV-913 publishes a contract, the schema manifest,
  generated-schema parity, fixtures, and JSON artifact validation are mandatory.

## Architecture Decisions

- Treat "reusable asset" as a role played by existing asset families, not as a
  new universal domain object. Scenarios, SDL modules, experiment tasks,
  studies, behavior vocabularies, manifests, profiles, and evidence artifacts
  keep their existing authority and validation boundaries.
- Prefer asset-family-specific trust checks over a generic
  `TrustedAssetModel`. A module import is trusted through `aces-trust.yaml`,
  `aces.lock.json`, digest pins, signatures, and module expansion. A
  vocabulary is trusted through concept-authority source metadata and governed
  terms. A task/run/study claim is trusted through experiment-core references,
  artifact checksums, and cross-artifact validators.
- Digest, path, and signature qualifiers are valid only when a validator binds
  them to concrete payload bytes. Do not add digest fields to every reference
  because they sound useful. Existing experiment references intentionally limit
  digest/path qualifiers by reference kind.
- Scenario identity and scenario snapshot identity must stay distinct. Generic
  scenario refs are id-only; integrity-bound reuse of a concrete composed
  scenario belongs on `scenario-snapshot` refs and associated evidence, after
  module resolution, namespace rewriting, and whole-scenario semantic
  validation.
- Reusable module trust remains in `aces_sdl.module_registry` and
  `aces_sdl.composition`. Runtime managers, processor planners, backend
  contracts, and control-plane APIs should continue to see only the expanded
  canonical scenario plus explicit provenance side channels.
- Reusable behavior vocabulary trust must extend
  `controlled-vocabularies-v1`, source metadata, `source_digest`, governed
  extension patterns, concept bindings, and catalog governance. Do not create a
  second vocabulary registry or accept raw external labels as portable ACES
  semantics.
- If a reusable-asset policy becomes a published portable artifact, it belongs
  under the existing contract discipline: closed `ContractModel` source,
  `contracts/schemas/`, `contracts/fixtures/`, `schema_bundle()` parity,
  `contracts/schema-publication-manifest.json`, `tools/check_json_artifacts.py`,
  and `aces_conformance` registration where conformance-visible.
- If the policy is local module-resolution configuration only, extend the
  existing `TrustPolicy` / `RegistryTrustPolicy` surface with explicit
  validation. Do not add environment-variable-only, CLI-only, or duplicate YAML
  parsing policy channels.

## Required Incumbents

- SDL ingress and validation: `parse_sdl()`, `parse_sdl_file()`,
  `_load_normalized_data()`, YAML `safe_load`, key normalization,
  variable-created mapping-key rejection, `SDLModel(extra="forbid")`,
  `SemanticValidator`, `SDLParseError`, `SDLValidationError`, and
  `SDLInstantiationError`.
- Module trust and packaging: `ImportDecl`, `ModuleDescriptor`, `TrustPolicy`,
  `RegistryTrustPolicy`, `Lockfile`, `LockRecord`, `ResolvedModule`,
  `resolve_import()`, `resolve_lock_records()`, `_validate_digest_pin()`,
  `_signable_payload()`, `_verify_signatures()`, `_read_capped()`,
  `_safe_tar_members()`, `_extract_bundle_to_cache()`,
  `publish_module_to_oci_layout()`, and the `aces sdl resolve`,
  `verify-imports`, and `publish` CLI commands.
- Module composition semantics: `expand_sdl_modules()`, namespace rewriting,
  export enforcement, import cycle rejection, private namespace rejection,
  module variable/spec provenance, and collision detection in
  `_module_provenance`.
- Contract corpus: `ContractModel`, `schema_bundle()`,
  `aces_contracts.corpus.corpus_family_root()`, `manifest_authority` contract
  allowlists, `ControlledVocabularyCatalogModel`,
  `validate_controlled_vocabulary_value()`,
  `validate_controlled_vocabulary_scope_values()`,
  `SemanticProfileModel`, `ReferenceModelCatalogModel`, `Diagnostic`, and
  `Severity`.
- Experiment-core references and evidence: `ExperimentReferenceModel`,
  `ExperimentScenarioReferenceModel`, `ExperimentManifestReferenceModel`,
  `ExperimentArtifactRefModel`, `ExperimentChecksumModel`,
  `ExperimentTaskModel`, `ExperimentRunModel`, `ExperimentStudyModel`,
  `validate_experiment_run_against_task()`, and
  `validate_experiment_apparatus_context_against_manifests()`.
- Participant implementation trust: `ParticipantImplementationManifestModel`,
  `ParticipantImplementationProvenanceModel`,
  `ParticipantImplementationSelectionModel`, `ParticipantExposurePolicyModel`,
  and existing manifest/config digest fields.
- Policy and verification: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_authority_boundary.py`,
  `tools/check_concept_authority_governance.py`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`,
  `tools/check_json_artifacts.py`, and `tools/verify_all.py`.
- Control-plane surface, if GOV-913 later exposes APIs:
  `ControlPlaneSecurityConfig.strict_defaults()`,
  `ControlPlaneRole`, read versus mutating identity dependencies,
  request-size guards, idempotency fingerprints, audit records, bounded
  `HTTPException` details, and the redacted internal-error handler.

## Whole-Repo View

In-scope repository surfaces are:

- normative prose under `specs/`, especially SDL, formal experiment-core, and
  concept-authority specs;
- normative contract assets under `contracts/schemas/`,
  `contracts/fixtures/`, `contracts/profiles/`, and
  `contracts/concept-authority/`;
- SDL module and parser implementation under
  `implementations/python/packages/aces_sdl/`;
- contract, conformance, processor, runtime, backend protocol, and CLI packages
  under `implementations/python/packages/`;
- compatibility wrappers under `implementations/python/src/aces/`, which must
  not receive new implementation logic;
- policy tools under `tools/` and the nox verification graph;
- examples and public docs when user-visible SDL, CLI, or contract behavior
  changes; and
- tests under `implementations/python/tests/`, especially module registry,
  concept authority, controlled vocabulary, contract conformance, and runtime
  API test families.

## Cross-Cutting Layers

The intended design must pass every layer it touches:

- SDL/YAML ingress: reusable asset declarations entering through SDL must use
  safe YAML parsing, normalized fields, closed models, semantic validation, and
  collected SDL errors. Trust policy values are data fields, not
  symbol-defining map keys or variable-created authority names.
- Module trust-policy gate: `aces-trust.yaml` enters only through
  `TrustPolicy` and `RegistryTrustPolicy`; OCI imports require an allowed
  registry, explicit insecure-HTTP opt-in, trusted signer ids when signatures
  are required, version checks, digest pins, export hashes, and lockfile drift
  checks.
- Network and archive gate: all OCI metadata, config, manifest, and bundle
  fetches must stay on timeout-bounded capped readers. Bundle extraction must
  keep path traversal, link, special-file, duplicate-path, size, and root-file
  containment checks before any module source reaches the parser.
- Contract/schema gate: portable trust policy or provenance artifacts must use
  closed `ContractModel` payloads, published schemas, schema-publication
  manifest entries, valid and invalid fixtures, generated-schema parity, and
  JSON artifact validation. Do not publish implementation-private config as a
  contract unless the authority boundary is deliberate.
- Concept/vocabulary gate: reusable behavior vocabulary terms must resolve
  through controlled vocabularies and concept-family bindings. New governed
  terms need catalog entries, source/provenance metadata, extension policy, and
  existing catalog governance checks.
- Experiment provenance gate: task, run, study, manifest, scenario-snapshot,
  evidence, and derived-measure claims must use existing experiment reference
  types and cross-artifact validators. Integrity claims that depend on bytes
  must bind to artifact checksums, manifest payload digests, or evidence
  records that can be validated.
- Control-plane/API gate, if exposed: use strict default auth, role-scoped
  read/mutation dependencies, request-size guards, idempotency, audit events,
  published request/response models, and redacted error envelopes. Asset trust
  status must not grant authorization by itself.
- Secret-handling gate: portable artifacts carry refs, digests, checksums,
  markings, provenance, and loss/redaction disclosure. They must not carry
  bearer tokens, private keys, raw credentials, hidden prompts, answer keys,
  private backend config, environment dumps, raw command output, or unchecked
  registry credentials.
- OS/process exposure gate: do not introduce subprocess shells, token-bearing
  command lines, environment-variable policy channels, or process-argv secrets.
  Existing publishing may read an explicit private-key path; implementations
  must not log, persist, echo, or copy key material.
- Error-envelope gate: module and SDL failures stay on `SDLParseError` /
  `SDLValidationError`; contract/conformance failures stay on `Diagnostic`;
  HTTP failures stay on bounded `HTTPException`/JSON detail. Messages may name
  the failed field, ref, digest class, or policy id, but not raw payloads,
  secrets, tracebacks, or full rejected artifacts.

## Extensibility Seam

The extension seam is asset-family classification over existing reference and
policy surfaces:

- modules: `TrustPolicy`, `RegistryTrustPolicy`, `ImportDecl`, `LockRecord`,
  digest/signature/export/hash checks, and module provenance side channels;
- scenarios: `scenario` versus `scenario-snapshot` references, with digest
  binding only at the snapshot/evidence boundary;
- tasks, runs, and studies: experiment-core refs, artifacts, checksums,
  apparatus context, traceability, and task/run/study semantic validators;
- behavior vocabularies: controlled-vocabulary catalogs, source digests,
  governed extensions, and concept bindings;
- participant implementations and manifests: manifest/provenance contracts,
  selected manifest/configuration digests, and exposure policies; and
- profiles or future corpus families: `aces_contracts.corpus` plus the
  authority-boundary manifest.

The obvious future parameter is `asset_family` or `ref_kind` paired with an
evidence requirement such as digest, signature, lock record, governed
vocabulary source, or artifact checksum. Add new asset families by extending
the relevant existing catalog, reference type, trust policy, or validator.
Do not route every future variation through one generic reusable-asset payload.

If operator-tunable module trust changes are needed, the seam is
`RegistryTrustPolicy` with bounded validated fields. If contract-level policy
selection is needed, the seam is a small published contract keyed by existing
contract ids, concept/vocabulary ids, and experiment `ref_kind` values. In both
cases, one future variation should not require edits to parser, compiler,
runtime, backend, control-plane, and conformance code at once.

## Gotchas And Anti-Patterns

Avoid:

- creating a universal `TrustedAsset`, `ReusableAsset`, or top-level SDL
  `reusable_assets` section that collapses modules, scenarios, experiment
  tasks, studies, vocabularies, manifests, and evidence artifacts;
- adding digest/path/signature fields to reference types that have no concrete
  payload validator;
- treating a scenario id, module id, task id, study id, vocabulary label, or
  profile id as proof of authenticity or integrity;
- treating the expanded scenario as the only review artifact when fragment,
  namespace, lock record, source digest, or mapping-ledger provenance matters;
- duplicating module registry, lockfile, trust-policy, vocabulary catalog,
  schema manifest, fixture loader, conformance runner, diagnostic model,
  exception hierarchy, audit log, or persistence stack;
- moving reusable asset authority into Python models, examples, explanatory
  docs, issue notes, or compatibility wrappers;
- accepting arbitrary external taxonomy labels, registry names, signer ids, or
  policy strings as portable ACES values outside governed vocabularies or
  explicit trust policy fields;
- using backend logs, runtime snapshots, evaluator details, or control-plane
  audit records as the canonical reusable-asset integrity record without
  projecting them into evidence/provenance contracts;
- weakening resource limits, tar extraction hardening, signature binding,
  digest verification, lockfile drift checks, redaction rules, or error
  redaction to make asset reuse easier; and
- putting credentials, private keys, tokens, hidden prompts, answer keys,
  registry auth, private config, or raw evidence payloads in fixtures,
  diagnostics, logs, CLI output, changelog fragments, schemas, or examples.

## Non-Goals

- Implementing GOV-913 behavior in this preflight note.
- Adding new SDL syntax, module source classes, lockfile schema, trust-policy
  files, contract schemas, fixtures, conformance cases, API routes, storage,
  registry services, signer discovery, key rotation, or runtime emission.
- Redesigning module composition, parser normalization, semantic validation,
  experiment-core reference semantics, participant implementation provenance,
  concept-authority governance, schema publication, or control-plane security.
- Standardizing a hosted ACES asset registry, package repository, certificate
  authority, transparency log, revocation service, or policy distribution
  mechanism.
- Promoting docs, examples, tests, runtime logs, backend-private state, or
  generated Python schemas to normative reusable-asset authority.
