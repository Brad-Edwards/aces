# Issue 1077 OS distribution and version realization preflight

- **Status:** implementation guidance
- **Date:** 2026-08-12
- **Issue:** #1077
- **Requirement:** none; the issue is the authoritative contract

This note records the repository-wide semantic boundary for carrying authored OS
distribution and version through admission and realization evidence. It does not
choose a backend image-selection algorithm and is not an implementation plan.
Existing ADRs already own the relevant boundaries, so this note does not create
a new architectural decision.

## Current-state inventory

| Fact | Current authority | Current behavior and ambiguity |
| --- | --- | --- |
| OS family | `Node.os` and the `OSFamily` controlled vocabulary | Portable, broad family (`linux`, `windows`, and similar). It is captured as a capability constraint, registered as the SEM-218 `os-family` concern, and admitted against `ProvisionerCapabilities.supported_os_families`. |
| OS distribution or product line | No authored field | It is sometimes embedded in `Node.os_version` (`Ubuntu 22.04`, `Server 2022`) and is otherwise selected by a backend. No portable admission contract exists. |
| OS version or release | `Node.os_version: str` | The unconstrained string is parsed and serialized but is not captured by the processor, registered as a realization concern, admitted by the planner, or checked by runtime non-approximation. |
| Architecture | `Node.architecture` | An independent compute constraint with its own controlled vocabulary, capability domain, SEM-218 concern, and admission checks. It must remain independent of OS identity. |
| Source or artifact | `Node.source`, `Source`, and `ArtifactRequirement` | A provider-neutral artifact selector and, when authored, an independent realization requirement. `Source.version` is an artifact selector; it is not an OS release. Source identity must not imply OS intent. |
| Backend selection | Reference and libvirt realization interpreters plus configuration-selected capability envelopes | The reference backend uses `Source.name` or an OS-family fallback. Libvirt interprets `Source.name` as a local image path. Both ignore `Source.version` and `Node.os_version`; neither independently observes guest OS identity. |
| Realized OS evidence | No typed OS observation | Planned node payloads can echo authored fields, but an echo is not observation. `RealizationObservationDisclosure` is the canonical operation-bound evidence carrier and currently has no value-bearing OS identity payload. |

`Node.os` and `Node.os_version` entered the extracted SDL model together in
commit `2e73ee6c` without a validator or a documented relationship between them.
The only normative origin recorded for `os` is the OCSF-style family vocabulary.
No later history assigns `os_version` release-only semantics. The current model,
documentation, and examples therefore do not justify treating the existing
string as an already-normalized release.

The external APTL behavior described by issue #1077 is an ecosystem boundary,
not code in this repository: its generic selector accepts `os_version` but may
choose Debian 12 or Rocky Linux 9 from package-manager hints. This repository
must make that substitution impossible to claim as successful, but cannot
prescribe or certify APTL's selection implementation here.

## Existing scenario audit

The authored examples with populated `os_version` currently mean:

| Location | Current value | Intended interpretation to make explicit |
| --- | --- | --- |
| `hospital-ransomware-surgery-day.sdl.yaml` | `Server 2022`, `Server 2019` | Windows Server product line plus release |
| `hospital-ransomware-surgery-day.sdl.yaml` | `11` | Windows client product line plus release |
| `port-authority-surge-response.sdl.yaml` | `10`, `11` | Windows client product line plus release |
| SDL section documentation | `Ubuntu 22.04` | Ubuntu distribution plus release |

The test and stress corpus additionally contains Ubuntu releases, Windows Server
releases, `Solaris 10`, and `SIEMENS S7-300`. The first three groups have the
same distribution/product-line-plus-release ambiguity. `SIEMENS S7-300` is a
device/platform model and is not OS identity; it must move to the appropriate
platform, device, or source semantic instead of being carried forward as an OS
release.

Migration must audit these values explicitly. It must not split arbitrary legacy
strings by whitespace, infer distribution from capitalization, or preserve a
dual meaning in `os_version`.

## Semantic boundary

Portable authored OS identity has three separate dimensions:

1. **Family** is the existing broad `Node.os` constraint.
2. **Distribution/product line** is a governed portable token such as `ubuntu`,
   `windows-server`, `windows-client`, or `solaris`.
3. **Version/release** is a bounded, non-empty opaque token within that
   distribution/product line.

The authoring surface should add one distribution/product-line field and narrow
`os_version` to release-only meaning. A version requires a distribution, and a
distribution requires a family. Family alone remains valid. Architecture,
artifact/source identity, package manager, kernel, edition, image reference,
and device model are not aliases for any of these dimensions.

Distribution tokens need one controlled-vocabulary authority and the repository's
existing governed-extension mechanism. Version comparison is exact token
comparison unless an authored finite domain is present. Do not introduce SemVer
interpretation, numeric ordering, wildcards, `latest`, implicit case folding, or
an `other`/`unknown` distribution sentinel. Absence and SEM-218 designation
already express openness without sentinel values.

The existing SEM-218 classifier and realization-designation resolver remain
separate authorities:

- an authored concrete literal leaf is **exact**, except for the classifier's
  existing `other`/`unknown` enum sentinels, which are **open**;
- a whole-field variable is **constrained**; OS planning admission requires a
  finite `allowed_values` domain rather than treating an unbounded variable as
  portable backend permission; and
- an absent leaf has no classifier record and becomes an **open** realization
  requirement only when explicitly designated through `realization.scopes`.

This permits an author to constrain only `os: linux` while deliberately leaving
distribution and version open. The open designation belongs on the missing OS
leaf or leaves; it must not be fabricated through `Source`, an artifact
requirement, an image mechanism, `*`, or a magic version value. An omitted leaf
without an open designation remains absent rather than becoming an implicit
backend promise.

When OS identity and source/artifact requirements are both authored, they are
conjunctive. A selected artifact must satisfy the artifact contract and the
realized guest must satisfy the OS contract. Image names, tags, package-manager
hints, and artifact metadata may inform backend selection but do not rewrite
authored OS intent or independently prove the running OS.

## Planning and capability admission

The canonical SEM-218 registry in
`raes_processor.semantics.realization_concerns` must own separate
`os-distribution` and `os-version` leaf concerns, alongside `os-family` and
`node-architecture`. The processor's typed `NodeRuntime` projection and
top-level plan payload must carry the corresponding values; an opaque copy under
`spec.node` is not canonical planning authority.

`capture_capability_constraints`, `CapabilityConstraint`, instantiated
explicitness, realization requirements, and `CompiledRealizationAuthority` must
carry the same finite value domains. The planner and runtime must reuse the
bounded-domain algebra in `raes_contracts.bounded_domains` and
`scalar_in_domain`. Adding OS-only constraint syntax or allowing ordinary
constrained scalar concerns to accept an arbitrary backend value would duplicate
and weaken the existing domain authority.

Backend support must be represented as coupled OS compatibility entries, not
three independent allowlists. A canonical entry binds:

- family;
- distribution/product line; and
- a bounded version domain.

An equivalent shape should be shared by `ProvisionerCapabilities`, its Pydantic
model, `RealizerConfigurationModel`, `BackendManifestV2Model` serialization,
and schema output.
The existing coarse family set should be derived from or mechanically
cross-validated against these entries so there is one value-level authority.
Independent `supported_os_distributions` and `supported_os_versions` sets are
forbidden because they falsely advertise the Cartesian product. The existing
`ArtifactMechanismCapability` pairing is the precedent for avoiding that
overclaim.

Admission intersects authored exact/constrained/open posture with a compatible
entry before backend side effects. Exact values must match one entry;
constrained values must have a non-empty intersection and retain their plan
authority bound; an open leaf permits a backend choice only within a compatible
entry. A family-only backend claim cannot satisfy a distribution or version
requirement.

## Backend selection and realization evidence

Reference, libvirt, and downstream backends may choose their own selection
algorithm, but the following contract is invariant:

- capability/configuration admission occurs before driver I/O;
- source/artifact and OS requirements are checked independently and jointly;
- a backend cannot advertise exact or constrained OS support until its selected
  artifact is compatible with the admitted OS entry;
- selected family, distribution, and version remain separate from the authored
  desired payload; and
- successful boot, plan echo, image name, or configuration assertion alone is
  not proof of the running OS.

Extend the existing operation-bound `RealizationObservationDisclosure` path with
one typed, bounded, non-secret observed OS identity. One observation may
corroborate the family, distribution, and version leaf requirements; do not
perform three guest probes or create three competing evidence DTOs. Each leaf is
still evaluated against its own requirement and authority bound. The disclosure
must retain operation, envelope, configuration digest, observer, and sequence
binding and pass the existing observation-consistency validator.

For a runnable guest, distribution and release claims require guest-observed
evidence (for example, the platform's canonical OS identity interface), not an
unverified image label. Raw probe output is not persisted. Backends that can
only describe or model an OS must disclose that weaker posture and cannot claim
exact runtime satisfaction. The selected identity belongs in realization
observations; it must not be placed in value-free provenance, metadata/details,
diagnostic messages, or by mutating the authored node payload.

Runtime non-approximation must reject and return the baseline snapshot for:

- an exact family, distribution, or version mismatch;
- a constrained selected value outside the authored finite domain;
- an admitted compatibility-row violation;
- missing, malformed, weak, stale, or execution-mismatched OS observation; and
- a backend claiming support without the corresponding manifest/configuration
  envelope and observation capability.

Use the existing stable diagnostic and backend-contract-invalid paths. Do not
add an OS-specific exception hierarchy or leak selected values, image paths,
probe output, or `str(exc)` through API error envelopes.

## Cross-cutting incumbents and gates

The implementation must build on these existing authorities rather than create
parallel ones:

| Layer | Canonical incumbent and required treatment |
| --- | --- |
| Input safety and shape | `raes.parser` (`SDLParserLimits`, bounded UTF-8/YAML parsing, tag/alias/directive/depth/node/scalar and duplicate-key checks) followed by closed Pydantic `SDLModel` shapes. New fields and vocabulary tokens pass these same bounds and `extra="forbid"`; no secondary YAML or free-form mapping parser. |
| Semantic validation | `SemanticValidator`, variable-reference validation, compute-node field validation, and designation pointer resolution. Enforce family/distribution/version dependency once here and in generated JSON Schema where structural; do not repeat divergent rules in each backend. |
| Instantiation | Existing substitution, finite `allowed_values`, explicitness/provenance derivation, namespace rewriting, and concrete model revalidation. Preserve exact/constrained/open records for the new leaves. |
| Controlled vocabularies | Existing vocabulary loader, concept authority registry, governed extensions, catalog parity, and generated-schema checks. Distribution/product-line spelling has one authority. |
| Processor and planning | `NodeRuntime`, `capture_capability_constraints`, `CapabilityConstraint`, the realization concern registry, `CompiledRealizationAuthority`, capability-domain checks, manifest validation, and plan authority completeness. No opaque `spec.node` lookup or backend-local reinterpretation. |
| Manifest and configuration | `ProvisionerCapabilities` plus its model, `RealizerConfigurationModel`, `RealizerManifestModel`, configuration digest binding, and the configuration-selected support envelope. The coupled OS entry is the value-level authority; coarse support declarations remain posture/kind declarations. |
| Backend boundary | Pure reference/libvirt realization interpreters and capability-envelope validation before the driver boundary. Fixed argv/no-shell and bounded subprocess conventions remain unchanged; OS tokens never become shell fragments, credentials, URIs, native IDs, or host paths. |
| Runtime contract | `_call_backend_apply`, snapshot contract checks, `realization_authority_disclosure`, `realization_disclosure`, observation consistency, and baseline rollback. Reuse `runtime.backend-contract-invalid` and exception-class-only backend failure reduction. |
| Evidence and persistence | `RealizationObservationDisclosure`, `RuntimeSnapshotEnvelopeModel`, `ControlPlaneStore`, and the existing atomic snapshot write/round-trip path. Do not add a sidecar, cache, repository, database column, or metadata/details escape hatch. |
| API/auth/audit | Existing strict control-plane security defaults, `_ControlPlaneApiAuth`, role/target authorization, request-size limits, planner-authorized plan checks, idempotency, and `AuditEvent`. No new route is required; authorized snapshot reads expose the typed evidence, while diagnostics stay value-free. |
| Conformance | `run_target_conformance`, positive and single-fault negative envelope probes, no-mutation evidence, dishonest-backend fixtures, and `BackendConformanceReport`. Exact, constrained, and open cases must cover processor output, manifest/configuration admission, runtime mismatch rejection, evidence binding, schema round-trip, and no side effect on preflight failure. |

OS identity is non-secret bounded data, but it still travels only through typed
models and authorized snapshot APIs. It must not be sourced from ambient
environment variables, passed in process arguments to ad hoc probes, written to
unstructured logs, or used to expose host paths. Artifact acquisition
credentials remain outside SDL, plans, snapshots, and process argv.

The repository workflow authorities in `.ground-control.yaml`,
`.gc/plan-rules.md`, `noxfile.py`, and `tools/` remain applicable, including
repository policy, authority-boundary, concept-authority, generated-schema,
schema-publication, SDL catalog/lineage, and JSON-artifact checks. The four
draft Node-bearing contracts under ADR-061 (`sdl-authoring-input-v1`,
`instantiated-scenario-v1`, `instantiated-scenario-snapshot-v1`, and
`scenario-satisfiability-evidence-v1`) must change together. The affected
generated contract surface also includes `backend-manifest-v2`,
`realization-envelope-v1`, `provisioning-plan-v1`, `runtime-snapshot-v1`, and
the controlled-vocabulary/catalog artifacts. Regenerate and publish these
through the canonical bundle and publication tooling with an explicit migration
record; do not hand-edit schema copies.

## Extensibility seam

The coupled OS compatibility entry and the typed observed identity are the seam
for the next legitimate dimension, such as edition, build, or kernel. Such a
dimension should be added as another separately authored, separately designated
leaf and another bounded component of the same compatibility/observation
contract. It must not require replacing the canonical OS entry, and it must not
be smuggled into distribution or version strings.

The bounded-domain and concern-registry machinery must remain generic enough for
the next constrained scalar concern. Backend selection stays behind the existing
manifest/configuration boundary, so a backend can add a selector without
changing portable authoring semantics.

## Non-goals and anti-patterns

This issue does not:

- standardize a reference, libvirt, or APTL image-selection algorithm;
- turn OS distribution/version into artifact identity, package-manager policy,
  architecture, runtime-package inventory, kernel, edition, or device model;
- expand the legacy whole-scenario satisfiability profile without a separately
  governed profile revision;
- introduce implicit distribution inference, best-effort substitution, fuzzy or
  ordered version comparison, magic sentinel values, or compatibility aliases
  outside the controlled-vocabulary authority;
- accept plan echo, image tags, boot success, logs, metadata/details, or
  value-free provenance as realization evidence;
- create duplicate schemas, validators, exception types, logging pipelines,
  stores, conformance runners, or backend-specific OS contracts; or
- preserve ambiguous legacy `os_version` strings through an automatic heuristic
  migration.

Reference and libvirt must advertise only what their selectors and observers can
actually satisfy. Until they can admit a coupled OS requirement and produce the
required independent observation, unsupported exact/constrained cases must fail
before mutation rather than being approximated by family or image choice.
