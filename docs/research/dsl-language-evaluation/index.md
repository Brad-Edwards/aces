# ACES SDL Language Evaluation

This directory is the shared evidence gate for issues #346 and #178 under
requirement ASR-530. It does **not** claim that ACES is already an
experimentally adequate language or accessible to non-infrastructure-expert
researchers. It preregisters how those distinct claims can be tested and pins
sanitized, not-started execution snapshots so architecture, parsing, schema
completeness, or the protocol itself cannot be mistaken for study evidence.

The protocol follows the concern raised by Gabriel, Goulão, and Amaral that a
domain-specific language is not validated merely by using domain concepts:
expressiveness, usability, effectiveness, maintainability, and domain-expert
productivity require explicit evaluation. Mernik, Heering, and Sloane provide
the DSL-development boundary; Kosar, Bohra, and Mernik provide the systematic
mapping context; VSDL supplies a cyber-range-language comparison point with
constraint/solver semantics. Exact source identities are frozen in the
protocol.

## Bundle

- [`bundle-manifest.json`](bundle-manifest.json) selects the exact primary and
  supplemental claim bundles without making a mutable branch name part of
  evidence identity. It also binds each stable claim id to its exact required
  scope and preregistered gating/comparison strata. Every selected bundle is
  checked; adding a claim cannot stop the frozen issue-346 record from being
  validated.
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
- [`protocol-v2.json`](protocol-v2.json) adds the issue-178
  `security-researcher` persona, adapter-specific docs/MCP/CLI/direct-library
  conditions, representative authoring/review tasks, and focused invalid and
  unsupported-boundary tasks without editing the frozen revision-1 protocol.
- [`execution-snapshot-accessibility-v1.json`](execution-snapshot-accessibility-v1.json)
  pins the public authoring docs, AUT-811 guidance, intended-use discovery,
  examples, CLI, MCP, language-service, and documented library surfaces. It is
  `not_started` and contains no study records.
- [`analysis-accessibility-v1.json`](analysis-accessibility-v1.json) selects
  only the issue-178 personas, tasks, conditions, variants, stages, dimensions,
  and measures. Its evidence status is `untested`.

Protocol, snapshot, and analysis are independently revisioned. An executed
study creates a new immutable snapshot and analysis. It does not edit the
not-started record or silently change protocol thresholds. A changed construct,
rubric, threshold, sampling rule, task meaning, or exclusion rule creates a new
protocol revision and amendment entry.

Each analysis repeats a closed scope of stable protocol identifiers, but it
cannot choose or narrow that scope: the checker requires an exact match with
the versioned manifest binding for the claim id. Frozen observations outside a
bound scope remain valid inputs for another claim but are excluded from its
recomputation, completion decision, and ADR-021 evidence status. A legitimately
narrower scope requires a distinct claim identity and statement. This prevents
accessibility results from silently promoting or refuting language adequacy,
and prevents a publisher from discarding unfavorable dimensions or populations.

## Researcher accessibility claim

Issue #178 separates four personas: `security-researcher`,
`benchmark-designer`, `backend-implementer`, and `evaluator-reviewer`. Backend
implementers are a comparison and boundary-testing population; their results
cannot substitute for non-infrastructure-expert researcher results. Relevant
SDL, benchmark, cloud/container, and programming experience is recorded only as
bounded bands. The manifest partitions target infrastructure novices by persona
and tooling condition as claim-gating strata. Infrastructure-familiar and prior
ACES users, plus backend implementers partitioned by experience and condition,
are persisted as comparison strata and cannot promote or refute the claim.

The protocol keeps `public-docs-only`, MCP, CLI, and documented-library
conditions separate. Every attempt pins the exact adapter, mode, source or
migration profile, intended-use profile, parameters, assistance policy, and
ACES revision. Positive tasks require a non-trivial benchmark scenario and
independent review. Negative tasks distinguish invalid, unsupported, and
profile-dependent outcomes and preserve the exact public diagnostic rather
than enriching it from source.

Success requires representative authoring and validation without cloud,
Terraform, OpenStack, Docker, backend source, or undocumented backend
conventions; diagnostics that locate defects and support correction; public
examples/templates that support the sealed non-trivial meaning; clear teaching
of unsupported boundaries; and blinded review that recovers critical meaning.
Requests for prohibited assistance, setup failures, wrong turns, missing public
guidance, weak diagnostics, abandoned attempts, and failed tasks remain
evidence. Product corrections belong to separate issues and later snapshots.

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

The checker validates every manifest-selected bundle: bounded duplicate-safe
JSON, closed shapes, stable IDs, claim-scope joins, source pins, repository path
containment, secret-safe locators, the closed
subject-attempt-observation-review graph, scoped workload assignment, the
protocol-derived task-variant-stage opportunity matrix, exact manifest claim
bindings, independently persisted persona/experience/condition stratum
recomputation, complete execution coverage, preserved disagreements, and
gating-stratum-only ADR-021 evidence-status promotion. It performs no network
access, backend deployment, shell evaluation, or private-data lookup. The same
check runs once in the canonical nox contracts graph.

## Interpretation boundary

`demonstrated` is permitted only for the manifest-bound population, tasks,
conditions, variants, stages, measures, ACES revision, and public surfaces
after every dimension in every preregistered gating stratum passes and coverage
is complete. Pooled success and comparison-population success cannot mask a
target persona, experience band, or condition failure. `partial` preserves
incomplete but relevant evidence. Any gating-stratum objective fail criterion
yields `refuted`; absent execution remains `untested`.

Failed observations are evidence. Product fixes belong to separately scoped
issues and owning SDL/specification/test surfaces. A later correction may be
evaluated in a new snapshot, but it must not overwrite the frozen falsifying
record.
