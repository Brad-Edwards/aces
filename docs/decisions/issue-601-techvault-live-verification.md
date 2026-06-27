# Issue 601 TechVault Live Verification

This note records the live TechVault smoke used while implementing the
libvirt provisioning backend. It is evidence for the full operational
TechVault bar that the libvirt planning/provisioning regression now mirrors.

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

## ACES/libvirt parity regression

The ACES regression in
`implementations/python/tests/test_libvirt_backend_techvault_integration.py`
now drives `examples/scenarios/techvault-operational.sdl.yaml`, the same
30-node/four-network operational surface, through:

1. SDL parse
2. runtime planning
3. provisioning-plan generation
4. `RuntimeControlPlane.submit_provisioning`
5. libvirt driver realization intent
6. runtime snapshot reconciliation

That regression proves dynamic composition through the issue-601 libvirt
provisioning boundary. A live libvirt VM boot of the SOC stack is not claimed
by this issue because the current branch does not ship TechVault VM images,
guest boot configuration, or SOC service/readiness probes for libvirt.
