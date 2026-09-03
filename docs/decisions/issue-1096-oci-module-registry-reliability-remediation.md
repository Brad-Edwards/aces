# Issue 1096 OCI Module Registry Reliability Remediation

Date: 2026-08-11

Issue: [#1096](https://github.com/OpenRAE/rae/issues/1096).

Requirement: GOV-913.

This note records the implementation defense for deterministic OCI module
publication, transactional extraction caching, and stable registry failures. It
changes implementation behavior and operator documentation only. It adds no SDL
field, portable contract, schema, registry service, key-distribution mechanism,
or backend protocol.

Issue [#1107](https://github.com/OpenRAE/rae/issues/1107) subsequently found
that the digest-only cache marker, two-directory replacement, and post-parse
tar limits below were insufficient. The current implementation strengthens
them with pre-parse whole-stream gzip bounds, a canonical full-tree cache
manifest, immutable version directories, and one atomic pointer. The issue
#1107 preflight is the controlling implementation defense where this historical
note describes the earlier marker or backup/rollback protocol.

## Gap claim and ownership

The existing architecture already had the correct owners: the module registry
owns bundle bytes, OCI descriptors, signatures, registry reads, and extraction.
The defect was that several implementation details were not canonical or
transactional. The remediation therefore hardens those incumbents rather than
introducing a second registry, cache, trust model, exception hierarchy, or
runtime adapter.

| Root cause | Consequence | Owning requirement | Remediation |
| --- | --- | --- | --- |
| `tarfile` and gzip inherited creation time and host metadata | Identical modules could receive different bundle, manifest, and lock digests | GOV-913 | Sort POSIX names and normalize gzip filename/mtime/compression plus tar uid, gid, owner names, mode, and mtime. |
| Relative and symlink entrypoints were used before one strict canonical resolution | Bundle membership and `root_file` could depend on invocation spelling | GOV-913 | Resolve the entrypoint once, derive one canonical publishing root, and contain every local import within it. |
| Cache identity used only the manifest directory and wrote extraction directly there | A stale, mismatched, concurrent, interrupted, or locally modified entry could be reused | GOV-913 | Bind a canonical complete-tree manifest to the verified layer digest, serialize with per-entry thread and OS locks, validate in a sibling stage, install an immutable version, and atomically replace one pointer. |
| Partial signing options silently produced unsigned output | Operator intent could be downgraded without a failure | GOV-913 | Require both signer id and readable valid Ed25519 PEM key, or neither; reject whitespace-confused ids and sanitize key errors. |
| OCI layouts were updated in place | Stale blobs/files survived and failed writes exposed partial inventory | GOV-913 | Build and validate the exact inventory in a sibling stage, install an immutable version, then atomically replace one pointer without moving the prior version. |
| Network helpers used a separate timeout constant | Configured OCI limits did not govern actual reads | GOV-913 | Use `_OCI_LIMITS.timeout_seconds` for metadata and blob requests. |
| UTF-8/JSON decoder exceptions escaped from three registry surfaces | Public errors varied by payload and could reflect decoder detail | GOV-913 | Decode tag metadata, manifests, and configs through one object-only helper with stable `SDLParseError` messages. |

## Incumbents and lineage

- Issues #12, #13, and #14 established capped reads, safe prevalidated tar
  extraction, config-blob verification, and `root_file` signature binding.
- Issue #115, ADR-071, and the reusable-asset trust specification keep identity,
  integrity, and authenticity distinct. A cache directory or module id is never
  proof of payload integrity.
- `SDLParseError` and `RegistryTrustPolicy` remain the relevant public error and
  policy seams.

## Standards basis

- The [OCI image-layout specification](https://github.com/opencontainers/image-spec/blob/main/image-layout.md)
  requires `oci-layout`, `index.json`, and content-addressed blobs whose bytes
  match their descriptors.
- OCI [image configuration guidance](https://github.com/opencontainers/image-spec/blob/main/config.md)
  recommends reproducible packing and unpacking so content identities do not
  drift.
- Python's [gzip documentation](https://docs.python.org/3/library/gzip.html)
  defines `mtime=0` as creation-time-independent output, while
  [tarfile](https://docs.python.org/3/library/tarfile.html) exposes the member
  metadata and extraction filters normalized here.
- [TUF](https://theupdateframework.github.io/specification/latest/) and
  [in-toto](https://github.com/in-toto/specification/blob/master/in-toto-spec.md)
  provide the precedent for hash-bound payloads, authenticated metadata, and
  consistent repository views.

## Transaction and failure invariants

1. Publication and extraction never stream files into their public final
   directory. A complete sibling stage is validated before commit.
2. If replacement fails after moving a prior directory aside, the prior
   directory is restored. Temporary stages are removed on rejection.
3. Every cache reader takes the same manifest-keyed lock and revalidates the
   canonical full-tree manifest: exact layer digest, paths, types, safe modes,
   sizes, file digests, declared regular root, and containment.
4. The complete decoded tar stream, including PAX/GNU metadata and padding, is
   bounded by absolute and expansion-ratio limits before `tarfile` parses it.
   The PEP 706 `data` filter is mandatory; early Python 3.11 patch releases fail
   closed instead of using unfiltered extraction.
5. Registry response sizes stay bounded before JSON decoding. Invalid UTF-8,
   syntax, or top-level JSON shape never includes body or decoder detail in the
   public error.
6. Private key bytes and registry response bodies never enter public errors or
   portable results.

## Verification evidence

`test_sdl_module_registry.py` covers byte-identical publication after host
metadata changes, normalized headers, relative/symlink identity, escape
rejection, strict signing, exact immutable layout inventory, atomic-pointer
failure and recovery, bounded version retention, configured timeout
propagation, stable metadata/manifest/config JSON errors,
PAX/GNU metadata bombs, pre-parse absolute/ratio bounds, full-tree cache
binding, content/mode/type/symlink/extra/missing tamper repair, concurrent
single extraction, old-reader continuity, and partial-extraction cleanup.

Repository policy, requirement governance, Ruff, focused pytest, and the full
`tools/verify_all.py` graph remain required before merge.

## Non-goals

- No hosted registry, registry authentication, key rotation, transparency log,
  signer distribution, or multi-signature threshold change.
- No cache eviction policy, cross-host shared cache, or general artifact store.
- No new OCI media type, SDL syntax, contract schema, or portable exception.
- No relaxation of the existing download, member-count, per-member, aggregate,
  traversal, link, special-file, duplicate-path, or root-containment checks.
