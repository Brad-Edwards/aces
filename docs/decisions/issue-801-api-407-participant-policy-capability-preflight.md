# Issue 801 API-407 Participant Policy Capability Preflight

Date: 2026-07-26

Issue: #801.

Requirement: API-407.

This note records architecture boundaries and implementation guardrails for
extending backend participant feature-support declarations to participant
information-flow and control features. It is guidance only. It does not change
the backend manifest, publish schemas or vocabularies, implement admission,
change a backend, run conformance, or claim participant-policy realization.

## Decisive Current-State Finding

API-407 already has one canonical manifest surface:
`capabilities.participant_runtime.feature_support` on
`backend-manifest-v2`. `ParticipantFeatureSupportModel`,
`ParticipantFeatureSupport`, `backend_manifest_v2_model()`, and
`backend_manifest_from_v2_model()` already preserve that surface across the
published contract and internal backend protocol.

The current surface is not sufficient for issue #801 by itself:

- the governed behavior and interaction feature vocabularies do not name the
  required participant-control features;
- feature entries carry strength, constraint refs, and disclosure refs, but
  not the issue's explicit limitation and conformance-evidence refs;
- below-exact disclosure and one contradiction are validated, but positive
  support is not checked against its required evidence contracts;
- `participant_runtime_capability_contract_gaps()` checks API-405 supported
  lists, while the planner independently reduces required features to set
  membership and ignores API-407 strength;
- `BACKEND_SUPPORTED_CONTRACT_IDS` and the full remote-control backend profile
  do not yet include the API-409/API-423 participant control/crossing
  contracts; and
- `BackendConformanceReport` can already carry finite cases, gaps,
  limitations, and explicit nonclaims, but no participant-control
  feature-support cases currently exercise it.

Issue #801 therefore extends existing declarations, evidence mapping,
admission, and conformance. It does not need another manifest block, profile
family, report, policy engine, or ADR.

## Binding Authorities

- Accepted ADR-085 and
  `specs/formal/participant-semantics/information-flow-control.md` define the
  participant-control operations, deny-first policy composition, weakening
  rule, evidence limits, and the requirement that missing support fail closed.
- ADR-060 and
  `specs/formal/runtime-contracts/participant-backend-contracts.md` own the
  API-405/API-407 manifest boundary and the existing
  `unsupported < disclosed_weak < bounded < exact` scale. ADR-085's later
  participant-control decision extends that entry; it does not merge it with
  SEM-218 realization support.
- API-409 `participant-control-occurrence-v1` and API-423
  `participant-crossing-occurrence-v1` own control and crossing realization
  facts. A manifest declaration references their contract/evidence surface; it
  does not copy their policy, occurrence, transformation, delivery, or audit
  fields.
- ADR-009, ADR-012, ADR-061, `contracts/README.md`, and the schema/concept
  policy tools govern published shape, vocabulary, compatibility, and
  publication records.
- `.ground-control.yaml`, `.gc/plan-rules.md`, and `noxfile.py` own workflow.
  The branch name does not contain `API-407`, so implementation and completion
  checks must set `RAES_REQUIREMENT_UID=API-407`.

These authorities settle the architecture. A new ADR is required only if the
implementation discovers an actual conflict with them.

## Architecture Decisions And Guardrails

### Extend the existing entry, never fork the surface

Participant-control support remains one `ParticipantFeatureSupport` entry per
governed feature under `capabilities.participant_runtime.feature_support`.
Keep the existing support-level enum and its ordering. Do not add control
booleans, a `participant_policy` manifest block, backend-specific capability
objects, another support-strength enum, or a second profile registry.

The six required semantic features are distinct:

- participant ingress admission;
- participant egress projection;
- governed declassification;
- non-mutating transformation;
- participant intervention; and
- participant-directed inject delivery.

Each must receive one canonical feature id in the existing participant runtime
feature authority. Ingress and egress must remain visible in the ids; generic
`admission` or `projection` terms are too ambiguous. Participant-directed
inject delivery must retain its distinction from an environment inject.
Lexical ids are declared once in
`participant-runtime-behavior-features` and reused everywhere; local enums or
aliases are not authority. These are participant-runtime policy features, not
new interaction patterns, so a third feature taxonomy is unwarranted.

### Keep constraint, limitation, disclosure, and evidence meanings separate

The same feature-support entry is the extension seam. In addition to its
existing `feature`, `support_level`, `constraint_refs`, and `disclosure_refs`,
issue #801 needs out-of-line `limitation_refs` and `evidence_refs`. Their
meanings must not collapse:

- `constraint_refs` identify the domain or bound within which support is
  claimed;
- `limitation_refs` identify known exclusions, weakened guarantees, and
  explicit nonclaims;
- `disclosure_refs` identify the disclosure required for an affected consumer
  or audience; and
- `evidence_refs` identify reviewable conformance/evidence records for a
  positive support claim.

All are unique, non-empty references. They never contain policy bodies,
payloads, backend logs, credentials, hidden participant state, or inline
evidence.

Preserve the existing rule that every below-exact entry requires disclosure.
A bounded claim must name its bound; a disclosed-weak claim must name its
limitations; and a positive claim (`disclosed_weak`, `bounded`, or `exact`)
must cite evidence and the term's required published contracts. Unsupported
is an explicit negative posture, not positive realization evidence.

For each issue-801 feature, the broad API-405 presence declaration and the
API-407 strength entry must agree: positive strength requires the feature to
be present in the owning supported-feature list, while `unsupported` requires
it to be absent. Duplicate entries, unknown ids or strengths, empty refs,
missing required refs, and either direction of contradiction fail manifest
validation.

Do not make every historical manifest globally total as an incidental schema
break. Total declaration of the six participant-control features belongs to
the backend profile/conformance/admission contexts that claim this capability.
Outside those contexts, absence continues to make no strength claim under
ADR-060. Inside them, absence is a fail-closed unsupported gap.

### Keep evidence criteria canonical and claims honest

`PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS` remains the single
term-to-required-contract table. Extend it for the new governed terms and keep
the existing vocabulary-parity test total. Do not add a second feature evidence
map in contracts, profiles, the planner, or conformance.

Required contract evidence must point to the owning surfaces. At minimum, the
mapping must distinguish:

- ingress admission from API-409 control and SEM-211 admission facts;
- egress projection from API-406 observation/projection facts;
- declassification and transformation from API-423 crossing facts;
- intervention from API-409 control occurrences plus API-423 crossings; and
- participant-directed inject delivery from its DSL-142 binding plus API-423
  delivery/observation facts.

Only backend-facing/live contract ids belong in a backend manifest. An SDL
authoring schema or requirement reference is not backend realization evidence.
Add any newly claimable API-409/API-423 contract ids to
`BACKEND_SUPPORTED_CONTRACT_IDS` before a manifest or profile can cite them,
and update the canonical full remote-control profile rather than inventing an
issue-specific profile.

An entry's evidence refs do not replace the required-contract table, and
declared contracts do not replace conformance. Contract publication, method
presence, a manifest claim, runtime realization, bounded conformance, model
checking, and proof remain independent statuses.

### Put strength-aware admission in the existing owning layer

`raes_backend_protocols.capability_admission` owns backend capability matching.
Extend that layer so one parameterized comparison evaluates:

- required governed feature id;
- required minimum strength;
- the manifest's explicit feature entry;
- required contract/evidence availability; and
- an optional, already-authorized downgrade reference and allowed effective
  strength.

The helper must not decide policy authorization itself. Without an explicit
authorization supplied by the owning participant policy/crossing decision,
missing support, a missing entry, insufficient strength, missing evidence, or
an unresolved extension term is an error gap. An authorized downgrade records
the weaker effective strength, provenance, disclosure, and limitation refs and
removes the stronger claim; success-with-warning while retaining `exact` is
forbidden.

The planner's `_participant_execution_diagnostics()` must consume this owning
helper instead of maintaining a second supported-feature set subtraction.
Target selection, planning, and conformance must call the same comparison; they
must not each reinterpret strength ordering or downgrade rules.

`RuntimeTarget._validate_runtime_target_shape()` remains a protocol-shape
check. Do not infer participant-policy support from `admit_action`, another
method's presence, a callable signature, or a component being non-null.

### Extend the existing conformance report

Use `run_target_conformance()`, `ConformanceCaseResult`,
`BackendConformanceReport`, `unsupported_capability_gaps`, and
`BehavioralClaimBindingModel`. Feature-specific cases must record the exact
feature, declared/effective strength, finite target/profile/corpus scope,
evidence refs, limitations, and explicit nonclaims. Negative cases cover
missing entries, insufficient strength, contradictions, missing evidence,
unauthorized downgrade, and a downgrade that retains a stronger claim.

Do not create an API-407 report type or runner. The existing bounded claim
already states that finite cases do not establish native realization,
unexecuted behavior, trace equivalence, bisimulation, or universal proof; keep
and specialize those nonclaims rather than replacing them.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Published manifest shape | `BackendManifestV2Model`, `BackendCapabilitiesV2Model`, `ParticipantRuntimeCapabilitiesModel`, and `ParticipantFeatureSupportModel`. Keep `ContractModel(extra="forbid")` and one model-level owner for entry/cross-field invariants. |
| Internal backend declaration | `BackendManifest`, `ParticipantRuntimeCapabilities`, `ParticipantFeatureSupport`, `backend_manifest_v2_model()`, `backend_manifest_payload()`, and `backend_manifest_from_v2_model()`. Preserve exact round-trip parity; add no DTO layer. |
| Concept and vocabulary | `controlled-vocabularies-v1`, `participant-runtime-behavior-features`, `participant-runtime-feature-support-levels`, existing scope validators, concept bindings, and controlled-vocabulary parity tests. |
| Evidence criteria | `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, `BACKEND_SUPPORTED_CONTRACT_IDS`, `participant_runtime_capability_contract_gaps()`, and their total-coverage tests. |
| Admission | `raes_backend_protocols.capability_admission`, `raes_processor.planner.core`, compiled `backend_feature_support_refs`, planner `Diagnostic` values, and the normal error-severity execution-plan gate. |
| Participant policy facts | ADR-085, SEM-211 admission, API-409 control occurrences, API-423 crossing decisions/operations/posture/loss records, SEM-226 exposure records, and DSL-142 inject bindings. Reference them; never duplicate their fields in a manifest. |
| Backend declarations | `raes_backend_stubs.manifest`, `raes_reference_backend.manifest`, and `raes_backend_libvirt.manifest`. Each declaration must describe delivered behavior honestly; no backend becomes exact merely to keep tests green. |
| Profiles and conformance | `contracts/profiles/backend/`, `BackendProfileModel`, `run_fixture_suite()`, `run_target_conformance()`, `ConformanceCaseResult`, `BackendConformanceReport`, and `BehavioralClaimBindingModel`. |
| Diagnostics and observability | `Diagnostic`, `DiagnosticModel`, `Severity`, `unsupported_capability_gaps`, bounded conformance payloads, and existing CLI/control-plane error redaction. No new exception hierarchy, logger, metric stream, or audit channel. |
| Publication | Hand-governed `contracts/schemas/backend-manifest/backend-manifest-v2.json`, matching `schema_bundle()` output, backend-manifest valid/invalid fixtures, `contracts/schema-publication/entries/backend-manifest-v2.json`, ADR-061 compatibility classification, and generated-schema drift checks. |
| Lineage | The participant section of `docs/explain/sdl/lineage.md`, `SDLLineageLedgerModel`, `tools/check_sdl_lineage.py`, and the source audit. Record delivery/evidence/nonclaims; change the ledger or source audit only for a changed normative derivation or compatibility claim. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and the repo-policy, requirement-governance, concept-authority, schema-publication, generated-schema, JSON-artifact, lineage, conformance, and full verification gates. |

## Cross-Cutting Layers And Security Posture

1. **Manifest file and parser gate.** External manifests continue through the
   existing `raes processor plan --manifest` path: a path argument only, a
   one-megabyte file limit, UTF-8 JSON decoding, object-shape check,
   `BackendManifestV2Model.model_validate()`, and reconstruction through
   `backend_manifest_from_v2_model()`. Backend-native loaders must reach the
   same models. Do not parse a second manifest fragment or accept policy from
   unvalidated mappings.
2. **Closed contract and semantic gate.** JSON Schema and Pydantic reject
   unknown fields and malformed refs; model validation owns single-entry and
   list contradictions; the capability-admission helper owns manifest-to-
   requirement strength/evidence agreement. Do not repeat semantic joins in
   schema conditionals, model constructors, planners, registries, and
   conformance runners.
3. **Concept and publication gate.** Every standard feature id is governed,
   every extension uses the existing `x-<owner>:<term>` rule, and every
   required contract id is manifest-authorized. The published schema is
   hand-governed authority; update its publication entry `last_change` and
   content hash, then keep `schema_bundle()` byte-semantically identical.
4. **Authentication and policy gate.** Issue #801 adds no HTTP route or
   authentication mechanism. If a later API exposes declarations or admission
   decisions, it must enter through `create_control_plane_app()`,
   `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy
   identity, `ControlPlaneRole`, target binding, request-size guards,
   fingerprints/idempotency for mutations, and `AuditEvent`. Caller
   authorization never authorizes participant action, visibility,
   declassification, or downgrade.
5. **Secret and hidden-content gate.** Manifests, profiles, fixtures,
   diagnostics, conformance reports, lineage, audit, and logs contain only
   bounded ids, refs, digests, codes, strengths, limitations, and nonclaims.
   They exclude tokens, keys, credentials, prompts/private memory, hidden
   answers/world state, policy bodies, raw rejected manifests, backend objects,
   environment dumps, and raw conformance payloads.
6. **Diagnostic and error-envelope gate.** Expected admission/conformance
   failures use stable, bounded `Diagnostic` codes/messages and
   `unsupported_capability_gaps`. They may identify governed feature ids and
   missing contract ids, but must not echo rejected ref values or whole
   entries. The plan CLI retains its field-path/error-kind summary and generic
   deep-validation failure. Unexpected HTTP failures retain
   `{"detail":"internal server error"}`.
7. **Configuration and OS/process gate.** The change needs no new environment
   binding, secret loader, subprocess, daemon, socket, or host configuration.
   Manifest content remains in a bounded file or typed in-process object; no
   policy, evidence, credential, hidden value, or full manifest belongs in
   process argv, environment variables, filenames, stdout/stderr, or host
   logs. A manifest path in existing argv is not authority and must not bypass
   validation.
8. **Persistence and observability gate.** Static manifest declarations and
   conformance reports do not create a new durable store. Any later realized
   downgrade or crossing uses first-class API-409/API-423/runtime/evidence
   carriers and existing `RuntimeSnapshot`/`ControlPlaneStore` append-only
   paths. It does not live only in snapshot `metadata`, audit `details`, logs,
   or a backend-local cache.
9. **Conformance and claim gate.** Profile contract gaps, manifest claim gaps,
   finite feature cases, target probes, native-conformance status, evidence
   refs, limitations, and explicit nonclaims remain separately visible.
   Passing shape validation or finite probes never upgrades the manifest's
   strength or establishes production enforcement or universal security.

## Extensibility Seam

The stable seam is the existing feature-support entry plus one strength-aware
capability comparison parameterized by feature id, minimum strength, required
contract/evidence set, and optional explicit downgrade authorization/effective
strength. The term-to-contract table and controlled vocabulary supply standard
feature data; callers supply scenario/profile demand and already-resolved policy
authorization.

This lets the next participant-control feature, backend extension term,
audience-specific downgrade, or stronger evidence profile add vocabulary/data
and cases without adding fields to `RuntimeTarget`, branching the planner,
creating another manifest block, or editing every backend adapter. New wire
meaning still follows ADR-061; an open metadata or `constraints` bag is not the
extension seam.

## Gotchas And Anti-Patterns

Avoid:

- a second manifest section, capability/profile registry, support enum,
  evidence map, schema registry, validator stack, fixture runner, conformance
  report, exception hierarchy, logger, audit channel, or persistence store;
- adding control features only to `feature_support` while omitting the owning
  supported-feature vocabulary/list, concept bindings, required-contract map,
  manifest contract allowlist, or profile;
- treating generic admission or projection as unambiguously participant
  ingress/egress, or treating every orchestration inject as participant input;
- collapsing constraints, limitations, disclosures, evidence, and nonclaims
  into one string list or free-form `constraints`/`metadata`/`details`;
- using the API-423 runtime `backend_posture` enum as a replacement for the
  API-407 support-level enum; a crossing posture and a manifest capability
  claim are linked but distinct records;
- treating API-405 list presence as `exact`, absence as `unsupported`, or an
  API-407 positive entry as realization without contract and conformance
  evidence;
- inferring support from method presence, protocol shape, schema publication,
  fixture validity, a target component being present, backend logs, or a
  successful unrelated probe;
- silently accepting below-required strength, authorizing a downgrade inside
  the capability helper, or retaining the stronger claim after downgrade;
- letting one strong component hide a weak adapter, policy evaluator,
  clock/order source, projection stage, evidence store, or replay path;
- reporting bounded conformance as native realization, noninterference,
  equivalence, bisimulation, model checking, or proof;
- echoing raw manifest entries, refs, policy bodies, hidden content, secrets,
  backend object representations, environment/process data, or tracebacks in
  diagnostics, audit, reports, or logs;
- hand-generating the published schema without publication-ledger and
  compatibility review, or changing Python alone and treating generated output
  as authority; and
- changing the lineage ledger/source audit merely because implementation
  delivery status changes.

## Non-Goals And Implementation Boundaries

- No RUN-319 backend enforcement, participant gateway, transport, endpoint,
  policy evaluator, policy expression language, UI, intervention service,
  inject delivery, projection, declassification, or transformation execution.
- No new SDL syntax, behavior mode, crossing/control carrier, realization
  support mode, validation profile, participant implementation capability, or
  general concern-domain disclosure surface.
- No inference of capability from methods and no capability booleans.
- No persistence, replay, migration, credential handling, provider
  integration, subprocess/daemon, or host configuration.
- No claim that a declaration is realization evidence, that a required
  contract is conformance evidence, or that finite conformance is universal
  assurance.
- No lineage-ledger/source-audit change unless implementation changes a
  normative external derivation or compatibility claim.
