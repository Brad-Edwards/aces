# Issue 1111 GOV-901 CLI Version Startup Preflight

Date: 2026-08-12

Issue: #1111.

Requirement: GOV-901. Discovery lineage: RUN-313 post-review.

## Decision

The installed `raes` console script uses a lightweight entry-point callable for
exact global `--version` and `-V` requests. Those two exact argument vectors
read the installed `raes` distribution version, preserve the honest
`0.0.0+unknown` fallback, print the existing output, and return success without
importing the Typer application or its command modules.

Every other argument vector lazily imports and calls the existing
`raes_cli.main.app` object without changing `sys.argv`. The Typer application
and its version callback remain available for direct and in-process callers.
This is an import-lifetime change, not a new command, option, distribution, or
version source.

## Measured Gap

At `e56f3cf54a259e02cde405c1804a044451529936`, the console entry point named
`raes_cli.main:app` imported all six command trees before Typer could invoke
the eager version callback. A CPython 3.13.5 benchmark on macOS used fresh
child processes, a warmed filesystem page cache, `PYTHONHASHSEED=0`, one
warmup, and eight measured samples. Child CPU time came from the delta of
`resource.getrusage(resource.RUSAGE_CHILDREN)`; wall time came from
`time.perf_counter_ns()`.

| Path | Median child CPU | Median wall | P95 child CPU |
| --- | ---: | ---: | ---: |
| Python no-op | 15.1 ms | 17.8 ms | 17.4 ms |
| `importlib.metadata.version("raes")` | 43.8 ms | 47.1 ms | 60.7 ms |
| `raes --version` | 1,107.1 ms | 1,121.4 ms | 1,197.6 ms |
| `raes --help` | 1,129.8 ms | 1,143.1 ms | 1,163.4 ms |

`python -X importtime -c 'import raes_cli.main'` reported 975.8 ms
cumulatively for `raes_cli.main`. The largest owning chain was
`raes_cli.conformance` (847.2 ms), its fixture suite (839.8 ms), and
`raes_contracts.contracts` (645.2 ms). Cumulative import times overlap and are
not summed; they identify the command graph loaded before option dispatch.

The benchmark is supporting evidence rather than a portable absolute latency
claim. Fresh process creation and CPU scheduling vary by host. The portable
defect signal is that an exact version probe imported processor, solver,
contract, conformance, and backend surfaces it could not use.

## Existing Surface And Ownership Audit

- `[project.scripts]` in `implementations/python/pyproject.toml` is the sole
  installed `raes` command. PyPA console scripts target a no-argument callable,
  so the existing entry can move to a lightweight function without adding a
  second command or distribution.
- `raes_cli.main` remains the canonical Typer application and command registry.
  Its SDL, processor, conformance, semantic, libvirt, and corpus registration
  must still load for every delegated invocation.
- GOV-901, ADR-075, issue #90, and
  `specs/evolution/versioning-deprecation-and-migration.md` own the version
  value and fallback. The wrapper reuses that policy; it does not infer a
  source-tree version or read `_version.py`.
- The issue #1097 compatibility lane already builds and installs a wheel, then
  smokes `raes --version` and `raes --help`. Installed-wheel acceptance extends
  that surface by checking the entry-point target and absence of heavy imports.
- RUN-313 issue #1099 optimized a pass-local processor projection and named CLI
  startup as a non-goal. Solver and scheduler changes likewise begin after the
  imports paid by the console launcher. RUN-313 therefore records how the gap
  was found, while GOV-901 owns the remediation.
- `raes-mcp`, SDL/contract schemas, parsers, validators, runtime and backend
  dispatch, module aliases, examples, and experiments do not participate in
  distribution-version reporting and are unchanged.
- Repository and GitHub issue/PR searches found no parallel lazy-version entry
  point. The existing Typer callback is retained instead of replaced.

The boundary follows the PyPA
[Entry Points specification](https://packaging.python.org/en/latest/specifications/entry-points/),
which defines a console-script object as a no-argument callable, and Python's
[`importlib.metadata` documentation](https://docs.python.org/3/library/importlib.metadata.html),
which defines `version()` and `PackageNotFoundError` for installed distribution
metadata.

## Exact-Argument And Compatibility Invariants

- Only `sys.argv[1:] == ["--version"]` and `sys.argv[1:] == ["-V"]` take the
  lightweight path.
- The result is exactly `raes <installed-version>\n`, or
  `raes 0.0.0+unknown\n` when the distribution is absent.
- Empty arguments, `--help`, subcommands, unknown options, and version flags
  combined with any other token delegate once to the existing Typer app.
- Delegation does not copy, normalize, reorder, or otherwise rewrite
  `sys.argv`; Click/Typer retains ownership of parsing, diagnostics, help, and
  exit behavior.
- Direct `CliRunner().invoke(raes_cli.main.app, ["--version"])` keeps the same
  metadata and fallback behavior through a shared version helper.
- No import cache, persistent result, filesystem read, network access,
  environment setting, telemetry, or new failure channel is added.

## Alternatives Rejected

- Keeping the evidence only would preserve correct output while making package
  managers, support scripts, and compatibility probes pay the unrelated
  command graph on every fresh process.
- Lazy Typer command registration could improve `--help`, but changes command
  discovery, completion, help rendering, and error surfaces. It is outside the
  exact-version defect and is deferred.
- Optimizing Pydantic schema construction would not remove the many other eager
  imports. `schema_bundle()` already caches its generated template and returns
  a defensive deep copy; changing that isolation contract is unrelated.
- A cross-process version cache adds invalidation and trust questions to a
  metadata lookup that already takes only tens of milliseconds.
- Special-casing version inside `raes_cli.main` is too late because importing
  the module already imports every command. Exiting during module import would
  also break library and test callers.

## Verification Boundary

Unit tests cover both exact flags, installed metadata, the
`PackageNotFoundError` sentinel, and a table of non-exact argument forms. A
source subprocess probe asserts that the lightweight path does not import
`raes_cli.main`, `raes_conformance`, `raes_contracts`, `raes_processor`, or Z3.

The timing guard uses five fresh processes and median child `process_time()`.
It requires the lightweight median to stay below 250 ms and below half the
same-host full-command-import median. The absolute budget is over five times
the measured metadata-only CPU median, while the paired relative check absorbs
large host-speed differences. The structural import assertions are the primary
regression oracle; no single wall-clock sample can fail the test.

The existing installed-distribution integration fixture builds the real wheel,
installs it in a clean environment without repository `PYTHONPATH`, invokes
the generated `raes --version` script, resolves the published console entry
point, and verifies that exact `-V` does not import the Typer or contracts
graph. The compatibility lane continues to smoke both version and help across
every supported CPython release.

A post-change same-host benchmark used CPython 3.14.4 free-threaded, one
warmup, and eight fresh processes per path. The reference proxy imported and
called `raes_cli.main.app` exactly as the former console target did; the new
path invoked the installed editable console script. Both received only
`--version`.

| Path | Median child CPU | Median wall | P95 child CPU |
| --- | ---: | ---: | ---: |
| Pre-change entry-point proxy | 1,121.1 ms | 1,135.6 ms | 1,304.1 ms |
| New exact-version entry point | 38.5 ms | 40.4 ms | 48.3 ms |
| New delegated `--help` | 1,173.1 ms | 1,181.4 ms | 1,205.6 ms |

The exact-version median used 96.6% less child CPU, or about 29.2 times less,
while help remained on the intentionally unchanged full-command path.

Repository policy, requirement governance, changed line and branch coverage,
Ruff, built artifacts, documentation, and the canonical `verify_all.py` and
completion graphs remain required with `RAES_REQUIREMENT_UID=GOV-901`.

## Nonclaims

- This change does not optimize or place a latency budget on `raes --help` or
  any subcommand.
- It does not optimize schema-bundle generation or remove defensive copies.
- It does not change reference-processor, solver, scheduler, runtime, backend,
  or experiment performance.
- It does not change the supported Python range, release version, CLI syntax,
  output schema, or compatibility policy.
