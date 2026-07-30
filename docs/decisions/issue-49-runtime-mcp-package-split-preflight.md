# Issue 49 Runtime And MCP Package Split Preflight

Date: 2026-07-30

Issue: #49.

Requirement: none. The GitHub issue is the delivery contract. This note records
architecture guardrails only; it does not implement the split.

## Current-Tree Reconciliation

The four current targets are:

- `raes_runtime.control_plane_api` (689 lines);
- `raes_runtime.workflow_result_contract_checks` (585 lines);
- `raes_mcp.tools.authoring` (694 lines); and
- `raes_mcp.tools.inspection` (599 lines).

ADR-015's amended source-file cap is 500 lines. Each target must become a
same-named package, every Python file in those packages must remain at or below
that cap, and only the four corresponding entries must be drained from
`tools/policy/oversized_allowlist.yaml`. The fixed historical baseline in
`tools/policy/repo_policy.py` must remain unchanged.

The issue asks for a `CHANGELOG.md` entry, but `.gc/plan-rules.md` and the
release workflow make release-please the sole owner of that file. The split
must leave `CHANGELOG.md` untouched and use a non-behavior-changing
Conventional Commit / PR title such as `refactor:`.

## Package Boundaries

### Runtime control-plane API

Keep the facade as the application composition boundary. Cohesive internal
boundaries already exist around authentication and FastAPI dependencies,
request guards, operation routes, workflow routes, and participant route
families. Route modules may register routes against `(FastAPI,
RuntimeControlPlane)`; they must not become controllers with their own runtime
service, store, security configuration, DTOs, or audit implementation.

The existing sibling modules remain canonical and remain at their current
stable import paths:

- `control_plane_api_models.py` owns request DTOs, contract/model conversion,
  snapshot conversion, and request fingerprints;
- `control_plane_api_guards.py` owns request-size enforcement and its 400/413
  envelopes;
- `control_plane_api_participant_retrieval.py` owns governed participant view
  routes;
- `control_plane_security.py` owns identities, roles, subject bindings, and
  fail-closed security defaults;
- `control_plane.py` is the service boundary; and
- `control_plane_store.py` is the persistence and append-only audit boundary.

Do not duplicate or move these concerns into the new package. Preserve route
registration order, route function names and signatures, response models,
response-status declarations, dependency annotations, `app.state` key,
idempotency header/fingerprint flow, audit calls, and exception mappings.

### Workflow result-contract checks

Partition the current implementation along its existing call graph:
snapshot/context normalization, state and step checks, history checks, and
compensation checks. `_WorkflowContext` remains an internal validation carrier,
not a new contract DTO or public schema. The existing
`workflow_result_contract_context.py`,
`workflow_result_contract_compensation.py`, `raes_contracts.workflow` models,
and `diagnostics.py` helpers remain the authorities.

Diagnostic order is behavior. Preserve the current fail-fast snapshot shape
check, workflow-result iteration order, context-normalization failure order,
and the ordered aggregation of schema, compensation requirement, step
presence, step contract, execution contract, history, and compensation-history
diagnostics. Do not replace `from_mapping()`, `from_payload()`,
`validate_workflow_step_result_contract()`, `_parse_timestamp()`, or
`_failure_diagnostic()` with local parsing or validation.

### MCP authoring and inspection

Keep `register(FastMCP)` as each package's sole server registration boundary,
with unchanged tool names, descriptions, signatures, defaults, registration
order, and text responses.

Authoring remains a presentation adapter over `parse_sdl()`,
`load_sdl_fragment()`, `instantiate_scenario()`, and their existing exception
types. Scaffold templates are examples, not schemas. Inspection remains a
best-effort human-readable view: its reference map and ASCII topology are not
semantic validation, compiler, or runtime topology authorities.

The similar section lists and input-size constants in authoring, inspection,
and `operation_support.py` do not have interchangeable output contracts.
Consolidating them could change visible sections or error envelopes and is
outside this behavior-preserving split. Do not introduce a generic MCP utility
layer or silently route these text tools through the structured operation-tool
pipeline.

## Compatibility Guardrails

The four source modules currently declare no `__all__`. Do not add a
restrictive `__all__` that changes star-import behavior. The package facades
must preserve at least every observed import and module-object seam:

- `raes_runtime.control_plane_api`: `create_control_plane_app`,
  `_receipt_response`, and `_control_plane_api_version`;
- `raes_runtime.workflow_result_contract_checks`:
  `workflow_result_contract_diagnostics` and `_WorkflowContext`;
- `raes_mcp.tools.authoring`: `register`; and
- `raes_mcp.tools.inspection`: `register`.

`test_version_classification.py` imports `raes_runtime.control_plane_api` as a
module and patches `distribution_version` on that package object before calling
`_control_plane_api_version()`. A simple re-export of a helper defined in a
submodule would resolve the unpatched submodule global and break this behavior.
Keep the version lookup in the facade or retain an equally narrow
facade-compatible indirection. Preserve `PackageNotFoundError` handling and the
`0.0.0+unknown` sentinel.

`workflow_result_contract_compensation.py` imports `_WorkflowContext` from
`.workflow_result_contract_checks` under `TYPE_CHECKING`, while
`workflow_result_contracts.py` imports
`workflow_result_contract_diagnostics` from the same path. Both lines must
continue to resolve without modification or a facade/submodule cycle.

FastAPI derives OpenAPI metadata from the decorated functions, and FastMCP
derives tool schemas from its decorated functions. Moving code must not change
function names, annotations, defaults, decorator metadata, route/tool order, or
the public module paths used by the server and Sphinx autodoc.

## Cross-Cutting Obligations

- **Authentication and authorization:** preserve bearer-token lookup, explicit
  proxy-header opt-in, verified-identity enforcement, target binding,
  read-versus-mutate role sets, governed participant audience/subject
  bindings, and denial auditing. Raw bearer tokens must never enter audit
  records, logs, errors, process arguments, or environment-derived fallback
  configuration.
- **Input and shape validation:** preserve FastAPI/Pydantic request validation,
  `extra="forbid"` request bodies, canonical `raes_contracts` response models,
  request-size/content-length guards, SDL input byte limits, canonical SDL
  parser and migration policy, duplicate-key-aware fragment loading, synthetic
  fragment name overwrite, JSON-object parameter validation, inspection
  attribute allowlisting, and recursion limits.
- **Errors and observability:** preserve exact HTTP status/detail behavior,
  redacted 500 responses, `RuntimeControlPlane.record_audit()` and
  `AuditEvent` persistence, MCP text error envelopes, and
  `runtime.backend-contract-invalid` diagnostics. Do not add a parallel
  exception hierarchy, logger, telemetry path, or error payload.
- **Secrets and data minimization:** MCP instantiation responses must remain
  summaries and must not echo parameter values. The split adds no network,
  filesystem, subprocess, credential, environment, or command-line surface.
- **Persistence and idempotency:** API modules call `RuntimeControlPlane`;
  only the existing control-plane/store layer owns operation records,
  snapshots, audit events, idempotency lookups, and atomic participant
  transitions. Route code must not access a store directly.
- **Module ownership:** retain ADR-036 import directions. `raes_mcp` must not
  import `raes_runtime`; `raes_runtime` must not import MCP, CLI, stub, or
  conformance implementations and may consume only allowed public processor
  prefixes and neutral `raes_contracts` DTOs.

## Repository Integration Guardrails

- Retarget the narrow Ruff `B008` override in
  `implementations/python/pyproject.toml` to only the new control-plane API
  file(s) that retain FastAPI `Depends()` annotations. Do not broaden the
  suppression to unrelated runtime code.
- Retarget the exact
  `implementations/python/packages/raes_runtime/control_plane_api.py` ownership
  entry in `tools/policy/requirement_order.yaml` to the package root so future
  path-prefix checks still cover its submodules.
- Update the implementation-path reference in
  `docs/explain/reference/shared-semantic-integrity.md` when the package exists.
  Keep the public autodoc target `raes_runtime.control_plane_api` unchanged.
- Hatch's existing package-root discovery already covers nested packages; do
  not add a second distribution or entry point. `raes-mcp` continues through
  `raes_mcp.server:main`, and the control-plane app remains an explicitly
  constructed ASGI object rather than a new host/process binding.
- Preserve every external import line identified by the issue, including the
  relative imports above. The only path-literal/configuration edits are those
  needed to follow the file-to-package conversion.

## Extensibility Seams And Non-Goals

The existing seams are sufficient:

- a future control-plane route family adds one registrar to the app composition
  boundary while reusing the same auth, guard, DTO, audit, and service layers;
- a future workflow rule joins the existing ordered diagnostic aggregation and
  consumes `_WorkflowContext`;
- a future scaffold complexity adds a template through the existing
  complexity-to-template selection; and
- a future inspection tool registers through `register(FastMCP)` and reuses the
  package's bounded canonical parse path.

This issue does not change HTTP or MCP behavior, public schemas, SDL semantics,
workflow contract meaning, validation rules, route/tool inventory, security
policy, trust defaults, persistence, audit contents, idempotency semantics,
diagnostic order or wording, scaffold content, reference-map coverage, topology
rendering, packaging entry points, or existing tests. It does not reconcile
the presentation-only section catalogs, introduce shared controllers/services,
move private helpers into `raes_contracts`, or create compatibility aliases for
the retired legacy namespaces.
