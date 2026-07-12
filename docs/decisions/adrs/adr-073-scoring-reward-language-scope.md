# ADR-073: Scoring and Reward Language Scope in the SDL

## Status

accepted

## Date

2026-07-05

## Classification

Classification: FM2
Required artifacts: ADR, prior-art/design-criteria note, scoring-surface
inventory, changelog fragment
Waivers: No schema, fixture, contract-source, implementation, runtime behavior,
or conformance-runner artifact is introduced by issue #671. This ADR is a
proposed boundary decision. The schema deprecation/removal, reference-model
changes, scenario migration, documentation edits, and the amendment to ADR-002's
objective-success clause are downstream implementation work spawned on
acceptance.

## Context

Issue #671 asks whether ACES should carry **scoring / grading language** at all:
the Open-Cyber-Range (OCR) scoring pipeline
(`conditions -> metrics -> evaluations -> TLOs -> goals`) and the
CybORG-inherited `agents.reward_calculator` field. The issue frames this as an
open design question, not a decision, and asks for an ADR. It explicitly does
not decide the answer.

### The inherited surfaces and how they entered

[ADR-001](adr-001-scenario-description-language.md) grounded the SDL in the OCR
SDL. [ADR-002](adr-002-declarative-sdl-objectives.md) then recorded that "the
repository preserved OCR's scoring pipeline
(`conditions -> metrics -> evaluations -> TLOs -> goals`) in the SDL" and added
a first-class `objectives` section whose `success` criteria may reference
declared `conditions`, `metrics`, `evaluations`, `tlos`, or `goals`. CybORG's
`agents.reward_calculator` was carried in as a label;
[ADR-020](adr-020-declarative-participant-framing-boundaries.md) recorded it only
as an inherited "reward-calculator label" and deferred "verifier/reward assets"
to future work. None of these surfaces were re-examined against a later,
deliberate experiment boundary because that boundary did not exist yet.

### The discriminator

Issue #671 proposes a single test: a signal is in scope for the authored ACES
experiment only if it is **used within the experiment by the participants** — a
signal a participant reads and acts on during the run, within its horizon. ACES
"specifies the experiment ... it does not specify what a researcher does with
the output of a run." RL reward-for-training, leaderboard ranking, and
downstream statistical analysis are consumers of a run's data, not part of the
experiment.

This is not a new boundary. It is the experiment-vs-data-use boundary the
project has already drawn three times:

- [ADR-055](adr-055-experiment-core-contract-boundary.md) put tasks, runs,
  studies, and metric definitions in the experiment-core contract family, not
  the SDL, and its guardrails state: "Do not treat SDL `objectives` as EXP-701
  task records; they remain scenario-local objective declarations."
- [ADR-064](adr-064-experiment-evidence-and-measure-contract-boundary.md)
  published `experiment-evidence-record-v1` (raw evidence) and
  `experiment-derived-measure-v1` ("a derived measure or evaluation output").
- [ADR-069](adr-069-cage-2-replication-architecture.md) §3 makes the backend
  **Evaluator** the component that "projects reward, objective,
  terminal-condition, and scoring facts into ACES evaluation results, evidence
  records, and derived measures," and §1 treats native reward arrays and
  leaderboard scores as *source facts* portable only when bound to existing ACES
  evidence/measure concepts. §7 rejects defining "equivalence as one score."

### What the surfaces actually are

The five surfaces form one coupled OCR grading chain plus one CybORG label. The
concrete map — schema locations, models, validators, and per-surface usage — is
recorded in the research note
[`scoring-surface-inventory`](../../research/scoring-scope/scoring-surface-inventory.md);
the literature grounding (reward hypothesis, specification gaming,
experiment-database separation) is in
[`prior-art-and-design-criteria`](../../research/scoring-scope/prior-art-and-design-criteria.md).
The load-bearing findings:

- `metrics`, `evaluations`, `tlos`, `goals` are graded values, thresholds, and
  training-exercise objective/goal trees. They are read by a grader, not by a
  participant in-horizon. (`tlos` is literally "Training Learning Objective" in
  the model.)
- `agents.reward_calculator` is a bare free-text string with **no
  cross-reference validator** anywhere in `aces_sdl/validator/`. It names a
  CybORG reward class that runs outside participant perception and binds to
  nothing in ACES. It is the weakest surface in the language.
- Typed propositions/assertions are observable state claims and `objectives`
  are participant intent. Executable `conditions` are probe realizations, not
  state facts (ADR-079).
- The one leak between the two sides is `objectives.success`, which today can be
  satisfied by the scoring pipeline instead of by observable state.

Usage is narrow: only four "study-style" example scenarios use the pipeline
(`enterprise-participant-evidence-loop`, `satcom-release-poisoning`,
`hospital-ransomware-surgery-day`, `port-authority-surge-response`); the six
`techvault-*` scenarios use none. The governing requirement is
**SEM-206 (Assessment Semantics)**. A downstream consumer,
`Brad-Edwards/aptl#606`, is blocked pending this decision.

## Decision

This ADR is **proposed**. It recommends a direction and defers acceptance to
human review.

### 1. The SDL scoring/reward surfaces are vestigial and should be removed

`metrics`, `evaluations`, `tlos`, `goals`, and `agents.reward_calculator` fail
the in-horizon discriminator: none is a signal a participant reads and acts on
during the run. Each expresses grading, ranking, or training machinery — a
data-use concern over the run's output. Every concern they express already has a
deliberately-scoped home in the experiment plane (ADR-055/064) or the backend
Evaluator (ADR-069). Keeping them in the SDL is not additive; it is a second,
weaker, authoring-time copy of a boundary the project already owns, and it
reconstructs inside the language the exact data-use concern the experiment
boundary was created to separate out.

The recommendation is therefore to **deprecate and remove** these five surfaces
from the SDL authoring language, its published schemas, the reference model, and
the example corpus.

### 2. Objectives and observable propositions stay in the horizon

Typed propositions/assertions (observable state claims) and `objectives`
(participant intent) are authored scenario meaning and remain first-class SDL
surfaces. `conditions` remain only as explicitly proposition-bound probe
implementations. Removing the grading pipeline must not weaken what a scenario
can assert about its own observable state (ADR-020's reproducibility warning).

### 3. Objective success references observable state, not a score

`objectives.success` references invariant or postcondition assertions over
typed propositions, not `conditions`, `metrics`, `evaluations`, `tlos`, or
`goals`. This preserves the issue #671 boundary: success is expressed against
observable state, which is in-horizon, rather than either an executable probe
or a score-shaped grading pipeline. ADR-079 defines the proposition and result
semantics.

### 4. Graded scoring and reward live only in the experiment/evaluator plane

When a scenario genuinely needs a graded score, cumulative reward, pass/fail
evaluation, or a leaderboard value, that concern is expressed through the
experiment-core contracts (`experiment-task-v1` metric definitions,
`experiment-study-v1` analysis plans, `experiment-derived-measure-v1`,
`experiment-evidence-record-v1`) and produced by the backend **Evaluator**
(ADR-069 §3) — never as an authored SDL environment fact. This answers issue
#671 question 3: scoring/reward belongs to the experiment/evaluator contract
boundary, and it enters the SDL only if and when a participant consumes such a
signal *in-run* (which none of the removed surfaces does).

### 5. Migration and deprecation path

Removal is staged, not abrupt (answering issue #671 question 4):

- **Deprecate first.** Mark the five surfaces deprecated in the schema and the
  SDL sections documentation with a pointer to the experiment/evaluator plane
  and to proposition/assertion-based objective success. Emit a deprecation diagnostic
  when a scenario uses them.
- **Migrate the four study-style scenarios.** For each, re-express objective
  success against typed propositions/assertions; move any genuinely-graded evaluation into an
  `experiment-*` artifact where the study intends scientific comparison; drop
  `reward_calculator` (it binds to nothing). The six `techvault-*` scenarios
  need no change.
- **Migrate the library artifacts.** `examples/library/patterns/study-scoring-chain.yaml`
  and `examples/library/templates/study/scored-study-protocol.yaml` are re-homed
  onto the experiment plane or retired.
- **Remove after a deprecation window.** Delete the surfaces from the language,
  schemas, and reference model; record the published-schema change per ADR-061
  and the schema-publication manifest; amend ADR-002.
- **Record the downstream dependency.** SEM-206's assessment semantics are
  updated to reflect that scoring/evaluation is an experiment-plane concern.
  `Brad-Edwards/aptl#606` follows by narrowing (not completing) its declared
  evaluator/scoring surface, per the dependency Brad recorded on issue #671.

### 6. Answers to the issue's four questions

1. **Do the scoring sections and `reward_calculator` belong in ACES?** Not in
   the SDL. They are vestigial given the experiment-vs-data-use boundary; their
   concerns belong to the experiment/evaluator plane.
2. **Should objective success reference conditions rather than a score?** It
   should reference observable state rather than a score, but ADR-079 corrects
   the original category error: typed propositions/assertions state observable
   truth; executable conditions only realize probes.
3. **If scoring belongs somewhere, is it the SDL or an experiment/evaluator
   contract?** The experiment/evaluator contract boundary (ADR-055/064/069), and
   only in the SDL when a participant consumes the signal in-run.
4. **What is the migration path?** Deprecate, migrate the four study scenarios
   and the two library artifacts, then remove after a deprecation window, with an
   ADR-002 amendment and a published-schema change record.

### 7. Scope of this decision

This ADR schedules and directs the examination's outcome; it introduces no
schema, model, or scenario change itself. Acceptance is a human decision at
review. On acceptance, downstream implementation issues execute sections 1, 3,
4, and 5.

## Alternatives Considered

### Keep the SDL scoring pipeline and only document the boundary

Rejected. This preserves two authorities for grading — the SDL pipeline and the
experiment-core contracts — and leaves `objectives.success` able to bypass
observable state. Documentation cannot repair a duplicated authority; it only
describes it. The experiment boundary (ADR-055/064/069) already owns these
concerns.

### Remove only `reward_calculator`, keep `metrics`/`evaluations`/`tlos`/`goals`

Rejected as the final position, though it is the correct *first* increment.
`reward_calculator` is the clearest case (unbound label, no validator, pure
training machinery), but the OCR grading chain fails the same discriminator for
the same reason. Stopping there would leave the coupled pipeline and the
`objectives.success` leak in place and would not resolve the SEM-206 or APTL
dependency. The staged migration in §5 removes `reward_calculator` first while
committing to the full removal.

### Move the scoring pipeline into the SDL runtime layer instead of removing it

Rejected. The concern is not which SDL layer owns grading; it is that grading is
a data-use concern that already has a non-SDL home. Relocating it within the SDL
would repeat the ADR-055 anti-pattern of reconstructing experiment concepts one
layer too low.

### Author the ADR as accepted with the removal in the same change

Rejected. Issue #671 explicitly does not decide the answer, and the removal
touches published schemas, the reference model, four scenarios, two library
artifacts, and an ADR-002 amendment — well beyond one change and requiring human
ratification. The ADR is proposed; implementation is spawned on acceptance.

## Consequences

### Positive

- One authority for scoring/evaluation/reward: the experiment/evaluator plane.
  The SDL stops carrying a duplicate, weaker copy.
- `objectives.success` becomes inspectable and in-horizon (typed observable
  propositions only), closing both the grading leak and the probe/meaning
  conflation.
- The language shrinks by five surfaces, one of which (`reward_calculator`) was
  unvalidated and unbound.
- SEM-206 and `Brad-Edwards/aptl#606` get a decision to follow instead of a
  duplicated surface to implement more completely.

### Negative / costs

- Four study-style scenarios and two library artifacts must be migrated.
- Removing published schema surfaces is a schema-evolution event (ADR-061) with
  a manifest change and a deprecation window.
- ADR-002's objective-success clause must be amended, and downstream consumers
  (APTL) must narrow their surfaces.

### Risks

- If "graded scoring lives in the experiment plane" is read as "graded scoring
  is gone," authors may lose a legitimate scientific capability. The migration
  must show the experiment/evaluator path for genuinely-graded studies, not just
  delete the SDL surfaces.
- If the deprecation window is skipped, existing scenarios break abruptly.
  Section 5 requires deprecate-then-remove.
- If only `reward_calculator` is removed and the follow-through lapses, the
  duplicated grading pipeline persists. The decision commits to the full removal
  via staged migration, and SEM-206 tracks completion.

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-07-06 | #682 | Accepted (proposed → accepted) and realized under SEM-206: the SDL scoring/reward surfaces (`metrics`/`evaluations`/`tlos`/`goals` and `agents.reward_calculator`) were removed, `objectives.success` narrowed to `conditions`, ADR-002's objective-success clause amended, and the published SDL schemas updated with change-ledger entries. The staged deprecation window in §5 was collapsed into one change: all in-repo consumers were migrated together, with the downstream `Brad-Edwards/aptl#606` tracked to follow. |
| 2026-07-12 | #725 | Per [ADR-079](adr-079-backend-neutral-proposition-and-truth-semantics.md), corrected the earlier classification of executable conditions as observable facts. Objective success now composes assertions over typed propositions; scoring/reward remains in the experiment/evaluator plane. |
