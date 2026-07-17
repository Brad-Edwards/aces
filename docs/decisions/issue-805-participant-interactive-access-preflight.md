# Issue 805 Participant Interactive Access Preflight

Date: 2026-07-15

Issue: #805. Requirement: DSL-117.

This note records the repository-wide architecture boundary for authored
participant interactive access. It is guidance only: it does not implement the
SDL change, a portal broker, backend realization, or an implementation plan.

## Binding Decisions

Interactive access belongs on the existing role-neutral participant-authoring
surface from ADR-020 and ADR-022:

```yaml
agents:
  operator:
    entity: blue-team
    starting_accounts: [workstation-user]
    interactive_access:
      primary-console:
        target_ref: workstation
        channel: rdp
        account_ref: workstation-user
```

`Agent.interactive_access` is an optional mapping keyed by a portable,
participant-local declaration id and defaults to empty. Each value is a closed
nested SDL model with exactly:

- required `target_ref`, resolving to one declared VM node;
- required `channel`, from a closed language vocabulary whose initial terms are
  exactly `ssh` and `rdp`;
- optional `account_ref`, resolving to one authored top-level account.

Absence means that the participant has no authored interactive-access endpoint.
No OS, role, image, service, port, account, credential, action, or backend fact
may create an implicit entry.

If `account_ref` is present, the account must belong to the same resolved VM and
must already occur in that participant's `starting_accounts`. The endpoint
therefore composes a route/channel with existing participant access authority;
it does not create a second account-grant mechanism. If it is absent, a consumer
must not select an account by inspecting `starting_accounts`, account count,
username, authentication method, or node contents.

The declaration key supplies stable local identity; the endpoint uniqueness
key is `(resolved node, concrete channel)` within one participant. Duplicate
endpoint keys are invalid even when declaration ids, raw reference spellings,
or `account_ref` values differ. Account choice is endpoint data, not endpoint
identity. Mapping order has no priority, fallback, or failover meaning.
Uniqueness and relational checks run again after variable substitution so a
placeholder cannot conceal a duplicate or mismatched account. Different
participants may declare the same endpoint independently.

`channel`, `target_ref`, and `account_ref` use the existing whole-field
variable rules. The authoring contract may retain a declared `${var}` token;
the instantiated contracts admit only a concrete `ssh` or `rdp` channel and
concrete resolvable references. Do not add interpolation, environment lookup,
or a second binding syntax.

## Existing Authority And Incumbents

- ADR-001 keeps authored SDL backend-agnostic. ADR-020 places participant
  framing on `agents`; ADR-022 keeps that surface role-neutral. Do not create a
  parallel `participants`, `users`, `operators`, or `machines` section.
- ADR-031 keeps SSH daemon policy under node runtime, and ADR-043 keeps observed
  listeners distinct from authored access. `interactive_access` is neither
  sshd/RDP configuration nor evidence that a listener exists.
- ADR-083 keeps tool affordances and decision/exposure policies distinct. A
  `shell` affordance is not an SSH channel, and this declaration does not expose
  hidden state or authorize participant actions.
- `aces_sdl.agents.Agent`, a focused nested `SDLModel`,
  `SDLModel(extra="forbid")`, `parse_enum_or_var()`, and the existing
  non-empty/reference validation patterns are the canonical authoring shapes.
  Do not introduce a free-form endpoint map or a second parser DTO.
- `ScenarioContent` is the shared closed section carrier for normalized,
  expanded, and instantiated scenarios. The field must survive through that
  carrier; do not add phase-specific copies or an out-of-band metadata channel.
- `parse_sdl()`, source validation, module composition, `instantiate_scenario()`,
  `admit_instantiated_scenario()`, and `SemanticValidator` are the canonical
  ingress and validation sequence. Endpoint reference checks belong with the
  existing participant checks in `validator/_content_objectives.py` and must use
  the declaration index/reference rules rather than string splitting or a new
  resolver.
- `contracts/concept-authority/controlled-vocabularies-v1.json` owns portable
  terms under ADR-012. Add one closed enumeration such as
  `participant-interactive-access-channels`, governed at
  `agents.interactive_access.channel`, and keep its terms in exact parity with
  the SDL enum. The controlled-vocabulary model's governed-scope allowlist and
  authoritative valid fixture are existing shape gates; do not validate a
  second free-string vocabulary in `SemanticValidator`.
- The three hand-governed SDL schemas under `contracts/schemas/sdl/` are the
  normative machine contracts under ADR-009/061. `schema_bundle()` and
  `tools/check_generated_schemas.py` prove Python compatibility; they do not
  replace schema authority. Since `Agent` exists in all three schemas, all
  three and their publication-manifest hashes/`last_change` move together.
- `specs/sdl/references.md` and the independently maintained
  `_REFERENCE_EDGE_EXPECTATIONS` in `tools/check_sdl_catalog_parity.py` are the
  canonical reference-edge contract. Register both `target_ref` and
  `account_ref`; editor/reference completion must extend the existing
  `REFERENCE_COMPLETION_TARGETS` and declaration index rather than add an
  interactive-access-specific symbol service.
- `aces_processor.compiler.participant_behaviors`, the existing node/account
  address helpers in `compiler.alias_index`/`compiler.addresses`, and
  `ParticipantBehaviorRuntime` are the compiled participant seam. Preserve
  access entries as typed participant data containing authored refs and resolved
  addresses, and include their resolved node/account addresses in refresh
  dependencies. Do not make the opaque `agent_specs` or `spec["agent"]` dump
  the only consumer contract, and do not create a separately addressed or
  planned access resource.
- `SDLParseError` with bounded source diagnostics, `SDLValidationError`, and
  `SDLInstantiationError` are the language error hierarchy. Processor-only
  failures use the existing `Diagnostic` envelope. No endpoint-specific
  exception, logger, repository, controller, or workflow is justified.

## Cross-Cutting Gates

- **Source/parser:** retain the `sdl-yaml/v1` safe loader, UTF-8 and source-size
  limits, alias/depth/node/tag/directive limits, exact snake-case handling,
  stable mapping-key rules, and closed Pydantic models. There is no endpoint
  shorthand, legacy alias, or permissive unknown-key path.
- **Shape and concept authority:** `target_ref`/`account_ref` contain references,
  not hostnames, usernames, credentials, URLs, or arbitrary strings with
  transport meaning. `channel` accepts only the enum or a declared whole-field
  variable at authoring time. The controlled-vocabulary catalog, its governed
  scope allowlist, SDL enum, and published schemas must agree on `ssh`/`rdp`.
- **Semantic references:** the normal collect-all `SemanticValidator` pass must
  reject dangling or ambiguous refs, non-VM targets, account/node mismatch,
  accounts outside `starting_accounts`, and duplicate resolved node/channel
  pairs. It must not reject SSH on Windows, RDP on Linux, or account auth-method
  combinations by inference; backend support is not SDL validity.
- **Phase/admission:** module composition rewrites references through the
  existing namespace machinery. Instantiation removes all `${...}` tokens and
  reruns structural and semantic validation. Direct instantiated-artifact
  admission performs the same closed-schema, provenance, token, declaration,
  and semantic checks before compiler use.
- **Authentication and authorization:** the declaration is a positive scenario
  authorization input saying that this participant may be offered this
  node/channel. It is not caller authentication, a bearer-token scope, or proof
  that an HTTP/control-plane principal is that participant. A portal consumer
  must retain its own authenticated caller-to-participant binding and fail
  closed on absent or unsupported declarations; no control-plane auth surface
  changes in this issue.
- **Secrets:** the declaration carries only declaration refs and a channel. It
  carries no password, key, token, connection string, portal session, host,
  username, or credential material. `account_ref` identifies authored account
  posture; it is not a credential lookup or authorization to serialize a
  secret.
- **Configuration and environment binding:** this change adds no backend config,
  provider setting, environment variable, CLI flag, or config dictionary.
  Scenario variables continue through the typed instantiation request and may
  not be resolved from ambient process environment.
- **Host/OS exposure:** parsing and compilation add no listener, route, firewall
  rule, service port, daemon setting, subprocess, shell command, or process
  argument. A downstream broker may map a validated channel to backend-owned
  connection mechanics, but hostnames, URLs, ports, private keys, tokens, and
  credentials must not enter SDL or process argv.
- **Error envelopes and observability:** parser errors remain bounded,
  source-anchored diagnostics without raw Pydantic input; semantic failures
  remain collected language errors. Do not echo full SDL documents, account
  details, generated portal URLs, native exceptions, or downstream credentials
  into diagnostics, logs, audit details, or API errors.
- **Persistence and realization:** the declaration is preserved in the SDL,
  instantiated snapshot, and typed compiled participant projection. It adds no
  database, store, cache, audit stream, plan operation, runtime status field, or
  realization-support claim. Carriage proves authored intent only, not that a
  broker, daemon, listener, ACL, or usable login exists.

## Extension Seam

The seam is the keyed nested endpoint record plus the closed channel vocabulary.
Adding the next portable channel requires one governed term, enum/schema parity,
and compatibility review; it must not require a new participant section or a
backend field. Adding backend support belongs in backend capability and broker
code outside this language issue.

Do not add `other`, `custom`, an `x-*` escape hatch, URL schemes, arbitrary
ports, or provider options. If a future portable requirement needs explicit
priority, temporal availability, account selection alternatives, or a
protocol-neutral broker constraint, it should add a typed optional field with
defined semantics to the nested record. It must not reinterpret mapping order,
`description`, `services`, or account metadata.

## Gotchas And Anti-Patterns

- Do not infer endpoints from OS family, node role/image, service ports, runtime
  listeners, SSH server configuration, accounts, credentials, ACLs, actions,
  tool affordances, or participant implementation capabilities.
- Do not infer an account when `account_ref` is absent, or let `account_ref`
  bypass `starting_accounts`. Do not include account in endpoint identity to
  permit conflicting duplicate routes.
- Do not require a port-22/3389 service, ACL, operating-scope entry, initial
  knowledge, action contract, runtime listener, or channel/OS compatibility as
  reciprocal validation. These are separate concepts and several are observed
  or backend-owned rather than authored access intent.
- Do not put portal URLs, hosts, ports, bastions, gateways, proxy modes,
  provider ids, instance ids, auth methods, or credential values in the SDL.
- Do not make mapping order meaningful, silently deduplicate conflicting
  declarations, resolve ambiguous bare refs by first match, or discover
  qualified ownership with `split`/longest-prefix heuristics.
- Do not duplicate the model across normalized/instantiated schemas, import
  `aces_contracts` into `aces_sdl` to share an enum across package boundaries,
  hand-edit compatibility wrappers under `implementations/python/src/aces/`, or
  rely on opaque compiler metadata instead of the typed participant projection.
- Do not create new exception, validation, reference-resolution, schema,
  persistence, logging, control-plane, conformance, or backend workflows.

## Non-Goals And Workflow Boundary

This issue does not implement Shifter or another portal broker; SSH/RDP daemon
configuration; service/port publication; ACL/firewall/NAT changes; credential
storage or distribution; caller authentication; backend capability negotiation;
runtime connection status; interactive session lifecycle; evidence that access
worked; or participant action/tool/exposure semantics.

The implementation remains subject to `.ground-control.yaml`,
`.gc/plan-rules.md`, `noxfile.py`, the repository-policy and
requirement-governance checks, concept-authority governance, SDL catalog parity, JSON
artifact checks, schema publication/generated-schema checks, and the full
`tools/verify_all.py` graph. No changelog fragment or project-version change is
part of this issue.
