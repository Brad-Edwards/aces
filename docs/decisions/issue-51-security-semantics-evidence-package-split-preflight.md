# Issue 51 Security, Semantics, And Evidence Package Split Preflight

Date: 2026-08-01

Issue: #51.

Requirement: none. The GitHub issue is the delivery contract. This note records
architecture guardrails only; it does not implement the split, change behavior,
drain the oversized allowlist, or add release content.

## Binding Decisions

- Convert only the four current targets to same-named packages. Every Python
  file in each package, including `__init__.py`, must remain at or below the
  ADR-015 500-line cap.
- Keep the four original dotted module names as the only supported facades.
  Child modules are package-private implementation details; no existing caller
  moves to a child import.
- Remove only the four deleted paths from
  `tools/policy/oversized_allowlist.yaml`. The fixed historical set in
  `tools/policy/repo_policy.py` is policy evidence and must not change.
- The issue asks for a `CHANGELOG.md` entry, but `.gc/plan-rules.md` makes
  release-please the sole owner of that file. Leave `CHANGELOG.md` untouched
  and use a non-behavior-changing Conventional Commit / PR title such as
  `refactor:`.
- ADR-015, ADR-016, and ADR-036 already decide the durable layering and
  coverage model. No new ADR, schema, contract, registry, DTO family, service,
  repository, exception hierarchy, or logging abstraction is needed.

## Package Boundaries

### Runtime security monitoring

Preserve the exact ordered `__all__`. It is consumed by
`_runtime_service_family_registry.py`, which treats the module object and its
exports as the canonical runtime-family registration surface and installs
those same objects into `runtime_configuration.py` and `nodes.py`. Continue to
re-export the detection-definition identities from the existing
`runtime_security_monitoring_definitions.py`; do not copy or absorb that
already-separated concern.

The cohesive internal boundaries are vocabulary, listener/component/agent and
content/setting inventory models, and manager aggregation/local-id validation.
They must continue to use `SDLModel`, `_base.parse_int_or_var`, and the shared
`runtime_values` parsers and redaction helpers. The manager's duplicate-id
check remains one cross-child invariant and must not be distributed into the
individual child models.

Package conversion currently weakens two invariant tests unless their discovery
is made package-aware: `test_runtime_modules_do_not_redeclare_shared_validation_helpers`
only scans flat `runtime_*.py` files, and `_runtime_family_enums()` imports a
package but only recognizes enums defined directly on that facade. Preserve
the same recursive enforcement for child modules; do not let the split make
shared-helper or open/closed-enum drift invisible.

### Objective semantics

Keep `raes.semantics.objective_semantics` as the single name-level objective
authority used by the validator and compiler. Preserve the public role
constants, catalogs, analysis/reference/issue records, and the two public
functions. The existing test patches
`OBJECTIVE_DEPENDENCY_DEPENDENCY_ROLES` on the facade and then calls
`partition_objective_dependencies`; moving that function behind a simple
re-export would make it read an unpatched child-module global. Keep that
observable facade seam or use an equally narrow explicit indirection.

Internal boundaries may separate records/catalogs, actor and target resolution,
success/window/dependency resolution, and ordered analysis coordination. Do not
duplicate `analyze_objective_window`, `AssessmentResourceKind`, target indexes,
or compiler dependency logic. Preserve reference and issue ordering, stable
deduplication, kind-qualified names, dependency-cycle behavior, and the exact
role allocation. The existing `AssessmentResourceCatalog`,
`WindowResourceCatalog`, per-category role constants, and
`partition_objective_dependencies` are the extension seams for a future
resource kind or role change.

### Participant behavior semantics

This package remains distinct from `raes.participant_behavior`. It owns
name-level analysis, not authored DTOs, runtime history, or processor models.
Keep the three public frozen records and `analyze_participant_behavior` at the
facade. Cohesive child concerns are base action/boundary references, observation
visibility, behavior-specification registries and governed vocabularies,
autonomous-execution checks, tool-affordance checks, and one ordered coordinator.

`_ParticipantBehaviorSemanticRegistries.from_keywords` remains the fail-closed
shape gate for the six injected registries. Do not replace it with a permissive
bag, service locator, or global registry. Preserve `is_unresolved` as the
caller-supplied placeholder-policy seam. Continue to reuse
`raes_contracts.controlled_vocabularies`,
`raes_contracts.manifest_authority`, and
`participant_behavior_specification.tool_affordance_reference`; do not fork
their vocabularies, supported-contract ids, or canonical references.

Diagnostic multiplicity and order are behavior. The coordinator must continue
to aggregate participant action/boundary issues, action interaction issues,
visibility issues, then behavior-specification issues; the validator remains
the sole renderer from `ParticipantBehaviorIssue.code` to authoring errors.

### Evidence-run artifact

The leading-underscore module becomes a leading-underscore package without
changing `raes_operations._evidence_run_artifact`. Keep
`EVIDENCE_RUN_SCHEMA` and `assemble_artifact(EvidenceArtifactInputs)` available
there. Partition section builders by backend/scenario provenance, realization
and topology, participant/observation evidence, evaluation/disclosures, and
redaction/invariant-ledger metadata; retain one assembly coordinator and the
current section order.

`_evidence_run_types.py` remains the structural DTO/protocol boundary that
avoids a forbidden `raes_processor` dependency. Continue to use the canonical
`backend_manifest_payload`, capability-gap helpers, published
`raes_contracts` models, `expected_surface`, and `portable_artifact_ref`.
Never turn the artifact's duck-typed read surface into duplicate concrete
processor DTOs.

Assembly is not the security or persistence gate. The existing producer must
still pass every artifact through
`validate_libvirt_evidence_run_artifact()`—schema/required sections, embedded
Pydantic contracts, redaction, participant boundary, and realization-source
checks—before `run_artifact_path()` and `atomic_write_json_artifact()` may
persist it. Preserve the fail-closed no-write outcome and bounded diagnostic
messages.

## Compatibility And Repository Guardrails

- Replace each `.py` and package atomically; never leave both import candidates.
  Preserve every absolute and relative external import line, callable
  signature/default/annotation, dataclass field order/default, enum identity,
  `__all__` order, Pydantic field/validator behavior, and module-level
  monkeypatch seam.
- The issue's absolute-import grep is necessary but not sufficient. Preserve
  relative imports from the validator and runtime siblings, the module-object
  imports in `runtime_configuration.py` and
  `_runtime_service_family_registry.py`, and the transitive public identities
  installed into `raes.nodes`.
- `objective_semantics.py`, `participant_behavior.py`, and
  `_evidence_run_artifact.py` currently have no `__all__`. Do not add a
  restrictive one casually; expose every observed import plus the original
  module's intentional public definitions, without wildcard or dynamic export
  discovery.
- A re-export preserves an import statement but can change `__module__`, repr,
  pickle targets, introspection, and generated-schema details. Keep public
  definitions in the facade where metadata or mutable facade globals are an
  observed contract; otherwise prove facade object identity and schema parity.
  Do not rewrite `__module__` as a blanket compatibility trick.
- Child modules import exact foundations/owners, not their package facade.
  Keep one acyclic direction from records and shared helpers through domain
  checks/builders to the coordinator and facade. Account for the extra package
  depth in relative imports, and do not create child names that shadow the
  existing `raes.semantics.objectives`, `raes.participant_behavior`, or
  `raes.runtime_security_monitoring_definitions` authorities.
- Hatch's existing package-root configuration already discovers nested
  packages. Do not add a distribution, entry point, import hook, or packaging
  configuration.
- Deleted `.py` paths are referenced by the live semantic coverage table,
  SDL/formal/reference documents, the runtime inventory gap analysis, and
  `tools/check_sdl_catalog_parity.py`. Retarget live implementation links to
  the package facade (normally
  `.../<module>/__init__.py`) and update the parity check's expected links.
  Historical decision provenance need not be rewritten.
- Generated SDL schemas include `RuntimeConfiguration` and the security
  monitoring models. `schema_bundle()` and all published schema files must be
  byte/content equivalent after the refactor. Schema drift is a refactor defect,
  not authorization to edit published schemas or the publication manifest.

## Cross-Cutting Layers

- **Repository/import policy:** ADR-015/ADR-036 and
  `tools/policy/adr_policy.yaml` retain the 500-line and package-direction
  gates. `raes` may use only its existing `raes_contracts` dependency;
  `raes_operations` retains only its currently allowed public import prefixes.
- **SDL structural validation:** `SDLModel(extra="forbid")`, Pydantic field and
  model validators, variable-placeholder parsing, enum/bool/int coercion,
  portable symbols, absolute paths, and duplicate-id checks remain canonical.
- **SDL semantic validation:** `SemanticValidator`, objective-window analysis,
  named-reference indexes, controlled vocabularies, manifest authority, and
  the existing issue-code renderers remain the only semantic/error boundary.
- **Runtime secret handling:** `RuntimeSensitivityClassification` and
  `enforce_observed_value_redaction` still reject unredacted values in secret
  classifications. The split must not log or surface setting values.
- **Evidence security:** allowlisted section builders feed the existing
  redaction and participant/evaluator-boundary validator. Raw libvirt XML,
  UUIDs, QEMU command lines, host paths, connection URIs, credentials, private
  keys, and backend-private snapshots remain excluded.
- **Persistence and OS exposure:** the semantic and runtime-model packages stay
  pure in-process code. Evidence assembly retains only its existing scenario
  file read/hash; validated output still uses safe run-id containment and the
  atomic JSON writer. No environment binding, subprocess/argv value, socket,
  credential lookup, database, cache, or new filesystem surface is introduced.
- **Configuration and environment shapes:** keep
  `LibvirtEvidenceRunConfig`, `EvidenceArtifactInputs`, and the Pydantic
  scenario/runtime models as the explicit inputs. Backend connection-URI
  credential rejection remains with
  `TechVaultNativeLibvirtDriver._validate_connection_uri`; no child module may
  add environment fallbacks or place a URI, token, path, or payload in process
  arguments.
- **Authentication:** none of the four facades owns authentication or
  authorization. Runtime control-plane and backend connection policy remain in
  their existing owners; the split adds no token or identity surface.
- **Errors and observability:** preserve Pydantic `ValidationError`/underlying
  `ValueError`, frozen semantic issue records rendered by the validator, and
  evidence validation problem lists/gating checks. Add no logger, traceback
  envelope, exception translation, audit stream, or payload dump.

The canonical repository gates remain `tools/check_repo_policy.py`,
`tools/check_requirement_governance.py`, `tools/verify_all.py`, semantic
coverage, SDL catalog parity, generated-schema drift, and the pinned nox
`verify` session in `.ground-control.yaml`.

## Gotchas And Anti-Patterns

- Do not split by line ranges, create a generic “semantic rule” framework, or
  merge objective, participant, runtime inventory, and evidence concepts.
- Do not move validator rendering into semantic helpers or mix semantic issue
  DTOs with Pydantic contract models.
- Do not duplicate runtime parsers/redaction, objective window logic,
  controlled vocabularies, manifest contract ids, evidence redaction patterns,
  artifact schemas, persistence, or exception types.
- Do not reorder validation, issue aggregation, artifact sections, references,
  diagnostics, mappings, or deduplication; do not sort data that is currently
  insertion ordered.
- Do not import `raes_processor` from `raes` or `raes_operations`, and do not
  route private child modules into callers as a shortcut around facade cycles.
- Do not weaken invariant or semantic-coverage discovery because a file became
  a directory. Strengthening package-aware discovery is not test relaxation.
- Do not modify pre-existing behavioral tests to accept changed output, and do
  not use this refactor to fix incidental semantics.

## Non-Goals

No behavior, SDL grammar, schema, contract, vocabulary, semantic rule, issue
code/message/order, compiler/planner behavior, runtime inventory meaning,
redaction policy, evidence claim, artifact format, auth policy, secret handling,
configuration, persistence, logging, packaging entry point, compatibility
namespace, published schema, version, or release-note change is in scope.
