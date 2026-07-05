# ADR-071: Validation and Admission Profiles

## Status

proposed

## Date

2026-07-05

## Classification

Classification: FM2
Required artifacts: ADR, formal spec, preflight guardrails, clause matrix,
changelog fragment
Waivers: No schema, fixture, contract-source, runtime behavior, API,
persistence, or conformance-runner artifact is introduced by issue #97. The
executable carrier and validator work for ASR-511 and ASR-515 is owned by the
spawned implementation issues #258 and #259.

## Context

ACES already has several validation and admission surfaces:

- SDL parsing and closed-world model validation;
- SDL semantic validation, reference resolution, instantiation, compilation,
  and planning;
- experiment-core task, run, study, evidence, derived-measure, traceability,
  realized-form, and augmentation validation;
- backend profile and conformance checks;
- participant action admission and runtime diagnostics; and
- claim evidence and falsification status.

Those surfaces do not all make the same kind of validity claim. A JSON Schema
pass is a structural claim. A semantic validator pass is a stronger domain
claim. A backend conformance or runtime admission result is a behavioral claim
over a concrete implementation path. A replay or maturity claim needs preserved
evidence, limitations, and a falsification status. Without a shared taxonomy,
consumers can over-read a weak signal as a strong validation result.

ASR-511 requires the ecosystem to define layered validation and admission
profiles that distinguish structural, semantic, behavioral, and stronger
validity claims. ASR-515 requires ACES to preserve and expose the profile,
strength, and limitations of the basis used for scenarios, tasks, runs,
studies, and related claims. These requirements have to be designed together:
the disclosure shape depends on the profile taxonomy, and the taxonomy is not
useful unless it can be named on concrete artifacts.

The preflight guardrails for this issue are recorded in
`docs/decisions/issue-97-asr-511-515-validation-strength-disclosure-preflight.md`.

## Decision

Adopt a shared validation/admission profile model and a validation-basis
disclosure discipline.

### 1. Profiles name the kind and strength of a validation basis

ACES validation/admission profiles use an ordered strength vocabulary:

- `structural`: syntax, schema, closed-world shape, type, and vocabulary checks.
- `semantic`: structural validation plus ACES domain invariants, reference
  resolution, lifecycle separation, and cross-artifact consistency checks.
- `behavioral`: semantic validation plus a concrete processor, backend,
  conformance, runtime, or admission path that exercised the relevant behavior
  and returned governed diagnostics.
- `evidence_backed`: semantic or behavioral validation plus preserved evidence,
  provenance, diagnostics, and limitations sufficient to review the claim.
- `falsification_backed`: evidence-backed validation plus an explicit
  falsification protocol and evidence status as defined by ADR-021.

The ordering is a disclosure rule, not a proof rule. A stronger label is valid
only when the disclosure names the gates that actually ran and the evidence or
diagnostics that support them.

### 2. Profile definition is separate from profile use

ASR-511 owns the governed profile taxonomy: profile ids, versions, strength
classes, gate kinds, and limitation categories.

ASR-515 owns per-artifact validation-basis disclosures. A disclosure states
which profile was applied to a particular subject, what strength was achieved,
which gates ran, which gates did not run or did not apply, what evidence and
diagnostics exist, and what limitations qualify the result.

Consumers must not infer profile strength from schema presence, successful
Pydantic validation, passing fixtures, private runtime flags, or prose that
does not carry a basis record.

### 3. Basis disclosures are reusable across existing carriers

The reusable semantic unit is a validation-basis disclosure, not a new
scenario/task/run/study super-model. The same disclosure discipline applies at
existing authority points:

- SDL scenario or scenario snapshot validation;
- experiment task protocol and apparatus support;
- experiment run provenance, evidence, traceability, realized-form, and
  augmentation support;
- experiment study allocation, analysis, replication, and comparison support;
- backend or participant conformance claims; and
- published claim or report artifacts.

Each carrier can bind the disclosure by embedding the shape or by referencing a
published disclosure artifact, but it must preserve the same semantics:
subject, profile, strength, gate results, evidence, diagnostics, and
limitations.

### 4. Admission-basis disclosure is not participant action admission

Artifact admission and validation-basis disclosure remain distinct from
participant action admission.

Participant action admission is already scoped by ADR-054 and ADR-060 through
`ParticipantActionAdmissionRequest`, participant lifecycle events, and
`admission_disposition`. ASR-511/ASR-515 must not overload that field with
scenario, task, run, study, or claim validation results.

### 5. Weak, partial, absent, and redacted basis must be explicit

A disclosure must expose weaker outcomes rather than hiding them by omission.
Required gate results use explicit statuses such as `passed`, `failed`,
`partial`, `not_run`, `not_applicable`, `unknown`, `unsupported`, or
`withheld`.

Redaction and withheld evidence qualify the exposed strength unless a governed
proof, attestation, digest, or diagnostic reference remains available for
review. A public view can be weaker than an internal view; the disclosure must
name the publication scope or audience when that matters.

### 6. Governed vocabularies carry portable terms

Portable profile ids, strength classes, gate kinds, limitation categories, and
subject kinds are governed vocabulary terms. Backend-specific or
processor-specific terms use the existing `x-<owner>:<term>` extension
discipline and cannot replace the ACES portable terms.

This decision does not introduce a second schema registry, validator stack,
claim graph, evidence store, admission service, profile loader, or persistence
surface.

## Required Boundaries

- Structural validity is not semantic validity.
- Semantic validity is not behavioral validation.
- Behavioral validation is not evidence-backed or falsification-backed support
  unless the evidence chain and limitations are preserved.
- Validation profiles are not semantic profiles, backend profiles,
  instantiation profiles, SEM-218 realization support, API-407 feature support,
  or participant action admission dispositions.
- Private flags such as an in-memory semantic-validation boolean are not
  portable disclosure records.
- Runtime snapshots, operation details, audit blobs, backend logs, tags, and
  free-form metadata are not sufficient carriers for validation strength.
- Secrets, hidden answers, prompts, raw evidence payloads, process argv,
  environment dumps, backend-native object representations, and full tracebacks
  must not appear in disclosures, examples, fixtures, diagnostics, logs, or
  public API responses.

## Implementation Mapping

Issue #97 is satisfied by this ADR, the formal specification in
`specs/formal/validation-admission-profiles/README.md`, the preflight
guardrail note, and the ASR-511/ASR-515 clause matrix in
`docs/research/validation-admission-profiles/traceability-matrix-asr-511-515.md`.

Executable carriers, fixtures, validators, conformance probes, API behavior,
or persistence changes remain owned by #258 and #259.

## Consequences

### Positive

- ACES gains one vocabulary for explaining whether a validation claim is only
  structural, semantic, behavioral, evidence-backed, or falsification-backed.
- Consumers can inspect which gate produced a claim and what limits it.
- Existing scenario, experiment-core, participant-runtime, conformance, and
  claim-evidence surfaces remain authoritative instead of being replaced by a
  parallel graph.

### Negative / Costs

- Future executable work has to carry basis records, not only boolean
  validation outcomes.
- Public disclosures may look more cautious because withheld evidence or
  not-run gates must reduce or qualify the exposed claim.

### Risks

- Implementers may continue to use generic `profile` fields. The formal spec
  requires terms to identify which profile family they belong to.
- Validation-basis records could become verbose. Carrier implementations should
  allow references to published evidence, diagnostics, and disclosure artifacts
  rather than forcing large payloads inline.
- A backend or processor could overstate strength by omitting weak gates. The
  disclosure invariant requires every required gate to be represented with an
  explicit status.

## Alternatives Considered

### Treat schema validity as the validation profile

Rejected. Schema validity is a structural floor. It cannot express semantic
reference resolution, behavioral conformance, preserved evidence, redaction
limits, or falsification status.

### Add a generic validation report graph

Rejected. Existing carriers already own scenario, task, run, study, evidence,
traceability, and claim-support facts. A parallel graph would split authority
and make consumers reconcile two provenance systems.

### Reuse participant action admission fields

Rejected. Participant action admission answers whether one participant action
attempt may proceed. ASR-511/ASR-515 cover validation and admission basis for
artifacts and claims across scenario, experiment, conformance, and evidence
surfaces.

### Leave strength as prose

Rejected. Prose cannot support portable comparison or downstream validation.
The profile, strength, gate, limitation, and subject terms need governed
identifiers.
