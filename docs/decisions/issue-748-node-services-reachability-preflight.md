# Issue 748 Node Services Reachability Preflight

Date: 2026-07-13

Issue: #748. Requirement: none; the issue is the delivery contract.

This note records the repository-wide architecture boundary for authored node
services, traffic authorization, and backend realization. It does not implement
the SDL, processor, backend, or conformance changes.

## Decision

`Node.services[]` is the positive authored or curated identity of a node-local
transport binding: optional service name, container/node-side port, and
transport protocol. A declaration can be a realization concern for a backend
that supports or synthesizes services, but it is not by itself:

- permission for any source to reach the port;
- a bind address, listener-scope observation, or proof that a daemon is live;
- a host-published port, NAT rule, image `EXPOSE` declaration, or firewall rule;
- an `internal` / `external` audience classification.

Consequently, a backend MUST NOT derive ingress, host publication, or an ACL
allow rule merely because a service is declared. Traffic authorization must be
authored through the existing `infrastructure.*.acls` policy surface, or a
future separately governed traffic-policy surface. The current ACL model does
not yet specify a portable default action, rule-order calculus, or end-to-end
reachability proof, so this issue must not claim that an ACL list alone proves
identical reachability across backends. The portable invariant for this issue
is narrower and fail-closed: a service declaration never grants reachability.

Do not add `ServicePort.role`. In the current canonical implementation,
`SDLModel(extra="forbid")` and both published SDL schemas reject that key; it is
not silently dropped. A free-form `role: internal` would conflate transport
identity, topology, participant or login roles, protocol-local roles, and
traffic authorization while still failing to identify an allowed source. If a
later requirement needs audience policy, it belongs on the authorization
surface as a typed source selector with defined evaluation and defaults, not as
a descriptive service label.

## Existing Authority And Incumbents

- ADR-025 keeps container-side `Node.services`, image exposed ports, and
  `runtime.network.published_ports` distinct. ADR-033 keeps transport bindings,
  runtime state, delivery mechanics, and evidence distinct. ADR-043 keeps
  authored service identity, observed `runtime.service_listeners`, and host
  publication distinct. These decisions already own the semantic boundary; a
  new ADR or competing endpoint schema is not justified.
- `aces_sdl.nodes.ServicePort`, `Node.validate_unique_service_ports()`, the
  shared `parse_int_or_var()` helper, `SDLModel`, `parse_sdl()`,
  `SemanticValidator`, and `instantiate_scenario()` are the canonical
  authoring, shape, semantic, and concrete-revalidation path.
- `aces_processor.compiler._compile_node_runtimes()` already carries the full
  node and matching infrastructure declarations in the existing node resource
  payload. Named services already participate in canonical aliases. Do not add
  a second service resource, DTO at the compiler boundary, or parallel plan.
- `RealizationConcern.SERVICE`, `RealizationConcern.ACL`,
  `ConcernDisposition`, `ObservationStrength`, and
  `TransformationKind.SERVICE_SYNTHESIS` already provide the backend claim
  vocabulary. `ProvisionerCapabilities.supports_acls`,
  `RealizationSupportDeclaration`, `BackendRealizationEnvelopeModel`, and
  `backend_manifest_payload()` are the existing capability/configuration
  surfaces. Do not add a standalone `supports_services` dialect.
- `aces_reference_backend.realization`, its existing `NetworkSpec` /
  `ContainerSpec` driver boundary, `ReferenceProvisioner`, and
  `DeploymentDriver` are the reference-backend seams. The libvirt
  `ServiceSpec` and fail-closed ACL translator are useful behavioral precedent,
  but they are backend-owned types and must not be imported to create a
  cross-backend dependency.
- `Diagnostic`, `ApplyResult`, `OperationReceipt`, `OperationStatus`, and
  `RuntimeSnapshot` are the error, result, and observation envelopes. Snapshot
  payload preservation proves carriage only; it is not evidence that a service
  listened or an ACL was enforced.

Two current gaps must not be hidden by the change. The reference manifest says
`supports_acls=True` although neither reference interpreter nor driver realizes
ACLs. That claim must either become false or be backed by real fail-closed
enforcement. Also, the planner's coarse ACL capability check currently inspects
network resources only, while `InfraNode.acls` and the libvirt backend support
node-attached ACLs. The canonical capability gate must cover every materialized
infrastructure entry rather than duplicating location-specific checks.

## Cross-Cutting Gates

- **Source and parser gate:** retain `_source_validation.py` UTF-8, byte,
  scalar, alias, depth, node, tag, and directive limits. Unknown service fields
  continue through `SDLParseError` and bounded, source-anchored
  `sdl.model.invalid` diagnostics; do not add a permissive YAML preprocessor or
  silently delete `role`.
- **SDL model and semantic gate:** retain closed-world Pydantic models, shared
  port bounds, protocol-plus-port and name uniqueness, ACL action/port parsing,
  and `SemanticValidator` network-reference checks. Authoring errors remain
  `SDLParseError` or `SDLValidationError`; do not add duplicate validators or a
  service exception hierarchy. Description text must never be parsed as
  policy.
- **Instantiation and contract gate:** concrete scenarios revalidate through
  `instantiate_scenario()`. The hand-governed schemas under
  `contracts/schemas/` remain normative; `schema_bundle()` is the reference
  implementation's compatibility proof, not authority to change them. Any
  future public model change must update the Python SDL model and every affected
  authoring/instantiated schema together, record the change in
  `contracts/schema-publication-manifest.json`, and keep
  `tools/check_generated_schemas.py` passing. Never update only the generator,
  one published phase, or one copy of `ServicePort`.
- **Compiler and planner gate:** use the existing node resource payload and
  canonical addresses. A required or claimed service/ACL runtime effect that a
  selected backend cannot honor must fail before side effects through the
  existing realization-support / capability `Diagnostic` path. Descriptor-only
  carriage may succeed only when the selected backend configuration discloses
  that disposition and claims no runtime effect. Merely echoing the authored
  payload into a snapshot must not satisfy realization or non-approximation
  evidence.
- **Manifest and configuration gate:** machine-readable claims remain bound to
  the selected backend configuration and rendered by
  `backend_manifest_payload()`. If a realization envelope is published, its
  existing configuration and envelope digests plus complete service/ACL concern
  disclosures are authoritative. Do not create an environment-variable flag,
  unvalidated config dictionary, or backend-local capability vocabulary.
- **Interpreter and error-envelope gate:** reference interpretation stays pure
  and driver-neutral, shape-checks plan mappings, and returns stable redacted
  `Diagnostic` values. `aces_runtime.backend_calls` remains the exception and
  return-contract boundary. Driver failures preserve the baseline snapshot and
  use `ApplyResult`; do not expose native exceptions, tracebacks, runtime ids,
  or raw rule payloads.
- **Host / OS gate:** the OCI driver retains its closed Docker/Podman runtime
  allowlist, fixed argv lists, bounded timeout, image trust policy, private
  stdout/stderr handling, ownership labels, and rollback. `Node.services` must
  never produce `--publish` / `-p` arguments. Firewall or namespace mutation is
  privileged host behavior and is outside this issue; a future implementation
  would need an explicit, ownership-checked, reversible driver mechanism rather
  than shell fragments or host-global rules assembled from free-form input.
- **HTTP, auth, and secret gate:** this change needs no new API, credential,
  secret, environment binding, or process argument. If plans traverse the
  remote control plane, reuse `ControlPlaneSecurityConfig.strict_defaults()`,
  request-size guards, identity and role authorization, target binding,
  idempotency, audit, and the redacted FastAPI exception handler unchanged.
- **Persistence and observability gate:** use the existing control-plane store,
  runtime snapshot, operation status, realization provenance, and evidence
  surfaces. Do not add a repository, migration, sidecar ledger, logger, or raw
  backend-output field. Structured diagnostics and observation strength are the
  observability surface.

## Conformance Boundary

Conformance must distinguish four claims instead of treating them as one:

1. parsing and compilation preserve a service declaration;
2. a backend interpreter extracts or explicitly rejects it;
3. a driver realizes the declared listener or ACL effect;
4. an independent daemon/guest/network probe observes the claimed effect.

A snapshot that repeats the provisioning payload proves only the first claim.
Service and ACL remain separate realization concerns, so a service-positive
probe cannot certify traffic authorization and an ACL-positive probe cannot
certify that a daemon is listening. Any backend claim of reachability needs a
positive authorized path and a negative unauthorized path, ordinary
`OperationStatus` / `Diagnostic` refusal without state mutation, and evidence at
the observation strength it declares. Backends that disclose service or ACL as
`descriptor-only` or `unsupported` are conformant only when they do not claim
the corresponding runtime effect.

Reuse the existing conformance scenario parameter while it remains the active
bridge; the realization-envelope witness seam is its governed replacement.
Tests belong in the existing SDL model/parser/schema, processor, pure backend
realization, OCI argv/redaction, libvirt ACL enforcement, and target-conformance
families rather than a second service-specific harness.

## Extension Seam

The immediate seam is the existing node resource's `spec.node.services`
collection paired with independent service and ACL realization-concern
disclosures for the selected backend configuration. Preserve every concrete
entry, including unnamed services, and preserve or reject the authored
protocol; never coerce an unknown protocol to TCP or discard an unnamed entry.

The next reasonable extension is richer source selection. Its parameter belongs
on a typed traffic-authorization rule and should identify governed network,
CIDR, zone, or principal selectors with explicit default and evaluation
semantics. That allows a future same-range, cross-range, or externally sourced
policy without reinterpreting `Node.services` or baking one backend's topology
choice into the portable service contract.

## Non-Goals And Anti-Patterns

- Do not implement shifter's same-range-derived firewall policy as the ACES
  default, infer audience from `internal`, topology membership, node roles, or
  service names, or auto-generate allow rules from services.
- Do not turn `Node.services` into observed listener state, host publication,
  image metadata, daemon configuration, an ACL container, or a reachability
  result. Do not move ACL fields onto `ServicePort`.
- Do not add `role`, `audience`, or a free-form policy bag without a separately
  specified source-selector and evaluation contract.
- Do not silently drop unnamed services, unsupported protocols, unresolved
  CIDRs, invalid ACL rules, or unsupported backend concerns. In particular, do
  not copy libvirt's current unknown-protocol-to-TCP fallback.
- Do not claim ACL support from extraction, snapshot carriage, labels, or test
  doubles. Do not claim service realization from a declared port or container
  metadata alone.
- Do not redesign ACL ordering/default semantics, backend privilege management,
  control-plane APIs, persistence, logging, runtime listener inventory,
  published-port semantics, image build metadata, or protocol-specific runtime
  inventories in this issue.
- Do not add implementation under `implementations/python/src/aces/`, hand-edit
  generated schemas, fork diagnostics/exceptions, or introduce a second
  compiler/backend workflow.
