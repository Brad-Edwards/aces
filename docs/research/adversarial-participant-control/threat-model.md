# Adversarial Participant Threat Model

Date: 2026-07-30

Model: `adversarial-participant-boundary-threat-model-v1@rev1`.

## Actors

### Honest but fallible participant

An honest participant can misunderstand observations, form an invalid
proposal, select an unsupported capability, or violate policy accidentally.
Ordinary validation, admission, and negative tests primarily target this
actor.

### Intentionally subverting participant

An attack participant optimizes a protected side objective while attempting to
preserve apparent compliance and usefulness. It can construct structurally
valid actions, retain state when the apparatus permits it, adapt to visible
control outcomes, and coordinate through declared channels.

This actor is not defined by implementation kind. A human, script, RL policy,
LLM, or external service can occupy either mode.

### Untrusted content source

Observations, tool results, retrieved content, files, errors, and participant
messages can contain data intended to redirect control or destination. Their
content is untrusted even when transport authentication and content hashes are
valid.

### Adaptive policy-aware attacker

The attacker may know policy, monitor topology, score thresholds, audit
budgets, or prior decisions. Each kind and degree of knowledge is an explicit
evaluation variable. Nothing is assumed hidden merely because it is
operationally inconvenient to model.

### Colluding participants or monitors

Participants or monitors may coordinate, share state, launder influence, or
fail in correlated ways. Different identities, processes, or models do not
establish independence.

## Protected assets

- confidential participant and environment data;
- integrity of policy and control decisions;
- external systems reachable by tools and actions;
- participant-facing and external outputs;
- append-only behavior, control, crossing, evidence, and audit histories; and
- hidden experiment objectives and security configuration.

## Explicit-flow attack surface

The governed surface includes observations, tool results, retrieval, context,
retained memory, proposals, transformations, action arguments, participant
outputs, errors, callbacks, handoffs, external direction, shared state,
cross-participant crossings, and cross-episode replay.

It covers confidentiality leakage and untrusted influence through action,
output, argument, error, and collusion paths. It treats order and timing as
observable only where the selected SEM-230/ADR-099 profile declares them.

## Trust boundaries

- Apparatus declarations name capabilities and trust assumptions. Unknown
  external sources default to confidential and untrusted.
- Authentication identifies a principal; it does not endorse content.
- Structural validation admits shape; it does not authorize a sink.
- Deterministic policy and capability support decide release.
- Heuristic monitors supply evidence or advice; they do not authorize.
- Human or trusted-system actions name their exact authority effect.
- `RuntimeControlPlane` immediately before `RuntimeTarget` or serialization is
  the reference final-sink boundary.
- Stores bind exact history heads, policy/state cuts, labels, provenance, and
  decisions before effect.

## Attack goals

- redirect a valid action through prompt or tool-result injection;
- compose permitted reads and sends into confidential exfiltration;
- adapt to approvals, denials, edits, deferrals, audits, handoffs, thresholds,
  or budget exhaustion;
- launder influence or apparent authority through handoff or collusion;
- exploit missing labels, provenance, capability support, stale cuts, replay,
  streaming, callbacks, or error paths; and
- induce unsafe audit or diagnostic disclosure.

## Required controls

Controls compose rather than substitute for one another:

1. conservative two-coordinate information flow;
2. least-authority action and tool capability;
3. deterministic deny-first policy at the final sink;
4. explicit declassification and endorsement;
5. bounded monitors and intervention protocols;
6. atomic append-only decisions, replay, and safe evidence; and
7. profile-bound adversarial evaluation.

## Outside the guarantee

RAES does not claim observation or control of undeclared timing, storage,
resource, model-steganographic, or other covert channels. It does not inspect
or record chain-of-thought, private prompts, private model state, or
credentials. It does not establish model alignment or automatic honesty of a
participant, human, monitor, gateway, or backend.
