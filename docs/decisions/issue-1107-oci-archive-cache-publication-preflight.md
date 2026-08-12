# Issue 1107 OCI Archive, Cache, and Publication Preflight

Date: 2026-08-11

Issue: [#1107](https://github.com/OpenRAE/rae/issues/1107).

Requirement: GOV-913.

This note records the implementation defense before changes to the OCI module
archive, extraction cache, or publication transaction. It is a correction to
the issue #1096 implementation, not a new SDL feature, portable contract, OCI
media type, hosted registry, or experiment surface.

## Gap claim and ownership

The incumbent module-registry boundaries remain correct, but three mechanisms
inside them are insufficient:

| Gap | Consequence | Incumbent owner |
| --- | --- | --- |
| `tarfile` receives the gzip stream before the complete decoded tar stream is bounded | PAX and GNU extension metadata can consume unbounded expansion and parse work before member limits run | `raes.module_registry` archive admission |
| Cache completion binds only the layer digest and declared root | An imported SDL, permission, type, or extra entry can change while a retained marker still produces a hit | `raes.module_registry` cache admission |
| Directory replacement moves the active target aside before installing the stage | Readers can observe absence, and process death can strand the only valid tree under a backup name | `raes.module_registry._filesystem` and `.publishing` |
| The completion manifest is derived only from the writable cache tree | Coordinated edits to both a cached file and its local manifest can falsely retain the verified layer-digest label | `raes.module_registry` cache admission |
| A validated cache path is reopened after its lock is released | A same-user writer can replace the root or a nested local import after inventory validation, while resolution still reports the verified layer digest and signer | `raes.module_registry` source admission and composition |
| Version pruning follows pointer replacement | A pruning error can report failure after the new version has already become current | `raes.module_registry._filesystem` transaction ordering |
| Legacy root layouts, linked cache/lock paths, recursive walks, and unsynced renames are admitted | Upgrades can expose stale alternate content, special lock nodes can block or escape the cache, deep trees can escape stable errors, and power loss can discard an apparently committed directory entry | `raes.module_registry._filesystem` and `.publishing` |

`SDLParseError`, the existing per-key OS/thread lock, deterministic archive
builder, content-addressed OCI blobs, and `test_sdl_module_registry.py` remain
the error, concurrency, artifact, and regression surfaces. No second cache,
database, archive library, or transaction service is justified.

## Lineage and standards basis

- Issues #12 and #13 introduced bounded OCI reads and prevalidated extraction;
  issue #14 bound config integrity and `root_file` into signatures.
- Issue #115, ADR-071, and GOV-913 establish separate identity, integrity,
  authenticity, bounded-input, and redaction duties for reusable assets.
- Issue #1096 added deterministic bundles, digest markers, locks, staging, and
  rollback. Issue #1107 closes the remaining P1 composition gaps.
- Python's
  [tarfile documentation](https://docs.python.org/3/library/tarfile.html) and
  [PEP 706](https://peps.python.org/pep-0706/) establish safe extraction filters
  but explicitly do not make archive resource use safe.
- [RFC 1952](https://www.rfc-editor.org/rfc/rfc1952) defines gzip framing. The
  whole decoded stream must be admitted before a tar parser sees it.
- The [OCI image-layout specification](https://github.com/opencontainers/image-spec/blob/main/image-layout.md)
  uses immutable content-addressed blobs.
- Python [`os.replace`](https://docs.python.org/3/library/os.html#os.replace)
  provides the one-directory-entry atomic commit needed for a small pointer.

## Primary implementation practice

### Archive admission

Decode gzip into a bounded binary spool while counting every output byte. Apply
an absolute decoded-tar cap and a compressed-to-decoded expansion-ratio cap,
validate a complete gzip stream, rewind, and only then construct `TarFile` in
uncompressed mode. This bounds regular payload, headers, padding, and PAX/GNU
metadata before parsing. Existing member-count, per-file, aggregate-file,
path-depth, traversal, duplicate, link, special-file, and mode checks remain
defense in depth. `extractall(filter="data")` is mandatory; runtimes without it
fail closed. Cache inventory uses an explicit bounded work stack rather than
Python recursion, so admitted depth cannot produce `RecursionError` residue.

### Cache integrity

Before any extracted-tree write, stream every validated regular member from the
bounded, already SHA-256-verified tar and build the trusted expected inventory.
It contains normalized paths, synthesized implicit directories, entry types,
safe modes in the permission classes representable by the host platform, sizes,
and file digests. POSIX directory modes are normalized to owner-only access;
Windows file and directory modes use CPython's writable `0666`/`0777`
representation. A hit parses the local
completion record under a size cap, reconstructs the exact on-disk inventory
without following links, and compares its bundle-derived projection to that
trusted inventory. The writable cache manifest is never accepted as the
authority for its own tree. Only a miss allocates a version stage and extracts
files. Hit validation remains linear in bundle bytes plus cached bytes, but it
performs no extracted-tree writes, version rename, or pointer commit; only the
bounded decoded-tar spool may spill after its memory threshold. Missing, extra,
replaced, linked, mode-changed, byte-changed, or coordinated tree-plus-manifest
edits invalidate the version and trigger a clean rebuild.

Validation and consumption are one boundary. While the per-entry cache lock is
still held, every reachable SDL document in the root module's local-import graph
is opened through a no-follow descriptor, bound to the inventory's regular-file
identity, size, mode, and SHA-256 digest, and decoded into an immutable in-memory
source document. Composition consumes that verified source map; the retained
cache paths are metadata and cycle identities only. Nested local imports inherit
the consumer-admitted lockfile and trust policy instead of discovering mutable
policy or lock files inside the extracted cache after validation. Ordinary local
filesystem imports outside an OCI source keep their existing read and policy
behavior. An uncooperative same-user writer can still mutate cache paths, but
cannot change the bytes composed under the already-reported bundle digest.

First-use lock creation is also a concurrent admission path. If a peer creates
the regular lock file after the missing-path check but before exclusive create,
the loser must re-enter the same no-follow type, identity, and anchored-parent
validation before opening the peer-created file. Ordinary concurrent first use
must not become an integrity failure, while linked or special files still fail
closed.

### Gapless publication

Each logical cache or OCI-layout slot contains immutable `versions/<id>` trees
and one small pointer file. A writer builds and validates a sibling stage, moves
it once into a new immutable version name, and atomically replaces the pointer
without first removing the previous pointer. Existing readers retain paths into
the old version. Startup repair removes abandoned stages and restores a missing
or invalid pointer only from a fully validated immutable version. Publication
never mutates or moves the version currently addressed by the pointer.

All fallible bounded-retention pruning occurs before pointer replacement while
retaining both the selected version and the previously selected version. Pointer
replacement is therefore the publication commit, rather than an intermediate
step followed by a failure-capable cleanup. Before renaming a complete version,
regular files and directories are synced; the version-store directory is synced
after the rename; the pointer file is synced before replacement; and the slot
directory is synced after replacement on hosts with directory-fsync support.
Cache roots, lock parents, and lock files reject links and non-regular nodes
before use, so a FIFO/device cannot block before the configured lock timeout and
an unsafe link cannot redirect creation outside the intended store. Where
directory-relative opens are available, lock-file lookup and creation are
anchored to a no-follow parent descriptor and the public parent identity is
rechecked afterward. Other hosts bind and recheck the parent identity around
the open.

The public publication result deliberately reports the selected usable
`<slot>/versions/<id>` OCI layout, not the logical `<id>-<version>.oci` slot
container. The returned path therefore retains the prior contract that
`layout_dir` itself contains `oci-layout`, `index.json`, and `blobs/`; callers do
not need to parse the private pointer. The slot spelling remains stable for
locking and recovery but is not itself an OCI image-layout directory.

A pre-versioned output already containing root-level `oci-layout`, `index.json`,
or `blobs/` is not silently converted in place. Publication fails with an
actionable instruction to move or remove that legacy output. This prevents a
dual layout in which updated callers consume `versions/<id>` while older callers
continue consuming permanently stale root files.

Version retention is bounded to eight complete versions per logical slot: the
selected current version, the pointer value observed immediately before the
update, and the newest remaining versions that fit the bound. This guarantees
that an immediate prior reader keeps a complete immutable path across a writer
transition while repeated changed publications cannot grow storage without
bound. A returned version is not a permanent artifact-retention service;
callers needing longer retention must copy or push the OCI layout.

## Alternatives rejected

1. Raise only tar member or extracted-payload limits. PAX/GNU metadata is parsed
   before those counters run.
2. Hash only `root_file` or retain the layer-digest text marker. Imported files
   and tree structure affect resolved behavior.
3. Add exception handling to the backup/rollback protocol. Process death skips
   rollback and cannot remove the observable absence interval.
4. Rebuild the active directory in place. Concurrent readers can observe partial
   mutation, and a failed writer destroys the last known-good view.
5. Keep the early Python 3.11 unfiltered fallback. A security boundary must fail
   closed when its mandatory runtime primitive is unavailable.

## Documentation and compatibility defense

The behavior is internal and operator-visible only on rejection: adversarial
archives, corrupted cache trees, unsupported early Python 3.11 patch releases,
and failed publication produce stable `SDLParseError` failures. Artifact bytes,
OCI media types, SDL syntax, lockfile schema, and the successful CLI JSON field
schema stay unchanged. The `layout_dir` value identifies an immutable complete
version below the logical slot; callers must not assume it is a mutable
stable-name directory.

## Verification plan

- Adversarial PAX and GNU metadata bombs prove decoding is rejected before any
  tar member is parsed; exact absolute, ratio, and path-depth boundaries are
  covered.
- Simulated absence of the PEP 706 `data` filter proves fail-closed behavior and
  no extracted file.
- Full-tree cache tests cover content, digest, size, mode, type, symlink, missing,
  extra, malformed/noncanonical manifest, coordinated tree-plus-manifest
  forgery, verified-bundle-derived expectation, retained completion record,
  clean rebuild, and a hit that performs no extraction or version staging.
- Descriptor-bound source tests replace the root and a nested local document
  immediately after tree validation, inject cache-local policy and lock files,
  and prove that composition and provenance retain the exact verified bytes and
  digests on both cache misses and hits.
- Transaction tests cover pointer replacement failure, process-death residue,
  prune-before-pointer ordering, sync ordering, startup repair, immutable prior
  readers, linked/special lock rejection, and concurrent writers/readers.
- Publication tests cover exact OCI inventory, deterministic bytes, atomic
  pointer transitions, failed-commit preservation, legacy-layout fail-closed
  upgrade behavior, and repair.
- Run focused line and branch coverage, focused tests on Python 3.11 through
  3.14, integration tests, Ruff, policy, requirement governance, and the full
  verification graph.

## Non-goals

- No cache eviction policy, cross-host cache, general artifact store, hosted
  registry, authentication, signing, or trust-policy change.
- No new SDL, schema, contract, media type, backend, experiment, or portable
  exception.
- No relaxation of digest, signature, path, link, type, size, concurrency,
  deterministic-byte, or redaction guarantees.
