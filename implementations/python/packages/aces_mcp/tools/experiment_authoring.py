"""Experiment authoring tools — validate, scaffold, and retrieve experiment specs.

These tools let agents author an experiment *specification* — the pre-run
authoring/input counterpart to the archival experiment-core outputs
(run/study/apparatus-context). An experiment spec binds a task to a run plan
(replication, seeds, episode controls, red-variant selection, condition
assignments) so an experiment can be specified and validated before execution.
See ADR-074 and specs/formal/experiment-core/.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Maximum input size to prevent resource exhaustion via YAML bombs or
# extremely large payloads. 64 KiB matches the SDL authoring tools.
_MAX_INPUT_BYTES = 64 * 1024


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / ".ground-control.yaml").exists():
            return candidate
    raise RuntimeError(f"could not locate aces-sdl repo root from {start}")


_REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
_EXAMPLES_DIR = _REPO_ROOT / "examples" / "experiments"

_ALLOWED_EXAMPLES = {
    "sweep": "techvault-red-tactic-sweep.exp.yaml",
    "smoke": "techvault-smoke-run.exp.yaml",
}


def _run_experiment_validate(spec_content: str) -> str:
    """Validate experiment-spec YAML and render a human-readable result."""
    if len(spec_content.encode("utf-8", errors="replace")) > _MAX_INPUT_BYTES:
        return f"INPUT TOO LARGE — limit is {_MAX_INPUT_BYTES} bytes."

    from aces_contracts.experiment_spec import (
        ExperimentSpecValidationError,
        parse_experiment_spec,
    )

    try:
        spec = parse_experiment_spec(spec_content)
    except ExperimentSpecValidationError as exc:
        return f"VALIDATION ERROR — the experiment spec is invalid.\n\nDetails:\n{exc.details}"

    run_plan = spec.run_plan
    allocation = run_plan.allocation
    run_count = (
        f"  compared conditions: {len(allocation.compared_conditions)}"
        if allocation is not None
        else f"  target run count: {run_plan.target_run_count}"
    )
    parts = [
        f"VALID — experiment spec '{spec.spec_id}' (v{spec.spec_version}) parsed successfully.",
        f"  task_ref: {spec.task_ref.ref_id}",
        f"  run-count source: {'allocation' if allocation is not None else 'target_run_count'}",
        f"  stochastic controls: {len(run_plan.stochastic_controls)}",
        f"  red-variant selections: {len(run_plan.red_variant_selections)}",
        f"  factors: {len(spec.factors)}",
        f"  capture-spec refs: {len(spec.capture_spec_refs)}",
        run_count,
    ]
    return "\n".join(parts)


def _run_experiment_scaffold(complexity: str, spec_id: str, task_ref_id: str) -> str:
    """Render a starter experiment-spec skeleton for the requested complexity."""
    key = complexity.lower().strip()
    if key not in ("minimal", "sweep"):
        return "Invalid complexity. Choose: 'minimal' or 'sweep'."
    template = _SCAFFOLD_MINIMAL if key == "minimal" else _SCAFFOLD_SWEEP
    return template.replace("{spec_id}", spec_id).replace("{task_ref_id}", task_ref_id)


def _run_experiment_get_example(name: str) -> str:
    """Return an allowlisted worked experiment-spec example."""
    filename = _ALLOWED_EXAMPLES.get(name.lower().strip())
    if filename is None:
        return f"Unknown example '{name}'. Available: {', '.join(sorted(_ALLOWED_EXAMPLES))}"
    path = _EXAMPLES_DIR / filename
    if not path.exists():
        return f"Example file not found: {filename}"
    return path.read_text(encoding="utf-8")


def register(mcp: FastMCP) -> None:
    """Register experiment authoring tools on the MCP server."""

    @mcp.tool(
        name="experiment_validate",
        description=(
            "Parse and validate an authored experiment specification (YAML for the "
            "experiment-authoring-input contract). Returns either a success "
            "confirmation with a short summary, or the structured validation "
            "errors found.\n\n"
            "An experiment spec is the pre-run design: it references an "
            "experiment task and declares the run plan (stochastic controls/seeds, "
            "episode controls such as turn order / step count / termination, "
            "red-variant selections, and either a condition allocation or a simple "
            "target run count). Pass the full YAML as `spec_content`."
        ),
    )
    def experiment_validate(spec_content: str) -> str:
        return _run_experiment_validate(spec_content)

    @mcp.tool(
        name="experiment_scaffold",
        description=(
            "Generate a starter experiment-specification skeleton (valid YAML you "
            "can edit). Choose a complexity level: 'minimal' (a single-condition "
            "design using target_run_count) or 'sweep' (a two-condition red-variant "
            "comparison using an allocation plan). Optionally provide a spec id and "
            "the task id the design targets."
        ),
    )
    def experiment_scaffold(
        complexity: str = "minimal",
        spec_id: str = "my-experiment-spec",
        task_ref_id: str = "task-example-v1",
    ) -> str:
        return _run_experiment_scaffold(complexity, spec_id, task_ref_id)

    @mcp.tool(
        name="experiment_get_example",
        description=(
            "Get a complete, annotated experiment-specification example. Available "
            "examples: 'sweep' (a two-condition red-tactic comparison with an "
            "allocation plan) and 'smoke' (a minimal single-condition design using "
            "target_run_count). Use 'sweep' to see the full authoring surface."
        ),
    )
    def experiment_get_example(name: str) -> str:
        return _run_experiment_get_example(name)


# ---------------------------------------------------------------------------
# Scaffold templates
# ---------------------------------------------------------------------------

_SCAFFOLD_MINIMAL = """\
schema_version: experiment-authoring-input/v1
spec_id: {spec_id}
spec_version: 1.0.0
title: My experiment
description: A minimal single-condition experiment design.

# Reference the separately authored experiment task (experiment-task-v1).
task_ref:
  ref_kind: task
  ref_id: {task_ref_id}
  ref_version: 1.0.0

run_plan:
  stochastic_controls:
    - control_id: episode-seed
      role: seed
      value: 1
      description: Base RNG seed.
  episode_control:
    turn_order: sequential
    max_steps: 100
    termination_rule: Terminate each episode after 100 logical steps.
  # Exactly one of allocation / target_run_count.
  target_run_count: 10
"""

_SCAFFOLD_SWEEP = """\
schema_version: experiment-authoring-input/v1
spec_id: {spec_id}
spec_version: 1.0.0
title: My red-variant sweep
description: A two-condition comparison of red variants with seeded replication.

task_ref:
  ref_kind: task
  ref_id: {task_ref_id}
  ref_version: 1.0.0

run_plan:
  stochastic_controls:
    - control_id: episode-seed
      role: seed
      value: 1
      description: Base RNG seed; per-run seeds derived deterministically.
  episode_control:
    turn_order: sequential
    max_steps: 100
    termination_rule: Terminate each episode after 100 logical steps.
  allocation:
    allocation_unit: run
    allocation_method: balanced
    compared_conditions:
      - cond-a
      - cond-b
    condition_assignments:
      cond-a:
        condition_id: cond-a
        factor_levels:
          red-variant: variant-a
        required_parameters:
          - name: red_variant
            value: variant-a
            value_kind: protocol
      cond-b:
        condition_id: cond-b
        factor_levels:
          red-variant: variant-b
        required_parameters:
          - name: red_variant
            value: variant-b
            value_kind: protocol
    target_runs_per_condition: 50
    replication_policy: 50 independent seeded runs per condition.
  red_variant_selections:
    variant-a:
      variant_id: variant-a
      agent_ref: red-agent
    variant-b:
      variant_id: variant-b
      agent_ref: red-agent

factors:
  red-variant:
    name: Red variant
    factor_kind: treatment
    levels:
      - variant-a
      - variant-b
"""
