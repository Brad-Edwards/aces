# libvirt backend — real-daemon smoke test

The hermetic `nox verify` graph exercises the libvirt/QEMU backend
(`raes_backend_libvirt`) through in-process fakes — it deliberately does **not**
require a real `libvirtd`, QEMU/KVM, or privileged host access (see the issue
#604 preflight note). This directory is the out-of-band counterpart: it runs the
backend against a **real libvirt daemon** so we can periodically confirm the
reconciliation/teardown behaviour actually works on real infrastructure.

## What it checks

`libvirt_smoke.py` drives `LibvirtDeploymentDriver` and `LibvirtProvisioner`
against `qemu:///system` and asserts, on real domains / networks / nwfilters:

- libvirt raises `VIR_ERR_NO_DOMAIN` (42) / `VIR_ERR_NO_NETWORK` (43) on missing
  lookups, and the driver's hardcoded codes match the installed `libvirt` module;
- CREATE realizes an active network + a running domain;
- UPDATE re-converges in place (no duplicate);
- teardown removes real objects with **no orphans**, and is idempotent
  (repeat teardown + never-realized teardown are clean no-ops);
- teardown of an already-inactive domain succeeds (`VIR_ERR_OPERATION_INVALID`
  on stop is benign);
- teardown refuses a foreign object at the same name (ownership fail-closed);
- nwfilters are owner-stamped on realize and undefined on teardown;
- a partial CREATE (define ok, start fails) is rolled back — no orphan;
- the provisioner CREATE → teardown → idempotent re-teardown path;
- a real cirros guest boots with a cloud-init seed ISO, then tears down cleanly.

The domain XML uses `<domain type="qemu">` (TCG software emulation), so **no
bare-metal or nested virtualization is required** — any x86 host with libvirt +
qemu + genisoimage works.

## Run it on AWS (ephemeral, self-cleaning)

```sh
AWS_PROFILE=aws-dev AWS_REGION=us-east-1 tools/real-daemon/run_aws_smoke.sh
```

This provisions a `c5.2xlarge` Ubuntu 24.04 instance, installs libvirt/qemu, syncs
this repo, runs the smoke test, prints the `SUMMARY: N/N passed` line, and tears
down the instance + security group + key pair on exit. Pass `--keep` to leave the
instance up for manual inspection (remember to terminate it later).

Exit code is non-zero if any check fails.

## Run it on any libvirt host

Copy `libvirt_smoke.py` next to an installed `raes_backend_libvirt` (with
`libvirt-python` available) on a host with libvirt/qemu/genisoimage and a
`/var/lib/libvirt/images/cirros.img`, then:

```sh
python real_daemon_smoke.py   # or: python libvirt_smoke.py
```

For seeds/disks outside `/var/lib/libvirt/images`, the host needs
`security_driver = "none"` and `user/group = "root"` in `/etc/libvirt/qemu.conf`
(the AWS script sets these automatically).

## Guest-certified realization proof (ASR-519, issue #715)

`libvirt_smoke.py` proves substrate reconciliation/teardown at the *daemon* level.
The **guest-certified** proof goes one layer deeper: it boots a guest-observing
appliance through the production apply path and reads concern facts back **from
inside the guest** (resource allocation, network addressing, file content, and
service state), freshness-bound to a per-run challenge, then verifies teardown.
Domain existence alone never satisfies it.

The generated appliance requires a **static x86_64 BusyBox** named `busybox` on
the command's `PATH` (on Ubuntu, install `busybox-static`) and a readable kernel
at the configured/default kernel path. The driver validates both before opening
libvirt. It encodes `newc` itself, so no host `cpio` executable is required.

The reproducible operator/self-hosted command is:

```sh
# Against a real libvirt/QEMU daemon (qemu:///system). Boots the appliance,
# certifies from inside the guest, writes a machine-readable evidence artifact,
# and returns non-zero on any failed stage.
raes libvirt techvault guest-certify \
  --scenario examples/scenarios/techvault-guest-certified.sdl.yaml \
  --project-dir . --run-id guest-proof-1 --yes
```

It emits the `raes.libvirt.scenario-evidence-run/v1` artifact under
`runs/<run-id>/scenario-evidence/libvirt-scenario-evidence-run.json`. The artifact
is validated (source separation, binding, redaction) **before** it is written, so
it contains no host paths, connection URIs, raw domain UUIDs, XML, or secrets; the
guest report is bound to a redacted control-plane operation reference, the fresh
challenge, the selected envelope/configuration + appliance digests, and a
`sha256:` native correlation. The report preserves the exact guest-observed
memory MiB value and separately discloses the configured one-sided memory
tolerance (16 MiB by default). The equivalent gate also runs as an opt-in pytest:

```sh
RAES_REAL_LIBVIRT_URI=qemu:///system \
  uv run pytest -m integration \
  implementations/python/tests/test_libvirt_backend_guest_certified_real_libvirt.py
```

Both are skipped by the default hermetic `nox verify` graph, which never requires
libvirt, QEMU/KVM, privileges, a host image, network access, or credentials — the
guest-certified proof is an explicit separate gate. The same host requirements
apply (`security_driver = "none"` + `user/group = "root"` in
`/etc/libvirt/qemu.conf` when boot artifacts and the run-local guest fact channel
live outside `/var/lib/libvirt/images`; the AWS script sets these automatically).
