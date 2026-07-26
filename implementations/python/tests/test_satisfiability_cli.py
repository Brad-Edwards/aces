"""Production CLI coverage for whole-scenario satisfiability (issue #826)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from raes_cli.main import app
from raes_contracts.satisfiability import ScenarioSatisfiabilityEvidenceModel
from typer.testing import CliRunner


def _invoke(path: Path):
    return CliRunner().invoke(
        app,
        [
            "processor",
            "satisfiability",
            str(path),
            "--profile",
            "aces-finite-domain-satisfiability-v1",
        ],
    )


def test_cli_emits_published_evidence_and_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "sat.sdl.yaml"
    source.write_text(
        """name: sat
variables:
  platform: {type: string, allowed_values: [windows, linux], required: true}
nodes:
  target: {type: vm, os: "${platform}"}
""",
        encoding="utf-8",
    )

    first = _invoke(source)
    second = _invoke(source)

    assert first.exit_code == 0, first.output
    assert first.stdout == second.stdout
    evidence = ScenarioSatisfiabilityEvidenceModel.model_validate_json(first.stdout)
    assert evidence.outcome.value == "satisfiable"


@pytest.mark.integration
def test_cli_evidence_is_stable_across_python_hash_seeds(tmp_path: Path) -> None:
    source = tmp_path / "sat.sdl.yaml"
    source.write_text(
        """name: sat
variables:
  platform: {type: string, allowed_values: [windows, linux], required: true}
nodes:
  target: {type: vm, os: "${platform}"}
""",
        encoding="utf-8",
    )
    executable = Path(sys.executable).with_name("raes")
    argv = [
        str(executable),
        "processor",
        "satisfiability",
        str(source),
        "--profile",
        "aces-finite-domain-satisfiability-v1",
    ]

    outputs = [
        subprocess.run(  # noqa: S603 - fixed local executable and argv
            argv,
            check=True,
            capture_output=True,
            text=True,
            env={"PYTHONHASHSEED": seed},
        ).stdout
        for seed in ("1", "8675309")
    ]

    assert outputs[0] == outputs[1]


def test_cli_uses_exit_two_for_typed_unsupported_result(tmp_path: Path) -> None:
    source = tmp_path / "unsupported.sdl.yaml"
    source.write_text(
        """name: unsupported
variables:
  count: {type: integer, allowed_values: [1, 2], required: true}
nodes:
  target:
    type: vm
    resources: {ram: 1 gib, cpu: "${count}"}
""",
        encoding="utf-8",
    )

    result = _invoke(source)

    assert result.exit_code == 2
    assert json.loads(result.stdout)["outcome"] == "unsupported"
    assert result.stderr == ""


def test_cli_sanitizes_malformed_input(tmp_path: Path) -> None:
    source = tmp_path / "SECRET-MARKER.sdl.yaml"
    source.write_text("name: [SECRET-MARKER\n", encoding="utf-8")

    result = _invoke(source)

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert "SECRET-MARKER" not in result.stderr
