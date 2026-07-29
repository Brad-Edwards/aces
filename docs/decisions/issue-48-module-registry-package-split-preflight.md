# Issue 48 Module Registry Package Split Preflight

Date: 2026-07-29

Issue: #48.

Requirement: none. The GitHub issue is the delivery contract. This note records
architecture guardrails only; it does not implement the split.

## Current-Tree Reconciliation

The issue's historical module path (from the retired pre-#884 SDL namespace) no
longer exists. The current, sole SDL namespace is `raes` (ADR-093 and the #884
hard cut), so the
target is `implementations/python/packages/raes/module_registry.py` and the
stable import is `raes.module_registry`. The current file is 897 lines.

ADR-015's amended source-file cap is **500 lines**, not the issue's historical
600-line figure. The split must therefore leave every non-test Python source
file in `raes/module_registry/` at or below 500 lines and remove the current
`raes/module_registry.py` entry from `tools/policy/oversized_allowlist.yaml`.

## Decisions And Boundaries

- Convert the module into a package with a deliberately thin `__init__.py`
facade. It must re-export every existing supported import name used by
`raes.composition`, `raes_cli.sdl`, tests, documentation, and any declared
public API. Do not introduce a retired-namespace alias, compatibility import hook,
or second resolver entry point. The current module has no `__all__`; do not
add a restrictive one that changes existing star-import semantics.
- Partition by existing responsibility, not by arbitrary line count: (1)
  Pydantic policy/lock and resolved-module models plus deterministic lockfile
  persistence; (2) local/locked/OCI resolution orchestration; (3) OCI
  transport, trust, signature, digest, cache, and archive safety boundary; and
  (4) OCI-layout publishing. Shared digest/version/descriptor helpers belong
  with the smallest existing dependency direction, rather than in a new
  generic utility layer.
- The OCI boundary must remain one cohesive security boundary. Its URL parsing,
  trust-policy lookup, explicit timeout, capped reads, JSON decoding order,
  manifest/config/bundle digest checks, signature binding, archive-member
  validation, cache containment, and root-file check must not be split across
  parser, CLI, composition, runtime, or backend modules.
- Preserve the exact existing model and error authority: `SDLModel`,
  `ImportDecl`, `ModuleDescriptor`, `TrustPolicy`, `RegistryTrustPolicy`,
  `Lockfile`, `LockRecord`, `ResolvedModule`, `SDLParseError`, and
  `SDLValidationError`. The refactor creates neither a second schema/DTO nor a
  registry-specific exception or logging path.

## Compatibility Guardrails

`test_sdl_module_registry.py` imports `raes.module_registry` as a module and
patches/uses private OCI seams on that module (`urlopen`, `_OCI_LIMITS`,
`_json_request`, `_bytes_request`, `_safe_tar_members`,
`_extract_bundle_to_cache`, `_oci_cache_dir`, `_sha256_digest`,
`_signable_payload`, and `_verify_signatures`). These are existing in-repo
behavioral seams even though they are private.

The package facade must preserve their names and patch behavior without
modifying pre-existing tests. Simple `from .oci import name` re-exports are
insufficient when an implementation function resolves a patched dependency
from its own module globals. Keep a narrow facade-compatible indirection (or
an equivalent single injected dependency seam) so patches to
`raes.module_registry.urlopen` and `raes.module_registry._OCI_LIMITS` affect
the request and archive paths exactly as before. Do not solve this by changing
tests, exposing a broad new public test API, or duplicating OCI logic.

## Cross-Cutting Obligations

- **Trust/config:** continue to parse `raes-trust.yaml` only through
  `TrustPolicy`/`RegistryTrustPolicy` Pydantic validation; retain defaults and
  `extra="forbid"` behavior inherited from `SDLModel`.
- **Supply chain and filesystem:** preserve registry allowlisting,
  insecure-HTTP opt-in, version selection, digest pins, lockfile checks,
  Ed25519 verification, bounded reads, archive validation before extraction,
  cache-root containment, and cache-hit root-file validation. A move must not
  alter error order or create a bypass.
- **Parser/composition:** continue to use the existing normalized-source
  parser, `ImportDecl`/`ModuleDescriptor` validation, and `resolve_import()` /
  `ResolvedModule` contract. `raes.composition` remains the sole expansion
  consumer; it must not learn OCI internals.
- **Error and process exposure:** preserve `SDLParseError`/Typer envelopes;
  do not add logging, environment configuration, subprocesses, credentials,
  secrets in argv, or response/body/key material in errors.
- **Build and policy:** retarget the narrow Ruff `S310`/`S202` suppression in
  `implementations/python/pyproject.toml` to only the new OCI implementation
  file. Do not broaden it to the package or remove it while the explicit URL
  fetch/tar extraction remains. Preserve Hatch package discovery and the API
  documentation's `raes.module_registry` path.
- **Release record:** the issue requests a `CHANGELOG.md` entry, but the
  repository's authoritative `.gc/plan-rules.md` forbids hand-editing that
  file or adding fragments; release-please generates it from the conventional
  commit on `main`. The implementation must leave `CHANGELOG.md` untouched and
  use an appropriate non-behavior-changing conventional commit/PR title (for
  example `refactor:`). This is the only repository-compliant interpretation
  of that acceptance item.

## Extensibility Seam And Non-Goals

The sole future extension seam remains the private registry-resolution policy:
source class plus SDL base directory, existing trust policy, and the private
OCI resource-limit policy. A future import source or tunable OCI limit adds to
that seam; it must not require parser/compiler/runtime/CLI-specific resolver
variants or a new lockfile schema.

This is a pure structural refactor. It must not change import syntax, schemas,
lockfile contents/serialization, resolved-source semantics, trust defaults,
signature payloads, cache layout, OCI publishing layout, CLI behavior,
composition order, validation, runtime behavior, or pre-existing tests. Do
not modify external `raes.module_registry` import lines, use wildcard exports,
or widen the work into registry authentication, cache redesign, observability,
or the legacy namespace.
