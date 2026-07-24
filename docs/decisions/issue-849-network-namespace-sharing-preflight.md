# Issue 849 Network Namespace Sharing Preflight

Date: 2026-07-22

Issue: #849. Requirement: none; the issue is the delivery contract.

This note records the repository-wide architecture boundary for one node
sharing another node's network namespace. It does not implement the SDL,
processor, backend, example, or conformance changes.

No new ADR is required. ADR-025 already owns container network realization,
ADR-033 places participant-interactable container state on the smallest typed
runtime surface, and ADR-070 owns configuration-bound backend realization
claims. This note applies those decisions to an asymmetric node-to-node
network-namespace relation.

## Decision

ACES should represent the requirement as a closed typed object under the
existing container namespace surface:

```yaml
nodes:
  kali-capture:
    type: vm
    runtime:
      container:
        namespaces:
          network:
            target_node_ref: kali
          pid: private
```

Presence of `runtime.container.namespaces.network` means that the declaring
node uses the exact network namespace owned by `target_node_ref`. The reference
is portable ACES node identity, not Docker Compose `service:kali`, Docker
`container:<id>`, a pod name, a PID, or another backend-native locator. Keep the
field an object rather than a raw string so the node-reference contract remains
typed and a future governed selector can be added without parsing backend
syntax.

The relation belongs neither in `infrastructure.links` nor in
`Node.runtime.network.endpoints`:

- an infrastructure link means an independently attached interface/address;
- a runtime endpoint records required endpoint identity on such a network; and
- namespace sharing means there is no independent interface, address, or
  network identity on the sharing node.

The target node is the canonical owner of endpoint, interface, IP, alias, and
published-port facts. A sharing node must not declare independent
`infrastructure.links`, per-link `properties`, network ACLs,
`runtime.network.endpoints`, or `runtime.network.published_ports`. It may still
declare its own services, processes, mounts, hostname/UTS state, DNS file
configuration, and other node-local runtime facts where those meanings remain
independent. Service declarations still do not authorize traffic or prove a
listener; issue #748's boundary remains unchanged.

Network sharing does not imply PID, mount, IPC, UTS, user, or cgroup namespace
sharing. The TechVault evidence-capture design must author `pid: private`
explicitly and the selected realizer must preserve and prove that separation.
Do not create a generic `sidecar` flag whose backend expands into several
namespace or mount choices.

## Semantic Invariants

The existing structural and semantic validation split remains authoritative.
The typed model owns local shape; `SemanticValidator` owns graph agreement.
For each concrete network-namespace reference:

- the target resolves as a local or `nodes.`-qualified reference to a declared
  VM node;
- source and target differ;
- source and target each denote exactly one runtime instance; absent
  infrastructure retains the existing single-instance posture, while a
  concrete `count` other than one is rejected;
- a target is a canonical namespace owner, not itself another network-namespace
  sharer; multiple sharing nodes may point to the same owner;
- the sharing node carries none of the independent network declarations listed
  above; and
- unresolved whole-field variables defer these checks until ordinary
  instantiation, after which the concrete scenario is revalidated.

Rejecting replicated or chained targets is deliberate. Mapping one logical
node reference to one of several runtime instances would otherwise be
ambiguous, and chains would obscure ownership and lifecycle order. If a later
requirement needs replica-aware sharing, the extension seam is a governed
instance selector inside the typed `network` object. It must resolve to a
stable compiled resource address; it must not expose a runtime container id or
guess by list position.

Module composition must rewrite `target_node_ref` through the existing node
symbol map, just as other authored node references are rewritten. Do not leave
an imported module's bare reference pointing outside its namespace, and do not
introduce a second module-reference resolver.

## Compilation, Realization, And Lifecycle Boundary

The compiler already preserves the full `Node` plus matching `InfraNode` in
the node resource payload. Reuse that carrier. It should additionally resolve
the authored target once to the canonical compiled node address, expose only
that normalized address to backend interpretation, and add it to both the
sharing node's ordering and refresh dependencies.

Those dependencies have material lifecycle meaning:

- the namespace owner exists before a sharing node is created;
- an owner update/replacement refreshes every sharing node;
- sharing nodes are stopped or deleted before the owner; and
- cycles fail through the existing provisioning ordering-cycle diagnostic.

Do not require authors to duplicate the relation in
`infrastructure.dependencies`, and do not rely on lexical node order. The
reference provisioner currently batches active container specs and the OCI
driver iterates its received sequence, so a supporting driver must explicitly
honor the normalized dependency instead of assuming plan order survived that
boundary.

Backend support is configuration-specific. Reuse the existing realization
envelope/configuration chain and `RealizationConcern.NETWORK`; do not add a
free-standing `supports_sidecars`, Compose mode, or environment toggle. A
selected configuration that cannot realize exact shared-node network namespace
identity must reject the plan before side effects. Descriptor carriage in a
snapshot is not realization evidence. Existing libvirt modes cannot satisfy
container namespace sharing and must not silently approximate it as two VM
interfaces on one network.

If the reference OCI driver is selected to realize the relation, extend its
existing portable `ContainerSpec` boundary with the canonical target address.
Backend-native namespace syntax is constructed privately from an
ownership-correlated runtime name or id. The driver must never accept an
author-provided `service:`, `container:`, PID, or host namespace locator.

## Required Cross-Cutting Reuse

- **SDL shape and parsing:** `RuntimeNamespaceConfiguration`,
  `RuntimeContainerConfiguration`, `SDLModel(extra="forbid")`, `parse_sdl()`,
  the bounded safe-YAML/source checks in `_source_validation.py`, canonical key
  normalization, and whole-field variable handling.
- **References and semantics:** the existing local/section-qualified
  node-reference convention, composition's node symbol map and
  `_rewrite_section_ref()`, `SemanticValidator`, `SDLValidationError`, and
  `instantiate_scenario()` concrete revalidation.
- **Network agreement:** `InfraNode`, `SimpleProperties`,
  `RuntimeNetworkRealization`, and `_NodesInfraNetworkMixin`; extend this
  incumbent validation pass rather than introducing a namespace validator or
  topology schema elsewhere.
- **Compilation and planning:** `_compile_node_runtimes()`, canonical node
  addresses, `NodeRuntime`, `ordering_dependencies`, `refresh_dependencies`,
  `resource_dependency_cycles()`, `refresh_impacted_nodes()`, and reverse
  delete ordering. The existing node plan payload remains the only carrier.
- **Backend claims and execution:** configuration-bound realization envelopes,
  `RealizationConcern.NETWORK`, `ConcernDisposition`, `ObservationStrength`,
  reference-backend `ContainerSpec`/`DeploymentDriver` and OCI ownership,
  fixed-argv, rollback, and runtime-allowlist patterns where applicable.
- **Errors, observation, and persistence:** `Diagnostic`, `ApplyResult`,
  `OperationReceipt`, `OperationStatus`, `RuntimeSnapshot`,
  `RealizationObservation`, the existing conformance evidence surface,
  `aces_runtime.backend_calls`, and `LocalControlPlaneStore`. Do not add a
  namespace exception hierarchy, logger, repository, ledger, or report shape.
- **Contract governance:** `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`, and
  `contracts/schema-publication-manifest.json`. The model is embedded in all
  four published schemas that contain `RuntimeNamespaceConfiguration`:
  authoring input, instantiated scenario, instantiated scenario snapshot, and
  satisfiability evidence. They must move together; the hand-governed published
  schemas remain authority and the generated bundle must stay identical.

## Security And Whole-Path Gates

1. **Source/parser gate.** Existing UTF-8, input-byte, scalar, alias, graph,
   depth, explicit-tag, directive, duplicate-key, and JSON-domain checks remain
   unchanged. The new field is closed shape; arbitrary Compose maps and unknown
   keys fail through source-anchored `SDLParseError` diagnostics.
2. **SDL model and semantic gate.** The typed object rejects scalar
   `network_mode` encodings. Semantic validation resolves only declared VM
   nodes and enforces singleton, ownership, non-self, non-chain, and no-separate-
   network-state invariants. Errors stay in `SDLParseError` /
   `SDLValidationError`; description strings are never interpreted.
3. **Composition and instantiation gate.** Imported node refs are rewritten by
   the canonical symbol map. Variables may occupy the reference value, never a
   symbol-defining key; concrete substitution reruns ordinary structural and
   semantic validation before compilation.
4. **Contract/schema gate.** Every published phase embedding the model is
   updated together with its schema-publication hash record. Updating only
   Python, only one JSON Schema, or only the authoring phase is invalid.
5. **Compiler/plan/config gate.** The compiler emits a canonical target address
   and dependency edges. Planner cycle/refresh semantics and the selected
   backend's configuration-bound realization admission reject ambiguity or
   unsupported realization before mutation. No new CLI, API, environment
   variable, credential, or secret-binding shape is needed.
6. **Authentication and authorization gate.** This issue adds no route or
   privilege. If the plan traverses the remote control plane, existing
   `ControlPlaneSecurityConfig.strict_defaults()`, request-size guards,
   authenticated role/target checks, idempotency, and audit controls remain the
   only authority. A node reference never authorizes joining an arbitrary host
   process or container.
7. **Host/OS execution gate.** A supporting OCI driver uses its runtime
   allowlist, fixed argv tokens, no shell, bounded timeout/output, ownership
   labels, and private native-id bookkeeping. It verifies the target is the
   exact run-owned container before joining its network namespace and preserves
   independently authored PID/mount/IPC/UTS/user/cgroup settings. Rollback and
   teardown remove dependents before the owner and retain failed resources for
   safe retry.
8. **Secret and process-exposure gate.** The portable relation contains only an
   ACES node/address. No token, credential, host path, PID, native id, raw
   inspect payload, or secret enters SDL, configuration digests, environment,
   process argv, diagnostics, logs, snapshots, fixtures, or evidence. Native
   output stays private and bounded.
9. **Error-envelope and persistence gate.** Backend failures become stable,
   redacted `Diagnostic` values through `aces_runtime.backend_calls`; raw
   exceptions, tracebacks, argv, native ids, and `str(exc)` do not cross the
   boundary. `LocalControlPlaneStore` persists only the portable node spec,
   canonical target address, normal dependencies, and operation envelopes.
10. **Observation/conformance gate.** Positive proof establishes that owner and
    sharer have the same network-namespace identity and network view at the
    claimed `ObservationStrength`. The security-negative proof establishes
    distinct PID namespace identities for the TechVault posture and no
    unintended independent endpoint/address. Desired-payload echo, matching
    network attachments, a common bridge, successful container start, or a
    test-double handle is insufficient. Logging is supplemental, not evidence.

## Gotchas And Anti-Patterns

- Do not add top-level `network_mode`, accept `service:kali`, or store raw
  Compose/OCI/Kubernetes namespace selectors in SDL or plans.
- Do not reinterpret `infrastructure.links`, `RuntimeNetworkDriver.HOST`,
  endpoint aliases, `RuntimeExtraHost`, service refs, relationships, or generic
  dependencies as namespace identity.
- Do not give the sharing node its own endpoint/IP/published-port identity or
  silently copy the owner's facts onto it. One namespace has one canonical
  network identity owner.
- Do not infer PID, mount, IPC, UTS, user, cgroup, volume, capability, privilege,
  or lifecycle sharing from the network relation. In particular, do not turn
  it into a generic sidecar/pod abstraction.
- Do not accept self-reference, chains, cycles, switch targets, replicated
  source/target nodes, or an unspecified replica choice.
- Do not assume a shared bridge, matching IP, or equal route table proves the
  same namespace. Conversely, do not use snapshot carriage as runtime proof.
- Do not join by an unverified runtime name, PID, or caller-supplied native id;
  this could expose an unrelated host workload's traffic and sockets.
- Do not start sharers in lexical order, forget refresh propagation, or delete
  the owner before its dependents.
- Do not add a second node-reference resolver, compiled plan type hierarchy,
  capability vocabulary, validator, exception family, logger, persistence
  store, or conformance harness.
- Do not add implementation under `implementations/python/src/aces/`, update
  only one phase schema, or change a published schema without its governed
  publication record and parity checks.

## Non-Goals And Implementation Boundaries

- Modeling PID, mount, IPC, UTS, user, or cgroup namespace sharing beyond the
  existing independent fields.
- Defining a general sidecar, pod, workload-group, service-mesh, network-policy,
  traffic-authorization, or evidence-volume abstraction.
- Supporting replicated namespace owners or a backend-native instance selector
  in the first contract.
- Changing `Node.services`, ACL ordering/default semantics, published-port
  semantics, runtime listener inventory, mounts, persistent-volume ownership,
  participant visibility, control-plane APIs, authentication, storage, or
  logging.
- Claiming support from existing libvirt modes or the hermetic in-process
  reference driver. Unsupported configurations remain fail-closed.
- Updating the downstream APTL `kali-capture` declaration in this repository or
  treating APTL's Compose file as ACES schema authority.
