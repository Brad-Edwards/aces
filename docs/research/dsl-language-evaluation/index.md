# ACES SDL Language Evaluation

This directory is the evidence gate for issue #346 and requirement ASR-530.
It does **not** claim that ACES is already an experimentally adequate language.
It preregisters how that claim can be tested and pins a sanitized, not-started
execution snapshot so architecture, parsing, or schema completeness cannot be
mistaken for study evidence.

The protocol follows the concern raised by Gabriel, Goulão, and Amaral that a
domain-specific language is not validated merely by using domain concepts:
expressiveness, usability, effectiveness, maintainability, and domain-expert
productivity require explicit evaluation. Mernik, Heering, and Sloane provide
the DSL-development boundary; Kosar, Bohra, and Mernik provide the systematic
mapping context; VSDL supplies a cyber-range-language comparison point with
constraint/solver semantics. Exact source identities are frozen in the
protocol.

## Bundle

- [`bundle-manifest.json`](bundle-manifest.json) selects the exact active
  artifacts without making a mutable branch name part of evidence identity.
- [`protocol-v1.json`](protocol-v1.json) freezes constructs, personas, tasks,
  variants, artifact stages, tooling conditions, measures, thresholds,
  sampling, missing-data rules, stopping rules, privacy boundaries, and
  validity threats before observations exist.
- [`execution-snapshot-v1.json`](execution-snapshot-v1.json) pins ACES commit
  `38ba081714b12a4dcc7a5c527e2f1250d80a4d1b` and the public documentation and
  production entrypoints under evaluation. Its status is `not_started`, its
  ethics state is `pending`, and it contains no subjects or observations.
- [`analysis-v1.json`](analysis-v1.json) names the ADR-021 claim, allowed and
  disallowed evidence, objective pass/fail criteria, and recomputable measure
  slots. Its evidence status is `untested`.

Protocol, snapshot, and analysis are independently revisioned. An executed
study creates a new immutable snapshot and analysis. It does not edit the
not-started record or silently change protocol thresholds. A changed construct,
rubric, threshold, sampling rule, task meaning, or exclusion rule creates a new
protocol revision and amendment entry.

## What is evaluated

The protocol keeps eight dimensions separate:

1. expressiveness;
2. usability and comprehension;
3. effectiveness and productivity;
4. maintainability and evolution;
5. ambiguity;
6. diagnostic quality;
7. reviewability; and
8. semantic traceability.

It includes all six issue personas and representative positive, negative,
underspecified, ambiguous, round-trip, non-equivalent mutation, maintenance,
diagnostic-repair, and blinded independent-review tasks. Each relation-bearing
task declares the artifact stage on which equivalence, non-equivalence,
invalidity, profile dependence, or loss is expected. Canonical digest equality
is used only for identity under the named canonicalization profile; it is not
treated as proof of behavioral or scientific equivalence.

Human study subjects are not SDL participants. Actual recruitment and data
collection require applicable ethics, consent, privacy, and data-protection
review. Only minimized pseudonymous observations or aggregates may be
committed. Names, addresses, recordings, raw chats/prompts, keystroke streams,
free-form biographies, credentials, private backend output, and pseudonym
linkage keys are prohibited from the repository bundle.

## Execution and reproduction

Before execution:

1. obtain and record the applicable ethics/privacy approval;
2. freeze task materials, sealed intended semantics, reviewer rubrics, balanced
   task order, recruitment deadline, and pseudonym handling outside the public
   reviewer packet;
3. verify the ACES revision and every public surface named by the snapshot;
4. assign tooling and assistance conditions without environment-selected
   semantics; and
5. run the integrity gate.

During execution, preserve missing, abandoned, tool-failed, and withdrawn
attempts according to the preregistered denominator rules. Every active subject
must receive the two structured workload groups in the execution plan: at least
one constructive or underspecified task and at least one challenge or independent
review task appropriate to that subject's persona. Every measure declares its
applicable task, variant, and artifact stages. Each non-withdrawn attempt must
contain exactly one observation for every resulting attempt-measure-stage
opportunity; measures are aggregated only after that stage coverage is closed.
Missing, abandoned, and tool-failed opportunities remain explicit rows;
withdrawn opportunities are derived from the matching withdrawal and attempt
records and are excluded from the denominator. Fix each independent review
judgment before revealing intended semantics. Adjudication adds a new record and
never replaces the original disagreement. Diagnostics are captured exactly as
the selected public entrypoint emits them; missing structure is a finding, not
permission to inspect source or rewrite the response.

Run the focused integrity gate with:

```bash
implementations/python/.venv/bin/python tools/check_dsl_language_evaluation.py
```

The checker validates bounded duplicate-safe JSON, closed shapes, stable IDs,
catalog and cross-artifact joins, source pins, repository path containment,
secret-safe locators, the closed subject-attempt-observation-review graph,
per-subject workload assignment, the protocol-derived task-variant-stage
opportunity matrix, recomputed measure results with outcome counts, complete
execution coverage, preserved disagreements, and ADR-021 evidence-status
promotion. It performs no network access, backend deployment, shell evaluation,
or private-data lookup. The same check runs once in the canonical nox contracts
graph.

## Interpretation boundary

`demonstrated` is permitted only for the exact preregistered population, tasks,
conditions, ACES revision, and public surfaces after every dimension passes and
coverage is complete. `partial` preserves incomplete but relevant evidence.
Any objective fail criterion yields `refuted`; absent execution remains
`untested`.

Failed observations are evidence. Product fixes belong to separately scoped
issues and owning SDL/specification/test surfaces. A later correction may be
evaluated in a new snapshot, but it must not overwrite the frozen falsifying
record.
