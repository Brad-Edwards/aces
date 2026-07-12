# Issue 727 Scientific-Scenario Completeness Profile Preflight

Date: 2026-07-12

Issue: #727.

Requirement: GOV-942. The requirement plus the issue title, body, and
acceptance criteria are the contract.

This note fixes the architecture guardrails for a versioned REV1 scenario
completeness matrix. It does not publish the matrix, add a profile schema or
loader, change SDL validity, declare any profile complete, or add examples.
No new ADR is needed: ADR-009, ADR-016, ADR-019, ADR-055, ADR-061, ADR-066,
ADR-068, ADR-070, ADR-072, ADR-073, ADR-074, and ADR-079 already fix the
authority and concept boundaries this issue must compose.

## Decision Boundary

REV1 answers one question: **which semantic surfaces must be present, may stay
underspecified, or are excluded for a stated scenario-use claim, and what is
the repository's current delivery status for each required surface?** It is a
scope and claim contract. It is not another SDL grammar, validator-strength
record, backend feature manifest, experiment artifact, or runtime admission
decision.

The five profiles form an intended-use progression, not five subclasses of
`Scenario` and not an automatic proof ordering:

1. valid SDL fragment;
2. deployable scenario intent;
3. participant-evaluation scenario;
4. controlled experiment scenario; and
5. reproducible benchmark/study input.

Structural SDL validity remains permissive. `name` is the only required
top-level authoring field; a fragment that passes source, closed-model, and
semantic checks does not thereby satisfy any stronger completeness profile.
Conversely, stronger profiles compose existing SDL and experiment contracts;
they must not make experiment tasks, runs, studies, evidence, or apparatus
context new SDL top-level sections.

## Canonical Matrix Model

Use one canonical, machine-readable, revision-labelled matrix with stable
profile ids and stable, atomic concern ids. Reader-facing prose or tables must
be generated from, or mechanically checked against, that authority. A concern
row must not combine independently deliverable facts merely because the issue
lists them together. For example, parameter typing, factor declaration,
allocation/randomization, and seed preservation need separate rows when their
statuses differ.

Keep these two dimensions separate:

- **profile disposition**: `required`, `allowed-underspecified`, or
  `excluded`; and
- **delivery status**: exactly `implemented`, `partial`, `external-contract`,
  `deliberately-excluded`, or `missing`.

Each concern row must also name its semantic owner, evidence paths, limitation,
and issue/requirement reference where applicable. `external-contract` is valid
only when a named, versioned non-SDL contract supplies the concern and the
profile states the binding obligation. A link to an open issue, proposed ADR,
formal design, or prose aspiration is not implementation evidence.

A profile may be labelled complete only when every `required` row is either
`implemented` or a satisfiable `external-contract` with a named contract id
and version, binding location, executable validation/evidence path, and no
unresolved integration gap. `partial` and `missing` always block completeness.
`deliberately-excluded` can satisfy only an `excluded` row, never a required
one. Omission is not a status. Profile completeness must be computed from rows,
not hand-authored as an independent boolean that can drift.

REV1 is a revision of the completeness taxonomy, not the SDL source version,
semantic canonicalization profile, software release, or current delivery
snapshot. Preserve a separate, explicit delivery-assessment revision (and
assessed repository release/commit or date) so an implementation status change
does not silently mutate the meaning of REV1. Completeness is always computed
for `(profile revision, delivery assessment revision)`. The extensibility seam
is `(profile_family, profile_revision, profile_id, concern_id)` joined to a
versioned delivery assessment by `concern_id`, with dispositions parameterized
by profile id. A later concern should add an atomic row; a later profile should
add a disposition record; a delivery change should publish a new assessment;
and a semantic change to existing profile or concern meanings should publish a
new profile revision rather than silently edit REV1. Do not bake five profiles
into five validators or five model classes, and do not repeat one concern's
delivery status in every profile cell.

Normative prose belongs under `specs/`. Publish the canonical closed matrix
under the existing `contracts/profiles/` root and validate it through the
existing contract, fixture, schema-publication, and corpus-packaging machinery.
That root is currently described in parts of the authority stack as
"capability profile declarations" even though it also contains semantic
profiles. The implementation must update the canonical authority description
and its drift fixtures once to cover governed versioned profile declarations,
while keeping backend, semantic, validation, and scientific-completeness
profile families explicitly distinct by subdirectory, schema, ids, and prose.
Do not smuggle this matrix in as a backend capability profile and do not create
a second profile root. Do not introduce a machine-readable duplicate merely to
render a Markdown table; derive or check reader-facing views against the one
authority. Examples remain non-normative under `examples/`, while valid/invalid
contract fixtures belong under `contracts/fixtures/`.

## Concern Ownership And Reuse

The matrix must disposition every issue concern against these incumbents. A
row may cite several incumbents, but it must not copy their schemas or redefine
their terms.

| Concern | Canonical incumbent and boundary |
| --- | --- |
| Structural fragment validity | `specs/sdl/document-model.md`, `sections.md`, `diagnostics.md`, `sdl-yaml/v1`, `contracts/schemas/sdl/sdl-authoring-input-v1.json`, `load_sdl_yaml`/`parse_sdl`, `SDLModel(extra="forbid")`, and `SemanticValidator`. This is the floor, not completeness. |
| Authored versus observed state | ADR-033 and ADR-066; `specs/sdl/observability-and-evidence.md`; authored SDL, runtime snapshots/results/history, evidence records, and derived measures remain distinct planes. |
| Scoped specificity and open-world intent | ADR-070; `specs/formal/realization/explicitness-and-realization.md`; `aces_sdl.explicitness`, `CompiledRealizationRequirement`, realization envelopes, provenance, and disclosures. Exact/constrained/open is not inferred from field omission ad hoc. |
| Parameters, factors, controlled variation, randomization, and seeds | SDL variables/`instantiate_scenario()` own scenario substitution. ADR-055/068/074 and the existing `experiment-authoring-input-v1`, task, run, study, apparatus, parameter, stochastic-control, factor, allocation, replication, stopping-rule, and cross-artifact validators own experimental design and archival realization. Do not duplicate these in `Scenario`. |
| Propositions and assertions | ADR-079; `specs/formal/objectives/proposition-and-assertion-semantics.md`; the existing proposition/assertion/condition models, reference catalog, shared semantic analyzers, truth domain, evidence basis, and evaluator-capability seams. Probe success is not proposition truth. |
| Cleanup and rollback | Workflow compensation semantics under ADR-006 and the formal workflow state machine own authored compensation. Backend teardown/reconciliation owns resource cleanup. Manual/advanced rollback remains an explicitly documented gap in `docs/explain/sdl/limitations.md`; do not merge these meanings into one boolean. |
| Time domains, clocks, ordering, deadlines, and pacing | ADR-022 participant time semantics, formal participant concurrency/time contracts, objective-window analysis, experiment clock context, and run timestamps are bounded incumbents. `docs/explain/sdl/limitations.md` and the related-work comparison state that the full SDL time/clock authoring model is incomplete. A timeout or timestamp alone must not satisfy this row family. |
| Episodes, reset, budgets, trajectories, hidden assets, verifiers, and rewards | ADR-013/022/054/067/069/073, participant episode/runtime contracts, participant histories, observation boundaries, outcome interpretation, experiment evidence/results, and CAGE-2 replication artifacts own the implemented portions. Graded reward/scoring is deliberately outside authored SDL; hidden truth and benchmark assets require view-boundary and experiment provenance, not free-form scenario metadata. Split these into atomic rows because delivery status differs. |
| Credential-bearing setup/provisioning | ADR-056/057 and the existing account/runtime-value classification distinguish intentional scenario credentials from operator secrets. Provisioning plans, apparatus context, participant/backend manifests, and realization provenance own setup. Raw operator credentials, tokens, keys, and environment dumps are never completeness evidence or portable profile content. |
| Host architecture and substrate constraints | ADR-055/063/070, experiment apparatus constraints/context, backend manifests and capability profiles, realization envelopes, compiled planning requirements, and realized-form disclosure. Do not encode Docker/libvirt/host-native choices as universal SDL semantics. |
| Vulnerability and weakness semantics | The existing `vulnerabilities` SDL section, concept-authority stack, controlled vocabularies/reference models, typed relationships, propositions/assertions, and evidence semantics. A vulnerability inventory entry is not proof of exploitability, reachability, or observed weakness. |
| Flexible step tooling | Existing scripts/workflows, action contracts, behavior specifications, participant implementation manifests, reusable artifact trust/integrity policy, and backend realization profiles. Tool names or ATT&CK labels are not portable behavior; arbitrary shell/argv must not become profile meaning. |

Status evidence must be taken from the current normative artifact plus an
executable surface where the claim requires behavior. Accepted ADRs and formal
specs establish meaning, not delivery by themselves. Appropriate evidence is
the published schema/fixture corpus, shared semantic validator/compiler/planner
agreement, contract validators, conformance results, runtime/evidence tests, or
an explicit external-contract binding. Research notes and roadmap issue state
may explain a gap but cannot upgrade its status.

## Existing Cross-Cutting Contracts

The implementation must build on these repository-wide incumbents:

- **Authority and publication:** ADR-009/019/061,
  `specs/authority/authority-boundary.yaml`, `contracts/schemas/`,
  `contracts/schema-publication-manifest.json`, `schema_bundle()`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`,
  `tools/check_json_artifacts.py`, `tools/check_authority_boundary.py`, and the
  existing `aces_contracts.corpus` packaged/source-checkout resolution seam.
- **SDL source and semantics:** `sdl-yaml/v1`, safe YAML ingress, source limits,
  duplicate-key and mapping-shape checks, `SDLModel(extra="forbid")`,
  `SemanticValidator`, `instantiate_scenario()`, canonical identifiers,
  `specs/sdl/sections.md`, and `specs/sdl/references.md`.
- **Experiment and evidence:** ADR-055/064/065/066/068/074; the existing task,
  authoring-input, run, study, apparatus, capture, evidence, derived-measure,
  traceability, realized-form, and augmentation contracts and their
  cross-artifact validators.
- **Capabilities and realization:** processor/backend/participant manifests,
  `manifest_authority`, backend profiles, controlled vocabularies, semantic
  profiles, realization envelopes/disclosures, and conformance runners.
- **Diagnostics and errors:** `SDLParseError`, `SDLValidationError`,
  `SDLInstantiationError`, collect-all semantic diagnostics, `Diagnostic`,
  `Severity`, operation envelopes, and `tools.policy.common.PolicyFailure` for
  repository checks. No completeness-specific exception hierarchy is needed.
- **Persistence and observation:** `RuntimeSnapshot` and `ControlPlaneStore`
  own live state; versioned experiment contracts own archival records; evidence
  refs/digests and bounded disclosures replace raw payload copies. The matrix
  itself is checked-in static authority, not a database or runtime cache.
- **Workflow and verification:** `.ground-control.yaml`, `.gc/plan-rules.md`,
  ADR-014, `noxfile.py`, `tools/verify_all.py`, repo-policy and requirement-
  governance checks, JSON/schema checks, Sphinx docs, and `SessionReporter`.
  The matrix is drift-prone by definition, so its semantic checker should emit
  `PolicyFailure` and be wired once into the canonical nox graph rather than
  duplicating CI logic. Reuse `check_json_artifacts.py` for schema validation;
  the focused checker owns only cross-row completeness and evidence/path
  invariants that JSON Schema cannot express.

Minimal examples must be validated by the same production parser/contracts and
must declare the exact completeness profile id and revision outside scenario
meaning unless a governed carrier already owns that field. Reuse existing
examples where they genuinely meet every required row, but do not relabel a
large showcase as minimal or complete. A stronger example should compose the
same scenario/snapshot with task, experiment-authoring input, apparatus, run,
study, and evidence artifacts as required; it must not inline those contracts
into SDL. Incomplete profiles may have gap illustrations, but those do not
satisfy the acceptance criterion for an implemented profile.

## Security And Operational Layers

The intended issue is a static normative profile and examples, so several
runtime layers are deliberately not traversed. The boundary must remain
explicit:

1. **Repository file/config gate:** read only fixed repo-relative normative,
   contract, and example paths as inert data. Resolve packaged/source corpus
   defaults through `aces_contracts.corpus`; validate any caller-controlled
   profile id before path construction using the closed id grammar established
   by `backend_profiles`, and confine checker-provided artifact/evidence paths
   with `tools.policy.common.safe_repo_path`. No absolute paths, `..`, symlink
   escape, dynamic import, evaluated YAML, or network fetch.
2. **SDL source/shape gate:** example SDL passes `sdl-yaml/v1` source limits,
   safe loading, duplicate-key checks, `SDLModel(extra="forbid")`, published
   schema parity, semantic validation, and post-instantiation revalidation.
   Completeness checking observes these results and does not replace them.
3. **Contract/config-shape gate:** any machine-readable profile or composed
   experiment example uses closed `ContractModel` shapes, published schemas,
   `x-aces-invariants`, fixture validation, cross-artifact validators, and the
   schema-publication manifest. No untyped metadata or parallel DTO/model is
   acceptable.
4. **Authentication/authorization gate:** no auth or control-plane endpoint is
   in scope. If a future service exposes completeness evaluation, it must reuse
   `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   target-bound role authorization, request-size limits, idempotency,
   fingerprints, and audit events; this issue must not add a weaker endpoint.
5. **Secret-handling gate:** profiles, matrix rows, examples, fixtures,
   diagnostics, logs, and docs may contain only safe identifiers, refs,
   classifications, digests, and bounded summaries. They must not contain
   operator credentials, bearer tokens, private keys, hidden answer material,
   raw prompts, environment dumps, raw backend objects, or raw evidence.
   Intentional scenario credentials remain governed by ADR-056/057 and must not
   be copied into the matrix or public evidence.
6. **Environment and OS/process gate:** add no environment binding, daemon,
   database, mutable cache, shell evaluation, or external command carrying
   profile payloads/secrets in argv. Repository checks use fixed argv in the
   existing nox environment and write no generated authority.
7. **Error-envelope and observability gate:** repository drift produces bounded
   `PolicyFailure` records with profile/concern ids and repo locations. SDL and
   contract example failures retain their existing error/diagnostic surfaces.
   Do not print rejected payload bodies, raw values, tracebacks, or backend
   exceptions. `SessionReporter` is sufficient; no new logger or telemetry
   stack is warranted.
8. **Persistence/distribution gate:** the checked-in normative artifact is the
   durable matrix. Examples/fixtures are packaged only through the canonical
   corpus/build paths. Do not persist profile claims in runtime snapshot
   metadata, audit blobs, tags, logs, or a new repository/service.

## Gotchas And Anti-Patterns

Avoid:

- treating `name`-only structural validity as deployability or scientific
  adequacy;
- treating a formal design, accepted ADR, open issue, schema property, or
  example mention as implemented behavior;
- one status cell that mixes profile applicability with delivery status;
- broad rows whose implemented sub-concern hides a missing sub-concern;
- calling a profile complete while any required row is partial or missing, or
  while an external contract has no named binding;
- conflating completeness with ASR-511/515 validation strength, GOV-920
  semantic profiles, backend profiles, instantiation profiles, realization
  support, participant feature support, or action admission;
- duplicating SDL fields inside task/run/study contracts or duplicating
  experiment fields inside `Scenario`;
- a second section/reference registry, schema registry, profile loader,
  validator stack, exception hierarchy, persistence store, logger, audit path,
  or CI workflow;
- deriving completeness from backend support, successful deployment, a
  private `_semantic_validated` flag, fixture size, tags, or free-form prose;
- treating authored evidence requirements as captured evidence, runtime state
  as authored intent, task as scenario, run as episode/workflow operation, or
  reward/verifier output as an SDL objective;
- treating timestamps as clocks, timeout as pacing, retries as controlled
  randomization, repeated operations as replications, or a seed field as proof
  of reproducibility; and
- putting secrets, hidden truth, raw argv, backend-native paths, or evidence
  bodies into examples or claim disclosures.

## Non-Goals And Implementation Boundaries

- Do not make stronger completeness profiles mandatory for ordinary SDL parse
  or semantic validation.
- Do not change the SDL grammar, source profile, schemas, models, validators,
  compiler, planner, runtime, backend behavior, or experiment contracts merely
  to publish REV1.
- Do not implement missing roadmap concerns, replay execution, range
  provisioning, reset, scoring/reward engines, verifier execution, or a full
  time/clock model in this issue.
- Do not certify a backend, apparatus, experiment result, academic claim, or
  benchmark quality. REV1 states required surfaces and gaps; validation-basis
  disclosures and evidence support concrete claims.
- Do not create a profile-evaluation API, database, UI, registry service, or
  automatic migration system.
- Do not promise that an artifact is deployable or reproducible on every
  backend. Host/substrate requirements and unsupported guarantees remain
  explicit apparatus/capability/realization disclosures.
