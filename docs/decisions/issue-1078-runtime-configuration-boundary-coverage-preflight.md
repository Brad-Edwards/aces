# Issue 1078 Runtime-Configuration Boundary Coverage Preflight

Date: 2026-09-03

Issue: #1078.

Status: architecture guidance only. This note inventories the current boundary
and fixes guardrails for implementation; it does not change SDL, compiler,
planner, runtime, backend, schema, or persistence behavior.

## Decision Boundary

No new realization mechanism or new ADR is justified. ADR-004 owns the
compile/plan/execute direction, SEM-218 owns explicitness and realization
designation, ADR-070 owns the author/capability/envelope intersection, issue
#985 established the canonical concern descriptor, and issue #1067 established
the complete backend-facing `ProvisioningPlan.realization_authority` carrier.
Issue #1078 completes that architecture; it must not create a parallel
interpreter for `RuntimeConfiguration`.

Every authorable runtime path must have exactly one documented disposition:

1. a portable scenario-realization concern with a canonical projection,
   admission rule, scenario-significant closure universe, and readback rule;
2. desired state already owned by another compiler resource/concern, referenced
   rather than lowered again; or
3. observation, evidence, provenance, or apparatus state that is not an
   authorable realization value and therefore must live on its existing owner.

There is no valid fourth disposition in which a field remains authorable while
the realization pipeline silently ignores it. A description or evidence
reference may be a non-realization annotation, but its exclusion must be
explicit and must not weaken the concern's explicitness classification.

## Complete `RuntimeConfiguration` Inventory

The current model has 31 top-level fields. In the status column, **registered**
means the canonical descriptor exists; it does not mean either in-repository
backend materializes or independently verifies the concern. **Partial** means
only the named child/source kinds are covered. **Absent** means author posture
does not currently reach a SEM-218 concern.

| Runtime field | Existing semantic owner and overlap | Current SEM-218 status | Required boundary classification |
| --- | --- | --- | --- |
| `mounts` | Runtime mount contract; ADR-056 redaction. `persistent_volumes`, `generated_artifacts`, and content placement own stateful/materialized resources. | **Partial:** `runtime-mounts` covers only `bind`/`tmpfs`. | Direct concern for non-stateful attachments. `volume` and materialized image/content attachments stay with their owning resources; merely observed mounts stay evidence. `other`/`unknown` require a typed envelope, not unbounded acceptance. Never lower one target twice. |
| `filesystem_inventory` | ADR-037 filesystem presence/inventory; overlaps content placement, generated artifacts, packages/components, and evidence. | **Absent.** | Portable concern only for deliberately promoted, scenario-significant paths and their authored facts. File bytes/materialization remain with content/artifact owners; capture output remains evidence. Closure is over managed/promoted paths, never the whole guest filesystem. |
| `local_control_interfaces` | Path-local API shell in ADR-051; ADR-056 owns path sensitivity. Orchestration authority owns what the holder may do. | **Absent.** | Direct presence/configuration concern keyed by `control_interface_id`. It must not absorb orchestration authority or native socket handles. |
| `processes` | Supervised/load-bearing process identity; ADR-027 distinguishes container init, ADR-030/issue #1066 use it as a selector, ADR-035 distinguishes unit lifecycle. | **Absent.** | Direct concern for authored process identity/state, scoped to scenario-significant processes. Incidental daemons and raw process scans stay substrate/evidence. Ephemeral PID or inspection provenance must either be an explicit realizable steady-state fact or leave the authoring surface; it cannot be ignored. |
| `environment` | Runtime environment contract; ADR-056/057 own value classification and secret boundaries. | **Registered:** `runtime-environment`. | Keep the existing concern and commitment projection. Add honest backend materialization/readback; protected values prove posture/presence, not raw-value equality. |
| `linux_capabilities` | ADR-030 capability policy, including process-scoped overrides. | **Registered:** `linux-capabilities`. | Keep the existing family projection and process-selector semantics. It is not equivalent to `container.privileged`. Require effective guest/runtime readback for claims. |
| `operational_policy` | Restart/capacity policy; issue #1066 separately owns process resource limits. | **Partial:** only `resource_limits.process_limits` is `process-resource-limits`. | Split along existing meanings: restart policy, node/container capacity (`memory`, `memory_swap`, `cpu`, `pids`), and process limits are separate concern families. Do not make one weakest-child aggregate or duplicate process-limit bounds. |
| `container` | ADR-027 init/PID-1; ADR-028 seccomp/security options; ADR-023 keeps image defaults distinct. | **Absent.** | Split portable launch, namespace, filesystem/security, device, resolver, and engine-selection concerns where their admission/readback domains differ. Backend-native options use bounded typed capability/envelope admission. Do not register the entire object as one concern. |
| `local_identity` | ADR-024 local users/groups/sudo inventory. Top-level `accounts` owns curated account provisioning and credential bindings. | **Absent.** | Direct concern only for promoted local identity records, keyed in their existing namespaces. Never compile them as account placements. Base-image/package-created accounts are incidental unless promoted; raw sudo text is evidence/annotation and redacted command posture stays value-free. |
| `identity_authorities` | ADR-032 directory/domain/realm logical state; top-level identity domains and accounts remain distinct. | **Absent.** | Family-specific configuration/presence concern using existing stable IDs and reference validation. Subject/policy settings retain closed redaction. Do not turn this inventory into a provisioning-command or provider schema. |
| `file_services` | ADR-037 file-service logical state; filesystem paths, top-level accounts, and transport services remain separate. | **Absent.** | Family-specific concern keyed by the existing service/child IDs. Credential strength is posture only; raw credentials remain unrepresentable. Access observations/evidence are not materialized configuration. |
| `mail_services` | ADR-038 mail logical state; DNS, transport, accounts, filesystem, and relationships own adjacent meanings. | **Absent.** | Family-specific concern. Split stable configuration/logical state from queues, observations, and evidence where those are outcomes. Preserve the existing no-raw-credential and setting-redaction rules. |
| `network` | ADR-025 required runtime network identity/attachments; infrastructure owns topology and `Node.services` owns transport declarations. | **Partial:** only `published_ports` is registered. | Separate hostname/domain identity, endpoint attachment/addressing, bounded backend/IPAM detail, and published-port concerns. Generated IDs/inspect output stay evidence. Backend details are admitted only by typed capabilities/envelopes. |
| `service_listeners` | ADR-043 in-node bind state; distinct from `Node.services`, published ports, and readiness evidence. | **Registered:** `service-listeners`. | Keep the existing bind projection and stable ID. Readiness/evidence remain outside value comparison. Add independent bind observation; plan echo is insufficient. |
| `applications` | ADR-026 participant-observable HTTP route/API/UI surface. | **Absent.** | Family-specific route/configuration concern keyed by application/route IDs. Transport, host publication, filesystem content, vulnerabilities, and test observations retain their owners. Sensitive exposed values use existing commitments/redaction. |
| `database_services` | ADR-029 relational database logical state; content placement/service materialization may own initial rows/schema materialization. | **Absent.** | Family-specific concern for engine/configuration and promoted logical objects. Do not duplicate content materialization, account provisioning, app authorization, or database observation evidence. Built-in/incidental objects need origin-aware closure. |
| `dns_services` | ADR-039 DNS logical/protocol state; network resolver/attachment, services, files, and content remain separate. | **Absent.** | Family-specific concern with zone/RRset stable identities. Zone-file bytes and observations remain with content/files/evidence owners. |
| `network_sensors` | ADR-042 monitoring posture; infrastructure owns attachment and evidence contracts own captured traffic/results. | **Absent.** | Configuration/presence concern for authored apparatus or system-under-test inventory. Monitoring effectiveness and captured telemetry are propositions/evidence, not realization values. Ownership/visibility classification must survive without becoming backend permission. |
| `network_detection_engines` | ADR-044 engine configuration/inventory; ADR-045 owns parsed detection-definition semantics. | **Absent.** | Family-specific concern for promoted engine/rule-source/control configuration. Loaded outcomes, alerts, raw rules, and telemetry remain evidence/content owners. |
| `security_monitoring_managers` | ADR-040 manager inventory and ADR-045 detection definitions; listeners, processes, units, files, forwarding, and evidence are adjacent owners. | **Absent.** | Family-specific concern for promoted configuration/logical state. Do not use it as a generic service, process, content, or telemetry aggregate. Sensitive settings use the established value-free projection. |
| `ssh_servers` | ADR-031 SSH policy; service listener/unit/account/process families own their own facts. | **Absent.** | Direct SSH configuration concern. Forced-command redaction remains structural; session IDs, keys, and operator credentials must not enter projection, diagnostics, or argv. |
| `datastore_services` | ADR-048/058 non-relational datastore logical state and node/endpoints; ADR-088 content materialization owns initial service content. | **Absent.** | Family-specific concern with existing service-wide stable-ID namespaces and profile guards. Split configuration from live counts/timestamps/outcomes; do not duplicate app authorization or service materialization. |
| `platform_applications` | ADR-049 platform logical state. Capability entries classify function and do not imply configuration, content, execution, or proof. | **Absent.** | Family-specific concern for authored application/configuration state. A capability label is never materialization evidence; content and authorization remain on their owners. |
| `forwarding_agents` | ADR-050 forwarding spine; ADR-066 and issue #1043 own apparatus/system-under-test ownership and evidence binding. | **Registered:** `forwarding-agents`. | Keep the concern projection and role exclusion. Require presence/configuration readback according to scope. Ownership role affects provenance/evidence direction, not realization mode or visibility. |
| `orchestration_authorities` | ADR-051 spawn authority; local control interface owns the shell and runtime children are observations. | **Absent.** | Concern for authority configuration and spawn templates, referencing the existing control-interface ID. `realized_children` and execution outcomes are observation/evidence, not permission or desired children by implication. |
| `app_authorizations` | ADR-046 application-internal RBAC; directory identities and database grants are separate. | **Absent.** | Family-specific logical-state concern using existing principal/role/grant IDs and resource-vocabulary validation. Credentials remain classification-only and value-free. |
| `scheduled_jobs` | ADR-047 recurrence configuration plus observed run state; units and event relationships are separate. | **Absent.** | Concern for identity, enabled state, command reference, and cadence. Last/next run and result are observation/evidence unless explicitly retained as a governed steady-state claim; they may not weaken configuration posture. |
| `service_manager_units` | ADR-035 service-manager unit lifecycle; services, processes, init, restart policy, SSH policy, packages, and files remain separate. | **Absent.** | Split unit configuration/presence/enablement from live PID, result, exit code, status text, and journal evidence. Closure covers scenario-significant units, never every unit supplied by the OS. |
| `packages` | Package-manager rows; ADR-034/056 and issue #417. Source artifact requirements own acquisition/trust, not installed final state. | **Absent.** | Direct installed-state concern at package-row granularity. Base image and transitive dependency packages are incidental unless promoted; exact closure is not a demand to remove the OS package closure. |
| `software_components` | ADR-034 component identity and lineage; source artifact/SBOM/scanner evidence remain distinct. | **Absent.** | Direct final-state concern keyed by `component_id`. PURL/CPE/hash/path constraints are component facts; scanner method/output and raw SBOM remain evidence. Package/manifest refs are lineage, not duplicate installation concerns. |
| `dependency_manifests` | ADR-034 manifest-file final state; filesystem inventory and source/evidence artifacts overlap. | **Absent.** | Direct manifest-presence/identity concern keyed by a canonical ecosystem/path identity. Resolved dependency graphs and raw manifest bodies remain evidence/content unless separately authored. |

This inventory deliberately does not equate “authorable” with “one concern per
field.” `operational_policy`, `container`, `network`, and the mixed
configuration/outcome service families require several concern boundaries.
Conversely, stateful resources, content materialization, account placement, and
source-artifact satisfaction already have owners and must not be copied into a
runtime concern.

## Current Loss And Ambiguity

- Four top-level fields have a descriptor at the field root (`environment`,
  `linux_capabilities`, `service_listeners`, and `forwarding_agents`), three are
  partial (`mounts`, `operational_policy`, and `network`), and 24 are absent.
  An absent path may be classified by `raes.explicitness` and targeted by a
  valid realization designation, but it never becomes compiled concern
  authority, a complete plan-authority entry, backend admission, runtime
  comparison, or evidence.
- Issue #1067 preserves closed omission only for the canonical registered
  universe. It therefore cannot close an unregistered runtime dimension.
- Aggregate explicitness currently follows the weakest child while several
  projections exclude `description`, `evidence_refs`, readiness, or ownership.
  Classification and comparison can therefore describe different semantic
  surfaces. Non-realization annotations and observation outcomes must be
  removed before concern classification, or placed in a separate concern;
  they must not turn exact configuration into open/constrained posture.
- Exact equality currently compares the projected value found in the returned
  `SnapshotEntry.payload`. Reference and libvirt provisioners populate that
  payload from the submitted operation, while their node/domain specs do not
  carry most runtime fields. For descriptors without a required verification
  scope/strength, plan echo can pass as realization. This affects the trust
  value of the existing environment, mount, capability, published-port, and
  listener paths.
- `process-resource-limits` and OS identity have explicit guest-observed bars;
  forwarding agents declare presence/configuration scope. The other current
  runtime descriptors do not uniformly require independent corroboration.
- Both in-repository manifests use the generic exact token
  `declared-capability-match`, and both advertise only a compute-substrate
  observation capability. That token must not be read as per-concern runtime
  implementation. A backend may claim a concern only when its adapter
  materializes the complete projection and its declared observation capability
  can prove it.
- The APTL code in this repository is an allowlisted, external-summary evidence
  adapter, not the downstream APTL backend. It checks authored scenario digest
  and compiled address sets but cannot establish #1078 backend completeness.
  The portable plan/schema/fixture contract is this repository's boundary;
  Brad-Edwards/aptl#869 remains downstream work.

## Collection Closure And Ownership

Closed-world excess detection needs an explicit observation universe for every
collection. The universe is the set of scenario-significant entries managed or
selected under that concern, identified by its existing semantic key and
ownership/readback provenance. It is not every native entry visible to `ps`,
`rpm`, `/etc/passwd`, `systemctl`, or a recursive filesystem walk.

- **Exact** requires equality of canonical managed identities and every exact
  projected leaf. Missing, substituted, or extra scenario-significant entries
  fail.
- **Closed/omitted** rejects any backend-added scenario-significant entry. It
  does not reject dependency closure, base-image files/packages/accounts,
  native handles, or measurement apparatus carried by their proper owners.
- **Constrained** preserves the exact stable identity set unless the concern's
  typed bound explicitly permits identity selection, and applies existing
  `DomainDescriptor` or concern-owned structured bounds to the selected leaves.
- **Open** admits backend choices only from the descriptor's typed
  capability/envelope domain and closure universe. It is not acceptance of an
  arbitrary JSON object or all native inventory.

Each collection family owns its identity and excess semantics. Reuse the IDs in
`RUNTIME_SERVICE_FAMILIES`, filesystem path, environment name, mount target,
package ecosystem/manager/name/architecture identity, and component ID as
applicable. Do not invent one universal aggregate model, list-order equality,
or one “runtime is open” bit.

## Architecture Decisions And Extensibility Seam

`raes_processor.semantics.realization_concerns.RealizationConcernDescriptor`
remains the only realization registry. Extend that incumbent only with the
metadata needed to make each concern total:

- authored and plan-payload paths plus precise applicability;
- stable semantic identity and canonical comparison projection;
- an ownership/observation selector that defines the scenario-significant
  closure universe;
- closed observation-shape validation and a persistence sanitizer;
- a concern-owned typed capability/envelope admission profile; and
- required verification scope and observation strength.

Those are descriptor hooks, not a new generic runtime schema. Family-specific
projectors and typed bounds remain appropriate because a file inventory, RBAC
graph, process selector, and service configuration do not share one collection
algebra. `RUNTIME_SERVICE_FAMILIES` remains the authority for family names,
stable IDs, child references, composition, and import rewriting; the concern
registry may consume that metadata but must not duplicate it or automatically
turn every registered family into one aggregate concern.

The backend-facing seam is the existing total lookup over
`ProvisioningPlan.realization_authority`. Values stay in the owning operation
payload; policy stays beside operations. Reference, libvirt, and downstream
consumers must not parse `Scenario.realization`, recompute explicitness, or keep
their own kind/path/closure tables.

The next runtime family or portable leaf should register its identity,
projection, closure selector, typed admission, sanitizer, and observation bar
once and then flow through compiler, plan completeness, backend admission,
runtime disclosure, and conformance. The variation parameter is concern
profile/semantic identity, never backend product name.

## Canonical Incumbents To Reuse

| Cross-cutting concern | Canonical incumbent and guardrail |
| --- | --- |
| SDL shape and parsing | `raes._yaml_loader.load_sdl_yaml`, `SDLParserLimits`, `raes.parser`, `raes._base.SDLModel(extra="forbid")`, and the existing `SDLParseError`/`SDLValidationError`/`SDLInstantiationError` boundaries. The registry consumes typed models; it is not another parser or exception layer. |
| Runtime field validation | `raes.runtime_configuration`, `runtime_values`, `runtime_mounts`, `runtime_filesystem`, `runtime_container`, `runtime_identity`, `runtime_network`, `runtime_resource_limits`, and each typed service-family module. Preserve enum, path, port, uniqueness, profile, redaction, and cross-field validators. |
| Cross-model validation | `raes.validator.SemanticValidator`, including runtime services, identity data, platform/service references, stateful-resource destinations, materialization, network references, and process-limit selectors. Do not repeat these checks in projectors or backends. |
| Service-family identity | `raes._runtime_service_family_registry.RUNTIME_SERVICE_FAMILIES` and `_runtime_service_families`. Do not add another service family/name/child-ID registry. |
| Author intent | `model_fields_set`, `raes.explicitness`, `raes.realization_designation`, instantiated explicitness/designation provenance, and concrete revalidation. Do not infer intent from `model_dump()`. |
| Concern compilation | `realization_concerns`, `compiler.realization_requirements`, `CompiledRealizationAuthority`, and `CompiledRealizationRequirement`. Keep one kind/path/projection authority. |
| Resolved execution policy | `planner.realization_authority`, `ResolvedRealizationAuthority`, `RealizationAuthorityBound`, `DomainDescriptor`, selected realization-envelope identity, and issue #1067 completeness checks. No authoring designation crosses the backend boundary. |
| Capability and envelopes | `RealizationSupportDeclaration`, `RealizationObservationCapability`, `realization_support_diagnostics`, `realization_envelope_diagnostics`, and ADR-070 `member`/`subsumes`. Capability narrows author permission; it never creates it. |
| Adjacent desired state | Processor-derived `persistent-volume`, `generated-artifact`, service-content-materialization concerns; account placements/credential bindings; and ADR-098 source artifact requirements/satisfaction. Reference these owners instead of duplicating them. |
| Runtime enforcement | `raes_runtime.control_plane_submission`, `Provisioner.validate`, `_call_backend_apply`, `realization_authority_disclosure`, `evaluate_registered_realization`, observation matching, snapshot sanitization, and baseline restoration. Validation must finish before backend mutation and again before accepting returned state. |
| Evidence and observability | `RealizationObservationDisclosure`, `RealizationProvenanceEntry`, `ExperimentCaptureSpecModel`, `ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`, `ExperimentRealizedFormDisclosureModel`, ADR-064, and ADR-066. Selection provenance is not observation strength. |
| Secrets and commitments | ADR-056/057, `enforce_observed_value_redaction`, the closed credential-classification vocabularies, `raes_contracts.canonical`, concern projectors, and `backend_account_credentials`. Do not add a second redactor, hash format, or credential carrier. |
| Diagnostics and API | `Diagnostic`, `ApplyResult`, operation receipts/status, `runtime.backend-contract-invalid`, `ControlPlaneSecurityConfig`, `RuntimeControlPlane.record_audit`, `AuditEvent`, request-size/idempotency guards, and the redacted 422/500 handlers. No realization exception hierarchy or raw exception logging. |
| Persistence | `RuntimeSnapshot`, `RuntimeSnapshotEnvelopeModel`, `ControlPlaneStore`, store payload converters, and `LocalControlPlaneStore` temporary-file plus `os.replace` writes. Sanitize before this boundary; do not add a posture/evidence sidecar. |
| Schema/workflow | ADR-009/061, hand-governed `contracts/schemas`, `schema_bundle()`, contract fixtures, `schema-publication-manifest.json`, `.ground-control.yaml`, `.gc/plan-rules.md`, and `tools/verify_all.py`. Models, normative schemas, fixtures, hashes, and consumers move as one governed surface. |

## Cross-Cutting Security And Runtime Layers

The intended design must pass every existing layer below.

- **YAML/parser shape:** bounded safe YAML loading, alias/depth/node limits,
  canonical key handling, and closed SDL models run before classification.
  Concern payloads are never accepted as free-form alternative input.
- **Local and semantic validation:** all current typed field validators,
  duplicate-ID checks, redaction consistency, required-profile guards, and
  cross-reference/stateful/content/account rules remain authoritative. A
  projector rejects malformed observations but does not duplicate authoring
  validation.
- **Instantiation and designation:** substitution preserves
  `model_fields_set`, explicitness, parameter provenance, RFC 6901 scoped
  designation, namespace ownership, and concrete revalidation. Classification
  is over the concern's semantic projection, not serialized defaults or
  excluded annotations.
- **Published config shapes:** closed plan, backend-manifest-v2,
  realization-envelope, runtime-snapshot, and API DTO models reject unknown
  fields and invalid mode/source/bound combinations. If descriptor capability
  or observation metadata changes a published shape, the hand-governed schema,
  generated parity, fixtures, authority sets, and publication ledger change
  together. No environment binding or per-concern configuration flag is added.
- **Capability/admission:** author authority, matching support declaration,
  selected digest-bound envelope, typed bounds, and declared observation
  capability intersect before mutation. Generic
  `declared-capability-match` is not proof that a backend implements every
  exact concern.
- **Backend/OS boundary:** reference OCI work reuses the injected, bounded-time,
  fixed-argv, no-shell runner and private native readback; libvirt reuses its
  existing typed specs/drivers and trust/ownership checks. Environment values,
  tokens, enrollment material, private keys, mount options, and secret-bearing
  commands must not enter process argv, labels, native object names, XML, audit,
  stdout-derived handles, or diagnostics. Use an existing bounded protected
  input channel; if no safe channel exists, report the concern unsupported.
- **Backend-return and error envelope:** `_call_backend_apply` validates result
  type, address transitions, realization authority, projection, observation,
  credential egress, and snapshot sanitization before acceptance. Failure
  returns the baseline and the existing coarse structured diagnostic. API 422
  and 500 responses stay redacted; audit may record stable code and exception
  class, never raw payload/value/native error/traceback.
- **Persistence and reads:** only sanitized projections, value-free provenance,
  and authorized observation disclosures enter `ControlPlaneStore` and
  `RuntimeSnapshotEnvelopeModel`. Reads retain strict-default authentication,
  bearer or trusted-proxy verification, backend/operator/auditor roles, target
  binding, request-size bounds, idempotency, and audit. Authentication never
  makes a secret-bearing payload safe to persist.
- **Secret equality:** redacted/operator-secret members prove classification,
  omission, and presence posture only. Do not hash an absent value or publish a
  low-entropy operator secret verifier. Deliberately disclosed
  `secret_fixture` values may use the existing domain-separated JCS commitment;
  raw values remain on their authorized scenario owner and are not redisclosed.

## Whole-Repository Contract Surface

The implementation is complete only when these existing surfaces agree:

- SDL models, public exports, language metadata, authoring/instantiated
  schemas, examples, and semantic-reference documentation;
- explicitness, designation resolution, composition/import rewriting,
  instantiation provenance, and semantic validation;
- concern registry/projectors/observation validators, compiler requirements and
  authority, planner materialization/completeness, plan projection and reverse
  conversion;
- backend manifest support and observation capability, selected envelopes,
  control-plane submission, direct backend calls, runtime disclosure,
  snapshot sanitization/persistence, and authenticated API reads;
- reference backend portable specs plus in-process/OCI drivers and independent
  readback;
- libvirt portable specs, generic/TechVault admission, guest/native observation,
  and honest unsupported reporting; and
- language-neutral published contracts/fixtures consumed by external APTL. The
  in-repository APTL evidence summary is not a substitute backend gate.

## Conformance Guardrails

For every admitted concern family, the existing SEM-218 and plan-authority test
surfaces must cover exact, constrained, open, omitted/closed, unauthorized
excess, unsupported capability, out-of-envelope selection, malformed
observation, insufficient observation strength, and safe persistence. Collection
tests must distinguish an unauthorized scenario-significant addition from an
incidental dependency/base-image/OS/apparatus entry.

Coverage must exercise parser/model validation, instantiation and scoped
designation, compilation, total plan-authority completeness, published
schema/JSON round-trip, control-plane reverse conversion, backend pre-mutation
admission, backend handoff, independent observation, runtime non-approximation,
provenance, snapshot persistence, and redacted diagnostics. Reference and
libvirt must reject unsupported concerns rather than widening manifests or
echoing plan values. Stable inventory/service IDs, permutation invariance,
duplicate rejection, exact missing/substitution/excess, typed constrained
bounds, open envelope membership, and secret-bearing fixtures require explicit
cases.

An executable inventory assertion should keep the 31 top-level runtime fields
partitioned exactly once among registered, delegated, and observation-only
dispositions so a future `RuntimeConfiguration` field cannot silently bypass
SEM-218.

## Gotchas And Anti-Patterns

Avoid:

- one concern per top-level field without examining nested ownership;
- one aggregate “runtime configuration” concern or weakest-child posture for
  unrelated leaves;
- a second concern registry, service-family registry, path table, backend
  posture resolver, constraint schema, observation DTO, exception tree,
  redactor, persistence ledger, logger, or conformance workflow;
- treating `model_dump()` defaults as authored declarations;
- excluding a semantic field from comparison while still letting it determine
  aggregate explicitness;
- applying exact collection equality to the whole native OS inventory;
- treating base-image files/packages/accounts/processes/units, transitive
  dependencies, backend handles, or measurement apparatus as unauthorized
  scenario content;
- solving incidental-state collisions by making the author boundary broadly
  open;
- treating open as arbitrary JSON, backend defaults, or capability alone;
- treating generic exact support, a successful apply, a snapshot echo, or a
  matching commitment as independent readback;
- making backend-native IDs, paths, inspect maps, XML, Compose keys, or provider
  vocabulary portable identity;
- duplicating persistent volume, generated artifact, content materialization,
  account credential, source artifact, service, topology, relationship, or
  evidence semantics under runtime;
- placing readiness, run results, alerts, captured traffic, raw scanner/SBOM
  output, or orchestration children in configuration comparison merely because
  an historical model calls them runtime inventory;
- leaking raw values or native exception/output through snapshots, provenance,
  diagnostics, logs, audit, fixtures, schemas, API responses, process argv, or
  backend metadata; or
- widening reference/libvirt manifests to make tests pass before their adapters
  can materialize and independently observe the complete concern.

## Non-Goals And Implementation Boundaries

- This preflight does not implement issue #1078 or provide an implementation
  sequence.
- It does not add SDL fields, a universal runtime aggregate, a second
  realization carrier, a new backend API, a new persistence store, or a new
  exception/logging hierarchy.
- It does not reclassify raw capture, scanner output, readiness results,
  participant telemetry, or derived measures as authored scenario state.
- It does not make incidental dependency/substrate state or measurement
  apparatus subject to scenario collection closure.
- It does not merge top-level accounts, identity domains, content, generated
  artifacts, persistent volumes, services, infrastructure, relationships,
  source artifacts, or evidence into `RuntimeConfiguration`.
- It does not claim that reference, libvirt, or external APTL currently supports
  the newly inventoried concerns. Unsupported is a required fail-closed result.
- It does not audit or modify the external APTL repository; interoperability is
  defined here through the published plan, schemas, fixtures, and portable
  conformance expectations.
- It does not create raw operator-secret equality. Stronger secret verification
  would require a separately governed, value-free verifier contract.
