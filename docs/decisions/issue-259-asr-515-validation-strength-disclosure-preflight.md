# Issue 259 ASR-515 Validation-Strength Disclosure Preflight

Date: 2026-07-24

Issue: #259. Requirement: ASR-515.

This note fixes the executable disclosure boundary before implementation. It
does not add a contract, schema, fixture, validator, carrier field, API,
persistence, or runtime behavior. ADR-072, the formal validation/admission
profile specification, and the joint #97 preflight remain normative for the
shared design; issue #258 already owns the static profile taxonomy.

## Decision Boundary

ASR-515 owns the use of an existing validation profile for one concrete
subject. The reusable unit is one closed validation-basis disclosure shape,
not a scenario/task/run/study replacement, generic validation-report graph,
or service. It records the exact validation-profile id and version, subject
kind and stable subject reference, achieved strength, gate-result rows,
safe producer/evidence/diagnostic/artifact references, and explicit
limitations. A public or audience-restricted view must expose its weaker basis
rather than borrowing strength from a non-public view.

The implementation must select the taxonomy with
`select_validation_profile(profile_id, profile_version, subject_kind)` from
`aces_contracts.validation_profiles`. Profile id/version, strength classes,
gate kinds, and limitation categories are foreign-key-like references to
`contracts/profiles/validation/validation-profile-catalog-v1.json`; they must
not be duplicated as carrier-specific enums, manifest tables, free strings,
or a second profile loader.

The disclosure validator is responsible for the profile-use join, not for
executing gates. It must fail closed on an unknown identity, an unsupported
subject kind, duplicate gate rows, an omitted required gate, an undeclared
portable gate or limitation term, or a claimed strength unsupported by the
represented outcomes. The actual parser, semantic validator, processor,
backend, conformance, evidence, and falsification owners remain the authority
for whether their gates ran and what they observed.

`minimum_strength` is the selected profile's requirement, not evidence that an
individual subject achieved it. A disclosure must apply the ADR-072/formal-spec
ordering to its actual rows: structural acceptance never implies semantic
validation; semantic validation never implies a behavioral path; and evidence-
or falsification-backed strength needs the specified evidence/protocol support.
Required weak, failed, partial, not-run, unknown, unsupported, or withheld
gates must be explicit and lower or qualify the claim. `not_applicable` must
not silently act as a pass; its use needs a profile-aware explanation and an
explicit limitation where it affects what the audience can infer.

"Expose" means publish the disclosure through its governed artifact carrier
and schema. It does not require a new HTTP endpoint, control-plane command,
database, event stream, or live admission decision.

## Canonical Carriers And Boundaries

- **Scenario and snapshot.** Build a claim from the existing safe SDL ingress
  and lifecycle: `parse_sdl()`/`parse_sdl_file()`, normalized closed `SDLModel`
  construction, `SemanticValidator`, `instantiate_scenario()`, and the
  `sdl-authoring-input-v1`, `instantiated-scenario-v1`, and
  `instantiated-scenario-snapshot-v1` contracts. Do not make
  `Scenario._semantic_validated`, raw YAML, source layout, or a parser success
  the portable record. A snapshot-bound disclosure must use its existing stable
  identity/version/digest semantics rather than an untyped pathname.
- **Experiment task.** Bind the disclosure to `ExperimentTaskModel` and its
  scenario reference, protocol, apparatus constraints, artifact refs, and
  `validity_notes`. Validity notes describe interpretation threats; they are
  neither validation profile selection nor per-gate outcomes.
- **Experiment run.** Bind it to `ExperimentRunModel`, preserving its task and
  snapshot refs, apparatus context, traceability, realized-form and
  augmentation disclosures, evidence artifacts, and result summaries.
  Reuse `validate_experiment_run_against_task()` and the existing evidence-ref
  resolution rules. A realization/augmentation disclosure, completed run, or
  result summary is not itself a validation-basis disclosure.
- **Experiment study.** Bind it to `ExperimentStudyModel` while preserving
  membership, allocation, analysis, behavioral-claim, validity-note, report,
  and export boundaries. Reuse
  `validate_experiment_study_against_tasks_and_runs()`; do not derive study
  strength from a tag, an analysis plan, or a member run without recording the
  study's own basis and limitations.
- **Evidence and diagnostics.** Use the existing typed reference and evidence
  surfaces (`ExperimentReferenceModel` variants,
  `ExperimentEvidenceRecordReferenceModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentRunTraceabilityModel`, `Diagnostic`, and `Severity`). A disclosure
  points to bounded refs, digests, and diagnostic codes; it must not embed raw
  evidence content, a backend-native object, or an exception rendering.
- **Admission and conformance.** Participant action admission remains
  `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`, and
  `RuntimeControlPlane.admit_participant_action()`. Do not put this disclosure
  in `admission_disposition`. Conformance continues to use
  `_validate_payload()`, `_semantic_diagnostics()`, `_fixture_case_diagnostics()`,
  `run_fixture_suite()`, and `run_target_conformance()`; a conformance result
  can support a behavioral gate but does not replace the profile-use validator.

The subject-reference boundary must reuse the existing typed experiment/SDL
reference family and enforce one explicit mapping from taxonomy subject kinds
(`scenario_snapshot`, `experiment_task`, and so on) to allowed reference
kinds. Do not introduce a second generic reference, make file paths identity,
or collapse profile subject kinds into transport `ref_kind` strings.

## Cross-Cutting Gates

1. **Contract and schema authority.** The reusable disclosure and gate rows
   must be `ContractModel` shapes (`extra="forbid"`), use the primitive aliases
   and model validators in `aces_contracts.contracts`, and expose cross-row
   rules through `x-aces-invariants`. Published schema changes follow
   `schema_bundle()`, `aces_contracts.versions`, generated-schema parity,
   `contracts/schemas/`, the matching schema-publication entry and manifest
   ledger, `check_generated_schemas.py`, `check_schema_publication.py`, and
   `check_json_artifacts.py`. The checked-in schema is authoritative; a Python
   model or generated output alone is insufficient.
2. **SDL parser and semantic gates.** A scenario disclosure that says
   `semantic` must be sourced from the existing parser/normalization and
   `SemanticValidator` path, including reference resolution, ambiguity,
   uniqueness, acyclicity, runtime-family checks, and instantiated revalidation
   where applicable. A contract parse or Pydantic model acceptance can support
   only its structural rows.
3. **Configuration and environment shapes.** This feature has no runtime
   environment binding, secret, executable, host, plugin, or profile-root
   setting. Do not add one. When a referenced artifact includes configuration
   facts, keep their existing redaction semantics (`ExperimentParameterModel`,
   `RuntimeEnvironmentVariable`, and `ImageEnvironmentDefault`) rather than
   copying values into the disclosure. No environment dump or discovered
   configuration is a validation basis.
4. **Authentication, authorization, and request limits.** This contract-only
   scope adds no HTTP/MCP/CLI surface, so it must not call or weaken the control
   plane. If a later API exposes disclosures, it must use
   `ControlPlaneSecurityConfig.strict_defaults()`, verified identity and role/
   target authorization, the request-size guard, idempotency key and request
   fingerprint, audit events, published request/response models, and the
   redacted internal-error handler. Selecting a profile never authorizes a
   gate to run or access to the referenced evidence.
5. **Errors, observability, and persistence.** Reuse Pydantic `ValidationError`
   / `ValueError` at construction and bounded `Diagnostic`/`Severity` for
   conformance projection. Do not add a validation-basis exception hierarchy.
   Validation failures may identify a contract path, profile/gate id, and safe
   reference, never rejected payload content. Durable disclosure facts belong
   with their scenario/experiment/evidence artifact; they must not exist only
   in `RuntimeSnapshot`, `ControlPlaneStore`, operation details, audit blobs,
   backend DTOs, telemetry, logs, tags, or prose.
6. **Secrets and OS/process exposure.** Records, fixtures, diagnostics, logs,
   examples, and schemas must contain only ids, refs, digests, bounded
   summaries, and redaction-safe limitation text. They must exclude credentials,
   bearer tokens, keys, hidden answers, prompts, raw traces/evidence, complete
   stack traces, environment dumps, process argv, and backend-native reprs. No
   subprocess, network fetch, dynamic import, or caller-selected filesystem
   root is needed. A future tool may put only bounded ids/versions and vetted
   paths on argv, never raw artifact bodies or secrets.
7. **Repository and release workflow.** Reuse `.ground-control.yaml`,
   `.gc/plan-rules.md`, `noxfile.py`, and `tools/verify_all.py`; set
   `ACES_REQUIREMENT_UID=ASR-515` because this branch name does not contain the
   requirement UID. Module-boundary, authority-boundary, semantic-coverage,
   repository-policy, requirement-governance, Sphinx, secret, and private-key
   checks remain in scope. Do not add logic under the compatibility-only
   `implementations/python/src/aces/` tree.

## Extensibility Seam

The stable seam is a versioned validation-basis disclosure joined to the
catalog by `(profile_id, profile_version, subject_kind)`. It carries repeatable
gate-result rows plus safe evidence/diagnostic/artifact refs, limitations, and
an optional publication/audience view. This lets a later profile, gate kind,
limitation category, claim subject, or redacted public view extend governed
data and shared validation without carrier-specific booleans, backend switch
statements, or a second registry.

Gate rows describe executed results; they must not contain Python callables,
module names, shell commands, remote URLs to execute, or backend dispatch
rules. Future portable terms extend the catalog under its versioning and
`x-<owner>:<term>` rules. They do not modify unrelated manifests, semantic
profiles, participant capabilities, runtime state, or profile loaders.

## Gotchas And Non-Goals

Avoid treating schema success, a private semantic flag, a successful run,
conformance fixture, FM classification, ADR-021 evidence status, realization
support, backend capability, semantic profile, instantiation profile, or
participant admission disposition as the disclosure itself. Avoid untyped
`validation_metadata`, `validation_report`, `admission_metadata`, generic
`profile`, or `claim_strength` fields; duplicate evidence/traceability stores;
and a separately maintained set of task/run/study validators or exceptions.

This issue does not redesign or execute SDL parsing, semantic validation,
instantiation, compilation, planning, backend conformance, participant action
admission, control-plane authorization, evidence capture, falsification, or
experiment analysis. It does not add an API, CLI, MCP tool, database, event
stream, audit stream, telemetry event, remote registry, plugin system, or
general claim graph. It also does not change the ASR-511 catalog except when a
separately governed taxonomy evolution is genuinely required.

When executable disclosure coverage lands, update the
`validation-admission-profiles` entry in
`specs/formal/assurance-fulfillment.yaml` from its current joint #258/#259
waiver to accurately distinguish delivered ASR-511 taxonomy coverage from
ASR-515 carrier and test coverage; do not claim that status in this preflight.
