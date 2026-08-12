# Issue 1094 / RUN-314 Libvirt Boot-Artifact Reliability

Date: 2026-08-11

Requirements: RUN-314 and ASR-519. Related work: issues #197, #714, #717,
and #1116; pull request #1085 first exposed the interface-rendering defect.

## Decision

The repository-owned libvirt appliance builder owns the exact bytes it asks
libvirt to boot. It therefore encodes the bounded appliance tree directly as
Linux `newc`, compresses it with a zero gzip timestamp, validates the embedded
BusyBox executable before native mutation, and caches the selected kernel by
content digest through atomic replacement.

This changes adapter implementation semantics, not SDL or a normative
contract. The published realization envelope still selects an x86_64 generated
appliance. The run evidence continues to bind the actual kernel and initramfs
digests.

## Gap and owning boundary

The prior implementation delegated `newc` creation to an ambient host `cpio`,
embedded the host's `/usr/bin/busybox`, retained source filesystem metadata,
and let `gzip.compress()` record wall-clock time. Identical inputs could
therefore yield different bytes, while supported development hosts without
those exact paths failed before the intended tests ran. Separately, the kernel
cache treated equal `st_mtime_ns` values as content identity, so changed bytes
with a preserved timestamp could reuse a stale kernel.

These faults belong to the libvirt adapter's boot-artifact boundary. Scenario
fields, runtime snapshots, or evidence-only changes cannot make the bytes
deterministic or fresh.

## Canonical initramfs

`raes_backend_libvirt._initramfs.encode_newc()` implements the kernel-documented
`070701` format:

- member names are sorted by encoded POSIX-relative path;
- inode numbers are assigned in that order;
- uid, gid, mtime, device fields, and checksum are zero;
- generated directory and symlink permissions are fixed, while deliberately
  assigned regular-file permissions are retained;
- regular files, directories, and links are encoded without invoking a host
  command; unsupported special files fail;
- names and contents are aligned to four bytes and a canonical `TRAILER!!!`
  entry terminates the archive; and
- gzip uses `mtime=0` and a platform-neutral header OS byte.

Generated text and executable modes are assigned explicitly. The completed
compressed artifact is fsynced in a sibling temporary file and atomically
replaces its target. This makes repeated builds byte-identical for the same
domain and BusyBox bytes; it does not claim that externally selected kernel or
BusyBox inputs are identical across hosts.

## Executable discovery and typed preflight

Both appliance builders accept an absolute `busybox_path`. When it is omitted,
they discover `busybox` on an optionally injected search path. Before a
libvirt connection is opened or a network is defined, preflight requires:

- a resolvable regular file with read and execute permission;
- a structurally valid ELF executable for the x86_64 appliance target; and
- no `PT_INTERP` program header, because the generated root has no dynamic
  loader or shared libraries.

The typed `InitramfsPreflight` result distinguishes missing, relative,
non-regular, non-executable, non-ELF, wrong-architecture, and dynamically linked
inputs. The driver maps any non-ready result to the stable redacted diagnostic
`libvirt-backend.techvault-native.initramfs-toolchain-unavailable`. A missing
or unreadable kernel similarly returns
`libvirt-backend.techvault-native.kernel-unavailable`. Neither diagnostic
contains a host path or raw exception.

An injected custom `InitramfsBuilder` may own a different hermetic toolchain and
omit the optional BusyBox preflight method. Its completed artifact is still
hashed and read back through the incumbent evidence path.

## Kernel cache

`copy_kernel_for_libvirt()` compares SHA-256 content, never timestamps. Equal
content reuses the existing inode after restoring its disclosed readable mode.
Changed content is copied to a sibling temporary file, hashed while copying,
fsynced, compared with the source digest to detect a concurrent source change,
chmodded, and atomically replaced. Failure leaves a prior complete target in
place and removes the incomplete temporary file.

This is a content-integrity cache, not a trust policy for choosing a kernel.
Configuration and operator controls still own which external kernel and static
BusyBox bytes are supplied.

## Rejected alternatives

1. Document Ubuntu-only `/usr/bin/busybox` and `cpio` prerequisites: rejected
   because archive metadata and gzip time would remain nondeterministic.
2. Add flags to host `cpio`: rejected because implementations differ and an
   ambient path-list protocol is unnecessary for this bounded tree.
3. Compare kernel mtime plus size: rejected because mutable metadata is not
   content identity.
4. Write cache targets directly: rejected because interruption can expose a
   partial boot artifact.

## Evidence and verification

The tests parse `newc` entries and verify order, modes, links, fixed metadata,
alignment, and trailer; compare repeated TechVault and guest-certified builds;
exercise injected, discovered, missing, dynamic, malformed, and wrong-target
executables; reproduce same-mtime kernel substitution; and prove atomic failure
preserves the old target. The changed artifact modules have 100% focused branch
coverage. Issue #1116's structural MAC/IP/CIDR validation is shared by both
init scripts, with no unrelated `.DS_Store` artifact.

Primary format references:

- Linux initramfs buffer format: <https://www.kernel.org/doc/html/latest/driver-api/early-userspace/buffer-format.html>
- Python gzip timestamp control: <https://docs.python.org/3/library/gzip.html#gzip.compress>
- OCI digest identity: <https://github.com/opencontainers/image-spec/blob/main/descriptor.md>
- Reproducible archive practice: <https://reproducible-builds.org/docs/archives/>
