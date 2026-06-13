# Issue 485 Assurance Fulfillment Preflight

Date: 2026-06-13

Issue: #485.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for adding the assurance
fulfillment gate. It is guidance for the implementation and does not implement
the checker, the fulfillment map, or the tests.

## Binding Sources

- ADR-007 defines the FM0-FM3 assurance ladder and required artifact kinds.
- ADR-018 establishes `specs/formal/assurance-policy.yaml` and
  `tools/check_assurance_policy.py` as the canonical machine-readable policy
  seam.
- `docs/explain/reference/fm-classification-ledger.yaml` is a per-change ADR
  classification ledger. It is related evidence, not the subsystem fulfillment
  map this issue requires.
- `specs/formal/<domain>/` is the formal-domain artifact tree whose classified
  subsystems need delivered-or-waived fulfillment records.

## Architecture Decisions

- Fulfillment is a classified-formal-subsystem concern, not a per-change ADR
  concern. Keep it separate from `fm-classification-ledger.yaml` even if the
  checker reuses similar validation helpers.
- Add one machine-readable fulfillment surface next to
  `assurance-policy.yaml`, preferably `specs/formal/assurance-fulfillment.yaml`
  unless extending `assurance-policy.yaml` keeps the shape clearer. If a sibling
  file is used, it must carry `policy_ref: specs/formal/assurance-policy.yaml`
  and ADR-007 / ADR-018 references.
- Make the "classified subsystem" set explicit and data-driven. The artifact
  should distinguish the subsystem registry (`id`, `path`, `fm_level`) from the
  fulfillment map keyed by subsystem id; the checker can then fail when a
  classified subsystem has no fulfillment entry without hard-coding the current
  list in Python.
- Derive required artifact kinds from `assurance-policy.yaml` by FM level.
  Do not duplicate the FM3 artifact list in the fulfillment schema, tests, or
  docs.
- Treat status as a per-required-artifact-kind value:
  `delivered` requires at least one concrete non-empty repo-relative path, and
  `waived` requires an ISO date plus at least one tracking reference.
- The current issue contract names these classified subsystems: delivered
  `workflows`, `planner`, `assessment`, `objectives`, `experiment-core`;
  waived `participant-runtime`, `participant-semantics`, and `realization`.
  `runtime-contracts` is also a formal domain; do not silently include or omit
  it. Either include it if the chosen classified-subsystem registry treats it as
  classified, or make the registry's boundary explicit.

## Required Incumbents

- Reuse `tools/check_assurance_policy.py`; do not add a second policy CLI or
  nox session.
- Reuse `tools.policy.common.PolicyFailure`, `failures_to_json`,
  `load_exceptions`, `apply_exceptions`, and `safe_repo_path`.
- Extend `implementations/python/tests/test_assurance_policy.py` using the
  existing temp-repo seeding and mutation style.
- Keep `nox -s policy` as the workflow entrypoint through the existing
  `noxfile.py` policy session.
- Keep ADR-007, ADR-018, `docs/specs/formal.md`, and
  `docs/explain/reference/coding-standards.md` as policy consumers; do not
  weaken accepted ADR text in place without the ADR-059 amendment and pin gate.

## Cross-Cutting Layers

- YAML/config parser: use `yaml.safe_load` and explicit mapping/list/string
  shape checks. Never evaluate YAML content or coerce malformed fields into
  empty structures that let checks pass.
- Repo-path security: every path from the fulfillment file must be
  repo-relative, non-escaping, and resolved through `safe_repo_path` or the same
  invariant. Absolute paths, `..`, and symlink escapes must fail.
- Artifact existence: a delivered artifact must point to concrete evidence that
  exists and is non-empty. A domain README can satisfy an artifact kind only
  when the map deliberately names that README for that kind; it must not be a
  blanket substitute for missing executable or model artifacts.
- Waiver authority: fulfillment waivers are first-class records in the
  fulfillment map. `tools/policy/exceptions.yaml` remains only for policy-gate
  exceptions and must not become the FM gap tracker.
- Error envelope: all failures should be `PolicyFailure` instances and respect
  the existing `--json` output. Do not add a new exception hierarchy or raw
  traceback output.
- Workflow gate: the new validation must run through the existing assurance
  policy checker so `nox -s policy` and `verify` fail on invisible gaps.
- Secret and host exposure: this design should not read secrets, environment
  bindings, auth tokens, or network state. Tracking refs are issue identifiers,
  not credentials or live GitHub lookups, and no token should appear in process
  argv, logs, JSON output, or policy failure messages.

## Extension Boundary

The extension seam is the policy YAML plus the classified-subsystem registry:

- adding an FM4 derives its required artifacts from `assurance-policy.yaml`;
- adding an artifact kind requires one policy-level YAML addition and
  fulfillment entries for classified subsystems at levels that inherit it;
- adding a formal subsystem requires one registry entry plus one fulfillment
  map entry, and omission of either side should fail the gate;
- adding more waiver evidence should extend a list of tracking refs or
  evidence refs, not add ad hoc waiver fields.

## Gotchas And Anti-Patterns

Avoid:

- conflating ADR-level classification fulfillment with formal-domain
  subsystem fulfillment;
- hard-coding the current subsystem list or FM3 artifact list in Python when it
  can be derived from YAML;
- using `tools/policy/exceptions.yaml` to hide known FM gaps;
- marking participant-runtime or participant-semantics delivered just because
  a README contains design prose while the issue calls out missing executable
  abstract models;
- accepting empty files, empty directories, absolute paths, parent traversal,
  or paths outside the repo as delivered evidence;
- adding a new nox session, new policy failure type, duplicate YAML parser,
  duplicate waiver schema, or duplicate test harness;
- editing accepted ADR-018 in place for this issue without following ADR-059.

## Non-Goals

- Implementing the fulfillment checker, tests, or YAML contents in this
  preflight note.
- Delivering the missing participant-runtime, participant-semantics, or
  realization formal artifacts.
- Reclassifying FM levels or changing ADR-007's required artifacts.
- Adding API, auth, persistence, logging, schema-generation, or runtime
  behavior.
