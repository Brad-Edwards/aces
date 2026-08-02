# Issue 713 PlannedResource Payload Accessors Preflight

Date: 2026-08-01

Requirement: none. GitHub issue #713 is the authoritative contract.

This note records the boundary for a public Python convenience API over
`PlannedResource.payload`. It is guidance only: it does not add a portable
semantic, schema, fixture, profile, backend capability, or production-backend
claim, and it is not an implementation plan.

No ADR is needed. ADR-009, ADR-036, and ADR-063 already establish normative
authority, package ownership, and the repository-owned reference-backend
boundary.

## Binding Sources

- `raes_contracts.planning.PlannedResource`, `ProvisioningPlan`,
  `RuntimeDomain`, `ChangeAction`, and `require_plan_operation_identity()` are
  the neutral planning DTO and shape authority.
- `raes_processor.models.runtime_model.resource_payload()` is the compiler-side
  producer of the stable planner payload; it is not a backend reader API.
- `raes_reference_backend.realization` and `raes_backend_libvirt.realization`
  are the two consumer migrations. Their pure interpretation and existing
  package-local `Diagnostic` behavior remain authoritative for realization
  failure reporting.
- `raes_backend_libvirt._payload` is the immediate duplication to retire or
  reduce to backend-only concerns. `capability_envelope_diagnostics()` remains
  the backend capability gate, not an accessor responsibility.
- `provider_resource_name()` is the incumbent backend-native name normalizer.
  `Diagnostic`, `Severity`, `RuntimeSnapshot`, `ApplyResult`, and the runtime
  backend-call gates remain the public error and persistence envelopes.
- ADR-009/019/061 and the corpus/publication checks govern normative artifacts;
  ADR-036 and `tools/policy/adr_policy.yaml` govern this import direction.

## Decision And Guardrails

Place one small, public, dependency-free accessor surface alongside
`PlannedResource` in `raes_contracts.planning` (or a directly public
`raes_contracts.planning` submodule re-exported there). It accepts only a
`PlannedResource`; it must not import a backend, processor implementation,
runtime, schema model, or provider naming helper.

The surface is a **total read/normalization convenience API**, not validation.
It must provide mapping-shaped access to the top-level payload and the node
`spec`, `infrastructure`, `resources`, and `source` surfaces, plus a stable
authored-name fallback. A missing optional subtree, a non-mapping payload, a
non-provisioning resource, or a non-node resource must produce the documented
safe empty/absent result for the relevant accessor; it must not throw, coerce,
guess, mutate the payload, or leak its contents. Source should retain its
existing string-or-mapping distinction rather than inventing an image/source
DTO. The name accessor may fall back to the stable planned address; a backend
that needs a provider-safe runtime name continues to apply
`provider_resource_name()` at its own boundary.

Use one consistent absent-result convention across all accessors (for example,
`None` for an unavailable scalar/subtree and an empty mapping only where the
API explicitly promises a mapping). Document the resource/domain precondition
and the absent-result behavior. Do not make `None` mean a malformed plan is
valid: realization collectors must retain their existing resource-type/domain
checks and their distinct `invalid-payload` versus `unsupported-resource`
diagnostics before using node-specific reads.

The helper must expose existing payload projections only. It must not validate
SDL meaning, enforce capability allowlists, resolve network or placement
references, convert RAM/CPU units, normalize service entries, choose an image,
or supply defaults with operational meaning. Those decisions stay respectively
with the parser/compiler/planner, `capability_envelope_diagnostics()`, and the
backend realization/driver layers.

Migrate both realization modules for every covered node read. Do not leave
parallel local traversal helpers for source, resources, infrastructure/spec, or
authored name. Shared generic access does not require migrating backend-only
placement, account, feature, ACL, cloud-init, or capability-envelope traversal
in this issue; those must continue to use their current local validation until
they have an equally clear shared contract.

## Cross-Cutting And Security Gates

| Layer | Required treatment |
| --- | --- |
| SDL, schemas, and compiler | No new input path or schema. Existing closed SDL/Pydantic validation and `resource_payload()` remain the sole producer/validator of plan payload meaning. |
| Plan DTO shape | Keep `PlannedResource` address/dependency checks and plan-domain admission unchanged. The accessor handles hostile or hand-built payload shapes defensively without changing DTO validation. |
| Capability and realization | Keep `ProvisionerCapabilities`, capability-envelope diagnostics, supported-resource checks, and pure realization diagnostics in the backends. The helper neither authorizes nor realizes anything. |
| Runtime/error envelope | Do not add exceptions, logs, or diagnostics in `raes_contracts`. Existing package-local `Diagnostic` codes and runtime `_call_backend_apply()`/snapshot validation continue to envelope failures. |
| Secrets and observability | The helper performs no IO, parsing of environment/config, logging, persistence, subprocess invocation, or serialization. Callers must not include returned payload values in diagnostic messages; existing redaction tests remain relevant. |
| Host/OS exposure | None: this layer must never reach driver configuration, libvirt, OCI, filesystem, process argv, or environment. Provider-safe naming remains in the backend protocol boundary. |
| Packaging and policy | Keep the public API within the already packaged `raes_contracts` root and the ADR-036-approved dependency direction. Run repository policy, requirement governance with the existing requirement-free setting, and hermetic verification. |

## Evidence Required From The Implementation

Add focused contract tests for valid node source/resources/infrastructure/name
reads; omitted optional fields; non-mapping payloads; and wrong resource type
or runtime domain. Include the fallback-name and string-versus-mapping-source
cases. Keep the existing reference and libvirt realization tests as migration
evidence: malformed payloads must still yield their existing redacted backend
diagnostic codes, and valid plans must preserve current realization output.

## Extensibility Boundary

The seam is a small family of `PlannedResource`-only accessors, with explicit
resource/domain applicability rather than a generic dotted-path evaluator or a
backend parameter. The next reasonable addition (for example node services or
network infrastructure) can add one named accessor with the same absent-result
contract. It must not require re-editing schemas, planner payload production,
runtime control, or either driver. If a later use needs semantic validation or a
typed portable value, that is a separate contract-evolution decision rather
than a widening of this convenience layer.

## Gotchas And Anti-Patterns

Avoid:

- a second payload schema, Pydantic model, source/image DTO, exception class,
  validation profile, diagnostic code set, or backend capability registry;
- a `dict`/deep-copy/serialization conversion that changes identity, accepts
  arbitrary mapping-like objects inconsistently, or makes the accessor a
  persistence boundary;
- treating wrong resource/domain or malformed payload as a valid empty node in
  backend control flow; retain the collectors' diagnostic gates;
- provider name sanitization, network/placement resolution, resource sizing,
  default-image selection, or cloud-init policy in `raes_contracts`;
- importing `raes_backend_*`, `raes_processor`, `raes_runtime`, or the legacy
  `raes.*` compatibility tree from the shared helper;
- exposing raw payloads or source/build data through logs, diagnostics,
  snapshots, control-plane records, or error messages.

## Non-Goals

- Changing normative portable semantics, schemas, fixtures, profiles, or
  conformance claims.
- Making the reference or libvirt backend a production backend, transferring
  ownership to LilRAE/BigRAE, or changing ADR-063's boundary.
- Refactoring all payload traversal across every backend concern, redesigning
  planning DTOs, or changing planner reconciliation.
- Adding a persistence, configuration, authentication, authorization, logging,
  IO, driver, or API surface.
