# Issue 653 SCE-004 Goal-Oriented Tool-Flexible Steps Preflight

Date: 2026-07-21

Issue: #653. Requirement: SCE-004.

This note records repository-wide architecture guardrails for goal-oriented,
tool-flexible scenario steps. It is guidance only: it does not implement SDL
fields, schemas, compiler records, runtime behavior, APIs, fixtures, tests, or
an implementation plan.

## Decision Boundary

SCE-004 is an authored scenario semantics change, not a tool runner. It makes
step objectives portable by separating what must be achieved from how a
participant, operator, backend, or agent tries to achieve it.

No new ADR is needed for the first implementation if it composes the existing
authorities:

- ADR-002 and ADR-079 own objective, proposition, assertion, and truth
  semantics.
- ADR-003 and ADR-006 own workflow control semantics and workflow-visible step
  state.
- ADR-083 owns participant tool, decision-surface, and exposure semantics.
- ADR-055, ADR-064, ADR-074, and ADR-084 own experiment intent, evidence, run
  provenance, and trial boundaries.
- The #791 preflight and runtime fact binding contracts own typed late-bound
  runtime facts.

A new ADR is warranted only if implementation changes one of those authorities,
adds an external planner/scorer/service boundary, changes published schema
evolution rules, or makes a stronger behavioral/equivalence/security claim.

## Step Mode Semantics

The required execution modes are a step-level authored semantic coordinate:

- `scripted`: prescribed reproducible mechanics are part of the scenario for
  calibration, compatibility, or exact procedural tests.
- `objective`: the step states a goal, applicability conditions, constraints,
  and success criteria while leaving tool and procedure choice to the
  participant/operator/agent.
- `scaffolded`: objective mode plus governed participant-visible hints,
  allowed action families, or affordance constraints.

These modes must not overload `participant-decision-surface-modes`. That
vocabulary describes how a participant implementation makes or relays
decisions. If implementation reuses any term spelling, the owner/scope and
validation path must make the distinction explicit.

Workflow steps remain declarative control nodes over objectives, predicates,
retries, calls, joins, and terminal states. Do not add a root `steps` language,
a second action-step schema, or command fields to objective/scaffolded steps.
Any extension to `WorkflowStep` must preserve ADR-006's control semantics and
the existing workflow result contracts.

Objective success is established only through invariant/postcondition
assertions over typed propositions and evidence-bearing truth results. A
participant action result, command exit status, HTTP response, tool output,
participant self-report, workflow step outcome, reward, score, or backend
status may support evidence only through an explicit governed binding. None is
portable success by itself.

Scripted mode is a compatibility/calibration surface. It may prescribe
procedure mechanics, but those mechanics remain disclosed realization/probe or
action-attempt facts. They do not define backend-neutral proposition meaning
and must not become the default path for objective/scaffolded mode.

Scaffolded mode exposes guidance through the existing participant information
and decision-surface model: scaffold instructions, subtask guidance, visible
context, allowed action-contract families, affordance refs, eligibility state,
markings, redaction, evidence, provenance, and limitations. Scaffolding is not
hidden answer material, a private planner, or an unvalidated command template.

Runtime facts from #791 may supply late-bound action inputs or observations at
authorized sinks. They cannot rewrite SDL variables, choose variation points,
retarget workflows, alter objectives, select apparatus, change trial identity,
or backfill success without the assertion/evidence path.

## Canonical Incumbents To Reuse

| Concern | Required incumbent |
| --- | --- |
| SDL ingress and phases | `parse_sdl()`, `parse_sdl_file()`, safe `sdl-yaml/v1` loading, `SDLModel(extra="forbid")`, `ScenarioContent`, module composition, `instantiate_scenario()`, `admit_instantiated_scenario()`, unresolved-token rejection, and post-instantiation semantic validation. |
| Workflow semantics | `aces_sdl.orchestration.WorkflowStep`, `WorkflowPredicate`, `WorkflowStepStateRef`, `WorkflowStepType`, `SemanticValidator._verify_workflows()`, `workflow_step_semantic_contract()`, `WorkflowExecutionContract`, `WorkflowResultContract`, workflow result/history schemas, and workflow capability declarations. |
| Objective and truth semantics | `Objective`, `ObjectiveSuccess`, `ObjectiveWindow`, `Proposition`, `Assertion`, `analyze_objective_window()`, `analyze_objective_semantics()`, proposition truth contracts, `proposition-truth-result-v1`, and #657 assertion/evidence work. |
| Participant affordances and actions | `ParticipantBehaviorSpecification`, `ParticipantToolAffordance`, `ParticipantActionContract`, `ParticipantObservationBoundary`, `ParticipantActionAdmissionRequest`, participant behavior history, action result contracts, and SEM-211 precondition/effect/failure semantics. |
| Decision surface and exposure | `ParticipantDecisionSurfaceModel`, `ParticipantContextViewModel`, exposure policies, participant implementation manifest/selection/provenance contracts, view timelines, observation envelopes, markings, redaction, and ADR-085 information-flow coordinates. |
| Runtime facts | `runtime-fact-binding-plane-v1`, `RuntimeFactBindingPlane`, `RuntimeFactBindingAdmission`, `RuntimeFactSinkModel`, runtime fact visibility/freshness/sensitivity policy, and one-shot dispatch boundaries from #791. |
| Evidence and run provenance | `ExperimentCaptureSpecModel`, `ExperimentEvidenceRecordModel`, derived-measure contracts, `ExperimentRunModel`, apparatus context, participant implementation provenance, evidence refs, digests, and loss/redaction disclosures. |
| Backend capability | `BackendManifestV2Model`, workflow/objective/evaluator/participant-runtime/observation capability declarations, governed concept vocabularies, backend profiles, and conformance report patterns. |
| Diagnostics and errors | `SDLParseError`, `SDLValidationError`, `SDLInstantiationError`, `Diagnostic`, `Severity`, operation receipts/statuses, bounded HTTP 4xx details, and the redacted FastAPI internal-error envelope. |
| Publication and workflow policy | Published schemas under `contracts/schemas/`, `schema_bundle()`, `contracts/schema-publication-manifest.json`, `contracts/fixtures/`, `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and `tools/verify_all.py`. |

Do not add duplicate schema registries, validators, reference resolvers,
exception hierarchies, planner engines, scoring engines, persistence stores,
audit streams, log formats, backend protocol families, or CI workflows.

## Cross-Cutting Layers And Gates

The intended design must pass these layers.

1. **SDL source/parser gate.** Authored step-mode data enters only through the
   existing bounded YAML/profile loader, normalized keys, closed SDL models,
   portable identifiers, and variable rules. It contains refs and governed
   enums, not shell, URL, environment, prompt, provider, credential, or opaque
   command fields for objective/scaffolded mode.

2. **Semantic-reference gate.** Objectives, assertions, participant actors,
   targets, action contracts, affordances, observation boundaries, fact sinks,
   workflows, and step-state refs resolve through `SemanticValidator`,
   declaration indexes, canonical addresses, objective-window analysis, and
   existing role checks. Dangling, ambiguous, cyclic, out-of-scope,
   unsupported, or role-incompatible refs fail closed with collected SDL
   diagnostics.

3. **Instantiation/config gate.** `${...}` placeholders use the existing
   whole-field substitution path and must be concrete in instantiated
   scenarios. Step modes, scaffold refs, capability refs, and sink identities
   cannot be created, renamed, retargeted, or sourced from ambient environment
   variables, CLI flags, process state, or runtime observations.

4. **Contract/schema gate.** Any published shape changes to SDL authoring,
   instantiated scenario, snapshots, workflow state, decision surface, runtime
   facts, or provenance records must use closed contract models, hand-governed
   schemas, schema-publication ledger entries, generated-schema parity, and
   valid plus single-defect invalid fixtures. Python generation alone is not
   authority for a published schema change.

5. **Capability/admission gate.** Backend and participant implementation
   support is declared through existing manifests, profiles, feature-support
   entries, and conformance evidence. Missing objective, workflow,
   decision-surface, action, observation, fact-source, time, or evidence
   capability returns typed unsupported/unmet-precondition diagnostics. It is
   never approximated by running a nearby command or hiding a weaker mode.

6. **Participant visibility and scaffold gate.** Hints, scaffolds, visible
   context, allowed action families, and affordances must pass the compiled
   observation boundary, view relation timeline, exposure policy, audience
   scope, markings, redaction policy, source-layer transformation, evidence,
   provenance, and order point. Future disclosure and operator/auditor access
   cannot justify participant-visible scaffold exposure.

7. **Action-attempt and fact-binding gate.** Tool choice remains at the
   participant/action layer. Every attempted action must resolve to a governed
   action-contract address, pass SEM-211 admission and runtime policy, bind
   only authorized runtime fact sinks, and emit attempt, selected tool or
   affordance, bound fact, outcome, evidence, and provenance records through
   existing carriers.

8. **Truth/evidence gate.** Step success composes assertion truth results over
   captured evidence. Missing, stale, redacted, lossy, ambiguous, unsupported,
   unauthorized, unknown, and false remain distinct. Unknown or unsupported
   never counts as success, and negation must not turn either into success.

9. **Authentication/API gate.** The normal language change adds no HTTP
   surface. Any later route for step execution, fact reads/writes, decision
   surfaces, or action dispatch must reuse `create_control_plane_app()`,
   `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy
   identity, target-bound role authorization, request-size limits,
   idempotency/fingerprints for mutations, audit recording, and bounded error
   details.

10. **Secret and OS/process gate.** No token, password, private key, raw secret
    value, hidden answer, prompt, policy body, raw evidence payload, rejected
    input, backend-native object, environment dump, stdout/stderr, traceback,
    or host path may enter SDL, contracts, diagnostics, audit, logs, fixtures,
    argv, command strings, filenames, or public API details. Adapters use fixed
    invocation shapes, controlled working directories, bounded time/output, no
    `shell=True`, and secret providers at authorized sinks only.

11. **Persistence and observability gate.** Durable facts belong in first-class
    versioned carriers: workflow result/history, participant behavior history,
    decision-surface/context views, runtime fact binding history, experiment
    evidence, run provenance, operation receipts/statuses, runtime snapshots,
    and audit events. Do not store step meaning or outcomes only in
    `metadata`, `details`, tags, raw logs, backend DTOs, or a mutable global
    key/value store.

12. **Package boundary gate.** Authored language models stay in `aces_sdl`,
    compiled projections in `aces_processor`, portable DTOs in
    `aces_contracts`, live control/security/persistence in `aces_runtime`,
    backend declarations in `aces_backend_protocols`, backend realization in
    backend adapters, and conformance in `aces_conformance`. No implementation
    logic belongs in compatibility-only `implementations/python/src/aces/`.

## Extensibility Seam

The extensibility seam is a closed step-mode/realization profile that carries
stable references, not copied semantics or executable text. It should be
parameterized by:

- mode (`scripted`, `objective`, `scaffolded`);
- objective and assertion refs;
- actor, target, workflow, and step canonical addresses;
- precondition/invariant/postcondition and failure-condition refs;
- governed budget/time-window refs from existing time carriers;
- allowed action-contract family, affordance, capability, and observation
  refs;
- scaffold exposure and limitation refs;
- runtime fact sink refs and absence disposition;
- required evidence/provenance refs; and
- compatibility/procedure provenance when mode is `scripted`.

The next reasonable variation should add a governed mode term, scaffold form,
capability family, fact source, or time/evidence profile at this seam. It
should not require a new workflow language, private planner, tool-selection
algorithm, scoring engine, visibility taxonomy, variable binder, runtime fact
store, or per-backend step implementation.

## Gotchas And Anti-Patterns

Avoid:

- renaming hardcoded commands to `objective`, `technique`, `tool`, `hint`, or
  `procedure` while preserving command-as-meaning;
- adding command, shell, URL, prompt, environment, provider option, browser
  script, package coordinate, or backend-native query fields to
  objective/scaffolded steps;
- treating a tool label, ATT&CK/CVE id, package name, endpoint, account,
  interactive-access declaration, installed binary, backend capability, or
  manifest expectation as an action contract;
- conflating step execution mode with participant decision-surface mode,
  behavior mode, implementation selection, exposure policy, or backend support;
- making workflow step outcome, participant-local action success, operation
  status, evaluator `passed`, reward, score, or self-report the objective truth
  model;
- deriving preconditions, postconditions, target properties, thresholds,
  evidence adequacy, or temporal guarantees from command text or descriptions;
- letting scaffold guidance reveal hidden truth, private answer keys, canaries,
  adjudication material, future disclosures, or evaluator-only evidence;
- allowing runtime facts, tool choice, observations, backend failures, or
  retries to mutate scenario variation, trial identity, topology, objective
  meaning, workflow structure, run id, random streams, or apparatus selection;
- silently downgrading unsupported capabilities to scripted mode, omitting
  failed preconditions, or treating stale/missing/ambiguous/unauthorized facts
  as absence-neutral;
- creating a step-local planner, scoring rubric, rules engine, expression
  language, visibility model, error hierarchy, logger, store, or conformance
  runner; and
- claiming backend-neutral success without evidence refs, truth-result
  provenance, capability support, clock/order context, and explicit limitation
  disclosure.

## Non-Goals And Implementation Boundary

- This preflight does not implement SCE-004, choose final field names, publish
  schemas, migrate examples, add fixtures, update traceability, or change
  runtime behavior.
- SCE-004 does not choose a participant planning algorithm, mandate autonomy,
  standardize prompts, provide an external-agent API, create a tool runner,
  credential broker, UI, portal, shell/RPC protocol, policy engine, or backend
  command vocabulary.
- It does not replace backend capability declarations, participant action
  contracts, observation boundaries, decision surfaces, runtime fact bindings,
  proposition truth, experiment evidence, run provenance, or archival study
  analysis.
- It does not make every workflow step autonomous. Scripted steps remain valid
  for calibration and exact procedural tests when they are explicit and
  provenance-bearing.
- It does not put a private planner or scoring engine in SDL. SDL defines
  goals, constraints, exposure/scaffold refs, capability requirements, and
  success assertions; runtime and participant layers record attempts,
  selected tools, observations, outcomes, and evidence.
