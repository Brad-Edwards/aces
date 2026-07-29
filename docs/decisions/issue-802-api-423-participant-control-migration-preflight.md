# Issue #802 — Participant I/O control migration preflight

Date: 2026-07-29

Issue: #802.

Requirements: SEM-230, API-423, RUN-319.

This note fixes the architecture boundaries for adopting the already delivered
participant information-flow boundary across legacy scenarios, records,
manifests, participant implementations, backend profiles, and persisted runtime
state. It is guidance only. It does not migrate an artifact, add an adapter,
change a contract or schema, enable a backend capability, or strengthen any
historical claim.

## Decisive current-state findings

- ADR-085, API-423, RUN-319, and ASR-535 are already delivered. The migration
  composes their existing carriers, resolver, capability declarations,
  persistence, and bounded assurance; it must not redesign them.
- Every directly affected published schema is currently `draft` under ADR-061.
  That permits reviewed in-line schema evolution but does not make a bare
  end-to-end compatibility claim true. Issue #802 must still name producer,
  consumer, direction, dimension, version/lineage, and evidence as required by
  ADR-075 and `specs/evolution/versioning-deprecation-and-migration.md`.
- A legacy action, observation, control occurrence, inject, history, or
  participant view has no evidence from which an exact historical crossing
  decision can generally be reconstructed. Migration may preserve or
  reproject it; it must not synthesize authorization, policy revision,
  declassification, delivery, observation, noninterference, or backend
  realization.
- `RuntimeControlPlane` already has the adoption seam:
  `crossing_policy_resolver`, the target manifest's governed
  `feature_support`, and the selected backend profile. A positive policy
  feature without a resolver fails at startup. A persisted
  `participant_crossing_history` also requires the resolver and is
  revalidated on load.
- The current API-408 status, history, and context routes authenticate a broad
  read role but do not forward the resulting `ControlPlaneIdentity` or a
  trusted crossing-evidence context into participant egress mediation. A
  configured resolver therefore does not, by itself, make those HTTP routes a
  participant-safe governed path. The adapter must pass the authenticated
  audience binding and obtain policy/cut evidence from trusted server-side
  state, never a caller-chosen header or query value.
- Current snapshot readers default an absent
  `participant_crossing_history` to an empty mapping. Compatibility
  classification must inspect the source payload before that default is
  applied, or preserve a separate migration-basis record; the materialized
  typed snapshot cannot later prove whether the field was absent historically
  or explicitly present and empty.
- Rollback is therefore asymmetric. Before the first governed write, a target
  may return to its legacy configuration. After the first governed write, a
  safe rollback must retain a reader and resolver that preserve and validate
  crossing history. Reverting to a binary, serializer, or store format that
  ignores or drops that history is data loss, not rollback.

ADR-061, ADR-075, ADR-085, and the normative evolution specification already
settle the architecture. No new ADR is needed unless implementation discovers
an incompatible requirement that these authorities cannot resolve.

## Compatibility classification by owning surface

A fixture or release note must make the following classifications explicit.
“Compatible” without the named direction and dimension is insufficient.

| Surface | Required classification and interpretation |
| --- | --- |
| Existing API-406/API-409 participant carriers | Historical lifecycle, behavior, observation, outcome, shared-state, and control records retain their published shape and meaning. A newer consumer may accept them structurally, but absence of a companion API-423 record is semantically `legacy/unknown`, never implicit permit, deny, delivery, observation, or exact enforcement. Do not add crossing fields to these carriers. |
| `participant-crossing-occurrence-v1` | This is an additive companion relation at the ecosystem/history level, not an in-place upgrade of an incumbent payload. Only a crossing evaluated at an exact policy state cut may produce it. There is no general legacy-to-crossing conversion. |
| `runtime-snapshot-v1` | Current readers accept an absent `participant_crossing_history` and materialize an empty mapping. That is backward structural acceptance only. Empty means no governed crossing evidence is present in this snapshot; it does not describe what historical enforcement occurred. Current writers must preserve all recognized incumbent and crossing histories; an adapter fails closed on unknown input rather than erasing it during round-trip. |
| `participant-decision-surface-v1` to `v2` | This is semantic migration by authoritative reprojection, as fixed by `docs/explain/reference/participant-decision-surface-v2-migration.md`, not field renaming. V1 remains historical evidence. `observation_order` cannot be copied into `decision_epoch`, and a v1 surface is not actionable merely because a v2 reader can parse related fields. |
| SDL authoring, instantiated scenarios, and snapshots | Existing environment injects and participant behavior declarations keep their meaning. A participant-directed inject is an explicit DSL-142 binding. Inferring an addressee, disclosure policy, intervention, or delivery evidence from an environment inject is not deterministic and is forbidden. Normal parsing, semantic validation, instantiation, composition, and post-instantiation validation remain mandatory. |
| Backend manifest v2 | A legacy manifest with no positive participant-policy feature remains structurally valid and makes no such support claim. A positive feature requires its exact API-407 `feature_support` entry and required contracts. Older closed readers are not proven forward-compatible with new enum values merely because ADR-061 classifies the schema edit as structurally additive. |
| Backend profiles | `full-remote-control-plane` already requires the API-409/API-423 carriers. Schema-valid legacy manifests can still fail profile admission, and that is the intended separation. Other profiles do not acquire participant-policy meaning implicitly. |
| Participant implementation manifest v1 | Participant implementations consume participant-facing carriers such as `participant-decision-surface-v2`; the API-423 assurance/history plane is not automatically participant-visible. Do not add `participant-crossing-occurrence-v1` to participant implementation declarations merely to signal migration. Existing apparatus/manifest contract checks own v2 opt-in. |
| Behavioral relation claims and conformance reports | Historical taxonomy revisions and finite reports retain their original relation, quantifier, projection, evidence, and limitation scope. `validate_behavioral_claim_binding()` resolves against the exact catalog revision. A rev1 record is not made rev3 or `policy-noninterference` by relabeling it; unresolved historical catalogs remain explicitly legacy/unsupported unless a pinned compatible authority is supplied. |
| Scientific-completeness assessment | This is a delivery assessment, not a migration switch or proof registry. Change it only when merged implementation and assurance evidence changes the assessed status. |

The before/after corpus should use the existing fixture families and their
owning schemas. Pair artifacts by stable test identifiers in the test harness;
do not create a generic “migration bundle” payload or schema that copies
scenario, history, manifest, profile, and evidence objects into one wrapper.

### Affected published-carrier inventory

The compatibility review must cover these exact published carriers rather than
using “participant contracts” as an unbounded shorthand:

- authored and derived input:
  `sdl-authoring-input-v1`, `instantiated-scenario-v1`, and
  `orchestration-plan-v1`;
- participant decision and crossing:
  `participant-decision-surface-v1`,
  `participant-decision-surface-v2`,
  `participant-control-occurrence-v1`,
  `participant-crossing-occurrence-v1`,
  `participant-observation-envelope-v1`, and
  `participant-lifecycle-event-v1`;
- participant state and projection:
  `participant-episode-state-envelope-v1`,
  `participant-episode-history-event-stream-v1`,
  `participant-behavior-history-event-stream-v1`,
  `participant-context-view-v1`, `participant-history-view-v1`,
  `participant-status-view-v1`, and `runtime-snapshot-v1`;
- apparatus and capability:
  `backend-manifest-v2`, `backend-profile-v1`,
  `participant-implementation-manifest-v1`,
  `participant-implementation-provenance-v1`, and
  `participant-configuration-result-v1`; and
- operation and claim envelopes:
  `operation-receipt-v1`, `operation-status-v1`, and
  `behavioral-relations-v1`, plus the non-schema
  `BackendConformanceReport`.

Participant execution binding/control/service-state, shared-state,
joint-action, time-management, outcome, evidence, and provenance carriers are
transitively gated and must round-trip without loss, but issue #802 must not
rewrite them merely to add participant-control adoption state.

## Adoption and rollback semantics

The existing composition seams define three states without a second runtime
mode system:

- **Legacy:** no positive participant-policy capability is selected and no
  resolver is configured. Existing carriers retain their old behavior.
  Results are described as legacy/unknown/unsupported, not exact.
- **Opt-in:** a selected target advertises the exact feature strengths and
  required contracts, a trusted resolver is configured, caller and audience
  bindings resolve, and trusted compiled/runtime state supplies the required
  bounded crossing evidence. The shared crossing mediator is mandatory for
  the selected scope; callers cannot supply policy decisions/cuts or choose a
  legacy bypass per request.
- **Required:** the selected backend/admission profile requires the applicable
  policy features and strengths. Missing resolver, contract, capability,
  authority, policy coordinate, evidence, or compatible store state rejects
  startup, target selection, or the operation at its owning gate.

Downgrade remains API-407/RUN-319 policy, not migration fallback.
`resolve_participant_feature_support()` owns strength comparison. A weaker
realization is accepted only when the exact policy authorizes it and the
effective strength, limitations, disclosure, and provenance are recorded;
stronger claims are removed. Legacy absence cannot serve as downgrade
authorization.

Rollback has two boundaries:

- Before governed persistence, restore the earlier manifest/profile/resolver
  selection and prove the legacy path with the same compatibility fixtures.
- After governed persistence, stop or drain new governed work as appropriate,
  but retain the current resolver, schema-aware reader, and append-only
  histories. A previous executable may be restored only when cross-version
  tests prove it preserves the complete snapshot, operation, idempotency, and
  audit write set. Never delete crossing history, rewrite it as an incumbent
  carrier, or choose the older local-store snapshot solely because it omits
  governed facts.

Deprecation is not needed merely to add opt-in/required adoption. If a legacy
surface is later deprecated, use the single
`specs/evolution/deprecation-records.yaml` ledger and its existing checker.
Do not encode deprecation as a schema validation failure, runtime policy
decision, log warning, or new registry.

## Canonical incumbents to reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| SDL parsing and source migration | `SDLMigrationPolicy`, `SDLParserLimits`, `parse_sdl*()`, `format_sdl_source()`, `language_format()`, semantic validators, instantiation, and module composition. The syntax migration policy does not authorize participant policy migration. |
| Existing carriers | API-406 lifecycle/observation/history/outcome carriers, API-409 `ParticipantControlOccurrenceModel`, DSL-142 `ParticipantInjectDelivery`, SEM-220/226 decision surfaces/exposure records, and SEM-211 action/admission records. Preserve and reference them; do not wrap or duplicate them. |
| Crossing contract and semantics | `ParticipantCrossingOccurrenceModel`, `ParticipantCrossingSubjectReferenceModel`, the closed stage/vocabulary records, and `validate_participant_crossing_occurrence_context()`. Do not create a legacy crossing DTO or a second join validator. |
| Runtime adoption | `RuntimeControlPlane(crossing_policy_resolver=...)`, `_require_crossing_policy_configuration()`, `ParticipantCrossingPolicyResolver`, shared ingress/egress mediation, and `resolve_participant_feature_support()`. Resolver/capability/profile selection is the adoption seam. |
| Manifest and profile validation | `BackendManifestV2Model`, `ParticipantRuntimeCapabilitiesModel`, `ParticipantImplementationManifestModel`, `manifest_authority.py` allowlists/required-contract maps, `BackendProfileModel`, controlled vocabularies, and existing capability-gap diagnostics. |
| Persistence and replay | `RuntimeSnapshot.participant_crossing_history`, participant full-snapshot and transition diagnostics, `ControlPlaneStore.commit_participant_transition()`, `LocalControlPlaneStore`, operation records, idempotency fingerprints, expected history heads, and `AuditEvent`. No migration store or metadata backfill. |
| Compatibility authority | ADR-061, ADR-075, `specs/evolution/versioning-deprecation-and-migration.md`, schema publication entries, `schema_bundle()`, and the generated-schema/publication checkers. |
| Errors and observability | Existing `Diagnostic`, SDL parse/validation errors, bounded conformance diagnostics, operation receipt/status envelopes, security audit events, bounded HTTP details, and redacted unexpected-error response. Add no migration exception hierarchy or logger. |
| Conformance and claim discipline | Existing fixture and target runners, ASR-535 participant-policy probes, `BackendConformanceReport`, `BehavioralClaimBindingModel`, and `validate_behavioral_claim_binding()`. Cross-version acceptance does not strengthen a claim. |
| Lineage and workflow | The participant section of `docs/explain/sdl/lineage.md`, lineage ledger/model/checker, source audit, `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and canonical policy/verification scripts. Use the in-scope requirement UID supplied by the workflow when the working branch carries no requirement UID, and reconcile SEM-230, API-423, and RUN-319 traceability. |

## Cross-cutting layers and security posture

The intended migration must pass every applicable layer below.

1. **Source-size and YAML-shape gate.** Authored scenarios still enter through
   `SDLParserLimits`, the safe YAML loader, closed `SDLModel` shapes, duplicate
   and alias checks, and semantic validation. An adapter cannot parse YAML
   independently or use migration acceptance to bypass normal validation.
2. **Contract and JSON Schema gate.** Each artifact validates against its
   exact source schema/model before interpretation and its exact target
   schema/model after transformation. Closed `ContractModel` shapes reject
   unknown bags. Hand-governed schemas, `schema_bundle()` output, fixtures,
   hashes, and publication entries remain in parity.
3. **Semantic/reference gate.** Existing contextual validators own participant,
   episode, state cut, policy revision, order, marking, authority, predecessor,
   delivery, observation, evidence, and provenance joins. Adapters preserve
   references; they do not recreate these checks or manufacture missing
   resolution context.
4. **Manifest/profile/capability gate.** Manifest allowlists, controlled
   vocabularies, required-contract maps, feature strength, backend profile, and
   participant apparatus declarations all validate independently. Structural
   acceptance cannot bypass target admission or turn unsupported into bounded
   or exact.
5. **Authentication and authorization gate.** Any live operation continues
   through `create_control_plane_app()`,
   `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy
   identity, role and target checks, participant/controller subject binding,
   separate audience binding, and policy authority. Offline migration grants
   none of these authorities. Participant/audience authorization runs before
   participant existence or content is disclosed, and unauthorized
   cross-participant probes receive bounded indistinguishable denials rather
   than address-bearing existence differences.
6. **Request, idempotency, and state-cut gate.** HTTP request limits,
   fingerprints, operation-scoped idempotency, resolver freshness, and expected
   history heads remain mandatory. A retry or migrated record cannot reuse an
   identity at a different policy state cut.
7. **Persistence and replay gate.** Snapshot/history validators run before
   durable use. In-memory and local stores preserve the atomic
   snapshot/operation/idempotency/audit write set. Source data is retained;
   automated output, if justified, is deterministic, idempotent, written
   atomically to a distinct target until verified, and reports ambiguous or
   lossy cases instead of overwriting them.
8. **Error-envelope gate.** Expected failures use safe controlled codes and
   existing diagnostics. Do not stringify rejected records, Pydantic input,
   policy bodies, hidden values, host paths, or evidence payloads into HTTP
   details, audit, logs, conformance reports, or fixture output. Unexpected
   HTTP failures retain `{"detail":"internal server error"}`.
9. **Secret and OS-exposure gate.** Migration needs no credential, secret
   loader, environment dump, network endpoint, shell interpolation, or token.
   No policy body, participant-private content, bearer token, raw payload, or
   evidence content belongs in process argv, environment variables,
   filenames, stdout/stderr, temporary-file names, or host logs. Existing
   local-store confinement and atomic replacement remain the only filesystem
   persistence pattern.
10. **Claim and lineage gate.** Every result retains exact source/target
    identity, compatibility dimension, markings, provenance, evidence,
    limitations, and loss. Schema validity, successful parsing, migrated
    syntax, passing fixtures, or a capability declaration does not prove
    enforcement, delivery, observation, native realization, noninterference,
    refinement, simulation, equivalence, or bisimulation.

Issue #802 adds no HTTP route, authentication mechanism, secret/config loader,
daemon, socket, database, or generic migration service. If a CLI presentation
is later justified, it must call the owning parser/adapter and accept bounded
file input rather than sensitive payloads in argv. It writes a separate output
by default and reuses existing diagnostic rendering.

## Extensibility seam

Compatibility evaluation is parameterized by the existing surface identities:
source contract/profile/catalog revision, target revision, producer, consumer,
direction, and compatibility dimension. Adapters stay at the owning boundary:
SDL syntax in `raes`, contract/catalog readers in `raes_contracts`, backend
manifest conversion in `raes_backend_protocols`, and runtime adoption in
`RuntimeControlPlane`.

For live adoption, the required seam is the existing tuple of selected backend
profile, per-feature `ParticipantFeatureSupportLevel`, and
`crossing_policy_resolver`. One trusted resolution point must apply that tuple
consistently across action ingress, control ingress, status/history/context
egress, participant-directed inject delivery, and governed transformation;
entry points must not repeat independent `resolver is None` fallbacks. Its
selection key must be able to distinguish run/scenario, participant, crossing
direction, and interaction kind so the next reasonable rollout can govern
egress before ingress, or one participant before another, without editing
every route, controller, serializer, and backend. The policy resolver's typed
subject and validation context is where a future governed carrier, policy
revision, causal-order model, or audience is added. It must not become an open
payload/metadata bag or a global environment boolean. For a future contract
revision, add an explicit source/target adapter and version-pair fixtures
rather than editing a single “current version” migrator.

## Gotchas and anti-patterns

Avoid:

- backfilling a legacy history with synthetic crossing decisions or treating
  an empty crossing history as proof of denial, permit, or enforcement;
- adding API-423 fields to action, observation, lifecycle, control, inject,
  decision-surface, or evidence payloads instead of using typed references;
- converting environment injects to participant-directed injects by heuristic;
- converting participant-decision-surface v1 to v2 by renaming or copying
  order fields instead of authoritative reprojection;
- adding the API-423 assurance carrier to participant-facing serialization or
  participant implementation manifests without a separate exposure decision;
- treating a new consumer accepting an old shape as forward compatibility,
  semantic equivalence, behavioral compatibility, or interoperability;
- relabeling an old behavioral taxonomy revision or finite conformance report
  as `policy-noninterference`;
- accepting a positive manifest feature without its required contracts,
  evidence criteria, resolver, or profile admission;
- a per-request “legacy bypass” after a target enters opt-in/required mode;
- client-authored policy, state-cut, authority, audience, or crossing-evidence
  values added to HTTP headers or query parameters to bridge the current API
  adapter gap;
- authorizing an API-408 read by broad operator/auditor role alone, or
  disclosing participant existence before exact audience binding;
- using resolver absence, parse defaults, a last-writer-wins snapshot, or
  current wall time to reinterpret historical policy;
- rolling back by dropping `participant_crossing_history`, choosing an older
  snapshot because it contains fewer governed events, mutating prior records,
  or replaying old operations under a new state cut;
- putting migration state in snapshot `metadata`, generic `details`,
  constraints bags, logs, or audit text;
- duplicating a carrier, schema registry, fixture runner, validator stack,
  capability vocabulary, exception hierarchy, logger, store, audit stream,
  deprecation ledger, or workflow script; and
- changing the lineage ledger/source audit for evidence-only delivery, or
  failing to change them when a real normative derivation or compatibility
  claim changes.

## Non-goals and implementation boundaries

- No flag-day replacement of action, observation, lifecycle, control, inject,
  decision-surface, history, backend, or participant implementation contracts.
- No generic message, migration-bundle, policy, evidence, metadata, or
  transport abstraction.
- No automatic historical authorization, declassification, transformation,
  crossing, delivery, observation, runtime-realization, or relation claim.
- No participant gateway, policy engine, provider integration, UI, endpoint,
  authentication stack, secret handling, database, or new persistence service.
- No requirement that legacy scenarios become participant-directed or that
  legacy backends advertise participant-policy support.
- No removal or deprecation of a legacy surface without its own complete
  governed lifecycle record and evidence.
- No universal noninterference, trace inclusion/equivalence, simulation,
  refinement, bisimulation, epistemic equivalence, model-check, proof, or
  native-backend claim from migration evidence.
- No scientific-completeness status change except from shipped evidence, and
  no lineage-ledger/source-audit change unless normative derivation or
  compatibility claims actually change.
