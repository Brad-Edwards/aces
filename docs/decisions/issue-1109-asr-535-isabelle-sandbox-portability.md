# Issue 1109 / ASR-535 Isabelle Sandbox Portability

Date: 2026-08-11

Issue: #1109. Requirement: ASR-535. Related: #963.

## Reproduced gap

The checksum-pinned Isabelle2025-2 distribution was acquired on Ubuntu 24.04
x86_64 and started inside the repository's bubblewrap network namespace. The
kernel replay stopped before loading the fixed session with `Fontconfig head is
null, check your fonts or fonts configuration`.

The sandbox already exposes `/etc/fonts` and `/usr/share/fonts`, but creates an
otherwise empty `/usr/share`. Ubuntu's `/etc/fonts/conf.d` entries resolve into
`/usr/share/fontconfig`, so the fixed runtime allowlist omits data required by
the pinned prover. The result is host-image-dependent proof admission even
though theorem sources and the prover archive are unchanged.

## Decision

Add `/usr/share/fontconfig` to the fixed, read-only system-runtime allowlist.
Do not bind the host root, user home, repository workspace, network, ambient
environment, or any mutable proof input. Existing paths remain conditional so
minimal distributions without that directory keep the same command shape.

The allowlist membership is covered by a focused regression. Acceptance also
requires a real Ubuntu 24.04 x86_64 replay of the checksum-pinned archive under
bubblewrap network isolation. The proof evidence digest and theorem semantics
must remain unchanged.

## Nonclaims

This repairs Linux distribution portability for the declared canonical proof
lane. It does not make arbitrary Isabelle installations portable, authorize a
different prover or archive, expand the theorem claim, or replace the existing
checksum, resource, filesystem, and offline-execution controls.

