# Participant Information-Flow And Control Implementation Program

Parent: [#794](https://github.com/OpenRAE/rae/issues/794)
Milestone: `Participant Information-Flow & Behavioral Equivalence`
Machine-readable gate: [`adoption-program.json`](adoption-program.json)

All program issues are assigned to the parent milestone. New requirement-backed
issues were created only after their DRAFT Ground Control requirements existed.
The existing issues were re-scoped with bounded outcomes, non-goals,
dependencies, acceptance criteria, and assurance evidence.

## Dependency graph

```text
#796 SEM-230 policy semantics
├── #251 ACT-617 mixed-control semantics
│   ├── #252 API-409 external-input/intervention contracts
│   │   ├── #255 RUN-310 supervisory lifecycle
│   │   └── #798 API-423 crossing contracts
│   └── #255 RUN-310 supervisory lifecycle
├── #294 SEM-219 affordances
│   └── #295 SEM-220 decision surfaces
│       └── #296 SEM-226 exposure enforcement
│           ├── #798 API-423 crossing contracts
│           └── #799 RUN-319 runtime enforcement
└── #797 DSL-142 participant-directed injects
    └── #798 API-423 crossing contracts

#798 API-423 crossing contracts
└── #801 API-407 backend capability declarations
    └── #799 RUN-319 runtime enforcement

#255 RUN-310 supervisory lifecycle ───────────┐
#296 SEM-226 exposure enforcement ────────────┼──> #799 RUN-319
#798 API-423 crossing contracts ──────────────┤
#801 API-407 backend capability declarations ─┘

#796 + #799 + #801 ──> #800 ASR-535 assurance/conformance
#799 + #800 ─────────> #802 migration
#800 + #802 ─────────> #803 documentation
```

The graph encodes semantic authority before contracts, contracts/capabilities
before runtime enforcement, runtime before conformance conclusions, and
evidence before migration/documentation claims. Sibling implementation may run
in parallel when every listed dependency has merged.

## Ordered delivery waves

### Wave 0 - semantic authority

| Issue | UID | Bounded outcome |
| --- | --- | --- |
| [#796](https://github.com/OpenRAE/rae/issues/796) | SEM-230 | Revisioned policy, labels, projections, IFC relation dimensions, and explicit nonclaims. |
| [#251](https://github.com/OpenRAE/rae/issues/251) | ACT-617 | Authored controller/authority state and mixed-control transitions. |

Wave 0 does not implement runtime mediation or claim proof. It fixes the
meaning that later artifacts implement.

### Wave 1 - authored participant surfaces

| Issue | UID | Bounded outcome |
| --- | --- | --- |
| [#294](https://github.com/OpenRAE/rae/issues/294) | SEM-219 | Governed tool/affordance bindings distinct from apparatus support. |
| [#295](https://github.com/OpenRAE/rae/issues/295) | SEM-220 | Participant-local decision-surface projection and selection meaning. |
| [#296](https://github.com/OpenRAE/rae/issues/296) | SEM-226 | Time-indexed exposure, withholding, declassification/redaction, transformation, and realized evidence. |
| [#797](https://github.com/OpenRAE/rae/issues/797) | DSL-142 | Participant-directed inject addressee/delivery semantics while preserving DSL-111 identity. |

Every issue reuses safe parsing, closed models, semantic validation,
instantiation, compiler addresses, concept authority, and schema publication.
Environment injects remain outside participant ingress.

### Wave 2 - portable contracts

| Issue | UID | Bounded outcome |
| --- | --- | --- |
| [#252](https://github.com/OpenRAE/rae/issues/252) | API-409 | External proposal, approval/denial, direction, intervention, handoff, override, and cancellation records. |
| [#798](https://github.com/OpenRAE/rae/issues/798) | API-423 | Common crossing policy-decision, transformation, disposition, evidence, and provenance refs. |

These issues compose API-406/ADR-054 carriers; they do not add a transport or
generic payload. Each published schema requires valid/invalid fixtures,
publication-ledger accounting, compatibility classification, generated-bundle
parity, and consumer tests.

### Wave 3 - capability and runtime realization

| Issue | UID | Bounded outcome |
| --- | --- | --- |
| [#801](https://github.com/OpenRAE/rae/issues/801) | API-407 | Governed backend feature support, strength, limitation, disclosure, and evidence. |
| [#255](https://github.com/OpenRAE/rae/issues/255) | RUN-310 | Secure, ordered, idempotent, append-only supervisory lifecycle. |
| [#799](https://github.com/OpenRAE/rae/issues/799) | RUN-319 | Deny-first reference-runtime crossing enforcement, persistence, audit, and evidence. |

Runtime work reuses `ParticipantControlMixin`, SEM-211 admission,
observation/projection incumbents, `RuntimeSnapshot`, `ControlPlaneStore`,
strict authentication/target binding, request bounds, idempotency/fingerprints,
bounded diagnostics, redacted unexpected errors, and `AuditEvent`.

Backend support is a declaration until realized and evidenced. Missing required
support rejects target selection/admission. Permitted downgrade removes the
stronger claim.

### Wave 4 - assurance and adversarial conformance

| Issue | UID | Bounded outcome |
| --- | --- | --- |
| [#800](https://github.com/OpenRAE/rae/issues/800) | ASR-535 | Negative leakage/declassification cases, exact relation bindings, bounded formal evidence, and adversarial backend conformance. |

This wave reuses `BackendConformanceReport`, existing fixture/target runners,
the behavioral-relation catalog, and `BehavioralClaimBindingModel`. Every
model-check/proof result states model, bound/quantifiers, tool/version,
assumptions, artifact digest, result/counterexample, and reproduction method.
Finite evidence retains finite scope.

### Wave 5 - migration and documentation

| Issue | UIDs | Bounded outcome |
| --- | --- | --- |
| [#802](https://github.com/OpenRAE/rae/issues/802) | SEM-230, API-423, RUN-319 | ADR-061 compatibility classification, staged adoption/rollback, and legacy fixtures without silent strengthening. |
| [#803](https://github.com/OpenRAE/rae/issues/803) | SEM-230, API-423, RUN-319 | Author, operator, backend, participant-implementation, and research guidance grounded in shipped authority/evidence. |

Legacy absence is legacy/unknown/unsupported according to the migration
profile; it is never evidence of exact policy enforcement or noninterference.
The scientific-completeness delivery assessment changes only from merged
evidence.

## Final child issue and requirement index

| Order | Issue | Requirement authority | Work class | Direct prerequisites |
| ---: | --- | --- | --- | --- |
| 1 | [#796](https://github.com/OpenRAE/rae/issues/796) | SEM-230 | semantic authority | #794 merged |
| 2 | [#251](https://github.com/OpenRAE/rae/issues/251) | ACT-617 | semantic authority | #796 |
| 3 | [#294](https://github.com/OpenRAE/rae/issues/294) | SEM-219 | SDL/semantic binding | #796 |
| 4 | [#295](https://github.com/OpenRAE/rae/issues/295) | SEM-220 | decision-surface contract/projection | #796, #294 |
| 5 | [#296](https://github.com/OpenRAE/rae/issues/296) | SEM-226 | exposure enforcement | #796, #295 |
| 6 | [#797](https://github.com/OpenRAE/rae/issues/797) | DSL-142 | participant-directed injects | #796 |
| 7 | [#252](https://github.com/OpenRAE/rae/issues/252) | API-409 | external-input/intervention contracts | #796, #251 |
| 8 | [#798](https://github.com/OpenRAE/rae/issues/798) | API-423 | crossing decision/evidence contracts | #796, #296, #252, #797 |
| 9 | [#255](https://github.com/OpenRAE/rae/issues/255) | RUN-310 | supervisory runtime | #251, #252 |
| 10 | [#801](https://github.com/OpenRAE/rae/issues/801) | API-407 | backend capability | #798 |
| 11 | [#799](https://github.com/OpenRAE/rae/issues/799) | RUN-319 | runtime enforcement/evidence | #798, #801, #255, #296 |
| 12 | [#800](https://github.com/OpenRAE/rae/issues/800) | ASR-535 | assurance/conformance | #796, #799, #801 |
| 13 | [#802](https://github.com/OpenRAE/rae/issues/802) | SEM-230, API-423, RUN-319 | migration | #799, #800 |
| 14 | [#803](https://github.com/OpenRAE/rae/issues/803) | SEM-230, API-423, RUN-319 | documentation | #802, #800 |

## Program-wide acceptance and evidence rules

Every child issue must:

- preserve its bounded outcome and explicit non-goals;
- use the listed Ground Control authority and reconcile IMPLEMENTS/TESTS links
  after merge;
- distinguish authored meaning, contract shape, reference implementation,
  backend declaration, backend realization, bounded conformance, formal
  evidence, and documentation;
- test fail-closed states, negative security cases, history/order/replay, and
  loss/weakening where applicable;
- avoid hidden payloads, secrets, policy bodies, backend objects, and unbounded
  diagnostic/error content;
- use exact relation/projection/quantifier/evidence bindings for every claim;
- update the participant section of `docs/explain/sdl/lineage.md` with the
  issue's adopted intellectual lineage, exact ACES artifact mappings, delivery
  status, evidence links, and explicit nonclaims. Update
  `contracts/provenance/sdl-lineage-ledger-v1.json` and its source audit only
  when normative derivation or compatibility claims change; and
- remain in milestone `Participant Information-Flow & Behavioral Equivalence`.

No child may report projected-history equality, passing fixtures, bounded
probes, schema validity, or capability declarations as universal
noninterference, trace inclusion, equivalence, simulation, refinement,
bisimulation, or runtime realization.

## Program completion condition

The adoption program is complete only when each child has merged, its governed
requirements and traceability reflect shipped artifacts, required backend
realization/conformance evidence exists, migration has run, documentation cites
the final authorities, and the scientific-completeness assessment is updated
without claim inflation. Closing #794 establishes the design and executable
program, not those future delivery states.
