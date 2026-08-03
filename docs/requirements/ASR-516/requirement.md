---
id: ASR-516
title: "RAES Authoring Adapter Semantic Consistency"
status: DRAFT
type: FUNCTIONAL
priority: SHOULD
wave: 3
created_at: 2026-04-03T07:17:05.483661Z
updated_at: 2026-07-30T18:38:11.148501Z
---

# ASR-516 — RAES Authoring Adapter Semantic Consistency

## Statement

RAES shall publish conformance vectors that let CLI, agent or MCP, graphical, and documentation-driven adapters prove that they produce equivalent canonical RAES artifacts, diagnostics, and semantic results for the same admitted inputs. Concrete user journeys, pack files, and runtime outcomes remain under their owning repositories.

## Rationale

Retains the RAES conformance responsibility while HUB-6 owns cross-product task and acceptance coordination.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `516` (Issue 516 inventory target secret boundary)
- DOCUMENTS → DOCUMENTATION `docs/aces/inventory/asset-inventory-methodology.md` (Participant-discoverable asset inventory methodology)
- DOCUMENTS → DOCUMENTATION `docs/aces/inventory/issue-516-redaction-boundary-preflight.md` (Issue 516 inventory redaction boundary preflight)
- DOCUMENTS → DOCUMENTATION `.codex-skills/aces-asset-inventory-capture/SKILL.md` (Codex asset inventory capture skill)
- DOCUMENTS → DOCUMENTATION `.claude/skills/aces-asset-inventory-capture/SKILL.md` (Claude asset inventory capture skill)
- DOCUMENTS → CODE_FILE `.codex-skills/aces-asset-inventory-capture/scripts/capture-container-evidence-template.sh` (Codex capture container evidence template)
- DOCUMENTS → CODE_FILE `.claude/skills/aces-asset-inventory-capture/scripts/capture-container-evidence-template.sh` (Claude capture container evidence template)
- TESTS → TEST `implementations/python/tests/test_agent_inventory_skill.py` (Agent inventory skill and template regression tests)
- DOCUMENTS → DOCUMENTATION `docs/aces/inventory/ad-preflight.md` (AD inventory preflight guidance)
- DOCUMENTS → DOCUMENTATION `docs/aces/inventory/webapp-preflight.md` (Webapp inventory preflight guidance)
- DOCUMENTS → DOCUMENTATION `docs/aces/inventory/kali-preflight.md` (Kali inventory preflight guidance)
- DOCUMENTS → GITHUB_ISSUE `1005` (ASR-516 — RAES Authoring Adapter Semantic Consistency)
