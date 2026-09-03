# Issue #1074 - Generated Artifact Environment Consumers Preflight

Date: 2026-08-04

This note records architecture guardrails for issue #1074. It does not
implement the SDL shape, schema change, compiler lowering, provisioner behavior,
or TechVault wiring.

No new ADR is required. This is a bounded extension of the existing
stateful-resource, runtime-environment, schema-authority, realization-honesty,
and explicit-redaction decisions: issue #780, issue #1010, ADR-004, ADR-009,
ADR-056, ADR-057, ADR-061, ADR-070, ADR-072, and ADR-088.

## Contract Boundary

Generated artifacts remain producer-owned desired state. Runtime environment
remains the node-owned declaration of process environment inputs. The new
affordance must connect those authorities without making either one absorb the
other.

The preferred authoring contract has one source of truth per delivery:

- a scalar environment variable is declared on
  `nodes.<node>.runtime.environment[]` with a value-free generated-artifact
  output reference instead of raw `value`;
- an env-file delivery is declared as a node runtime environment input, not as a
  fake variable name and not as an ordinary file mount;
- the compiler derives the generated-artifact consumer projection needed by the
  provisioning resource. Authors do not duplicate the same binding under both
  `runtime.environment` and `generated_artifacts[].consumers[]`.

The shared reference tuple is the seam: generated artifact id, output name,
delivery kind (`environment` or `env_file`), and consumer node. For scalar
environment delivery it also carries the target environment variable name. For
env-file delivery it carries an env-file identity or target within the runtime
environment contract, but not individual key/value entries unless a later
profile explicitly parses them.

Generated output sensitivity and environment value classification stay
separate. `ResourceSensitivity.SECRET` describes artifact handling. A generated
runtime value is not an `operator_secret`; `operator_secret` remains reserved
for out-of-SDL operator-controlled material. A generated secret environment
binding should omit raw `value`, use the existing explicit-redaction discipline,
and identify the generated-artifact source by reference.

## Canonical Incumbents

The implementation must extend these existing authorities, not create parallel
ones:

- SDL model admission: `SDLModel(extra="forbid")`, `PortableIdentifier`,
  `RuntimeEnvironmentVariable`, `RuntimeEnvironmentValueClassification`,
  `RuntimeEnvironmentVariableProvenance`, `GeneratedArtifact`,
  `GeneratedArtifactOutput`, `GeneratedArtifactConsumer`,
  `ResourceSensitivity`, and the existing generated-output and mount-path
  validators.
- Semantic validation: `SemanticValidator._verify_stateful_resources()`,
  `stateful_resource_reference_errors()`, unresolved-variable validation,
  module composition and namespacing for stateful refs, and duplicate runtime
  environment name validation.
- Compilation and planning: `_stateful_spec()`,
  `_compile_generated_artifacts()`, `GeneratedArtifactRuntime`,
  `RuntimeConfiguration.environment`, `CompiledRealizationRequirement` for both
  `generated-artifact` and `runtime-environment`, `resource_payload()`,
  `_collect_resources()`, and the existing dependency, refresh, reconciliation,
  and reverse-delete utilities.
- Capability and admission: `ProvisionerCapabilities`,
  `ProvisionerCapabilitiesModel`, backend-manifest v2 rendering/restoration,
  `_validate_artifact_and_volume_support()`,
  `generated_artifact_payload_diagnostic()`,
  `_stateful_submission_diagnostic()`, and direct control-plane submission
  checks.
- Realization and observation: `project_environment()`,
  `validate_environment_observation()`, `sanitize_realization_snapshot()`,
  `realization_payloads_match()`, `realization_disclosure()`,
  `runtime.backend-contract-invalid`, `Diagnostic`, `ApplyResult`,
  `RuntimeSnapshot`, `SnapshotEntry`, and `RealizationProvenanceEntry`.
- Persistence and API: `RuntimeManager`, `_call_backend_apply()`,
  `ControlPlaneSecurityConfig`, control-plane auth roles, request-size guards,
  idempotency, audit records, and `LocalControlPlaneStore` atomic JSON writes.
- Contract publication: `schema_bundle()`, `contracts/schemas/`,
  `contracts/schema-publication-manifest.json`,
  `contracts/schema-publication/entries/`, generated-schema parity checks, SDL
  lineage/reference docs, and the release-please workflow.

## Security And Validation Gates

1. **Source and model shape.** YAML/source guards, closed Pydantic models,
   identifier validation, enum parsing, duplicate environment names, and
   generated-artifact output uniqueness must all run before compilation. Error
   messages name fields, refs, and output names, not generated values.
2. **Secret-handling.** `enforce_observed_value_redaction()` remains the
   shared raw-value gate. Generated secret environment values must not be
   serialized into SDL, plans, snapshots, diagnostics, audit events, or HTTP
   envelopes. A `value_from` style reference is not a secret-reference resolver
   and must not read operator environment variables.
3. **Reference and entitlement.** The generated artifact reference must resolve
   unambiguously, the output must exist, and `producer_private` outputs must not
   be consumed by environment or env-file delivery. Output names remain
   artifact-local identifiers, not global declaration symbols.
4. **Runtime environment projection.** The `runtime-environment` realization
   concern must compare value-from bindings through the existing value-free
   projection and commitment machinery. Returned observations may disclose
   presence or commitment metadata, never generated bytes.
5. **Planner and direct submission.** Planner-produced and externally submitted
   `generated-artifact` and node payloads must share the same model-backed
   admission helpers. The generic HTTP plan payload dictionary is not sufficient
   validation.
6. **Capability.** `supports_generated_artifacts` and
   `supported_generated_artifact_kinds` are necessary but not enough. Add one
   capability seam for generated-artifact consumer delivery modes so a backend
   can claim mount delivery without falsely claiming environment or env-file
   injection.
7. **Realization honesty.** Exact generated-artifact payloads and exact
   runtime-environment payloads must both pass SEM-218. Dropping a binding,
   changing an output ref, injecting a different variable name, or silently
   converting env-file delivery into a mount is an exactness failure.
8. **Lifecycle.** Runtime-generated values may become available only after a
   producer service boots. The backend must have an explicit ordering,
   restart, or reload behavior for consumers that need the value before process
   start. A dependency edge is not implied by a consumer ref.
9. **Host and OS exposure.** Environment variables and env files can be exposed
   through process inspection, container metadata, service managers, crash
   dumps, logs, and backup paths. Materialization must avoid shell text, process
   argv, stdout/stderr, diagnostics, audit details, world-readable files, and
   broad host-level environment propagation.
10. **Error envelopes.** Pydantic errors, backend exceptions, native command
    output, temporary paths, and generated values must be reduced to bounded
    `Diagnostic` records before they cross planner, runtime, HTTP, or store
    boundaries.

## Extensibility Seam

Keep the delivery mode parameterized. The immediate modes are `mount`,
`environment`, and `env_file`; future modes such as service-specific reload,
file-per-variable projection, or secret-store handoff should extend the same
delivery-mode vocabulary and capability set. They must not become new top-level
sections, backend-specific `constraints` strings, per-generator booleans, or
output-name conventions.

The env-file path needs a closed profile if RAES later wants to parse, validate,
or compare the file's individual variables. Until then, an env file is an
opaque generated artifact output delivered as one runtime environment input.

## Gotchas And Anti-Patterns

- Do not model generated runtime secrets as `operator_secret` or
  `SecretReferenceId`.
- Do not put raw generated values into `value`, `source`, `provenance`,
  snapshots, operation records, diagnostics, audit details, logs, or examples.
- Do not require authors to declare the same binding in two places or reconcile
  contradictory copies.
- Do not infer an environment variable name from output name or output path.
- Do not treat env-file delivery as a normal read-only mount if the process
  environment semantics matter.
- Do not let `producer_private`, `sensitivity: secret`, or omitted
  `selected_outputs` carry entitlement meanings they do not already have.
- Do not add a second reference resolver, schema generator, realization gate,
  capability registry, exception hierarchy, persistence store, or logger.
- Do not satisfy the issue with a TechVault-only script, cloud-init fragment,
  Docker Compose extension, manual post-boot command, or provider-native secret
  store.

## Non-Goals

- No generated secret bytes in portable SDL or contract payloads.
- No new operator secret lookup mechanism or ambient environment-variable
  resolver.
- No real Cortex/TheHive bootstrap implementation in the SDL contract change.
- No service-materialization profile for Cortex organizations, users, or API
  keys unless a separate issue defines that native control contract.
- No change to account credentials, application authorization posture, SSH
  server configuration, content placement, or persistent-volume semantics.
- No lifecycle scheduler, rotation, revocation, recovery, backup, or secret
  store design beyond declaring how a generated artifact output is consumed.
