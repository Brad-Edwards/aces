# Issue 784 SCE-003 Adaptive Difficulty Preflight

Date: 2026-07-30

Issue: #784.

Requirement: SCE-003.

This note fixes the architecture boundary for observable, bounded adaptive
difficulty over declared scenario variants. It is guidance only: it does not
add SDL syntax, contracts, schemas, policy algorithms, runtime behavior,
persistence, fixtures, tests, APIs, or an implementation plan.

ADR-084 remains authoritative. Adaptation is a governed consumer of an
immutable admitted baseline; it cannot become a second scenario-selection,
trial-realization, participant-control, or archival-run lifecycle.

## Existing Authorities And Current Gap

- ADR-084, `raes.variation`, `raes.experiment_selection`,
  `raes.selected_scenario`, `AdmittedTrialPlanModel`,
  `compile_admitted_trial_plan()`, and `realize_admitted_trial_entry()` already
  own bounded scenario-family variation, experiment selection, immutable trial
  intent, deterministic realization, and preallocated run identity. A live
  adaptive policy cannot call those concepts "runtime mutation" and alter the
  current run.
- `ExperimentSpecModel`, `ExperimentStudyFactorModel`,
  `ExperimentRunAllocationPlanModel`, `ExperimentRunModel`, and
  `ExperimentStudyModel` already own pre-run design, factors, compared
  conditions, allocation, archival execution provenance, validity notes, and
  analysis. Fixed, adaptive, and scaffolded conditions belong here rather than
  in SDL topology or backend configuration.
- SDL `WorkflowStep.execution_mode`, `WorkflowStep.scaffold_refs`,
  `ParticipantObservationBoundary`, and the semantic checks in
  `SemanticValidator._verify_workflows()` already own declared scaffolded work
  and the instruction, starter-file, scaffold-instruction, and subtask-guidance
  boundaries that may be exposed. SCE-003 must select only among such declared
  carriers; it must not invent guidance text or a second scaffold schema.
- ADR-066, `ExperimentCaptureSpecModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentDerivedMeasureModel`, `ExperimentAugmentationDisclosureModel`,
  and `ExperimentRunTraceabilityModel` already separate observation intent,
  raw evidence, derived measures, realized augmentation, and run provenance.
  A policy input is not evidence merely because it was logged.
- ADR-085/095, participant decision-surface v2, participant crossing,
  participant inject delivery, exposure policy, delivery, and observation
  records already own participant-facing disclosure at an exact state cut.
  Producing guidance is not authorization, delivery, acknowledgement, or proof
  that the participant used it.
- API-409 `ParticipantInterventionOccurrenceModel` means a mixed-control
  intervention against an existing participant action, control, or attempt. It
  is not a generic adaptive-difficulty event. An adaptive decision may
  reference an API-409 occurrence when those exact semantics apply, but it
  must not overload or duplicate that carrier.
- `ExperimentAugmentationDisclosureModel` is a run-level disclosure of
  processor/backend augmentation and comparability effects. It is not the
  policy decision, trigger record, delivery receipt, or operational event.
- `ControlPlaneStore`, `ControlPlaneOperationRecord`, request fingerprints,
  idempotency keys, compare-and-set participant history heads, and `AuditEvent`
  already own live operational durability and audit. Archival run/evidence
  contracts remain separate and must not be reconstructed from mutable
  snapshots or audit text.

The missing surface is a closed adaptive-policy declaration and an append-only
decision/intervention provenance record that compose those incumbents by
reference. The implementation must not add another variation domain, scenario
binder, workflow language, observation model, participant delivery model,
run/study record, repository, exception hierarchy, or policy engine.

## Architecture Decisions And Guardrails

### One declared policy, one exact decision, and separately evidenced effects

Use one versioned adaptive-policy family with an explicit experiment condition:

- `fixed`: no adaptive action is permitted;
- `adaptive`: a declared policy may choose a permitted action from current,
  evidence-bearing observations; or
- `scaffolded`: declared guidance is available under a fixed or explicitly
  declared trigger, without implying that the challenge itself was rescaled.

The condition is not inferred from whether an intervention happened. A fixed
condition that unexpectedly contains an intervention is invalid, not
silently reclassified. Benchmark profiles default to `fixed`; adaptation must
be explicitly declared in the experiment design and run provenance.

A policy declaration identifies:

- stable policy id, version, and immutable digest;
- exact baseline experiment, admitted plan/entry, run, task, and scenario
  family/snapshot references as applicable;
- named difficulty dimensions and named variants that reference existing
  variation points, admitted outcomes, factors, and declared scaffold/action
  carriers rather than copying them;
- exact observation-source roles and evidence requirements;
- decision cadence in a named logical-time, decision-epoch, event-order, or
  state-cut domain;
- a closed trigger/evaluator profile, either exact typed thresholds or a
  governed versioned policy reference;
- a finite allowlist of actions and affected semantic references;
- bounds such as maximum interventions, direction/range limits, cooldown or
  hysteresis, and terminal/unsupported disposition; and
- validity and comparability disclosures required when the policy acts.

Policy ids and profiles are governed identifiers, not import paths, commands,
callbacks, entry points, URLs, prompts, plugin names, or aliases such as
`latest`. Free-form policy `parameters`, expression trees, JSON Patch, and
backend-native option maps are not admitted extension mechanisms.

Difficulty ordering is policy-local and explicit. A variation point does not
become intrinsically "easy" or "hard", and faster completion is not a universal
competence measure. A named variant is a reference to a complete, admitted
selection or scaffold/action profile; it is not another scenario identity,
mutable preset, or partial patch.

### Policy inputs are exact-cut evidence, not ambient state

Each decision binds the exact current state cut and only the observation
records, evidence records, or derived measures admitted by the policy.
Observation ids, source roles, capture/evidence refs, timestamps/order
coordinates, sensitivity, redaction, and derivation profile must resolve.

Raw logs, mutable counters, wall-clock time, host load, backend-private state,
environment variables, final outcomes from the future, hidden answer material,
and unsealed evaluator details are not implicit policy inputs. If a policy is
authorized to use a hidden or assurance-only source, that source remains out of
the participant view and its output still passes the independent
authorization/declassification/disclosure gates. Using hidden truth as a
policy input never authorizes revealing it.

The policy decision record is append-only and carries policy identity/version/
digest, prior policy state, exact cut/cadence coordinate, input observation
refs, trigger result, selected action ref, affected semantic refs, disposition,
timing, evidence/provenance refs, and declared validity effect. The action
attempt, realization outcome, participant delivery, participant observation,
and measured downstream effect remain separate referenced occurrences.

A repeated request with the same policy, cut, observation set, and idempotency
identity must return the same decision or conflict. Stale, future,
cross-run/cross-episode, already-consumed, incomparable, or policy-mismatched
cuts fail before any side effect or history append.

### In-run actions are forward-only uses of admitted carriers

An in-run adaptive decision may only request an action already admitted for
that run, for example:

- disclose one declared scaffold reference through the existing observation
  boundary, exposure, crossing, delivery, and observation path;
- request a declared participant-directed inject or mixed-control operation,
  when that exact carrier and authority are already present; or
- request an existing compiled workflow/action transition that independently
  passes its normal predicate, action-admission, apparatus, and backend gates.

The adaptive policy does not execute the effect itself. It returns a typed
decision that the owning runtime service validates and dispatches through the
incumbent carrier. Unsupported carrier/backend capability produces an explicit
unsupported or denied record, not a private fallback.

No in-run action may:

- change an SDL variation-point selection or instantiation binding;
- add/remove/retarget topology, declarations, objectives, workflows, or
  participant identities;
- change task factors, condition assignment, trial coordinate, run id,
  apparatus selection, random-stream address, seed, or admitted timeout;
- rewrite, delete, reorder, or reinterpret past events, evidence, delivery, or
  observations; or
- bypass participant information-flow, action-admission, capability,
  realization-envelope, or backend validation.

### A harder follow-up variant is a new admitted trial

When the selected action changes scenario-family difficulty rather than using
an already admitted in-run carrier, the output is a proposal for a derived
follow-up trial. It re-enters the existing experiment selection,
`compile_admitted_trial_plan()`, `select_scenario_family()`, ordinary
instantiation/admission, processor planning, and one-entry realization path.

The follow-up receives a new trial coordinate, plan entry, and `run_id`. Its
run uses existing `trial_provenance` and `derived_from_refs` to link the source
run and adaptive decision. It does not reuse or supersede the source run
identity, mutate its snapshot, or continue its random streams by convention.
Admission failure remains a visible failed/unsupported decision outcome; the
policy cannot clamp, resample, repair, or select another backend silently.

### Validity and comparison are experiment concerns

Fixed, adaptive, and scaffolded conditions must be distinct factor levels and
condition assignments in experiment/study allocation. Every archival adaptive
run reconciles its declared policy condition with the actual decision records,
augmentation disclosures, evidence, and derived follow-up links.

Comparisons involving adaptive runs require an analysis plan and validity note
that state the estimand and treatment received. A fixed-versus-adaptive
comparison may estimate a policy effect; it must not present participants as
having faced the same fixed treatment. Per-run difficulty paths and guidance
exposure are post-allocation treatment facts, not baseline factors to rewrite.
Missing, denied, unsupported, or evidence-lost interventions remain explicit
and feed the existing missing-data/invalidation rules.

## Required Incumbents And Cross-Cutting Reuse

- **SDL and scenario-family authority:** `load_sdl_yaml`, bounded source and
  composition profiles, `Scenario`, `ExpandedScenario`,
  `InstantiatedScenario`, `SemanticValidator`, `raes.variation`,
  `validate_experiment_selection_against_family()`,
  `select_scenario_family()`, `instantiate_scenario()`,
  `admit_instantiated_scenario()`, `InstantiationProvenance`, and canonical
  instantiated-snapshot bytes/digests.
- **Trial identity and realization:** `ExperimentSpecModel`,
  `ExperimentSelectionPolicyModel`, `AdmittedTrialPlanModel`,
  `revalidate_admitted_trial_plan()`, `compile_admitted_trial_plan()`,
  `realize_admitted_trial_entry()`, `TrialRunProvenanceModel`,
  `validate_admitted_trial_run()`, and
  `validate_admitted_trial_study()`.
- **Scaffold and action authority:** `WorkflowStep.execution_mode`,
  `WorkflowStep.scaffold_refs`, `ParticipantObservationBoundary`,
  `ParticipantInformationBoundaryClass`, participant inject delivery,
  `ParticipantActionAdmissionRequest`, participant decision-surface v2,
  participant crossing, exposure, delivery, observation, and API-409 control
  occurrences where their narrower semantics apply.
- **Experiment evidence and validity:** `ExperimentCaptureSpecModel`,
  `ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentAugmentationDisclosureModel`, `ExperimentRunTraceabilityModel`,
  `ExperimentRunModel`, `ExperimentStudyModel`,
  `validate_experiment_run_against_task()`, and
  `validate_experiment_study_against_tasks_and_runs()`.
- **Validation and diagnostics:** `ContractModel(extra="forbid")`,
  `ValidationBasisDisclosureModel`, `Diagnostic`, `DiagnosticModel`,
  `CompilationFailure`, `sanitized_failure_message()`, `x-raes-invariants`,
  strict scalar types, canonical JSON/JCS digest helpers, and exact reference/
  digest equality. Do not add an adaptation exception hierarchy.
- **Persistence and audit:** `ControlPlaneStore`,
  `LocalControlPlaneStore`, `ControlPlaneOperationRecord`, append-only
  `AuditEvent`, request fingerprints, idempotency keys, expected history heads,
  and existing atomic artifact writes. Operational recovery and archival
  experiment provenance remain separate.
- **Schema publication and conformance:** ADR-009/019/061,
  `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json`,
  `contracts/schema-publication/entries/`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`, and the
  existing conformance validator/fixture registries.
- **Repository workflow:** `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`,
  `tools/check_authority_boundary.py`, `tools/check_semantic_coverage.py`,
  `tools/check_specification_coverage.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers The Intended Design Must Pass

1. **Authoring parser and config-shape gate.** Adaptive declarations enter
   through the bounded, duplicate-key/alias-rejecting experiment loader and
   closed contract models. Reject unknown fields, coercive scalar forms,
   non-finite numbers, unbounded rule/action graphs, ambiguous policy versions,
   and undeclared refs before contextual validation.
2. **Schema and publication gate.** Any portable policy or intervention
   contract is published from its owning `raes_contracts` model with exact
   generated parity, positive/negative fixtures, conformance registration,
   semantic annotations, compatibility classification, and a
   `schema-publication-manifest.json` change-ledger entry. The published schema
   remains normative; do not hand-edit only Python or generated JSON.
3. **Experiment and trial gate.** Policy condition, factor/level/condition,
   baseline plan/entry/run, named variant, variation point/outcome, action,
   task, apparatus, and profile refs resolve exactly against concrete,
   digest-matched artifacts. Fixed conditions reject intervention authority.
4. **Policy-input and exact-cut gate.** Reconstruct inputs from trusted
   evidence/participant carriers, resolve the named order domain and current
   state cut, enforce cadence/bounds/hysteresis, and reject stale, future,
   duplicate, cross-scope, unsupported, or loss-hidden inputs before selecting
   an action.
5. **Participant information-flow gate.** Participant-facing guidance passes
   observation-boundary projection, current exposure policy and markings,
   crossing authorization, transformation/declassification as applicable,
   delivery, and observation. Operator/auditor visibility, policy access, or
   evidence retention is not participant disclosure.
6. **Runtime, apparatus, and backend gate.** Revalidate the chosen action
   against the compiled run, current lifecycle/history heads, action/control
   authority, capability declaration, realization envelope, backend
   `validate()` result, and effect-specific admission. A policy decision alone
   grants none of those authorities.
7. **Authentication and authorization gate.** Any remote surface reuses
   `ControlPlaneSecurityConfig.strict_defaults()`, bearer or verified-proxy
   identity, target binding, read/mutating role separation, participant/
   controller or audience scope where relevant, request-size guards,
   idempotency/fingerprint conflicts, and append-only audit. Policy execution,
   evidence reads, participant disclosure, follow-up admission, and artifact
   dereference are separate deny-first permissions.
8. **Secret, environment, and configuration gate.** Policies, observations,
   decisions, variants, digests, fixtures, and provenance contain no
   credentials or resolved secrets. Use the existing typed
   literal/secret-reference and protected-sink patterns only if a declared
   action genuinely needs a secret. Thresholds, cadence, bounds, policy
   version, and baseline identity come from sealed artifacts, never ambient
   environment, process-global state, mutable backend defaults, or an
   unvalidated config file.
9. **OS/process exposure gate.** The reference resolver should remain
   in-process over typed DTOs. A future external policy adapter requires a
   separately governed boundary using fixed argv, no shell, bounded stdin or
   private files, controlled working directory, timeout, output bounds, and
   redaction. Tokens, policy bodies, observations, hints, plans, secret refs,
   hidden truth, and parameter maps never enter argv, process titles,
   filenames, environment captures, stdout/stderr, or logs.
10. **Error-envelope and logging gate.** Expected failures use bounded,
    canonically ordered `Diagnostic`/`DiagnosticModel` records with safe codes,
    domains, JSON-pointer addresses, and fixed messages. Do not render raw
    Pydantic input, observations, thresholds, hints, policy bodies, hidden
    refs, secret locators, paths, backend output, exception text, or
    tracebacks. HTTP retains the redacted
    `{"detail":"internal server error"}` fallback; 4xx details are bounded and
    value-free. Logs/audit carry safe ids, digests, versions, cuts, counts,
    dispositions, and durations only.
11. **Persistence and archival gate.** Persist in-flight decision identity,
    current policy state, idempotency, and history heads through the existing
    operational store and atomic transition pattern. Archive observation,
    intervention, delivery/effect evidence, run disclosure, and follow-up
    lineage through the experiment/evidence artifacts. Do not use
    `RuntimeSnapshot.metadata`, operation `details`, tags, logs, or audit blobs
    as the only provenance authority.
12. **Run/study reconciliation gate.** Revalidate each run against its task,
    admitted entry, declared adaptation condition/policy, decision records,
    participant crossings/deliveries, augmentation disclosures, evidence,
    results, and derived follow-ups. Revalidate study allocation and analysis
    so adaptive treatment cannot be compared as if it were fixed.

## Extensibility Seam

The seam is a pure, versioned policy-resolution operation over explicit
parameters:

```text
(policy identity/version/digest,
 baseline refs, condition, named policy state,
 exact state cut, admitted observation refs,
 cadence and bounds)
    -> one typed decision or bounded diagnostics
```

The decision names one predeclared action and carries no side effect. Separate
runtime adapters realize the action through existing scaffold, crossing,
control, workflow, or follow-up-trial authorities and append separately typed
outcome evidence.

The next reasonable change—a new threshold profile, observation source,
difficulty dimension, scaffold carrier, policy-state transition, or
follow-up-selection strategy—extends a closed union or governed profile and its
fixtures. It does not require editing SDL variation semantics, participant
delivery, run identity, persistence, or every runtime route. A new action
authority, policy execution mechanism, or mutation plane requires a new
architecture decision rather than a free-form parameter.

## Verification Guardrails

Coverage must include:

- positive fixed, adaptive guidance, and newly admitted harder-follow-up cases;
- exact-threshold, cadence, cooldown/hysteresis, intervention-count, and
  terminal boundaries;
- unsupported policy profile, observation source, action carrier, backend
  capability, and follow-up admission;
- violations for undeclared actions, policy/version/digest mismatch,
  cross-run/cross-episode observations, stale/future cuts, hidden-information
  leakage, retroactive events, topology/factor/identity/stream mutation, and
  fixed-condition intervention;
- idempotent replay, conflicting replay, concurrent current-head updates, and
  append-only recovery;
- schema/model/conformance parity and cross-artifact run/study reconciliation;
- participant projection/delivery/observation separation and comparability
  disclosure; and
- redaction assertions over diagnostics, HTTP envelopes, logs, audit,
  persistence, fixtures, and subprocess boundaries.

Deterministic policy fixtures prove only the declared bounded resolver profile.
They do not prove user competence, policy optimality, pedagogical benefit,
backend equivalence, universal noninterference, or scientific validity.

## Gotchas And Anti-Patterns

Avoid:

- treating completion speed, score, retry count, or objective success as a
  universal difficulty or competence scale;
- calling an arbitrary scenario difference a difficulty dimension without a
  declared policy-local ordering and validity rationale;
- changing live variation selections, variables, topology, workflow structure,
  factors, identity, or random streams in place;
- using JSON Patch, templates, callbacks, scripts, prompts, backend defaults,
  environment variables, or mutable maps as policy/action authority;
- generating guidance dynamically outside declared scaffold/information-flow
  carriers, or treating policy output as delivery/observation;
- reusing API-409 participant intervention or augmentation disclosure as a
  generic adaptive event when their narrower semantics do not apply;
- treating audit/log entries as evidence, evidence as a participant view,
  delivery as observation, or a derived measure as raw observation;
- letting an unsupported action silently fall back, clamp, resample, select
  another variant/backend, or mutate the baseline;
- reusing the source `run_id` for a follow-up, or treating a retry as a new
  adaptive trial;
- comparing adaptive and fixed runs without explicit factor/allocation,
  treatment-path, missing-data, and validity handling;
- storing raw observations, hints, hidden truth, policy bodies, rejected
  values, secrets, backend objects, environment dumps, argv, stdout/stderr, or
  tracebacks in portable records or secondary surfaces; and
- adding a duplicate schema registry, loader, validator stack, exception
  hierarchy, policy controller, scenario binder, workflow engine, event store,
  repository, audit channel, logger, conformance runner, or CI workflow.

## Non-Goals And Implementation Boundaries

- This preflight does not implement SCE-003 or select a universal adaptation
  algorithm.
- It does not define one universal difficulty or competence scale, or equate
  fast completion with expertise.
- It does not add a private runtime controller, policy scripting language,
  optimizer, model provider, prompt protocol, recommendation service, or
  external policy plugin system.
- It does not add SDL topology/variation kinds, arbitrary runtime mutation,
  hidden-truth publication, participant transport, UI, API, scheduler, worker,
  backend selector, secret resolver, persistence repository, or analysis
  engine.
- It does not change historical run, event, evidence, participant knowledge,
  trial identity, factor allocation, random streams, or archival provenance.
- It does not claim that an intervention was effective merely because it was
  selected, attempted, delivered, or observed.
