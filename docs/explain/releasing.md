# Releasing aces-sdl

`aces-sdl` is published to **PyPI** and releases are cut **automatically** when
`dev` is promoted to `main`. The model is the conventional-commit-driven pipeline
from aces-scenario-packs ADR 0006 (tracked for aces in issue #684), built on the
corpus-bundled wheel from #537.

`aces-sdl` ships the published contract corpus (backend/semantic profiles, the
fixture conformance corpus, the concept-authority catalogs, and the schemas) as
package data, so `aces conformance backend` and SDL semantic validation work from
an installed wheel — no source checkout required. Every release binds the Python
code and the corpus together in one versioned artifact.

## The model (how a release happens)

1. Feature PRs **squash-merge into `dev`** with a Conventional Commit PR title
   (the required `pr-title-lint` check enforces the type). The squashed commit
   subject becomes the conventional commit.
2. Promoting **`dev` → `main`** (merge or rebase — never squash, or the
   per-change history PSR reads is lost) triggers `.github/workflows/release.yml`.
3. `python-semantic-release` (PSR) inspects the Conventional Commits since the
   last tag, computes the next SemVer, and creates the **git tag + GitHub
   Release** with notes generated from the commits. It is **tag-only**
   (`commit = false`) — it never pushes a commit back to protected `main`.
4. If PSR reports a release, the job builds the corpus-bundled wheel + sdist with
   `uv build`, **re-verifies the corpus payload** is present (the #537
   guarantee), attaches a CycloneDX SBOM + the distributions to the GitHub
   Release, and **publishes to PyPI via OIDC trusted publishing** (no stored
   token).

If the batch of commits since the last tag is chores/docs only, PSR releases
**nothing** — no tag, no PyPI upload.

### Versioning is tag-derived

There is no version string to edit. `[tool.hatch.version] source = "vcs"`
(hatch-vcs) derives the built artifact's version from the git tag PSR creates;
`aces.__version__` reads it back from installed distribution metadata. Do not
hand-edit a version anywhere.

### The type → bump rubric

The commit *type* is the decision (authoritative mapping:
`[tool.semantic_release.commit_parser_options]` in
`implementations/python/pyproject.toml`, kept in sync with `CONVENTIONAL_TYPES`
in `tools/check_pr_title.py`):

| Type | Releases? | Bump |
|---|---|---|
| `feat`, `added`, `changed`, `deprecated`, `removed` | yes | minor |
| `fix`, `fixed`, `perf`, `security` | yes | patch |
| any of the above with `!` / `BREAKING CHANGE:` footer | yes | major (pre-1.0 → minor) |
| `docs`, `chore`, `ci`, `test`, `refactor`, `build`, `style`, `revert` | no | — |

One-line rule: **release when a consumer of the package would observe the
change; hold when it is repo-internal.** A breaking removal is `removed!:`.

Note: this is deliberately a superset of PSR's default `feat`/`fix` vocabulary,
because aces uses towncrier-style change types as first-class PR-title types.
The changelog *fragment* files under `changelog.d/<issue>.<type>.md` are a
separate mechanism that feeds the in-repo `CHANGELOG.md` via towncrier; PSR
generates the GitHub Release notes from the commits.

## How the corpus is bundled

The corpus is the normative authority at the repository-root `contracts/` tree
(ADR-009). It is **not** moved or duplicated in source control. At build time a
hatchling build hook (`implementations/python/hatch_build.py`) force-includes it
into the wheel at `aces_contracts/_corpus`, and the sdist vendors it at
top-level `_corpus/` so a wheel built from the sdist finds it too. At runtime,
`aces_contracts.corpus` resolves the corpus via `importlib.resources`, falling
back to the in-repo `contracts/` tree only for source/editable checkouts.

Build artifacts locally with:

```sh
uv build --out-dir dist implementations/python
```

Locally (no git tag at `HEAD`) hatch-vcs stamps a dev version; on the release
runner the tag PSR just created yields the exact release version.

## First-release bootstrap (one-time)

`main` has no release tag yet, so the first promotion has no prior version to
bump from. Bootstrap by running the **Release** workflow via
`workflow_dispatch` with `force: minor` (from the Actions tab, on `main`). With
no prior tag and `allow_zero_version = true` that cuts **`v0.1.0`** — the first
PyPI release. PSR auto-manages every release after that.

> To start the PyPI line at `v0.3.0` instead (matching the last hand-maintained
> `version` string), first create and push a baseline tag `git tag v0.2.0 <main-sha>
> && git push origin v0.2.0` (never built/published), then run the workflow with
> `force: minor` → `v0.3.0`. Decide before the first run; the default `force:
> minor` from zero gives `v0.1.0`.

## PyPI trusted publishing (one-time, maintainer)

PyPI OIDC publishing needs a one-time **pending trusted publisher** registered on
PyPI before the first upload (no token is stored):

- PyPI → *Your projects* → *Publishing* → *Add a pending publisher*
- PyPI Project Name: `aces-sdl`
- Owner: `Brad-Edwards`, Repository: `aces`
- Workflow name: `release.yml`
- Environment name: `pypi`

The workflow's `release` job sets `environment: pypi`, so the GitHub `pypi`
environment must exist (Settings → Environments). A mismatch in the workflow
filename or environment name 403s only the PyPI publish step.

## Pinning from a downstream backend

Once published, pin the PyPI release:

```
aces-sdl==<X.Y.Z>
```

or, for a pre-release/unpublished commit, the git subdirectory install:

```
aces-sdl @ git+https://github.com/Brad-Edwards/aces.git@v<X.Y.Z>#subdirectory=implementations/python
```
