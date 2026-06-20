---
name: ACES Asset Inventory
about: Capture participant-discoverable asset evidence and map it to ACES.
title: "[INVENTORY] <scenario>: <asset>"
labels: enhancement
assignees: ""
---

# ACES Asset Inventory Issue Template

Copy this file, or the body below, into a downstream backend repository's
`.github/ISSUE_TEMPLATE/` tree when that repository needs an issue form for
inventorying realized scenario assets against the ACES methodology.

## Methodology Authority

Use the ACES participant-discoverable asset inventory methodology as the
authority:

- Methodology:
  `docs/aces/inventory/asset-inventory-methodology.md`
- Assurance report:
  `docs/aces/inventory/methodology-assurance-report.md`
- Agent workflow:
  `.codex-skills/aces-asset-inventory-capture/SKILL.md` and
  `.claude/skills/aces-asset-inventory-capture/SKILL.md`

## Target

- Scenario:
- Asset id:
- Asset kind: image / running container / VM / host / composed service / other
- Backend/runtime:
- Expected source class: custom-build / upstream-image / runtime-composed
- Allowed discovery vantages:
- Destructive reset allowed: yes / no

## Scope

Capture every fact that a participant or in-range agent could discover from
the realized range. Do not filter by relevance, intent, current backend
support, or elegance. Host-side Docker or backend evidence may support
provenance, but it does not shrink the participant-discoverable boundary.

Operator/out-of-scenario secrets are outside the inventory boundary. Exclude
them or record a first-class `capture-limits.txt` entry. Scenario-target
secrets are capture facts when an in-range participant or agent could discover
them.

## Required Bundle

The asset bundle should include:

- `README.md` with scope, target identity, commands, and limits.
- `capture-evidence.sh` or equivalent committed capture commands.
- `mapping-ledger.yaml`.
- `evidence/captured-at-utc.txt`.
- `evidence/capture-limits.txt`.
- `evidence/evidence-sha256sums.txt`.
- Raw evidence for discovery vantage, runtime state, provenance, package/SBOM,
  vulnerability, filesystem, relationship, and trust-surface facts.

For Docker/Compose/container-image captures, start from:

- `.codex-skills/aces-asset-inventory-capture/scripts/capture-container-evidence-template.sh`
- `.codex-skills/aces-asset-inventory-capture/scripts/normalize-syft-cyclonedx.jq`

## Capture Checklist

- [ ] Defined all in-range discovery vantages.
- [ ] Captured participant-discoverable network, service, process, package,
      filesystem, credential, trust, relationship, data, and configuration
      facts.
- [ ] Captured source provenance, immutable image/artifact identifiers, runtime
      configuration, and scanner/tool versions.
- [ ] Captured required Trivy CycloneDX SBOM and Trivy vulnerability JSON, or
      recorded a first-class limit with ledger reference.
- [ ] Attempted Syft, osquery, and filesystem-manifest capture where
      applicable, or recorded first-class limits with ledger references.
- [ ] Kept every evidence-affecting normalization deterministic and committed
      as script or jq.
- [ ] Generated `evidence-sha256sums.txt` after evidence capture.

## Mapping And Gap Triage

For every captured fact, record one mapping disposition in
`mapping-ledger.yaml`:

- `encoded`
- `encoded_with_caveat`
- `blocked_by_aces_gap`
- `blocked_by_aptl_gap`
- `needs_gap_triage` only while actively triaging

Before completion:

- [ ] No `needs_gap_triage` mapping remains.
- [ ] Every evidence file is referenced by a fact, provenance entry,
      correspondence check, or capture-limit fact.
- [ ] Every `blocked_by_aces_gap` row links an ACES issue.
- [ ] Every `blocked_by_aptl_gap` row links a downstream backend issue.
- [ ] Correspondence checks describe how later encoding work will compare ACES
      surfaces against fresh realized evidence.

## Validation

Run the downstream ledger validator before closing:

```shell
aptl aces-inventory schema
aptl aces-inventory validate <asset-dir>
aptl aces-inventory gaps <asset-dir>
```

Also run the backend repository's normal test and documentation checks for any
changed code, docs, templates, or committed evidence.

## Completion Claim

This issue is complete only when every participant-discoverable fact in scope
is captured, mapped to ACES, or blocked by a linked ACES/downstream issue with
an explicit limitation. Evidence bundles, scanner output, screenshots,
summaries, and backend support limits are proof inputs only; they do not
replace ACES specification or explicit gap records.
