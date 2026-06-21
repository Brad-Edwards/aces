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
- [Reference asset-inventory issue template](asset-inventory-issue-template.md)
  is the vendorable GitHub issue skeleton downstream backends can copy into
  their own `.github/ISSUE_TEMPLATE/` trees.
- [SCN-010 expressivity gap analysis](scn010-expressivity-gap-analysis.md)
  is the peer-review-grade analysis of the ACES SDL runtime-surface
  expressivity gaps found while holding the 16 remaining APTL TechVault
  SCN-010 SOC-stack containers to the wazuh.manager parity depth bar, and
  the cohesive whole-SDL architecture that resolves them (requirements
  DSL-132 through DSL-139).
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
asset-inventory-issue-template
scn010-expressivity-gap-analysis
issue-516-redaction-boundary-preflight
webapp-preflight
kali-preflight
ad-preflight
```
