# AD RAES Inventory Preflight

This is a historical APTL TechVault validation note imported into RAES as a
reference example. It is not the methodology authority; the canonical RAES
methodology is `docs/raes/inventory/asset-inventory-methodology.md`.

This note records the local architecture preflight for SCN-010 / issue #332.
The Ground Control `gc_codex_architecture_preflight` call completed and wrote
the issue phase marker, but the tool did not create a repo-local note file.

## Binding Guardrails

- Keep this work as an RAES inventory and specification update. Evidence,
  Docker output, package manifests, scanner output, checksums, and ledgers are
  proof inputs only; catalogued facts that RAES can express belong in
  `scenarios/techvault.sdl.yaml`.
- Do not create an APTL-local schema, parser, validator, Pydantic model, or
  runtime exception hierarchy for AD inventory facts.
- Reuse `docs/raes/inventory/asset-inventory-methodology.md`,
  `src/aptl/core/aces_inventory.py`, `src/aptl/cli/aces_inventory.py`, the
  existing webapp and db inventory bundles, and `docs/raes/parity-inventory.yaml`.
- Historical note: issue #516 supersedes the original blanket-redaction rule
  for source inventory bundles. Preserve AD administrator credentials,
  generated flags, Kerberos/Samba secret material, Wazuh client keys, and
  private key contents when they are participant-discoverable scenario-target
  facts; withhold only operator/out-of-scenario material and record that
  boundary in `capture-limits.txt`.
- Keep legacy `aptl.core.sdl` and `scenarios/*.yaml` functional until the
  downstream APTL ADR-035 cutover PR. This issue does not change backend
  runtime behavior or flip default scenario selection.

## Applied Scope

The implementation captures the realized `aptl-ad` container after a fresh
`uv run aptl lab stop -v -y && uv run aptl lab start --skip-seed`, then records
the AD inventory under `docs/raes/inventory/ad/`, maps every catalogued fact in
`mapping-ledger.yaml`, and encodes the AD host, Samba domain, runtime, network,
service, identity, vulnerability, content, and relationship facts in
`scenarios/techvault.sdl.yaml`.
