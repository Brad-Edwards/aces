# ADR-103: Branch-Aware Python Coverage Policy

## Status

accepted

## Date

2026-08-13

## Classification

Classification: FM0
Required artifacts: repository configuration and focused policy tests
Waivers: none

## Context

ADR-014 makes nox the canonical verification graph and already places Python
coverage collection in that graph. The coverage configuration measures
statements only, omits some repository-owned Python entry points, and accepts a
50% aggregate floor even though the integrated repository is close to 90% line
coverage. Branch outcomes are therefore invisible and the threshold does not
represent the repository's quality policy.

Coverage is useful as a regression guard and review signal, but it is not a
proof of behavioral correctness. Requiring 100% aggregate or changed-code
coverage creates incentives to execute lines without asserting behavior,
over-mock difficult boundaries, distort defensive code, or add exclusions that
serve the metric rather than the design.

ADR-015 also defines the trust model for repository-authored policy: gates
prevent accidental regressions, while review protects the mutable gate itself.
An in-repository coverage checker cannot provide an adversarial security
boundary because the checker, its configuration, tests, and invocation can all
change in the same pull request.

## Decision

1. Coverage.py remains the authority for Python statement, exclusion, and
   branch semantics. The repository does not maintain a second Python semantic
   analyzer for coverage.
2. Canonical unit and integration coverage is combined before reporting.
   Coverage collection includes shipped packages, repository tooling,
   `noxfile.py`, and the Hatch build hook. Tests, documentation, generated
   environments, and acquired caches remain outside the production denominator.
3. Canonical verification enforces a fixed 90% aggregate **line-coverage**
   floor. The floor is an explicit quality threshold, not a manually advanced
   ratchet. Falling below it fails verification; exceeding it does not require a
   metadata update.
4. Canonical verification measures branch coverage and publishes it in XML and
   JSON reports. This ADR establishes no aggregate or changed-branch threshold;
   branch results remain visible for review until repository evidence justifies
   a separate threshold.
5. The repository does not impose blanket 100% changed-line or changed-branch
   coverage. Reviewers apply the proportionate FM0-FM3 assurance policy from
   ADR-007 and ADR-018 when a change needs stronger evidence than the aggregate
   floor.
6. Coverage configuration and report handling use ordinary fail-closed input
   checks for malformed or missing data. They do not attempt to resist a pull
   request author who can edit the gate itself; that would require a separately
   accepted immutable-CI trust boundary.
7. Coverage.py XML remains the SonarCloud input. JSON is published alongside it
   so the line-only threshold and branch totals are inspectable without
   reinterpreting Python source.

## Alternatives Considered

### A manually maintained aggregate ratchet

Rejected. A floor that can only be raised still permits all gains above a stale
recorded value to be lost. It depends on recurring manual updates while
presenting itself as automatic regression protection.

### 100% coverage for changed code

Rejected. Diff boundaries are a poor proxy for behavioral risk, particularly
for small changes, defensive paths, multiline statements, and branch exits.
Enforcing the rule also requires semantic diff machinery disproportionate to
the repository's accidental-regression trust model.

### Exact base-versus-head aggregate comparison

Not adopted. Running the complete unit and integration suite at both revisions
would provide an automatic debt comparison, but it would approximately double
the coverage portion of canonical verification. The fixed floor and branch
visibility provide the intended guardrail at materially lower cost.

### SonarCloud as the only coverage gate

Rejected. SonarCloud provides useful new-code line and condition metrics, but it
is an external service and is unavailable to some pull-request contexts. The
canonical local graph must retain its repository-owned aggregate floor.

## Consequences

- Coverage reports include branch information and all agreed repository-owned
  Python surfaces.
- The coverage policy is understandable from standard Coverage.py behavior and
  a small line-total check rather than a custom semantic analyzer.
- The 90% floor remains stable and meaningful without maintenance commits.
- Branch coverage may regress without independently failing while no branch
  threshold is adopted; the reports and SonarCloud make that movement visible.
- Changes that intentionally alter measured scope must update this ADR or be
  justified by a later superseding decision.
