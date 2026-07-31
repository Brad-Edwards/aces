# Mixed Cross-Backend Participant Control Requirement Disposition

Date: 2026-07-31

## New DRAFT authority

SEM-234, **Mixed Cross-Backend Participant-Control Composition**, is DRAFT,
MUST, wave 4. Canonical Ground Control id:
`38d807a4-ff50-4f9f-99a0-09e3ee3cdaa2`.

It owns:

- alternative simulation or emulation/operation realization;
- simultaneous mixed realization in one admitted trial;
- stable allocation units and explicit topology edges;
- separation of controller authority, realization responsibility, HLA
  ownership, routing, and disclosure;
- clock/order and policy mappings;
- linked inter-trial and finite pre-admitted within-run changes;
- the three open/closed axes; and
- fail-closed loss, weakening, and evidence rules.

ASR-537, **Cross-Backend Participant-Control Realization and Transfer
Evidence**, is DRAFT, MUST, wave 4, non-functional. Canonical Ground Control
id: `b425b452-a796-4997-a29f-3432baa6496a`.

It owns:

- pure simulation, pure emulation/operation, simultaneous mixed, and staged
  lanes;
- open-loop and closed-loop cases;
- stale, unsupported, unmapped, mismatched, delivery, retraction, and metadata
  adversarial cases;
- complete apparatus/model/data/time/provenance binding;
- zero-effect requirements for denied cases;
- transfer, readiness, conformance, and reproduction evidence; and
- separation from trace, bisimulation, IFC/noninterference, and equivalence.

Issue #813 defines both authorities but does not satisfy their positive
implementation or evaluation clauses.

## Reused and downstream authority

| Requirement | Disposition | Scope | Boundary |
| --- | --- | --- | --- |
| SEM-230 | reuse | Participant/audience projection, exact-cut policy, release, memory, strategy, and noninterference boundary | SEM-234 adds composition; it does not add a second participant world |
| SCE-002 | extend downstream | Scenario-family selection, deterministic trial admission, apparatus pinning, immutable plan/run identity | #1015 adds mixed allocation and finite phases without a parallel lifecycle |
| API-407 | extend downstream | Declared/effective backend support, constraints, downgrade, realization, and conformance | #1017 adds governed mixed services in the existing manifest block |
| API-423 | reuse | Typed crossing request through audit, context, predecessors, order, and evidence | Composition edges reference crossings; no generic federation event |
| RUN-310 | reuse and extend downstream | Authenticated control, one acting controller, revision-fenced handoff, persistence, replay | Providers do not become controllers; #1016 composes the exact cut |
| RUN-319 | extend downstream | Reference crossing mediation and atomic decision-before-effect | #1016 resolves allocation/topology/time before the same final boundary |
| ASR-535 | reuse | Bounded assurance, relation claim binding, finite falsification, and overclaim prevention | ASR-537 adds mixed/transfer variables without merging assurance axes |

## Deferred authority

Revision 1 does not support:

- simultaneous controllers for different scopes;
- leases;
- quorum, priority, arbitration, unanimity, or fused control; or
- transfer oscillation/livelock guarantees.

A future version requires exact controller/scope identities, renewal/expiry
and fencing or composition rules, atomic transition, clock/order, failure,
progress, and evidence semantics. These concepts are not encoded in open
metadata or synthetic controller identities.

## Ordered work

- #1013: SEM-234 semantic authority.
- #1014: portable contracts after #1013.
- #1015: deterministic trial admission after #1014.
- #1016: fail-closed runtime coordination after #1014 and #1015.
- #1017: backend capability and conformance after #1014 and #1016.
- #1018: ASR-537 demonstration after #1015, #1016, and #1017.
- #1019: evidenced documentation after #1016, #1017, and #1018.

All children name SEM-234 or ASR-537 and retain explicit nonclaims. Generic
backend capability and conformance work is in milestone 61. Participant
semantics, runtime composition, evaluation, and claims remain in milestone 67.
