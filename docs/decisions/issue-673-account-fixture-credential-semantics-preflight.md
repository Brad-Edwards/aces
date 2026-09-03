# Issue 673 account fixture-credential semantics preflight

Date: 2026-08-02

Issue: #673.

Requirement: DSL-439 (`59b420b3-f36d-4bd3-be4e-34ecf0633518`). The
requirement statement and rationale are the governing contract; the issue body
supplies the ownership context, acceptance criteria, and non-goals.

This note records architecture guardrails only. It does not add SDL fields,
schemas, validators, participant views, backend behavior, or an implementation
plan.

## Canonical decision and ownership boundary

Choose a typed credential binding nested under the existing top-level
`Account`. Do not make an account point at an arbitrary runtime environment
entry, setting, JSON pointer, variable name, or backend option.

The semantic shape is:

```yaml
accounts:
  exercise-admin:
    username: admin
    node: web
    password_strength: weak
    auth_method: password
    credential_bindings:
      - credential_id: primary-login
        purpose: primary_authentication
        auth_method: password
        material:
          classification: secret_fixture
          value: "deliberately-weak"
      - credential_id: operator-bootstrap
        purpose: administrative_authentication
        auth_method: password
        material:
          classification: operator_secret
          reference_id: operator-secret.web-bootstrap
```

The final contract must preserve these semantics even if schema review adjusts
individual field spellings:

- `credential_id` is a stable portable id unique within the owning account.
- Nesting is the account binding. A credential binding has no `account_ref` and
  cannot be shared with or retargeted to another account.
- `purpose` is required, normalized through one governed account-authentication
  purpose vocabulary, and has no `unknown`, unclassified, or free-form fallback.
  A bounded governed-extension form is the seam for a genuinely new purpose.
- The binding's `auth_method` is required. The existing account-level
  `auth_method` is currently an unconstrained string, not an incumbent
  vocabulary. Establish exactly one governed authentication-method vocabulary
  and normalizer using the existing controlled-vocabulary machinery, and apply
  it to both the account-level posture and every binding; do not create two
  method taxonomies. Preserve the current `password` default and normalize
  reviewed compatibility aliases. When bindings exist, exactly one
  `primary_authentication` binding must agree with the account-level posture;
  additional bindings may use another governed method.
- `material` is a closed discriminated union. A `secret_fixture` member requires
  a literal `value` field (an explicitly authored empty string remains distinct
  from omission). An `operator_secret` member requires only a bounded,
  explicitly non-sensitive `reference_id`. Unknown fields are forbidden.
- `credential_id` and the `classification` discriminator are always concrete
  in authored SDL; neither is variable-backed. Purpose, method, fixture value,
  and safe reference id may use ordinary whole-field variables inside the
  already-selected material branch and are revalidated after binding.
- Absence of `credential_bindings` means the account has no portable credential
  material declaration. It does not imply a blank password, generated default,
  operator secret, or lookup convention.

`password_strength`, `disabled`, and account existence remain posture facts.
They never become credential material and cannot satisfy a credential binding.
Runtime environment/settings remain node-runtime facts and are not a credential
registry. Application principals, database roles, file-service principals,
runtime local users, directory subjects, participant identities, and top-level
accounts remain distinct concept owners.

RAES owns this typed meaning and the canonical account/binding identity. Packs
and catalogs own concrete fixture literals. Env-packs owns pack admission and
authoring workflow. Backends own authorized secret-reference resolution and
realization. Hub may render or edit the published contract, but it must not
infer credential meaning from field names or runtime placement.

## Value, redaction, normalization, and provenance rules

The two material variants are intentionally asymmetric:

- A `secret_fixture` is scenario content under ADR-057. Its literal is present
  in the authoritative source, normalized/expanded/instantiated SDL, canonical
  SDL digest input, and the provisioning input that needs it. It is not an
  operator secret and must never be silently redacted, hashed, generated, or
  replaced because its name resembles a credential.
- An `operator_secret` is never a literal. Only a safe logical reference
  identity may enter SDL or portable provisioning input. Reuse the restrictive
  reference-identity posture of
  `SecretReferenceBindingValueModel.reference_id`: no environment-variable
  names, filesystem paths, URI locators, commands, provider objects, resolved
  values, or hashes of resolved values. Dereferencing is a separate authorized
  backend operation at a protected sink.

Reuse `SDLModel`, `parse_enum_or_var()`, portable-id validation, the
schema-visible governed-vocabulary pattern in `raes.architectures`, and the
explicit-redaction semantics centralized by ADR-056/057 and
`runtime_values.enforce_observed_value_redaction()`. The helper's internal raw-
value truthiness test must not decide fixture presence because an explicitly
authored empty fixture is meaningful; the required union field decides presence.
Extract a dependency-safe shared reference-id type/helper if necessary; do not
copy the experiment-binding regular expression or create a second secret-
reference meaning. The account union itself must make invalid combinations
unrepresentable: no unclassified literal, no fixture without `value`, no
operator reference with `value`, and no object carrying both value and
reference.

Enum and purpose/method aliases normalize with the existing case/hyphen rules.
Fixture literal bytes and safe reference ids are preserved exactly after YAML
scalar construction; do not trim, case-fold, Unicode-normalize, interpolate,
mask, or parse them as another scalar type. Whole-field variables may be used
only where the ordinary SDL variable/type system admits them. Instantiation
must reconstruct the discriminated union and rerun semantic validation, so a
placeholder cannot defer an invalid classification/value combination past the
concrete boundary.

Do not add a competing user-authored provenance string. Existing source ranges,
module expansion provenance, instantiation bindings, canonical account address,
and canonical credential id are the authoring lineage. ADR-078 intentionally
retains selected variable values in authoritative `instantiation_provenance`,
so a variable-backed fixture literal can appear there as part of the
authoritative instantiated artifact; tools must not duplicate it onto a
secondary surface. Compiler/runtime projections preserve the canonical account
and binding identities and use the existing SEM-218 realization
provenance/disclosure surfaces for realization claims. Generic runtime
diagnostics, realization provenance, audits, and inspection output carry ids,
paths, classification, purpose, and method only; they never repeat a literal,
resolved secret, sensitive locator, or material-only hash.

## Lifecycle and inspection boundary

The account binding must keep one meaning through the existing lifecycle:

1. `sdl-yaml/v1` and `Account` admit the closed local shape.
2. `SemanticValidator` rejects duplicate `(purpose, auth_method)` bindings,
   missing/inconsistent primary bindings, unresolved account/node semantics,
   and any account/binding identity disagreement that cannot be decided locally.
3. Composition retains the binding under its owning qualified account;
   instantiation preserves provenance and revalidates the concrete union.
4. `raes_processor.compiler.placement` carries the validated binding through
   the existing `AccountPlacement.spec`; it does not create a second credential
   resource or lookup registry.
5. `provisioner_account_features()` emits one governed
   `credential_bindings` feature term. Planner and direct-plan admission reject
   a provisioner that does not explicitly support the feature; an old backend
   must not silently ignore it.
6. A supporting backend resolves an operator reference only inside its trusted
   realization boundary and independently verifies the account/purpose it
   realized. Backend-native injection mechanics remain private.
7. Generic runtime snapshots, operation records, apply-result details,
   backend diagnostics, audits, logs, and error envelopes are value-free for
   account credentials. A fixture literal may transit the authenticated
   provisioning request but must be removed from a backend result before any
   result is returned, persisted, or published. Operator reference ids should
   likewise project to reference-present/classification posture unless a
   narrower trusted contract explicitly requires the safe id. The
   `RuntimeManager` realization-context path and the direct control-plane path
   must enforce the same projection; today only the former supplies
   realization requirements to `_call_backend_apply()`.

Canonical/format/transform commands emit authoritative SDL and therefore may
contain deliberate fixture literals; they must not be advertised as sanitized
exports. Generic `inspect` and compiler/runtime summaries remain value-free.

Participant-visible inspection is an explicit audience projection, not a side
effect of `/snapshot`, generic inspection, `starting_accounts`,
`interactive_access`, or knowing a runtime setting name. Starting-account and
interactive-access bindings may establish eligibility, but they are never
sufficient disclosure authority. A `secret_fixture` literal may cross only
when an explicit governed participant observation/view rule identifies the
exact `(canonical account address, credential_id)`, has a disclosed visibility
disposition and disclosure rule, and passes the existing participant audience
binding, visibility, marking, transformation, crossing-policy, audit, and
provenance gates. The projected carrier carries the account address,
credential id, purpose, method, classification, and source provenance. An
operator-secret binding projects classification/reference presence only—never
the reference id or resolved value. Sanitized publication uses the same
value-free projection rule; it does not mutate the authoritative SDL.

## Canonical incumbents to reuse

- Account and identity authority: `raes.accounts.Account`,
  `Scenario.accounts`, `SemanticValidator._verify_accounts()`, authored-domain
  topology analysis, participant starting/interactive-account validation, and
  the `scenario-account` reference model in
  `contracts/concept-authority/reference-models-v1.json`.
- Source, shape, and normalization: `sdl-yaml/v1`, `SDLModel(extra="forbid")`,
  `_base.parse_enum_or_var()`, the schema-visible governed core/alias/extension
  pattern in `raes.architectures`, `runtime_values.require_symbol()`, portable
  identifiers, mapping-key collision checks, source-ranged model diagnostics,
  module composition, and ordinary variable instantiation/revalidation.
- Secret semantics: ADR-056, ADR-057,
  `enforce_observed_value_redaction()`, the discriminated value/reference
  precedent in `raes_contracts.contracts.experiment_bindings`, and the
  value-free protected-sink precedent in runtime fact binding. Reuse mechanics,
  not the experiment/runtime-fact ownership models themselves.
- Compilation and planning: existing account addresses,
  `AccountPlacement`, `placement._compile_account_placements()`,
  `ProvisioningPlan`/`PlanOperationModel`, named planned-resource accessors,
  `provisioner_account_features()`, `ProvisionerCapabilities`, manifest
  capability validation, capability-envelope diagnostics, the canonical
  realization-concern descriptor/projection/sanitization registry, and SEM-218
  realization requirements. Credential sanitization belongs in that existing
  projection seam, not in a second redaction registry.
- Runtime security and persistence: `backend_calls._call_backend_apply()`,
  its coarse exception-to-`Diagnostic` handling, `RuntimeSnapshotEnvelopeModel`,
  `_snapshot_payload()`/`_snapshot_from_payload()`, `ControlPlaneStore`,
  `ControlPlaneSecurityConfig.strict_defaults()`, request-size/idempotency
  guards, role/target authorization, audit records, and the redacted HTTP 500
  envelope. The default FastAPI request-validation response is not a safe
  incumbent for this surface because it can echo rejected input; credential
  paths require an input-free 422 envelope.
  Backend-returned `Diagnostic` messages are currently type-checked but not
  sanitized, so they also require a credential-specific value-free gate.
- Participant visibility: participant starting-account and interactive-access
  semantics, `ParticipantAudienceSubjectBinding`, participant retrieval/view
  contracts, authored `ParticipantObservationBoundary` view/disclosure rules,
  visibility projections, participant crossing policy/egress, and
  information-flow provenance. Do not add an unauthenticated credential route,
  and do not treat starting-account membership as a projection decision.
- Contract/governance: ADR-009/019/061, `schema_bundle()`, the hand-governed
  published schemas, schema-publication entries, concept-family/reference-model
  catalogs, the controlled-vocabulary catalog, and the generated-schema,
  schema-publication, JSON-artifact, authority-boundary, SDL-catalog, lineage,
  semantic/specification-coverage, and repo-policy checks.
- Test patterns: extend the focused model/parser/semantic cases in
  `test_sdl_models.py`, `test_sdl_parser.py`, and `test_sdl_validator.py`; the
  phase/schema parity cases in `test_sdl_phase_contracts.py`,
  `test_instantiated_scenario_schema.py`, and
  `test_example_schema_conformance.py`; account capability tests in
  `test_backend_protocols_account_features.py` and `test_runtime_planner.py`;
  reference-model tests in `test_reference_models.py`; and participant/control
  boundary cases in `test_participant_interactive_access.py` and
  `test_runtime_control_plane_api.py`. Add focused negative cases for each union
  mismatch, duplicate/cross-account binding, unsupported provisioner, snapshot
  leakage, and diagnostic leakage. Invalid fixtures must use sentinel text and
  must never contain a real credential.

The semantic CLI's `_inspection_payload()` and `_runtime_summary()` are already
value-free incumbents. In contrast, `raes_cli.processor._execution_plan_payload()`
serializes complete operation payloads to stdout; it is a known leakage point,
not a safe inspection precedent. Generic plan display must use the same
value-free credential projection even though the in-memory authenticated
provisioning carrier can contain fixture material.

No new controller/service/repository/exception/logging hierarchy is needed.
Where an untyped plan payload crosses a trust boundary, add an account-specific
shape checker/accessor beside the existing planned-resource and
capability-envelope helpers rather than a second account DTO.

## Cross-cutting security gates

1. **Source/authored-config gate.** Safe bounded YAML parsing, exact mapping-key
   uniqueness, structural closure, portable ids, and the discriminated material
   union reject ambiguous or smuggled fields before model construction.
2. **Semantic/instantiation gate.** Account/node/domain/participant references,
   primary-method consistency, per-account binding uniqueness, and cross-account
   ownership are checked by the existing collect-all semantic pass and checked
   again after parameter substitution and direct instantiated-artifact admission.
3. **Pack/config gate.** Env-packs validates concrete fixture ownership and may
   supply safe operator reference ids, but must consume the RAES schema and
   purpose/method vocabulary. It must not maintain a parallel credential schema
   or infer a binding from arbitrary runtime placement.
4. **Plan/manifest gate.** Compiler output and directly submitted provisioning
   plans shape-check the account/binding/account-address join. The selected
   provisioner must advertise the governed `credential_bindings` account
   feature before any side effect. Capability support does not grant permission
   to resolve an operator secret. Direct submission must reuse
   `provisioner_account_features()` and reconstruct the canonical `Account`
   shape from `account-placement.spec`; compiler-only validation is not
   sufficient.
5. **Authentication/secret-handling gate.** HTTP plan mutation retains existing
   backend/operator authentication, target binding, request limits,
   idempotency, and audit. Secret-reference resolution is deny-first and occurs
   only at the backend's protected sink; the resolved value never re-enters a
   portable model.
6. **Host/OS exposure gate.** Neither fixture literals nor resolved operator
   secrets may appear in process argv, shell command text, environment dumps,
   native exception text, stdout/stderr, or world-readable temporary files.
   Reuse fixed-argv/no-shell runners and protected stdin/file-descriptor/API or
   owner-only file/seed patterns such as the libvirt seed writer. Backend
   support must account for plaintext-to-native credential transformation
   without returning the plaintext or resulting verifier.
7. **Backend-return/persistence gate.** Validate and sanitize account-placement
   snapshot payloads before accepting a backend result. The gate covers the
   snapshot, returned diagnostics, and `ApplyResult.details`, and it must run for
   both `RuntimeManager` execution and direct control-plane execution. Persist
   only binding identity/posture and value-free realization evidence. Generic
   snapshot and audit stores are not credential stores.
8. **Error/observability gate.** Reuse `SDLParseError`, `SDLValidationError`,
   `SDLInstantiationError`, bounded structured language diagnostics, and runtime
   `Diagnostic`. Messages identify paths/ids and coarse failure classes only;
   never call `str()`/`repr()` on a material object or include rejected input.
   Audit events record action, actor, target, decision, and safe binding ids—not
   material, request bodies, reference ids, or backend exceptions. Install an
   input-free request-validation envelope for credential-bearing plan paths;
   FastAPI's default 422 response can include the rejected `input`. The existing
   route-level `HTTPException(detail=str(exc))` is safe only when the new
   validators themselves emit bounded, value-free messages.
9. **Participant/publication gate.** A fixture literal crosses to a participant
   only through an exact binding-addressed, participant/account/audience-
   authorized disclosed view rule with crossing evidence. Starting-account or
   interactive-access scope alone never authorizes disclosure. Operator
   material is always value-free. Public or generic views default to the same
   value-free projection.
10. **Schema/contract gate.** The SDL authoring, instantiated scenario,
    instantiated snapshot, and scenario-satisfiability schemas all embed
    `Account` and must move together, with publication hashes/summaries and
    generated parity. Update the `scenario-account` reference model/key fields
    and the governed provisioner account-feature/purpose vocabularies; do not
    hand-edit generated output in isolation.

## Extensibility seam

The extension seam is the per-account list of stable credential bindings,
parameterized by credential id, governed purpose, normalized auth method, and a
closed material union. The next reasonable variation—another credential for a
different purpose or method—adds a binding. A genuinely new portable purpose
adds one governed vocabulary term (or reviewed owner extension), not a new
account field, runtime placement convention, backend flag, or credential store.

Bindings with the same `(purpose, auth_method)` remain ambiguous and therefore
fail closed in this contract. If a future rotation window, ordered factor, or
parallel credential set genuinely needs more than one, the extension seam is a
new governed selector/slot that participates in the canonical binding key; do
not silently relax uniqueness or infer order from list position.

A future non-literal material kind requires a reviewed new union member plus
its information-flow, inspection, plan, realization, and snapshot rules. It
must not enter through `other`, a free-form properties map, or an overloaded
reference id. A future runtime secret resolver implements the existing
operator-reference sink boundary; it does not change the account contract.

## Gotchas and anti-patterns

Avoid:

- putting `password`, `password_value`, `secret`, `api_key`, or a runtime-value
  ref directly on `Account`;
- treating `password_strength`, `auth_method`, a credential-shaped name, an
  environment variable, or a backend default as credential material;
- adding an `account_ref` inside a nested binding, allowing one binding object
  to target several accounts, or accepting duplicate purpose/method bindings;
- representing both fixture and operator forms as optional fields on one model,
  accepting an unclassified literal, or using `redacted` as an unresolved
  credential with no safe reference;
- copying the experiment-binding model wholesale into SDL, reusing runtime
  facts as authored credentials, or creating another secret-reference regex,
  secret taxonomy, canonicalizer, provenance ledger, or resolver registry;
- inferring purpose/method from `credential_id`, username, field name, route,
  node role, participant starting account, or selected backend;
- normalizing or redacting fixture content by name, hashing a low-entropy
  fixture as concealment, hashing resolved operator material, or logging either
  (the existing whole-request idempotency fingerprint is not a material
  projection and must not be repurposed as one);
- allowing compiler-only validation to stand in for direct HTTP plan admission,
  or letting an unsupported backend ignore the new account feature;
- copying desired account material into a runtime snapshot and calling it
  observation, or exposing the generic snapshot as a participant credential
  view;
- relying on FastAPI's default 422 body, `HTTPException(detail=str(exc))`,
  backend-supplied diagnostic prose, or `ApplyResult.details` without proving
  the carrier is value-free;
- emitting the complete credential-bearing provisioning payload from the
  generic `raes-plan plan` command, debug logs, test failure diffs, or tracing;
- returning fixture literals in generic diagnostics, inspect output, audit
  details, conformance reports, or invalid fixtures;
- editing only `accounts.py` or only one generated schema while omitting
  instantiation, composition, account placement, capability, reference-model,
  publication, participant-view, and negative conformance coverage; or
- widening every backend manifest merely to keep tests green. A backend claims
  support only when it can realize the complete binding and produce value-free
  independent evidence. In particular, libvirt's current `auth_method` feature
  claim and owner-only cloud-init seed writer do not amount to credential-
  binding support; libvirt currently locks passwords and renders no password.

## Non-goals and implementation boundary

- No operator secret store, resolver protocol, provider locator syntax, key
  rotation workflow, or backend-specific injection mechanism.
- No backend implementation or claim that libvirt, reference, stub, container,
  cloud, or another provisioner supports credential realization.
- No automatic credential generation, password hashing policy, strength
  measurement, MFA policy, recovery credential, credential discovery/capture,
  or inference from `password_strength`.
- No collapse of top-level accounts with runtime local identity, directory
  subjects, application/file/database principals, participant identities, or
  role models.
- No arbitrary account-to-runtime-value references, JSON pointers, environment
  bindings, filesystem paths, commands, templates, provider objects, or generic
  metadata/properties escape hatch.
- No new generic snapshot, persistence, audit, exception, logging, CLI, MCP,
  HTTP, or participant-control framework. Hub/env-packs/backend work consumes
  the published RAES contract in its owning repository.

The RAES implementation boundary is the nested account semantics, normative
SDL specification, model/semantic admission, lifecycle-preserving compiled
projection, capability fail-closed behavior, value-free runtime/inspection
rules, generated contracts, and conformance evidence. Concrete pack values,
pack authoring UX, secret resolution, and native realization stay with their
owners.
