# Issue 674 Target-Node CPU Architecture Preflight

Date: 2026-08-02

Issue: #674. Requirement: none; the issue is the delivery contract.

This note records the repository-wide boundary for target-node CPU
architecture. It is guidance only: it does not implement the SDL, processor,
backend, example, or conformance changes, and it is not an implementation plan.

No new ADR is required. ADR-001 already separates portable SDL intent from
physical realization, ADR-008/036 own the processor and runtime boundaries,
ADR-009/061 own contract authority and evolution, ADR-012 owns portable
vocabularies, and ADR-070 owns configuration-bound realization claims.

## Binding Semantics

Add one optional, direct `Node.architecture` field:

```yaml
nodes:
  workstation:
    type: vm
    architecture: x86_64
```

It is the CPU architecture required of the target VM or guest described by the
node. It is not RAM/CPU quantity, so it does not belong in `Resources`; it is
not a package artifact classifier, so it does not belong in
`RuntimePackage`; and it is not a physical host or runner capability. Like the
other VM-only node properties, it is invalid on a `switch`.

Absence means that the author has imposed no target-node CPU architecture
requirement. It never means the controller architecture, the selected runner,
`platform.machine()`, the current container host, the QEMU binary default, or
the architecture of an image or package. Absence remains absent in normalized
SDL and semantic comparison; no consumer may materialize an inferred default.

Use one governed CPU-architecture vocabulary on all portable target/package
comparison surfaces. The deliberately small initial canonical set is:

| Canonical value | Authoring aliases |
| --- | --- |
| `x86_64` | `amd64`, `x64`, `x86-64` |
| `aarch64` | `arm64` |

Normalization is case-insensitive and applies the existing hyphen-to-underscore
rule before alias resolution. Canonical serialization always emits the value in
the first column. Do not accept ambiguous family labels such as `x86` or `arm`;
they omit width or variant information. Do not add `unknown`, `other`, `any`,
`all`, or `noarch` as target architectures: absence already expresses no
target constraint, and package-manager portability classifiers are not CPU
architectures.

Unknown unqualified strings fail closed. A custom value is admitted only in
the existing governed-extension form `x-<owner>:<term>`, in canonical lowercase
syntax. Custom values have exact-token compatibility only and no implicit
aliases. Adding another portable architecture or alias is a concept-authority
change; it must not require edits to planner or backend branching code.

`RuntimePackage.architecture` remains package-artifact metadata but must use the
same canonical tokens when populated. Its existing empty value means that the
package is not architecture-constrained. Compatibility for every node is:

- node absent and every package architecture empty: valid, with no target
  architecture requirement;
- node present and package architecture empty: valid;
- node present and package architecture present: valid only when normalized
  canonical values are exactly equal; and
- node absent and any package architecture present: invalid because package
  metadata must not become an implicit target-node requirement.

The last rule is intentionally fail-closed and may tighten previously admitted
documents. Treat that as a published semantic compatibility decision under
ADR-061, with publication metadata and regression coverage; do not preserve
legacy ambiguity by consulting the current host. Variables defer the comparison
only until normal instantiation. Finite `allowed_values` for architecture are
normalized with the same field-aware function and checked again after binding.

## Canonical Incumbents And Required Reuse

- **SDL and validation:** extend `raes.nodes.Node`, its existing
  `_populated_vm_only_fields` rule, `SDLModel(extra="forbid")`,
  `normalize_enum_value()` / `parse_enum_or_var()`, `parse_sdl()`, and the
  collect-all `SemanticValidator`. Parent-node/package agreement belongs in the
  existing node pass in `validator/_nodes_infra_network.py`; do not place
  relational validation in a child package model or create a second validator.
- **Concept authority:** add the vocabulary, aliases, governed scopes, and valid
  fixture to `contracts/concept-authority/controlled-vocabularies-v1.json` and
  the matching concept-authority specification. Reuse
  `validate_controlled_vocabulary_scope_values()` and keep the SDL enum/
  normalizer, catalog, fixtures, schemas, backend declarations, and envelope
  values in parity. Do not maintain a second backend-only architecture list.
- **Phase contracts and variables:** extend the existing finite-domain path in
  `instantiate.py::_capture_capability_constraints`, the
  `CapabilityConstraint` JSON-pointer allowlist in `raes.phase_contracts`,
  composition's `_prefixed_constraint`, and the OS-family patterns in
  `planner/capability_domains.py`. The canonical path is
  `/nodes/<id>/architecture`; do not introduce another binding syntax or read
  process environment variables.
- **Compilation:** retain the existing node resource and add a typed canonical
  architecture member to `raes_processor.models.resources.NodeRuntime` through
  `_compile_node_runtimes()`. The opaque `spec["node"]` dump is not a sufficient
  consumer contract, and a separate architecture resource/DTO is not justified.
- **Realization demand and admission:** register the authored node path once in
  `raes_processor.semantics.realization_concerns` and let
  `compiler/realization_requirements.py` and
  `realization_support_diagnostics()` use that descriptor. Reuse the existing
  `RealizationConcern.ARCHITECTURE`, `ConcernDisposition`, and
  `ObservationStrength`; do not create a second architecture concern or a
  special compiler branch.
- **Backend capability:** extend `ProvisionerCapabilities`, the neutral
  `ProvisionerCapabilitiesModel`, provisioner-manifest serialization, backend
  manifest aggregation, and the published backend-manifest contract with a
  clearly named `supported_node_architectures` set. This set reports target
  architectures a selected backend configuration can realize; it does not
  describe physical host hardware or select a runner. An absent/empty set makes
  no architecture support claim and fails only nodes that explicitly require
  architecture.
- **Configuration-bound truth:** `RealizerConfigurationModel.architecture` and
  the realization envelope already carry an architecture claim. Interpret it
  as the selected configuration's realized target architecture, normalize it
  canonically, and require it to agree with the provisioner capability used for
  admission. The envelope remains the configuration-bound evidence surface;
  neither it nor a host manifest may overwrite authored SDL intent.
- **Errors, execution, and persistence:** retain `SDLParseError`,
  `SDLValidationError`, `SDLInstantiationError`, `Diagnostic`, `ApplyResult`,
  `OperationReceipt`, `OperationStatus`, `RuntimeSnapshot`, and
  `raes_runtime.backend_calls`. Existing compiled plans, snapshots, operation
  envelopes, and realization observations are the only persistence carriers.
  No architecture exception hierarchy, logger, repository, cache, ledger, or
  controller is needed.
- **Schemas and comparison:** update all four Node-bearing normative contracts:
  authoring input, instantiated scenario, instantiated scenario snapshot, and
  satisfiability evidence, plus their schema-publication entries. Reuse
  `schema_bundle()`, `tools/generate_contract_schemas.py`, and
  `tools/check_generated_schemas.py`. The current semantic projection already
  compares full normalized node/package payloads; extend its tests rather than
  add architecture-specific diff code. Alias-only changes compare equal;
  absence/presence and distinct canonical values are semantic changes.

## Security And Whole-Path Gates

1. **Source/parser gate.** The existing safe YAML loader, UTF-8 and source-size
   limits, alias/depth/node/tag/directive limits, duplicate-key checks,
   JSON-domain validation, closed Pydantic shapes, and source-anchored bounded
   diagnostics remain unchanged. Architecture accepts only a canonical term,
   governed alias, governed extension, or declared whole-field variable.
2. **Shape/concept gate.** The direct node field, package field, finite variable
   domains, capability declarations, configuration envelope, schemas, and
   catalog all use one normalizer and vocabulary. Values are bounded tokens,
   not free-form host names, image selectors, runner ids, commands, or provider
   configuration.
3. **Semantic/phase gate.** `SemanticValidator` enforces VM-only placement and
   package compatibility; ordinary instantiation and direct instantiated-
   artifact admission rerun closed-shape and semantic checks. Composition uses
   its existing capability-constraint rewrite, and compilation receives only a
   concrete canonical token or absence.
4. **Planner/config gate.** The typed `NodeRuntime` requirement is checked
   against the selected configuration's existing provisioner capability and
   realization envelope before any mutation. Configuration factories remain
   the seam for selecting a backend/host; there is no new CLI flag, environment
   variable, unvalidated config dictionary, or RAES runner-selection workflow.
5. **Authentication/authorization gate.** This issue adds no API route,
   identity, role, or privilege. If the artifact crosses the remote control
   plane, `ControlPlaneSecurityConfig.strict_defaults()`, request-size limits,
   authenticated role/target checks, idempotency, and audit remain the only
   authorization surface. An architecture token grants no host access.
6. **Secrets and OS exposure gate.** Architecture is non-secret declarative
   data and must carry no credential, token, native id, host path, process id,
   or machine identifier. Parsing, planning, and admission require no process,
   shell, environment lookup, or argv. A future backend probe remains private,
   fixed-argv/no-shell, bounded, allowlisted, normalized, and must not leak raw
   output or host identity into SDL, snapshots, logs, or diagnostics.
7. **Backend execution gate.** A supporting driver rejects an unsupported
   target before side effects and propagates the canonical target requirement
   through its existing typed spec. Libvirt must not retain hard-coded
   `x86_64`; container realization must not claim support merely because the
   controller host matches. Emulation is backend-owned and does not change the
   SDL compatibility rule.
8. **Error-envelope/observability gate.** Parser and semantic failures retain
   bounded stable language diagnostics. Backend failures cross
   `raes_runtime.backend_calls` only as stable redacted `Diagnostic` values;
   raw exceptions, tracebacks, commands, argv, native XML, host probe output,
   and `str(exc)` do not cross the boundary. Guest `uname -m` is normalized
   realization evidence, never the source of the desired requirement.
9. **Contract/evidence gate.** Published-schema hashes and `last_change` move
   with the normative contracts. Positive conformance compares the authored
   canonical requirement with configuration-bound and guest-observed evidence.
   Echoing desired payload, reporting host architecture, or successful boot
   alone is not proof that the guest architecture was realized.

## Extension Seam

The extension seam is the governed term/alias table plus exact token matching,
the finite-domain capability-constraint path, and the parameterized
`supported_node_architectures` set. Adding a core architecture or spelling
alias changes concept authority and parity fixtures, not planner/backend
conditionals. Adding a backend or runner changes its configuration-bound
capability/envelope, not SDL.

Keep `Node.architecture` singular. A future alternative-architecture choice
uses the existing whole-field variable and finite-domain mechanism rather than
turning the field into an ordered list. A future ABI, endianness, CPU feature,
ARM variant, or physical-host requirement needs a separately typed companion
constraint after its semantics are defined; it must not be encoded into an
opaque architecture string or inferred from OS/package metadata.

## Gotchas And Anti-Patterns

- Do not conflate target node, guest, runtime-package artifact, container image,
  backend configuration, runner, emulator, or physical-host architecture.
- Do not infer target intent from packages, images, OS family, image names,
  controller/runner probes, QEMU defaults, or observed guest output.
- Do not accept arbitrary strings, silently map ambiguous `arm`/`x86`, use
  package-manager `noarch` as a CPU architecture, or let different custom
  owners compare by suffix.
- Do not validate package compatibility only in `RuntimePackage`, only in JSON
  Schema, or only in a backend. The relational language rule belongs in the
  canonical semantic pass and runs after variable binding too.
- Do not duplicate vocabularies, alias maps, schema models, exception trees,
  capability DTOs, diff projections, realization concerns, persistence paths,
  backend workflows, or host-probing code.
- Do not make `spec["node"]` the only compiled contract, add a new planned
  architecture resource, or let a backend manifest replace authored intent.
- Do not update only Python or one phase schema. The four Node-bearing
  contracts, publication metadata, controlled vocabulary, generated parity,
  examples, semantic diff, phase, planner, backend-manifest, envelope, and
  conformance coverage are one compatibility surface.

## Non-Goals And Workflow Boundary

This issue does not model or select a cloud instance, runner image, deployment
host, emulator, CPU model, instruction-set extension, ABI, endianness, package
manager, or image manifest. It does not schedule hosts, negotiate capacity,
assume host and guest equality, install or rebuild packages, add authentication
or secret handling, change control-plane routes, or invent a new evidence
protocol.

Env-packs, adapters, and backends continue to own physical capability
declarations, selection, negotiation, and realization evidence. RAES owns the
portable target requirement, normalization, package compatibility, and
pre-mutation admission against a selected backend's declared capability. The
implementation remains subject to `.ground-control.yaml`, `.gc/plan-rules.md`,
repository policy, concept-authority checks, JSON artifact checks, schema
publication/generated-schema parity, module-boundary checks, and the full
`tools/verify_all.py` graph.
