# Issue 1076 Compute-Node Realization Semantics Preflight

Date: 2026-08-11

Issue: #1076. Requirement: none. The GitHub issue title, body, and acceptance
criteria are the authoritative contract.

This note records the repository-wide architecture boundary for expressing a
compute node independently of the mechanism that realizes it. It does not
implement an SDL, processor, backend, schema, migration, or conformance change,
and it is not an implementation plan.

No new ADR is required for this preflight. ADR-001 already makes SDL
backend-agnostic; SEM-218 owns author realization posture and non-approximation;
ADR-066 separates authored, planned, observed, and derived facts; ADR-070 owns
configuration-bound realization envelopes; and ADR-061/ADR-075 own contract
evolution and migration. The gap is an unresolved collision among those
authorities at `Node.type`, so this issue note makes the collision and its
guardrails explicit.

## Evidence-Based Diagnosis

### Historical and normative authority

- `NodeType`, `Node.type`, and their VM/switch discriminator semantics entered
  the repository together in initial extraction commit `2e73ee6c` on
  2026-04-03. Their original and current documentation says a node is either a
  virtual machine or a switch, that `type` activates that variant, and that the
  remaining node fields are VM-only. `Resources` and `Role` use the same literal
  VM terminology. The required `type` field and the `vm`/`switch` enum have not
  acquired a mechanism-neutral definition in the model.
- The normative SDL prose and ADR-001 say that scenarios describe portable
  intent and backends translate that intent into concrete infrastructure. The
  published `sdl-authoring-input-v1`, `instantiated-scenario-v1`,
  `instantiated-scenario-snapshot-v1`, and
  `scenario-satisfiability-evidence-v1` schemas nevertheless embed a required
  `Node.type` whose only values are literal `vm` and `switch`.
- `specs/sdl/diagnostics.md` treats “VM without resources” as a deployability
  advisory, confirming that the existing SDL meaning is a virtual machine even
  when its sizing is incomplete. It does not define `vm` as generic compute.

### SEM-218 and planning authority

- `raes_processor.semantics.realization_concerns` registers
  `nodes.<name>.type` as the `node-type` realization concern. Because
  `Node.type` is required, the explicitness ledger always contains that leaf.
  `_compiled_registered_requirement()` therefore compiles it as exact,
  author-declared intent; an inherited open designation cannot override it.
- `ProvisionerCapabilities.supported_node_types`, the
  `provisioner-node-types` controlled vocabulary, processor manifest validation,
  and libvirt capability-envelope validation all compare `vm` and `switch` as
  backend support terms. The vocabulary specifically says that `vm` means a
  provisioner can realize virtual-machine nodes.
- The compiler also uses the same value as a structural discriminator:
  `switch` creates a network resource/address and every other current value
  creates a node deployment. Host references, service placement, domain
  topology, deployment tenancy, evaluation, orchestration, aliases, summaries,
  and inspection tools use `NodeType.VM` to mean “compute endpoint” or
  `NodeType.SWITCH` to mean “network/switch resource.” That is scenario
  structure, not a backend mechanism choice.

The current plan therefore carries one token as three different facts:

| Current use of `vm` | Actual concept |
| --- | --- |
| Node variant and reference target | authored compute-resource semantics |
| SEM-218 exact leaf and provisioner support term | authored/backend mechanism constraint |
| `node_type` copied into a provisioning resource | planned structural discriminator |

Those facts cannot remain one field without preserving the defect.

### Backend and downstream interpretation

- The reference backend advertises `vm` and `switch`, but realizes every
  compiled node deployment as a `ContainerSpec`. Its OCI driver creates an
  operating-system container, and its in-process driver only emulates the
  portable driver protocol. Neither path interprets `node_type=vm` as a request
  for a virtual machine. The Docker/Podman integration fixture proves the
  mismatch directly with authored `type: vm` input.
- The reference target can swap an injected in-process or OCI driver under one
  manifest. Unlike libvirt, it has no configuration-selected realization
  envelope binding the advertised capability to the chosen driver mechanism.
  The selected mechanism is also absent from its portable snapshot.
- The libvirt backend interprets every node deployment as a `DomainSpec`, binds
  its manifest and plan to a configuration-selected realization envelope, and
  validates `node_type` against that configuration. Its generic mode therefore
  realizes `vm` literally as a libvirt/QEMU domain, subject to the separate
  honesty/readback limits already recorded by issues #714-#716.
- The in-repository cross-backend corpus deliberately preserves one authored
  scenario digest and common compiled address sets while disclosing materially
  different substrates: native libvirt/QEMU virtual machines versus APTL
  Docker/Compose containers. This is existing evidence that authored scenario
  identity and selected substrate are intended to be different facts.
- This repository contains bounded APTL evidence summaries, not APTL source.
  RAES can define the portable authority and conformance boundary, but it cannot
  claim to have migrated or certified APTL from this checkout. That downstream
  work remains in the APTL repository.

### Determination

`vm` is an overloaded combination, not a consistently implemented abstraction.
Its historical and formal authored meaning is literal virtual machine; its
structural consumers use it as generic compute; and the reference/APTL paths
reinterpret it as permission to use containers. No one of those later uses can
retroactively make an explicitly authored `vm` mechanism-neutral.

## Architecture Decisions and Guardrails

### Separate resource semantics from realization mechanism

The portable model needs two independent authorities:

1. A required node resource kind distinguishes a compute endpoint from a strict
   switch/network resource. The canonical compute value means that compute-node
   semantics are required; it says nothing about VM, container, image-building,
   cloud placement, or another delivery mechanism. The existing wire key may
   remain `type` for contract compatibility, but the model/helper terminology
   must say `kind` or `compute` rather than preserve “VM means non-switch.”
2. Optional authored realization constraints govern how that compute resource
   may be realized. They belong to the existing scenario-root realization
   authority and SEM-218 exact/constrained/open rules, not to VM-only fields on
   `Node` and not to backend configuration.

The existing `node-type` requirement and provisioner support check may continue
only as the exact resource-kind gate (`compute` versus `switch`). It must not
also admit or select the compute mechanism. If the public term or capability
field is renamed, normalize it once at the owning contract boundary; do not run
old and new support lists as parallel authorities.

Mechanism-neutral compute is an explicit compute resource kind with no narrower
mechanism constraint, under an author realization posture that admits backend
selection. It is not a missing node kind, a wildcard string, a third switch
variant, or an instruction to ignore all explicit node leaves. Required node
kind must remain closed and structurally validated.

### Reuse realization concerns rather than create a flat mechanism enum

The examples in the issue do not all occupy one taxonomy level:

- virtual machines and operating-system containers describe execution or
  isolation substrate;
- a cloud instance describes placement/provisioning context and may itself be a
  VM, container, or physical host; and
- a constructed root filesystem describes image/filesystem construction and can
  be used inside several substrates.

Do not flatten those into one `compute_mechanism` enum. Reuse and, where the
portable meaning is established, extend the existing realization-envelope
concern structure. A constraint is scoped to a compute node and a governed
realization concern; the concern's mechanism domain is exact, a finite governed
set, or deliberately open. For example, substrate and image-construction
constraints remain distinguishable and can coexist.

The authoring extension belongs under `Scenario.realization`, which already
owns typed, scoped author posture. Extend that one root surface with addressed,
typed constraint bindings; do not add `Node.mechanism`, `Node.backend`, native
runtime options, or a second scenario envelope. Canonical RFC 6901 paths,
namespace specificity, most-specific-wins resolution, typed bounded domains,
and conflict diagnostics must reuse `raes.realization_designation`, the
realization-envelope domain relation, and the existing instantiation constraint
provenance machinery.

Mechanism identifiers need governed, concern-specific vocabulary authority and
governed extension terms. Product names, driver class names, Docker/Compose
flags, libvirt XML concepts, cloud vendor SKUs, filesystem paths, image digests,
and arbitrary free text are not portable mechanism vocabulary. A future
portable placement concern is added only after its meaning is distinct from
substrate and image concerns.

### Preserve exact legacy meaning

Existing authored `type: vm` is binding virtual-machine intent. It must never be
silently normalized to mechanism-neutral compute.

If the old spelling remains temporarily accepted, the only meaning-preserving
migration is a diagnosed legacy adapter that normalizes once to canonical
compute kind plus an exact virtual-machine substrate constraint, preserves
source/explicitness provenance, rejects collision with a separately authored
constraint, and emits canonical output. Otherwise it must be removed through a
versioned/deprecated contract transition. ADR-061 and ADR-075 govern that
choice. Backend/runtime code must not carry a legacy `vm` branch.

This intentionally exposes current false positives: a container-only target
must reject legacy exact-VM intent, while the same target may accept canonical
mechanism-neutral compute. Existing scenarios that intended portability must be
migrated explicitly to compute-neutral intent rather than having their meaning
changed underneath them.

### Keep requested constraints, backend choice, and evidence distinct

- The compiled model and provisioning plan must carry the compute resource kind,
  the addressed authored mechanism constraint, its exact/constrained/open
  posture, and its governing scope as separate fields. A selected backend
  envelope/configuration identity is an apparatus fact. Neither may rewrite
  the source node declaration or copy a selected mechanism into `node_type`.
- Backend admission compares the requested mechanism domain with the selected,
  configuration-bound realization envelope. Reuse
  `RealizationSupportDeclaration`, `BackendRealizationEnvelopeModel`, the
  envelope domain/subsumption helpers, and the existing planner diagnostics.
  `ProvisionerCapabilities.supported_node_types` remains a resource-kind gate;
  adding mechanism names to it would recreate the overload.
- The reference target needs the same manifest/configuration/driver identity
  binding already established by `create_libvirt_target()`,
  `_selected_driver_mode()`, and `_validate_manifest_mode()`. An injected OCI
  driver cannot inherit an in-process or generic manifest claim, and an
  unbound injected driver cannot support a claim-bearing conformance run.
- The actual selected mechanism is a backend-observed realization fact bound to
  the compiled node address and concern. It belongs in the existing
  `RealizationObservation` / `RuntimeSnapshot.realization_observations` family,
  with a governed non-secret mechanism term, observation strength, and current
  operation/envelope/configuration binding. Extend that carrier and its closed
  published model rather than hiding the value in `SnapshotEntry.payload`,
  `RuntimeSnapshot.metadata`, `ApplyResult.details`, logs, or a backend-only
  report.
- Preserve two provenance statements even when their values agree: the author
  declared a constraint, while the backend selected and observed the actual
  mechanism. Do not label the observed virtual machine or container as
  `author-declared`, and do not treat `backend-realized` provenance as proof of
  daemon/guest observation. The full observation is validated at
  `_call_backend_apply()`; the bounded snapshot disclosure is persisted and
  exposed through the existing control-plane contract.
- Plan/payload echo, a `ContainerHandle`, a libvirt `DomainHandle`, a successful
  operation, or a configured envelope mechanism is not independent evidence
  that the mechanism was actually realized. OCI support requires bounded
  runtime readback; VM support requires bounded libvirt/daemon readback. Native
  IDs, raw inspect output, and XML remain private.

### Preserve strict switch/network semantics

`switch` remains a required, exact resource kind and continues to compile to the
network address/resource family. Compute-only fields and compute-mechanism
constraints are invalid on a switch. Open compute realization posture must not
make a switch eligible to become a compute node, and backend substrate support
must not satisfy switch/network support. Generalizing network-appliance
mechanisms is outside this issue and requires its own semantic analysis.

## Alternatives Rejected

- **Redefine `vm` to mean generic compute.** This changes existing authored
  meaning, contradicts the model and controlled vocabulary, and still gives
  authors no honest way to require a virtual machine.
- **Make `Node.type` optional and interpret omission as open.** Node kind selects
  resource/address families and reference validity before a backend is chosen.
  Omission would make invalid structure look like deliberate delegation and
  could weaken switch semantics.
- **Add `compute` beside `vm` but keep both in one backend node-type domain.** A
  transitional parser may accept both, but the canonical model cannot keep one
  discriminant as both resource kind and mechanism constraint.
- **Add `Node.mechanism` or backend-native options.** This creates a second
  realization-authority surface and leaks delivery vocabulary into scenario
  structure.
- **Treat a backend manifest or realization envelope as authored intent.** Those
  are backend offers and apparatus facts. They can bound a choice but cannot
  create author permission or override an exact author constraint.
- **Disclose only the selected envelope.** A configuration claim does not prove
  the per-node mechanism actually used, especially for injected drivers or
  future mixed-mechanism backends.
- **Keep current behavior and document that VM may mean container.** That leaves
  SEM-218 exactness, capability admission, source authority, and evidence in
  contradiction.

## Canonical Incumbents to Reuse

The implementation must build on these existing authorities rather than create
parallel schemas, validators, errors, or workflow logic:

- SDL shape and source admission: `raes._base.SDLModel`, `raes.nodes.Node` and
  `NodeType`, `parse_sdl()`, the bounded safe-YAML/source-profile path, closed
  models, duplicate/canonical-key checks, and variable parsing;
- semantic and phase validation: `raes.validator.SemanticValidator`,
  `SDLParseError`, `SDLValidationError`, `instantiate_scenario()`,
  `SDLInstantiationError`, concrete revalidation, explicit `model_fields_set`,
  and instantiation/source provenance;
- author posture and domains: `raes.explicitness`,
  `raes.realization_designation`, `raes.realization_envelope`,
  `CapabilityConstraint`, and the exact/constrained/open and
  membership/subsumption rules;
- structural node semantics: existing validator/compiler/reference-resolution,
  address, placement, tenancy, topology, orchestration, evaluation, MCP
  inspection, and summary consumers of `NodeType`; replace VM-as-compute checks
  through one canonical compute-kind predicate rather than adding
  `VM or COMPUTE` at every call site;
- concern compilation and admission:
  `raes_processor.semantics.realization_concerns`,
  `CompiledRealizationRequirement`, compiler realization requirements,
  `realization_support_diagnostics()`, manifest validation, realization-envelope
  diagnostics, and shared domain comparison;
- capability and concept authority: `ProvisionerCapabilities`,
  `RealizationSupportDeclaration`, `BackendManifestV2Model`,
  `contracts/concept-authority/controlled-vocabularies-v1.json`, canonical
  concept bindings, and the `realization-and-disclosure` concept family;
- configuration-specific claims: `RealizerConfigurationModel`,
  `RealizationConcernDisclosureModel`, `BackendRealizationEnvelopeModel`,
  packaged envelopes under `contracts/realization-envelopes/`, canonical
  digests, and the libvirt target's config allowlist/mode validation;
- backend seams: reference `ContainerSpec`, `DeploymentDriver`,
  `InProcessDriver`, `OciDeploymentDriver`, and `ImageTrustPolicy`; libvirt
  `DomainSpec`, `LibvirtDriver`, plan interpreter, ownership/readback, and
  configuration-bound envelope;
- runtime validation and errors: `raes_runtime.backend_calls._call_backend_apply`,
  `ApplyResult`, `Diagnostic`, `OperationStatus`, baseline-snapshot retention,
  realization disclosure, observation validation, and backend-exception
  reduction;
- observation, persistence, and API: `RealizationObservation`,
  `RealizationObservationDisclosure`, `RuntimeSnapshot`,
  `RuntimeSnapshotEnvelopeModel`, `ControlPlaneStore`, `LocalControlPlaneStore`,
  `_snapshot_payload()`, `_snapshot_from_payload()`, `_snapshot_model()`, atomic
  local-store replacement, and existing audit events;
- conformance/evidence: `run_target_conformance()`, realization-envelope
  positive/negative probes, cross-backend corpus invariants, libvirt honesty
  fixtures, and existing redaction/atomic artifact writers; and
- contract/workflow governance: the four SDL-containing schemas,
  `backend-manifest-v2`, `realization-envelope-v1`, `provisioning-plan-v1`,
  `runtime-snapshot-v1`, `schema_bundle()`,
  `contracts/schema-publication-manifest.json`, generated-schema parity,
  concept-authority checks, `.ground-control.yaml`, `.gc/plan-rules.md`, and
  `tools/verify_all.py`.

## Cross-Cutting Security and Whole-Path Gates

1. **Source/parser shape.** The new author surface passes UTF-8/resource bounds,
   safe YAML parsing, duplicate/merge-key rejection, canonical-key checks,
   `extra="forbid"`, closed enums/models, and ordinary source diagnostics.
   Constraint keys cannot be variable-generated; whole-field values use the
   existing typed variable/domain path. No arbitrary backend options map is
   admitted.
2. **SDL model and semantic shape.** Node kind stays required. Compute-only
   concerns on switches, unknown mechanism terms, duplicate addressed
   constraints, exact/allowed-set conflicts, invalid pointers, unresolved
   namespaces, and legacy/canonical collisions are fatal meaning errors through
   `SDLValidationError`, not advisories or backend diagnostics.
3. **Instantiation and explicitness.** Parameter binding preserves bounded
   domains and provenance, removes unresolved placeholders, and reruns semantic
   validation. The compiler consumes the canonical explicitness/designation
   result; it does not infer intent from raw strings, absence, backend defaults,
   or selected drivers.
4. **Published contract shape.** Every affected SDL embedding, plan, manifest,
   envelope, and snapshot schema moves with its model, fixtures,
   `schema_bundle()`, invariants, publication manifest/hash/ledger, and ADR-061
   compatibility classification. Updating only Python, one embedded schema, or
   generated output is invalid.
5. **Manifest/config binding.** Controlled-vocabulary validation, manifest
   contract-id allowlists, realization support, provisioner resource-kind
   support, and configuration-specific envelope subsumption are separate
   necessary gates. Target factories accept only their typed/allowlisted config,
   and driver mode, configuration digest, envelope, plan, observer, and snapshot
   identities agree before mutation.
6. **Backend return and error envelope.** `_call_backend_apply()` remains the
   fail-closed admission point. Unsupported constraints fail before mutation;
   missing, contradictory, weak, stale, or unbound mechanism evidence returns
   the baseline snapshot with existing stable `Diagnostic` / `OperationStatus`
   handling. Do not add a mechanism exception hierarchy or accept a backend
   exception as a portable result.
7. **Authentication and authorization.** This issue adds no HTTP route or role.
   Snapshot/operation access continues through
   `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy
   identity, backend/operator/auditor authorization, target binding,
   request-size limits, idempotency, and audit recording. The new non-secret
   disclosure must round-trip through the same authenticated surface rather
   than a public debug endpoint.
8. **Secrets and environment binding.** Portable mechanism terms and digests are
   non-secret and require no new environment variable, credential binding, or
   secret store. Never derive mechanism identity from an environment dump or
   persist credentials, tokens, connection URIs, cloud metadata, private image
   references, or injected driver representations with it.
9. **Host/OS and argv exposure.** A portable mechanism term is data for
   admission, never an executable name, dynamic import/class selector, shell
   fragment, path, or argv splice. OCI continues to use its runtime allowlist,
   `ImageTrustPolicy`, fixed tokenized argv, no shell, bounded timeout/output,
   and private native IDs. Libvirt continues to use typed configuration,
   structured XML, ownership checks, and bounded readback. No secret or raw
   authored payload enters argv.
10. **Observability, persistence, and leakage.** The addressed governed
    mechanism term, provenance distinction, strength, and binding may be
    disclosed. Raw Docker/Podman inspect, libvirt XML/UUIDs, host paths, process
    argv, stdout/stderr, object reprs, environment, traceback, and native
    handles may not enter snapshots, diagnostics, logs, audit details, fixtures,
    API errors, or cross-backend reports. Existing control-plane serialization,
    atomic persistence, redaction checks, and coarse exception reduction remain
    authoritative; logging is supplemental evidence only.

## Extensibility Boundary

The required seam is an addressed mechanism-domain binding parameterized by:

- canonical compute-node address or namespace plus RFC 6901 scope;
- governed realization concern, so substrate, placement, and image construction
  do not collapse into one dimension;
- exact, finite constrained, or open domain;
- selected configuration/envelope identity; and
- backend observation source/strength and operation binding.

A backend that always uses one mechanism can bind it at configuration scope. A
future backend that selects different mechanisms per node uses the same carrier
at node-address scope. Adding one governed mechanism term or a new backend mode
must not require a new node field, concern registry, planner branch, snapshot
schema family, API route, persistence store, or conformance runner.

The next likely variation is a mixed-mechanism target or a constraint on a
different concern such as image construction. That variation extends the
governed concern/domain data and backend mappings; it must not require reopening
the compute/switch structural discriminator.

## Conformance Guardrails

The issue's conformance claim requires, at minimum, these distinctions:

- one canonical mechanism-neutral compute scenario accepted by two materially
  different, honestly identified configurations: an OCI-container target and a
  libvirt/QEMU virtual-machine target;
- the same authored compute semantics and compiled compute address preserved
  across those runs, with different addressed actual-mechanism disclosures;
- exact virtual-machine intent accepted by the VM configuration and rejected by
  the OCI configuration before mutation;
- exact container intent accepted by the OCI configuration and rejected by the
  VM configuration before mutation;
- finite constrained intent accepted only for members of the authored domain;
- missing, unsupported, contradictory, unobserved, stale, or tampered mechanism
  evidence rejected without persisting a changed snapshot;
- legacy `vm` proven to preserve exact-VM meaning, including collision and
  canonical migration coverage if the adapter exists;
- switch nodes remaining switch/network resources, rejecting compute-only
  fields and mechanism constraints, and never being accepted through compute
  capability;
- model/schema/fixture parity, plan and snapshot round trips, API/store
  round trips, stable bounded diagnostics, redaction, and configuration/envelope
  mismatch cases; and
- hermetic tests in the default verification graph plus separately labelled
  real-runtime/real-libvirt evidence for claims that require native observation.

The in-process reference driver is useful for negative and protocol tests but
does not count as a materially different native compute mechanism. A plan echo,
stub handle, injected recording driver, or self-declared envelope cannot turn a
hermetic test into native mechanism evidence.

## Gotchas and Anti-Patterns

Avoid:

- keeping `NodeType.VM` as the generic “not a switch” predicate;
- adding `COMPUTE` and then sprinkling `VM or COMPUTE` checks throughout
  validators, compilers, MCP tools, and backends;
- using a missing/optional node kind as realization openness;
- treating virtual machine, container, cloud placement, and root-filesystem
  construction as mutually exclusive terms in one flat enum;
- putting mechanism names in `ProvisionerCapabilities.supported_node_types` or
  treating resource-kind support as proof of substrate support;
- letting `OPEN_REALIZATION`, a backend default, host capability, injected
  driver, or selected envelope override exact legacy/authored VM intent;
- adding parallel authoring fields, concern registries, capability lists,
  envelope relations, validators, exception hierarchies, logs, stores, report
  schemas, or backend-local vocabularies;
- carrying both legacy `vm` and canonical compute/mechanism constraints past
  normalization, or silently choosing one on collision;
- selecting a mechanism in the processor and rewriting the authored node or
  marking backend observation as authored intent;
- treating planned payload equality, success, handles, or a configuration claim
  as observed realization;
- allowing a mechanism term to select executable code, enter shell/argv, bypass
  OCI image trust, weaken libvirt ownership checks, or expose native state;
- certifying APTL from the bounded summary in this repository; or
- weakening strict switch/network semantics while generalizing compute.

## Non-Goals and Implementation Boundaries

- Implementing or sequencing the SDL, migration, processor, backend, schema,
  fixture, or test changes in this preflight.
- Choosing backend-product syntax, native driver options, cloud vendor SKUs, or
  a universal taxonomy for placement and image construction.
- Making node kind optional, making switches mechanism-neutral, or redesigning
  networks, topology, addressing, host references, services, tenancy, or
  orchestration beyond replacing their VM-as-compute predicate.
- Treating all compute mechanisms as behaviorally or scientifically equivalent.
  Mechanism neutrality means the authored constraint permits the choice; it is
  not an equivalence claim about timing, isolation, fidelity, or evidence.
- Redesigning SEM-218, realization-envelope set semantics, backend manifests,
  control-plane authentication, persistence, diagnostics, or conformance where
  the existing parameterized surfaces can be extended.
- Migrating APTL, env-packs, or another external backend from this repository.
- Adding a new endpoint, secret, environment binding, daemon requirement,
  privileged operation, persistence service, or logging stack.
