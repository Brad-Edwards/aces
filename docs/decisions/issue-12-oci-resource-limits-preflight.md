# Issue 12 OCI Import Resource Limits Preflight

Date: 2026-07-01

Issue: #12.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture preflight guardrails for bounding OCI module
registry fetches and archive extraction. It is implementation guidance only:
it does not change resolver behavior, tests, changelog, schemas, or published
SDL documentation.

## Binding Sources

- ADR-053 owns SDL module composition. Remote modules are resolved through the
  module registry before semantic validation, then downstream parser,
  validator, compiler, runtime, and backend code see one canonical expanded
  scenario.
- `aces_sdl.module_registry` owns OCI source parsing, trust policy loading,
  registry fetches, digest verification, signature verification, cache
  placement, bundle extraction, `root_file` resolution, lock records, and
  resolved import identity.
- `docs/decisions/issue-13-oci-tar-extraction-preflight.md` owns the existing
  tar path-safety guardrails. Issue #12 extends that boundary with network and
  extracted-size limits; it must not replace or weaken the issue #13 path,
  member-type, link, mode, and root-file containment rules.
- `ImportDecl`, `ModuleDescriptor`, `TrustPolicy`, `RegistryTrustPolicy`,
  `Lockfile`, `LockRecord`, and `ResolvedModule` are the canonical model
  surfaces. Do not add a second OCI module schema, resolver DTO, exception
  hierarchy, or workflow path for this bug.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and
  `implementations/python/pyproject.toml` define the verification graph and
  the narrow security-lint posture for explicit OCI URL fetch and tar
  extraction.

## Architecture Decisions

- Keep the resource-limit policy inside the SDL module registry boundary.
  Parser, composition, semantic validation, compiler, runtime manager,
  reference backend OCI driver, and MCP tooling should continue to consume only
  `resolve_import()` / `ResolvedModule`.
- Enforce limits before buffering untrusted network responses. Manifest,
  config, tag-list metadata, and bundle blob reads must use a counted read path
  with explicit timeout and maximum bytes; `Content-Length` may reject early
  but must not be trusted as the only check.
- Use separate limits for compressed response bytes and extracted archive
  bytes. A valid small gzip can expand into a large tar payload, so the archive
  policy must cap member count, per-file size, and total regular-file bytes
  before any filesystem write.
- Treat OCI descriptor `size` fields as early rejection hints only. The
  resolver still needs actual byte-count enforcement and digest verification
  on the bytes received from the registry.
- Fail closed through existing `SDLParseError` failures. Error messages may
  identify the limit class, safe URL identity, digest, member name, and limit
  value, but must not echo response bodies, config payloads, private keys,
  environment values, credentials, or tracebacks.
- Preserve existing trust, lock, and identity semantics. A size-limit fix must
  not change source syntax, registry allowlist behavior, insecure-HTTP opt-in,
  signature policy, version selection, digest pins, export-hash checks,
  `manifest_digest`, `content_digest`, `resolved_source`, or `root_file`
  meanings.

## Required Incumbents

- Resolver and supply-chain checks: `_parse_oci_source()`,
  `_registry_base_url()`, `_json_request()`, `_bytes_request()`,
  `_select_tag()`, `_validate_digest_pin()`, `_verify_signatures()`,
  `_verify_allowed_parameters()`, `_descriptor_digest()`, and
  `_oci_cache_dir()`.
- Bundle filesystem policy: `_safe_tar_members()` and
  `_extract_bundle_to_cache()`, including the issue #13 full-archive validation
  before extraction and cache-hit root-file containment check.
- Models and validation: `SDLModel(extra="forbid")`, `ImportDecl`,
  `ModuleDescriptor`, `TrustPolicy`, `RegistryTrustPolicy`, `Lockfile`,
  `LockRecord`, and `ResolvedModule`.
- Parse and composition flow: `_load_normalized_data()`,
  `parse_sdl_file()`, `aces_sdl.composition.expand_sdl_modules()`, import cycle
  detection, namespace rewriting, and whole-scenario `SemanticValidator`
  validation.
- Request-size precedent: `aces_runtime.control_plane_api_guards` uses a
  two-stage `Content-Length` plus actual-body-size check. Reuse the pattern,
  not the FastAPI-specific implementation, for remote OCI response bounds.
- Error handling: use `SDLParseError` for resolver failures and keep CLI
  exposure through the existing Typer command envelopes. Do not add
  registry-specific public exceptions or diagnostic models.
- Tests and workflow: extend `implementations/python/tests/test_sdl_module_registry.py`
  and its in-process OCI registry/test doubles for timeout, bounded reads,
  missing/oversized `Content-Length`, manifest/config/blob limits, tar member
  count, per-member size, and extracted total. Keep the per-file Ruff Bandit
  ignores in `implementations/python/pyproject.toml` narrow.

## Cross-Cutting Layers

- Trust-policy/config gate: `aces-trust.yaml` enters only through
  `TrustPolicy` and `RegistryTrustPolicy`. If public operator-tunable limits
  are added, they belong on this existing Pydantic config surface with bounded
  numeric validation. Do not add environment-variable-only, CLI-only, or
  duplicated YAML parsing for limits.
- Registry auth/source gate: OCI imports still require an allowed registry,
  respect `allow_insecure_http`, and must not introduce credentials in source
  strings, process argv, logs, or exception messages. This issue adds no auth
  mechanism.
- Network I/O gate: all `urlopen` calls must pass an explicit timeout and feed
  a single bounded reader. The bounded reader must enforce limits even when
  `Content-Length` is absent, invalid, or understated.
- JSON/parser gate: tag lists, manifests, and config payloads are decoded only
  after byte limits pass. Existing JSON and Pydantic validation remain the
  structural authority; do not validate config by ad hoc string inspection.
- OCI integrity gate: manifest, config, and bundle bytes remain digest-checked
  against the identities already carried in the OCI manifest, lockfile, and
  import digest pins. Descriptor `size` checks do not replace digest checks.
- Archive/filesystem gate: extraction remains confined to
  `.aces/module-cache/<manifest-digest>/`; member policy must account for
  member count, regular-file size, and total extracted bytes before calling
  `extractall()`. Path containment, link rejection, special-file rejection,
  root-file containment, and mode hardening from issue #13 remain mandatory.
- Persistence/cache gate: the module cache remains the only write surface.
  Limit enforcement must happen before new extraction writes. Cache-hit logic
  still has to validate the returned root file, and the implementation must not
  use stale cache content to bypass resource checks for a newly fetched bundle.
- Runtime/backend gate: compiled scenarios and runtime managers see only the
  expanded canonical scenario. Do not leak OCI byte limits, tar member details,
  cache internals, or registry response shapes into runtime contracts,
  backend conformance, or the reference backend OCI container driver.
- Error-envelope gate: public failures stay on `SDLParseError` /
  `SDLValidationError` and Typer's existing command failure envelope. Limit
  messages should be deterministic and redacted.

## Extension Boundary

The extensibility seam is one private OCI resource-limit policy used by both
network fetch and archive extraction. It should carry, at minimum, timeout,
maximum manifest/config/metadata bytes, maximum bundle blob bytes, maximum tar
members, maximum per-member extracted bytes, and maximum total extracted bytes.

The first implementation may use private defaults. If the project later needs
operator-specific tuning, extend `RegistryTrustPolicy` with validated optional
overrides and merge them with the same private defaults. Do not thread ad hoc
limit arguments through parser, compiler, runtime, CLI command bodies, or the
reference backend driver.

## Gotchas And Anti-Patterns

Avoid:

- calling `response.read()` without a maximum or without counting streamed
  chunks;
- trusting `Content-Length` alone, or accepting invalid/negative response
  lengths;
- applying one global byte limit to both compressed downloads and extracted
  files;
- using `tar.getmembers()` as the only member-count guard if it materializes an
  unbounded metadata list before the cap is checked;
- validating only total extracted bytes while allowing one pathological member
  to exceed a per-member limit;
- extracting any member before the full archive has passed path, type, count,
  per-member, and total-size policy;
- letting duplicate normalized member paths or sparse/unknown tar types bypass
  accounting;
- reporting raw response bodies, config JSON, bundle bytes, private keys,
  registry credentials, or environment values in exceptions or logs;
- conflating SDL OCI module resolution with
  `aces_reference_backend.drivers.oci`, Docker/Podman image realization, or
  runtime backend policy;
- changing public lockfile, trust-policy, module descriptor, import source,
  parser, semantic validator, runtime, or backend schemas unless the
  implementation deliberately adds validated `RegistryTrustPolicy` limit
  fields;
- broadening Ruff/Bandit ignores, adding compatibility-wrapper logic under
  `implementations/python/src/aces/`, or adding duplicate resolver services.

## Non-Goals

- Implementing the size-limit fix, tests, changelog, or public docs in this
  preflight.
- Redesigning registry authentication, signer distribution, lockfile schema,
  module publishing layout, cache eviction, atomic cache repair, or OCI
  distribution compliance.
- Changing SDL import source classes, trust defaults, lock identity, digest
  semantics, module descriptor semantics, namespace rewriting, parser
  normalization, semantic validation, instantiation, compiler, runtime,
  control-plane, MCP, or reference backend OCI behavior.
- Raising the Python support floor as the primary fix.
