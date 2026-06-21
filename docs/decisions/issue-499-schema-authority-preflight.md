# Issue 499 Schema Authority Preflight

Date: 2026-06-14

Issue: #499.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for flipping published
schema authority per ADR-009 section 7. It is guidance for the implementation
and does not implement the checker, manifest ledger, schema edits, or tests.

## Binding Sources

- ADR-009 decides that normative schemas exist independently and that
  validation proves implementation compatibility with normative artifacts.
- ADR-019 and `specs/authority/authority-boundary.yaml` are the canonical
  authority-boundary seam: `contracts/schemas/` is normative, and
  implementations are non-normative consumers.
- ADR-061 and `contracts/schema-publication-manifest.json` are the schema
  publication and evolution seam. Extend this seam; do not add a second schema
  registry or review ledger.
- The GitHub issue depends on CT-6 prose-spec work and pairs with CT-1
  schema-evolution policy. If either surface is absent, make the remaining
  milestone explicit instead of implying full steady state.

## Architecture Decisions

- Published files under `contracts/schemas/` are the hand-governed normative
  contract artifacts. Python models and `schema_bundle()` are compatibility
  evidence, not schema authority.
- `tools/check_generated_schemas.py` should keep its byte-match mechanics but
  report the inverted meaning: the reference implementation must generate the
  same schemas as the published normative set.
- `contracts/schema-publication-manifest.json` remains the only schema
  publication registry. Add any per-schema contract-review/change ledger fields
  there, keyed by the existing `contract_id` and `schema_path` identity.
- The process gate should fail a `contracts/schemas/` change unless the same
  change set carries a manifest ledger entry with a contract-facing or
  spec-facing rationale. Do not satisfy this with a generator-driver edit.
- `.gc/plan-rules.md`, `tools/policy/conftest/repo_policy.rego`, tool help,
  and living contributor guidance must stop calling direct schema edits
  forbidden generated-output edits. Historical accepted ADR text should not be
  rewritten in place unless ADR-059 amendment rules are followed.

## Required Incumbents

- Authority boundary: ADR-009, ADR-019,
  `specs/authority/authority-boundary.yaml`, and
  `tools/check_authority_boundary.py`.
- Schema publication/evolution: ADR-061,
  `contracts/schema-publication-manifest.json`,
  `tools/check_schema_publication.py`, and
  `implementations/python/tests/test_repo_policy_tools.py`.
- Compatibility proof: `aces_contracts.contracts.schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  and `test_published_contract_schemas_exist_and_match_bundle`.
- Workflow policy: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/policy/adr_policy.yaml`,
  `tools/policy/conftest/repo_policy.rego`, and `noxfile.py` policy/contracts
  sessions.
- Artifact validation: `tools/check_json_artifacts.py`,
  `check-jsonschema`, closed-world `ContractModel` descendants, and existing
  valid/invalid fixture conventions.

## Cross-Cutting Layers

- JSON/config parsing: use `json.loads` and `yaml.safe_load` with explicit
  mapping/list/string checks. Do not evaluate schema content, fetch remote
  `$ref` targets, or coerce malformed ledger fields to empty defaults.
- Repo-path security: ledger paths and refs must be normalized repo-relative
  paths, reject absolute paths and `..`, and reuse `_safe_schema_path()` or
  `safe_repo_path()`-equivalent checks before any file read.
- Git/base-revision input: compare changed schemas through the existing
  `--base-rev` path in `noxfile.py` and fixed-argv `subprocess.run` calls.
  Do not introduce shell command construction.
- Policy error surface: preserve existing CLI behavior: Rego failures return
  `rule_id`/`msg`/`path`, Python policy failures use `PolicyFailure`, and
  schema-publication failures stay concise. Do not dump schema bodies,
  environment variables, or tracebacks.
- Secret and OS exposure: this governance path should read only checked-in
  repo files and Git metadata. Review refs, spec refs, and change summaries
  must not contain credentials, bearer tokens, private keys, environment
  bindings, or command examples that put secrets in process argv.

## Extension Boundary

The extension seam is the manifest entry for a published `contract_id`, plus a
change-ledger field that can be checked against a base revision. Future schema
families, stability levels, or review references should extend that manifest
shape and checker validation, not add sidecar ledgers or hard-code today's
contract ids in Rego or Python.

The obvious future parameter is the comparison base revision. Keep it threaded
through the existing `--base-rev` nox/checker route so local, CI, and staged
checks do not grow separate policy semantics.

## Gotchas And Anti-Patterns

Avoid:

- keeping the old Rego rule that treats a generator-driver edit as sufficient
  authorization for schema changes;
- adding a second schema manifest, review ledger, schema registry, fixture
  loader, or compatibility checker;
- making the ledger a PR-template prose convention that policy cannot inspect;
- keying review evidence by Python class, generator function, or output path
  alone instead of `contract_id` and `schema_path`;
- silently dropping the extra-published-schema check from
  `check_generated_schemas.py`; in the new semantics it proves the reference
  bundle covers every normative schema;
- weakening ADR-061 stable-schema compatibility checks while adding review
  metadata;
- rewriting accepted historical ADR bodies or old research notes as part of
  this issue unless the ADR-059 amendment and pin gate requires it.

## Non-Goals

- Editing published schemas or the manifest ledger in this preflight note.
- Implementing the policy gate, checker tests, or nox wiring here.
- Changing SDL prose semantics, contract payload shapes, or stability classes
  except where the implementation PR deliberately edits a contract surface.
- Moving schema authority into Python models, generated bindings, fixtures,
  examples, docs, or the compatibility `implementations/python/src/aces/`
  tree.
