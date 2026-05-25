# ACES Asset Inventory Methodology

ACES owns the participant-discoverable asset inventory methodology. Downstream
projects can implement capture tooling and evidence ledgers, but the inclusion
rule, semantic gates, and capture-to-specification workflow live here.

Use these documents as the ACES authority:

- [Participant-discoverable asset inventory methodology](asset-inventory-methodology.md)
  defines the canonical capture workflow, evidence boundary, ACES mapping
  dispositions, and gap-handling rules.
- [Methodology assurance report](methodology-assurance-report.md) records the
  DevOps, supply-chain, reproducible-research, and verification/validation
  basis for the method.
- The preflight notes are imported validation records from the APTL TechVault
  proof work. They are useful implementation examples for downstream asset
  captures, but they do not replace the methodology.

The original TechVault proof bundles remain in APTL as downstream evidence
artifacts. ACES keeps the methodology and reusable agent entry points so later
range implementations can consume the same rules without making APTL the
methodology owner.

```{toctree}
:maxdepth: 1

asset-inventory-methodology
methodology-assurance-report
webapp-preflight
kali-preflight
ad-preflight
```
