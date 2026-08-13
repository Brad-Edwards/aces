# Issue 1098 GOV-913 Supply-Chain Security Preflight

Date: 2026-08-11

Issue: #1098.

Requirement: GOV-913 (Trust And Integrity Of Reusable Assets).

This note records the review boundary and enforcement policy for repairing two
known vulnerabilities in the frozen Python dependency graph. It covers
repository dependencies and CI automation only. It does not change reusable
asset semantics, SDL, runtime trust policy, OCI publication, or release
automation.

## Findings And Fixed Floors

The audited `origin/dev` lock at commit
`5c210d520e884cca0c08ad201b033fae920ce0c2` resolved:

| Package | Locked finding | Affected surface | First fixed release |
| --- | --- | --- | --- |
| Click | `8.3.1`; PYSEC-2026-2132 / CVE-2026-7246 | `click.edit()` command launch could pass shell metacharacters to an OS shell | `8.3.3` |
| cryptography | `49.0.0`; GHSA-g6cj-pr64-35w5 / CVE-2026-69247 | PKCS#7 EnvelopedData RSA decryption exposed distinguishable errors and timing | `50.0.0` |

The project therefore declares `click>=8.3.3` and
`cryptography>=50.0.0`. The Click declaration is also dependency hygiene:
`raes_cli.semantic` imports Click directly, so relying only on Typer's
transitive declaration was insufficient.

Primary advisory and fix sources:

- <https://osv.dev/vulnerability/PYSEC-2026-2132>
- <https://github.com/pallets/click/releases/tag/8.3.3>
- <https://github.com/advisories/GHSA-g6cj-pr64-35w5>
- <https://github.com/pyca/cryptography/releases/tag/50.0.0>

## Reachability And Consumer Review

Reachability was reviewed to bound the incident, not to justify suppressing a
known-vulnerable package:

- OpenRAE's direct Click call is `click.get_binary_stream("stdin")`. No
  `click.edit()` or pager call was found in production source. Typer and Uvicorn
  are the other resolved Click consumers. Their published constraints accept
  Click 8.3.3.
- OpenRAE directly uses cryptography for Ed25519 private-key loading, signing,
  and verification. No `pkcs7_decrypt_der`, `pkcs7_decrypt_pem`,
  `pkcs7_decrypt_smime`, or EnvelopedData call was found. AsyncSSH and the
  PyJWT crypto extra are the other resolved consumers; their published
  constraints accept cryptography 50.0.0.
- The cryptography advisory requires repeated decryption of attacker-supplied
  EnvelopedData with observable outcomes. That route was not found in the
  current OpenRAE call graph. This is an observed limit, not a universal
  non-exploitability claim for every downstream deployment or future consumer.

The reviewed fixed releases support OpenRAE's Python `>=3.11` floor. The lock
refresh is intentionally limited to Click, cryptography, and resolver-required
metadata and artifacts, then checked with frozen reverse-dependency trees and a
live OSV scan.

## Existing Scanner Lineage

Issue #34 introduced the canonical scanner architecture:

- scan only `implementations/python/uv.lock`;
- acquire a pinned OSV-Scanner binary with release checksum verification;
- keep the networked scan outside the hermetic `verify` graph;
- write one ignored JSON report and upload it even after failure;
- distinguish vulnerability exit code 1 from scanner/setup errors.

Those decisions remain. Issue #34's initial advisory result policy is
superseded by issue #1098 because concrete vulnerable releases were able to
remain in the frozen lock without failing CI.

## Required Failure Contract

The scanner wrapper has one closed outcome classification:

| Exit result | Classification | CI behavior |
| --- | --- | --- |
| `0` | clean | pass |
| `1` | findings | fail with a vulnerability-specific diagnostic |
| any other value | scanner error | fail with the exact scanner/setup exit code |

The CI job must not use job-level or step-level `continue-on-error`. Its report
upload remains guarded by `if: always()` so both findings and tool failures
leave reviewable evidence. A scanner failure can never be interpreted as a
clean scan.

OSV remains a standalone CI gate rather than part of `verify`: the local proof
graph is designed to be hermetic, while OSV acquisition and advisory lookup are
network-dependent. See the official return-code contract at
<https://google.github.io/osv-scanner/output/#return-codes>.

## Alternatives Rejected

- **Suppress based on current reachability.** The vulnerable APIs are not
  observed today, but the packages are shipped and remain callable by direct,
  transitive, or future consumers. Suppression would make a clean-lock claim
  false.
- **Refresh only the lock.** The old project constraints could select a
  vulnerable release again, and Click's direct import would remain undeclared.
- **Raise floors but leave OSV advisory.** This repairs one snapshot without
  preventing the same failure mode for later advisories.
- **Put OSV inside hermetic verification.** This would make ordinary local and
  proof verification depend on external network availability. The dedicated
  required CI job preserves the correct boundary.

## Verification And Nonclaims

Regression coverage checks the direct dependency floors, locked versions,
closed OSV exit classification, distinct nox failures, absence of CI soft-fail
configuration, and unconditional report upload. Focused CLI and registry
signing tests protect the two used dependency surfaces. The final review also
runs a live OSV scan, frozen dependency trees, Ruff, repository policy,
requirement governance, and the canonical verification graph.

This remediation does not claim that dependency scanning proves software
security, that unobserved vulnerable entry points are unreachable in every
downstream use, or that OSV availability is hermetic. It establishes the
narrower invariant that the reviewed frozen lock has no reported OSV findings
and that the required scan cannot fail silently.
