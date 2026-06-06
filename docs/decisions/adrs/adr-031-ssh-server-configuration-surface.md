# ADR-031: SSH Server Configuration Surface

## Status

accepted

## Date

2026-05-23

## Context

Issue #387 requires SDL expressivity for SSH server configuration that
materially changes a participant's login surface. The motivating APTL
TechVault `kali` container records:

- `Match User kali` with `ForceCommand /usr/local/bin/aptl-wrap-shell.sh`
- `AcceptEnv APTL_SESSION_ID APTL_RUN_ID APTL_TRACE_ID`

Those facts are not plain transport bindings. `Node.services` records
`port`/`protocol`/`name`, top-level `accounts` records curated scenario or
provisioning account resources, `runtime.local_identity` records observed local
users/groups/sudoers, `runtime.environment` records observed environment
variables and values, and `runtime.applications` records HTTP route surfaces.
None of those surfaces owns sshd policy that replaces an SSH login shell or
whitelists client-supplied environment names.

The design risk is to hide SSH server policy in a nearby but different concept:
transport services, user accounts, local identity inventory, runtime process
state, process environment values, HTTP application route inventory, or raw
`sshd_config` text.

## Decision

### 1. Model SSH server configuration under node runtime

SSH server configuration belongs under the node-scoped runtime surface as a
typed observed service configuration, for example:

`Node.runtime.ssh_servers`

Each SSH server configuration should have a stable `server_id` and an explicit
`service` reference to the owning same-node `Node.services[].name` or qualified
`nodes.<node>.services.<name>` form. It must not mutate `Node.services` or make
transport binding fields protocol-specific.

The initial SSH surface should include the participant-observable sshd policy
needed by the issue:

- global `accept_env` names/patterns
- global or scoped forced command configuration
- scoped match rules, especially user-scoped rules such as `Match User kali`
- room for adjacent sshd policy such as allow/deny users or groups and
  permitted authentication methods when observed

Use list records with stable identifiers and duplicate validators. Do not use
user names, service names, or raw directive lines as mapping keys.

### 2. Keep adjacent concepts distinct

The implementation must preserve these boundaries:

- `Node.services` remains transport-level binding and naming.
- top-level `accounts` remains the curated scenario/provisioning account
  surface. Do not require every `Match User` or `AllowUsers` entry to be a
  top-level account.
- `runtime.local_identity` remains observed local user/group/sudoers
  inventory. SSH match criteria may optionally cross-check exact local users
  when the local identity inventory is present, but wildcard/pattern criteria
  are not account records.
- `runtime.environment` records observed environment variables and classified
  values. `AcceptEnv` records only accepted client-supplied variable names or
  patterns, never session id values.
- `runtime.process`/`runtime.processes` may show that a wrapper ran in a
  session. They are evidence, not the sshd policy authority.
- `runtime.applications` remains HTTP/API/UI inventory; SSH is not an HTTP
  route surface.

### 3. Reuse existing SDL and contract gates

The new surface must reuse the repository's existing gates:

- `SDLModel` closed-world Pydantic validation and local field/model validators.
- shared parsing helpers such as `parse_bool_or_var()`,
  `parse_optional_bool_or_var()`, `absolute_path_or_var()` where a value is a
  path, `parse_runtime_enum_or_var()` for governed local enums, and
  `coerce_string_list()`.
- parser key normalization, source-shorthand behavior, hashmap-key
  preservation, and variable-placeholder key rejection.
- `SemanticValidator` and `SDLValidationError` for same-node service
  resolution and any optional local-identity consistency checks.
- `instantiate_scenario()` and `SDLInstantiationError` for substitution and
  concrete revalidation.
- `schema_bundle()`, `tools/generate_contract_schemas.py`, and
  `tools/check_generated_schemas.py`; generated schemas under
  `contracts/schemas/` must not be edited directly.
- existing `aces_processor.models.Diagnostic` and published runtime/control
  plane envelopes if SSH facts later flow through snapshots, backend reports,
  or API responses.

No new parser, schema registry, validation framework, exception hierarchy,
logging stack, persistence mechanism, or backend-specific sshd dialect is
justified for this issue.

### 4. Validate SSH policy shape without leaking secrets

The model should validate portable shape and internal consistency:

- `accept_env` entries are names or patterns, not assignments; reject empty
  entries, whitespace-bearing entries, duplicate entries, and entries
  containing `=`.
- forced-command data must have an explicit redaction path. If the command or
  arguments include secrets, bearer tokens, session ids, or operator-only
  values, the raw command must be omitted.
- when a forced command is a concrete executable path, validate it as an
  absolute path; allow explicitly modeled non-path sshd commands such as
  `internal-sftp` only through the typed command shape.
- match rule identifiers are stable symbols, not variable placeholders.
- concrete duplicate match rules for the same criteria and directive set should
  be rejected.
- validation errors should name the field and rule without echoing full backend
  configuration dumps.

### 5. Keep the extensibility seam SSH-scoped

The extension seam for this issue is the typed SSH server configuration model,
not `ServicePort`. The next likely changes are additional sshd directives:
`AllowUsers`, `DenyUsers`, `AllowGroups`, `DenyGroups`,
`AuthenticationMethods`, `PasswordAuthentication`, `PubkeyAuthentication`,
`PermitTTY`, `ChrootDirectory`, `AuthorizedKeysFile`, and richer `Match`
criteria.

Those should extend the SSH server and match-rule submodels with typed fields
and focused validators. A generic protocol-agnostic service-configuration
surface should require a separate decision after more than one protocol has a
concrete shape in the repo.

## Security and Validation Gates

- Parser gate: hyphenated field names such as `ssh-servers`, `accept-env`, and
  `force-command` should normalize through the existing parser. Prefer lists
  over native maps. Avoid nested fields named `source` unless source-shorthand
  skip rules are deliberately updated.
- SDL model gate: closed-world validation must reject unknown fields, malformed
  env-name/pattern entries, duplicate lists, non-stable identifiers, unsafe
  forced-command path shapes, and raw commands when the redaction flag is set.
- Semantic validation gate: owning service refs must resolve to a service on
  the same node. Exact user refs may be checked against
  `runtime.local_identity.users` when that inventory is present; do not force
  wildcard/pattern criteria or all SSH users into top-level `accounts`.
- Instantiation gate: variable placeholders may stand in value fields, but not
  symbol-defining server ids, match ids, or mapping keys. Instantiated
  scenarios must revalidate after substitution.
- Contract/schema gate: schema changes come from Python model sources and
  regeneration, never direct edits under `contracts/schemas/`.
- Host/OS exposure gate: `ForceCommand` changes the OS-level login result and
  may expose wrapper paths or argv. Preserve the fact as participant-visible
  SSH policy, but do not persist sensitive argv, raw sshd dumps, or runtime
  capture output.
- Environment and secret gate: `AcceptEnv` is an allowlist of environment
  names/patterns, not an environment-value surface. Do not record
  `APTL_SESSION_ID`, `APTL_RUN_ID`, `APTL_TRACE_ID`, or similar values in
  SDL examples, fixtures, diagnostics, logs, snapshots, or operation metadata.
- Runtime/control-plane gate: if these facts are surfaced through APIs or
  snapshots, reuse existing envelopes, authentication, authorization, audit,
  idempotency, request-size limits, and redacted-error handling instead of raw
  backend payloads.

## Guardrails

- Do not add SSH server configuration to `Node.services`; service ports are
  transport bindings.
- Do not add SSH server policy to top-level `accounts` or to
  `Account.auth_method`; those are account-resource facts, not daemon policy.
- Do not use `runtime.environment` for `AcceptEnv`; it does not describe
  observed environment values.
- Do not represent `ForceCommand` only as a process entry; process inventory
  is evidence, not configuration authority.
- Do not model SSH as an HTTP application route or place it under
  `runtime.applications`.
- Do not embed raw `sshd_config`, `sshd -T` output, container inspect payloads,
  session transcripts, tcpdump paths, tokens, or environment values into the
  portable SDL model.
- Do not create duplicate schemas, parser branches, exception hierarchies,
  logging paths, or persistence mechanisms.
- Do not add implementation logic under `implementations/python/src/aces/`;
  that tree is compatibility-only wrappers.
- Keep the surface inside the governed concept taxonomy. SSH server
  configuration is node-scoped runtime state under the existing
  `scenario-node` reference model; no new concept-authority catalog entry is
  needed for this issue.

## Non-Goals

- Implementing issue #387.
- Updating `examples/scenarios/techvault.sdl.yaml` or APTL inventory bundles.
- Building an `sshd_config`, `sshd -T`, Docker, Compose, Podman, Kubernetes,
  shell-wrapper, `script(1)`, or `tcpdump` discovery tool.
- Defining backend provisioning behavior for SSH server policy.
- Redesigning `Node.services`, top-level `accounts`, `runtime.local_identity`,
  `runtime.environment`, `runtime.applications`, backend manifests, runtime
  snapshots, or control-plane APIs.
- Modeling actual per-session environment values, session transcripts, packet
  captures, or participant episode provenance.

## Consequences

### Positive

- SSH login policy becomes expressible without overloading transport services,
  account resources, environment values, process inventory, or HTTP route
  surfaces.
- Existing SDL parsing, validation, instantiation, schema generation,
  diagnostics, concept authority, and control-plane boundaries remain
  authoritative.
- APTL TechVault can record the wrapper shell and accepted session identifier
  names as participant-observable SSH policy without leaking session values.

### Negative

- The runtime surface gains another protocol-specific optional submodel.
- Consumers that only inspect `Node.services` must also read runtime SSH
  configuration to understand what an SSH login actually produces.

### Risks

- A generic free-form service-config dictionary would quickly become a raw
  backend-payload dumping ground.
- Extending `ServicePort` would make transport binding and server policy hard
  to reason about independently.
- Recording raw forced-command argv or session environment values could leak
  secrets into fixtures, generated schemas, diagnostics, logs, or snapshots.
