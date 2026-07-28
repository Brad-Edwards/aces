# Issue 828 Formal Semantic Validation Retest Preflight

Date: 2026-07-27

Issue: #828. Requirement: ASR-530. The issue body, test protocol, and
acceptance criteria narrow the requirement for this evidence release.

This note fixes the repository-wide boundary for the retest after issues #826
and #827. It does not run the protocol, add cases, change production semantics,
or implement either analyzer. No new ADR is needed: ADR-021, ADR-072, ADR-086,
the issue #168 preflight, and the issue #827 formal specification already own
claim evidence, validation strength, satisfiability, and exploit-path meaning.

## Decision Boundary

Issue #828 is an evidence integration and replay gate. It is not an owner for
SDL parsing, semantic validation, satisfiability translation or solving,
attack-graph derivation, path search, participant semantics, or compiler
behavior.

Preserve every issue #168 v1 protocol, corpus, execution snapshot, analysis,
and observation byte-for-byte. Create a new protocol and corpus revision for
the retest. Every v1 case id and single-defect intent remains present. Replay
the executable v1 cases at the new pinned revision. The historical
satisfiability and exploit-path request cases remain historical baseline
controls; do not reinterpret their old `unsupported` observations as results
from capabilities that did not exist then. Add distinct case ids for the new
production satisfiable, unsatisfiable, valid-path, and invalid-path controls.

The new evidence release must be one coherent selection, not an independent
"highest base plus highest supplement" composition. One immutable bundle
record must atomically bind the exact protocol, corpus, execution snapshot,
analysis, and production evidence artifacts by repository path and SHA-256.
Validate every indexed historical bundle record, not only the record selected
as latest. This prevents a changed historical snapshot, missing capability
join, or incompatible protocol/snapshot combination from being hidden by a
newer record.

Reuse the digest-pinned immutable bundle-record pattern in
`docs/research/specification-coverage/bundles/` and
`tools/check_specification_coverage.py`. Keep
`tools/evidence_bundle_index.py` as the shared bounded discovery and semantic
revision helper. Do not add another manifest discovery utility. The existing
formal-validation checker's independent maximum-selection behavior is a
historical compatibility path, not the design for the integrated retest.

## Evidence Ownership And Joins

The research bundle records observations; it does not redefine production
evidence.

- Whole-scenario cases use
  `raes_processor.satisfiability.analyze_scenario_file()` and
  `replay_satisfiability_evidence()`. The complete
  `ScenarioSatisfiabilityEvidenceModel` is the result authority, including the
  normalized model, pinned solver configuration, satisfiable witness or
  subset-minimal unsatisfiable core, structured diagnostics, and digests.
- Exploit-path cases use
  `raes_processor.exploit_path.analyze_exploit_path_file()` and
  `replay_exploit_path_evidence()`. The complete
  `ExploitPathAnalysisEvidenceModel` is the result authority, including the
  source and admitted-snapshot digest bindings, normalized graph, query, search
  configuration, valid-path witness or invalid-path evidence, structured
  diagnostics, and digests. The admitted snapshot remains in the separate
  governed input artifact; do not duplicate it into the research record or
  claim that the result envelope embeds it.
- Consumer-facing reproduction commands use the existing
  `raes processor satisfiability` and `raes processor exploit-path` commands
  with explicit profile and repository-confined input path arguments. The
  checker must compare their parsed published envelopes with direct production
  service replay; a CLI success label or test helper is not evidence.
- Schema, semantic, workflow-reachability, participant-obligation, and
  parse-to-compile determinism cases continue through the issue #168 production
  entrypoints. Do not replace them with contract-model construction or
  analyzer-specific shortcuts.

Store complete production evidence envelopes as immutable research evidence
artifacts. Keep each exact analyzer input in the versioned corpus and prove its
join through the envelope's source digest, snapshot/model joins, and production
replay. Join the envelope from the execution snapshot by case id, execution id,
source digest, evidence profile, analysis profile, configuration digest,
canonical evidence digest, artifact path, and artifact SHA-256. Do not copy
selected witness, core, graph, query, snapshot, or diagnostic fields into a
second research schema. The published contract models and schemas already own
those shapes.

Every new corpus case has exactly one fixed-argv command, one observation, and
one production evidence artifact. Every observation joins exactly one protocol
claim and corpus case. Reject duplicate ids, dangling or many-to-one joins,
unselected artifacts, outcome/payload mismatches, missing positive or negative
controls, absent evidence payloads, stale digests, and artifacts whose source
or configuration does not reproduce.

## Claim Status And Drift

Keep these axes independent:

- production outcome: `satisfiable`, `unsatisfiable`, `unsupported`,
  `valid-path`, or `invalid-path`;
- gate execution status under ADR-072;
- validation-strength disclosure;
- ADR-021 claim status: `demonstrated`, `partial`, `untested`, or `refuted`.

Derive each claim status from the new protocol's required controls and recorded
observations. A declared expected status is a preregistered ceiling, not a value
to copy into the analysis. A claim is `refuted` when a required supported
positive fails, a single-defect negative is accepted, an evidence envelope
does not replay, or a required join is absent. It is `untested` when no governed
production entrypoint ran. `Partial` and `demonstrated` must follow the
protocol's declared coverage boundary and cannot exceed it.

The current issue #168 `recompute_claim_results()` behavior copies the declared
expected status after matching its historical case matrix. Preserve that
behavior only for replaying the immutable baseline; it is not the derivation
rule for the new protocol or analysis.

Compare every replayable retained v1 case with its immutable v1 observation.
Record any new-revision difference as an explicit, bounded drift disposition
in the new snapshot and analysis; never edit the baseline or silently whitelist
the new digest. Existing historical rename compatibility constants remain
narrow v1 migration accommodations. Do not add new digest-pair exceptions for
the retest.

The satisfiability claim is bounded to
`raes-finite-domain-satisfiability-v1`, its declared translation and theory,
and the exact solver configuration. An unsatisfiable core is subset-minimal
under the governed deletion procedure; it is not a general proof certificate.
The exploit-path claim is bounded to `raes-exploit-path-analysis-v1`, its
admitted snapshot, binding and transition semantics, query, search profile, and
bounds. A failed query does not establish real-world non-exploitability, and a
witness does not establish backend execution.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required reuse |
| --- | --- |
| Historical baseline | `docs/research/formal-semantic-validation/`, issue #168 preflight, `protocol-v1.json`, `corpus/manifest-v1.json`, and every v1 snapshot and analysis. Preserve; do not rewrite. |
| Evidence index | `tools/evidence_bundle_index.py` plus the digest-pinned atomic bundle records used by specification coverage. Do not create parallel discovery or select independent maxima. |
| Integrity failures | `tools.policy.common.load_bounded_json_object`, `safe_repo_path`, `PolicyFailure`, stable rule ids, closed key sets, bounded counts, and complete joins. |
| SDL source and semantics | `read_sdl_source`, `parse_sdl_file()`/`parse_sdl()`, `SemanticValidator`, `instantiate_scenario()`, phase admission, and existing SDL exception/diagnostic types. |
| Compiler and workflow evidence | `compile_runtime_model()`, canonical model serialization, existing workflow semantic analyzers, and the issue #168 replay cases. |
| Participant evidence | The protocol-declared pytest node ids, fixed local pytest invocation, timeout, and existing participant contract/runtime diagnostics. |
| Satisfiability | ADR-086, `specs/formal/scenario-satisfiability/`, `raes_contracts.satisfiability`, `raes_processor.satisfiability`, the published evidence schema, and its replay API. |
| Exploit paths | `specs/formal/exploit-path-analysis/`, `raes_contracts.exploit_path`, `raes_processor.exploit_path`, the published evidence schema, and its replay API. |
| Canonical digests | RFC 8785/JCS `canonical_contract_digest`, source-byte digests, canonical instantiated SDL digest, and the existing model/graph/query/configuration digest fields. |
| CLI and errors | `raes_cli.processor`, value-free stderr, published JSON on stdout, exit `0` for completed supported results, `2` for typed unsupported, and `1` for malformed or operational failure. |
| Contract publication | Existing hand-governed schemas, `schema_bundle()` parity, schema-publication entries, fixtures, and JSON artifact checks. Issue #828 should consume them, not revise or duplicate them. |
| Workflow and observability | The existing nox contracts gate, `SessionReporter`, `tools/verify_all.py`, repo policy, requirement governance, docs, JSON artifact, OSV, private-key, and gitleaks checks. |

There is no controller, HTTP DTO, repository, mutable service, database, cache,
runtime snapshot field, experiment archive, or new logger in this design.

## Cross-Cutting Security And Validation Layers

1. **Research artifact shape.** Load protocol, corpus, bundle records,
   snapshots, analyses, and retained evidence through bounded,
   duplicate-rejecting JSON loading. Use closed keys, bounded lists and strings,
   stable ids, SHA-256 validation, and `safe_repo_path`. Corpus roots and bundle
   selection are repository data, never environment-selected paths.
2. **SDL source gate.** Satisfiability and retained SDL cases keep the existing
   UTF-8, byte/scalar/depth/node/alias, YAML tag/directive, duplicate-key,
   composition/import confinement, closed-model, semantic-validation, and
   instantiation gates. The retest must not repair an invalid fixture or bypass
   semantic validation.
3. **Exploit-path input gate.** Use the production file entrypoint's 2 MiB
   bound, UTF-8 JSON decoding, closed `ExploitPathAnalysisInputModel`, canonical
   snapshot digest, normalized-graph join, closed query, profile, and search
   bounds. The production JSON loader currently does not itself reject
   duplicate keys; the research artifact loader must reject them without
   claiming that this strengthens the production analyzer. If this affects a
   case, record it as a limitation or separate capability finding rather than
   patching #827 here.
4. **Contract and evidence gate.** Parse stored outputs through the existing
   published evidence models and checked-in schemas. Their model validators
   enforce outcome/payload exclusivity, digest joins, witness/core/failure
   shape, and diagnostic joins. Do not add a research-only equivalent.
5. **Configuration gate.** Profiles are explicit closed ids. Retain the typed
   Z3 configuration and exploit search configuration from the evidence
   envelopes. Record only the allow-listed output-affecting versions:
   repository commit, Python/runtime package version where relevant, Z3
   package and engine versions, and analysis/configuration profiles. Do not
   add environment-selected artifact paths or profiles, and do not capture an
   environment dump. The historical participant replay inherits the host
   environment; preserve that behavior only for baseline replay and do not call
   it hermetic. Any new subprocess environment input must be non-sensitive,
   output-affecting, explicitly allow-listed, and recorded as bounded
   configuration rather than as raw environment data.
6. **Authentication and authorization.** The retest is local, offline, and
   read-only, so it adds no auth surface. Do not route it through the control
   plane or introduce a research bypass. A future remote adapter must reuse
   `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
   role/target authorization, request-size and idempotency guards, audit
   summaries, and redacted internal errors.
7. **Secrets and sensitive data.** Use synthetic public fixtures. Never include
   credentials, hidden answers, raw parameter maps, environment values, trust
   policies, backend-native objects, full exception inputs, source snippets,
   tracebacks, or unrestricted subprocess output in fixtures, evidence,
   diagnostics, logs, or committed snapshots. The repository secret and
   private-key gates remain mandatory.
8. **OS and process exposure.** Solver and exploit analysis remain in-process
   and network-free. Reproduction subprocesses use a fixed local executable,
   argument arrays, `shell=False`, bounded timeout and output, and a
   repository-confined working directory. Process argv may contain only
   non-sensitive fixture paths, stable ids, and profile names—not raw SDL,
   query JSON, witnesses, credentials, tokens, or evidence payloads.
9. **Error envelopes.** Preserve `SDLParseError`, `SDLValidationError`,
   `SDLInstantiationError`, `SatisfiabilityOperationalError`,
   `ExploitPathOperationalError`, published `DiagnosticModel`, and
   `PolicyFailure` boundaries. Store stable codes, safe addresses, bounded
   messages, result kinds, and digests. Do not create a second exception tree
   or commit raw exception text.
10. **Persistence and logging.** Persistence is limited to sanitized,
    Git-tracked immutable research artifacts. Gate reporting uses
    `SessionReporter` and bounded `PolicyFailure` output. Do not write to
    `ControlPlaneStore`, runtime/experiment persistence, a database, cache,
    audit blob, telemetry stream, or bespoke log.

## Whole-Repository Scope

The retest must account for:

- `docs/research/formal-semantic-validation/`, its checker and integrity tests,
  plus the immutable-bundle pattern in specification coverage;
- `specs/formal/scenario-satisfiability/`, ADR-086,
  `raes_contracts.satisfiability`, `raes_processor.satisfiability`, the
  production CLI, published schema/fixtures, and solver dependency pin;
- `specs/formal/exploit-path-analysis/`, `raes_contracts.exploit_path`,
  `raes_processor.exploit_path`, the production CLI, and published
  schema/fixtures;
- SDL source loading, semantic validation, instantiation, phase contracts,
  compiler canonicalization, workflow analyzers, participant contract tests,
  and their existing error envelopes;
- ADR-021 claim statuses, ADR-072 validation-strength disclosure,
  `specs/formal/assurance-fulfillment.yaml`, and the formal validation-profile
  documentation; and
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/verify_all.py`, `.github/workflows/ci.yml`, schema publication,
  generated-schema parity, JSON artifact validation, docs, OSV, gitleaks, and
  private-key detection.

## Extensibility Seam

The stable observation identity is:

```text
(protocol_revision, corpus_revision, repository_revision, execution_id,
 claim_class_id, case_id, entrypoint_id, evidence_profile, analysis_profile,
 configuration_digest)
```

The atomic bundle record selects all artifacts for one evidence release. Cases
and observations carry profile ids and configuration digests as data, not
hard-coded per-tool columns in a growing top-level manifest. The next
reasonable variation—a new solver adapter, attack-transition family, search
profile, repeated repository revision, or new claim class—adds a new protocol
or case revision and immutable bundle record. It must not require editing prior
evidence, SDL models, production evidence envelopes, exception hierarchies,
runtime persistence, or the shared bundle discovery helper.

## Gotchas And Anti-Patterns

Avoid:

- editing v1 protocol, corpus, snapshots, analyses, or observations to reflect
  capabilities that shipped later;
- independently selecting the newest base, satisfiability, and exploit-path
  parts without an atomic compatible-release join and digest pins;
- reusing historical unsupported case ids for new executable semantics, or
  counting the historical placeholders as production controls;
- storing only outcome labels or evidence digests while omitting the governed
  witness, unsatisfiable core, invalid-path evidence, or diagnostics;
- copying production witness/core/path fields into a duplicate research DTO or
  schema;
- using test helpers, direct Pydantic construction, monkeypatches, mocks,
  test-local solvers/searches, generated schemas, or CLI exit codes as
  substitutes for production service replay;
- deriving `demonstrated` from an expected-status field, a green test suite,
  FM classification, validation-strength label, or documentation;
- promoting a finite-domain solver result beyond its theory/translation/domain
  or an exploit-path result beyond its exact snapshot/graph/query/search
  semantics;
- calling workflow reachability, topology, ACLs, vulnerability labels,
  deployment success, or scenario satisfiability an exploit-path witness;
- calling a subset-minimal unsatisfiable core a universal proof certificate;
- silently accepting drift, adding new hard-coded old/new digest pairs, or
  validating only the latest bundle so historical mutation goes unnoticed;
- adding another schema registry, manifest loader, graph/query model, solver
  wrapper, canonical digest format, diagnostic envelope, exception hierarchy,
  persistence store, logger, or CI workflow; and
- exposing raw sources, parameters, credentials, query bodies, witnesses,
  solver/native dumps, subprocess output, absolute host paths, argv,
  environment dumps, or tracebacks in errors or committed evidence.

## Non-Goals And Implementation Boundaries

- Do not change or extend the satisfiability theory, translation, solver,
  witness/core semantics, or solver dependency.
- Do not change or extend attack-graph bindings, transition semantics, query
  semantics, path search, evidence contracts, or analyzer input handling.
- Do not fix findings exposed by the retest under issue #828. Freeze the
  observation, classify the claim honestly, and assign product correction to
  its owning surface.
- Do not add SDL syntax, validation profiles, contract schemas, runtime
  behavior, backend behavior, HTTP/MCP endpoints, authentication, persistence,
  deployment, network scanning, exploit execution, or external services.
- Do not claim arbitrary-SDL satisfiability, a complete unsatisfiability proof,
  real-world exploitability or non-exploitability, backend realizability,
  runtime determinism, participant causality, or counterfactual necessity.
- The shipped result is the new immutable evidence release, integrity/replay
  gate, derived bounded analysis, and documentation of what that evidence does
  and does not establish.
