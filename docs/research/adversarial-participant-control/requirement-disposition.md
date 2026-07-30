# Adversarial Participant Control Requirement Disposition

Date: 2026-07-30

## New DRAFT authority

SEM-233, **Adversarial Participant Boundary Information-Flow Control**, is
DRAFT, MUST, wave 4. Canonical Ground Control id:
`fe8c490c-20c1-4178-b32b-49085d6da69c`.

It owns independent confidentiality and integrity coordinates, conservative
explicit-flow derivation, distinct release operations, typed cross-participant
and cross-episode carriage, and fail-closed final-sink decisions.

ASR-536, **Intentional-Subversion Participant Control Evaluation**, is DRAFT,
MUST, wave 4, non-functional. Canonical Ground Control id:
`6ff9b816-4603-41e1-b3f0-cf0128a033db`.

It owns honest/attack modes, main/side objectives, attacker knowledge and
adaptation, collusion, monitor topology/correlation, audit and intervention
protocols, memory/replay, and separate safety/usefulness/cost/uncertainty
evidence.

Issue #812 defines both authorities but does not satisfy their positive
implementation or evaluation clauses.

## Reused and downstream authority

| Requirement | Disposition | Scope | Boundary |
| --- | --- | --- | --- |
| SEM-230 | reuse | participant projection, exact-cut policy, memory, strategies, declassification, noninterference | SEM-233 adds explicit label coordinates and sinks, not another participant world |
| ACT-617 | reuse | control authority, intervention, handoff, override, cancellation | control change is not flow release or action admission |
| API-409 | reuse | typed control occurrences | records carry flow refs; no second control schema |
| API-423 | reuse | typed crossing stages and context/order | contract validity is not final-sink enforcement |
| RUN-310 | reuse | authenticated supervisory lifecycle, persistence, replay | final-sink work reuses its identity and atomicity boundary |
| RUN-319 | extend downstream | reference crossing enforcement | #1003 adds SEM-233 last-boundary enforcement |
| API-407 | extend downstream | declared/effective capability, downgrade, realization, conformance | #1004 adds bounded flow/quarantine/sink support |
| ASR-535 | reuse | bounded flow assurance and overclaim prevention | ASR-536 adds intentional-subversion variables; it does not relabel old evidence |

## Ordered work

- #1001: semantic authority.
- #1002: portable contracts after #1001.
- #1003: final-sink runtime enforcement after #1002.
- #1004: apparatus and backend support after #1002.
- #1007: adversarial evaluation after #1001 and #1002.
- #1008: evidenced documentation after #1003, #1004, and #1007.

All children name at least one of SEM-233 or ASR-536 and retain explicit
nonclaims. DRAFT status remains correct until their positive obligations and
traceability are complete.
