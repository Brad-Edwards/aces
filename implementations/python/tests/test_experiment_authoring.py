"""Tests for the experiment authoring-input loader and MCP authoring tools (issue #675)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from paths import EXPERIMENTS_DIR, REPO_ROOT
from raes_contracts.contracts import ExperimentSpecModel
from raes_contracts.experiment_spec import (
    ExperimentSpecValidationError,
    find_experiment_specs,
    load_experiment_spec,
    parse_experiment_spec,
)
from raes_mcp.tools.experiment_authoring import (
    _MAX_INPUT_BYTES,
    _run_experiment_get_example,
    _run_experiment_scaffold,
    _run_experiment_validate,
)

_VALID_FIXTURE = (
    REPO_ROOT
    / "contracts"
    / "fixtures"
    / "experiment-core"
    / "experiment-authoring-input-v1"
    / "valid"
    / "reference.json"
)


def _valid_payload() -> dict:
    return json.loads(_VALID_FIXTURE.read_text(encoding="utf-8"))


def _valid_yaml() -> str:
    # YAML is a JSON superset; the JSON fixture is valid YAML.
    return _VALID_FIXTURE.read_text(encoding="utf-8")


# --- loader / parser ------------------------------------------------------


def test_parse_experiment_spec_accepts_valid_yaml() -> None:
    spec = parse_experiment_spec(_valid_yaml())
    assert spec.spec_id == "spec-techvault-red-tactic-sweep-v1"
    assert spec.run_plan.allocation is not None


def test_parse_experiment_spec_rejects_empty() -> None:
    with pytest.raises(ExperimentSpecValidationError):
        parse_experiment_spec("   \n")


def test_parse_experiment_spec_rejects_non_mapping() -> None:
    with pytest.raises(ExperimentSpecValidationError):
        parse_experiment_spec("- a\n- b\n")


def test_parse_experiment_spec_rejects_bad_yaml() -> None:
    with pytest.raises(ExperimentSpecValidationError):
        parse_experiment_spec("spec_id: [unterminated\n")


def test_parse_experiment_spec_rejects_schema_invalid() -> None:
    with pytest.raises(ExperimentSpecValidationError):
        parse_experiment_spec("schema_version: experiment-authoring-input/v1\nspec_id: x\n")


def test_load_experiment_spec_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "demo.exp.yaml"
    path.write_text(_valid_yaml(), encoding="utf-8")
    spec = load_experiment_spec(path)
    assert isinstance(spec, ExperimentSpecModel)


def test_load_experiment_spec_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_experiment_spec(tmp_path / "nope.exp.yaml")


def test_find_experiment_specs_finds_shipped_examples() -> None:
    found = find_experiment_specs(EXPERIMENTS_DIR)
    assert found, "expected shipped *.exp.yaml examples"
    assert all(p.name.endswith(".exp.yaml") for p in found)


def test_find_experiment_specs_missing_dir(tmp_path: Path) -> None:
    assert find_experiment_specs(tmp_path / "absent") == []


# --- model validators -----------------------------------------------------


def test_run_plan_rejects_both_run_count_sources() -> None:
    payload = _valid_payload()
    payload["run_plan"]["target_run_count"] = 10  # allocation already present
    with pytest.raises(ValueError, match="exactly one"):
        ExperimentSpecModel.model_validate(payload)


def test_run_plan_rejects_no_run_count_source() -> None:
    payload = _valid_payload()
    del payload["run_plan"]["allocation"]
    with pytest.raises(ValueError, match="exactly one"):
        ExperimentSpecModel.model_validate(payload)


def test_run_plan_rejects_red_variant_key_mismatch() -> None:
    payload = _valid_payload()
    payload["run_plan"]["red_variant_selections"] = {
        "aggressive": {"variant_id": "not-aggressive", "agent_ref": "red-agent"}
    }
    with pytest.raises(ValueError, match="variant_id"):
        ExperimentSpecModel.model_validate(payload)


def test_target_run_count_path_is_valid() -> None:
    payload = _valid_payload()
    del payload["run_plan"]["allocation"]
    del payload["factors"]
    payload["run_plan"]["target_run_count"] = 5
    spec = ExperimentSpecModel.model_validate(payload)
    assert spec.run_plan.target_run_count == 5


# --- MCP tool helpers -----------------------------------------------------


def test_tool_validate_valid() -> None:
    out = _run_experiment_validate(_valid_yaml())
    assert out.startswith("VALID —")
    assert "run-count source: allocation" in out


def test_tool_validate_invalid() -> None:
    out = _run_experiment_validate("schema_version: experiment-authoring-input/v1\nspec_id: x\n")
    assert out.startswith("VALIDATION ERROR")


def test_tool_validate_too_large() -> None:
    out = _run_experiment_validate("x" * (_MAX_INPUT_BYTES + 1))
    assert "INPUT TOO LARGE" in out


@pytest.mark.parametrize("complexity", ["minimal", "sweep"])
def test_tool_scaffold_outputs_are_valid(complexity: str) -> None:
    out = _run_experiment_scaffold(complexity, "demo-spec", "task-demo-v1")
    spec = parse_experiment_spec(out)
    assert spec.spec_id == "demo-spec"


def test_tool_scaffold_rejects_unknown_complexity() -> None:
    assert "Invalid complexity" in _run_experiment_scaffold("ultra", "x", "y")


@pytest.mark.parametrize("name", ["sweep", "smoke"])
def test_tool_get_example_returns_shipped(name: str) -> None:
    out = _run_experiment_get_example(name)
    assert "schema_version: experiment-authoring-input/v1" in out


def test_tool_get_example_unknown() -> None:
    assert "Unknown example" in _run_experiment_get_example("nope")
