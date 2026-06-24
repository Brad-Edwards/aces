"""RUN-314: SEM-218 realization provenance via RuntimeManager.apply."""

from __future__ import annotations

import textwrap

from aces_reference_backend import create_reference_backend_target
from aces_sdl.explicitness import ExplicitnessClass, ExplicitnessProvenance

from aces.core.runtime.manager import RuntimeManager
from aces.core.sdl import parse_sdl

_EXACT_SCENARIO = """
name: ref-sem-218
nodes:
  web:
    type: vm
    os: linux
    resources: {ram: 1 gib, cpu: 1}
"""


def test_apply_records_realization_provenance():
    manager = RuntimeManager(create_reference_backend_target())
    plan = manager.plan(parse_sdl(textwrap.dedent(_EXACT_SCENARIO)))

    result = manager.apply(plan)

    assert result.success, [diag.message for diag in result.diagnostics]
    by_field = {entry.field_path: entry for entry in result.snapshot.realization_provenance}
    assert by_field["nodes.web.os"].provenance is ExplicitnessProvenance.AUTHOR_DECLARED
    assert by_field["nodes.web.os"].explicitness is ExplicitnessClass.EXACT
    assert by_field["nodes.web.os"].requirement_kind == "os-family"
    assert by_field["nodes.web.type"].explicitness is ExplicitnessClass.EXACT


def test_apply_snapshot_preserves_planned_payload_no_emulator_state():
    manager = RuntimeManager(create_reference_backend_target())
    plan = manager.plan(parse_sdl(textwrap.dedent(_EXACT_SCENARIO)))

    result = manager.apply(plan)

    entry = result.snapshot.entries["provision.node.web"]
    assert entry.payload.get("os_family") == "linux"
    rendered = repr(result.snapshot.entries)
    for forbidden in ("container_id", "docker", "podman", "/var/run", "InProcessDriver"):
        assert forbidden not in rendered
