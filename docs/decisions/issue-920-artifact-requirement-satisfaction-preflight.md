# Issue 920 Artifact Requirement Satisfaction Preflight

Date: 2026-07-27

Issue: #920. Requirement: none. The GitHub issue is the authoritative delivery
contract.

This note records architecture guardrails only. It does not add SDL syntax,
publish a schema, implement resolution or acquisition, select a backend
adapter, or prescribe an implementation sequence.

## Preflight Finding

The repository already owns the required cross-cutting semantics, but no single
artifact contract joins them:

- `Source` is a provider-neutral artifact selector and `Source.build` records
  observed container build/provenance facts.
- SEM-218 owns exact, constrained, open, and omitted author intent across
  validation, compilation, planning, execution, and disclosure.
- backend `realization_support` owns apparatus capability claims.
- associated-artifact manifests and reusable-asset policy own byte integrity,
  authenticity, provenance, and admission evidence.
- runtime realization provenance and experiment-run realized-form disclosures
  own live and archival disclosure.

The intended design joins those authorities. It must not turn `Source.build`
into an executable recipe, use acquisition as authority, put mutable registry
facts into scenario identity, or add a second realization, trust, diagnostic,
or persistence stack.

## Architecture Decisions And Guardrails

### Publish one semantic family with phase-distinct carriers

The portable surface is one versioned artifact-requirement-satisfaction
semantic family with closed, phase-appropriate carriers:

- the **requirement** records author authority and acceptable satisfaction;
- the **capability declaration** records what an apparatus claims it can
  satisfy; and
- the **satisfaction disclosure** records the artifact and mechanism actually
  used.

These carriers share identifiers and validation rules but are not one mutable
object. Authored requirements do not acquire backend output fields, backend
manifests do not restate author intent, and runtime/archival records do not
rewrite the instantiated scenario. This preserves ADR-008 and ADR-078 phase
boundaries.

The contract belongs to the existing `Source` realization concern rather than
to a new top-level artifact graph. `Source` remains the provider-neutral
artifact identity/selector component. The artifact requirement owns authority
over that component; it does not redefine nodes, content, generated artifacts,
associated artifacts, or environment-pack layout.

### Preserve the four author postures without a second taxonomy

Artifact posture reuses SEM-218:

- **exact** identifies exactly one immutable artifact. A backend either uses
  that identity or rejects. Rebuilding, substituting, approximating, or choosing
  an equivalent artifact is not satisfaction.
- **constrained** declares a non-empty candidate/domain surface from which the
  backend may choose. Every selected artifact must satisfy all declared bounds.
- **open** explicitly delegates artifact choice at an admitted `Source`
  realization point and may still constrain permitted mechanisms, timing,
  trust, or input requirements.
- **absent** is the owning optional `Source` requirement being absent. It is not
  another positive union member and does not authorize backend choice. A
  backend may use implementation-private artifacts, but they do not become
  authored scenario meaning or a satisfaction of a nonexistent requirement.

Do not add an artifact-only posture enum. `ExplicitnessClass`,
`AuthorRealizationPosture`, the typed designation cascade, and
`ExplicitnessProvenance` remain canonical. The compiler must register the
artifact concern with the existing SEM-218 concern authority instead of
inferring posture from whether a name, tag, URI, build block, or backend image
is present.

The existing `Source` shorthand and default `version="*"` are selectors, not
proof of immutable exact identity. A contract may classify a selector as
constrained, but it must not call it exact unless the authored form binds one
immutable identity using the existing digest/reference discipline. Any change
to legacy interpretation must be explicit, versioned, fixture-backed, and
reviewed under ADR-061; generic field-presence classification must not silently
promote `"*"` or a mutable tag to exact.

Alternatives are author authority. An exact branch cannot gain implicit
fallbacks from a catalog, backend policy, materialization capability, or
`Source.build`. Candidates or alternative specifications exist only in a
constrained requirement that names them.

### Keep satisfaction, acquisition, timing, and availability independent

A satisfaction mechanism is not an acquisition verb. The core contract must
therefore carry these as separate dimensions:

- **mechanism**: an exact artifact, backend-owned artifact, published candidate,
  dynamic composition, explicitly permitted materialization specification, or
  another declared mechanism;
- **acquisition**: pull, copy, import, local lookup, or no transfer;
- **timing**: publication, pack ingestion, explicit backend preparation, or
  realization; and
- **availability**: provider/account/project/region/registry/channel facts.

Mechanisms are an open governed extension surface, not a closed Python/JSON
union. A mechanism has a portable namespaced identifier plus an exact
profile/contract version (and digest where it references a published
specification). An unfamiliar mechanism can remain structurally valid but is
unrealizable unless the selected backend declares that exact mechanism
profile. Mechanism-specific payloads are closed versioned profiles; arbitrary
`options`, callback names, commands, or backend-native dictionaries are not a
portable extension mechanism.

Acquisition and timing are disclosures/constraints on a satisfaction; neither
selects semantic authority. A pull can acquire an exact artifact, a candidate,
or an input. A dynamically composed artifact may use no transfer. Artifact type
must not imply timing.

Availability is operational evidence and must not enter the scenario semantic
digest, exact requirement identity, candidate identity, or published-output
identity. Mutable locators and channels may be disclosed through their existing
operational/evidence surface, but identity joins use immutable refs and
digests. Credentials, entitlement, account/project selection, and registry
policy remain operator/product concerns.

### Extend the existing realization and manifest seams

Artifact requirements lower into `CompiledRealizationRequirement` (or a typed
artifact payload owned by it) with the canonical owner address, field path,
requirement kind, SEM-218 posture/provenance, governing scope, and requirement
identity. Do not add a second compiled requirement list or an artifact-only
planner.

Backend support stays under `BackendManifest.realization_support` and
`BackendManifestV2Model.realization_support`. The artifact domain needs
mechanism-indexed capability declarations that preserve the existing exact,
constraint, and open matching rules. Each mechanism entry must declare its
supported requirement kinds and supported timing/acquisition combinations.
A collection of independent mechanism, timing, and acquisition lists is
insufficient because it falsely claims their Cartesian product.

Portable mechanism/profile identifiers that require cross-backend comparison
must bind to the existing `realization-and-disclosure` and
`tools-and-artifacts` concept authorities. Product catalog policy and backend
native driver names are not RAES mechanism identifiers.

Planning remains conjunctive. A requirement is realizable only when its posture,
artifact/candidate bounds, locked inputs, permitted mechanism, mechanism
profile, timing, and selected backend declaration all agree. A realization
envelope may further restrict the offer; it does not replace artifact
requirement matching.

### Keep materialization specifications and build observations distinct

`Source.build` remains the ADR-023 observation surface. It may support
provenance or trust evidence about a published artifact, but it is not:

- a universal recipe;
- a backend instruction;
- permission to rebuild an exact artifact;
- a materialization alternative; or
- proof that referenced inputs are present, trusted, or reproducible.

An executable materialization specification participates only when the authored
requirement explicitly permits its versioned mechanism profile. Its locked
inputs use immutable artifact references/checksums and the existing
associated-artifact/trust validators. It does not embed credentials, registry
tokens, host paths, shell text, environment dumps, or unbounded external fetch
instructions.

Module `LockRecord` and `ResolvedImportProvenance` are useful digest/portability
incumbents but remain module-specific. Reuse their primitives and fail-closed
rules; do not relabel a module lockfile as a universal artifact input lock.

### Reuse diagnostics and distinguish realizability failures

All failures use the existing `Diagnostic` / `DiagnosticModel` envelope and
normal planner/runtime failure flow. The artifact domain must expose stable,
separately testable codes for at least:

- unavailable exact artifact;
- unsatisfied artifact constraint;
- unsupported open artifact realization;
- missing or unverified locked input;
- unavailable published candidate; and
- unsupported backend mechanism/profile.

These are not exception subclasses and must not collapse into
`not-found`, `build-failed`, or a generic `unsupported` string. A supported
mechanism that fails during execution still uses the ordinary backend-call or
operation failure surface; capability absence and execution failure are
different facts.

Diagnostics name the canonical requirement/address, posture, mechanism/profile,
and failure class. They do not echo credentials, signed URLs, raw selectors,
candidate inventories, locked-input contents, backend-native objects, process
output, or exact values that may be sensitive.

### Disclose satisfaction without changing scenario identity

A successful satisfaction disclosure binds:

- the exact requirement identity;
- the immutable realized artifact identity;
- the selected mechanism profile;
- acquisition and timing;
- the satisfying candidate/materialization/input refs where applicable;
- the backend/apparatus identity; and
- provenance, integrity, authenticity, admission, and evidence refs.

The live carrier is a typed artifact-specific payload on, or exact reference
from, the existing `RealizationProvenanceEntry` ledger. It is not
`RuntimeSnapshot.metadata`, `ApplyResult.details`, a backend-private result, or
a second snapshot sidecar. The runtime non-approximation gate in
`realization_disclosure()` remains the acceptance boundary before a backend
snapshot is persisted.

Archival runs reuse `ExperimentRunModel.realized_form_disclosures` and their
evidence traceability. If an artifact-specific shared component is needed, both
live and archival carriers reference that one component rather than copying
similar field sets. A new experiment-run root or provenance database is
forbidden.

The realized/published output identity is realization provenance, not scenario
meaning. Selecting a candidate, composing an artifact, changing a registry
location, or promoting a mutable channel does not rewrite
`canonical_sdl_digest()`, `canonical_instantiated_sdl_digest()`, or the
instantiated scenario snapshot. An exact authored artifact identity remains
part of the requirement's meaning; a backend-selected output remains outside
that meaning.

## Canonical Incumbents To Reuse

- **Source and SDL shape:** `raes._source.Source`, the parser's scoped
  `_expand_source()` shorthand, `SDLModel(extra="forbid")`, every existing
  `Source | None` owner, the authored/instantiated phase models, and the SDL
  schema/fixture families.
- **SEM-218 authority:** `raes.explicitness`, `raes.realization_designation`,
  `ExpansionProvenance`, `InstantiationProvenance`,
  `ExplicitnessProvenanceRecord`, `SemanticValidator`,
  `SDLValidationError`, and `SDLInstantiationError`.
- **Compilation and planning:** `CompiledRealizationRequirement`,
  `registered_realization_concerns()`,
  `_compile_realization_requirements()`,
  `realization_support_diagnostics()`,
  `realization_envelope_diagnostics()`, `ExecutionPlan`,
  `ProvisioningPlan`, and canonical compiled addresses.
- **Backend manifests:** `RealizationSupportMode`,
  `RealizationSupportDeclaration`,
  `RealizationSupportDeclarationModel`, `BackendManifest`,
  `BackendManifestV2Model`, `backend_manifest_v2_model()`,
  `backend_manifest_from_v2_model()`,
  `BACKEND_SUPPORTED_CONTRACT_IDS`, concept bindings, and backend profiles.
- **Runtime boundary:** `realization_disclosure()`,
  `_call_backend_apply()`, `_snapshot_contract_diagnostics()`, `ApplyResult`,
  `RuntimeSnapshot`, `RealizationProvenanceEntry`,
  `RuntimeSnapshotEnvelopeModel`, operation receipts/statuses, and baseline
  snapshot rollback on invalid backend output.
- **Trust and artifacts:** `AssociatedArtifactManifestModel`,
  `validate_associated_artifact_manifest()`,
  `ExperimentArtifactRefModel`, `ExperimentChecksumModel`, ADR-071 reusable
  asset evidence classes/policy, module registry trust/signature verification,
  and URI credential/query rejection.
- **Observation and archival provenance:** `ExperimentRunModel`,
  `ExperimentRealizedFormDisclosureModel`, experiment evidence refs,
  apparatus manifest refs, and ADR-065/066 provenance/evidence separation.
- **Persistence and API:** `ControlPlaneStore`,
  `LocalControlPlaneStore._atomic_write()`, snapshot serializers,
  `ControlPlaneSecurityConfig`, request-size guards, role authorization,
  idempotency fingerprints, `AuditEvent`, and redacted HTTP 500 envelopes.
- **Host execution security:** the reference OCI driver's `ImageTrustPolicy`,
  fixed argv, runtime allowlist, bounded timeout, injected runner, rollback,
  and native-output redaction. A future mechanism adapter must meet the same
  boundary without making that OCI driver normative.
- **Contract publication:** ADR-009/019/061,
  `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication/entries/`,
  `contracts/schema-publication-manifest.json`, `ContractModel`,
  `schema_bundle()`, and `x-raes-invariants`.
- **Repository workflow:** `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`,
  `tools/check_authority_boundary.py`,
  `tools/check_concept_authority_governance.py`,
  `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_sdl_catalog_parity.py`,
  `tools/check_sdl_lineage.py`, `tools/check_json_artifacts.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers The Design Must Pass

| Layer | Required behavior |
|---|---|
| YAML/source parsing | Continue through the bounded source reader, duplicate-key/tag/alias/scalar guards, scoped shorthand normalization, and closed Pydantic models. Nested mechanism/specification fields named `source` must not be accidentally rewritten by `_expand_source()`; update the canonical scoped rule rather than adding a second parser. |
| SDL semantic validation | Validate owner applicability, exact/constrained/open/absent exclusivity, immutable exact identity, non-empty constrained domains, candidate/ref uniqueness, locked-input joins, canonical pointers/addresses, and composition namespace rewriting through `SemanticValidator`. |
| Phase and digest validation | Preserve posture and requirement identity through expansion/instantiation provenance and compiler admission. Backend-selected artifacts, availability, acquisition, and mutable locations remain outside scenario semantic identity. |
| Contract/schema validation | Use closed `ContractModel` shapes, hand-governed published schemas, semantic invariants, valid/invalid fixtures, schema-bundle parity, publication-ledger updates, and ADR-061 compatibility review. Schema validity alone is not realizability or trust. |
| Manifest/config validation | Extend the canonical backend manifest renderer/parser and manifest-authority allowlist. Capability claims must pass model/schema shape, concept binding, contract-version, profile, and backend-profile validation; no backend-local environment flag or prose `constraints` entry substitutes for a typed mechanism declaration. |
| Trust/admission validation | Bind exact artifacts, candidates, specifications, and locked inputs to immutable checksum/digest refs; run associated-artifact byte/size validation and reusable-asset integrity/authenticity/provenance policy. URI or name equality is not byte, signature, entitlement, or admission proof. |
| Planner admission | Match the compiled requirement against one backend declaration without first-match/first-available fallback. Emit the required distinct `Diagnostic` codes before backend I/O when capability, candidate, input, constraint, mechanism, or timing is unsatisfied. |
| Runtime adapter validation | Admit backend results through `_call_backend_apply()` and `realization_disclosure()` before accepting the snapshot. Exact mismatches, undeclared mechanisms, missing satisfaction disclosure, and contradictory artifact identity fail closed and restore the baseline snapshot. |
| Persistence | Round-trip typed satisfaction provenance through `RuntimeSnapshot`, `ControlPlaneStore`, local atomic writes, and published snapshot models. Do not create an artifact resolver repository, sidecar file, cache index, or metadata-only ledger in this issue. |
| HTTP/auth and audit | No new endpoint is required. Any existing snapshot/operation exposure inherits strict identity defaults, role checks, target scoping, request-size limits, idempotency, audit events, and redacted 500 responses. Audit details carry ids/codes only, not selectors, locators, credentials, or raw materialization payloads. |
| Secret/env/config handling | Portable requirements, manifests, fixtures, provenance, and diagnostics are secret-free. Credentials and entitlement stay in operator-owned backend configuration. Do not add credential fields, environment bindings, token refs, signed URLs, or secret materialization parameters to the portable contract. |
| OS/process exposure | Immutable non-secret artifact refs may be discrete argv values only at a backend's impure leaf. Preserve fixed argv, no shell evaluation, bounded timeouts, allowlisted executables/runtime, injected runners, coarse diagnostics, and no credentials or raw backend output in argv/logs. |
| Observability and archival evidence | Use structured `Diagnostic`, `AuditEvent`, realization provenance, experiment evidence, and experiment-run disclosures. Do not add a general logger payload, claim that a manifest proves execution, or treat a planned/echoed value as fresh realization evidence. |
| Conformance/testing | Reuse SEM-218, backend-manifest, runtime-planner, runtime-contract, associated-artifact, trust, schema, and realization-honesty suites. Matrix/property tests must vary posture, mechanism, acquisition, timing, availability, trust, and exactness independently so accidental axis coupling is observable. |

## Extensibility Seam

The extension seam is a versioned mechanism-profile reference carried through
the requirement, backend mechanism capability matrix, compiled realization
requirement, and satisfaction disclosure. The matcher is parameterized by
artifact requirement kind, canonical owner/address, mechanism profile, timing,
and immutable input/candidate refs.

A future artifact class or satisfaction mechanism adds its closed profile,
concept binding, backend declaration, validator, and conformance evidence. It
does not edit a closed pull-versus-build union, add a backend name to SDL,
change `Source.build`, or fork planner/runtime matching. This admits the next
reasonable mechanisms—such as another backend-native composer or prepared
artifact form—without changing the core posture contract.

## Gotchas And Anti-Patterns

Avoid:

- treating pull and build/materialize as opposites or the complete mechanism
  set;
- treating acquisition, timing, availability, location, or channel as semantic
  authority;
- treating a tag, default `"*"`, URI, backend-local id, or successful lookup as
  immutable exact identity;
- allowing an exact requirement to fall back to candidates, composition,
  reconstruction, approximation, or an equivalent artifact;
- turning absence into open realization, or an implementation-private artifact
  into authored meaning;
- using `Source.build` as executable input or accepting raw Dockerfile/shell
  text as a portable mechanism;
- embedding credentials, entitlement, provider/account/project/region,
  environment variables, host paths, commands, or opaque options in the
  portable contract;
- flat capability lists whose accidental Cartesian product overclaims supported
  mechanism/timing/acquisition combinations;
- first-available candidate selection, order-dependent fallback, or
  backend-specific policy in RAES semantics;
- putting satisfaction only in `metadata`, `details`, logs, or backend-native
  state;
- minting a second explicitness classifier, artifact planner, trust policy,
  checksum type, diagnostics hierarchy, exception family, persistence store,
  audit log, schema registry, or experiment-run root;
- copying live satisfaction fields independently into archival provenance;
- changing scenario or snapshot semantic identity when only a realized output,
  availability fact, registry location, or mutable channel changes; and
- declaring backend conformance from schema validity, a manifest claim, planned
  state, or echoed output without runtime rejection tests and provenance.

## Non-Goals And Implementation Boundaries

- No registry, catalog, build farm, hosted service, credential broker,
  entitlement service, or operated distribution channel.
- No environment-pack layout, release packaging, publication tooling, or
  downstream catalog policy.
- No requirement that every scenario/node has an image or that every artifact
  is reproducible, materializable, or transferable.
- No product-specific resolution order, candidate ranking, preparation timing,
  VM-image policy, or backend adapter implementation.
- No new SDL topology, content, generated-artifact, associated-artifact, trust,
  experiment-run, or runtime-lifecycle authority.
- No universal recipe model and no reinterpretation of `Source.build`.
- No new API endpoint, auth mode, secret/config surface, persistence service,
  background resolver, or external network operation.
- No implementation code, schema, fixture, manifest, vocabulary, example, or
  conformance change in this preflight.
