# Issue 1106 / GOV-913 OSV Scanner Cache Integrity

Date: 2026-08-11

Issue: #1106. Requirement: GOV-913. Related: #34 and #1098.

## Decision

The repository pins the official OSV-Scanner v2.4.0 SHA-256 for each admitted
Linux and macOS amd64/arm64 asset. Every `ensure_osv_scanner` call validates an
existing cache entry with `lstat`, accepts only a regular non-symlink executable,
opens the final component without following links where the host supports that
flag, verifies the opened file's identity with `fstat`, and hashes its complete
bounded bytes against the repository pin before returning it.
Tampered regular files and symlinks are unlinked and reacquired; directories or
an unsafe cache-parent shape fail closed.

Downloaded bytes are checked against the same repository pin and installed from
a uniquely named sibling temporary file with an atomic replace. No partial
download is ever published at the executable path. Remote checksum metadata is
not the root of trust for an already reviewed tool version.
Release-asset acquisition also has a finite 60-second request timeout so a
stalled endpoint cannot hold the verification lane indefinitely.

## Nonclaims

This local cache integrity boundary does not make OSV advisory availability
hermetic, establish host compromise resistance, or replace release upgrade
review. A process with authority to mutate executable bytes continuously can
still race any path-based execution; repository CI assumes its workspace is not
actively controlled by another principal.

## Verification

Tests cover valid hits without network access, tampered bytes, symlinks,
directories, missing platform pins, download mismatch, atomic replacement, and
concurrent acquisition. The live clean-lock scan, Ruff, repository policy, and
required supply-chain job remain mandatory.
