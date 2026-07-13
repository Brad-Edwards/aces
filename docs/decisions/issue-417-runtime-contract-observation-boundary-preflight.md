# Issue 417 Runtime Contract / Observation Boundary Preflight

Date: 2026-07-13

Issue: #417.

This note fixes the architecture boundary for the upcoming implementation. It
is guidance only: it does not change SDL syntax, models, schemas, fixtures,
compiler behavior, evidence contracts, or inventory tooling.

## Binding Sources

- `specs/sdl/document-model.md` makes normalized and instantiated SDL authored
  scenario contracts. `Node.runtime` is inside those closed authoring forms.
- ADR-004 and ADR-036 define the SDL -> processor -> runtime -> backend package
  and lifecycle direction. The compiler turns the complete node into desired
  provisioning payloads; it is not an inventory importer.
- SEM-218 (`specs/formal/realization/explicitness-and-realization.md`) and
  `aces_sdl.explicitness` distinguish exact, constrained, and open authoring
  concerns and author/processor/backend realization origin. They do not
  classify capture evidence or observation strength.
- ADR-064 and ADR-066 separate capture intent, raw captured evidence, derived
  measures, operational observability, and scenario-native observability.
- ADR-065's `ExperimentRealizedFormDisclosureModel` is the archival carrier for
  a backend/processor/operator choice made while realizing an underspecified
  run concern. It is not a generic runtime inventory.
- `docs/aces/inventory/asset-inventory-methodology.md` owns the capture bundle,
  `mapping-ledger.yaml`, `capture-limits.txt`, evidence checksum, and
  correspondence-check workflow. Its maximal-capture inclusion rule does not
  decide which captured facts become SDL requirements.
- ADR-056 and ADR-057 own observed-value redaction and secret-name handling.
  The issue #516 inventory guidance separately permits authoritative source
  bundles to retain participant-discoverable scenario-target secrets while
  withholding operator/out-of-scenario material.
- ADR-009, ADR-061, `contracts/README.md`, and
  `contracts/schema-publication-manifest.json` own schema authority and
  evolution. Published schemas are hand-governed authority; generated-schema
  tooling proves Python parity and does not replace that review direction.

## Architectural Diagnosis

The current carrier semantics and some model/documentation wording disagree.

1. `Node.runtime` is accepted by `SDLModel`, included in the published
   authoring and instantiated schemas, canonicalized as scenario meaning, and
   serialized by `aces_processor.compiler._compile_node_runtimes()` into the
   desired `NodeRuntime.spec`. Planning then compares that payload with a live
   `RuntimeSnapshot`. A value authored there is therefore a scenario
   requirement, regardless of whether its Python class or docstring says
   "observed".
2. `runtime.health` currently carries health status and check logs;
   `runtime.network` carries backend IDs and generated endpoint identity; and
   `runtime.package_vulnerabilities` carries scanner, database, and scan-time
   state. Those are capture results, yet the authoring carrier promotes them
   into desired state.
3. `model_dump()` includes model defaults in compiled node payloads, while
   `aces_sdl.explicitness` visits only `model_fields_set`. A serialized value is
   therefore not proof that the author wrote it. A global `exclude_unset=True`
   change would also be wrong because some defaults are normative SDL defaults.
4. SEM-218 currently classifies authored `unknown` and `other` enum sentinels
   as open realization. That is useful for an authored open contract, but it
   makes `runtime.health.status: unknown` especially misleading: it is neither
   an observed unknown result nor evidence that a health check ran.
5. The inventory methodology correctly requires maximal capture, but its
   current "attempt maximal ACES specification" wording can be read as an
   instruction to copy every schema-compatible observation into SDL. Schema
   compatibility is not semantic authority to promote evidence into a
   requirement.

The implementation must correct this at the carrier boundary. A compiler
denylist, backend filter, prose-only convention, or inventory-tool heuristic
would leave canonical SDL meaning and validation inconsistent.

## Architecture Decisions And Guardrails

### `Node.runtime` is declarative contract state

Every field reachable from authored `Node.runtime` states one of these:

- exact state the scenario requires;
- a typed constraint on acceptable state; or
- an explicitly open realization point admitted by SEM-218.

It is not a place to preserve what one capture happened to observe. Presence in
authored SDL is the deliberate promotion decision; do not add a second generic
`origin`, `phase`, `observed`, or `is_requirement` flag to every runtime model.
Observation provenance is determined by its evidence carrier, not by a tag on
an SDL field.

The six issue #160 categories remain distinct:

| Category | Authority and meaning | Correct carrier |
| --- | --- | --- |
| authored | Explicit scenario declaration | SDL source/normalized/instantiated forms and `model_fields_set` |
| defaulted | SDL semantic default applied without explicit author text | phase contract plus explicitness/default provenance; never inferred from a dumped value |
| planned | Processor desired operation after compilation/reconciliation | `RuntimeModel`, typed plans, `PlannedResource` |
| realized | Value/structure selected by a backend, processor, or operator at an admitted open/constrained point | live `realization_provenance`; archival `ExperimentRealizedFormDisclosureModel`, with evidence refs when asserted |
| observed | Concrete fact read during one realization/capture | source evidence bundle, `mapping-ledger.yaml`, and `ExperimentEvidenceRecordModel` when published portably |
| derived | Interpretation computed from evidence | `ExperimentDerivedMeasureModel`, result/analysis/report carriers with source-evidence refs |

Do not overload `ExplicitnessProvenance.BACKEND_REALIZED` as observation
strength: it says who selected a value, not whether Docker, a guest probe, or a
scanner independently observed it.

### Container health reuses conditions and evidence contracts

- A healthcheck definition is already a `Condition` (`command`, `interval`,
  `timeout`, `retries`, `start_period`) bound through `Node.conditions`.
- Required healthy truth belongs in the existing
  proposition/assertion/objective/evidence-requirement path when it affects
  readiness or success.
- Check status, failing streak, timestamps, exit code, and output are observed
  evidence. They must not remain an authored `runtime.health` observation bag.
- `unknown` means an authored open taxonomy point only where the owning
  contract admits one. Capture absence or indeterminate health belongs in
  evidence loss/limitations or `capture-limits.txt`, not `status: unknown` in
  SDL.

The regression example must show a condition bound to a container node and a
separate observed health result/evidence record. It must not encode the result
as desired runtime state.

### Network contract and endpoint evidence stay separate

- `infrastructure`, node links, and `Node.services` remain topology and service
  authority.
- Runtime network values such as a specifically required hostname, alias,
  static address, gateway, MAC, publication binding, or backend detail may
  remain in SDL only when the author intentionally requires that exact or
  constrained state.
- Docker/runtime network IDs, endpoint IDs, generated DNS names, generated
  container identities, and observed driver/IPAM output belong in the capture
  bundle and mapping ledger by default. A value is promoted to SDL only when
  the scenario deliberately makes it contract state; its presence then carries
  ordinary exact/constrained/open semantics.
- Stable ACES declaration IDs and backend-native/generated IDs remain different
  concepts. Generated IDs must not become declaration keys, reference targets,
  canonical addresses, or participant identity.
- A backend choice that materially realizes an open/constrained authored
  concern may also receive a realized-form disclosure. Mere observation of an
  incidental Docker ID does not justify one.

Do not create a second network topology, Docker-specific SDL dialect, raw
inspect DTO, or backend-ID registry.

### Software inventory and scanner state use different carriers

- `runtime.packages`, `runtime.software_components`, and
  `runtime.dependency_manifests` may describe required final scenario state at
  the selected granularity. An exact captured package row becomes SDL only
  through a deliberate requirement decision.
- Scanner identity/version/database, scan time, raw findings, and advisory
  snapshot state are capture/analysis facts. The current
  `RuntimePackageVulnerabilityFinding` shape is therefore not valid authored
  runtime contract state.
- Raw SBOM, package-list, manifest, and scanner output belongs in the evidence
  bundle or an `ExperimentEvidenceRecordModel` artifact reference/URI plus
  checksum. Vulnerability interpretation and severity summaries belong in
  derived measures or analysis.
- Top-level authored `vulnerabilities` remains the scenario weakness
  declaration surface. A scanner finding is not automatically that authored
  declaration.
- Audit mixed provenance enums such as
  `RuntimeSoftwareComponentProvenance`: artifact/source origin may be contract
  state, while scanner or process-inspection method is evidence provenance.
  Do not preserve the mixture merely for compatibility and do not add a second
  universal provenance model.

### Defaults and compilation must preserve meaning

- Use existing `model_fields_set`, `ExplicitnessRecord`, instantiation
  provenance, and typed compiler/plan contracts. Do not infer authored intent
  from `model_dump()` output.
- Distinguish a normative SDL default from an empty/sentinel serialization
  default. Only the former may become desired state, and its provenance must
  remain defaulted/processor-derived rather than author-declared.
- Do not globally switch node serialization to `exclude_unset=True`; that would
  silently remove normative defaults across unrelated SDL surfaces.
- Observation-only fields should be unreachable from the authoring schema.
  Do not maintain a matching compiler denylist or backend scrubber as duplicate
  validation.
- The compiler and planner must continue consuming one closed, validated
  instantiated scenario. Inventory evidence must never enter compilation as a
  hidden side channel.

### Existing evidence and provenance carriers are sufficient

- `mapping-ledger.yaml` owns fact-level evidence paths, discovery vantage,
  mapping disposition, caveats, and correspondence checks for inventory
  capture. `capture-limits.txt` owns skipped/withheld/indeterminate capture.
- `ExperimentCaptureSpecModel` says what should be captured;
  `ExperimentEvidenceRecordModel` says what was captured; and
  `ExperimentDerivedMeasureModel` says what was inferred. Preserve this split.
- `ExperimentRealizedFormDisclosureModel` records realization choices, not a
  full exact inventory. Its bounded summary cannot replace raw evidence.
- `RuntimeSnapshot` is live reconciliation/control state. Do not use
  `RuntimeSnapshot.metadata`, `SnapshotEntry.payload`, `OperationStatus`
  details, audit blobs, or logs as an archival capture ledger.
- No new evidence root, runtime-observation SDL tree, provenance graph,
  exception hierarchy, persistence store, or inventory workflow is justified.

## Required Incumbents

- SDL ingress and phase validation: `parse_sdl()` / `parse_sdl_file()`,
  `SDLModel`, `Scenario`, `InstantiatedScenario`, `instantiate_scenario()`,
  `SemanticValidator`, `SDLParseError`, `SDLValidationError`, and
  `SDLInstantiationError`.
- Author/default/realization semantics: `model_fields_set`,
  `classify_scenario_explicitness()`, `ExplicitnessRecord`,
  `derive_instantiated_explicitness()`, `CompiledRealizationRequirement`, and
  `realization_disclosure()`.
- Compiler/planner/runtime contracts: `_compile_node_runtimes()`,
  `RuntimeModel`, `NodeRuntime`, `PlannedResource`, `ProvisioningPlan`,
  `RuntimeSnapshot`, `SnapshotEntry`, `RealizationProvenanceEntry`,
  `ApplyResult`, and `OperationStatus`.
- Health truth/evaluation: `Condition`, node condition bindings,
  `Proposition`, `Assertion`, `EvidenceRequirement`, condition compilation, and
  proposition-truth result contracts.
- Evidence and provenance: `ExperimentCaptureSpecModel`,
  `ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentRealizedFormDisclosureModel`, run traceability, and the inventory
  methodology's ledger/capture-limit/correspondence contracts.
- Observability classification: `ObservabilityEvidencePlane`,
  `PLANE_BY_CONTRACT_ID`, `PLANE_BY_SDL_SECTION`,
  `classify_contract_plane()`, and `assert_single_primary_plane()`.
- Schema authority: the published SDL and experiment schemas,
  `ContractModel`, `schema_bundle()`, the SDL YAML and contract fixture corpora,
  `contracts/schema-publication-manifest.json`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`, and
  `tools/check_sdl_catalog_parity.py`.
- Diagnostics and API safety, if a portable carrier crosses HTTP:
  `Diagnostic`, `Severity`, `RuntimeSnapshotEnvelopeModel`,
  `OperationReceiptModel`, `OperationStatusModel`,
  `ControlPlaneSecurityConfig.strict_defaults()`, request-size guards,
  idempotency fingerprints, audit events, and the redacted FastAPI 500
  envelope.

## Security And Whole-Path Gates

- **YAML/parser shape:** source still passes bounded safe YAML decoding,
  canonical-key handling, closed `SDLModel` construction, semantic validation,
  instantiation, and full revalidation. Unknown observation bags fail closed;
  no `source` shorthand or literal-key scope may be repurposed.
- **SDL/contract shape:** published SDL schemas, Python models, section/runtime
  catalogs, canonicalization, instantiated schemas, and compiler admission must
  agree. A docs-only distinction is insufficient while the schema accepts an
  observation-only authored field.
- **Evidence shape:** portable capture artifacts pass closed `ContractModel`
  validation, capture-spec/requirement binding, RFC 3339 checks, raw-content
  artifact/URI/checksum rules, sensitivity/redaction/loss disclosure, unique
  refs, run traceability, and observability-plane classification. The mapping
  ledger separately passes its canonical APTL validator until ACES owns an
  executable ledger schema.
- **Schema publication:** review the hand-governed schema change, keep Python
  `schema_bundle()` in parity, add positive and negative fixtures, update the
  publication manifest's hash/change ledger, and apply ADR-061 compatibility
  rules. Accepted ADR corrections require ADR-059 supersession or recorded
  amendment; never silently edit ADR-025/033/034/056.
- **Secret handling:** SDL, portable schemas, fixtures, diagnostics, logs,
  audit details, summaries, and error envelopes must not expose operator
  secrets, credentials, private keys, bearer tokens, raw environment dumps,
  scanner payloads, or backend inspect objects. Authoritative inventory source
  bundles may retain participant-discoverable scenario-target facts under the
  issue #516 boundary; sanitized/public derivatives must declare redaction and
  loss rather than replace the source bundle.
- **Authentication/authorization:** issue #417 needs no new route. If evidence
  or snapshot data later crosses HTTP, reuse fail-closed bearer/proxy identity,
  backend/operator/auditor role checks, target scoping, request-size limits,
  idempotency, request fingerprints, and audit. Artifact dereference is a
  separate authorized read from reading a summary/ref.
- **Config and environment binding:** add no environment variable, token,
  credential, or config binding. Scanner and Docker configuration are capture
  parameters/evidence metadata, not SDL config. Runtime values still pass their
  existing field validators and ADR-056/057 redaction helpers where applicable.
- **OS/process exposure:** capture tools must not put credentials, raw evidence,
  or sensitive host paths in process argv. Use bounded files/artifact refs,
  fixed argument vectors, no shell interpolation, controlled paths, checksums,
  and explicit capture limits. Generated network IDs are data, never command or
  path authority.
- **Error envelopes:** parsing uses structured SDL errors; planning/runtime uses
  addressed `Diagnostic` values; HTTP retains redacted internal errors.
  Diagnostics name safe SDL paths, categories, and refs, not raw health output,
  scanner JSON, Docker inspect payloads, secrets, or full tracebacks.
- **Persistence:** live state continues through `RuntimeSnapshot` and
  `ControlPlaneStore`; archival capture continues through evidence artifacts
  and run traceability. Do not duplicate either store or persist claim-bearing
  observations only in `metadata` or logs.
- **Policy/workflow:** preserve package boundaries, compatibility wrappers,
  concept authority, SDL lineage coverage, generated-schema parity, schema
  publication governance, ADR pinning, scientific-completeness checks, and the
  canonical nox verification graph.

## Extensibility Boundary

The seam is carrier plus capture granularity, not backend product name.

- SDL contract state remains parameterized through existing variables,
  explicitness classes, typed runtime fields, and canonical references.
- Evidence remains parameterized by requirement, source refs, capture window,
  media type, artifact/checksum, sensitivity/redaction, provenance refs, and
  ledger fact IDs.
- Realized-form disclosure remains parameterized by concern kind, realization
  basis/authority, realized ref or bounded summary, and evidence refs.

A future Podman/Kubernetes identifier, another health evaluator, a second SBOM
format, or another scanner should vary those existing parameters and evidence
media types. It must not require another SDL observation tree or a
Docker/Trivy-specific schema. A genuinely new portable runtime contract field
belongs on the smallest existing typed runtime family and remains a requirement
when authored.

## Regression And Conformance Guardrails

- Include a declarative container healthcheck/condition and separate observed
  health evidence. Reject or migrate authored health result/log state.
- Include a Docker network endpoint capture containing generated network and
  endpoint IDs, generated DNS identity, and MAC data in the evidence/ledger
  side, while SDL contains only deliberately required topology/runtime facts.
- Include scanner metadata and vulnerability output as evidence and any
  interpreted summary as derived analysis; ensure it is not accepted as
  authored runtime state.
- Assert author/default distinction: an omitted model field must not become an
  author-declared exact requirement merely because a compiled payload contains
  its default.
- Assert `unknown` does not mean "capture could not determine this" in SDL.
- Exercise raw source, normalized authoring schema, Pydantic model, semantic
  validator, instantiation, compiler/plan payload, generated-schema parity,
  valid/invalid contract fixtures, and relevant inventory ledger validation.
- Keep hermetic tests independent of Docker and scanners. Native capture tests,
  if any, remain opt-in; committed fixtures are bounded and secret-reviewed.

## Gotchas And Anti-Patterns

Avoid:

- treating every participant-discoverable fact as authored scenario intent;
- using `runtime.health.status: unknown` to mean no observation was available;
- copying Docker network/endpoint IDs, generated names, MACs, inspect maps, or
  scanner timestamps into SDL because the current model accepts them;
- using a capture specification, backend capability, plan, success receipt, or
  runtime snapshot payload as proof of observation;
- using realized-form disclosures as a generic exact inventory or putting
  observations in `RuntimeSnapshot.metadata`;
- a compiler/backend denylist that duplicates the authoring schema boundary;
- a global `exclude_unset` serialization change;
- overloading SEM-218 explicitness/origin with observation strength;
- adding generic metadata/provenance/observation bags, duplicate validators,
  exception trees, logging paths, persistence stores, schema registries,
  reference resolvers, or inventory workflows;
- hand-editing only generated schemas, or regenerating schemas without the
  hand-governed contract and publication-manifest review;
- silently rewriting accepted ADRs whose original decisions placed observed
  facts under authored `Node.runtime`;
- leaking raw health output, scanner reports, environment/process dumps,
  backend payloads, target/operator secrets, or stack traces through fixtures,
  diagnostics, logs, API responses, or public evidence summaries.

## Non-Goals

- Implementing issue #417 or selecting exact field removals/version migrations
  in this preflight.
- Building Docker/Compose/Podman/Kubernetes inspectors, health runners, SBOM or
  vulnerability scanners, capture scheduling, retention, artifact storage, or
  report generation.
- Creating a new observed-runtime SDL schema, evidence root, realization
  provenance graph, API, persistence system, exception hierarchy, logging
  stack, or workflow pipeline.
- Redesigning topology, services, propositions/assertions, experiment-core,
  participant visibility, control-plane security, or inventory redaction.
- Claiming a mapping ledger or evidence bundle proves an authored SDL contract
  has been realized; that remains correspondence/conformance work.
