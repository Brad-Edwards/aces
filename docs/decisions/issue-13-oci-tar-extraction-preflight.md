# Issue 13 OCI Tar Extraction Preflight

Date: 2026-06-21

Issue: #13.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for closing the unsafe OCI
module bundle extraction path on supported Python runtimes. It is guidance for
implementation only: it does not change resolver behavior, tests, changelog, or
published SDL documentation.

## Binding Sources

- ADR-053 owns SDL module composition: remote modules are resolved through the
  module registry, checked against trust/digest/version/export policy, expanded
  before semantic validation, and then compiled as one canonical scenario.
- `aces_sdl.module_registry` owns OCI source parsing, trust policy loading,
  registry fetches, digest verification, signature verification, cache
  placement, bundle extraction, `root_file` resolution, lock records, and
  resolved import identity.
- `ImportDecl`, `ModuleDescriptor`, `TrustPolicy`, `RegistryTrustPolicy`,
  `Lockfile`, and `ResolvedModule` are the canonical model surfaces. Do not add
  a second OCI bundle schema or resolver DTO for this bug.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and
  `implementations/python/pyproject.toml` define the verification graph and
  Python support floor (`requires-python = ">=3.11"`).

## Architecture Decisions

- Fail closed on every supported runtime. Python 3.11 cannot call
  `TarFile.extractall(..., filter="data")`, so the design must not rely on
  catching `TypeError` and then calling unfiltered `extractall(...)`.
- Keep one private OCI bundle extraction policy in `aces_sdl.module_registry`.
  The resolver, CLI, parser, and composition layer should consume that policy
  through `resolve_import()` / `_extract_bundle_to_cache()`, not duplicate tar
  validation.
- Treat remote OCI bundle bytes as attacker-controlled even after registry
  allowlist, digest pinning, and signature checks. Those checks prove identity
  and integrity; they do not make tar member paths safe to apply to the local
  filesystem.
- Validate the complete member list before writing any member. Reject absolute
  paths, parent-directory segments, host-dependent drive/root spellings,
  symlinks, hard links, device nodes, FIFOs, and any member type outside
  regular files and directories.
- Validate `root_file` with the same cache-containment policy after
  normalization. The resolved root must remain inside
  `.aces/module-cache/<manifest-digest>/` and must be an extracted regular file.
- Preserve existing OCI lock and trust behavior. The fix is an extraction
  hardening change, not a change to source syntax, lockfile identity,
  signature policy, digest semantics, or module descriptor validation.

## Required Incumbents

- Resolver and supply-chain checks: `_parse_oci_source()`,
  `_registry_base_url()`, `_json_request()`, `_bytes_request()`,
  `_select_tag()`, `_validate_digest_pin()`, `_verify_signatures()`,
  `_verify_allowed_parameters()`, `_descriptor_digest()`, and
  `_oci_cache_dir()`.
- Models and validation: `SDLModel(extra="forbid")`, `ImportDecl`,
  `ModuleDescriptor`, `TrustPolicy`, `RegistryTrustPolicy`, `Lockfile`,
  `LockRecord`, and `ResolvedModule`.
- Parse and composition flow: `_load_normalized_data()`,
  `parse_sdl_file()`, `aces_sdl.composition.expand_sdl_modules()`, import cycle
  detection, namespace rewriting, and whole-scenario `SemanticValidator`
  validation.
- Error handling: use `SDLParseError` for resolver failures and keep CLI
  exposure through the existing Typer command envelopes. Do not add a tar- or
  registry-specific exception hierarchy.
- Tests and workflow: extend `implementations/python/tests/test_sdl_module_registry.py`
  for malicious tar members and `root_file` escapes; run the canonical
  `nox -s tests`, `nox -s lint`, `nox -s hygiene`, and `nox -s verify` graph as
  appropriate for the implementation.
- Security lint posture: `module_registry.py` already carries the narrow Ruff
  Bandit ignores for explicit OCI URL fetch and tar extraction. Do not broaden
  ignores globally; the extraction call must remain justified by local policy
  tests.

## Cross-Cutting Layers

- YAML/config parsing: imported `root_file`, module descriptors, trust policy,
  and lockfiles still enter through existing Pydantic models and parser
  helpers. No ad hoc YAML or JSON parser should be introduced.
- Registry trust policy: preserve registry allowlists, insecure-HTTP opt-in,
  signature requirement, trusted signer matching, version selection, digest
  pins, lockfile digest checks, and export-hash checks before parsing the
  extracted module.
- Filesystem boundary: all writes are confined to the digest-keyed cache
  directory under the SDL base directory. Path checks must be based on resolved
  containment, not string prefix comparisons.
- OS/process exposure: this issue should add no shell commands, subprocesses,
  environment variables, tokens, private keys, or process-argv secrets. It only
  consumes already-fetched bundle bytes in memory.
- Error envelope: failures should name the unsafe member or invalid
  `root_file`, but should not print bundle contents, config payloads, private
  key material, registry credentials, environment values, or tracebacks.
- Runtime/backend layers: compiled scenarios and runtime managers see only the
  already-expanded canonical scenario. They must not learn about tar members,
  cache internals, or module source-file layout.
- Repository policy: implementation belongs under
  `implementations/python/packages/aces_sdl/` with focused tests under
  `implementations/python/tests/`; user-visible security behavior needs a
  `changelog.d/13.security.md` fragment when the code fix lands.

## Extension Boundary

The extensibility seam is the private bundle extraction policy, parameterized by
destination cache directory and declared root file. Future changes such as
alternate archive formats, stricter member metadata policy, cache atomicity, or
additional remote source classes should plug into that seam without changing
CLI comparison logic, parser behavior, lockfile serialization, or runtime
contracts.

Keep the seam about extraction safety only. Source identity remains
`resolved_source`; runtime reads use `ResolvedModule.root_file`; cache keying
uses the manifest digest; content integrity uses the bundle digest.

## Gotchas And Anti-Patterns

Avoid:

- retaining any path that calls `tar.extractall(cache_dir)` on Python 3.11;
- treating `members=` alone as equivalent to Python 3.12 `filter="data"` if the
  implementation still accepts links, special files, ownership, or dangerous
  permission metadata;
- validating only the final resolved path while allowing literal `..` segments
  in member names or `root_file`;
- using host-dependent `Path` parsing before accounting for tar's POSIX path
  format and Windows drive/backslash edge cases;
- checking `root_path.exists()` as the only proof that the cached extraction is
  safe across different manifest or bundle identities;
- extracting members one by one before the full archive has passed policy;
- conflating OCI module bundles with the reference backend OCI container
  driver or Docker/Podman runtime behavior;
- changing `manifest_digest`, `content_digest`, `resolved_source`, `root_file`,
  or `module.id` meanings while fixing extraction;
- adding duplicate schemas, duplicate validators, duplicate resolver services,
  duplicate exception types, or compatibility-wrapper logic under
  `implementations/python/src/aces/`;
- widening the bug into registry operations, cache eviction, signer
  distribution, lockfile migration, module publishing redesign, or runtime
  planning changes.

## Non-Goals

- Implementing the extraction fix, tests, changelog, or docs updates in this
  preflight.
- Changing SDL import source classes, module descriptor semantics, trust policy
  defaults, lockfile schema, OCI publishing layout, or CLI command names.
- Changing parser normalization, semantic validation, instantiation, compiler,
  runtime, control-plane, backend conformance, MCP, or reference backend OCI
  behavior.
- Raising the Python support floor as the primary fix unless the project makes
  a separate explicit runtime-support decision.
