"""Tests for canonical SDL formatting and migration CLI surfaces."""

from __future__ import annotations

from raes_cli.main import app
from raes import format_sdl_source
from typer.testing import CliRunner


def test_format_api_migrates_fields_and_expands_shorthands() -> None:
    result = format_sdl_source(
        """\
Name: migrate-me
Nodes:
  web-app:
    Type: VM
    roles: {admin: operator}
infrastructure:
  web-app: 1
"""
    )

    assert result.content.startswith("name: migrate-me\nnodes:\n  web-app:\n    type: vm\n")
    assert "username: operator" in result.content
    assert "count: 1" in result.content
    assert [item.code for item in result.diagnostics] == [
        "sdl.noncanonical_field",
        "sdl.noncanonical_field",
        "sdl.noncanonical_field",
    ]


def test_format_cli_supports_stdout_write_and_check(tmp_path) -> None:
    source = tmp_path / "scenario.yaml"
    source.write_text("Name: cli-format\n", encoding="utf-8")
    runner = CliRunner()

    stdout_result = runner.invoke(app, ["sdl", "format", str(source)])
    assert stdout_result.exit_code == 0
    assert "name: cli-format" in stdout_result.stdout
    assert "sdl.noncanonical_field" in stdout_result.stderr
    assert source.read_text(encoding="utf-8") == "Name: cli-format\n"

    check_result = runner.invoke(app, ["sdl", "format", str(source), "--check"])
    assert check_result.exit_code == 1

    write_result = runner.invoke(app, ["sdl", "format", str(source), "--write"])
    assert write_result.exit_code == 0
    assert source.read_text(encoding="utf-8") == "name: cli-format\n"

    clean_check = runner.invoke(app, ["sdl", "format", str(source), "--check"])
    assert clean_check.exit_code == 0
