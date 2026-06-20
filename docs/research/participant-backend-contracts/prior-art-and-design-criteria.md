# Prior Art And Design Criteria For The Participant Backend-Contract Surface

Issue #76 — API-405, API-406, API-407, API-408, API-411.

## 1. The Design Question

ADR-022 and ADR-054 define what participant actions, observations, state,
histories, interactions, and outcomes *mean*. Issue #76 must decide how those
objects travel as plain data between backends, the processor/runtime layer, and
consumers — and how a backend declares, without ambiguity, which parts of that
surface it supports. The contract surface fails if any of the following hold:

- a semantic object named by the requirement statements has no schema carrier
  (incompleteness);
- a carrier admits a reading the formal specs forbid (unsoundness);
- support claims are scalar or implicit where the runtime model is
  vector-valued and disclosure-based (overclaim);
- retrieval returns backend-local objects rather than the governed contracts
  (portability collapse).

## 2. Prior Art: How Adjacent Systems Serialize The Same Concepts

### 2.1 Action/observation interfaces (Gymnasium, PettingZoo, OpenSpiel)

Gymnasium serializes the agent boundary as typed spaces plus per-step tuples
(observation, reward, terminated, truncated, info); PettingZoo adds per-agent
keying and agent-set discipline; OpenSpiel serializes information states as
strings/tensors with explicit current-player, chance, and simultaneous-move
structure. Lessons for ACES:

- spaces/signals are *declared surfaces with identity*, not conventions —
  ACES carriers must reference governed space/contract ids, not infer shape;
- per-agent keying is mandatory in multi-participant data: every carrier keys
  by `participant_address` and `episode_id` (already the ADR-054 base-envelope
  rule);
- none of these ecosystems carries provenance, markings, capability honesty,
  or evidence linkage — exactly the gap ACES contracts add. They are interface
  precedent, not contract precedent.

### 2.2 Security event/object schemas (OCSF, STIX 2.1)

OCSF and STIX are the strongest plain-data precedents in the domain: explicit
schema versioning, registry-governed classification tuples, normalized status
with preserved source labels, raw-data integrity fields, granular markings,
and a governed extension policy. ADR-054 already adopts this pattern for the
runtime base envelope. Lesson: the #76 schema set inherits the base-envelope
discipline wholesale; no carrier may define its own ad hoc identity,
versioning, marking, or extension rules.

### 2.3 Command/playbook interchange (OpenC2, CACAO)

OpenC2 separates command/response with correlation ids and actuator profiles;
CACAO separates playbooks, steps, commands, agents/targets, and variables with
explicit success/failure routing. Lesson: cyber-action carriers preserve
source correlation identity and routing facts as references with declared
mapping loss — ADR-054's `CyberActionEnvelope` already fixes this shape; the
schema set publishes it rather than redesigning it.

### 2.4 Capability and conformance declaration (HLA, FMI, OGC, IETF)

Declared-capability precedent converges on the same finding from four
directions: HLA federates declare time-regulating/time-constrained roles and
services per the federation agreement; FMI publishes per-FMU capability flags
in a static model description; OGC services declare conformance classes;
IETF/IANA registries govern extension terms. Lessons:

- capability is declared per named term against a governed registry, never
  free text — API-405's governed vocabularies and `x-<owner>:<term>` extension
  rule follow this and stand;
- a boolean per term is the *floor*, not the model: FMI's experience (flags
  that proved too coarse and grew variants) supports ADR-054's move to
  per-concern guarantee strengths. API-407's unsupported/constrained/partial
  declarations should therefore reuse the ADR-054 guarantee-strength scale
  rather than inventing a third support vocabulary;
- conformance-class precedent (OGC) supports binding each declared term to
  evidence criteria — the API-405 term-level evidence table generalizes to
  API-407 constraints.

### 2.5 Retrieval surfaces (control planes, replay logs)

The repo's own control-plane contract (API-403/404, `runtime-snapshot-v1`,
result envelopes) is the governing retrieval precedent: durable store, DTO
parity with published contracts, idempotency and audit. External precedent
(OpenC2 query, HLA object reflection, ROS bag replay) adds one lesson ACES
must keep: retrieval is a *projection* of recorded contracts, never a second
source of truth. API-408 therefore defines retrieval shapes over the API-406
carriers — status, views, histories — and forbids retrieval-only fields that
do not exist in the recorded contracts.

### 2.6 Outcome reporting (benchmark harnesses, evaluator contracts)

Cybench/AutoPenBench-style harnesses reduce outcomes to task success plus
milestones; the repo's evaluator-results contract and SEM-215 forbid exactly
that collapse. Lesson: the API-411 carrier reports participant-local outcomes
as interpretation records — outcome source grounding, interpretation rule
refs, and explicit relationship references to scenario/workflow state — not
as scores. Reward/return remain step signals (ADR-054), not outcomes.

## 3. Formal Analysis: Required Carriers And Totality

The five requirement statements name concrete object families. Mapping each
to the normative object that defines it and the carrier that must exist:

| Requirement clause | Defining surface | Carrier obligation |
| --- | --- | --- |
| API-406 "actions" | ADR-054 lifecycle envelope; SEM-208/211 action contracts | participant action/lifecycle event contract |
| API-406 "observations" | ADR-054 observation envelope; SEM-210 boundaries | participant observation contract |
| API-406 "state snapshots" | `runtime-snapshot-v1` participant surfaces | ratified; extended for new envelope refs |
| API-406 "histories" | behavior/episode history event streams | ratified; event payloads bound to new contracts |
| API-406 "state-change reports" | ADR-054 shared-state record + access | shared-state record/access contract |
| API-405 roles/features | backend-manifest v2 `participant_runtime` | ratified as shipped (PR #405) |
| API-407 unsupported/constrained/partial | ADR-054 capability guarantee vectors; SEM-218 realization split | per-feature support declaration on the manifest block |
| API-408 status/views/histories | control-plane contract; SEM-214 (semantics deferred, wave 3) | retrieval projection contracts over API-406 carriers |
| API-411 outcomes + relationships | SEM-215 interpretation records | participant outcome report contract |

Totality check: every noun phrase in the five statements resolves to a row;
no row's carrier depends on an undefined semantic object. Two deferrals are
deliberate and must be stated in the ADR: (a) the *semantics* of derived
context views belong to SEM-214 (DRAFT, wave 3) — API-408 defines the carrier
and its provenance/marking discipline only; (b) operation records, step
signals, interaction contexts, joint actions, and time-management contexts are
ADR-054 surfaces whose carriers belong to the RUN-30x implementation issues —
API-406 must reference, not absorb, them.

Soundness obligations inherited from the formal specs (the carriers must make
these expressible and must not make their violation expressible as valid):

- closed vocabularies: lifecycle phase, phase realization, admission
  disposition, operation state, information guarantee, ordering basis,
  isolation guarantee, conflict policy, mapping loss, delivery basis,
  capability strength (runtime spec I16);
- base-envelope identity, three-timestamp, marking, and evidence-integrity
  rules (PRT-01..PRT-04);
- hidden-truth boundary: no carrier may put hidden state, scoring state, or
  centralized-training state in a participant-visible field (I2/SEM-210);
- capability honesty: support claims are per-term and per-concern with
  explicit downgrade values; missing is failure, not neutral (I14, I20, I21,
  and the capability-meet rules);
- outcome separation: local outcome, episode status, objective success,
  workflow state, evaluation result, and reward stay distinct (I10/SEM-215).

## 4. Design Criteria

The ADR and schema set must satisfy all of the following. Each criterion
cites its basis.

1. **One contract family, one base discipline.** All new carriers live in one
   `participant-runtime` contract family and embed the ADR-054 base-envelope
   fields and rules; no carrier invents local identity, versioning, marking,
   or extension semantics. (Basis: §2.2; ADR-009; PRT-01.)
2. **Serialize the spec, do not re-specify it.** Field meanings are defined by
   reference to `specs/formal/participant-semantics/` and
   `specs/formal/participant-runtime/`; the schema set adds requiredness,
   shape, and vocabulary bindings only. Divergence between spec vocabulary and
   schema enum values is a defect. (Basis: §3 soundness; PRT-19.)
3. **Ratify API-405; extend, never fork, for API-407.** The shipped
   `capabilities.participant_runtime` block is the API-405 surface. API-407
   adds per-feature support declarations on that same block using the ADR-054
   guarantee-strength scale (`unsupported`, `disclosed_weak`, `bounded`,
   `exact`) plus constraint disclosures; it does not introduce a second
   support vocabulary or a parallel manifest section. (Basis: §2.4; ADR-059
   amendment policy if ratification requires ADR-022/054 amendment.)
4. **API-407 is distinct from realization-support.** Feature-support
   declarations cover the participant-feature surface; SEM-218
   explicitness/realization declarations cover cross-domain realization
   handling. The manifest carries both without merging them, and the ADR
   states the boundary. (Basis: API-407 statement; SEM-218.)
5. **Retrieval is projection.** API-408 carriers are read-shapes over recorded
   API-406 contracts keyed by participant/episode/order-point, with visibility
   projection and marking enforcement applied before publication; they carry
   no retrieval-only state. Derived-context-view retrieval declares its view
   ref and provenance but defers view semantics to SEM-214. (Basis: §2.5;
   I11/I22.)
6. **Outcomes are interpretation records.** The API-411 carrier grounds every
   outcome in its sources (action result, episode terminal state, evidence
   refs), names its interpretation rule, and links scenario/workflow state by
   reference. No score, reward, or objective-success field appears on it.
   (Basis: §2.6; SEM-215; I10.)
7. **Evidence criteria per declared term.** Every declarable role/feature/
   support term binds to required evidence contracts, extending the API-405
   evidence-criteria table; conformance can falsify any declaration. (Basis:
   §2.4; ADR-021 falsification-first.)
8. **Governed extension only.** New roles, features, vocabularies, and
   support terms enter through the controlled-vocabulary authority with
   `x-<owner>:<term>` syntax for backend-specific terms. (Basis: ADR-012;
   API-405 precedent.)
9. **Versioned, generated, drift-gated.** Carriers are generated from contract
   models into `contracts/schemas/`, with schema names and versions following
   the existing family conventions and drift checked by the contract-schema
   parity gates. (Basis: ADR-009; repo plan rules.)
10. **Scope honesty.** The design issue publishes shapes; emission,
    validation, conformance checks, and tests belong to #200–#203, and the
    ADR says so. A carrier published here makes no claim that the runtime
    produces it yet. (Basis: issue #76 scope; PRT-19 traceability.)

## 5. Decision Sketch Carried Into The ADR

- New contract family `participant-runtime/` under `contracts/schemas/`:
  participant lifecycle/action events, observation envelopes, shared-state
  records and accesses, outcome reports, and the retrieval projections for
  status/views/histories.
- Backend-manifest v2 `participant_runtime` block ratified (API-405) and
  extended with `feature_support` entries (API-407): per governed feature
  term, a guarantee-strength support level, optional constraint refs, and
  required disclosure refs for anything below `exact`.
- Control-plane retrieval contracts (API-408) defined as projections of the
  recorded carriers; endpoint binding stays in the control-plane contract
  family.
- Outcome report contract (API-411) as a SEM-215 interpretation record with
  scenario/workflow relationship refs.
- All five requirements' carriers inherit the base envelope and closed
  vocabularies from ADR-054 as amended by the 2026-06 remediation (mapping
  loss, delivery basis, attribution/outcome refs).
