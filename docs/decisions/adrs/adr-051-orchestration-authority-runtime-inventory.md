# ADR-051: Orchestration Authority Runtime Inventory

## Status

accepted

## Date

2026-05-30

## Context

SCN-010 (DSL-137) identifies an SDL expressivity gap for a node whose defining
logical state is the authority to *spawn* containers or workloads through a
control interface — a SOAR orchestrator (e.g. Shuffle's Orborus) or an analyzer
engine holding `docker.sock` read-write. `RuntimeControlInterface`
(`runtime.local_control_interfaces`) types the docker.sock *shell* — a present
read-write Unix socket — but carries no field for what the holder is authorized
to *do*. The spawn contract (engine, scope, spawn templates, lifecycle policy,
realized children, privilege class) has no home.

Adjacent surfaces each own narrower meaning:

- `runtime.local_control_interfaces` records the control-interface shell (path,
  kind, access), not the spawn authority that holds it.
- `runtime.container` records the node's own container configuration, not the
  children it spawns.
- `runtime.platform_applications` records security-platform application
  inventory, not container-spawn privilege.

The design risk is to duplicate `RuntimeControlInterface`, infer spawn
authority from a socket mount alone, or encode the privilege fact in free-form
relationship properties.

## Decision

### 1. Add node-scoped orchestration authorities under runtime

Add `Node.runtime.orchestration_authorities` as an observed runtime inventory
surface. Each entry is a `RuntimeOrchestrationAuthority` with a stable
`orchestration_authority_id`, an OPEN `engine` taxonomy
(`docker`/`containerd`/`podman`/`kubernetes`/`cri_o`, plus `unknown`/`other`),
an `engine_api_version`, an optional `scope`, and an OPEN `privilege_class`
discriminator (`host_root_equivalent`, `namespaced`, plus `unknown`/`other`).

### 2. Reference the control-interface shell, never duplicate it

`control_interface_ref` is the `control_interface_id` of a same-node
`RuntimeControlInterface`. The spawn contract is carried here; the shell stays
in `runtime.local_control_interfaces`. This surface never imports or duplicates
`RuntimeControlInterface`.

### 3. Preserve typed child inventories

The authority owns typed `spawn_templates` (image + purpose), an optional
`lifecycle_policy` (timeout/cleanup/execution-timeout), and typed
`realized_children` (observed spawned workloads with image, count, and evidence
ref). Each carries a stable local id.

### 4. Make the discriminator executable

A `require_profile_for_privilege_class` after-validator makes the host-root
privilege-escalation fact executable: a `host_root_equivalent` authority that
does not carry a concrete `control_interface_ref` fails validation. A `${var}`
discriminator is exempt; `namespaced`/`unknown`/`other` are permissive. At
scenario scope, `control_interface_ref` resolves to a same-node
`RuntimeControlInterface`, and for `host_root_equivalent` the referenced
interface must additionally be a read-write docker socket (access `read_write`,
kind `unix_socket`, path ending in `docker.sock`), with `${var}` interface
access/kind/path treated as deferred and therefore permissive.

### 5. Keep orchestration inventory targetable but not executable

Authorities and child records may be referenced from relationships using
qualified refs such as
`nodes.<node>.runtime.orchestration_authorities.<orchestration_authority_id>.spawn_templates.<template_id>`.
These refs are inventory targets; they do not imply spawn execution.

## Security and Validation Gates

- Parser/model gate: stable authority and child ids are concrete symbols, not
  variables; duplicate authority ids and duplicate authority-local child ids
  fail early; realized-child `count` is a non-negative integer, a `${var}`, or
  none.
- Profile gate: the model-local `require_profile_for_privilege_class` guard
  rejects a `host_root_equivalent` authority with no concrete
  `control_interface_ref`.
- Semantic validation gate: `control_interface_ref` resolves to a same-node
  `RuntimeControlInterface`; a `host_root_equivalent` interface must be a
  read-write docker socket.
- Contract/schema gate: published schemas are regenerated from Python model
  sources; generated JSON schemas are not edited by hand.

## Guardrails

- Do not duplicate `RuntimeControlInterface`; reference it by id.
- Do not infer spawn authority from a socket mount, package name, or process
  argv alone.
- Do not model spawned children as full nodes; they are observed inventory.
- Do not make Docker or Shuffle the schema authority; they motivate the
  surface, the model stays product-neutral.

## Non-Goals

- Implementing container spawning, lifecycle reconciliation, or engine API
  calls.
- Replacing the OCI Runtime/Image Specs, Kubernetes, or the Docker Engine API.
- Redesigning `runtime.local_control_interfaces`, `runtime.container`, or
  `runtime.platform_applications`.

## Consequences

### Positive

- The container-spawn authority and its host-root privilege fact become typed,
  targetable, and validation-backed, with the docker.sock shell referenced
  rather than duplicated.
- The `host_root_equivalent` profile makes the docker.sock privilege-escalation
  fact (ATT&CK T1610/T1611) executable rather than implied.

### Negative

- Node runtime gains another optional inventory surface.

### Risks

- Over-expanding into an orchestration engine would recreate the original
  ambiguity under a new name.
- Treating a socket mount as proof of spawn authority would overclaim what the
  SDL can validate.

## References

- [Platform Application Runtime Inventory](adr-049-platform-application-runtime-inventory.md)
- [Forwarding Agent Runtime Inventory](adr-050-forwarding-agent-runtime-inventory.md)
- [Scenario/Delivery Boundary for Runtime Node State](adr-033-scenario-delivery-boundary-for-runtime-node-state.md)
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md)
