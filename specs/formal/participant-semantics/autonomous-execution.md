# Autonomous Participant Execution

This specification defines DSL-437 execution as a composition of existing
participant semantics and the shared time model. It introduces no background
actor, inject, or private clock.

## Authored Policy

For behavior specification \(B\), autonomous policy \(P\) contains:

- a non-empty participant set \(A_P \subseteq A_B\);
- an ordered action sequence \(Q_P \subseteq Q_B\);
- observation boundary \(V_P \in V_B\);
- participant implementation reference \(I_P\);
- shared clock \(C_P\), progression policy \(G_P\), and temporal constraints
  \(T_P\);
- finite action-attempt and in-flight bounds;
- failure disposition; and
- evaluation-authority mode and references.

Every participant action and observation in \(P\) must already be admitted by
the participant and parent behavior specification. \(G_P\) and every member of
\(T_P\) use \(C_P\). Exactly one member of \(T_P\) is a cadence constraint.
Cadence starts must be non-negative. For stepped progression, its start and
period must be integer multiples of `step_ticks`; unreachable cadence points
are invalid. Externally paced
autonomous policies are rejected until a portable backend-to-runtime transition
driver exists. Runtime-owned wall pacing drives `real_time` and `dilated`
policies only when the bound clock declares runtime authority. Backend,
system, and external clock authorities are never advanced by the participant
driver. Stepped and event-driven clocks advance only through shared-time
control.

## Non-Evaluated Authority Invariant

When `evaluation_authority.mode = none`:

\[
\forall a \in A_P : role(a) = green
\]

and \(B\) has no outcome-interpretation or authority-scope refs, no objective
names \(a\) as its actor, and the authority record has no objective, proof,
score, or receipt refs. This is a semantic rejection condition, not guidance.

## Deterministic Selection

For the v1 `ordered_cycle` strategy, scheduler state for participant \(a\) is:

\[
S_{P,a} = (digest(P,T), episode, segment, nextTick, nextAction, attempted, succeeded, failed, state)
\]

At a due tick, the selected action is:

\[
Q_P[attempted \bmod |Q_P|]
\]

The scheduler makes no random draw. A stochastic participant implementation is
run apparatus and must use the existing random-stream control and experiment
apparatus contracts; it does not change this selection relation.
The digest covers the resolved clock, time domain, progression policy, and
temporal constraints, not only their addresses.

## Execution And Evidence

An action may commit only in this order:

1. resolve the run-selected participant implementation;
2. require its manifest reference to equal \(I_P\);
3. bind the participant, action, observation boundary, and every temporal
   constraint;
4. invoke the backend-native participant action;
5. require a typed native outcome distinct from control-operation success;
6. append action, state-transition, and observation events; and
7. update typed scheduler readback.

The scheduler applies these checks to every participant-runtime implementation,
not only implementations derived from the reference base class. If the result
has the wrong result type, is absent, non-terminal, bound to another episode,
reports an observation point outside the bound temporal contexts, or lacks the
matching terminal history event, the native snapshot and portable behavior
history are not committed. The failed attempt is recorded only in scheduler
accounting so the same action instance cannot be replayed. If native execution
reports a valid terminal failure, no successful behavior history is fabricated.
The current action must append exactly the ordered attempted, transition, and
terminal observation events, and the attempted event's actor provenance must
match the selected participant implementation.
`stop` marks the scheduler failed; `continue` advances the bounded attempt
counter and cadence.

## Lifecycle

Pause changes non-terminal scheduler states on the governed clock to `paused`;
resume returns them to `running`. Reset begins a new shared-time segment,
resets each bound participant episode, and restores the initial cadence,
action index, and counters. Reapplying an unchanged plan preserves state.
Reapplying a materially changed policy at the same address fails before
mutation. A participant belongs to at most one autonomous execution policy.
Clock transitions that would cross a due cadence without executing it fail
before clock mutation. Reset-capable autonomous policies require the backend
manifest to advertise `supports_coordinated_participant_reset`. Runtime
registration then requires the time authority's `reset_with_participants`
operation and the participant runtime's atomic `reset_many` operation through
capability-specific runtime protocols. Together they form one backend
transaction: the implementation must prepare all clock and episode changes
before commit, return one coherent snapshot on success, and leave no externally
observable mutation on failure. Scheduler
counters are updated locally only after that transaction succeeds. A copied
predecessor snapshot is not treated as rollback of backend side effects.
Participant runtimes with additional native reset state must supply their own
atomic batch implementation rather than inherit the reference in-memory
transaction.
Durable and conformance validation require scheduler segment/lifecycle and
episode identity to agree with the bound shared clock and live episode.

## Backend Admission

Let backend capability \(K\) declare supported strategies and finite maxima.
Admission requires:

\[
|A_P| \le K.participants
\]

\[
P.maxAttempts \le K.actionAttempts
\]

\[
P.maxInFlight \le K.inFlight
\]

and \(P.strategy \in K.strategies\). This establishes only that the backend
claims it can attempt realization. Admission also requires:

\[
Q_P \subseteq K.actions
\]

\[
V_P \in K.observationBoundaries
\]

\[
targets(Q_P) \subseteq K.targets
\]

and every parent behavior feature required by \(P\) must be in the backend
feature set. A reset-capable policy additionally requires the coordinated
participant-reset capability and runtime method. Runtime state, typed native
action outcome, history, and backend evidence establish what occurred.

## Nonclaims

This contract does not prove participant intelligence, human realism, service
fidelity, throughput, causal attribution, evaluator correctness, or
golden-range equivalence. Those claims require their existing RAES evidence and
conformance surfaces.

## Delivery Status

The reference implementation covers authored validation, canonical
compilation, exact fail-closed capability admission, RuntimeManager-driven
shared-clock execution, native binding and typed action outcomes, policy
identity and lifecycle, automatic real-time/dilated cadence driving,
transactional backend clock/participant reset admission and invocation,
durable/API/conformance cross-surface scheduler state, and focused race and
negative cases. The wall driver re-reads clock state after waits, remains
owned until its thread exits, and records unexpected termination. Externally paced autonomous
execution remains rejected because no portable transition-notification
contract is yet governed. This establishes the portable protocol behavior only. A
production backend still must prove that its selected participant
implementation, native adapter, targets, evidence, and readback faithfully
materialize a scenario.
