# Issue 668 Envelope Relation Preflight

Date: 2026-07-05

Issue: #668.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture guardrails for implementing the realization
envelope membership, subsumption, and witness relation. It is guidance only: it
does not implement the relation, publish schemas, change manifests, alter
conformance behavior, or replace the #663 bridge.

## Binding Sources

- ADR-070 and `specs/formal/realization/envelope-semantics.md` own the
  realization-envelope language, admitted fragment, set-relation semantics,
  witness rules, and negative-conformance requirement.
- `docs/decisions/issue-667-realization-envelope-preflight.md` owns the
  design boundary for envelope semantics. Issue #668 consumes that semantics;
  it must not widen the language while implementing the relation.
- `specs/sdl/variables-and-instantiation.md` owns typed variables,
  placeholder syntax, fail-closed instantiation, and post-instantiation
  semantic revalidation.
- `specs/sdl/diagnostics.md` owns the fail-closed SDL diagnostic stages and
  collect-all validation behavior.
- `specs/formal/realization/explicitness-and-realization.md` and
  `aces_processor.semantics.realization` own SEM-218 exact/constrained/open
  runtime realization gates. The envelope relation composes with those gates;
  it does not replace or redefine them.
- `docs/explain/reference/backend-conformance.md` and
  `docs/decisions/issue-663-target-conformance-provisioning-scope-preflight.md`
  own target-conformance guardrails and the temporary `reference_scenario`
  bridge the witness relation is meant to retire later.
- ADR-009, ADR-019, ADR-061, `specs/authority/authority-boundary.yaml`, and
  `contracts/schema-publication-manifest.json` own contract authority and schema
  publication discipline.

## Architecture Decisions

- Implement one deterministic semantic relation over the #667 envelope
  expression: concrete membership, envelope subsumption, and witness generation
  must share domain comparison and closure logic. Do not create separate
  author-side, backend-side, and conformance-side interpretations.
- A concrete scenario is in an envelope only after ordinary SDL structural
  validation, semantic validation, instantiation, and no-unresolved-variable
  checks pass. Invalid SDL is never a member.
- Subsumption is set inclusion in the admitted fragment. It must reduce to
  bounded domain subset checks, product/record checks, governed-reference
  subset checks, and scoped closure compatibility. No silent approximation,
  sampling, probabilistic answer, backend callback, or solver-only answer is
  acceptable.
- Witness generation is a deterministic selector plus ordinary SDL validation.
  A witness proves one executable in-envelope instance; it is not proof of
  subsumption, backend honesty, or closed-world refusal.
- Negative probes for closed envelopes must use the same relation evidence and
  must expect refusal through `OperationStatus` / `Diagnostic` without runtime
  mutation. Backend-native exceptions or no-op successes are not portable
  refusal evidence.
- Relation diagnostics must be stable and public-safe: name relation kind,
  envelope id/ref, SDL path/address, domain kind, governed refs, and contract or
  digest ids when needed. Do not echo raw concrete values that may be sensitive.
- Keep current coarse manifest fields in their lane. `realization_support`,
  `ProvisionerCapabilities`, backend profiles, semantic profiles, validation
  profiles, and experiment study membership are not substitutes for envelope
  membership/subsumption.
- If implementation discovers the current unpublished envelope shape is
  insufficient, update the formal spec or ADR path first. Do not smuggle new
  semantics through prose `constraints` strings or conformance-only DTOs.

## Required Incumbents

Reuse these before adding anything new:

- Envelope authority:
  `docs/decisions/adrs/adr-070-realization-envelope-semantics.md`,
  `specs/formal/realization/envelope-semantics.md`, and
  `docs/research/realization-envelope/`.
- SDL parsing, variables, and validation: `parse_sdl()`, `parse_sdl_file()`,
  `SDLModel(extra="forbid")`, `VARIABLE_TOKEN_RE`, `Variable`,
  `VariableType`, `instantiate_scenario()`, `SDLParseError`,
  `SDLValidationError`, `SDLInstantiationError`, and `SemanticValidator`.
- Existing realization semantics:
  `aces_sdl.explicitness`, `CompiledRealizationRequirement`,
  `realization_support_diagnostics()`, `realization_disclosure()`,
  `RuntimeSnapshot.realization_provenance`, and the SEM-218 formal spec.
- Contract and authority surfaces: `ContractModel`, `schema_bundle()`,
  published `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/profiles/`, `contracts/concept-authority/`,
  `validate_controlled_vocabulary_scope_values()`, reference-model validators,
  concept bindings, and schema-publication checks.
- Backend manifest path: `BackendManifest`,
  `RealizationSupportDeclaration`, `ProvisionerCapabilities`,
  `BackendManifestV2Model`, `backend_manifest_payload()`,
  `validate_backend_supported_contract_versions()`, and capability-gap helpers.
- Processor/runtime/conformance path: `run_reference_processor()`,
  `compile_scenario_runtime_model()`, `plan()`, `RuntimeTarget`,
  `RuntimeControlPlane`, `_call_backend_apply()`, `_snapshot_contract_diagnostics()`,
  `run_target_conformance()`, `ConformanceCaseResult`, `OperationReceipt`,
  `OperationStatus`, `Diagnostic`, and `Severity`.
- Repository workflow: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config ingress: relation inputs that represent SDL must enter through
  parsed `Scenario` / `InstantiatedScenario` models or a contract model, not
  free-form dicts. Unknown fields, variable placeholders in keys, unresolved
  variables, reference ambiguity, and semantic validation failures remain fatal.
- Domain validation: envelope domains must use the typed variable substrate and
  governed reference surfaces. Numeric intervals need declared numeric type and
  bounded endpoints; enum and governed-reference domains must be finite; record
  domains must reject unknown extras when closed.
- Contract shape: any public envelope payload or manifest carrier must be a
  closed `ContractModel` with `schema_bundle()` parity, valid/invalid fixtures,
  `contracts/schema-publication-manifest.json` ledger entries, and
  `x-aces-invariants` for semantic rules JSON Schema cannot express.
- Manifest authority: backend carriage must render through
  `backend_manifest_payload()` and validate as a backend manifest. Support
  declarations, concept bindings, supported contract versions, capability
  vocabularies, and governed extension terms must keep using existing
  validators.
- Planning admission: a failed relation check is admission evidence, not a
  backend deployment attempt. It should surface as stable `Diagnostic` values
  and must not bypass planner diagnostics, capability-gap checks, or SEM-218
  realization-support gates.
- Runtime/control-plane: generated witnesses and negative probes must execute
  only through `RuntimeControlPlane` and target components that already pass
  `RuntimeTarget` shape validation. `_call_backend_apply()` must remain the
  fail-closed backend result boundary.
- Error envelope: public diagnostics and reports may contain ids, refs, paths,
  domain kinds, relation kinds, and bounded summaries. They must not contain
  credentials, bearer tokens, private keys, raw backend objects, host paths,
  process argv, stdout/stderr, hidden truth, scoring state, full tracebacks, or
  environment dumps.
- OS and secret exposure: witness generation must not require reading
  `~/.secrets`, local daemon inventory, privileged host state, or secrets in
  command-line arguments. Default verification must stay hermetic.
- Persistence/evidence: conformance remains report-oriented. If durable
  artifacts are later needed, persist envelope refs, digests, relation result
  summaries, witnesses, and refusal evidence through existing run-artifact or
  experiment evidence surfaces, not a new relation database or cache.

## Extensibility Seam

The seam is a pure relation over a versioned envelope expression plus a
validated SDL instance. Keep it parameterized by:

- relation kind: membership, subsumption, witness, or negative probe;
- scope/path: field, node, topology, app, or scenario;
- domain kind: exact, enum, boolean, numeric interval, governed reference, or
  record;
- closure/posture: scoped open-world or closed-world overlays and exact,
  constrained, or open posture;
- governed authority: vocabulary, reference-model, scenario registry, contract
  id, digest, or concept-family ref; and
- witness policy/seed: deterministic selection without a global hard-coded
  scenario.

Future domain kinds or carriers should land by extending the formal envelope
spec, contract model/schema, fixtures, relation helper, and tests together.
They should not require per-backend relation code, duplicate manifest
renderers, or conformance-profile branches.

## Gotchas And Anti-Patterns

Avoid:

- equating `instance in envelope` with experiment-study membership,
  validation/admission profile membership, backend-profile selection, or
  semantic-profile applicability;
- treating `subsumes(offered, requested)` as a planner capability shortcut that
  can skip manifest, capability, SEM-218, or snapshot validation;
- treating `realization_support.support_mode` as value-level envelope posture;
- letting authored variables survive into concrete membership checks;
- deriving witness values from Python dict iteration, current time, host state,
  random choices without an explicit seed policy, or backend discovery;
- implementing relation failures as new exception hierarchies, raw Pydantic
  prose, booleans with lost diagnostics, or backend-native errors;
- adding arbitrary predicates, unbounded regex, recursion, non-linear
  arithmetic, quantification over unbounded collections, external queries, or
  backend callbacks to portable envelopes;
- duplicating schema registries, fixture loaders, vocabulary tables, manifest
  renderers, conformance reports, persistence stores, or validation passes;
- using `constraints` prose as the machine-checkable carrier for membership,
  subsumption, closure, or witness policy; and
- leaking sensitive concrete values through diagnostics, witnesses, negative
  probes, fixtures, docs, audit details, or report payloads.

## Non-Goals

- Implementing issue #668 in this preflight.
- Publishing a new envelope schema or backend-manifest version.
- Replacing `run_target_conformance(reference_scenario=...)` in this note.
- Redesigning SDL variables, SEM-218 explicitness, backend profiles,
  validation/admission profiles, experiment run-set semantics, runtime
  snapshots, control-plane security, or conformance reporting.
- Adding a solver dependency, HTTP API, persistence service, backend adapter,
  controlled vocabulary, or new SDL dialect.
