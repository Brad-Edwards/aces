# Architecture Preflight Guardrails

Date: 2026-06-11

Issue: #76.

Requirements: API-405, API-406, API-407, API-408, API-411.

This note is architecture preflight guidance for the joint participant
backend-facing contract surface. It is not an implementation plan and does not
publish the ADR or schemas required by the issue.

## Architecture Decisions

- Issue #76 publishes contract shapes over ADR-022 participant semantics and
  ADR-054 participant runtime emission points. It does not redefine action,
  observation, visibility, attribution, temporal, interaction, lifecycle, or
  outcome semantics.
- API-405 is the existing `backend-manifest-v2`
  `capabilities.participant_runtime` block. API-407 extends that same block
  for feature support and constraints; it must not create a parallel manifest
  section, backend profile branch, or processor-side capability surface.
- API-407 support is a per-feature guarantee declaration, not a scalar boolean.
  Reuse ADR-054's ordered concern vocabulary:
  `unsupported < disclosed_weak < bounded < exact`, with `not_applicable`
  outside that order.
- API-406 carriers serialize existing participant episode, behavior, action,
  observation, shared-state, attribution, temporal, and outcome surfaces. They
  compose with `RuntimeSnapshot.participant_episode_*` and
  `RuntimeSnapshot.participant_behavior_history`; they do not replace those
  fields with snapshot metadata or backend-native DTOs.
- API-408 retrieval shapes are projections of recorded API-406 carriers keyed
  by participant, episode, order point, and view reference. Retrieval must not
  invent state that was not recorded, and view semantics that belong to SEM-214
  remain deferred.
- API-411 outcome reports are SEM-215 interpretation records linking
  participant-local sources to scenario, workflow, evaluation, evidence, or
  reward layers. They are not scores, objective results, episode statuses, or
  reward records.
- If the implementation adds a `participant-runtime` schema family, update the
  schema generation routing explicitly. Do not let new contract ids fall through
  to the current `control-plane` default by accident.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- Contract authority: ADR-009, `contracts/README.md`,
  `contracts/schema-publication-manifest.json`, `ContractModel`,
  `schema_bundle()`, `tools/generate_contract_schemas.py`, and the generated
  schema drift/publication checks.
- Concept authority: ADR-012, `controlled-vocabularies-v1`,
  `concept-families-v1`, `ConceptBindingEntryModel`,
  `validate_controlled_vocabulary_scope_values()`, and the manifest concept
  binding validators.
- Participant semantics and runtime: ADR-022, ADR-054,
  `specs/formal/participant-semantics/`,
  `specs/formal/participant-runtime/`,
  `ParticipantBehaviorHistoryEventModel`,
  `ParticipantEpisodeStateModel`, `ParticipantEpisodeHistoryEventModel`,
  participant behavior validators, and participant outcome/temporal/
  attribution validators.
- Backend declarations: `BackendManifestV2Model`,
  `ParticipantRuntimeCapabilitiesModel`,
  `BACKEND_SUPPORTED_CONTRACT_IDS`,
  `ParticipantRuntimeCapabilities`,
  `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`,
  `participant_runtime_capability_contract_gaps()`, and
  `backend_manifest_payload()`.
- Runtime and retrieval: `RuntimeSnapshot`, `RuntimeSnapshotEnvelopeModel`,
  `ControlPlaneStore`, `_snapshot_model()`,
  `participant_runtime_state_contract_diagnostics()`, and
  `participant_runtime_history_transition_diagnostics()`.
- API/security path: `ControlPlaneSecurityConfig`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, control-plane request-size limits, idempotency keys,
  request fingerprints, audit events, redacted FastAPI error handling, and
  structured `Diagnostic` values.
- Verification: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`,
  `tools/check_json_artifacts.py`, and `tools/verify_all.py`.

## Cross-Cutting Gates

- Contract shape gate: every published payload must be a closed-world contract
  model with generated JSON Schema and valid/invalid fixtures. Direct edits to
  `contracts/schemas/` are forbidden; change generator inputs and regenerate.
- Vocabulary gate: every portable role, feature, support concern, lifecycle
  value, observation guarantee, outcome layer, and extension term must resolve
  through existing enum or controlled-vocabulary authority. Backend-local terms
  use the governed `x-<owner>:<term>` extension syntax.
- Manifest authority gate: new participant backend contract ids must be added
  to the canonical manifest authority lists and evidence-gap checks when they
  are claimable by a backend. API-407 support claims must be falsifiable
  against published contract evidence.
- Runtime state gate: participant state/history belongs in first-class
  snapshot fields and event streams. Shared state, outcomes, or observation
  details must not be smuggled through `RuntimeSnapshot.metadata` or generic
  `details` maps when a first-class carrier exists.
- Retrieval security gate: any API-408 HTTP read surface must reuse
  control-plane authentication, auditor/operator/backend role checks, request
  size limits, audit recording, and redacted error envelopes. Visibility
  projection and markings must be applied before returning participant-facing
  views.
- Secret-handling gate: contracts carry references, digests, markings, and
  provenance, not credentials, bearer tokens, raw prompts, hidden answer keys,
  private configuration payloads, backend object representations, environment
  dumps, or process argv.
- Error-envelope gate: validation and runtime failures use `Diagnostic` or the
  existing redacted HTTP error pattern. Do not add a participant-specific
  exception hierarchy or leak raw tracebacks.
- Persistence gate: use `ControlPlaneStore` and JSON-like contract payloads for
  control-plane durability. Do not introduce a participant-specific durable
  store as part of the contract design.

## Extension Boundary

The primary extension seam is the published contract id plus schema version.
Adding a participant backend contract should require adding one generated
contract model, fixtures, publication-manifest entry, and conformance validator
registration, not ad hoc branches across runtime, API, and conformance code.

API-407's seam is the governed feature-support entry: feature term, concern
name, guarantee strength, constraint refs, disclosure/evidence refs, and
optional backend-specific extension term. New concerns should extend that entry
shape and controlled vocabulary, not add more boolean fields.

API-408's seam is the retrieval projection selector: participant address,
episode id, order point, and view reference. Derived context views should cite
their view ref and provenance while leaving SEM-214 view semantics outside this
issue.

## Gotchas And Anti-Patterns

Avoid:

- hand-editing `contracts/schemas/` or forgetting
  `contracts/schema-publication-manifest.json`;
- adding a second schema registry, DTO layer, fixture loader, profile table,
  validation stack, exception hierarchy, persistence store, or audit log;
- placing new participant runtime schemas under `control-plane` by generator
  fallthrough when a dedicated family is intended;
- treating missing API-407 support as neutral rather than an invalid or
  unsupported declaration;
- collapsing `unknown`, `opaque`, `unsupported`, and `not_applicable`;
- treating episode terminal reason, objective result, evaluation score, reward,
  or workflow state as participant-local outcome;
- exposing hidden world truth, scoring state, centralized-training state,
  private answer keys, canaries, prompts, credentials, or raw configuration as
  participant-visible data;
- treating SDL `agents`, participant implementation manifests, backend
  participant-runtime capability, and participant episode state as the same
  concept;
- inferring causality from timestamps or backend scheduler order;
- using backend-native action names, ATT&CK/CVE/tool labels, OpenC2/CACAO
  fields, or RL spaces as ACES action semantics without loss-labeled mapping;
- weakening accepted ADRs in place without the ADR-059 amendment and pin gate.

## Non-Goals

- Implementing runtime emission, storage, HTTP endpoints, backend adapters, or
  conformance execution.
- Adding SDL authoring syntax.
- Replacing ADR-013 participant episode lifecycle, ADR-022 participant
  semantics, ADR-041 participant implementation apparatus identity, or ADR-054
  participant runtime lifecycle.
- Defining SEM-214 derived-view semantics.
- Publishing secret material, hidden truth, or backend-private data as portable
  contract payloads.
