# Adversarial Participant Trust and Flow Architecture

Date: 2026-07-30

## Two revisioned profiles

`participant-boundary-flow-policy-v1@rev1` defines source defaults,
confidentiality and integrity domains, conservative joins, derivation,
declassification, endorsement, sinks, exact cuts, memory, and unknown
behavior.

`intentional-subversion-control-evaluation-v1@rev1` separately defines mode,
objectives, attacker knowledge, adaptive strategy, collusion, monitor
topology/correlation, audit and intervention protocols, memory/replay, and
measures.

Keeping the profiles separate prevents experiment roles or monitor scores from
becoming runtime authorization.

## Typed propagation path

```text
source/apparatus declaration
  -> observation, retrieval, tool result, or runtime fact
  -> participant context and retained memory
  -> proposal, transformation, output, and action arguments
  -> API-409 control/handoff and API-423 crossing
  -> exact-cut deterministic decision
  -> atomic append-only commit
  -> RuntimeTarget effect or participant/external disclosure
```

Every derived result has a fresh identity and binds its possible sources,
effective labels, profile revision, authority, exact cut, destination/sink,
predecessors, and safe evidence. Opaque processing retains the conservative
join of every possible influence.

## Final boundary

The final decision occurs after the last identity, authority, policy,
capability, destination, label, provenance, and state-cut resolution and
immediately before an irreversible effect or disclosure. The decision is
committed before effect.

Missing label or provenance, unknown profile, ambiguous join, stale cut,
unsupported capability, policy denial, history conflict, or failed commit
causes no backend call and no participant-visible or external release.
Streaming, callbacks, tool arguments, errors, and persistent writes are sinks.

## Existing owners to reuse

| Concern | Canonical owner |
| --- | --- |
| participant projection, policy, memory, strategy | ADR-085, ADR-095, SEM-230, SEM-231 |
| action proposal and admission | SEM-211 and participant action-admission contracts |
| control, intervention, and handoff | ACT-617, API-409, RUN-310 |
| crossings, transformations, delivery | API-423, RUN-319 |
| fact sources, derivation, audience, sinks | runtime-fact contracts and `RuntimeFactBindingPlane` |
| runtime boundary | `RuntimeControlPlane`, `RuntimeTarget`, crossing resolver/boundary |
| persistence | `RuntimeSnapshot`, participant histories, `ControlPlaneStore.commit_participant_transition()` |
| backend posture | API-407 and `resolve_participant_feature_support()` |
| experiment/evidence | existing experiment task/protocol/study/run/apparatus/evidence/measure contracts |
| diagnostics/audit | `Diagnostic`, sanitized failures, redacted 500 envelope, `AuditEvent` |
| governance | `ContractModel`, controlled vocabularies, publication manifests, concept authority, lineage |

No new generic action, event, crossing, policy, evidence, audit, error,
trajectory, or persistence hierarchy is authorized.

## Cross-cutting security path

1. Apparatuses declare capabilities and trust assumptions without portable
   prompts, credentials, private state, or hidden objectives.
2. Closed DTOs and request-size guards parse transport. Touched path, query,
   and header values receive separate bounds.
3. Strict identity, target, role, participant, controller, audience, and
   destination binding precedes semantic fact creation.
4. Existing runtime-fact, action, API-409, API-423, snapshot, and transition
   validators retain one owner per relation.
5. Flow policy, action admission, release authority, and API-407 effective
   capability compose deny-first.
6. The final runtime sink rechecks the stable cut and commits before effect.
7. Idempotency, replay, and expected heads preserve the decision and reject
   changed state.
8. Projection precedes serialization; errors and audit retain safe refs,
   digests, classifications, and counts only.
9. Portable semantics add no required environment variable, argv secret,
   subprocess, socket, daemon, sidecar, or host path.
10. Later schema work updates models, schemas, fixtures, publication hashes,
    generator parity, authority, and tests together.

## Human and monitor semantics

A human approval can be authorization, declassification, endorsement,
admission, editing, deferral, handoff, interruption, shutdown, or advice.
Each effect is explicit. Trusted editing creates a fresh proposal and re-enters
ordinary gates.

A monitor has a profile-scoped role, topology, visibility, correlation
assumption, and failure behavior. Its output is evidence or advice. Missing
monitor output never widens permission and a monitor score never authorizes an
action.

## Extensibility

New label domains, sources, sinks, participants, monitors, apparatuses,
backends, and attack strategies extend the two profiles and resolvers. They do
not rewrite the carrier model or add implementation-specific branches to
portable semantics.
