# Issue 1067 resolved-realization-posture handoff preflight

Status: accepted implementation architecture record for issue #1067.
This record is not a second realization authority; it documents the portable
projection implemented by the compiler, planner, published contract, runtime,
and control-plane gates.

## Decision summary

The realization cascade itself is already authoritative. The missing boundary
is its portable, execution-facing projection.

The backend-facing `ProvisioningPlan` contract must carry one closed, typed,
plan-level collection of **resolved realization-authority entries**. The
collection is complete for every canonical scenario-realization concern that
applies to every non-delete planned provisioning resource. This includes
concerns whose effective result is closed and whose value is therefore absent
from the operation payload. It is adjacent to operations and the selected
realization-envelope identity; it is not embedded in
`PlannedResource.payload`.

Completeness is derived, not asserted by the producer. The validation universe
is the canonical concern registry, including each descriptor's applicability
rule, bound through the compiler's canonical resource identities to the
non-delete provisioning operations, plus the processor-derived provisioning
concerns named in `CONCERN_PAYLOAD_PATH`. A caller-supplied `complete` flag,
count, or digest cannot substitute for recomputing that set.
Orchestration/evaluation requirements and source-artifact requirements remain
on their owning plan or contract; they are not copied into the provisioning
authority collection.

Each entry is a realization-value-free projection of the existing
`RealizationResolution`, `CompiledRealizationRequirement`, compiled capability
constraints, and canonical concern descriptor. It carries only the portable
facts a backend needs:

- the canonical concern identity: compiled resource `address`, semantic
  `field_path`, realization `domain`, and `requirement_kind`;
- the canonical operation-payload location: the descriptor's `payload_path`
  for a registered authored concern or the existing `CONCERN_PAYLOAD_PATH`
  entry for a processor-derived concern, encoded once as an RFC 6901 pointer
  so downstream adapters do not copy the concern/path table;
- one resolved effective mode: closed, open, constrained, or exact;
- the stable governing scope and resolution source, including whether the
  effective decision came from an authored leaf/scope, an apparatus default,
  the legacy closed fallback, or deterministic processor derivation; and
- for constrained concerns, the typed author bounds required to admit a
  backend choice. Reuse the existing `DomainDescriptor` algebra and the
  existing compiled finite/value-constraint records. A free-form constraint
  map or a bare `constrained` label is insufficient. Because general SDL
  variable domains have no secret-classification metadata, only
  concern-approved, publication-safe domains may cross this contract; do not
  mechanically serialize arbitrary `allowed_values`.

Delegation is an origin of a resolved decision, not a fifth effective mode.
No unresolved `unspecified`, nullable permission, backend callback, or
authoring designation table may cross the execution handoff. The selected
apparatus default is resolved during planning, while the fact that it supplied
the decision remains in the entry. The implementation may choose the exact
closed Pydantic representation, but it must encode the four effective cases as
a discriminated, invalid-combination-resistant contract rather than as loosely
related booleans.

The normal operation payload remains the source for an exact selected value.
The authority entry must not duplicate exact values, environment material,
credentials, source bodies, artifact mechanisms, or backend-native data.
Structured constraints such as process resource limits retain their existing
semantic record identities and typed leaf bounds.

This does not require a new ADR. ADR-008 fixes the compile/plan/execute
boundary, ADR-009 fixes normative schema authority, and ADR-061 governs the
published schema migration. ADR-070 separates author permission, bounded
envelopes, and backend capability. ADR-078 keeps authoring machinery out of
executable shapes, while ADR-098 keeps artifact requirements on their owning
contract. This record selects the minimum carrier needed to close the gap
between those accepted decisions.

## End-to-end trace and exact loss points

| Phase | Current canonical carrier | Result |
| --- | --- | --- |
| Parse and authoring | `Scenario.realization`, `AuthorRealizationPosture`, `RealizationScopeDesignation` | Typed closed/open/unspecified authoring input is distinct from backend capability. No loss. |
| Expansion and imports | `composition._expand`, the symbol map, qualified namespace tuples, and `ExpansionProvenance.realization_designations` | Imported pointers are rewritten and namespace-qualified. Import order is not specificity. No loss. |
| Instantiation | `instantiate_scenario`, `InstantiationProvenance.realization_designations`, capability constraints, and explicitness records | Authoring-only fields are removed, derivation records survive, and the concrete scenario is revalidated. No loss. |
| Semantic validation | `SemanticValidator._verify_realization_designations` and `resolve_json_pointer_surface` | Namespace ownership and RFC 6901 scope targets are checked against typed SDL surfaces. No loss. |
| Compilation | `registered_realization_concern_descriptors`, `resolve_realization_designation`, and `CompiledRealizationRequirement` | Explicit exact/constrained/open leaves and open/delegated omissions become demands. **First loss:** concrete closed and legacy-closed omissions return `None`, so the complete denial boundary disappears. |
| Planning | `materialize_realization_requirements`, `realization_support_diagnostics`, `realization_envelope_diagnostics`, and `ExecutionPlan.model.realization_requirements` | Delegation is resolved and capability/envelope checks run. **Second loss:** delegated-closed requirements disappear and delegated-open requirements are rewritten with `delegated=False`, losing authority origin. The effective requirements remain only on the composite internal model. |
| Provisioning plan construction and projection | `ProvisioningPlan`, `ProvisioningPlanModel`, and `provisioning_plan_model` | Operations and realization-envelope identity are carried. **Third loss:** no resolved realization boundary is projected; `plan_projection` deliberately excludes the compiled model. |
| Reference and libvirt adapters | their pure `interpret_provisioning_plan` functions and the shared `planned_*` readers | Both reconstruct desired resources from plan payloads. Surrounding admission paths, and specifically libvirt's provisioner, also consult capability/envelope state. Neither adapter can reconstruct closed omission, governing scope, or leaf precedence from the plan. Capability can therefore be mistaken for permission. |
| Direct runtime-manager execution | `_RealizationApplyContext` and `realization_disclosure` | The in-process composite path retains requirements out of band and can enforce non-approximation and emit provenance. This is useful defense, but it is not a portable handoff and must not remain a second authority. |
| HTTP/control-plane execution | `ProvisioningPlanModel`, `_provisioning_plan`, `_submitted_plan_diagnostics`, and `execute_operation` | **Fourth loss:** the published DTO cannot carry authority, the reverse converter cannot restore it, and `execute_operation` calls the backend without requirements or manifest in the realization apply context. Runtime disclosure is consequently skipped on this path. |
| Snapshot and persistence | `realization_disclosure`, `sanitize_realization_snapshot`, `RuntimeSnapshot.realization_provenance`, `_snapshot_payload`, and `_snapshot_from_payload` | Provenance and safe observations round-trip when disclosure ran. They cannot reconstruct the authority that was absent from a remote plan, and persistence must not become a compensating posture ledger. |
| Downstream APTL | No APTL adapter exists in this repository; ADR-063 identifies APTL as a downstream plan consumer. | The only portable input available here is `provisioning-plan-v1`, which lacks the boundary. An external adapter cannot recover it without reimplementing authoring semantics. |

## Semantic and validation invariants

1. **One resolution authority.** Scope resolution remains
   `resolve_realization_designation`; leaf classification remains the SEM-218
   explicitness records; concern enumeration and payload paths remain the
   realization-concern registry. The plan carrier is a projection of those
   results, never another resolver.
2. **Complete denial information.** Closed omissions are affirmative denial
   records. They must survive compilation and planning even though they are not
   realization demands and have no operation-payload value.
3. **Leaf precedence.** An exact or constrained authored leaf remains effective
   beneath an open scope. A backend cannot replace it merely because its domain
   advertises `OPEN_REALIZATION`.
4. **Resolved delegation.** Apparatus policy may resolve an explicit delegated
   concern, but the handoff records both the effective result and its
   apparatus-default origin. Omitted realization designation continues to mean
   legacy closed, not delegated.
5. **Intersection, not substitution.** A backend selection is admitted only by
   the intersection of the resolved author authority, matching
   `RealizationSupportDeclaration`, and the full selected realization envelope
   whose immutable identity is already on the plan. `OPEN_REALIZATION` and an
   offered open envelope never create author permission.
6. **Typed constrained bounds.** A constrained backend choice must pass the
   author domain using the existing bounded-domain membership semantics. If a
   constrained concern cannot be represented by an existing portable typed
   domain or value-constraint contract, planning fails closed; it must not emit
   an unbounded label or prose constraint.
7. **Referential integrity.** Authority identities are unique. Each entry
   references a registered concern and a non-delete desired operation/resource
   with the same canonical address. Delete operations do not inherit stale
   authority from a prior snapshot. The payload pointer is the one owned by the
   canonical concern registry. Completeness is recomputed from that registry
   and the plan's non-delete resource types; a producer-declared completeness
   marker is not trusted.
8. **No excess scenario state.** A returned scenario concern at a closed entry
   is a backend-contract failure. A backend-filled value at an open or
   constrained entry is accepted only after capability, envelope, typed-domain,
   projection, and evidence checks. Unknown or additional state in a scenario
   resource payload is not legitimized by a broad open scope.
9. **Backend/apparatus state has a different owner.** Driver handles, native
   identifiers, transformation evidence, apparatus defaults, and operational
   metadata remain in backend-private state or their existing typed manifest,
   envelope, artifact-satisfaction, observation, audit, or snapshot-metadata
   contract. They are not scenario state and are not added to a
   `SnapshotEntry.payload` under author permission.
10. **One runtime evidence input.** Once a plan exists, runtime disclosure and
    non-approximation consume its resolved boundary directly. The internal
    compiled requirements may remain the planning source, but a separate
    runtime requirements argument must either be removed as authority or be
    proven identical to the plan projection before mutation. Provenance is
    derived from the exact admitted entry; it is never reconstructed from the
    returned value or backend manifest.
11. **Boundary presence is mandatory.** A compliant execution endpoint rejects
    a boundary-free or partially enumerated plan. An optional field with an
    empty default would recreate the vulnerability. `provisioning-plan-v1` is
    currently draft under ADR-061, so an in-place coordinated draft evolution
    is permitted; if an external compatibility promise exists, mint the next
    contract id. In either case, contract authority declarations, profiles,
    schemas, fixtures, and consumers move atomically, and no legacy adapter may
    infer missing permission from capability.

## Canonical incumbents and cross-cutting concerns

| Concern | Canonical incumbent to reuse | Guardrail |
| --- | --- | --- |
| Authoring shape | `raes.realization_designation`, `Scenario.realization`, `SDLModel(extra="forbid")` | Do not expose `Scenario.realization` or unresolved designation records to backends. |
| Composition and namespaces | `composition._expand`, symbol-map pointer rewriting, `QualifiedName`, and provenance namespace tuples | Preserve module ownership and most-specific pointer-then-namespace selection; do not split dotted strings or use import order. |
| Semantic validation | `SemanticValidator`, `resolve_json_pointer_surface`, phase-contract uniqueness validators | Do not add backend-local scope parsing or duplicate conflict rules. |
| Leaf specificity | `ExplicitnessClass`, `ExplicitnessProvenance`, and instantiated explicitness records | Do not reinterpret exact/constrained/open from concrete values after substitution. |
| Concern inventory | `RealizationConcernDescriptor`, `registered_realization_concern_descriptors`, `CONCERN_PAYLOAD_PATH`, and projector/sanitizer/observation hooks | Extend the registry for a new concern; never duplicate kind-to-payload mappings in adapters, tests, or DTO converters. |
| Compiled semantics | `CompiledRealizationRequirement`, `RealizationResolution`, `CompiledCapabilityConstraint`, `RealizationValueConstraint` | Produce the complete boundary beside the existing demand graph; do not force closed denial into the demand type or serialize the internal dataclass wholesale. |
| Constraint algebra | `raes_contracts.bounded_domains.DomainDescriptor` and `scalar_in_domain`, plus the existing structured process-limit identity rules | Do not create string constraints or backend-specific bound schemas. |
| Plan ownership | `raes_contracts.planning.ProvisioningPlan`, `PlanOperation`, plan identity validators, and the total `planned_*` readers | The plan owns authority; resource payload stays desired scenario state. Add one total concern lookup/view rather than per-backend traversal logic. |
| Published projection | `raes_contracts.contracts.realization_plans`, `plan_projection`, `control_plane_api_models._provisioning_plan`, `contracts/bundle.py` | Forward and reverse conversion must be lossless and differential-tested. Under ADR-009, the hand-governed normative schema remains authoritative and the closed Pydantic model must match it exactly. |
| Capability and envelope | `BackendManifest`, `RealizationSupportDeclaration`, `realization_support_diagnostics`, `realization_envelope_diagnostics`, ADR-070 `member`/`subsumes`, and `RealizationEnvelopeIdentityModel` | Capability and offered set are additional gates, never sources of author permission. Do not copy the full backend envelope into the plan; resolve it by its digest-checked identity. |
| Runtime enforcement | `_call_backend_apply`, `_finalize_backend_apply`, `realization_disclosure`, `evaluate_registered_realization`, concern projectors, and `sanitize_realization_snapshot` | Validate after backend return and before accepting or persisting the snapshot; preserve baseline snapshot on failure. |
| Provenance and evidence | `RealizationProvenanceEntry`, `RealizationObservationDisclosure`, artifact-satisfaction disclosure, and ADR-066 evidence ownership | Reuse the admitted entry's identity/mode/scope/source. Do not put raw values in provenance or claim backend self-report alone is corroboration. |
| Persistence | `LocalControlPlaneStore`, `_snapshot_payload`, `_snapshot_from_payload`, tempfile-plus-`os.replace`, and credential projection | Preserve safe provenance and observations atomically; do not add a posture sidecar or store raw plan secrets. |
| Diagnostics and observability | `Diagnostic`, `OperationReceipt`, `OperationStatus`, `AuditEvent`, and the API response helpers | Use stable codes and value-free paths/kinds/scopes. Do not add a logger/metric stream or a realization-specific exception hierarchy. |
| Conformance tests | `test_sem_218_realization_designation.py`, `test_sem_218_realization.py`, `test_sem_218_runtime_realization.py`, issue 985/1066 concern tests, plan-projection tests, control-plane API tests, and published plan fixtures | Extend the existing semantic matrices and forward/reverse differential tests; do not build a second backend-only conformance harness. |
| Published schema workflow | `contracts/schemas/plans/provisioning-plan-v1.json`, plan fixtures, schema-publication entry/manifest, `generate_contract_schemas.py`, `check_generated_schemas.py`, `check_schema_publication.py`, and manifest/profile contract-id authority sets | Treat the normative schema, matching model, fixtures, publication hash, and authority declarations as one governed surface. Update none of them in isolation. |
| Repository workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, requirement-governance checks, and `tools/verification_plan.py` | Run the governed implementation workflow with `RAES_REQUIREMENT_UID=SEM-218` when the branch name lacks that UID; do not hand-bypass traceability or contract gates. |

## Security and host-boundary review

The intended carrier crosses these existing gates:

- **SDL parser/model/semantic gates:** the carrier adds no authoring input and
  therefore does not relax YAML size/alias/tag checks, key normalization,
  closed Pydantic models, reference validation, or designation scope
  validation. Every source fact must already have passed `parse_sdl`,
  instantiation revalidation, and `SemanticValidator` before projection.
- **Plan shape gates:** internal `ProvisioningPlan.__post_init__`, published
  `ContractModel(extra="forbid")`, compiled-address/domain/resource validators,
  and new authority uniqueness/referential/completeness invariants all fail
  closed. Unknown fields and invalid mode/source/bound combinations remain
  structural errors, not ignored hints.
- **Control-plane authentication and request gates:**
  `ControlPlaneSecurityConfig.strict_defaults`, bearer or trusted-proxy
  identity handling, backend/operator mutating roles, request-size guards,
  Pydantic request validation, and raw-body idempotency fingerprinting remain
  unchanged. Authentication identifies a relay but does not attest that the
  body came from the planner, and the idempotency fingerprint is not a
  signature. The HTTP adapter therefore canonicalizes the submitted plan and
  admits operation-bearing requests only when that exact digest was registered
  from a planner-produced `ProvisioningPlan` through the in-process control
  boundary. BACKEND and OPERATOR principals may relay a registered artifact;
  neither role can register, rewrite, or mint its authority through HTTP. The
  reference registry is intentionally in-memory, so a restarted adapter must
  receive the trusted planner artifacts again before accepting their relay.
- **Submission policy gates:** `_submitted_plan_diagnostics`, manifest identity
  and capability validation, realization support, envelope identity, artifact,
  topology, materialization, credential, and stateful-resource gates continue
  to run. Boundary validation complements them; it does not bypass or duplicate
  them.
- **Secret-handling gates:** authority/provenance/diagnostics carry no realized
  or duplicated exact values; safe typed constraint domains are the only value
  material admitted by the authority contract. Exact values remain only in
  their owning operation contract. The generic variable model's
  `allowed_values` has no sensitivity classification, so it is not itself a
  safe serialization source. Protected
  runtime environment and mount values continue through concern commitments
  and sanitizers; account credentials continue through
  `value_free_account_placement_payload`; artifact mechanism details remain in
  the artifact-requirement/satisfaction contracts. Never include raw parameter
  bindings, allowed domains containing secret material, credentials, source
  bodies, host paths, or realized values in diagnostics, audit reasons, or
  provenance. A constraint that cannot be safely published must fail or use an
  existing opaque/owning contract, not leak through this carrier.
- **Backend result and persistence gates:** `ApplyResult`, address transition,
  observation shape/strength, non-approximation, snapshot sanitization, and
  safe persistence run before a returned snapshot becomes current. A malformed
  or excess realization returns the existing coarse
  `runtime.backend-contract-invalid` diagnostic and preserves the baseline.
- **API error envelopes:** request validation remains the redacted 422
  `request validation failed`; catch-all responses remain a generic 500 with
  only exception type in audit reason; planner/runtime failures remain bounded
  `Diagnostic` payloads. Do not echo the invalid authority item or its bounds.
- **OS/process exposure:** posture records are in-memory/JSON policy and must not
  be forwarded into process argv, environment variables, libvirt metadata,
  container labels, or backend-native object names. When an admitted selection
  is materialized by an existing native driver, its current fixed-argv,
  validated-runtime-name, timeout, no-shell, redaction, and trust-policy rules
  still apply. This issue adds no secret file, configuration environment
  binding, socket, port, privilege, or host-path surface.

## Extensibility seam

The seam for the next realization concern is the canonical concern registry.
`RealizationConcernDescriptor` owns the authored path, concern kind, payload
path, applicability, projection/sanitization, and evidence needs.
`CONCERN_PAYLOAD_PATH` adds the canonical locations for processor-derived
concerns. The bound compiler record supplies the authority entry. A single
plan-level total lookup by canonical concern identity supplies reference,
libvirt, and downstream APTL adapters. Adding a concern must extend this
canonical inventory, not another adapter-local path table.

The seam for another constraint form is the existing closed
`DomainDescriptor` union (or an existing concern-owned typed value-constraint
contract for structured values). The seam for another backend configuration is
the selected realization-envelope identity and the manifest's digest-checked
full envelope. Neither seam permits backend-name branches.

The reference HTTP adapter resolves an exact canonical plan digest against an
in-memory registry populated at its trusted in-process planner boundary. If
execution later needs durable cross-restart authorization, the existing
control-plane operation store is the seam for atomically persisting the
canonical admitted plan or its trusted reference. It must not reconstruct
authority from an idempotency fingerprint, snapshot payload, or untrusted
caller-provided digest.

## Conformance obligations

Conformance must exercise the same published plan through direct projection,
JSON/schema round-trip, control-plane reverse conversion, backend
interpretation, runtime return validation, and snapshot persistence. The
required semantic matrix covers root and scoped open/closed posture in both
directions, plus exact and constrained leaves beneath open scopes. It covers
host, imported, and nested namespace ownership, and explicit delegation
resolved open and closed. Failure cases include unsupported openness,
out-of-envelope open selection, out-of-domain constrained selection,
closed-omission materialization, and excess or unknown scenario state. Boundary
cases include an operation-free plan with an empty but present boundary, delete
operations, provisioning versus orchestration/evaluation ownership, and
apparatus-owned state on its proper contract.

Reference and libvirt must consume the same total plan lookup and produce the
same admission result for portable concerns. Published valid/invalid fixtures
must prove missing, duplicate, partial, unknown, cross-address, invalid
mode/source combination, unsafe bound, and stale-delete authority are rejected.
The runtime-manager and authenticated HTTP paths must yield the same
non-approximation diagnostic and preserve the same baseline snapshot. Because
there is no APTL adapter in this repository, APTL compatibility is established
here by the language-neutral published contract and fixtures, not by an
in-repository imitation of downstream enforcement.

## Gotchas and anti-patterns

- Do not serialize `CompiledRealizationRequirement` directly. It is a demand
  model, omits closed concerns, contains internal/owning-contract details, and
  currently uses `delegated` to mean unresolved.
- Do not place authority under `PlannedResource.payload` or operation payload.
  That conflates policy with desired scenario state and risks persisting or
  realizing the metadata itself.
- Do not send the authoring designation table and ask the backend to resolve
  scopes. That leaks phase machinery, creates a second semantics layer, and
  makes imports/apparatus defaults backend-dependent.
- Do not let missing boundary, missing entry, unknown concern, unknown
  apparatus default, or unsupported openness fall back to manifest capability.
  Every one is fail-closed.
- Do not encode closed as `EXACT_ONLY`, open as `OPEN_REALIZATION`, or delegated
  as `None`. Author authority, explicitness, capability, and envelope closure
  are distinct concepts.
- Do not lose delegation origin when replacing an unresolved requirement with
  an effective open requirement.
- Do not assume the operation payload proves closed omission; absence is
  ambiguous without the authority entry.
- Do not accept `constrained` without portable bounds or treat the instantiated
  concrete value as the whole allowed domain.
- Do not publish arbitrary variable `allowed_values` as a constraint domain;
  the variable contract has no secret classification. Only a concern-owned,
  publication-safe typed domain may appear in the handoff.
- Do not use a producer-populated `complete` boolean, count, or digest to bless
  a partial collection. Validators derive completeness from the canonical
  concern inventory and the plan's non-delete resources.
- Do not use a plan-wide open bit. Exact/constrained leaf precedence and
  imported namespace scope require concern-level identities.
- Do not treat backend-private/native state as scenario excess and then solve
  the conflict by broadening author openness. Put that state on its owning
  contract; scenario payload excess remains an error.
- Do not preserve only in-process behavior. Projection, HTTP round-trip,
  control-plane submission, reference/libvirt interpretation, runtime
  disclosure, snapshot persistence, and external contract conformance are one
  handoff surface.
- Do not treat request authentication or `_request_fingerprint` as planner
  attestation. A canonical digest is only a lookup key: it becomes authority
  evidence when the exact digest is already present in the trusted
  planner-produced-plan registry. Never accept a caller-recomputed digest as a
  self-attestation. Do not add an unrelated target field to the realization
  entry.
- Do not add duplicate validators, exception types, schema registries,
  persistence ledgers, logging paths, hash algorithms, or adapter-specific
  posture logic.

## Non-goals and implementation boundaries

- No change to the author-facing `Scenario.realization` syntax, namespace
  cascade, specificity ordering, or legacy omission semantics.
- No new realization-envelope expression language, apparatus capability mode,
  manifest family, backend selection policy, or authoring annotation bag.
- No permission for undeclared topology, unknown SDL keys, arbitrary optional
  fields, secret-bearing configuration, or backend-native state.
- No redesign of resource payloads, mechanism-neutral compute intent (#1076),
  runtime concern registration breadth (#1078), artifact requirement semantics,
  TechVault authoring, or APTL's external implementation.
- No relocation of orchestration/evaluation realization demands or artifact
  requirement bodies into `ProvisioningPlan`; this issue closes the
  provisioning execution handoff only. Any future carrier for another plan
  domain must reuse the common typed authority vocabulary without widening
  this plan's ownership.
- No requirement that a backend choose a value for every open concern; absence
  remains allowed where the concern semantics allow absence. If it chooses a
  value, the full authority/capability/envelope/evidence intersection applies.
- No durable storage of raw plan authority merely to compensate for a lossy
  control-plane DTO. The DTO must be lossless first.
- No cross-repository assumptions about APTL. This repository defines and tests
  the portable plan contract and its reference/libvirt consumers; downstream
  adapters consume that contract without reimplementing RAES authoring rules.
