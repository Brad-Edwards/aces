# Issue 1125 / GOV-928 Exact-SHA Release Verification Preflight

Date: 2026-08-11

Issue: #1125. Requirement: GOV-928. Related delivery epic: #684.

This note records the architecture and security preflight for making canonical
verification of the exact release commit a hard prerequisite for PyPI
publication. It is a focused remediation of the current Release Please path; it
does not change package dependencies, Python support, version calculation,
release-note ownership, contract semantics, or the release artifact format.

## Binding Contract And Lineage

- GOV-928 requires short-lived, identity-bound package publication and forbids
  long-lived release tokens where the registry supports a stronger mechanism.
  The incumbent `pypi` environment and GitHub OIDC trusted publisher satisfy the
  credential half of that requirement and must remain the only PyPI authority.
- Issue #684 remains the open delivery issue for automatic PyPI publication.
  Its original implementation details are historical: PR #689 replaced the
  proposed semantic-release flow with Release Please, a committed version
  literal, and `.github/workflows/release-please.yml`.
- Issue #537 / PR #543 established the package boundary: release distributions
  must contain the normative contract corpus and must work when installed
  without a source checkout. The existing package integration tests are the
  executable acceptance contract and must not be weakened.
- `.github/workflows/canonical-verification.yml` owns the repository's existing
  hermetic admission graph: `nox -s verify`, pinned Isabelle, and sandboxed
  proof checks. Publication must depend on that graph, not on a smaller
  release-specific subset. Optional and networked CI lanes keep their existing
  development semantics outside this reusable verifier.
- `docs/explain/releasing.md` documents Release Please as the current operator
  contract. Its existing caveat permits an admin merge of a bot-created release
  PR without required checks, so branch protection alone is not sufficient
  release evidence.

## Preflight Finding

The current `publish` job depends only on `release-please`. Canonical CI is a
different workflow triggered by the same push, so the two runs are concurrent
and unordered. A successful Release Please job can therefore publish even when
canonical verification for that commit fails, is cancelled, or has not
finished. The manual recovery path has the same gap.

Polling check runs or branch status cannot close this gap safely. A branch is a
mutable name, status APIs are eventually observed external state, similarly
named checks can come from another workflow, and a new push can change the
commit between lookup and publication. The publication dependency must carry
one immutable commit SHA through resolution, verification, checkout, build,
and smoke testing in one Actions dependency graph.

## Selected Design

### One reusable canonical verifier

Extract the incumbent `verify` job into a repository-owned reusable workflow
invoked with an exact 40-character commit SHA. The workflow must:

1. reject a branch, tag, abbreviated SHA, malformed SHA, or missing commit;
2. check out the supplied SHA with full history and prove that `HEAD` equals it;
3. resolve a valid policy base SHA without changing the verification target;
4. preserve the current Python 3.12 runner, `uv`, Bubblewrap, pinned Isabelle
   cache/acquisition, requirement-UID handling, canonical `nox -s verify`
   invocation, and coverage artifact;
5. expose no publishing permission, environment, OIDC authority, or secret.

The ordinary CI workflow must call this same reusable workflow for
`github.sha`. This makes the called graph, rather than a copied release-only
approximation, canonical. GitHub documents that a local reusable workflow is
loaded from the same commit as its caller, and that caller permissions can only
be maintained or reduced across the call:
<https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows>.

Both protected branches currently require the historical `verify` check
context. A reusable call reports a nested check context, so ordinary CI must
retain a same-run `verify` result-join job that runs with `if: always()` and
fails unless the canonical call result is exactly `success`. This compatibility
join preserves branch protection; it does not perform or substitute for
verification and it cannot convert failed, cancelled, or skipped verification
into a passing required check.

### Resolve once, then carry the exact release SHA

Release Please creates a draft GitHub Release and force-creates its tag so no
public Release or generated source archives precede admission. Add a
non-privileged release-resolution job before verification:

- For an automatic release, consume Release Please's documented `sha` output
  and require the emitted tag to resolve to that same commit.
- For a manual recovery release, resolve the supplied existing GitHub Release
  tag once to its commit SHA.
- In both paths, require a full SHA, a stable `vX.Y.Z` release tag, a real parent
  commit, ancestry from `origin/main`, and a stable Release object identity;
  automatic releases must still be drafts. Emit the immutable release SHA, its
  parent policy base, Release id/draft state, and validated tag as job outputs.

The pinned Release Please action exposes `sha` as “the SHA that a GitHub release
was tagged at”; this output is preferable to assuming that a mutable branch or
the workflow event SHA is the release commit:
<https://github.com/googleapis/release-please-action/blob/45996ed1f6d02564a971a2fa1b5860e934307cf7/README.md>.

The release verification job calls the reusable canonical verifier with the
resolved release SHA. A release-only read-only job then runs the existing
RUN-314 Docker integration at that SHA in required mode, rejecting unavailable
runtime/image state, skips, or zero tests. A read-only build job runs only after
that gate, checks out and builds the SHA rather than a branch or tag, executes
the artifact smokes, and uploads only the tested distributions. The PyPI job
has release resolution, exact verification, required real-container evidence,
and the read-only build as explicit successful prerequisites and downloads that
same-run artifact. Immediately after protected-environment approval and
artifact download, it freshly revalidates the Release id, draft state, exact
tag ref, and fully dereferenced commit SHA before invoking the pinned OIDC
publisher. A separate GitHub publication job runs only after PyPI and repeats
the identity checks before attachment, re-reads the Release object after the
tag-addressed upload, and finalizes by the bound numeric Release id. A lost
successful-finalization response is retryable only when the same Release is
already public, both downloaded assets byte-match the tested distributions,
and the id, tag, and commit SHA still match. No status API, polling,
workflow-name matching, or stale mutable-ref observation is an admissible
publication gate.

### Test the built artifact before granting publication authority

Keep the existing archive-level corpus probes, extend them to the sdist, and
run post-build smoke tests against both actual artifacts in `dist/`:

1. create a fresh virtual environment outside the checkout;
2. install the built wheel and sdist into separate environments;
3. run `raes conformance backend --profile provisioning-only` from outside the
   checkout; and
4. require the installed distribution version to match the release tag and a
   JSON report for the requested profile with `passed: true` and at least one
   executed case.

This is intentionally consistent with
`implementations/python/tests/test_corpus_packaging.py`. The canonical verifier
continues to run that installed-distribution suite; the two release smokes prove
that every specific distribution about to be uploaded satisfies the contract.

## Trust, Provenance, And Permission Boundaries

- The resolution, verification, real-container, and build/smoke jobs receive only
  `contents: read`. They do not receive `id-token: write`, the `pypi`
  environment, or release-write authority. The tested distributions cross into
  the publish job through a same-run immutable Actions artifact.
- The `publish-pypi` job remains the sole holder of `id-token: write` and keeps
  the `pypi` environment. PyPI Trusted Publishing exchanges the workflow
  identity for short-lived credentials and requires this permission; no API
  token or inherited secret is introduced:
  <https://docs.pypi.org/trusted-publishers/using-a-publisher/>.
- Publishing-critical third-party actions remain pinned to full commit SHAs,
  which GitHub identifies as the immutable action reference:
  <https://docs.github.com/en/actions/reference/security/secure-use>.
- This change does not claim to implement GOV-927 or add an SBOM/provenance
  generator. If an SBOM or attestation step is present when this work is
  integrated, it must remain derived from the exact-SHA `dist/` artifacts after
  canonical verification and before upload; it must not move OIDC authority
  into the reusable verifier or create a second publication path.
- A successful canonical verifier is necessary but not sufficient publishing
  authority. The exact Release/tag binding, installed wheel and sdist smokes,
  protected environment, OIDC trusted-publisher identity, artifact attachment,
  and draft finalization all remain conjunctive.
- A protected `v*` tag ruleset that prevents deletion or movement outside the
  approved release authority remains an external repository-administration
  control. The workflow detects identity changes at both irreversible
  boundaries but cannot make already-published PyPI bytes reversible, and it
  intentionally does not grant repository code permission to mutate live
  organization rulesets.

## Alternatives Rejected

- **Rely on release-PR branch protection:** bot-created release PR checks may not
  run, and the documented admin-merge path bypasses them.
- **Poll CI/check-run status:** races mutable refs and external state, duplicates
  check-selection policy, and cannot express a direct same-run dependency.
- **Copy selected CI steps into `publish`:** creates a second verification graph
  that can silently drift and weakens the meaning of “canonical”.
- **Publish from the CI workflow:** broadens the proof job's permissions and
  mixes untrusted-code verification with the OIDC deployment boundary.
- **Use the tag for the publish checkout after verification:** tags are names,
  not the immutable value proved by the dependency. The validated SHA must be
  carried explicitly.

## Verification And Policy Tests

Add YAML-focused tests that parse, rather than execute, the workflow graph and
assert these structural invariants:

- CI and release both invoke the same local canonical verifier, and CI's stable
  required `verify` context fails unless that reusable invocation succeeds;
- the verifier checks out its exact SHA input and fails on any `HEAD` mismatch;
- release resolution binds Release Please's SHA to the tag and main ancestry;
- a release-only job binds real Docker integration to that SHA and rejects an
  unavailable runtime/image, skipped test, or empty collection;
- PyPI and GitHub publication require successful exact-SHA verification; the
  build and attachment jobs check out that SHA, and the no-checkout PyPI job
  freshly queries and dereferences the exact tag immediately before OIDC;
- no release step polls branch/check status;
- wheel and sdist archive checks and installed-artifact conformance smokes all
  precede the SHA-pinned PyPI action;
- only `publish-pypi` has the `pypi` environment and `id-token: write`;
- GitHub attachment is a separate retryable job that revalidates the Release
  and tag, attaches artifacts, revalidates the object after upload, and only
  then removes draft state by numeric Release id. An already-public retry must
  byte-match both attached distributions before it can succeed; and
- proof acquisition, the canonical nox command, coverage upload, trusted
  publishing, and GitHub Release attachment remain present.

Run the focused workflow tests, the installed-wheel packaging tests, lint, the
repository policy checker, requirement governance, and `tools/verify_all.py`.

## Traceability Plan

- Add IMPLEMENTS links from GOV-928 to the release workflow, reusable canonical
  verifier, this preflight, and the release runbook.
- Add TESTS links to the workflow-structure test and the installed-wheel corpus
  acceptance test.
- Link issue #1125 as this repository-owned guarantee and #684 as the broader
  release delivery lineage without rewriting its stale implementation proposal
  as the current architecture.
- Move GOV-928 to ACTIVE only when the workflow, tests, and documentation land
  together and all governance checks pass.
