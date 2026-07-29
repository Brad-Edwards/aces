# Participant-Crossing Bisimulation Requirement Disposition

Date: 2026-07-29

## New Authority

SEM-232, **Proof-Bearing Participant-Crossing Bisimulation**, is DRAFT, MUST,
wave 4. It owns:

- canonical Ground Control requirement id
  `860b0b1e-55cc-42e6-9da8-b7eeeab7172c`;
- the revision-pinned abstract and concrete formal LTS pair;
- the closed participant/audience projection and exact relation;
- the complete finite quantified carrier;
- independently reproducible machine-check evidence;
- safe witness and counterexample evidence;
- normative-semantics/model/runtime drift mapping; and
- explicit separation from runtime, backend, noninterference, and opacity
  claims.

Issue #811 defines that authority but does not satisfy its positive
machine-check result.

## Reused Authority

| Requirement | Disposition | Reused scope | Boundary |
| --- | --- | --- | --- |
| SEM-230 | reuse | Participant/audience projection, exact-cut policy, labels, memory, order, declassification, and noninterference boundary. | Bisimulation does not prove noninterference. |
| SEM-231 | coordinate | Revisioned observer-relative profile and opacity boundary. | Bisimulation does not prove opacity; no parallel profile registry. |
| ASR-535 | reuse | Relation claim binding, finite evidence discipline, mapping/conformance separation, and negative evidence. | Finite probes are not the relation result. |
| API-423 | reuse | Portable crossing request, decision, transformation, delivery, observation, and audit occurrences. | Contract validity is not equivalence. |
| RUN-319 | reuse | Reference mediation, exact-cut gates, idempotency, replay, histories, and atomic persistence. | Runtime realization is separate from formal equivalence. |

## Dependency Order

- #971 implements the independent formal models.
- #972 maps the reference runtime after #971.
- #973 builds counterexamples after #971 and #972.
- #974 runs the finite equivalence check after #971, #972, and #973.
- #975 independently reproduces after #973 and #974.
- #976 updates scientific and public documentation after #974 and #975.

All children declare SEM-232 and are trace-linked to it. Scientific
completeness remains blocked until a positive result has been independently
reproduced.
