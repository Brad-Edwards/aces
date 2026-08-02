# Issue #1004 — Adversarial-Control Apparatus And Backend Preflight

Date: 2026-08-02

Issue: #1004.

Requirements: `SEM-233`, `ASR-536`, `API-407`, and `ACT-617`.

This note fixes the integration boundary for declared apparatus and backend
posture. It is guidance only. It does not publish a capability, schema,
profile, manifest entry, runtime guard, conformance result, or adversarial
assurance claim.

## Decisive boundaries

- `ACT-617` owns authored controller/authority state and ordered control
  transitions. A controller, approval, handoff, or authenticated operator is
  neither a trust label, endorsement, action admission, nor backend support.
- `SEM-233` owns two-coordinate labels, derivation, release, and the portable
  final-sink decision. It is not an apparatus configuration or realization
  assertion. #1004 may reference its exact `sem-233/rev1` profile and carrier
  bindings, never embed, fork, or reinterpret them.
- `API-407` owns one backend declaration surface:
  `capabilities.participant_runtime.feature_support`, its governed vocabulary,
  strength ordering, required contracts/evidence, limitations, disclosures,
  and explicit downgrade authorization. The apparatus/backend work extends
  that surface rather than adding a security, monitor, model, or quarantine
  manifest block.
- The experiment apparatus, task, protocol, run, evidence, measure, and
  traceability contracts own evaluation configuration and bounded evidence.
  Trusted/untrusted roles, monitor topology, independence/correlation
  assumptions, prompt separation, and tool scope are apparatus/evaluation
  facts, not portable participant semantics.
- #1003 owns live pre-effect mediation and atomic persistence. A declaration,
  wrapper, gateway, quarantine, or conformance probe cannot claim final-sink
  enforcement unless every effect/disclosure path reaches that runtime guard.

No ADR is needed: ADR-101, ADR-085, ADR-060, and the issue #801/#1002/#1003
preflights already decide the relevant ownership and deny-first posture.

## Required composition

Add only governed API-407 feature terms for the independently claimable
apparatus/backend properties: SEM-233 flow/profile resolution and propagation,
quarantined processing, trusted/untrusted processing-role declaration,
monitor-topology declaration, and final-sink mediation. The exact lexical
terms must be added once to the existing participant-runtime behavior feature
vocabulary and once to
`PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`; do not create aliases or
a second feature taxonomy. Each term must map to its actual contract surface:
SEM-233 relation/profile, API-409/ACT-617 control facts where applicable,
API-423 crossing, RUN-319 final-sink realization, and ASR-536 experiment
evidence. A term does not make all of those layers interchangeable.
Before a backend manifest can make a positive claim, add only the genuinely
backend-facing published contract ids to `BACKEND_SUPPORTED_CONTRACT_IDS` and
the canonical full remote-control profile; do not smuggle SDL-only, evaluation,
or authored-policy ids into backend support lists.

Use the existing `ParticipantFeatureSupport` / `ParticipantFeatureSupportModel`
entry and `resolve_participant_feature_support()` for declared-versus-effective
support. Positive support needs the existing required contract and evidence
checks; `bounded` needs explicit constraints, every below-exact posture needs
disclosure, and weakened policy features need limitations. Missing, unknown,
contradictory, insufficient, or evidence-free declarations are unsupported.
Only an owning SEM-233/API-423 decision may authorize a downgrade, with the
existing policy and provenance references; a downgrade must not retain the
stronger effective claim.

Use existing backend manifests and their exact round-trip path
(`BackendManifestV2Model`, `BackendManifest`, `backend_manifest_v2_model()`,
and `backend_manifest_from_v2_model()`). Use the existing selected-apparatus
admission path (`ExperimentManifestReferenceModel`,
`validate_selected_apparatus()`, `validate_admitted_apparatus()`, canonical
digest binding) for task/run compatibility. Apparatus identity or a manifest
claim is declarative: it is not proof of isolation, independent monitors,
non-collusion, source trust, flow propagation, or sink enforcement.

Conformance remains in `run_target_conformance()`,
`ConformanceCaseResult`, `BackendConformanceReport`, and
`BehavioralClaimBindingModel`. Cases must bind the exact backend manifest,
SEM-233 profile revision/digest, feature declaration and effective level,
apparatus/evaluation profile, safe evidence, constraints, limitations, and
nonclaims. Cover closed/unsupported, honest bounded, weakened/downgraded,
overclaiming, and intentionally colluding/correlated fixtures. A green finite
suite is bounded realization evidence for that exact apparatus/profile only;
it is not a proof of enforcement, model trustworthiness, monitor honesty, or
adversarial robustness.

## Cross-cutting security and runtime layers

1. **Manifest/config ingress.** Continue through the existing one-megabyte
   UTF-8 JSON/object check, `BackendManifestV2Model.model_validate()`, and
   reconstruction path. Selected experiment apparatus continues through exact
   subject/version/schema/digest admission. Do not accept caller-selected
   policy/profile files, URLs, free-form maps, or environment-selected
   capabilities.
2. **Vocabulary, shape, and semantic gates.** `ContractModel(extra="forbid")`,
   controlled-vocabulary validation, model-level feature contradictions,
   `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, and
   `resolve_participant_feature_support()` each retain one job. JSON Schema
   checks wire shape; it must not duplicate resolver joins or imply runtime
   realization.
3. **Control, flow, and capability composition.** Reuse
   `validate_participant_control_occurrence_context()` for ACT-617/API-409,
   `validate_participant_crossing_occurrence_context()` for API-423, and
   `validate_participant_flow_control_resolved_context()` for SEM-233. The
   apparatus layer supplies only a declared/effective capability conjunct;
   it cannot turn approval, monitor output, or a successful manifest parse
   into admission, endorsement, release, or permit.
4. **HTTP/auth and final effects.** If any declaration or probe is exposed,
   retain `create_control_plane_app()`,
   `ControlPlaneSecurityConfig.strict_defaults()`, `_ControlPlaneApiAuth`,
   request-size guards, closed DTOs, exact target/participant/controller/
   audience binding, fingerprints, idempotency, and `AuditEvent`. Authenticated
   caller identity does not establish semantic controller authority or data
   trust. Live effects remain #1003's `RuntimeControlPlane` / `RuntimeTarget`
   pre-effect, commit-before-effect boundary.
5. **Persistence, errors, logs, and OS exposure.** Backend/apparatus records
   and conformance evidence contain safe ids, revisions, digests, bounded
   codes, counts, constraints, limitations, and opaque refs only. Reuse
   `Diagnostic`, `Severity`, operation envelopes, `sanitized_failure_message()`,
   the redacted unexpected-error handler, and existing audit/provenance refs.
   Do not put prompts, credentials, tokens, raw facts/action arguments,
   policy bodies, monitor thresholds, private state, hidden objectives, or
   secret-derived exception text in manifests, `constraints`, audit details,
   logs, fixtures, argv, environment, paths, stdout, or stderr.

## Extensibility seam

The one seam is a governed API-407 feature entry, parameterized by exact
profile/contract revisions, declared/effective support level, constraints,
limitations, disclosure, and evidence references. A later backend, model
role, monitor topology, tool gateway, streaming sink, or quarantine mechanism
adds a closed feature term or an experiment/apparatus configuration bound to
that entry; it does not add backend-name branches, an open `metadata` bag, a
`trusted` scalar, or a parallel capability resolver. Independence and
non-collusion remain explicit, testable experiment assumptions rather than a
property inferred from different process, model, or service identifiers.

## Gotchas, anti-patterns, and non-goals

- Do not equate trusted/untrusted *role declaration* with an integrity label,
  source resolution, endorsement, independent monitor, or non-collusion proof.
- Do not treat quarantine, a prompt sanitizer, MCP gateway, model wrapper,
  heuristic monitor, redaction, or action admission as the sole enforcement
  point. Quarantined processing has no consequential authority unless the
  real final-sink path still permits the exact effect.
- Do not add another manifest section, capability enum/order, profile family,
  policy engine, DTO, resolver, exception hierarchy, logger, audit channel,
  store, conformance runner, or workflow script.
- Do not silently downgrade unavailable propagation/quarantine/sink mediation
  to support, or infer support from a method signature, process identity, or
  a declared contract. Keep unsupported, stale, denied, unresolved, and
  weakened outcomes distinct.
- Do not copy API-409, API-423, runtime-fact, SEM-233, or experiment payloads
  into manifests. Reference exact stable identities and let their owning
  validators retain semantic meaning.
- This work does not define portable prompts, LLM messages, hidden state,
  credentials, model reasoning, provider configuration, tool implementation,
  a universal gateway, runtime persistence, final-sink enforcement, a proof
  of backend realization, or an adversarial-robustness/model-alignment claim.
