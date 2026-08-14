# Issue 1097 Python 3.14 Support Preflight

Date: 2026-08-11

Issue: #1097. Requirement: GOV-901.

## Decision

The `raes` distribution supports standard CPython 3.11, 3.12, 3.13, and
3.14. `Requires-Python` is therefore bounded to `>=3.11,<3.15`, and the Trove
classifiers list those four tested feature releases. The lower and upper
metadata bounds are install admission; the classifiers and blocking CI matrix
identify the versions for which this repository makes a tested support claim.

Python 3.15 is outside this change. It remains pre-final until 2026-10-01 and
must not receive a classifier, compatibility job, or package-support claim
before final. A later qualification issue must refresh the governed lock,
review native-wheel coverage on every claimed platform, run clean build/install
and integration gates, and then decide whether to raise the upper bound.

Free-threaded CPython 3.14 (`3.14t`) is an early-compatibility signal, not part
of the standard-interpreter guarantee. A nonblocking scheduled/manual lane may
install and test it, but must assert that the selected interpreter is actually
free-threaded and label the result preview-only. Failures there cannot be
described as a standard 3.14 regression without reproducing them on the normal
GIL build.

## Compatibility Gates

The blocking matrix must, for each standard feature release:

1. select the requested interpreter explicitly and assert `sys.version_info`;
2. perform a frozen all-extras sync rather than silently resolving another
   dependency graph;
3. run the hermetic default unit suite;
4. build both wheel and source distribution;
5. install the wheel into a fresh environment with dependencies; and
6. smoke distribution metadata, public package imports, `raes --version`, and
   `raes --help` from that clean environment.

The compatibility job is separate from canonical `verify`: proof replay,
policy, Sonar coverage, and contract generation remain single-version because
their result is not interpreter-specific. This avoids multiplying proof cost
while making every advertised interpreter blocking for code and packaging.

The job must not trust its label. `UV_PYTHON`, the runtime assertion, wheel
smoke interpreter, and log output all resolve to the same matrix value. This
prevents a `.python-version`, reused environment, or hard-coded smoke command
from turning the matrix into cosmetic coverage.

Nox removes an inherited `UV_PYTHON` selector from commands by default. The
compatibility session therefore copies the admitted selector into Nox's
per-session command environment before any nested `uv` call. A tooling
regression covers that handoff, while the exact-runtime assertion remains the
independent fail-closed check.

## Dependency And Platform Boundary

The frozen lock and current native dependency set must install on standard
CPython 3.14. A source build is not automatically a defect, but the build
prerequisites and platform claim must remain honest. The compatibility matrix
is initially the repository's existing Ubuntu execution contract; macOS local
verification supplements it but does not silently create a cross-platform
support promise. Backend-specific native integration remains governed by its
own runtime and host prerequisites.

The 3.14 test change replaces deprecated `asyncio.get_event_loop()` use with
`asyncio.run()` only at synchronous test boundaries. Product async APIs retain
their existing lifecycle and do not create nested event loops.

## Nonclaims

This issue does not:

- support or preview Python 3.15;
- claim production support for free-threaded builds;
- change SDL, contract, runtime, or backend semantics;
- make every optional native backend available on every operating system; or
- weaken canonical verification, coverage, policy, or release gates.
