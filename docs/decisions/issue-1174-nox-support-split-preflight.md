# Issue 1174 Nox Support Split Preflight

Date: 2026-09-03

Issue: #1174. This is a requirement-free maintenance change; the issue is the
authoritative contract.

## Boundary Decision

ADR-014 already records the required boundary and does not need another
amendment. The root `noxfile.py` remains the only public Nox entry point: it
owns global Nox options, session decorators, public session names, and the thin
adaptation from `nox.Session` to private support functions. It is not a general
compatibility facade for tests or other Python callers.

`tools/nox_support/` owns private configuration, command execution and
reporting, policy lanes, test/documentation lanes, and graph composition. Each
constant, helper, and lane implementation has one defining module. Tests import
and patch that owner directly; they must not require duplicate re-exports from
`noxfile.py` or patch a symbol opportunistically across every loaded module.
The package dependency direction remains:

```text
config
  └─ runner
      ├─ policy_lanes
      ├─ test_lanes
      └─ graph → policy_lanes + test_lanes

noxfile → all required private modules
```

No support module imports `noxfile.py`, registers a session, or mutates
`nox.options`. Shared lower-level behavior belongs in the existing `config` or
`runner` module; lane-specific behavior belongs in the existing lane modules;
cross-lane selection and composition belongs in `graph`. A new support layer is
not justified unless behavior cannot fit one of those established roles.

## Canonical Behavior That Must Not Move or Fork

- ADR-014's public session inventory and the `verify`, `verify-completion`,
  changed-file, hook, compatibility, proof, documentation, OSV, and Docker
  semantics remain unchanged. `.ground-control.yaml`, `.pre-commit-config.yaml`,
  `tools/verify_all.py`, contributor documentation, and CI continue to invoke
  only the root `noxfile.py`.
- `SessionReporter` remains the sole stage event and summary mechanism.
  Support functions continue to propagate failures after recording `FAIL`; no
  parallel exception hierarchy or error envelope is introduced.
- `tools.parallel_verification.VerificationLane` and
  `run_verification_lanes()` remain the process-isolation and bounded-worker
  seam. The lane tuple, CPU-derived worker count, per-lane environment, and
  declaration-order result collection must not be reimplemented in the
  registry.
- `runner` remains authoritative for frozen project synchronization, fixed-list
  subprocess construction, changed-path normalization, option-value checks,
  pytest/coverage invocation, gitleaks staging, and the 90% line threshold.
  `policy_lanes` and `test_lanes` compose those primitives rather than growing
  competing validators or subprocess wrappers.
- Coverage.py remains authoritative for measured Python scope. Its repository
  source root, branch measurement, unit/integration combination, and narrow
  cache/docs/venv/test omissions stay intact. Neither Coverage.py nor Sonar may
  gain a blanket `tools/nox_support/**` exclusion. Sonar continues to analyze
  `tools/`; the final scanner configuration must also demonstrably include the
  root `noxfile.py`, because ADR-014's reference to both surfaces includes the
  registry as well as its private support package.
- Ruff continues to check both `tools` and `noxfile.py`. Focused tests retain
  exact public-session inventory, one-definition ownership, acyclic imports,
  lane inventory/environment/worker assertions, coverage configuration, and
  reporter/failure behavior, but exercise private behavior through its defining
  module.

## Cross-Cutting and Security Guardrails

This refactor crosses development-tooling boundaries, not the product's auth,
domain-schema, DTO, service, repository, or persistence layers. No product
contract or published schema changes.

The input gates it does cross must remain fail closed:

- Nox session arguments continue through `_required_option_value`,
  `_split_policy_session_args`, `_hygiene_flags`, and `_normalize_paths` before
  reaching git or file operations. Do not add a second parser or bypass
  repo-relative file filtering.
- Requirement identity continues through `RAES_REQUIREMENT_UID`, the branch UID
  check, and the existing repository/requirement policy tools. This
  requirement-free issue must not fabricate a requirement mapping.
- Coverage lane paths continue through `RAES_VERIFY_COVERAGE_FILE`; missing
  orchestrator input fails before a lane runs. Coverage files remain in bounded
  temporary directories and are combined before XML/JSON/report generation.
- Child commands remain argv lists with explicit working directories, frozen
  dependency selection, bounded workers, and the established per-lane
  environment map. Do not introduce shell interpolation. Git revisions and
  repo paths may appear in process argv; credentials, tokens, or secret values
  must not. Existing inherited environment behavior must not be broadened or
  logged.
- Secret scanning continues to use private-key detection plus checksum-verified
  gitleaks with `--redact`. Refactoring must not print environment mappings,
  subprocess secrets, or unredacted scanner output.
- User-visible diagnostics remain Nox failures plus `SessionReporter` events.
  Preserve exception causes at parsing/report-reading boundaries and avoid
  converting failures into skips or success.

The natural extension seam is data, not another registry: a future lane is
registered once at the root, implemented in its owning support module, and
added to graph composition through a `VerificationLane` entry and its existing
`posargs`/`env` fields. CPU budget and coverage destination stay parameters;
session names and command lists must not be duplicated in CI or hooks.

## Gotchas and Anti-Patterns

- Do not preserve a private-helper facade in `noxfile.py` solely for tests.
- Do not use wildcard imports, import support modules back through the root, or
  rely on import order to patch globals.
- Do not confuse a public Nox session wrapper with a second implementation of
  its lane. Registration stays public; behavior has one private owner.
- Do not weaken the graph while moving code: especially policy inclusion,
  integration coverage, proof replay, docs-local, deterministic coverage
  combination, changed-file fail-closed fallback, or final summaries.
- Do not solve coverage pressure with `omit`, `sonar.coverage.exclusions`, CPD
  package exclusions, pragmas, or tests that merely import lines without
  asserting behavior.
- Do not broaden `sonar.sources` without preserving the source/test distinction
  and generated-artifact exclusions, and do not claim `noxfile.py` is analyzed
  unless the scanner configuration actually includes it.
- Do not create a second lane schema, reporter, subprocess abstraction,
  validation path, exception taxonomy, workflow file, or persistent registry.

## Non-Goals

- No session additions, removals, renames, or command-semantic changes.
- No dependency, Python-version, coverage-threshold, marker, or worker-policy
  changes.
- No changes to product runtime behavior, APIs, schemas, authentication,
  storage, or observability.
- No redesign of `tools.parallel_verification`, policy tooling, CI topology,
  pre-commit hooks, or Ground Control commands.
- No exemptions to make relocated tooling invisible to quality gates.
