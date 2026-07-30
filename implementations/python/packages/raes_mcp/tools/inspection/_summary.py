"""Scenario summary rendering for the SDL inspection tools."""

from __future__ import annotations

from ._common import _MAX_RECURSION_DEPTH, _SECTION_FIELDS


def _build_summary(scenario) -> str:
    """Build a human-readable summary of a scenario."""
    from raes.nodes import NodeType

    lines = [
        f"Scenario: {scenario.name}",
    ]
    if scenario.description:
        lines.append(f"Description: {scenario.description.strip()}")
    if scenario.version != "*":
        lines.append(f"Version: {scenario.version}")

    # Section counts
    lines.append("\n--- Sections ---")
    total_elements = 0
    for field in _SECTION_FIELDS:
        data = getattr(scenario, field, None)
        if data:
            count = len(data)
            total_elements += count
            lines.append(f"  {field}: {count}")
    lines.append(f"  (total named elements: {total_elements})")

    # Topology stats
    vm_count = 0
    switch_count = 0
    for node in scenario.nodes.values():
        if node.type == NodeType.VM:
            vm_count += 1
        elif node.type == NodeType.SWITCH:
            switch_count += 1
    if scenario.nodes:
        lines.append("\n--- Topology ---")
        lines.append(f"  VMs: {vm_count}")
        lines.append(f"  Switches: {switch_count}")

    # Variables
    if scenario.variables:
        lines.append("\n--- Variables ---")
        for var_name, var in scenario.variables.items():
            default_str = f" (default: {var.default})" if var.default is not None else ""
            req = " [required]" if var.required else ""
            lines.append(f"  ${{{var_name}}}: {var.type.value}{default_str}{req}")

    # Entities hierarchy
    if scenario.entities:
        lines.append("\n--- Entities ---")
        _format_entities(scenario.entities, lines, indent=2)

    # Objectives summary
    if scenario.objectives:
        lines.append("\n--- Objectives ---")
        for obj_name, obj in scenario.objectives.items():
            actor = obj.agent or obj.entity
            deps = f" (depends: {', '.join(obj.depends_on)})" if obj.depends_on else ""
            lines.append(f"  {obj_name}: actor={actor}{deps}")

    # Workflows summary
    if scenario.workflows:
        lines.append("\n--- Workflows ---")
        for wf_name, wf in scenario.workflows.items():
            step_count = len(wf.steps) if wf.steps else 0
            lines.append(f"  {wf_name}: {step_count} steps, start={wf.start}")

    return "\n".join(lines)


def _format_entities(entities: dict, lines: list[str], indent: int, depth: int = 0) -> None:
    """Recursively format entity hierarchy."""
    if depth > _MAX_RECURSION_DEPTH:
        lines.append(" " * indent + "(truncated — max depth reached)")
        return
    prefix = " " * indent
    for name, entity in entities.items():
        role_str = f" ({entity.role.value})" if entity.role and hasattr(entity.role, "value") else ""
        display = entity.name or name
        lines.append(f"{prefix}{name}: {display}{role_str}")
        if entity.entities:
            _format_entities(entity.entities, lines, indent + 2, depth + 1)
