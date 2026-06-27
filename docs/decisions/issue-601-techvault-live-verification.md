# Issue 601 TechVault Live Verification

This note records the live TechVault smoke used while implementing the
libvirt provisioning backend. It includes both the baseline APTL live gate and
the ACES/libvirt operational parity gate added for issue 601.

## APTL full live gate

Command run from `/home/atomik/src/aptl` on 2026-06-27:

```bash
uv run aptl lab validate-live --yes --run-id aces-601-libvirt-techvault-live-20260627
```

Result: PASS.

The gate reported all live checks passing:

- `static_prerequisite`
- `boot_inputs_match_public_path`
- `aces_driven_boot`
- `defensive_stack_readiness`
- `kali_reachability`
- `telemetry_evidence_path`
- `scenario_variation`
- `run_archive_manifest`

The run archive manifest was written to:

```text
/home/atomik/src/aptl/runs/aces-601-libvirt-techvault-live-20260627/live-gate/manifest.json
```

Manifest summary:

- Scenario: `scenarios/techvault-operational.sdl.yaml`
- Selected profiles: `wazuh`, `victim`, `kali`, `enterprise`, `soc`,
  `fileshare`, `dns`, `otel`
- ACES-realized nodes: 30
- Snapshot containers: 31 total, including the exited Cortex init container
- Running `aptl-*` containers after the gate: 30
- Networks: `aptl_aptl-dmz`, `aptl_aptl-internal`,
  `aptl_aptl-redteam`, `aptl_aptl-security`
- Kali reachability targets: `aptl-victim`, `aptl-workstation`,
  `aptl-webapp`, `aptl-wazuh-manager`, `aptl-db`, `aptl-fileshare`,
  `aptl-dns`, `aptl-ad`, `aptl-suricata`
- Telemetry window: `2026-06-27T01:34:10.554151+00:00` to
  `2026-06-27T01:34:22.252573+00:00`
- Wazuh alert count in the gate summary: 3
- Suricata event types in the gate summary: `stats: 2`

Manual readback after the gate:

- Wazuh `agent_control -l`: 10 agents listed, 10 active.
- Wazuh `alerts.json` contained the live-gate failed SSH activity:
  three rule `5710` events, `sshd: Attempt to login using a non-existent user`,
  at `2026-06-27T01:34:11.282+0000` and `2026-06-27T01:34:11.782+0000`.
- Wazuh `alerts.json` also showed new `files.techvault.local` and
  `dc.techvault.local` agent connections during the same gate window.
- Suricata `eve.json` readback contained 78 events total:
  `alert: 24`, `flow: 1`, `netflow: 1`, `stats: 52`.
- Suricata stats reported 96 kernel packets, 0 kernel drops, 49,954 rules
  loaded, and 0 failed rules.

## ACES/libvirt operational parity gate

Command run from `/home/atomik/src/aces5` on 2026-06-27:

```bash
uv run --project implementations/python --frozen aces libvirt techvault validate-live \
  --scenario /home/atomik/src/aces5/examples/scenarios/techvault-operational.sdl.yaml \
  --project-dir /home/atomik/src/aptl \
  --run-id aces-libvirt-techvault-live-20260627T0218Z \
  --yes
```

Result: PASS.

The command performed a destructive clean boot and drove the scenario through
the ACES/libvirt provisioning path before running the live checks:

- `run_id_input`
- `planning`
- `aces_libvirt_driven_boot`
- `defensive_stack_readiness`
- `kali_reachability`
- `telemetry_evidence_path`
- `scenario_variation`
- `run_archive_manifest`

The run archive manifest was written to:

```text
/home/atomik/src/aptl/runs/aces-libvirt-techvault-live-20260627T0218Z/live-gate/manifest.json
```

A follow-up non-destructive readback run exercised the strengthened SOC check:

```bash
uv run --project implementations/python --frozen aces libvirt techvault validate-live \
  --scenario /home/atomik/src/aces5/examples/scenarios/techvault-operational.sdl.yaml \
  --project-dir /home/atomik/src/aptl \
  --run-id aces-libvirt-techvault-live-readback-20260627T0218Z \
  --skip-clean-boot
```

Result: PASS, including `soc_stack_readback`.

Readback manifest summary:

- Selected profiles: `wazuh`, `victim`, `kali`, `enterprise`, `soc`,
  `fileshare`, `dns`, `otel`
- Snapshot containers: 31
- Networks: 4
- Telemetry window: `2026-06-27T03:58:29.804184+00:00` to
  `2026-06-27T03:58:41.259287+00:00`
- Wazuh alert count in the gate summary: 3
- Wazuh active agents in SOC readback: `wazuh.manager`,
  `aptl-webapp-agent`, `aptl-suricata-agent`, `aptl-db-agent`,
  `aptl-dns-agent`, `aptl-fileshare-agent`, `aptl-ad-agent`,
  `ns1.techvault.local`, `dc.techvault.local`, `files.techvault.local`,
  `webapp`
- Suricata readback: 86 events, 48 alerts, 36 stats records, 186 kernel
  packets, 0 kernel drops, 49,954 rules loaded, 0 failed rules

A final destructive run after moving the live orchestration into
`aces_operations` and strengthening the SOC readback gate also passed:

```bash
uv run --project implementations/python --frozen aces libvirt techvault validate-live \
  --scenario /home/atomik/src/aces5/examples/scenarios/techvault-operational.sdl.yaml \
  --project-dir /home/atomik/src/aptl \
  --run-id aces-libvirt-techvault-final-strict-20260627T0415Z \
  --yes
```

Result: PASS, including `soc_stack_readback`.

The run archive manifest was written to:

```text
/home/atomik/src/aptl/runs/aces-libvirt-techvault-final-strict-20260627T0415Z/live-gate/manifest.json
```

Strict SOC readback summary:

- Wazuh active agents: `wazuh.manager`, `aptl-dns-agent`,
  `aptl-fileshare-agent`, `aptl-ad-agent`, `aptl-webapp-agent`,
  `aptl-suricata-agent`, `aptl-db-agent`, `ns1.techvault.local`,
  `dc.techvault.local`, `files.techvault.local`, and `webapp`
- Telemetry window: `2026-06-27T04:10:16.739674+00:00` to
  `2026-06-27T04:10:28.150274+00:00`
- Wazuh alert count in the gate summary: 3
- Suricata readback: 45 events, 24 alerts, 19 stats records, 88 kernel
  packets, 0 kernel drops, 49,954 rules loaded, 0 failed rules

A final current-head destructive run after the SonarCloud hardening commits
also passed from commit `43a4d5b`:

```bash
uv run --project implementations/python --frozen aces libvirt techvault validate-live \
  --scenario /home/atomik/src/aces5/examples/scenarios/techvault-operational.sdl.yaml \
  --project-dir /home/atomik/src/aptl \
  --run-id aces-libvirt-techvault-final-head-20260627T0550Z \
  --yes
```

Result: PASS, including `soc_stack_readback`.

The run archive manifest was written to:

```text
/home/atomik/src/aptl/runs/aces-libvirt-techvault-final-head-20260627T0550Z/live-gate/manifest.json
```

Current-head SOC readback summary:

- Selected profiles: `wazuh`, `victim`, `kali`, `enterprise`, `soc`,
  `fileshare`, `dns`, `otel`
- ACES/libvirt mapped TechVault nodes: 30
- Running `aptl-*` containers after the gate: 30
- Telemetry window: `2026-06-27T05:47:45.851134+00:00` to
  `2026-06-27T05:47:57.261119+00:00`
- Wazuh alert count in the gate summary: 4
- Wazuh active agents: `wazuh.manager`, `aptl-dns-agent`,
  `aptl-webapp-agent`, `aptl-ad-agent`, `aptl-fileshare-agent`,
  `aptl-db-agent`, `aptl-suricata-agent`, `dc.techvault.local`,
  `files.techvault.local`, and `ns1.techvault.local`
- Wazuh manual readback in the telemetry window: 4 alerts, including
  three rule `5710` failed SSH events and one rule `19003` SCA summary event
- Suricata gate readback: 45 events, 24 alerts, 19 stats records, 89 kernel
  packets, 0 kernel drops, 49,954 rules loaded, 0 failed rules
- Suricata manual readback after the gate: 51 events, including 24 alerts,
  1 flow, 1 netflow, and 25 stats records; latest stats still reported
  89 kernel packets, 0 kernel drops, 49,954 rules loaded, and 0 failed rules

## ACES/libvirt regression coverage

The ACES regression in
`implementations/python/tests/test_libvirt_backend_techvault_integration.py`
now drives `examples/scenarios/techvault-operational.sdl.yaml`, the same
30-node/four-network operational surface, through:

1. SDL parse
2. runtime planning
3. provisioning-plan generation
4. `RuntimeControlPlane.submit_provisioning`
5. the TechVault operational libvirt driver
6. runtime snapshot reconciliation

The live command proves that the new reference backend can deliver TechVault
through ACES to the same operational level as the APTL smoke: startup,
readiness, Kali reachability, telemetry generation, Wazuh readback, Suricata
readback, and a run-archive manifest.
