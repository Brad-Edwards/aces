"""Determinism witness for the SDL ``parse -> instantiate -> compile`` pipeline.

Records the executable witness that review finding IMP-4 (issue #506) found
missing: ``docs/explain/sdl/parser.md`` claims "Import expansion is file-backed
and deterministic", and the pipeline design (lockfile-backed imports, no ambient
state) is plausibly deterministic, but no test ran the pipeline twice and
asserted identical output. This is also the narrow witness for the broader
ASR-514 determinism-verification surface.

Three checks:

1. ``test_pipeline_is_byte_identical_across_two_passes`` -- run the public
   pipeline twice in one process over the shipped complex example scenarios
   (multiple agents / features / relationships + variable substitution +
   ordered collections) and assert the canonical serializations are
   byte-identical.
2. ``test_module_import_pipeline_is_byte_identical_across_two_passes`` -- same
   two-pass assertion for a local module-import scenario (explicit namespace,
   module ``exports``, multiple imported nodes) so import-expansion order is
   exercised.
3. ``test_pipeline_is_hash_seed_independent`` -- compile the same scenario in
   two fixed-argv ``sys.executable`` subprocesses under different
   ``PYTHONHASHSEED`` values and assert the canonical serializations are
   byte-identical. A single process pins one hash seed, so cross-process
   variation is the only way to catch hash-order dependence (set/dict iteration
   order leaking into the output).

Canonical serializer notes:

* Keys are intentionally **not** sorted. Determinism means the pipeline must
  reproduce identical ordering on its own; sorting keys would canonicalize away
  the hash-seed-dependent ordering that check (3) exists to detect. The pipeline
  is verified hash-stable, so the strict assertion is not flaky. (This is a
  deliberate refinement over the Step 2.5 preflight's ``sort_keys=True``
  serializer suggestion, justified by the hash-order acceptance criterion.)
* The generated-timestamp exclusion set is **empty by design**: the
  ``parse -> instantiate -> compile`` path injects no wall-clock / uuid / random
  values, so the compiled ``RuntimeModel`` carries no per-run fields (verified:
  no ``datetime.now`` / ``time.time`` / ``uuid4`` / ``random`` / ``secrets`` in
  ``raes`` or ``raes_processor``). Author-provided time-typed values
  (``start_time``, OCR durations, script ``time``) are deterministic functions
  of the input and need no exclusion. The strip mechanism is retained and
  check (1) is the tripwire: a future generated timestamp would differ between
  two same-process passes and fail loudly, prompting its field name to be added
  to ``_GENERATED_TIMESTAMP_FIELDS``.
"""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from paths import EXAMPLES_DIR

from raes_processor.compiler import compile_runtime_model
from raes import instantiate_scenario, parse_sdl_file

# This whole witness is integration-style: it reads shipped scenarios from the
# real repo on disk and spawns subprocesses, so it is excluded from the default
# fast unit sweep and runs in the `integration` session (which `nox -s verify`
# and CI both execute). A module-level mark keeps every current and future test
# in this file inside that boundary -- per the repo's pytest marker taxonomy.
pytestmark = pytest.mark.integration

# Shipped scenarios that exercise ordered-collection surfaces (multiple agents,
# features, and relationships) and -- for the first two -- variable
# substitution. These are the representative inputs the witness compiles.
COMPLEX_EXAMPLES = [
    EXAMPLES_DIR / "hospital-ransomware-surgery-day.sdl.yaml",
    EXAMPLES_DIR / "satcom-release-poisoning.sdl.yaml",
    EXAMPLES_DIR / "port-authority-surge-response.sdl.yaml",
]

# Compiled RuntimeModel field names carrying per-run wall-clock / generated
# values to exclude from the determinism comparison. Empty by design -- see the
# module docstring. Adding a name here is the documented escape hatch if the
# compiler ever emits a genuinely generated timestamp.
_GENERATED_TIMESTAMP_FIELDS: frozenset[str] = frozenset()


def _strip_excluded(value: object) -> object:
    """Recursively drop excluded (generated-timestamp) keys from a payload."""
    if isinstance(value, dict):
        return {k: _strip_excluded(v) for k, v in value.items() if k not in _GENERATED_TIMESTAMP_FIELDS}
    if isinstance(value, list):
        return [_strip_excluded(item) for item in value]
    return value


def _canonical_json(model: object) -> str:
    """Serialize a compiled ``RuntimeModel`` deterministically for byte compare.

    ``sort_keys`` is intentionally ``False`` (see the module docstring).
    ``default=str`` renders any enum or non-JSON-native leaf deterministically.
    """
    payload = _strip_excluded(dataclasses.asdict(model))
    return json.dumps(payload, ensure_ascii=False, sort_keys=False, separators=(",", ":"), default=str)


def _compile_canonical(path: Path, *, substitute_variables: bool) -> str:
    """Run the full public pipeline for ``path`` and return canonical JSON."""
    scenario = parse_sdl_file(path)
    parameters: dict[str, object] = {}
    if substitute_variables:
        # Exercise variable substitution through the parameters path (rather
        # than relying on implicit defaults) by passing each declared default
        # back in as a provided value.
        parameters = {name: var.default for name, var in scenario.variables.items() if var.default is not None}
    instantiated = instantiate_scenario(scenario, parameters=parameters)
    return _canonical_json(compile_runtime_model(instantiated))


@pytest.mark.parametrize("scenario_path", COMPLEX_EXAMPLES, ids=lambda path: path.stem)
def test_pipeline_is_byte_identical_across_two_passes(scenario_path: Path) -> None:
    first = _compile_canonical(scenario_path, substitute_variables=True)
    # Non-vacuous guard: a serializer that collapsed to empty/constant output
    # would make byte-identity trivially true. Require real compiled content.
    assert len(first) > 1000
    assert '"node_deployments"' in first
    second = _compile_canonical(scenario_path, substitute_variables=True)
    assert first == second


def test_canonical_serializer_distinguishes_distinct_scenarios() -> None:
    # Proves the comparison is meaningful (sensitive to input), so the two-pass
    # equality assertions above are not tautological.
    first = _compile_canonical(COMPLEX_EXAMPLES[0], substitute_variables=True)
    second = _compile_canonical(COMPLEX_EXAMPLES[1], substitute_variables=True)
    assert first != second


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return path


def _module_import_root(tmp_path: Path) -> Path:
    """Write a local module + an importing root, returning the root path.

    The module exports multiple nodes and infrastructure with switch links so
    import expansion and ordered-collection rewriting are exercised. A ``path:``
    import needs no lockfile/trust material (it is the backward-compatible
    direct-path source).
    """
    _write(
        tmp_path / "shared.yaml",
        """
        name: shared
        version: 1.2.3
        module:
          id: acme/shared
          version: 1.2.3
          exports:
            nodes: [web, db, edge]
            infrastructure: [web, db, edge]
        nodes:
          web: {type: vm, os: linux, resources: {ram: 1 gib, cpu: 1}}
          db: {type: vm, os: linux, resources: {ram: 2 gib, cpu: 2}}
          edge: {type: switch}
        infrastructure:
          web: {count: 1, links: [edge]}
          db: {count: 1, links: [edge]}
          edge: 1
        """,
    )
    return _write(
        tmp_path / "root.yaml",
        """
        name: root
        imports:
          - path: shared.yaml
            namespace: shared
        """,
    )


def test_module_import_pipeline_is_byte_identical_across_two_passes(tmp_path: Path) -> None:
    root = _module_import_root(tmp_path)
    first = _compile_canonical(root, substitute_variables=False)
    # Confirm the namespaced import actually expanded into the compiled model.
    assert "shared.web" in first
    second = _compile_canonical(root, substitute_variables=False)
    assert first == second


# Fixed-argv subprocess driver: read a scenario path (argv[1]), run the public
# pipeline, and print the sha256 of the canonical serialization. The exclusion
# set is passed as a JSON argv (argv[2]) so the driver mirrors `_canonical_json`
# exactly with a single source of truth. No shell, no secrets in argv/stdout.
_SUBPROCESS_DRIVER = textwrap.dedent(
    """
    import dataclasses
    import hashlib
    import json
    import sys
    from pathlib import Path

    from raes_processor.compiler import compile_runtime_model
    from raes import instantiate_scenario, parse_sdl_file

    exclude = set(json.loads(sys.argv[2]))

    def strip(value):
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k not in exclude}
        if isinstance(value, list):
            return [strip(item) for item in value]
        return value

    scenario = parse_sdl_file(Path(sys.argv[1]))
    parameters = {n: v.default for n, v in scenario.variables.items() if v.default is not None}
    model = compile_runtime_model(instantiate_scenario(scenario, parameters=parameters))
    canonical = json.dumps(
        strip(dataclasses.asdict(model)),
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
        default=str,
    )
    sys.stdout.write(hashlib.sha256(canonical.encode("utf-8")).hexdigest())
    """
)


def _subprocess_digest(scenario_path: Path, hash_seed: str) -> str:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hash_seed
    exclude_arg = json.dumps(sorted(_GENERATED_TIMESTAMP_FIELDS))
    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_DRIVER, str(scenario_path), exclude_arg],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, f"determinism driver failed (seed={hash_seed}): {result.stderr}"
    digest = result.stdout.strip()
    assert len(digest) == 64, f"unexpected driver output (seed={hash_seed}): {result.stdout!r} / {result.stderr!r}"
    return digest


@pytest.mark.parametrize("scenario_path", COMPLEX_EXAMPLES, ids=lambda path: path.stem)
def test_pipeline_is_hash_seed_independent(scenario_path: Path) -> None:
    digest_seed_0 = _subprocess_digest(scenario_path, "0")
    digest_seed_1 = _subprocess_digest(scenario_path, "1")
    assert digest_seed_0 == digest_seed_1
