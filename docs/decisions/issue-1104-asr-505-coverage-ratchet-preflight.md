# Issue 1104 Coverage Ratchet Preflight

Date: 2026-08-11

Issue: #1104. Requirement: ASR-505.

## Decision

Canonical verification measures branch as well as statement coverage. Every
executable production or repository-tooling line added or modified relative to
the exact verified base revision must execute, and every branch whose source is
added or modified must take all of its exits. A changed measured Python file
that is absent from coverage data is a failure rather than an implicit skip.

The changed-code rule is 100%. The legacy aggregate is not: current OpenRAE has
thousands of uncovered statements and no historical branch data. The repository
therefore records an honest whole-tree baseline and enforces it as a monotonic
ratchet. Raising that baseline is welcome; lowering it or adding exclusions to
hide difficult code is not. A later issue may set 100% aggregate only after the
measured corpus actually reaches it.

When the ratchet already exists at the exact base revision, the gate also reads
that historical file and rejects any lower line or branch floor. Editing the
checked-in threshold downward therefore fails in the same job that evaluates
the coverage report.

The initial canonical full unit-plus-integration inventory on CPython 3.12.3
and Linux x86_64 contains 82,536 executable statements and 25,836 branches. It
covers 74,067 statements (89.739023%) and 19,542 branches (75.638644%); the
checked-in floors round down to 89.739% and 75.638%. Subsequent updates may only
raise them.

Measured scope includes the twelve shipped package roots, repository-owned
`tools`, `noxfile.py`, and the Hatch build hook. Tests, generated environments,
and external dependencies are not production denominator padding. Existing
explicit exclusions retain their separately documented integration rationale.

## Diff And Branch Semantics

The gate consumes Coverage.py JSON produced from the combined unit and
integration data and a Git commit accepted by `git merge-base --is-ancestor`.
It parses zero-context added-line ranges from that exact base through `HEAD`.
Comments and other non-executable changed lines are ignored. An executable
changed line is covered only when Coverage.py reports it executed. When a
changed executable line is a branch source, no missing destination from that
source is allowed.

Files outside the measured OpenRAE source/tool roots do not enter the changed
coverage gate. New and renamed files use their destination path; a rename is
checked conservatively as a new destination file. Deleted files have no
remaining executable obligation.

## Verification

Unit tests cover diff ranges, new and renamed files, path normalization,
comments, missing source records, missing lines, missing branches, branch-data
absence, and invalid base revisions. Canonical verification must publish XML and
JSON, enforce the aggregate ratchet, and run the changed-code gate with the same
base SHA used by repository policy.
