# Issue 14 OCI Config Integrity Preflight

Date: 2026-07-03

Issue: #14.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture preflight guardrails for binding OCI module
config bytes and `root_file` into the resolver's existing trust model. It is
implementation guidance only: it does not change resolver behavior, tests,
changelog, schemas, or published SDL documentation.

## Binding Sources

- ADR-053 owns SDL module composition. Remote modules are resolved through the
  module registry before semantic validation, then downstream parser,
  validator, compiler, runtime, and backend code see one canonical expanded
  scenario.
- `aces_sdl.module_registry` owns OCI source parsing, trust policy loading,
  registry fetches, digest verification, signature verification, cache
  placement, bundle extraction, `root_file` resolution, lock records, and
  resolved import identity.
- `docs/decisions/issue-12-oci-resource-limits-preflight.md` owns bounded
  remote fetch and extraction-size guardrails. Config integrity must reuse the
  same capped fetch path.
- `docs/decisions/issue-13-oci-tar-extraction-preflight.md` owns bundle member
  safety and `root_file` containment. Config integrity must bind the selected
  `root_file`; extraction still enforces the final filesystem boundary.
- `docs/decisions/issue-551-import-lockfile-portability-preflight.md` preserves
  the distinction between persisted lock identity, runtime `root_file`, and OCI
  registry/digest identity. Do not conflate those fields while fixing this
  issue.
- `ImportDecl`, `ModuleDescriptor`, `TrustPolicy`, `RegistryTrustPolicy`,
  `Lockfile`, `LockRecord`, and `ResolvedModule` are the canonical model
  surfaces. Do not add a second OCI resolver contract, lockfile schema,
  exception hierarchy, or workflow path for this bug.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and
  `implementations/python/pyproject.toml` define the repository workflow,
  verification graph, Python support floor, and narrow security-lint posture for
  explicit OCI URL fetch and tar extraction.

## Architecture Decisions

- Treat the OCI config object as the binding document between the manifest
  descriptor, module descriptor, signatures, declared `root_file`, and bundle
  layer digest. The resolver must not parse or trust config JSON until the
  fetched config bytes hash exactly to the manifest's `config.digest`.
- Verify the config blob using the existing byte-level digest helper and digest
  spelling: `sha256:<_sha256_digest(config_bytes)>`. OCI descriptor `size`,
  HTTP `Content-Length`, and media type checks may reject early, but they do not
  replace hashing the actual bytes received.
- Keep config fetches on `_bytes_request()` with the metadata byte limit and
  timeout from the issue #12 resource-limit boundary. Do not introduce another
  network reader or unbounded `response.read()` path.
- Include the config-declared `root_file` in the signed payload used by both
  publishing and resolving. `_signable_payload()` is the single canonical signer
  payload builder; `_verify_signatures()` and
  `publish_module_to_oci_layout()` must consume the same payload shape.
- Fail closed for required signatures produced over the old payload that omitted
  `root_file`. A compatibility fallback would preserve the semantic
  substitution bug for registries where signatures are supposed to be the trust
  boundary.
- Preserve digest and identity meanings: `manifest_digest` is the digest of the
  manifest bytes, `content_digest` is the bundle/layer digest, `root_file` is the
  config-declared module entrypoint inside the verified bundle, and
  `resolved_source` remains registry/repository plus manifest digest.
- Validate the config `root_file` as one string value before it reaches the
  signature payload or extraction. The final containment and regular-file check
  remains `_extract_bundle_to_cache()`, including cache-hit validation.
- Defer "sign the full canonical config object" to a later explicit design
  decision. If that change lands, extend the single signing seam with a payload
  version or canonical unsigned-config payload; do not add a parallel signature
  verifier beside `_signable_payload()` / `_verify_signatures()`.

## Required Incumbents

- Resolver and supply-chain checks: `_parse_oci_source()`,
  `_registry_base_url()`, `_json_request()`, `_bytes_request()`,
  `_read_capped()`, `_select_tag()`, `_sha256_digest()`,
  `_validate_digest_pin()`, `_signable_payload()`, `_verify_signatures()`,
  `_verify_allowed_parameters()`, `_descriptor_digest()`, and
  `_oci_cache_dir()`.
- Bundle filesystem policy: `_safe_tar_members()` and
  `_extract_bundle_to_cache()`, including full-archive validation before
  extraction and cache-hit root-file containment.
- Models and validation: `SDLModel(extra="forbid")`, `ImportDecl`,
  `ModuleDescriptor`, `TrustPolicy`, `RegistryTrustPolicy`, `Lockfile`,
  `LockRecord`, and `ResolvedModule`.
- Parse and composition flow: `_load_normalized_data()`, `parse_sdl_file()`,
  `aces_sdl.composition.expand_sdl_modules()`, import cycle detection, namespace
  rewriting, and whole-scenario `SemanticValidator` validation.
- Error handling: use `SDLParseError` for resolver failures and keep CLI
  exposure through the existing Typer command envelopes. Do not add
  registry-specific public exceptions or diagnostic models.
- Tests and workflow: extend
  `implementations/python/tests/test_sdl_module_registry.py` and its in-process
  OCI registry/test doubles for config digest mismatch, root-file signature
  tampering, publishing/resolving payload parity, and no legacy-signature
  fallback when `require_signatures` is true. Keep the per-file Ruff Bandit
  ignores in `implementations/python/pyproject.toml` narrow.

## Cross-Cutting Layers

- Trust-policy/config gate: `aces-trust.yaml` enters only through
  `TrustPolicy` and `RegistryTrustPolicy`; OCI imports still require an allowed
  registry, respect `allow_insecure_http`, and use trusted signer ids from that
  existing policy surface.
- Network I/O gate: all manifest, config, tag-list, and bundle reads stay on the
  timeout-bounded `_json_request()` / `_bytes_request()` path. Limits are
  enforced on bytes actually read, not only on advisory headers.
- OCI descriptor/integrity gate: manifest bytes are hashed for lockfile
  identity, config bytes are hashed against `manifest.config.digest`, bundle
  bytes are hashed against the layer digest, import digest pins check
  `content_digest`, and lockfile checks preserve existing manifest/module/export
  comparisons.
- JSON/model gate: config JSON is decoded only after config digest verification.
  Module descriptor validation remains `ModuleDescriptor.model_validate()`. Any
  additional private config shape check should use the local `SDLModel` pattern
  rather than a public contract schema for this private OCI layout.
- Signature gate: Ed25519 verification remains `_verify_signatures()` over the
  canonical `_signable_payload()`. The payload must bind `module_id`,
  `module_version`, `exports`, `content_digest`, and `root_file`.
- Archive/filesystem gate: extraction remains confined to
  `.aces/module-cache/<manifest-digest>/`; `_extract_bundle_to_cache()` still
  rejects escaping, missing, non-regular, or stale-cache `root_file` results.
- Parser/semantic gate: after resolution, the selected root file still flows
  through `_load_normalized_data()`, module expansion, Pydantic scenario
  construction, and whole-scenario semantic validation. Runtime layers do not
  learn OCI config internals.
- Error-envelope gate: public failures stay on `SDLParseError` /
  `SDLValidationError` and Typer's existing command failure envelope. Messages
  may name the digest class or invalid field, but must not echo config bodies,
  bundle bytes, signatures, private keys, registry credentials, environment
  values, or tracebacks.
- OS/process exposure gate: this issue should add no subprocesses, shell
  commands, environment variables, tokens, process-argv secrets, or new
  credential sources. Existing publishing may read the explicit private key
  path; the fix must not log or persist key material.
- Repository policy gate: implementation belongs under
  `implementations/python/packages/aces_sdl/` with focused tests under
  `implementations/python/tests/`; do not add implementation logic to
  `implementations/python/src/aces/`. User-visible security behavior needs a
  `changelog.d/14.security.md` fragment when the code fix lands.

## Extension Boundary

The extensibility seam is one private OCI config-integrity and signature-binding
path in `aces_sdl.module_registry`:

- raw config bytes are fetched through `_bytes_request()`;
- byte integrity is checked with `_sha256_digest()` against
  `manifest.config.digest`;
- the config-declared `root_file` is normalized once; and
- `_signable_payload()` receives that `root_file` alongside the module
  descriptor and bundle `content_digest`.

Future variants such as signature payload versioning, signing a canonical
unsigned config object, additional descriptor checks, or operator-tunable config
limits should extend that seam. They should not thread separate root-file or
signature rules through parser, compiler, runtime, CLI command bodies, lockfile
comparison, or the reference backend OCI container driver.

## Gotchas And Anti-Patterns

Avoid:

- decoding or inspecting the config JSON before verifying the fetched config
  bytes against `config.digest`;
- trusting descriptor `size`, `mediaType`, or HTTP `Content-Length` as a
  substitute for byte hashing;
- hashing a reserialized JSON object instead of the exact bytes returned by the
  config blob endpoint;
- verifying signatures with a default `root_file` while extracting a different
  config-declared `root_file`;
- accepting old signatures that omit `root_file` when `require_signatures` is
  true;
- signing absolute paths, cache paths, `Path` reprs, or publisher-local paths
  instead of the OCI config's normalized `root_file` string;
- changing `content_digest` to mean config digest, adding `config_digest` to the
  lockfile as a second trust anchor, or weakening manifest digest lock checks;
- adding a public `contracts/` schema for this private OCI config shape unless a
  separate publication decision is made;
- broadening Ruff/Bandit ignores, adding compatibility-wrapper logic under
  `implementations/python/src/aces/`, or adding duplicate resolver services;
- conflating SDL OCI module resolution with
  `aces_reference_backend.drivers.oci`, Docker/Podman image realization, or
  runtime backend policy;
- widening the bug into registry authentication, signer distribution, cache
  eviction, atomic cache repair, lockfile migration, or OCI distribution
  compliance.

## Non-Goals

- Implementing the config-integrity fix, tests, changelog, or public docs in
  this preflight.
- Changing SDL import source classes, trust defaults, lockfile schema,
  `ModuleDescriptor` semantics, namespace rewriting, parser normalization,
  semantic validation, instantiation, compiler, runtime, control-plane, MCP, or
  reference backend OCI behavior.
- Providing compatibility for signed OCI modules whose required signatures were
  generated without binding `root_file`.
- Redesigning registry authentication, signer discovery, certificate handling,
  key rotation, publishing layout, cache eviction, cache atomicity, or OCI
  registry operations.
