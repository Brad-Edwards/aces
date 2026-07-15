# Participant Information-Flow And Control Requirement Disposition

Date: 2026-07-15
Ground Control project: `aces-sdl`
Parent issue: [#794](https://github.com/Brad-Edwards/aces/issues/794)

Requirement authority was reconciled before dependent issues were filed. New
requirements remain DRAFT: their existence authorizes and scopes future work;
it does not claim implementation. Issue #794 itself is requirement-free and
does not transition any new requirement ACTIVE.

## Disposition rules

- **Reuse**: the existing statement already owns the required meaning; child
  work must not redefine it.
- **Amend**: the existing concern is correct but its Ground Control statement
  was strengthened by #794 before implementation proceeds.
- **New**: no existing requirement cleanly owns the bounded concern; #794
  created the requirement before its dependent issue.
- **Replace**: retire one authority in favor of another. No replacement is
  required by this design.
- **Adjacent**: retain the requirement and its independent scope; consume it as
  a dependency without making it part of the new authority.

## Disposition map

| UID | Status on 2026-07-15 | Disposition | Decision | Program issue |
| --- | --- | --- | --- | --- |
| SEM-208 | ACTIVE | reuse | Role-neutral action/observation/state semantics remain canonical. | dependency of #796 |
| SEM-209 | ACTIVE | reuse | Joint action and interaction remain canonical. | dependency of #796 |
| SEM-210 | ACTIVE | reuse | `V_p,o` and ordered view transitions remain the visibility authority. | dependency of #796/#296 |
| SEM-211 | ACTIVE | reuse | Typed action applicability/admission remains canonical. | dependency of #251/#799 |
| SEM-212 | ACTIVE | reuse | Evidence-labelled attribution remains canonical. | dependency of #796 |
| SEM-213 | ACTIVE | reuse | Participant time/order semantics remain canonical. | dependency of #796 |
| SEM-219 | DRAFT | reuse | ADR-083 scope is sufficient; implementation remains bounded to affordances. | [#294](https://github.com/Brad-Edwards/aces/issues/294) |
| SEM-220 | DRAFT | reuse | ADR-083 scope is sufficient; implementation remains bounded to decision surfaces. | [#295](https://github.com/Brad-Edwards/aces/issues/295) |
| SEM-226 | DRAFT | amend | Statement now names withholding, projection/masking, redaction, disclosure/declassification, transformation, loss, and evidence while retaining ADR-083 authority. | [#296](https://github.com/Brad-Edwards/aces/issues/296) |
| **SEM-230** | **DRAFT** | **new** | Owns revisioned participant information-flow/control policy, labels, projections, and exact claim boundaries. | [#796](https://github.com/Brad-Edwards/aces/issues/796) |
| ACT-617 | DRAFT | amend | Statement now requires explicit controller/authority state and ordered approval, direction, intervention, handoff, override, and cancellation distinct from admission/execution/observation. | [#251](https://github.com/Brad-Edwards/aces/issues/251) |
| DSL-111 | ACTIVE | reuse | Continues to own environment/orchestration inject identity and scheduling. | dependency of #797 |
| **DSL-142** | **DRAFT** | **new** | Owns participant addressee, disclosure/delivery, order, intervention binding, and evidence while preserving DSL-111 inject identity. | [#797](https://github.com/Brad-Edwards/aces/issues/797) |
| API-406 | ACTIVE | reuse | Existing lifecycle, observation, shared-state, snapshot, and history carriers remain canonical. | dependency of #798 |
| API-407 | ACTIVE | reuse | Existing feature-support/constraint seam owns new participant-control capabilities; no replacement or second manifest is needed. | [#801](https://github.com/Brad-Edwards/aces/issues/801) |
| API-409 | DRAFT | amend | Statement now distinguishes proposals, approvals/denials, directions, interventions, handoffs, overrides, cancellations, controller/authority, order, provenance, evidence, and disposition. | [#252](https://github.com/Brad-Edwards/aces/issues/252) |
| **API-423** | **DRAFT** | **new** | Owns common crossing decision, transformation, declassification/redaction, disposition, loss, evidence, and provenance refs without a generic payload carrier. | [#798](https://github.com/Brad-Edwards/aces/issues/798) |
| RUN-305 | DRAFT | reuse | Append-only state/history remains the persistence incumbent; traceability/status needs separate reconciliation when its own scope is resumed. | dependency of #799 |
| RUN-306 | ACTIVE | reuse | Observable proposal/admission/attempt/observation/state lifecycle remains canonical. | dependency of #255/#799 |
| RUN-307 | ACTIVE | reuse | Shared operational state remains canonical. | dependency of #799 |
| RUN-308 | ACTIVE | reuse | Ordering, concurrency, conflict, and time-management carriers remain canonical. | dependency of #796/#799 |
| RUN-310 | DRAFT | amend | Statement now requires ordered supervision/control transitions, stale/conflict handling, append-only evidence, and separation from admission/execution/observation. | [#255](https://github.com/Brad-Edwards/aces/issues/255) |
| **RUN-319** | **DRAFT** | **new** | Owns reference-runtime crossing enforcement, fail-closed capability use, persistence, audit, and realization evidence. | [#799](https://github.com/Brad-Edwards/aces/issues/799) |
| ASR-502 | ACTIVE | adjacent | Existing backend conformance runner/corpus remains canonical. | dependency of #800 |
| ASR-519 | ACTIVE | adjacent | Existing realization-honesty checks remain canonical. | dependency of #800 |
| ASR-527 | ACTIVE | adjacent | Existing participant implementation/exposure conformance remains canonical. | dependency of #800 |
| **ASR-535** | **DRAFT** | **new** | Owns participant-policy falsification, bounded formal evidence, adversarial backend cases, relation bindings, and explicit nonclaims. | [#800](https://github.com/Brad-Edwards/aces/issues/800) |

## New requirement records

### SEM-230 - Participant Information-Flow And Control Semantics

The ecosystem shall define revisioned participant-relative information-flow
and control semantics for input admission, output projection, disclosure and
declassification, transformation, observable and hidden action labels, policy
change over time, and the precise relation and assurance boundary of every
noninterference or behavioral claim.

### DSL-142 - Participant-Directed Inject Binding And Delivery

The language shall model participant-directed inject bindings and delivery
policies distinctly from environment-directed injects while preserving
orchestration identity, participant addressee, disclosure/observation basis,
temporal/ordering semantics, intervention meaning when applicable, and
required delivery evidence.

### API-423 - Participant Crossing Policy And Evidence Contracts

The ecosystem shall define portable plain-data contracts for participant
ingress/egress policy decisions, transformations, disclosures, interventions,
participant-directed inject deliveries, and bounded evidence/provenance without
imposing a generic message transport or duplicating existing carriers.

### RUN-319 - Participant Information-Flow Policy Enforcement

The runtime shall enforce and record participant-relative crossing policies
for input admission, output projection, intervention/handoff, participant-
directed inject delivery, and governed transformations, failing closed when
required semantics or capabilities are unavailable and preserving append-only
decision/realization evidence.

### ASR-535 - Participant Information-Flow And Relation Assurance

The ecosystem shall provide executable assurance for participant information-
flow/control claims, including negative leakage/declassification cases,
relation-bound claim records, bounded model checks or proofs where explicitly
claimed, backend conformance evidence, and nonclaims preventing finite evidence
from being promoted to universal noninterference or bisimulation.

## Replacement decision

No requirement is replaced or deprecated. The gap came from missing
composition and bounded sub-authorities, not conflicting ownership. Accepted
ADRs are not rewritten. ADR-085 composes them and future accepted-content
changes follow ADR-059.

## Governance nonclaims

- DRAFT does not mean implemented, tested, proved, or runtime-realized.
- An issue link is a planning/documentation relation until delivery is merged
  and traceability is reconciled.
- API-407 ACTIVE does not mean every new participant-control feature is already
  supported.
- No child requirement transitions ACTIVE through issue #794.
