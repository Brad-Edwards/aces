# Releasing RAES via raes

`raes` is published to **PyPI**, and releases are automated with
[release-please](https://github.com/googleapis/release-please) (#684). You never
hand-edit the version or `CHANGELOG.md`: release-please derives both from the
Conventional Commit history on `main`.

`raes` also ships the published contract corpus as package data, so
`raes conformance backend` and SDL semantic validation work from an installed
wheel. Every release binds the code and the corpus in one versioned artifact
(#537). PyPI publication additionally requires the repository's canonical
verification graph to pass for the exact commit named by the release (GOV-928).

## How a release happens

1. Feature PRs **squash-merge** (into `dev`, then promoted to `main`) with a
   Conventional Commit **PR title** — the squashed commit is what release-please
   reads. The required `title-guard` check enforces the shape.
2. On every push to `main`, `.github/workflows/release-please.yml` maintains a
   **release PR** titled `chore(main): release X.Y.Z` that bumps the version and
   regenerates `CHANGELOG.md` from the commits since the last release.
3. **Merge that release PR.** Release Please tags `vX.Y.Z`, creates a **draft**
   GitHub Release, and returns the commit SHA that it tagged. Forced tag creation
   keeps draft releases discoverable by Release Please. The release workflow
   requires that tag and SHA to match and that the commit belong to `main`.
4. The workflow invokes `.github/workflows/canonical-verification.yml` for that
   exact SHA. This is the same proof-bearing `nox -s verify` gate used by CI.
   It does not poll branch status or accept a check from another commit.
5. A separate read-only job checks out that SHA and must complete the RUN-314
   reference-backend tests against a real container runtime. Release-required
   mode fails when the runtime or digest-pinned reviewed image is unavailable,
   when pytest collects zero tests, or when any selected test skips. The
   ordinary PR/local Docker lane remains optional.
6. A read-only job checks out the verified SHA, builds the corpus-bundled wheel
   and sdist, checks the corpus in both archives, installs each exact artifact in
   its own fresh environment, and runs `raes conformance backend --profile
   provisioning-only` outside the checkout.
7. Only those tested distributions cross into the `pypi` environment. After any
   environment approval and artifact download, the job freshly revalidates the
   Release object id, draft state, exact tag ref, and fully dereferenced commit
   SHA immediately before its pinned OIDC publisher runs. A separate GitHub-only
   job performs the same identity checks again, attaches the artifacts, and
   re-reads the Release identity after attachment before making the exact
   numeric Release id public. Keeping these jobs separate means a failed
   attachment/finalization can be retried without attempting a second PyPI
   upload. If the public-finalization response was lost after GitHub applied
   it, the retry accepts the already-public Release only after downloading and
   byte-comparing both attached distributions and rechecking the id, tag, and
   commit SHA.

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
  the root), `release-type: python`, `package-name: raes`. The actual version
  literal lives in a dedicated RAES package file and is bumped via `extra-files`
  (`implementations/python/packages/raes/_version.py`).
- `.release-please-manifest.json` — the version source of truth: `{".": "X.Y.Z"}`.
- `implementations/python/packages/raes/_version.py` — build version source
  (release-please rewrites it). `raes.__version__` derives from the installed
  `raes` distribution metadata.
  The `raes` and `raes-mcp` console scripts are the only current commands.
- `.github/workflows/canonical-verification.yml` — reusable exact-commit
  verification graph called by both ordinary CI and the release workflow. Its
  input is a full commit SHA, not a branch or tag; the proof-bearing nox job
  checks out and binds itself to that value.
- `release-please-config.json` creates releases as drafts and forces the tag to
  exist immediately. Only the gated GitHub publication job removes draft state.

## Caveat: the release PR and required checks

The release PR is opened by `GITHUB_TOKEN`, so **required status checks do not
auto-run on the PR** (GitHub's recursion guard). Two review options remain:

- **Admin-merge** the release PR (bypass the required checks for that PR), or
- Give release-please a **PAT** (repo `contents`+`pull_requests`) as the `token`
  input so its PRs trigger checks normally.

Neither option can bypass publication verification. After the release PR lands,
the release workflow keeps the GitHub Release private as a draft while it runs
the canonical graph against the exact tagged commit. PyPI upload,
GitHub artifact attachment, and public Release finalization depend directly on
that successful graph. On automatic pushes, release resolution also requires
the Release Please job itself to finish successfully; an output from a skipped,
cancelled, or failed job is never sufficient.

## External tag-protection control

Configure a GitHub tag ruleset for `v*` that prevents tag deletion and updates
outside the explicitly approved release authority. The repository workflow
revalidates mutable GitHub state at both publication boundaries, but it cannot
make a tag immutable after PyPI accepts an artifact, and repository-owned code
must not grant itself permission to rewrite live organization rulesets. This
ruleset remains a maintainer-owned external control and a release-readiness
requirement.

## Manual recovery publish

`workflow_dispatch` accepts an existing GitHub Release tag when a prior upload
needs to be retried. The tag must be stable SemVer (`vX.Y.Z`), resolve to a
commit reachable from `main`, and have a policy base. The workflow resolves it
once to a full SHA and runs the same canonical verification, build, corpus
checks, exact wheel and sdist installation/conformance smokes, and OIDC
publication chain. PyPI upload and GitHub attachment are separate jobs, so use
GitHub's **re-run failed jobs** operation if attachment or finalization fails
after PyPI succeeds.
Manual dispatch is not a verification bypass and never builds from the current
branch head.

## First release

`main` starts at `0.18.0` (the manifest/pyproject baseline; the historical
changelog through `0.18.0` is preserved in `CHANGELOG.md`). The first `feat:`/
`fix:` merged to `main` after adoption produces a release PR bumping from
`0.18.0`; merging it publishes the first PyPI artifact.

## PyPI trusted publishing (one-time, maintainer)

Register a **pending** trusted publisher on PyPI before the first upload (no
token stored):

- PyPI → *Your projects* → *Publishing* → *Add a pending publisher* → GitHub
- PyPI Project Name: `raes`
- Owner: `OpenRAE`  ·  Repository: `rae`
- **Workflow name: `release-please.yml`**  ·  Environment name: `pypi`

> If you previously registered the publisher against `release.yml`, update it to
> `release-please.yml` (or add a second pending publisher) — the workflow filename
> must match or only the PyPI publish step 403s.

The `pypi` environment and `id-token: write` permission exist only on the PyPI
upload job. Configure that environment's deployment branch policy for `main`.
Resolution, canonical verification, distribution installation, GitHub
attachment, and CLI execution cannot mint the PyPI publishing credential.

## Pinning from a downstream backend

```
raes==<X.Y.Z>
```
