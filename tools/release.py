#!/usr/bin/env python3
"""Cut a release (#684): compute the next version from the pending towncrier
fragments, write it as the ``__version__`` literal, and run ``towncrier build``.

No git operations are performed. Run it, then commit the result on a
``release/vX.Y.Z`` branch and open a PR to ``main``; merging that PR triggers the
release workflow, which tags + builds + publishes.

Fragment type -> bump (highest pending wins):
    removed                     -> major once already >= 1.0, else minor (pre-1.0)
    added, changed, deprecated  -> minor
    security, fixed             -> patch
    breaking                    -> recorded in the changelog but does NOT
                                   auto-escalate the bump; force the major
                                   explicitly with ``--version 1.0.0``.

Usage:
    python tools/release.py                 # auto-compute from fragments
    python tools/release.py --version 1.0.0 # force an explicit version
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "implementations" / "python" / "src" / "aces" / "__init__.py"  # {{VERSION_FILE}}
FRAGMENTS = ROOT / "changelog.d"

_VERSION_RE = re.compile(r'^__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', re.M)

MINOR = {"added", "changed", "deprecated"}
PATCH = {"fixed", "security"}
BREAK = {"removed"}
# `breaking` is a real changelog type but intentionally has no auto-bump effect.
KNOWN_TYPES = MINOR | PATCH | BREAK | {"breaking"}


def current_version() -> tuple[int, int, int]:
    m = _VERSION_RE.search(INIT.read_text(encoding="utf-8"))
    if not m:
        sys.exit(f"no __version__ literal found in {INIT}")
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def pending_types() -> set[str]:
    found: set[str] = set()
    unknown: list[str] = []
    for frag in sorted(FRAGMENTS.glob("*.md")):
        if frag.name == "README.md" or frag.name.startswith("_"):
            continue
        parts = frag.name.split(".")
        if len(parts) < 3:
            continue
        ftype = parts[-2]
        if ftype not in KNOWN_TYPES:
            unknown.append(frag.name)
            continue
        found.add(ftype)
    if unknown:
        sys.exit(f"changelog fragments with unknown type (expected {sorted(KNOWN_TYPES)}): {unknown}")
    return found


def next_version(current: tuple[int, int, int], types: set[str]) -> str | None:
    major, minor, patch = current
    if types & BREAK:
        return f"{major + 1}.0.0" if major >= 1 else f"{major}.{minor + 1}.0"
    if types & MINOR:
        return f"{major}.{minor + 1}.0"
    if types & PATCH:
        return f"{major}.{minor}.{patch + 1}"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Cut a release from pending changelog fragments (#684).")
    parser.add_argument("--version", help="force an explicit X.Y.Z (e.g. to cut 1.0.0)")
    args = parser.parse_args()

    types = pending_types()
    if args.version:
        version = args.version
    elif not types:
        sys.exit("no pending changelog fragments; nothing to release")
    else:
        version = next_version(current_version(), types)
        if version is None:
            sys.exit(f"pending fragment types {sorted(types)} imply no release; use --version to force one")

    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        sys.exit(f"bad version {version!r} (expected X.Y.Z)")

    INIT.write_text(_VERSION_RE.sub(f'__version__ = "{version}"', INIT.read_text(encoding="utf-8"), count=1))
    subprocess.run([sys.executable, "-m", "towncrier", "build", "--yes", "--version", version], cwd=ROOT, check=True)

    print(
        f"\nv{version} prepared. Next:\n"
        f"  git switch -c release/v{version}\n"
        f"  git commit -am 'chore: release v{version}'\n"
        f"  gh pr create --base main --title 'chore: release v{version}' --fill"
    )


if __name__ == "__main__":
    raise SystemExit(main())
