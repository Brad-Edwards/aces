# Issue 52 SDL Core Runtime-Services Package Split Preflight

Date: 2026-08-02

Issue: #52.

Requirement: none. The GitHub issue is the delivery contract. This note records
architecture guardrails only; it does not implement the split, change behavior,
drain the oversized allowlist, modify tests, or add release content.

## Binding Decisions

- Convert only `raes.composition`, `raes.orchestration`,
  `raes.participant_behavior`, and `raes.runtime_mail_service` into same-named
  packages. Their existing dotted names remain the supported facades; child
  modules are implementation details, not new caller import surfaces.
- The current `origin/dev` sizes are 1,279, 654, 826, and 525 lines
  respectively. The issue's 1,110-line composition snapshot is stale. Every
  Python file in each replacement package, including `__init__.py`, must be at
  or below ADR-015's 500-line cap.
- Remove only the four deleted paths from
  `tools/policy/oversized_allowlist.yaml`. The fixed historical baseline in
  `tools/policy/repo_policy.py` is policy evidence and must remain unchanged.
- `.gc/plan-rules.md` overrides the issue's stale `CHANGELOG.md` acceptance
  item: release-please owns that file. Leave it untouched and use a
  non-behavior-changing Conventional Commit / PR title such as `refactor:`.
- ADR-015, ADR-022, ADR-036, ADR-038, and ADR-053 already settle the durable
  ownership and behavior boundaries. No new ADR, schema, DTO family, service,
  repository, exception hierarchy, logger, registry, or compatibility layer is
  justified by this structural refactor.

## Package Boundaries

### Composition

Keep three existing responsibilities distinct: the pure symbol/reference
rewrite kernel, namespacing and section merge coordination, and import
expansion orchestration. `_rewrite_payload_with_symbols` remains the one pure
rewrite seam shared by module composition and `_transformation_rename.py`.
Do not create a second field/reference table or move semantic reference meaning
out of `_module_symbols.py`, `specs/sdl/references.md`, and the owning
validators.

`expand_sdl_modules` remains the only import-expansion coordinator. Preserve
the exact order of source normalization, import/descriptor validation,
lock/trust loading, registry resolution, recursive budget and cycle checks,
structural admission, parameter binding, symbol construction, namespacing,
collision rejection, provenance rebasing, and final expansion provenance.
Filesystem/OCI resolution, signatures, digests, archive/cache safety, and trust
policy stay in `module_registry`; parser source bounds stay in the parser and
source-profile modules. A child composition module must not become another
resolver, parser, validator, trust boundary, or persistence layer.

Rewrite-family child modules may group already-cohesive declaration/reference
families, but the ordered coordinator remains singular. Preserve insertion
order, recursive variable-token rewriting, exported-versus-private symbol
rules, forwarding-agent list identity, ambiguous stateful dependency errors,
merge collision wording, and provenance record order. These are observable
composition behavior, not incidental implementation details.

### Orchestration

Keep authored SDL models separate from semantic analysis and runtime result
contracts. Narrative timing (`Inject`, `Event`, `Script`, `Story`), duration
normalization, workflow predicates/policies, and the workflow graph models are
cohesive model concerns. Name-level graph validation remains in
`raes.validator`; portable step semantics remain in
`raes.semantics.workflow`; compilation remains in `raes_processor.compiler`;
execution/result state remains in `raes_contracts.workflow` and
`raes_runtime`.

Do not merge the authored `raes.orchestration.WorkflowStepOutcome` with the
distinct runtime-contract enum of the same name. Preserve Pydantic validator
registration and order, aliases (`next`, `then`, `else`, `default`), duration
rounding, variable-placeholder handling, enum identities, defaults, type-
specific rejection order and messages, and workflow policy normalization.
Moving a model must not move or duplicate graph reachability, branch/join,
support, compilation, compensation execution, or result-contract logic.

### Participant behavior

Keep authored DTO ownership distinct from both adjacent semantic layers. This
package owns action-argument domains, interaction declarations, authored
action contracts, view rules/transitions, and observation-boundary structural
invariants. `participant_action_semantics.py` remains the owner of typed
preconditions/effects/failure mappings; `participant_temporal_semantics.py`
remains the temporal owner; `raes.semantics.participant_behavior` remains the
name-level analyzer; processor/runtime/conformance packages retain realized
models and history checks.

Preserve the object identity of the existing `ParticipantEffectClass`,
`ParticipantFailureClass`, and `ParticipantPreconditionClass` re-exports. Do
not copy their enums or the imported action/temporal models into child modules.
Keep argument normalization and validation with
`ParticipantActionArgumentDefinition`, action-wide invariants with
`ParticipantActionContract`, transition invariants with
`ParticipantViewTransition`, and cross-rule sequencing with
`ParticipantObservationBoundary`. Validation and diagnostic order is behavior,
especially duplicate detection and the ordered view-transition relation.

### Runtime mail service

The package remains a typed, node-scoped logical inventory, not a mail parser,
transport controller, provisioning service, account store, or evidence
repository. Cohesive internal groups may cover components/listeners/domains,
mailbox storage and addresses, routing/queues/settings, and service aggregation
plus relationship access. `runtime_mail_vocab.py` remains the vocabulary
owner, `runtime_values.py` remains shared validation/redaction policy,
`Node.services` remains transport ownership, top-level accounts remain account
ownership, and `relationships.py` remains relationship ownership.

Preserve the exact ordered `__all__`. `_runtime_service_family_registry.py`
imports the module object and derives `RuntimeServiceFamily.public_symbols`
from it; `runtime_configuration.py` also imports that object and types
`mail_services` through it. The facade must therefore expose the same objects,
not replacements. Keep service-wide duplicate-id checks at the aggregate model
and semantic same-node/local-ref checks in `raes.validator._runtime_mail`; do
not distribute or duplicate those cross-child invariants.

The existing runtime-family invariant tests are already package-aware: they
recursively inspect `runtime_*/**/*.py` for shared-helper shadowing and import
package submodules for enum-sentinel checks. Do not weaken, bypass, or replace
that discovery after the conversion.

## Compatibility And Repository Guardrails

- Replace each `.py` and directory atomically; never leave both import
  candidates. No existing absolute or relative external import line changes.
- Preserve the public definitions of the three modules without `__all__`, not
  only the names found by a narrow import grep. At minimum, the facades must
  retain `expand_sdl_modules`, `_namespace_payload`, and
  `_rewrite_payload_with_symbols`; every orchestration model/enum plus
  `parse_duration`; every participant model/enum/type alias plus its existing
  action-semantic re-exports; and the exact mail-service `__all__`.
- A re-export must retain object identity, callable signatures/defaults/
  annotations, dataclass/Pydantic metadata, enum identity, aliases, model dump
  behavior, and generated JSON Schema. Do not add a restrictive `__all__` to a
  facade that did not have one, use wildcard/dynamic discovery, or rewrite
  `__module__` as a blanket compatibility trick.
- Child modules import exact sibling foundations or owners, never their package
  facade. Keep an acyclic dependency direction and account for the additional
  package depth in relative imports. In particular, do not route composition
  children back through `composition.__init__` or participant children back
  through `participant_behavior.__init__`.
- `docs/public/api/sdl.rst` autodoc targets remain
  `raes.composition` and `raes.orchestration`; rendered public membership must
  not disappear merely because definitions moved. Hatch already discovers
  nested packages; add no distribution, entry point, import hook, or build
  package declaration.
- Retarget live source links in the shared-semantic-integrity table, formal SDL
  references, current research guidance, and `tools/check_sdl_catalog_parity.py`
  to package facades. Also retarget orchestration/participant paths in the SDL
  lineage ledger and the scientific-completeness delivery assessment: their
  policy gates require cited repository artifacts to remain real files.
  Historical ADR/preflight prose need not be rewritten. Determine other JSON
  records by their owning checker, not by blind replacement.
- Add only narrow facade lint configuration if explicit re-exports require it;
  do not broaden an F401 suppression across `raes`. Published SDL schemas and
  the schema-publication manifest must remain content-identical. Schema drift
  is a refactor defect, not permission to regenerate or amend authority.

## Required Cross-Cutting Layers

- **Source, configuration, and composition admission:** retain the bounded safe
  SDL loader, UTF-8 and parser limits, duplicate/normalized-key checks,
  `SDLSourceParseOptions`, explicit `SDLMigrationPolicy`,
  `CompositionBudget`/`CompositionTraversal`, `ImportDecl`/
  `ModuleDescriptor`, lockfile and `TrustPolicy` validation, registry
  allowlisting, digest/signature checks, and resolver error order.
- **Structural validation:** all authored data still enters
  `SDLModel(extra="forbid")`, the existing Pydantic fields and validators,
  `PortableIdentifier`, shared variable/int/float/enum parsers, and—in the mail
  family—`runtime_values` symbol, list, path, duplicate, and redaction helpers.
- **Semantic validation:** `SemanticValidator`, its workflow analyzers and
  `_runtime_mail` pass, participant name-level analysis, declaration/reference
  indexes, and existing issue rendering remain authoritative. A package-local
  helper does not become a second semantic validator.
- **Schemas and downstream contracts:** `Scenario`/`ExpandedScenario`,
  `RuntimeConfiguration`, `relationships.py`, `schema_bundle()`, checked-in SDL
  schemas, processor compiler models, neutral `raes_contracts` DTOs, and
  runtime result-contract checks must continue to consume identical facade
  objects and produce identical output.
- **Secrets and information boundaries:** participant action arguments remain
  explicitly non-secret; hidden/view/evidence separation remains in the
  participant models and validators. Mailboxes continue to make raw credentials
  unrepresentable, and redacted/operator-secret mail settings continue through
  `RuntimeSensitivityClassification` and
  `enforce_observed_value_redaction`. Do not put payloads, setting values,
  credentials, hidden truth, source bodies, trust keys, or registry responses
  into errors or logs.
- **Authentication, environment, OS, and persistence:** none of the four model
  facades owns authentication or authorization. The split adds no identity,
  token, environment-variable fallback, process-argv value, subprocess,
  socket, host binding, database, or new filesystem path. Composition retains
  only its existing source/lock/trust reads and resolver/cache behavior; the
  other three packages remain in-process data/model code. `Inject.environment`
  is authored SDL data, not authority to bind the host process environment.
- **Errors and observability:** preserve Pydantic `ValidationError` with the
  existing ordered `ValueError` messages, and composition's
  `SDLParseError`/`SDLValidationError`/`SDLInstantiationError` translations and
  source paths. CLI, MCP, and runtime callers retain their existing envelopes.
  These modules currently define no logger, audit stream, or telemetry path;
  the refactor must not add one or dump raw inputs/tracebacks.
- **Workflow and policy:** ADR-014's nox graph, `.ground-control.yaml`,
  `.gc/plan-rules.md`, `tools/check_repo_policy.py`, requirement governance,
  SDL lineage/catalog parity, scientific-completeness evidence-path checks,
  generated-schema drift, Sphinx, runtime-family invariants, and the pinned
  nox `verify` session are the canonical gates. Do not add a parallel check
  script or workflow.

## Extensibility Seams

Preserve the existing explicit seams rather than inventing plugin machinery:

- composition's parameters remain `source_format`, `migration_policy`,
  `limits`, and the private traversal/budget context; a future reference-bearing
  SDL field joins the single `_rewrite_payload_with_symbols` coordinator and
  canonical symbol/reference authorities once;
- workflow extension remains the closed `WorkflowStep.type` discriminator
  coordinated with existing validator, `raes.semantics.workflow`, compiler,
  capability, and runtime-contract mappings—not a package-local handler
  registry;
- a participant argument/view variation extends its owning closed enum/model
  and existing ordered model/semantic validators, not a generic participant
  schema or service locator; and
- a mail capability extends the existing typed child/vocabulary surface and,
  when addressable, the one `RuntimeServiceFamily.child_refs` registration.
  It does not require another top-level runtime family or mail-specific parser.

The split itself needs no new public parameter. Adding one solely to justify
the new package layout would change behavior and is out of scope.

## Gotchas And Anti-Patterns

- Do not split by line ranges, introduce `common.py` dumping grounds, wildcard
  re-exports, dynamic registries, or package initialization side effects.
- Do not confuse authored orchestration with semantic graph rules or runtime
  workflow state; authored participant contracts with name-level analysis or
  runtime histories; mail logical state with transport/accounts/evidence; or
  pure composition rewriting with resolver/trust I/O.
- Do not duplicate schemas, enums, reference catalogs, validators, exception
  classes, error rendering, logging, redaction, persistence, or workflow logic.
- Do not reorder model validators, rewrite passes, imports, merges, provenance,
  diagnostics, transition checks, enum exports, or insertion-ordered output.
- Do not change callers to private child imports to avoid a facade cycle. Fix
  the child dependency direction instead.
- Do not modify pre-existing tests to accept changed behavior, hand-edit
  generated schemas, alter the locked oversized baseline, or perform unrelated
  semantic cleanup while moving code.

## Non-Goals

No SDL grammar, schema, model field, enum, validator, reference meaning,
composition algorithm, module trust policy, workflow semantics, participant
semantics, runtime-mail meaning, secret policy, compiler/runtime behavior,
error/diagnostic, logging, persistence, authentication, configuration,
packaging entry point, compatibility namespace, version, or release-note
change is in scope. This issue does not reconcile similarly named authored and
runtime enums, redesign module composition, add a workflow step, add a
participant contract family, parse/provision mail systems, or repair incidental
behavior.
