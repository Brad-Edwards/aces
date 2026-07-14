# Issue #776 — Domain Topology Realizer Preflight

Date: 2026-07-14

Issue: #776.

Requirement: none. The issue title, body, and acceptance criteria are the
authoritative contract.

This note is architecture guidance only. It does not implement a realizer,
change a capability declaration, publish an envelope, or provide an
implementation plan.

No new ADR is required. ADR-082 owns authored identity-domain topology and its
portable compiled projection; ADR-063 owns the reference-emulation backend;
ADR-066 owns operational observation versus evidence; and ADR-070 plus the
issue #100/#715 preflights own configuration-bound libvirt claims and guest
proof. This note applies those decisions to the first operational domain
realizer. The issue's ADR-081 reference is stale; ADR-082 is authoritative.

## Current-State Correction And Scope

There are two distinct backends and their claims must not be conflated.

- `reference-emulation` still declares `active_directory` and `spn`, but its
  pure interpreter reduces placements to address/name/target records and its
  drivers realize only networks and containers. Copying the plan payload into a
  snapshot is not domain or account realization. The minimum honest correction
  is to remove those two claims unless that backend independently gains real
  behavior. This issue does not establish that its other account-feature claims
  are evidence-backed; they need the same honesty audit.
- `libvirt-qemu` currently has no false public AD claim. Every published libvirt
  envelope has an empty `supported_domain_profiles`, and each admitted account
  feature set excludes `spn`. The marker-file branch in
  `aces_backend_libvirt.realization` is therefore legacy, unreachable behavior
  for an admitted current configuration; it must not be promoted into evidence.

The real fix belongs in a new, explicitly selected **AD-capable libvirt material
configuration**, not in `reference-emulation` and not as a silent widening of
the generic, TechVault, or guest-certified appliance configurations. A
digest-pinned AD-compatible appliance is an acceptable reference mechanism if
its envelope states its actual OS/image/network bounds and native evidence
proves the required directory behavior. A Samba-based implementation may claim
the portable AD-compatible semantics it proves; it must not imply Windows
Server or Microsoft-product equivalence.

## Architecture Decisions And Guardrails

### Keep one portable topology authority

`IdentityDomain`, typed controller/join relationships, the pure SDL topology
analyzer, and `DomainTopologyBinding` remain the only authored and compiled
authorities. The libvirt interpreter consumes the existing binding on node and
account-placement payloads. It must not reparse SDL, infer a domain from names,
OS/image, SPN, DNS, observed inventory, or create a second domain/account
schema.

Use `domain_topology_plan_diagnostics()` at backend validation and apply
admission, with the real baseline snapshot and selected
`supported_domain_profiles`. Use `DomainTopologyBinding.from_mapping()`,
`domain_topology_profile()`, `provisioner_account_features()`, and the existing
libvirt payload helpers rather than duplicating shape, reference, or feature
logic. Any backend-private execution record is a projection of these admitted
values, not a public DTO or another validation authority.

`RuntimeSnapshot` continues to preserve the normalized desired binding for
SEM-218 exact readback. That copy proves carrier fidelity only. It is never
operational evidence that promotion, join, DNS, or SPN registration succeeded,
and observed `Node.runtime.identity_authorities` must not be synthesized from
it.

### Bind support to one material libvirt configuration

Extend the existing `LibvirtDriverMode` -> published envelope -> manifest ->
provisioner -> driver identity chain with one separately versioned mode. Its
closed envelope is the single source of supported OS, image, network, resource,
content, account-feature, domain-profile, ACL, transformation, and observation
claims. Existing modes retain their current envelopes and claims.

Only a mode that completes controller promotion, member join, genuine SPN
registration, authoritative readback, and cleanup may publish both
`supported_domain_profiles={"active_directory"}` and account feature `spn`.
The manifest must bind the domain-profile capability scope to the existing
`identities` concept family. `_validate_manifest_mode()` must compare
`supported_domain_profiles` as it already compares the other envelope-derived
dimensions. Construction must select the driver for the normalized mode from
one target factory and fail on a mode/driver/envelope mismatch; no mode may
fall through to `LibvirtDeploymentDriver` accidentally.

Do not add a backend-local support vocabulary. Exact topology remains covered
by the existing SEM-218 `declared-capability-match` declaration, while the
governed profile and account feature are checked by `ProvisionerCapabilities`,
the shared plan analyzer, and the table-driven libvirt capability envelope.
Change a published schema or controlled vocabulary only if those incumbents
cannot express a portable claim.

### Make directory readiness a commit invariant

Plan ordering is not guest readiness. The current provisioner batches active
domain specs into one driver call, so tuple order or
`ordering_dependencies` alone cannot establish a usable controller. The
AD-capable driver must enforce these state invariants inside the existing
staged native-driver boundary:

- libvirt networks and owned domains are defined before guest operations;
- one controller from the explicit authored controller set bootstraps the
  domain, then passes bounded DNS/Kerberos/directory readiness and identity
  readback;
- additional controllers join only after that gate and independently prove
  controller state;
- each member uses only its authored, ordered `controller_addresses`, waits for
  one of them to be ready, joins, and proves its machine identity and secure
  channel;
- domain accounts and SPNs are applied only against the proven domain, and the
  SPN is queried back from the authoritative directory on the exact target
  principal; and
- the driver returns successful handles only after every required observation
  and cleanup gate passes.

The authored topology has no “primary controller” semantic. A v1 driver may
choose a deterministic bootstrap leader (for example, the lexically smallest
compiled controller address) from the explicit set, but that is a fixed,
versioned operational policy. It is not authored meaning, must not alter the
snapshot binding, and must never select an unlisted controller. Member
candidate order remains authored and must be respected.

Incremental operations use the topology closure, not only the directly changed
node. A changed SPN/account or member may require an unchanged owned controller
for execution and proof without redefining it. Replays must observe and
converge exact state before acting; a conflicting foreign domain, principal,
machine account, or SPN fails rather than being adopted, overwritten, or moved.
Partial delete/update must unregister owned directory state before removing a
surviving member/account/controller when stale state would otherwise remain.
If the first mode cannot safely support an operation shape, backend admission
must reject it before mutation; the manifest cannot imply success and then
silently skip directory cleanup.

### Keep bootstrap credentials outside portable state

`authority_account_ref` is a logical account address, not a credential
reference. Control-plane bearer identity is also unrelated to domain authority.
For a self-contained reference appliance, generate strong, per-apply bootstrap
material only at the impure driver boundary. If an external provider is ever
needed, inject a credential resolver/handle at target construction; do not add
an SDL field, plan field, environment binding, `.env` convention, or CLI secret
option.

Secret values, keytabs, tickets, join blobs, hashes, and recovery material must
never enter the SDL, plan, envelope/configuration digest, cloud-init payload
retained in a snapshot, process argv, command text, environment, diagnostic,
log, audit event, fixture, `ApplyResult.details`, runtime snapshot, or evidence
artifact. Deliver bootstrap and per-member join material through a private,
least-privilege file/device/stdin or offline-join channel, with restrictive
ownership/modes, bounded lifetime, detachment, deletion, and verified cleanup.
Use fixed argv, no shell, a controlled cwd/environment, and bounded timeouts;
parse bounded structured output and discard raw stdout/stderr. If no safe
channel is available, the configuration must fail closed and must not claim
support.

### Require authoritative, fresh, bounded evidence

Reuse `RealizationObservation`, `DriverResult.observations`, the existing
daemon-then-guest staging pattern, and the canonical libvirt evidence-run
artifact/validator. Do not add a domain evidence store, report schema, logger,
or exception hierarchy. Use the existing closed concerns:

- `topology` for exact domain identity and controller/member role/secure-channel
  facts;
- `account-placement` for the authority account, target principal, and exact SPN
  registration; and
- `service` for the DNS/Kerberos/directory readiness facts the selected mode
  claims.

Controller evidence must read DNS name, NetBIOS name, forest/domain identity,
and controller role from the authoritative directory. Member evidence must read
domain membership and a working secure channel from the member. SPN evidence
must query the directory, identify the exact principal, enforce global
uniqueness, and return only the bounded expected value/correlation—not a
directory dump, ticket, or keytab. Package presence, a marker file, a process,
an open port, successful VM boot, cloud-init completion, or an echo of desired
input is insufficient.

A fresh per-run non-secret challenge and ownership-verified native correlation
must bind observations to the current guests, selected envelope/configuration,
image/appliance digest, ACES addresses/field paths, and control-plane operation.
The operation id is joined by the existing operations/evidence layer after
submission, not added to `LibvirtDriver.realize()`. Operational facts belong in
the validated evidence artifact; portable desired bindings stay in the runtime
snapshot.

### Preserve transactional and cleanup behavior

The selected mode inherits the existing ownership UUIDs, collision checks,
rollback, bounded state directory, and verified-absence cleanup rules. A failed
promotion, join, registration, readback, timeout, or cleanup returns stable
`Diagnostic` values, no changed addresses, and the baseline snapshot. A later
stage never repairs or upgrades a failed earlier stage.

Directory operations are not magically atomic. Track which run-owned native
and directory objects were created so compensation is ownership-scoped and
idempotent. Never delete by name prefix, treat lookup failure as absence, adopt
pre-existing directory objects, or report success while temporary credential
media, overlays, fact channels, domains, networks, machine accounts, or SPNs
remain in an unintended state. Cleanup uncertainty is a failed operation/proof,
not a warning.

## Required Cross-Cutting Reuse

- **SDL and compilation:** `IdentityDomain`, typed domain relationships,
  `analyze_domain_topology()`, `DomainTopologyBinding`, compiler
  `NodeRuntime`/`AccountPlacement`, canonical compiled addresses and dependency
  ordering. ADR-082 remains the semantic authority.
- **Plan admission:** `domain_topology_plan_diagnostics()`,
  `ProvisioningPlan`, resource plus non-`DELETE` operation materialization,
  `_submitted_plan_diagnostics()`, and the normal planner/direct-control-plane
  gates. Backend checks may be stricter but not weaker or parallel.
- **Capabilities and exactness:** `ProvisionerCapabilities`,
  `provisioner_account_features()`, `domain_topology_profile()`, the libvirt
  `_ENVELOPE_DIMENSIONS` table, `CompiledRealizationRequirement`,
  `realization_support_diagnostics()`, `realization_disclosure()`, and the
  configuration-bound envelope identity carried through plan and snapshot.
- **Libvirt execution:** `interpret_provisioning_plan()`, `Realization`,
  `DomainSpec`, `NetworkSpec`, `LibvirtProvisioner`, the
  `TechVaultNativeLibvirtDriver` staged extension hooks, structured XML
  builders, deterministic ownership, image/seed workspace protections,
  rollback, and safe absence checks. Extend these private carriers only enough
  to preserve the admitted binding and domain-bound account intent.
- **Observation and evidence:** `RealizationObservation`, `DriverResult`,
  `ObservationStrength`, `GuestFactTransport`'s bounded fact-channel pattern,
  `libvirt_evidence_run`, `validate_libvirt_evidence_run_artifact()`, redaction
  validation, run-artifact paths/atomic writes, existing cleanup, and the
  explicit destructive-confirmation CLI convention.
- **Runtime, errors, and persistence:** `RuntimeControlPlane`,
  `_call_backend_diagnostics()`, `_call_backend_apply()`, `Diagnostic`,
  `ApplyResult`, `OperationReceipt`, `OperationStatus`, `RuntimeSnapshot`,
  `LocalControlPlaneStore` atomic persistence, and existing audit summaries.
  Public failures stay in those envelopes and backend exceptions stay type-only.
- **Contract governance:** the existing realization-envelope model/schema,
  libvirt envelope corpus, manifest rendering and concept-binding validators,
  schema publication manifest, packaged corpus, fixtures, digest/parity tests,
  and authority-boundary checks. A published carrier change must update the
  complete governed set; editing only generated JSON is forbidden.

## Security And Whole-Path Gates

The intended design passes every layer below.

1. **SDL parser and closed shapes.** Existing safe YAML/source bounds,
   `SDLModel(extra="forbid")`, profile/name validators, typed refs, semantic
   analysis, instantiation, and post-instantiation validation remain unchanged.
   Authored strings are inert and never trigger directory or host activity.
2. **Compiler and plan shape.** The compiler emits the one typed binding.
   `DomainTopologyBinding.from_mapping()` and
   `domain_topology_plan_diagnostics()` shape-check resources, non-delete
   operations, and baseline state before backend IO. The libvirt interpreter
   consumes only admitted plan payloads.
3. **Capability and configuration shape.** Planner capability checks, SEM-218,
   `_validate_config_keys()`, `_selected_driver_mode()`, envelope loading and
   digest validation, `_validate_manifest_mode()`, provisioner identity checks,
   and driver admission all agree on one normalized mode. Unknown config,
   profile, feature, image, topology, or mode mismatch fails before mutation.
4. **Authentication and authorization.** No new HTTP route is needed.
   `ControlPlaneSecurityConfig.strict_defaults()`, request-size limits, verified
   bearer/proxy identity, operator/backend mutation roles, target scope after
   either authentication mechanism, idempotency fingerprints, and audit events
   continue to guard submission. Domain authority material is never derived
   from a caller token.
5. **Secret handling and env binding.** There is no incumbent libvirt env-secret
   shape, so none is introduced. Secrets are generated or resolved behind an
   injected driver boundary, represented only by opaque in-memory handles, and
   excluded from target/manifest/envelope serialization, CLI args, environment,
   portable payloads, logs, diagnostics, and evidence.
6. **Guest/host OS and network exposure.** Subprocess leaves use fixed argv,
   no shell, bounded input/output/time, and no secret argv/environment. Temporary
   media and files reuse symlink/ownership/mode safeguards and are removed after
   use. Controller IPs come from ownership-correlated libvirt/guest observation,
   never by interpreting ACES addresses. DNS resolution, clock agreement,
   routing, required AD protocol reachability, and member/controller network
   overlap are checked before join. No host port forwarding or public exposure
   is added by default, and backend augmentation must not silently weaken an
   authored ACL.
7. **Errors and observability.** Stable package-local diagnostic codes carry a
   safe ACES address/stage and generic message. Raw native XML, paths, process
   output, directory dumps, credentials, backend reprs, and `str(exc)` do not
   cross the driver boundary. Existing type-only backend-call errors and generic
   API 500 handling remain intact; logging is supplemental, not evidence.
8. **Persistence and evidence.** `LocalControlPlaneStore` persists full snapshot
   and operation payloads, so only portable domain/principal/controller
   identities may enter them. Guest facts pass redaction, binding, freshness,
   completeness, and artifact validation before atomic evidence persistence.
   No secret or raw observation is stored in snapshot metadata or result details.
9. **Cleanup and read authorization.** Success and failure both verify removal
   of run-local secrets/artifacts and the intended state of owned directory and
   libvirt objects. Existing snapshot/operation read authorization is not
   widened by the new evidence path.

## Extensibility Seam

The seam is the existing normalized `driver_mode` selecting a versioned libvirt
envelope and staged driver implementation. The private realizer is parameterized
by the admitted `DomainTopologyBinding`, domain-bound account placements, the
explicit ordered controller candidates, bounded stage/overall deadlines, and
the mode's fixed image/network/guest-transport/bootstrap-leader policy. Material
policy is configuration identity and must be fixed by or represented in a new
envelope revision; it is not an unbound runtime toggle.

The next reasonable variation—Windows AD instead of an AD-compatible Linux
appliance, a second architecture, another credential-free join transport, or a
different deterministic bootstrap policy—adds another driver mode/envelope (or
a governed revision) behind the same seam. It must not require SDL changes, a
new topology DTO, a new capability dimension, a new control-plane route, a new
exception/store/evidence hierarchy, or edits to existing modes.

## Gotchas And Anti-Patterns To Avoid

- Do not restore `spn` to a generic envelope while its implementation is a
  marker file, and do not call snapshot payload preservation realization.
- Do not make `reference-emulation` claims stand in for `libvirt-qemu` behavior,
  or give both backends a shared mutable manifest/capability table.
- Do not use controller tuple order as an undocumented authored “primary,” use
  a controller outside the explicit candidate set, or infer failover from DNS.
- Do not assume dependency order, an active VM, ping, a listening port, package
  presence, or cloud-init completion proves directory readiness or membership.
- Do not pass passwords to `setspn`, `samba-tool`, `realm`, `adcli`, PowerShell,
  or any other process through argv, command text, environment, user-data, or
  the kernel command line. Do not expose a general guest command channel.
- Do not silently override member DNS, routing, time, or ACL intent. Reject a
  topology the selected mode cannot connect safely.
- Do not use an unbounded directory query or record tickets, keytabs, password
  hashes, raw LDAP/Kerberos output, native ids, or full principal inventories as
  evidence.
- Do not treat SPN assignment as a local account property. Enforce directory-
  global uniqueness and exact principal ownership; a collision is a blocking
  diagnostic, not permission to move or overwrite a foreign SPN.
- Do not ignore unchanged controllers needed by a changed member/SPN, or allow
  partial delete/update to leave stale machine accounts and SPNs in a surviving
  domain.
- Do not add a second validator, payload parser, concern enum, report writer,
  credential service, logger, persistence store, or backend exception hierarchy.
- Do not let fake-driver tests or a self-skipped native test certify the claim.
  Hermetic tests cover admission, stage ordering, replay, failure, mutation,
  rollback, redaction, and cleanup; an opt-in real-libvirt run through the
  production control-plane/evidence path supplies the claim-bearing proof.
- Do not copy the self-hosted proof host's permissive QEMU/root security
  settings into production defaults. Host hardening exceptions belong only to
  an isolated disposable proof environment and must be explicit.

## Non-Goals And Implementation Boundaries

- No implementation of issue #776 in this preflight.
- No change to ADR-082 topology meaning, SDL syntax, observed runtime identity,
  account schema, plan schema, control-plane API, or participant visibility.
- No general secret store, credential distribution protocol, remote shell,
  directory administration API, universal image registry, or backend-neutral
  domain-realizer framework.
- No claim for trusts/forests, cross-domain joins, group policy, federation,
  cloud directory tenancy, generic LDAP/Kerberos realization, arbitrary Windows
  images, or workloads outside the selected envelope.
- No widening of generic, TechVault, guest-certified, or reference-emulation
  configurations without independent operational evidence for each material
  configuration.
- No implementation logic under `implementations/python/src/aces/`, no
  changelog/version edits, and no partial edits to governed schemas or generated
  artifacts.
