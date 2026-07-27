# ADR-097: Scoped Participant Resource Budgets And Shared-Service Fairness

## Status

proposed

## Date

2026-07-27

## Classification

Classification: FM3

Required artifacts: authority-boundary decision, formal state and aggregation
invariants, closed authored and runtime contracts, semantic and instantiated
admission, canonical compilation, atomic backend-capacity admission, runtime
accounting and reset reconciliation, negative and race tests, cross-range
isolation probes, evidence-bearing conformance, lineage, migration, and
bidirectional issue/test/release traceability.

Waivers: none.

## Context

Issue #899 requires participant activity to be governed across action rate,
concurrency, storage growth, inference tokens, image generation, and
accelerator use. Limits can be owned by a participant, deployment tenant/range,
shared service, or fleet pool. Admission must protect evaluated participants
and range reliability when autonomous participants contend for shared
inference and accelerator capacity.

The repository already has adjacent authority:

- ADR-022 and the participant-semantics specification reserve participant
  budget and quota/exhaustion meaning for the participant semantic family.
- ADR-092 and
  `ParticipantBehaviorSpecification.autonomous_execution` own autonomous
  participant activity. V1 and v2 already carry finite attempt, occurrence,
  burst, retry, and in-flight limits.
- ADR-087 owns deployment-tenant identity, shared-service use, tenant
  isolation, mutable-state ownership, and reset-generation ownership. It
  explicitly does not make deployment cells cloud projects or quota
  boundaries.
- ADR-060 and `backend-manifest-v2.capabilities.participant_runtime` own
  participant-runtime capability and evidence claims.
- `participant-execution-binding-v1`,
  `participant-execution-service-state-v1`, planner capability admission, and
  the participant scheduler already own exact native bindings, bounded
  concurrency, generation fencing, and typed capacity/readback.
- ADR-054, ADR-066, `RuntimeSnapshot`, `ControlPlaneStore`, `Diagnostic`,
  operation status, audit events, and conformance reports own runtime state,
  durable evidence, public errors, and observability/evidence separation.

The current maxima express only policy-local counts and backend-declared
ceilings. They cannot express multi-resource accounting, aggregation,
configured shared-pool capacity, tenant isolation, fairness, reset
reconciliation, or measured throttling. Extending them as more unrelated
`max_*` fields would conflate authored demand, backend support, configured
capacity, current availability, and measured use.

Relevant precedent is deliberately used as design guidance, not as a wire
format:

- Kubernetes
  [ResourceQuota](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
  separates scoped quota from workload objects, while
  [API Priority and Fairness](https://kubernetes.io/docs/concepts/cluster-administration/flow-control/)
  separates priority classes, queues, and concurrency control.
- Kueue
  [ClusterQueues and cohorts](https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/)
  distinguish nominal quota, borrowing/lending, priority, and cohort-wide
  capacity.
- Dominant Resource Fairness
  ([Ghodsi et al., NSDI 2011](https://www.usenix.org/conference/nsdi11/dominant-resource-fairness-fair-allocation-multiple-resource-types))
  demonstrates why multi-resource fairness cannot be reduced to one scalar
  quota.
- The OCI runtime
  [Linux resource model](https://github.com/opencontainers/runtime-spec/blob/main/config-linux.md)
  and Kubernetes
  [Dynamic Resource Allocation](https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/)
  separate logical demand from host CPU, memory, device, and accelerator
  enforcement.
- OpenTelemetry's
  [metric guidance](https://opentelemetry.io/docs/specs/semconv/general/metrics/)
  and
  [GenAI token metric](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-metrics.md)
  reinforce explicit units, meter identity, and bounded-cardinality
  attributes. Telemetry remains an observation projection, not RAES policy or
  evidence authority.

## Decision

### 1. Extend participant semantics; do not create another actor or scheduler

Resource governance is part of ordinary participant execution and shared
service admission. Autonomous policies continue to compile and execute through
the ADR-092 participant scheduler, execution bindings, lifecycle control, and
backend protocol.

V1 and v2 autonomous profiles keep their existing meaning. A richer authored
profile must be versioned and reference governed resource-budget policy rather
than silently changing v2. Existing attempt, occurrence, retry, burst, and
in-flight fields compile into the same canonical budget demand used by the new
profile, with legacy provenance. There is one planner/runtime enforcement path,
not a legacy validator beside a new budget service.

The portable budget models are reusable by ordinary evaluated or
non-evaluated participants and shared services. They contain no provider,
product, model-vendor, or KeplerOps-specific field.

### 2. One contract family, with separate intent, capacity, and observation carriers

Adopt one versioned participant-resource-budget contract family with shared
identity, scope, resource-dimension, quantity, meter, reset, aggregation,
priority, and evidence value models. The family has distinct carriers:

1. **Budget policy/demand** records authored or admitted limits and resource
   demand.
2. **Configured pool capacity** records the configuration-bound capacity and
   isolation posture available from one logical backend/shared pool.
3. **Budget runtime state and events** use a canonical policy-scoped state
   identity and record logical reservations, use, throttling/rejection, reset
   reconciliation, and evidence.
4. **Physical-pool runtime state** is the single allocation authority for an
   exact owner/pool/resource/unit/accounting/meter identity across every
   admitted policy.

These carriers must not copy one another's authority. They join by exact
policy-scoped budget state, owner, canonical pool, generation,
contract-version, and digest identities.
Actual measurements never become manifest capability truth, and a manifest
declaration never becomes evidence that capacity was configured or realized.

The existing participant execution-service `capacity`, `reserved`, and
`in_flight` fields remain the service-local concurrency projection. When a
resource-budget state governs that concurrency, the service state references
the authoritative budget state and equality is validated. Two independently
mutable concurrency counters are forbidden.

### 3. Scope is typed ownership plus an explicit aggregation graph

Every budget and pool has one typed owner and stable owner reference. Initial
portable owner kinds are:

- participant;
- deployment tenant/range;
- shared service; and
- fleet.

Participant refs resolve to compiled participant addresses. Deployment-tenant
and shared-service refs reuse ADR-087 identities and exact
`uses_shared_service` bindings; budget ownership does not grant cross-tenant
access. Fleet refs are configuration-bound apparatus identities and are not
invented as SDL tenants or nodes.

Aggregation is a finite acyclic parent relation over resolved owners and pools.
Every child names at most one parent for a resource dimension. A child limit
does not expand its parent, unused capacity is not borrowable unless the
configured policy says so, and the same usage event cannot be counted twice
through aliases or multiple parents. Compilation canonicalizes owner and pool
refs before duplicate and cycle checks.

### 4. Resource dimensions are governed typed entries, not a generic quota map

Each dimension declares:

- a governed resource kind and unit;
- an accounting mode: windowed counter, cumulative counter, reservable gauge,
  growth counter, or lease;
- a governed meter/profile reference and measurement basis;
- finite bounds and, where applicable, window/clock and burst;
- reservation, commit, release, exhaustion, and reset behavior; and
- evidence and limitation requirements.

The initial kinds cover action rate, concurrent actions, storage growth,
inference token use, image generations, and accelerator allocation/time.
Inference tokens distinguish input, output, and billable accounting and name a
compatible tokenizer/meter profile; counts from incompatible profiles do not
aggregate. Image-generation and accelerator quantities likewise name a
portable meter/resource class rather than assuming every image or accelerator
unit has equal cost.

The extension seam is a governed resource-kind plus meter/profile entry.
Adding a future network, CPU, memory, or evidence-ingest dimension extends that
catalog and the accounting-mode conformance table; it does not add another
budget root, free-form unit, provider schema, or scheduler.

### 5. Admission is atomic across the complete scope and resource vector

Structural and semantic admission resolve all owners, pools, parent relations,
meters, clocks, reset owners, and shared-service isolation bindings.
Compilation emits one canonical demand vector and aggregation graph.

Planner admission compares the entire aggregated demand against:

- manifest-declared support and guarantee strength;
- configuration-bound pool capacity;
- current pool ownership and tenant-isolation capability;
- the required fairness/priority policy; and
- exact action-to-target execution bindings.

Admission fails before a plan is emitted if any dimension, ancestor scope,
isolation obligation, meter, reset behavior, or fairness guarantee is
unsupported. It is all-or-nothing: accepting concurrency while silently
dropping token or accelerator limits is invalid.

Admission aggregates every policy limit by canonical pool identity and rejects
aliases or aggregate overcommit before runtime. Runtime admission reserves the
complete vector against one authoritative pool ledger before native work.
Completion commits only an exact, bounded native measurement vector whose
operation, generation, resource, unit, meter, and evidence match the
reservation;
failure, cancellation, timeout, stale generation, and teardown release or
reconcile it exactly once. Backend success cannot bypass serialized RAES
accounting, and RAES accounting cannot claim that a backend enforced an OS or
service limit without backend evidence.

### 6. Fairness and priority are explicit obligations, not booleans

Fairness policy is independent of participant role, evaluation authority, and
resource ownership. A `green` role is not automatically low priority, and
evaluation authority does not by itself grant unlimited capacity.

Every contended shared pool declares a governed priority/fairness policy with:

- explicit protected evaluated-participant capacity or latency obligation;
- priority classes and tie-breaking basis;
- weighted share or other bounded allocation rule;
- borrowing, lending, reclaim, and preemption posture;
- queue and starvation bounds or an explicit unsupported disclosure; and
- evidence needed to falsify the claim.

Autonomous/background work may use only residual or explicitly lendable
capacity and must yield according to the admitted reclaim rule. A fairness,
latency, or starvation-free claim is invalid without bounded queue/deviation
evidence. Multi-resource fairness may use a governed weighted max-min/DRF-like
policy only when demand and capacity vectors are comparable under their meter
profiles; one scalar "cost" is not an acceptable substitute.

### 7. Backend manifests separate support, configuration, and realization

`backend-manifest-v2.capabilities.participant_runtime` remains the only
participant backend capability root. It is extended with:

- declared supported owner scopes, resource kinds, accounting/reset modes,
  fairness policies, isolation strengths, and evidence contract ids;
- configuration-bound logical pool capacities and a secret-free material
  configuration digest; and
- explicit contract/evidence identities promised for measured realization.

The existing `unsupported < disclosed_weak < bounded < exact` feature-support
scale remains the guarantee vocabulary. More `supports_*` booleans or unrelated
`max_*` fields are not added as the primary model.

Actual utilization, throttle decisions, latency deviations, and reconciliation
events remain typed runtime/evidence carriers in `RuntimeSnapshot`,
participant histories, operation results, and conformance reports. They are
not mutable samples embedded in a capability manifest or prose in
`constraints`.

### 8. Runtime accounting is append-only, generation-fenced, and reset-aware

The runtime snapshot gets first-class typed budget-state, physical-pool-state,
and event surfaces.
Budget data must not be stored in `RuntimeSnapshot.metadata`, generic
`details`, audit text, or backend-private dictionaries.

The accounting transition is reserve, admit/reject, commit/release, and
reconcile. Every transition carries canonical budget-state identity, owner,
pool, participant/episode
when applicable, execution generation, order point, resource quantity/meter,
disposition, predecessor, and evidence refs. Reservation and settlement are
idempotent under stable operation/action identity.

Episode reset does not reset a tenant, shared-service, or fleet counter.
Reset behavior names its clock, generation owner, and accounting owner.
Persistent storage growth remains until evidence-backed reclamation; token and
image windows reset only at their declared boundary; accelerator leases are
released or marked unreconciled. Coordinated reset drains or reconciles
outstanding reservations before advancing generation and appends evidence
instead of deleting prior use.

### 9. Reuse existing security, persistence, diagnostics, and observability gates

- SDL and contract payloads remain closed (`SDLModel` / `ContractModel`) and
  pass parser shape checks, semantic validation, instantiated-artifact
  admission, compiler diagnostics, planner admission, runtime snapshot
  validation, and conformance validation.
- Any control-plane mutation uses existing backend/operator authentication,
  target authorization, request-size bounds, idempotency, request
  fingerprints, atomic store transitions, and audit recording. Readback uses
  existing read authorization and applies tenant/audience markings before
  publication.
- Portable artifacts carry logical refs, units, counts, digests, markings,
  and evidence only. They never carry credentials, bearer tokens, prompts,
  generated images, model inputs/outputs, hidden truth, environment dumps,
  host paths, device nodes, backend-native ids, or raw tracebacks.
- Backend capacity configuration enters through a typed, closed
  configuration-bound manifest model. It is not accepted from unchecked
  `**config`, environment-variable-only parsing, free-form manifest
  `constraints`, or process argv. Secrets remain outside this capability.
- Public failures use existing `Diagnostic`, `ApplyResult`, operation status,
  and redacted HTTP error envelopes. No resource-budget exception hierarchy is
  introduced. Limit errors name safe logical ids, kinds, quantities, and
  dispositions, never private payloads or backend objects.
- `ControlPlaneStore` and its atomic local-store pattern remain the durable
  owner. Security audit records who attempted a control action; typed budget
  events and experiment evidence record resource behavior. Logs or
  OpenTelemetry may mirror those records but are not the evidence authority.
- Host enforcement is backend evidence. OCI/cgroup limits, accelerator device
  claims, service-side inference quotas, filesystem quotas, and tenant
  partitions must be validated against the selected backend's declared
  isolation strength. Portable success never follows from a process flag,
  environment value, device path, or provider response alone.

### 10. Publication, lineage, compatibility, and traceability are end-to-end

Contract models generate schemas through `schema_bundle()` and
`tools/generate_contract_schemas.py`; generated schemas are never edited by
hand. Publication entries, contract authority lists, controlled vocabularies,
concept bindings, fixtures, profiles, backend adapters, and schema
compatibility records advance together.

If an SDL authoring field is added, module composition, symbol/reference
rewriting, source/instantiated schema parity, semantic admission, examples,
agent guidance, and the exact bidirectional SDL lineage ledger are updated in
the same change. External precedent is recorded as semantic influence, not
code/schema derivation or compatibility.

Issue #899 has no formal Ground Control requirement. Do not invent one.
Traceability binds issue #899 to the ADR, normative clauses, implementation
surfaces, tests, conformance evidence, migration/release notes, and released
contract ids. Requirement reconciliation uses the repository's
requirement-free/orphan-link path.

## Consequences

### Positive

- Existing participant, tenant, shared-service, manifest, scheduler, runtime,
  persistence, diagnostic, and conformance authorities remain intact.
- Authored demand, configured capacity, current availability, measured use,
  and evidence cannot silently collapse into one number.
- New resource dimensions and backend pool types have governed extension
  seams without provider fields or parallel schedulers.
- Evaluated-participant protection and cross-range isolation become
  falsifiable contract obligations.

### Negative

- The contract family and runtime accounting state machine are larger than
  extending the existing `max_*` fields.
- Existing v1/v2 autonomous limit fields need canonical legacy projection and
  migration guidance.
- Backends cannot make exact capacity, fairness, isolation, or enforcement
  claims from manifest shape alone; they need configuration and measured
  evidence.

### Risks

- Ambiguous meters can make token, image, accelerator, or storage quantities
  appear comparable when they are not.
- A non-atomic multi-scope reservation can leak capacity or oversubscribe a
  parent pool.
- Participant reset can incorrectly erase tenant/fleet use or release
  still-active shared-service resources.
- High-cardinality participant/prompt/model attributes can leak information
  and exhaust telemetry systems.
- Strict priority without bounded reclaim and starvation evidence can protect
  evaluated work while making an unsupported fairness claim.

## Rejected Alternatives

- A second autonomous-activity scheduler or background-actor service.
- More unrelated optional `max_*` fields on SDL policies or backend manifests.
- A free-form `dict[str, number]` quota/capacity/usage map.
- Treating deployment cells as cloud projects, quota pools, or realized
  isolation.
- Inferring priority from participant color, evaluated status, or source
  order.
- One global fleet counter with no participant/range/shared-service ownership.
- Storing budget state in snapshot metadata, audit logs, telemetry labels, or
  backend-private objects.
- Treating declared support, configured capacity, current availability, and
  measured realization as interchangeable.
- Provider/model/device-specific portable fields or arbitrary policy
  callbacks.
- Resetting aggregate usage on participant episode reset or deleting history
  during reconciliation.

## Non-Goals

- Selecting a provider, inference product, model, tokenizer vendor,
  accelerator vendor/profile, cloud project, cluster scheduler, or storage
  implementation.
- Defining billing, currency, procurement, chargeback, or cost optimization.
- Proving model quality, human realism, throughput, latency, fairness,
  isolation, or OS enforcement from a declaration alone.
- Replacing deployment tenancy, shared-time, participant lifecycle,
  execution-binding, experiment apparatus, observability/evidence, or
  realization-envelope semantics.
- Exposing prompts, completions, images, hidden evaluator state, credentials,
  or backend-native resource identifiers.
- Making OpenTelemetry, Kubernetes, Kueue, OCI, or DRF a RAES wire format or
  mandatory backend implementation.
