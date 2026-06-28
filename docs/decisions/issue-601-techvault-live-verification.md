# Issue 601 TechVault Native Libvirt Verification

This note records the live TechVault checks used for issue 601 after the
libvirt backend was corrected to prove a second independent substrate. Earlier
ACES/libvirt live-gate attempts in this PR delegated TechVault startup to APTL
Compose; those attempts are superseded and are not used as acceptance evidence.

## Baseline APTL gate

Command run from `/home/atomik/src/aptl` on 2026-06-27:

```bash
uv run aptl lab validate-live --yes --run-id aces-601-libvirt-techvault-live-20260627
```

Result: PASS.

Baseline summary:

- Scenario: `scenarios/techvault-operational.sdl.yaml`
- Selected profiles: `wazuh`, `victim`, `kali`, `enterprise`, `soc`,
  `fileshare`, `dns`, `otel`
- ACES-realized nodes: 30
- Running `aptl-*` containers after the gate: 30
- Networks: `aptl_aptl-dmz`, `aptl_aptl-internal`,
  `aptl_aptl-redteam`, `aptl_aptl-security`
- Manual readback found 10 active Wazuh agents, Suricata traffic/alert events,
  0 kernel drops, 49,954 loaded rules, and 0 failed rules.

This baseline is the operational comparison point only; it is not the libvirt
backend proof.

## Native libvirt substrate

The accepted ACES/libvirt path is now native:

- `aces libvirt techvault validate-live` creates libvirt networks and QEMU
  domains from the ACES provisioning plan.
- Domains boot generated BusyBox initramfs appliances through libvirt/QEMU.
- The live gate no longer imports APTL, starts Docker Compose, or probes Docker
  containers.
- Clean boot removes prior `aces-techvault-*` libvirt domains/networks before
  realizing the next scenario, so a full TechVault run can be followed by a
  reduced variant without carrying over the old topology.

Local host setup for the proof:

```bash
sudo apt-get install -y qemu-system-x86 libvirt-daemon-system \
  libvirt-clients python3-libvirt iputils-ping
```

Because `libvirt-python` remains optional and lazy for normal CI, the local
manual run exposed only the system libvirt binding to the project venv:

```bash
mkdir -p /tmp/aces-libvirt-python
ln -s /usr/lib/python3/dist-packages/libvirt.py /tmp/aces-libvirt-python/libvirt.py
ln -s /usr/lib/python3/dist-packages/libvirtmod.cpython-312-x86_64-linux-gnu.so \
  /tmp/aces-libvirt-python/libvirtmod.cpython-312-x86_64-linux-gnu.so
```

The old APTL Docker lab was stopped before native libvirt runs because its
bridges already occupied the authored TechVault `172.20.x.0/24` CIDRs.

## Native reduced variants

These variants mirror the APTL curated scenario shapes and are ordinary SDL
inputs to the libvirt backend, not name-based presets.

### Observability core

```bash
sudo env PYTHONPATH=/tmp/aces-libvirt-python PATH=$PATH \
  /home/atomik/.local/bin/uv run --project implementations/python --frozen \
  aces libvirt techvault validate-live \
  --scenario /home/atomik/src/aces5/examples/scenarios/techvault-observability-core.sdl.yaml \
  --output-dir /tmp/aces-libvirt-native \
  --run-id native-observability-20260627T0820Z \
  --yes --boot-timeout-seconds 90 --appliance-memory-mib 64
```

Result: PASS.

Manifest:

```text
/tmp/aces-libvirt-native/runs/native-observability-20260627T0820Z/live-gate/manifest.json
```

Surface:

- Domains: `aptl-grafana-otel`, `aptl-otel-collector`, `aptl-tempo`
- Networks: `security-net`
- Service listeners: 4
- Substrate: `libvirt-qemu-initramfs`

### Attacker target

```bash
sudo env PYTHONPATH=/tmp/aces-libvirt-python PATH=$PATH \
  /home/atomik/.local/bin/uv run --project implementations/python --frozen \
  aces libvirt techvault validate-live \
  --scenario /home/atomik/src/aces5/examples/scenarios/techvault-attacker-target.sdl.yaml \
  --output-dir /tmp/aces-libvirt-native \
  --run-id native-attacker-target-20260627T0825Z \
  --yes --boot-timeout-seconds 120 --appliance-memory-mib 64
```

Result: PASS.

Surface:

- Domains: `aptl-grafana-otel`, `aptl-otel-collector`, `aptl-tempo`, `kali`,
  `kali-capture`, `victim`, `wazuh-indexer`, `wazuh-manager`
- Networks: `internal-net`, `redteam-net`, `security-net`
- Wazuh readback: `victim`, `wazuh-manager`

### Defensive minimum after full TechVault

The defensive-minimum variant was run after the full 30-domain scenario with
clean boot enabled, proving the backend recomposes the live surface instead of
over-starting the full topology.

```bash
sudo env PYTHONPATH=/tmp/aces-libvirt-python PATH=$PATH \
  /home/atomik/.local/bin/uv run --project implementations/python --frozen \
  aces libvirt techvault validate-live \
  --scenario /home/atomik/src/aces5/examples/scenarios/techvault-defensive-min.sdl.yaml \
  --output-dir /tmp/aces-libvirt-native \
  --run-id native-defensive-min-final-20260627T0855Z \
  --yes --boot-timeout-seconds 120 --appliance-memory-mib 64
```

Result: PASS.

Live libvirt state after the run:

- Running domains: `aces-techvault-aptl-grafana-otel`,
  `aces-techvault-aptl-otel-collector`, `aces-techvault-aptl-tempo`,
  `aces-techvault-wazuh-dashboard`, `aces-techvault-wazuh-indexer`,
  `aces-techvault-wazuh-manager`
- Active native network: `aces-techvault-security-net`
- No full-TechVault domains remained from the preceding run.

## Native full TechVault

Final command run from `/home/atomik/src/aces5` on 2026-06-27:

```bash
sudo env PYTHONPATH=/tmp/aces-libvirt-python PATH=$PATH \
  /home/atomik/.local/bin/uv run --project implementations/python --frozen \
  aces libvirt techvault validate-live \
  --scenario /home/atomik/src/aces5/examples/scenarios/techvault-operational.sdl.yaml \
  --output-dir /tmp/aces-libvirt-native \
  --run-id native-operational-final-20260627T0850Z \
  --yes --boot-timeout-seconds 240 --appliance-memory-mib 64
```

Result: PASS.

Manifest:

```text
/tmp/aces-libvirt-native/runs/native-operational-final-20260627T0850Z/live-gate/manifest.json
```

Surface:

- Domains: 30, matching `examples/scenarios/techvault-operational.sdl.yaml`
- Networks: `dmz-net`, `internal-net`, `redteam-net`, `security-net`
- Declared service listeners: 36
- Substrate: `libvirt-qemu-initramfs`

SOC readback:

- Case-management surface present: TheHive, MISP, Cortex, Shuffle
- Suricata readback: present, 49,954 rules loaded, 0 failed rules, 0 kernel
  drops
- Wazuh active-agent readback: `ad`, `db`, `dns`, `fileshare`, `suricata`,
  `victim`, `wazuh-manager`, `webapp`, `workstation`

Manual endpoint probes against the live native domains:

| Node | IP | Port | Result |
|---|---:|---:|---|
| `wazuh-manager` | `172.20.0.29` | 55000 | OK |
| `thehive` | `172.20.0.24` | 9000 | OK |
| `misp` | `172.20.0.15` | 443 | OK |
| `cortex` | `172.20.0.13` | 9001 | OK |
| `shuffle-frontend` | `172.20.0.20` | 80 | OK |
| `shuffle-backend` | `172.20.0.19` | 5001 | OK |
| `suricata` | `172.20.0.23` | 80 | OK |
| `webapp` | `172.20.1.14` | 8080 | OK |
| `kali` | `172.20.4.10` | 22 | OK |
| `victim` | `172.20.2.16` | 22 | OK |

## Regression coverage

Native coverage now includes:

- `test_libvirt_backend_techvault_integration.py`: the full TechVault SDL
  drives 30 node domains and four networks through runtime planning and
  provisioning.
- `test_libvirt_backend_techvault_native.py`: full TechVault and all four
  reduced variants realize distinct native libvirt surfaces; live manifest
  evidence is native and contains no Docker/APTL probe surface; clean boot
  removes prior libvirt resources.
- `test_libvirt_backend_cli.py`: CLI wiring passes connection, memory, and
  boot-timeout controls to the native live gate.

## Scope statement

This is a reference-backend operational proof, not an equivalence proof with
APTL. The libvirt backend boots native QEMU appliance domains and validates the
ACES-composed topology, network reachability, declared service listeners, and
SOC surface/readback. It does not claim byte-identical guest images, application
data, or upstream Wazuh/MISP/TheHive internals from the APTL Docker stack.
