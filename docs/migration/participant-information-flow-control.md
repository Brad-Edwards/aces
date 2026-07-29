# Participant Information-Flow Control Migration

Issue #802 adopts the SEM-230/API-423/RUN-319 boundary without changing the
historical meaning of existing scenarios, participant carriers, histories,
manifests, or backend profiles. The governing decisions are ADR-061, ADR-075,
ADR-085, and ADR-095.

## Compatibility Contract

A compatibility statement must name the producer, consumer, direction,
dimension, and source/target revision. Structural acceptance never implies
semantic equivalence, behavioral compatibility, operational interoperability,
runtime realization, or noninterference.

| Producer and source | Consumer and target | Direction and dimension | Interpretation and evidence |
| --- | --- | --- | --- |
| SDL author using `sdl-authoring-input-v1` | Current `raes` parser, validator, instantiator, and compiler | Backward structural and semantic acceptance | Existing scenarios retain their authored meaning. The paired SDL fixtures and parser test prove no rewrite. An environment inject is not inferred to be participant-directed. |
| API-406/API-409 producer | API-423-aware history consumer | Backward structural acceptance only | Existing lifecycle, behavior, observation, control, and outcome records retain their shape. No companion crossing record means legacy/unknown, not permit, denial, delivery, observation, or exact enforcement. |
| Legacy `runtime-snapshot-v1` writer | Current runtime snapshot reader | Backward structural acceptance | `participant_crossing_history` may be absent. `participant_crossing_history_presence()` distinguishes absent, explicitly empty, and populated source payloads before defaults apply. Empty history is not evidence of historical enforcement. |
| Decision-surface v1 producer | Decision-surface v2 consumer | Manual semantic reprojection | V1 remains historical evidence. `observation_order` is not copied to `decision_epoch`; use the ADR-095 reprojection procedure and its existing tests. |
| Backend-manifest v2 producer | Current manifest/profile admission | Backward structural, profile-relative operational | Missing participant-policy features remain unsupported. Positive API-407 features require an exact `feature_support` entry, required contracts, evidence, resolver, and profile admission. The manifest fixture pair exercises the existing typed adapter and bounded-strength declaration. |
| Participant implementation manifest v1 producer | Current apparatus admission | Backward structural, explicit v2 opt-in | Participant implementations opt into participant-facing decision-surface v2. They do not declare the API-423 assurance/history carrier merely to signal migration. |
| Backend-profile v1 producer | Current target admission | Exact profile-relative operational | `full-remote-control-plane` explicitly requires API-409/API-423 carriers. Other profiles acquire no participant-policy meaning by implication. |
| API-408 HTTP client | RUN-319 governed runtime projection | Backward legacy behavior or governed operational enforcement | With no resolver, the legacy projection remains available. With a resolver, the HTTP adapter passes the authenticated identity, requires a participant/audience candidate binding before lookup, obtains evidence from `resolve_participant_view_evidence()`, and commits the crossing before serialization. Headers and query values cannot author policy, audience, state-cut, or crossing evidence. |
| Historical behavioral claim/conformance producer | Exact catalog/report reader | Backward revision-pinned interpretation | Historical relation, projection, quantifier, evidence, and limitation scope is retained. A rev1 record is not relabeled as rev3 or `policy-noninterference`. |

The directly affected published-carrier inventory is:

- authored and derived inputs: `sdl-authoring-input-v1`,
  `instantiated-scenario-v1`, and `orchestration-plan-v1`;
- decision and crossing carriers: `participant-decision-surface-v1`,
  `participant-decision-surface-v2`, `participant-control-occurrence-v1`,
  `participant-crossing-occurrence-v1`,
  `participant-observation-envelope-v1`, and
  `participant-lifecycle-event-v1`;
- state and projection carriers: `participant-episode-state-envelope-v1`,
  `participant-episode-history-event-stream-v1`,
  `participant-behavior-history-event-stream-v1`,
  `participant-context-view-v1`, `participant-history-view-v1`,
  `participant-status-view-v1`, and `runtime-snapshot-v1`;
- apparatus carriers: `backend-manifest-v2`, `backend-profile-v1`,
  `participant-implementation-manifest-v1`,
  `participant-implementation-provenance-v1`, and
  `participant-configuration-result-v1`; and
- operation and claim carriers: `operation-receipt-v1`,
  `operation-status-v1`, `behavioral-relations-v1`, and the non-schema
  `BackendConformanceReport`.

Execution binding/control/service state, shared state, joint action, time,
outcome, evidence, and provenance carriers are transitively gated. They
round-trip unchanged and do not carry an adoption flag.

## Adoption Phases

Legacy means no positive participant-policy capability is selected and no
crossing resolver is configured. Existing carriers remain valid under their
historical meaning. Their participant-control posture is unknown or
unsupported.

Opt-in means the selected target declares the applicable API-407 feature
strengths and required contracts, a trusted resolver is configured, caller and
audience bindings resolve, and trusted compiled/runtime state provides the
evidence. The shared mediator is mandatory for that selected scope. There is
no per-request legacy bypass.

Required means the selected backend profile requires the applicable features
and strengths. Missing resolver, contract, capability, binding, policy
coordinate, evidence, or compatible store state rejects startup, target
selection, or the operation at its owning gate.

Downgrade is the existing API-407/RUN-319 policy path, not a migration
fallback. `resolve_participant_feature_support()` requires the exact downgrade
policy and provenance references. It records effective strength, limitations,
disclosure, and provenance and removes stronger claims. Legacy absence never
authorizes downgrade.

## Data Preservation

Migration never reconstructs a historical crossing decision from timestamps,
logs, views, current policy, or an empty default. Existing source/result
identity, digests, markings, provenance, evidence, order, limitations, and
loss remain in their owning carriers. New API-423 records describe only
crossings evaluated at an exact governed state cut and are appended beside,
not inside, incumbent records.

The fixture corpus exercises:

- unchanged legacy SDL before and after opt-in selection;
- absent versus explicitly empty crossing history while incumbent behavior
  history remains byte-for-byte equivalent;
- legacy and bounded API-407 backend-manifest declarations through the
  existing v2 adapter;
- participant-manifest v2 opt-in without exposing API-423 assurance; and
- legacy and required backend-profile admission.

Run the focused evidence with:

```console
RAES_REQUIREMENT_UID=SEM-230 implementations/python/.venv/bin/python -m pytest \
  -q implementations/python/tests/test_issue_802_participant_control_migration.py
```

## Rollout And Rollback

Roll out by selected backend profile, feature strength, resolver, and a trusted
scope key capable of distinguishing run/scenario, participant, direction, and
interaction kind. This permits egress-before-ingress or participant-by-
participant adoption without global environment switches.

Before the first governed write, rollback may restore the earlier
manifest/profile/resolver selection and rerun the legacy fixtures. After a
governed write, rollback is asymmetric: stop or drain new governed work, but
retain a resolver, schema-aware reader, and append-only snapshot, operation,
idempotency, crossing-history, and audit write set. Never delete crossing
history, rewrite it as an incumbent carrier, or select an older snapshot
because it omits governed facts.

No legacy surface is deprecated by issue #802. A later deprecation must use
`specs/evolution/deprecation-records.yaml`, name its replacement and notice
window, and prove the old surface remains supported. No removal is scheduled.

## Claim Boundary

The migration fixtures, parsers, adapters, runtime tests, and bounded
conformance evidence do not prove native-backend realization, universal
noninterference, trace inclusion or equivalence, simulation, refinement,
bisimulation, epistemic equivalence, timed or probabilistic security, model
checking, or proof.

Issue #802 adds shipped compatibility evidence but no new normative external
derivation. The lineage ledger and source audit therefore remain unchanged.
The scientific-completeness assessment already cites the shipped RUN-319 and
ASR-535 evidence and is not promoted by this migration.
