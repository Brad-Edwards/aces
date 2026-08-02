# Issue 50 Libvirt And Workflow Package Split Preflight

Date: 2026-08-01

Issue: #50.

Requirement: none. The GitHub issue is the delivery contract. This note records
architecture guardrails only; it does not implement the split, drain the
oversized allowlist, alter tests, or add release content.

## Binding Decisions

- The four live targets are
  `raes_backend_libvirt.drivers.libvirt` (555 lines),
  `raes_backend_libvirt.realization` (571 lines),
  `raes_backend_libvirt.techvault_native` (563 lines), and
  `raes_contracts.workflow` (688 lines). Each becomes a same-named package with
  a thin `__init__.py`; every Python file in the replacement packages,
  including each facade, must remain at or below ADR-015's 500-line cap.
- Child modules are implementation details. Existing callers continue to use
  the four facade paths, and no absolute or relative external import line that
  targets those paths changes.
- This is an atomic file-to-package conversion. A target `.py` and same-named
  package must never coexist, even transiently in the submitted tree.
- Remove only the four deleted paths from
  `tools/policy/oversized_allowlist.yaml`. The fixed historical set in
  `tools/policy/repo_policy.py` remains unchanged.
- Release-please owns `CHANGELOG.md`. Although the issue asks for a changelog
  entry, `.gc/plan-rules.md` and `docs/DEVELOPMENT_WORKFLOW.md` prohibit manual
  edits and fragments. Leave `CHANGELOG.md` untouched and use a
  non-behavior-changing Conventional Commit / PR title such as `refactor:`.
- No new ADR is required. ADR-015 already decides the package split and size
  gate; ADR-036 already decides DTO, processor, runtime, and backend ownership.

## Architecture Boundaries

### Generic libvirt driver

Keep `LibvirtDeploymentDriver` as one concrete driver, not a controller plus a
new service/repository hierarchy. Internal ownership can follow the existing
call graph: native identity/lookup/stop semantics, driver realization and
teardown, and small connection/name/diagnostic helpers. Existing XML and seed
owners remain `drivers._libvirt_xml`, `drivers.seed`, and `cloudinit`; do not
copy them into the package.

The split must preserve the security-relevant distinction between `_lookup()`
on define/convergence paths and `_find_native()` on teardown paths, the stable
libvirt error-code classification, deterministic per-address UUIDs, nwfilter
owner UUIDs, ownership-conflict refusal, stop-before-undefine order,
created-only rollback, and verified fail-closed teardown. Do not turn native
absence, permission failure, connection failure, and foreign-name collision
into one generic lookup result.

### Pure plan realization

Keep `interpret_provisioning_plan()` pure and preserve its current dependency
direction: typed plan/capability DTOs and payload projections feed network/node
spec construction, placement/cloud-init aggregation, ACL realization, and
ordered diagnostics. Driver calls, filesystem access, host inspection, and
snapshot persistence do not belong in this package.

The existing concepts stay distinct: capability-envelope admission is not
payload-shape admission; node/network specs are not portable plan DTOs;
placement-to-cloud-init translation is not TechVault appliance admission; and
`Realization.placement_targets` is a refresh/reconciliation aid, not a second
planner or persistence ledger. Preserve resource sorting, diagnostic order,
placement binding behavior, OS-dialect routing, path-component sanitization,
password locking, argv-list `runcmd`, and exact default/coercion behavior.

### TechVault native driver

Keep `TechVaultNativeLibvirtDriver` as the concrete lifecycle coordinator over
the existing `techvault_*`, `_techvault_native_*`, envelope, appliance,
observation, and probe modules. Do not split the class into mixins, create a
second native lifecycle service, or move low-level logic back out of its
current canonical sibling modules merely to populate the new package.

Preserve the stage order: envelope/spec admission before host mutation;
network definition/readback before domain definition/readback; daemon
observation validation before the optional guest stage; evidence binding before
success; ownership-checked rollback on every failed later stage; and snapshot
publication only after all gates pass. The subclass hooks
`_admission_diagnostics`, `_build_matrix`, `_render_domain_xml`, `_guest_stage`,
`destroy`, and `_cleanup_artifacts`, plus the test-patched `_material_binding`
method seam, must keep their method-resolution and override behavior for
`GuestCertifiedLibvirtDriver`. If the class module needs headroom, extract only
a narrow pure helper behind the same method seam; do not introduce a framework.

### Workflow contracts

Keep one dependency direction inside `raes_contracts.workflow`: workflow enums
and attempt provenance; result/execution contract parsing and validation;
history and execution-state payload normalization/validation; then the facade.
Child modules import exact owners and never import the facade, avoiding
partially initialized package cycles.

These dataclasses are normalized runtime/backend DTOs. They are not the
normative Pydantic publication models in
`raes_contracts.contracts.execution_state`, and neither set replaces or wraps
the other. `raes.semantics.workflow.WorkflowStepSemanticContract` and
`validate_workflow_step_result()` remain the SDL-semantic authorities. Retain
`raes_contracts._validation` as the shared primitive validator set. Do not
duplicate schemas, enum coercion, semantic checks, or exception types in child
modules.

Preserve dataclass field order/defaults, enum identity, mutable-versus-immutable
field behavior, `from_mapping()` / `from_payload()` coercions, `to_payload()`
shapes, `__post_init__` validation order, exact `TypeError`/`ValueError`
conditions and text, and mapping/list iteration order. In particular, do not
"tighten" iterable handling, filtered compensation-failure parsing, empty
details fallback, timeout coercion, or the currently unvalidated cancellation
request during this refactor.

## Facade Compatibility Inventory

`raes_contracts.workflow.__all__` remains the exact ordered 13-name tuple now
declared by the module. Re-export the same objects so
`raes_processor.models` continues to expose object-identical neutral DTOs.

`raes_backend_libvirt.techvault_native.__all__` remains the exact ordered
seven-name list now declared by the module. The facade must additionally retain
`DriverResult` and `_artifact_token`, which
`guest_certified_driver.py` imports from that path even though they are absent
from `__all__`.

The other two modules currently declare no `__all__`; do not add a restrictive
one that changes star-import behavior. Preserve at least every observed facade
seam:

- `drivers.libvirt`: `LibvirtDeploymentDriver`, `Connector`, `_error_code`,
  `_existing_uuid`, `_raes_uuid`, and `_filter_owner_uuid`;
- `realization`: `Realization`, `interpret_provisioning_plan`, `_image_ref`,
  `_infrastructure_spec`, `_memory_mib`, `_node_resources`, `_resource_name`,
  `_services`, and `_vcpus`.

The issue's absolute-import grep does not find the backend's relative imports.
Those are compatibility consumers too: `target.py`, `provisioner.py`,
`techvault_lifecycle.py`, `techvault_matrix.py`,
`techvault_plan_admission.py`, `_techvault_native_ops.py`,
`guest_certified_driver.py`, and the backend root `__init__.py` must keep their
current facade imports unchanged.

Use explicit re-exports, not wildcard imports, dynamic `__getattr__`, import
scanning, or registration side effects. Do not rewrite class/function
`__module__` metadata or add pickle shims without a demonstrated compatibility
contract. Preserve the Sphinx target `raes_contracts.workflow` and the public
prefix `raes_backend_libvirt.techvault_native` in ADR-036 policy.

## Canonical Incumbents To Reuse

- **Plans, capabilities, and snapshots:** `raes_contracts.planning`,
  `raes_contracts.runtime_state`, `raes_backend_protocols.capabilities`,
  `raes_backend_libvirt.manifest`, `capability_envelope_diagnostics()`,
  `LibvirtProvisioner`, and its existing snapshot reconciliation remain the
  authorities. No libvirt-specific replacement DTO/schema/store is needed.
- **Target and config shape:** `raes_backend_libvirt.target._CONFIG_KEYS`,
  `_validate_config_keys()`, `_driver_config()`, `LibvirtDriverMode`, manifest
  and realization-envelope pairing, and the existing injected driver/connector
  constructors remain the only backend configuration path. Add no environment
  fallback or second config model.
- **Native security and lifecycle:** `provider_resource_name()`, deterministic
  owner UUIDs, `techvault_lifecycle`, `_techvault_native_ops`, structured XML
  builders, `drivers.seed`, `techvault_appliance`, and the observation/probe
  modules remain canonical. Do not fork lookup, ownership, cleanup, XML,
  artifact-token, digest, or diagnostic logic.
- **Guest realization:** `cloudinit`, `dialects`, `acls`, and
  `techvault_concerns` own safe path components, argv-list commands,
  OS-specific emission, ACL translation, bounded guest paths/names, exact
  concern admission, and daemon/guest observation comparison.
- **Workflow contracts and schemas:** `raes_contracts._validation`,
  `raes.semantics.workflow`, `raes_contracts.versions`,
  `raes_contracts.contracts.execution_state`, `schema_bundle()`, and the
  checked-in published schemas remain their separate authorities.
- **Runtime errors and persistence:** `raes_runtime.backend_calls` owns
  deep-copy/fail-closed backend invocation and `runtime.backend-contract-invalid`;
  `workflow_result_contract_context` and
  `workflow_result_contract_checks` own compiled-contract/result validation;
  `RuntimeControlPlane` and `ControlPlaneStore` own operations, snapshots,
  idempotency, audit, and persistence. The four replacement packages add no
  store, audit sink, or error envelope.
- **Repository workflow:** ADR-015, ADR-036,
  `tools/policy/adr_policy.yaml`, `tools/check_repo_policy.py`, the locked
  oversized reference set, Hatch's existing nested-package discovery,
  `implementations/python/pyproject.toml`, generated-schema drift checks, the
  optional real-daemon smoke harness, and the pinned nox `verify` session are
  the completion graph.

## Cross-Cutting And Security Layers

- **Authoring, compilation, and plan shape:** normal input still passes the SDL
  parser/validators, compiler, planner, typed `ProvisioningPlan` construction,
  manifest capability checks, and realization-envelope checks. Direct plans
  still pass `LibvirtProvisioner.validate()` / `apply()` and
  `capability_envelope_diagnostics()` before reconciliation or driver IO. The
  split adds no raw SDL or unvalidated dictionary ingress.
- **TechVault admission and observation:** direct driver callers still pass
  constructor URI/flag/name validation, `load_libvirt_realization_envelope()`,
  `techvault_spec_diagnostics()`, native-name/ownership checks, exact daemon
  readback, `techvault_observation_diagnostics()`, optional challenge-bound
  guest observation, digest binding, and verified cleanup. No stage may be
  bypassed by importing a child module directly.
- **Workflow shape and semantics:** payloads still pass the same dataclass
  `from_*` shape checks, shared primitive validators, semantic step-result
  validator, runtime compiled-contract normalization, ordered result/history/
  compensation checks, and separately the closed Pydantic publication models
  where schema validation is required. Moving a definition must not weaken,
  duplicate, or reorder these gates.
- **Authentication and authorization:** none of the four modules authenticates
  a caller. HTTP-triggered work remains behind the existing control-plane API
  bearer-token, verified-identity, role, target-binding, request-size,
  idempotency, and audit gates. Do not add a libvirt or workflow child-module
  endpoint that bypasses `RuntimeControlPlane`.
- **Secrets and configuration:** TechVault continues to reject connection URIs
  carrying user information or passwords. Generic libvirt configuration stays
  explicit and is passed to the Python libvirt API, not inferred from ambient
  environment. Cloud-init may contain authored content and SSH public keys;
  retain password locking, private source/ISO modes, owner/symlink checks, and
  redaction. Never place URI credentials, content, keys, challenge values,
  environment values, or native exception text into diagnostics, audit, or
  portable snapshots.
- **OS/process/filesystem exposure:** preserve lazy `libvirt` import; structured
  XML calls; deterministic, ownership-checked host mutations; scoped artifact
  cleanup; safe path components; fixed argv, no shell, bounded timeout, and
  discarded output in `GenisoimageSeedBuilder`; and the existing bounded
  initramfs builder. The guest challenge remains a non-credential correlation
  value on the kernel command line. The split adds no subprocess, argv,
  environment, network, filesystem, privilege, or daemon surface.
- **Errors and observability:** preserve `Diagnostic`/`Severity`, every stable
  libvirt/TechVault/runtime code, message redaction, multiplicity and order,
  `DriverResult` observations, `last_snapshot` evidence binding, and upstream
  control-plane audit behavior. These modules have no logger; do not add a
  parallel logger, telemetry channel, exception hierarchy, raw traceback, XML
  dump, subprocess output, or payload-bearing error.
- **Persistence:** generic driver name/realized/seed/filter maps and TechVault
  artifact maps are private live-driver state. `RuntimeSnapshot`, control-plane
  records, and validated run artifacts remain the portable/durable surfaces.
  Workflow contract dataclasses remain data-only. Do not introduce a cache,
  database, repository, native-state ledger, or child-module global registry.
- **Import and policy gates:** child modules stay within the ADR-036 dependency
  directions: `raes_backend_libvirt` consumes only its allowed protocol,
  contract, and public runtime registry surfaces; `raes_contracts` consumes
  only `raes`. Every new file passes module-boundary, path-safety,
  secret/private-key, Ruff, type, coverage, and 500-line checks.

## Extensibility Seams

The existing seams are sufficient and must remain usable after the split:

- generic backend variation remains the explicit `provisioner_capabilities`
  parameter plus target/driver `connection_uri`, connector, name prefix,
  workspace, and `SeedBuilder` injection;
- plan-to-guest variation remains `GuestDialect` plus the manifest capability
  envelope, not conditionals scattered through child modules;
- TechVault/guest-certified variation remains `driver_mode`, realization
  envelope, `InitramfsBuilder`, connector, and the existing subclass hooks;
- a future workflow field or rule belongs with its owning DTO/validator, is
  deliberately re-exported if public, and joins the existing runtime check
  ordering and separate publication model explicitly.

A future remote libvirt target, seed transport, bounded appliance mode, or
workflow contract field must not require changes to `RuntimeManager`, the
control-plane API, published import paths, or an unrelated child module. Do not
replace these explicit parameters with environment binding, discovery,
registries, plugins, service containers, or generic validator frameworks.

## Gotchas And Anti-Patterns

- Do not modify external import lines, including relative backend imports, or
  expose child-module paths as a new supported API.
- Do not import a package facade from one of its child modules. In particular,
  avoid cycles among the workflow DTO families and among libvirt ownership,
  TechVault lifecycle, and driver modules.
- Do not preserve compatibility with wildcard re-exports. Conversely, do not
  omit the observed private facade seams merely because their names begin with
  `_` or are absent from `__all__`.
- Do not merge the generic and TechVault drivers, treat TechVault's bounded
  appliance proof as generic libvirt realization, or conflate daemon-observed
  facts with guest-observed service/application facts.
- Do not move `techvault_plan_admission`'s realization projections into a new
  schema or copy them; its facade imports are an existing coupling to preserve
  during this mechanical issue, not permission to create another payload
  authority.
- Do not merge workflow runtime dataclasses with Pydantic publication models,
  workflow SDL semantics, runtime result-check contexts, or control-plane
  workflow coordination. They have different owners and validation roles.
- Do not reorder diagnostics, sorting, mutation/rollback, observation stages,
  payload conversion, validation, or cleanup. Do not "fix" broad exception
  handling, coercion quirks, mutable defaults created by factories, unused
  helpers, or comments as incidental cleanup.
- Do not broaden Ruff suppressions to whole new packages. Use explicit
  same-name re-exports where possible; if a suppression is truly necessary,
  scope it to the facade and rule that require it.
- Do not hand-edit generated schemas, policy code, the locked oversized set,
  versions, `CHANGELOG.md`, or pre-existing tests to absorb refactor drift.
  Existing tests and the optional real-daemon harness remain behavior oracles.

## Non-Goals

- No libvirt, QEMU, cloud-init, TechVault, guest-certified, workflow,
  compensation, validation, diagnostic, observation, rollback, cleanup,
  snapshot, persistence, API, auth, audit, or security behavior change.
- No new SDL fields, contract/schema/profile/vocabulary changes, generated
  schema churn, backend capability claim, realization concern, driver mode,
  workflow state field, history event, or cancellation behavior.
- No new public child-module API, compatibility namespace, DTO, schema,
  validator framework, exception hierarchy, logger, telemetry path,
  repository, cache, service, registry/plugin system, config/environment
  surface, CLI command, HTTP endpoint, or host integration.
- No movement of contract ownership into runtime/backend code, backend-native
  state into portable contracts, pure realization into driver IO, or concrete
  backend logic into `raes_contracts`, `raes_processor`, `raes_runtime`, or the
  legacy compatibility tree.
- No test relaxation, behavior-motivated test edit, policy redesign,
  performance rewrite, dead-code cleanup, version edit, or manual release note.
