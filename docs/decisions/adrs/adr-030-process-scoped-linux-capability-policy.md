# ADR-030: Process-Scoped Linux Capability Policy

## Status

accepted

## Date

2026-05-23

## Context

Issue #386 requires SDL expressivity for a runtime container whose Linux
capability posture differs between the container/init process and a descendant
process subtree. The motivating case is a container that keeps
`CAP_AUDIT_CONTROL` available to the root entrypoint long enough to install
audit rules, then starts `sshd` through `capsh --drop=cap_audit_control` so
the interactive participant shell cannot remove the audit trail.

The repository already has nearby runtime surfaces:

- `Node.runtime.linux_capabilities`, modeled by `RuntimeCapabilityPolicy`, for
  observed node/container capability policy
- `Node.runtime.process` and `Node.runtime.processes`, modeled by
  `RuntimeProcessIdentity`, for observed process identity and process tree
  facts
- `Node.runtime.container`, modeled by `RuntimeContainerConfiguration`, for
  container host/security configuration such as privileged mode, seccomp,
  devices, namespaces, entrypoint, and command
- `Node.runtime.local_identity`, modeled by `RuntimeLocalIdentityInventory`,
  for local users, groups, and sudo policy

Flattening the entrypoint capability set and the `sshd` subtree capability set
into one `required` / `effective` / `add` / `drop` list loses the security
property the inventory needs to express. Moving capability lists onto process
identity records would create the opposite problem: process identity would own
capability policy semantics and each consumer would need to rediscover how
container-wide and process-scoped policy combine.

## Decision

### 1. Keep capability semantics under `RuntimeCapabilityPolicy`

Per-process and per-subtree capability facts belong under
`Node.runtime.linux_capabilities`, not as capability fields on
`RuntimeProcessIdentity`, not in `RuntimeContainerConfiguration`, and not in a
new top-level SDL section.

The implementation should extend `RuntimeCapabilityPolicy` with a small list
of scoped override records, for example `process_overrides`. Each record
describes the subject process or process subtree and its scoped capability
posture. The existing container-wide fields keep their current meaning as the
node/container capability baseline; they must not be reinterpreted as a merged
or lowest-common-denominator effective set.

### 2. Treat process identity as selector and evidence, not policy owner

Scoped capability records may refer to observed process facts such as process
name, PID, parent PID, role, user, command, or description when those facts are
available. Those selectors are evidence/attachment points for the scoped
policy. They must not make `RuntimeProcessIdentity` responsible for Linux
capability validation or inheritance semantics.

At least one concrete selector or descriptive subject should identify the
override. For a subtree claim, the scope must say that descendants inherit the
drop or effective set; do not make consumers infer subtree semantics from an
`sshd` process name or parent PID alone.

### 3. Reuse the existing capability normalization and SDL gates

Scoped capability lists must reuse the existing capability-name normalization:
trim, uppercase, hyphen-to-underscore, require `CAP_*`, allow full `${var}`
placeholders, and reject duplicates in each list.

The implementation must reuse:

- `SDLModel` closed-world Pydantic validation and local field/model validators
- shared runtime parsing helpers such as `coerce_string_list()`,
  `parse_int_or_var()`, `parse_bool_or_var()`, and
  `parse_runtime_enum_or_var()`
- parser key normalization, hashmap-key preservation, source-shorthand skip
  rules, and variable-placeholder key rejection
- `SemanticValidator` and `SDLValidationError` only for cross-reference checks
  that cannot live in the local Pydantic model
- `instantiate_scenario()` and `SDLInstantiationError` for substitution and
  concrete revalidation
- `schema_bundle()`, `tools/generate_contract_schemas.py`, and
  `tools/check_generated_schemas.py`; generated schemas under
  `contracts/schemas/` must not be edited directly
- existing `aces_processor.models.Diagnostic`, runtime snapshot envelopes,
  operation envelopes, control-plane security, audit, idempotency,
  request-size, persistence, and redacted-error handling if these facts later
  flow through processor/runtime APIs

No new parser, schema registry, validation framework, exception hierarchy,
logging stack, persistence mechanism, or backend-native capability dialect is
justified for this issue.

### 4. Model observed security posture, not an inspector transcript

The SDL surface should capture the portable security fact that one subject
retains or drops capabilities relative to the container baseline. It should not
embed raw `capsh`, `/proc/*/status`, Docker inspect, Compose, Podman, or
Kubernetes payloads as the portable contract.

Evidence such as `grep Cap /proc/1/status` versus `grep Cap /proc/self/status`
may motivate the authored values, but the portable model remains structured
capability names and scoped subject data. Raw command output, argv, usernames,
paths, or backend payloads must not be echoed in validation errors or
diagnostics.

### 5. Keep the extensibility seam capability-scoped

The extension seam is the scoped capability override record under
`RuntimeCapabilityPolicy`. Future variants such as distinguishing effective,
permitted, inheritable, bounding, and ambient capability sets; file
capabilities; alternate process selectors; or evidence references should
extend that scoped record rather than adding parallel process, container, or
snapshot-only capability schemas.

## Security and Validation Gates

- Parser gate: hyphenated authoring keys such as `process-overrides` must
  normalize through the existing parser; no new native-keyed map is needed for
  the initial surface.
- SDL model gate: scoped records must be closed-world models; capability lists
  must reuse the canonical normalization and duplicate checks; process IDs must
  reuse positive integer-or-variable parsing; subtree/process scope values must
  be explicit and enum-like.
- Semantic validation gate: only add semantic checks if an override references
  named entries in `runtime.processes`; do not introduce a second semantic
  validation path.
- Instantiation gate: variable placeholders may stand in value fields, but not
  symbol-defining mapping keys. Instantiated scenarios must revalidate scoped
  capability names and scope values after substitution.
- Contract/schema gate: schema changes come from Python model sources and
  regeneration, never direct edits under `contracts/schemas/`.
- Runtime/control-plane gate: if scoped capability facts are surfaced through
  snapshots or APIs, use the existing runtime snapshot and operation envelopes,
  `Diagnostic` shape, authentication, authorization, audit, idempotency,
  request-size, persistence, and redacted-error behavior.
- Host/OS exposure gate: per-subtree drops are security-relevant least
  privilege facts. Do not flatten them away or treat the interactive shell's
  missing capability as proof that the entrypoint lacked it.
- Secret and argv gate: this surface is not an environment-binding or secret
  surface. Do not persist bearer tokens, sudo passwords, raw command output,
  or sensitive argv values in capability subjects, examples, diagnostics,
  fixtures, snapshots, logs, or operation metadata.

## Guardrails

- Do not place Linux capability lists directly on `RuntimeProcessIdentity`.
  Process identity records can identify subjects; capability policy owns
  capability semantics.
- Do not collapse process-scoped drops into the container-wide `drop` field.
  That would say the container never had the capability.
- Do not move this fact into `runtime.container.privileged`, seccomp,
  security options, namespaces, device rules, image provenance, local identity,
  sudo policy, backend manifests, or processor capability declarations.
- Do not infer subtree scope from process names, command text, or parent PID
  without an explicit scoped record.
- Do not store raw Linux hexadecimal capability masks as the primary portable
  model. If raw masks are ever needed as evidence, add an explicitly redacted
  evidence/reference path.
- Do not add implementation logic under `implementations/python/src/aces/`;
  that tree is compatibility-only wrappers.

## Non-Goals

- Implementing issue #386.
- Updating APTL or TechVault inventory bundles.
- Building a Docker, Compose, Podman, Kubernetes, `capsh`, or `/proc`
  inspector.
- Defining backend provisioning behavior for process-scoped capability drops.
- Modeling the full Linux capability algebra beyond the expressivity needed
  for observed per-process or per-subtree runtime posture.
- Changing runtime snapshot, control-plane, backend manifest, or processor
  capability contracts unless a later implementation explicitly routes these
  facts through those surfaces.

## Consequences

### Positive

- Container-wide capability posture and descendant process capability posture
  stay distinguishable.
- Process inventory remains reusable evidence instead of becoming a second
  capability-policy schema.
- Existing SDL parsing, validation, instantiation, schema generation,
  diagnostics, and runtime/control-plane boundaries remain authoritative.

### Negative

- The capability policy surface gains a nested scoped-record concept instead
  of staying as four flat lists.
- Some inventories may intentionally record related process facts in both
  `runtime.processes` and `runtime.linux_capabilities.process_overrides`, with
  different meanings.

### Risks

- Weak selector validation could make scoped records ambiguous if authors do
  not identify the process or subtree clearly.
- Overloading the current `effective` or `drop` fields would silently erase the
  least-privilege distinction this issue exists to preserve.
- Capturing raw `/proc` output or argv without redaction could leak unrelated
  runtime details through examples, diagnostics, logs, or snapshots.
