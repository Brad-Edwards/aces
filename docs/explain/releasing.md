# Releasing aces-sdl

`aces-sdl` is published to **PyPI**. The version is a **single committed literal**
— `__version__` in `implementations/python/src/aces/__init__.py` — bumped by
`tools/release.py` from the pending towncrier changelog fragments. The changelog
fragments, the `__version__` literal, and the git tag all carry the same value
(#684).

`aces-sdl` also ships the published contract corpus as package data, so
`aces conformance backend` and SDL semantic validation work from an installed
wheel. Every release binds the code and the corpus in one versioned artifact
(#537).

## Version rubric (fragment type → bump)

`tools/release.py` scans the pending fragments and takes the **highest** bump:

| Fragment type | Bump |
|---|---|
| `removed` | **major** once already ≥ 1.0; **minor** while pre-1.0 |
| `added`, `changed`, `deprecated` | **minor** |
| `security`, `fixed` | **patch** |
| `breaking` | recorded in the changelog, **no auto-bump** — force with `--version` |
| *(no fragments)* | nothing to release |

`breaking` renders a "Breaking Changes" section so incompatible changes are
recorded now, but it never escalates the version on its own. To cut the first
major, force it: `python tools/release.py --version 1.0.0`.

## Cutting a release

1. From an up-to-date checkout (with the pending fragments present), run:

   ```sh
   python tools/release.py            # or: --version X.Y.Z to force
   ```

   This bumps `__version__`, runs `towncrier build` (collating the fragments into
   `CHANGELOG.md` and deleting them), and prints the next commands.
2. Commit on a release branch and open a PR to `main`:

   ```sh
   git switch -c release/vX.Y.Z
   git commit -am "chore: release vX.Y.Z"
   gh pr create --base main --title "chore: release vX.Y.Z" --fill
   ```
3. Merge the PR into `main`. That push runs `.github/workflows/release.yml`: the
   `decide` job confirms the fragments are collated (none pending) and that
   `v<version>` is untagged, then the `release` job builds the corpus-bundled
   wheel + sdist, verifies the corpus + version, tags `v<version>` (tag-only —
   `main` is never committed to by the workflow), publishes to PyPI via OIDC, and
   cuts a GitHub Release whose notes are the `CHANGELOG.md` section.

No commit is pushed to `main` by any bot — only a tag — so no PAT, deploy key, or
ruleset bypass is needed. The version-bump/changelog commit reaches `main` the
normal way: a human-reviewed PR merge.

### Keeping `dev` in sync

Feature PRs merge to `dev` (each adds a `changelog.d/` fragment). The release PR
targets `main`, so after it merges, **back-merge `main` → `dev`** to bring the
bumped `__version__` and the collated `CHANGELOG.md` back to `dev` (otherwise the
next `release.py` run computes from a stale literal).

## First release (0.18.0)

The literal starts at `0.17.0` (the last hand-authored changelog version, never
published). The `decide` job **skips publishing while fragments are pending**, so
merging the release-infra change to `main` cannot accidentally publish `0.17.0`.
To ship the first release:

1. Run `python tools/release.py` — the pending backlog (`added`/`changed`/
   `fixed`/`security`) computes a minor bump → **`0.18.0`**, collated into
   `## [0.18.0]`.
2. PR the `release/v0.18.0` branch to `main` and merge → `v0.18.0` is tagged,
   built, and published.

## PyPI trusted publishing (one-time, maintainer)

Register a **pending** trusted publisher on PyPI before the first upload (no
token stored):

- PyPI → *Your projects* → *Publishing* → *Add a pending publisher* → GitHub
- PyPI Project Name: `aces-sdl`
- Owner: `Brad-Edwards`  ·  Repository: `aces`
- Workflow name: `release.yml`  ·  Environment name: `pypi`

The `release` job sets `environment: pypi` (a GitHub environment restricted to
`main`). A filename/environment mismatch 403s only the PyPI publish step.

## Contributor rule

Per PR, add a `changelog.d/<slug>.<type>.md` fragment; **never edit
`CHANGELOG.md` directly** (only `tools/release.py` / release-collation commits
do). The fragment `<type>` is what determines the next version.

## Pinning from a downstream backend

```
aces-sdl==<X.Y.Z>
```

or, for an unpublished commit, the git subdirectory install:

```
aces-sdl @ git+https://github.com/Brad-Edwards/aces.git@v<X.Y.Z>#subdirectory=implementations/python
```
