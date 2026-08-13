# Issue 1095 / ASR-519 Libvirt Guest-Evidence Freshness

Date: 2026-08-11

Requirements: ASR-519 and RUN-314. This implements the freshness and resource
evidence guardrails recorded for issue #715.

## Decision

Every guest-certified `realize()` attempt starts with empty operation-scoped
guest evidence. After admission and boot-input preflight, the driver obtains a
new challenge, rejects any challenge already used by that driver instance,
removes each prior fact-channel object, and only then opens libvirt. A report is
accepted only when its returned challenge equals the current operation's value.

Guest memory remains an exact observed integer. A configurable and explicitly
published one-sided tolerance is applied only when appraising that integer
against requested memory; no boolean “corroborated” observation replaces the
measurement.

## Freshness lifecycle

The old driver generated one challenge in `__post_init__` and reused it for all
later operations. Its stable file-backed serial path could also contain a prior
completed report. The transport could return that terminal report immediately,
allowing old evidence to reach validation and making retry behavior depend on
stale local state.

The operation lifecycle is now:

1. clear `challenge`, `last_guest_observations`, `last_guest_facts`, and
   `last_guest_binding` at the beginning of every attempt, including attempts
   rejected by admission or boot-input preflight;
2. after those gates, request a challenge from the injected factory and require
   a 16–64-character lowercase hexadecimal token that has not been used by this
   driver instance;
3. remove a prior regular, link, FIFO, socket, or broken-link fact channel for
   every admitted domain; reject a directory or any unlink failure;
4. pass the current challenge through the disclosed kernel-command-line
   mechanism, boot, and validate the returned report in the existing staged
   order; and
5. publish facts and binding only after every daemon and guest comparison
   succeeds. Rollback and destroy remove the fact channel and clear published
   guest evidence.

Preparation failure returns
`libvirt-backend.guest.freshness-preflight-failed` before native mutation. A
stale or cross-operation report that appears after channel clearing fails the
existing `libvirt-backend.guest.challenge-mismatch` gate. A deterministic
challenge factory remains injectable for hermetic tests, but repeated output is
rejected rather than silently weakening production freshness.

The challenge proves report recency relative to this driver operation. It is
not a secret, a guest identity credential, a measured-boot attestation, or proof
against a malicious guest that can read its own command line.

## Exact memory evidence and appraisal

The old observer reduced `/proc/meminfo` to
`guest-memory-corroborated: true` whenever the value was between one half and
all of requested memory. A 128 MiB definition could therefore accept a 64 MiB
guest report while discarding the exact measurement from the claim-bearing
observation set.

The observer now emits `guest-memory-mib` with the exact parsed integer. The
expected value remains the exact requested MiB value. `GuestObservationConfig`
declares `memory_tolerance_mib` (default 16 MiB), and comparison accepts only:

```text
max(0, requested_mib - memory_tolerance_mib)
    <= observed_mib
    <= requested_mib
```

The allowance is one-sided because Linux `MemTotal` may exclude small reserved
regions from memory assigned by the hypervisor; an observed value above the
definition is not explained by that effect. The exact integer remains in both
`RealizationObservation` and bounded per-domain facts. The evidence report and
driver binding publish `memory_tolerance_mib`, so reviewers can separate
measurement from appraisal. Negative, boolean, or non-integer tolerances fail
configuration construction.

Changing the default tolerance or probe method changes comparison semantics and
must be reviewed together with the probe-policy identity. It must never rewrite
the recorded measurement.

## Evidence boundaries and alternatives

The existing source layers remain distinct: daemon XML proves the exact memory
definition; `/proc/meminfo` is a guest observation; the tolerance comparison is
an appraisal. Neither source upgrades the other.

Rejected alternatives:

1. retain one process-lifetime challenge: it cannot distinguish retry reports;
2. rely only on file mtime or truncate the old channel: timestamps are mutable,
   and an old writer can retain an open inode;
3. accept the first completed report and wait for later evidence only on parse
   failure: a stale report must fail closed, not race the new boot;
4. retain a boolean memory result: it destroys the evidence needed to audit the
   tolerance; and
5. accept a percentage or half-memory heuristic: it is overly permissive at
   larger sizes and was not disclosed in the evidence binding.

## Verification

Hermetic tests cover two successful operations with distinct challenges,
repeated and stale challenge rejection, pre-existing channel removal, channel
directory and unlink failures, factory failure, clearing evidence before a
failed new attempt, exact memory retention, the 16 MiB boundary, values below
and above the permitted range, injected tolerance, invalid tolerance, and
evidence-report disclosure. The guest freshness and observation modules have
100% focused branch coverage; the opt-in real-libvirt proof remains the native
certification gate.

Related evidence guidance:

- RFC 9334 attestation freshness model: <https://www.rfc-editor.org/rfc/rfc9334.html>
- libvirt domain memory definition: <https://libvirt.org/formatdomain.html#memory-allocation>
- Linux `/proc/meminfo`: <https://docs.kernel.org/filesystems/proc.html#meminfo>
