# Prior Art and Design Criteria for Scoring/Reward Scope

These notes support issue #671, which asks whether ACES should carry
scoring/reward language at all. They are research and design evidence for the
proposed decision recorded in
[`ADR-073`](../../decisions/adrs/adr-073-scoring-reward-language-scope.md); they
are not contract authority by themselves. The concrete surface map that this
analysis reasons over is in
[`scoring-surface-inventory`](scoring-surface-inventory.md).

## The question in one line

The Open-Cyber-Range (OCR) scoring pipeline
(`conditions -> metrics -> evaluations -> TLOs -> goals`) and the CybORG
`agents.reward_calculator` field were inherited into the SDL early (ADR-002) and
preserved without re-litigating whether authored *scenario meaning* is the right
home for *grading and reward*. The experiment-core work has since built a
separate, deliberately-scoped home for measurement and evaluation. This note
assembles the prior art that decides which home is correct.

## The reward hypothesis places reward inside the agent-environment loop, not the scenario text

In reinforcement learning, reward is the scalar signal an agent maximizes; the
reward hypothesis holds that goals and purposes can be framed as the
maximization of expected cumulative reward (Sutton and Barto,
*Reinforcement Learning: An Introduction*, 2nd ed., MIT Press, 2018; Silver,
Singh, Precup, and Sutton, "Reward is enough," *Artificial Intelligence* 299,
2021). Two consequences matter for ACES:

1. Reward is a property of the **agent-environment interface and the training
   objective**, not of the environment's authored description. The same
   environment can be trained against many reward functions; the reward function
   belongs to the experiment/agent, not to the scenario.
2. A reward function is a *measurement extracted from the run and consumed by
   training or ranking*. In the CAGE-2 evaluation protocol a fixed policy is run
   and cumulative reward is accumulated as the researcher's score
   (TTCP CAGE Challenge 2, arXiv:2309.07388, pinned in ADR-069). That is the
   textbook case of a data-use signal: it is read by the *evaluator*, not by a
   participant acting within the horizon.

This is the same conclusion the issue's discriminator reaches from first
principles, and it is why `agents.reward_calculator` — a bare label naming a
CybORG reward class — is the weakest of the surfaces: it selects training
machinery that no ACES participant perceives.

## Specification gaming shows reward is unsafe to freeze as authored fact

The AI-safety literature on reward misspecification and specification gaming
(Amodei, Olah, Steinhardt, Christiano, Schulman, and Mané, "Concrete Problems
in AI Safety," arXiv:1606.06565, 2016; and the subsequent
specification-gaming/reward-hacking literature) shows that reward functions are
frequently revised as flaws are found, and that a reward is only meaningful
relative to the agent and training regime it scores. Baking a specific
reward-calculator selection into the authored, versioned scenario couples
scenario meaning to a mutable, agent-specific training artifact — exactly the
coupling the experiment-core boundary was created to avoid.

## Experiment-database practice separates scenario, task, run, and evaluation

The experiment-database and reproducibility literature already relied on for the
experiment-core design (see
[`../experiment-core/ml-experiment-rigor`](../experiment-core/ml-experiment-rigor.md))
consistently separates the *data/scenario-like input* from the *task*, the
*run*, and the *evaluation/metrics* (Vanschoren, van Rijn, Bischl, and Torgo,
"OpenML: networked science in machine learning," *SIGKDD Explorations* 15(2),
2014; and the REFORMS/DOME reproducibility work cited there). Metrics are task-
and study-level analysis concepts, not properties of the scenario input. ACES
adopted this separation in ADR-055: `experiment-task-v1` binds a scenario to an
evaluation protocol and metric definitions, and ADR-055's guardrails explicitly
say **"Do not treat SDL `objectives` as EXP-701 task records; they remain
scenario-local objective declarations."** The SDL scoring pipeline predates that
separation and now reconstructs it one layer too low.

## ACES has already drawn this boundary — three times

The decisive prior art is internal and verifiable:

- **ADR-055 (Experiment Core Contract Boundary)** established that tasks,
  runs, studies, and metric definitions live in the experiment-core contract
  family, not the SDL, and warned that reusing SDL objectives as task records
  blurs scientific claims.
- **ADR-064 (Experiment Evidence and Measure Contract Boundary)** published
  `experiment-evidence-record-v1` (raw evidence) and
  `experiment-derived-measure-v1` ("a derived measure or evaluation output").
  Evaluation outputs and derived measures are, by this decision, experiment
  artifacts.
- **ADR-069 (CAGE-2 Replication Architecture) §3** makes the backend
  **Evaluator** the component that "projects reward, objective,
  terminal-condition, and scoring facts into ACES evaluation results, evidence
  records, and derived measures," and §1 treats native "reward arrays" and
  "leaderboard scores" as *source facts* that become portable only when bound to
  existing ACES evidence/measure concepts. ADR-069 §7 also rejects defining
  "equivalence as one score."

Under these three decisions there is already a correct home for every
score-shaped concern the SDL pipeline expresses. Keeping the SDL pipeline is not
additive; it is a second, weaker, authoring-time copy of a boundary the project
already owns.

## What legitimately stays in the horizon

The same corpus is equally clear about what belongs in authored scenario
meaning:

- **`conditions`** are observable state facts (ADR-002; assessment-semantics
  reference), and ADR-020 anchors participant "starting conditions" to them.
  They are read within the horizon.
- **`objectives`** are scenario-local participant intent (ADR-002). ADR-055
  affirms they stay scenario-local and must not become task records.

The only defect on the in-horizon side is the **success bridge**:
`objectives.success` can currently be expressed as a score
(`metrics`/`evaluations`/`tlos`/`goals`) instead of as observable state
(`conditions`). Issue #671 question 2 asks precisely this, and the boundary
answers it: objective success should be expressed against observable state, not
a grading pipeline.

## Design criteria for ADR-073

A sound decision on scoring scope must satisfy:

1. **Discriminator consistency.** Keep a surface in the SDL only if a
   participant reads and acts on it within the horizon. Score-shaped surfaces
   fail this; observable-state surfaces pass it.
2. **No duplicate authority.** Do not keep an SDL surface whose concern is
   already owned by the experiment-core contracts (ADR-055/064) or the backend
   evaluator (ADR-069). Grading and reward are already owned there.
3. **Preserve reproducibility.** Objective success and observable outcomes must
   remain expressible against `conditions`, so removing the grading pipeline
   does not weaken what a scenario can assert about its own state (ADR-020's
   reproducibility warning).
4. **Honest migration, not silent breakage.** Existing study-style scenarios
   that use the pipeline must have a stated path — either to `conditions`-based
   objective success, or to the experiment/evaluator plane for genuine graded
   scoring — with deprecation rather than abrupt removal.
5. **Falsifiable claim.** Per ADR-021, the decision must name the artifacts it
   changes and the downstream consumers it affects (SEM-206 assessment
   semantics; APTL evaluator/scoring surface, Brad-Edwards/aptl#606), so the
   claim can be checked.
6. **Decision deferral.** Issue #671 explicitly does not decide the answer; the
   ADR is authored **proposed** so acceptance is a human decision at review.

## Sources

Internal (authoritative, in-repo):

- ADR-002 Declarative Experiment Objectives in the SDL (records the OCR pipeline
  inheritance).
- ADR-020 Declarative Participant Framing Boundaries (reward assets deferred;
  conditions as starting state; reproducibility warning).
- ADR-055 Experiment Core Contract Boundary.
- ADR-064 Experiment Evidence and Measure Contract Boundary.
- ADR-065 Experiment Run Provenance Contract Boundary.
- ADR-068 Experiment Trials, Replication, and Replay Claims.
- ADR-069 CAGE-2 Replication Architecture.
- ADR-021 Falsification-First Claim Evidence Gate.
- Requirement SEM-206 Assessment Semantics.

External:

- Sutton and Barto, *Reinforcement Learning: An Introduction*, 2nd ed., MIT
  Press, 2018.
- Silver, Singh, Precup, and Sutton, "Reward is enough," *Artificial
  Intelligence* 299, 2021.
- Amodei, Olah, Steinhardt, Christiano, Schulman, and Mané, "Concrete Problems
  in AI Safety," arXiv:1606.06565, 2016.
- Vanschoren, van Rijn, Bischl, and Torgo, "OpenML: networked science in machine
  learning," *SIGKDD Explorations* 15(2), 2014.

Upstream (pinned by ADR-069):

- TTCP CAGE Challenge 2, arXiv:2309.07388, and the `cage-challenge-2` / `CybORG`
  repositories at the commits pinned in ADR-069 (reward calculators and
  `Evaluation/evaluation.py`).
