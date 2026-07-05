# Releasing aces-sdl

`aces-sdl` is published to **PyPI**, and the release version is **derived from the
towncrier changelog fragments** — the single source of truth. The fragment types
you already write (`changelog.d/<issue>.<type>.md`) drive the changelog *and* the
SemVer bump *and* the git tag, so they can never disagree. There is no version
string to hand-edit (#684).

`aces-sdl` also ships the published contract corpus as package data, so
`aces conformance backend` and SDL semantic validation work from an installed
wheel — no source checkout required. Every release binds the code and the corpus
in one versioned artifact (#537).

## Version rubric (fragment type → bump)

`tools/compute_release.py` scans the pending fragments and takes the **highest**
bump present:

| Fragment type | Bump |
|---|---|
| `breaking`, `removed` | **major** |
| `added`, `changed`, `deprecated` | **minor** |
| `security`, `fixed` | **patch** |
| *(no fragments)* | no release |

Major is real: a `breaking` (or `removed`) fragment on `0.x` bumps to `1.0.0`.
`breaking` is the explicit major signal; use it for any backward-incompatible
change that is not itself a `removed`. The base version is the latest `v*` git
tag, falling back to the latest `CHANGELOG.md` header.

## Cutting a release

1. **Prepare** — run the **Prepare Release** workflow (`release-prep.yml`,
   `workflow_dispatch`) from `dev`. It computes the next version, collates the
   pending fragments into `CHANGELOG.md` with towncrier (deleting them), and
   opens a PR into `dev`.
2. **Merge** that collation PR into `dev`.
3. **Promote** `dev` → `main` (merge or rebase — never squash).
4. `release.yml` runs on the push to `main`: it reads the just-collated version
   from the top of `CHANGELOG.md` and, if there's no tag for it yet, **creates
   the tag** (tag-only — `main` is never committed to), builds the
   corpus-bundled wheel + sdist (hatch-vcs stamps the version from the tag),
   re-verifies the corpus payload, attaches a CycloneDX SBOM, publishes to PyPI
   via OIDC, and creates a GitHub Release whose notes are the `CHANGELOG.md`
   section for that version.

If the pending fragments are empty, `compute_release.py` reports no release and
nothing ships.

Everything is derivable locally:

```sh
python tools/compute_release.py --format json      # next version + bump + counts
uvx towncrier build --version <X.Y.Z> --draft      # preview the changelog section
uv build --out-dir dist implementations/python     # build (clean tag → clean version)
```

## Why the split (protected `main`)

`main` is branch-protected with no bypass, so the release can't commit to it. The
changelog collation (which *is* a commit — it rewrites `CHANGELOG.md` and deletes
fragments) therefore lands on `dev` via the prep PR; `main` is only ever
**tagged**. That's why cutting a release is prepare-on-`dev` then
promote-to-`main`, not a single push.

## First-release bootstrap (one-time)

The changelog reflects `0.17.0` (hand-authored history), but nothing was ever
tagged or published. Seed the baseline so automation starts cleanly:

```sh
git tag v0.17.0 <current-main-sha>
git push origin v0.17.0
```

This marks `0.17.0` as already-released (never published to PyPI — it's a
baseline), so the first *published* release is the next computed version
(`0.18.0` from the current backlog). Without this tag the first push to `main`
would try to publish `0.17.0`.

## PyPI trusted publishing (one-time, maintainer)

Register a **pending** trusted publisher on PyPI before the first upload (no
token stored):

- PyPI → *Your projects* → *Publishing* → *Add a pending publisher* → GitHub
- PyPI Project Name: `aces-sdl`
- Owner: `Brad-Edwards`  ·  Repository: `aces`
- Workflow name: `release.yml`  ·  Environment name: `pypi`

The `release` job sets `environment: pypi` (a GitHub environment restricted to
`main`). A filename/environment mismatch 403s only the PyPI publish step.

## Pinning from a downstream backend

```
aces-sdl==<X.Y.Z>
```

or, for an unpublished commit, the git subdirectory install:

```
aces-sdl @ git+https://github.com/Brad-Edwards/aces.git@v<X.Y.Z>#subdirectory=implementations/python
```
