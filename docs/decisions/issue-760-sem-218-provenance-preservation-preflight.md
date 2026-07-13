# Issue 760 SEM-218 Provenance Preservation Preflight

Date: 2026-07-13

Issue: #760. Requirement: none; the issue is the delivery contract.

This note narrows the existing issue #491 SEM-218 runtime-realization preflight
to the provenance-loss defect. It records architecture guardrails only and does
not implement the compiler or runtime change.

## Decision

`ExplicitnessRecord.provenance` is the canonical origin classification at the
SDL-to-runtime boundary. The compiler must preserve that value on the existing
`CompiledRealizationRequirement`; the honoured branch of
`realization_disclosure()` must copy it to the existing
`RealizationProvenanceEntry`. Only a value selected by the backend because the
declared value was not honoured is `BACKEND_REALIZED`. The compiled field must
be required rather than defaulting to `AUTHOR_DECLARED`; a default would let a
future constructor silently recreate the same attribution bug.

This is an internal typed-carrier repair. It does not add a public field: the
published `runtime-snapshot-v1` schema, `RealizationProvenanceEntryModel`, and
control-plane snapshot serializer already admit and persist all three values.
Therefore the implementation must not version or regenerate the public schema,
add another provenance enum, or create a sidecar persistence channel.

The canonical classifier resolves the wording overlap in SEM-218 I5:
parameter substitution is `PROCESSOR_DERIVED`, whether the selected parameter
value came from a caller binding or an SDL default. `AUTHOR_DECLARED` is
reserved for a value that survives instantiation without substitution. This
follows `derive_instantiated_explicitness()` and the issue contract; runtime
code must not infer origin from equality, explicitness class, plan presence, or
backend success.

## Existing Boundaries To Reuse

- Classification and validation: `aces_sdl.explicitness`,
  `derive_instantiated_explicitness()`, and the closed SDL/Pydantic admission
  path remain the only origin authority.
- Compilation and planning: `_compile_realization_requirements()`,
  `RuntimeModel.realization_requirements`, `CompiledRealizationRequirement`,
  and `realization_support_diagnostics()` remain the single typed path. The
  added carrier is metadata and must not enter backend `resource_payload()`.
- Runtime enforcement: `realization_disclosure()` and
  `aces_runtime.backend_calls._call_backend_apply()` remain the fail-closed
  adapter boundary. Existing `runtime.backend-contract-invalid` diagnostics,
  rollback behavior, and snapshot acceptance order do not change.
- Observation and persistence: `RealizationProvenanceEntry`,
  `RuntimeSnapshot.realization_provenance`, `RealizationProvenanceEntryModel`,
  `RuntimeSnapshotEnvelopeModel`, `_snapshot_payload()`, and
  `_snapshot_from_payload()` remain the only disclosure and persistence path.
- Verification: extend the existing SEM-218 differential/compiler and runtime
  tests. The decisive case instantiates a realization concern through a
  parameter/default substitution, compiles it, has the backend honour it, and
  observes `PROCESSOR_DERIVED` in the runtime ledger.

## Cross-Cutting Guardrails

- Security and exposure: provenance is an enum label, not the realized value.
  Do not add authored or realized values to diagnostics, logs, audit details,
  fixtures, environment variables, process arguments, or error envelopes.
  No authentication, secret, configuration, subprocess, or OS interface is
  introduced by this repair.
- Validation: reuse enum typing at the dataclass and published Pydantic contract
  boundaries. Do not add duplicate string validation or a new exception type.
  Compiled-address validation in `CompiledRealizationRequirement.__post_init__`
  remains unchanged.
- Errors and observability: an invalid backend result still uses the existing
  structured `Diagnostic` path. Provenance preservation itself is not a new
  warning, metric, log event, or exception surface.
- Schema and compatibility: because `processor-derived` is already a valid
  published enum member, no schema-publication manifest entry, fixture-shape
  change, contract version bump, or downstream compatibility shim is required.
- Persistence: the existing control-plane round trip already serializes enum
  values. Do not introduce repository, database, migration, metadata-map, or
  generic-details storage for compiled provenance.

## Extension Seam

The seam is the provenance field on the existing compiled requirement, keyed
with the already parameterized `field_path`, `address`, `domain`, and
`requirement_kind`. Future realization concerns can flow through that carrier
and the existing concern-path/kind mappings. They must not require a
backend-specific provenance vocabulary or another runtime gate.

## Non-Goals And Anti-Patterns

- Do not change explicitness classification, parameter binding semantics,
  realization-support matching, exactness/non-approximation behavior, concern
  coverage, backend manifests, SDL syntax, or public contract shapes.
- Do not treat `PROCESSOR_DERIVED` as backend realization, or infer provenance
  from whether the backend honoured a value. Honouring answers whether the
  backend substituted; the compiled provenance answers where the honoured
  value originated.
- Do not reclassify SDL at runtime, inspect `record.variables` outside the
  classifier, use a boolean such as `authored`, or duplicate the three-value
  enum in processor/runtime packages.
- Do not place provenance in backend payloads, snapshot `metadata`, apply-result
  `details`, logs, or a private APTL-facing contract.
- Do not alter accepted ADRs. The existing SEM-218 authority and issue #491
  architecture are sufficient; this defect does not justify a new abstraction
  or ADR.
