# Initial Service State

Status: **normative**.

This contract governs scenario content that must be established through a
named service rather than copied onto the service's node. It extends the
existing `content` declaration and `content-placement` lifecycle. It does not
define historical data, product adapters, event replay, or a second state
authority.

## 1. Authority

Top-level `content` is the sole authored authority for initial files,
directories, datasets, messages, records, and comparable data. The stable
authored identity is `content.<id>` in the instantiated scenario. Age,
represented business time, or a narrative about prior activity MUST NOT create
a different SDL object class.

Ordinary node placement remains the default. A content entry MAY carry
`service_materialization` only when establishing the required state through the
named service is materially different from node placement.

## 2. Service Materialization Binding

`service_materialization` is a closed object with these fields:

| Field | Shape | Requirement |
|---|---|---|
| `target_service_ref` | exact named-service reference | REQUIRED |
| `interface_profile` | literal `service-content` | OPTIONAL; defaults to the literal |
| `profile_version` | literal `"1"` | OPTIONAL; defaults to the literal |
| `requirements.operation` | literal `ensure-owned-items` | REQUIRED |
| `requirements.conflict_policy` | literal `reject-unowned-collision` | REQUIRED |
| `requirements.readback` | literal `canonical-content-digest` | REQUIRED |
| `shared_service_relationship_ref` | relationship reference | OPTIONAL except for cross-tenant state |
| `ordering_content_refs` | unique content references | OPTIONAL; defaults empty |
| `readback_assertion_refs` | non-empty unique assertion references | REQUIRED |
| `evidence_requirement_refs` | non-empty unique evidence-requirement references | REQUIRED |
| `observation_boundary_refs` | non-empty unique participant-observation-boundary references | REQUIRED |

`content.target` remains the owning VM node. `target_service_ref` MUST resolve
to an exact `nodes.<node>.services.<service>` declaration on that same VM.
Every ordering reference MUST resolve to another content declaration;
self-dependency is invalid. Local deployment tenancy is derived from the
owning node and MUST NOT be redundantly authored in this binding.

Every readback assertion MUST be a postcondition over an observed-state
proposition for the exact content subject. Every bound evidence requirement
MUST be required by that proposition. Every observation boundary MUST expose
the exact content subject. These references define the portable observed
result and participant projection; neither planned state nor a backend success
response satisfies them.

Cross-tenant state requires `shared_service_relationship_ref`. That
relationship MUST be a typed `uses_shared_service` edge to the exact target
service and MUST assign mutable-state and reset-generation ownership under
ADR-087. The compiler derives consumer tenancy and ownership from this typed
relationship.

## 3. Compilation And Control

The binding compiles as the existing `content-placement` resource. Compilation
MUST retain:

- canonical content identity;
- exact service and owning-node addresses;
- interface profile, profile version, and exact operation requirements;
- canonical content digest;
- derived tenant ownership and the shared-service relationship reference;
- content ordering;
- readback assertion addresses; and
- evidence-requirement references;
- observation-boundary addresses.

The owning node and ordered content placements are provisioning dependencies.
No separate plan, lifecycle engine, scheduler, result store, or reset authority
is created.

The provisioner manifest capability term `service-content-v1` in
`supported_service_materialization_profiles` is independent of
`supported_content_types`. Admission requires the content type, exact
interface/profile version, and exact requirements. A claimed profile also
requires a realization-envelope
`content-placement` concern with `realized` disposition and at least
`daemon-observed` independent readback. Missing support is fatal before backend
I/O. Direct plan submission MUST repeat these checks.

## 4. Backend Conformance And Equivalence

RAES standardizes the portable profile without selecting a product or backend.
A backend MAY claim `service-content-v1` only when its own conformance evidence
demonstrates native materialization through the RAES control path, fresh
independent readback, reset ownership, and the declared participant projection.
A manifest claim is not execution evidence.

Two realizations are equivalent only with respect to the admitted portable
contract and declared participant-visible assertions/evidence. They need not
share provider resources, product adapters, deployment topology, bootstrap
mechanisms, native identifiers, or implementation code.

## 5. Non-Goals

This contract does not:

- classify content as historical;
- author native product identifiers, endpoints, commands, queries,
  credentials, or adapter options;
- prove product-native creation time or audit history;
- define an event sequence or replay trajectory;
- make runtime inventory authored authority; or
- permit a scenario pack to define materialization control semantics.
