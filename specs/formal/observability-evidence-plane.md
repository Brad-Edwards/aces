# Observability and Evidence Plane Formal Design

This cross-domain formal design artifact supports ADR-066 and issue #127 for:

- `SEM-224` - Observability Plane Separation Semantics
- `SEM-225` - Realization Augmentation And Environment-Visibility Semantics
- `DSL-123` - Scenario-Native Observability And Telemetry Systems
- `DSL-124` - Authored Data And Evidence Requirements

It is design coverage. It defines the invariant set and source-to-contract-to-
test matrix that the spawned implementation issues must realize in SDL models,
semantic helpers, contract fields, fixtures, validators, and tests.

## FM Classification

Classification: FM2, Semantic Graph / Constraint.

Rationale:

- The design defines cross-artifact relationships between SDL authoring,
  participant-runtime visibility, experiment-core capture/evidence contracts,
  processor/backend apparatus telemetry, and derived analysis outputs.
- The key obligations are type separation, reference ownership, visibility
  projection, provenance links, loss/redaction disclosure, and comparability
  claims across artifacts.
- This artifact does not define a live state machine or runtime protocol.

## Plane Definitions

### Scenario-Native Observability

In-world observability systems authored as part of the scenario. They are
targetable only when represented by an SDL section, runtime family, or typed
relationship endpoint. Examples include network sensors, detection engines,
security monitoring managers, forwarding agents, telemetry collectors, tracing
services, dashboards, or metrics stores when the scenario makes them part of
the environment.

### Authored Evidence Requirement

An authoring obligation that names the data, evidence, output, source, scope,
window, channel, or boundary that must be captured. It may compile to or bind
with `experiment-capture-spec-v1`, but it is not captured evidence and is not a
participant objective.

### Processor/Backend Operational Observability

Apparatus data used to operate, audit, or diagnose processors and backends:
logs, traces, diagnostics, audit records, health checks, setup evidence,
measurement-channel facts, and capability declarations. These facts are not
scenario meaning unless explicitly projected into an SDL or runtime contract.

### Captured Evidence

Concrete evidence artifacts or `experiment-evidence-record-v1` records. They
cite the capture specification or authored requirement they satisfy and carry
source, capture time/window, raw content reference or bounded summary,
sensitivity, redaction state, provenance, and integrity metadata.

### Derived Analysis

Interpreted outputs over evidence: derived measures, result summaries, outcome
interpretations, studies, reports, exports, and claims. They must cite source
evidence and must not stand in for raw evidence.

## Augmentation Classification

An augmentation is processor/backend-added apparatus behavior or
instrumentation used to satisfy evidence, evaluation, operational, or
comparability needs. The classification set is additive:

| Classification | Meaning | Required carrier |
| --- | --- | --- |
| `apparatus_only` | Visible only to processor/backend/operator/control apparatus. | Diagnostic, manifest, apparatus context, audit, setup evidence, or other apparatus carrier. |
| `environment_visible` | Changes or adds realized environment behavior. | Runtime/evidence/provenance carrier plus realized-form or equivalent disclosure. |
| `participant_visible` | Can affect participant-visible information. | Participant visibility projection, observation envelope, marking, and redaction carrier. |
| `comparability_relevant` | Can affect run/backend/participant/condition comparison. | Run provenance, validity note, realized-form disclosure, or derived-analysis support record. |

## Invariants

| ID | Invariant | Enforcement target |
| --- | --- | --- |
| OE-01 | Every claim-bearing observability/evidence artifact has exactly one primary plane, even when it references artifacts in other planes. | Plane classifier over SDL, runtime, experiment, and apparatus carriers. |
| OE-02 | Scenario-native observability is targetable only through SDL authoring surfaces, runtime-family refs, or typed relationship endpoints. | SDL semantic validation and reference-resolution catalog. |
| OE-03 | Authored evidence requirements name source, scope, window or trigger, channel or boundary, sensitivity, integrity, and loss/redaction expectations before they can claim capture intent. | SDL evidence-requirement model and validator. |
| OE-04 | A capture requirement is not proof of capture. Satisfaction requires a captured evidence record or artifact with an explicit satisfaction link. | Experiment-core reference validation and traceability checks. |
| OE-05 | Captured evidence must not contain metric values, scores, evaluation decisions, or derived conclusions as raw evidence meaning. | Contract model validators and invalid fixtures. |
| OE-06 | Derived analysis must cite source evidence and must not reveal hidden adjudication assets without governed marking, redaction, and authorization. | Derived-measure/run/study validators and redaction checks. |
| OE-07 | Backend diagnostics, logs, traces, and audit records are apparatus operational observability until a governed projection maps them into another plane. | Runtime diagnostics and control-plane API gates. |
| OE-08 | Participant-visible observation claims must pass the ADR-022/ADR-054 visibility projection, marking, redaction, and information-guarantee rules. | Participant observation envelope and behavior-history validators. |
| OE-09 | Augmentation that is environment-visible, participant-visible, or comparability-relevant must have a first-class disclosure carrier. | Augmentation disclosure validator and provenance links. |
| OE-10 | Loss, redaction, latency, observer effects, weaker capability guarantees, and unsupported capture concerns are explicit when a claim depends on them. | SDL, experiment-core, and participant-runtime validators. |
| OE-11 | The same string value, such as `log`, `telemetry`, `observation`, or `evidence`, does not decide plane ownership by itself. | Concept/vocabulary binding plus carrier-type classifier. |
| OE-12 | No observability/evidence plane may use `RuntimeSnapshot.metadata`, evaluator detail fields, audit blobs, raw backend DTOs, or free-form tags as its only portable carrier. | Policy, semantic validation, and review gates. |

## Source-To-Contract-To-Test Matrix

| Requirement | Clause | Current design artifact | Future contract/helper | Lifecycle enforcement point | Positive fixture | Negative fixture | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SEM-224 | Distinguish scenario-native observability systems. | ADR-066; this spec; SDL catalog. | Plane classifier plus SDL runtime-family target helper. | SDL semantic validation and compiler address emission. | In-world detection engine referenced by participant action and capture requirement source. | Backend-only log treated as a participant-visible observation. | #334 |
| SEM-224 | Distinguish authored evidence requirements. | ADR-066; this spec; SDL catalog. | Authored evidence-requirement model and capture-spec binding helper. | SDL validation, instantiation revalidation, experiment capture binding. | Requirement names source, scope, window, channel, sensitivity, integrity, and loss disclosure. | Raw capture record treated as authored requirement satisfaction with no requirement ref. | #334, #337 |
| SEM-224 | Distinguish processor/backend operational observability. | ADR-066; this spec. | Apparatus observability classifier over diagnostics, manifests, audit, setup evidence, and measurement channels. | Processor/backend manifest and control-plane diagnostic gates. | Backend health trace cited as setup evidence with sensitivity metadata. | Backend trace projected into scenario meaning by free-form metadata. | #334 |
| SEM-224 | Distinguish captured evidence. | ADR-066; this spec; ADR-064. | Evidence satisfaction validator over capture spec, evidence record, artifact refs, and provenance. | Experiment-core contract validation and run traceability. | Evidence record cites capture spec, requirement, source, window, raw content, redaction state, and checksum. | Evidence record carries a derived score as raw evidence meaning. | #334 |
| SEM-224 | Distinguish derived analysis outputs. | ADR-066; this spec; ADR-065. | Derived-analysis source-evidence validator. | Derived-measure, run, study, and report validation. | Derived measure cites source evidence and method. | Hidden adjudication asset leaks through analysis output without marking/redaction. | #334 |
| SEM-225 | Define augmentation used to satisfy evidence, evaluation, or operational requirements. | ADR-066; this spec. | Augmentation disclosure model with concern, carrier, classification, evidence refs, and markings. | Compiler/runtime provenance and experiment run validation. | Apparatus-only packet capture sidecar disclosed as measurement-channel augmentation. | Instrumentation modifies environment but appears only in backend logs. | #335 |
| SEM-225 | Include environment-visible augmentation. | ADR-066; this spec. | Environment-visible augmentation validator. | Runtime/provenance validation. | Added sensor service has realized-form disclosure and scenario/runtime refs. | Environment behavior changes without disclosure. | #335 |
| SEM-225 | Include participant-visible augmentation. | ADR-066; this spec; ADR-054. | Participant-visible augmentation validator. | Participant observation envelope and visibility projection. | Participant sees monitoring dashboard through explicit projection. | Hidden adjudication asset reaches visible observation history. | #335 |
| SEM-225 | Include comparability-relevant augmentation. | ADR-066; this spec; ADR-065. | Comparability disclosure support record. | Run/study validity and derived-analysis validation. | Augmentation names comparison impact and supporting evidence refs. | Observer effect omitted from a benchmark comparison claim. | #335 |
| DSL-123 | Support scenario-native observability, telemetry, logging, tracing, and monitoring as first-class scenario elements. | ADR-066; SDL catalog. | Runtime-family or section model for product-neutral in-world service identity. | SDL parser, schema, semantic validator, and reference resolver. | Telemetry collector has stable id and typed refs. | Generic top-level `observability` bag accepts unrelated vendor payloads. | #336 |
| DSL-123 | Allow those elements to be depended on, interacted with, or targeted. | ADR-066; SDL catalog. | Typed relationship/reference edges and target helper. | SDL references, typed relationship subtypes, and compiler addresses. | Objective/action targets an in-world observability service. | Bare ambiguous ref resolves by first match. | #336 |
| DSL-124 | Support authored requirements for data/evidence/output capture. | ADR-066; SDL catalog. | Evidence-requirement model and capture-spec binding. | SDL parser, schema, semantic validator, instantiation, compiler. | Requirement names source, scope, window, channel, role, sensitivity, and loss disclosure. | Capture requirement has no source or window. | #337 |
| DSL-124 | Requirements come from declared sources, scopes, windows, or comparable boundaries. | ADR-066; SDL catalog. | Qualified source/scope/window resolver. | SDL semantic validation and experiment binding. | Requirement references runtime sensor and run window. | Requirement references an unknown hidden backend object. | #337 |
| DSL-124 | Requirements are independent of participant objectives. | ADR-066; SDL catalog. | Cross-plane validation between objectives and evidence requirements. | SDL semantic validation and compiler. | Evidence requirement exists without an objective. | Objective success criterion is treated as capture requirement by implication. | #337 |
| DSL-124 | Requirements are distinct from scenario-native observability systems. | ADR-066; SDL catalog. | Plane classifier and source binding helper. | SDL semantic validation. | Requirement cites an observability system as source but remains a separate obligation. | Observability system declaration is treated as proof of capture. | #337 |

## Negative Probe Set

The minimum adversarial fixture set for implementation is:

- backend logs treated as participant observations;
- raw capture treated as evidence-requirement satisfaction;
- hidden adjudication assets leaking through analysis;
- augmentation changing environment-visible behavior without disclosure;
- participant-visible augmentation without a visibility projection;
- comparability-relevant observer effects omitted from evidence claims;
- loss, redaction, or latency omitted from evidence claims;
- a generic observability bag accepting vendor payloads without typed refs;
- ambiguous evidence source refs accepted by first match; and
- derived measures accepted with no source evidence.

## Non-Goals

- This design does not add SDL syntax, schemas, fixtures, runtime services,
  APIs, storage, capture scheduling, telemetry collection, packet parsing,
  analysis engines, or backend adapters.
- This design does not replace ADR-022, ADR-054, ADR-064, ADR-065, SEM-218, or
  existing control-plane security and diagnostics.
- This design does not transition SEM-224, SEM-225, DSL-123, or DSL-124 to
  implementation coverage. It records the criteria the spawned issues must
  satisfy.
