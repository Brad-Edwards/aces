# Issue 987 semantic projection reports preflight

Date: 2026-08-09

Issue: #987.

Requirement: none. The GitHub issue title, body, acceptance criteria, and
non-goals are the authoritative contract.

This note records architecture guardrails for scheme-neutral semantic
projections and evidence-bounded reports. It is guidance only: it does not add
or change a contract, schema, predicate, validator, report, persistence
surface, or implementation plan.

## Existing authorities and their boundaries

- ADR-012 and ADR-062, `specs/concept-authority/`, and
  `contracts/concept-authority/` own concept identity, external authority,
  controlled vocabularies, and offline catalog governance. A report may group
  native results by external concept; it cannot give the external scheme
  authority over native RAES meaning or execution.
- `external-concept-bindings/v1`, `ExternalConceptBindingDocumentModel`,
  `ExternalConceptSubjectModel`, `ExternalConceptSchemeSnapshotModel`, and
  `admit_external_concept_bindings()` already own the scheme-neutral authored
  assertion and exact local resolution path. The projection must consume that
  path rather than define another mapping schema or a weaker resolver.
- Binding resolution, relationship, semantic effect, confidence,
  approximation, review, and participant eligibility are independent
  dimensions. A resolved or reviewed binding is not a native predicate result,
  and an `instance-of`, `equivalent-to`, or other relationship is not permission
  to infer runtime realization.
- ADR-079 and `raes.propositions`, `raes.semantics.propositions`, and
  `PropositionTruthResultModel` own typed propositions, subject quantification,
  truth composition, declared/observed evaluation bases, probe provenance,
  temporal context, evidence, and loss. Projection classification is not a new
  truth algebra and must not reinterpret those outcomes.
- ADR-072 and `ValidationBasisDisclosureModel` own validation/admission profile
  selection, gate results, achieved strength, evidence, limitations, and
  audience restrictions. An admission view must reference that authority; the
  projection must not infer admission from successful parsing or binding
  resolution.
- ADR-064 and ADR-066 separate capture intent, raw evidence, derived measures,
  operational telemetry, participant observations, and reports. Evidence
  references support a result only after their owner-specific joins, freshness,
  sensitivity, redaction, and loss rules pass.
- ADR-078, ADR-080, `canonical_json_digest()`, SDL canonical digest helpers, and
  transformation reports own phase, canonicalization, derivation, and digest
  identity. A projection changes when its frame changes; it never changes the
  underlying transition system.
- ADR-085 and ADR-095, participant context/view contracts, API-423 crossing
  contracts, and control-plane audience binding own participant-visible
  projection, authorization, redaction, disclosure, delivery, and exact-cut
  policy. A report's perspective or a binding's participant eligibility is not
  an access-control decision.
- `ContractModel`, shared strict types, `Diagnostic`/`DiagnosticModel`,
  `sanitized_failure_message()`, the conformance registry, schema publication
  records, generated-schema parity, and fixture tooling own the portable
  contract lifecycle.
- `SemanticComparisonProfileModel` and its owner-specific admitted-artifact
  adapters establish a useful pattern for a pure, digest-pinned, bounded,
  deterministic operation. Semantic-comparison request, impact-scope, and
  result models retain their comparison-specific meaning and must not be
  renamed or widened into projection DTOs.

These accepted decisions are sufficient. A new ADR is warranted only if the
implementation proposes to make concepts executable or add a native truth or
admission algebra. The same applies if it weakens participant information-flow
controls, adds ambient discovery, or persists projections as runtime truth.

## Architecture decisions and guardrails

### Publish one report family with its complete frame embedded

Publish one closed, versioned semantic-projection report family. Its result
embeds the complete frame and a canonical frame digest. The reusable frame
model may be accepted directly by the pure projection function; do not publish
a second request schema unless an independently exchanged request is a real
consumer requirement.

The report is a derived view over explicitly supplied, already typed artifacts.
It is not an SDL section, proposition, outcome, realization envelope,
validation disclosure, evidence record, participant context, runtime snapshot,
or behavioral claim. Do not copy it into each of those carriers.

The frame must contain typed coordinates for all of these independent axes:

- exact scheme id, authority, revision, and source-content digest;
- a sorted, unique, non-empty concept inclusion set, which is the only concept
  denominator;
- one native subject kind, owning contract/lifecycle scope, and sorted exact
  artifact digests;
- one governed native predicate plus exact predicate/profile id, revision, and
  digest;
- the asserting or observing perspective and, when participant-relative, the
  participant, episode, audience, projection policy, and applicable cut;
- an explicit configuration coordinate and state cut, or a typed
  `not-applicable` posture when the selected predicate profile declares that an
  axis is irrelevant;
- quantifier kind, quantified unit, and threshold where applicable;
- evidence-boundary and freshness-policy id, revision, digest, evaluation cut,
  time domain, and clock authority, or a profile-governed `not-applicable`
  posture;
- exact external binding-set schema version, set id/version, and canonical
  digest; and
- every transformation/profile/adapter id, version, and digest used to derive
  the view.

Do not use nullable omission, free-form `context`, or an arbitrary JSON
configuration bag to mean “not applicable.” A frame axis is required or is
explicitly inapplicable under the selected profile. Configuration and state
coordinates carry ids, versions, digests, and cuts, not secret values or a
serialized mutable world.

The external binding document and scheme snapshot are recomputed and resolved
as exact local inputs. Do not trust an author-supplied `active`, `admitted`, or
resolution flag, and do not treat the current
`ExternalConceptBindingAdmissionReport.binding_set_id` alone as a digest-bound
attestation. The projector should invoke the incumbent admission function (or
an exact shared helper extracted from it) against the supplied document,
subjects, and snapshot.

The frame digest uses `canonical_json_digest()` and includes every semantic
axis above. Changing scheme revision, denominator, subject scope, predicate,
perspective, configuration, state cut, quantifier, evidence boundary,
freshness, binding version, or transformation version therefore creates a
different view without mutating native artifacts or transition semantics.

### Treat the denominator as an exact scheme-snapshot partition

The supplied pinned scheme snapshot is the report universe. The inclusion set
must resolve exactly within that snapshot and is the denominator. Terms in the
snapshot but outside the inclusion set are excluded and remain visible as an
excluded list or rows; they never enter the denominator. Missing revision or
source digest, an unknown included concept, duplicate concept candidates, or
an empty/implicit inclusion set fails closed.

Every concept in the pinned snapshot receives exactly one primary
classification. Included concepts may be `witness`, `gap`, `unknown`, or
`ambiguous`; concepts outside the inclusion set are `excluded`:

- `witness`: the selected native predicate and quantifier are decisively
  satisfied by admissible digest-stable native witnesses under the exact frame;
- `gap`: the selected predicate and quantifier are decisively not satisfied in
  a complete, exact, fully evaluable native subject scope;
- `unknown`: the result is not decidable because required native facts,
  evidence, freshness, support, scope completeness, or governed context are
  missing, withheld, stale, partial, conflicting, lossy beyond policy, or
  unsupported;
- `ambiguous`: the exact scheme, concept, binding, subject, or native-result
  join has multiple candidates and no unique governed result; or
- `excluded`: the concept is in the pinned snapshot but outside the explicit
  inclusion set.

These are report classifications, not `TruthValue`,
`PropositionTruthOutcome`, validation strength, binding resolution, review
status, or a maturity level. Do not reuse those enums merely because labels
overlap.

A gap is a strong closed-world negative. Mere absence of a binding,
observation, evidence record, adapter, or local snapshot is unknown, not a gap.
Likewise, `false`, `unsupported`, and `unknown` retain the owning native
predicate semantics; a profile must state exactly which decisive native result
and quantified domain establishes a projection gap.

The report must preserve orthogonal binding facts for every contributing
binding: binding id, resolution outcome, relationship kind, semantic effect,
confidence, approximation posture and loss details, limitations, and review
status. Stale and ambiguous bindings cannot contribute a positive witness.
Approximate or lossy bindings may yield a witness only when the exact governed
projection profile explicitly admits that posture; the report must still mark
the posture and limitations. Otherwise the concept remains unknown. Never
first-match, deduplicate, or hide additional bindings.

The binding direction remains RAES subject to external concept. Grouping
native subjects under a concept is a frame-bounded query projection, not an
inverse ontology assertion and not proof that a concept was executed,
realized, observed, or verified.

### Keep predicate profiles owner-specific and views independent

The projection core accepts one exact, digest-pinned native predicate profile
and owner-specific admitted inputs. The profile is declarative and
non-executable: it identifies the native predicate, producing contract,
accepted native outcomes, quantified unit, required configuration/cut axes,
required witness/evidence coordinates, and loss/freshness rules. It contains no
expression language, import path, callback, query string, or plugin selector.

Use a fixed trusted owner-adapter dispatch, following the semantic-comparison
adapter pattern, to project already validated native artifacts into a small
private immutable fact shape. Do not publish a falsely universal “native fact”
schema and do not dynamically import adapters. Unknown profile/predicate
coordinates fail before projection. A new predicate adds one owner adapter and
one governed profile artifact; it does not add a scheme branch or change the
report classification engine.

Existing profile families are not interchangeable. GOV-920 semantic profiles
describe phase-stack compatibility, validation profiles describe
validation/admission gates, and behavioral-relation profiles close relation
parameters. If a projection-specific profile artifact is needed, keep it
narrow and under the existing `contracts/profiles/` authority rather than
widening one of those models.

“Declared,” “admitted,” “observed,” and “verified” are separate profile-backed
native predicates, not ordered states. A report selects exactly one of them and
names its native producer. No rule may infer admitted from declared, observed
from admitted, verified from observed, or any reverse implication. A UI that
shows several views joins independent reports by compatible exact frames; it
does not synthesize a ladder or take the strongest-looking label.

Candidate native producers include declared artifact digests and native
proposition results, validation-basis disclosures, observed proposition truth
results with probe/temporal/evidence context, and digest-pinned verification
records. Those examples do not authorize a generic mapping by English label:
each delivered profile must bind one incumbent contract and its validator. If
RAES has no governed native producer for a desired predicate, the projector
rejects that predicate or reports it unsupported; it does not invent truth.

Projection quantification is distinct from concept denominator and from a
proposition's own subject quantifier. The frame must name the quantified unit,
such as distinct exact native subjects or admitted binding-subject pairs.
Existential, universal, and threshold forms are a closed discriminated shape;
thresholds are positive and cannot exceed the finite quantified population.
Other quantifiers require a separately governed profile. Reuse
`compose_truth()` only when the selected owner profile genuinely produces its
truth domain; do not coerce report classifications into it.

### Make every positive result replayable and evidence-bounded

Every witness links to the complete `ExternalConceptSubjectModel` coordinate,
the exact native result or declaration coordinate, the producing contract and
profile revision/digest, and the admissible evidence coordinates required by
that native predicate. References without the owner artifact needed to verify
their version/digest join are not positive evidence.

Do not weaken `ExperimentEvidenceRecordReferenceModel` by adding a digest in a
consumer-specific way: that reference intentionally uses its owning identity
rules. Resolve the referenced `ExperimentEvidenceRecordModel`, verify its
run/capture/provenance/sensitivity/redaction/loss joins, and compute or retain
its canonical artifact digest in the projection witness. If a digest-bearing
artifact coordinate gains a second real caller, extract one dependency-neutral
shared model rather than copying a projection-specific variant.

Observed positive results retain the incumbent probe binding, evidence refs,
temporal context, and loss bounds from `PropositionTruthResultModel`. Verified
positive results additionally require the selected verification profile's
digest-pinned producer/validator identity and non-empty admissible evidence;
an evidence-free verification claim is structurally or contextually invalid.
Evidence age is evaluated only under the declared freshness policy, cut, time
domain, and clock authority. Host wall-clock time and “latest” are not semantic
defaults.

Transformation inputs use `ArtifactTransformationReportModel` semantics:
source/target/profile/policy/derivation digests must join, refused
transformations produce no view, and preservation loss remains visible. A
successful transformation is not by itself semantic preservation or evidence
of the selected native predicate.

### Report exact counts, never an unqualified score

Rows are deterministically sorted and unique by scheme concept id and exact
native witness identity. Summary counts must reconcile exactly with the row
partition and repeat the exact predicate/profile and frame digest.

Do not emit fields named `coverage`, `coverage_percent`, `score`, `quality`, or
`maturity`. The portable report should retain integer counts for witnesses,
gaps, unknowns, ambiguous concepts, excluded concepts, and the explicit
included denominator. A renderer may display a clearly qualified fraction. For
example: “concepts with witnesses for predicate P under frame F: 7/12.” It must
also show the other state counts and must not call it an environment capability.

Governed limits cap concepts, bindings, native facts, witnesses, evidence refs,
diagnostics, and serialized input size. Frames above the selected profile's
limits fail before projection. Do not truncate a denominator or witness set and
then present a complete ratio.

### Apply information-flow policy to the report and every source

A report is visible to an audience only when every source binding, native
fact, evidence artifact, diagnostic, transformation, and limitation passes its
incumbent deny-first policy for that audience. Do not invent a projection-local
classification lattice to combine them. Aggregation, counting, hashing, or
omitting identifiers is not declassification. Counts and gap patterns can
themselves disclose hidden state.

Participant-visible publication must pass the existing authenticated
participant/audience binding, exact-cut policy, API-423 request/decision,
projection or redaction, disclosure, delivery, and audit path. The report
contract itself must not carry an ACL or claim delivery. If API-423's closed
subject vocabulary has no report carrier, extend that one incumbent vocabulary
and its controlled-vocabulary parity once; do not masquerade as experiment
evidence, a participant context view, or generic metadata.

The portable report contains only fields admitted for its audience. A hidden
witness must become a governed redacted/withheld/unknown presentation with
explicit loss, not a stable pseudonym that permits correlation and not a
positive result with its support removed. Internal and participant-visible
reports with different evidence boundaries are different frames and have
different digests.

## Canonical incumbents to reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| external concepts | `external-concept-bindings/v1`, its document/subject/scheme models, scheme adapters, and `admit_external_concept_bindings()`; use identical machinery for ATT&CK and NIST CSF (and the existing W3C/FIPA adapters) |
| native predicates | `raes.propositions`, `raes.semantics.propositions`, `PropositionTruthResultModel`, validation-profile selection and `ValidationBasisDisclosureModel`, and technique-owned verification records; never create a second truth/admission hierarchy |
| identity and digest | ADR-076/078/080, `ExternalConceptSubjectModel`, `canonical_json_digest()`, SDL canonical digests, and exact owner coordinates; extract the existing binding-set coordinate from semantic comparison if it gains a second caller rather than duplicating it |
| transformation | `ArtifactTransformationReportModel`, its preservation/loss rules, canonical profile/policy/derivation digests, and transformation admission functions |
| evidence and freshness | ADR-064/066, `ExperimentEvidenceRecordModel`, typed evidence refs, proposition temporal context/loss disclosure, participant context freshness patterns, and ADR-090 time authority |
| contract shape | `ContractModel(extra="forbid")`, `NonEmptyString`, `PrefixedDigestString`, RFC 3339 types, strict/discriminated unions, sorted uniqueness, explicit bounds, and `x-raes-invariants` |
| contextual validation | model/schema validation, the conformance registry's structural/context-required split, public owner-specific resolvers, and the same pure projector used by fixtures and production callers |
| diagnostics and errors | `Diagnostic`, `DiagnosticModel`, `Severity`, bounded stable codes, and `sanitized_failure_message()`; no raw Pydantic input echo or issue-specific exception hierarchy |
| participant security | ADR-085/095, `ControlPlaneSecurityConfig.strict_defaults()`, `ParticipantAudienceSubjectBinding`, participant retrieval/view rules, `ParticipantCrossingOccurrenceModel`, exact audience/policy/cut joins, `AuditEvent`, and the generic redacted HTTP error envelopes |
| persistence | ordinary versioned contract artifacts and id/version/digest refs; no database, cache, runtime-snapshot metadata field, audit blob, or mutable projection registry |
| publication and workflow | `versions.py`, contract exports and `schema_bundle()`, `tools/generate_contract_schemas.py`, schema-publication entries, `manifest_authority`, conformance fixtures, the canonical nox graph, repository policy, and existing CI workflow |

## Cross-cutting validation, security, and runtime layers

1. **Bounded parser and shape gate.** External JSON enters through
   `parse_bounded_json_object()` (or the equivalent existing bounded ingress),
   the closed `ContractModel`, the normative published schema, strict digest
   and timestamp types, duplicate/sorted-set checks, governed limits, and
   conditional validators. Extra fields, implicit denominators, missing scheme
   revisions/digests, unknown predicates, invalid thresholds, and malformed
   evidence claims fail here.
2. **Scheme and binding semantic gate.** The exact document, subject index, and
   pinned snapshot pass the existing offline binding admission path. Stale,
   unavailable, superseded, ambiguous, and unknown-concept outcomes remain
   distinct and cannot silently become active.
3. **Native owner gate.** The exact predicate profile resolves one trusted
   owner adapter and admitted native artifact type. Owner schema, semantic,
   profile, configuration, state-cut, temporal, evidence, capability, and loss
   validators run before the generic classification. No caller-selected code or
   open predicate string is accepted.
4. **Evidence and freshness gate.** Positive observed/verified facts resolve
   digest-stable evidence, producer/validator identity, run/scope/provenance,
   redaction/loss, and declared freshness at the exact cut. Missing, stale,
   withheld, conflicting, or out-of-bound evidence yields unknown or failure,
   never a positive witness or silent gap.
5. **Authorization and information-flow gate.** Offline internal generation
   introduces no authentication surface. Any participant-visible or remotely
   served view uses existing verified identity, target/role/audience binding,
   deny-first crossing policy, marking/redaction/declassification, delivery,
   idempotency/fingerprint, audit, and request-size gates. Assertion authority,
   scheme authority, and report perspective are descriptive coordinates, not
   authenticated identities.
6. **Secret-handling gate.** Frames and reports contain safe ids, versions,
   digests, classifications, bounded diagnostics, and authorized evidence
   coordinates only. They contain no tokens, credentials, secret values,
   policy bodies, hidden payloads, raw evidence, environment-variable names,
   backend-native objects, or credential-bearing URIs. A digest of secret
   material is not automatically safe to disclose.
7. **Configuration/environment gate.** Scheme snapshots, profiles, native
   artifacts, configuration coordinates, state cuts, clocks, and evidence are
   explicit typed arguments. No environment lookup, feature flag, implicit
   default profile, mutable singleton, filesystem search, or “latest” registry
   selects semantics.
8. **OS and network gate.** Projection is pure, in-process, deterministic, and
   offline. It performs no URL dereference, network call, subprocess, shell
   interpolation, plugin import, host-path lookup, socket access, or privileged
   operation. Locators, concept ids, predicate refs, evidence refs, and secret
   material never enter process argv.
9. **Error-envelope and observability gate.** Public failures use stable codes,
   safe JSON-pointer-like addresses, bounded messages, and
   `sanitized_failure_message()`. Logs/audit may retain authorized frame/report
   ids, digests, safe predicate/profile ids, counts, outcome, and exception
   class. They must not contain rejected values, complete frames, source/evidence
   payloads, URI queries, Pydantic `input_value`, exception strings, tracebacks,
   argv, or environment dumps. A future HTTP surface retains
   `{"detail":"internal server error"}` and
   `{"detail":"request validation failed"}` for unexpected/shape failures.
10. **Persistence and replay gate.** The durable result is the versioned report
    artifact plus exact referenced inputs and digests. Do not persist projection
    rows in `RuntimeSnapshot.metadata`, `AuditEvent.details`, control-plane
    operation payloads, backend stores, or a new repository/cache. A future
    query service is a separate API/persistence decision.

## Whole-repository scope

The implementation must account for the external-binding prose, schema,
fixtures, adapters, controlled vocabularies, and governance checker. It must
also account for native proposition, admission, verification, evidence, time,
transformation, participant-flow, and digest authorities. Contract exports,
versions, manifest authority, generated schemas, publication records, fixture
discovery, conformance, the public Python facade, and docs are also in scope.

Repository gates in scope include generated-schema parity, schema publication,
JSON artifacts, authority-boundary and concept-authority governance, docs,
typing/lint/tests, repository policy, and the canonical nox verification graph.
Use the existing workflow and CI definitions; do not add an issue-local
generator, fixture runner, policy script, logger, exception family, or CI
workflow.

Contract fixtures must include both unrelated schemes and the same public
projection entry point. Negative fixtures must cover an unknown predicate, an
implicit or empty denominator, a missing scheme revision/digest, and a verified
positive result without admissible evidence. They must also preserve ambiguous,
approximate, stale, and lossy bindings in the resulting rows or diagnostics.

The host/runtime layer is narrow. Normal projection is offline, unprivileged,
and read-only except for ordinary output or test temporaries. It has no
listener, daemon, store, backend, cloud, container, libvirt, credential, or
secret-provider interaction. Participant delivery uses the existing control
plane and crossing machinery only when delivery is in scope.

## Extensibility seam

The stable seam is a digest-pinned predicate profile plus a trusted
owner-specific adapter:

```text
(scheme authority/revision/digest, inclusion-set digest,
 subject kind/artifact scope, predicate profile/revision/digest,
 perspective, configuration/state cut, quantifier,
 evidence/freshness profile, binding-set digest,
 transformation/adapter versions)
    -> exact native facts -> classified concept partition
```

A third unrelated scheme supplies another existing neutral scheme snapshot and
uses the same binding admission, profile, projector, result schema, and report
renderer. A new native predicate supplies one governed non-executable profile
and one trusted owner adapter. A new audience supplies a different authorized
frame/crossing. None requires a scheme-name branch, report-schema fork, new
truth value, global registry, or edit to native transition semantics.

## Gotchas and anti-patterns

- Do not extend native manifest `ConceptBinding`, external binding assertions,
  propositions, validation disclosures, evidence records, participant context,
  semantic-comparison results, or runtime snapshots until one appears to be a
  generic report carrier. Their overlapping words do not give them the same
  authority.
- Do not define one `declared/admitted/observed/verified` enum with ordinal
  strength, a `max()` operation, or implied transitions.
- Do not invert an external binding into ontology authority, treat a concept as
  a subject, or report a concept as executed, realized, observed, or verified.
- Do not treat a resolved binding, accepted review, high confidence, evidence
  citation, validation strength, backend declaration, or realization envelope
  as the selected native predicate result.
- Do not infer a denominator from all scheme terms, all bindings, visible rows,
  returned witnesses, or a mutable latest snapshot. Never move unknown,
  ambiguous, stale, or excluded concepts out of the recorded partition after
  seeing results.
- Do not call missing data a gap. A gap requires complete scope and a decisive
  negative under the exact native predicate and quantifier.
- Do not collapse ambiguous, approximate, lossy, stale, superseded,
  unavailable, redacted, withheld, conflicting, or unsupported states into
  false, zero, omitted, or one generic warning.
- Do not first-match, case-fold, alias-resolve, set-deduplicate, successor-
  rewrite, or “best confidence” select multiple subjects, concepts, bindings,
  native results, or evidence records.
- Do not reuse proposition subject quantification as concept denominator, or
  count bindings when the frame says distinct native subjects.
- Do not publish a bare percentage, universal quality score, maturity score,
  environment capability, or leaderboard.
- Do not make profile data executable, dynamically import an adapter, fetch a
  scheme, inspect arbitrary object attributes, evaluate a backend query, or
  hide network/cache access inside validation.
- Do not weaken existing evidence-reference semantics, duplicate canonical JSON
  or digest helpers, add a second scheme/predicate/profile registry, or create a
  second validation/diagnostic/exception/persistence/workflow stack.
- Do not assume aggregation is anonymization or declassification. Counts,
  exclusions, gaps, timestamps, and stable digests may leak source information.
- Do not echo whole rejected documents, external identifiers, locators,
  evidence, configuration, state, policy, or exception text into diagnostics,
  logs, audit, or HTTP errors.

## Non-goals and implementation boundary

Issue #987 does not:

- define or rank a universal quality, maturity, completeness, or capability
  score;
- add native execution semantics or make an external concept executable;
- define the meaning of a new declared, admitted, observed, or verified native
  predicate when no incumbent governed producer exists;
- replace propositions, assertions, truth results, validation/admission
  profiles, outcomes, traces, evidence, realization, behavioral claims, or
  participant information-flow controls;
- select or synchronize external schemes, follow successors, perform live
  lookup, or establish a global scheme/predicate registry;
- add SDL syntax, compiler/planner behavior, backend capability, runtime state,
  transition-system mutation, evaluator behavior, or evidence capture;
- add an API, CLI, UI, dashboard, database, cache, runtime snapshot field,
  audit store, or report repository;
- claim that one scheme, one witness, one finite artifact scope, one evidence
  boundary, or one perspective represents environment capability or universal
  coverage; or
- make a participant-visible report available merely because it was generated.
