# Issue 539 realization-posture cascade preflight

Status: implementation guardrail for issue #539; not an implementation plan or
a new semantic authority.

## Decision summary

Issue #539 extends the SEM-218 designation authority. It does not create a
second realization system. The author-facing cascade must lower into the
existing explicitness, realization-envelope, planner, and provenance contracts.

The repository currently has three similarly named but distinct concepts. They
must remain distinct:

- an author scope default: `closed`, `open`, or `unspecified` (delegated);
- a resolved realization-envelope closure: `closed-world` or `open-world`;
- an apparatus capability: `RealizationSupportMode` (`exact-only`,
  `constrained`, or `open-realization`).

`RealizationSupportMode` must not be reused as the authoring enum. Capability is
not intent, and `exact-only` is not closed-world. A resolved author default may
reuse the existing `Closure` vocabulary. Explicit leaf exact/constrained/open
intent continues to use the SEM-218 explicitness/posture vocabulary and wins
over every inherited scope default.

## Authoring and resolution boundary

There must be one scenario-root, typed, SEM-218-owned designation surface. It
may contain the scenario default and scoped override entries, but must not add a
generic realization field to every SDL model, a generic annotation bag, or a
second manifest family. `unspecified` is the one authored spelling for delegated
intent; do not add `delegated` as a second accepted alias. This is the narrowly
justified addition to the SDL surface reserved by SEM-218's staged designation
authority.

The designation surface is authoring-phase machinery. It belongs on the
`Scenario`/expansion side; it must not be added to the common executable
`ScenarioContent` shape or survive as an unresolved executable field on
`InstantiatedScenario`. Typed designation records—including an explicit root
`unspecified` marker awaiting selected-apparatus context—travel in the existing
expansion/instantiation provenance aggregate and compiled carrier instead.
Preserve the disjoint phase contracts and phase equations established by
ADR-078.

Scope targets need one canonical structured identity. Reuse the repository's
namespace-segment machinery and its existing RFC 6901 field-pointer convention
(`ResolvedImportProvenance.namespace`, `CapabilityConstraint.field_pointer`,
and language-edit pointers are incumbents). Do not expose the permissive dotted
`_PATH_TOKEN_RE` syntax as new author input, and do not introduce JSONPath,
wildcards, or a parallel grammar. Convert the canonical identity to structured
relation-engine tokens at one checked boundary; never recover scope by splitting
an arbitrary string on dots.

The authored form and the resolved form are different phase contracts:

- Explicit `unspecified` is unresolved author intent. It inherits a
  concrete declaration from an outer scope; at the outermost unresolved scope
  it is resolved only after the processor has a selected apparatus context.
- Resolved envelopes remain context-free set expressions. An unresolved value
  must never enter `member()`, `subsumes()`, `witness()`, or negative-probe
  generation.
- Omitting the designation surface entirely is not the same as explicitly
  delegating at the root. Omission preserves the legacy effective closed-world
  behavior. This distinction must survive Pydantic defaulting, module
  expansion, instantiation, compilation, and serialization.

Composition must qualify and rewrite scoped entries with the existing symbol
map, namespace tuple, and composition-provenance machinery before resolving the
cascade. A default at the root of an imported module governs only declarations
owned by that module namespace; it must not leak onto host or sibling-module
declarations. Import order is not specificity, and composition must not erase
the distinction between an omitted surface and an explicit `unspecified` entry.

Resolution is deterministic semantic specificity, never input-list order:

1. an explicit leaf exact/constrained/open declaration;
2. the most-specific concrete scoped default;
3. an inherited concrete outer default;
4. for an explicitly delegated root, the selected processor/apparatus default;
5. for an omitted surface, the legacy closed-world fallback.

Conflicting declarations at equal path and scope are validation errors.
Identical duplicates should either normalize to one declaration or be rejected
consistently; they must not create order-dependent behavior.

An inner open default under an outer closed default, and the inverse, are valid
cascade operations. This is distinct from widening an explicit envelope domain
binding. ADR-070 and `specs/formal/realization/envelope-semantics.md` currently
require `overrideable` for widening under a fixed parent; implementation must
clarify that the rule remains applicable to explicit domain bindings, not to
the new lexical closure cascade.

The current envelope engine is not yet a correct cascade implementation:
`effective_constraints()` does not use `EnvelopeBinding.scope`, permissive path
tokenization can skip invalid characters, and open-world closure overlays do
not remove inherited closed-world state. These are canonical-engine gaps to
resolve, not reasons to add a second resolver. The canonical engine must parse
the full path or reject it; a tokenizer that silently discards unmatched text is
not a shape validator.

## Meaning of open and closed

Open author intent applies only to realization points admitted by the one
designation authority. It does not make arbitrary SDL keys valid, synthesize
undeclared topology, relax references or identities, or allow a backend to
invent secret-bearing configuration. `SDLModel(extra="forbid")` remains in
force in both modes.

Closed means that an unspecified *admitted realization point* cannot be chosen
by the backend. It must not be implemented as "every optional Pydantic field
must be authored"; that would change the meaning of existing schemas and break
backward compatibility. Deterministic schema/processor defaults remain
processor-derived rather than backend-realized.

Collection creation, opaque-artifact internals, and other absent values become
backend-realizable only when their owning semantic rule admits them. A broad
scenario-level open default cannot by itself turn every absent model field into
a realization slot.

## Canonical incumbents to extend

- `aces_sdl.explicitness`, `SemanticValidator._verify_explicitness()`, and
  `classify_authoring_specificity()` own author specificity. Extend or compose
  this authority; do not add a parallel classifier.
- `aces_sdl.phase_contracts.ExplicitnessProvenanceRecord` and the existing
  expansion/instantiation provenance aggregates carry author/processor
  derivation across phases. A scope default is not itself leaf explicitness. If
  the existing leaf record cannot express canonical scope identity, governing
  source, and effective closure without semantic overloading, add one closed,
  typed sibling record inside the same provenance aggregate. Do not encode it in
  `reason`, a private attribute, or a metadata sidecar. Extend the incumbent
  uniqueness and composition-prefix validators with the same identity rules.
- `aces_contracts.realization_envelope` and
  `aces_sdl.realization_envelope` own the set expression, membership,
  subsumption, witnesses, and negative probes. Keep one relation engine.
- `aces_processor.semantics.realization.CompiledRealizationRequirement`,
  `resolve_realization_concern()`, and `realization_support_diagnostics()` own
  compiled realization demand and apparatus matching. Open requirements must
  be carried and checked there; do not add a planner-only matcher.
- `aces_backend_protocols.backend_manifest.RealizationSupportDeclaration` and
  its contract model remain apparatus capability declarations. A scoped open
  request is accepted only when the selected domain explicitly declares
  `OPEN_REALIZATION` and satisfies any finer offered-envelope constraint.
- The existing realization-envelope `subsumes()` relation is the fine-grained
  requested/offered compatibility seam. The planner currently checks only a
  concrete instance with `member()`; route a compiled author request through
  the canonical relation API rather than encoding backend names or capability
  exceptions in the SDL resolver.
- `aces_processor.semantics.realization.realization_disclosure()` and
  `aces_contracts.runtime_state.RealizationProvenanceEntry` own disclosure.
  Backend-filled open slots must be recorded as `backend-realized`, including a
  stable governing-scope reference, without copying the realized value.
- `aces_runtime.backend_calls`, `RuntimeTarget`, and the snapshot contract own
  the live backend boundary. Preserve fail-closed result validation and baseline
  snapshot behavior on disclosure failure.
- `aces_runtime.control_plane_store` owns runtime snapshot persistence. Extend
  the existing serializer and schema if the provenance shape changes; do not
  add a posture ledger or store.

The current compiler deliberately skips open explicitness records, the current
support gate does not reject unsupported open requests, and disclosure skips
paths without a plan-side baseline. All three stages must consume one compiled
carrier so planning and provenance cannot disagree about which slots were open.

## Cross-cutting gates

The design must pass every existing gate below.

### SDL shape and semantic validation

`parse_sdl()` remains the only YAML entry point. Its size, alias, tag, scalar,
key-normalization, JSON-domain, and closed-Pydantic checks remain unchanged.
The typed designation surface must then pass `SemanticValidator`, canonical
scope/path resolution, duplicate/conflict detection, and reference validation.
CLI and MCP authoring operations must continue to call this same parser and
must not interpret the cascade independently.

If the public SDL shape changes, update the authoritative Pydantic contract,
`contracts/schemas/sdl/sdl-authoring-input-v1.json`, valid and invalid fixtures,
`specs/sdl/sections.md`, language metadata where applicable, and the schema
publication manifest/generator parity checks together. The JSON Schema remains
the hand-governed authority under ADR-009; update
`contracts/schema-publication-manifest.json` (`last_change` and digest inputs)
and pass `tools/check_generated_schemas.py` and
`tools/check_schema_publication.py` rather than treating a generated schema as
the source of truth.

### Apparatus configuration and policy

`BackendManifestV2Model`, `BackendManifest`,
`RealizationSupportDeclaration`, concept-family bindings, and realization-
envelope identity validation remain the apparatus shape gates. Delegation must
not be inferred from `realization_support`, an offered envelope, backend name,
or environment variable: those describe capability, not the apparatus's chosen
default policy.

The planner must reject, with the existing structured diagnostic model, an open
request unsupported by the selected apparatus. There is no silent approximation
or fallback from open to constrained/exact.

### Runtime, persistence, and error envelopes

Backend `ApplyResult`, address-transition, snapshot, and realization-disclosure
validation remain fail closed. Extend the existing phase/snapshot DTOs and
`control_plane_store` serialization atomically if governing-scope provenance is
published. Preserve unknown-field rejection and schema/model differential tests.

The current `control_plane_api_models._snapshot_model()` mapping omits
`realization_provenance` even though the runtime snapshot contract already owns
that field. Delivery of governing-scope disclosure must close this existing
mapping gap and prove contract -> store -> readback -> authenticated snapshot
API preservation. Do not claim provenance delivery based only on the in-memory
DTO or persistence serializer.

Use the existing diagnostic and API error envelopes. Diagnostics may include a
canonical path, scope, domain, requirement kind, declaration reference, and
digest; they must not include raw authored or realized values. Runtime catch-all
handling must continue to expose only the generic internal-error response and
log exception type rather than payload contents. Do not introduce a new
exception hierarchy for cascade failures.

### Authentication, secrets, and OS exposure

Issue #539 requires no new endpoint. Any existing control-plane read or mutation
that exposes the extended snapshot remains behind the incumbent bearer/trusted-
proxy identity, role/target authorization, request-size, idempotency, and audit
gates.

Open posture never bypasses `RuntimeEnvironmentVariable`, `ImageBuildArg`, or
`ImageEnvironmentDefault` redaction validation, evidence redaction checks, or
the rule that redacted/operator-secret values are omitted. Do not configure
posture or delegated defaults with secrets, environment variables, command-line
arguments, or backend-specific process flags. No token, author value, realized
value, or unredacted configuration may enter argv, logs, audit events,
diagnostics, fixtures, or provenance.

## Extensibility seam

Root delegation needs one injected resolver at the processor/planner boundary,
parameterized by the selected processor/apparatus compatibility context. Until
a typed apparatus default exists, its agreed fallback remains closed. EXP-721
or a later apparatus-default contract must be able to supply this resolver
without changing SDL cascade resolution, the envelope algebra, or backend
implementations.

The same canonical path/scope resolver must later admit opaque-artifact scopes
(issue #377) and new realization domains through registered semantic ownership,
not by editing a global switch or adding backend-condition branches.
The extension parameter is therefore the registered realization concern/domain
and selected-apparatus default resolver, not another posture enum or resolver
implementation.

## Specification and verification guardrails

The implementing change must reconcile and update, as one semantic change:

- `specs/formal/realization/explicitness-and-realization.md`;
- `docs/explain/reference/explicitness-realization-semantics.md`;
- ADR-070 and `specs/formal/realization/envelope-semantics.md` for cascade versus
  explicit-binding widening;
- the SEM-218 row in
  `docs/explain/reference/shared-semantic-integrity.md`.

The existing specification currently describes designation as staged while
other wording describes SEM-218 enforcement as complete. Do not leave that
coverage state internally contradictory after delivery.

Required verification properties include both override directions, explicit
leaf precedence, explicit root delegation versus omission, module-namespace
isolation, equal-specificity conflicts, order independence, unsupported-open
planner rejection, successful backend-realized disclosure with governing scope,
redacted diagnostics, contract/store/authenticated-API round trips, and
schema/model differential coverage. Include dotted and escaped-key scope cases
so path canonicalization cannot pass only simple identifiers. These are
contract properties, not separate workflow logic.

## Non-goals and prohibited shortcuts

- No new manifest family, generic annotation/metadata bag, second registry,
  constraint DSL, path grammar, relation engine, matcher, provenance sidecar,
  persistence store, exception hierarchy, logger, or validation pipeline.
- No realization field mixed into every nested Pydantic model, unresolved
  designation on the instantiated executable shape, or dotted-string scope
  matching exposed as an author contract.
- No relaxation of `extra="forbid"`, identity/reference validation, semantic
  invariants, secret redaction, authorization, or backend result validation.
- No inference that missing author input means open, or that advertised backend
  support grants permission to realize an exact/closed request.
- No conversion of unspecified optional schema fields into realization points
  without an owning semantic designation.
- No backend-name branching, process-environment posture switch, raw-value
  diagnostics, or silent approximation.
- No compatibility logic in `implementations/python/src/aces`; owning packages
  remain the only implementation authority.
- No new API or control-plane workflow is required by this issue.
