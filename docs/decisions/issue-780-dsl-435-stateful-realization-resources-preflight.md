# Issue #780 / DSL-435 — Stateful Realization Resources Preflight

Date: 2026-07-16

This note records architecture guardrails for DSL-435. It does not implement
the language, processor, provisioner, or a backend.

No new ADR is required. ADR-004 owns compile/plan/execute and dependency
semantics; ADR-009 and ADR-061 own the normative schema boundary; ADR-036 owns
package direction; ADR-056/057 own secret and redaction distinctions; ADR-070
owns realization honesty; ADR-072 owns validation-strength language; ADR-075
owns release/version governance; and ADR-076 owns authored identifiers and
compiled addresses.

## Decisions and boundaries

`generated_artifacts` and `persistent_volumes` are authored desired state.
They are not `Content` placements, observed `RuntimeMount` records, filesystem
inventory, generic metadata, associated-artifact manifests, or backend-native
fragments. Those incumbents may share narrow lexical helpers, but none carries
the lifecycle, access, dependency, sensitivity, and realization meaning of
these declarations.

Each declaration has one portable id and one compiler-owned address:
`provision.generated-artifact.<id>` or
`provision.persistent-volume.<id>`. Mutable fields never enter identity. The
same typed resource flows through `ScenarioContent`, `InstantiatedScenario`, a
`ResolvedResource` specialization in `RuntimeModel`, `PlannedResource`,
`ProvisionOp`, and `SnapshotEntry`; no parallel DTO, metadata side channel, or
backend-specific schema is permitted.

Three provenance concepts remain distinct:

- generator provenance is a non-secret, inert reference to the declared recipe
  or source and is not proof that bytes were generated correctly;
- SEM-218 explicitness provenance is carried by the existing
  `CompiledRealizationRequirement` and `RealizationProvenanceEntry`; and
- operational evidence that a backend generated, attached, or retained state
  belongs to existing realization observation/conformance surfaces, not the SDL
  declaration or snapshot payload alone.

Output bytes, private keys, credentials, rendered configuration, and backend
handles are unrepresentable in this contract. `secret` is a sensitivity label,
not a field that authorizes a raw secret value. A mixed-sensitivity artifact is
consumed as one resource; implementations must not infer per-output filtering.
Authors needing different audiences split the outputs into separate resources.

`ordering_dependencies` and `refresh_dependencies` retain the meanings fixed by
ADR-004. The processor must use the existing typed dependency graph,
topological ordering, reverse delete ordering, and refresh propagation. A
consumer reference is not silently an ordering edge, and lexical address order
is never a lifecycle guarantee. If consumer attachment imposes an order, that
order must be stated once in the normative semantics and lowered explicitly.

Capability admission has two independent obligations. The provisioner must
declare support for the portable resource kind, and the existing SEM-218 gate
must confirm exact, non-approximating realization support for the complete
resource payload. Neither a generic exactness claim nor a kind-support flag can
substitute for the other.

## Canonical concerns to reuse

- **Source admission:** `load_sdl_yaml()` and its source/alias limits,
  `SDLModel(extra="forbid")`, `PortableIdentifier`/`QualifiedName`, the
  `Scenario` -> `ExpandedScenario` -> `InstantiatedScenario` phase boundary,
  and unresolved-variable admission.
- **References and composition:** the SDL section/reference catalogs,
  `_mapping_scopes.HASHMAP_SECTIONS`, `_module_symbols.symbol_index()`, module
  export/collision checks, `DeclarationIndex`, and `SemanticValidator`.
  Section-qualified references remain authoritative when a bare name is
  ambiguous; composition rewrites through section-specific symbol maps.
- **Compilation and identity:** the compiler address builders,
  `ResolvedResource`, `RuntimeModel.__post_init__`, `resource_payload()`, and
  `aces_contracts.addressing.require_compiled_address()`.
- **Planning:** `PLAN_RESOURCE_TYPES_BY_DOMAIN`,
  `require_plan_operation_identity()`, and the functions in
  `aces_processor.semantics.planner` for graph validation, stable ordering,
  reconciliation, refresh, and deletion.
- **Realization honesty:** `CompiledRealizationRequirement`,
  `realization_support_diagnostics()`, `realization_envelope_diagnostics()`,
  `realization_disclosure()`, `BackendManifest`, and
  `ProvisionerCapabilities`.
- **Runtime admission and errors:** `RuntimeManager` plan provenance checks,
  `RuntimeControlPlane._submitted_plan_diagnostics()`,
  `_call_backend_diagnostics()`, `_call_backend_apply()`, `Diagnostic`,
  `ApplyResult`, `OperationReceipt`, and `OperationStatus`. No new exception or
  logging hierarchy is warranted.
- **Persistence and observation:** `RuntimeSnapshot`, `SnapshotEntry`, and the
  existing `ControlPlaneStore` atomic snapshot path. A snapshot preserves the
  admitted desired payload and SEM-218 ledger; it is not proof of native volume
  durability or artifact contents.
- **Contracts and workflow:** the hand-governed schemas under
  `contracts/schemas/`, `schema_bundle()`, the schema publication manifest,
  SDL catalog parity and lineage ledgers, canonical repo-policy checks, and
  release-please. A consumer-visible feature uses the repository's `feat:`
  release signal; package versions and `CHANGELOG.md` are not hand-edited.

## Security and whole-path gates

1. **YAML and model shape.** Safe bounded YAML loading, duplicate-key checks,
   closed Pydantic models, identifier validation, collection cardinality, path
   validation, and enum validation run before semantic resolution. Validators
   emit bounded, source-anchored messages and must not echo generated material.
2. **Semantic and instantiation admission.** Consumer and dependency references
   resolve against canonical declaration identities, not set membership or
   delimiter guessing. Bare cross-section collisions fail as ambiguous.
   Instantiation leaves no `${...}` token in a compiled path, provenance
   reference, consumer, output, or dependency.
3. **Path and host exposure.** Output paths are canonical contained relative
   paths. Mount destinations are canonical paths in the consumer guest/runtime,
   never host paths. The contract must either declare a POSIX-only v1 and reject
   incompatible consumers or carry an explicit closed path dialect; it must not
   accept a POSIX-looking path for a Windows consumer and let the backend guess.
   A materializing backend anchors writes below an owned root, rejects symlink
   and traversal escapes after native normalization, uses fixed non-shell
   invocation, and never places sensitive bytes in argv, environment, command
   text, stdout/stderr, diagnostics, or audit events.
4. **Compiler and plan shape.** Canonical-address, unique-address, closed
   resource-type, dependency-resolution, and cycle gates complete before any
   backend call. The full typed spec, including lifecycle and sensitivity
   metadata, survives projection without reinterpretation.
5. **Manifest and dispatch admission.** Manifest-kind support and SEM-218 exact
   support are checked at every dispatch entry point, including direct
   `RuntimeControlPlane`/HTTP submission. Backend `validate()` is an additional
   stricter gate, not the sole authority. An error diagnostic prevents
   `execute_operation()` and therefore prevents `Provisioner.apply()`.
6. **HTTP/auth surface.** The existing mutating-role authorization, target
   binding, request-size guard, idempotency fingerprint, and redacted 500
   envelope remain in force. No bearer token, credential resolver, environment
   binding, CLI secret option, or ambient configuration surface is introduced.
7. **Backend result and persistence.** `_call_backend_apply()` retains the
   baseline snapshot on malformed results or SEM-218 approximation, reports
   only structured diagnostics, and accepts realization provenance only after
   exact readback. The authorized snapshot API and local store may expose the
   declared metadata, so generator provenance and payload metadata must be
   non-secret by construction.

## Admission blockers and gotchas

- Bare dependency names shared by `generated_artifacts` and
  `persistent_volumes` must fail during semantic admission with a qualified-ref
  diagnostic. Accepting them and raising a compiler `ValueError` later is both
  too late and the wrong error surface.
- Consumer mount destinations must be unique across the combined stateful
  resource set for a node unless an explicit overlay/stacking semantic is added.
  Per-resource duplicate checks do not catch cross-resource collisions.
- `read_only_many` admits no writer. `read_write_once` admits at most one writer
  node. Generated-artifact write access needs explicit copy/writeback and
  provenance semantics; absent those semantics it must fail rather than imply
  mutable exact state.
- Paths must reject non-canonical equivalents, control/NUL characters,
  traversal, root destinations, and path-dialect mismatches. Do not preserve
  multiple spellings such as repeated separators as different exact payloads.
- Output names and paths, consumers, and dependency entries require stable
  uniqueness rules. Semantic uniqueness not expressible in ordinary JSON
  Schema must use the repository's existing semantic-invariant disclosure and
  model/corpus validation; schema success must not be described as semantic
  success under ADR-072.
- `retain` and `ephemeral` govern delete behavior. A delete operation keeps the
  prior payload so the backend can honor it. Retained native state must never be
  silently adopted by name on a later create, and a lifecycle transition must
  not become an implicit destructive migration.
- A capability default is false. Stubs may claim full support to exercise the
  contract; production manifests claim only behavior their provisioner and
  conformance evidence actually support. Do not obfuscate normative vocabulary
  literals to appease secret scanners; fix or scope the scanner rule instead.
- The SDL mapping catalog, module-symbol catalog, normative section/reference
  tables, generated bundle, published schemas, lineage ledger, manifest
  renderer, fixtures, and plan resource-type registry are synchronized
  incumbents. Do not add a third section list, reference resolver, schema, or
  capability registry.

## Extensibility seam

The extension seam is the portable resource-kind discriminator plus governed
capability dimensions. Common identity/lifecycle/consumer/dependency fields
remain stable; a future generator kind receives a kind-scoped typed payload,
not a generic `options` map. When backends need partial support, capability
sets are keyed by the existing portable generator kind, lifecycle, access mode,
and path-dialect vocabularies rather than adding one boolean per variation or
placing provider terms in `constraints`. The planner consumes those sets through
one table-driven capability gate.

## Non-goals and anti-patterns

- No provider selection, storage class, host path, cloud volume id, Docker
  Compose fragment, Terraform fragment, shell command, or backend handle in SDL.
- No raw generated bytes, credential value, secret store, certificate authority,
  renderer, artifact registry, backup system, or volume implementation.
- No conversion of observed mounts/filesystem inventory or `Content` placement
  into desired state, and no claim that desired snapshot metadata is operational
  evidence.
- No storage sizing, performance tier, snapshot/backup, encryption-key, or
  cross-region policy until a separate portable requirement defines it.
- No second graph engine, generic resource base beyond the existing
  `ResolvedResource`, duplicate realization-support mechanism, new persistence
  repository, new exception hierarchy, or feature-specific logger.
- No silent backend fallback, best-effort dropping of unsupported fields,
  provider-private extension blob, ambiguity resolution by declaration order,
  or reliance on incidental dictionary/lexical ordering.
