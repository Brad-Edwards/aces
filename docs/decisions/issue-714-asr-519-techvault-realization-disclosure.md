# Issue 714 / ASR-519 TechVault Realization Disclosure

Requirement: ASR-519 (`9ad95f1d-7c4a-4532-8a3e-50453e8286d4`).

The TechVault appliance driver is a bounded native-substrate mode. It does not
claim to provision the full TechVault guest/application stack. Admission,
readback, persistence, and evidence publication all use the concern boundaries
below.

## Concern accounting

| Concern | Current disposition | Success evidence |
|---|---|---|
| topology | realized | active native object and exact native-name readback |
| architecture | realized | domain XML readback |
| image | selected generated-initramfs policy realized; concrete images rejected | exact attached kernel/initramfs paths plus artifact digests |
| resource allocation | realized exactly | domain memory/vCPU XML readback |
| network | realized exactly | network/domain XML readback for CIDR, gateway, forwarding policy, and attachments |
| content placement | unsupported | typed pre-I/O diagnostic |
| account placement | unsupported | typed pre-I/O diagnostic |
| feature binding | unsupported | typed pre-I/O diagnostic |
| service | unsupported | typed pre-I/O diagnostic |
| ACL | unsupported | typed pre-I/O diagnostic |

Guest readiness, applications, and SOC state are not observed. A domain handle,
domain name, declared listener, ping, or TCP connection is not accepted as proof
of any nested concern.

## Admission and exactness

The provisioner validates TechVault concerns before snapshot reconciliation and
before driver I/O. The native driver repeats the gate for direct callers. Values
outside the published envelope, implicit network values, silently normalized or
duplicate names, concrete images, guest placements, services, ACLs, unbound
metadata, and unsupported update/recovery shapes fail closed.

Memory and CPU values are never clamped. Network `internal: false` remains an
explicit false value and is verified as NAT forwarding; it is not lost as an
omitted default.

## Observation and commit

Each admitted field has one typed `daemon-observed` readback record. Missing,
duplicate, wrong-source, type-coerced, or mismatched records fail the operation.
An exact daemon report and realization binding are required before the runtime
snapshot commits.

Reports keep these sources separate:

- authored scenario identity;
- planned topology and concern values;
- driver-reported operation outcomes;
- bounded daemon-observed substrate facts;
- guest-observed facts, currently `not-observed`; and
- derived evaluator analysis.

The binding covers the published realization-envelope and configuration digests,
hashed connection/naming configuration, and hashes of the actual run-local kernel
and initramfs artifacts. Artifacts never contain raw libvirt XML, UUIDs, host
paths, connection URIs, credentials, or exception text.

## Recovery

Partial creation and post-create readback/binding failures trigger cleanup of only
the current operation's ownership-stamped resources. Cleanup is successful only
after native absence is verified. Lookup/listing uncertainty, ownership conflict,
or failed destroy/undefine produces a residual-state diagnostic and withholds
success. Prefix-wide cleanup is not available.

Updates and compound delete transactions are rejected until a verified native
restore path exists. Failed provisioner operations retain the prior runtime
snapshot; successful native deletion clears the driver's prior observation report
so it cannot be reused as fresh evidence.

## Verification focus

Falsification coverage includes clamped resources, fabricated handles, incomplete
and duplicate observations, type coercion, inactive readback, substituted boot
artifacts, extra attachments, altered forwarding policy, foreign ownership,
partial rollback, unverifiable cleanup, stale evidence relabeling, and mismatched
realization bindings.
