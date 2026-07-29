# Issue 811 Participant-Control Bisimulation Architecture Preflight

Date: 2026-07-29

Issue: #811.

Requirements: none. The GitHub issue title, body, acceptance criteria, and
non-goals are the contract. Requirement-backed proof work must not begin until
its owning DRAFT Ground Control authority exists.

This note records repository-wide architecture guardrails for the bisimulation
design and proof program. It is guidance only: it does not select or prove a
theorem, publish a relation profile, amend an ADR or formal specification,
choose a proof tool on behalf of the design record, create a requirement or
child issue, change runtime behavior, certify a backend, or establish
bisimulation.

## Decisive Current-State Findings

RAES has the semantic, contract, runtime, claim, and evidence carriers needed
for one bounded participant-control bisimulation result. It does not yet have a
normative proof LTS, an executable relation profile, or a proof-result artifact.

- ADR-081, `specs/formal/behavioral-relations/README.md`, and
  `contracts/concept-authority/behavioral-relations-v1.json` are the only
  relation taxonomy. Revision `rev5` defines strong and weak bisimulation but
  deliberately records no implementation, model check, or proof.
- `BehavioralClaimBindingModel` already separates relation identity, carriers,
  observation projection, quantifier/evidence scope, relation-parameter
  profile, assurance axis, evidence, limitations, and nonclaims. Universal
  scopes already require model-check or proof evidence.
- The relation-profile seam is not complete. The shared binding currently
  validates only that a required profile ref/revision pair is present; it does
  not resolve or validate the referenced profile. Issue #811 must coordinate
  with the SEM-231 closed-profile work instead of creating a
  bisimulation-only registry or treating an opaque string as a checked profile.
- ADR-085, ADR-095, and SEM-230 revision `sem-230/rev2` define the abstract
  state coordinates, closed label classes, exact-cut policy state,
  participant/audience-relative projection, `tau` treatment, memory,
  declassification, scheduler/environment, order, and noninterference
  boundary.
- `implementations/python/tests/sem230_information_flow_model.py` is explicitly
  a test-local bounded falsification helper. It is not the normative SEM-230
  LTS and cannot become a theorem carrier by renaming it or exhausting its
  current examples.
- API-423 `ParticipantCrossingOccurrenceModel` and its contextual validator
  define portable request, decision, transformation, delivery-attempt,
  delivery, observation, and audit evidence. RUN-319 crossing mediation adds
  authenticated subject binding, capability admission, exact-cut resolution,
  fail-closed gates, idempotency, replay protection, append-only history, and
  atomic persistence.
- The live runtime includes generated operation ids, wall-clock timestamps,
  backend capability declarations, audit-only facts, and implementation
  bookkeeping. Those are not automatically semantic observations or `tau`.
  Each must be retained, redacted, or hidden by the selected profile.
- ASR-535 finite enumeration and backend probes are falsification and
  conformance evidence. They do not prove a relation. Proof status, reference
  runtime realization, and backend conformance remain separate axes.

The missing boundary is therefore a revision-pinned formal model pair plus a
checked mapping from SEM-230/API-423/RUN-319 carriers into those models. The
gap is not another participant DTO, policy engine, runtime store, backend
profile, conformance runner, exception hierarchy, or logger.

## Candidate-Surface Architecture Fit

The design must evaluate all five issue candidates, but their repository fit is
not equal:

| Candidate | Repository fit and guardrail |
| --- | --- |
| Abstract SEM-230 LTS versus the complete reference runtime | High value but currently too broad for a first claim unless the design inventories every enabled participant-control path, HTTP/error observation, policy change, scheduler, persistence, and backend interaction. A crossing-kernel theorem must not be promoted to whole-runtime equivalence. |
| Two policy configurations | Feasible only after both configurations are closed, revisioned policy carriers. Equal projected histories or one opacity witness is not configuration bisimulation. |
| Abstract crossing operation versus concrete contract/runtime refinement | Best-bounded primary surface. SEM-230, API-423, and RUN-319 already expose its state, labels, gates, evidence, and mapping seams. The theorem must still distinguish a formal concrete model from live-runtime realization. |
| Two backend realizations | Unsuitable as the first theorem. The current backend-comparison claim surface prohibits bisimulation, and uncontrolled backend internals cannot be hidden without a governed projection and divergence argument. |
| High-action-hidden system versus purge/restriction | Useful as a separately named noninterference lemma. It must not turn policy noninterference into bisimulation by definition or claim opacity/noninterference without its own preservation argument. |

The evidence-led default is candidate 3 over one complete finite profile. A
design may choose another target, but it must show that its carrier and mapping
surface are no broader than the evidence and do not depend on uncontrolled
backend internals.

## Architecture Decisions And Guardrails

### Use an exact relation, not generic “weak equivalence”

The likely crossing-kernel fit is divergence-preserving branching
bisimulation under a named participant/audience projection:

- concrete policy resolution, validation, capability lookup, record
  preparation, and atomic commit can take finite internal steps;
- the participant-visible branching point before permit, deny, transform, or
  unsupported must remain observable as branching structure;
- hidden divergence must not be equated with finite internal work; and
- deliberate terminal states, deadlock, failed resolution, and successful
  completion must remain distinguishable.

This relation is not currently a catalog identity. If selected, add a distinct
governed relation or an explicit catalog evolution that represents its exact
semantics; do not label it `weak-bisimulation`, silently strengthen the current
weak relation, or encode divergence sensitivity only in prose. Strong
bisimulation remains available only if every internal step is intentionally
matched. Ordinary weak bisimulation requires a separate justification because
it can forget the branching and divergence facts that matter here.

A profile fixes at least:

- left and right model ids, revisions, digests, state spaces, and initial-state
  relation;
- participant, episode/memory scope, audience, controller/authority, policy
  decision/revision/cut, projection revision, and visible order;
- complete input and label alphabets, including redacted occurrence labels and
  the exact `tau` set;
- enabledness, environment, scheduler, nondeterminism, fairness, progress,
  termination, deadlock, divergence, stuttering, and retry/replay semantics;
- concurrency, order, time, probability, declassification, transformation,
  policy-change, and controller-handoff treatment;
- relation witness/invariant family and preservation/non-preservation results;
  and
- finite carrier domains and a declaration that they are the complete
  quantified carrier when a finite equivalence decision is the final result.

Redacted occurrence, denial, withholding, unsupported status, omission under a
declared opportunity, and a sanitized error can be visible labels. They are
not `tau` merely because content is absent. Audit/evidence facts may be hidden
from a participant profile while remaining visible to an auditor profile.

### Bound the first theorem without weakening its truth

A scientifically useful first profile may fix one participant, one audience,
one episode/memory scope, one logical total order, a finite source/action
domain, finite exact-cut policy states, deterministic environment inputs, and
no wall-clock or probability semantics. It should include the security-bearing
permit/deny/unsupported/transform or declassify outcomes and retry/replay
boundary that distinguish RUN-319 from a trivial schema machine.

The profile must state excluded dimensions as excluded:

- the current per-participant lock may justify sequential interleaving for the
  selected runtime surface, not concurrent or partial-order equivalence;
- a fixed policy revision excludes policy-change behavior but does not make
  later-revision replay safe by assumption;
- a fixed controller excludes handoff behavior but does not establish handoff
  preservation;
- an untimed profile excludes latency and timeout observations; and
- finite non-probabilistic branching says nothing about probability measures,
  strategies, or fairness outside the fixed profile.

A finite result is final only for its complete finite carrier. A depth bound,
sampled schedule, truncated state space, property test, or finite trace corpus
remains intermediate evidence.

### Keep abstract model, concrete model, and runtime mapping independent

The abstract LTS is governed formal authority derived from SEM-230. The
concrete LTS is a formalization of the selected API-423/RUN-319 crossing
kernel. Live Python execution is a separate realization lane.

Do not generate both LTSs from one table that already asserts matching
transitions; that makes the result circular. The safe boundary is:

- one hand-reviewed abstract transition authority;
- one independently derived concrete carrier or deterministic exporter;
- one shared, closed label/projection profile; and
- differential mapping tests that drive the real runtime boundary and compare
  its typed occurrences, history heads, dispositions, and side effects with
  the concrete model.

The mapping must account for:

- `ParticipantCrossingIntent`, exact policy resolution, every independent
  semantic gate, API-407 effective support, and transformed subject identity;
- API-423 predecessor/order/context invariants and delivery/observation
  separation;
- authenticated caller, target, participant/controller, and audience binding;
- `RuntimeSnapshot` crossing/control/behavior histories, expected history
  heads, atomic commits, audit facts, and unchanged-state guarantees on
  refusal;
- idempotent replay at the same cut and rejection after the cut advances; and
- safe abstraction of UUIDs, wall-clock timestamps, host paths, and
  audit-internal details only when the profile proves they are outside its
  observer.

Source-code digests and commit pins detect review boundaries; they do not prove
the mapping. Avoid a Python-AST scraper that mistakes implementation shape for
semantic authority.

### Reuse one relation-profile and claim-binding authority

The behavioral catalog remains the only relation registry and
`BehavioralClaimBindingModel` remains the only claim-binding authority. The
selected theorem needs one closed, revisioned relation-parameter profile
resolved by the shared validator.

Coordinate that profile carrier with SEM-231. The common header should own
relation id, carrier refs/digests, observation projection, label partition,
quantification, model dimensions, and assurance/evidence refs. Exact
relation-specific parameters may use a closed discriminated variant. Do not
create parallel `BisimulationProfileModel` and `OpacityProfileModel`
registries, reuse a GOV-920 semantic profile or backend profile, or place a
serialized mini-language in `subject`, `limitations`, `metadata`, or
`evidence_boundary`.

Advancing the relation taxonomy requires all current revision producers,
fixtures, claim surfaces, reader-facing relation definitions, and claim-policy
tests to move together. Adding a relation entry does not by itself require a
new published schema version when the catalog shape is unchanged. Adding a
portable profile or evidence shape does require the normal
`ContractModel`/schema/publication/compatibility decision.

One proved or model-checked profile must not promote every use of the generic
relation. The claim binding records the exact positive assurance axis and
evidence. The catalog definition keeps profile-specific limits explicit.

### Select tooling by the theorem, not by repository language

The proof-tool decision record must compare at least these routes:

- **Explicit-state equivalence:** mCRL2 `ltscompare` directly supports strong,
  branching, divergence-preserving branching, weak, and
  divergence-preserving weak bisimilarity and explicit action hiding. Its
  documentation describes counterexamples for strong and branching
  bisimulation; the decision record must verify counterexample support for the
  exact selected mode or pair the checker with an independently checked
  negative-result path. This is the best current fit for a complete finite
  crossing profile.
- **Temporal/model checking:** TLC is an explicit-state checker for finite TLA+
  models and safety/liveness properties. It is useful for deadlock, replay,
  atomicity, and progress checks, but it is not a bisimulation decision merely
  because both systems satisfy the same temporal properties. A relational
  product construction and checked invariant would have to be explicit.
- **Machine-checked relational proof:** Isabelle/HOL supports coinductive
  definitions and coinduction, making it proportionate if the target becomes a
  parameterized or unbounded theorem. It has a higher toolchain and proof
  maintenance cost than the first finite carrier.

Relevant official tool facts:

- <https://www.mcrl2.org/web/user_manual/tools/release/ltscompare.html>
- <https://www.mcrl2.org/web/user_manual/tools/release/ltsconvert.html>
- <https://lamport.azurewebsites.net/tla/tools.html>
- <https://isabelle.in.tum.de/dist/library/Doc/Isar_Ref/HOL_Specific.html>

The design record may select another established environment, but it must
demonstrate exact relation support, deterministic noninteractive execution,
available witness/counterexample behavior, CI viability, version pinning,
licensing, and independent reproduction. A positive process exit is not a
proof certificate unless the tool documents that artifact. If the selected
checker emits no positive witness, exact pinned inputs plus an independent
reproduction path are mandatory; mutation failures still require a durable,
safe counterexample corpus.

### Publish evidence through existing artifact and workflow patterns

Reuse the protocol/bundle/execution-snapshot pattern in
`docs/research/formal-semantic-validation/` and the claim discipline in
`BehavioralClaimBindingModel`. A proof evidence record must bind:

- theorem/profile/relation/taxonomy ids and revisions;
- left/right model, mapping, projection, and source-revision digests;
- complete domains or explicit bounds and state/transition counts;
- tool name, version, binary/archive checksum or container digest, fixed
  command, platform limits, and result;
- relation witness/certificate when available, or the independently
  reproducible result;
- counterexample/mutation ids and artifact digests;
- exact assurance axis (`model-check` for a finite equivalence decision,
  `proof` only for a proof checked as such);
- limitations, preserved properties, and explicit nonclaims; and
- independent reviewer command and expected digest/result.

Do not overload `BackendConformanceReport`, API-423 occurrences, the existing
scheduler-isolation evidence carrier, `RuntimeSnapshot.metadata`, operation
details, or `AuditEvent` as a proof result. Do not publish a generic
proof-result schema until a portable consumer justifies it. Domain evidence
can remain a
revisioned, checked research/formal bundle while the shared claim binding
provides the portable claim surface.

The checker enters the canonical nox/workflow graph through a named session,
not an issue-local shell script. Tool pins belong in `tools/tool_versions.py`
or a full-digest CI/container pin; acquisition follows the checksum/provenance
pattern used by repo-managed tools. The equivalence result and drift checks are
blocking evidence for any positive claim. Scientific-completeness and public
documentation changes wait for independently reproduced evidence.

### Keep bisimulation, noninterference, opacity, and realization separate

Bisimulation preserves only the properties justified by the selected relation,
projection, and state/atomic-proposition mapping.

- A participant-observation bisimulation can support a named noninterference or
  opacity result only with a separate theorem showing that the selected
  low-equivalence, secret/release policy, and observer facts are preserved.
- Bisimulation does not automatically imply SEM-230 policy noninterference,
  because noninterference compares high variations, adaptive low strategies,
  memory, purge, and declassification schedules.
- It does not automatically imply SEM-231 opacity, because opacity quantifies
  secret and nonsecret possible points in observer information cells.
- A theorem between formal LTSs does not establish that RUN-319 realizes the
  concrete model. Differential mapping evidence is necessary and remains
  separate from backend declaration, native realization, and conformance.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Formal-method classification | ADR-007/018, `specs/formal/assurance-policy.yaml`, and `specs/formal/assurance-fulfillment.yaml`; retain FM3 abstract-state-machine and proportional evidence requirements. |
| Relation authority | ADR-081, `specs/formal/behavioral-relations/README.md`, `BehavioralRelationCatalogModel`, `BehavioralRelationDefinitionModel`, `BehavioralClaimBindingModel`, `load_behavioral_relation_catalog()`, and `validate_behavioral_claim_binding()`. |
| Claim policy | `tools/check_behavioral_relation_claims.py`, relation/catalog tests, catalog fixtures, claim surfaces, and every current `rev5` producer. |
| Abstract semantics | ADR-022, ADR-085, ADR-095, SEM-230 revision 2, participant runtime semantics, exact-cut policy, dynamic projection, memory, order, labels, and explicit nonclaims. |
| Crossing contracts | API-423 crossing models, typed subjects/policies/gates/losses, `validate_participant_crossing_occurrence_context()`, and crossing-history snapshot/transition validators. |
| Runtime mapping | `ParticipantCrossingIntent`, policy resolution and mediation, ingress/egress boundaries, `RuntimeControlPlane`, strict subject binding, API-407 capability admission, and safe runtime diagnostics. |
| Persistence/order | `RuntimeSnapshot`, `ControlPlaneStore.commit_participant_transition()`, in-memory/local stores, expected history heads, scoped idempotency/fingerprints, append-only histories, and `AuditEvent`. |
| Backend boundary | API-407 feature support, required-contract mapping, `resolve_participant_feature_support()`, manifest/profile validation, and explicit declared/effective strength. |
| Conformance | ASR-535 semantic/runtime/backend lanes, `run_target_conformance()`, participant-policy harnesses, `ConformanceCaseResult`, `BackendConformanceReport`, and final cross-field validation. These validate mapping; they are not the proof artifact. |
| Diagnostics/errors | `Diagnostic`, `DiagnosticModel`, `Severity`, `sanitized_failure_message()`, request-size/auth guards, and the redacted HTTP 500 envelope. Add no proof exception hierarchy. |
| Evidence/artifacts | Formal-semantic-validation protocol/bundle/snapshot conventions, `run_artifact_path()`, `atomic_write_json_artifact()`, canonical JSON, digests, and root-confined safe labels. |
| Tooling/CI | `tools/tool_versions.py`, checksum-verified tool wrappers, pinned GitHub actions, `noxfile.py`, `.github/workflows/ci.yml`, and the canonical `verify` graph. |
| Governance | ADR-009/019/036/059/061, schema publication entries/manifest, lineage checks, scientific-completeness gates, `.ground-control.yaml`, `.gc/plan-rules.md`, repo policy, requirement governance, and `tools/verify_all.py`. |

Package ownership remains unchanged: `raes_contracts` owns portable relation and
crossing carriers, `raes_runtime` owns live mediation/persistence,
`raes_backend_protocols` owns capability admission, `raes_conformance` owns
bounded runtime/backend assessment, and `tools` plus `specs/formal` own
repository proof execution and formal authority. Proof tooling must not become
a runtime dependency.

## Cross-Cutting Layers And Security Posture

1. **Model/profile input gate.** Committed formal sources are trusted,
   revision-pinned inputs. Generated or external JSON uses bounded UTF-8 reads,
   duplicate-member rejection where applicable, closed `ContractModel` shapes,
   root-confined paths, exact revisions/digests, and one semantic
   cross-reference validator. No executable expression, import path, remote
   URL, or open metadata bag is a model parameter.
2. **Relation and claim gate.** Catalog id/revision, relation id, projection,
   resolved profile, carrier refs/digests, quantifier scope, assurance axis,
   evidence scope, limitations, and nonclaims must agree before evidence is
   serialized. A string profile ref or green tool exit cannot bypass this join.
3. **Runtime authentication gate.** Pure model checking makes no HTTP or caller
   authorization claim. Runtime mapping tests still use
   `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`,
   role and target binding, participant/controller or audience binding,
   request bounds, and audit denials. Authentication remains separate from
   participant authority and visibility.
4. **Policy/capability gate.** Caller, target, participant authority, action
   admission, visibility, marking, declassification, backend support, and
   transformation validity remain independent and fail closed.
   `NOT_APPLICABLE` at a required gate is unresolved, not permit. Declared and
   effective backend strength remain separate state facts.
5. **Persistence/replay gate.** Mapping evidence includes append-only typed
   history, expected-head atomic commit, unchanged backend/participant state on
   refusal, safe decision/audit evidence, and same-cut idempotent replay.
   Proof/check results never enter runtime snapshots, metadata, operation
   details, or a side database.
6. **Secret-handling gate.** Models, profiles, fixtures, witnesses,
   counterexamples, diagnostics, logs, audit, CI artifacts, and review records
   contain synthetic bounded values and safe ids/refs/digests only. They exclude
   credentials, tokens, prompts/private memory, hidden answers/world state,
   policy bodies, raw participant/backend payloads, rejected values, native
   objects, connection data, environment dumps, and host paths. Hashing a
   secret-bearing value does not make it suitable evidence.
7. **Diagnostic/error-envelope gate.** Expected failures use bounded stable
   codes and safe model/profile coordinates. Raw Pydantic `input_value`, tool
   stderr, exception text, tracebacks, model payloads, or counterexample secret
   values do not enter portable evidence, audit, CLI summaries, or HTTP
   responses. Unexpected HTTP errors retain
   `{"detail":"internal server error"}`.
8. **OS/process gate.** Invoke a fixed allowlisted checker without a shell,
   with safe repo-relative file arguments, deterministic locale/working
   directory, bounded time/memory/output, and no network during verification.
   Put no model content, policy, witness, participant value, credential, or
   report in argv, environment variables, filenames, stdout/stderr, shell
   history, or host logs. Version output and binary/archive checksum or
   container digest become evidence.
9. **Artifact-publication gate.** Validate the complete evidence record before
   atomic writing. Use canonical JSON, safe run ids, root confinement, content
   digests, stable artifact names, and explicit retention. CI uploads the
   bounded evidence bundle, not the workspace, caches, tool binary, environment,
   or unrestricted raw logs.
10. **Schema/governance gate.** A catalog revision, shared profile resolver,
    published schema, proof evidence checker, assurance fulfillment entry,
    lineage statement, and documentation outcome move through their existing
    policy gates. No accepted ADR is edited without ADR-059, no hand-governed
    schema changes without its publication entry, and no requirement-backed
    child opens before DRAFT authority.

## Extensibility Seam

The stable seam is one resolved behavioral-relation profile plus one
proof-evidence bundle:

```text
catalog relation
  -> closed relation profile
     -> left/right model + projection + mapping digests
        -> claim binding + axis-specific evidence bundle
```

The relation profile is parameterized by participant/audience, carrier
revisions, label/projection partition, model dimensions, initial relation, and
quantifier domain. Runtime, backend, conformance, study, and documentation
consumers reference it; they do not copy its coordinates.

This allows the next theorem—another policy pair, a larger finite carrier,
policy change, controller handoff, a concurrent order model, a different
observer, an unbounded coinductive proof, or a second backend mapping—to add a
profile/model/evidence bundle without editing every claim carrier or creating a
new checker/report/store. A timed, probabilistic, strategic, or true-concurrent
relation may still require a new governed relation; the profile seam cannot
disguise a changed mathematical property as configuration.

## Gotchas And Anti-Patterns

Avoid:

- proving the test-local SEM-230 helper and calling it normative;
- calling schema equality, matching digests, projected-history equality,
  passing probes, two shared traces, or exhaustive tests bisimulation;
- selecting the complete reference runtime while modeling only crossing
  decisions;
- generating both systems from one self-confirming transition table;
- using strong, weak, branching, divergence-preserving, stuttering, alternating,
  probabilistic, timed, or partial-order terminology interchangeably;
- hiding every runtime-internal or backend-native action as `tau`, or ignoring
  divergence, deadlock, refusal, omission, error, and termination;
- treating a redacted occurrence, denial, unsupported result, or sanitized
  error as unobservable by default;
- treating UUID/timestamp removal as harmless without a projection argument;
- treating one scheduler linearization or per-participant lock as a concurrent
  or partial-order theorem;
- treating finite depth, sampled schedules, timeouts, or state-space
  truncation as a complete finite carrier;
- classifying an explicit-state equivalence result as `proof` when the shared
  assurance axis requires `model-check`;
- promoting one positive profile to the generic relation, whole runtime, every
  policy, every participant, or any backend;
- inferring noninterference or opacity from bisimulation without the separate
  secret/low-equivalence preservation theorem;
- copying relation/profile coordinates into API-423, backend manifests,
  conformance reports, runtime metadata, audit details, or local enums;
- adding a relation registry, profile family, proof report, validator stack,
  exception hierarchy, logger, audit channel, persistence store, or workflow
  beside the incumbents;
- passing model/policy content or secrets through environment variables, argv,
  filenames, logs, diagnostics, witnesses, or CI artifacts;
- using floating tool versions, unverified downloads, mutable container tags,
  opaque hosted results, shell evaluation, unrestricted subprocess output, or
  network-dependent proof runs;
- treating a tool exit code as a certificate it did not emit; and
- opening proof children before DRAFT authority or updating scientific
  completeness/documentation before independent reproduction.

## Non-Goals And Implementation Boundaries

- No theorem selection, relation profile, catalog revision, proof-tool decision,
  formal model, generator, checker, witness, counterexample corpus, proof,
  model check, runtime mapping, or CI job is delivered by this preflight.
- No SEM-230/231 amendment, noninterference or opacity result, runtime
  enforcement claim, backend declaration, realization, conformance, or
  cross-backend equivalence is made.
- No SDL syntax, policy language, participant gateway, route, transport,
  endpoint, UI, credential broker, plugin, provider integration, daemon,
  scheduler, or OS sandbox is added.
- No new participant state/view/history, crossing/control carrier family,
  backend profile family, conformance runner, exception hierarchy, logger,
  audit stream, persistence store, or generic proof schema is created.
- No Ground Control requirement or GitHub child issue is created. The design
  work must disposition existing authorities, create the required DRAFT owner,
  and only then open dependency-ordered implementation/proof/reproduction work.
