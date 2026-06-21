# ADR-060: Participant Backend-Facing Contract Surface

## Status

proposed

## Date

2026-06-11

## Context

Issue #76 is the joint design surface for `API-405`, `API-406`, `API-407`,
`API-408`, and `API-411`: the backend-facing participant contract surface.
These five requirements cannot be designed independently. `API-406` defines
the plain-data shapes for participant actions, observations, state snapshots,
histories, and state-change reports; `API-405` and `API-407` declare backend
support for that surface; `API-408` retrieves what `API-406` serializes; and
`API-411` reports participant-local outcomes against `API-406` state shapes.
Designed separately, the contracts diverge.

The semantic and runtime ground is already fixed and is not reopened here:

- ADR-022 and `specs/formal/participant-semantics/` define what participant
  actions, observations, visibility, failures, attribution, temporal
  behavior, and outcomes mean.
- ADR-054 and `specs/formal/participant-runtime/` define the observable
  lifecycle, the base-envelope discipline (identity, three timestamps,
  ordering basis, markings, evidence integrity), the closed vocabularies
  (lifecycle phase, phase realization, admission disposition, information
  guarantee, ordering basis, isolation guarantee, conflict policy, mapping
  loss, delivery basis, capability strength), shared operational state,
  concurrency, and capability guarantee vectors.
- ADR-041 defines participant implementation manifests and provenance — the
  apparatus identity surface these contracts compose with.
- ADR-009 makes schemas authoritative artifacts generated from contract
  models; ADR-012 governs vocabulary authority and extension discipline.

`API-405` is already `ACTIVE`: PR #405 shipped
`backend-manifest/v2` `capabilities.participant_runtime` with governed
role/feature vocabularies, the `x-<owner>:<term>` extension rule, and
term-level evidence criteria, ahead of this joint design. This ADR must take
an explicit position on that shipped surface.

What is missing is the carrier layer: no portable boundary-record contracts
for actions, observations, or state-change reports; no per-feature support
and constraint declaration; no portable retrieval projections for participant
status, context views, and histories; and no participant-local outcome
reporting contract.

The research basis, prior-art survey, totality analysis, and numbered design
criteria for this decision are recorded in
`docs/research/participant-backend-contracts/`.

## Decision

Adopt one joint backend-facing participant contract surface with the
following structure.

1. **One carrier family, one base discipline.** New participant runtime
   carriers form a `participant-runtime` contract family generated into
   `contracts/schemas/participant-runtime/`. Every carrier embeds the ADR-054
   base envelope (single shared model, defined once) and uses the ADR-054
   closed vocabularies. No carrier defines local identity, versioning,
   marking, or extension semantics. Carriers serialize the formal specs by
   reference; they add shape, requiredness, and vocabulary bindings only.

2. **`API-406` carriers.** The plain-data contracts are:
   `participant-lifecycle-event-v1` (action attempts and lifecycle boundary
   records, including attribution-edge and outcome-interpretation references),
   `participant-observation-envelope-v1` (participant-visible observations,
   including information guarantee and declared delivery point), and
   `participant-shared-state-record-v1` (state-change reports with revision,
   digest, access records, ordering basis, and conflict policy). State
   snapshots and histories are already carried by `runtime-snapshot-v1`,
   `participant-episode-state-envelope-v1`, and the episode/behavior history
   event streams; this ADR ratifies those as the `API-406` snapshot and
   history carriers. Operation records, step signals, interaction contexts,
   joint actions, and time-management contexts remain ADR-054 surfaces owned
   by the `RUN-30x` implementation issues; `API-406` carriers reference them
   and do not absorb them.

3. **`API-405` ratified as shipped.** The
   `capabilities.participant_runtime` block from PR #405 is the participant
   capability declaration surface: governed roles, behavior features,
   interaction features, governed extension terms, and term-level evidence
   criteria. No amendment is required.

4. **`API-407` extends the same manifest block.** Feature support and
   constraint declarations are `feature_support` entries on
   `capabilities.participant_runtime`, one per governed behavior or
   interaction feature term, each declaring a support level on the ADR-054
   guarantee-strength scale (`unsupported`, `disclosed_weak`, `bounded`,
   `exact`) plus constraint references and disclosure references. Rules:
   a feature absent from `feature_support` defaults to the `API-405`
   presence claim (`exact` is *not* implied; absence of an entry makes no
   strength claim); any entry below `exact` requires a disclosure reference;
   a term listed in the `API-405` supported lists may not be declared
   `unsupported` (contradiction fails validation); terms not in the governed
   vocabularies fail validation. `API-407` declarations are participant
   feature support and remain distinct from SEM-218
   explicitness/realization declarations, which cover cross-domain
   realization handling; the manifest carries both without merging them.

5. **`API-408` retrieval is projection.** The control-plane retrieval
   contracts are read-shapes over recorded carriers, keyed by participant,
   episode, and order point: `participant-status-view-v1` (episode state and
   lifecycle facts), `participant-history-view-v1` (episode/behavior history
   retrieval with visibility projection applied), and
   `participant-context-view-v1` (derived operational context views). All
   three apply visibility projection and marking/redaction enforcement before
   publication and carry no retrieval-only state that does not exist in
   recorded contracts. The *semantics* of derived context views (meaning and
   comparability) belong to `SEM-214` (wave 3); `participant-context-view-v1`
   carries the view reference, provenance, and marking discipline only and
   makes no comparability claim.

6. **`API-411` outcomes are interpretation records.**
   `participant-outcome-report-v1` reports participant-local outcomes as
   SEM-215 interpretation records: outcome source grounding (action result,
   episode terminal state, evidence references), the interpretation rule
   reference, and explicit relationship references to scenario, workflow,
   and objective state. The carrier has no score, reward, or
   objective-success field; reward and return remain ADR-054 step signals.

7. **Vocabulary and evidence governance.** Support levels and any new
   declarable terms are governed vocabulary entries under the concept
   authority; backend-specific terms use `x-<owner>:<term>`. Every declarable
   role, feature, and support term binds to required evidence contracts,
   extending the API-405 evidence-criteria table, so conformance can falsify
   any declaration (ADR-021).

8. **Scope honesty.** This design issue publishes the contract models, the
   generated schema set, and the formal spec sections. Runtime emission,
   semantic validation beyond shape and vocabulary, conformance checks, and
   tests belong to the per-UID implementation issues (#200–#203; #199 is
   already merged). A schema published here is a settled shape, not a claim
   that any backend or the reference runtime produces it yet.

## Consequences

Positive:

- The data model is settled once for all five requirements; the per-UID
  implementation issues get a stable, reviewable contract target instead of
  negotiating shapes independently.
- Backend support claims stay falsifiable end to end: capability terms,
  per-feature strengths, and constraint disclosures all bind to governed
  vocabularies and evidence criteria.
- Retrieval cannot fork the data model: API-408 shapes are projections of
  recorded carriers by construction.
- The already-shipped API-405 surface is ratified rather than reworked,
  avoiding a breaking manifest change.

Negative:

- The contract-model surface in `aces_contracts` grows substantially, and the
  base envelope is modeled ahead of the `RUN-30x` carriers that will also
  embed it; that model must be reused, not duplicated, when those land.
- Schemas exist before any runtime emits them. Consumers must read manifest
  declarations plus evidence criteria — never schema presence — as the
  support signal.

Risks:

- The `SEM-214` deferral means `participant-context-view-v1` could prove
  inadequate when derived-context-view semantics are designed; mitigated by
  keeping that carrier reference-and-provenance only.
- The API-407 guarantee-strength scale could be misread as SEM-218
  realization support; mitigated by the explicit boundary rule in this ADR
  and by distinct manifest fields.
- A backend could declare `feature_support` entries without the runtime
  carriers existing; mitigated because evidence criteria for those terms
  reference the published contracts, and conformance fails claims whose
  evidence contracts are absent.
