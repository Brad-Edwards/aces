# Schemas

`contracts/schemas/` publishes versioned JSON Schema documents for
language-neutral ACES external contracts.

This directory is now the contract bucket in the repo layout. It is intended to
be the home of the authoritative machine-readable artifacts, independent of any
single implementation language or package layout.

Current published schemas cover:
- SDL authoring input
- instantiated scenarios
- backend manifests (`v1` legacy plus shared-apparatus `v2`)
- processor manifests (`v1` legacy plus shared-apparatus `v2`)
- concept-authority catalogs
- reference model catalogs
- UCO alignment evidence
- controlled vocabulary catalogs
- semantic profiles
- live-execution snapshots
- workflow result envelopes
- workflow history streams
- evaluation result envelopes
- evaluation history streams
- operation receipts and statuses
- control-plane participant status/history/context views, including SEM-214
  context-view meaning and comparability semantics
- experiment-core task, run, apparatus-context, study/collection, capture
  specification, raw evidence, and derived measure contracts

Current filenames still use `runtime` for some live-execution artifacts. That
naming is preserved for compatibility while the repository migrates toward the
processor/runtime boundary described in
[ADR-008](../../docs/decisions/adrs/adr-008-processor-layer-and-execution-artifact-boundaries.md).

For apparatus manifests, `v2` is now the authoritative shared envelope:

- `identity`
- `supported_contract_versions`
- `compatibility`
- `realization_support`
- `constraints`
- `capabilities`

These sections are intended to be concrete declarations, not placeholders. In
particular:

- `supported_contract_versions` must declare at least one contract
- `compatibility` must declare at least one compatible apparatus surface
- `realization_support` entries must declare non-empty disclosure kinds and at
  least one exact or constraint support kind
- processor capability blocks must declare non-empty SDL and feature support
- backend capability blocks must declare concrete provisioning and orchestration
  surfaces rather than empty shells

`v1` backend and processor manifests remain checked in as deprecated legacy
schema artifacts. The reference stack, contract tests, and conformance profiles
use `v2`.

## Concept Authority Catalog

The `concept-families-v1` schema publishes the machine-readable shared concept
authority catalog. Catalog entries distinguish adopted, adapted, and
ACES-native concept families.

Adopted and adapted families must declare `authority` and
`authority_reference`. Native families must not declare those authority fields;
instead they must declare non-empty `extension_scope`, `relation_rules`, and
`non_ambiguity_constraints`. This keeps ACES experiment, runtime, apparatus,
provenance, and governance concepts explicit without letting them silently fork
shared cyber-domain concepts.

## UCO Alignment Evidence

The `uco-alignment-v1` schema publishes the machine-readable UCO alignment
evidence catalog. It pins the reviewed UCO version and maps each adopted and
adapted cyber-domain concept family (from `concept-families-v1`) to the UCO
object types it aligns to, enumerating adapted-family divergences explicitly.

The catalog lives at `contracts/concept-authority/uco-alignment-v1.json`.
Coverage is catalog-derived: every adopted or adapted family whose authority is
UCO must have exactly one alignment entry. Validation uses local evidence only
and does not fetch the UCO ontology; semantic checks beyond JSON Schema enforce
coverage, provenance agreement with `concept-families-v1`, canonical UCO IRIs,
and the adapted-family divergence rule.

## Semantic Profiles

The `semantic-profile-v1` schema publishes shared semantic profile documents.
Each profile declares the compatible concept, contract, and behavior
assumptions required across authoring, exchange, processing, and execution
phases.

The initial profile lives at `contracts/profiles/semantic/reference-stack-v1.json`.
Its processing and execution phases also declare required concept bindings for
the governed apparatus-manifest vocabulary surfaces introduced by GOV-918.

## Shared Reference Models

The `reference-models-v1` schema publishes shared reference model catalogs.
Each catalog entry binds a recurrent object model to an authoritative concept
family and to published contract schema definitions plus governed instance
paths.

The initial catalog lives at
`contracts/concept-authority/reference-models-v1.json`. It anchors the current
recurrent SDL object slice for nodes, accounts, relationships, conditions,
events, and content to the shared concept-authority layer.

## Controlled Vocabularies And Enumerations

The `controlled-vocabularies-v1` schema publishes controlled-vocabulary
catalogs for stable portable term sets.

The initial catalog lives at
`contracts/concept-authority/controlled-vocabularies-v1.json`. It defines:

- closed portable enumerations for processor features, workflow features,
  workflow state-predicate features, realization support modes, and concept
  provenance categories
- governed-extension vocabularies for apparatus-manifest capability surfaces
  that need stable shared base terms plus disciplined extension space

For governed apparatus-manifest capability fields, contract validation and
runtime validation both treat the catalog as normative. Values must either be
declared terms or valid governed extensions; closed enumerations reject
extensions.

## Cross-Artifact Concept Binding

Apparatus manifests (`v2`) require a `concept_bindings` section that binds
vocabulary fields to canonical concept families from the concept-authority
catalog. Each binding entry declares:

- `scope`: a dot-delimited field path identifying the bound vocabulary surface
  (e.g. `capabilities.provisioner.supported_node_types`)
- `family`: a concept family identifier from the authoritative catalog
  (e.g. `assets`, `identities`, `tools-and-artifacts`)

This is the "artifact binding layer" described in ADR-012. It prevents
artifact-local strings from becoming de facto semantics by explicitly declaring
which concept family each vocabulary surface belongs to.

The field is required with at least one binding entry. Duplicate scopes within a
single manifest are rejected. Family identifiers must resolve against the
authoritative `concept-families-v1` catalog, and scope paths must resolve to a
governed vocabulary field that is actually declared in the manifest.

Generation or sync helpers may exist under `tools/`, but those helpers are
supporting repo machinery, not the authority boundary.

## Experiment Core

The `experiment-core` schema family publishes:

- `experiment-task-v1`
- `experiment-apparatus-context-v1`
- `experiment-run-v1`
- `experiment-study-v1`
- `experiment-capture-spec-v1`
- `experiment-evidence-record-v1`
- `experiment-derived-measure-v1`

These schemas keep SDL scenario authoring, experiment task protocol, execution
apparatus context, archival run provenance, study/collection analysis,
declarative capture requirements, raw evidence records, and derived
measure/evaluation outputs separate. The normative invariant set lives in
`specs/formal/experiment-core/`. ADR-055 records the original task/run/study
boundary, and ADR-064 records the evidence/measure and backend observation
capability extension. ADR-065 records `experiment-run-v1` as the canonical run
provenance record with required traceability links and realized-form
disclosures.

Schema-expressible invariants are encoded in the published schemas. In
particular, task/run reference-kind constraints and invalidated-run
requirements are part of `experiment-task-v1` and `experiment-run-v1`, while
identifier uniqueness for metrics, apparatus components, result summaries,
study members, and study factors is represented with keyed object maps.
Run traceability and realized-form disclosure invariants keep claims grounded
in evidence/derived-measure refs and keep realized choices distinct from
authored scenario meaning and result values.
Cross-artifact or graph invariants that standard JSON Schema cannot express are
published under the ACES semantic-invariant profile with `x-aces-invariants`
entries that name the validator and input contract paths. The generated schemas
declare draft 2020-12 identity, and the annotation profile shape is published as
`aces-semantic-invariants-v1` and checked during generation. Generic JSON Schema
validation remains structural; consumers of experiment-core records must apply
the named semantic validators before accepting records as ACES-conformant.

The optional backend-manifest `capabilities.observation` block declares EXP-715
observation/evidence collection support. Backends that declare it must also
declare the published capture-spec, evidence-record, and derived-measure
contracts that make the claim inspectable.
