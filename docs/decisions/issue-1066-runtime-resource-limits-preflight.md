# Issue 1066 Runtime Resource Limits Preflight

Date: 2026-08-09

Issue: #1066. Requirement: SEM-218; the issue supplies the concrete acceptance
contract for this extension of the existing realization-semantics authority.

This note records the repository-wide boundary for portable runtime process
limits. It does not implement the SDL, processor, backend, scenario, or
conformance changes.

No new ADR is required. ADR-030 already keeps process-scoped policy under its
policy owner while using `RuntimeProcessIdentity` only as selector/evidence;
ADR-033 separates authored runtime state from delivery mechanics; and SEM-218
plus the issue #985 preflight own exact, constrained, and open realization.
This note applies those decisions to the part of `RuntimeOperationalPolicy`
that issue #985 deliberately left for a separate policy review.

## Decision

### Keep portable process limits under the operational policy

The semantic owner is
`Node.runtime.operational_policy.resource_limits`, not
`RuntimeContainerConfiguration`. The existing `memory`, `memory_swap`, `cpu`,
and `pids` fields describe node/container capacity enforcement. Process limits
are a distinct child collection on the same resource-policy owner.

Each process-limit record must carry:

- a governed, backend-neutral resource term, initially
  `open_file_descriptors` (a count) and `locked_memory_bytes` (bytes);
- explicit `soft` and `hard` values, each a non-negative integer, the closed
  `unlimited` sentinel, or a whole-field variable reference;
- a `RuntimeProcessIdentity` subject used only as a selector/evidence anchor;
  and
- explicit `process` or `subtree` scope, reusing the scoped-capability
  semantics from ADR-030.

At least one structural subject selector must be present. A description alone
does not identify a process. Concrete finite values must satisfy
`soft <= hard`; `unlimited` is above every finite value. Duplicate records for
the same normalized `(resource, subject, scope)` are invalid. Omission means no
authored requirement; an explicit empty collection means exact absence when
the field itself was authored.

This shape preserves the fact that a container runtime normally applies an
RLIMIT to its initial workload process and its descendants while permitting a
VM or native-OS backend to target a service process. A backend that can only
configure an initial process subtree may accept only a subject it can
unambiguously correlate with that subtree. It must reject other selectors or
scopes rather than broadening the limit to every process on the node.

`nofile`, `memlock`, Compose maps, OCI JSON, systemd directives, PAM files,
libvirt XML, `/proc` column labels, and magic `-1` values are backend dialects
or evidence sources, not SDL vocabulary. Translation to those forms happens
inside a driver after typed validation.

The current scalar `RuntimeResourceLimits.open_files` cannot remain a second
semantic authority. Its published-schema migration is governed by ADR-061 and
ADR-075: either replace it at the applicable version boundary or accept it only
as a diagnosed legacy input normalized immediately to the structured
`open_file_descriptors` record. Never carry both representations into
explicitness, compilation, snapshots, or backend code; reject collisions.

The extensibility seam is the process-limit record plus the single concern
descriptor. Adding another portable process resource should add one governed
resource term, its unit/value validator, canonical projection coverage, and
explicit mappings in supporting drivers. It must not add a sibling SDL field,
a new concern, or another backend manifest shape. A genuinely new target or
inheritance meaning extends the typed subject/scope contract only after its
cross-runtime semantics are defined; it is never smuggled into a resource name.

### Keep adjacent resource meanings distinct

| Fact | Canonical owner | Must not be used as a substitute |
| --- | --- | --- |
| Memory/swap, CPU, and task-count capacity | existing `RuntimeResourceLimits` capacity fields | process address-space, CPU-time, or `RLIMIT_NPROC` policy |
| Open-descriptor and locked-memory soft/hard limits | structured process limits under `RuntimeResourceLimits` | Docker `ulimits`, VM memory, or a flat scalar |
| Subject and inheritance scope | process-limit policy using `RuntimeProcessIdentity` as selector | process inventory as a policy schema |
| Effective realized limits | canonical snapshot concern plus inside-workload observation | desired payload echo or daemon configuration alone |
| Datastore `memory_locked` | `RuntimeDatastoreNode` observed engine posture | proof that `locked_memory_bytes` was configured or was sufficient |
| Health/readiness checks | `conditions`; readiness results remain evidence | a new readiness realization concern or service-family default |
| Native spelling and host ceiling | selected backend/apparatus configuration | authored scenario intent |

A known component requirement is a component constraint, not a backend
default. For this issue, scenarios with known OpenSearch/TechVault needs should
materialize those requirements once in the node's process-limit policy. Do not
infer limits from an observed datastore engine, listener, readiness state,
image name, or the static service-family registry. If reusable component
profiles later become an authored source, their constraints must be lowered
with provenance into this same node policy and conflict-checked there; they
must not create per-service duplicate limit schemas.

Backend selection is permitted only when the author or apparatus deliberately
leaves the concern open or constrained. The native mechanism and host ceiling
are apparatus facts. The concrete selected values are backend-realized state
and must be disclosed as such.

## SEM-218 Realization Boundary

Register one node concern for the authored process-limit collection:

| Authored path | Concern kind | Plan/snapshot payload path |
| --- | --- | --- |
| `nodes.<node>.runtime.operational_policy.resource_limits.process_limits` | `process-resource-limits` | `spec.node.runtime.operational_policy.resource_limits.process_limits` |

Do not register the whole operational policy, restart behavior, or the existing
capacity fields as part of this concern. `raes_processor.semantics.realization_concerns`
remains the single descriptor registry. Registration, compilation, support
admission, nested open designation, canonical projection, observation
validation, runtime comparison, sanitization, and disclosure must all consume
the same descriptor. Do not add parallel path/kind tables or per-backend
concern names.

The canonical projection must retain resource, soft/hard values, normalized
structural subject selectors, and scope; omit descriptions and native evidence;
require an omitted command plus another stable projected selector when
`command_redacted` is true; and sort by the semantic `(resource, subject,
scope)` identity. The same normalized selector matches `runtime.processes`,
detects duplicates, and drives projection/runtime comparison. Exact comparison
includes the whole set: omission, substitution, or an excess record is a
mismatch. The closed observation validator must reuse the SDL models rather
than accepting a free dictionary.

Exact process limits require configuration-scope corroboration backed by an
effective, inside-workload readback. For Linux targets that means a bounded
typed projection of the selected process's effective soft/hard limits, with
`guest-observed` strength where the existing vocabulary applies. Container or
hypervisor inspect data can corroborate requested configuration but cannot by
itself establish the running process limit or a readiness claim. Raw `/proc`
output, native inspect documents, PIDs, and runtime ids stay private.

The current constrained runtime evaluator records a differing valid value as
`backend-realized` but does not prove that it belongs to the author's allowed
domain. Issue #1066 must not inherit that gap. Extend the existing
`CapabilityConstraint` / instantiation-provenance carrier and its compiled
constraint representation to preserve finite variable domains for process-
limit leaves, then enforce membership against the canonical realized record.
Constraint identity must follow the semantic limit identity and leaf, not a
backend spelling or post-sort list position. If numeric intervals are needed,
extend the existing bounded-domain/realization-envelope vocabulary; do not add
string-encoded ranges or a separate “limit constraint” schema.

For open posture, `OPEN_REALIZATION` support is capability, not permission by
itself. The author designation and selected apparatus configuration/envelope
must bound which resources and values may be chosen. A backend must not claim
open support until that boundary is expressible. Every non-empty backend choice
is projected into the snapshot and receives `backend-realized` provenance.

The same selected backend envelope configuration must repeat the exact typed
resource, scope, and numeric/unlimited domain claimed by the compatible global
support declaration for exact, constrained, and open scenarios. Planning and
runtime evaluation admit only those repeated claims, so a capability belonging
to another backend mode cannot authorize the selected mode. Do not use the
manifest's free-form `constraints` map or a concern-wide support claim as a
substitute for configuration-specific value-domain admission.

Unsupported exact, constrained, or open posture fails in existing planning and
envelope admission before mutation. A missing, invalid, weakly observed, or
out-of-domain result fails through `_call_backend_apply()` with
`runtime.backend-contract-invalid`, returns the baseline snapshot, and never
reports successful realization.

## Supported-Target Inventory

| Target in this repository | Current mechanism | Issue #1066 boundary |
| --- | --- | --- |
| Reference in-process driver | portable handles only; no OS resource control | unsupported; do not echo planned limits or widen its manifest |
| Reference OCI driver | fixed-argv Docker/Podman `run`; `ContainerSpec` has no limits | extend the portable spec only; map closed terms to native arguments privately, and advertise support only for a driver mode with effective readback |
| Generic libvirt | `DomainSpec` carries VM memory/vCPU; cloud-init is available | VM allocation is not process policy; support needs typed guest/service materialization plus inside-guest readback, otherwise reject |
| TechVault libvirt | configuration-bound envelope and daemon XML readback | XML memory/vCPU observation cannot prove process RLIMITs; remain unsupported unless the appliance and fact channel gain complete support |
| Guest-certified libvirt | challenge-bound, bounded inside-guest fact channel | the existing guest-observation channel is the extension seam for effective limits; a new claim still needs configuration/materialization support |
| Stub backend | test-only declared behavior | use only for negative/contract fixtures; do not make the shipped stub an honest-support claim |

The libvirt realization-envelope `resource-allocation` concern currently means
VM memory/vCPU. It is a separate taxonomy from SEM-218 concern kinds and must
not be renamed or overloaded for process limits.

The RAES repository contains no APTL source and no exact copy of APTL #909's
fixed values. The issue contract establishes that APTL currently injects
`nofile` and `memlock` into every image-backed node; the exact downstream
soft/hard values were not independently retrievable during this preflight.
Those values are migration evidence owned by APTL #909, not defaults to guess
or encode in RAES. RAES must ship a per-node portable contract and evidence
surface that lets APTL remove the universal fallback; APTL owns the actual
fallback retirement and its before/after regression fixture.

## Canonical Incumbents

The implementation must build on:

- SDL shape/parsing: `raes._base.SDLModel`,
  `raes.runtime_configuration`, `raes.runtime_capabilities`, shared
  `runtime_values` parsers, `parse_sdl()`, `_source_profile.SDLParserLimits`,
  and the bounded safe-YAML/source validation path;
- semantic and phase validation: `raes.validator.SemanticValidator`,
  `SDLValidationError`, `instantiate_scenario()`, `SDLInstantiationError`,
  explicit `model_fields_set`, concrete revalidation, and the existing
  `CapabilityConstraint` / `ExpansionProvenance` / `InstantiationProvenance`
  chain;
- author posture: `raes.explicitness`, `raes.realization_designation`, and the
  SEM-218 weakest-child classification rules;
- compilation/admission:
  `raes_processor.compiler.realization_requirements`,
  `CompiledRealizationRequirement`, the existing node resource payload,
  `realization_support_diagnostics()`, `realization_envelope_diagnostics()`,
  and canonical envelope `subsumes()` / domain membership;
- concern comparison:
  `raes_processor.semantics.realization_concerns`,
  `realization_concern_projections`,
  `realization_concern_observations`, and
  `realization_runtime_evaluation`;
- apparatus claims: `RealizationSupportDeclaration`,
  `RealizationObservationCapability`, `BackendManifestV2Model`,
  `RealizationEnvelopeModel`, `ObservationStrength`, and
  `RealizationVerificationScope`; no per-limit support booleans;
- execution/errors: `raes_runtime.backend_calls._call_backend_apply`,
  `Diagnostic`, `ApplyResult`, the realization-disclosure path, and the
  existing fail-closed backend exception reduction;
- observation/persistence/API: `RuntimeSnapshot`, `SnapshotEntry`,
  `RealizationProvenanceEntry`, `RealizationObservationDisclosure`,
  `RuntimeSnapshotEnvelopeModel`, `ControlPlaneStore`,
  `LocalControlPlaneStore`, the API conversion helpers, and existing operation
  and audit envelopes;
- backend seams: reference `ContainerSpec` / `DeploymentDriver` / OCI runner,
  libvirt `DomainSpec`, cloud-init and mode-specific admission, and the
  challenge-bound guest fact channel; and
- contract/workflow governance: the four published SDL-containing schemas
  (authoring input, instantiated scenario, instantiated snapshot, and
  satisfiability evidence), `schema_bundle()`, schema-publication entries,
  generated-schema parity, `.ground-control.yaml`, `.gc/plan-rules.md`, repo
  policy, requirement-governance handling for a requirement-free issue, and
  `tools/verify_all.py`.

## Cross-Cutting Security And Whole-Path Gates

1. **Source/parser gate.** Existing UTF-8, byte/scalar/depth/alias limits,
   safe YAML 1.2 loading, duplicate/merge-key rejection, canonical key rules,
   and `extra="forbid"` remain authoritative. The new surface is closed models
   and enums, never a native options map.
2. **SDL model gate.** Resource-specific units, finite/unlimited values,
   soft/hard ordering, selector presence, scope, duplicates, and legacy-field
   collision are local model invariants. Booleans, negatives, partial pairs,
   unknown resource names, and raw option fragments fail before semantics.
3. **Semantic/instantiation gate.** Subject selectors must agree with any
   authored process inventory where a resolvable identity is claimed.
   Variables remain value-only, preserve their domains and provenance, and
   concrete substitution reruns ordinary validation. Do not validate YAML or
   reclassify explicitness in the compiler.
4. **Contract/schema gate.** All four published embeddings and their
   publication-ledger entries move together with `schema_bundle()` parity.
   Updating only Python, only one JSON Schema, or only a generated artifact is
   invalid.
5. **Manifest/config/admission gate.** Exact, constrained, and open support,
   observation capability, configuration-bound envelopes, and concern
   disclosure use the existing manifest and planner. A global backend default
   or host capability is not authorization to add a limit.
6. **Backend-return gate.** `_call_backend_apply()` remains the sole acceptance
   boundary. It validates the closed observation, constraint membership,
   projection equality, corroboration, and provenance before accepting or
   persisting a snapshot.
7. **Authentication/authorization gate.** This issue adds no endpoint or role.
   Snapshot access continues through `ControlPlaneSecurityConfig.strict_defaults()`,
   verified identity/bearer handling, backend/operator/auditor authorization,
   target binding, request-size limits, idempotency, and audit recording.
8. **Secret/config-binding gate.** Limit values are non-secret and need no new
   environment or credential binding. Process selectors retain existing
   command-redaction rules. Do not place environment values, credentials, raw
   commands, host paths, or native inspect output in the policy, snapshot,
   evidence, fixture, log, or diagnostic.
9. **Host/OS and argv gate.** Reference OCI materialization continues to use
   the runtime allowlist, fixed tokenized argv, no shell, bounded timeout and
   output, ownership checks, and private native-id bookkeeping. Only validated
   enum-to-option mappings and formatted numeric/unlimited values may reach
   argv. VM/native materialization uses typed cloud-init/service configuration,
   not author-supplied shell fragments. No secret is introduced into argv.
10. **Error-envelope/logging gate.** Reuse stable `Diagnostic` codes and
    operation envelopes. Messages may name the portable address, field path,
    concern kind, and coarse omission/mismatch/unsupported reason; they must
    not include raw `/proc`, inspect/XML, argv, native ids, stderr, traceback,
    or backend exception text. No new exception hierarchy or logging stack is
    justified.
11. **Observation/persistence gate.** Persist only the canonical portable
    limits, value-free observation disclosure, and existing provenance. The
    native readback remains bounded and private. Desired-payload echo,
    successful process start, or `memory_locked=true` is not independent limit
    observation.

## Conformance Guardrails

The conformance surface must distinguish:

- absent under closed posture (no requirement and no fallback) from explicitly
  empty exact policy (no excess limits admitted);
- exact finite and unlimited soft/hard pairs, including reordered equivalent
  records;
- constrained finite domains, with accepted and out-of-domain backend choices;
- intentionally open selection with and without author/apparatus permission;
- unsupported resource, target, selector, scope, and observation strength;
- omitted, substituted, weakened, broadened, and excess limits;
- false substitutions such as cgroup `pids` for process count, VM memory for
  locked memory, or datastore `memory_locked` for the enabling RLIMIT; and
- backend failure after attempted realization, proving the baseline snapshot
  is retained and success is not reported.

Backend matrix tests must keep reference in-process and unsupported libvirt
modes negative. A supporting real backend needs materialization plus effective
readback tests; plan echo is insufficient. Schema parity, explicitness,
constraint-provenance round trips, snapshot store/API round trips, stable
diagnostics, argv tokenization, and redaction are part of the same conformance
claim, not optional unit-test extras.

## Gotchas And Anti-Patterns

Avoid:

- putting portable limits in `RuntimeContainerConfiguration` or exposing a
  Compose/Docker `ulimits` dictionary;
- treating cgroup capacity, POSIX process limits, VM allocation, engine memory
  lock state, and readiness as one resource concept;
- applying a known OpenSearch/TechVault limit to every image-backed node;
- keeping scalar `open_files` and structured open-file limits as parallel
  authorities;
- using native names, host units, magic `-1`, raw `/proc` columns, or arbitrary
  strings in the portable model;
- attaching policy semantics to process inventory or using a description as a
  process selector;
- inferring requirements from an image, datastore engine, listener, service
  family, or readiness result;
- preserving only the `constrained` label while dropping its allowed domain;
- allowing `OPEN_REALIZATION` manifest support to create undeclared defaults;
- comparing only requested records and ignoring excess realized limits;
- claiming exact support from desired-payload echo, container/VM existence, or
  daemon configuration without effective process readback;
- advertising one manifest for reference driver modes with different honest
  support, or widening stub/libvirt manifests to keep scenarios green;
- overloading libvirt `resource-allocation` or creating per-backend manifest,
  schema, validator, exception, persistence, logging, or workflow paths; or
- retiring the downstream fallback before APTL consumes per-node limits and
  proves its exact current baseline was removed only where replaced.

## Non-Goals And Boundaries

- No issue implementation is performed by this preflight.
- No complete POSIX RLIMIT catalog, Windows Job Object model, Kubernetes
  resource dialect, host kernel tuning, cgroup redesign, or scheduler quota
  model.
- No new top-level SDL section, component-profile registry, service-family
  defaults table, readiness concern, parser, exception hierarchy, logging
  stack, API endpoint, persistence store, or secret/config channel.
- No reinterpretation of existing memory/CPU/pids capacity, datastore
  `memory_locked`, service-manager inventory, participant resource budgets, or
  libvirt VM `resource-allocation` evidence.
- No claim that every backend must support every process limit. Unsupported
  binding requirements reject; honest lack of support is preferable to an
  approximation.
- No RAES-owned numeric default for OpenSearch. Component/scenario authors or a
  governed apparatus boundary own allowed values; APTL #909 owns its downstream
  baseline capture and fallback retirement.
