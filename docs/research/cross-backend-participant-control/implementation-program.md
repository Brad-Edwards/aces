# Mixed Cross-Backend Participant-Control Implementation Program

Date: 2026-07-31

Parent issue: [#813](https://github.com/OpenRAE/rae/issues/813)

Participant milestone: `Participant Information-Flow & Behavioral Equivalence`

Backend coordination milestone: `Backend Contract & Conformance`

The machine-readable authority is
[`implementation-program.json`](implementation-program.json).

## Definition delivered by issue 813

Issue #813 delivers ADR-102, the edition-pinned primary-source assessment,
current-state gap analysis, SEM-234 composition profile, ASR-537 demonstration
protocol, two canonical DRAFT requirements, and the dependency-ordered
program.

It does not publish wire contracts, change trial admission or runtime
behavior, certify a backend, execute the demonstration, support multiple
acting controllers, or establish interoperability, transfer,
IFC/noninterference, trace inclusion, bisimulation, or backend equivalence.

## Dependency graph

```text
#1013 semantic authority
   |
   v
#1014 portable contracts
   | \
   |  v
   | #1015 trial admission
   |   |
   +---+----+
       |    |
       v    |
 #1016 runtime
       |    |
       +----+
         |
         v
 #1017 backend capability/conformance
         |
         v
 #1018 demonstration/evaluation
      \  |  /
       \ | /
        \|/
 #1019 documentation/claims
```

#1017 also depends directly on #1014. #1018 depends on #1015, #1016, and
#1017. #1019 depends on #1016, #1017, and #1018.

## Work packages

### #1013: Semantic authority

Publish the revisioned allocation, topology, authority, time, policy,
trial/phase, open/closed, loss, and failure invariants. Revision 1 retains one
acting controller.

### #1014: Portable composition contracts

Publish closed profile, allocation, edge, phase, time-mapping, loss, and
evidence bindings through existing contract families and schema governance.

### #1015: Trial admission

Deterministically compile and seal multiple components, allocation, topology,
clock/policy mappings, and finite phases. Preserve SDL neutrality, identity,
random streams, isolation, and cleanup.

### #1016: Runtime coordination

Resolve the exact controller/authority/policy/allocation/time cut, commit
before effect, dispatch only to the admitted provider, and append every
transition, weakening, and failure.

### #1017: Backend capability and conformance

Extend API-407 and existing conformance surfaces with mixed services and
runtime readback. This generic backend work is coordinated in milestone 61.

### #1018: Demonstration and evaluation

Run pure, mixed, staged, open/closed, and adversarial cases with complete
apparatus/provenance and independent reproduction.

### #1019: Documentation and claims

Only after runtime, backend, and evaluation evidence exists, reconcile
scientific completeness, assurance, lineage, related work, public guidance,
and residual gaps.

## Program invariants

- Both alternative and simultaneous mixed realization are first-class.
- Portable SDL remains backend-neutral.
- Allocation uses stable compiled refs and no implicit fallback.
- Every edge binds authority, mapping, policy, time/order, support, loss,
  failure, and evidence.
- Multiple providers do not become multiple controllers.
- HLA ownership, backend responsibility, action admission, and participant
  control remain separate.
- Routing and filtering do not authorize disclosure or establish IFC.
- Timestamps alone do not establish governed order.
- Inter-trial changes use new run identities; within-run changes are finite and
  pre-admitted.
- Control loop, world assumption, and federation membership are separate
  open/closed axes.
- Denied authority, policy, mapping, admission, and commit cases have zero
  prohibited effects.
- Conformance, readiness, transfer, trace inclusion, bisimulation,
  IFC/noninterference, and equivalence remain separate.
