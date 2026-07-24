# Releasing RAES via aces-sdl

`aces-sdl` is published to **PyPI**, and releases are automated with
[release-please](https://github.com/googleapis/release-please) (#684). You never
hand-edit the version or `CHANGELOG.md`: release-please derives both from the
Conventional Commit history on `main`.

`aces-sdl` also ships the published contract corpus as package data, so
`raes conformance backend` and SDL semantic validation work from an installed
wheel. Every release binds the code and the corpus in one versioned artifact
(#537).

## How a release happens

1. Feature PRs **squash-merge** (into `dev`, then promoted to `main`) with a
   Conventional Commit **PR title** — the squashed commit is what release-please
   reads. The required `title-guard` check enforces the shape.
2. On every push to `main`, `.github/workflows/release-please.yml` maintains a
   **release PR** titled `chore(main): release X.Y.Z` that bumps the version and
   regenerates `CHANGELOG.md` from the commits since the last release.
3. **Merge that release PR.** release-please tags `vX.Y.Z` and creates the GitHub
   Release; the `publish` job then builds the corpus-bundled wheel + sdist,
   verifies the corpus payload (#537), publishes to PyPI via OIDC, and attaches
   the distributions to the Release.

Nothing is hand-run, and feature PRs never touch `CHANGELOG.md` (release-please
owns it) — no fragment collisions.

## Version rubric (PR-title type → bump)

| Type | Releases? | Bump |
|---|---|---|
| `feat` | yes | minor |
| `fix`, `perf` | yes | patch |
| `feat!` / `fix!` / `BREAKING CHANGE:` footer | yes | major (pre-1.0 demoted to minor) |
| `docs`, `chore`, `refactor`, `test`, `ci`, `build` | no | — |

Use `feat:`/`fix:` for consumer-visible changes so release-please cuts a release.

## Configuration

- `release-please-config.json` — package at repo root (so `CHANGELOG.md` stays at
  the root), `release-type: python`, `package-name: aces-sdl`. The actual version
  literal lives in the subdir pyproject and is bumped via `extra-files`
  (`implementations/python/pyproject.toml` → `$.project.version`).
- `.release-please-manifest.json` — the version source of truth: `{".": "X.Y.Z"}`.
- `implementations/python/pyproject.toml` — static `[project] version`
  (release-please rewrites it). `aces.__version__` derives from the installed
  distribution metadata. The `raes` and `raes-mcp` console scripts are the
  preferred current commands; `aces` and `aces-mcp` remain compatibility aliases.

## Caveat: the release PR and required checks

The release PR is opened by `GITHUB_TOKEN`, so **required status checks do not
auto-run on it** (GitHub's recursion guard). Two options:

- **Admin-merge** the release PR (bypass the required checks for that PR), or
- Give release-please a **PAT** (repo `contents`+`pull_requests`) as the `token`
  input so its PRs trigger checks normally.

## First release

`main` starts at `0.18.0` (the manifest/pyproject baseline; the historical
changelog through `0.18.0` is preserved in `CHANGELOG.md`). The first `feat:`/
`fix:` merged to `main` after adoption produces a release PR bumping from
`0.18.0`; merging it publishes the first PyPI artifact.

## PyPI trusted publishing (one-time, maintainer)

Register a **pending** trusted publisher on PyPI before the first upload (no
token stored):

- PyPI → *Your projects* → *Publishing* → *Add a pending publisher* → GitHub
- PyPI Project Name: `aces-sdl`
- Owner: `Brad-Edwards`  ·  Repository: `aces`
- **Workflow name: `release-please.yml`**  ·  Environment name: `pypi`

> If you previously registered the publisher against `release.yml`, update it to
> `release-please.yml` (or add a second pending publisher) — the workflow filename
> must match or only the PyPI publish step 403s.

## Pinning from a downstream backend

```
aces-sdl==<X.Y.Z>
```
