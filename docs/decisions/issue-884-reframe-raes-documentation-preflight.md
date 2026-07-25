# Issue 884 RAES Documentation Reframing Preflight

Date: 2026-07-25

Issue: #884. Requirement: GOV-884. The requirement is the positioning
constraint; the issue supplies the implementation context and acceptance
criteria.

This note records repository-wide guardrails for presenting Reproducible
Agentic Environments System (RAES) as a domain-neutral system while keeping
every capability and assurance statement within the evidence currently
published by the repository. It is design guidance, not an implementation
plan, a new semantic authority, or a new product claim.

## Binding Decisions And Evidence

- ADR-093 makes Reproducible Agentic Environments System (RAES) the current
  project identity while retaining SDL as the name of the authored scenario
  language. Current user-facing prose introduces the full name on first use.
- ADR-009, ADR-019, and `specs/authority/authority-boundary.yaml` keep
  explanatory docs, normative specs, published contracts, reference code, and
  examples in separate authority classes.
- ADR-021 and `specs/agent-guidance/agent-guidance.yaml` require claims to stop
  at their named evidence. Valid SDL, a dry-run plan, a fixture, or one
  conformance probe must not be promoted into deployment, reproduction, replay,
  participant-readiness, or behavioral-equivalence evidence.
- ADR-055, ADR-065, ADR-068, ADR-074, and the experiment-core contracts keep
  scenario intent, experiment design, apparatus context, archival runs,
  evidence, measures, studies, and replay/reproducibility claims distinct.
- ADR-070 and ADR-084 keep authored variation, experiment selection, backend
  realizability, realization, scheduling, and provenance as separate planes.
- `scientific-scenario-completeness-rev1.json` defines a reproducible benchmark
  or study input as support for a bounded reproduction attempt, not a guarantee
  of bitwise replay, equal outcomes, scientific validity, generalizability, or
  behavioral equivalence. The current delivery assessment reports that
  stronger profile as incomplete.
- ADR-014, `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and the
  docs workflow define the verification path.

No ADR amendment is required. The issue changes explanatory positioning and
current user-facing metadata; it does not change an accepted architectural
decision or normative SDL meaning. GOV-884 is the traceability authority for
the repository check, tests, and governed documentation changes.

## Framing Vocabulary

Use these distinctions consistently across the README, documentation entry
points, glossary, architecture/reference pages, examples, and metadata:

**RAES**
: Reproducible Agentic Environments System, the repository-wide system of
  specifications, contracts, reference implementations, examples, and
  assurance material. RAES is broader than its SDL and broader than any one
  backend or application domain.

**Agentic environment**
: For explanatory positioning, a declared and realized setting in which one or
  more participants can receive observations, take actions, interact with
  resources or other participants, and be evaluated under stated controls.
  Participants may be software agents, policies, scripts, or human-control
  proxies. This definition does not introduce a new schema, root object,
  participant kind, or runtime guarantee.

**Authored scenario**
: Intent expressed in SDL before instantiation, compilation, planning, or
  backend realization. SDL remains a scenario description language; it is not
  renamed to an “agentic environment schema.”

**Realized environment**
: The concrete environment produced by a selected processor, backend,
  participant implementations, configuration, and runtime choices. It is not
  identical to the authored scenario, and underspecified choices require
  realized-form and apparatus disclosure where the applicable contracts
  provide it.

**Reproducibility support**
: Preservation and connection of authored intent, explicit deterministic or
  governed variation, instantiation and realization inputs, participant
  behavior and observations, apparatus identity, provenance, evidence, replay
  boundaries, and conformance results so that a bounded reproduction attempt
  can be made and assessed. Do not shorten this to “RAES guarantees
  reproducibility.”

Cyber, AI security, AI safety, testing, research, and evaluation are
non-exhaustive application areas. The general model can support additional
domains whose environments and evidence fit the same authored-intent,
realization, participant, observation, provenance, and conformance boundaries.
That statement is about model applicability, not a claim that each domain
already has complete vocabularies, examples, profiles, assets, or production
backends.

## Architecture Guardrails

- Lead with RAES as the system and present SDL, contracts, the Python reference
  implementation, examples, and conformance material as its current
  materialized parts. Do not redefine RAES as only the SDL or describe the SDL
  as the entire environment.
- Preserve the one-way conceptual boundary:
  authored intent -> admitted/instantiated scenario -> compiled plans ->
  backend realization and participant execution -> observations/evidence ->
  archival provenance and bounded replay/conformance claims.
- Describe deterministic behavior only at the proven phase. Canonicalization,
  deterministic composition, governed random streams, or deterministic plan
  construction do not imply deterministic participant behavior, backend
  behavior, observations, outcomes, or exact replay.
- Keep the domain-neutral core separate from domain-specific examples,
  controlled vocabularies, semantic profiles, reusable assets, and backend
  profiles. Existing cyber examples remain valid demonstrations and must not
  become the definition of the core.
- Keep current implementation limits adjacent to high-level positioning:
  there is no managed service or production backend in this repository;
  several participant, evidence, provenance, time, storage, and study surfaces
  are partial, architecture-level, or separately contracted; stronger
  scientific-completeness profiles remain incomplete.
- Use `docs/explain/reference/glossary.md` as the explanatory terminology
  anchor. Entry points should link to it or repeat only a short consistent
  definition, not create competing definitions of agent, participant,
  scenario, environment, apparatus, run, evidence, replay, or conformance.
- Historical ADRs, research records, external titles/URLs, source package names,
  and governed `aces-*` contract/profile identifiers are not stale positioning
  prose. Classify them under ADR-093 before changing them.

## Canonical Incumbents

Build on these existing surfaces rather than introducing a second documentation
taxonomy or project-description registry:

- Project identity and migration: ADR-093 and
  `docs/migration/raes-rename.md`.
- Current-state prose policy:
  `docs/explain/reference/documentation-style-guide.md`.
- Entry and navigation surfaces: `README.md`, `docs/index.md`,
  `docs/explain/getting-started.md`, and
  `docs/explain/reference/canonical-reference-map.md`.
- Terminology and boundaries: `docs/explain/reference/glossary.md`,
  `docs/explain/sdl/index.md`,
  `docs/explain/sdl/runtime-architecture.md`,
  `docs/explain/reference/explicitness-realization-semantics.md`,
  `docs/explain/reference/realization-envelopes.md`, and
  `docs/explain/reference/scenario-variation-and-trial-realization.md`.
- Normative claim limits: `specs/agent-guidance/agent-guidance.yaml`,
  `specs/sdl/scientific-scenario-completeness.md`,
  `specs/formal/experiment-core/README.md`, and the current
  scientific-completeness taxonomy and delivery assessment under
  `contracts/profiles/scientific-completeness/`.
- Examples and library entry points: `examples/README.md` and
  `examples/library/catalog.yaml`, guarded by
  `tools/check_example_library.py`.
- Published metadata: `implementations/python/pyproject.toml` for the short
  distribution description; the root `README.md` for the Hatch-injected PyPI
  long description; the root README citation metadata;
  `implementations/python/packages/raes_mcp/server.py` for MCP discovery
  instructions; `implementations/python/packages/raes_mcp/tools/reference.py`
  for the emitted SDL overview; and `docs/conf.py` for generated Sphinx
  project/title metadata. Do not add another package README or metadata
  source.
- Verification: `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/verify_all.py`,
  `tools/policy/requirement_order.yaml`, `.github/workflows/docs.yml`, and
  `.github/workflows/ci.yml`.
- Policy implementation conventions: `tools.policy.common.PolicyFailure`,
  `tools/policy/exceptions.yaml`, the pure evaluator/CLI split in
  `tools/check_agent_guidance.py`, and its temporary-root tests in
  `implementations/python/tests/test_agent_guidance_policy.py`.
- Existing adjacent claim gates:
  `tools/check_behavioral_relation_claims.py` owns governed behavioral-relation
  overclaim detection, and `tools/check_scientific_scenario_completeness.py`
  owns scientific-completeness nonclaim coverage. GOV-884 must not duplicate or
  weaken either gate.

Normative specs or contracts may need a current-name correction when ADR-093
requires it, but they must not be rewritten merely to broaden positioning.
No application schema, DTO, runtime validator, controller, service, repository,
or exception hierarchy is needed for this documentation issue. GOV-884 does
require one repository policy check; that check is tooling, not a new RAES
runtime validation layer.

## Executable Positioning Guard

Implement the GOV-884 check as one standalone repository-policy evaluator in
the existing `tools/check_*.py` family. Its pure evaluation entry point must
return `tools.policy.common.PolicyFailure` values, its CLI must use the existing
JSON/error rendering and exception mechanism, and `noxfile.py` must invoke it
inside `_run_policy`. Do not add another GitHub Actions job, shell wrapper,
pre-commit command, or verification command: `policy`, `verify`,
`verify-changed`, the pre-push hook, and CI already converge through nox.

`tools/policy/requirement_order.yaml` does not currently map GOV-884. Reuse the
existing `project-identity-migration` phase established for GOV-866, because it
already owns the current project-description, docs, package-metadata, MCP, and
identity surfaces. Add GOV-884 to that phase and admit the exact new focused
policy-test path; do not create a parallel documentation-governance phase or
broaden the phase to unrelated implementation packages. Record IMPLEMENTS and
TESTS traceability for the checker and its focused test even though the current
governance filter exempts `tools/` from path-based code-link enforcement.

The guard must use an explicit, small table of current primary positioning
surfaces and the obligation each surface carries. It must not recursively ban
words such as `cyber`, `range`, `deterministic`, `replay`, or `reproducible`
across the repository. Those words are valid in domain-specific examples,
historical records, normative contracts, negative capability statements, and
phase-bounded technical claims. At minimum, the evaluator must fail closed on
missing or unreadable registered surfaces and verify:

- the principal entry points introduce Reproducible Agentic Environments System
  (RAES), define an agentic environment, and describe the application list as
  non-exhaustive;
- RAES, SDL, authored scenarios, and realized environments are not presented as
  aliases;
- reproducibility language remains bounded to preserved intent, governed
  variation, realization/apparatus context, participants, observations,
  provenance, evidence, replay boundaries, and conformance;
- primary summaries do not make positive claims of complete domain coverage,
  deterministic runtime outcomes, exact replay, or guaranteed reproducibility;
  and
- cyber-specific lineage, examples, identifiers, and honest current backend
  limitations remain permitted.

Parse structured metadata at its owning shape. Use `tomllib` for
`[project].description`; use Python AST inspection for literal MCP instruction
and overview constants rather than importing or executing the MCP server; and
read Markdown as UTF-8 text. Do not create a second YAML/JSON positioning
schema or move prose into a generated registry merely to make the check easy.
Keep all registered paths repository-relative, containment-checked, size
bounded, deterministic, and free of network access.

Focused tests must exercise the evaluator through temporary repository roots:
one conforming fixture; one failure per obligation; missing/unreadable and
malformed structured surfaces; explicit negative claims; allowed
cyber-specific passages; and exclusion of historical, research, generated, and
external material. Pin `REQUIREMENT_REF = "GOV-884"` in the checker test. Add
the focused test to the existing targeted policy-test set rather than creating
a separate test runner.

## Cross-Cutting Layers

### Authority and shape validation

- Markdown and MyST content passes the existing Sphinx parser, toctree, autodoc,
  and warning-as-error CI build. Internal links must resolve from the edited
  document, and code snippets must use current import and CLI names.
- `docs/conf.py` is executable build configuration. Keep the installed `raes`
  distribution metadata as the version source and the honest
  `0.0.0+unknown` fallback; positioning changes do not add environment-driven
  titles or version literals.
- `implementations/python/pyproject.toml` remains a valid PEP 621/Hatch shape.
  Change only user-facing description metadata; do not hand-edit the
  release-please-owned version or duplicate the dynamic README hook.
- `examples/library/catalog.yaml` passes its existing YAML shape, path,
  requirement-reference, and parser/semantic-validation gate. Reframing its
  description must not change catalog IDs, body validation, or authority.
- `tools/policy/requirement_order.yaml` passes the existing safe-YAML
  requirement-governance loader. GOV-884 belongs in
  `project-identity-migration`; its ownership change should name only the new
  focused test because the phase already covers the intended governed
  documentation, metadata, and MCP roots.
- The GOV-884 evaluator passes fixed, repository-contained inputs through
  UTF-8 decoding, TOML parsing, Python AST shape checks, and bounded semantic
  claim checks. It must not import application modules or execute docs,
  metadata, examples, or MCP code while inspecting them.
- Repository-relative paths remain confined to their owning roots. Generated
  Sphinx output and built package metadata are verified, not hand-edited.

### Security and exposure

- Runtime authentication and authorization surfaces are not touched: no HTTP
  route, MCP tool, control-plane role, trusted-proxy header, or request-size
  guard changes. Documentation must not imply that reframing changes those
  controls.
- The secret boundary remains ADR-057 plus repository hygiene. Do not read or
  publish operator credentials, tokens, private keys, environment dumps,
  prompts, hidden answers, raw backend objects, or real host paths. Synthetic
  scenario values remain distinct from operator secrets.
- Do not add environment variables or config aliases. The branch name
  `884-reframe-raes-docs` does not contain a requirement UID, so local
  governance runs must set `ACES_REQUIREMENT_UID=GOV-884` or pass
  `--requirement-uid GOV-884`. Do not use the requirement-free
  `--skip-requirement` lane for this work.
- Requirement governance must resolve GOV-884 through
  `project-identity-migration`, enforce that phase's existing ownership roots,
  and find the new TESTS/IMPLEMENTS links. A missing phase mapping is a policy
  failure, not a reason to bypass governance.
- Shell examples use fixed current commands and repo-relative sample paths.
  Tokens, credentials, evidence payloads, or secrets must not appear in process
  argv. Examples that start MCP or runtime services must retain their current
  non-execution and authentication boundaries.
- Error envelopes stay owned by their existing layers: SDL parse/validation
  errors, processor `Diagnostic` values, Typer CLI errors, MCP structured JSON,
  and bounded runtime HTTP errors. The rewrite must not promise a unified error
  model, quote raw exception payloads, or introduce documentation-only error
  terminology that conflicts with those incumbents.
- Logging, audit, and persistence behavior are unchanged. Provenance and
  evidence contracts are portable artifacts, not proof that this repository
  ships production storage, log collection, replay execution, or study
  services.
- The policy checker has no auth, network, secret, environment-binding, or
  persistence surface. Its only OS-visible argument may be a repository root or
  JSON-output selector; it reports bounded rule id/path/message envelopes and
  never file bodies, environment values, tracebacks, or parsed payloads.
- The canonical hygiene graph retains text/YAML/JSON checks, private-key
  detection, and gitleaks. Do not weaken or bypass it for example prose.

Remote GitHub repository/About metadata is not a checked-in authority and must
not become a network dependency of the hermetic policy check. If maintainers
choose to update that remote description, treat it as a separately authorized,
authenticated external action; do not pass a token in process arguments or
duplicate the remote value into a new repository registry.

## Extension Boundary

The extension seam is the existing profile-and-catalog boundary, not a new
top-level `domain` field or a closed application-domain enum.

A future application area should add or reference its domain-owned examples,
controlled vocabularies, semantic profiles, reusable assets, backend profiles,
and evidence through their current authorities. The domain-neutral RAES
definition and authored/realized/evidence lifecycle should not need revision
merely because another application area is added.

The parameter at that seam is the selected domain-specific profile or artifact
reference carried by the existing authoring, apparatus, concept-authority, and
example/catalog surfaces. Environments may span domains, so do not force one
global domain discriminator into SDL, runtime DTOs, contracts, or package
metadata.

## Gotchas And Anti-Patterns

Avoid:

- replacing “cyber range” with “agentic environment” mechanically when the
  sentence accurately describes a cyber-specific example, lineage source,
  contract, or current backend boundary;
- claiming that RAES, SDL validity, a seed, canonical bytes, deterministic
  planning, or preserved provenance guarantees reproducibility or exact replay;
- treating an authored scenario, instantiated snapshot, execution plan,
  runtime snapshot, realized environment, experiment run, and study as aliases;
- implying complete current support for AI security, AI safety, testing, or any
  other application area without the relevant examples, profiles, backends, and
  evidence;
- describing cyber as an exhaustive boundary or, conversely, hiding that it is
  the repository's strongest current example and lineage base;
- adding a `Domain`, `AgenticEnvironment`, `Reproducibility`, or `Replay` schema,
  DTO, service, controller, persistence table, validator, or exception solely
  to support positioning prose;
- duplicating glossary definitions, metadata sources, example catalogs,
  verification commands, claim taxonomies, or scientific-completeness checks;
- implementing the guard as a repository-wide keyword ban, allowing a
  hand-maintained exclusion list to grow around false positives, or treating a
  negated limitation as a forbidden positive claim;
- importing `raes_mcp.server`, evaluating `docs/conf.py`, building the package,
  or running examples merely to extract user-facing strings for the policy
  check;
- adding a second CI workflow, test runner, result class, waiver format, or
  failure renderer for GOV-884 instead of reusing nox and
  `tools.policy.common.PolicyFailure`;
- bypassing `GOV-884` with `--skip-requirement`, adding an overbroad
  requirement-order ownership root, or creating a duplicate governance phase
  instead of extending `project-identity-migration`;
- editing accepted historical ADR text, external references, contract IDs,
  profile IDs, package import paths, fixtures, generated schemas, generated
  docs, `CHANGELOG.md`, or the package version as part of the rewrite;
- using normative `MUST`/`SHALL` language in explanatory positioning or
  presenting architecture-level and draft contract surfaces as shipped
  operational services;
- weakening warnings, negative capability statements, backend boundaries, or
  evidence qualifications to make the opening copy read more broadly.

## Non-Goals And Implementation Boundaries

- No SDL semantic, schema, contract, runtime, backend, participant, conformance,
  security, logging, persistence, replay, or exception behavior changes.
- No new domain taxonomy, application registry, project-description service, or
  generated metadata pipeline.
- No claim that every domain has complete examples, vocabularies, profiles,
  assets, backends, participant implementations, or scientific evidence.
- No removal of useful cyber examples or rewriting of historical/external
  records solely to make the repository appear domain-neutral.
- No production backend, managed service, storage system, scheduler, study
  manager, evidence collector, replay engine, or general agent framework.
- No implementation work in this preflight note.
