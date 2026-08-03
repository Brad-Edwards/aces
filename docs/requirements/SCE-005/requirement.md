---
id: SCE-005
title: "Scenario Generation from ATT&CK Layers and Threat Intel"
status: DRAFT
type: FUNCTIONAL
priority: COULD
wave: 3
created_at: 2026-07-15T03:17:25.906650Z
updated_at: 2026-07-15T03:17:25.906650Z
---

# SCE-005 — Scenario Generation from ATT&CK Layers and Threat Intel

## Statement

The platform shall support generating scenario specifications from MITRE ATT&CK Navigator layer files and/or threat intelligence feeds (STIX bundles, APT reports), automatically mapping selected techniques to executable scenario steps.

## Rationale

Manual scenario authoring doesn't scale. Aurora (2024) demonstrated PDDL-based generation from CTI with 1,800+ actions. Auto-generation from ATT&CK layers enables rapid scenario creation from real-world threat profiles.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `654` (SCE-005 — Generate admitted SDL candidates from ATT&CK and threat intelligence)
