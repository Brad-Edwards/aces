# aces-sdl plan rules

Mandatory constraints the `/implement` skill applies during plan phase.
These encode the hard rules previously in `AGENTS.md` prose.

- Plans MUST run `implementations/python/.venv/bin/python tools/check_repo_policy.py`
  before declaring completion.
- Plans MUST run `implementations/python/.venv/bin/python tools/check_requirement_governance.py`
  before declaring completion.
- Plans MUST run `implementations/python/.venv/bin/python tools/verify_all.py`
  before declaring completion.
- Plans MUST set `ACES_REQUIREMENT_UID` when the branch name does not
  already contain a UID such as `GOV-918`.
- Plans MUST NOT add new authority-bearing artifacts outside `specs/`,
  `contracts/`, `docs/`, and `implementations/`.
- Plans that change a published schema under `contracts/schemas/` (the
  hand-governed normative authority per ADR-009 §7) MUST record a
  contract-facing change-ledger entry (`last_change`: summary + content hash)
  in `contracts/schema-publication-manifest.json`, and a plan that **removes**
  a published schema MUST record a `removed_schemas` tombstone (schema path +
  summary) in the same manifest. Plans MUST keep the reference implementation
  (`schema_bundle()`) generating an identical bundle so
  `tools/check_generated_schemas.py` passes. The published schema is the
  authority; a generator/Python edit alone is NOT authorization for a schema
  change.
- Plans MUST NOT add new implementation logic to
  `implementations/python/src/aces/`; that tree is compatibility-only
  wrappers.
- Plans MUST NOT import `aces.*` from owning packages under
  `implementations/python/packages/`.
- Plans MUST keep concept-authority artifacts in the approved
  concept-authority surfaces.
- Plans MUST keep IMPLEMENTS and TESTS traceability in Ground Control
  aligned with changed code and tests.
- Plans with a user-visible change MUST add a fragment under
  `changelog.d/<issue>.<type>.md` (or `changelog.d/+<slug>.<type>.md`
  for issue-free entries), where `<type>` is one of `security`, `added`,
  `changed`, `deprecated`, `removed`, `fixed`; do not edit `CHANGELOG.md`
  directly outside release-collation commits.
