# Contracts

`contracts/` contains the machine-readable contract side of the repository.

The goal of this bucket is organizational clarity:

- `schemas/` contains published contract schemas
- `fixtures/` contains valid and invalid payload corpora for those contracts
- `profiles/` contains capability profile declarations
- `realization-envelopes/` contains configuration-bound backend realization
  declarations whose identity is carried through manifests, plans, and snapshots

`schema-publication-manifest.json` is the authoritative publication inventory
for the current machine-readable schema set. The contracts verification gate
checks that every entry points at `contracts/schemas/`, that every listed schema
exists, that every JSON Schema file under `contracts/schemas/` is listed, and
that every entry records its stability class and canonical content hash.

## Schema authority direction (ADR-009 §7)

The published schemas under `contracts/schemas/` are the **hand-governed
normative authority**. Changes to a contract originate as edits to the published
schema, reviewed against the SDL prose specification — not as a side-effect of
regenerating from a reference implementation. The Python `schema_bundle()` and
`tools/generate_contract_schemas.py` are the reference implementation's output;
`tools/check_generated_schemas.py` runs that generation into a throwaway
directory and **proves the reference implementation still matches the published
normative schemas** (it never overwrites them). A schema change must record a
contract-facing change-ledger entry (`last_change`: summary + content hash) in
`schema-publication-manifest.json`; a schema **removal** must record a
`removed_schemas` tombstone (schema path + summary) in the same manifest.
`tools/check_schema_publication.py --base-rev` and the
`schema-change-missing-manifest` policy rule reject a `contracts/schemas/`
change — including a removal — that lands without one, so a schema cannot
change without contract-level review. This is the steady state ADR-009 §7 calls for;
optional code generation *from* the normative schemas into implementation
bindings remains future work.

Current checked-in schemas are marked `draft` in the manifest. A `v1` or `v2`
filename suffix identifies the schema lineage; it does not by itself promise a
stable compatibility surface. Stable schema evolution is governed by
[ADR-061](../docs/decisions/adrs/adr-061-published-schema-evolution-policy.md):
additive changes may stay under the same suffix, while breaking changes require
a new version suffix.

These assets are intentionally language-neutral. Any conformance runners or
implementation-specific validation helpers belong under `implementations/`,
not here.

At the architecture level, the contract space spans more than just backend I/O.
It includes:

- processor-facing contracts and manifests
- backend-facing contracts and manifests
- participant-implementation declaration surfaces
- live runtime/control-plane contracts
- experiment, evidence, and provenance artifact boundaries

The control-plane `participant-context-view-v1` contract includes the SEM-214
meaning and comparability envelope for derived operational context views:
participant-local scope, audience scope, observation point, governed source
layers, transformation rule, evidence/provenance basis, semantic limitations,
and explicit comparability disclosure.

The published experiment-core contract family includes task, run,
apparatus-context, study/collection, capture specification, raw evidence record,
and derived measure schemas under `contracts/schemas/experiment-core/`. These
contracts are archival design artifacts for scientific experiment records; they
do not add runtime execution, capture, storage, scheduling, statistical engines,
or API behavior by themselves.

`experiment-run-v1` is the canonical run provenance record. It carries the
task/run/apparatus context, result and evidence pointers, traceability links to
capture specs, evidence records, derived measures, and claims, plus
realized-form disclosures for underspecified concerns resolved during a run.

Within experiment-core contracts, identifier-bearing collections that require
uniqueness are object maps keyed by that identifier. This keeps uniqueness
portable in the published JSON Schemas rather than implementation-private.

Not every one of those surfaces is fully materialized in published schemas yet,
but they share the same language-neutral contract discipline.

This split follows the repository-structure decision captured in
[ADR-009](../docs/decisions/adrs/adr-009-normative-artifact-authority-and-repository-structure.md).

The canonical machine-readable manifest of the authority boundary
(ASR-517) lives at
[`specs/authority/authority-boundary.yaml`](../specs/authority/authority-boundary.yaml),
governed by
[ADR-019](../docs/decisions/adrs/adr-019-normative-authority-boundary-manifest.md)
and enforced by `tools/check_authority_boundary.py`.
The `provenance/` family contains revision-pinned SDL lineage, derivation, and
third-party notice dispositions governed by ADR-019 and ADR-079.
