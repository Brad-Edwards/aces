# Issue #1010 — SSH Generated Artifacts and Output Isolation Preflight

Date: 2026-07-31

This note records architecture guardrails for issue #1010. It does not
implement an SSH generator, an SDL change, a provisioner, or key distribution.

No new ADR is required. This is a bounded extension of the stateful-resource
contract established by the issue #780 preflight and the compile/plan/execute,
schema-authority, realization-honesty, validation-strength, and identifier
decisions it cites. This note supersedes only issue #780's temporary rule that
a mixed-sensitivity generated artifact must be delivered as an indivisible
unit.

## Contract boundary

Add one SSH-specific generated-artifact kind. The preferred wire value is
`ssh_key_bundle`: it covers SSH keypairs, SSH CA keys and issued material, and
public or `authorized_keys` projections without implying that the artifact
owns sshd authorization policy. `certificate_bundle` remains the X.509/SOC
material kind, and `rendered_config` remains configuration rendering.

The new kind is generated key material, not the SSH server-configuration
surface in ADR-031, an `Account.auth_method`, authored `Content`, a runtime
filesystem observation, or a participant information-flow policy. Raw private
or public key bytes remain unrepresentable in SDL, compiled plans, snapshots,
provenance, diagnostics, audit events, and API envelopes.

Output sensitivity and output entitlement are orthogonal:

- `ResourceSensitivity` classifies handling; it does not grant a consumer
  access.
- Each generated output has a closed distribution disposition:
  `consumer_selected` or `producer_private`.
- A generated-artifact consumer selects a non-empty, unique list of declared
  output names. Selection grants that consumer read-only delivery; it does not
  grant writeback or transfer artifact lifecycle ownership.
- A `producer_private` output is never selectable or materialized into any
  consumer. It remains backend-owned state beneath the artifact producer's
  protected root.
- Every `consumer_selected` SSH output is selected by at least one consumer;
  omission must not silently create a second producer-private meaning.

Use an artifact-specific consumer subtype that extends the existing stateful
consumer coordinates with output selection. Do not add an optional output
field to the persistent-volume consumer shape, and do not duplicate node,
destination, access-mode, or path validation.

For compatibility, existing `certificate_bundle` and `rendered_config`
documents may retain their current omitted-selection meaning during the
governed migration window: all non-producer-private outputs are selected.
`ssh_key_bundle` must require explicit selections from its first published
form. A producer-private output is excluded even on the legacy path. New
examples should use explicit selection for every kind so omission does not
become a permanent second authoring style.

The artifact remains one lifecycle and dependency unit. Selection changes
only the projection delivered to a consumer; it does not split generation,
refresh, provenance, identity, reconciliation, or deletion into per-output
resources. A backend must generate the complete declared output set atomically
enough to avoid mixed generations, then expose only each consumer's selected
projection.

## Canonical incumbents

The implementation must extend, not parallel, these existing authorities:

- **Source and model admission:** `load_sdl_yaml()` and the source limits and
  duplicate-key checks behind it; `SDLModel(extra="forbid")`;
  `PortableIdentifier`; `GeneratedArtifact`, `GeneratedArtifactOutput`,
  `StatefulResourceConsumer`, `ResourceSensitivity`, the canonical relative
  output-path validator, and the canonical mount-destination validator.
- **Semantic and composition admission:**
  `stateful_resource_reference_errors()`, `SemanticValidator`,
  `composition._rewrite_stateful_dependency_ref()`, the existing namespacing
  of stateful consumer node refs, unresolved-variable checks, and concrete
  revalidation through the `Scenario` -> `ExpandedScenario` ->
  `InstantiatedScenario` phases. Output selections are artifact-local names
  and are not module-global symbols.
- **Compilation and planning:** `_stateful_spec()`,
  `_compile_generated_artifacts()`, `GeneratedArtifactRuntime`,
  `resource_payload()`, `_collect_resources()`, the existing stateful graph
  ordering/refresh/reverse-delete logic, and
  `CompiledRealizationRequirement(requirement_kind="generated-artifact")`.
  The complete distribution declaration remains one exact SEM-218 payload.
- **Capability and realization admission:** `ProvisionerCapabilities`,
  `ProvisionerCapabilitiesModel`, backend-manifest v2 serialization,
  `_validate_artifact_and_volume_support()`,
  `_stateful_submission_diagnostic()`,
  `realization_support_diagnostics()`,
  `realization_envelope_diagnostics()`, and `realization_disclosure()`.
- **Execution, errors, and observation:** `_call_backend_diagnostics()`,
  `_call_backend_apply()`, `Diagnostic`, `ApplyResult`,
  `runtime.backend-contract-invalid`, `RuntimeSnapshot`, `SnapshotEntry`, and
  `RealizationProvenanceEntry`. No feature-specific exception or logger is
  warranted.
- **Persistence and API:** `ControlPlaneStore`, the local store's atomic
  snapshot path, `_snapshot_payload()`, `_snapshot_from_payload()`,
  `RuntimeSnapshotEnvelopeModel`, `_snapshot_model()`,
  `ControlPlaneSecurityConfig`, the existing authentication/role/target
  checks, request-size guard, idempotency fingerprint, audit path, and
  redacted HTTP 500 envelope.
- **Contract publication and workflow:** `schema_bundle()`, the hand-governed
  schemas and publication manifest, the SDL lineage ledger,
  `tools/check_generated_schemas.py`, `.ground-control.yaml`,
  `.gc/plan-rules.md`, repo policy, requirement governance, and
  `tools/verify_all.py`.
- **Tests:** `test_stateful_realization_resources.py` is the canonical
  parse/semantic/compile/plan/schema suite; `test_runtime_planner.py` and
  `test_runtime_control_plane.py` own capability and direct-submission
  admission; `test_backend_manifest.py` and
  `test_backend_manifest_v2_adapter.py` own capability round trips and
  fixtures. Extend these rather than creating a second SSH-only harness.

The published SDL schemas directly affected are
`sdl-authoring-input-v1`, `instantiated-scenario-v1`, and
`instantiated-scenario-snapshot-v1`; the satisfiability-evidence schema embeds
the instantiated snapshot and changes transitively. Refining backend
capabilities also changes `backend-manifest-v2`. Published schemas, generated
bundle output, schema-publication ledger hashes, fixtures, and lineage records
must advance together.

## Validation and security gates

1. **YAML/source gate.** Existing safe construction, alias/node/size limits,
   mapping-key normalization, duplicate-key rejection, and source diagnostics
   run unchanged. Output selectors are lists, not dynamic mapping keys.
2. **Closed model gate.** Existing enum, identifier, canonical POSIX path,
   collection-cardinality, duplicate, and read-only checks remain
   authoritative. The generated-artifact invariant additionally rejects
   duplicate selectors, missing output refs, selection of producer-private
   outputs, empty SSH selections, and unselected `consumer_selected` SSH
   outputs. Errors name coordinates only and never echo payload values.
3. **Semantic/composition gate.** Consumer nodes still resolve through the
   canonical node-reference and module-symbol machinery; cross-resource mount
   collisions and Windows/POSIX mismatches still fail before compilation.
   Output refs resolve only within their owning artifact and must not enter the
   global declaration or reference catalogs.
4. **Instantiation gate.** The existing unresolved-token walk and concrete
   model reconstruction cover disposition and selector values. Output names
   remain stable identifiers, not variable slots. No compiler-side guessing or
   late string matching is permitted.
5. **Planner and direct-submission shape gate.** Planner-produced and
   externally submitted `generated-artifact` operations must use one shared
   stateful payload admission helper that delegates to the canonical
   `GeneratedArtifact` model/invariant. The HTTP plan DTO's generic `payload`
   dictionary is not sufficient validation. Do not create a second dict
   schema or copy the selector rules into `raes_runtime`.
6. **Capability gate.** The coarse `supports_generated_artifacts` flag cannot
   authorize an unknown generator. The provisioner capability contract needs
   a governed `supported_generated_artifact_kinds` set, validated and rendered
   through backend-manifest v2. Planner admission and direct control-plane
   submission both require kind membership. Output isolation is intrinsic to
   support for `ssh_key_bundle`, not an optional approximation flag.
7. **Exact-realization gate.** The complete spec, including kind, output
   dispositions, selections, paths, sensitivity, lifecycle, provenance, and
   dependencies, remains the existing exact generated-artifact concern.
   A returned declaration that drops or changes a selector is an exactness
   failure and must restore the baseline snapshot through the existing
   sanitized backend failure path. Declaration equality alone cannot prove
   that the backend avoided an extra native mount; independent backend
   readback and conformance evidence own that stronger claim.
8. **Secret and persistence gate.** Plan and snapshot payloads contain desired
   metadata only. The control-plane store and authorized snapshot API copy
   `SnapshotEntry.payload` verbatim, so authentication is not a license to put
   generated bytes there. A producer-private disposition is an enforcement
   rule, not a redaction marker and not proof that a leaked value is safe.
9. **HTTP/auth and error-envelope gate.** Existing backend/operator mutation
   roles, backend/operator/auditor read roles, target binding, body limit,
   idempotency, and audit recording remain in force. Direct-plan validation
   returns bounded structured diagnostics; it must not surface Pydantic input
   renderings, backend exception text, private paths from native state,
   tracebacks, or key material through 409/422/500 responses.
10. **Host/OS materialization gate.** A real producer anchors all outputs below
    one owned root, rejects native traversal and symlink escapes, creates
    private material with restrictive ownership/mode and atomic replacement,
    and derives public/`authorized_keys` projections without redisclosing the
    private serialization. Secret bytes never enter process argv, environment
    variables, shell command text, stdout/stderr, diagnostics, audit details,
    or general logs. If a subprocess is unavoidable, use fixed argv,
    `shell=False`, bounded execution, and a protected input channel. Consumer
    materialization preserves the existing POSIX-only destination contract and
    must not mount or stage unselected siblings even transiently.

`reuse_valid` producer state is backend-private persistence keyed to the
canonical artifact identity and validated lifecycle/provenance inputs. It must
not be stored in control-plane JSON, a repository content tree, or a generic
temporary directory, and it must not be adopted solely because a matching
filename exists. Regeneration atomically advances private source material and
all derived consumer projections as one generation.

There is no new authentication surface, credential resolver, environment
binding, CLI secret option, HTTP endpoint, or secret-store configuration in
this issue. `provenance` remains an inert, non-secret recipe/source reference;
it is not a shell command, private-key carrier, or evidence that generation
succeeded.

## Capability and extensibility seams

The immediate capability seam is
`supported_generated_artifact_kinds`, not one boolean per generator. A backend
claims `ssh_key_bundle` only when it honors complete generation and
consumer-output isolation. Stub support may exercise the contract, but
reference/libvirt or other production manifests must not be widened without a
real producer and conformance evidence.

The next likely SSH variations are key algorithm/size, private-key encoding,
public projection format, SSH certificate/CA issuance, validity, and
principal/key-comment inputs. Those belong in a kind-scoped typed
`ssh_key_bundle` generator payload with matching capability dimensions. They
must not become a free-form `options`/`constraints` map, output-name
conventions, provenance-string parsing, or changes to `certificate_bundle`.

Output disposition plus artifact-local selected-output refs is the
distribution seam. A future audience or projection mode extends that closed
disposition vocabulary and its capability/admission rules. It does not add
per-consumer booleans, embed node lists into outputs, or fork the artifact
lifecycle.

## Gotchas and anti-patterns

- Do not infer privacy from `sensitivity: secret`; some secret outputs are
  intentionally delivered to exactly one consumer. Conversely, `public` does
  not mean every node is entitled to receive an output.
- Do not use an empty or omitted selector as producer-private for the new SSH
  kind. Privacy must be explicit and invalid selections must fail closed.
- Do not add selectors to the shared persistent-volume consumer DTO or weaken
  persistent-volume access semantics.
- Do not split one SSH generation transaction into unrelated artifacts merely
  to recover isolation; that loses the issue's shared lifecycle and refresh
  semantics. Separate artifacts remain valid when they genuinely have
  independent lifecycle or provenance.
- Do not flatten selected outputs, rename them by consumer, reinterpret output
  names as paths, or infer roles such as “private key” from names. Existing
  output paths and mount-destination semantics remain authoritative.
- Do not treat a consumer ref as an ordering/refresh dependency or create a
  second graph engine.
- Do not satisfy the request with `certificate_bundle`, `rendered_config`,
  authored `Content`, runtime SSH server configuration, accounts, cloud-init
  private extensions, or backend-native fragments.
- Do not hand-edit only one published schema, rely on JSON Schema for
  relational selector invariants, or describe shape validation as complete
  semantic admission.
- Do not let the generic HTTP plan payload bypass the model invariant, and do
  not log validation input while reducing it to a diagnostic.
- Do not put generated bytes, digests of private serialization, native producer
  roots, temporary filenames, commands, or backend handles in snapshots,
  realization provenance, operation details, or audit events.
- Do not add a new exception hierarchy, persistence repository, logger,
  capability registry, schema, output resolver, or workflow for this feature.

## Non-goals and implementation boundaries

- No runtime SSH server-policy changes (ADR-031).
- No real SSH key generator, CA service, key store, distribution daemon,
  rotation scheduler, revocation policy, backup, or recovery design in the SDL
  contract change.
- No change to X.509 `certificate_bundle` or configuration
  `rendered_config` semantics beyond the governed compatibility path for
  selectors.
- No provider selection, host path, Docker/Compose/Kubernetes/cloud-init
  fragment, shell command, Terraform resource, or backend handle in SDL.
- No raw key material or author-supplied key content in the generated-artifact
  declaration.
- No per-output lifecycle, refresh graph, provenance identity, compiled
  address, plan operation, or snapshot entry.
- No Windows path dialect, mutable consumer access, consumer writeback, or
  producer-as-node identity in this issue.
- No field-level snapshot authorization redesign. The current authorized API
  may expose non-secret declaration metadata; generated bytes remain outside
  the snapshot entirely.
