# Issue #724 — Instantiated Phase Contract Preflight

Date: 2026-07-12

Issue: #724.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This is implementation guidance only. It does not change normative prose,
published schemas, or reference behavior.

## Binding Authority And Incumbents

- `specs/sdl/document-model.md`, `variables-and-instantiation.md`,
  `sections.md`, `references.md`, and `diagnostics.md` own SDL phase semantics.
  In particular, the existing four-step binding contract remains: choose,
  type-check, constraint-check, substitute and revalidate.
- `contracts/schemas/sdl/` is the normative machine-readable contract under
  ADR-009 and ADR-061. `schema_bundle()` is a compatibility proof, not schema
  authority; `contracts/schema-publication-manifest.json`,
  `tools/check_schema_publication.py`, and
  `tools/check_generated_schemas.py` remain mandatory for a schema change.
- `aces_sdl` owns parsing, composition, instantiation, and semantic validation
  (ADR-036). Reuse `Scenario`, `ExpandedScenario`, `instantiate_scenario`,
  `SemanticValidator`, the token helpers in `aces_sdl._base`, and the existing
  SDL exception/diagnostic boundary. Do not move SDL meaning into processor,
  runtime, CLI, or MCP code.
- Module trust and resolution remain exclusively in `aces_sdl.module_registry`:
  `ResolvedModule`, lock records, path confinement, digest checks, export-hash
  checks, signature verification, and bounded OCI extraction. Provenance is a
  record of an already verified resolution; it must never reimplement or
  weaken that gate.
- Preserve the current narrow planner need represented by
  `module_variable_specs`, `module_node_variable_refs`, and
  `node_variable_refs`. Those private side channels must become explicit,
  portable phase provenance, not a new general backend template system.

## Phase Contract

The implementation must make these shapes distinct. A field not listed for a
phase is forbidden, not represented as an empty or null compatibility shell.

| Form | Public shape and purpose | Allowed authoring machinery |
| --- | --- | --- |
| Normalized authoring | `Scenario`, after `sdl-yaml/v1` decoding, key normalization, shorthand expansion, and structural closure. Local declaration ids only. | `variables`, `module`, and declared `imports` are allowed. |
| Expanded authoring | Internal `ExpandedScenario`, after trusted module resolution and namespace rewrite, before final binding. Generated qualified top-level ids are allowed. | Root variables may remain for final binding; `module` and `imports` have been consumed. Resolution facts travel in typed expansion context, not in rewritten authoring fields. |
| Instantiated | The portable `instantiated-scenario-v1` payload and its concrete model. It contains executable scenario content plus required `instantiation_provenance`. | No `variables`, `imports`, or `module` member at all; no `${name}` token in any string value. |
| Canonical snapshot | A JCS/RFC-8785 digestable envelope for an instantiated artifact: profile id, concrete instantiated scenario, and exactly its instantiation provenance. | None. It is a sealed artifact, not input to parsing, composition, or substitution. |

`aces-sdl-semantic/v1` remains the canonical identity of the validated,
expanded **authoring** scenario and must continue to reject an instantiated
model. Do not silently redefine it. The instantiated snapshot needs its own
profile identifier and digest function, with a back-reference to that authored
digest. A future envelope change mints a new snapshot profile; it does not
change the meaning of the existing profile.

## Decision Guardrails

1. Replace inheritance-as-phase-proof. `InstantiatedScenario` must not inherit
   the authoring fields and then try to police them after construction. Factor
   shared concrete section fields only as an implementation detail if needed;
   keep the two closed public payload shapes separate. The instantiated schema
   and model must reject even `variables: {}`, `imports: []`, or `module: null`
   through ordinary closed-world structural validation.
2. Require a dedicated, immutable-on-public-API
   `instantiation_provenance` object on every instantiated payload, including a
   no-variable/no-import scenario. It is the portable replacement for
   `_instantiation_parameters`, `_instantiation_profile`,
   `_module_variable_specs`, `_module_node_variable_refs`, and
   `_node_variable_refs`; no consumer may depend on Python private state.
3. The provenance object must carry only replay-relevant facts: the canonical
   authored digest/profile; the selected profile; resolved root bindings with
   source (`provided` or `default`); resolved import records in declared order;
   and the existing narrow capability-constraint facts needed for
   `nodes.os`/`infrastructure.count`. A resolved import record needs its
   namespace path, requested source/version/digest, module id/version, resolved
   source, manifest/content digest, export hash, signer identity when present,
   and its resolved bindings. Use namespace segments, not a dotted string that
   consumers must parse.
4. Capability provenance is not a live `Variable` declaration. Model it as
   typed constraint facts addressed to the concrete field and parameter identity
   (including only the constraint data the planner needs, such as
   `allowed_values`). This is the extension seam for another explicitly
   justified pre-instantiation capability check. Do not retain a second
   `variables` map, reconstruct general template evaluation in the planner, or
   expose private composition naming as author input.
5. `module` is packaging metadata and `imports` are authoring instructions;
   neither survives in executable scenario content. Their resolved evidence is
   retained only under provenance. Absolute `root_file` paths, OCI cache paths,
   trust-policy contents, credentials, registry headers, and raw signatures do
   not belong in the portable artifact.
6. The public conversion path is `parse_sdl`/`parse_sdl_file` (authoring), then
   `instantiate_scenario` (concrete artifact), followed by compiler admission.
   The public instantiator must always apply the normal input and post-binding
   semantic gates. Any pre-merge module-only helper is private and must never
   mint or publish an `InstantiatedScenario`. A direct model payload is only
   external artifact admission: it must receive the same structural,
   provenance-consistency, token, and semantic validation before compilation.
   `model_construct` is an explicitly unsafe Pydantic escape hatch and not a
   supported ingestion API.

## Security And Cross-Cutting Gates

- **Source and configuration ingress:** retain `load_sdl_yaml`, source limits,
  mapping-key checks, `SDLModel(extra="forbid")`, and parser normalization. Do
  not make the authoring parser accept generated qualified names or instantiated
  payloads.
- **Module supply chain:** build records only from `resolve_import()` results,
  after local-path confinement, lock/digest/export-hash/signature checks, and
  OCI resource bounds. A provenance record is evidence, not authorization to
  bypass the registry or trust policy.
- **Model/schema/semantic admission:** the closed instantiated model, the
  published JSON Schema, `SemanticValidator`, and the post-substitution
  structural revalidation all remain necessary and non-duplicative: schema
  makes the interoperable shape rejectable, model validation enforces
  cross-field provenance rules, and semantic validation resolves concrete SDL
  references and control flow.
- **Secrets and error envelopes:** parameter values can reach
  `SDLInstantiationError` and MCP responses today. Do not render raw values,
  Pydantic `str(ValidationError)`, whole parameter mappings, or full scenario
  payloads on a binding failure. Reuse the bounded, input-free diagnostic style
  already used by parser diagnostics and the existing
  `SDLParseError`/`SDLValidationError`/`SDLInstantiationError` hierarchy. The
  MCP `sdl_instantiate` and operation pipeline must stop echoing resolved
  parameter values. Existing `redacted`/`operator_secret` validators still
  prohibit a raw substituted secret from appearing in a portable scenario or
  provenance payload.
- **OS, logging, and persistence:** instantiation/provenance capture must add no
  subprocess invocation, argv/env binding, log/audit store, or control-plane
  persistence. The only permitted remote access remains the existing
  `module_registry` OCI resolution path. In particular, do not add a CLI flag or
  log line that puts a parameter value in process argv or telemetry. Reuse the
  module registry's checkout-independent local `resolved_source` convention;
  never persist host paths.
- **Runtime boundary:** compiler and reference-processor entry points may
  consume an admitted instantiated artifact, but runtime/backends must receive
  only their existing compiled model/plan DTOs. Do not add a backend-facing SDL
  variable/provenance channel.

## Contract, Test, And Workflow Guardrails

- Keep prose, `InstantiatedScenario`, `schema_bundle()`, the hand-governed
  `instantiated-scenario-v1.json`, parser/instantiator APIs, and fixtures in
  exact agreement. Update the publication manifest hash and `last_change` when
  the schema changes; the current contract is draft, so the required tightening
  may remain in the `v1` lineage under ADR-061.
- Add conversion fixtures for flat and composed input, and negative conformance
  fixtures for each forbidden authoring field, unresolved token, missing or
  inconsistent provenance, and attempted direct-model/compiler admission with
  a non-concrete shape. Exercise JSON Schema independently of Pydantic, plus
  parser/instantiator/processor conversion and canonical-snapshot determinism.
- Preserve existing fixture discovery and JSON checks under
  `contracts/fixtures/sdl/`, `test_instantiated_scenario_schema.py`,
  `test_sdl_parser.py`, `test_sdl_validator.py`,
  `test_sdl_canonicalization.py`, `test_sdl_module_registry.py`, and processor
  planner tests. Run the repository policy, requirement-governance,
  schema-publication, generated-schema, and full `verify` graph configured in
  `.ground-control.yaml` / `.gc/plan-rules.md`.

## Non-Goals And Anti-Patterns

This change does not create an environment-variable binding language, a second
template syntax, a new schema registry, a new exception hierarchy, a generic
provenance database, an import resolver outside `module_registry`, a runtime
API, a backend protocol field, or an audit/logging subsystem. It does not make
an artifact's claimed provenance cryptographic proof that the local process
performed expansion; verification remains at the existing import/trust gate.

Avoid allowing empty authoring machinery as a compatibility crutch; relying on
private attributes or `isinstance` alone as an admission proof; reusing the
authoring schema for instantiated output; treating an instantiated snapshot as
an authoring canonical digest; copying raw parameter values into diagnostics,
MCP output, logs, or paths; and adding per-field planner special cases instead
of one typed provenance seam.
