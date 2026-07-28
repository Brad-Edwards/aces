# Scenario Variation And Trial Realization Invariants

Status: normative design invariant set

Classification: FM2 (semantic graph / constraint)

Requirements: SCE-002, SCE-006, SCE-007, DSL-101, DSL-103, EXP-706, EXP-718, EXP-719,
EXP-720, EXP-736, RUN-300, RUN-301

Decisions: ADR-084 and accepted ADR-070

## Scope

This specification constrains the path from a composed SDL scenario family to
an admitted trial plan, an instantiated scenario, and existing archival
experiment provenance. It fixes identity, phase ordering, selection,
random-stream, secrecy, admission, backend, scheduling, and late-binding
properties for follow-on implementations.

It is not an executable model. The SCE-002 family declarations are published in
the SDL authoring schema, and experiment selection policies are published in
the experiment authoring schema. The remaining executable contracts, compiler,
properties, and differential witnesses are tracked by #274 and #788 through
#791.

## Model

Let:

- `A` be a normalized authored scenario family;
- `C(A) = F` be trusted deterministic composition yielding an admitted expanded
  family `F`;
- `V(F)` be the finite map of stable variation-point identities to bounded
  domains and typed targets;
- `E` be an admitted experiment specification that references `F`;
- `Q(E)` be the finite set of unique logical trial coordinates required by its
  allocation/selection policies;
- `N(E)` be the explicit stable randomness namespace carried by the experiment's
  stochastic control, independent of the aggregate identity/digest of `E`;
- `M(q, v)` mean selection `v` is a member of all family domains and closed
  cross-point constraints for coordinate `q`;
- `B` be the selected apparatus manifests, capability declarations, and
  accepted realization-envelope evidence;
- `R_B(F, v)` mean the selected scenario is realizable under `B`;
- `G` be the exact compiler, identity, canonicalization, and random-stream
  profiles;
- `T(F, E, B, G) = P` be trial compilation and admission;
- `P[q]` be the immutable plan entry at logical coordinate `q`;
- `I(F, P[q]) = S_q` be public SDL selection/instantiation/admission yielding
  instantiated scenario `S_q`;
- `H` be authorized runtime facts and secret references;
- `L(S_q, H)` be late binding into explicitly compiled run-local sinks; and
- `Run(P[q])` be the archival experiment run produced if execution of entry
  `q` starts.

Every named transform is partial. Undefined means failure with bounded
diagnostics and no output artifact at the next boundary.

## Phase And Authority Invariants

### SVR-001 — Composition precedes selection

For every admitted plan:

```text
T(F, E, B, G) is defined => exists A such that C(A) = F
```

No policy, random draw, backend, scheduler, or runtime fact participates in
`C`. All imports, namespaces, locks, trust checks, and digests are resolved
before any variation point is selected.

### SVR-002 — Canonical symbols are selection-independent

For every declaration or variation point `x` and valid selections `v1` and
`v2`:

```text
canonical_id(x, v1) = canonical_id(x, v2) = canonical_id(x)
```

The id contains no selected value, source/cache path, run id, worker id,
backend id, or schedule position.

### SVR-003 — One authority per plane

SDL owns family domains and typed targets; experiment contracts own selection,
factors, allocation, and stochastic intent; the processor owns trial
compilation/admission and realization orchestration; runtime owns typed
late-bound facts; backends own realization within admitted envelopes;
schedulers own placement/isolation; experiment run/study contracts own archival
provenance. No artifact from one plane may be interpreted as authority for
another.

### SVR-004 — Closed phase progression

The only supported progression is:

```text
A -> F -> E-bound design -> P -> S_q -> compiled/planned forms
  -> run-local bindings/operations -> Run(P[q])
```

An operational artifact cannot move backward and edit an earlier artifact.
Every exchange artifact is closed for its phase.

## Family And Selection Invariants

### SVR-005 — Closed, bounded variation kinds

Every point belongs to the versioned closed set:

```text
{parameter, governed-reference, alternative, subset, order, logical-timing}
```

Every point has a finite member set or explicit bounded numeric interval plus a
selection/output budget. Unknown kinds, unbounded evaluation, external queries,
callbacks, templates, and arbitrary document patches are invalid.

### SVR-006 — Typed target ownership

Every point target is a closed descriptor admitted by the SDL model that owns
the target slot. No generic path language may authorize mutation. Selected
content must pass the owning value/fragment validator.

### SVR-007 — Independent branch validity

Each declared alternative/member is well-typed and semantically valid in its
declared local context. Requires/excludes/cardinality/precedence constraints
are closed finite relations. A contradictory or empty declared domain makes
the family invalid.

### SVR-008 — Selection membership

For every plan entry:

```text
q in Q(E) and P[q].selection = v => M(q, v)
```

The compiler cannot clamp, coerce, substitute, silently omit, or select an
undeclared value.

### SVR-009 — Whole-scenario admission

Local point validity is insufficient:

```text
P[q] exists => semantic_valid(I(F, P[q]))
```

Every selected combination is admitted as a whole concrete scenario. One
invalid combination prevents the requested plan from being emitted.

### SVR-010 — Experiment selection is separate from family validity

Changing an enumeration/sampling/allocation policy without changing `F` does
not change the family identity. Reusing a family in multiple experiments does
not copy its declarations into those experiment documents.

### SVR-011 — Scenario and backend membership are ordered

For every entry:

```text
P[q] exists => M(q, P[q].selection)
               and R_B(F, P[q].selection)
```

Backend realizability is checked after family membership. Backend feasibility
cannot widen, narrow, or choose the experiment selection.

## Random-Stream Invariants

### SVR-012 — Complete stochastic profile

Every stochastic selection names exact versions for generator, seed encoding,
semantic-address encoding, stream derivation, raw-bit interpretation,
distribution/sampling transformations, and failure behavior. A seed or library
default alone is not executable stochastic control. The experiment also carries
a canonical root seed and explicit randomness namespace; both are admitted
inputs rather than values inferred from the experiment document digest.

### SVR-013 — Semantic stream address

Every draw address is a pure canonical function of:

```text
(randomness namespace N(E),
 logical trial coordinate,
 policy id,
 variation-point id,
 draw purpose,
 stable local draw coordinate)
```

It contains no aggregate experiment id/digest, worker, process, thread, host,
wall-time, queue, batch, completion-order, retry, hash-order, or
backend-availability input. The exact experiment id/digest remains plan and run
provenance. Independent randomization requires an explicit namespace or seed
change.

### SVR-014 — Schedule independence

For any two execution schedules `s1` and `s2` over identical admitted inputs:

```text
bytes(T_s1(F, E, B, G)) = bytes(T_s2(F, E, B, G))
```

This includes serial/parallel, worker permutation, batch partition, completion
order, pre-seal retry, and supported cross-process/hash-seed variation.

### SVR-015 — Stream non-interference

If input `E'` retains `N(E)` and the root seed while adding or changing a draw
or unrelated metadata outside concern `c`, then every draw and selection at
addresses in unaffected concern `c` is unchanged. No mutable global stream is
shared across points, policies, or coordinates. This does not require plan
digests or run ids to survive an experiment-spec revision.

### SVR-016 — Canonical traversal preserves semantic order

Maps are traversed by canonical id. A semantically ordered SDL collection keeps
its declared or selected order. Serialization cannot sort away meaningful
order, and runtime scheduling cannot stand in for logical order.

### SVR-017 — Failure does not consume or replace randomness

Constraint exhaustion, invalid selection, apparatus rejection, worker failure,
timeout, retry, or cancellation does not advance a shared stream or trigger
resampling. The same address always denotes the same draw under the same
profile.

## Plan And Identity Invariants

### SVR-018 — Atomic plan admission

`T` returns exactly one fully admitted plan or one deterministic diagnostic set:

```text
T(F, E, B, G) = P
  iff for every q in Q(E), P[q] is valid and realizable
```

There is no partially admitted subset formed by dropping failed coordinates.

### SVR-019 — Unique stable logical coordinates

`Q(E)` contains no duplicate canonical coordinate. Coordinate identity is
experiment meaning, never list position or scheduler order.

### SVR-020 — Preallocated archival run identity

For each `q`, `P[q].run_id` is a deterministic function of admitted execution
intent and `q`. It is unique within `P`. If execution starts:

```text
Run(P[q]).run_id = P[q].run_id
```

No `experiment-trial-v1` or second archival trial identity is introduced.

### SVR-021 — Retry and re-execution differ

An idempotent pre-execution transport retry reuses `P[q].run_id`. A genuine
re-execution uses a new explicit replicate/execution ordinal, is admitted
again, receives a distinct run id, and may cite the source run by lineage.

### SVR-022 — Plan identity is not run identity

The plan is immutable grouped execution intent and has its own canonical
content identity. Scheduler jobs, operation ids, runtime snapshots, and plan
ids cannot be used as archival run ids.

### SVR-023 — Complete plan provenance

The plan commits to exact task/family/spec/artifact refs and digests, all
compiler/identity/RNG/canonicalization profiles, logical coordinates,
selections, factor assignments, non-secret bindings, selected apparatus
claims, and bounded admission evidence.

## Instantiation, Fact, And Secret Invariants

### SVR-024 — Public SDL instantiation only

`I(F, P[q])` applies only plan-recorded selections/bindings, performs no new
draw/import/query/secret read/backend callback, uses the public SDL
instantiation and admission path, and reruns whole-scenario semantic validation.
A private binder cannot mint an admitted `S_q`.

### SVR-025 — Selection provenance is snapshot identity

`S_q` carries family, plan, run, point-selection, binding, and existing
composition/instantiation provenance. Canonical snapshot identity includes that
provenance; serialization cannot discard it.

### SVR-026 — Late binding is monotone

`L(S_q, H)` may fill only a compiled declared sink after validating source,
type, scope, freshness, sensitivity, authorization, and evidence metadata. It
does not mutate `F`, `E`, `P`, `S_q`, or their identities.

### SVR-027 — Runtime facts are not selectors

No fact or observation may choose an alternative/subset/order/timing point,
change a scalar factor, alter topology, change a logical coordinate/run id,
select apparatus, or advance a random stream. Missing/invalid facts cause an
explicit runtime disposition, not fallback selection.

### SVR-028 — Secret non-disclosure and non-identity

Raw credentials and secret values are not factors, condition assignments,
random seeds, stream-address inputs, canonical ids/digests, portable plan
bindings, diagnostics, fixtures, argv, logs, or telemetry. Secret references
are resolved only at authorized run-local sinks, and secondary provenance is
redacted.

## Backend, Scheduler, And Archive Invariants

### SVR-029 — Envelope-governed realization

Every plan entry pins selected apparatus claims and passes manifest capability
and accepted ADR-070 realization-envelope membership/subsumption checks. A
backend may choose only a realized form permitted by that envelope and must
disclose the choice.

### SVR-030 — Backend refusal is observable failure

Availability change or refusal after admission yields failure/deviation
provenance. It cannot authorize another value, backend, omitted member, clamped
configuration, or resampled trial.

### SVR-031 — Scheduler opacity

Any two valid scheduler placements/orders for the same `P` observe identical
plan entries, run ids, selections, factors, snapshots, and streams. A scheduler
may control placement, isolation, bounded parallelism, timeouts, cancellation,
and cleanup only.

Portable cleanup intent, receipts, clean-state claims, retry safety, backend
capability, and bounded-parallelism proof are defined in
[cleanup-contracts.md](cleanup-contracts.md). Scheduler policy and worker
management remain outside these contract semantics.

### SVR-032 — Archival separation

The admitted plan is not stored as mutable runtime state, and live operation
records are not archival runs. `ExperimentRunModel` and `ExperimentStudyModel`
remain the authorities for actual execution context, evidence, factors,
allocation, deviations, and analysis lineage.

### SVR-033 — Adaptation is an intervention

Adaptive difficulty cannot rewrite the admitted baseline. An intervention is a
run event with policy/observation/trigger/action provenance. A derived follow-up
trial has a new admitted coordinate and run id linked to its source.

### SVR-034 — Generated content re-enters normal admission

ATT&CK layers, STIX, playbooks, PDDL/planners, CTI reports, and AI generators
may produce candidates only. Candidates pass ordinary authoring, trust,
composition, semantic validation, experiment binding, and trial admission.

## Compatibility Invariants

### SVR-035 — Static SDL is a singleton family

An existing SDL document with no variation points retains its identifiers and
meaning and denotes exactly one family member.

### SVR-036 — Existing variable binding remains authoritative

Existing `Variable` declarations and substitution semantics are reused for
scalar parameterization. Structural variation does not create a second string
template or binder. IP/address and typed path inputs use those variables under
their declared constraints. Credential-shaped inputs use governed secret
references or declared late-bound secret-reference sinks; raw credentials are
never portable selection values.

### SVR-037 — Existing experiment and archive artifacts remain distinct

Existing experiment authoring documents remain valid but descriptive
randomization text cannot execute without typed profiles. Existing task, run,
study, apparatus, evidence, and measure contracts retain their authority.

### SVR-038 — Campaign composition preserves canonical roots

An executable campaign composed from reusable SDL units is exactly one expanded
canonical `Scenario` produced by `C`; it is not a tree of independently running
scenario lifecycles. A campaign across multiple executions is represented by
an experiment design and admitted plan and is archived through the existing
run/study contracts. Neither form creates a `Campaign` runtime root or derives
meaning by concatenating mutable runtime state.

## Deterministic Failure Properties

For identical invalid inputs, diagnostic records are byte-equivalent after
canonical serialization. Diagnostics are ordered by stage, safe canonical
address/id, and code. They are bounded by explicit count/size budgets and never
render supplied values, complete domains, secret/fact refs, raw artifacts,
backend-private objects, environment data, or tracebacks.

At minimum, `T` is undefined for:

- invalid/untrusted composition or digest mismatch;
- unknown point/target/policy/profile;
- empty or contradictory domain;
- selection outside a domain or closed constraint;
- unbounded/exceeded product, trial, plan, or diagnostic budget;
- duplicate coordinate or derived run id;
- invalid selected whole scenario;
- unavailable/incompatible apparatus evidence;
- realization-envelope non-membership; and
- canonicalization or sealing failure.

## Claim Boundary

These invariants support claims of deterministic scenario-family selection,
schedule-independent admitted-plan construction, explicit instantiation
provenance, and bounded archival lineage. They do not establish behavioral
equivalence between backends, validity of an adaptive benchmark, continuing
artifact availability, truth of provenance claims, recreation of hidden
backend state, cryptographic unpredictability, or exact replay from a seed.

## Assurance Fulfillment

The invariant list is delivered by this file. Issue #786 supplies the bounded
family declaration contract and tests. Issue #787 supplies the closed
experiment selection-policy registry, exact allocation/factor joins,
family-context admission validator, canonical parser hardening, published
schema, positive/negative fixtures, and unit tests. It deliberately does not
compile logical trial coordinates or instantiate selected scenarios. Remaining
evidence is allocated as follows:

- unit-test evidence is waived to #789, #790, and #791;
- typed IR/contract evidence is waived to #274, #788, and #791; and
- property/differential evidence is waived to #274, #789, #790, and #791.

The dated waivers and paths are registered in
`specs/formal/assurance-fulfillment.yaml`. SCE-002 remains DRAFT until those
follow-on artifacts land.
