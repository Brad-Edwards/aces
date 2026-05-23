# ADR-027: Container Init/Reaper Runtime Surface

## Status

accepted

## Date

2026-05-22

## Context

Issue #384 requires SDL expressivity for a container that runs under a
backend-injected init/PID-1 reaper process, such as Docker Compose
`init: true` causing PID 1 to be `/sbin/docker-init`. That fact changes the
participant-observable process tree and child-reaping semantics. It is also a
backend-authored runtime configuration fact, not only an observed process.

The repository already has adjacent surfaces:

- `Node.runtime.container` records observed host/container configuration,
  namespace/security facts, entrypoint, command, logging, devices, DNS, and
  related container runtime state.
- `Node.runtime.process` and `Node.runtime.processes` record observed process
  identities and process sets.
- `runtime.container.runtime_name` records the OCI runtime name, such as
  `runc`.
- `source.build.config.entrypoint` and `source.build.config.command` record
  image-default configuration, distinct from runtime-effective state.
- `runtime.operational_policy.restart` records orchestrator restart/resource
  policy, not in-container process supervision.

The design risk is to express a backend-injected PID-1 reaper by overloading
one of those nearby concepts and thereby conflate OCI runtime identity, image
defaults, effective entrypoint/command, observed process inventory, restart
policy, and backend runtime configuration.

## Decision

### 1. Model the init/reaper as container runtime configuration

A backend-injected init/PID-1 reaper belongs under
`RuntimeContainerConfiguration`, the existing node-scoped surface for observed
container runtime configuration. It must not be modeled as a new top-level SDL
section, as image build provenance, or as a mutation of declared services or
infrastructure.

Prefer a small typed descriptor such as `init_process` over a Docker-specific
field name. The descriptor should keep these facts separate when known:

- whether the backend init/reaper is enabled
- the init/reaper implementation or executable path
- whether child reaping is part of the intended semantics
- optional bounded command/argv evidence, with explicit redaction behavior if
  raw arguments could expose sensitive data

`runtime.process` and `runtime.processes` may also record the observed PID-1
process and children. That is complementary evidence, not the authority for
the authored/effective container init setting.

### 2. Keep adjacent concepts distinct

The implementation must preserve these boundaries:

- `runtime_name` remains the OCI runtime name. It must not be overloaded to
  mean Docker's `init` flag or the PID-1 executable.
- `entrypoint` and `command` remain runtime-effective application launch
  values. A backend-injected init wrapper may explain why PID 1 differs from
  the entrypoint, but it must not rewrite image-default or runtime-effective
  command semantics.
- `RuntimeProcessRole.SUPERVISOR` remains an observed process role. Do not
  make every PID-1 reaper a supervisor role, and do not add process-reference
  target semantics unless a later decision introduces them.
- `runtime.operational_policy.restart` remains orchestrator lifecycle policy,
  not in-container child reaping.

### 3. Reuse existing SDL and contract gates

The new surface must reuse the repository's existing gates:

- `SDLModel` closed-world Pydantic validation and local field/model validators.
- shared parsing helpers such as `parse_bool_or_var()`,
  `parse_optional_bool_or_var()`, `absolute_path_or_var()`, and
  `coerce_string_list()`.
- parser key normalization, hashmap-key preservation rules, source-shorthand
  behavior, and variable-placeholder key rejection.
- `SemanticValidator` and `SDLValidationError` if a future implementation adds
  cross-field or cross-reference semantics; the initial init/reaper fact should
  not need a new semantic-validation subsystem.
- `instantiate_scenario()` and `SDLInstantiationError` for substitution and
  concrete revalidation.
- `schema_bundle()`, `tools/generate_contract_schemas.py`, and
  `tools/check_generated_schemas.py`; generated schemas under
  `contracts/schemas/` must not be edited directly.
- existing processor diagnostics and runtime/control-plane envelopes if these
  facts later flow through backend reports or runtime snapshots.

No new parser, schema registry, validation framework, exception hierarchy,
logging stack, persistence mechanism, or backend-specific SDL dialect is
justified for this issue.

## Security and Validation Gates

- Parser gate: `init-process` should normalize to `init_process`; no new
  native-keyed maps or nested `source` fields are needed for the initial
  surface.
- SDL model gate: boolean-like fields must use the existing bool-or-variable
  helpers; executable paths, when present, must use the existing absolute-path
  validator; command evidence must normalize with existing string-list helpers.
- Instantiation gate: variable placeholders may stand in value fields, but not
  symbol-defining mapping keys. Instantiated scenarios must revalidate after
  substitution.
- Contract/schema gate: schema changes come from Python model sources and
  regeneration, never direct edits under `contracts/schemas/`.
- Host/OS exposure gate: `/proc/1/cmdline`, process argv, and backend inspect
  payloads can contain tokens or operator-only arguments. Do not persist or log
  raw argv unless the model includes redaction semantics and the value is safe
  for examples, diagnostics, generated schemas, logs, and snapshots.
- Error-envelope gate: parsing and validation failures must use existing SDL
  parse/validation errors. If surfaced through runtime/control-plane APIs,
  preserve existing authentication, authorization, audit, idempotency, request
  size, and redacted-error behavior instead of returning raw backend payloads.

## Guardrails

- Do not add a Docker-specific top-level field such as `docker_init`; Docker is
  one backend source of this observed fact, not the SDL authority boundary.
- Do not represent the init flag only by adding `docker-init` to
  `runtime.processes`; process inventory does not carry backend configuration
  intent.
- Do not treat the init/reaper as a service, participant, declared objective
  target, or infrastructure dependency.
- Do not infer child-reaping semantics solely from a process name. Record the
  reaper semantic as explicit data when known, and leave it unknown otherwise.
- Do not introduce raw Docker Compose or Docker inspect JSON into SDL.
- Do not add implementation logic under `implementations/python/src/aces/`;
  that tree is compatibility-only wrappers.

## Non-Goals

- Implementing issue #384.
- Updating `examples/scenarios/techvault.sdl.yaml` or APTL inventory bundles.
- Building a Docker, Compose, Podman, Kubernetes, or `/proc` inspector.
- Redesigning `RuntimeProcessIdentity`, process roles, source/image build
  provenance, restart policy, backend manifests, runtime snapshots, or
  control-plane APIs.

## Consequences

### Positive

- Backend init/reaper configuration, observed PID-1 process identity, image
  defaults, OCI runtime identity, and restart policy stay distinguishable.
- Existing SDL parsing, validation, instantiation, schema generation,
  diagnostics, and control-plane boundaries remain authoritative.
- Future runtimes can represent non-Docker init/reaper variants without adding
  a second schema or baking Docker Compose syntax into SDL.

### Negative

- The runtime container surface gains another optional submodel for a fact that
  is often represented as a single backend boolean.
- Implementations that also record process inventory may intentionally record
  related evidence in both `runtime.container.init_process` and
  `runtime.processes`, with different meanings.

### Risks

- A flat boolean-only field would be easy to author but would not preserve the
  distinction between enabled state, observed executable, and child-reaping
  semantics.
- Capturing raw PID-1 argv without redaction could leak secrets in fixtures,
  diagnostics, logs, or snapshots.
- Overloading `runtime_name`, `entrypoint`, `command`, or process roles would
  make downstream runtime and security reasoning ambiguous.
