# libvirt backend — real-daemon smoke test

The hermetic `nox verify` graph exercises the libvirt/QEMU backend
(`aces_backend_libvirt`) through in-process fakes — it deliberately does **not**
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

Copy `libvirt_smoke.py` next to an installed `aces_backend_libvirt` (with
`libvirt-python` available) on a host with libvirt/qemu/genisoimage and a
`/var/lib/libvirt/images/cirros.img`, then:

```sh
python real_daemon_smoke.py   # or: python libvirt_smoke.py
```

For seeds/disks outside `/var/lib/libvirt/images`, the host needs
`security_driver = "none"` and `user/group = "root"` in `/etc/libvirt/qemu.conf`
(the AWS script sets these automatically).
