# Issue 1108 / ASR-530 Operation-Bounded Solver

Date: 2026-08-11

Issue: #1108. Requirement: ASR-530. Related: #1114 and closed issue #826.

## Decision

One satisfiability analysis builds one deterministic incremental QF_LIA solver
session. Each normalized clause is encoded once behind a Boolean assumption.
The initial decision, canonical witness probes, and sorted-deletion core probes
select clauses and fixed domain indices through assumptions; they do not rebuild
the variable and expression graph.

A monotonic 5000 ms operation deadline starts before solver construction and
covers expression construction, every Z3 call, and deterministic result
selection. Each check receives the remaining operation time, rounded up to a
positive millisecond and capped at the governed timeout. A result that returns
after the deadline is an operational failure, never SAT or UNSAT evidence.
The existing derived check-count budget remains an independent cardinality
bound.

## Compatibility and Nonclaims

The normalized theory, solver package/logic/options, initial decision, canonical
lexicographic witness order, sorted-deletion subset-minimal core order, evidence
schema, and replay digest remain unchanged. The configuration field
`timeout_ms=5000` now honestly bounds the whole solver operation rather than
each individual check. This is an in-process resource bound; it is not a claim
of hard process isolation against a compromised native Z3 library.

## Verification

Differential property tests compare complete SAT assignments and UNSAT cores
with the incumbent rebuilding algorithm over generated bounded models. Tests
count one solver construction, force expiry during construction, before a
check, inside repeated selection, and immediately after a nominal Z3 result,
and verify that no partial evidence crosses the service boundary. A high-check
shape guards against renewed per-check graph construction.
