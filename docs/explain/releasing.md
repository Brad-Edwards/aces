# Releasing aces-sdl

`aces-sdl` ships the published contract corpus (backend/semantic profiles, the
fixture conformance corpus, the concept-authority catalogs, and the schemas) as
package data so that `aces conformance backend` and SDL semantic validation work
from an installed wheel — no source checkout required. Releases bind the Python
code and the corpus together in one versioned artifact, so downstream backends
(e.g. APTL) can pin a real version instead of a `dev` commit SHA.

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

Both the wheel and the sdist contain the corpus and are independently
installable.

## Cutting a release

1. Bump `version` in `implementations/python/pyproject.toml` (and run
   `uv lock` so the lockfile records the new version).
2. Collate the changelog fragments into `CHANGELOG.md`:

   ```sh
   uvx towncrier build --version <X.Y.Z> --date $(date -u +%F)
   ```

3. Land the version bump + changelog on the default branch via the normal PR
   flow (CI must be green).
4. Tag the merged commit and push the tag:

   ```sh
   git tag v<X.Y.Z>
   git push origin v<X.Y.Z>
   ```

   The `Release` workflow (`.github/workflows/release.yml`) runs on `v*` tags:
   it builds the wheel + sdist, asserts the corpus payload is present in the
   wheel, and publishes a GitHub Release with the artifacts attached. The push
   to `v*` also runs the normal CI `verify`/`fuzz`/`sonar` jobs.

## Pinning from a downstream backend

Once a release is published, pin the tag instead of a `dev` commit SHA:

```
aces-sdl @ git+https://github.com/Brad-Edwards/aces.git@v<X.Y.Z>#subdirectory=implementations/python
```

or install the release wheel directly.

## PyPI (future)

The release workflow publishes a GitHub Release using the built-in
`GITHUB_TOKEN`; no extra secrets are required. Publishing to PyPI is a separate,
maintainer-owned step that requires configuring
[trusted publishing](https://docs.pypi.org/trusted-publishers/) for the project;
it is intentionally not wired into this workflow so the release path needs no
long-lived publishing credentials.
