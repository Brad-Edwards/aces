# Issue 260 ASR-512 executable behavioral validation preflight

Date: 2026-07-28

Issue: #260. Ground Control requirement: ASR-512. The issue statement and the
requirement record are the delivery contract.

This note sets the boundary for executable behavioral validation probes. It
does not add SDL syntax, contracts, schemas, fixtures, or executors. It also
does not add reports, APIs, storage, or runtime behavior. No new ADR is needed.
ADR-072 owns validation strength and disclosure. ADR-079 owns proposition,
probe-binding, and truth semantics. ADR-081 owns behavioral-relation claims.
ADR-066 owns the observation and evidence-plane split.

## Implementation status

Issue #260 implements the subject-bound execution seam in
`raes_conformance.behavioral_validation`. A `BehavioralProbeCase` joins one
scenario, participant, workflow, or experiment subject to one validated
behavioral claim, digest-pinned probe binding, finite input digest, and
execution basis. `run_behavioral_validation_probe()` admits the claim and
its left-carrier match to the exact subject ref, plus executor capabilities,
before invoking trusted injected code. It then constructs a
`BehavioralProbeResult` from the admitted case identities and returned
evidence. The executor cannot replace the subject, claim, binding, input, or
execution basis in the result.

The runner fails closed for invalid claims, subject-claim carrier mismatches,
unsupported capabilities, missing or blank evidence references, unverified
cleanup, residual state, and sanitized executor failures. It is an internal
implementation seam, not a portable schema, command dispatcher, plugin loader,
truth algebra, report graph, or persistence surface. Subject-specific carriers
remain authoritative and supply cases through their trusted adapters.

## Decision boundary

ASR-512 adds an independent technique for exercising a behavioral property
claimed by a scenario, participant, workflow, or experiment. It does not add a
new meaning for those properties.

Keep four concerns separate:

1. **Claim semantics** say what property is claimed. Use a proposition and
   assertion for finite state truth. Use a revisioned
   `BehavioralClaimBindingModel` for a behavioral or empirical relation. A
   probe must not infer meaning from a command or test name. It must not infer
   meaning from a workflow outcome, action name, metric, or description.
2. **Probe binding** names a checked and versioned implementation. It may
   exercise the claim, but it cannot change the claim. Use
   `PropositionProbeBindingModel` for proposition truth. Use the injected
   `RealizationConformanceHarness` pattern for conformance-owned execution. Do
   not put Python callables or module names in profile data. The same ban
   covers shell commands, executable URLs, and backend dispatch rules.
3. **Probe execution** is one bounded invocation. It binds the exact subject,
   target, configuration, input, clock or seed, observation policy, and
   cleanup policy. It runs only after parser and semantic admission. Capability,
   authorization, and contract gates also run first.
4. **Probe evidence and disclosure** record what happened. Use the owning
   truth, workflow, participant-history, experiment-evidence, and conformance
   carriers. Use the existing validation-basis carrier too. A probe result may
   support `behavioral_execution` and `governed_diagnostics` gate rows. It does
   not replace `ValidationBasisDisclosureModel`. It cannot create strength by
   itself.

A probe pass is finite evidence about the exact recorded case. It is not a
universal proof or backend equivalence. It is not participant conformance or
experiment validity. It is not a falsification-backed claim. Those stronger
claims have separate quantifier, evidence, and protocol rules.

## Claim-surface mapping

| Subject | Claim authority | Execution and observation authority | Durable result/evidence |
| --- | --- | --- | --- |
| Scenario or scenario snapshot | `Proposition`, `Assertion`, snapshot identity, and `SemanticValidator`. | Compiled claim resources, evaluator capabilities, a versioned probe binding, and runtime truth admission. | `PropositionTruthResultModel`, evidence refs, and a subject-bound `ValidationBasisDisclosureModel`. |
| Workflow | Assertion refs and workflow state-machine semantics. Step completion is not property truth. | The existing workflow and control-plane path. Proposition truth is checked at the governed step or window boundary. | `WorkflowExecutionStateModel` and workflow history. Also use attempt truth/evidence refs and validation-basis disclosure. |
| Participant or behavior specification | Action contracts, observation boundaries, outcome rules, authority, scope, and behavior specifications. Use any revisioned relation claim too. | Existing action admission, lifecycle, decision surface, history validators, and conformance probes. | Participant behavior and episode history. Also use observation, outcome, evidence, claim, and validation-basis records. |
| Experiment task, run, or study | Task protocol, metric definitions, study `behavioral_claims`, allocation, analysis plan, and validity notes. | Existing apparatus, capture, evidence, derived-measure, and cross-validation paths. | `ExperimentEvidenceRecordModel`, run traceability, result summaries, and derived measures. Also use claim and validation-basis records. |
| Backend or participant conformance claim | A revisioned relation binding and selected backend/profile contract. | `run_fixture_suite()`, `run_target_conformance()`, existing cases and probes, and the realization harness when needed. | Existing bounded report and claim. Also use evidence refs, diagnostics, and validation-basis disclosure. |

Do not force every subject into proposition truth. Proposition truth is the
oracle for a finite typed state claim. Participant trace properties use their
own contracts. Cross-carrier and statistical claims use the relation catalog
and existing evidence contracts. The reverse shortcut is also banned. Do not
use a generic relation claim to avoid proposition truth rules.

## Canonical incumbents

| Concern | Canonical incumbent and required reuse |
| --- | --- |
| Validation taxonomy and result disclosure | Use ADR-072 and the validation profile catalog. Use `select_validation_profile()` and the existing disclosure, gate, and limit models. Catalog and disclosure data never dispatch execution. |
| Scenario truth | Use ADR-079, `Proposition`, `Assertion`, compiled claim resources, and evaluator capabilities. Use `Condition` only for the legacy binding. Keep `PropositionProbeBindingModel`, `PropositionTruthResultModel`, and runtime truth diagnostics. |
| Behavioral and empirical claims | Use ADR-081 and the behavioral-relations catalog. Use `BehavioralClaimBindingModel`, its validator, and `bounded-probe-success`. Do not add a local relation registry. Do not weaken universal-quantifier checks. |
| Participant behavior | Use ADR-067 and the participant formal specs. Keep action contracts, behavior specifications, observation boundaries, outcome rules, action admission, and history. Keep participant history, snapshot, concurrency, and conformance validators. |
| Workflow behavior | Use workflow state-machine and compensation semantics. Keep compiled assertion refs, workflow state/history, and attempt provenance. Use the proposition truth algebra. Lifecycle success is not truth. |
| Experiment behavior | Use the task, run, and study models. Keep capture, evidence, derived-measure, traceability, and cross-artifact validators. |
| Conformance execution | Use the fixture and target runners, existing cases and reports, execution bases, probe outcomes, and injected harness pattern. Keep deterministic cases, cleanup, diagnostics, evidence, and bounded claims. Do not make realization DTOs a universal schema. |
| Diagnostics and errors | Use `Diagnostic`, `Severity`, and stable local codes. Keep existing SDL and Pydantic errors, operation envelopes, and the redacted HTTP 500 envelope. Do not add an ASR-512 exception tree or logger. |
| Persistence and artifacts | Use snapshots and `ControlPlaneStore` for live state. Use experiment evidence, provenance, and validation disclosures for archive facts. Use the shared redaction, safe-path, and atomic-write helpers for a requested artifact. |
| Schema and workflow governance | Use closed `ContractModel` shapes and `schema_bundle()`. Keep published schemas, the publication ledger, fixtures, and conformance checks in sync. Use the checked-in Ground Control, nox, and verification workflow. |

`ConformanceCaseResult`, `RealizationProbeRequest`, and
`RealizationProbeEvidence` are useful internal patterns. They do not authorize
an unreviewed generic schema. `BackendConformanceReport` remains specific to
backend conformance. Do not overload it for all ASR-512 subjects. Prefer the
owning result and evidence carrier. Pair it with the generic validation-basis
disclosure. Add a contract only when a portable fact has no typed home. Keep
that contract small and subject-bound.

## Cross-cutting and security gates

1. **SDL source and parser.** Authoring changes pass the safe YAML loader and
   its limits. Duplicate keys, bad names, and invalid variables still fail.
   Closed `SDLModel` shapes still apply. Instantiation rejects unresolved
   tokens. `SemanticValidator` runs again after instantiation. Parsing and
   language tools remain inert. They never run a probe.
2. **Claim and reference shape.** A probe resolves one exact subject. It also
   resolves an admitted proposition and assertion, or a pinned relation claim.
   Existing reference, role, polarity, projection, scope, digest, and version
   checks fail closed. Carrier identity must match. A path or test name is not
   claim identity. Neither is a free string or object id.
3. **Contract and schema shape.** Portable data uses closed `ContractModel`
   shapes and existing primitive types. It carries a schema version. Cross-file
   rules use `x-raes-invariants`. Add valid and single-defect invalid fixtures
   when a contract changes. Keep generated and published schemas equal. Update
   the publication ledger and conformance registry. A dataclass or serializer
   is not a published contract.
4. **Profile and capability admission.** Resolve the exact profile with
   `select_validation_profile()`. Resolve backend capabilities through existing
   manifests, profiles, and admission helpers. This covers evaluation,
   orchestration, participant runtime, observation, cleanup, and time.
   Unknown or missing support yields an explicit failed or unsupported result.
   Never select a nearby probe. Never lower the property in silence.
5. **Configuration and environment shape.** ASR-512 needs no generic
   environment binder. It also needs no executable path, profile root, plugin
   root, or remote registry. Backend execution still passes its closed config
   checks. Libvirt uses `_validate_config_keys` and the safe URI check. Test
   environment inputs are opt-in apparatus settings. Validate them before
   driver creation. Ambient environment state is not claim or evidence
   authority.
6. **Executable artifact and supply-chain gate.** Treat each script, package,
   image, and external probe as untrusted apparatus. Use pinned digests,
   trust policy, source limits, and allowlists. Use `ImageTrustPolicy` when it
   fits. A source name, import, executable bit, image tag, or download does not
   grant trust. Probe data must not select an arbitrary import or executable.
7. **Authentication and authorization.** Prefer the in-process conformance
   composition root. ASR-512 needs no new route. If a probe crosses HTTP, use
   `create_control_plane_app()` and strict security defaults. Keep verified
   identity, role, target, and participant-controller checks. Keep request
   limits, idempotency, fingerprints, and audit records. Scenario authority is
   not participant authority. Probe capability is not caller authorization. A
   profile never grants execution or evidence-read access.
8. **OS and host exposure.** Adapters use fixed argument lists and
   `shell=False`. They set time, output, and resource bounds. They use a
   controlled work directory and environment. They run with least privilege
   and clean up owned resources. Secrets and hidden answers never enter argv.
   The same ban covers raw payloads, connection URIs, and host paths. Keep the
   OCI injected-runner and redacted-output pattern. Keep the libvirt read-only
   fact channel. Do not add a general guest command runner.
9. **Observation and evidence admission.** Process success, HTTP 2xx, workflow
   completion, action success, and receipts are not property truth.
   Observations must be fresh and addressed. Bind them to the subject, probe,
   and configuration. Meet the required observation strength. Apply the owning
   visibility and redaction rules. Capture intent is not evidence. Raw evidence
   is not a derived measure. Logs are not portable evidence. Participant views
   are not hidden truth.
10. **Error envelopes and observability.** Public failures use a stable code,
    safe address, coarse outcome, and short redacted message. Never expose
    rejected bodies, commands, output, environment values, native objects, or
    traces. Some current helpers join `str(exc)` into messages. Participant
    probe and operation errors can also carry unsafe text. So can
    `HTTPException(detail=str(exc))`. Sanitize these paths before reuse. Audit
    and logs may summarize work. They are not probe evidence.
11. **Persistence and cleanup.** Live state stays in typed snapshots and the
    control-plane store. Archive facts stay in truth, workflow, participant,
    experiment, conformance, and validation-basis carriers. Do not store probe
    meaning only in metadata, details, audit blobs, DTOs, tags, or logs.
    Validate and redact a report before an atomic write. A mutating probe needs
    owned teardown and residual-state disclosure. Unverified cleanup makes the
    result fail.
12. **Repository and package boundary.** SDL meaning stays in `raes`.
    Portable DTOs stay in `raes_contracts`. Compilation stays in
    `raes_processor`. Live control, security, and storage stay in
    `raes_runtime`. Capabilities stay in `raes_backend_protocols`. Adapters
    execute concrete probes. `raes_conformance` owns conformance flow.
    `raes_operations` owns native assembly and artifact writes. `raes_cli`
    owns user wiring. Keep the package policy intact. Do not bypass it with
    private imports, `Any` bags, or compatibility code.

## Outcome and concept separation

These vocabularies answer different questions and must not be merged:

| Surface | Meaning |
| --- | --- |
| `ProbeOutcome` (`passed`, `failed`, `skipped`, `unsupported`) | Whether one bounded probe case executed and met its case oracle |
| Proposition outcome (`true`, `false`, `unknown`, `unsupported`) | Truth/support result for one proposition |
| Validation gate outcome (`passed`, `failed`, `partial`, `not_run`, `unknown`, `unsupported`, `withheld`, `not_applicable`) | One row in an ASR-515 validation-basis disclosure |
| Operation/workflow/evaluator lifecycle status | Whether apparatus work progressed or completed |
| Participant action/outcome interpretation | What one participant action meant at its participant-local boundary |
| ADR-021 evidence status (`untested`, `partial`, `demonstrated`, `refuted`) | Status of a falsification protocol for a major claim |
| Behavioral relation assurance/evidence scope | Quantified boundary and strength of a revisioned relation claim |

A mapping between two rows must be explicit and cautious. A passed finite probe
may support a passed `behavioral_execution` gate. It may also support a finite
`bounded-probe-success` claim. Both uses need evidence and diagnostics. The
probe cannot produce `true` by itself. Nor can it produce `demonstrated`,
`proved`, or `falsification_backed`.

## Extensibility seam

The seam is a stable, subject-bound probe case. Trusted code gives it to an
injected and capability-checked executor. The result uses existing evidence
carriers. The seam has these parameters:

- exact subject kind, stable ref, version, digest, target, and configuration;
- an oracle ref to a proposition/assertion or revisioned relation claim;
- probe implementation id, version, digest, and required capabilities;
- finite case identity and canonical input digest;
- execution basis and any governed clock, boundary, seed, or observation
  policy;
- expected observation and evidence rules, with a cautious outcome map;
- time, resource, and cleanup policy chosen by trusted code; and
- evidence and diagnostic refs, limits, audience, redaction, and profile
  identity.

A future predicate family should add one governed adapter at this seam. The
same rule applies to a participant case or workflow oracle. It also applies to
an experiment design, backend, execution basis, or observation source. Such an
addition must not need a new claim language or profile registry. It must not
need a new truth algebra, report graph, error tree, logger, store, auth path,
or process framework.

## Whole-repository surfaces in scope

- **Normative:** validation profiles and proposition truth. Also include the
  relation taxonomy, participant behavior, workflows, evidence, and experiment
  specs. Include each changed schema, fixture, profile, catalog, and publication
  record.
- **Implementation:** SDL models and semantic checks. Include contract models,
  schema output, compiler projections, manifests, and capability admission.
  Include runtime truth, workflow, participant, security, audit, snapshot,
  store, and cleanup paths. Include conformance runners, injected harnesses,
  adapters, redaction, and artifact writes. Include CLI wiring only if a user
  command is in scope.
- **Verification:** positive and negative fixtures and truth tables. Include
  bad subject, ref, digest, and capability cases. Include stable replay and
  dishonest, no-op, stale, and wrong-target evidence. Test auth, redaction,
  argv, time, resources, cleanup, and residue. Check report/disclosure links,
  module rules, authority, schemas, and policy.
- **Workflow:** use `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  and the three required policy and verification tools. Use
  `RAES_REQUIREMENT_UID=ASR-512` because the branch name lacks a UID. Issue #260
  remains the delivery contract.

## Gotchas and anti-patterns

Avoid:

- executable code, commands, imports, URLs, or dispatch tables in contract
  data;
- one universal property, probe, report, or metadata dictionary;
- making legacy `Condition.command` the portable probe contract;
- deriving expected truth from process exit status;
- making realization-envelope probes the universal ASR-512 model;
- using `BackendConformanceReport` for every subject family;
- creating four new report or runner stacks;
- calling schema acceptance, operation success, action success, evaluator
  readiness, workflow success, or a lone evidence ref behavioral validation;
- equating finite probe coverage with all inputs, all traces, equivalence,
  conformance, empirical validity, or proof;
- merging timeout, missing evidence, unsupported support, false, skip,
  withheld evidence, and cleanup failure into one Boolean;
- copying raw evidence into truth results or disclosures;
- using snapshots or logs as archive evidence;
- using derived measures as raw observations;
- selecting executors or paths from untrusted data;
- falling back to a default target, profile, or probe;
- using `shell=True` or an open child environment;
- leaking sensitive values through argv or errors;
- passing a mutating negative probe without independent non-mutation,
  ownership, cleanup, and residual-state evidence; or
- duplicating schemas, resolvers, vocabularies, validators, truth tables,
  errors, diagnostics, audit, storage, or workflow policy.

## Non-goals and implementation boundaries

- This preflight does not implement ASR-512. It does not choose final field
  names.
- It does not implement ASR-513 counterfactual or necessity validation. It also
  does not implement ASR-514 determinism or stability validation. Negative
  cases and repeated executions do not establish either sibling claim.
- It adds no rules engine, query language, temporal logic, theorem prover, or
  model checker. It adds no statistics engine, remote probe service, plugin
  system, credential broker, or command API.
- It does not redesign profiles, disclosures, truth, relations, action
  admission, workflows, experiment analysis, conformance, security, evidence
  storage, or cleanup.
- It does not make every claim executable. Unsupported properties stay
  explicit when a safe governed path does not exist.
- It adds no authoring-time side effects. Parsing, validation, compilation,
  documentation, MCP inspection, and schema generation remain inert.
- A finite suite does not prove universal behavior, backend equivalence,
  participant strategy coverage, experiment validity, or
  falsification-backed strength.
