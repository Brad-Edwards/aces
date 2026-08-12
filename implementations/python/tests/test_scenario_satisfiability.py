"""Governed whole-scenario satisfiability analysis (issue #826)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import z3
from pydantic import ValidationError
from raes_contracts.satisfiability import (
    SatisfiabilityOutcome,
    ScenarioSatisfiabilityEvidenceModel,
)
from raes_processor.satisfiability import (
    SatisfiabilityEvidenceError,
    SatisfiabilityOperationalError,
    analyze_scenario_file,
    replay_satisfiability_evidence,
)
from raes_processor.satisfiability._solver import SolverOperationalError, solve_model

_SATISFIABLE = """\
name: satisfiable-control
variables:
  platform:
    type: string
    allowed_values: [windows, linux]
    required: true
nodes:
  target:
    type: vm
    os: ${platform}
"""

_UNSATISFIABLE = """\
name: unsatisfiable-control
variables:
  platform:
    type: string
    allowed_values: [linux, allow]
    required: true
nodes:
  target:
    type: vm
    os: ${platform}
infrastructure:
  target:
    acls:
      - action: ${platform}
"""

_UNSUPPORTED = """\
name: unsupported-control
variables:
  cpu_count:
    type: integer
    allowed_values: [1, 2]
    required: true
nodes:
  target:
    type: vm
    resources:
      ram: 1 gib
      cpu: ${cpu_count}
"""

_EMPTY_TARGET_DOMAIN = """\
name: empty-target-domain
variables:
  copies:
    type: integer
    allowed_values: [0]
    required: true
nodes:
  target:
    type: vm
infrastructure:
  target:
    count: ${copies}
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_satisfiable_control_emits_replayable_lexicographic_witness(tmp_path: Path) -> None:
    source = _write(tmp_path, "satisfiable.sdl.yaml", _SATISFIABLE)

    evidence = analyze_scenario_file(source)

    assert evidence.outcome is SatisfiabilityOutcome.SATISFIABLE
    assert evidence.witness is not None
    assert evidence.unsat_core is None
    assert evidence.unsupported is None
    bindings = evidence.witness.snapshot.scenario.instantiation_provenance.root_binding_values
    assert bindings == {"platform": "linux"}
    assert replay_satisfiability_evidence(source, evidence) == evidence


def test_unsatisfiable_control_emits_stable_replayable_core(tmp_path: Path) -> None:
    source = _write(tmp_path, "unsatisfiable.sdl.yaml", _UNSATISFIABLE)

    first = analyze_scenario_file(source)
    second = analyze_scenario_file(source)

    assert first.outcome is SatisfiabilityOutcome.UNSATISFIABLE
    assert first.witness is None
    assert first.unsat_core is not None
    assert first.unsupported is None
    assert first.unsat_core.clause_ids == tuple(sorted(first.unsat_core.clause_ids))
    assert len(first.unsat_core.clause_ids) >= 2
    assert first.model_dump_json() == second.model_dump_json()
    assert replay_satisfiability_evidence(source, first) == first


def test_integer_and_boolean_targets_use_finite_domains(tmp_path: Path) -> None:
    source = _write(
        tmp_path,
        "scalar-targets.sdl.yaml",
        """\
name: scalar-targets
variables:
  copies: {type: integer, allowed_values: [2, 0, 1], required: true}
  private: {type: boolean, required: true}
nodes:
  target: {type: vm}
infrastructure:
  target:
    count: ${copies}
    properties:
      cidr: 192.0.2.0/24
      gateway: 192.0.2.1
      internal: ${private}
""",
    )

    evidence = analyze_scenario_file(source)

    assert evidence.outcome is SatisfiabilityOutcome.SATISFIABLE
    assert evidence.witness is not None
    bindings = evidence.witness.snapshot.scenario.instantiation_provenance.root_binding_values
    assert bindings == {"copies": 1, "private": False}


def test_unsupported_construct_fails_closed_with_value_free_diagnostic(tmp_path: Path) -> None:
    source = _write(tmp_path, "unsupported.sdl.yaml", _UNSUPPORTED)

    evidence = analyze_scenario_file(source)

    assert evidence.outcome is SatisfiabilityOutcome.UNSUPPORTED
    assert evidence.witness is None
    assert evidence.unsat_core is None
    assert evidence.unsupported is not None
    assert [item.code for item in evidence.diagnostics] == ["scenario-satisfiability.unsupported-target"]
    rendered = evidence.model_dump_json()
    assert "cpu_count" not in " ".join(item.message for item in evidence.diagnostics)
    assert str(tmp_path) not in rendered


def test_replay_rejects_source_solver_and_payload_mutations(tmp_path: Path) -> None:
    source = _write(tmp_path, "satisfiable.sdl.yaml", _SATISFIABLE)
    evidence = analyze_scenario_file(source)

    source.write_text(_SATISFIABLE.replace("windows, linux", "linux, windows"), encoding="utf-8")
    with pytest.raises(SatisfiabilityEvidenceError, match="source digest"):
        replay_satisfiability_evidence(source, evidence)

    source.write_text(_SATISFIABLE, encoding="utf-8")
    payload = evidence.model_dump(mode="json")
    payload["solver_configuration"]["random_seed"] = 1
    with pytest.raises(ValidationError):
        ScenarioSatisfiabilityEvidenceModel.model_validate(payload)

    payload = evidence.model_dump(mode="json")
    payload["witness"]["snapshot_digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError):
        ScenarioSatisfiabilityEvidenceModel.model_validate(payload)


def test_evidence_contract_rejects_cross_outcome_payloads(tmp_path: Path) -> None:
    source = _write(tmp_path, "satisfiable.sdl.yaml", _SATISFIABLE)
    payload = analyze_scenario_file(source).model_dump(mode="json")
    payload["outcome"] = "unsatisfiable"

    with pytest.raises(ValidationError):
        ScenarioSatisfiabilityEvidenceModel.model_validate(payload)


def test_evidence_bytes_are_stable_across_json_round_trip(tmp_path: Path) -> None:
    source = _write(tmp_path, "satisfiable.sdl.yaml", _SATISFIABLE)
    evidence = analyze_scenario_file(source)

    round_tripped = ScenarioSatisfiabilityEvidenceModel.model_validate(json.loads(evidence.model_dump_json()))

    assert json.dumps(evidence.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) == json.dumps(
        round_tripped.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )


def test_stored_evidence_replays_after_model_round_trip(tmp_path: Path) -> None:
    source = _write(tmp_path, "satisfiable.sdl.yaml", _SATISFIABLE)
    evidence = analyze_scenario_file(source)
    stored = ScenarioSatisfiabilityEvidenceModel.model_validate_json(evidence.model_dump_json())

    replayed = replay_satisfiability_evidence(source, stored)

    assert replayed.model_dump(mode="json") == stored.model_dump(mode="json")


def test_domain_order_permutations_have_same_solver_neutral_semantics(tmp_path: Path) -> None:
    first = analyze_scenario_file(_write(tmp_path, "first.sdl.yaml", _SATISFIABLE))
    second = analyze_scenario_file(
        _write(
            tmp_path,
            "second.sdl.yaml",
            _SATISFIABLE.replace("[windows, linux]", "[linux, windows]"),
        )
    )

    assert first.outcome is second.outcome is SatisfiabilityOutcome.SATISFIABLE
    assert first.normalized_model.symbols == second.normalized_model.symbols
    assert first.normalized_model.clauses == second.normalized_model.clauses
    assert first.witness is not None and second.witness is not None
    assert (
        first.witness.snapshot.scenario.instantiation_provenance.root_binding_values
        == second.witness.snapshot.scenario.instantiation_provenance.root_binding_values
        == {"platform": "linux"}
    )


def test_contract_rejects_unknown_fields(tmp_path: Path) -> None:
    source = _write(tmp_path, "satisfiable.sdl.yaml", _SATISFIABLE)
    payload = deepcopy(analyze_scenario_file(source).model_dump(mode="json"))
    payload["unexpected"] = True

    with pytest.raises(ValidationError):
        ScenarioSatisfiabilityEvidenceModel.model_validate(payload)


def test_max_length_variable_names_have_bounded_portable_normalized_ids(tmp_path: Path) -> None:
    variable_name = "v" * 64
    source = _write(
        tmp_path,
        "long-identifier.sdl.yaml",
        _SATISFIABLE.replace("platform", variable_name),
    )

    evidence = analyze_scenario_file(source)

    assert evidence.outcome is SatisfiabilityOutcome.SATISFIABLE
    assert all(len(item.symbol_id) == 71 for item in evidence.normalized_model.symbols)


def test_symbol_limit_returns_bounded_unsupported_evidence(tmp_path: Path) -> None:
    variables = "\n".join(f"  flag_{index:03d}: {{type: boolean, required: true}}" for index in range(129))
    source = _write(tmp_path, "symbol-limit.sdl.yaml", f"name: symbol-limit\nvariables:\n{variables}\n")

    evidence = analyze_scenario_file(source)

    assert evidence.outcome is SatisfiabilityOutcome.UNSUPPORTED
    assert len(evidence.normalized_model.symbols) == 128
    assert [item.code for item in evidence.diagnostics] == ["scenario-satisfiability.resource-limit"]


def test_diagnostic_limit_returns_bounded_unsupported_evidence(tmp_path: Path) -> None:
    variables = "\n".join(
        f"  count_{index:03d}: {{type: integer, allowed_values: [1, 2], required: true}}" for index in range(65)
    )
    nodes = "\n".join(
        "\n".join(
            (
                f"  target_{index:03d}:",
                "    type: vm",
                "    resources:",
                "      ram: 1 gib",
                f"      cpu: ${{count_{index:03d}}}",
            )
        )
        for index in range(65)
    )
    source = _write(
        tmp_path,
        "diagnostic-limit.sdl.yaml",
        f"name: diagnostic-limit\nvariables:\n{variables}\nnodes:\n{nodes}\n",
    )

    evidence = analyze_scenario_file(source)

    assert evidence.outcome is SatisfiabilityOutcome.UNSUPPORTED
    assert len(evidence.diagnostics) == 64
    assert "scenario-satisfiability.resource-limit" in {item.code for item in evidence.diagnostics}


def test_clause_limit_returns_bounded_unsupported_evidence(tmp_path: Path) -> None:
    nodes = "\n".join(f"  target_{index:03d}: {{type: vm, os: '${{platform}}'}}" for index in range(512))
    source = _write(
        tmp_path,
        "clause-limit.sdl.yaml",
        "\n".join(
            (
                "name: clause-limit",
                "variables:",
                "  platform: {type: string, allowed_values: [linux, windows], required: true}",
                "nodes:",
                nodes,
                "",
            )
        ),
    )

    evidence = analyze_scenario_file(source)

    assert evidence.outcome is SatisfiabilityOutcome.UNSUPPORTED
    assert len(evidence.normalized_model.clauses) == 512
    assert [item.code for item in evidence.diagnostics] == ["scenario-satisfiability.resource-limit"]


def test_published_valid_and_invalid_fixtures_enforce_outcome_joins() -> None:
    fixtures = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "satisfiability"
    valid = fixtures / "scenario-satisfiability-evidence-v1" / "valid" / "unsupported-target.json"
    invalid = fixtures / "scenario-satisfiability-evidence-v1" / "invalid" / "cross-outcome-payload.json"

    ScenarioSatisfiabilityEvidenceModel.model_validate_json(valid.read_text(encoding="utf-8"))
    invalid_payload = invalid.read_text(encoding="utf-8")
    with pytest.raises(ValidationError) as exc_info:
        ScenarioSatisfiabilityEvidenceModel.model_validate_json(invalid_payload)

    assert "outcome must select exactly one matching payload" in str(exc_info.value)


def _force_unknown_on_call(monkeypatch: pytest.MonkeyPatch, target_call: int) -> None:
    """Make the ``target_call``-th z3 check report ``unknown`` (a timeout proxy)."""

    original = z3.Solver.check
    state = {"calls": 0}

    def patched(self: z3.Solver, *assumptions: object) -> z3.CheckSatResult:
        state["calls"] += 1
        if state["calls"] == target_call:
            return z3.unknown
        return original(self, *assumptions)

    monkeypatch.setattr(z3.Solver, "check", patched)


def test_unknown_during_core_reduction_fails_loudly_without_forging_minimality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write(tmp_path, "unsatisfiable.sdl.yaml", _UNSATISFIABLE)
    # Call one is the decisive UNSAT check; call two is the first deletion probe,
    # where an undetected timeout would silently retain a droppable clause and
    # publish a core claiming subset-minimality it never established.
    _force_unknown_on_call(monkeypatch, target_call=2)

    with pytest.raises(SatisfiabilityOperationalError):
        analyze_scenario_file(source)


def test_unknown_during_witness_selection_fails_loudly_without_forging_canonicality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write(tmp_path, "satisfiable.sdl.yaml", _SATISFIABLE)
    # Call one decides SAT; call two probes the canonical first domain value,
    # where an undetected timeout would skip it and forge a non-lexicographic
    # witness while still claiming canonical-lexicographic selection.
    _force_unknown_on_call(monkeypatch, target_call=2)

    with pytest.raises(SatisfiabilityOperationalError):
        analyze_scenario_file(source)


def test_duplicate_clause_ids_rejected_at_solver_boundary(tmp_path: Path) -> None:
    source = _write(tmp_path, "satisfiable.sdl.yaml", _SATISFIABLE)
    model = analyze_scenario_file(source).normalized_model
    # ``model_copy`` bypasses contract validation to inject a collapsed clause
    # id; the solver must reject it rather than track the assumption twice.
    duplicated = model.model_copy(update={"clauses": model.clauses + (model.clauses[0],)})

    with pytest.raises(SolverOperationalError, match="duplicate clause ids"):
        solve_model(duplicated)


def test_empty_target_domain_is_unsatisfiable(tmp_path: Path) -> None:
    source = _write(tmp_path, "empty-target-domain.sdl.yaml", _EMPTY_TARGET_DOMAIN)

    evidence = analyze_scenario_file(source)

    assert evidence.outcome is SatisfiabilityOutcome.UNSATISFIABLE
    assert evidence.unsat_core is not None
    # The count target admits only values >= 1, so a {0} domain produces an empty
    # membership clause that must resolve to false, not a bare zero-argument Or.
    assert any(clause.allowed_values == () for clause in evidence.normalized_model.clauses)
