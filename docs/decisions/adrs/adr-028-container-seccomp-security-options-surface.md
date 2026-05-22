# ADR-028: Container Seccomp and Security Options Surface

## Status

accepted

## Date

2026-05-22

## Context

Issue #385 requires SDL expressivity for a container runtime security fact:
the seccomp profile, and the backend-native `security_opt` posture that can
carry seccomp and adjacent Linux security options. The motivating evidence is
a Docker container with `HostConfig.SecurityOpt: ["seccomp:unconfined"]`.
That posture disables Docker's default seccomp syscall filter and materially
widens the syscall attack surface.

The repository already has nearby runtime security surfaces:

- `Node.runtime.container.privileged`
- `Node.runtime.container.namespaces`
- `Node.runtime.container.masked_paths` and `read_only_paths`
- `Node.runtime.container.device_cgroup_rules`
- `Node.runtime.linux_capabilities`

None of those fields owns seccomp profile state or arbitrary engine security
options. Treating `seccomp:unconfined` as `privileged`, a namespace mode, a
capability, a device rule, or a raw Docker inspect payload would conflate
distinct security controls and make downstream security review unreliable.

## Decision

### 1. Model seccomp posture under runtime container configuration

Seccomp and backend-native security options belong under the existing
node-scoped runtime container surface:

`Node.runtime.container`

They are observed runtime container host/security facts. They must not become
new top-level SDL sections, image build-provenance fields, infrastructure
properties, Linux capability fields, or backend-specific Docker dialects.

### 2. Preserve portable seccomp posture and native options separately

The SDL surface should preserve two related but distinct meanings:

- `seccomp_profile`: a first-class portable seccomp posture/profile value,
  such as `default`, `unconfined`, a named profile, a profile path, or a
  variable placeholder.
- `security_opt`: a list of backend-native security option strings observed
  from the runtime engine, such as `seccomp:unconfined`,
  `apparmor=profile-name`, or `no-new-privileges`.

`seccomp_profile` is the portable fact consumers can compare without parsing a
Docker option list. `security_opt` is the bounded native-option seam that
preserves adjacent engine options without pretending ACES has typed every
container security control.

When both fields are present and concrete, and `security_opt` contains a
recognized seccomp option form, the values must agree. Known Docker and
Compose spelling variants may be recognized for this consistency check, but
that parsing must not turn Docker inspect JSON into the SDL authority boundary.

### 3. Reuse existing SDL and contract gates

The implementation must reuse the repository's existing cross-cutting gates:

- `SDLModel` closed-world Pydantic validation.
- shared runtime parsing helpers such as `coerce_string_list()` and
  variable-placeholder helpers.
- parser key normalization, source-shorthand behavior, hashmap-key
  preservation, and variable-placeholder key rejection.
- `SemanticValidator` and `SDLValidationError` only if future seccomp or
  security-option facts introduce cross-reference or cross-field authoring
  semantics that do not belong in the local Pydantic model.
- `instantiate_scenario()` and `SDLInstantiationError` for substitution and
  concrete revalidation.
- `schema_bundle()`, `tools/generate_contract_schemas.py`, and
  `tools/check_generated_schemas.py`; generated schemas under
  `contracts/schemas/` must not be edited directly.
- existing runtime/control-plane diagnostics and envelopes if these facts later
  flow through snapshots, backend reports, or API responses.

No new parser, schema registry, validation framework, exception hierarchy,
logging stack, persistence mechanism, or raw backend-payload contract is
justified for this issue.

### 4. Validate shape without inventing policy claims

The model should validate portable shape and internal consistency:

- `security_opt` accepts a scalar string or list of strings through the
  existing list-coercion pattern.
- empty option entries and exact duplicate option entries should be rejected.
- `seccomp_profile` should not be inferred from absence unless the scenario
  explicitly records the posture.
- validation errors should identify the field and rule without echoing full
  backend-native payloads.

The SDL should record the observed security posture. It should not claim that
an omitted `security_opt` list proves Docker default seccomp was active, unless
the profile is explicitly recorded as such.

### 5. Keep the extensibility seam container-scoped

The extension seam remains `RuntimeContainerConfiguration`. Future typed
security controls such as AppArmor profile, SELinux label policy,
`no-new-privileges`, Landlock, or Kubernetes security context projections
should extend this container-scoped runtime security posture and, where they
overlap with `security_opt`, define consistency rules between the typed field
and the native option list.

## Security and Validation Gates

- Parser gate: hyphenated field names such as `security-opt` should normalize
  through the existing parser. Option values must remain literal strings; no
  nested hashmap preservation is needed for a list field.
- SDL model gate: closed-world validation must reject unknown fields, malformed
  list shapes, empty option strings, duplicate exact options, and concrete
  `seccomp_profile`/`security_opt` disagreement.
- Semantic validation gate: this issue should not add semantic cross-reference
  logic unless seccomp profiles become named SDL artifacts later.
- Instantiation gate: variable placeholders may stand in value fields, but not
  mapping keys; instantiated scenarios must revalidate consistency after
  substitution.
- Contract/schema gate: schema changes come from Python model sources and
  regeneration, never direct edits under `contracts/schemas/`.
- Runtime/control-plane gate: if these facts are exposed through snapshots or
  APIs, use existing `aces_processor.models.Diagnostic` and published envelope
  shapes plus existing authentication, authorization, audit, request-size,
  idempotency, and redacted error handling.
- Host/OS exposure gate: `seccomp:unconfined` is increased syscall exposure.
  It must remain visible as runtime container security posture and must not be
  normalized away as merely non-privileged.
- Secret and environment gate: this surface is not an environment-binding or
  secret-value surface. Do not store raw inspect payloads, credentials, tokens,
  or command output as security options or diagnostics.

## Guardrails

- Do not collapse seccomp posture into `privileged`; non-privileged containers
  can still be seccomp-unconfined.
- Do not use `linux_capabilities` for seccomp. Capabilities and syscall filters
  are different controls.
- Do not put seccomp or `security_opt` into `namespaces`, path masks, device
  cgroup rules, network realization, image provenance, or infrastructure.
- Do not embed raw Docker, Compose, Podman, Kubernetes, or harness inspect
  payloads into SDL as the portable model.
- Do not create duplicate schemas, parser branches, exception hierarchies, or
  logging paths for this field.
- Do not edit generated JSON schemas by hand.
- Do not treat an empty or absent `security_opt` field as proof of a secure
  default. Record `seccomp_profile` explicitly when that posture matters.

## Non-Goals

- Implementing issue #385.
- Updating `examples/scenarios/techvault.sdl.yaml`.
- Building a Docker, Compose, Podman, Kubernetes, or harness inspector.
- Defining backend provisioning behavior for seccomp profiles or security
  options.
- Defining a comprehensive Linux security module policy model.
- Changing runtime snapshot, control-plane, backend manifest, or processor
  capability contracts unless a later implementation explicitly routes these
  facts through those surfaces.

## Consequences

### Positive

- Seccomp posture becomes a first-class runtime security fact without
  overloading `privileged`.
- Adjacent backend-native security options can be preserved without making
  Docker inspect JSON normative.
- Existing SDL parsing, validation, instantiation, schema generation,
  diagnostics, and control-plane envelopes remain authoritative.

### Negative

- The model intentionally allows overlap between a typed `seccomp_profile` and
  native `security_opt` entries, so consistency validation is needed when both
  are present.
- Consumers that only understand `security_opt` may need to learn the typed
  `seccomp_profile` field for portable comparison.

### Risks

- A loose native-option list could become a dumping ground if future typed
  security controls are not promoted deliberately.
- Inferring defaults from missing data would make inventory evidence look more
  complete than it is.
- Echoing raw backend payloads in diagnostics could leak paths, labels, or
  unrelated sensitive runtime details.
