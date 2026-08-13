---
id: GOV-913
title: "Trust And Integrity Of Reusable Assets"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 3
created_at: 2026-04-03T07:58:36.322037Z
updated_at: 2026-07-05T02:43:29.021311Z
---

# GOV-913 — Trust And Integrity Of Reusable Assets

## Statement

The ecosystem shall support trust, authenticity, and integrity policies for reusable scenarios, modules, tasks, studies, behavior vocabularies, and comparable reusable assets.

## Rationale

Requirement inventory expansion. Reusable ecosystem assets need explicit trust and integrity expectations so experiment meaning does not drift across reuse boundaries.

## Traceability

- IMPLEMENTS → SPEC `specs/supply-chain/reusable-asset-trust-integrity.md` (Reusable Asset Trust, Authenticity, and Integrity (normative spec))
- IMPLEMENTS → SPEC `contracts/schemas/asset-trust/reusable-asset-trust-policy-v1.json` (reusable-asset-trust-policy-v1 published schema)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-071-reusable-asset-trust-and-integrity-policy.md` (ADR-071: Reusable Asset Trust and Integrity Policy)
- TESTS → TEST `implementations/python/tests/test_reusable_asset_trust_policy.py` (Reusable-asset trust policy contract tests)
- IMPLEMENTS → GITHUB_ISSUE `1137` (Bounded retries for pinned CI tool downloads)
- IMPLEMENTS → CODE_FILE `tools/release_download.py` (Approved-origin, bounded transient retry policy)
- IMPLEMENTS → CODE_FILE `tools/http_download.py` (Compatibility facade for the governed release boundary)
- IMPLEMENTS → CODE_FILE `tools/policy/conftest_tool.py` (Conftest release acquisition adapter)
- IMPLEMENTS → CODE_FILE `tools/vale_tool.py` (Vale release acquisition adapter)
- IMPLEMENTS → CODE_FILE `tools/gitleaks_tool.py` (Gitleaks release acquisition adapter)
- IMPLEMENTS → CODE_FILE `tools/osv_scanner_tool.py` (OSV Scanner release acquisition adapter)
- TESTS → TEST `implementations/python/tests/test_release_download.py` (Retry classification, bounds, and integrity non-retry regressions)
- TESTS → TEST `implementations/python/tests/test_http_download.py` (Compatibility delegation and policy-cap regressions)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1137-ci-release-download-retries.md` (Release-download retry decision)
- IMPLEMENTS → GITHUB_ISSUE `115` (Trust & integrity of reusable assets (GOV-913))
- IMPLEMENTS → GITHUB_ISSUE `1098` (Upgrade vulnerable Click and cryptography locks and gate OSV findings)
- IMPLEMENTS → CONFIG `implementations/python/pyproject.toml` (Fixed Click and cryptography dependency floors)
- IMPLEMENTS → CONFIG `implementations/python/uv.lock` (Reviewed frozen dependency resolution)
- IMPLEMENTS → CONFIG `.github/workflows/ci.yml` (Required OSV dependency-vulnerability gate)
- IMPLEMENTS → CONFIG `noxfile.py` (Explicit OSV findings and scanner-error enforcement)
- IMPLEMENTS → CODE_FILE `tools/osv_scanner_tool.py` (OSV result classification)
- IMPLEMENTS → DOCUMENTATION `docs/decisions/issue-1098-gov-913-supply-chain-security-preflight.md` (Dependency vulnerability and gating preflight)
- TESTS → TEST `implementations/python/tests/test_repo_policy_tools.py` (Dependency-floor and OSV gate regression tests)
- DOCUMENTS → GITHUB_ISSUE `1106` (Cached OSV-Scanner integrity validation)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1106-gov-913-osv-cache-integrity.md` (Repository pin and atomic cache decision)
- IMPLEMENTS → CODE_FILE `tools/osv_scanner_tool.py` (Per-use cache type, mode, and digest validation)
- TESTS → TEST `implementations/python/tests/test_repo_policy_tools.py` (Tampered, symlinked, and atomic OSV cache regressions)
- DOCUMENTS → GITHUB_ISSUE `1096` (OCI module-registry reliability remediation)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1096-oci-module-registry-reliability-remediation.md` (OCI module-registry reliability decision)
- IMPLEMENTS → GITHUB_ISSUE `1107` (Bound OCI archive parsing and make cache/layout publication gapless)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1107-oci-archive-cache-publication-preflight.md` (Verified-bundle cache admission, bounded archive trees, and durable versioned publication preflight)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/module_registry/_archive.py` (Bounded gzip admission and safe tar extraction)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/module_registry/_verified_sources.py` (Descriptor-bound immutable OCI source graph)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/module_registry/_cache.py` (Anchored cache locking, bounded archive admission, and concurrent first-use recovery)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/module_registry/_filesystem.py` (Immutable version directories and atomic pointer repair)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/module_registry/publishing.py` (Deterministic bundles and durable OCI layout publication)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/module_registry/resolution.py` (Stable registry parsing and verified cache admission)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/composition/_expand.py` (Verified nested-source and admitted policy context propagation)
- TESTS → TEST `implementations/python/tests/test_sdl_module_registry.py` (Bundle-bound cache integrity, safe lock/depth handling, legacy-layout rejection, and atomic-pointer regressions)
- TESTS → TEST `implementations/python/tests/test_issue_1107_oci_source_snapshot.py` (Descriptor-bound source snapshot regressions)
