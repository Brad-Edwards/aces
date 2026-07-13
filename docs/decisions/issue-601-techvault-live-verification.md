# Issue 601 TechVault Live Verification — Corrected Claim Boundary

This historical verification note is corrected by issue 714 / ASR-519. The
earlier issue-601 results must not be cited as proof that TechVault guest images,
cloud-init content, accounts, features, ACLs, named services, or SOC applications
were realized by the libvirt backend.

## What the earlier run established

The runs established that ACES could create a separate libvirt/QEMU substrate
containing generated initramfs domains and networks. That is a useful substrate
check, but it is narrower than scenario realization.

Several former claims exceeded the available evidence:

- planned domain and network data was copied into the native report without an
  independent source label;
- generic listeners were treated as realization of named services;
- SOC state was inferred from domain names rather than observed inside guests;
- requested memory and CPU values could be clamped;
- a successful native handle was treated as sufficient without exact daemon
  readback; and
- prefix-wide cleanup was treated as a safe clean boot without per-resource
  ownership proof.

Consequently, the former counts for services, Wazuh agents, Suricata rules,
case-management applications, and scenario variants are withdrawn as libvirt
realization evidence. Historical endpoint reachability proved only that a
generated listener answered at an address; it did not prove the declared
application or service was installed and operating.

The APTL live-gate results remain evidence about the APTL substrate only. They do
not transfer to libvirt.

## Current bounded native mode

The TechVault appliance mode now accepts only concerns it can apply exactly and
verify through bounded libvirt daemon readback. A successful run accounts for:

- native domain and network existence;
- exact architecture and generated-initramfs attachment policy;
- exact memory and virtual CPU values;
- exact network CIDR, gateway, internal/NAT policy, and domain attachments; and
- a realization binding covering the published envelope, driver configuration,
  connection and naming configuration digests, and boot-artifact digests.

The following concerns are explicitly unsupported in this mode and block the
operation before native resource creation:

- concrete guest images;
- cloud-init content, content placements, accounts, and feature bindings;
- declared guest services;
- network ACLs;
- unbound metadata or silently normalized names; and
- updates or compound delete transactions without a verified restore path.

Guest readiness and SOC/application state remain `not-observed`. Concern-specific
guest probes are separate work; generic ping or TCP reachability is not promoted
to realization evidence.

## Current live-gate interpretation

The live gate may pass only for a bounded scenario whose admitted substrate is
successfully created and read back. The repository's operational TechVault and
curated variants declare unsupported guest concerns, so they now fail with typed
diagnostics instead of producing a partial-success manifest.

For an admitted bounded scenario, the operator command is:

```bash
aces libvirt techvault validate-live \
  --scenario path/to/bounded.sdl.yaml \
  --project-dir . \
  --run-id bounded-native-check \
  --yes
```

There is no memory-clamping, boot-timeout, or prefix-cleanup switch. Resource
values come from the governed plan. Connection URIs carrying user information or
passwords are rejected.

The manifest keeps sources separate:

| Section | Permitted basis |
|---|---|
| `authored` | scenario reference |
| `planned` | compiler/runtime plan |
| `driver_reported` | driver operation result |
| `daemon_observed` | bounded libvirt XML and active-state readback |
| `guest_observed` | `not-observed` |

Planned topology remains labelled `planned`; daemon observations do not imply
guest services, SOC state, or application behavior.

## Recovery and cleanup

Creation failures trigger ownership-checked cleanup of resources created by the
current operation. Success is withheld unless absence can be verified. Uncertain
or failed cleanup produces a residual-state diagnostic and retains run-local boot
artifacts for investigation. The backend does not enumerate and delete resources
solely by name prefix.

## Scope statement

The corrected proof is a bounded native-substrate realization proof. It is not an
APTL equivalence proof, an application deployment proof, a service-readiness proof,
or a SOC detection-quality proof.
