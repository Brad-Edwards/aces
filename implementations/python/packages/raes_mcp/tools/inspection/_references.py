"""Cross-reference analysis and ASCII topology rendering for the SDL inspection tools."""

from __future__ import annotations


def _element_references(scenario, name: str) -> str:
    """Show what an element references and what references it."""
    outgoing: list[str] = []
    incoming: list[str] = []

    ref_map = _build_reference_map(scenario)
    for (src_section, src_name), targets in ref_map.items():
        src_key = f"{src_section}.{src_name}"
        for tgt in targets:
            if src_name == name or src_key == name:
                outgoing.append(tgt)
            if tgt == name or tgt.endswith(f".{name}"):
                incoming.append(src_key)

    lines = [f"References for '{name}':"]

    if outgoing:
        lines.append(f"\n  Outgoing ({len(outgoing)}):")
        for ref in sorted(set(outgoing)):
            lines.append(f"    -> {ref}")
    else:
        lines.append("\n  No outgoing references found.")

    if incoming:
        lines.append(f"\n  Incoming ({len(incoming)}):")
        for ref in sorted(set(incoming)):
            lines.append(f"    <- {ref}")
    else:
        lines.append("\n  No incoming references found.")

    return "\n".join(lines)


def _full_reference_graph(scenario) -> str:
    """Build a summary of all cross-references in the scenario."""
    ref_map = _build_reference_map(scenario)
    if not ref_map:
        return "No cross-references found in this scenario."

    lines = ["Cross-reference graph:"]
    for (src_section, src_name), targets in sorted(ref_map.items()):
        if targets:
            targets_str = ", ".join(sorted(targets))
            lines.append(f"  {src_section}.{src_name} -> {targets_str}")

    return "\n".join(lines)


def _build_reference_map(scenario) -> dict[tuple[str, str], list[str]]:
    """Extract cross-section references from a scenario.

    Returns a dict mapping (section, element_name) -> list of referenced names.
    This is a best-effort extraction covering the most important references.
    """
    refs: dict[tuple[str, str], list[str]] = {}

    # Nodes -> features, conditions, vulnerabilities
    for name, node in scenario.nodes.items():
        targets: list[str] = []
        if node.features:
            targets.extend(node.features.keys())
        if node.conditions:
            targets.extend(node.conditions.keys())
        if node.vulnerabilities:
            targets.extend(node.vulnerabilities)
        if targets:
            refs[("nodes", name)] = targets

    # Infrastructure -> nodes, links, dependencies
    for name, infra in scenario.infrastructure.items():
        targets = []
        if infra.links:
            targets.extend(infra.links)
        if infra.dependencies:
            targets.extend(infra.dependencies)
        if targets:
            refs[("infrastructure", name)] = targets

    # Features -> dependencies
    for name, feat in scenario.features.items():
        if feat.dependencies:
            refs[("features", name)] = list(feat.dependencies)

    # Events -> precondition assertions, injects
    for name, event in scenario.events.items():
        targets = []
        if event.assertions:
            targets.extend(event.assertions)
        if event.injects:
            targets.extend(event.injects)
        if targets:
            refs[("events", name)] = targets

    for name, proposition in scenario.propositions.items():
        refs[("propositions", name)] = [*proposition.subjects, *proposition.evidence_requirements]

    for name, assertion in scenario.assertions.items():
        refs[("assertions", name)] = [assertion.proposition]

    # Scripts -> events
    for name, script in scenario.scripts.items():
        if script.events:
            refs[("scripts", name)] = list(script.events.keys())

    # Stories -> scripts
    for name, story in scenario.stories.items():
        if story.scripts:
            refs[("stories", name)] = list(story.scripts)

    # Relationships -> source, target
    for name, rel in scenario.relationships.items():
        targets = []
        if rel.source:
            targets.append(rel.source)
        if rel.target:
            targets.append(rel.target)
        if targets:
            refs[("relationships", name)] = targets

    # Accounts -> node
    for name, acct in scenario.accounts.items():
        if acct.node:
            refs[("accounts", name)] = [acct.node]

    # Content -> target
    for name, content in scenario.content.items():
        if content.target:
            refs[("content", name)] = [content.target]

    # Agents -> entity, accounts, etc.
    for name, agent in scenario.agents.items():
        targets = []
        if agent.entity:
            targets.append(agent.entity)
        if agent.starting_accounts:
            targets.extend(agent.starting_accounts)
        if targets:
            refs[("agents", name)] = targets

    # Objectives -> agent/entity, targets, success refs, deps
    for name, obj in scenario.objectives.items():
        targets = []
        if obj.agent:
            targets.append(obj.agent)
        if obj.entity:
            targets.append(obj.entity)
        if obj.targets:
            targets.extend(obj.targets)
        if obj.depends_on:
            targets.extend(obj.depends_on)
        if obj.success:
            targets.extend(obj.success.assertions)
        if targets:
            refs[("objectives", name)] = targets

    # Injects -> entities
    for name, inject in scenario.injects.items():
        targets = []
        if inject.from_entity:
            targets.append(inject.from_entity)
        if inject.to_entities:
            targets.extend(inject.to_entities)
        if targets:
            refs[("injects", name)] = targets

    return refs


def _build_diagram(scenario) -> str:
    """Build an ASCII topology diagram."""
    from raes.nodes import NodeType

    lines = [f"Topology: {scenario.name}", "=" * 40]

    # Group VMs by their connected switches
    switch_to_vms: dict[str, list[str]] = {}
    unlinked_vms: list[str] = []

    switches = [name for name, node in scenario.nodes.items() if node.type == NodeType.SWITCH]
    vms = [name for name, node in scenario.nodes.items() if node.type == NodeType.VM]

    for sw in switches:
        switch_to_vms[sw] = []

    for vm_name in vms:
        infra = scenario.infrastructure.get(vm_name)
        if infra and infra.links:
            for link in infra.links:
                if link in switch_to_vms:
                    switch_to_vms[link].append(vm_name)
        else:
            unlinked_vms.append(vm_name)

    # Render each switch and its connected VMs
    for sw_name in switches:
        connected = switch_to_vms.get(sw_name, [])
        sw_infra = scenario.infrastructure.get(sw_name)
        cidr = ""
        if sw_infra and sw_infra.properties:
            props = sw_infra.properties
            if hasattr(props, "cidr") and props.cidr:
                cidr = f" ({props.cidr})"
            elif isinstance(props, list) and props:
                pass  # complex properties

        sw_node = scenario.nodes.get(sw_name)
        desc = ""
        if sw_node and sw_node.description:
            desc = f" - {sw_node.description}"

        lines.append(f"\n[{sw_name}]{cidr}{desc}")
        if connected:
            for i, vm in enumerate(connected):
                connector = "├── " if i < len(connected) - 1 else "└── "
                vm_node = scenario.nodes.get(vm)
                svc_info = ""
                if vm_node and vm_node.services:
                    svc_names = [s.name for s in vm_node.services if s.name]
                    if svc_names:
                        svc_info = f"  [{', '.join(svc_names)}]"
                lines.append(f"  {connector}{vm}{svc_info}")
        else:
            lines.append("  (no VMs connected)")

    if unlinked_vms:
        lines.append("\n[unlinked VMs]")
        for vm in unlinked_vms:
            lines.append(f"  └── {vm}")

    # Show infrastructure dependencies
    deps_found = False
    for name, infra in scenario.infrastructure.items():
        if infra.dependencies:
            if not deps_found:
                lines.append("\n--- Dependencies ---")
                deps_found = True
            for dep in infra.dependencies:
                lines.append(f"  {name} --> {dep}")

    return "\n".join(lines)
