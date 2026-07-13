# Reproducible Related-Work Comparison

Issue: #728. Requirement: ASR-534.

This directory is the reproduction bundle for the reader-facing
[Related-Work Comparison](../../explain/sdl/related-work-comparison.md). It
replaces the earlier prose-only `yes`/`partial`/`no` table with a preregistered
protocol, a frozen extraction snapshot, and recomputable analysis.

The result is deliberately bounded. It supports no universal winner or
`highest quality` claim. Within the scenario-authoring stratum, different
predeclared weighting profiles place ACES, VSDL, or OCR SDL first. Systems with
different purposes remain in separate scope strata.

## Bundle Contents

- [`protocol-v1.json`](protocol-v1.json) freezes inclusion and exclusion rules,
  system identities, scope strata, the twelve required axes and rubrics, three
  representative authoring tasks, two negative cases, and analysis rules.
- [`extraction-snapshot-2026-07-13.json`](extraction-snapshot-2026-07-13.json)
  records pinned primary sources, all 96 system-axis observations, and all 40
  system-case walkthroughs. Every observation includes an exact locator,
  rationale, confidence, limitations, and review state.
- [`analysis-v1.json`](analysis-v1.json) records scope-qualified Pareto
  frontiers, four weight profiles, recomputed totals, the observed ranking
  reversals, and the claims permitted on the public page. Every claim carries
  ADR-021 evidence status, threats to validity, falsification criteria, named
  evidence artifacts, and a structured derivation from recomputed cells.
- [`search-log.md`](search-log.md) records source acquisition, revision and
  digest choices, corpus boundaries, and the extraction method.

:::{toctree}
:hidden:

search-log
:::

## Reproduce

Run the focused offline gate and its mutation tests from the repository root:

```bash
implementations/python/.venv/bin/python tools/check_related_work_comparison.py
implementations/python/.venv/bin/python -m pytest \
  implementations/python/tests/test_related_work_comparison.py
```

The checker performs no network access and executes no compared project. It
validates bounded closed JSON shapes, source pins, safe locators, primary-source
coverage, rectangular matrices, ACES executable evidence, task and negative-case
coverage, Pareto and sensitivity recomputation, and reader-page parity.
It also rejects a public claim whose evidence status, falsification record,
declared scope, derivation, or canonical statement drifts from the frozen
observations and weight-profile results.

## Extraction And Review Status

The 2026-07-13 snapshot uses two evidence methods:

- repository execution for existing ACES production and negative-test
  boundaries where the cited repository paths already exercise the case;
- source walkthroughs for external systems, using pinned standards,
  publications, official documentation, and source revisions.

The external cases are not executions of third-party code and are not a user
study. The snapshot has one extraction pass and awaits independent replication
or adjudication, so every public claim retains ADR-021 status `partial`.
Usability therefore remains limited to documentation and walkthrough evidence;
repository activity is not treated as independent adoption.

## Authority Boundary

These artifacts are non-normative research synthesis. They report observed
evidence about ACES and precedents but do not define SDL meaning, validity,
runtime behavior, or external-system capability. ACES semantics remain in
`specs/`, published contracts, accepted ADRs, and implementation tests. A source
refresh creates a new extraction snapshot; a rubric change creates a new
protocol revision.
