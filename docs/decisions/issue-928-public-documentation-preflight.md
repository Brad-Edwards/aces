# Issue 928 Public Documentation Preflight

Date: 2026-07-27

Issue: #928. Requirement: DOC-928.

This note records the repository-wide boundaries for the public-documentation
and community-readiness work. It is design guidance, not an implementation
plan, a new documentation schema, or a change to RAES runtime behavior.

## Architecture Decisions

### Public source and developer records

- `docs/public/` is the only Sphinx source root for the hosted site. Public
  pages move beneath it while retaining their current source-root-relative
  paths where practical; for example, `docs/explain/sdl/index.md` becomes
  `docs/public/explain/sdl/index.md` and still publishes at
  `/explain/sdl/index.html`.
- `docs/README.md` is the repository-facing developer-documentation index.
  `CONTRIBUTING.md` links to it. ADRs, issue/preflight notes, research working
  records, migrations, audits, search logs, and requirement/status snapshots
  remain under `docs/` but outside `docs/public/`.
- The public root is the positive publication authority. A blacklist of
  internal filenames may be defense in depth, but must not decide what is
  public. Files outside the root are never copied, symlinked, included, or
  globbed into a public build.
- Published URLs and repository source paths are separate compatibility
  concerns. Preserve hosted URLs by preserving paths relative to the new
  source root. Update repository-relative links and governed `source_refs`
  after moves. Add an explicit redirect only when a hosted route actually
  changes; do not redirect an intentionally unpublished working record back
  into the public site.

One `PUBLIC_DOCS_ROOT` constant in `noxfile.py` is the local build, Vale, and
publication-check parameter. `.github/workflows/docs.yml` calls the nox docs
session instead of repeating source and output paths. Read the Docs points its
Sphinx configuration directly into the same root because its configuration
schema cannot consume a Python constant. Adding a page beneath the root must
not require another allowlist edit.

### Independent validation responsibilities

Keep the existing validation layers distinct:

- Sphinx owns MyST/reStructuredText parsing, autodoc, toctrees, references,
  and warning-strict HTML and link-check builds.
- Vale owns the mechanically enforceable subset of public prose style.
- `tools/check_project_positioning.py` continues to own RAES identity,
  application-area framing, and evidence-bounded capability claims. Update its
  registered paths after public files move; do not reproduce those semantic
  checks as Vale vocabulary rules.
- One focused public-documentation checker owns source-root containment and
  publication inventory. It derives allowed page routes and search-index
  document names from files beneath `docs/public/`, known Sphinx-generated
  routes, plus an explicit redirect map if redirects are later needed. It
  rejects symlinks and source directives that escape the root, and verifies
  that generated HTML/search artifacts contain no additional document routes.
  It also rejects Sphinx-copied downloads whose source is outside the root;
  public references to canonical specs/contracts use repository links rather
  than silently copying those authorities into the hosted artifact.
- Existing example-library and SDL validators continue to own example meaning.
  Quickstart and README snippets must be executed by focused tests against the
  current CLI or Python entrypoint rather than acquiring a second SDL parser.
  The current CLI has `format`, `resolve`, `verify-imports`, and `publish`, but
  no generic `raes sdl validate` command. Use `parse_sdl`/`parse_sdl_file` for
  the first validation success rather than adding a command to fit the prose.

The publication checker follows the existing repository-policy convention: a
pure evaluator returns `tools.policy.common.PolicyFailure`; its CLI reuses the
existing text/JSON rendering and exception mechanism. It reads bounded UTF-8
or structured inputs through containment-checked repository paths, performs no
network access, and reports rule id, path, and bounded messages rather than
file bodies.

### Reader-first editorial boundary

Stripe Documentation is the editorial exemplar for task-first,
example-led entry pages, not a source of RAES semantics, copied content, theme
assets, or a new documentation framework.

- The README, overview, quickstart, tutorial entry points, SDL authoring entry,
  CLI/Python entry, backend entry, research entry, and contributing/support
  entry lead with a reader task and a current, tested example.
- Normative specifications, explanatory guidance, academic evidence,
  reference material, and implementation status remain visibly distinct.
  ADR-009, ADR-019, and `specs/authority/authority-boundary.yaml` remain the
  authority boundary; moving or rewriting a page does not promote it.
- `docs/explain/reference/documentation-style-guide.md` is the incumbent prose
  policy and becomes developer guidance outside the public root. Extend it
  with the reader-first rules and the Stripe exemplar. Vale rules encode only
  objective checks and point back to that guide.
- A repository-owned RAES Vale style and vocabulary may enforce spelling,
  casing, prohibited promotional/process language, and other low-ambiguity
  rules. Do not add broad bans on valid technical words such as `surface`,
  `boundary`, `authority`, `bounded`, `cyber`, `replay`, or `deterministic`.
  Do not fetch third-party Vale packages during a gate.

Pin Vale in `tools/tool_versions.py` and provision it through the same
versioned, checksum-verified, repository-local cache pattern as gitleaks and
OSV-Scanner. Vale is a nox docs substage with `SessionReporter` output, not a
new pre-commit command, GitHub Actions command list, logger, or exception
hierarchy.

### Publication and workflow topology

- `_run_docs` in `noxfile.py` is the canonical docs graph. It runs the source
  boundary check, Vale, warning-strict Sphinx HTML, public-output inventory,
  focused executable documentation examples, and link checking. `verify`,
  `verify-changed`, pre-push, CI, and the docs workflow must select that graph
  consistently.
- Update `tools/verification_plan.py`: documentation configuration, Vale
  configuration/styles, public-source moves, publication tooling, and docs
  workflow changes must select the docs graph. The current full fallback has
  `docs=False`; leaving that unchanged would let the riskiest documentation
  changes skip documentation validation locally.
- `.readthedocs.yaml`, `docs/public/conf.py`, `docs/Makefile`, and the GitHub
  Pages upload all use the public root and keep output outside it. Read the
  Docs remains warning-strict and installs through the frozen uv lock.
- Search indexes and sitemaps are derivative publication artifacts, not
  independent content sources. The same public source root governs production,
  pull-request previews, GitHub Pages, search document names, and sitemap
  routes. Do not maintain separate public lists for each publisher.
- `docs/public/conf.py` retains installed distribution metadata as the version
  source and the honest `0.0.0+unknown` fallback. Do not introduce an
  environment-controlled title, version, source root, or inclusion list.

DOC-928 belongs in the existing `documentation-surfaces` requirement phase.
Extend that phase only for the focused publication/style tests and moved
public paths it must own; do not add a parallel documentation-governance phase.
Because the branch name does not contain a UID, governance commands use
`RAES_REQUIREMENT_UID=DOC-928` or `--requirement-uid DOC-928`, never the
requirement-free bypass.

## Canonical Incumbents

Implementation builds on these existing surfaces:

- Documentation build and publication: `noxfile.py`, `.readthedocs.yaml`,
  `.github/workflows/docs.yml`, `docs/Makefile`, `docs/conf.py`, and the
  locked `docs` extra in `implementations/python/pyproject.toml` and
  `implementations/python/uv.lock`.
- Verification and workflow composition: ADR-014,
  `.ground-control.yaml`, `.gc/plan-rules.md`, `.pre-commit-config.yaml`,
  `tools/verification_plan.py`, `tools/verify_all.py`, and
  `.github/workflows/ci.yml`.
- Policy evaluation and errors: `tools.policy.common.PolicyFailure`,
  `safe_repo_path`, bounded loaders, `tools/policy/exceptions.yaml`,
  `tools/check_repo_policy.py`, and the temporary-root test pattern in
  `implementations/python/tests/test_*_policy.py`.
- Claims and terminology: `tools/check_project_positioning.py`,
  `docs/explain/reference/documentation-style-guide.md`,
  `docs/explain/reference/glossary.md`, ADR-009, ADR-019, ADR-021, ADR-093,
  `specs/agent-guidance/agent-guidance.yaml`, and
  `specs/authority/authority-boundary.yaml`.
- Examples and commands: `examples/README.md`,
  `examples/library/catalog.yaml`, `tools/check_example_library.py`, current
  parser/CLI integration tests, and checked-in scenarios. A public example
  points to or is tested against these authorities; it does not become a
  parallel fixture corpus.
- Community and release workflow: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, `SUPPORT.md`, existing issue/PR templates,
  `.github/workflows/release-please.yml`, and `.github/dependabot.yml`.
- README packaging: root `README.md`, the Hatch metadata hook in
  `implementations/python/hatch_build.py`, and installed-wheel tests. The root
  README is also the PyPI long description; do not add a package-local copy.
- Supply-chain workflow conventions: SHA-pinned actions, explicit least-
  privilege permissions, `GITHUB_TOKEN`, Dependabot updates for GitHub
  Actions, OIDC where already required for publishing, and no repository PAT.

Moving the public tree requires a whole-repository reference migration.
Hard-coded incumbents include `tools/check_project_positioning.py`,
`tools/check_sdl_lineage.py`, `specs/agent-guidance/agent-guidance.yaml`,
`examples/library/catalog.yaml`, example `source_refs`, root/community
Markdown links, formal-spec links, and their focused tests. Treat broken
governed references as migration defects; do not leave compatibility copies
outside the public root or duplicate pages to satisfy old paths.

## Cross-Cutting Layers

### Security and configuration

- **GitHub authorization:** Scorecard uses the official OpenSSF workflow and
  the workflow `GITHUB_TOKEN`. Start from `permissions: {}` or an equivalent
  deny-by-default shape, then grant `contents: read` and only the documented
  job-level `security-events`/`id-token` capabilities required for SARIF and
  result publication. Keep checkout credentials non-persistent. Do not add a
  PAT, `pull_request_target`, write access to repository contents, or an
  approval rule that blocks the sole maintainer or release-please.
- **Release authorization:** `.github/workflows/release-please.yml` remains the
  version, changelog, release, and `main`-to-`dev` authority. Repository rules
  and required checks must continue to admit its `GITHUB_TOKEN`-created release
  PR and the maintainer's documented release operation.
- **Read the Docs and Pages:** public builds consume checked-in source and the
  frozen docs dependency set. No token, private repository content, environment
  dump, or host path is injected into Sphinx configuration or generated pages.
  Only the verified public output directory is uploaded.
- **Path and parser validation:** RTD YAML, GitHub workflow YAML, Vale config,
  MyST/reStructuredText, Python Sphinx config, TOML/uv lock data, and any
  redirect mapping pass their owning parsers. Publication tooling resolves
  repository-relative paths, rejects absolute/parent traversal and symlink
  escapes, bounds file size, and never executes documentation input.
- **Secret handling:** retain private-key detection and gitleaks in the
  canonical hygiene graph. Do not publish `.env` examples with real values,
  credentials, tokens, private URLs, prompts, hidden answers, raw backend
  objects, or machine-specific paths. Synthetic SDL values remain distinct
  from operator secrets.
- **OS-level exposure:** invoke Sphinx, Vale, and link checking with fixed argv
  and repository-contained paths. Tokens and credentials never appear in argv,
  command interpolation, artifacts, or error messages. Downloaded Vale
  binaries are version pinned and checksum verified before execution.
- **Error envelopes and observability:** repository policy failures use
  `PolicyFailure`; nox uses `SessionReporter`; Sphinx and Vale retain their
  native bounded diagnostics; Scorecard emits its official SARIF and GitHub
  annotations. Do not dump source bodies, environment values, tokens,
  tracebacks, or complete external responses into a new result format. No new
  application logger, audit stream, or exception class is needed.
- **Persistence:** checked-in sources, the uv lock, ephemeral build output,
  GitHub Pages/Read the Docs pages, official Scorecard/SARIF publication, and
  the bestpractices.dev project record are the only persistence surfaces.
  There is no application database, DTO, repository class, migration, or
  runtime configuration binding in this work.

Enrollment on bestpractices.dev and repository-rule changes are authenticated
external administrative actions. Keep credentials in the provider's browser
or app authorization flow, verify resulting public state before adding a
badge, and record unmet criteria honestly. Do not make a hermetic repository
check depend on bestpractices.dev availability.

Community-file revisions use the CNCF Project Template as a checklist, not a
source of fictional teams, meetings, elections, contributor ladders,
independent escalation bodies, CLAs/DCO enforcement, or response guarantees.
Keep one owner for each route: `CONTRIBUTING.md` for setup and submissions,
`SUPPORT.md` for questions, issue templates for bugs/features, `SECURITY.md`
for coordinated disclosure, and `CODE_OF_CONDUCT.md` for conduct. Move the
dated commit-authorship anomaly out of the public security policy and retain it
through the developer/audit index. Validate issue-template frontmatter and
referenced labels rather than copying labels that do not exist.

### Extensibility seam

The extension seam is placement beneath `PUBLIC_DOCS_ROOT`.

- A new public page is curated by placing it under that root and linking it
  from the public information architecture; source, search, sitemap, preview,
  and Vale coverage follow without adding another publication allowlist.
- A new developer record is placed outside the root and linked from
  `docs/README.md`; it remains repository-visible without entering a hosted
  artifact.
- A real hosted route change adds one explicit old-to-new redirect entry.
  Redirects are the only parameterized exception to the output route set.
- A new public root-level community entrypoint is added to the small
  `PUBLIC_ENTRYPOINTS` style/test tuple. Do not recursively lint all developer,
  historical, normative, or research prose to accommodate one new public file.

## Gotchas and Anti-Patterns

Avoid:

- changing only the toctree or `exclude_patterns` while Sphinx still receives
  the full `docs/` tree;
- copying, symlinking, `include`-ing, or `literalinclude`-ing developer records
  from outside the public root;
- maintaining separate allowlists for Sphinx, search, sitemap, previews,
  Pages, RTD, and Vale;
- treating absence from navigation as absence from generated HTML or search;
- overlooking `{download}`, `download`, include, or literal-include directives
  that can copy or inline files from outside the public root even when the page
  route itself is allowed;
- moving public source paths without updating policy checkers, source
  references, formal-spec links, examples, tests, and `html_theme_options`;
- duplicating public pages at old repository paths to preserve GitHub links;
- adding redirects for internal pages that should stop publishing;
- checking generated HTML only for a growing blacklist instead of deriving
  its allowed routes from the positive source root;
- using Vale as a semantic claim checker, SDL validator, link checker, or
  substitute for editorial review;
- enforcing reader-first prose with broad keyword bans, sentence-length
  absolutism, or a copied third-party style package;
- copying Stripe content, branding, information architecture, or visual
  assets, or implying Stripe endorses RAES;
- creating another docs script, CI command list, failure DTO, waiver file,
  logger, or test runner outside nox and `tools.policy.common`;
- duplicating SDL examples that are not extracted and executed by tests, or
  documenting commands that only display `--help` but do not reach first
  success;
- inventing a generic validation CLI or runtime feature solely to make the
  quickstart read more smoothly;
- publishing raw ADR/preflight, audit, migration-working, research-log,
  requirement, Ground Control, or current-state records merely because they
  contain durable facts; curate the useful fact into a public explanation;
- claiming Scorecard or bestpractices.dev status before the external result is
  live, gaming criteria, using N/A dishonestly, or adding governance the
  single-maintainer project cannot satisfy;
- copying CNCF meetings, teams, elections, escalation committees, labels,
  CLAs/DCO requirements, or service levels that the repository does not have;
- granting broad workflow permissions, using unpinned actions, introducing a
  long-lived token, or weakening release-please to improve a score;
- editing `CHANGELOG.md`, the package version, normative specifications,
  contracts, schemas, runtime behavior, or conformance semantics to make
  documentation claims easier.

## Non-Goals and Implementation Boundaries

- No SDL, schema, contract, parser, processor, backend, runtime, API, MCP,
  authentication, authorization, logging, persistence, or exception behavior
  change.
- No deletion of developer, research, migration, audit, issue, preflight, or
  Ground Control records from the repository.
- No new documentation content schema, CMS, database, service, controller,
  repository layer, project-description registry, or generated prose system.
- No promise of production backends, managed environments, deterministic
  outcomes, exact replay, complete domain coverage, staffing levels, response
  SLAs, independent review, or multi-maintainer governance.
- No Silver/Gold best-practices claim, mandatory independent approval, PAT for
  Scorecard/release automation, or replacement of release-please.
- No broad editorial rewrite of normative or historical records. Public prose
  may explain their durable conclusions while retaining their authority and
  evidence boundaries.
- No implementation of DOC-928 in this preflight note.
