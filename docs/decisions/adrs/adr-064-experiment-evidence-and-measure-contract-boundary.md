# ADR-064: Experiment Evidence and Measure Contract Boundary

## Status

accepted

## Date

2026-06-21

## Classification

Classification: FM1
Required artifacts: ADR, formal spec, schemas, fixtures, conformance tests
Waivers: none

Issue #88 publishes a contract boundary for EXP-707, EXP-708, EXP-709, and
EXP-715. The work adds declarative data contracts and backend capability
declarations; it does not implement runtime capture, storage, scheduling,
statistical analysis, or HTTP APIs. FM1 is appropriate because the decision
adds schema-governed external artifacts and semantic invariants, but no new
state-machine or solver behavior.

## Context

[ADR-055](adr-055-experiment-core-contract-boundary.md) established the
experiment-core family for tasks, runs, studies, and apparatus context. That
boundary intentionally left evidence capture and downstream measure publication
to follow-on work so the first experiment contracts would not blur protocol
intent, raw observations, and interpreted results.

Issue #88 fills that gap as a joint design issue for:

- EXP-707: declare what evidence an experiment intends to capture.
- EXP-708: publish raw captured observations and artifacts as evidence records.
- EXP-709: publish metrics, evaluations, summaries, and analysis outputs
  derived from raw evidence.
- EXP-715: let a backend declare its observation and evidence-collection
  capability without implying execution or evaluator semantics.

The spawned implementation issues remain responsible for actual capture,
retention, API, and processor/runtime behavior. This ADR records only the
schema-first contract split those issues must consume.

## Decision

Add three experiment-core contracts:

- `experiment-capture-spec-v1`: a declarative capture specification. It names
  the task/run/apparatus scope, capture windows, capture requirements, channels,
  media types, sensitivity, integrity requirements, retention policy, and loss
  disclosure expectations. It records what should be captured, not whether a
  backend captured it.
- `experiment-evidence-record-v1`: a raw evidence record. It binds a capture
  specification and requirement to a run, source references, capture time,
  capture window, raw content reference or bounded payload summary, sensitivity,
  redaction state, and provenance. It does not carry metric values or evaluation
  outcomes.
- `experiment-derived-measure-v1`: a derived measure or evaluation output. It
  binds a metric reference, derivation method, source evidence records,
  generation time, value status, reported value when present, uncertainty,
  limitations, and provenance. It cannot stand in for raw evidence.

Add an optional `capabilities.observation` block to `backend-manifest-v2` for
EXP-715. This block declares supported capture kinds, channel kinds, evidence
contracts, media types, sealing modes, redaction support, loss-disclosure
support, chain-of-custody support, and constraints. Its governed vocabularies
live in the concept-authority catalog under:

- `capabilities.observation.supported_capture_kinds`
- `capabilities.observation.supported_channel_kinds`
- `capabilities.observation.supported_sealing_modes`

A backend that declares `capabilities.observation` must also declare the
published experiment evidence contracts that make the claim falsifiable:
`experiment-capture-spec-v1`, `experiment-evidence-record-v1`, and
`experiment-derived-measure-v1`.

## Consequences

**Positive**

- Experiment evidence intent, raw observations, and derived measures now have
  separate closed-world artifacts, making provenance and interpretation chains
  reviewable.
- Backend manifests can advertise observation capability without overloading
  orchestrator, evaluator, or participant-runtime capability blocks.
- Conformance can reject observation capability claims that lack the published
  evidence contracts needed to inspect them.

**Negative / costs**

- Existing experiment schemas include the extended experiment reference
  vocabulary, so their published hashes change even though their primary
  contract shape remains intact.
- Backends that choose to claim observation capability must keep concept
  bindings, supported contract versions, fixtures, and conformance evidence in
  sync.

**Risks**

- Implementers may treat a capture specification as proof that capture occurred.
  The contract names and validators intentionally separate
  `capture-spec`, `evidence-record`, and `derived-measure` references to keep
  this distinction visible.
- A derived measure can be misread as raw evidence unless review tooling follows
  `source_evidence_refs`. The derived-measure contract therefore requires at
  least one evidence-record reference.

## Alternatives Considered

- **Embed capture requirements into `experiment-task-v1`.** Rejected: tasks
  already express protocol intent; capture plans evolve by apparatus and run,
  and forcing them into tasks would make task publication imply backend
  collection behavior.
- **Use run evidence artifacts for raw evidence and result summaries for
  measures.** Rejected: those fields remain useful summaries, but they are too
  coarse to publish capture requirement bindings, redaction/loss disclosure, and
  source-to-measure provenance as first-class artifacts.
- **Declare observation support only through evaluator capability.** Rejected:
  evidence collection can be backend, participant-runtime, network, or service
  mediated and is not identical to scoring or objective evaluation.
- **Implement capture storage and APIs in the same change.** Rejected: issue
  #88 is the contract-boundary decision. Runtime capture, storage, API, and
  processor behavior are intentionally left to the spawned implementation
  issues that can consume these contracts.
