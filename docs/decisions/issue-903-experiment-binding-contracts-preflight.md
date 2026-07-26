# Issue 903 Cross-Plane Experiment Binding Contracts Preflight

Date: 2026-07-26

Issue: #903.

Requirement: none. The GitHub issue title, body, acceptance criteria, and
non-goals are the authoritative contract.

This note records architecture guardrails for publishing experiment binding
descriptors and typed participant-implementation configuration targets. It is
guidance only: it does not add or change contract models, schemas, validators,
runtime behavior, trial plans, fixtures, or an implementation plan.

## Binding Authorities And Existing Gaps

- ADR-009 makes `contracts/schemas/` the hand-governed machine-readable
  authority and the Python `schema_bundle()` output its parity proof. ADR-061
  and `contracts/schema-publication/` govern schema lineage, compatibility,
  content hashes, and removal.
- ADR-055, ADR-065, and ADR-074 make experiment authoring input, apparatus
  context, archival runs, studies, and participant-implementation provenance
  distinct artifacts. An authored parameter is not automatically a scenario
  mutation, apparatus setting, or run fact.
- `ExperimentParameterModel` currently has only `name`, scalar `value`,
  `value_kind`, and `redaction`.
  `ExperimentConditionAssignmentParameterModel` narrows that shape, while
  `_parameter_satisfies_requirement()` and
  `_condition_assignment_run_criteria_signature()` still compare parameters by
  name, kind, type name, and serialized value. None of those fields identifies
  a binding plane, owner, canonical target, source factor/condition, or
  validator. They are legacy descriptive/audit parameters, not an authority
  boundary.
- ADR-084, `raes.variation`, `SemanticValidator._verify_variation_points()`,
  `instantiate_scenario()`, and instantiation provenance already own scenario
  family selection and scalar SDL binding. Issue #903 must connect experiment
  intent to that path; it must not add another SDL target registry,
  substitution engine, or instantiation path.
- ADR-076, `DeclarationIndex`, and SDL composition already preserve canonical
  declaration collisions before alias projection. Aliases are lookup
  conveniences, not identities. Cross-plane binding needs the same
  collision-preserving rule without importing private SDL implementation code
  into `raes_contracts` or treating processor runtime addresses as authoring
  addresses.
- ADR-041 and
  `ParticipantImplementationManifestModel` /
  `ParticipantImplementationSelectionModel` own participant implementation
  declaration and selection. `configuration_ref` and
  `configuration_digest` preserve opaque configuration identity, but the
  manifest currently declares no typed configuration targets and no portable
  complete-configuration validation result.
- `ParticipantImplementationManifestModel.constraints` and
  `ParticipantExposurePolicyModel.constraints` are disclosure text. They are
  not schemas, validators, target registries, defaults, or permission to inject
  arbitrary configuration.
- `ExperimentApparatusContextModel.configuration_parameters` records apparatus
  parameters but does not make their names authoritative. Processor, backend,
  participant-implementation, and other apparatus components remain separate
  manifest owners.
- Runtime fact contracts and `RuntimeFactBindingPlane` already demonstrate
  strict scalar unions, value-or-secret-reference separation, typed sink
  policy, explicit failure dispositions, and value-free portable events.
  Runtime facts are nevertheless run-local late-bound action inputs. They must
  not be reused as pre-run experiment factors, scenario selections,
  participant configuration, or apparatus configuration.
- `canonical_contract_digest()` already implements RFC 8785/JCS plus SHA-256
  for closed contracts. Ad hoc `json.dumps(sort_keys=True)` digests are not a
  second canonicalization profile.

## Architecture Decisions And Guardrails

### One descriptor family, three closed authority planes

Publish one versioned, closed binding-descriptor contract family with a closed
plane vocabulary:

- `scenario`;
- `participant-implementation`; and
- `apparatus`.

Unknown planes are invalid. A plane is declared data, never inferred from
`value_kind`, a parameter name or prefix, a target spelling, a matching field,
the selected component kind, or fallback order.

The descriptor records the source factor id, factor level id, and condition id
explicitly. Those ids must resolve against the owning
`ExperimentSpecModel` / `ExperimentStudyModel` factor and allocation maps.
Collection position and equality between a parameter name and a factor name
carry no provenance meaning.

The descriptor also records:

- the exact plane-specific canonical target;
- the exact JSON scalar type (`string`, `integer`, `number`, `boolean`, or
  `null`);
- a discriminated literal-value or secret-reference disposition;
- the owning contract id and version; and
- a governed validator/profile id and version.

The validator identity is a portable governed identifier, not a Python import
path, callback, command, entry point, template, plugin name, or experiment-
selected dispatch string. Trusted code maps the governed identity to an
installed validator behind the owning package/backend boundary.

Use strict Pydantic scalar types and explicit type predicates, following
`RuntimeFactScalar` and `_value_matches_type()`. Boolean is not integer, integer
and number remain distinguishable where declared, strings are not parsed into
numbers or booleans, and non-finite numbers fail before canonicalization.
`ContractModel` closure alone is insufficient because default Pydantic scalar
coercion and float acceptance do not prove this invariant.

### Canonical targets are typed owner references, not generic paths

The target is a discriminated plane-specific reference, not one universal
string path:

| Plane | Canonical owner and target | Admission rule |
| --- | --- | --- |
| Scenario | The exact scenario-family identity plus canonical variation-point address and its owner-declared target | Resolve through the existing composed `Scenario` variation registry, declaration index, variation semantic validator, selection application, and public instantiation/admission path. Do not bind directly to arbitrary SDL fields or `${...}` occurrences. |
| Participant implementation | Selected implementation identity and manifest version plus one manifest-declared configuration-target id | Resolve only in the selected `ParticipantImplementationManifestModel` target registry and validate through that manifest's governed configuration contract/validator. |
| Apparatus | Selected apparatus component identity/manifest plus one configuration-target id declared by that public owning contract | Processor, backend, host, or other component configuration is admissible only when its selected portable manifest/contract publishes the target. Component presence, `configuration_parameters`, private backend schema fields, and free-text constraints do not create targets. |

This preserves the difference between SDL declaration addresses, processor
compiled addresses (`raes_contracts.addressing.CompiledAddress`), participant
configuration ids, and apparatus component configuration ids. Common dotted
rendering does not give those concepts common authority.

Each owner may publish bounded input aliases for migration or ergonomics.
Resolution produces exactly one canonical target before any value validation or
mutation. Preserve every supplied spelling until collision analysis is
complete. Two bindings that resolve to the same `(plane, owner, canonical
target)` fail even when values, source factors, or secret-reference identities
are equal. An alias colliding with another canonical id or alias also fails.
Never trim, lowercase, case-fold, choose first/last writer, deduplicate through
a set/map, or use source order to resolve ambiguity.

Reuse the collision-preserving semantics of `DeclarationIndex`; do not import
the private SDL class across the package boundary. If a dependency-neutral
helper is extracted, it may own only canonical-key/alias collision mechanics.
It must not become a global registry that owns SDL, participant, and apparatus
target meaning.

### Target declarations and complete participant configuration

A configuration-target declaration is a reusable closed scalar-target value
model, but its registry and validation remain owner-specific. A declaration
needs a stable target id, exact scalar type, optional same-type default, allowed
literal or secret-reference dispositions, sensitivity posture, aliases, owning
contract/validator identity, and any bounded declarative constraints that are
portable. It must not contain arbitrary JSON Schema fragments, Python
callables, commands, paths, environment lookups, backend option maps, or
free-text constraints interpreted as executable validation.

Extend the participant implementation manifest capability surface with a keyed
typed target registry. Map keys must equal embedded target ids, aliases must be
unique across the complete registry, defaults must validate at manifest
admission, and the manifest's supported contract ids must declare the
configuration contract/result versions it claims.

Participant configuration validation is a complete, atomic owner operation:

1. resolve all aliases and reject unknown, ambiguous, or duplicate canonical
   targets;
2. apply declared defaults and explicit overrides without type coercion;
3. require every target whose declaration has neither a default nor an
   admitted override;
4. validate the complete configuration with the selected manifest's governed
   validator;
5. return normalized same-type realized values, default/override origin,
   per-target provenance, and one authoritative configuration digest; and
6. publish no mutation or success result if any target fails.

Normalization may canonicalize an admitted value within its declared type; it
must not convert between JSON scalar types, silently drop inputs, substitute a
different target, clamp values, or turn a failure into a default.

The portable validation/result carrier belongs with neutral participant
contracts in `raes_contracts`; the callable/protocol that realizes owner
validation belongs behind the participant/backend protocol boundary. It must
compose with `ParticipantImplementationSelectionModel` and the existing
participant action-admission path, not create a second participant identity,
action binder, control plane, or backend plugin mechanism.

### Secret references are structurally distinct and never resolved here

Literal values and secret references are a discriminated union. A secret
reference cannot be represented as a string literal plus `redaction`, and a
redacted legacy parameter is not automatically a secret reference.

Only a bounded, explicitly non-sensitive reference identity may enter an
authoring descriptor, trial plan, validation result, digest, or provenance
record. Provider credentials, secret locator details that themselves expose
private data, resolved values, hashes of resolved values, environment-variable
names, file paths, command fragments, and backend-native objects remain
outside portable contracts.

Secret dereference is a separate deny-first runtime authorization at a
protected sink. Successful descriptor/configuration validation does not grant
dereference authority. Borrow the value-free event and protected-sink posture
from runtime fact binding where applicable; do not reuse a runtime fact as the
experiment binding itself.

ADR-056/057 distinguish authored scenario fixture values from operator secrets.
That does not authorize operator secrets in experiment binding artifacts.
Scenario fixture values remain governed by their SDL owner; issue #903's secret
reference form exists specifically so resolved external secret material never
enters the portable experiment/configuration lifecycle.

### Canonicalization, ordering, identity, and provenance

Canonicalization happens only after plane, owner, target, type, source
factor/level/condition, disposition, and value/reference validation succeeds.
Normalize semantically unordered bindings by `(plane, owner identity,
canonical target)` before RFC 8785/JCS serialization. Input list order, aliases,
map insertion order, source paths, private validator objects, and resolved
secret values never affect identity.

Reuse `canonical_contract_digest()` and its RFC 8785 semantics, or move that
dependency-neutral implementation behind a shared public contract helper if
its current satisfiability module placement would create a conceptually wrong
import. Do not create a binding-only canonical JSON implementation.

An authoritative realized-configuration digest commits to:

- configuration contract/profile and owner identity/version;
- each canonical target and exact declared type;
- each default/override origin;
- normalized non-secret realized values; and
- admitted non-sensitive secret-reference identities.

It never commits to resolved secret material. If an external configuration
artifact also has a byte checksum, keep that artifact checksum distinct from
the authoritative normalized configuration digest. Existing
`ParticipantImplementationSelectionModel.configuration_digest` must equal or
unambiguously reference the authoritative result digest; do not publish two
fields with overlapping meanings.

Define one reusable realized-binding provenance value model, distinct from the
authoring descriptor. It preserves source factor, level and condition, plane,
canonical target, exact type, default/override origin, normalized non-secret
value or non-sensitive reference identity, owning contract/validator version,
and authoritative configuration digest.

Each lifecycle owner embeds that value rather than copying its fields:

- admitted trial intent records the binding to be realized;
- scenario instantiation provenance records the scenario binding actually
  applied through the existing instantiation path;
- participant configuration validation records the complete normalized
  configuration result; and
- `ExperimentRunModel` / participant implementation provenance archive the
  realized binding and digest used by the run.

Do not place binding provenance in `RuntimeSnapshot.metadata`, generic
`metadata`/`details`, audit text, logs, or backend-private state. Repeated
representations must be joined by exact ids/digests and validated for equality,
not treated as independent authorities.

### Compatibility is explicit and fail-closed

The affected published schemas are currently `draft`, so ADR-061 permits
reviewed in-line structural changes, but every change still needs its
per-contract publication record, content hash/change summary, generated-schema
parity, reader tests, and explicit compatibility statement. A `v1` suffix does
not by itself prove stability or old-reader compatibility.

When a workflow/profile requires explicit binding semantics, legacy
`ExperimentParameterModel` or
`ExperimentConditionAssignmentParameterModel` inputs without a descriptor are
invalid before trial compilation or runtime mutation. No adapter may infer a
plane, target, factor, condition, type, sensitivity, default, owner, or
validator from `name`, `value_kind`, prefixes, free text, matching fields,
collection order, or a selected backend.

Legacy descriptive parameters may remain accepted only on paths that make no
binding/mutation claim. Any deterministic migration must be version-pair
specific, preserve the original input, and fail on ambiguity; a best-effort
upgrade is prohibited.

## Required Incumbents

- Experiment contracts and joins:
  `ExperimentParameterModel`,
  `ExperimentConditionAssignmentParameterModel`,
  `ExperimentStudyFactorModel`,
  `ExperimentConditionAssignmentModel`,
  `ExperimentRunAllocationPlanModel`, `ExperimentSpecModel`,
  `ExperimentApparatusContextModel`, `ExperimentRunModel`,
  `_run_satisfies_condition_assignment()`, and the existing task/run/study
  semantic validators and `x-aces-invariants`.
- Scenario-family authority:
  `Variable`, `VariableTarget`, `ParameterVariationPoint`, the other closed
  variation target types, `DeclarationIndex`,
  `SemanticValidator._verify_variation_points()`, module composition,
  `instantiate_scenario()`, `admit_instantiated_scenario()`,
  `InstantiationProvenance`, and canonical instantiated snapshots.
- Participant and apparatus authority:
  `ParticipantImplementationManifestModel`,
  `ParticipantImplementationCapabilitiesModel`,
  `ParticipantImplementationSelectionModel`,
  `ParticipantImplementationProvenanceModel`,
  `ProcessorManifestV2Model`, `BackendManifestV2Model`,
  manifest authority allowlists, controlled vocabulary validation,
  `ParticipantActionAdmissionRequest`, and participant/backend protocols.
- Shared contract mechanics:
  `ContractModel(extra="forbid")`, strict Pydantic scalar types,
  `Diagnostic` / `DiagnosticModel`, `canonical_contract_digest()` RFC 8785
  semantics, `schema_bundle()`, `x-aces-invariants`, and the existing
  reference-model/concept-authority machinery where a new public concept
  binding is actually required.
- Schema and conformance:
  `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication/entries/`,
  `tools/generate_contract_schemas.py`,
  `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`,
  `raes_conformance.conformance.validators`,
  `raes_conformance.conformance.semantics`, and backend profile contract sets
  only when a backend is expected to claim the new contracts.
- Security, persistence, and public delivery:
  `ControlPlaneSecurityConfig.strict_defaults()`, read/mutating role
  dependencies, request-size guards, request fingerprints, idempotency keys,
  `AuditEvent`, `ControlPlaneStore`, bounded `HTTPException` details, and the
  redacted `{"detail": "internal server error"}` handler.
- Repository workflow:
  `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_authority_boundary.py`, `tools/check_sdl_catalog_parity.py`,
  `tools/check_semantic_coverage.py`, `tools/check_specification_coverage.py`,
  and `tools/verify_all.py`.

## Cross-Cutting Layers The Implementation Must Pass

- **Authoring/config shape:** experiment input enters closed experiment models;
  scenario targets additionally pass safe SDL parsing, phase-specific schema,
  composition/trust, portable-id, declaration collision, variation semantic,
  instantiation, and post-instantiation admission gates. Participant/apparatus
  targets pass their selected manifest and owner registry. Raw mappings never
  become configuration merely because Pydantic can parse them.
- **Factor/condition join:** every source id resolves against the exact
  experiment spec/study allocation artifact. Factor level and condition
  membership are validated before target resolution, and target resolution is
  completed for the whole binding set before any mutation.
- **Type/default/normalization:** strict scalar and finite-number validation
  runs for explicit values, manifest defaults, owner-normalized results, and
  reconstructed provenance. Default application is owner-declared behavior,
  not missing-field inference.
- **Alias/collision:** preserve canonical declarations and all aliases until
  an injective resolution is proven. Duplicate canonical targets are rejected
  before constructing dictionaries or digests, including identical-value
  duplicates.
- **Manifest/owner validation:** selected participant/apparatus identity,
  manifest digest/version, supported contracts, target registry, validator
  identity, complete realized configuration, and result digest agree. Manifest
  constraints remain disclosure only.
- **Authentication/authorization:** publishing and validating offline
  contracts adds no auth surface. Any later HTTP mutation reuses control-plane
  strict defaults, target-bound principals, mutating roles, request limits,
  idempotency/fingerprints, and audit. Experiment binding authority, caller
  authorization, apparatus support, and secret dereference authorization are
  independent gates.
- **Secret handling:** only the non-sensitive reference identity crosses the
  portable boundary. Resolved values and sensitive locator/provider details
  are excluded from models, digests, fixtures, diagnostics, provenance, audit,
  persistence, and logs. Redaction is structural, not a promise to scrub later.
- **Environment and OS exposure:** environment binding is a non-goal. Do not
  resolve target/value/secret data through environment names, arbitrary files,
  filenames, process argv, shell interpolation, stdout/stderr, or plugin
  dispatch. If a trusted owner adapter later needs a process boundary, it uses
  fixed invocation shapes, controlled working directories, bounded input via
  an appropriate protected channel, bounded timeouts, no `shell=True`, and
  redacted output handling.
- **Error envelope and observability:** expected failures use bounded
  `Diagnostic` codes, domains, JSON-pointer addresses, and safe messages or the
  existing contract/SDL error envelopes. Do not include rejected values,
  secret refs, raw Pydantic `input_value`, backend exception strings, full
  payloads, or tracebacks. HTTP 500 remains redacted; logs/audit may carry safe
  ids, contract/profile versions, digests, counts, dispositions, stages, and
  durations only.
- **Persistence and archival joins:** this issue needs no new repository,
  controller, database, cache, or mutable parameter store. Git-tracked schemas,
  fixtures, publication records, and specs are the publication audit surface.
  Live state continues through existing control-plane/runtime carriers;
  admitted intent and archival evidence continue through trial,
  instantiation, participant provenance, apparatus context, and experiment-run
  contracts.
- **Schema/conformance:** structure, cross-object semantics, canonicalization,
  and runtime owner validation are separate gates. Every new root contract is
  routed explicitly, exported publicly, registered with conformance, published
  with positive/negative fixtures, and included in applicable support
  allowlists/profiles. JSON Schema acceptance alone is not owner validation.

## Extensibility Seam

The extension seam is an owner-published configuration-target registry plus a
governed validator profile. It is parameterized by plane, owner
identity/manifest, target id and aliases, exact scalar type, default and allowed
value disposition, sensitivity, validator contract/profile version, and
normalization/digest profile.

The next reasonable change is another participant implementation target,
another portable apparatus component target, or another version of an owning
validator. It should add a declaration/validator version and fixtures behind
that seam. It must not require editing the cross-plane resolver, adding a
backend-specific field to experiment input, creating a second SDL binder, or
allowing experiment input to select executable code.

Adding an entirely new authoritative plane is a contract-lineage and
architecture change: extend the closed union, provenance, compatibility rules,
validators, schemas, and negative fixtures together. Do not admit
`x-<owner>` planes as an escape hatch.

## Gotchas And Anti-Patterns

Avoid:

- enriching `ExperimentParameterModel` while retaining name equality as the
  binding authority;
- inferring plane or target from `value_kind`, prefixes, field names, free-text
  constraints, component order, selected backend, or fallback;
- treating SDL variable names, variation-point ids, compiled resource
  addresses, participant target ids, backend option names, and environment
  names as interchangeable strings;
- binding scenario values directly to arbitrary JSON/YAML pointers, templates,
  overlays, patches, object attributes, or private compiler fields;
- using participant manifest `constraints`, apparatus
  `configuration_parameters`, backend driver config, or a private provider
  schema as a portable target registry;
- accepting duplicate canonical targets because their values match, or losing
  alias collisions through dict/set construction;
- relying on permissive union parsing, bool/int equivalence, numeric/string
  coercion, `NaN`/infinity, insertion order, or non-JCS JSON serialization;
- making defaults, normalization, validation, and digest computation separate
  mutable passes that can observe different configuration;
- hashing a resolved secret, treating a redacted scalar as a secret reference,
  putting a sensitive locator in the reference identity, or leaking rejected
  input through validation errors;
- letting an experiment choose a Python entry point, validator callable,
  provider plugin, command, environment variable, file path, or backend option
  map;
- using runtime facts to select pre-run factors/conditions, scenario variation,
  participant implementation configuration, or apparatus;
- creating duplicate target schemas, reference resolvers, canonicalizers,
  validator registries, exception hierarchies, diagnostic envelopes,
  provenance roots, configuration stores, audit streams, or conformance
  runners; and
- hand-editing generated/reference schemas without the authoritative schema,
  publication record, compatibility, fixture, and parity changes moving
  together.

## Non-Goals And Implementation Boundary

- This preflight does not implement issue #903 or downstream issues #787,
  #788, #789, #790, or #345.
- Issue #903 does not select or construct participant providers, execute or
  schedule trials, resolve secrets, mutate runtime state, or add HTTP/CLI/MCP
  execution surfaces.
- It does not define an APTL-specific allowlist, expose arbitrary backend or
  provider configuration, or make free-text manifest constraints executable.
- It does not add environment-variable binding, arbitrary filesystem paths,
  command fragments, Python entry points, templates, generic overlays,
  experiment-selected plugins, or backend-private schema injection.
- It does not persist or hash resolved secret values, and it does not turn SDL
  scenario fixture credentials into operator-secret references.
- It does not replace SDL variation/instantiation, participant action
  admission, runtime fact binding, apparatus manifests, control-plane
  security/persistence, experiment run/study provenance, or schema publication
  governance.
