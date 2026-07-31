# Prior Art And Design Criteria For Participant-Relative Opacity

Date: 2026-07-29

Issue: [#810](https://github.com/OpenRAE/rae/issues/810)

## 1. Research Question And Method

The review asks how to define opacity for a RAES participant whose knowledge
may be affected by observations, omissions, controller decisions, timing,
ordering, policy revisions, and supervisor behavior. It also asks how that
relation differs from SEM-230 policy noninterference and from the incumbent
projected-history and epistemic relations.

Sources were selected in four passes:

1. foundational predicate-opacity definitions and knowledge
   characterizations;
2. discrete-event-system variants, verification, and supervisory synthesis;
3. adversary, declassification, dynamic-policy, timing, probability, and
   concurrency work that exposes missing quantifiers or observation channels;
4. epistemic logic and hyperproperty work used to compare opacity with
   knowledge and noninterference.

Preference was given to the original paper, author manuscript, publisher
record, or official book record. Surveys were used to locate and compare
variants, not as sole authority for the formal kernel. Recent preprints are
identified as such and are used only to expose design choices that older
known/unknown-supervisor models leave implicit.

This is a focused design review, not a systematic review or a claim of
exhaustive coverage.

## 2. Source Findings

### 2.1 Predicate opacity is a knowledge condition

[Bryans, Koutny, Mazaré, and Ryan, *Opacity Generalised to Transition
Systems*](https://doi.org/10.1007/s10207-008-0058-x) generalize opacity to a
predicate on runs and an observation function. The definition is
possibilistic: whenever the secret predicate is true on an actual run, the
observer's indistinguishable alternatives must include a run on which it is
false.

[Schoepe and Sabelfeld, *Understanding and Enforcing
Opacity*](https://doi.org/10.1109/CSF.2015.41) give a program-level formulation
parameterized by an environment relation and an observation relation. Their
knowledge characterization is the decisive bridge for RAES: opacity excludes
an observer information set contained wholly in the secret. It does not
require every pair of low-equivalent worlds to have equal observations.

The same work establishes three boundaries that RAES must preserve:

- ordinary opacity is one-sided and prevents learning that the predicate is
  true; learning that it is false is allowed;
- symmetric opacity requires opacity of both the predicate and its
  complement; and
- noninterference corresponds to opacity of every informative predicate under
  a matching observer model, while opacity of one selected predicate is
  strictly weaker.

Therefore the selected RAES baseline is predicate opacity, not an alias for
trace equivalence, policy noninterference, anonymity, or a generic
confidentiality flag.

### 2.2 DES variants select a secret scope; they do not replace the kernel

[Lin, *Opacity of Discrete Event Systems and its
Applications*](https://doi.org/10.1016/j.automatica.2011.01.002) and
[Saboori and Hadjicostis, *Verification of Infinite-Step Opacity and
Complexity Considerations*](https://doi.org/10.1109/TAC.2011.2173774) develop
state-estimation variants under partial observation. Current-state,
initial-state, finite/K-step, and infinite-step opacity answer different
questions about the cut or past state whose secrecy must remain possible.

[Jacob, Lesage, and Faure, *Overview of Discrete Event Systems Opacity:
Models, Validation, and
Quantification*](https://doi.org/10.1016/j.arcontrol.2016.04.015) compares
these model families and confirms that opacity is parameterized by both the
secret and the intruder's observation map.

RAES should represent the variants as declared profiles of one predicate-
opacity kernel:

- a secret predicate over current, initial, historical, or language-level
  facts;
- a named evaluation cut or horizon; and
- a declared observer projection and memory scope.

Treating every named DES variant as a separate relation identity would obscure
their common quantifier and make combinations such as participant-relative
K-step opacity unnecessarily difficult.

### 2.3 Supervisor knowledge and decisions are part of the threat model

[Badouel, Bednarczyk, Borzyszkowski, Caillaud, and Darondeau, *Concurrent
Secrets*](https://doi.org/10.1007/s10626-007-0020-5) study multiple partial
observers and synthesize control while the observers know the controller. This
is strong precedent for keeping the observer and controller distinct and for
declaring whether the controller is public.

[Yin and Lafortune, *A Uniform Approach for Synthesizing
Property-Enforcing Supervisors for Partially-Observed Discrete Event
Systems*](https://doi.org/10.1109/TAC.2015.2484359) construct a finite
information-state game for several enforceable properties, including opacity.
This supports a future finite-state synthesis path. It does not show that the
RAES runtime enforces opacity and does not turn a catalog definition into an
algorithm.

[Xie, Yin, and Li, *Opacity Enforcing Supervisory Control Using
Nondeterministic Supervisors*](https://doi.org/10.1109/TAC.2021.3131125)
show that nondeterministic online control choices can preserve plausible
alternatives in cases where deterministic supervisors cannot. Randomized or
nondeterministic choice must therefore be modeled in the possible-world
carrier; it is not itself evidence of opacity.

[Cui, Ma, Giua, and Yin, *Opacity Enforcing Supervisory Control with a
Priori Unknown Supervisors*](https://doi.org/10.48550/arXiv.2604.04070) is a
2026 preprint addressing the important intermediate case between a fully known
and a fully unknown supervisor. Its intruder cannot inspect the implementation
but learns about it by eavesdropping on online control decisions. It also
distinguishes observation-triggered and decision-triggered issuance. RAES must
make these choices explicit rather than treating “supervisor hidden” as one
binary setting.

The literature supports at least these supervisor-visibility profiles:

1. **fully known** — the same supervisor and policy realization constrain the
   actual world and every alternative;
2. **public contract, hidden realization** — alternatives may vary over hidden
   implementations consistent with the same public contract;
3. **online learned** — approvals, denials, edits, choices, handoffs, and
   deferrals enter the observer history according to declared issuance rules;
4. **selectively disclosed** — decision content, occurrence, timing, or
   delivery may be redacted or delayed under an explicit projection.

Even in profiles 2 and 4, changed external behavior can reveal a hidden
supervisor or policy change. Hiding the revision event is not a guarantee that
the revision is epistemically hidden.

### 2.4 Active participants require a strategy quantifier

[Partovi, Jung, and Hai, *Opacity of Discrete Event Systems with Active
Intruder*](https://arxiv.org/abs/2007.14960) is a preprint that models an
intruder able to inject inputs and observe responses. Reactive opacity requires
secrecy regardless of how the intruder manipulates the system.

This is directly relevant to RAES participants, which can act rather than only
watch. A passive profile can omit adversarial inputs. An active profile must
quantify over every allowed participant strategy mapping accumulated
observations to actions and compare actual and alternative worlds under the
same strategy. Otherwise an adaptive probe can distinguish worlds that a
passive trace projection equates.

The strategy domain must be bounded by declared participant capabilities and
policy. “Every strategy” must not silently include actions the participant
cannot issue or omit actions that the selected threat model permits.

### 2.5 Epistemic logic fixes the carrier and memory questions

[Fagin, Halpern, Moses, and Vardi, *Reasoning About
Knowledge*](https://mitpress.mit.edu/9780262562003/reasoning-about-knowledge/)
provides the interpreted-systems basis for knowledge at a point: an agent
knows a fact when it holds at every point compatible with the agent's local
state.

[Halpern and O'Neill, *Secrecy in Multiagent
Systems*](https://arxiv.org/abs/cs/0307057) treats secrecy relative to agents
and discusses nondeterminism, probability, synchrony, and resource bounds.
The practical RAES consequence is that the possible-world carrier cannot be
only “two event arrays.” It must include the model, run, cut, participant
local state, observation memory, policy/supervisor realization, and selected
scheduler/order assumptions.

Coalitions need a declared fused observation and memory model. Opacity for
every participant individually does not imply opacity for a coalition that
shares observations.

### 2.6 Noninterference and hyperproperties are adjacent, not synonyms

[Clarkson and Schneider,
*Hyperproperties*](https://doi.org/10.3233/JCS-2009-0393) classify
noninterference as a property of sets of traces and explain self-composition
and finite counterexample structure for important subclasses.

SEM-230's policy noninterference universally compares selected pairs of
policy-equivalent worlds under its declared strategy, release, and projection
parameters. Predicate opacity instead asks whether each actual secret point
has at least one nonsecret alternative in the observer's information set.

Under exactly matching carriers, observation relations, active strategies,
memory, time/order assumptions, and release policy:

- SEM-230 noninterference implies opacity of every eligible secret predicate;
- opacity of one predicate does not imply SEM-230 noninterference;
- equal projected histories for one pair provide a possible alternative for
  that pair, but do not establish the universal opacity quantifier; and
- epistemic indistinguishability defines the information-cell membership
  relation, while opacity constrains which secret labels may occupy a whole
  cell.

Trace inclusion, trace equivalence, simulation, refinement, and bisimulation
do not imply opacity unless their carriers and mappings preserve the selected
secret and observation semantics. Opacity does not imply those structural
relations.

### 2.7 Release and policy change alter knowledge

[Askarov and Sabelfeld, *Gradual
Release*](https://doi.org/10.1109/SP.2007.22) models attacker knowledge as a
set of secret inputs and requires knowledge to remain unchanged between
explicit release events.

[Myers, Sabelfeld, and Zdancewic, *Enforcing Robust Declassification and
Qualified Robustness*](https://doi.org/10.3233/JCS-2006-14204) and
[Askarov and Myers, *Attacker Control and Impact for
Confidentiality and Integrity*](https://arxiv.org/abs/1107.5594) show why an
active attacker must not gain uncontrolled influence over what is released or
whether release occurs.

[Broberg, van Delft, and Sands, *The Anatomy and Facets of Dynamic
Policies*](https://doi.org/10.1109/CSF.2015.16) separates dynamic-policy
choices such as direct release, replay, and time-transitive flow. These facets
matter for supervisor changes and declassification in RAES.

The selected opacity design must therefore state:

- whether policy revisions and release decisions are observations;
- whether a release changes the protected predicate, the observer
  information, or both;
- whether previously released information may be replayed; and
- whether the observer retains knowledge across episodes, retries, policy
  revisions, handoffs, concealment, or revocation.

Authorized declassification legitimately shrinks an information set and may
make a formerly opaque predicate knowable. The system remains conformant only
if the revised policy no longer requires opacity for that predicate or still
leaves a nonsecret alternative. Concealment and revocation affect future
availability; they do not erase knowledge already acquired.

### 2.8 Timing, probability, and concurrency need separate profiles

Schoepe and Sabelfeld distinguish progress-insensitive,
progress-sensitive, and timing-sensitive observation relations. Making ticks
observable turns secret-dependent duration into an output. RAES omissions and
delays are observable only when the selected model includes progress,
opportunities, deadlines, clocks, or another basis from which absence can be
inferred.

[Bérard, Mullins, and Sassolas, *Quantifying
Opacity*](https://doi.org/10.1017/S0960129513000637) treats secrets and
observations probabilistically and measures disclosure and uncertainty.
Possibilistic opacity considers support: an extremely unlikely nonsecret
alternative can suffice. It neither bounds posterior belief nor supplies
differential privacy. Probability-weighted leakage needs a separately
identified quantitative relation and evidence method.

[André, Lime, Marinho, and Sun, *Guaranteeing Timed Opacity Using Parametric
Timed Model Checking*](https://doi.org/10.1145/3502851) gives a specialized
timed model-checking path. Timed opacity must not be claimed from an untimed
event projection.

Concurrency requires a declared observation-order model. Total order, per-
participant order, causal partial order, and scheduler-visible interleavings
create different information cells. A witness based on a different schedule
is admissible only if that schedule is inside the declared possible-world
carrier and produces an observation equivalent under the chosen order model.

## 3. Selected Formal Kernel

Let the revisioned relation profile declare:

- \(\Omega\), the allowed points
  \(x=(M,\rho,t,\ell_o,\pi,\kappa)\), including model/supervisor realization
  \(M\), run \(\rho\), cut \(t\), observer local state or memory \(\ell_o\),
  policy realization \(\pi\), and declared scheduler/order context \(\kappa\);
- observer \(o\), which may be a participant, named audience, or coalition;
- initial-information function \(Init_o\);
- accumulated observation function \(Obs_o\);
- secret predicate \(S:\Omega\rightarrow\{\mathsf{true},\mathsf{false}\}\);
- optional active strategy domain \(\Sigma_o\); and
- horizon, memory, time, order, probability-support, and
  supervisor-visibility profiles.

The observer information cell at \(x\) is:

\[
I_o(x)=\{y\in\Omega\mid Init_o(y)=Init_o(x)
                  \land Obs_o(y)=Obs_o(x)\}.
\]

The one-sided participant-relative predicate-opacity relation is:

\[
\forall x\in\Omega.\quad
S(x)\Rightarrow\exists y\in I_o(x).\ \neg S(y).
\]

Equivalently, no actual secret point satisfies \(K_oS\). This equivalence
assumes the information cell contains exactly the worlds compatible with the
declared initial information and accumulated observation; it is not a claim
that the backend computes knowledge.

For an active profile, the definition is parameterized by each allowed
strategy \(\sigma\in\Sigma_o\). Actual and alternative runs must both be
possible under the same \(\sigma\), and the opacity condition must hold for
every allowed \(\sigma\). Quantifier order is part of the profile and must not
be inferred from prose.

Symmetric opacity is the conjunction of opacity for \(S\) and opacity for
\neg S\). It is an explicit stronger profile, not the default meaning of
opacity.

## 4. Observation Alphabet Requirements

`Obs_o` must state whether it includes each of the following:

- projected content and markings;
- event occurrence and delivery;
- failure, rejection, denial, approval, modification, cancellation,
  intervention, deferral, and handoff decisions;
- policy and supervisor revisions;
- an omission or withholding only when a declared opportunity, deadline, or
  progress model makes absence detectable;
- total order, participant-local order, causal partial order, or another
  named order projection;
- logical time, wall-clock time, durations, buckets, or no time;
- authorized evidence, audit, and retrieval surfaces;
- prior episodes, retries, replayed disclosures, and shared coalition memory.

The relation must distinguish “not observed” from “known not to have
occurred.” It must also distinguish decision content from the occurrence,
timing, and delivery of a decision. Redacting the content of a denial does not
hide the fact or timing of the denial when those remain observable.

## 5. Worked Design Tests

These examples are requirements for the later formal specification and
falsification suite.

### 5.1 One equal-history pair does not establish opacity

Worlds \(a\) and \(b\) have equal projected histories and opposite secret
labels, so \(b\) witnesses opacity for \(a\). Another actual secret world
\(c\) produces a unique projected history. A two-world equality probe over
\(a,b\) passes while opacity fails at \(c\). The universal actual-secret
quantifier is indispensable.

### 5.2 A supervisor decision leaks with identical payload projection

Two worlds project the same action payload and state observation. In the
secret world the supervisor denies the action; in the nonsecret world it
approves it. If the decision occurrence or outcome is observable, the
participant's information cell can become secret-only even though payload
projection is equal.

### 5.3 Opacity holds while noninterference fails

Every secret world has some nonsecret alternative with the same observation,
so predicate \(S\) is opaque. Two worlds that are equivalent under SEM-230's
policy nevertheless produce different low observations about a distinct
nonsecret fact. The selected opacity property holds while policy
noninterference fails.

### 5.4 Declassification changes knowledge

Before an authorized release, an information cell contains both secret and
nonsecret worlds. The release observation splits the cell and reveals the
predicate. Opacity fails after release unless the policy revision removes that
predicate from protection or the released value still admits a nonsecret
alternative. Later concealment cannot reconstruct the former information
cell for an observer with memory.

## 6. Design Criteria

The ADR, formal specification, catalog revision, bindings, examples, and child
program must satisfy all of the following.

1. **One revisioned predicate-opacity identity.** Define the one-sided kernel
   once. Express current/initial/K/infinite/language scopes and symmetric
   opacity as declared profiles, not undocumented synonyms.
2. **Participant-relative information cells.** Name the observer or coalition,
   initial information, observation function, memory, and possible-world
   carrier. Do not substitute two hand-picked traces for an information set.
3. **Explicit secret and cut.** Every claim identifies a typed predicate, the
   facts on which it may depend, its revision, and the cut/horizon at which it
   is evaluated.
4. **Supervisor visibility is a profile.** Declare known, hidden-realization,
   online-learned, or selective-disclosure semantics and the issuance rule for
   decisions. Never infer invisibility from implementation hiding.
5. **Decision leakage is first-class.** Include approval, denial, modification,
   deferral, handoff, cancellation, and intervention content/occurrence/time/
   delivery according to the selected observation profile.
6. **Omission requires an opportunity model.** An absent event is observable
   only under declared progress, opportunity, delivery, deadline, or clock
   assumptions.
7. **Active probing has a strategy quantifier.** Passive and active profiles
   stay separate; actual and witness worlds use the same allowed adaptive
   strategy.
8. **Time and order are dimensions.** Untimed, progress-sensitive,
   timing-sensitive, total-order, and partial-order claims cannot be silently
   exchanged.
9. **Nondeterminism is declared.** Possibilistic support, scheduler choices,
   environment choices, and supervisor randomization belong to the carrier.
   Randomness alone is not assurance.
10. **Probability is a different claim.** Baseline opacity is possibilistic.
    Posterior, entropy, leakage-probability, or differential-privacy claims
    require a separate quantitative relation and evidence scope.
11. **Coalitions are explicit observers.** Individual opacity never implies
    opacity under shared observations or memory.
12. **Release changes knowledge monotonically for a remembering observer.**
    Declassification, direct release, replay, concealment, and revocation have
    explicit policy effects; prior knowledge is not erased by a later policy.
13. **Relation boundaries remain exact.** State the conditional implication
    from matching SEM-230 noninterference, the non-implication in the reverse
    direction, and the non-equivalence with projected-history, epistemic,
    trace, simulation, refinement, and bisimulation relations.
14. **Assurance axes remain separate.** Relation definition, finite example,
    bounded falsification, finite-state model checking, mathematical proof,
    runtime enforcement, and backend realization are independently recorded.
15. **No adoption claim from literature.** A synthesis or verification
    algorithm in a cited model is prior art, not evidence that a RAES model,
    runtime, or backend implements it.
16. **Authority precedes delivery children.** Create the required DRAFT Ground
    Control semantic authority before opening requirement-backed
    implementation or assurance child issues.

## 7. Relation-Selection Recommendation

Use the catalog identity `participant-predicate-opacity`, class
`epistemic`, with unary property direction and an explicitly declared
possible-point carrier. The name keeps the one-sided predicate semantics
visible and avoids suggesting that all participant information is protected.

The relation should reuse the catalog's projection, quantifier, time, order,
probability, adversary, and assurance dimensions. The catalog and claim
binding should be advanced through the normal revision process; no opacity
claim should be inferred from a SEM-230 binding or from a projected-history
equality result.

The first revision should define the relation and its profiles but remain
honest about delivery: no general decision procedure, synthesis algorithm,
runtime monitor, proof, timed/probabilistic checker, or backend realization is
part of the definition issue unless separately implemented and evidenced.
