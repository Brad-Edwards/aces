---
id: GOV-866
title: "RAES Project Identity Migration"
status: ACTIVE
type: CONSTRAINT
priority: MUST
created_at: 2026-07-24T19:02:16.997614Z
updated_at: 2026-07-25T16:23:46.815033Z
---

# GOV-866 — RAES Project Identity Migration

## Statement

Repository-owned current-state prose, public command surfaces, package distribution metadata, MCP tool surfaces, machine-readable guidance surfaces, and migration documentation shall use Reproducible Agentic Environments System (RAES) as the canonical project identity, and old ACES public command, MCP, package, and guidance aliases shall be removed rather than preserved. ACES identifiers may remain only as documented source import paths, governed contract or schema identifiers, external workflow or service keys, historical records, or other surfaces whose owning migration is out of scope for issue 866.

## Rationale

Issue 866 is a hard-cutover project rename that needs a durable governance and traceability anchor so implementation files, removed public aliases, tests, and migration documentation can be reconciled under the repository policy gates.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `866` (Rename ACES to RAES across repository surfaces)
- IMPLEMENTS → GITHUB_ISSUE `866` (Issue #866 RAES project identity migration)
- IMPLEMENTS → PULL_REQUEST `870` (PR #870 feat: cut over public surfaces to RAES)
- IMPLEMENTS → PULL_REQUEST `879` (PR #879 fix(release): publish package as raes)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-093-raes-rename-and-compatibility-boundaries.md` (ADR-093 RAES rename and compatibility boundaries)
- IMPLEMENTS → DOCUMENTATION `docs/migration/raes-rename.md` (RAES hard cutover migration map)
- IMPLEMENTS → CONFIG `release-please-config.json` (release-please package name set to raes)
- IMPLEMENTS → CONFIG `.github/workflows/release-please.yml` (release workflow validates raes wheel artifacts)
- IMPLEMENTS → CONFIG `implementations/python/pyproject.toml` (Python distribution and console scripts expose RAES package identity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_cli/main.py` (RAES CLI version/help identity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/server.py` (RAES MCP server identity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/operations.py` (RAES MCP tool surface payload)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/agent_guidance.py` (RAES machine-readable guidance identifiers)
- IMPLEMENTS → SPEC `specs/agent-guidance/agent-guidance.yaml` (RAES canonical agent guidance profile id)
- IMPLEMENTS → CODE_FILE `implementations/python/src/aces/__init__.py` (Version derives from the raes distribution metadata)
- IMPLEMENTS → CODE_FILE `tools/check_agent_guidance.py` (RAES agent guidance policy validation)
- TESTS → TEST `implementations/python/tests/test_version_classification.py` (Distribution, CLI, OpenAPI version, and old command removal tests)
- TESTS → TEST `implementations/python/tests/test_mcp_server.py` (RAES MCP registration and old alias removal tests)
- TESTS → TEST `implementations/python/tests/test_agent_guidance.py` (RAES guidance profile identifier tests)
- TESTS → TEST `implementations/python/tests/test_agent_guidance_policy.py` (RAES guidance policy validation tests)
- TESTS → TEST `implementations/python/tests/test_corpus_packaging.py` (Installed raes wheel corpus packaging tests)
- IMPLEMENTS → DOCUMENTATION `docs/decisions/issue-907-raes-env-packs-naming-preflight.md` (Issue 907 RAES ecosystem naming preflight)
- IMPLEMENTS → CODE_FILE `tools/check_identity_cutover.py` (RAES identity cutover policy gate)
- IMPLEMENTS → POLICY `tools/policy/historical_identity_records.json` (Content-bound historical identity policy records)
- TESTS → TEST `implementations/python/tests/test_identity_cutover_policy.py` (RAES identity cutover policy tests)
