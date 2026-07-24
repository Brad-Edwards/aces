# Issue #845 — Domain-Controller Placement Preflight

Date: 2026-07-24

Issue: #845.

Requirement: none. The issue title, body, and acceptance criteria are the
authoritative contract.

This note is architecture guidance only. It does not add a provisioning
resource, change a schema, or implement a backend operation. ADR-082 remains
the durable authority and is amended only to distinguish topology bindings
from the actionable controller placement.

## Finding and boundary

The authored contract is already complete for the requested scope:
`IdentityDomain`, `domain_controller_for`, the pure domain-topology analyzer,
and `DomainTopologyBinding` own the portable domain identity and controller
fact. The compiler already attaches that binding to node and domain-bound
account payloads, and planning/direct admission already checks the effective
topology graph. Those bindings are nevertheless context carriers. A backend
cannot distinguish "this node has controller topology" from the lifecycle
operation "establish this controller" through the closed provisioning resource
vocabulary.

Add one provisioning resource kind, `domain-controller-placement`, for that
lifecycle operation. Do not add an SDL section, a second identity-domain model,
an AD-specific top-level declaration, or a raw-command escape hatch.

The issue quotes `aces_contracts.addressing.PLAN_RESOURCE_TYPES_BY_DOMAIN`, but
the effective plan validator and published-schema generator use the separate
registry in `aces_contracts.planning`. The two copies have already drifted:
`planning` includes the newer stateful resource kinds while `addressing` does
not. `aces_contracts.planning.PLAN_RESOURCE_TYPES_BY_DOMAIN` remains the single
authority established by the contracts package split. Remove or delegate the
unused addressing copy rather than updating two allowlists or creating a third.

## Placement identity, payload, and lifecycle

Emit one placement for each normalized controller node/domain pair. Its
compiler-owned identity includes both stable identities, for example
`provision.domain-controller.<domain-id>.<node-id>`; mutable DNS, NetBIOS,
profile, account, or backend values never enter the address.

The payload is the existing typed projection:

- `target_address` identifies the controller node;
- `domain_topology` is the same `DomainTopologyBinding` carried by that node
  and has `role == "controller"`; and
- ordinary resolved-resource identity fields may remain where the existing
  `resource_payload()` projection requires them.

Do not flatten `profile`, `dns_name`, `netbios_name`, or authority identity into
a parallel placement schema. Do not pass the authored `IdentityDomain`,
relationship model, raw SDL, a Samba command, or a backend options mapping
through the plan. `authority_account_address` is logical identity, not a
password or credential handle.

The dependency graph carries the lifecycle contract:

- a controller placement orders after its target node;
- a member node orders after the selected controllers' placements, not merely
  after controller node existence;
- every domain-bound account placement, including the authority account,
  orders after every controller placement for that domain and after its own
  target node; and
- the existing reverse-delete algorithm consequently removes dependants before
  controller state and the controller node.

The controller placement must never depend on the authority account placement:
that creates the bootstrap cycle ADR-082 explicitly forbids. Keep ordering and
refresh semantics distinct; add refresh edges only where the existing
reconciliation contract requires reapplication, never as a substitute for the
required ordering edge.

Multiple controllers remain valid. The SDL has no primary-controller meaning.
The portable plan must preserve the full explicit controller set, while a
profile interpreter may apply one deterministic, versioned bootstrap-leader
policy and treat the remaining placements as additional controllers. It must
not infer leadership from operation order, node names, images, or accounts.

## Canonical incumbents to reuse

- **SDL authority and validation:** `IdentityDomain`,
  `IdentityDomainProfile`, typed domain relationships,
  `analyze_domain_topology()`, `SemanticValidator`,
  `SDLParseError`/`SDLValidationError`/`SDLInstantiationError`, safe YAML
  loading, `SDLModel(extra="forbid")`, variable instantiation, and
  post-instantiation admission. No authoring schema or validator is duplicated.
- **Compiled topology:** `DomainTopologyAnalysis`, `DomainNodeBinding`,
  `DomainTopologyBinding`, `_compiled_domain_binding()`, canonical address
  builders, `ResolvedResource`, `RuntimeModel.__post_init__`, and
  `resource_payload()`. The new placement is another resolved resource using
  the existing binding, not another domain DTO.
- **Planning and reconciliation:**
  `aces_contracts.planning.PLAN_RESOURCE_TYPES_BY_DOMAIN`,
  `require_plan_operation_identity()`, the explicit `_collect_resources()`
  table, `PlannedResource`, `ProvisionOp`, `ProvisioningPlan`, dependency-cycle
  diagnostics, topological and reverse-delete ordering, refresh propagation,
  and snapshot reconciliation.
- **Plan admission:** `domain_topology_plan_diagnostics()` and its effective
  resources plus non-`DELETE` operations plus admitted-snapshot materialization,
  called by both normal planning and
  `RuntimeControlPlane._submitted_plan_diagnostics()`. Extend this gate; do not
  add a placement-only validator or rely only on backend validation.
- **Capability truth:** `ProvisionerCapabilities.supported_domain_profiles`,
  controlled-vocabulary validation, manifest rendering/parsing,
  planner manifest diagnostics, `domain_topology_profile()`, and backend
  capability-envelope tables. A profile claim already means the provisioner
  accepts the portable controller operation; no second support boolean or
  free-form `constraints` key is warranted.
- **Realization honesty and conformance:**
  `CompiledRealizationRequirement`, `CONCERN_PAYLOAD_PATH["domain-topology"]`,
  `realization_support_diagnostics()`, `realization_disclosure()`,
  `RealizationConcern.TOPOLOGY`/`SERVICE`, the conformance resource-concern
  table, `RealizationObservation`, and existing evidence artifacts. Snapshot
  payload equality proves carrier fidelity, not successful domain promotion.
- **Runtime, persistence, and errors:** `_call_backend_diagnostics()`,
  `_call_backend_apply()`, `Diagnostic`, `ApplyResult`, `OperationReceipt`,
  `OperationStatus`, `RuntimeSnapshot`, `SnapshotEntry`,
  `ControlPlaneStore`, atomic local-store writes, and bounded audit summaries.
  No new exception hierarchy, logger, store, service, or repository is needed.
- **Contract governance:** `ProvisioningPlanModel`,
  `contracts/schemas/plans/provisioning-plan-v1.json`, `schema_bundle()`,
  `contracts/schema-publication/entries/provisioning-plan-v1.json`, schema
  constraints, contract fixtures, and generated-schema/publication parity
  checks. The published schema is hand-governed authority; changing only Python
  or only generated JSON is invalid.

## Shared admission invariants

The canonical plan analyzer must shape-check the new carrier together with the
existing node and account carriers. For the effective materialized graph it
rejects:

- a placement without a mapping-valued, valid `DomainTopologyBinding`;
- unknown binding keys, non-string scalar fields, or non-string controller
  addresses (the existing `from_mapping()` string coercion is too permissive
  for an untrusted direct-plan boundary and must be hardened in that one
  canonical parser);
- a placement whose binding is not a controller binding;
- a missing or non-node `target_address`;
- a target node whose binding differs from the placement binding;
- duplicate placements for the same controller node/domain pair;
- a controller node without its corresponding effective placement, or a
  placement without its corresponding controller node;
- a member or domain-bound account missing the required placement ordering
  dependencies;
- a profile outside the selected provisioner's
  `supported_domain_profiles`; and
- conflicting domain definitions across node, placement, account, operation,
  resource, and snapshot carriers.

Apply the same rules to compiler-produced resources, direct HTTP operations,
incremental operations completed from the admitted snapshot, and backend
validation. `DELETE` removes a carrier from effective desired state and does
not demand a profile term, but its persisted dependencies still govern reverse
deletion. Diagnostics use the existing stable `provisioning.domain-topology.*`
family, safe addresses, and domain ids; they do not echo raw payloads.

## Security and whole-path gates

1. **Source/parser gate.** Existing source-size, safe-YAML, alias,
   duplicate-key, key-normalization, and bounded Pydantic diagnostic gates run
   unchanged. The issue adds no new authored field; names remain inert data.
2. **Closed SDL shape and semantic gate.** `SDLModel(extra="forbid")`,
   profile/DNS/NetBIOS validators, declaration/reference resolution, typed
   relationships, and the collect-all domain analyzer remain the only SDL
   authorities. Compiler output is admitted only after the same semantic
   analysis passes.
3. **Instantiation/config-shape gate.** Existing typed variables,
   allowed-value constraints, substitution, unresolved-token rejection, and
   post-instantiation semantic validation apply. Do not add an SDL env binding,
   `.env` reader, CLI secret flag, or plan-only DNS-forwarder field.
4. **Compiled and wire-shape gate.** Canonical addresses, unique runtime-model
   addresses, closed plan resource types, dependency resolution/cycle checks,
   `ProvisioningPlanModel`, and the hardened shared topology parser reject
   malformed in-process and serialized carriers before dispatch.
5. **Capability/non-approximation gate.** Controlled
   `supported_domain_profiles` admission runs in planning, direct submission,
   and backend validation. The placement receives an exact
   `domain-topology` realization requirement; returned snapshots must preserve
   its binding, and operational conformance uses existing topology/service
   concerns rather than treating a copied payload as proof.
6. **HTTP/auth gate.** Submission remains behind request-size limits,
   `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer or trusted
   proxy identity, target-bound roles, idempotency fingerprints, and bounded
   audit summaries. MCP compilation/plan-inspection surfaces retain their own
   request-size and compile-pipeline gates and return bounded summaries rather
   than raw payloads. Control-plane identity is not domain authority.
7. **Secret and OS/process gate.** SDL, plan, snapshot, diagnostics, logs,
   audit, fixtures, argv, command text, and environment dumps carry no password,
   keytab, ticket, join blob, token, or credential resolver output. A backend
   profile interpreter resolves bootstrap credentials at the target boundary
   and uses fixed argv with no shell plus a private file/device/stdin channel,
   least privilege, bounded timeouts/output, redaction, and verified cleanup.
   If it cannot do so, it must not claim the profile.
8. **Persistence/read API gate.** `RuntimeSnapshot` and `ControlPlaneStore`
   persist the placement payload for authorized readback. Therefore it may
   contain only safe domain, node, account, and profile identities—not host
   paths, secret URIs, backend handles, stdout/stderr, or native configuration.
   Preserve atomic writes and existing authorization.
9. **Error-envelope gate.** Parser/semantic errors use safe field paths;
   planning/runtime failures use bounded `Diagnostic` values; backend adapters
   convert exceptions without exposing messages that may contain native
   command values; HTTP keeps its generic internal-error envelope. No raw
   payload, traceback, or subprocess output enters an error response.

`RuntimeConfiguration.dns_services` and
`Node.runtime.identity_authorities` are observed/runtime inventory surfaces,
not portable controller-bootstrap configuration. A DNS forwarder or similar
future profile input may be added only as a governed, profile-specific authored
field with validation, instantiation, schema, exactness, and publication
coverage, or as configuration-bound backend policy when it is not portable
scenario intent. It must not first appear as an ad hoc placement option.

## Extensibility seam

The seam is the existing closed `DomainTopologyBinding.profile` plus
`supported_domain_profiles` and a backend profile interpreter. The placement
identity and common payload stay stable; a future directory profile adds
governed profile-specific typed data only when its controller semantics require
it. One obvious next profile must not require a new top-level SDL section,
resource kind, capability boolean, validator, or backend DTO.

Keep controller bootstrap distinct from member join. This issue makes
controller facts actionable. It does not define a separate
`domain-member-placement`; if a backend cannot make member bindings actionable
through the existing node realization contract, that is a separately governed
expressivity change rather than a reason to overload this resource.

## Required evidence and repository workflow

Use the existing authoring/domain-topology, compiler/planner, plan-contract,
control-plane, backend-capability, SEM-218, snapshot-store, and conformance test
patterns. Evidence must cover:

- exactly one placement per controller node/domain pair, deterministic
  addresses and payload equality with the controller node binding;
- single- and multi-controller ordering, authority-account cycle avoidance,
  member/account ordering, cycle diagnostics, and reverse deletion;
- malformed direct carriers, unknown/coerced binding values, missing or
  mismatched targets, duplicates, conflicts, unsupported profiles, and
  incremental plans completed from snapshot state;
- serialized `ProvisioningPlanModel` admission and the published resource-type
  enum;
- exact placement readback/provenance plus rejection of omitted or approximated
  snapshot entries;
- backend capability and conformance agreement without widening a production
  manifest that lacks operational support; and
- bounded diagnostics, API/MCP responses, audit records, persisted snapshots,
  and fixtures containing no secret or native command material.

A plan-contract schema change updates the hand-governed schema, generated
bundle, publication entry/hash, and parity fixtures together. Follow
`.ground-control.yaml` and `.gc/plan-rules.md`; run
`tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
`tools/verify_all.py`, and the pinned nox `verify` command. Release Please owns
the version and changelog.

## Gotchas and anti-patterns

- Do not treat a controller node operation, node existence, account placement,
  SPN, package list, service unit, image, OS, runtime inventory, or copied
  snapshot payload as controller bootstrap.
- Do not reuse `account-placement` for domain creation or make
  `supports_accounts` imply a supported domain profile.
- Do not add arbitrary argv, shell fragments, provider options, secret refs,
  environment values, or backend-native state to the portable payload.
- Do not update both drifted resource-type registries, hand-edit only the
  generated schema, skip the schema-publication ledger, or introduce another
  resource vocabulary.
- Do not validate only compiler output. Direct and incremental plans must pass
  the same effective-state analyzer before backend mutation.
- Do not stringify malformed wire values, accept unknown binding keys, infer a
  missing target, or silently choose an unlisted controller.
- Do not create a dependency cycle through the authority account, rely on
  lexical operation order, or forget reverse-delete behavior.
- Do not widen production backend manifests. A backend claims
  `active_directory` only when it translates the placement, establishes
  readiness, preserves exact readback, and supplies the required evidence.
- Do not add code under `implementations/python/src/aces/`, hand-edit package
  versions or `CHANGELOG.md`, or add a new exception/logging/persistence stack.

## Non-goals

- Implementing Samba, Windows AD DS, LDAP, Kerberos, DNS, member join, trust,
  replication, SPN/account commands, credential resolution, or a backend
  profile interpreter.
- Changing the authored `identity_domains`, relationship, account, runtime
  inventory, or control-plane authentication schemas.
- Defining an authored primary controller or weakening multi-controller
  topology.
- Proving operational controller readiness from desired-state readback.
- Adding a generic command operation, provider-specific plan options, a secret
  store, a new capability family, or a new persistence service.
