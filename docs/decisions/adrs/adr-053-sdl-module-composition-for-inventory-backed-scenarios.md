# ADR-053: SDL Module Composition for Inventory-Backed Scenarios

## Status

accepted

## Date

2026-06-03

## Context

Inventory-backed SDL scenarios can become too large to review as one authored
YAML file. The TechVault inventory work exposed the problem directly: when
node-level inventory is embedded in one monolithic scenario, vocabulary
migrations, review comments, capture evidence, and mapping-ledger updates all
become harder to separate from unrelated scenario content.

The repository already has module/import implementation surfaces:

- `Scenario.module` and `Scenario.imports` in the SDL model
- disk-backed `parse_sdl_file(...)` expansion before semantic validation
- local, OCI, and locked import source classes
- `aces.lock.json` and `aces-trust.yaml`
- namespace rewriting in the composition layer
- CLI commands for resolving, verifying, and publishing modules
- tests for local, locked, OCI, digest, signature, cycle, and namespace behavior

What was missing was the durable architecture proposal that explains why this
shape is the right one, how it should handle large inventory fragments, which
tradeoffs comparable systems expose, and which gaps remain before fragment-level
inventory review is fully ergonomic.

## Decision

ACES SDL supports module composition as typed, deterministic scenario
composition, not as textual YAML inclusion.

The root SDL file remains the entry document passed to the parser. It may import
publishable SDL modules. Each imported module is parsed as SDL, structurally
validated as a scenario/module payload, optionally instantiated with explicit
parameters, namespace-rewritten, merged into the root payload, and then the
existing full-scenario semantic validator and compiler run against the expanded
canonical scenario.

This keeps compiler and runtime behavior stable: after composition, downstream
code sees a single canonical SDL scenario, not a tree of source files. Source
file layout is an authoring and audit concern; canonical identities, semantic
validation, compiled addresses, planning, and runtime contracts remain source
layout independent.

## Precedent Lessons

The design is informed by these systems, but ACES does not adopt any of them
wholesale.

| System | Relevant lesson for ACES |
| --- | --- |
| [Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/) | Composition should be declared through a manifest and should operate over typed resources. ACES should keep module imports explicit and deterministic rather than treating YAML text as the unit of reuse. |
| [Terraform modules](https://developer.hashicorp.com/terraform/language/modules/configuration) | Reusable units need stable input/output boundaries, versioning, and addresses that remain meaningful after composition. ACES mirrors this with module descriptors, parameters, exports, namespaces, and canonical compiled identities. |
| [OpenAPI multi-document descriptions](https://spec.openapis.org/oas/v3.1.1.html) | Multi-file descriptions need an entry document and explicit reference resolution rules. ACES keeps one root scenario as the entry point and expands imports before existing reference validation. |
| [JSON Schema `$ref`](https://json-schema.org/understanding-json-schema/structuring) | References need base identity, pointer semantics, and clear failure behavior. ACES should reject ambiguous or missing cross-module references rather than letting source-file locality decide meaning. |
| [CUE modules](https://cuelang.org/docs/reference/modules/) | Versioned modules and OCI distribution are useful, but ACES should not become a constraint language. ACES uses OCI packaging for SDL modules while keeping the SDL semantic model explicit. |
| [Dhall imports](https://docs.dhall-lang.org/tutorials/Language-Tour.html#installing-packages) | Integrity checks and cacheable resolved imports are strong supply-chain guardrails. ACES follows the same direction through digest pins, lock records, signature verification, and trust policy. |
| [Jsonnet imports](https://jsonnet.org/ref/spec.html) | Imported units should be parsed and checked as their own files before substitution. ACES parses imported SDL as SDL before composition instead of blindly pasting text. |
| [YAML anchors and aliases](https://yaml.org/spec/1.2.2/#3222-anchors-and-aliases) | YAML aliases are serialization-level reuse within a document. They do not provide typed cross-file module semantics, audit provenance, or ACES reference validation. |

## Composition Model

An SDL module is a publishable SDL unit with:

- `module.id` using canonical publisher/name form
- `module.version`
- optional `module.parameters`
- `module.exports` describing the section names and identifiers that are
  intentionally public
- optional `module.description`

An import declares:

- `source`, or deprecated backward-compatible `path`
- `namespace`
- requested `version`
- optional `parameters`
- optional `digest`

Supported source classes are:

- `local:...` for repository-local files
- `oci:...` for trusted registry modules
- `locked:...` for a previously resolved lockfile entry

The namespace is the author-facing disambiguator for imported symbols. Imported
private variables are retained through module-provenance side channels so the
runtime planner can still enforce allowed-values constraints after imported
variables are stripped from the merged payload.

## Validation Order

Composition must preserve this order:

1. Resolve the root file path and load repo-local trust and lock policy.
2. Parse YAML with safe SDL loading and normal key normalization.
3. Validate import declarations and module descriptors.
4. Resolve each import source through the module registry.
5. Verify version, digest, lockfile, export hash, and signature/trust policy.
6. Recursively expand imported modules while rejecting import cycles.
7. Instantiate imported modules with explicit import parameters.
8. Rewrite exported and private symbols into the import namespace.
9. Merge section maps while rejecting collisions.
10. Construct the expanded `Scenario` or `ExpandedScenario` model.
11. Run existing semantic validation across the whole composed scenario.
12. Compile, plan, and execute exactly as for a non-composed scenario.

This order is deliberately stricter than raw YAML inclusion. Fragment-local
syntax and module metadata fail before merge. Cross-fragment references fail
after the global symbol table exists. Compiler behavior does not depend on the
number or names of source files.

## Reference Resolution

Cross-fragment references resolve through canonical identities produced by
namespace rewriting. The composition layer must update every SDL reference
surface that can point at imported symbols, including:

- node feature, condition, inject, vulnerability, and role entity references
- infrastructure dependencies, links, and property target keys
- metrics, evaluations, TLOs, goals, events, scripts, stories, content,
  accounts, relationships, agents, objectives, and workflows
- qualified runtime references that participate in relationships, objectives,
  or generic reference validation

Duplicate canonical identities, missing exported targets, namespace collisions,
reserved private namespace use, import cycles, unresolved references, and
ambiguous references are hard errors.

Imported modules are not allowed to mutate arbitrary paths in the root
scenario. They contribute section entries through typed SDL sections and
published exports. This keeps module composition reviewable and avoids a
Kustomize-style overlay patch language for now.

## Diagnostics And Source Locations

Current parser and validator errors can point at the root SDL file, and module
resolution failures can name the imported file or source. That is sufficient for
correctness, but not yet sufficient for large inventory review.

Follow-on implementation should preserve source provenance for composed model
nodes:

- fragment file path
- line and column when available from the YAML loader
- module id and namespace
- SDL section and identifier
- composed scenario path
- original fragment-local path
- digest or lock record when the source is resolved through `oci:` or `locked:`

Diagnostics should report both the authoring location and the composed
canonical path. For example, if `relationships.misp-to-db.target` points at a
missing imported node, the error should name the relationship fragment location,
the reference value, the namespace context, and the expected canonical target
space.

The expanded scenario is an implementation artifact. It must not become the
only review surface for diagnostics, academic evidence, or mapping ledgers.

## Compiler And Runtime Behavior

Composition ends before semantic validation and compilation. The compiler
receives the same canonical scenario shape it receives for a flat SDL document.

Consequences:

- compiled runtime addresses are based on canonical identities, not source-file
  paths
- planner dependency, ordering, and refresh semantics remain unchanged
- runtime managers and backend contracts do not need to understand module
  trees
- compiled output for a composed scenario should match the equivalent flat
  scenario except for non-runtime provenance metadata
- module source metadata may be preserved for diagnostics, evidence, audit, and
  tooling, but not as a semantic dependency in runtime contracts

This preserves the existing `DSL-103` and `SEM-205` invariants: deterministic
module composition and canonical namespace-extensible identities across
expansion, compilation, planning, and backend contracts.

## Traceability And Evidence

Large inventory-backed work should be reviewable at fragment granularity.
Evidence bundles and mapping ledgers should cite:

- root scenario path
- fragment path
- module id and namespace
- fragment digest or lockfile record when available
- capture evidence path
- mapping-ledger row or inventory methodology artifact
- composed SDL path affected by the fragment

Ground Control traceability remains requirement-to-artifact traceability. Code
and tests that implement composition stay linked to `DSL-103` and `SEM-205`.
ADR and documentation artifacts that explain composition should use
`DOCUMENTS` or `CONSTRAINS` links. Inventory evidence should not cite only the
expanded root scenario when the reviewable unit is a fragment.

## Rejected Alternatives

### Arbitrary YAML `include`

Rejected. It has no typed insertion point, no schema boundary, no stable module
identity, no source trust model, and no ACES-specific reference validation.

### Cross-file YAML anchors

Rejected. YAML anchors and aliases are representation/serialization mechanics
within YAML processing. They do not provide module descriptors, versioning,
lockfiles, digest checks, trust policy, or cross-fragment diagnostics.

### Overlay Patch Language

Rejected for the initial composition model. Patches are useful in Kustomize,
but an overlay language would introduce arbitrary mutation paths and make
scenario review harder. ACES can revisit targeted patches later if a concrete
use case cannot be expressed through typed modules and imports.

### Jsonnet, Dhall, Or CUE As The SDL Authoring Language

Rejected. Each offers useful ideas, but adopting a programmable or constraint
language would move ACES away from an explicit SDL model and make validation,
diagnostics, and academic review depend on another language runtime.

### Runtime-Aware Module Trees

Rejected. Runtime and backend layers consume compiled canonical scenario
models. Making them interpret module trees would leak authoring layout into
runtime semantics and break the current layering model.

## Consequences

### Positive

- Large scenarios can be split into bounded, reviewable inventory fragments.
- Import resolution remains deterministic and supply-chain aware.
- Existing parser, validator, compiler, planner, and runtime contracts stay the
  semantic authority.
- Equivalent flat and composed scenarios compile to the same runtime meaning.
- Inventory evidence can cite fragments without weakening whole-scenario
  validation.

### Negative

- The authoring model is less flexible than generic YAML inclusion or overlay
  patching.
- Module authors must declare exports and namespaces explicitly.
- Diagnostics need follow-on source-provenance work to be fully ergonomic for
  large inventories.
- Hosted registry operations, signer distribution, and ecosystem discovery
  remain outside the repository's current implementation scope.

### Risks

- New SDL sections can be added without updating module reference rewriting.
  Mitigation: section ADRs and tests must update composition alias rewriting
  alongside validation, relationships, and docs.
- Reviewers may treat the expanded scenario as the source of truth. Mitigation:
  evidence and mapping-ledger guidance must cite fragments and digests.
- OCI support can be mistaken for an operated registry service. Mitigation:
  docs should distinguish packaging/resolution support from hosted ecosystem
  operations.

## Follow-On Implementation Plan

1. Add source-location capture to SDL YAML loading without changing the public
   scenario model shape.
2. Thread source provenance through module expansion, namespace rewriting, and
   semantic validation.
3. Teach diagnostics and language-service tools to report original fragment
   location plus composed canonical path.
4. Extend inventory methodology guidance so fragment path and digest appear in
   mapping ledgers and evidence citations.
5. Keep compiler/runtime output stable unless provenance is explicitly requested
   by authoring or audit tooling.
