# Scoring/Reward Surface Inventory

This note is the falsifiable evidence base for the scoring-scope examination
(issue #671). It records, per surface, where the surface is defined, how it is
validated, where it is used, and how it fares under the in-horizon
discriminator. It is research evidence, not contract authority.

## The discriminator

Issue #671 proposes a single test for whether a signal belongs in the authored
ACES **experiment** rather than in downstream **data use**:

> A signal is in scope only if it is **used within the experiment by the
> participants** — a signal a participant reads and acts on during the run,
> within its horizon.

This is the same experiment-vs-data-use boundary already drawn by the
experiment-core decisions (ADR-055, ADR-064, ADR-065, ADR-068) and applied to a
concrete replication target by ADR-069. Scoring, reward, measures, and
evaluation are consumers of a run's output; they are not, by themselves, signals
a participant perceives and acts on inside the horizon.

## The coupled OCR scoring pipeline

The five surfaces under examination are not independent. They form one coupled
Open-Cyber-Range (OCR) inheritance chain, preserved verbatim by ADR-002:

```
conditions -> metrics -> evaluations -> TLOs -> goals
```

`agents.reward_calculator` is a separate CybORG inheritance, not part of that
chain.

### 1. `metrics`

- **Schema**: `contracts/schemas/sdl/sdl-authoring-input-v1.json`
  (`$defs.Metric`, `$defs.MetricType` = `manual` | `conditional`,
  `$defs.MinScore`), mirrored in `instantiated-scenario-v1.json`.
- **Model**: `implementations/python/packages/aces_sdl/scoring.py` (`Metric`),
  container `aces_sdl/scenario.py`. Cross-field validator forbids `condition`
  on manual metrics and requires it on conditional metrics.
- **Meaning**: a scored quantity — `max_score`, plus either a human-graded
  `artifact` (manual) or a `condition` reference (conditional). A metric is a
  *graded value assigned to a run*, not a state a participant reads.

### 2. `evaluations`

- **Schema**: `$defs.Evaluation` in `sdl-authoring-input-v1.json`
  (`metrics` list, `min_score`).
- **Model**: `aces_sdl/scoring.py` (`Evaluation`, `MinScore` with exclusive
  `absolute` / `percentage`).
- **Meaning**: a pass/fail threshold over a group of metrics. This is a
  grading rule applied to accumulated scores.

### 3. `tlos`

- **Schema**: `$defs.TLO` in `sdl-authoring-input-v1.json`
  (`evaluation` reference, required).
- **Model**: `aces_sdl/scoring.py` (`TLO`); docstring defines TLO as
  "Training Learning Objective." (Note: the term is *training* learning
  objective, an exercise-grading construct, not "terminal" learning objective.)
- **Meaning**: a training-exercise learning objective linked to one
  evaluation. Pure exercise-scoring vocabulary.

### 4. `goals`

- **Schema**: `$defs.Goal` in `sdl-authoring-input-v1.json` (`tlos` list).
- **Model**: `aces_sdl/scoring.py` (`Goal`).
- **Meaning**: a high-level exercise goal composed of TLOs. The top of the
  grading tree.

### 5. `agents.reward_calculator`

- **Schema**: `$defs.Agent.reward_calculator` — a plain string with default
  `""`, no `$ref`.
- **Model**: `aces_sdl/agents.py` (`Agent.reward_calculator: str = ""`). This
  is the **only** occurrence, and there is **no cross-reference validator** for
  it anywhere under `aces_sdl/validator/` — unlike every other surface in this
  inventory, it is an unresolved free-text label.
- **Meaning**: names a CybORG reward-calculator class
  (e.g. `HybridImpactPwn`, `SupplyChainImpact`). It selects training/scoring
  machinery that runs *outside* the participant's perception, and it binds to
  nothing inside ACES. ADR-020 already deferred "verifier/reward assets" to
  future work and only recorded the field as an inherited label, not a modeled
  concept.

### The bridge: `objectives.success`

`objectives` is an in-horizon surface (ADR-002), but its success model
(`$defs.ObjectiveSuccess`, `aces_sdl/objectives.py`) currently lets an objective
succeed on **either** observable state (`conditions`) **or** the score-shaped
surfaces (`metrics` / `evaluations` / `tlos` / `goals`). This is the seam where
the scoring pipeline reaches into the participant-facing surface. The validator
requires at least one referenced condition/metric/evaluation/TLO/goal, so today
a scenario can express objective success purely in grading terms.

### In-horizon contrast: `conditions`

- **Schema**: `$defs.Condition` in `sdl-authoring-input-v1.json` (command +
  interval form, or `source` form).
- **Model**: `aces_sdl/conditions.py` (`Condition`).
- **Meaning**: an observable state fact about the run ("web-alive",
  "OTService available"). This is exactly the class of signal the discriminator
  keeps in scope: it describes the state of the environment that participants
  and objectives can reference within the horizon.

## Usage across the corpus

Usage is narrow and concentrated in "study-style" scenarios:

| Scenario | metrics/eval/tlos/goals | reward_calculator |
|---|---|---|
| `examples/scenarios/enterprise-participant-evidence-loop.sdl.yaml` | yes | no |
| `examples/scenarios/satcom-release-poisoning.sdl.yaml` | yes | yes |
| `examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml` | yes | yes |
| `examples/scenarios/port-authority-surge-response.sdl.yaml` | yes | yes |
| `examples/scenarios/techvault*.sdl.yaml` (all six) | none | none |
| `examples/library/patterns/study-scoring-chain.yaml` | yes (pattern) | no |
| `examples/library/templates/study/scored-study-protocol.yaml` | yes (template) | no |

The six `techvault-*` runtime-parity scenarios use none of these surfaces. The
`paper-agent-loop` scenario named in issue #671 does not exist in the tree yet
(it is referenced only in preflight notes for other issues). Governing
requirement for the assessment pipeline is **SEM-206 "Assessment Semantics."**

## Where scoring/evaluation already lives (the experiment plane)

The experiment-core contract family already owns the concepts the SDL pipeline
duplicates:

- `contracts/schemas/experiment-core/experiment-study-v1.json` carries an
  analysis plan with its own `metrics` / `primary_metric` (statistical
  experiment metrics, distinct from SDL grading).
- `contracts/schemas/experiment-core/experiment-derived-measure-v1.json`
  (ADR-064) is "a derived measure or evaluation output" bound to source
  evidence records.
- `contracts/schemas/experiment-core/experiment-evidence-record-v1.json`
  (ADR-064) is raw captured evidence.
- The compiled runtime evaluation contract
  (`implementations/python/packages/aces_contracts/evaluation.py`) is the
  processor/backend evaluation result surface.
- ADR-069 §3 makes the backend **Evaluator** the component that "projects
  reward, objective, terminal-condition, and scoring facts into ACES evaluation
  results, evidence records, and derived measures."

So a scenario that needs a graded score already has a home for it — outside the
SDL, in the experiment/evaluator plane, where the score is treated as an output
of the run rather than an authored environment fact.

## Discriminator verdict per surface

| Surface | Read by a participant in-horizon? | Verdict |
|---|---|---|
| `conditions` | yes — observable state | in scope (keep) |
| `objectives` | yes — participant intent | in scope (keep); narrow success to observable state |
| `metrics` | no — graded value over a run | data-use; vestigial in SDL |
| `evaluations` | no — pass/fail grading rule | data-use; vestigial in SDL |
| `tlos` | no — exercise grading construct | data-use; vestigial in SDL |
| `goals` | no — exercise grading tree | data-use; vestigial in SDL |
| `agents.reward_calculator` | no — training machinery, unbound label | data-use; vestigial in SDL |

Every score-shaped surface fails the discriminator; every observable-state
surface passes it. This is the evidence the proposed ADR (ADR-073) reasons
over.
