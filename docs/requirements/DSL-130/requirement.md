---
id: DSL-130
title: "Security-Monitoring Manager Runtime Inventory"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-05-29T00:46:56.674955Z
updated_at: 2026-05-29T00:47:01.727541Z
---

# DSL-130 — Security-Monitoring Manager Runtime Inventory

## Statement

The language shall represent SIEM and security-monitoring manager logical runtime state as typed node-scoped runtime inventory, including manager identity, listeners, components, enrolled agents, agent groups, detection content sets, bounded settings, and evidence references, without overloading transport services, processes, service-manager units, filesystem evidence, raw configuration, event telemetry, or prose-only relationships.

## Rationale

Issue #428 identifies a downstream inventory blocker from APTL TechVault Wazuh manager capture: ACES could represent surrounding transport, process, unit, filesystem, package, and HTTP/API evidence, but lacked a typed, queryable surface for SIEM/security-monitoring manager inventory and detection-manager state.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Semantic validation for security-monitoring managers)
- IMPLEMENTS → GITHUB_ISSUE `428` (SDL gap: SIEM and security-monitoring manager runtime inventory)
- IMPLEMENTS → PULL_REQUEST `432` (Add security-monitoring manager runtime inventory)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_security_monitoring.py` (Security-monitoring runtime models)
- TESTS → TEST `implementations/python/tests/test_runtime_security_monitoring.py` (Runtime security-monitoring tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_configuration.py` (Runtime configuration surface wiring)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/nodes.py` (SDL node exports for security-monitoring runtime types)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_module_symbols.py` (Module alias rewriting for security-monitoring refs)
- IMPLEMENTS → CONFIG `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema security-monitoring surface)
- IMPLEMENTS → CONFIG `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated scenario schema security-monitoring surface)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-040-security-monitoring-manager-runtime-inventory.md` (ADR-040 Security-Monitoring Manager Runtime Inventory)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md` (SDL lineage security-monitoring manager semantics)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (SDL precedents security-monitoring manager rationale)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections security-monitoring manager reference)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL validation security-monitoring manager rules)
- DOCUMENTS → DOCUMENTATION `docs/index.md` (Documentation index security-monitoring manager entry)
- DOCUMENTS → DOCUMENTATION `changelog.d/428.added.md` (Changelog entry for security-monitoring manager inventory)
- DOCUMENTS → DOCUMENTATION `docs/decisions/adrs/README.md` (ADR index entry for security-monitoring manager inventory)
- DOCUMENTS → SPEC `https://doi.org/10.6028/NIST.SP.800-92` (NIST SP 800-92: Guide to Computer Security Log Management)
- DOCUMENTS → DOCUMENTATION `https://documentation.wazuh.com/current/user-manual/manager/index.html` (Wazuh server/manager documentation)
- DOCUMENTS → DOCUMENTATION `https://documentation.wazuh.com/current/user-manual/api/reference.html` (Wazuh API reference)
- DOCUMENTS → DOCUMENTATION `https://documentation.wazuh.com/current/user-manual/agent/agent-management/grouping-agents.html` (Wazuh agent grouping documentation)
- DOCUMENTS → SPEC `https://schema.ocsf.io/` (Open Cybersecurity Schema Framework schema browser)
- DOCUMENTS → SPEC `https://sigmahq.io/docs/basics/rules.html` (Sigma detection rules documentation)
- DOCUMENTS → DOCUMENTATION `https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/rules.html` (Wazuh rules syntax documentation)
- DOCUMENTS → DOCUMENTATION `https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/decoders.html` (Wazuh decoders syntax documentation)
