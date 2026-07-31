# Issue #963 — Participant Opacity Mathematical-Proof Preflight

Date: 2026-07-31

Issue: #963.

Requirements: `SEM-231`, `ASR-535`.

This note records repository-wide architecture guardrails for the mathematical-
proof assurance lane. It is guidance only. It does not state or mechanize the
theorems, select or pin a tool release, add a proof profile or evidence
contract, run a prover, change catalog assurance, establish opacity of a RAES
system, enforce a policy, synthesize a supervisor, or certify a backend.

## Decisive Current-State Finding

Issue #963 is a proof over the existing SEM-231 relation and its relationship
to SEM-230. It is not another opacity checker or formal-assurance subsystem.

- ADR-099 and the SEM-231 specification own the one-sided possibilistic
  opacity kernel, possible points, observer information cells, strategies,
  release, memory, supervisor visibility, and relation boundaries.
- ADR-085 and SEM-230 own policy noninterference, low equivalence, complete
  projected-history support, exact-cut declassification, adaptive low
  strategies, scheduler/environment classes, and order assumptions.
- ADR-081, the behavioral-relation catalog, the shared relation profile, and
  `BehavioralClaimBindingModel` already own relation identity, claim scope,
  assurance axis, evidence scope, limitations, and explicit nonclaims.
- Issues #961 and #962 already own executable finite falsification, the shared
  information-cell kernel, exact finite-state exploration, safe
  counterexamples, and replay. Those artifacts are supporting examples and
  regression oracles, not premises accepted on trust by the mathematical
  proof.
- The participant-bisimulation proof-tool decision already identifies
  Isabelle/HOL as the repository's proportionate route for a parameterized or
  unbounded, kernel-checked relational theorem. Python tests, the in-process
  model checker, Z3 satisfiability, mCRL2 finite equivalence, and a successful
  process exit do not establish this issue's proof axis.

Two gaps must be closed by the later implementation. First, “eligible
predicate” is not yet a formal assumption: noninterference cannot manufacture
a nonsecret alternative for a predicate that is true everywhere in a public
initial-state class. Second, the only published opacity profile is explicitly
fixture-bound and finite (`finite-possible-points`, finite bounds, and a
`declared-complete-finite-carrier` scope). It cannot honestly bind an abstract
theorem by changing only its assurance axis.

No new ADR, relation id, relation registry, proof-result family, runtime
package, exception hierarchy, logger, store, endpoint, or authentication path
is justified. The missing boundary belongs in a proof-specific preflight,
formal theorem source, a non-finite variant of the existing closed relation-
profile seam, and one checked evidence bundle.

## Expanded Verification-Execution Scope

During implementation, the canonical verification graph exposed a separate
repository architecture problem: its independent gates were composed as one
serial session, unit and integration tests shared a mutable coverage file, and
the local completion path waited on rate-limited external HTTP link checks.
Warm-cache execution therefore took about 13 minutes before the organization
rename and about 18 minutes after new GitHub links encountered public rate
limits. Retrying a timed-out caller restarted the complete graph.

Issue #963 now also owns the bounded remediation needed to make this proof lane
practical without weakening assurance:

- one parent `verify` session synchronizes the locked Python environment once;
- static checks, contracts, the Isabelle proof, unit tests, integration tests,
  and deterministic documentation checks execute as six isolated nox
  subprocess lanes, concurrently;
- the parent caps simultaneous lanes at the smaller of four or half the
  available CPU affinity, the unit lane uses at most half those CPUs through
  xdist, and the JSON batch pool uses at most one quarter, preventing the graph
  from treating every nested layer's local maximum as independently available;
- lanes are queued longest-first so unit, integration, and contracts start
  immediately, while proof and documentation backfill the slots released by
  static checks instead of adding to the initial process burst;
- JSON contract validation groups all metaschemas together and instances by
  shared schema, then executes those batches with a bounded four-worker pool
  instead of launching one tool process for each of 246 artifacts;
- unit and integration lanes write separate coverage data files, and the parent
  combines and thresholds them only after every lane succeeds;
- local verification builds documentation without external HTTP requests,
  while the pull-request docs workflow retains a separately visible and
  blocking external-link session;
- direct `verify` and CI still include repository policy; the Ground Control
  completion session omits only that lane because the workflow's mechanically
  paired `policy_command` runs it immediately afterward; and
- every lane is reported even when another lane fails, so parallelism does not
  reduce diagnostics or create fail-open cancellation behavior.

The target is a warm-cache critical path governed by the slowest deterministic
lane rather than their sum. This change does not cache successful results,
silence failures, reduce coverage, parallelize stateful integration tests
internally, or make external-link health a local-network prerequisite.

## Architecture Decisions And Guardrails

### Prove a small theorem suite over one explicit carrier

The mechanized source must define one abstract possible-point carrier `Omega`,
initial-information function `Init`, accumulated-observation function `Obs`,
selected predicate `S`, and information cell:

```text
I(x) = { y in Omega | Init(y) = Init(x) and Obs(y) = Obs(x) }.
```

The positive theorem suite is limited to:

1. the SEM-231 one-sided opacity kernel;
2. its knowledge characterization: no protected actual point has an
   information cell wholly contained in `S`; and
3. the conditional implication from the exactly matching SEM-230 policy-
   noninterference instance to SEM-231 opacity for every predicate satisfying
   the declared eligibility assumptions.

The proof must not import the Python kernel's result as an axiom or prove only
that the implementation returns a value. The formal definition is the
authority; `_kernel.py`, #961, and #962 are executable agreement and mutation
evidence. Any claim that the Python implementation realizes the mechanized
definition would require a separate correspondence theorem or checked
translation and is not part of #963.

Knowledge must be defined over the exact information cell. If the proof uses
the epistemic word “knowledge,” it must establish the information relation's
reflexivity/factivity conditions rather than treating an arbitrary relation as
an S5 accessibility relation. The characterization must preserve the
one-sided polarity: learning `not S` remains allowed.

### Make the noninterference implication genuinely conditional

The implication theorem must quantify in this order, or an explicitly
equivalent order:

```text
for every matching profile and SEM-230 parameter instance,
  for every eligible predicate S,
    if SEM-230 policy noninterference holds,
      then SEM-231 participant-predicate-opacity holds.
```

“Matching” is a checked premise, not prose. It requires the same model and
reachable carrier construction; participant or coalition and audience;
initial public information; complete observation projection; participant
memory; exact cut/horizon; active-strategy domain; supervisor visibility;
policy sequence and declassification schedule; scheduler/environment class;
nondeterminism support; time, progress, concurrency, and order interpretation;
and probability posture.

“Eligible” must require at least a nonsecret high variation for every protected
actual initial/public class and preservation of that nonsecret label on the
alternative point selected from equal SEM-230 low-history support. It must
also require that the alternative is reachable under the same active strategy
and all other coordinates that the opacity profile fixes. A tautological
predicate, a predicate fixed by public initial information, or a predicate
whose only nonsecret alternative lies outside the admitted carrier is not
eligible.

For an active profile, the strategy quantifier remains outside the actual-
point obligation and the actual and alternative points use the same strategy.
For a coalition, the theorem sees the declared fused observation and memory;
individual results cannot be combined after the fact. For release, the theorem
assumes the same exact-cut schedule and evaluates the post-release predicate
and observation state. Revocation or concealment never supplies a memory-reset
axiom.

SEM-230 compares complete support sets. If the opacity profile requires the
same individual scheduler, environment, or order choice for a witness rather
than membership in the same declared class, that stronger matching condition
must be an explicit premise. The proof must not hide this choice in a
convenient witness selection.

### Mechanize the invalid implications as checked negative boundaries

The same proof session must contain checked countermodels or negative lemmas
for the issue's invalid promotions:

- opacity of one predicate does not imply policy noninterference;
- one equal-history secret/nonsecret pair does not satisfy the universal
  secret-point obligation;
- declassification can change the information cell and knowledge;
- later revocation or concealment does not erase a retained observation; and
- epistemic indistinguishability, trace equivalence, simulation, refinement,
  or bisimulation without secret/observation preservation can hold while
  opacity fails; and
- an untimed possibilistic theorem supplies no timed, probabilistic,
  quantitative, coalition, all-linearization, partial-order, or stronger
  progress result.

Epistemic indistinguishability is the information-cell membership relation,
not opacity itself. Trace equivalence, simulation, refinement, and
bisimulation may be used only behind a separately stated secret-, reachability-,
and observation-preservation theorem. Do not add axioms that make these
relations definitionally equal merely to obtain the desired implication.

Negative evidence is a checked countermodel or theorem with a stable theorem
id. A proof script that merely fails, a commented-out theorem, `sorry`, an
admitted fact, an oracle, or an expected nonzero process exit is not durable
negative evidence. The session and evidence gate must reject unfinished proof
features and undeclared axioms.

### Reuse the shared profile and claim authorities without relabeling the fixture

Every positive proof claim remains a `BehavioralClaimBindingModel` for
`participant-predicate-opacity` with `assurance_axis=proof`,
`assurance_status=proved`, and `evidence_scope=proof`. Use one binding per
positive theorem scope, with exact theorem ids and evidence refs. The
knowledge lemma and the conditional implication do not create relation ids
such as `knowledge-opacity` or `noninterference-implies-opacity`.

A passive theorem instance uses `quantifier_scope=all-traces`; an active
instance uses `quantifier_scope=all-strategies`. The active label cannot be
inferred merely because the abstract theory has a strategy type.

The existing `participant-opacity-baseline-v1@sem-231/rev2` artifact is bound
to the finite fixture carrier and taxonomy `rev8`. It remains the #961/#962
profile and must not be mutated, reinterpreted as abstract, or replayed against
ambient latest catalog/profile bytes.

The proof needs a distinct, immutable profile artifact through the existing
`BehavioralRelationProfileModel` registry and loader. Generalize the existing
closed carrier/assurance-scope discriminant so a theorem profile can name an
abstract SEM-231 carrier and omit finite bounds; do not create a parallel
`ProofProfileModel` registry or copy the observer, secret, memory, release,
strategy, scheduler, environment, order, and time fields. Finite and theorem
variants share those semantic coordinates but retain different carrier and
evidence invariants.

If the published profile schema changes, its Python model, hand-governed JSON
Schema, semantic invariants, fixtures, generated bundle, conformance validator
routing, publication entry/hash, corpus packaging, and compatibility decision
move together. Earlier rev8 catalog/profile/model-check bytes and digests must
remain available to reproduce #962 evidence. A taxonomy assurance update
advances the taxonomy revision; it does not rewrite historical evidence or
silently substitute a current profile.

Stored claims and replay must resolve the profile by `(profile_id,
profile_revision)`. The incumbent id-only loader may remain a latest-authoring
convenience, but it is not an admissible historical-evidence resolver.

### Keep proof evidence repository-local until a portable consumer exists

Do not reuse `participant-opacity-model-check-evidence-v1`,
`scheduler-isolation-proof-v1`, `BackendConformanceReport`, an API-423
occurrence, `RuntimeSnapshot.metadata`, `AuditEvent`, or operation details as a
mathematical proof record. Their domains and trust boundaries differ.

The proof sources and session definition belong with formal authority under
`specs/formal/participant-semantics/`. A closed proof-evidence manifest should
follow the existing formal-semantic-validation protocol/bundle/execution-
snapshot convention and embed the incumbent `BehavioralClaimBindingModel`
directly. It must bind:

- theorem ids and exact human-readable statements;
- catalog, profile, SEM-230, SEM-231, source, and dependency revisions/digests;
- carrier construction and every assumption named by the issue;
- prover name/version, distribution checksum or immutable container digest,
  session configuration, and proof-kernel result;
- fixed replay command, working directory, locale, platform boundary, resource
  limits, and verification-time network posture;
- source and generated-artifact digests, with generated output distinguished
  from the checked source;
- every positive theorem, negative lemma/countermodel, and mutation id;
- exact proof-axis claim bindings, limitations, and explicit nonclaims; and
- an independently reproduced result and expected digest.

The outer manifest may remain a repository-owned, strictly checked evidence
shape while there is no external contract consumer. It must not invent a
generic portable proof vocabulary. If a portable consumer is later identified,
publish a domain-appropriate `ContractModel` through the normal schema bundle
instead of stabilizing an ad hoc JSON shape.

One semantic gate owns all cross-field joins. Pydantic or JSON shape validation
does not establish theorem success; a prover exit code does not validate the
claim/profile/catalog joins; and `tools/check_behavioral_relation_claims.py`
must still resolve every embedded claim through the canonical validator.

### Use a kernel-checked development tool, not a runtime dependency

Use the existing Isabelle/HOL theorem route identified by the participant-
bisimulation proof-tool decision for the parameterized/unbounded theorem. If a
different prover is selected, a scoped tool decision must first demonstrate
equivalent kernel checking, deterministic noninteractive replay, unfinished-
proof rejection, CI feasibility, immutable pinning, licensing, and independent
reproduction. Repository implementation language is not a selection reason.

The prover is development/verification tooling under `tools`, `noxfile.py`,
and CI. It is not a dependency of `raes`, `raes_contracts`, `raes_processor`,
the CLI runtime, control plane, conformance runner, or backend. The canonical
verification graph invokes one fixed wrapper/session; no issue-local shell
script or hosted proof service becomes an authority.

Catalog `proof_status` remains `deliberately-unproved` until the complete
pinned session, negative boundaries, manifest joins, and clean replay pass.
Tool absence, timeout, resource exhaustion, network dependence, stale digest,
missing theorem, admitted axiom, or replay drift fails closed and cannot emit
or retain a positive proof binding.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Opacity authority | ADR-099 and `specs/formal/participant-semantics/participant-predicate-opacity.md`; theorem sources formalize this kernel and do not redefine it from Python behavior. |
| Noninterference premise | ADR-085 and `specs/formal/participant-semantics/information-flow-control.md`; reuse low equivalence, complete support sets, exact-cut release, memory, strategy, scheduler/environment, and order coordinates. |
| Relation/profile/claim authority | ADR-081, the behavioral-relation catalog, `BehavioralRelationProfileModel`, corpus loader, `BehavioralClaimBindingModel`, `validate_behavioral_claim_binding()`, and `tools/check_behavioral_relation_claims.py`. |
| Executable agreement evidence | `raes_processor.participant_opacity._kernel`, #961 bounded evidence, #962 exact-model evidence/replay, and their single-fault mutations. These are regression evidence, not proof axioms or proof certificates. |
| Formal-method policy | ADR-007/018, `specs/formal/assurance-policy.yaml`, and `specs/formal/assurance-fulfillment.yaml`; keep the FM3 classification and proportional, reproducible evidence. |
| Proof-tool precedent | `docs/research/participant-bisimulation/proof-tool-decision.md` and the Isabelle/HOL parameterized-theorem route. mCRL2's finite equivalence result remains a separate model-check lane. |
| Evidence convention | `docs/research/formal-semantic-validation/` protocol, bundle manifest, execution snapshot, safe repo-path resolution, bounded command output, empty/allowlisted environment, digest joins, and replay gate. |
| Digests and ingress | `ContractModel(extra="forbid")`, `parse_bounded_json_object()`, safe refs/revisions, `PrefixedDigestString`, and RFC 8785 `canonical_json_digest()` / `canonical_contract_digest()`. |
| Diagnostics/errors | Existing policy-gate failures, bounded safe diagnostics, and value-free operational failure posture. Do not import conformance only for its sanitizer or add a proof exception hierarchy. |
| Artifact handling | Canonical JSON, root-confined repository paths, safe labels, validated manifests, and atomic writes where a generated artifact is persisted. Add no mutable witness or proof store. |
| Schema/publication | `schema_bundle()`, hand-governed `contracts/schemas/`, fixtures, `x-raes-invariants`, schema-publication entries, generated-schema parity, and compatibility checks if the shared profile contract changes. |
| Tooling/workflow | `tools/tool_versions.py`, checksum-verified tool acquisition precedents, `noxfile.py`, pinned CI actions, `.ground-control.yaml`, `.gc/plan-rules.md`, requirement governance, and `tools/verify_all.py`. Governed commands use `RAES_REQUIREMENT_UID=ASR-535` because the branch name contains issue 963 but not the requirement UID. |

Package ownership remains unchanged. `specs/formal` owns the theorem source;
`raes_contracts` owns portable relation/profile/claim shapes;
`raes_processor` owns executable finite analysis only; `tools` and nox own
proof replay; runtime, operations, conformance, and backend packages are not
proof authorities.

## Cross-Cutting Layers And Security Posture

1. **Authority and config shape.** Proof semantics come from committed formal
   sources and one closed profile, not SDL metadata, YAML expressions, Python
   import paths, remote URLs, environment variables, or caller-authored
   theorem text. Profile and manifest JSON use bounded UTF-8, duplicate-member
   rejection, object-root checks, safe ids, exact revisions, and digests.
2. **Schema and semantic joins.** The profile passes its published schema and
   `ContractModel`; the claim passes `BehavioralClaimBindingModel`; the shared
   validator joins catalog, profile, carrier, projection, quantifier, axis,
   evidence, limitations, and nonclaims. A proof-specific gate then joins
   theorem ids, assumptions, source/tool digests, and replay result exactly
   once. Neither layer duplicates the other's validation.
3. **Authentication and policy boundary.** The proof is local, read-only
   development tooling. It crosses no HTTP authentication, control-plane
   identity/role/target binding, RUN-319 authorization, API-407 capability,
   runtime mediation, persistence, or backend boundary and makes no claim
   about them. Any future service exposure must reuse
   `create_control_plane_app()`, strict security defaults, request bounds,
   identity/target binding, fingerprints/idempotency, audit, and the redacted
   error envelope; #963 adds no route.
4. **Supply-chain and tool gate.** Pin the prover release and every theory or
   component dependency by immutable digest. Verify acquisition before use and
   record the measured version. Verification runs offline; it does not fetch
   sessions, packages, archives, theories, or containers on demand and does
   not rely on ambient credentials or a mutable hosted service.
5. **OS/process exposure.** Invoke a fixed allowlisted executable with list-
   form argv and no shell, from a fixed repository-relative session path.
   Use a temporary tool state/home, deterministic locale, allowlisted
   environment, no network, bounded CPU, wall time, output, and per-process
   address space, plus explicit Java and ML heap ceilings. Report these as
   per-process/per-runtime limits, never as aggregate process-tree accounting.
   Mount only the pinned prover distribution, fixed session inputs, required
   system runtime paths, and private scratch state; never bind the host root,
   user home, or repository-wide workspace into the proof sandbox.
   Do not place theorem contents, predicates, models, witnesses, credentials,
   tokens, complete evidence, or host paths in argv, environment variables,
   filenames, shell history, process listings, stdout/stderr, or host logs.
6. **Secret-handling boundary.** Formal sources use abstract types and
   synthetic examples only. Profiles, countermodels, manifests, logs, CI
   artifacts, and review output contain safe refs, theorem ids, counts, and
   digests, never real secret values, participant content or memory, policy
   bodies, supervisor internals, credentials, rejected payloads, native
   objects, environment dumps, or hidden world state. Hashing sensitive content
   does not make it publishable.
7. **Diagnostic and error-envelope gate.** Expected failures use bounded stable
   codes and safe theorem/profile coordinates. Do not copy raw prover output,
   source excerpts, Pydantic `input_value`, exception text, tracebacks, paths,
   or environment data into the manifest, CLI summary, audit, or documentation.
   A failed proof produces no positive evidence. A future HTTP boundary keeps
   the incumbent `{"detail":"internal server error"}` response.
8. **Artifact and persistence gate.** Validate claims, theorem coverage,
   digests, nonclaims, and redaction before canonical serialization or atomic
   publication. Committed proof evidence is immutable and replayable. It never
   enters runtime snapshots, operation details, audit blobs, backend reports,
   a database, or a new evidence service.
9. **Logging and observability gate.** Progress and prover logs are not proof
   evidence. Retain only bounded safe summaries needed to diagnose the gate;
   the validated manifest carries the exact result and provenance. CI uploads
   the bounded evidence bundle, not the workspace, tool cache, environment,
   unrestricted logs, or prover installation.
10. **Governance gate.** A proof assurance change advances the catalog
    revision and every current producer, reader-facing specification, fixture,
    profile, claim-policy surface, and lineage/nonclaim reference together.
    Historical model-check evidence remains bound to its original bytes. The
    canonical policy, schema, docs, tests, and full verification graph remain
    the only delivery workflow.

## Whole-Repository Surfaces In Scope

- **Normative authority:** ADR-081/085/099, SEM-230, SEM-231, the behavioral
  catalog, relation profile, claim validator, and assurance aggregates.
- **Proof source and evidence:** one formal session beside SEM-231, exact
  theorem/negative-lemma ids, a closed checked manifest, pinned tool provenance,
  and clean replay.
- **Portable contracts:** only the existing profile and claim authorities, plus
  their schema/publication surfaces if the finite-only profile discriminant is
  generalized. No generic proof-result contract is presumed.
- **Verification:** proof replay, unfinished-proof/axiom rejection, negative
  countermodels, profile and claim joins, historical digest replay, claim
  policy, schema/concept/JSON/docs gates, and the canonical nox graph.
- **Host/CI:** checksum-verified acquisition, offline bounded execution,
  temporary tool state, safe argv/environment/output, and bounded artifact
  upload. Runtime, backend, conformance, control-plane, and data-store layers
  are explicit non-traversed boundaries.

## Extensibility Seam

The stable seam is:

```text
SEM-231 relation
  -> resolved closed theorem profile
     -> parameterized possible-point / information-cell locale
        -> optional matching SEM-230 locale and eligibility premise
           -> named checked theorems and countermodels
              -> proof-axis claim bindings and replay manifest
```

The required parameter is the resolved relation profile plus an explicit
SEM-230-to-SEM-231 correspondence record for the implication theorem. The
theorem locale must parameterize the carrier, observer projection, secret,
memory, strategy, release, scheduler/environment, time, and order coordinates
rather than hard-code the finite fixture or Python field layout.

A future eligible predicate, observer, active-strategy domain, coalition fusion
rule, release schedule, or total-order model can instantiate the same kernel
only when its profile and correspondence obligations are discharged. A timed,
probabilistic, quantitative, progress-sensitive, or true partial-order result
needs its own semantics and proof obligations; the seam rejects that lift
rather than adding an unchecked Boolean option.

## Gotchas And Anti-Patterns

Avoid:

- relabeling #961 bounded evidence or #962 finite model-check evidence as
  `proof`, or treating exhaustive Python execution as a mathematical theorem;
- binding an abstract theorem to the fixture-only baseline profile or changing
  its carrier/digest under `sem-231/rev2`;
- claiming noninterference implies opacity without the nonsecret-variation,
  reachability, secret-preservation, and exact profile-correspondence premises;
- treating a tautological predicate or one fixed by public information as an
  eligible secret;
- reversing the implication from one-predicate opacity to noninterference;
- replacing the universal secret-point obligation with one equal-history pair;
- defining knowledge without the exact information cell and its
  reflexivity/factivity boundary;
- changing active strategy, memory, release, scheduler, environment, order, or
  supervisor posture between actual and witness points without an explicit
  theorem premise;
- treating declassification as knowledge-preserving or revocation,
  concealment, reset, rollback, or supersession as erasure;
- treating trace equivalence, epistemic indistinguishability, simulation,
  refinement, or bisimulation as opacity without a checked preservation
  theorem;
- lifting the possibilistic untimed result to probability, posterior risk,
  entropy, timing, progress, coalition sharing, all schedules, partial order,
  or quantitative leakage;
- accepting admitted axioms, unfinished proofs, skipped sessions, timeout,
  unavailable tooling, mutable pins, network fetches, stale digests, missing
  negative lemmas, or replay drift as positive evidence;
- creating another relation/profile registry, claim DTO, generic proof schema,
  exception hierarchy, logger, store, executable, endpoint, auth stack, or
  workflow;
- making the prover a Python/runtime dependency or invoking it through a shell,
  user-controlled command, import path, URL, or environment-selected profile;
  and
- publishing raw tool output, host paths, source excerpts with sensitive
  values, model content, predicates, witnesses, credentials, or environment
  data in artifacts or errors.

## Non-Goals And Implementation Boundary

Issue #963 may state and independently check the one-sided opacity kernel, its
knowledge characterization, the exactly conditional SEM-230 implication, and
the required negative lemmas; bind them to an abstract closed theorem profile
and proof-axis claims; and integrate hermetic replay with repository
verification.

It does not:

- prove that RAES, RUN-319, the reference runtime, or any backend satisfies or
  enforces opacity or SEM-230 policy noninterference;
- authenticate a source model, synthesize a supervisor or policy, mediate a
  crossing, or add backend declaration, realization, or conformance;
- prove the Python checker corresponds to the formal theorem, certify #961 or
  #962 materializers, or replace their finite evidence;
- prove the reverse implication, arbitrary predicates without eligibility,
  symmetric opacity, erasure, anonymity, trace inclusion/equivalence,
  simulation, refinement, or bisimulation;
- establish timed, progress-sensitive, probabilistic, quantitative,
  coalition, all-schedule, causal-frontier, or partial-order variants outside
  an exact independently proved profile;
- add SDL syntax, an executable secret-predicate language, a world/history or
  belief store, runtime API, proof service, backend feature, or operational
  persistence; or
- make any proof claim before the pinned tool, complete session, negative
  boundaries, exact manifest joins, independent replay, and catalog/profile
  revision discipline all pass.
