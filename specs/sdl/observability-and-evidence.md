# Catalog 5 - Observability and Evidence Planes

This catalog states SDL authoring rules for ADR-066. The implemented
`evidence_requirements` top-level section carries authored capture intent;
scenario-native observability remains expressed through the relevant node
runtime families. A future field still has to update `sections.md`,
`references.md`, the published SDL schemas, the reference implementation,
fixtures, and tests.

## Plane Rule

An SDL authoring construct that makes an observability or evidence claim MUST
have a primary plane:

- scenario-native observability;
- authored evidence requirement;
- processor/backend operational observability;
- captured evidence; or
- derived analysis.

The carrier decides the plane. A string such as `log`, `trace`, `telemetry`,
`observation`, or `evidence` does not decide meaning on its own.

## Scenario-Native Observability

A scenario-native observability system is an in-world resource. It may be a
runtime service, sensor, detection engine, monitoring manager, telemetry
collector, tracing backend, metrics store, dashboard, forwarding agent, or
comparable scenario element when the scenario makes that system part of the
environment.

Scenario-native observability systems:

- MUST have stable SDL identity when they are targetable;
- MUST use the runtime-family model under `nodes.<node>.runtime.*` when the
  system is node-scoped logical service state;
- MAY use existing runtime families such as `network_sensors`,
  `network_detection_engines`, `security_monitoring_managers`,
  `forwarding_agents`, `service_listeners`, `platform_applications`, or
  `datastore_services` when those families carry the intended meaning;
- MUST NOT be represented as a generic top-level observability bag; and
- MUST NOT satisfy an authored evidence requirement merely by existing.

A new runtime family is appropriate only when the observability system has a
distinct product-neutral logical service identity, collection name, primary id,
child-ref tree, owning ADR, schema, validation, and tests.

## Authored Evidence Requirements

An authored evidence requirement says what data, evidence, or output must be
captured. It is an authoring obligation, not proof of capture.

SDL carries authored evidence requirements in the map-keyed
`evidence_requirements` section. Each entry is a portable capture-intent
declaration. It may cite a scenario-native observability runtime-family ref as
one source, but that source remains an in-world system and does not satisfy the
requirement merely by existing.

An authored evidence requirement MUST declare:

- the source refs or source class;
- the scope refs or scope;
- the capture window, trigger ref, boundary ref, or comparable boundary kind;
- the channel, channel refs, modality, or boundary kind;
- expected artifact role or media kind when applicable;
- sensitivity and redaction expectation;
- integrity or chain-of-custody expectation when applicable; and
- loss-disclosure expectation.

Authored evidence requirements:

- MAY reference a scenario-native observability system as a source;
- MAY map to `experiment-capture-spec-v1` concepts when executable capture
  contracts are generated;
- MUST remain independent of participant `objectives`;
- MUST NOT be objective targets or implied by objective success criteria;
- MUST remain distinct from `experiment-evidence-record-v1` raw evidence; and
- MUST remain distinct from `experiment-derived-measure-v1` interpreted
  outputs.

## Processor/Backend Operational Observability

Processor/backend operational observability includes apparatus logs,
diagnostics, audit records, health checks, traces, setup evidence, measurement
channels, and capability declarations. These facts are not scenario meaning
unless an SDL or runtime contract explicitly projects them.

SDL authoring MUST NOT depend on backend-private object ids, raw trace payloads,
operator secrets, process argv, environment dumps, full stack traces, or
diagnostic text as portable evidence or participant-visible state.

## Captured Evidence And Derived Analysis

Captured evidence belongs to evidence records or artifact references. Derived
analysis belongs to derived measures, result summaries, outcome
interpretations, studies, reports, exports, or claims.

SDL authoring MAY name the requirement or source that later evidence must
satisfy, but it MUST NOT treat a captured artifact, backend log, result
summary, metric value, or analysis output as the authored requirement itself.

Derived analysis MUST cite source evidence before it supports a claim. Hidden
truth, hidden answer keys, evaluator state, private traces, prompts, secrets,
and adjudication assets MUST NOT become participant-visible or public analysis
content without an explicit marking, redaction, and authorization boundary.

## Augmentation

When processor or backend augmentation is represented in SDL-adjacent
contracts, the augmentation classification is additive:

- `apparatus_only`;
- `environment_visible`;
- `participant_visible`; and
- `comparability_relevant`.

Participant-visible augmentation MUST route through visibility projection and
participant observation rules. Environment-visible and comparability-relevant
augmentation MUST have first-class provenance or evidence disclosure. They MUST
NOT be hidden in metadata, diagnostics, audit blobs, backend-native DTOs, or
raw logs.

Run-level processor/backend augmentation disclosures are carried by
`experiment-run-v1` `augmentation_disclosures`. That carrier records the
augmentation purpose, realization layer, additive classifications, portable
carrier refs, disclosure policy, markings, observer/comparability effects, and
run-traced evidence refs. SDL authoring that depends on augmentation output
must map to that run-provenance carrier rather than relying on backend logs,
free-form metadata, evaluator internals, or untyped diagnostic text.

## Reference And Validation Requirements

Future SDL fields for this catalog must satisfy the existing SDL gates:

- parser and model closure through `SDLModel`;
- concrete identifier keys, with no `${var}` placeholders in symbol-defining
  keys;
- fail-closed reference resolution through `references.md`;
- instantiation followed by full semantic revalidation;
- controlled vocabulary or concept-authority bindings for portable kinds;
- published schema parity with the reference implementation; and
- ADR-056/057 redaction for observed values and secret-bearing facts.

## Extension Rule

To add a scenario-native observability or authored evidence-requirement
surface, update the canonical catalogs instead of adding parallel prose:

1. add or amend the owning ADR;
2. add a row to `sections.md` and reference edges to `references.md` when a new
   SDL field exists;
3. add a runtime-family row to `runtime-inventory.md` when the surface is a
   node-scoped logical service;
4. update published schemas and the schema publication manifest when the
   structural contract changes;
5. update semantic validation and fixtures; and
6. add positive and negative tests from
   `specs/formal/observability-evidence-plane.md`.
