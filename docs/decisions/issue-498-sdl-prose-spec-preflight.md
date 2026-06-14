# Issue 498 SDL Prose Specification Preflight

Date: 2026-06-14

Issue: #498.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for authoring the normative
SDL prose specification. It is guidance for the implementation and does not
write the SDL spec, update the authority manifest, change schemas, or alter
reference implementation behavior.

## Binding Sources

- ADR-009 and ADR-019 define the authority boundary: normative prose belongs
  under `specs/`, while reference code and explanatory docs consume that
  authority.
- `specs/authority/authority-boundary.yaml` is the canonical machine-readable
  seam. Extend that seam for the SDL prose path; do not create a second
  authority registry.
- ADR-001 defines the SDL as backend-agnostic scenario specification with 21
  named authoring sections and two-phase validation, but the current schemas and
  reference implementation have grown additional top-level authoring surfaces.
  The prose spec must reconcile the live contract instead of freezing the stale
  section count.
- ADR-003, ADR-004, ADR-008, ADR-015, ADR-036, and ADR-053 define the current
  boundaries for variables, target refs, workflows, processor/runtime layering,
  and module composition.
- ADR-033, ADR-056, ADR-057, and the runtime-family ADR sequence define the
  runtime-inventory boundary and observed-value/redaction constraints.
- `docs/explain/sdl/sections.md` is useful evidence and a migration aid, but it
  must not become the normative source.

## Architecture Decisions

- Put the prose specification under `specs/sdl/`, not `specs/formal/sdl/`.
  The requested artifact is the language-neutral SDL authoring authority;
  `specs/formal/` remains for optional formal-methods artifacts under ADR-007.
- Register `specs/sdl/` in `specs/authority/authority-boundary.yaml` as
  `prose`. Do not introduce a new authority family such as `sdl` unless the
  authority-boundary ADR/checker is intentionally extended for a new family.
- Treat `contracts/schemas/sdl/*.json` as the machine-readable companion that
  must agree with the prose, not as prose replacement and not as Python-owned
  authority.
- Normatively state the authoring model in terms of SDL concepts, section names,
  references, variables, instantiation, and diagnostics. Avoid Python class,
  Pydantic, package, or validator-function names except in non-normative
  implementation-evidence notes.
- Separate top-level metadata/composition fields from authoring sections, and
  separate map-keyed sections from list-valued surfaces. Do not claim that every
  optional top-level surface is a dict keyed by user-defined identifiers:
  `forwarding_agents` is list-valued today.
- Runtime inventory should be a normative index plus shared invariants. Delegate
  per-family semantics to family ADRs and lineage instead of restating every
  field in the SDL authoring spec.

## Required Incumbents

- Authority and policy: ADR-009, ADR-019,
  `specs/authority/authority-boundary.yaml`, `specs/README.md`,
  `tools/check_authority_boundary.py`, `tools/check_repo_policy.py`, and
  `nox -s policy`.
- Authoring structure evidence: `Scenario`, `SDLModel`, parser key
  normalization, `_HASHMAP_SECTIONS`, `_NESTED_HASHMAP_FIELDS`, and the
  published SDL schemas under `contracts/schemas/sdl/`.
- Reference semantics evidence: `SemanticValidator._named_ref_index`,
  `_validate_named_ref`, the objective/relationship semantic helpers, and
  `collect_qualified_runtime_family_refs`.
- Variables and instantiation evidence: `Variable`, `is_variable_ref`,
  `extract_variable_name`, and `instantiate_scenario`.
- Runtime-inventory invariants: `_runtime_service_families.RUNTIME_SERVICE_FAMILIES`,
  `runtime_values.py`, `test_runtime_family_invariants.py`, and the family ADRs
  for service listeners, applications, database/DNS/mail/identity/app-auth,
  scheduled jobs, datastore, platform applications, forwarding agents, and
  orchestration authorities.
- Diagnostics surface: `SDLParseError`, `SDLValidationError`,
  `SDLInstantiationError`, language-service diagnostics, and the existing
  advisory list on `Scenario`.

## Cross-Cutting Layers

- YAML/config parsing: the spec must match the existing safe loading boundary:
  YAML maps only, top-level string keys, normalized field keys, preserved
  user-defined mapping keys, no variable placeholders in symbol-defining keys,
  and `extra="forbid"` structural closure.
- Semantic validation: unresolved, missing, or ambiguous references fail closed.
  Advisories stay non-fatal and must not be described as optional errors.
- Instantiation: variables are authoring placeholders until instantiation; type,
  default, `allowed_values`, undeclared parameters, and unresolved placeholders
  are checked before producing an instantiated scenario. Variable definitions and
  unresolved `${...}` placeholders must not survive as ordinary authoring
  variables in the instantiated payload.
- Runtime observed values: explicit `redacted` or `operator_secret`
  classifications omit raw values. Name-based secret heuristics are advisory
  only. Posture-only models must not gain raw credential fields.
- Repo-path and policy security: authority-manifest paths stay repo-relative,
  no absolute paths or `..`, and policy failures use structured
  `PolicyFailure` output without dumping file bodies, environment values, or
  tracebacks.
- OS/process exposure: spec examples and workflow notes must not place tokens,
  private keys, bearer credentials, or operator secrets in command-line argv.
- Error envelopes: do not invent a new SDL exception hierarchy or diagnostic
  envelope. Document the existing parse, semantic-validation, instantiation, and
  advisory boundary by reference, coordinating any future error/advisory changes
  with the review IMP-3 issue.

## Extension Boundary

The extensibility seam is a small set of normative catalogs, not scattered prose:

- a section catalog for top-level SDL sections, requiredness, key shape, and
  identifier/ref behavior;
- a reference-resolution catalog for bare, qualified, nested, runtime-family,
  workflow-step, and module-composed refs;
- a variable/instantiation catalog for allowed variable types, defaults,
  substitution, and post-instantiation exclusions;
- a runtime-family index that names the family key, collection name, primary
  `<noun>_id`, child-ref collections, owning ADR, and shared invariants.

Future SDL sections or runtime families should add rows to those catalogs and
the authority/schemas/tests that consume them. They should not require rewriting
unstructured prose or adding a parallel registry.

## Gotchas And Anti-Patterns

Avoid:

- copying Pydantic model docs into `specs/sdl/` as the specification;
- making `docs/explain/sdl/sections.md` normative by cross-reference;
- carrying forward the stale "21 sections, all dicts" wording without reconciling
  `action_contracts`, `observation_boundaries`,
  `outcome_interpretation_rules`, `forwarding_agents`, and any other published
  SDL schema fields;
- adding duplicate schemas, duplicate validation helpers, duplicate exception
  classes, or a new runtime-family registry;
- duplicating every runtime-family field in the SDL spec instead of delegating
  family semantics to ADRs and the runtime-family index;
- resolving ambiguous references by first match or by source-file locality;
- allowing variables in identifier-defining mapping keys;
- treating authored `accounts`, runtime `local_identity`, application RBAC,
  database roles, and participant identities as one identity model;
- collapsing `Node.services`, `runtime.service_listeners`,
  `runtime.applications`, `runtime.database_services`, host-published ports,
  and image provenance into one service concept;
- editing `docs/_build/`, implementation code, schemas, or tests as part of
  this preflight.

## Non-Goals

- Implementing the SDL prose specification in this note.
- Changing parser, validator, instantiation, processor, runtime, schema, or MCP
  behavior.
- Adding a new formal-methods artifact unless the implementation introduces new
  FM1+ semantics beyond documenting the existing authoring model.
- Rewriting explanatory SDL docs or historical ADR bodies except for narrow
  cross-reference updates required by policy.
- Solving the review IMP-3 error/advisory issue; this work should reference that
  boundary, not decide it.
